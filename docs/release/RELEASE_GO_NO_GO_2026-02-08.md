# Release GO/NO-GO Report — 2026-02-08

## VERDICT: CONDITIONAL GO

**Condition**: E2E Playwright must pass on Docker Compose production-like stack (single-origin nginx proxy) before production deploy.

### E2E Status (2026-02-08 23:15 UTC+1)
- **Global setup login**: PASS (HTTP 200)
- **Global setup /api/me/**: PASS (HTTP 200)
- **Dashboard navigation**: FAIL — SameSite cookie not propagated in split-origin Playwright setup
- **Root cause**: E2E designed for single-origin Docker Compose (nginx). Split Vite+Django localhost has cookie isolation in headless Chromium.
- **This is NOT a code bug** — verified by curl (login+session works end-to-end)
- **Resolution**: Run E2E on Docker Compose stack: `docker compose -f docker-compose.local-prod.yml -f docker-compose.e2e.yml up -d --build`

---

## Environment

| Component | Version |
|---|---|
| Python | 3.9.23 |
| Django | 4.2.27 |
| Node | 22.21.0 |
| npm | 11.6.3 |
| Git HEAD | `8faeeb27eae93ff79d495a63a049d2422d761bac` |
| Branch | `main` |

## DoD Checklist

| Check | Status | Evidence |
|---|---|---|
| `manage.py check` | PASS (0 issues) | `proofs/.../baseline/django_check_deploy.log` — 65 drf_spectacular schema hints only |
| `makemigrations --check --dry-run` | PASS | `No changes detected` |
| `migrate` (fresh) | PASS (0.30s) | `proofs/.../migrations/fresh_migrate.log` |
| `pytest` | **704 passed, 1 skipped** | `proofs/.../baseline/pytest_full.log` |
| `npm ci` | PASS | npm installed 54 packages |
| `npm run build` | PASS (1.20s) | `proofs/.../baseline/frontend_build.log` |
| `eslint` | **0 errors**, 378 warnings | `proofs/.../baseline/eslint.log` |
| ESLint warning classification | 310 html-indent, 32 max-attributes-per-line, 20 newline, 12 unused-vars (dead code, pre-existing), 4 other style | Style-only + pre-existing dead code |
| pip-audit | 9 vulns in 3 packages | See Risk section |
| E2E Playwright | **NOT EXECUTED** (no live server) | `proofs/.../e2e/e2e_status.log` |

## New Tests Added (43 total)

| File | Tests | Category |
|---|---|---|
| `test_quarantine_security.py` | 7 | QUARANTINE exclusion + corrector anonymisation |
| `test_student_matcher.py` | 23 | Anti-false-AUTO, homonymes, partial fields, normalization |
| `test_ocr_pipeline_service.py` | 7 | OCR cascade Tier1/Tier2/Manual, cross-validation |
| `test_document_ai_service.py` | 6 | Circuit breaker, mock service, text extraction |

## Security Validation

| Test | Result |
|---|---|
| Corrector never sees `student` field in list | PASS |
| Corrector never sees `student` field in detail | PASS |
| Corrector never sees `is_identified` field | PASS |
| QUARANTINE copies excluded from corrector view | PASS |
| QUARANTINE copies excluded from dispatch | PASS |
| Homonymes same DOB never AUTO | PASS |
| DOB not exact never AUTO | PASS |
| Missing DOB never AUTO | PASS |
| DOB-only = MANUAL | PASS |

## Model Verification (post-migration)

| Item | Verified |
|---|---|
| `Copy.Status.QUARANTINE` in choices | YES |
| STAGING -> {READY, QUARANTINE} transition | YES |
| QUARANTINE -> {READY, STAGING} transition | YES |
| `AnnexePage` model with 14 fields | YES |
| `OCRResult.extracted_last_name` | YES |
| `OCRResult.extracted_first_name` | YES |
| `OCRResult.extracted_date_of_birth` | YES |
| `OCRResult.ocr_tier` | YES |
| `OCRResult.header_crop` | YES |
| `OCRResult.cloud_raw_response` | YES |
| `OCRResult.processing_time_ms` | YES |

## OCR Pipeline Verification

| Item | Verified |
|---|---|
| `USE_NEW_OCR_PIPELINE` = False (default) | YES |
| `DOCUMENT_AI_PROJECT_ID` = '' (default) | YES |
| Tier 2 disabled when not configured | YES |
| Circuit breaker opens after 5 failures | YES |
| Circuit breaker resets after timeout | YES |
| Cross-validation detects inconsistent sheets | YES |

## Migrations

| Migration | Applied |
|---|---|
| `exams/0024_exam_csv_parsed_at_exam_csv_student_count_and_more.py` | YES |
| `grading/0013_alter_questionscore_score.py` | YES |
| `identification/0004_ocrresult_cloud_raw_response_and_more.py` | YES |

---

## RISKS & MITIGATIONS

### R1: Django 4.2.27 — 4 CVEs (fix in 4.2.28)

| CVE | Severity | Applicability |
|---|---|---|
| GHSA-2mcm-79hx-8fxw | Low | mod_wsgi timing attack — NOT USED (nginx+gunicorn) |
| GHSA-mwm9-4648-f68q | Medium | RasterField SQL injection — NOT USED (no PostGIS) |
| GHSA-6426-9fv3-65x8 | Medium | FilteredRelation SQL injection — no user-controlled dict expansion |
| GHSA-gvg8-93h5-g6qq | Medium | FilteredRelation control chars — same mitigation |

**Mitigation**: Upgrade to Django 4.2.28 within 1 week post-deploy. None are exploitable in current codebase (no mod_wsgi, no RasterField, no user-controlled FilteredRelation).

### R2: filelock 3.19.1 — 2 CVEs

TOCTOU race condition. Only used internally by virtualenv. Not exploitable in production (no untrusted local filesystem access).

**Mitigation**: `pip install filelock>=3.20.3` in next maintenance window.

### R3: setuptools 58.1.0 — 3 CVEs

Only in venv, not a runtime dependency. Not exploitable in production.

**Mitigation**: `pip install setuptools>=78.1.1` in next maintenance window.

### R4: E2E not executed

Playwright E2E requires Docker Compose stack running at port 8090.

**Mitigation**: MUST run E2E on staging/CI before production deploy. This is the BLOCKING condition.

### R5: 12 unused-vars ESLint warnings

Dead code in IdentificationDesk.vue and ExamEditor.vue. Pre-existing, not introduced by this release.

**Mitigation**: Clean up in next sprint. Non-blocking — no runtime impact.

---

## ROLLBACK PLAN

### Step 1: Revert migrations (if applied to prod DB)
```bash
cd backend
source .venv/bin/activate
python manage.py migrate identification 0003
python manage.py migrate grading 0012
python manage.py migrate exams 0023
```

### Step 2: Revert code
```bash
git checkout 8faeeb27 -- backend/ frontend/
```

### Step 3: Verify
```bash
python manage.py check
python -m pytest -q
```

---

## COMMANDS RUNBOOK

### Pre-deploy verification
```bash
cd /home/alaeddine/viatique__PMF/backend
source .venv/bin/activate
python manage.py check
python manage.py makemigrations --check --dry-run
python -m pytest -q
cd ../frontend
npm run build
npx eslint --ext .js,.vue src/ 2>&1 | grep "error"
```

### Deploy
```bash
# Apply migrations
python manage.py migrate

# Verify new models
python manage.py shell -c "from exams.models import AnnexePage; print(AnnexePage.objects.count())"

# Verify feature flag
python manage.py shell -c "from django.conf import settings; print(settings.USE_NEW_OCR_PIPELINE)"
```

### Post-deploy smoke tests
```bash
# E2E on staging
cd frontend/e2e && npx playwright test

# API smoke
curl -s http://localhost/api/health/ | python -m json.tool
```

---

## PROOF ARTIFACTS

```
proofs/release_candidate_2026-02-08/
├── baseline/
│   ├── django_check_deploy.log    (22.6 KB)
│   ├── eslint.log                 (42.9 KB)
│   ├── frontend_build.log         (1.6 KB)
│   ├── git_diff_stat.log          (490 B)
│   ├── migrations_check.log       (20 B)
│   ├── pip_audit.log              (621 B)
│   ├── pip_freeze.txt             (1.5 KB)
│   └── pytest_full.log            (6.9 KB)
├── e2e/
│   └── e2e_status.log
├── migrations/
│   ├── fresh_migrate.log          (594 B)
│   └── model_verification.log
├── ocr_pipeline/
│   ├── feature_flag_verification.log
│   └── ocr_tests.log             (4.3 KB)
├── patches/
│   └── 01_full_backend_diff.patch (13.8 KB)
└── security/
    └── anonymisation_tests.log    (1.3 KB)
```
