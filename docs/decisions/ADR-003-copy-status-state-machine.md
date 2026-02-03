# ADR-003 : Machine à États pour le Statut des Copies

## Statut
✅ **Accepté** (2026-01-21)

## Contexte

Les copies passent par plusieurs étapes dans leur cycle de vie :
1. Détection automatique (fascicules)
2. Validation manuelle
3. Correction par professeur
4. Publication aux élèves

Nous devons définir les états possibles et les transitions autorisées.

**Contraintes** :
- Traçabilité complète du workflow
- Impossible de corriger une copie non prête
- Impossible de modifier une copie finalisée
- Verrouillage pendant correction (un seul correcteur)
- Possibilité de débloquer si erreur

## Décision

**Implémenter une machine à états stricte avec 4 états et transitions contrôlées.**

### États

```python
class Status(models.TextChoices):
    STAGING = 'STAGING', "En attente de validation"
    READY = 'READY', "Prêt à corriger"
    LOCKED = 'LOCKED', "En cours de correction"
    GRADED = 'GRADED', "Corrigé et finalisé"
```

### Diagramme de Transitions

```
STAGING ──(validate)──> READY
                         ↓
                      (lock)
                         ↓
                       LOCKED ←─(unlock, si erreur)─┐
                         ↓                           │
                    (finalize)                       │
                         ↓                           │
                       GRADED (immutable)            │
                                                     │
         (si nécessaire, rollback exceptionnel) ────┘
```

### Transitions Autorisées

| État Actuel | Action      | État Suivant | Qui           |
|-------------|-------------|--------------|---------------|
| STAGING     | validate    | READY        | Professeur    |
| READY       | lock        | LOCKED       | Professeur    |
| LOCKED      | unlock      | READY        | Même prof ou Admin |
| LOCKED      | finalize    | GRADED       | Professeur    |
| GRADED      | (aucune)    | -            | Immutable     |

### Validation Backend

```python
def lock_copy(copy, professor):
    if copy.status != Copy.Status.READY:
        raise ValueError(f"Cannot lock copy in state {copy.status}")

    copy.status = Copy.Status.LOCKED
    copy.locked_by = professor
    copy.locked_at = timezone.now()
    copy.save()

def finalize_copy(copy):
    if copy.status != Copy.Status.LOCKED:
        raise ValueError(f"Cannot finalize copy in state {copy.status}")

    # Générer PDF final, etc.
    copy.status = Copy.Status.GRADED
    copy.graded_at = timezone.now()
    copy.save()
```

## Conséquences

### Positives
- ✅ Workflow métier explicite et vérifiable
- ✅ Impossible de contourner les étapes
- ✅ Traçabilité complète (timestamps par état)
- ✅ Verrouillage automatique pendant correction
- ✅ État GRADED immutable (intégrité)

### Négatives
- ❌ Rollback complexe si erreur après GRADED
- ❌ Besoin de procédure admin pour cas exceptionnels
- ❌ Tests de toutes les transitions nécessaires

### Risques
- ⚠️ Si bug dans validation transition, copies bloquées
- ⚠️ Unlock doit être tracé (qui, quand, pourquoi)

## Alternatives Considérées

### Alternative A : États libres sans validation
**Rejetée car** :
- Risque d'incohérences (copie GRADED modifiée)
- Pas de traçabilité workflow
- Bugs difficiles à diagnostiquer

### Alternative B : Plus d'états (REVIEWING, PUBLISHED, etc.)
**Rejetée car** :
- Complexité inutile pour V1
- 4 états suffisent pour workflow actuel
- Évolutif si nécessaire (ajout états futurs)

### Alternative C : Soft delete au lieu d'immutable
**Rejetée car** :
- État GRADED doit être fiable
- Audit trail nécessite immutabilité
- Rollback possible via admin si vraiment nécessaire

## Validation

Cette décision respecte :
- ✅ Workflow métier (correction_flow.md)
- ✅ Intégrité des données (règle 04_database_rules.md)
- ✅ Traçabilité (règle 00_global_rules.md)

## Implémentation Requise

- [x] Enum Status dans Copy model
- [x] Validation transitions dans services
- [x] Tests toutes les transitions
- [x] Tests transitions interdites (doivent échouer)
- [x] Logging changements de statut
- [x] Admin action pour unlock exceptionnel

## Tests Critiques

```python
def test_cannot_lock_staging_copy():
    copy = Copy.objects.create(status=Copy.Status.STAGING)
    with pytest.raises(ValueError):
        CopyService.lock_copy(copy, professor)

def test_cannot_finalize_ready_copy():
    copy = Copy.objects.create(status=Copy.Status.READY)
    with pytest.raises(ValueError):
        CopyService.finalize_copy(copy)

def test_graded_is_immutable():
    copy = Copy.objects.create(status=Copy.Status.GRADED)
    copy.status = Copy.Status.READY
    copy.save()

    copy.refresh_from_db()
    # Devrait rester GRADED (ou lever exception)
    assert copy.status == Copy.Status.GRADED
```

## Champs Traçabilité

```python
class Copy(models.Model):
    status = models.CharField(choices=Status.choices)

    # Traçabilité
    created_at = models.DateTimeField(auto_now_add=True)
    validated_at = models.DateTimeField(null=True)  # STAGING → READY
    locked_at = models.DateTimeField(null=True)     # READY → LOCKED
    locked_by = models.ForeignKey(User, null=True)
    graded_at = models.DateTimeField(null=True)     # LOCKED → GRADED
```

## Date
2026-01-21

## Auteur
Alaeddine BEN RHOUMA (Backend Architect)
