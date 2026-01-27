# Inventory - Testing & Quality Assurance

**Date**: 2026-01-27  
**Phase**: PHASE 1 - INVENTAIRE  
**Step**: Inventory - Testing & Quality Assurance  
**Status**: ✅ COMPLETE

---

## Executive Summary

### Test Inventory Statistics

| Category | Count | Status |
|----------|-------|--------|
| **Backend Test Files** | 29 | ✅ |
| **Backend Test Functions** | 137 | ✅ |
| **Frontend E2E Test Files** | 3 | ⚠️ Limited |
| **Frontend Unit Tests** | 0 | ❌ None |
| **CI/CD Pipelines** | 1 (GitHub Actions) | ✅ |
| **Coverage Tool** | pytest-cov installed | ⚠️ Not enforced |

### Quality Metrics

- **Backend Test Coverage**: Unknown (no coverage reporting configured)
- **Frontend Test Coverage**: 0% (no unit tests)
- **E2E Coverage**: Partial (admin/teacher flows only, no student portal)
- **CI Test Execution**: Backend only (no frontend E2E in CI)

---

## 1. Backend Testing Infrastructure

### 1.1 Test Configuration

**pytest.ini** (`backend/pytest.ini`):
```ini
[pytest]
DJANGO_SETTINGS_MODULE = core.settings_test
python_files = test_*.py *_test.py
python_classes = Test*
python_functions = test_*

addopts =
    --verbose
    --strict-markers
    --tb=short

markers =
    unit: Fast, isolated unit tests
    api: Integration tests using API Client and DB
    e2e: End-to-end tests

filterwarnings =
    error
    ignore:.*SERIALIZE test database setting is deprecated.*:django.utils.deprecation.RemovedInDjango50Warning
```

**Key Observations**:
- ✅ Strict markers enforced (`--strict-markers`)
- ✅ Warnings treated as errors (`filterwarnings = error`)
- ✅ Single targeted ignore for Django deprecation warning
- ❌ **NO coverage thresholds** (--cov, --cov-report, --cov-fail-under)
- ❌ **NO parallel execution** (no -n flag for pytest-xdist)

**Test Settings** (`backend/core/settings_test.py`):
- ✅ DEBUG=False in tests
- ✅ Faster password hashing (MD5PasswordHasher)
- ✅ CELERY_TASK_ALWAYS_EAGER=True (synchronous tasks)
- ✅ RATELIMIT_ENABLE=False (no Redis needed)
- ✅ Unique test DB per worker (supports parallel if enabled)
- ✅ CONN_MAX_AGE=0 (prevents connection pooling issues)

**conftest.py** (`backend/conftest.py`):
- ✅ Fixtures for authentication: `admin_user`, `teacher_user`, `regular_user`
- ✅ Fixtures for API clients: `authenticated_client`, `teacher_client`
- ✅ Auto-fixture for media mocking (`mock_media`) - uses tempdir
- ✅ Proper cleanup (shutil.rmtree on teardown)

### 1.2 Backend Test Files (29 files, 137 tests)

#### **grading/** (12 files, ~64 tests)
| File | Tests | Category | Critical Path |
|------|-------|----------|---------------|
| `test_concurrency.py` | 2 | Concurrency | ✅ CRITICAL (locking, race conditions) |
| `test_finalize.py` | 6 | API | ✅ CRITICAL (GRADED transition, PDF gen) |
| `test_phase39_hardening.py` | 4 | Integration | ✅ CRITICAL (error handling) |
| `test_workflow.py` | 5 | Integration | ✅ CRITICAL (state transitions) |
| `test_workflow_complete.py` | 3 | E2E | ✅ CRITICAL (full cycle) |
| `test_serializers_strict.py` | 2 | Unit | ⚠️ (validation) |
| `test_fixtures_advanced.py` | 6 | Integration | ⚠️ (fixture quality) |
| `test_integration_real.py` | 3 | Integration | ✅ CRITICAL (API endpoints) |
| `test_validation.py` | 6 | Unit | ✅ CRITICAL (input validation) |
| `test_error_handling.py` | 7 | Unit | ✅ CRITICAL (resilience) |
| `test_anti_loss.py` | 4 | Integration | ✅ CRITICAL (data loss prevention) |
| `test_fixtures_p1.py` | 4 | Unit | ⚠️ (fixture quality) |
| `test_services_strict_unit.py` | 5 | Unit | ✅ CRITICAL (business logic) |

#### **core/** (4 files, ~29 tests)
| File | Tests | Category | Critical Path |
|------|-------|----------|---------------|
| `test_auth_rbac.py` | 8 | Security | ✅ CRITICAL (AuthN/AuthZ) |
| `test_full_audit.py` | 6 | Integration | ✅ CRITICAL (system-wide) |
| `test_rate_limiting.py` | 5 | Security | ✅ CRITICAL (DoS protection) |
| `test_audit_trail.py` | 10 | Integration | ✅ CRITICAL (compliance) |

#### **exams/** (2 files, ~17 tests)
| File | Tests | Category | Critical Path |
|------|-------|----------|---------------|
| `test_pdf_validators.py` | 13 | Security | ✅ CRITICAL (PDF bomb, malformed) |
| `tests.py` | 4 | Unit | ⚠️ (models) |

#### **students/** (2 files, ~8 tests)
| File | Tests | Category | Critical Path |
|------|-------|----------|---------------|
| `test_gate4_flow.py` | 3 | E2E | ✅ CRITICAL (student portal) |
| `test_import_students_csv.py` | 5 | Integration | ✅ CRITICAL (CSV import) |

#### **identification/** (5 files, ~19 tests)
| File | Tests | Category | Critical Path |
|------|-------|----------|---------------|
| `test_e2e_bac_blanc.py` | 3 | E2E | ✅ CRITICAL (full workflow) |
| `test_workflow.py` | 3 | Integration | ✅ CRITICAL (OCR flow) |
| `test_ocr_assisted.py` | 4 | Integration | ✅ CRITICAL (OCR accuracy) |
| `tests.py` | 8 | Unit | ⚠️ (models) |
| `test_backup_restore_full.py` | 1 | Integration | ✅ CRITICAL (disaster recovery) |

#### **processing/** (1 file, ~2 tests)
| File | Tests | Category | Critical Path |
|------|-------|----------|---------------|
| `test_splitter.py` | 2 | Unit | ✅ CRITICAL (PDF split/flatten) |

#### **backend/tests/** (2 files, ~5 tests)
| File | Tests | Category | Critical Path |
|------|-------|----------|---------------|
| `test_api_bac_blanc.py` | 3 | E2E | ✅ CRITICAL (full API workflow) |
| `test_backup_restore.py` | 2 | Integration | ✅ CRITICAL (disaster recovery) |

### 1.3 Test Markers Usage

**Analysis of markers in test files**:
```bash
@pytest.mark.unit: 36 occurrences
@pytest.mark.api: 1 occurrence
@pytest.mark.e2e: 0 occurrences
@pytest.mark.django_db: ~100+ occurrences (most tests)
```

**⚠️ FINDINGS**:
- **Marker underutilization**: Only 37 tests explicitly marked (unit/api), rest unmarked
- **No E2E marker usage**: Despite having E2E tests (test_api_bac_blanc.py, test_gate4_flow.py)
- **Inconsistent categorization**: Cannot reliably filter by test type
- **Impact**: Cannot run `pytest -m unit` or `pytest -m e2e` effectively

### 1.4 Seed Data & Determinism

**E2E Seed Scripts**:
1. **`backend/seed_e2e.py`**: 
   - Creates deterministic users (admin, teacher, teacher2, student_e2e)
   - Creates exam with PDF fixture
   - Imports copies from PDF
   - Sets first copy to READY status
   - ✅ Idempotent (clears existing data first)
   - ✅ Returns JSON with created IDs
   
2. **`backend/scripts/seed_gate4.py`**:
   - Creates Student (ine="123456789")
   - Creates Exam ("Gate 4 Exam")
   - Creates 3 copies in different states:
     - GRADED + owned (should be visible/downloadable)
     - LOCKED + owned (should NOT be visible)
     - GRADED + other student (should NOT be visible)
   - ✅ Tests security boundaries (IDOR protection)
   - ✅ Idempotent (get_or_create)

**✅ Determinism Status**: CONFIRMED
- Seed scripts use fixed values (no random data)
- At least 2 students created (main student + "OTHER")
- Copies in different states: GRADED, LOCKED, other owner
- Matches requirement: "at least 2 students, copies graded/locked/other"

---

## 2. Frontend Testing Infrastructure

### 2.1 Test Configuration

**package.json** (`frontend/package.json`):
```json
{
  "scripts": {
    "lint": "eslint .",
    "typecheck": "vue-tsc --noEmit"
  },
  "devDependencies": {
    "@playwright/test": "^1.57.0",
    "eslint": "^9.39.2",
    "eslint-plugin-vue": "^10.7.0",
    "typescript": "^5.9.3",
    "vue-tsc": "^3.2.2"
  }
}
```

**⚠️ FINDINGS**:
- ❌ **NO unit test framework** (no Vitest, Jest, or similar)
- ❌ **NO unit test script** in package.json
- ✅ Lint and typecheck scripts present
- ✅ Playwright installed for E2E

**playwright.config.ts** (main):
```typescript
export default defineConfig({
    testDir: './tests/e2e',
    globalSetup: './tests/e2e/global-setup.ts',
    fullyParallel: true,
    forbidOnly: !!process.env.CI,
    retries: process.env.CI ? 2 : 0,
    workers: process.env.CI ? 1 : undefined,
    reporter: 'html',
    use: {
        baseURL: 'http://localhost:5173',
        trace: 'on-first-retry',
    },
});
```

**frontend/e2e/playwright.config.ts** (alternative):
```typescript
export default defineConfig({
  testDir: './tests',
  fullyParallel: false,  // Sequential for E2E stability
  retries: process.env.CI ? 2 : 1,
  workers: 1,  // Single worker for deterministic execution
  timeout: 60000,
  globalSetup: path.resolve(__dirname, 'global-setup.ts'),
  use: {
    baseURL: process.env.BASE_URL || 'http://127.0.0.1:8090',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },
});
```

**✅ E2E Configuration Quality**:
- ✅ Single worker (deterministic)
- ✅ Sequential execution (fullyParallel: false)
- ✅ Retries configured (2 in CI, 1 local)
- ✅ Trace on first retry
- ✅ Screenshot/video on failure
- ✅ Global setup for authentication
- ⚠️ **Two configs exist** (main vs e2e subfolder) - potential confusion

### 2.2 Frontend E2E Tests (3 files)

| File | Tests | Coverage | Critical Path |
|------|-------|----------|---------------|
| `admin_flow.spec.ts` | 1 | Admin login → Dashboard → UI checks | ✅ CRITICAL |
| `tests/teacher_flow.spec.ts` | 2 | Admin login → Dashboard (authenticated session) | ⚠️ Named "Admin" but in teacher_flow |
| `tests/example.spec.ts` | ? | Unknown (not examined) | ❌ Example/placeholder |

**⚠️ FINDINGS**:
- **Limited coverage**: Only admin dashboard tested
- **No teacher correction flow**: Lock → Annotate → Autosave → Finalize → PDF
- **No student portal flow**: Login → View copies → Download PDF
- **No identification flow**: Upload → Split → OCR → Merge → Validate
- **Naming inconsistency**: `teacher_flow.spec.ts` tests admin, not teacher
- **Example test not removed**: `example.spec.ts` should be deleted or replaced

**global-setup.ts**:
- ✅ Logs in as admin via API (`/api/login/`)
- ✅ Fetches user data (`/api/me/`)
- ✅ Navigates to dashboard to verify auth works
- ✅ Saves storage state (cookies)
- ✅ Diagnostic logging (console, pageerror)
- ✅ Captures screenshot/HTML on failure

---

## 3. CI/CD Integration

### 3.1 GitHub Actions CI

**Workflow**: `.github/workflows/korrigo-ci.yml`

**Pipeline Stages**:
1. **lint** (Backend only)
   - Flake8 on backend code
   - ❌ No frontend lint
   
2. **unit** (Backend only)
   - Runs `pytest -q` (all tests)
   - ❌ No marker filtering (runs ALL tests, not just unit)
   - ❌ No coverage reporting
   
3. **security** (Backend only)
   - `pip-audit` (dependency vulnerabilities)
   - `bandit` (static analysis)
   - ✅ CRITICAL security checks
   
4. **integration** (Backend subset)
   - Runs specific critical tests:
     - `test_workflow_complete.py`
     - `test_concurrency.py`
     - `test_pdf_validators.py`
     - `test_full_audit.py`
   - ⚠️ Subset only, not all integration tests
   
5. **packaging** (Backend only)
   - Docker build test
   - ✅ Verifies Dockerfile builds

**⚠️ CI GAPS**:
- ❌ **NO frontend lint/typecheck** in CI
- ❌ **NO frontend E2E tests** in CI
- ❌ **NO coverage reporting** in CI
- ❌ **NO coverage thresholds** enforced
- ❌ **Unit stage runs ALL tests** (not just unit), slow and misleading
- ⚠️ Integration stage runs only 4 files (hardcoded subset)

### 3.2 Makefile

**Test Command**: `make test`
```makefile
test:
    @echo "Running Full Test Suite (Unit, Integration, E2E)..."
    docker-compose -f infra/docker/docker-compose.prod.yml exec -T backend pytest
```

**⚠️ FINDINGS**:
- ✅ Runs pytest in Docker (production-like environment)
- ❌ No frontend tests
- ❌ No coverage reporting
- ❌ No arguments (runs all tests, no filtering)

---

## 4. Test Execution Commands

### 4.1 Backend

**All Tests**:
```bash
cd backend
pytest
# or
make test
```

**By Marker** (limited due to underutilization):
```bash
pytest -m unit        # Only 36 tests
pytest -m api         # Only 1 test
pytest -m e2e         # 0 tests
```

**By File/Directory**:
```bash
pytest grading/tests/test_concurrency.py
pytest grading/tests/
pytest core/tests/
```

**With Coverage** (tool installed, not configured):
```bash
pytest --cov=grading --cov=exams --cov=core --cov-report=html
```

**Documented in TEST_PLAN.md**:
```bash
# Unit tests
python -m pytest grading/tests/test_services_strict_unit.py -v

# Integration tests
python -m pytest grading/tests/test_integration_real.py -v

# Concurrency tests
python -m pytest grading/tests/test_concurrency.py -v

# Security tests
python -m pytest exams/tests/test_pdf_validators.py -v
python -m pytest grading/tests/test_error_handling.py -v
```

### 4.2 Frontend

**Lint**:
```bash
cd frontend
npm run lint
```

**Typecheck**:
```bash
npm run typecheck
```

**E2E** (not in package.json, must use npx):
```bash
cd frontend/e2e
npx playwright test
# or from root
cd frontend
npx playwright test --config=e2e/playwright.config.ts
```

**❌ NO UNIT TESTS** (no command available)

### 4.3 Smoke Tests

**Script**: `scripts/smoke.sh`
```bash
# Health check
curl http://localhost:8080/api/health/

# Media access block (security)
curl http://localhost:8080/media/marker.txt  # Should be 403/404
```

**✅ Minimal but effective**: Checks critical production gates

---

## 5. Coverage Analysis

### 5.1 Coverage Tooling

**Installed**: `pytest-cov~=4.1` (in requirements.txt)

**Configured**: ❌ NO
- No `--cov` in pytest.ini addopts
- No `--cov-report` in pytest.ini
- No `--cov-fail-under` threshold
- No coverage reporting in CI
- No `.coveragerc` file

**Documented Goals** (docs/quality/TEST_PLAN.md):
- Global: >80%
- Critical Modules (grading, exams): >85%

**⚠️ REALITY**: 
- **Coverage is measured: NO**
- **Coverage is reported: NO**
- **Coverage is enforced: NO**
- **Goals are aspirational only**

### 5.2 Estimated Coverage by Module

**Based on test file distribution** (not actual coverage):

| Module | Test Files | Test Count | Estimated Coverage |
|--------|------------|------------|-------------------|
| **grading** | 12 | ~64 | ⚠️ Likely >60% (most critical paths tested) |
| **core** | 4 | ~29 | ⚠️ Likely >50% (auth/audit covered) |
| **exams** | 2 | ~17 | ⚠️ Likely >40% (PDF validation covered) |
| **students** | 2 | ~8 | ⚠️ Likely >30% (critical flows only) |
| **identification** | 5 | ~19 | ⚠️ Likely >40% (OCR and workflow) |
| **processing** | 1 | ~2 | ❌ Likely <20% (only splitter tested) |

**⚠️ NOTE**: These are guesses. **Actual coverage measurement required**.

---

## 6. Critical Path Coverage Analysis

### 6.1 Gate 4 (Student Portal) ✅ COVERED

**Test**: `backend/students/tests/test_gate4_flow.py`

**Coverage**:
- ✅ Student login (`POST /api/students/login/`)
- ✅ Student "me" endpoint (`GET /api/students/me/`)
- ✅ List graded copies (`GET /api/students/copies/`)
  - ✅ Only GRADED status visible
  - ✅ Only own copies visible (IDOR protection)
- ✅ Download final PDF (`GET /api/students/copies/{id}/final_pdf/`)
  - ✅ 403 if not owner
  - ✅ 403 if not GRADED

**Seed**: `backend/scripts/seed_gate4.py`
- ✅ Creates 2 students
- ✅ Creates 3 copies: GRADED+owned, LOCKED+owned, GRADED+other
- ✅ Deterministic

**E2E**: ❌ NO PLAYWRIGHT TEST for student portal

### 6.2 Teacher Correction Workflow ✅ MOSTLY COVERED

**Tests**: 
- `backend/grading/tests/test_workflow_complete.py`
- `backend/grading/tests/test_workflow.py`

**Coverage**:
- ✅ Import PDF (`POST /api/exams/{id}/copies/import/`)
- ✅ Transition to READY (manual in test, not via API)
- ✅ Lock copy (`POST /api/grading/copies/{id}/lock/`)
- ✅ Create annotation (`POST /api/grading/copies/{id}/annotations/`)
- ✅ Update annotation (`PATCH /api/grading/copies/{id}/annotations/{id}/`)
- ✅ Delete annotation (`DELETE /api/grading/copies/{id}/annotations/{id}/`)
- ✅ Finalize (`POST /api/grading/copies/{id}/finalize/`)
- ✅ PDF generation (mocked in some tests, real in others)
- ⚠️ Autosave tested implicitly (via annotation CRUD)
- ❌ **NO EXPLICIT AUTOSAVE FAILURE RECOVERY TEST**

**E2E**: ❌ NO PLAYWRIGHT TEST for full teacher flow

### 6.3 Admin Identification Workflow ⚠️ PARTIALLY COVERED

**Tests**:
- `backend/identification/test_workflow.py`
- `backend/identification/test_e2e_bac_blanc.py`
- `backend/identification/test_ocr_assisted.py`

**Coverage**:
- ✅ Upload PDF
- ✅ Split pages
- ⚠️ OCR (tested but accuracy/error cases unclear)
- ⚠️ Merge/validation (tested but edge cases unclear)
- ⚠️ Ready for grading transition
- ❌ **NO MANUAL CORRECTION FLOW** (if OCR fails)
- ❌ **NO BULK IDENTIFICATION TEST**

**E2E**: ⚠️ Playwright test for admin dashboard only (no identification flow)

### 6.4 Export (CSV Pronote) ❌ NO DEDICATED TEST

**Evidence**: No test file named `test_export.py` or similar

**⚠️ CRITICAL GAP**: Export to Pronote is listed as "MOYENNE" priority in TEST_PLAN.md but has no tests

### 6.5 Concurrency (Multi-Teacher) ✅ COVERED

**Test**: `backend/grading/tests/test_concurrency.py`

**Coverage**:
- ✅ Last Write Wins (sequential interleaved updates)
- ✅ Lock acquisition
- ⚠️ **NOT TRUE CONCURRENCY** (SQLite memory DB limitation)
- ⚠️ Comment in test: "True concurrency impossible on SQLite memory DB in this harness"

**⚠️ LIMITATION**: Concurrency tests are sequential simulations, not parallel

---

## 7. Identified Gaps

### 7.1 P0 Gaps (Blocking Production)

❌ **NO COVERAGE ENFORCEMENT**
- Impact: Cannot guarantee code quality
- Risk: Untested code in production
- Fix: Add `--cov-fail-under=80` to pytest.ini

❌ **NO FRONTEND UNIT TESTS**
- Impact: No validation of Vue components, stores, utils
- Risk: UI bugs in production
- Fix: Add Vitest, write component tests

❌ **NO E2E TESTS IN CI**
- Impact: Regressions not caught before deploy
- Risk: Broken UI in production
- Fix: Add Playwright to CI pipeline

❌ **NO EXPORT CSV TEST**
- Impact: Cannot verify Pronote export correctness
- Risk: Incorrect grades exported
- Fix: Write test for CSV generation and format

### 7.2 P1 Gaps (Serious)

⚠️ **MARKER UNDERUTILIZATION**
- Impact: Cannot filter tests by type (unit/integration/e2e)
- Risk: Slow test runs, unclear test purpose
- Fix: Mark all tests consistently

⚠️ **NO REAL CONCURRENCY TESTS**
- Impact: Race conditions may exist
- Risk: Data corruption under load
- Fix: Use PostgreSQL in tests, parallel execution

⚠️ **INCOMPLETE E2E COVERAGE**
- Impact: Critical flows not tested end-to-end
- Risk: Integration bugs in production
- Fix: Add Playwright tests for:
  - Teacher full correction flow
  - Student portal flow
  - Admin identification flow

⚠️ **NO FRONTEND LINT/TYPECHECK IN CI**
- Impact: Type errors not caught before merge
- Risk: Runtime errors in production
- Fix: Add `npm run lint` and `npm run typecheck` to CI

⚠️ **TWO PLAYWRIGHT CONFIGS**
- Impact: Confusion, potential for wrong config
- Risk: Tests run with wrong settings
- Fix: Consolidate to one config

### 7.3 P2 Gaps (Quality/DX)

⚠️ **NO COVERAGE REPORTING**
- Impact: No visibility into test quality
- Fix: Add `--cov-report=html` to CI, publish as artifact

⚠️ **EXAMPLE TEST NOT REMOVED**
- Impact: Clutter, confusion
- Fix: Delete `frontend/e2e/tests/example.spec.ts`

⚠️ **INCONSISTENT TEST NAMING**
- Impact: Confusion (teacher_flow tests admin)
- Fix: Rename files to match content

⚠️ **NO AUTOSAVE FAILURE RECOVERY TEST**
- Impact: Unknown behavior on autosave failure
- Fix: Add explicit test for autosave retry/recovery

---

## 8. Test Coverage Matrix (Critical Paths)

| Workflow | Backend Unit | Backend Integration | Backend E2E | Frontend E2E | Status |
|----------|--------------|---------------------|-------------|--------------|--------|
| **Import PDF** | ✅ | ✅ | ✅ | ❌ | ⚠️ Backend only |
| **Identification** | ✅ | ⚠️ Partial | ⚠️ Partial | ❌ | ⚠️ Gaps exist |
| **Lock Copy** | ✅ | ✅ | ✅ | ❌ | ⚠️ Backend only |
| **Annotate** | ✅ | ✅ | ✅ | ❌ | ⚠️ Backend only |
| **Autosave** | ⚠️ Implicit | ⚠️ Implicit | ❌ | ❌ | ⚠️ Not explicit |
| **Finalize** | ✅ | ✅ | ✅ | ❌ | ⚠️ Backend only |
| **Generate PDF** | ✅ | ✅ | ✅ | ❌ | ⚠️ Backend only |
| **Student Login** | ✅ | ✅ | ✅ | ❌ | ⚠️ Backend only |
| **Student View Copies** | ✅ | ✅ | ✅ | ❌ | ⚠️ Backend only |
| **Student Download PDF** | ✅ | ✅ | ✅ | ❌ | ⚠️ Backend only |
| **Export CSV** | ❌ | ❌ | ❌ | ❌ | ❌ NO TESTS |
| **Concurrency** | ✅ | ⚠️ Simulated | ❌ | ❌ | ⚠️ Not real |
| **Admin Dashboard** | ✅ | ✅ | ❌ | ✅ | ⚠️ UI only |
| **Teacher Dashboard** | ❌ | ❌ | ❌ | ⚠️ Minimal | ⚠️ Gaps |

---

## 9. Canonical E2E Status (per instructions)

**E2E (Playwright)**: 
- **Logic**: Seed scripts are deterministic (fixed data, 2+ students, graded/locked/other states)
- **Execution**: May be flaky on local runner (env-dependent)
- **Reference**: CI/container is the reference environment
- **Config**: retries=2, trace=on-first-retry

**Canonical Formulation**:
> "E2E (Playwright): logic compliant (tests fixed + deterministic seed). Execution may be flaky on local runner; CI/container is the reference environment (retries=2, trace=on-first-retry)."

**Verification**:
- ✅ Seed determinism: CONFIRMED (`seed_e2e.py`, `seed_gate4.py`)
- ✅ 2+ students: CONFIRMED (main student + "OTHER" student)
- ✅ Graded/locked/other states: CONFIRMED (3 copies with different states)
- ⚠️ CI execution: NOT CONFIGURED (E2E not in CI pipeline yet)

---

## 10. Deliverable: Test Coverage Matrix + Gaps Analysis

### Deliverable Summary

**Test Files**: 32 total (29 backend + 3 frontend E2E)

**Test Functions**: 137+ (backend only)

**Test Infrastructure**:
- ✅ pytest configured with strict markers and warnings-as-errors
- ✅ Django test settings optimized (fast hashing, no rate limiting)
- ✅ Fixtures for authentication and media mocking
- ✅ Deterministic seed scripts for E2E
- ✅ GitHub Actions CI with 5 stages
- ✅ Smoke tests for critical production gates
- ❌ NO coverage enforcement
- ❌ NO frontend unit tests
- ❌ NO E2E in CI

**Critical Path Coverage**:
- ✅ Backend: Well covered (unit, integration, E2E)
- ⚠️ Frontend: Minimal (only admin dashboard E2E)
- ❌ Export CSV: No tests
- ⚠️ Concurrency: Simulated, not real

**Priority Gaps**:
1. **P0**: Add coverage enforcement, frontend unit tests, E2E in CI, CSV export tests
2. **P1**: Consistent test markers, real concurrency tests, complete E2E coverage, frontend lint/typecheck in CI
3. **P2**: Coverage reporting, cleanup example tests, autosave recovery tests

---

## 11. Recommended Actions

### Immediate (P0)

1. **Enable coverage enforcement**:
   ```ini
   # backend/pytest.ini
   addopts =
       --verbose
       --strict-markers
       --tb=short
       --cov=grading --cov=exams --cov=core --cov=students --cov=identification --cov=processing
       --cov-report=html
       --cov-report=term-missing
       --cov-fail-under=80
   ```

2. **Add frontend unit test framework**:
   ```bash
   npm install -D vitest @vitest/ui @vue/test-utils
   ```

3. **Add E2E to CI**:
   ```yaml
   # .github/workflows/korrigo-ci.yml
   e2e:
     name: E2E (Playwright)
     runs-on: ubuntu-latest
     steps:
       - run: npx playwright test --config=frontend/e2e/playwright.config.ts
   ```

4. **Write CSV export test**:
   ```python
   # backend/students/tests/test_export_csv.py
   def test_export_csv_pronote_format():
       # Test CSV generation, headers, format, data correctness
       pass
   ```

### Short-term (P1)

1. Mark all tests consistently (unit/api/e2e)
2. Add PostgreSQL to test environment for real concurrency tests
3. Complete E2E coverage (teacher flow, student portal, identification)
4. Add frontend lint/typecheck to CI

### Long-term (P2)

1. Add coverage reporting to CI (HTML artifact)
2. Remove example tests
3. Add autosave failure recovery tests
4. Improve test documentation

---

## Appendix: Test File Inventory (Full List)

### Backend Tests (29 files)

```
backend/students/tests/
├── test_gate4_flow.py (3 tests) ✅ CRITICAL
└── test_import_students_csv.py (5 tests) ✅ CRITICAL

backend/identification/
├── test_e2e_bac_blanc.py (3 tests) ✅ CRITICAL
├── test_workflow.py (3 tests) ✅ CRITICAL
├── test_ocr_assisted.py (4 tests) ✅ CRITICAL
├── tests.py (8 tests)
└── test_backup_restore_full.py (1 test) ✅ CRITICAL

backend/processing/tests/
└── test_splitter.py (2 tests) ✅ CRITICAL

backend/exams/tests/
├── test_pdf_validators.py (13 tests) ✅ CRITICAL
└── tests.py (4 tests)

backend/core/
├── test_auth_rbac.py (8 tests) ✅ CRITICAL
└── tests/
    ├── test_audit_trail.py (10 tests) ✅ CRITICAL
    ├── test_rate_limiting.py (5 tests) ✅ CRITICAL
    └── test_full_audit.py (6 tests) ✅ CRITICAL

backend/grading/tests/
├── test_concurrency.py (2 tests) ✅ CRITICAL
├── test_finalize.py (6 tests) ✅ CRITICAL
├── test_phase39_hardening.py (4 tests) ✅ CRITICAL
├── test_workflow.py (5 tests) ✅ CRITICAL
├── test_workflow_complete.py (3 tests) ✅ CRITICAL
├── test_serializers_strict.py (2 tests)
├── test_fixtures_advanced.py (6 tests)
├── test_integration_real.py (3 tests) ✅ CRITICAL
├── test_validation.py (6 tests) ✅ CRITICAL
├── test_error_handling.py (7 tests) ✅ CRITICAL
├── test_anti_loss.py (4 tests) ✅ CRITICAL
├── test_fixtures_p1.py (4 tests)
└── test_services_strict_unit.py (5 tests) ✅ CRITICAL

backend/tests/
├── test_api_bac_blanc.py (3 tests) ✅ CRITICAL
└── test_backup_restore.py (2 tests) ✅ CRITICAL
```

### Frontend Tests (3 files)

```
frontend/e2e/
├── admin_flow.spec.ts (1 test) ✅ CRITICAL
└── tests/
    ├── teacher_flow.spec.ts (2 tests) ⚠️ Misnamed (tests admin)
    └── example.spec.ts (?) ❌ Should be removed
```

---

**END OF INVENTORY - TESTING & QUALITY ASSURANCE**
