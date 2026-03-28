# ADR-003 : Machine à États du Statut des Copies

## Statut
✅ **Accepté — Version 3 (Mars 2026)**

> ⚠️ Ce document remplace intégralement les versions précédentes.
> L'ancienne machine à 4 états (STAGING/READY/LOCKED/GRADED) est **obsolète** depuis la migration 0026.
> La machine actuelle comporte **3 états** : READY / IN_PROGRESS / FINALIZED.

---

## Contexte

### Historique des versions

**V1 — Janvier 2026 (migrations 0001–0025)**
Machine à 4 états : `STAGING → READY → LOCKED → GRADED`
Problème : états redondants, friction corrective (double lock/unlock), confusion LOCKED vs GRADED, tests complexes.

**V2 — Février 2026**
Ajout de `GRADED → READY` (réouverture admin) pour corriger des erreurs post-finalisation.

**V3 — Mars 2026 (migrations 0026, 0027, 0028) — VERSION ACTUELLE**
Simplification radicale à 3 états : `READY / IN_PROGRESS / FINALIZED`.
- Suppression de STAGING (les copies importées arrivent directement en READY)
- Fusion de LOCKED et GRADING_IN_PROGRESS en un seul état IN_PROGRESS
- Renommage de GRADED en FINALIZED
- Ajout du champ `finalizing_at` comme mutex atomique anti-doublon (migration 0028)

---

## Décision

**Implémenter une machine à états à 3 états avec transitions contrôlées et garde atomique à la finalisation.**

### États actuels

```python
class Copy.Status(models.TextChoices):
    READY       = 'READY',       "Prêt à corriger"
    IN_PROGRESS = 'IN_PROGRESS', "En cours de correction"
    FINALIZED   = 'FINALIZED',   "Finalisée"
```

### Diagramme de transitions

```
                   [Première annotation créée]
READY ─────────────────────────────────────────────→ IN_PROGRESS
  ↑                                                        │
  │                                              [POST /finalize/]
  │                                                        │
  │              [Admin reopen — superuser only]           ↓
  └────────────────────────────────────────────── FINALIZED
```

### Tableau des transitions autorisées

| État actuel | Déclencheur | État suivant | Qui | Effets de bord |
|-------------|-------------|--------------|-----|----------------|
| READY | Première annotation créée via `AnnotationService.add_annotation()` | IN_PROGRESS | Enseignant assigné | GradingEvent.CREATE_ANN enregistré |
| IN_PROGRESS | `POST /api/grading/copies/{id}/finalize/` | FINALIZED | Enseignant assigné | PDF aplati, `graded_at=now()`, `finalizing_at=None`, GradingEvent.FINALIZE |
| READY | `POST /api/grading/copies/{id}/finalize/` | FINALIZED | Enseignant assigné | Idem (finalisation directe possible depuis READY) |
| FINALIZED | `POST /api/grading/copies/{id}/reopen/` | READY | Superuser admin uniquement | `final_pdf` effacé, `graded_at=None`, `grading_retries` reset, GradingEvent.REOPEN |

### Cas spécial : ré-upload bloqué

Un ré-upload de PDF sur un examen est **bloqué** si une copie est IN_PROGRESS ou FINALIZED.
Il est **autorisé** si toutes les copies sont READY (les copies READY sont supprimées et recréées).

---

## Implémentation

### Service de finalisation (`GradingService.finalize_copy`)

La finalisation est protégée par un **mutex atomique PostgreSQL** via le champ `finalizing_at`.

**Problème résolu** : `select_for_update(nowait=True)` ne garantissait pas qu'un seul thread appellait `flatten_copy` dans tous les scénarios de concurrence (si le premier thread terminait avant que le second tente le lock, les deux pouvaient passer la vérification de statut).

**Solution** : UPDATE conditionnel atomique (migration 0028) :

```python
# GradingService._finalize_copy_inner (grading/services.py)

# 1. CLAIM ATOMIQUE — une seule requête concurrente peut passer
claimed = (
    Copy.objects
    .filter(
        id=copy.id,
        status__in=(Copy.Status.READY, Copy.Status.IN_PROGRESS),
        finalizing_at__isnull=True,   # ← condition de guard
    )
    .update(finalizing_at=timezone.now())  # ← atomic SQL UPDATE
)
# PostgreSQL garantit : exactement 1 requête obtient claimed=1

if claimed != 1:
    raise LockConflictError("Finalization en cours par une autre requête — réessayez.")

# 2. Recharge avec verrou pour la suite de l'écriture
copy = Copy.objects.select_for_update().get(id=copy.id)

# 3. Aplatissement PDF
pdf_bytes = PDFFlattener().flatten_copy(copy)
copy.final_pdf.save(...)

# 4. Finalisation atomique — finalizing_at remis à None en même temps
copy.status        = Copy.Status.FINALIZED
copy.graded_at     = timezone.now()
copy.finalizing_at = None   # ← libère le mutex sur succès
copy.save(update_fields=["status", "graded_at", "final_pdf", "finalizing_at", ...])
```

**Gestion d'échec** : si une exception se produit, `@transaction.atomic` effectue un rollback complet de la transaction, y compris le `UPDATE SET finalizing_at=NOW()`. Le champ revient automatiquement à NULL sans cleanup explicite.

### Transition READY → IN_PROGRESS automatique

```python
# AnnotationService.add_annotation (grading/services.py)
@transaction.atomic
def add_annotation(copy, payload, user):
    if copy.status == Copy.Status.READY:
        copy.status = Copy.Status.IN_PROGRESS
        copy.save(update_fields=['status'])
    # ... création annotation
```

### Réouverture admin

```python
# Vue reopen (grading/views.py ou équivalent)
# Accessible uniquement aux superusers
copy.status = Copy.Status.READY
copy.final_pdf.delete()
copy.graded_at = None
copy.grading_retries = 0
copy.save(...)
GradingEvent.objects.create(
    copy=copy, action=GradingEvent.Action.REOPEN, actor=user,
    metadata={'old_status': 'FINALIZED', 'old_pdf': old_pdf_name}
)
```

---

## Champ `finalizing_at` (migration 0028)

```python
# exams/models.py — Copy
finalizing_at = models.DateTimeField(
    null=True,
    blank=True,
    verbose_name="Finalisation en cours depuis",
    help_text="Marqueur atomique anti-doublon : mutex PostgreSQL pour éviter deux finalisations simultanées"
)
```

- Valeur NULL : copie non en cours de finalisation
- Valeur NON NULL : finalisation en cours (timestamp de début)
- Jamais visible en dehors de `GradingService` — ne pas l'exposer à l'API publique

---

## Tests critiques

```python
# Tests de la machine à états
def test_copy_statuses_are_exactly_three():
    valid = {c[0] for c in Copy.Status.choices}
    assert valid == {"READY", "IN_PROGRESS", "FINALIZED"}
    assert "STAGING" not in valid      # Supprimé migration 0026
    assert "LOCKED" not in valid       # Supprimé migration 0026
    assert "GRADED" not in valid       # Renommé → FINALIZED

def test_first_annotation_transitions_to_in_progress(copy_ready):
    AnnotationService.add_annotation(copy_ready, {...}, user)
    copy_ready.refresh_from_db()
    assert copy_ready.status == Copy.Status.IN_PROGRESS

def test_finalize_sets_finalized(copy_in_progress):
    GradingService.finalize_copy(copy_in_progress, user)
    copy_in_progress.refresh_from_db()
    assert copy_in_progress.status == Copy.Status.FINALIZED
    assert copy_in_progress.final_pdf
    assert copy_in_progress.finalizing_at is None  # mutex libéré

def test_finalize_concurrent_calls_flatten_once(teacher_user):
    # Postgres uniquement — @pytest.mark.postgres
    # Deux threads concurrents → 1 succès, 1 LockConflictError
    # flatten_copy appelé exactement 1 fois
    # (backend/grading/tests/test_concurrency_postgres.py)
    ...

def test_cannot_finalize_already_finalized(copy_finalized):
    with pytest.raises(LockConflictError, match="déjà finalisée"):
        GradingService.finalize_copy(copy_finalized, user)

def test_reopen_requires_superuser(copy_finalized, teacher_user):
    with pytest.raises(PermissionError):
        reopen_copy(copy_finalized, teacher_user)  # Doit échouer

def test_reopen_clears_final_pdf(copy_finalized, admin_user):
    reopen_copy(copy_finalized, admin_user)
    copy_finalized.refresh_from_db()
    assert copy_finalized.status == Copy.Status.READY
    assert not copy_finalized.final_pdf
```

---

## Conséquences

### Positives
- ✅ Machine à états simple, explicite, testable
- ✅ Mutex atomique garantit l'idempotence de la finalisation
- ✅ Zéro friction corrective (pas de lock/unlock manuel)
- ✅ Traçabilité complète via GradingEvent
- ✅ Réouverture admin possible pour corriger les erreurs post-finalisation
- ✅ Tests de concurrence verts (636 passed)

### Négatives
- ❌ Le champ `finalizing_at` ajoute une colonne en DB (migration 0028)
- ❌ La réouverture est réservée au superuser — procédure admin nécessaire

### Risques et mitigations
- ⚠️ **`finalizing_at` non-null bloquant** : si la DB crashe entre la claim et le rollback, le champ reste à une valeur non-null. Mitigation : le rollback PostgreSQL nettoie automatiquement dans 99,9% des cas ; script de récupération `recover_stuck_copies.py` pour les cas résiduels.
- ⚠️ **Annot sur copie FINALIZED bloquée** : prévu — raises ValueError. L'admin doit réouvrir avant toute modification.

---

## Alternatives considérées

### Alternative A : Conserver les 5 états (STAGING/READY/LOCKED/GRADING_IN_PROGRESS/GRADED)
**Rejetée** : états redondants causant confusion dans les tests et l'UI. Friction inutile sur le workflow correcteur.

### Alternative B : 4 états avec FINALIZING comme état transitoire
**Rejetée** : `finalizing_at` offre la même garantie sans ajouter un état visible à l'API ; rollback plus propre.

### Alternative C : Verrou Redis distribué pour la finalisation
**Rejetée** : introduit une dépendance externe supplémentaire. La solution PostgreSQL atomique est plus simple et plus robuste dans notre architecture.

---

## Fichiers concernés

| Fichier | Rôle |
|---------|------|
| `backend/exams/models.py` | Définition Copy.Status + Copy.finalizing_at |
| `backend/exams/migrations/0026_simplify_copy_status.py` | Suppression états obsolètes |
| `backend/exams/migrations/0027_rename_copy_statuses.py` | Renommage vers noms actuels |
| `backend/exams/migrations/0028_copy_finalizing_at.py` | Ajout champ finalizing_at |
| `backend/grading/services.py` | GradingService.finalize_copy + _finalize_copy_inner |
| `backend/grading/tests/test_concurrency_postgres.py` | Test de concurrence Postgres |
| `backend/grading/tests/test_multi_exam_isolation.py` | Isolation multi-examens |
| `backend/exams/tests/test_audit_fixes.py` | Tests audit + re-upload |

---

## Date
- V1 : 2026-01-21 (4 états)
- V2 : 2026-02-15 (réouverture admin)
- V3 : 2026-03-28 (3 états + `finalizing_at`) — **VERSION ACTUELLE**

## Auteur
Alaeddine BEN RHOUMA (Backend Architect)
