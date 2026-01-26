Voici une **revue de vérification (audit de conformité)** basée **uniquement** sur les extraits fournis : CI/CD, modèle métier, endpoints, et cohérence Front ↔ Back.

---

## 1) CI/CD : le correctif “path mismatch” est plausible… mais `deploy.yml` est actuellement fragile

### 1.1. Erreur YAML probable : étape vide

Dans votre `deploy.yml` :

```yaml
  - name: Deploy over SSH
  - name: Setup SSH
    uses: webfactory/ssh-agent@v0.9.0
```

La ligne `- name: Deploy over SSH` est une **step sans `run:` ni `uses:`**. GitHub Actions va très souvent **refuser** ou **échouer** au parsing/validation (selon la tolérance du runner, mais c’est typiquement invalide).
✅ Correctif : supprimer cette step ou lui donner un `run:`.

### 1.2. Les secrets “sanity check” ne vérifient pas `GHCR_USER/GHCR_PAT`

Vous faites le login GHCR **sur le VPS** avec `GHCR_USER/GHCR_PAT`, mais votre “Sanity check deploy secrets” ne teste pas leur présence.
✅ Ajoutez :

* `GHCR_USER`
* `GHCR_PAT`

Sinon le déploiement plantera au moment du `docker login`.

### 1.3. `docker compose -f infra/docker/docker-compose.prod.yml ...` : OK, mais attention à `VPS_PATH`

Vous faites :

```bash
cd ${{ secrets.VPS_PATH }}
docker compose -f infra/docker/docker-compose.prod.yml pull
```

Cela suppose que :

* le repo est effectivement cloné dans `VPS_PATH`
* et que `infra/docker/docker-compose.prod.yml` existe **relativement** à ce path.

✅ À vérifier sur le VPS :
`ls -la $VPS_PATH/infra/docker/docker-compose.prod.yml`

---

## 2) Domaine métier : structure globale cohérente, mais transitions d’état incomplètes / incohérentes

Vous avez un triptyque :

* `Exam` (source, barème, correcteurs assignés)
* `Booklet` (fascicule staging)
* `Copy` (entité finale, statut)

C’est une bonne modélisation **en intention**. Mais dans le code visible :

### 2.1. Incohérence “BookletSplitView” : ne scinde pas, ne respecte pas le payload front

Votre Front (Vue) appelle :

```js
POST /api/exams/booklets/<id>/split/
body: { split_at: splitIndex }
```

Or votre `BookletSplitView` :

* **ignore totalement** `split_at`
* ne modifie aucun modèle
* ne crée aucun nouveau fascicule
* ne fait que **rendre une image de header** (crop top 20%) et renvoie un `HttpResponse(image/png)`.

➡️ Conclusion : **fonctionnalité annoncée “scission” = non implémentée** dans l’extrait.
✅ À faire pour que ce soit réel :

* lire `split_at`
* créer **2 Booklets** (ou 1 nouveau + mise à jour de l’existant)
* réécrire `start_page/end_page`
* régénérer `pages_images` (ou recalculer un sous-ensemble, selon architecture)
* faire ça en transaction, et refuser si copy associée ≠ STAGING.

### 2.2. `BookletDetailView.perform_destroy` : usage de `serializers.ValidationError` mais `serializers` non importé

Vous avez :

```python
raise serializers.ValidationError(...)
```

Mais je ne vois pas `from rest_framework import serializers` dans le fichier montré.
➡️ Risque : **NameError runtime** au premier delete.

### 2.3. Machine à états “ADR-003” : timestamps et champs `locked_by` non alimentés

Vous avez prévu :

* `validated_at`, `locked_at`, `graded_at`, `locked_by`

Mais dans les vues montrées :

* `MergeBookletsView` crée une `Copy` en **READY** directement sans `validated_at`
* `ExamUploadView` crée des copies STAGING sans lien clair vers un “validate”
* le “locking” et la traçabilité ne sont pas visibles ici

➡️ Conclusion : la machine à états existe **dans le modèle**, mais elle n’est pas démontrée comme **enforced + auditée** dans les endpoints visibles.

---

## 3) API / URLs : incohérences et erreurs de référence probables

Dans `urls.py` vous écrivez :

```python
from .views import (
    ExamUploadView, BookletListView, ExamListView, BookletHeaderView,
    ExamDetailView, CopyListView, MergeBookletsView, ExportAllView, CSVExportView,
    CopyIdentificationView, UnidentifiedCopiesView, StudentCopiesView,
    CopyImportView, ExamSourceUploadView, BookletSplitView, BookletDetailView
)
```

Puis dans `urlpatterns` :

```python
path('booklets/<uuid:id>/split/', views.BookletSplitView.as_view(), name='booklet-split'),
path('booklets/<uuid:id>/', views.BookletDetailView.as_view(), name='booklet-detail'),
```

➡️ Problème : vous utilisez `views.BookletSplitView` alors que vous avez importé `BookletSplitView` directement, et surtout **`views` n’est pas importé** dans l’extrait.

✅ Correctif : choisir **une seule** forme.

* Soit `from . import views` + `views.BookletSplitView`
* Soit `BookletSplitView.as_view()` directement

### Autre point : `BookletHeaderView` est importé mais dans vos extraits, je ne le vois pas défini (vous avez `BookletSplitView` qui renvoie un header PNG, mais pas `BookletHeaderView`).

➡️ Risque : **ImportError** au lancement.

---

## 4) CSV Pronote : “à vérifier” est une alerte réelle (et le code actuel est risqué)

Votre `CSVExportView` :

* dépend de `c.scores.exists()` et `c.scores.first()`
  Or, dans le `Copy` model fourni, je ne vois **aucune relation** `scores`. Sauf si elle est dans un autre fichier non collé.

➡️ Si `scores` n’existe pas : **AttributeError** et export CSV impossible.

* le total :

```python
total = sum(float(v) for v in data.values() if v)
```

Si un champ contient `""`, `"NA"`, `None`, ou un objet, c’est fragile.

✅ Ce que je recommande (opinion assumée) :
Tant que l’export “Pronote-compatible” n’est pas **testé avec un jeu de données réel**, vous n’êtes pas en “ready prod”. C’est un point de non-régression critique.

---

## 5) Settings “hardening” : bonne direction, mais une faille logique sur DEBUG/production

Vous avez :

```python
DEBUG = os.environ.get("DEBUG", "True").lower() == "true"
DJANGO_ENV = os.environ.get("DJANGO_ENV", "development")
if DJANGO_ENV == "production" and not RATELIMIT_ENABLE:
    raise ...
```

Mais **DEBUG ne dépend pas de DJANGO_ENV**.

➡️ Cas dangereux : `DJANGO_ENV=production` mais `DEBUG` non défini → DEBUG vaut `"True"` → donc DEBUG=True en prod.
C’est exactement le genre d’accident qui arrive.

✅ Correctif simple et robuste :

* mettre `DEBUG` par défaut à False
* ou forcer `DEBUG = False` si `DJANGO_ENV=production`

Exemple logique attendue :

* `DJANGO_ENV=production` ⇒ DEBUG doit être False **quoi qu’il arrive**.

---

## 6) “DEPLOY_PRODUCTION.md” : document utile, mais il manque 2-3 garde-fous essentiels

Votre guide est globalement bon (clone, .env, secrets, logs, rollback).
Mais je conseille fortement d’ajouter :

1. **Check de santé** post-déploiement côté VPS (pas juste `/api/health/`) :

* `docker compose ps`
* `docker compose logs --tail=200 backend`
* test de création d’un examen / upload

2. **Persistance** :

* confirmation explicite des volumes : `media`, DB (Postgres)
* procédure de backup/restore (même minimale)

3. **Gestion TLS/Nginx** :

* si vous restez sur HTTP: ok en LAN, pas en internet
* si production réelle : TLS + reverse proxy + HSTS cohérents avec `SSL_ENABLED`

---

## 7) Verdict “Go/No-Go” sur la base de vos extraits

### Ce qui est réellement “OK” (à ce que je vois)

* Architecture globale (Exam/Booklet/Copy) : logique.
* Pipeline CI build/push : cohérent.
* Durcissement security headers : direction correcte.
* Documentation de déploiement : base solide.

### Ce qui empêche de fermer le ticket “Prod ready” sans réserve

1. **Split** : la feature “scinder” est (dans l’extrait) une illusion : endpoint ne fait pas le split et ne lit pas `split_at`.
2. **URLs / imports** : risques d’erreurs immédiates (`views.` sans import, `BookletHeaderView` manquant).
3. **Export CSV** : dépendance `scores` non garantie + parsing fragile.
4. **DEBUG en prod possible** si env incomplet : risque majeur.

👉 Mon avis : **No-Go tant que ces 4 points ne sont pas verrouillés par tests ou vérification locale**.

---

## 8) Checklist de vérification finale (concrète, reproductible)

Sans me demander le repo complet, vous pouvez valider vous-même en 15 minutes :

### A. Lancement backend

* `python manage.py check`
* `python manage.py urls` (ou juste runserver) : vérifier qu’il n’y a **aucune ImportError**

### B. API staging

* upload exam PDF : `POST /api/exams/upload/`
  vérifier que `booklets_created > 0` et que `booklets` existent
* split sur un booklet : `POST /api/exams/booklets/<id>/split/` avec `split_at`
  vérifier : **2 booklets au lieu de 1** (si c’est bien l’intention produit)
* delete booklet : vérifier absence de NameError `serializers`

### C. CSV Pronote

* exporter CSV sur un examen avec copies corrigées
* ouvrir dans Excel/LibreOffice
* importer dans Pronote (ou au moins vérifier format strict demandé)

### D. CI/CD

* vérifier que `deploy.yml` passe la validation YAML (la step vide)
* vérifier la présence de tous secrets, y compris GHCR_USER/GHCR_PAT
* vérifier sur VPS : `docker compose ps` + `curl /api/health/`

Voici un **plan de patch minimal** (fichiers + modifications attendues) pour atteindre vos 4 objectifs **sans élargir le périmètre** au-delà des missions **Korrigo V1** (import/traitement CSV, endpoints stables, exécution reproductible, comportement prod sûr).

> Hypothèse raisonnable (alignée “minimal patch”) : le projet est un **Django** (vu `urls.py`, `DEBUG`) et “split” correspond à une fonctionnalité attendue de **découpage** (données/CSV) actuellement “présente mais non opérationnelle” (stub, endpoint cassé, logique non branchée, etc.). Le patch ci-dessous est conçu pour fonctionner même si l’implémentation actuelle est partielle.

---

## 1) Rendre “split” réellement fonctionnel

### Objectif minimal (V1)

* “split” doit **faire réellement quelque chose d’utile** et vérifiable : découper un CSV en *N* fichiers **ou** produire un *train/test split* déterministe.
* Le plus robuste en V1 est le **split en chunks** (pas de ML implicite) : *input CSV → fichiers de sortie chunk_001.csv …*.

### Fichiers à modifier / créer

#### A. Créer un service pur (testable) : `korrigo/core/services/split.py` *(nouveau)*

Contenu attendu :

* Fonction pure, indépendante de Django :

  * `split_csv(input_path: Path, output_dir: Path, rows_per_file: int, *, encoding="utf-8-sig", delimiter=",") -> list[Path]`
* Règles :

  * Conserve l’en-tête.
  * Ouvre les fichiers avec `newline=""` (csv module).
  * Valide `rows_per_file >= 1`.
  * Retourne la liste des fichiers générés (utile pour tests).

#### B. Exposer split via un point d’entrée stable

Choisir **un seul** mécanisme V1 (minimal) :

**Option 1 (recommandée V1)** : commande Django

* `korrigo/core/management/commands/split_csv.py` *(nouveau)*
  Permet d’exécuter :
* `python manage.py split_csv --input data.csv --out out/ --rows 5000 --delimiter ","`

**Option 2** : endpoint HTTP (si déjà prévu dans V1)

* `korrigo/core/views.py` *(modifier)*
* `korrigo/core/urls.py` *(modifier ou créer)*
  Expose `POST /api/split` avec un chemin de fichier serveur (ou upload si déjà existant).
  ⚠️ Minimal V1 = éviter l’upload si pas déjà dans le scope.

👉 **Plan minimal** : implémenter **Option 1** (commande) + éventuellement l’endpoint **uniquement** si déjà documenté/attendu.

### Critères d’acceptation

* Lancer la commande sur un CSV réel produit des chunks corrects.
* Même entrée → même sortie (hors timestamp) : reproductible.
* En cas d’erreur (fichier absent, en-tête manquant, rows_per_file invalide), le message est clair et le code sort non-zéro (commande).

---

## 2) Corriger `urls.py`

### Objectif minimal

* `urls.py` doit :

  * démarrer (imports OK),
  * router correctement,
  * ne pas servir de “static/media” en prod,
  * éviter les collisions de noms/paths.

### Fichiers à modifier

#### A. `korrigo/urls.py` *(modifier)*

Modifications attendues (pattern Django standard) :

1. Importer correctement :

   * `from django.contrib import admin`
   * `from django.urls import path, include`
2. S’assurer que `urlpatterns` contient :

   * `path("admin/", admin.site.urls)`
   * `path("api/", include("korrigo.core.urls"))` *(ou votre app réelle)*
3. N’ajouter `static()` **que si** `settings.DEBUG` est True :

   * `from django.conf import settings`
   * `from django.conf.urls.static import static`
   * `if settings.DEBUG: urlpatterns += static(...)`

#### B. `korrigo/core/urls.py` *(créer ou modifier)*

* Déclarer explicitement les routes V1 (dont split si HTTP) :

  * `path("split/", views.split_view, name="split")` (si endpoint requis)
  * sinon, **aucun endpoint split** (commande only).

### Critères d’acceptation

* `python manage.py check` OK
* `python manage.py runserver` démarre sans erreur d’import/URLconf
* En prod, pas de `static()`.

---

## 3) Sécuriser `DEBUG` en prod

### Objectif minimal

* `DEBUG` ne doit **jamais** être True en prod, même si l’environnement est mal configuré.
* Les secrets doivent provenir d’ENV, pas du code.

### Fichiers à modifier

#### A. `korrigo/settings.py` *(modifier)* — patch minimal sans refactor en `settings/base.py`

Modifs attendues :

1. Introduire une variable d’environnement “mode” (ou `DJANGO_ENV`) :

   * `ENV = os.getenv("DJANGO_ENV", "dev").lower()`
2. Définir `DEBUG` ainsi :

   * En dev (ENV=dev) : `DEBUG = os.getenv("DJANGO_DEBUG", "1") == "1"`
   * En prod (ENV=prod) : `DEBUG = False` **forcé** (ignorant toute autre valeur)
3. Forcer `SECRET_KEY` en prod :

   * `SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "dev-insecure-key")`
   * si `ENV == "prod"` et `DJANGO_SECRET_KEY` absent → `raise ImproperlyConfigured(...)`
4. Durcir `ALLOWED_HOSTS` en prod :

   * `ALLOWED_HOSTS = os.getenv("DJANGO_ALLOWED_HOSTS", "localhost").split(",")`
   * si prod et `ALLOWED_HOSTS` vide ou `["*"]` → lever erreur.
5. (Si pertinent) `CSRF_TRUSTED_ORIGINS` via ENV en prod.

#### B. `.env.example` *(nouveau)* (optionnel mais très utile)

* Documenter les variables attendues :

  * `DJANGO_ENV=dev|prod`
  * `DJANGO_DEBUG=0|1`
  * `DJANGO_SECRET_KEY=...`
  * `DJANGO_ALLOWED_HOSTS=example.com,www.example.com`

### Critères d’acceptation

* En prod (`DJANGO_ENV=prod`), `DEBUG` est False quoi qu’il arrive.
* Une config prod incomplète échoue explicitement au démarrage (meilleur que “prod insecure”).

---

## 4) Rendre le CSV robuste et testable

### Objectif minimal (V1)

* Parsing CSV fiable (encodage, séparateur, en-têtes).
* Les erreurs sont **explicites** (exceptions dédiées).
* Tests unitaires reproductibles sur des fixtures CSV.

### Fichiers à modifier / créer

#### A. Créer un module d’I/O CSV : `korrigo/core/services/csv_io.py` *(nouveau)*

Contenu attendu :

* `class CsvSchemaError(Exception)` / `class CsvReadError(Exception)`
* `read_csv(path, *, encoding="utf-8-sig", delimiter=",", required_headers=None) -> tuple[list[str], list[dict]]`

  * Utiliser `csv.DictReader`
  * Valider :

    * fichier non vide,
    * en-têtes présents,
    * `required_headers ⊆ headers`.
* Option “dialect sniff” minimal (facultatif) :

  * si delimiter non fourni, tenter `csv.Sniffer().sniff(...)` sur quelques KB.
  * **mais** garder un fallback stable (`,`), sinon tests plus fragiles.

#### B. Brancher `split.py` sur `csv_io.py`

* `split_csv` doit utiliser `csv_io` pour :

  * lire/valider l’en-tête proprement,
  * écrire proprement les chunks.

#### C. Ajouter une suite de tests

Choix minimal :

* Si projet Django : `pytest` + `pytest-django` **ou** `unittest` standard Django.

Fichiers :

* `tests/test_csv_io.py` *(nouveau)*

  * cas nominal : CSV utf-8-sig + delimiter `,`
  * cas erreur : en-tête manquant, fichier vide, mauvais delimiter
* `tests/test_split.py` *(nouveau)*

  * split en 2–3 chunks, vérifie :

    * nombre de fichiers,
    * présence en-tête,
    * nombre total de lignes reconstitué = original.

Fixtures :

* `tests/fixtures/sample_ok.csv`
* `tests/fixtures/sample_bad_headers.csv`
* `tests/fixtures/empty.csv`

#### D. (Optionnel minimal mais utile) Ajouter un `Makefile` ou scripts

* `Makefile` *(nouveau)* :

  * `test: pytest -q`
  * `lint` si déjà existant (sinon, ne pas ajouter).

### Critères d’acceptation

* Tests passent en CI et local.
* Une erreur CSV produit une exception claire, pas un “KeyError” ou un crash silencieux.
* Le split est déterministe et vérifiable par tests.

---

## Synthèse patch “minimal” (checklist fichiers)

### Créations

* `korrigo/core/services/csv_io.py`
* `korrigo/core/services/split.py`
* `korrigo/core/management/commands/split_csv.py` *(si commande retenue)*
* `korrigo/core/urls.py` *(si manquant)*
* `tests/test_csv_io.py`
* `tests/test_split.py`
* `tests/fixtures/*.csv`
* `.env.example` *(optionnel)*

### Modifications

* `korrigo/urls.py`
* `korrigo/settings.py`
* (éventuel) `korrigo/core/views.py` si split HTTP déjà prévu

---

## Ce que je recommande (opinion assumée, V1 pragmatique)

* **Commande `split_csv`** en V1 : c’est le chemin le plus propre, le plus testable, le moins risqué (pas d’upload, pas d’auth, pas de surface HTTP).
* Endpoint HTTP uniquement si vous avez déjà une UI/API explicitement prévue dans les missions V1.
* Forcer `DEBUG=False` en prod **sans discussion** : c’est typiquement le genre de détail qui ruine un déploiement sinon.

# Cahier des charges — Patch minimal (diffs & correctifs) aligné Korrigo V1

## 0) Contexte et périmètre

Vous demandez un **plan de patch minimal** (puis des diffs) pour :

1. rendre **“split” réellement fonctionnel**
2. **corriger `urls.py`**
3. **sécuriser `DEBUG` en production**
4. rendre l’**import CSV robuste et testable**

Le tout **sans élargir le scope** (pas de refonte architecture, pas de migrations DB, pas de changements front, pas de nouvelles dépendances lourdes), et **aligné avec Korrigo V1** (OCR/Identification → Grading → gestion élèves, endpoints API, E2E seed, etc.).

> Remarque importante (qualité de la matière fournie) : votre extrait de `backend/core/settings.py` est **tronqué au milieu** d’une configuration CSP (dictionnaire `CONTENT_SECURITY_POLICY`). Le cahier des charges ci-dessous propose donc des modifications **strictement localisées** autour des lignes existantes `DEBUG` / `DJANGO_ENV`, sans réécrire le bloc CSP (afin d’éviter d’introduire un état invalide).

---

## 1) Objectifs mesurables (Definition of Done)

### DoD global

Le patch est considéré “terminé” si :

* **Production safety** : en environnement `DJANGO_ENV=production`, il est **impossible** de démarrer avec `DEBUG=True` (échec explicite et immédiat), et **le défaut** ne met plus DEBUG à vrai.
* **URLs** : les routes existantes restent accessibles (missions 17/18/étapes), pas de collision de préfixes, **static media** uniquement en debug (ou configuration explicitement contrôlée), et l’endpoint `/api/health/` fonctionne toujours.
* **Split** : `A3Splitter.process_scan()` ne renvoie plus un placeholder “left/right uniquement”, mais un résultat exploitable : **type (RECTO/VERSO/UNKNOWN)** + **pages ordonnées** (au minimum recto/verso déterminés et pages associées), sans fuite de fichiers temporaires.
* **CSV** : un service de lecture CSV robuste existe, **testé unitairement**, et la commande `import_students` l’utilise (testable sans DB dans la partie parsing).

---

## 2) Contraintes “périmètre minimal”

* Modifications limitées aux fichiers suivants (et ajouts minimaux nécessaires aux tests/services) :

  * `backend/core/settings.py`
  * `backend/core/urls.py`
  * `backend/processing/services/splitter.py`
  * `backend/students/management/commands/import_students.py`
  * **Ajouts** : un module service parsing CSV + un test unitaire (minimum)
* Aucune dépendance externe additionnelle obligatoire (pas de `chardet`, pas de librairie PDF supplémentaire, etc.).
* Ne pas changer la signature publique des endpoints existants (compatibilité Korrigo V1).

---

## 3) Spécifications détaillées par patch

## Patch A — Sécuriser `DEBUG` en production (`backend/core/settings.py`)

### Problème actuel

```python
DEBUG = os.environ.get("DEBUG", "True").lower() == "true"
```

* **Défaut dangereux** : DEBUG actif par défaut (même si `DJANGO_ENV=production`).

### Exigences fonctionnelles

1. Introduire une logique “safe-by-default” :

   * Si `DJANGO_ENV=production`, alors **DEBUG doit être False** sauf impossibilité (mais dans ce cahier, on impose un garde-fou : **refus de démarrer** si DEBUG est True).
2. Maintenir la compatibilité dev :

   * En dev, `DEBUG` peut être activé par variable d’environnement.
3. Garde-fou :

   * Si `DJANGO_ENV=production` et `DEBUG=True` → **raise explicite** (RuntimeError ou ValueError, message clair).

### Exigences non-fonctionnelles

* Changement **localisé** (éviter d’intervenir dans la partie CSP tronquée).
* Ne pas casser la logique existante “SSL_ENABLED / E2E”.

### Critères d’acceptation

* `DJANGO_ENV=production` + `DEBUG=True` → le serveur Django **ne démarre pas** (erreur claire).
* `DJANGO_ENV=production` + `DEBUG` absent → DEBUG **False**.
* `DJANGO_ENV=development` + `DEBUG` absent → comportement conforme au souhait minimal (au choix : True ou False, mais recommandé : True en dev uniquement si explicitement assumé).
  **Recommandation Korrigo** : `DEBUG` dev reste possible, mais pas “par accident en prod”.

---

## Patch B — Corriger / durcir `urls.py` (`backend/core/urls.py`)

### Problèmes / risques actuels

1. **Collision/ambiguïté potentielle** :
   `path('api/', include('grading.urls'))` est très large et peut masquer ou entrer en conflit avec d’autres routes `api/*` si `grading.urls` contient des patterns génériques.
2. **Static media servi en toutes circonstances** :
   `urlpatterns += static(settings.MEDIA_URL, ...)` est ajouté sans condition ; en prod, ce n’est pas souhaitable (c’est le rôle du reverse proxy / stockage).
3. Import d’éléments “dev” conditionnels : OK, mais à garder net.

### Exigences fonctionnelles

1. Préfixer `grading` de manière explicite (minimal) :

   * Remplacer `path('api/', include('grading.urls'))` par quelque chose de non ambigu :
     **ex** `path('api/grading/', include('grading.urls'))`
   * ou bien, si Korrigo V1 impose déjà certains chemins “dans grading” sous `/api/...`, on doit **préserver les URLs existantes**. Dans ce cas :

     * documenter précisément les routes contenues dans `grading.urls` (non fourni ici),
     * et éviter la collision en vérifiant l’exhaustivité des patterns.
   * **Choix minimal recommandé** : `api/grading/` (moins de risques).
2. Static media :

   * N’ajouter `static()` **que si `settings.DEBUG`** (ou variable dédiée E2E si vous avez besoin en environnement de tests).
3. Conserver :

   * `api/health/`
   * `api/schema/`, `api/docs/`, `api/redoc/`
   * `api/dev/seed/` conditionnel à `E2E_SEED_TOKEN`
   * endpoints auth (`login/logout/me/...`) et users.

### Critères d’acceptation

* Démarrage Django sans warnings d’URLs dupliquées/masquées.
* `/api/health/` répond.
* En prod : pas de `urlpatterns += static(...)`.
* Si vous migrez `grading` vers `/api/grading/` : mise à jour confirmée côté usages (tests/E2E), sinon **interdiction** de casser l’existant.

> Note : ce cahier des charges est strictement “patch minimal”. Si un front consomme déjà `/api/...` pour grading, il faudra soit conserver l’ancien chemin, soit fournir un alias temporaire (mais cela augmente légèrement le périmètre). À décider au moment du diff, en fonction de `grading/urls.py`.

---

## Patch C — Rendre “split” réellement fonctionnel (`backend/processing/services/splitter.py`)

### Problème actuel

`A3Splitter.process_scan()` découpe en deux moitiés et renvoie un dict contenant seulement `left/right/width/height`, avec des commentaires “placeholder”.
La logique utile existe pourtant (`determine_scan_type_and_order`, `reconstruct_booklet`) mais n’est pas intégrée.

### Exigences fonctionnelles minimales

1. `process_scan(image_path)` doit :

   * charger l’image (comme actuellement),
   * découper (gauche/droite),
   * déterminer le type (RECTO/VERSO) via `HeaderDetector` **en s’appuyant réellement** sur `determine_scan_type_and_order`,
   * renvoyer un résultat **structuré et directement exploitable**.
2. Gestion propre des temporaires :

   * `determine_scan_type_and_order` écrit un fichier temporaire (`temp_right_path`).
   * Exigence : création dans un répertoire temporaire système (`tempfile`) + suppression en fin de traitement même en cas d’erreur (try/finally).
3. Résultat attendu (contrat minimal) :

   * `type`: `"RECTO" | "VERSO" | "UNKNOWN"`
   * `pages`: dict `{"p1": ndarray, "p2": ..., "p3": ..., "p4": ...}` **si reconstruction complète possible**
     ou a minima, le dict renvoyé par `determine_scan_type_and_order` (RECTO contient p1/p4, VERSO contient p2/p3).
4. Robustesse :

   * si détection en-tête échoue (exception), renvoyer `UNKNOWN` + crops bruts, sans crash silencieux.

### Tests minimaux attendus

Sans introduire d’outils lourds :

* **Test unitaire** (si pytest disponible) : mock du `HeaderDetector.detect_header()` pour forcer RECTO/VERSO et vérifier la structure.
* Vérifier absence de fuite de fichier temporaire (au moins via appel dans un répertoire temp contrôlé).

### Critères d’acceptation

* `process_scan()` renvoie un dict avec `type` et des pages cohérentes.
* En cas d’image introuvable/illisible → exception explicite inchangée.
* Pas de “placeholder logic” restant (ou strictement cantonné au cas UNKNOWN).

---

## Patch D — CSV robuste et testable (`backend/students/management/commands/import_students.py` + nouveau service)

### Problème actuel

* Parsing CSV dans la commande, logique mêlée à la DB (difficile à tester proprement).
* Encodage `utf-8` (pas `utf-8-sig`) + BOM patch local.
* Délimiteur “;” forcé (OK si spéc imposée) mais pas réellement robuste.
* Validation d’en-têtes implicite.

### Exigences fonctionnelles

1. Extraire le parsing CSV dans un module dédié, pur et testable :

   * ex : `backend/students/services/import_csv.py`
2. Fonction attendue (contrat) :

   * lecture fichier,
   * support `utf-8-sig`,
   * normalisation en-têtes,
   * détection simple du séparateur si non imposé (ou conserver `;` si c’est la norme Korrigo V1),
   * validation des champs requis : `INE`, `NOM`, `PRENOM` (et idéalement `CLASSE`, `EMAIL` optionnels).
3. La commande `import_students` :

   * appelle le service pour obtenir une liste de dict normalisés,
   * puis exécute la logique `update_or_create` comme actuellement (minimum),
   * conserve les compteurs success/errors et logs.

### Tests minimaux attendus

* Test unitaire du service de parsing CSV :

  * utilise un CSV fixture (si existante dans le repo) ou un CSV “inline” créé en temp.
  * vérifie que :

    * BOM ne casse pas le premier header,
    * les champs sont trim,
    * lignes vides ignorées,
    * champs requis manquants → erreur ou marquage explicite (selon choix minimal).
* (Optionnel mais utile) test d’intégration Django minimal : pas requis dans le scope minimal.

### Critères d’acceptation

* Le parsing est testable indépendamment de Django ORM.
* La commande continue de fonctionner avec le format annoncé.
* Les erreurs CSV sont plus explicites (ligne, champ manquant, etc.).

---

## 4) Paramètres d’environnement (contrats attendus)

### Production / E2E

* `DJANGO_ENV` :

  * `production` active les garde-fous (DEBUG interdit)
  * `development` / défaut : comportement dev
* `DEBUG` :

  * reconnu, mais **interdit en prod**
* `SSL_ENABLED` :

  * inchangé (déjà présent)
* `ALLOWED_HOSTS`, `CORS_ALLOWED_ORIGINS`, `RATELIMIT_ENABLE` :

  * inchangés

---

## 5) Plan de validation (checklist de recette)

### A. Config

* [ ] Lancer avec `DJANGO_ENV=production` sans `DEBUG` : DEBUG False.
* [ ] Lancer avec `DJANGO_ENV=production` et `DEBUG=True` : crash explicite.
* [ ] Lancer en dev : fonctionne comme avant.

### B. URLs

* [ ] `GET /api/health/` → 200 OK
* [ ] `GET /api/schema/` → OK
* [ ] `GET /api/docs/` → OK
* [ ] `POST /api/login/` → OK (si user test)
* [ ] En prod : pas de route static media servie par Django

### C. Split

* [ ] Appel `process_scan(path)` renvoie `type` + pages attendues selon mock detect_header.
* [ ] Pas de fichier temporaire résiduel.

### D. CSV

* [ ] Test unitaire parsing passe.
* [ ] Commande sur CSV réel : succès, erreurs cohérentes.

---

## 6) Livrables attendus (format “diff/patch”)

Pour chaque patch (A→D), vous attendez ensuite un **diff unifié** (`git diff`) avec :

* liste exacte des fichiers modifiés/ajoutés,
* modifications minimales,
* tests ajoutés (au moins pour le parsing CSV et/ou split via mock),
* aucune modification hors scope.

---

## 7) Points de décision (à trancher “minimalement” avant d’écrire les diffs)

1. **URL grading** : peut-on déplacer `grading.urls` sous `/api/grading/` sans casser les consumers ?

   * Si oui : c’est la correction la plus propre et minimale côté collisions.
   * Si non : il faudra conserver `/api/` mais s’assurer que `grading.urls` n’a pas de patterns “catch-all”.

2. **CSV séparateur** : Korrigo V1 impose-t-il strictement `;` ?

   * Si oui : on conserve `;` par défaut, détection optionnelle uniquement si besoin.
   * Si non : auto-détection simple (virgule/point-virgule/tab).

---

Ci-dessous : **(A) cahier des charges “patch minimal”** puis **(B) patch diff exact (unified diff, ligne par ligne)**, strictement sur le périmètre demandé :

* rendre **split** réellement fonctionnel (service A3),
* corriger **`urls.py`** (notamment **préfixe grading**),
* sécuriser **`DEBUG`** en prod,
* rendre l’import **CSV** **robuste et testable** (**séparateur virgule** par défaut),
* rester aligné “missions Korrigo V1” (MVP, pas de refonte).

---

## A) Cahier des charges minimal (spécifications patch)

### 1) Sécurisation `DEBUG` en production (`backend/core/settings.py`)

**Objectif :** empêcher tout démarrage en prod avec un `DEBUG=True` accidentel, tout en gardant un comportement souple en dev.

**Exigences :**

* Introduire `DJANGO_ENV` **tôt** (au début du fichier), en minuscules.
* Comportement :

  * si `DJANGO_ENV=production` :

    * `DEBUG` doit être **False par défaut** si variable `DEBUG` absente,
    * si `DEBUG=true` est explicitement fourni ⇒ **raise ValueError** (fail fast).
  * sinon (dev) : conserver la compatibilité actuelle (`DEBUG` par défaut à True).
* Adapter les gardes existantes qui testent `os.environ.get("DJANGO_ENV")` pour utiliser `DJANGO_ENV`.

**Non-objectifs :**

* Ne pas restructurer le reste du settings (CSP, CORS, etc.), uniquement patch minimal.

---

### 2) Correction et rationalisation des routes (`backend/core/urls.py`)

**Objectif :**

* corriger l’intégration `grading` via un **préfixe dédié** (vous avez demandé “pour le grading choisissez le préfix”),
* éviter de servir les médias via Django en prod.

**Exigences :**

* Remplacer :

  * `path('api/', include('grading.urls'))`
  * par **`path('api/grading/', include('grading.urls'))`**
* Servir `MEDIA_URL` via `static()` **uniquement en DEBUG** :

  * En prod, ce sera Nginx/serveur web qui servira `/media/`.
* Ne pas changer les autres endpoints ni leur structure (missions Korrigo V1).

---

### 3) “Split” réellement fonctionnel (`backend/processing/services/splitter.py`)

**Objectif :** passer d’un placeholder à un service exploitable en prod (sans refacto lourde).

**Exigences minimales :**

* `process_scan(image_path)` doit :

  * charger l’image,
  * la couper en 2 moitiés,
  * exécuter la détection d’en-tête (via `HeaderDetector.detect_header`) sur la moitié **droite**,
  * retourner une structure **stable** :

    * `type`: `RECTO|VERSO`,
    * `left_page`, `right_page`,
    * `has_header` (bool),
    * et **`pages`** (mapping `p1/p4` ou `p2/p3`) conforme à `determine_scan_type_and_order`.
* Gestion safe du fichier temporaire :

  * usage de `tempfile.NamedTemporaryFile(delete=False)` pour fournir un chemin au détecteur,
  * suppression du fichier temporaire en `finally` (pas de fuite).
* Aucune dépendance nouvelle hors stdlib.

**Non-objectifs :**

* Ne pas implémenter un pipeline PDF complet ni écrire sur disque les pages finales ; on rend le service **appelable** et cohérent.

---

### 4) Import CSV robuste et testable (`backend/students/management/commands/import_students.py` + nouveau service + tests)

**Objectif :** sortir la logique métier du `Command.handle()` afin de pouvoir la tester sans lancer la commande, et fiabiliser l’import.

**Exigences :**

* **Séparateur : virgule (`,`) par défaut.**
* Ajouter un module de service (nouveau fichier) qui :

  * détecte le séparateur si besoin (`csv.Sniffer`) mais **privilégie la virgule**,
  * gère BOM (`utf-8-sig`),
  * normalise les entêtes (trim + upper),
  * valide les champs requis : `INE`, `NOM`, `PRENOM` (classe/email optionnels),
  * retourne un objet résultat testable (compteurs + erreurs structurées).
* La commande Django devient un simple “wrapper” :

  * vérifie l’existence du fichier,
  * appelle le service,
  * affiche un résumé final.
* Ajouter des tests (pytest / pytest-django compatible) couvrant :

  * import nominal (création),
  * ré-import (update),
  * ligne invalide (skip + erreur structurée).

**Non-objectifs :**

* Ne pas ajouter de dépendances externes, ne pas changer le modèle Student.

---

## B) Patch diff exact (unified diff)

> **Note** : je fournis ici un patch “git apply” standard.
> Il crée 2 nouveaux fichiers (`csv_import.py` + tests) et modifie uniquement les 4 fichiers du périmètre.

---

### 1) `backend/core/settings.py` — DEBUG prod safe + DJANGO_ENV centralisé

```diff
diff --git a/backend/core/settings.py b/backend/core/settings.py
index 1111111..2222222 100644
--- a/backend/core/settings.py
+++ b/backend/core/settings.py
@@ -1,11 +1,26 @@
 import os
 import dj_database_url
 from pathlib import Path
 
 BASE_DIR = Path(__file__).resolve().parent.parent
 
+# Environment
+DJANGO_ENV = os.environ.get("DJANGO_ENV", "development").lower()
+
 # Security: No dangerous defaults in production
 SECRET_KEY = os.environ.get("SECRET_KEY")
 if not SECRET_KEY:
-    if os.environ.get("DJANGO_ENV") == "production":
+    if DJANGO_ENV == "production":
         raise ValueError("SECRET_KEY environment variable must be set in production")
     # Development fallback only
     SECRET_KEY = "django-insecure-dev-only-" + "x" * 50
 
-DEBUG = os.environ.get("DEBUG", "True").lower() == "true"
+_debug_env = os.environ.get("DEBUG")
+if DJANGO_ENV == "production":
+    # Safe default in production: DEBUG must be False unless explicitly set,
+    # and we hard-fail if someone tries DEBUG=True.
+    DEBUG = (_debug_env or "False").lower() == "true"
+    if DEBUG:
+        raise ValueError("DEBUG must be False in production environment")
+else:
+    # Development-friendly default
+    DEBUG = (_debug_env or "True").lower() == "true"
 
 # ALLOWED_HOSTS: Explicit configuration required
 ALLOWED_HOSTS = os.environ.get("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")
-if "*" in ALLOWED_HOSTS and os.environ.get("DJANGO_ENV") == "production":
+if "*" in ALLOWED_HOSTS and DJANGO_ENV == "production":
     raise ValueError("ALLOWED_HOSTS cannot contain '*' in production")
@@ -143,10 +158,9 @@ RATELIMIT_USE_CACHE = 'default'
 
 # Enable/disable django-ratelimit via env (default: enabled)
 # Can be disabled for E2E testing environment only
 RATELIMIT_ENABLE = os.environ.get("RATELIMIT_ENABLE", "true").lower() == "true"
 
 # Production guard: prevent accidental rate limiting disable in production
-DJANGO_ENV = os.environ.get("DJANGO_ENV", "development")
 if DJANGO_ENV == "production" and not RATELIMIT_ENABLE:
     raise ValueError("RATELIMIT_ENABLE cannot be false in production environment")
```

---

### 2) `backend/core/urls.py` — préfixe grading + média uniquement en DEBUG

```diff
diff --git a/backend/core/urls.py b/backend/core/urls.py
index 3333333..4444444 100644
--- a/backend/core/urls.py
+++ b/backend/core/urls.py
@@ -1,7 +1,7 @@
 from django.contrib import admin
 from django.urls import path, include
 from django.conf import settings
 from django.conf.urls.static import static
 from core import views
 from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView
 
 urlpatterns = [
     path('admin/', admin.site.urls),
     path('api/exams/', include('exams.urls')),
     path('api/copies/', include('exams.urls_copies')), # Mission 17
     path('api/students/', include('students.urls')), # Mission 18
     path('api/identification/', include('identification.urls')), # ÉTAPE 1-2: OCR & Identification
-    path('api/', include('grading.urls')),  # Étape 3: Annotations & Grading
+    path('api/grading/', include('grading.urls')),  # Étape 3: Annotations & Grading (prefixed)
     path('api/login/', views.LoginView.as_view(), name='login'),
     path('api/logout/', views.LogoutView.as_view(), name='logout'),
     path('api/me/', views.UserDetailView.as_view(), name='user_detail'),
     path('api/settings/', views.GlobalSettingsView.as_view(), name='settings'),
     path('api/change-password/', views.ChangePasswordView.as_view(), name='change_password'),
     path('api/users/', views.UserListView.as_view(), name='user_list'),
     path('api/users/<int:pk>/', views.UserManageView.as_view(), name='user_manage'),
 ]
@@ -33,4 +33,7 @@ urlpatterns += [
         path('api/dev/seed/', seed_e2e_endpoint, name='seed_e2e'),
     ]
 
-urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
+if settings.DEBUG:
+    # Only serve media via Django in dev. In production, serve via reverse proxy (Nginx).
+    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
```

---

### 3) `backend/processing/services/splitter.py` — split A3 réellement exploitable

```diff
diff --git a/backend/processing/services/splitter.py b/backend/processing/services/splitter.py
index 5555555..6666666 100644
--- a/backend/processing/services/splitter.py
+++ b/backend/processing/services/splitter.py
@@ -1,6 +1,8 @@
 import cv2
 import numpy as np
+import os
+import tempfile
 from django.utils.translation import gettext_lazy as _
 from .vision import HeaderDetector
 
 class A3Splitter:
@@ -18,7 +20,7 @@ class A3Splitter:
     def process_scan(self, image_path: str):
         """
         Découpe une image A3 en deux A4 et détermine si c'est un Recto ou un Verso.
         
@@ -34,44 +36,53 @@ class A3Splitter:
                 'right_page': numpy.ndarray,
                 'has_header': bool
             }
         """
         image = cv2.imread(image_path)
         if image is None:
             raise ValueError(_("Impossible de lire l'image : ") + image_path)
 
-        height, width, _ = image.shape
+        height, width, _ = image.shape
         
         # Découpage vertical strict à 50%
         mid_x = width // 2
         left_crop = image[:, :mid_x]
         right_crop = image[:, mid_x:]
 
-        # Sauvegarde temporaire pour la détection (HeaderDetector attend un chemin)
-        # Optimisation: HeaderDetector pourrait accepter un ndarray directement.
-        # Pour ce MVP, on suppose que HeaderDetector a été refactorisé ou on garde l'API path.
-        # Modifions HeaderDetector pour accepter une image en mémoire si on pouvait, 
-        # mais respectons l'interface existante. Hack: sauvegarder temp.
-        
-        # Pour l'instant on réimplémente une logique simple ou on mock.
-        # Utilisons la logique "Right Half has Header => Recto"
-        
-        # Simuler la détection sur la partie DROITE
-        # En prod, on passerait right_crop à detector.detect_header_from_array(right_crop)
-        
-        # Placeholder logic: On assume que create_temp_file est géré ailleurs. 
-        # Ici on retourne les crops.
-        
-        return {
-            'left': left_crop,
-            'right': right_crop,
-            'width': width,
-            'height': height
-        }
+        # HeaderDetector attend un chemin : on écrit temporairement la partie droite
+        tmp_path = None
+        try:
+            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
+                tmp_path = tmp.name
+
+            # Détermine type + ordre logique (p1/p4 ou p2/p3)
+            order_data = self.determine_scan_type_and_order(
+                left_img=left_crop,
+                right_img=right_crop,
+                temp_right_path=tmp_path
+            )
+
+            return {
+                'type': order_data['type'],
+                'left_page': left_crop,
+                'right_page': right_crop,
+                'has_header': (order_data['type'] == 'RECTO'),
+                'pages': order_data['pages'],
+                'width': width,
+                'height': height,
+            }
+        finally:
+            if tmp_path and os.path.exists(tmp_path):
+                try:
+                    os.remove(tmp_path)
+                except OSError:
+                    # Best effort cleanup: do not hide main processing result
+                    pass
 
     def determine_scan_type_and_order(self, left_img, right_img, temp_right_path: str) -> dict:
         """
         Détermine si le scan est Recto ou Verso en cherchant un en-tête à droite.
```

---

### 4) CSV : extraction logique + virgule par défaut + tests

#### 4.1 Nouveau service : `backend/students/services/csv_import.py`

```diff
diff --git a/backend/students/services/csv_import.py b/backend/students/services/csv_import.py
new file mode 100644
index 0000000..7777777
--- /dev/null
+++ b/backend/students/services/csv_import.py
@@ -0,0 +1,178 @@
+from __future__ import annotations
+
+import csv
+from dataclasses import dataclass, field
+from typing import Dict, Iterable, List, Optional, Tuple, Type
+
+from django.db import transaction
+
+
+REQUIRED_FIELDS = ("INE", "NOM", "PRENOM")
+OPTIONAL_FIELDS = ("CLASSE", "EMAIL")
+
+
+@dataclass
+class ImportErrorItem:
+    row: int
+    message: str
+    data: Dict[str, str] = field(default_factory=dict)
+
+
+@dataclass
+class ImportResult:
+    delimiter: str
+    created: int = 0
+    updated: int = 0
+    skipped: int = 0
+    errors: List[ImportErrorItem] = field(default_factory=list)
+
+
+def _normalize_key(key: str) -> str:
+    return (key or "").strip().upper()
+
+
+def _normalize_value(value: Optional[str]) -> str:
+    return (value or "").strip()
+
+
+def detect_delimiter(sample: str, default: str = ",") -> str:
+    """
+    Best-effort delimiter detection. We keep comma as the default separator,
+    but accept sniffed delimiters when the file clearly uses another one.
+    """
+    try:
+        dialect = csv.Sniffer().sniff(sample, delimiters=[",", ";", "\t"])
+        return dialect.delimiter or default
+    except Exception:
+        return default
+
+
+def read_rows_from_csv(fp, delimiter: Optional[str] = None) -> Tuple[str, Iterable[Dict[str, str]]]:
+    """
+    Returns (delimiter_used, iterator over raw rows).
+    """
+    # Read a small sample for delimiter sniffing, then rewind.
+    sample = fp.read(4096)
+    fp.seek(0)
+
+    delimiter_used = delimiter or detect_delimiter(sample, default=",")
+
+    reader = csv.DictReader(fp, delimiter=delimiter_used)
+
+    # Normalize BOM in first header if present
+    if reader.fieldnames:
+        reader.fieldnames = [fn.replace("\ufeff", "") if fn else fn for fn in reader.fieldnames]
+
+    return delimiter_used, reader
+
+
+def parse_students_csv(path: str, delimiter: str = ",") -> Tuple[ImportResult, List[Dict[str, str]]]:
+    """
+    Parse file into normalized rows without touching the DB.
+    """
+    result = ImportResult(delimiter=delimiter)
+    rows: List[Dict[str, str]] = []
+
+    # utf-8-sig handles BOM robustly
+    with open(path, "r", encoding="utf-8-sig", newline="") as f:
+        delimiter_used, reader = read_rows_from_csv(f, delimiter=delimiter)
+        result.delimiter = delimiter_used
+
+        for idx, row in enumerate(reader, start=1):
+            if not row:
+                result.skipped += 1
+                continue
+
+            normalized: Dict[str, str] = {}
+            for k, v in row.items():
+                nk = _normalize_key(k)
+                if not nk:
+                    continue
+                normalized[nk] = _normalize_value(v)
+
+            # Validate required fields
+            missing = [k for k in REQUIRED_FIELDS if not normalized.get(k)]
+            if missing:
+                result.skipped += 1
+                result.errors.append(
+                    ImportErrorItem(
+                        row=idx,
+                        message=f"Missing required fields: {', '.join(missing)}",
+                        data=normalized,
+                    )
+                )
+                continue
+
+            # Keep only known fields + required
+            cleaned = {
+                "INE": normalized.get("INE", ""),
+                "NOM": normalized.get("NOM", ""),
+                "PRENOM": normalized.get("PRENOM", ""),
+                "CLASSE": normalized.get("CLASSE", ""),
+                "EMAIL": normalized.get("EMAIL", ""),
+            }
+            rows.append(cleaned)
+
+    return result, rows
+
+
+def import_students_rows(rows: List[Dict[str, str]], student_model) -> ImportResult:
+    """
+    Apply rows to DB. Separated from parsing to keep it testable.
+    """
+    result = ImportResult(delimiter=",")
+
+    for i, r in enumerate(rows, start=1):
+        ine = r["INE"]
+        last_name = r["NOM"]
+        first_name = r["PRENOM"]
+        class_name = r.get("CLASSE", "")
+        email = r.get("EMAIL", "")
+
+        try:
+            with transaction.atomic():
+                obj, created = student_model.objects.update_or_create(
+                    ine=ine,
+                    defaults={
+                        "first_name": first_name,
+                        "last_name": last_name,
+                        "class_name": class_name,
+                        "email": email,
+                    },
+                )
+            if created:
+                result.created += 1
+            else:
+                result.updated += 1
+        except Exception as e:
+            result.errors.append(
+                ImportErrorItem(
+                    row=i,
+                    message=str(e),
+                    data=r,
+                )
+            )
+
+    return result
+
+
+def import_students_from_csv(path: str, student_model, delimiter: str = ",") -> ImportResult:
+    """
+    High-level helper: parse + import.
+    """
+    parse_result, rows = parse_students_csv(path, delimiter=delimiter)
+    db_result = import_students_rows(rows, student_model=student_model)
+
+    # Merge results (delimiter + skipped/errors from parsing + created/updated/errors from DB)
+    merged = ImportResult(delimiter=parse_result.delimiter)
+    merged.created = db_result.created
+    merged.updated = db_result.updated
+    merged.skipped = parse_result.skipped
+    merged.errors = [*parse_result.errors, *db_result.errors]
+    return merged
```

---

#### 4.2 `backend/students/management/commands/import_students.py` — devient wrapper + virgule

```diff
diff --git a/backend/students/management/commands/import_students.py b/backend/students/management/commands/import_students.py
index 8888888..9999999 100644
--- a/backend/students/management/commands/import_students.py
+++ b/backend/students/management/commands/import_students.py
@@ -1,78 +1,48 @@
 from django.core.management.base import BaseCommand
 from students.models import Student
-import csv
 import os
+from students.services.csv_import import import_students_from_csv
 
 class Command(BaseCommand):
-    help = 'Imports students from a CSV file (Format: INE;NOM;PRENOM;CLASSE;EMAIL)'
+    help = 'Imports students from a CSV file (Format: INE,NOM,PRENOM,CLASSE,EMAIL)'
 
     def add_arguments(self, parser):
         parser.add_argument('csv_file', type=str, help='Path to the CSV file')
 
     def handle(self, *args, **options):
         csv_file_path = options['csv_file']
 
         if not os.path.exists(csv_file_path):
             self.stdout.write(self.style.ERROR(f'File not found: {csv_file_path}'))
             return
 
         self.stdout.write(f'Importing students from {csv_file_path}...')
 
-        success_count = 0
-        error_count = 0
-
         try:
-            with open(csv_file_path, 'r', encoding='utf-8') as f:
-                # Detect delimiter if needed, or assume ';' based on spec
-                reader = csv.DictReader(f, delimiter=';')
-                
-                # Check for BOM just in case
-                if reader.fieldnames and reader.fieldnames[0].startswith('\ufeff'):
-                     reader.fieldnames[0] = reader.fieldnames[0].replace('\ufeff', '')
-                
-                # Expected Columns: INE, NOM, PRENOM, CLASSE, EMAIL
-                # Allow case-insensitive matching or standard names
-                
-                for row_idx, row in enumerate(reader, start=1):
-                    # Normalized keys
-                    row_clean = {k.strip().upper(): v.strip() for k, v in row.items() if k}
-                    
-                    ine = row_clean.get('INE')
-                    last_name = row_clean.get('NOM')
-                    first_name = row_clean.get('PRENOM')
-                    class_name = row_clean.get('CLASSE')
-                    email = row_clean.get('EMAIL', '')
-
-                    if not ine or not last_name or not first_name:
-                        self.stdout.write(self.style.WARNING(f'Skipping Row {row_idx}: Missing required fields (INE/NOM/PRENOM) - Data: {row}'))
-                        error_count += 1
-                        continue
-
-                    try:
-                        student, created = Student.objects.update_or_create(
-                            ine=ine,
-                            defaults={
-                                'first_name': first_name,
-                                'last_name': last_name,
-                                'class_name': class_name,
-                                'email': email
-                            }
-                        )
-                        action = "Created" if created else "Updated"
-                        # self.stdout.write(f'{action}: {student}') # Verbose
-                        success_count += 1
-                    except Exception as e:
-                        self.stdout.write(self.style.ERROR(f'Error Row {row_idx}: {e}'))
-                        error_count += 1
-
-            self.stdout.write(self.style.SUCCESS(f'Import Complete. Success: {success_count}, Errors: {error_count}'))
-
+            result = import_students_from_csv(csv_file_path, student_model=Student, delimiter=',')
+            self.stdout.write(
+                self.style.SUCCESS(
+                    "Import Complete. "
+                    f"Created: {result.created}, Updated: {result.updated}, "
+                    f"Skipped: {result.skipped}, Errors: {len(result.errors)}, "
+                    f"Delimiter: '{result.delimiter}'"
+                )
+            )
+            if result.errors:
+                for err in result.errors[:50]:
+                    self.stdout.write(self.style.WARNING(f"Row {err.row}: {err.message}"))
         except Exception as e:
-             self.stdout.write(self.style.ERROR(f'Failed to read CSV: {e}'))
+            self.stdout.write(self.style.ERROR(f'Import failed: {e}'))
```

---

#### 4.3 Tests : `backend/students/tests/test_import_students_csv.py`

```diff
diff --git a/backend/students/tests/test_import_students_csv.py b/backend/students/tests/test_import_students_csv.py
new file mode 100644
index 0000000..aaaaaaa
--- /dev/null
+++ b/backend/students/tests/test_import_students_csv.py
@@ -0,0 +1,74 @@
+import pytest
+
+from students.models import Student
+from students.services.csv_import import import_students_from_csv
+
+
+@pytest.mark.django_db
+def test_import_students_from_csv_creates_and_updates(tmp_path):
+    p = tmp_path / "students.csv"
+    p.write_text(
+        "INE,NOM,PRENOM,CLASSE,EMAIL\n"
+        "1234A,Dupont,Jean,T1,jean.dupont@example.com\n"
+        "5678B,Martin,Lea,T2,lea.martin@example.com\n",
+        encoding="utf-8",
+    )
+
+    res1 = import_students_from_csv(str(p), student_model=Student, delimiter=",")
+    assert res1.created == 2
+    assert res1.updated == 0
+    assert res1.skipped == 0
+    assert len(res1.errors) == 0
+
+    # Update same INE with different values
+    p.write_text(
+        "INE,NOM,PRENOM,CLASSE,EMAIL\n"
+        "1234A,Dupont,Jean,T3,jean.dupont@example.com\n",
+        encoding="utf-8",
+    )
+    res2 = import_students_from_csv(str(p), student_model=Student, delimiter=",")
+    assert res2.created == 0
+    assert res2.updated == 1
+    assert res2.skipped == 0
+    assert len(res2.errors) == 0
+
+
+@pytest.mark.django_db
+def test_import_students_from_csv_skips_invalid_rows(tmp_path):
+    p = tmp_path / "students_invalid.csv"
+    p.write_text(
+        "INE,NOM,PRENOM,CLASSE,EMAIL\n"
+        ",Dupont,Jean,T1,jean.dupont@example.com\n"
+        "9999C,,Sarah,T1,sarah@example.com\n"
+        "1111D,Valid,Student,T1,valid@example.com\n",
+        encoding="utf-8",
+    )
+
+    res = import_students_from_csv(str(p), student_model=Student, delimiter=",")
+    assert res.created == 1
+    assert res.updated == 0
+    assert res.skipped == 2
+    assert len(res.errors) == 2
```

---

## Points d’intégration / vérifications (mini checklist)

1. **URLs**

* Vérifier rapidement que `grading.urls` ne “double-préfixe” pas déjà (ex: s’il contient `path('grading/...')`).

  * Avec le patch : base = `/api/grading/…`

2. **Prod safety**

* Démarrage en prod (`DJANGO_ENV=production`) :

  * sans `DEBUG` ⇒ `DEBUG=False` OK
  * avec `DEBUG=true` ⇒ crash volontaire (sécurité)

3. **CSV**

* Le service accepte par défaut `delimiter=","` (exigence),
* il est testable isolément (parse + import),
* erreurs structurées + compteurs déterministes.

4. **Split**

* `process_scan()` n’est plus un placeholder : il renvoie `type/has_header/pages` cohérents et nettoie le temporaire.




