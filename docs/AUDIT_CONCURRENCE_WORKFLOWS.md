# Audit de Sûreté Concurrente — Workflows de Correction Korrigo

> **Statut documentaire**
> Audit historique daté. Ce document conserve le raisonnement d’audit au moment de sa rédaction.
> Il peut mentionner des statuts et transitions antérieurs qui ne correspondent plus exactement au modèle actif courant.

**Date** : 7 mars 2026  
**Auditeur** : Cascade (AI)  
**Périmètre** : Toutes les écritures concurrentes sur données critiques (scores, annotations, remarques, appréciations, transitions d'état, drafts, locks, audit trail)  
**Base de code** : Post-corrections LOT 8 (permissions, guards, ownership checks)

---

## 1. Inventaire des zones de concurrence

### 1.1 Fonctions/vues/services qui écrivent dans les données critiques

| Cible | Fonction/Vue | Fichier | Type d'écriture |
|---|---|---|---|
| **Score** | `CopyScoresView.put` | `grading/views.py:487` | `update_or_create` sur `Score` |
| **Score** (finalize) | `GradingService.compute_score` | `grading/services.py:182` | Lecture seule (utilisé par finalize) |
| **Annotation** | `AnnotationService.add_annotation` | `grading/services.py:73` | `Annotation.objects.create` |
| **Annotation** | `AnnotationService.update_annotation` | `grading/services.py:106` | `annotation.save()` avec `F('version') + 1` |
| **Annotation** | `AnnotationService.delete_annotation` | `grading/services.py:154` | `annotation.delete()` |
| **Remarque** | `QuestionRemarkListCreateView.create` | `grading/views.py:347` | `update_or_create` sur `QuestionRemark` |
| **Remarque** | `QuestionRemarkDetailView.update` | `grading/views.py:384` | `serializer.save()` |
| **Remarque** | `QuestionRemarkDetailView.destroy` | `grading/views.py:401` | `remark_obj.delete()` |
| **Appréciation** | `CopyGlobalAppreciationView._update` | `grading/views.py:435` | `copy.save(update_fields=['global_appreciation'])` |
| **Draft** | `DraftReturnView.put` | `grading/views_draft.py:64` | `get_or_create` + `filter().update()` |
| **Copy.status** | `GradingService.validate_copy` | `grading/services.py:295` | `copy.save()` (STAGING→READY) |
| **Copy.status** | `GradingService._finalize_copy_inner` | `grading/services.py:338` | `select_for_update` + transitions multiples |
| **Copy.status** | `CopyReadyView.post` | `grading/views.py:157` | Appelle `GradingService.ready_copy` |
| **Copy.status** | `CopyFinalizeView.post` | `grading/views.py:175` | Appelle `GradingService.finalize_copy` |
| **Copy.status** (async) | `async_finalize_copy` | `grading/tasks.py:21` | Appelle `GradingService.finalize_copy` |
| **Exam.results_released_at** | `ExamReleaseResultsView.post` | `grading/views.py:742` | `exam.save(update_fields=...)` |
| **Exam.results_released_at** | `ExamUnreleaseResultsView.post` | `grading/views.py:774` | `exam.save(update_fields=...)` |
| **CopyLock** | `GradingService.acquire_lock` | `grading/services.py:427` | `select_for_update` + create/update |
| **CopyLock** | `GradingService.release_lock` | `grading/services.py:486` | `select_for_update` + delete |
| **CopyLock** | `GradingService.heartbeat_lock` | `grading/services.py:519` | `select_for_update` + update |
| **CopyLock** (cleanup) | `cleanup_expired_locks` | `grading/tasks.py:213` | Bulk `delete()` |
| **Copy.llm_summary** | `CopyLLMSummaryView.post` / `ExamLLMSummaryView.post` | `grading/views.py:820/789` | Écrit via `LLMSummaryService` |
| **UserAnnotation** | `AutoSaveAnnotationView.post` | `grading/views_annotation_bank.py:155` | `F('usage_count') + 1` ou `create` |
| **GradingEvent** | Toutes les opérations ci-dessus | Multiples | `GradingEvent.objects.create` / `get_or_create` |

### 1.2 Objets pouvant être touchés simultanément

| Objet | Scénario concurrent réaliste |
|---|---|
| **Score (même copie)** | Un correcteur ouvre 2 onglets, sauvegarde des notes quasi-simultanément |
| **Score (même copie)** | Frontend autosave vs. save manuel explicite |
| **Annotation (même copie)** | Correcteur crée/modifie 2 annotations en rafale (requêtes parallèles du frontend) |
| **Copy.status** | Double-clic "Finaliser" → 2 POST `/copies/<id>/finalize/` en ~100ms |
| **Copy.status** | Admin finalise via UI pendant que Celery `async_finalize_copy` tourne |
| **CopyLock** | 2 correcteurs tentent d'acquérir le lock sur la même copie (dispatch error) |
| **Draft** | Autosave toutes les 5s + save manuel au même instant |
| **Exam.results_released_at** | 2 admins cliquent "Publier" simultanément (bénin) |
| **Remarque (même question)** | Correcteur édite la même remarque dans 2 onglets |

### 1.3 Scénarios réalistes en production Korrigo

**Scénario A — Double-clic finalisation** : Le correcteur clique 2 fois sur "Finaliser". Le frontend envoie 2 POST en ~100ms. Les deux entrent dans `_finalize_copy_inner`.

**Scénario B — Autosave concurrent scores** : Le frontend envoie un PUT scores toutes les N secondes. L'utilisateur clique aussi "Sauvegarder" manuellement. Deux PUT arrivent en ~200ms.

**Scénario C — Celery + HTTP finalize** : L'admin lance une finalisation async, puis re-clique avant la fin du task. Le task Celery et le HTTP direct entrent tous deux dans `finalize_copy`.

**Scénario D — 2 onglets draft autosave** : Le correcteur ouvre la même copie dans 2 onglets. Les 2 onglets font du PUT draft toutes les 5s avec des `client_id` différents.

**Scénario E — Lock expiration race** : Le lock expire pendant que le correcteur sauvegarde. Un autre correcteur acquiert le lock. Le premier correcteur finit sa sauvegarde (le lock n'est PAS vérifié sur les écritures d'annotation/score).

---

## 2. Vérification de `CopyScoresView.put`

### 2.1 Code actuel (`grading/views.py:544-556`)

```python
# LOT 4 fix: select_for_update to prevent lost updates on concurrent PUT
from django.db import transaction
with transaction.atomic():
    # Lock the Copy row to serialize concurrent score writes
    Copy.objects.select_for_update().filter(id=copy.id).first()

    score, created = Score.objects.update_or_create(
        copy=copy,
        defaults={
            'scores_data': scores_data,
            'final_comment': final_comment,
        }
    )
```

### 2.2 Analyse critique

**Ce qui est correct :**
- `select_for_update` sur `Copy` sérialise les écritures concurrentes sur le même `copy_id`
- `update_or_create` garantit un seul `Score` par copie (renforcé par `UniqueConstraint`)
- Le tout est dans `transaction.atomic()`
- L'audit trail `GradingEvent` est créé dans le même bloc atomique

**Ce qui est problématique :**

#### PROBLÈME 2.2.1 — `select_for_update` sur mauvaise table (sévérité: MOYENNE)

Le `select_for_update` verrouille la ligne `Copy`, pas la ligne `Score`. C'est intentionnel — ça sérialise par copie. Mais le problème est que **la validation des scores** (lignes 502-542) se fait **AVANT** le bloc `transaction.atomic()` :

```python
# Lignes 502-542: validation sans lock
scores_data = request.data.get('scores_data', {})
# ... validation barème max ...

# Ligne 546: SEULEMENT ICI on prend le lock
with transaction.atomic():
    Copy.objects.select_for_update().filter(id=copy.id).first()
    score, created = Score.objects.update_or_create(...)
```

**Conséquence sous PostgreSQL réel** : Si T1 et T2 arrivent en même temps avec des scores différents :
1. T1 valide `scores_data = {q1: 5.0}` → OK
2. T2 valide `scores_data = {q1: 3.0}` → OK
3. T1 entre dans `atomic`, prend le lock, écrit `{q1: 5.0}`
4. T2 attend le lock, puis écrit `{q1: 3.0}`

**Résultat** : Last Write Wins. Le correcteur voit `{q1: 5.0}` dans son UI mais la DB a `{q1: 3.0}`. **C'est un lost update silencieux**. Le `select_for_update` empêche la corruption de la ligne Score (pas de merge partiel), mais il ne protège PAS contre l'écrasement d'un save plus récent par un save plus ancien.

**Atténuation réelle** : Le `assigned_corrector` ownership check limite le problème à un seul utilisateur (2 onglets). Le correcteur ne verrait de toute façon que SES PROPRES données, et le frontend recharge après save. En production Korrigo (4-8 correcteurs, chacun sur ses copies), le risque de collision réelle est **très faible**.

#### PROBLÈME 2.2.2 — Pas de versioning sur Score (sévérité: FAIBLE)

Contrairement à `Annotation` qui a un champ `version` avec optimistic locking, `Score` n'a PAS de champ version. Il est impossible de détecter un concurrent write au niveau applicatif. C'est un "Last Write Wins" pur.

#### PROBLÈME 2.2.3 — Copy lue hors transaction (sévérité: FAIBLE)

```python
copy = get_object_or_404(Copy, id=copy_id)  # Ligne 488: hors atomic
# ... validation ...
with transaction.atomic():
    Copy.objects.select_for_update().filter(id=copy.id).first()  # Re-lock
```

Le `copy.status` est lu en ligne 494 (`if copy.status == Copy.Status.GRADED`) **HORS du bloc atomique**. Une transition READY→GRADED entre les deux lectures ne serait pas détectée. Toutefois, `select_for_update` sur la Copy empêche les transitions concurrentes pendant l'écriture du score.

### 2.3 Comportement sous PostgreSQL réel

- `select_for_update` émet un `SELECT ... FOR UPDATE` qui prend un row-level exclusive lock
- T2 attend que T1 libère le lock (commit/rollback du `transaction.atomic()`)
- **Pas de deadlock possible** : un seul objet locké (Copy), pas de lock croisé
- **Durée du lock** : ~10ms (validation + update_or_create + GradingEvent create) → acceptable
- **Isolation level** : PostgreSQL default `READ COMMITTED` → T2 voit le commit de T1 après l'attente

### 2.4 Cas non couverts

| Cas | Protégé ? | Détail |
|---|---|---|
| 2 PUT simultanés même copie même user | ✅ Sérialisé | `select_for_update` → second attend |
| Lost update silencieux (2 onglets) | ❌ Non détecté | Pas de version sur Score |
| Score écrit sur copie GRADED pendant finalize | ⚠️ Partiel | Le `if copy.status == GRADED` est hors atomic |
| Merge partiel de scores_data | ✅ Impossible | `update_or_create` remplace tout `scores_data` |

### 2.5 Verdict `CopyScoresView.put`

**Sécurité partielle**. La sérialisation est correcte (pas de corruption de données), mais le lost update silencieux entre 2 onglets n'est pas détecté. C'est un risque **faible en production Korrigo** (mono-utilisateur par copie, ownership enforced) mais **réel en théorie**.

---

## 3. Vérification de `DraftState` / autosave

### 3.1 Mécanisme actuel (`grading/views_draft.py`)

```python
# Étape 1: Vérification client_id sur le draft existant (hors atomic)
existing_draft = DraftState.objects.get(copy=copy, owner=request.user)
if existing_draft.client_id and str(existing_draft.client_id) != str(client_id):
    return Response(status=409)  # CONFLICT

# Étape 2: get_or_create
draft, created = DraftState.objects.get_or_create(
    copy=copy, owner=request.user,
    defaults={"payload": payload, "client_id": client_id, "version": 1}
)

# Étape 3: conditional update avec F()
if not created:
    updated_count = DraftState.objects.filter(
        id=draft.id, client_id=draft.client_id
    ).update(payload=payload, version=F('version') + 1)
    if updated_count == 0:
        return Response(status=409)  # CONFLICT
```

### 3.2 Protections existantes

- **`unique_together = ['copy', 'owner']`** : Un seul draft par utilisateur par copie (contrainte DB)
- **`client_id`** : Anti-écrasement entre sessions (si 2 onglets ont des client_id différents → 409)
- **`F('version') + 1`** : Version atomique via SQL (pas de read-modify-write)
- **`filter(client_id=draft.client_id).update()`** : Conditional update — si le client_id a changé entre le get et le update, `updated_count = 0` → 409

### 3.3 Analyse des scénarios concurrents

#### Scénario 3.3.1 — Même onglet, 2 saves rapides (même client_id)

1. T1: `filter(id=X, client_id=ABC).update(payload=P1, version=F+1)` → `updated_count=1` ✅
2. T2: `filter(id=X, client_id=ABC).update(payload=P2, version=F+1)` → `updated_count=1` ✅

**Résultat** : Last Write Wins. Les deux passent car le `client_id` n'a pas changé. C'est le comportement souhaité pour un autosave.

#### Scénario 3.3.2 — 2 onglets différents (client_id différents)

1. Onglet A (client_id=AAA) fait un PUT. Draft existant a client_id=BBB (de l'onglet B).
2. Ligne 87: `str(existing_draft.client_id) != str(client_id)` → `True` → 409 CONFLICT ✅

**Protection correcte.** L'onglet A est rejeté.

#### Scénario 3.3.3 — Race condition sur le premier PUT (aucun draft existant)

1. T1 et T2 arrivent quasi-simultanément, aucun draft n'existe encore.
2. T1: `get_or_create` → crée le draft (created=True), retourne
3. T2: `get_or_create` → le draft existe déjà (created=False), tombe dans le `if not created` branch
4. T2: `filter(id=draft.id, client_id=draft.client_id).update(...)` → passe si même client_id, ou `updated_count=0` si différent

**Pas de race dangereuse** : `get_or_create` utilise `unique_together` sous le capot. Si les deux tentent de créer simultanément, un seul réussit grâce à la contrainte DB, l'autre obtient le `get`.

### 3.4 Problème résiduel — TOCTOU sur le check client_id

```python
# Lignes 86-93: check HORS de toute transaction atomique
existing_draft = DraftState.objects.get(copy=copy, owner=request.user)
if existing_draft.client_id and str(existing_draft.client_id) != str(client_id):
    return Response(status=409)
```

Ce check est une lecture simple. Entre cette lecture et le `get_or_create` (ligne 95), le draft pourrait être modifié par une autre requête. Mais le `filter(client_id=draft.client_id).update()` (ligne 106) rattrape ce TOCTOU en faisant un conditional update atomique.

**Faille théorique** : Si un onglet A change le `client_id` du draft entre les lignes 86 et 95, le `get_or_create` retournera le draft avec le nouveau `client_id`, et le `filter(client_id=draft.client_id)` utilisera l'ancien. Résultat : `updated_count=0` → 409. **C'est safe** — on rejette en cas de doute.

### 3.5 Verdict DraftState / autosave

**Sécurité correcte.** Le mécanisme `client_id` + `conditional update` + `F('version')` est robuste. Le TOCTOU est rattrapé par le conditional update. Le seul risque est un 409 "faux positif" en cas de race extrême, ce qui est le comportement sûr (fail-closed). **Pas de perte de données possible.**

---

## 4. Vérification annotations / remarques / appréciations

### 4.1 Annotations

#### Protections existantes

- **Optimistic locking** (`Annotation.version`) : `update_annotation` vérifie `expected_version` vs `annotation.version`, et incrémente avec `F('version') + 1`
- **`@transaction.atomic`** sur `add_annotation`, `update_annotation`, `delete_annotation`
- **Status guard** : toutes les opérations vérifient `copy.status == READY`
- **Ownership** : `_can_write_copy` dans la vue, pas dans le service

#### Problème 4.1.1 — Optimistic locking est OPTIONNEL (sévérité: MOYENNE)

```python
expected_version = payload.get('version', None)
if expected_version is not None:
    if int(expected_version) != annotation.version:
        raise ValueError("Version mismatch...")
```

Le check `if expected_version is not None` signifie que **si le frontend n'envoie pas `version` dans le payload, le check est bypassed**. C'est du "best effort" optimistic locking. Si le frontend n'implémente pas le versioning, on revient à un Last Write Wins pur.

**Vérification nécessaire** : Le frontend CorrectorDesk envoie-t-il le champ `version` lors des PATCH d'annotation ? Si non, le mécanisme est inopérant.

#### Problème 4.1.2 — TOCTOU sur status check (sévérité: FAIBLE)

```python
if annotation.copy.status != Copy.Status.READY:
    raise ValueError(...)
```

Le status est lu via `annotation.copy.status` qui est chargé par `select_related("copy")` au début. Si un autre thread finalise la copie entre ce check et le `annotation.save()`, l'annotation sera modifiée sur une copie GRADED. Toutefois :
- Le `@transaction.atomic` ne prend pas de lock sur la Copy
- Le `finalize_copy` prend un `select_for_update` sur la Copy, mais les annotations ne lockent pas la Copy

**Atténuation** : En pratique, la finalisation est déclenchée manuellement par le correcteur qui a fini d'annoter. Le risque de course entre "encore en train d'annoter" et "click finaliser" est un bug d'UX, pas de concurrence serveur.

### 4.2 Remarques (QuestionRemark)

#### Protections existantes

- **`unique_together = ['copy', 'question_id']`** : Une seule remarque par question par copie
- **`update_or_create`** dans `QuestionRemarkListCreateView.create` : Pas de duplication possible
- **Ownership** : `_can_write_copy` dans la vue

#### Problème 4.2.1 — Pas de versioning ni de lock (sévérité: FAIBLE)

`QuestionRemark` n'a ni champ `version` ni `select_for_update`. Deux saves simultanés sur la même remarque → Last Write Wins pur. Mais le scénario est quasi-impossible : le correcteur édite UNE remarque à la fois.

#### Problème 4.2.2 — `QuestionRemarkDetailView.update` n'est PAS atomique

```python
def update(self, request, *args, **kwargs):
    remark_obj = self.get_object()
    if not _can_write_copy(request.user, remark_obj.copy):
        return 403
    serializer = self.get_serializer(remark_obj, data=request.data, partial=partial)
    serializer.is_valid(raise_exception=True)
    serializer.save()  # Pas de transaction.atomic ici
```

Le `serializer.save()` fait un simple `remark_obj.save()`. Pas de `transaction.atomic` explicite (Django wrappe chaque requête dans sa propre transaction par défaut avec `ATOMIC_REQUESTS=False`). Sous PostgreSQL, chaque `save()` est sa propre mini-transaction, donc pas de risque de corruption partielle. Mais un concurrent update pourrait écraser silencieusement.

### 4.3 Appréciations (global_appreciation)

#### Protections existantes

```python
def _update(self, request, copy_id):
    copy = get_object_or_404(Copy, id=copy_id)
    if not _can_write_copy(request.user, copy):
        return 403
    copy.global_appreciation = global_appreciation
    copy.save(update_fields=['global_appreciation'])
```

#### Problème 4.3.1 — Aucune protection concurrente (sévérité: FAIBLE)

- Pas de `transaction.atomic`
- Pas de `select_for_update`
- Pas de versioning
- `save(update_fields=['global_appreciation'])` ne touche que ce champ → pas de corruption croisée avec d'autres champs de Copy

**Atténuation** : L'appréciation est un texte libre, édité par un seul correcteur sur sa copie. Le risque de concurrence est négligeable en production.

### 4.4 Verdict annotations / remarques / appréciations

| Objet | Protection | Risque résiduel |
|---|---|---|
| **Annotation** | Optimistic locking (optionnel), `@transaction.atomic` | MOYEN si frontend n'envoie pas `version` |
| **QuestionRemark** | `update_or_create`, `unique_together` | FAIBLE — LWW sur update |
| **Appréciation** | `update_fields` | FAIBLE — mono-correcteur par copie |

**Aucune de ces opérations ne peut produire un état structurellement incohérent** (pas de merge partiel, pas de ligne orpheline). Le pire cas est un lost update silencieux, atténué par le modèle mono-correcteur.

---

## 5. Vérification des transitions d'état

### 5.1 `validate_copy` / `ready_copy` (STAGING → READY)

```python
@transaction.atomic
def validate_copy(copy: Copy, user):
    if copy.status != Copy.Status.STAGING:
        raise ValueError(f"Status mismatch: {copy.status} != STAGING")
    copy.status = Copy.Status.READY
    copy.validated_at = timezone.now()
    copy.save()
```

#### Analyse

- **`@transaction.atomic`** : ✅ Présent
- **`select_for_update`** : ❌ ABSENT
- **Risque double action** : Si 2 requêtes entrent simultanément pour la même copie STAGING, les deux lisent `status=STAGING`, passent le check, et les deux écrivent `status=READY`. Le deuxième `save()` est un no-op fonctionnel (READY→READY), mais il crée **2 GradingEvent VALIDATE** pour la même copie.

#### Sévérité : FAIBLE

La double validation produit un doublon d'audit trail. Pas de corruption de données. L'état final est correct (READY). En production, la validation est faite par un admin via le backoffice, pas susceptible de double-clic.

### 5.2 `finalize_copy` (READY → GRADING_IN_PROGRESS → GRADED)

```python
@transaction.atomic
def _finalize_copy_inner(copy: Copy, user, lock_token=None):
    copy = Copy.objects.select_for_update().get(id=copy.id)  # ROW LOCK

    if copy.status == Copy.Status.GRADED:
        raise LockConflictError("Copie déjà finalisée.")

    if copy.status not in [Copy.Status.READY, Copy.Status.GRADING_FAILED]:
        raise ValueError(...)

    copy.status = Copy.Status.GRADING_IN_PROGRESS
    copy.save(update_fields=["status", "grading_retries"])

    # ... PDF generation ...

    copy.status = Copy.Status.GRADED
    copy.save(update_fields=["status", "graded_at", ...])

    GradingEvent.objects.get_or_create(
        copy=copy, action=GradingEvent.Action.FINALIZE, actor=user, ...)
```

#### Analyse

- **`select_for_update`** : ✅ Correctement placé — verrouille la ligne Copy AVANT le check de status
- **Double finalize** : T2 attend le lock, puis voit `GRADED` → `LockConflictError` ✅
- **`get_or_create` sur GradingEvent** : Protection idempotente — un seul event FINALIZE par copie/actor ✅
- **Transition intermédiaire `GRADING_IN_PROGRESS`** : Empêche les reads concurrents de voir la copie comme "READY" pendant la génération PDF ✅
- **Fallback `GRADING_FAILED`** : Si le PDF échoue, le status passe à GRADING_FAILED avec retry counter ✅
- **Top-level `OperationalError` catch** : Attrape les contention DB hors du `@transaction.atomic` ✅

#### Problème 5.2.1 — Long lock pendant la génération PDF (sévérité: MOYENNE)

Le `select_for_update` est pris au début de `_finalize_copy_inner`, et le `@transaction.atomic` ne se termine qu'après la génération du PDF (`PDFFlattener.flatten_copy`). Sur le serveur (12 cores, 62GB), cette opération prend **~2-30 secondes** selon le nombre de pages.

**Pendant ce temps, la ligne Copy est verrouillée.** Toute requête qui tente un `select_for_update` sur cette même Copy (score save, autre finalize) sera bloquée.

**Impact réel** : Les `CopyScoresView.put` font aussi un `select_for_update` sur la même Copy. Si un PUT scores arrive pendant la finalisation, il sera bloqué pendant 2-30 secondes. Le frontend pourrait afficher un timeout ou un spinner long.

**Atténuation** : `async_finalize_copy` (Celery) isole ce long lock du thread HTTP. Si la finalisation passe par Celery, le HTTP est libéré immédiatement. Mais si le correcteur utilise le path synchrone (HTTP direct), le lock est long.

#### Problème 5.2.2 — `if not copy.final_pdf` idempotency check (sévérité: FAIBLE)

```python
if not copy.final_pdf:
    pdf_bytes = flattener.flatten_copy(copy)
    copy.final_pdf.save(output_filename, ContentFile(pdf_bytes), save=False)
```

Ce check évite de re-générer le PDF si `final_pdf` est déjà rempli. Mais dans le flow normal, `final_pdf` est vide à ce stade (la copie vient de passer de READY à GRADING_IN_PROGRESS). Le check est un safety net pour les retries sur `GRADING_FAILED`.

### 5.3 `ExamReleaseResultsView` / `ExamUnreleaseResultsView`

```python
def post(self, request, exam_id):
    exam = get_object_or_404(Exam, id=exam_id)
    if exam.results_released_at:
        return Response({'message': 'Résultats déjà publiés.'})
    exam.results_released_at = timezone.now()
    exam.save(update_fields=['results_released_at'])
```

#### Analyse

- **Pas de `transaction.atomic`** : ❌
- **Pas de `select_for_update`** : ❌
- **Risque double action** : 2 admins cliquent "Publier" → les deux lisent `results_released_at=None`, les deux écrivent. Le premier a un timestamp légèrement antérieur, le second écrase avec un timestamp légèrement postérieur.

#### Sévérité : NÉGLIGEABLE

L'état final est correct (results_released_at est non-null). Le seul effet est un timestamp décalé de quelques ms. Pas de doublon d'audit trail (aucun GradingEvent n'est créé pour release). Pas d'impact fonctionnel.

### 5.4 Tâches async qui interagissent avec les transitions

#### `async_finalize_copy` (Celery task)

```python
@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def async_finalize_copy(self, copy_id, user_id, lock_token=None, request_id=None):
    copy = Copy.objects.get(id=copy_id)
    user = User.objects.get(id=user_id)
    finalized_copy = GradingService.finalize_copy(copy, user, lock_token=lock_token)
```

**Protection** : Délègue à `GradingService.finalize_copy` qui utilise `select_for_update`. La protection est identique au path synchrone. ✅

**Risque de double task** : Si le frontend envoie 2 fois le request, 2 tasks Celery sont créées. La première réussit (READY→GRADED), la seconde échoue (`LockConflictError: Copie déjà finalisée`). ✅ Correct.

**Risque de retry sur task déjà réussie** : Si la task réussit mais le ack Celery échoue (worker crash entre `return` et ack), Celery re-exécute la task. `GradingService.finalize_copy` détecte `status==GRADED` et lève `LockConflictError`. Le task handler catch ça comme `(ValueError, LockConflictError)` → retourne `{'status': 'error'}` au lieu de retry. ✅ Correct.

#### `cleanup_expired_locks`

```python
expired = CopyLock.objects.filter(expires_at__lte=now)
expired.delete()
```

**Pas de `select_for_update`** : Ce bulk delete pourrait supprimer un lock qui vient d'être renouvelé par un heartbeat dans les dernières ms. Mais le `heartbeat_lock` utilise `select_for_update`, donc le heartbeat bloquera le cleanup (ou vice versa) grâce au row-level lock implicite du DELETE.

**PostgreSQL behavior** : Le `DELETE` prend un row-level lock (FOR UPDATE implicitly). Si `heartbeat_lock` fait un `select_for_update` sur la même ligne au même moment, l'un attend l'autre. Pas de race. ✅

### 5.5 Résumé transitions

| Transition | `select_for_update` | `@transaction.atomic` | Risque double action | Risque état incohérent |
|---|---|---|---|---|
| STAGING→READY | ❌ | ✅ | Doublon audit trail | ❌ Non |
| READY→GRADING_IN_PROGRESS→GRADED | ✅ | ✅ | ❌ Non (LockConflictError) | ❌ Non |
| GRADING_FAILED→retry | ✅ | ✅ | ❌ Non | ❌ Non |
| Release results | ❌ | ❌ | Timestamp écrasé (bénin) | ❌ Non |

---

## 6. Vérification des mécanismes de lock

### 6.1 `CopyLock` model

```python
class CopyLock(models.Model):
    copy = models.OneToOneField(Copy, ...)   # Un seul lock par copie
    owner = models.ForeignKey(User, ...)
    token = models.UUIDField(default=uuid.uuid4)
    expires_at = models.DateTimeField(db_index=True)
    
    constraints = [
        UniqueConstraint(fields=["copy"], name="uniq_copylock_copy"),
    ]
```

**`OneToOneField` + `UniqueConstraint`** : Double protection. Impossible d'avoir 2 locks sur la même copie au niveau DB. ✅

### 6.2 `acquire_lock`

```python
@transaction.atomic
def acquire_lock(copy, user, ttl_seconds=1800):
    try:
        existing = CopyLock.objects.select_for_update().get(copy=copy)
    except CopyLock.DoesNotExist:
        existing = None
    
    if existing is not None:
        if existing.expires_at > now and existing.owner != user:
            raise LockConflictError(...)  # Locked by another user
        if existing.owner == user:
            existing.expires_at = expires_at  # Renew
            existing.save(...)
            return existing, False
        else:
            # Expired lock by another user: take over
            existing.owner = user
            existing.token = uuid.uuid4()
            existing.save(...)
            return existing, False

    lock = CopyLock.objects.create(copy=copy, owner=user, expires_at=expires_at)
    return lock, True
```

#### Analyse

- **`select_for_update`** sur le lock existant : ✅ Empêche 2 users de "takeover" un lock expiré simultanément
- **`@transaction.atomic`** : ✅ Le create et le select_for_update sont dans la même transaction
- **Race on create** : Si 2 users arrivent quand aucun lock n'existe, les deux passent `existing=None`, les deux tentent `CopyLock.objects.create()`. La `UniqueConstraint` fait que le second lève `IntegrityError`.

**PROBLÈME 6.2.1 — IntegrityError non catchée (sévérité: MOYENNE)**

Si deux users tentent d'acquérir un lock inexistant au même instant :
1. T1: `select_for_update().get()` → `DoesNotExist` → `existing = None`
2. T2: `select_for_update().get()` → `DoesNotExist` → `existing = None`
3. T1: `CopyLock.objects.create(copy=copy, ...)` → ✅ Succès
4. T2: `CopyLock.objects.create(copy=copy, ...)` → ❌ `IntegrityError`

Le `IntegrityError` n'est pas catchée dans `acquire_lock`. Il remonte comme une exception non gérée. La vue `LockAcquireView` a un `except Exception` générique qui retourne 500.

**Fix potentiel** : Catch `IntegrityError` dans `acquire_lock` et le traduire en `LockConflictError`.

**Atténuation** : En production, l'`assigned_corrector` ownership empêche 2 correcteurs de travailler sur la même copie. Le seul cas serait un admin et un correcteur qui lockent au même instant, ce qui est extrêmement rare.

### 6.3 `release_lock` et `heartbeat_lock`

Les deux utilisent `select_for_update` sur le `CopyLock` et vérifient le `token`. ✅ Correct.

### 6.4 Cohérence `CopyLock` ↔ `Copy.Status.LOCKED`

**PROBLÈME MAJEUR 6.4.1 — `CopyLock` et `Copy.status` sont découplés (sévérité: HAUTE)**

Le modèle `Copy` a un status `LOCKED`, mais **aucune partie du code ne change `Copy.status` vers `LOCKED` lors de l'acquisition d'un lock**. Inversement, **aucune partie du code ne vérifie `Copy.status == LOCKED` avant d'autoriser les écritures**.

Preuve :
- `acquire_lock` crée un `CopyLock` mais ne fait PAS `copy.status = Copy.Status.LOCKED; copy.save()`
- `release_lock` supprime le `CopyLock` mais ne fait PAS `copy.status = Copy.Status.READY; copy.save()`
- `AnnotationService.add_annotation` vérifie `copy.status == READY`, pas `LOCKED`
- `CopyScoresView.put` ne vérifie PAS si un lock existe

**Conséquence** : Le `CopyLock` est un **soft lock applicatif** purement consultatif. Il est vérifié par le frontend (qui affiche un message "copie verrouillée par X") mais **pas enforced côté serveur** sur les écritures d'annotations, scores, remarques ou appréciations.

Un correcteur B pourrait théoriquement :
1. Ne pas vérifier le lock status
2. Envoyer des PUT scores directement via API (curl/script)
3. Écrire dans une copie lockée par le correcteur A

**Atténuation réelle** :
- Le `_can_write_copy` ownership check empêche B d'écrire sur une copie assignée à A
- Le frontend vérifie le lock et bloque l'UI
- Seul un admin pourrait bypasser les deux

**Ce n'est PAS un bug de concurrence au sens strict** — c'est une architecture "advisory lock" documentée. Mais le status `LOCKED` dans `Copy.Status` est trompeur car il n'est jamais écrit automatiquement.

### 6.5 `Copy.locked_at` et `Copy.locked_by` jamais écrits

Les champs `Copy.locked_at` et `Copy.locked_by` existent dans le modèle mais **aucun code ne les écrit**. Seul `CopyLock.locked_at` (auto_now_add) et `CopyLock.owner` sont utilisés. Les champs sur Copy sont des vestiges inutilisés.

### 6.6 `get_lock_status` — cleanup sans lock

```python
def get_lock_status(copy):
    lock = CopyLock.objects.select_related("owner").get(copy=copy)
    if lock.expires_at <= now:
        lock.delete()  # Cleanup sans select_for_update
        return None
```

Ce `delete()` est hors de toute `@transaction.atomic` et sans `select_for_update`. Si un heartbeat arrive au même moment :
- `get_lock_status` lit le lock, voit expiré, fait `delete()`
- `heartbeat_lock` fait `select_for_update`, trouve le lock, renouvelle → mais le lock vient d'être supprimé

**PostgreSQL** : Le `delete()` prend un implicit row-lock. Le `select_for_update` du heartbeat attendra. Si le delete finit d'abord, le heartbeat lèvera `DoesNotExist` → `LockConflictError("Lock not found")`. ✅ Safe — le heartbeat détecte correctement que le lock a été perdu.

### 6.7 Verdict locks

**Sécurité partielle.**
- L'acquisition/release/heartbeat sont correctement sérialisés via `select_for_update` ✅
- La contrainte `OneToOneField` empêche les doublons ✅
- **MAIS** le `CopyLock` n'est pas enforced côté serveur sur les écritures (advisory lock) ⚠️
- Le status `Copy.Status.LOCKED` n'est jamais écrit ⚠️
- Le `IntegrityError` sur double create simultané n'est pas catchée ⚠️

---

## 7. Audit trail

### 7.1 Mécanismes existants

| Opération | Événement | Mécanisme | Atomique avec l'écriture ? |
|---|---|---|---|
| Import PDF | `IMPORT` | `GradingEvent.objects.create` dans `@transaction.atomic` | ✅ Oui |
| Validate (STAGING→READY) | `VALIDATE` | `GradingEvent.objects.create` dans `@transaction.atomic` | ✅ Oui |
| Finalize (→GRADED) | `FINALIZE` | `get_or_create` dans `@transaction.atomic` | ✅ Oui, idempotent |
| Lock acquire | `LOCK` | `GradingEvent.objects.create` dans `@transaction.atomic` | ✅ Oui |
| Lock release | `UNLOCK` | `GradingEvent.objects.create` dans `@transaction.atomic` | ✅ Oui |
| Create annotation | `CREATE_ANN` | dans `@transaction.atomic` | ✅ Oui |
| Update annotation | `UPDATE_ANN` | dans `@transaction.atomic` | ✅ Oui |
| Delete annotation | `DELETE_ANN` | dans `@transaction.atomic` | ✅ Oui |
| Score save | `scores_saved` | dans `transaction.atomic()` | ✅ Oui |
| Remark save | `remark_saved` | `try/except` (fail-silent) | ⚠️ Non-atomic |
| Appreciation save | `apprec_saved` | `try/except` (fail-silent) | ⚠️ Non-atomic |
| Release results | aucun | — | N/A |
| Unrelease results | aucun | — | N/A |

### 7.2 Événements potentiellement dupliqués

#### `validate_copy` : doublon possible

Comme vu en §5.1, 2 validations simultanées créent 2 événements `VALIDATE` pour la même copie. Ce n'est pas un bug fonctionnel mais une trace d'audit incorrecte.

#### `finalize_copy` : protégé par `get_or_create`

```python
GradingEvent.objects.get_or_create(
    copy=copy, action=GradingEvent.Action.FINALIZE, actor=user, ...)
```

Idempotent. Si 2 threads arrivent dans le même bloc (impossible grâce au `select_for_update`, mais safety net), un seul événement est créé. ✅

#### Score/Remark/Appreciation : pas de protection contre doublon

Chaque PUT scores crée un `GradingEvent` `scores_saved`. 5 saves = 5 events. C'est voulu (audit trail complet), mais un double-clic rapide crée 2 events quasi-identiques.

### 7.3 Événements manqués

#### Remark save et Appreciation save — fail-silent

```python
try:
    GradingEvent.objects.create(copy=copy, actor=request.user, action='remark_saved', ...)
except Exception:
    logger.warning("Failed to create GradingEvent...")
```

Si la création du `GradingEvent` échoue (ex: DB timeout), la remarque est sauvegardée mais l'audit trail est perdu. C'est un **fail-open** sur l'audit.

**Sévérité : FAIBLE**. La remarque elle-même a un `updated_at` auto. L'audit trail est un nice-to-have pour les remarques, pas un invariant métier.

#### Release/Unrelease : aucun audit trail

Ni `ExamReleaseResultsView` ni `ExamUnreleaseResultsView` ne créent de `GradingEvent`. Il n'y a aucune trace de qui a publié ou dépublié les résultats, ni quand.

**Sévérité : MOYENNE** pour un audit trail complet. Mais la colonne `Exam.results_released_at` + `Exam.updated_at` fournissent une trace minimale.

### 7.4 Événements désynchronisés de l'état réel

Le seul risque est sur `validate_copy` : 2 événements VALIDATE pour une copie validée une seule fois. C'est un faux doublon d'audit, pas une désynchronisation d'état.

Pour `finalize_copy`, l'événement FINALIZE (success) est créé DANS le même `@transaction.atomic` que le `copy.status = GRADED`. Si le PDF échoue, un événement FINALIZE (failure) est créé à la place. **L'audit trail est toujours cohérent avec l'état final de la copie.** ✅

### 7.5 Verdict audit trail

**Sécurité correcte pour les opérations critiques** (finalize, annotations, scores). **Lacunes sur les opérations secondaires** (release/unrelease sans event, remark/appreciation fail-silent).

---

## 8. Tests

### 8.1 Tests de concurrence existants

| Fichier | Test | Ce qu'il prouve | Ce qu'il ne prouve pas |
|---|---|---|---|
| `test_concurrency.py:38` | `test_concurrent_annotation_updates_sequential_lww` | LWW séquentiel sur annotations | Concurrence réelle (SQLite) |
| `test_concurrency.py:76` | `test_double_finalize_race` | **Rien** — le body est `pass` | — |
| `test_concurrency.py:109` | `test_finalize_uses_select_for_update_on_copy` | `select_for_update` est appelé dans finalize | Que le lock bloque réellement un concurrent |
| `test_lot3_11_fixes.py:333` | `TestScoreAtomicWrite` | Séquentiel LWW + pas de duplication | Concurrence réelle |
| `test_lot3_11_fixes.py:396` | `TestScoreUniqueConstraint` | `UniqueConstraint` sur Score.copy | — |
| `test_permissions_lot8.py` | 42 tests permissions | Permissions et ownership | Concurrence |

### 8.2 Ce que les tests ne prouvent PAS

1. **Aucun test de concurrence réelle** (threads/processus parallèles). Tous les tests sont séquentiels, car SQLite (utilisé par le test runner) ne supporte pas `select_for_update` de manière réaliste.

2. **`test_double_finalize_race`** a un body `pass` — c'est un placeholder jamais implémenté.

3. **Aucun test de lock acquisition concurrent** (2 users acquérant le lock simultanément).

4. **Aucun test de race condition draft** (2 onglets sauvegardant un draft simultanément).

5. **Aucun test de `IntegrityError` sur `CopyLock` double create**.

### 8.3 Ce qu'il faudrait tester sous PostgreSQL réel

| Test | Priorité | Difficulté |
|---|---|---|
| Double finalize concurrent (2 threads) | HAUTE | Nécessite PostgreSQL + `TransactionTestCase` + threading |
| Score PUT concurrent (2 threads, même copie) | HAUTE | Idem |
| Lock acquire concurrent (2 users) | MOYENNE | Idem |
| Draft autosave concurrent (2 client_ids) | FAIBLE | Possible sur SQLite avec séquentiel |
| Annotation version conflict | FAIBLE | Possible sur SQLite |
| finalize_copy + score PUT concurrent | HAUTE | Vérifie que le lock bloque le PUT pendant la génération PDF |

**Infrastructure requise** : Le projet a un `settings_test_postgres.py` prévu mais non utilisé dans la CI. Les tests réels de concurrence nécessiteraient :
- Un PostgreSQL de test
- `TransactionTestCase` (pas `TestCase`) pour permettre les threads
- `threading.Thread` ou `concurrent.futures` pour les workers concurrents

---

## 9. Focus spécial "impact données"

### 9.1 Risques résiduels et impact par type de données

| Risque concurrent résiduel | Probabilité production | Impact notes | Impact annotations | Impact remarques | Impact appréciations | Impact états | Impact PDFs | Impact audit |
|---|---|---|---|---|---|---|---|---|
| **Lost update scores (2 onglets)** | Faible | ⚠️ Un save écrase l'autre silencieusement | — | — | — | — | — | ✅ Les 2 saves sont loggés |
| **Double validate** | Très faible | — | — | — | — | ✅ État correct | — | ⚠️ Doublon event |
| **Annotation sans version frontend** | Moyenne | — | ⚠️ LWW si 2 PATCH rapides | — | — | — | — | ✅ Les 2 updates sont loggés |
| **Lock non-enforced sur écritures** | Très faible (ownership) | ✅ Ownership protège | ✅ Ownership protège | ✅ Ownership protège | ✅ Ownership protège | — | — | — |
| **Long lock pendant finalize** | Faible | ⚠️ PUT scores bloqué 2-30s | ⚠️ POST annotation bloqué | — | — | — | — | — |
| **LLM summary concurrent** | Faible | — | — | — | — | — | ⚠️ 2 PDFs générés (LWW sur llm_summary) | — |
| **Release results sans audit** | Faible | — | — | — | — | — | — | ❌ Pas tracé |

### 9.2 Pire cas réaliste : perte de score

**Scénario** : Correcteur ouvre 2 onglets. Onglet A note Q1=5.0, Q2=3.0. Onglet B (ouvert avant) note Q1=2.0, Q3=4.0. Les deux cliquent "Sauvegarder" à 1s d'intervalle.

**Résultat** : Le dernier PUT écrase complètement `scores_data`. Si B arrive après A, le résultat est `{Q1: 2.0, Q3: 4.0}` — les notes Q2 de A sont perdues.

**Probabilité** : Très faible. Le frontend recharge après save, donc les onglets se synchronisent. Mais un utilisateur "power user" avec des saves rapides pourrait le déclencher.

**Impact** : Perte de notes par question. Récupérable via l'audit trail (`GradingEvent` `scores_saved` contient `nq` et `total`).

### 9.3 Pire cas réaliste : doublon d'audit

**Scénario** : Admin clique 2 fois "Valider" (STAGING→READY) en 100ms.

**Résultat** : 2 `GradingEvent VALIDATE` créés pour la même copie. L'état final est correct (READY).

**Impact** : Pollution de l'audit trail. Mineur. Détectable par query `GROUP BY copy_id, action HAVING count > 1`.

### 9.4 Pire cas théorique : annotation sur copie en cours de finalisation

**Scénario** : Le correcteur clique "Finaliser" et au même instant un autosave d'annotation tente un POST.

**Résultat** :
- Le POST annotation lit `copy.status = READY` (avant le lock)
- `finalize_copy` prend le lock, passe à `GRADING_IN_PROGRESS`
- Le POST annotation fait `Annotation.objects.create()` sans lock → réussit
- `finalize_copy` génère le PDF → le PDF INCLUT la dernière annotation car `flatten_copy` lit les annotations au moment de la génération
- Résultat : ✅ Le PDF est cohérent (inclut toutes les annotations au moment de la génération)

Mais si l'annotation arrive APRÈS la génération du PDF :
- Le PDF final ne contient PAS la dernière annotation
- L'annotation existe en DB mais pas dans le PDF
- **Incohérence PDF ↔ DB**

**Probabilité** : Extrêmement faible (fenêtre de ~100ms pendant la génération PDF).

**Impact** : Une annotation manquante dans le PDF final. Corrigeable par re-finalisation.

---

## 10. Verdict

### Classification

| Domaine | Verdict |
|---|---|
| **Finalization (READY→GRADED)** | ✅ **Sécurisé** — `select_for_update` + status check + `get_or_create` audit |
| **Score write (`CopyScoresView.put`)** | ⚠️ **Partiellement sécurisé** — sérialisé mais LWW sans détection |
| **Draft autosave** | ✅ **Sécurisé** — `client_id` + conditional update + `F('version')` |
| **Lock acquire/release/heartbeat** | ⚠️ **Partiellement sécurisé** — correctement sérialisé mais advisory-only + IntegrityError non catchée |
| **Annotations** | ⚠️ **Partiellement sécurisé** — optimistic locking optionnel |
| **Remarques / Appréciations** | ⚠️ **Faiblement sécurisé** — LWW pur, mais mono-correcteur atténue |
| **Transitions STAGING→READY** | ⚠️ **Faiblement sécurisé** — pas de `select_for_update`, doublon audit possible |
| **Release/Unrelease results** | ✅ **Acceptable** — opération idempotente, risque bénin |
| **Audit trail** | ⚠️ **Partiellement complet** — release/unrelease non tracés, remark/appreciation fail-silent |
| **Tests de concurrence** | ❌ **Insuffisants** — aucun test de concurrence réelle, placeholder `pass` |

### Verdict global : **SÉCURITÉ PARTIELLE**

**Justification sévère :**

Les protections les plus critiques sont en place :
- `finalize_copy` est correctement protégé par `select_for_update` — c'est l'opération la plus dangereuse et elle est sûre.
- Le `UniqueConstraint` sur `Score.copy` empêche les doublons.
- Le `CopyLock` est correctement sérialisé via `select_for_update`.
- Le draft autosave est robuste via conditional update.

Mais des lacunes réelles existent :
1. **Aucun test de concurrence réelle** — on PROUVE que `select_for_update` est appelé, mais on ne PROUVE PAS qu'il bloque correctement sous PostgreSQL.
2. **`validate_copy` n'a pas de `select_for_update`** — doublon d'audit possible.
3. **Le `CopyLock` est advisory** — pas enforced côté serveur. Le status `LOCKED` n'est jamais écrit.
4. **Le versioning des annotations est optionnel** — dépend du frontend.
5. **L'audit trail est incomplet** — release/unrelease et certains fail-silent.
6. **Le long lock pendant finalize** peut bloquer les PUT scores pendant 30s.

**Ce qui sauve la situation en production** :
- Le modèle `assigned_corrector` ownership fait qu'un seul humain travaille sur une copie à la fois.
- Le frontend est le seul client (pas d'API publique).
- Le volume est faible (4-8 correcteurs, 209 copies).
- Les opérations les plus critiques (finalize, scores, locks) sont correctement sérialisées.

### Recommandations par priorité

| # | Action | Priorité | Effort |
|---|---|---|---|
| 1 | Ajouter `select_for_update` dans `validate_copy` | P1 | 2 lignes |
| 2 | Catch `IntegrityError` dans `acquire_lock` → `LockConflictError` | P1 | 5 lignes |
| 3 | Ajouter des tests de concurrence réels sous PostgreSQL | P1 | 1 jour |
| 4 | Ajouter un `GradingEvent` pour release/unrelease results | P2 | 10 lignes |
| 5 | Rendre le versioning annotations obligatoire (rejeter si `version` absent sur PATCH) | P2 | 5 lignes |
| 6 | Documenter que `CopyLock` est advisory et supprimer ou implémenter `Copy.Status.LOCKED` | P2 | Documentation |
| 7 | Envelopper remark/appreciation audit dans `transaction.atomic` au lieu de try/except | P3 | 10 lignes |
| 8 | Ajouter un champ `version` sur `Score` pour détection de concurrent write | P3 | Migration + 15 lignes |
| 9 | Raccourcir le lock finalize en séparant la génération PDF du `select_for_update` | P3 | Refactoring significatif |
