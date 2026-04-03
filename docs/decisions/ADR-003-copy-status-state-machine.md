# ADR-003 : Machine à États du Statut des Copies

## Statut
✅ **Accepté — Version 4 (Avril 2026)**

> Ce document remplace les versions antérieures qui décrivaient les états `STAGING`, `LOCKED`, `GRADING_IN_PROGRESS`, `GRADED` ou l’usage de `finalizing_at` comme mécanisme actif.

---

## Décision

Le modèle métier actif pour `Copy.status` est :

```python
class Copy.Status(models.TextChoices):
    READY = "READY"
    IN_PROGRESS = "IN_PROGRESS"
    FINALIZED = "FINALIZED"
```

Transitions autorisées :

```text
READY -> IN_PROGRESS -> FINALIZED
  ^                         |
  +------ reopen admin -----+
```

---

## Règles métier

| État actuel | Déclencheur | État suivant | Acteur |
|-------------|-------------|--------------|--------|
| `READY` | première annotation | `IN_PROGRESS` | correcteur assigné |
| `READY` | finalisation directe | `FINALIZED` | correcteur assigné |
| `IN_PROGRESS` | finalisation | `FINALIZED` | correcteur assigné |
| `FINALIZED` | réouverture | `READY` | superuser |

Conséquences :
- les copies importées arrivent directement en `READY`
- `FINALIZED` est l’unique état stable d’une copie terminée
- la réouverture administrative efface le PDF final et rétablit la copie en `READY`

---

## Concurrence de finalisation

Le code courant ne repose plus sur `Copy.finalizing_at`.

La protection active utilise :
1. `select_for_update(nowait=True)` pour empêcher l’entrée concurrente dans la phase critique
2. une mise à jour atomique du statut vers `FINALIZED`
3. `LockConflictError` pour signaler les doublons de finalisation

Schéma logique :

```python
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
```

---

## Obsolescence explicitée

Les éléments suivants sont historiques et ne doivent plus être traités comme état courant :
- `STAGING`
- `LOCKED`
- `GRADING_IN_PROGRESS`
- `GRADED`
- `Copy.finalizing_at`

Ils peuvent apparaître dans des audits, spécifications ou documents archivés conservés pour contexte.

---

## Impacts documentaires

Les documents normatifs alignés sur cette ADR sont :
- [ARCHITECTURE](../technical/ARCHITECTURE.md)
- [API_REFERENCE](../technical/API_REFERENCE.md)
- [DATABASE_SCHEMA](../technical/DATABASE_SCHEMA.md)
- [BUSINESS_WORKFLOWS](../technical/BUSINESS_WORKFLOWS.md)
- [CURRENT_STATE_MARCH_2026](../technical/CURRENT_STATE_MARCH_2026.md)

---

## Historique condensé

- **V1** : workflow long avec `STAGING/READY/LOCKED/GRADED`
- **V2/V3** : simplification vers 3 états, puis usage temporaire de `finalizing_at`
- **V4** : maintien des 3 états sans `finalizing_at`, avec garde transactionnelle sur la finalisation
