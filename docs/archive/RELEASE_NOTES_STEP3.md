# Release Notes - Étape 3: Backend Annotation & Grading Workflow

**Date:** 2026-01-21
**Status:** ✅ Production-ready
**Key commits:** 1d2790c, 7d940d6, 094a7b2, c34cafb, 85f5931, c4033f3

---

## Highlights

- **Vector Annotation System (ADR-002)** (7d940d6): Normalized coordinates [0,1] for resolution-independent rectangles with strict validation (w>0, h>0, x+w≤1, y+h≤1, page_index bounds checked).

- **State Machine Workflow (ADR-003)**: Enforced Copy lifecycle (STAGING→READY→LOCKED→GRADED) with `GradingEvent` audit trail. Annotations restricted to READY status.

- **7 REST API Endpoints**: Full CRUD for annotations + workflow transitions (lock/unlock/finalize), protected by `IsTeacherOrAdmin`.

- **Fixed AUTH_USER_MODEL references** (1d2790c): Replaced direct User imports with `settings.AUTH_USER_MODEL` for custom user model compatibility.

- **Removed media files from git** (1d2790c): Added `backend/media/` to `.gitignore`. Runtime outputs no longer versioned.

- **Storage-agnostic PDF flattener** (7d940d6): Refactored to use `NamedTemporaryFile` instead of hardcoded paths. Compatible with S3/MinIO/GCS.

- **Runtime P0 validation proof** (c34cafb): Script `test_etape3_p0_validation_simple.sh` proves all 4 invariants (w=0 rejected, overflow rejected, page_index bounds, PATCH validation).

- **Standardized DRF error format** (85f5931): All errors return `{"detail": "<message>"}`. Exception mapping: ValueError/KeyError→400, PermissionError→403, Exception→500 with context logging.

- **Int-like page_index handling** (094a7b2): Accepts string values convertible to integers ("0", "1") for frontend compatibility.

- **Comprehensive documentation** (c4033f3): Added `docs/ETAPE_3_ANNOTATION_GRADING.md` (ADR refs, known limitations, checklist) and `scripts/README.md` (container restart warning).

---

## Known Limitations

No pytest unit tests (bash/curl proof only) • No STAGING→READY endpoint • compute_score() not transactional • No soft-delete for annotations • Migration 0002 destructive (backup required)

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET/POST | `/api/copies/<uuid>/annotations/` | List/create annotations |
| GET/PATCH/DELETE | `/api/annotations/<uuid>/` | Retrieve/update/delete annotation |
| POST | `/api/copies/<uuid>/lock/` | Lock copy for grading |
| POST | `/api/copies/<uuid>/unlock/` | Unlock copy |
| POST | `/api/copies/<uuid>/finalize/` | Finalize grading + generate PDF |

---

## Verification

Run `docker-compose exec -T backend python manage.py check` (0 issues), restart backend, execute `./scripts/test_etape3_p0_validation_simple.sh` (4/4 tests pass), verify `git ls-files | grep "^backend/media/"` returns empty.

---

**Maintainer:** Alaeddine BEN RHOUMA
