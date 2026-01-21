# Étape 3 - Backend Annotation & Grading Workflow

**Status:** ✅ Completed
**Date:** 2026-01-21
**Commits clés:** 1d2790c, 7d940d6, 094a7b2, 85f5931
**Commande de vérification:** `docker-compose exec -T backend python manage.py check` → 0 issues

---

## Vue d'ensemble

Implémentation complète du workflow de correction avec annotations vectorielles normalisées (ADR-002) et machine d'états stricte (ADR-003).

### Composants livrés

- **Models** : `Annotation` (coordonnées [0,1]), `GradingEvent` (audit trail)
- **Services** : `AnnotationService`, `GradingService` (logique métier + validation)
- **API** : 7 endpoints REST protégés par `IsTeacherOrAdmin`
- **PDFFlattener** : Génération PDF annotés avec storage agnostique
- **Tests runtime** : Script bash/curl prouvant les 4 invariants P0

---

## Invariants ADR-002 : Coordonnées normalisées

### Validation stricte des rectangles

Toutes les annotations doivent respecter :

```python
# Bornes individuelles
0 ≤ x ≤ 1  # Position horizontale
0 ≤ y ≤ 1  # Position verticale
0 < w ≤ 1  # Largeur (strictement positive)
0 < h ≤ 1  # Hauteur (strictement positive)

# Bornes du rectangle
x + w ≤ 1  # Pas de débordement horizontal
y + h ≤ 1  # Pas de débordement vertical

# Page_index borné
0 ≤ page_index < nb_pages_réelles
```

**Localisation de la validation :**
- Service layer : `backend/grading/services.py` (`validate_coordinates()`, `validate_page_index()`)
- Serializer DRF : Validation partielle (uniquement si tous les champs présents)

**Conséquence :** Les rectangles vides (w=0 ou h=0) et les débordements sont **rejetés avec HTTP 400**.

---

## Storage-agnostic PDF Flattener

### Architecture

Le `PDFFlattener` ne dépend pas du stockage local :

```python
# ❌ Avant (couplé au filesystem)
output_path = MEDIA_ROOT / "copies/final/" / filename
doc.save(output_path)
copy.final_pdf.save(filename, File(output_path))

# ✅ Après (storage-agnostic)
with NamedTemporaryFile(suffix=".pdf") as tmp:
    doc.save(tmp.name)
    tmp.seek(0)
    copy.final_pdf.save(filename, File(tmp), save=False)
```

**Bénéfices :**
- Compatible S3/MinIO/GCS sans modification
- Pas de gestion manuelle de répertoires
- Le storage Django est la seule source de vérité

**Localisation :** `backend/processing/services/pdf_flattener.py:78-89`

---

## Standardisation des erreurs DRF

### Format uniforme

Toutes les erreurs API retournent le format DRF standard :

```json
{"detail": "<message>"}
```

Jamais `{"error": "..."}` ou format custom.

### Mapping exception → HTTP

| Exception | HTTP | Body | Log Level |
|-----------|------|------|-----------|
| `ValueError` | 400 | `{"detail": "<message>"}` | `logger.warning` |
| `KeyError` | 400 | `{"detail": "Missing required field: <field>"}` | `logger.info` |
| `PermissionError` | 403 | `{"detail": "<message>"}` | `logger.warning` |
| `Exception` (autre) | 500 | `{"detail": "Internal server error"}` | `logger.exception` |

### Context dans les logs

Chaque erreur inclut le contexte d'origine :

```python
logger.warning("Service error (%s): %s", context, str(e))
# Exemple: Service error (AnnotationListCreateView.create): w and h must be in (0, 1]
```

**Localisation :** `backend/grading/views.py` helpers `_handle_service_error` et `_handle_unexpected_error`

---

## Machine d'états ADR-003

### Workflow Copy

```
STAGING ──validate──> READY ──lock──> LOCKED ──finalize──> GRADED
              ↑                           │
              └──────────unlock───────────┘
```

### Règles annotations

| Statut | Créer | Modifier | Supprimer | Lire |
|--------|-------|----------|-----------|------|
| STAGING | ❌ | ❌ | ❌ | ✅ |
| READY | ✅ | ✅ | ✅ | ✅ |
| LOCKED | ❌ | ❌ | ❌ | ✅ |
| GRADED | ❌ | ❌ | ❌ | ✅ |

**Implémentation :** Toutes les transitions créent un `GradingEvent` pour audit trail.

---

## Tests runtime

### Script de validation P0 (coordonnées)

```bash
./scripts/test_etape3_p0_validation_simple.sh
```

**Tests couverts :**
1. ✅ `w=0` rejeté avec 400
2. ✅ `x+w > 1` rejeté avec 400
3. ✅ `page_index` hors bornes rejeté avec 400
4. ✅ PATCH partiel causant débordement rejeté avec 400

### Script E2E Workflow

```bash
./scripts/test_etape3_workflow_e2e.sh
```

**Tests couverts :**
1. ✅ STAGING → READY (validates booklets have pages)
2. ✅ Create annotation on READY copy
3. ✅ READY → LOCKED
4. ✅ LOCKED → GRADED (finalize)
5. ✅ Download final PDF (200 response, endpoint functional)

**Prérequis :**
- Backend up : `docker-compose up -d backend`
- Migrations appliquées

**⚠️ Note importante :** Si vous modifiez le code backend, **redémarrez le container** avant de relancer les tests :

```bash
docker-compose restart backend
sleep 5
./scripts/test_etape3_*.sh
```

Sans redémarrage, le container utilise l'ancienne version du code (faux positifs/négatifs possibles).

---

## API Endpoints

### Annotations

| Méthode | Endpoint | Description | Permission |
|---------|----------|-------------|------------|
| GET | `/api/copies/<uuid>/annotations/` | Liste annotations | IsTeacherOrAdmin |
| POST | `/api/copies/<uuid>/annotations/` | Crée annotation (si READY) | IsTeacherOrAdmin |
| GET | `/api/annotations/<uuid>/` | Détail annotation | IsTeacherOrAdmin |
| PATCH | `/api/annotations/<uuid>/` | Modifie annotation (si READY) | IsTeacherOrAdmin |
| DELETE | `/api/annotations/<uuid>/` | Supprime annotation (si READY) | IsTeacherOrAdmin |

### Workflow Copy

| Méthode | Endpoint | Description | Permission |
|---------|----------|-------------|------------|
| POST | `/api/copies/<uuid>/ready/` | STAGING → READY (validates pages exist) | IsTeacherOrAdmin |
| POST | `/api/copies/<uuid>/lock/` | READY → LOCKED | IsTeacherOrAdmin |
| POST | `/api/copies/<uuid>/unlock/` | LOCKED → READY | IsTeacherOrAdmin |
| POST | `/api/copies/<uuid>/finalize/` | LOCKED → GRADED + génère PDF | IsTeacherOrAdmin |
| GET | `/api/copies/<uuid>/final-pdf/` | Download corrected PDF (FileResponse) | IsTeacherOrAdmin |

---

## Known Limitations / Next Steps

1. **Pas de tests unitaires pytest** : Les validations sont prouvées par script bash/curl runtime uniquement (scripts/test_etape3_*.sh). Recommandation : ajouter `tests/test_annotation_service.py` avec pytest-django pour coverage automatisé.

2. **Finalize transaction strategy** : `finalize_copy()` est @transaction.atomic et inclut la génération PDF. En cas d'erreur PDF, la transaction DB est rollback (état cohérent), mais le fichier PDF temporaire peut rester sur le storage si Django storage a écrit avant l'erreur. Stratégie acceptable pour MVP : nettoyage manuel des fichiers orphelins si nécessaire. Alternative (non implémentée) : générer PDF hors transaction puis commit, mais risque inverse (Copy GRADED sans PDF si storage échoue).

3. **Pas de soft-delete pour Annotation** : Une annotation supprimée est définitivement perdue (pas de flag `is_deleted`). Acceptable en MVP, mais envisager un audit trail plus robuste pour production.

4. **Migration 0002 destructive** : Supprime les anciennes annotations (modèle pré-ADR-002). Si migration sur base existante, prévoir une sauvegarde ou script de conversion.

5. **PDF generation requires real page images** : PDFFlattener expects valid PNG/JPG paths in `booklets.pages_images`. E2E test creates fake paths, resulting in empty PDF (endpoint still responds correctly). Real workflow requires exam PDF upload + split.

---

## Checklist de vérification post-modification

Après tout changement dans `backend/grading/`, exécuter :

```bash
# 1. Checks Django
docker-compose exec -T backend python manage.py check

# 2. Compilation Python
docker-compose exec -T backend bash -c "cd /app && python -m compileall grading"

# 3. Redémarrer backend
docker-compose restart backend && sleep 5

# 4. Tests runtime P0
./scripts/test_etape3_p0_validation_simple.sh

# 5. Vérifier aucun media versionné
git ls-files | grep -E "^backend/media/" && echo "FAIL" || echo "OK"
```

**Résultat attendu :** Tous les checks passent, 4/4 tests P0 réussis, aucun fichier media versionné.

---

## Références

- **ADR-002** : Coordonnées normalisées pour annotations vectorielles
- **ADR-003** : Machine d'états workflow de correction
- **Commits clés** :
  - `1d2790c` : Correctifs critiques (media, AUTH_USER_MODEL, migrations)
  - `7d940d6` : Validations P0 (rectangles, page_index, storage)
  - `094a7b2` : Améliorations P1 (int-like, docstrings)
  - `85f5931` : Context + logging final pass

**Maintainer:** Claude Sonnet 4.5
**Last updated:** 2026-01-21
