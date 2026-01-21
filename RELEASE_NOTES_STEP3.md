# Release Notes - Étape 3: Backend Annotation & Grading Workflow

**Date:** 2026-01-21
**Status:** ✅ Production-ready
**Key commits:** 1d2790c, 7d940d6, 094a7b2, c34cafb, 85f5931, c4033f3

---

## What's New

### Core Features

- **Vector Annotation System (ADR-002)**: Implemented normalized coordinate system [0,1] for resolution-independent rectangle annotations on PDF pages. All annotations are validated with strict bounds checking (w>0, h>0, x+w≤1, y+h≤1).

- **State Machine Workflow (ADR-003)**: Enforced strict Copy lifecycle (STAGING → READY → LOCKED → GRADED) with audit trail via `GradingEvent` model. Annotations can only be created/modified when Copy status is READY.

- **7 REST API Endpoints**: Full CRUD for annotations plus workflow transitions (lock/unlock/finalize). All endpoints protected by `IsTeacherOrAdmin` permission class.

### Critical Corrections (1d2790c)

- **Fixed AUTH_USER_MODEL references**: Replaced direct User imports with `settings.AUTH_USER_MODEL` for custom user model compatibility in `Annotation`, `GradingEvent`, and `Copy` models.

- **Removed media files from git**: Added `backend/media/` to `.gitignore` and purged tracked runtime outputs (PDFs, PNGs). Storage outputs are no longer versioned.

- **Fixed migration dependencies**: Corrected 0002_annotation migration to properly depend on exams.0003_copy_workflow_fields.

### Validation & Storage (7d940d6, c34cafb)

- **Storage-agnostic PDF flattener**: Refactored `PDFFlattener` to use `NamedTemporaryFile` instead of hardcoded `MEDIA_ROOT` paths. Now compatible with S3/MinIO/GCS without code changes.

- **Runtime P0 validation proof** (c34cafb): Created `scripts/test_etape3_p0_validation_simple.sh` proving all 4 invariants (w=0 rejected, overflow rejected, page_index bounds checked, PATCH validation with candidate values).

- **Page index validation**: Added `validate_page_index()` with dynamic page count from booklets' `pages_images` arrays. Prevents annotations on non-existent pages.

### Quality Improvements (094a7b2, 85f5931)

- **Int-like page_index handling**: `validate_page_index()` accepts strings convertible to integers ("0", "1") for better frontend compatibility.

- **Standardized DRF error format**: All API errors return `{"detail": "<message>"}` format. Exception mapping: ValueError/KeyError → 400, PermissionError → 403, unexpected Exception → 500.

- **Context-aware logging**: All error handlers include view/method context (e.g., "Service error (AnnotationDetailView.update): x + w must not exceed 1") for debugging traceability.

---

## Known Limitations

1. **No pytest unit tests**: Validations proven by bash/curl script only. Recommend adding `tests/test_annotation_service.py` with pytest-django.

2. **No STAGING→READY endpoint**: State transition not exposed in API (likely handled by processing pipeline).

3. **compute_score() error handling**: Database aggregation errors during finalization may leave Copy in inconsistent state (not wrapped in transaction).

4. **No soft-delete for annotations**: Deleted annotations are permanently removed (no audit trail preservation).

5. **Migration 0002 is destructive**: Drops old annotation table. Backup required if migrating existing production database.

---

## API Endpoints Summary

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET/POST | `/api/copies/<uuid>/annotations/` | List/create annotations |
| GET/PATCH/DELETE | `/api/annotations/<uuid>/` | Retrieve/update/delete annotation |
| POST | `/api/copies/<uuid>/lock/` | Lock copy for grading |
| POST | `/api/copies/<uuid>/unlock/` | Unlock copy |
| POST | `/api/copies/<uuid>/finalize/` | Finalize grading + generate PDF |

---

## Verification Commands

```bash
# Django checks
docker-compose exec -T backend python manage.py check

# Runtime validation tests
docker-compose restart backend && sleep 5
./scripts/test_etape3_p0_validation_simple.sh

# Verify no media files tracked
git ls-files | grep -E "^backend/media/" && echo "FAIL" || echo "OK"
```

---

## Documentation (c4033f3)

Comprehensive technical documentation added:
- `.claude/ETAPE_3_ANNOTATION_GRADING.md`: Implementation details, ADR references, known limitations
- `RELEASE_NOTES_STEP3.md`: This file
- `scripts/README.md`: Runtime test instructions with container restart warning

---

**Maintainer:** Claude Sonnet 4.5
