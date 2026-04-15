# Architecture Korrigo v2

> **Version** : 3.0.0
> **Date** : 28 mars 2026
> **Public** : Développeurs, Architectes, DevOps
> **Production** : https://korrigo.labomaths.tn
> **Alias DNS éventuel** : https://korrigo.nexusreussite.academy

Ce document décrit l'architecture complète de la plateforme Korrigo v2, une solution de correction numérique d'examens scannés pour établissements scolaires (lycées).

---

## Table des Matières

1. [Contexte Projet](#1-contexte-projet)
2. [Stack Technique](#2-stack-technique)
3. [Applications Django](#3-applications-django)
4. [Architecture en Couches](#4-architecture-en-couches)
5. [Diagramme d'Infrastructure](#5-diagramme-dinfrastructure)
6. [Machine à États Copy (actuelle)](#6-machine-à-états-copy-actuelle)
7. [Modèle de Concurrence pour la Finalisation](#7-modèle-de-concurrence-pour-la-finalisation)
8. [Système de Coordonnées des Annotations (ADR-002)](#8-système-de-coordonnées-des-annotations-adr-002)
9. [Authentification et Autorisation](#9-authentification-et-autorisation)
10. [Services Docker (Production)](#10-services-docker-production)
11. [Workflows GitHub Actions](#11-workflows-github-actions)
12. [Patterns Architecturaux Clés](#12-patterns-architecturaux-clés)
13. [Flux de Données Métier](#13-flux-de-données-métier)
14. [Justifications Techniques](#14-justifications-techniques)

---

## 1. Contexte Projet

### Description

Korrigo est une plateforme de correction numérique d'examens scannés de bout en bout, conçue pour les établissements scolaires (lycées). Elle couvre l'intégralité du cycle de vie d'un examen :

1. **Ingestion** : upload de PDF scannés (lots A3 ou fichiers individuels A4)
2. **Anonymisation** : attribution d'un identifiant anonyme à chaque copie
3. **Identification** : OCR assisté sur l'en-tête de la copie pour lier élève et copie
4. **Dispatch** : assignation des copies aux correcteurs
5. **Correction annotée** : interface web de correction avec annotations vectorielles, barème interactif, appréciation globale
6. **Finalisation** : génération du PDF aplati (copie + annotations fusionnées)
7. **Bilans IA** : génération d'un bilan personnalisé par LLM (Ollama/qwen2.5:32b)
8. **Publication élèves** : portail élève permettant de consulter sa copie corrigée et son bilan

### Contraintes Spécifiques

- **Sans QR Code** : identification semi-automatique (OCR + validation humaine via vidéo-codage)
- **Déploiement Cloud Privé** : serveur dédié (pas SaaS multi-tenant)
- **Workflow pédagogique** : double finalité administrative (notes Pronote) et pédagogique (consultation élève)
- **Stockage fichiers local** : volumes Docker (PDF, images rasterisées)
- **Conformité RGPD** : audit trail complet, rétention et purge documentées

### URL de Production

| Domaine | Usage |
|---------|-------|
| `korrigo.labomaths.tn` | Domaine principal |
| `korrigo.nexusreussite.academy` | Alias DNS si conservé |

> Note de contexte: Korrigo est une application distincte des autres stacks présentes sur la machine de production. Les services, le code et le déploiement décrits ici concernent uniquement Korrigo.

---

## 2. Stack Technique

### Backend

| Composant | Version | Rôle |
|-----------|---------|------|
| **Python** | 3.11 | Langage principal |
| **Django** | 4.2 LTS | Framework web, ORM, Admin |
| **Django REST Framework** | 3.x | API REST |
| **Gunicorn** | — | Serveur WSGI (production) |
| **PostgreSQL** | 15 | Base de données relationnelle |
| **Redis** | 7 | Cache, broker Celery, backend résultats |
| **Celery** | 5.x | Traitement asynchrone |
| **Celery Beat** | — | Planificateur de tâches périodiques |
| **PyMuPDF (fitz)** | 1.23.26 | Manipulation PDF (rasterisation, aplatissement) |
| **OpenCV headless** | 4.8.0 | Traitement d'images (détection en-têtes) |
| **Pillow** | 12.1+ | Traitement images (crop en-tête pour OCR) |
| **Tesseract OCR** | — | OCR fallback (fra+eng) |
| **OpenAI GPT-4o-mini** | Vision | OCR principal (écriture manuscrite) |
| **Ollama** | qwen2.5:32b ou llama3.2 | LLM local pour bilans pédagogiques |
| **pdf2image** | — | Conversion PDF vers images PNG |
| **python-magic** | 0.4.27 | Validation type MIME |
| **django-ratelimit** | 4.1.0 | Protection brute force |
| **django-csp** | 3.8 | Content Security Policy |
| **prometheus-client** | 0.19.0 | Métriques monitoring |
| **DRF Spectacular** | 0.27.1 | Documentation OpenAPI 3.0 |

### Frontend

| Composant | Version | Rôle |
|-----------|---------|------|
| **Vue.js** | 3.4 | Framework UI (Composition API) |
| **Pinia** | 2.1 | State management |
| **Vue Router** | 4.2+ | Routing SPA |
| **Axios** | 1.13 | Client HTTP |
| **PDF.js** | 4.0 | Rendu PDF dans le navigateur |
| **Vite** | 5.1 | Build tool, dev server HMR |
| **TypeScript** | 5.9+ | Typage statique |
| **TailwindCSS** | 4.1 | Framework CSS utilitaire |

### Infrastructure

| Composant | Version | Rôle |
|-----------|---------|------|
| **Docker** | 20+ | Conteneurisation |
| **Docker Compose** | 2+ | Orchestration |
| **Nginx** | 1.25+ | Reverse proxy, TLS, fichiers statiques |

---

## 3. Applications Django

Le backend est organisé en **6 applications Django**, chacune avec une responsabilité claire et délimitée.

### 3.1 `core` — Fondations et Transversal

**Responsabilité** : Configuration globale, authentification, audit RGPD, profils utilisateurs, middlewares.

**Modèles** :
- `GlobalSettings` : singleton de paramétrage applicatif (`institution_name`, `theme`, `default_exam_duration`, `notifications_enabled`)
- `AuditLog` : journal d'audit RGPD centralisé (toutes actions critiques : connexion, téléchargement, déverrouillage) — rétention 12 mois
- `UserProfile` : extension du `User` Django (`must_change_password`)

**Middlewares** :
- CORS (configurable par environnement)
- CSP (Content Security Policy via `django-csp`)
- Rate limiting (via `django-ratelimit 4.1`)
- Métriques Prometheus

**Rôles utilisateurs** (`UserRole` enum via groupes Django) :
- `ADMIN` : Django superuser + groupe ADMIN — accès total
- `TEACHER` / Correcteur : `is_staff` + groupe TEACHER — accès à ses copies assignées seulement
- `STUDENT` / Élève : utilisateur standard + groupe STUDENT — portail élève uniquement

### 3.2 `exams` — Gestion des Examens et Copies

**Responsabilité** : Cycle de vie complet des examens et copies, upload de PDF, découpage, dispatch.

**Modèles principaux** :
- `ExamType` : type d'examen (BAC_BLANC, DNB_BLANC, EAM, etc.) avec code, couleur, icône
- `Exam` : examen concret avec barème JSON (`grading_structure`), correcteurs M2M, mode upload
- `Booklet` : fascicule détecté lors du split A3 (entité de staging)
- `Copy` : copie validée d'un élève — **entité centrale du système** (voir section 6)
- `ExamPDF` : fichier PDF individuel (mode INDIVIDUAL_A4)
- `ExamDocumentSet` + `ExamDocument` : gestion documentaire versionnée (sujet, corrigé, barème)
- `DocumentTextExtraction`, `DocumentPage`, `DocumentChunk` : pipeline d'extraction de texte pour suggestions contextuelles
- `JuryReport` : rapport de jury rattaché à un `ExamType`

**Modes d'upload** :
- `BATCH_A3` : scan par lots, découpage automatique en fascicules, puis fusion en copies
- `INDIVIDUAL_A4` : un PDF par élève, déjà découpé — identifiant via nom de fichier (`NOM_PRENOM_DDMMYYYY`)

**Validators sur les PDF** (`exams/validators.py`) :
- `FileExtensionValidator(['pdf'])`
- `validate_pdf_size` (max 50 MB)
- `validate_pdf_not_empty`
- `validate_pdf_mime_type` (MIME = `application/pdf`)
- `validate_pdf_integrity` (contrôle de lecture PyMuPDF)

### 3.3 `grading` — Correction et Annotations

**Responsabilité** : Tout le workflow de correction — annotations, scores, verrouillage, finalisation, audit.

**Modèles** :
- `Annotation` : annotation vectorielle sur une copie (coordonnées normalisées [0,1] selon ADR-002, verrouillage optimiste via champ `version`)
- `GradingEvent` : journal d'audit immutable — chaque transition d'état, chaque annotation créée/modifiée/supprimée
- `Score` : notes JSON par question (contrainte unicité 1 Score par Copy au niveau DB)
- `CopyLock` : verrou transitoire stocké en base pour coordination et nettoyage périodique
- `DraftState` : sauvegarde automatique de l'état de l'éditeur (anti-perte de données)
- `QuestionRemark` : remarques libres par question du barème
- `AnnotationTemplate` : banque d'annotations officielles contextualisées par exercice/question
- `UserAnnotation` : mémoire personnelle du correcteur (annotations personnelles avec compteur d'usage)
- `QuestionnaireResponse` : réponses aux questionnaires de satisfaction

**Services principaux** (`grading/services.py`) :
- `GradingService` : `add_annotation`, `update_annotation`, `delete_annotation`, `finalize_copy`, `reopen_copy`, `lock_copy`, `unlock_copy`
- `AnnotationService` : gestion du cycle de vie des annotations
- `LockConflictError` : exception métier levée en cas de conflit de verrouillage ou de double finalisation

### 3.4 `students` — Gestion des Élèves

**Responsabilité** : Référentiel des élèves, authentification par date de naissance, portail élève.

**Modèles** :
- `Student` : prénom, nom, date de naissance, classe, groupe, email, lien `OneToOne` vers `User` Django

**Authentification élève** : email + date de naissance (pas de mot de passe). Le backend crée ou récupère un `User` Django associé au `Student` et ouvre une session cookie.

**Import** : CSV via `POST /api/students/import/` — format `Nom;Prénom;Date-naissance;Email;Classe;Groupe`

### 3.5 `identification` — OCR et Identification

**Responsabilité** : Pipeline d'identification automatique des copies par OCR sur l'en-tête.

**Modèles** :
- `OCRResult` : résultat OCR (`detected_text`, `confidence`, `suggested_students` M2M)

**Pipeline OCR** :
1. Extraction de l'image d'en-tête de la copie (crop via OpenCV/Pillow)
2. Envoi à GPT-4o-mini Vision (principal) ou Tesseract (fallback)
3. Matching flou avec la base élèves (`Student`)
4. Suggestions retournées à l'opérateur (vidéo-codage) pour validation humaine

### 3.6 `processing` — Services Techniques PDF

**Responsabilité** : Traitements techniques PDF (découpage, détection en-têtes, aplatissement). Pas de modèles Django propres.

**Services** :
- `PDFSplitter` : découpage d'un PDF A3 en fascicules individuels
- `HeaderDetector` : détection et extraction de la zone d'en-tête (nom élève)
- `PDFFlattener` : fusion des annotations sur les pages PDF pour générer le `final_pdf`

---

## 4. Architecture en Couches

```
┌─────────────────────────────────────────────────────────────────────┐
│                    COUCHE PRÉSENTATION (Frontend)                    │
│  Vue 3.4 SPA  │  Pinia Stores  │  Vue Router  │  PDF.js  │  Axios   │
└────────────────────────────┬────────────────────────────────────────┘
                             │ HTTPS / JSON (session cookie)
┌────────────────────────────▼────────────────────────────────────────┐
│                     COUCHE API (Django REST Framework)               │
│  ViewSets  │  Serializers  │  Permissions RBAC  │  Session Auth      │
│  Rate limiting  │  CSP  │  CORS  │  OpenAPI (DRF Spectacular)       │
└────────────────────────────┬────────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────────┐
│                  COUCHE LOGIQUE MÉTIER (Services Layer)              │
│  GradingService  │  AnnotationService  │  PDFFlattener               │
│  OCR Pipeline  │  LLM Bilan  │  Dispatch Service                    │
│  Transactions atomiques  │  Audit Trail  │  LockConflictError        │
└────────────────────────────┬────────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────────┐
│                   COUCHE DONNÉES (Django ORM + PostgreSQL 15)        │
│  Modèles  │  Migrations  │  Index composites  │  Contraintes DB      │
│  JSONField (barème, coordonnées)  │  FileField (PDF, images)         │
└────────────────────────────┬────────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────────┐
│              COUCHE TRAITEMENT ASYNCHRONE (Celery + Redis)           │
│  flatten_copy  │  OCR pipeline  │  Bilans LLM  │  Celery Beat       │
└─────────────────────────────────────────────────────────────────────┘
```

### Séparation des responsabilités

#### Couche Présentation
Les composants Vue.js communiquent via des stores Pinia qui encapsulent tous les appels API. Aucun appel direct à Axios depuis les composants de présentation — tout passe par les services de store.

#### Couche API
Les ViewSets DRF délèguent systématiquement la logique métier au Service Layer. Ils ne contiennent que : validation des entrées (serializers), vérification des permissions, formatage de la réponse.

#### Services Layer
Isole la logique métier complexe des views. Permet les tests unitaires sans HTTP. Toutes les opérations critiques (finalisation, verrouillage) sont wrappées dans `@transaction.atomic`.

#### Couche Données
L'ORM Django joue le rôle de repository. Les index composites sont déclarés dans les `Meta.indexes` des modèles pour les patterns de requête fréquents.

---

## 5. Diagramme d'Infrastructure

```
Browser ──HTTPS──→ Nginx (443/80)
                      │
          ┌───────────┼──────────────────┐
          │           │                  │
     /static/     /api/*            /media/*
   (fichiers     (proxy pass)     (fichiers media)
    statiques)        │
                 Gunicorn :8000
                 (Django 4.2)
                 3 workers, timeout 120s
                      │
            ┌─────────┼──────────────────┐
            │         │                  │
       PostgreSQL    Redis :6379      Celery Workers
           15       (broker +          (tâches async :
        :5432       result             flatten_copy,
                   backend)           OCR pipeline,
                                      bilans LLM)
                                          │
                                    Ollama :11434
                                   (qwen2.5:32b)
                                          │
                                    OpenAI API
                                  (GPT-4o-mini Vision)
```

### Volumes Docker persistants

| Volume | Point de montage | Contenu | Criticité |
|--------|-----------------|---------|-----------|
| `postgres_data` | `/var/lib/postgresql/data` | Base de données | **CRITIQUE** |
| `media_volume` | `/app/media` | PDF sources, images rasterisées, PDF finaux | **CRITIQUE** |
| `static_volume` | `/app/staticfiles` | CSS, JS compilés, Django admin | Moyen |

> **Avertissement** : Ne jamais exécuter `docker-compose down -v` en production. Cela détruirait les volumes et toutes les données. Le backup de `postgres_data` et `media_volume` est automatisé toutes les 30 minutes vers Hetzner StorageBox.

---

## 6. Machine à États Copy (actuelle)

### États actuels (depuis migration 0027)

```python
class Copy.Status(TextChoices):
    READY        = 'READY'        # Prête à corriger
    IN_PROGRESS  = 'IN_PROGRESS'  # En cours de correction
    FINALIZED    = 'FINALIZED'    # Finalisée (PDF aplati généré)
```

### Diagramme de transitions

```
         première annotation créée
READY ──────────────────────────────→ IN_PROGRESS
  ↑                                        │
  │                                   POST /finalize/
  │                                        │
  └──────────── reopen (admin) ─── FINALIZED (PDF final généré)
```

### Transitions autorisées

| État source | Déclencheur | État cible | Acteur | Effets de bord |
|-------------|-------------|------------|--------|----------------|
| `READY` | Création de la première annotation (`AnnotationService.add_annotation`) | `IN_PROGRESS` | Correcteur | Transition automatique |
| `IN_PROGRESS` | `POST /api/grading/copies/{id}/finalize/` | `FINALIZED` | Correcteur | Génération PDF aplati, `graded_at=now()`, GradingEvent FINALIZE |
| `READY` | `POST /api/grading/copies/{id}/finalize/` | `FINALIZED` | Correcteur | Idem (copie sans annotation) |
| `FINALIZED` | Action admin `reopen` | `READY` | Superuser seulement | `final_pdf` supprimé, `graded_at=None`, `grading_retries=0`, GradingEvent REOPEN |

### Re-upload bloqué

La re-ingestion d'un PDF est bloquée si au moins une copie de l'examen est en état `IN_PROGRESS` ou `FINALIZED`. Cela protège les données de correction déjà effectuées.

### Ancienne machine à états (obsolète, pre-migration 0026)

L'ancienne machine à 5 états est **entièrement obsolète** depuis mars 2026. Elle ne doit plus être référencée ni implémentée.

```
# OBSOLÈTE — ne plus utiliser
STAGING → READY → LOCKED → GRADING_IN_PROGRESS → GRADED
                               ↓
                         GRADING_FAILED (retry max 3)
```

Les données ont été migrées automatiquement :
- `STAGING` → `READY`
- `LOCKED` → `GRADING_IN_PROGRESS` → `IN_PROGRESS`
- `GRADED` → `FINALIZED`
- `GRADING_FAILED` → `READY`

Voir [ADR-003](../decisions/ADR-003-copy-status-state-machine.md) pour l'historique complet de cette décision.

---

## 7. Modèle de Concurrence pour la Finalisation

### Problème

Lors d'une finalisation, deux requêtes HTTP concurrentes pouvaient toutes deux passer la garde `status IN (READY, IN_PROGRESS)` et appeler `flatten_copy` simultanément, provoquant deux PDF finaux corrompus ou une condition de course.

Le mécanisme `select_for_update(nowait=True)` seul ne suffisait pas à garantir l'exclusion mutuelle dans tous les cas de race condition.

### Solution actuelle

Le code courant n’utilise plus `Copy.finalizing_at`. La protection active repose sur :

1. `select_for_update(nowait=True)` pour qu’une seule transaction entre dans la phase critique
2. une mise à jour atomique du statut vers `FINALIZED`
3. un rejet explicite des doublons via `LockConflictError`

### Code de référence

```python
# backend/grading/services.py — GradingService._finalize_copy_inner

@transaction.atomic
def _finalize_copy_inner(copy, user, lock_token=None):
    copy = Copy.objects.select_for_update(nowait=True).get(id=copy.id)
    if copy.status == Copy.Status.FINALIZED:
        raise LockConflictError("Copie déjà finalisée.")
    rows_updated = Copy.objects.filter(
        id=copy.id,
        status__in=(Copy.Status.READY, Copy.Status.IN_PROGRESS),
    ).update(
        status=Copy.Status.FINALIZED,
        graded_at=timezone.now(),
        grading_error_message=None,
    )
    if rows_updated == 0:
        raise LockConflictError("Copie déjà finalisée (concurrent).")
    copy.refresh_from_db()
    # ... flatten_copy, save final_pdf ...
```

### Garanties

| Scénario | Comportement |
|----------|--------------|
| 1 requête seule | Succès normal |
| 2 requêtes concurrentes | 1 succès + 1 `LockConflictError` (HTTP 409) |
| Crash pendant flatten_copy | Transaction rollback, statut non confirmé |
| Copie déjà FINALIZED | `LockConflictError("Copie déjà finalisée.")` |

---

## 8. Système de Coordonnées des Annotations (ADR-002)

Toutes les coordonnées d'annotation (`x`, `y`, `w`, `h`) sont **normalisées dans l'intervalle [0, 1]** relatif aux dimensions de la page PDF.

**Conversion vers coordonnées absolues (PDF.js côté frontend)** :
```
x_pixels = annotation.x * page_width_px
y_pixels = annotation.y * page_height_px
w_pixels = annotation.w * page_width_px
h_pixels = annotation.h * page_height_px
```

**Avantages** :
- Indépendant de la résolution d'affichage et du zoom PDF.js
- Cohérence entre l'affichage frontend et l'aplatissement backend (PyMuPDF)
- Pas besoin de recalculer lors d'un changement de résolution de rasterisation

Voir [ADR-002](../decisions/ADR-002-pdf-coordinate-normalization.md) pour la décision complète.

---

## 9. Authentification et Autorisation

### Mécanisme d'authentification

**Session cookie Django** (pas JWT) — choix délibéré pour des raisons de sécurité :
- Cookie `HttpOnly` : inaccessible au JavaScript, protège contre le vol par XSS
- Cookie `Secure` (production) : transmission uniquement via HTTPS
- Révocation immédiate : déconnexion invalide la session côté serveur
- Protection CSRF native : intégrée à Django pour toutes les requêtes POST/PUT/DELETE

### Rôles et permissions

| Rôle | Conditions Django | Accès |
|------|-------------------|-------|
| **Admin** | `is_superuser=True` + groupe ADMIN | Accès total, y compris reopen copies, gestion utilisateurs, tous examens |
| **Correcteur** | `is_staff=True` + groupe TEACHER | Ses copies assignées uniquement (`assigned_corrector = request.user`) |
| **Élève** | `is_active=True` + groupe STUDENT | Portail élève — ses propres copies finalisées si `results_released_at` est défini |
| **Secrétariat** | `is_staff=True` + groupe TEACHER | Interface vidéo-codage OCR |

### Authentification élève

L'élève ne se connecte **pas** avec un mot de passe. Le flux est :
1. Saisie de l'adresse email et de la date de naissance sur le portail élève
2. Le backend vérifie `Student.email` + `Student.date_naissance`
3. Si correspondance : création ou récupération du `User` Django associé, ouverture de session

### Rate Limiting

Via `django-ratelimit 4.1` :
- `/api/login/` : 5 tentatives / 15 min / IP
- `/api/students/login/` : 30 tentatives / 15 min / IP
- certains endpoints métiers sensibles sont limités par utilisateur ou IP selon la vue
- Désactivé en mode test E2E (variable d'environnement `KORRIGO_DISABLE_RATELIMIT=1`)

---

## 10. Services Docker (Production)

| Service | Image | Port interne | Rôle |
|---------|-------|-------------|------|
| `backend` | Python 3.11 + Django/Gunicorn | 8000 | Serveur applicatif principal |
| `db` | PostgreSQL 15 | 5432 | Base de données |
| `redis` | Redis 7 | 6379 | Broker Celery + cache |
| `celery` | Python 3.11 + Celery worker | — | Tâches asynchrones (flatten, OCR, LLM) |
| `celery-beat` | Python 3.11 + Celery Beat | — | Planificateur tâches périodiques |
| `nginx` | Nginx 1.25 | 80, 443 | Reverse proxy, TLS, serving static/media |

### Configurations Docker Compose

**`docker-compose.yml`** (développement) :
- Ports mappés en local (backend:8088, db:5435, redis:6385, frontend:5173)
- `DEBUG=True`, hot reload activé (volumes montés)
- Pas de TLS, CORS permissif

**`infra/docker/docker-compose.prod.yml`** (production) :
- `DEBUG=False` — vérifié au démarrage, crash si `True`
- HTTPS et HSTS configurés via Nginx
- CORS strict (origine unique `korrigo.labomaths.tn`)
- Session cookies `Secure + HttpOnly`
- JSON structured logging
- Gunicorn 3 workers, timeout 120s
- Variable `OPENAI_MODEL=gpt-4.1-mini-2025-04-14`

---

## 11. Workflows GitHub Actions

Cinq workflows CI/CD dans `.github/workflows/` :

| Fichier | Déclencheur | Rôle |
|---------|-------------|------|
| `ci.yml` | Push/PR sur `main` | CI principal : tests + lint + build |
| `korrigo-ci.yml` | Push/PR | CI Korrigo spécifique (variante) |
| `tests-optimized.yml` | Push | Matrice de tests optimisée (parallélisation) |
| `deploy.yml` | Tag ou dispatch manuel | Déploiement automatisé vers production |
| `release-gate.yml` | Push tag `v*` | Gate de publication : zéro tolérance (pytest 100%, E2E 3/3, validation seed) |

Le `release-gate.yml` bloque tout déploiement si :
- au moins un test pytest échoue
- au moins un test E2E (Playwright) échoue
- la validation des données seed échoue

---

## 12. Patterns Architecturaux Clés

### Service Layer Pattern

La logique métier est concentrée dans des classes de service (`GradingService`, `AnnotationService`) indépendantes des views. Avantages :
- Tests unitaires sans HTTP
- Réutilisation entre plusieurs ViewSets
- Transactions atomiques centralisées

### Audit Trail (GradingEvent)

Chaque action significative génère un `GradingEvent` immutable :

```python
GradingEvent.objects.create(
    copy=copy,
    action=GradingEvent.Action.FINALIZE,
    actor=user,
    metadata={'final_score': score}
)
```

Actions tracées : `IMPORT`, `VALIDATE`, `LOCK`, `UNLOCK`, `CREATE_ANN`, `UPDATE_ANN`, `DELETE_ANN`, `FINALIZE`, `EXPORT`, `REOPEN`, `SAVE_APPREC`.

### Draft Auto-Save (DraftState)

`DraftState` persiste l'état complet de l'éditeur (annotations en cours, texte non sauvegardé, position de scroll) toutes les N secondes côté frontend. Prévient la perte de données en cas de crash navigateur ou de déconnexion réseau. Contrainte : 1 seul DraftState par (copy, user).

### Verrouillage Optimiste (Annotation.version)

Le champ `version` de `Annotation` est incrémenté atomiquement à chaque mise à jour via `F('version') + 1`. Le client envoie la `version` courante dans sa requête PUT. Si la version en base a déjà été incrémentée par une autre requête concurrente, le service lève une erreur de conflit. Référence ADR-P0-DI-008.

### Verrou transitoire (`CopyLock`)

`CopyLock` reste présent comme mécanisme auxiliaire de coordination et de nettoyage des verrous expirés. Il ne constitue plus le centre de la machine à états métier.

---

## 13. Flux de Données Métier

### Flux complet de correction (mode BATCH_A3)

```
Admin : Upload PDF A3 (50 MB max)
  └→ processing/PDFSplitter : découpe en N fascicules (Booklets)
       └→ HeaderDetector : extrait image en-tête (crop Pillow/OpenCV)
            └→ OCR Pipeline : GPT-4o-mini Vision → texte détecté
                 └→ matching flou sur Student → OCRResult.suggested_students
                      └→ Opérateur : valide/corrige identification → Copy.student = Student
                           └→ Admin : dispatch copies aux correcteurs (assign_corrector)

Correcteur : ouvre la copie
  └→ 1ère annotation → Copy.status READY → IN_PROGRESS (automatique)
       └→ Annotations VRAI/FAUX/COMMENT/ERROR + scores par question
            └→ Appréciation globale (Copy.global_appreciation)
                 └→ POST /finalize/ → verrou DB + transition atomique
                      └→ PDFFlattener : fusion PDF + annotations → final_pdf
                           └→ Copy.status → FINALIZED, graded_at = now()
                                └→ GradingEvent.FINALIZE
                                     └→ Celery : génération bilan LLM (Copy.llm_summary)

Admin : results_released_at = now() → portail élève activé
  └→ Élève : s'authentifie (email + date naissance)
       └→ Consulte copie finalisée + bilan LLM
```

### Communication Frontend ↔ Backend

```
Composant Vue
  └→ dispatch action Pinia store
       └→ Axios (cookie session inclus automatiquement)
            └→ DRF ViewSet
                 └→ Serializer (validation)
                      └→ Service Layer (logique métier)
                           └→ Django ORM → PostgreSQL
                                └→ JSON response
                                     └→ Store mise à jour → réactivité Vue
```

---

## 14. Justifications Techniques

### Pourquoi Django (pas FastAPI) ?

- ORM puissant pour les relations complexes (Exam → Booklet → Copy → Annotation)
- Admin Django intégré — indispensable pour la gestion des examens, correcteurs, copies
- Écosystème mature : DRF, Celery, django-ratelimit, django-csp
- Migrations versionnées avec support des fonctions Python (migrations 0026, 0027)
- Transactions atomiques natives avec `@transaction.atomic`

### Pourquoi Vue.js 3 (Composition API) ?

- Composition API : logique réutilisable par composable, meilleure organisation que Options API
- Réactivité fine : annotations en temps quasi-réel sur le canvas PDF.js
- Pinia : state management sans boilerplate (remplace Vuex)
- Vite 5 : HMR quasi-instantané en développement, build optimisé (tree-shaking)

### Pourquoi PostgreSQL (pas SQLite) ?

- ACID strict : critique pour les transactions de finalisation et les contraintes d'intégrité
- `UPDATE ... WHERE` atomique : fondation de la transition de finalisation
- `select_for_update()` : verrouillage pessimiste au niveau ligne
- Support natif `JSONField` : barème (`grading_structure`), metadata des événements
- Index composites performants sur les patterns de requête fréquents

### Pourquoi Session Cookie (pas JWT) ?

- Révocation immédiate côté serveur (logout réel)
- Cookie `HttpOnly` : inaccessible au JS, protège contre XSS
- Gestion CSRF native Django
- Pas de gestion de token côté client (moins de surface d'attaque)
- Adapté à une application mono-domaine (pas besoin de tokens cross-domain)

### Pourquoi Celery + Redis (pas synchrone) ?

- `flatten_copy` (génération PDF avec PyMuPDF) peut prendre 2 à 10 secondes selon la taille
- OCR GPT-4o-mini : latence réseau variable (1 à 5 secondes)
- Bilans LLM Ollama : de 10 secondes à plusieurs minutes selon le modèle
- Le traitement asynchrone libère les workers Gunicorn pour servir d'autres requêtes

---

## Références

- [DATABASE_SCHEMA.md](DATABASE_SCHEMA.md) — Schéma base de données complet
- [API_REFERENCE.md](API_REFERENCE.md) — Référence API REST
- [BUSINESS_WORKFLOWS.md](BUSINESS_WORKFLOWS.md) — Workflows métier détaillés
- [FRONTEND_ARCHITECTURE.md](FRONTEND_ARCHITECTURE.md) — Architecture frontend Vue.js
- [ADR-002 : Normalisation Coordonnées PDF](../decisions/ADR-002-pdf-coordinate-normalization.md)
- [ADR-003 : Machine à États Copy](../decisions/ADR-003-copy-status-state-machine.md)
- Code source : `backend/grading/services.py`, `backend/exams/models.py`

---

**Dernière mise à jour** : 28 mars 2026
**Auteur** : Alaeddine BEN RHOUMA
**Licence** : Propriétaire — NEXUS RÉUSSITE
