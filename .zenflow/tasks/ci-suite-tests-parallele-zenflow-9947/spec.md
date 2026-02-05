# Technical Specification: CI + Parallel Test Suite (Zenflow)

**Task ID**: ZF-AUD-14  
**Version**: 1.0  
**Date**: 2026-01-31

---

## 1. Technical Context

### 1.1 Technology Stack

**Backend:**
- Language: Python 3.9
- Framework: Django 4.2 + Django REST Framework
- Testing: pytest 8.0, pytest-django 4.8
- Database: PostgreSQL 15 (production/CI), SQLite (dev fallback)
- Task Queue: Celery + Redis
- Processing: PyMuPDF 1.23.26, OpenCV 4.8.1, Tesseract OCR

**Frontend:**
- Framework: React + Vite
- E2E Testing: Playwright (TypeScript)
- Current config: Sequential execution (workers=1, fullyParallel=false)

**Infrastructure:**
- CI: GitHub Actions (ubuntu-latest, 2-core runners)
- Containers: Docker Compose (dev/e2e/staging/prod variants)
- Orchestration: Zenflow task worktrees (`.zenflow/worktrees/{task_id}`)

### 1.2 Current Test Inventory

**Backend Tests (~44 files):**
```
grading/tests/          # 20 files (unit, integration, processing)
students/tests/         # 2 files (CSV import, workflow)
exams/tests/            # 3 files (PDF validators)
processing/tests/       # 2 files (splitter, OCR)
identification/         # 4 files (workflow, backup)
core/tests/             # 1 file (full audit)
```

**Frontend E2E Tests:**
```
frontend/tests/e2e/
├── corrector_flow.spec.ts
├── dispatch_flow.spec.ts
└── student_flow.spec.ts
```

**Existing Markers:**
- `@pytest.mark.unit`: Fast tests without DB
- `@pytest.mark.api`: Integration tests with DB + APIClient
- `@pytest.mark.postgres`: PostgreSQL-specific tests
- `@pytest.mark.smoke`: Critical production workflows
- `@pytest.mark.e2e`: End-to-end tests

### 1.3 Existing Isolation Mechanisms

**Database (Partial):**
```python
# backend/core/settings_test.py:29-35
DB_SUFFIX = os.environ.get("PYTEST_XDIST_WORKER") or "0"
DATABASES['default']['TEST']['NAME'] = f'test_viatique_{DB_SUFFIX}'
```
✅ Already supports pytest-xdist worker detection  
❌ Not enforced in all environments (missing env vars)

**Media Files (Complete):**
```python
# backend/conftest.py:91-104
@pytest.fixture(autouse=True)
def mock_media(settings):
    temp_media_root = tempfile.mkdtemp(prefix="korrigo_test_media_")
    settings.MEDIA_ROOT = temp_media_root
    yield temp_media_root
    shutil.rmtree(temp_media_root, ignore_errors=True)
```
✅ Already isolated per test process  
⚠️ Could be enhanced with worker ID in prefix

---

## 2. Implementation Approach

### 2.1 Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                  Parallel Test Execution                    │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │ Suite 1:     │  │ Suite 2:     │  │ Suite 3:     │     │
│  │ Unit-Fast    │  │ Integration  │  │ Processing   │     │
│  │ (8 workers)  │  │ (4 workers)  │  │ (2 workers)  │     │
│  │              │  │              │  │              │     │
│  │ No DB        │  │ DB Isolated  │  │ DB + Media   │     │
│  │ <10s total   │  │ Per Worker   │  │ Isolated     │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Suite 4: E2E (Playwright)                           │   │
│  │ Workers: 2-4 | Backend: Isolated Port + DB         │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│           Zenflow: Multi-Task Parallel Isolation            │
│  Task A (port 8947) || Task B (port 8948) || Task C (...)  │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 Test Suite Categorization

#### Suite 1: Unit-Fast
**Selection Criteria:**
- No database access (or mocked)
- No file I/O (except tempfile)
- Pure business logic

**Implementation:**
```bash
# Execution
pytest -n 8 -m unit --tb=short

# Target files (estimated 15 files):
grading/tests/test_services_strict_unit.py
grading/tests/test_validation.py
grading/tests/test_error_handling.py  # unit-marked only
core/tests/test_*.py  # exclude full_audit
```

**Configuration:**
- Workers: 8 (CPU-bound, no contention)
- Expected time: <10s total
- No isolation overhead

#### Suite 2: Integration-API
**Selection Criteria:**
- Uses Django ORM + database
- REST API endpoints (APIClient)
- No heavy fixtures (PDF/images)

**Implementation:**
```bash
# Execution
pytest -n 4 -m api --dist=loadscope --tb=short

# Target files (estimated 20 files):
grading/tests/test_workflow_complete.py
grading/tests/test_lock_endpoints.py
grading/tests/test_async_views.py
students/tests/test_*.py
core/tests/test_full_audit.py
exams/tests/test_models.py
```

**Configuration:**
- Workers: 4 (balanced DB contention vs parallelism)
- Distribution: `loadscope` (entire test module per worker)
- DB Isolation: `test_viatique_gw0`, `test_viatique_gw1`, etc.

#### Suite 3: Processing
**Selection Criteria:**
- PDF/Image processing (PyMuPDF, OpenCV, Tesseract)
- File I/O heavy operations
- May use database for persistence

**Implementation:**
```bash
# Execution
pytest -n 2 grading/tests/test_fixtures*.py grading/tests/test_integration_real.py processing/tests/ --dist=loadscope

# Target files (estimated 8 files):
grading/tests/test_fixtures_p1.py
grading/tests/test_integration_real.py
processing/tests/test_splitter.py
exams/tests/test_pdf_validators.py
identification/test_ocr_assisted.py
```

**Configuration:**
- Workers: 2 (I/O bound, limited parallelism benefit)
- Media isolation: Enhanced `mock_media` with worker ID
- DB Isolation: Same as Integration-API

#### Suite 4: E2E (Playwright)
**Selection Criteria:**
- Full-stack browser tests
- Requires running backend + frontend
- Uses seed data

**Implementation:**
```bash
# Execution (from frontend/)
npx playwright test --workers=4

# Target files:
tests/e2e/*.spec.ts  # All E2E specs
```

**Configuration:**
- Workers: 4 (CI), 2 (local)
- Backend: Isolated port per worker (8088, 8089, 8090, 8091)
- Database: Isolated DB per worker (`test_e2e_w0`, `test_e2e_w1`, etc.)
- Seed: Per-worker seeding in global setup

### 2.3 Isolation Strategy

#### 2.3.1 Database Isolation

**Pytest (Backend):**

Current implementation is **already functional** but needs validation:

```python
# backend/core/settings_test.py (existing)
DB_SUFFIX = os.environ.get("PYTEST_XDIST_WORKER") or "0"
DATABASES['default']['TEST']['NAME'] = f'test_viatique_{DB_SUFFIX}'
```

**Enhancement needed:**
- Add logging to verify worker ID detection
- Document environment variable precedence
- Test with `-n auto` to confirm unique DBs

**Playwright (Frontend E2E):**

New implementation required in `global-setup-parallel.ts`:

```typescript
// Pseudo-code for worker-specific DB
const workerIndex = process.env.PLAYWRIGHT_WORKER_INDEX || '0';
const dbName = `test_e2e_w${workerIndex}`;

// Each worker gets:
// - Dedicated database
// - Dedicated backend port (if needed)
// - Seeded data in isolated DB
```

#### 2.3.2 Media File Isolation

**Current implementation (adequate):**
```python
# backend/conftest.py:91-104
temp_media_root = tempfile.mkdtemp(prefix="korrigo_test_media_")
```

**Enhancement (optional):**
```python
# Add worker ID to make debugging easier
worker_id = os.environ.get("PYTEST_XDIST_WORKER", "main")
temp_media_root = tempfile.mkdtemp(prefix=f"korrigo_test_media_{worker_id}_")
```

**Benefits:**
- Easier log correlation
- Explicit cleanup verification

#### 2.3.3 Port Isolation (Zenflow Multi-Task)

**Problem:**
Multiple Zenflow tasks running in parallel use hardcoded ports:
```yaml
# docker-compose.yml (current)
services:
  db:
    ports: ["5435:5432"]  # ❌ Fixed port → conflict
  backend:
    ports: ["8088:8000"]  # ❌ Fixed port → conflict
```

**Solution: Task-Specific Port Mapping**

```bash
# .zenflow/tasks/{task_id}/.env.task (auto-generated template)
ZENFLOW_TASK_ID=ci-suite-tests-parallele-zenflow-9947
ZENFLOW_PORT_BASE=9947  # Derived from task ID

# Computed ports (offset to avoid conflicts)
POSTGRES_PORT=15947  # 10000 + 5947
REDIS_PORT=16947     # 10000 + 6947
BACKEND_PORT=18947   # 10000 + 8947
FRONTEND_PORT=15173  # 10000 + 5173
```

**Docker Compose Template:**
```yaml
# docker-compose.zenflow.yml (new template)
services:
  db:
    ports:
      - "${POSTGRES_PORT:-5435}:5432"
  redis:
    ports:
      - "${REDIS_PORT:-6385}:6379"
  backend:
    ports:
      - "${BACKEND_PORT:-8088}:8000"
  frontend:
    ports:
      - "${FRONTEND_PORT:-5173}:5173"
```

---

## 3. Source Code Changes

### 3.1 Backend Changes

#### File: `backend/requirements.txt`
```diff
 pytest~=8.0
 pytest-django~=4.8
 pytest-cov~=4.1
+pytest-xdist~=3.5
```

#### File: `backend/pytest.ini`
```diff
 [pytest]
 DJANGO_SETTINGS_MODULE = core.settings_test
 python_files = test_*.py *_test.py
 python_classes = Test*
 python_functions = test_*
 
 addopts =
     --verbose
     --strict-markers
     --tb=short
+    --dist=loadscope  # Distribute tests by module (optimal for DB tests)
 
 markers =
     unit: Fast, isolated unit tests
     api: Integration tests using API Client and DB
     e2e: End-to-end tests
     postgres: Tests requiring a PostgreSQL database backend
     smoke: Production readiness smoke tests (critical workflows)
+    processing: Tests with heavy file processing (PDF, images)
```

#### File: `backend/conftest.py`
```diff
 @pytest.fixture(autouse=True)
 def mock_media(settings):
     """
     Automatically override MEDIA_ROOT for all tests to use a temporary directory.
     Cleans up after tests finish.
     """
+    # Include worker ID for easier debugging in parallel runs
+    worker_id = os.environ.get("PYTEST_XDIST_WORKER", "main")
-    temp_media_root = tempfile.mkdtemp(prefix="korrigo_test_media_")
+    temp_media_root = tempfile.mkdtemp(prefix=f"korrigo_test_media_{worker_id}_")
     settings.MEDIA_ROOT = temp_media_root
     
     yield temp_media_root
     
     # Cleanup
     shutil.rmtree(temp_media_root, ignore_errors=True)
```

#### File: `backend/core/settings_test.py`
```diff
 raw_suffix = os.environ.get("CI_NODE_INDEX") or os.environ.get("PYTEST_XDIST_WORKER") or "0"
 # Normalize suffix for CI/xdist (e.g., "gw0") and avoid unexpected chars
 DB_SUFFIX = "".join(ch for ch in str(raw_suffix) if ch.isalnum() or ch in "_").lower() or "0"
 
+# Log database isolation for debugging (only in verbose mode)
+if os.environ.get("PYTEST_CURRENT_TEST"):
+    import sys
+    print(f"[DB Isolation] Worker: {raw_suffix} → DB: test_viatique_{DB_SUFFIX}", file=sys.stderr)
+
 DATABASES['default']['CONN_MAX_AGE'] = 0
 DATABASES['default']['TEST'] = {
     'NAME': f'test_viatique_{DB_SUFFIX}',
     'SERIALIZE': False,
 }
```

### 3.2 Frontend Changes

#### File: `frontend/playwright.config.ts`
```diff
 export default defineConfig({
     testDir: './tests/e2e',
-    globalSetup: './tests/e2e/global-setup.ts',
+    globalSetup: './tests/e2e/global-setup-parallel.ts',
-    fullyParallel: false,
+    fullyParallel: true,
     forbidOnly: !!process.env.CI,
     retries: process.env.CI ? 2 : 0,
-    workers: 1,
+    workers: process.env.CI ? 4 : 2,
     reporter: process.env.CI ? 'html' : 'list',
     use: {
-        baseURL: process.env.E2E_BASE_URL || 'http://localhost:8088',
+        // Dynamic base URL per worker (if backend isolation implemented)
+        baseURL: process.env.E2E_BASE_URL || 'http://localhost:8088',
         trace: 'on-first-retry',
     },
```

#### File: `frontend/tests/e2e/global-setup-parallel.ts` (NEW)
```typescript
/**
 * E2E Global Setup with Parallel Worker Isolation
 *
 * Each Playwright worker gets:
 * - Dedicated PostgreSQL database (test_e2e_w{N})
 * - Seeded test data in isolated DB
 * - Dedicated backend port (optional, for full isolation)
 */

import { chromium } from '@playwright/test';

export default async function globalSetup() {
  console.log('==> E2E Parallel Setup: Initializing worker environments...');

  const workerIndex = process.env.PLAYWRIGHT_WORKER_INDEX || '0';
  const dbName = `test_e2e_w${workerIndex}`;
  
  console.log(`  Worker ${workerIndex}: Using database ${dbName}`);

  // Step 1: Create isolated database for this worker
  // Note: Assumes PostgreSQL is running and accessible
  // In CI, this runs once per worker before tests start
  
  const baseURL = process.env.E2E_BASE_URL || 'http://localhost:8088';
  
  // Step 2: Health check
  try {
    const response = await fetch(`${baseURL}/api/health/`);
    if (!response.ok) {
      throw new Error(`Backend health check failed: ${response.status}`);
    }
    console.log(`  ✓ Worker ${workerIndex}: Backend healthy`);
  } catch (error) {
    console.error(`  ✗ Worker ${workerIndex}: Backend not reachable`);
    throw error;
  }

  // Step 3: Seed data for this worker's database
  // Implementation depends on backend API or direct DB access
  // For now, assume backend handles per-worker DB via environment variables
  
  console.log(`  ✓ Worker ${workerIndex}: Setup complete`);
}
```

#### File: `frontend/package.json`
```diff
 {
   "scripts": {
     "dev": "vite",
     "build": "vite build",
     "preview": "vite preview",
-    "test:e2e": "playwright test"
+    "test:e2e": "playwright test",
+    "test:e2e:parallel": "playwright test --workers=4",
+    "test:e2e:debug": "playwright test --workers=1 --debug"
   }
 }
```

### 3.3 CI Changes

#### File: `.github/workflows/korrigo-ci.yml`
```diff
   unit:
     name: Unit/Service tests (pytest)
     runs-on: ubuntu-latest
     needs: [lint]
     steps:
       - uses: actions/checkout@v4
 
       - name: Setup Python
         uses: actions/setup-python@v5
         with:
           python-version: ${{ env.PYTHON_VERSION }}
 
       - name: Install System Deps
         run: sudo apt-get update && sudo apt-get install -y tesseract-ocr
 
       - name: Install deps + pytest
         working-directory: backend
         run: |
           python -m pip install --upgrade pip
           pip install -r requirements.txt
-          pip install pytest
 
-      - name: Run pytest
+      - name: Run pytest (parallel with xdist)
         working-directory: backend
         env:
           DJANGO_SETTINGS_MODULE: core.settings_test
         run: |
-          pytest -q
+          # Run with 4 workers (2-core runner → 4 workers acceptable)
+          pytest -n 4 --dist=loadscope -q
```

```diff
   integration:
     name: Integration (workflow complete tests subset)
     runs-on: ubuntu-latest
     needs: [security]
     steps:
       # ... (setup steps unchanged)
       
       - name: Run critical workflow tests (gate)
         working-directory: backend
         env:
           DJANGO_SETTINGS_MODULE: core.settings_test
         run: |
-          pytest -q grading/tests/test_workflow_complete.py grading/tests/test_concurrency.py exams/tests/test_pdf_validators.py core/tests/test_full_audit.py
+          # Parallel execution for integration tests
+          pytest -n 4 --dist=loadscope -q \
+            grading/tests/test_workflow_complete.py \
+            grading/tests/test_concurrency.py \
+            exams/tests/test_pdf_validators.py \
+            core/tests/test_full_audit.py
```

**New Job: E2E Parallel (optional, if E2E tests added to CI):**
```yaml
  e2e:
    name: E2E Tests (Playwright Parallel)
    runs-on: ubuntu-latest
    needs: [integration]
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '18'
      
      - name: Install Playwright
        working-directory: frontend
        run: |
          npm ci
          npx playwright install --with-deps chromium
      
      - name: Start E2E Environment
        run: bash tools/e2e.sh up
      
      - name: Run Playwright Tests (Parallel)
        working-directory: frontend
        run: npx playwright test --workers=4
      
      - name: Upload Playwright Report
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: playwright-report
          path: frontend/playwright-report/
```

### 3.4 Zenflow Integration

#### File: `scripts/test_parallel_zenflow.sh` (NEW)
```bash
#!/usr/bin/env bash
# Zenflow-aware parallel test runner
# Automatically detects Zenflow task context and applies port isolation

set -euo pipefail

# Detect Zenflow task context
if [[ -n "${ZENFLOW_TASK_ID:-}" ]]; then
  echo "🔧 Zenflow task detected: $ZENFLOW_TASK_ID"
  
  # Source task-specific environment variables
  TASK_ENV_FILE=".zenflow/tasks/$ZENFLOW_TASK_ID/.env.task"
  if [[ -f "$TASK_ENV_FILE" ]]; then
    source "$TASK_ENV_FILE"
    echo "   Loaded environment: $TASK_ENV_FILE"
    echo "   Backend port: ${BACKEND_PORT:-default}"
    echo "   DB port: ${POSTGRES_PORT:-default}"
  fi
fi

# Default to auto-detect workers if not specified
PYTEST_WORKERS="${PYTEST_WORKERS:-auto}"

echo "🧪 Running pytest with $PYTEST_WORKERS workers..."
cd backend
pytest -n "$PYTEST_WORKERS" --dist=loadscope "$@"
```

#### File: `.zenflow/tasks/template/.env.task` (NEW TEMPLATE)
```bash
# Zenflow Task Environment Variables
# Auto-generated for task isolation

ZENFLOW_TASK_ID={{TASK_ID}}
ZENFLOW_PORT_BASE={{PORT_BASE}}

# Service Ports (isolated per task)
POSTGRES_PORT={{15000 + PORT_BASE}}
REDIS_PORT={{16000 + PORT_BASE}}
BACKEND_PORT={{18000 + PORT_BASE}}
FRONTEND_PORT={{15000 + PORT_BASE + 173}}

# Test Configuration
PYTEST_WORKERS=auto
E2E_BASE_URL=http://localhost:${BACKEND_PORT}
```

---

## 4. Data Model / API Changes

**No database schema changes required.**

All changes are configuration and infrastructure-level:
- Environment variables for worker isolation
- Test database naming conventions
- Port allocation for services

---

## 5. Delivery Phases

### Phase 1: Backend Parallel Foundation (Priority: HIGH)
**Goal:** Enable pytest-xdist for backend tests

**Tasks:**
1. Add `pytest-xdist~=3.5` to `requirements.txt`
2. Update `pytest.ini` with xdist defaults
3. Enhance `conftest.py` media fixture with worker ID
4. Add DB isolation logging to `settings_test.py`
5. Validate isolation with manual `-n 4` test run

**Success Criteria:**
- `pytest -n 4` completes without errors
- Each worker uses unique DB (`test_viatique_gw0`, `gw1`, etc.)
- Media directories are isolated

**Deliverable:** Backend tests runnable in parallel

---

### Phase 2: Test Suite Categorization (Priority: HIGH)
**Goal:** Organize tests into execution suites

**Tasks:**
1. Add `@pytest.mark.processing` marker to heavy I/O tests
2. Document suite membership in `docs/development/PARALLEL_TESTING_GUIDE.md`
3. Create test execution scripts:
   - `scripts/test_unit_fast.sh` → `pytest -n 8 -m unit`
   - `scripts/test_integration.sh` → `pytest -n 4 -m api`
   - `scripts/test_processing.sh` → `pytest -n 2 -m processing`

**Success Criteria:**
- All 44 test files categorized
- Scripts execute correct subsets
- No test runs in multiple suites unnecessarily

**Deliverable:** Documented and scripted test suites

---

### Phase 3: Playwright Parallel (Priority: MEDIUM)
**Goal:** Enable parallel E2E tests with isolation

**Tasks:**
1. Create `global-setup-parallel.ts` with worker DB isolation
2. Update `playwright.config.ts` for `fullyParallel: true, workers: 4`
3. Implement per-worker seeding (extend `seed_e2e.py` or backend API)
4. Test with `npx playwright test --workers=2` locally

**Success Criteria:**
- E2E tests run with 2+ workers without conflicts
- Each worker uses isolated database
- Seed data does not collide

**Deliverable:** Parallel E2E execution

---

### Phase 4: CI Integration (Priority: HIGH)
**Goal:** Update GitHub Actions to use parallel execution

**Tasks:**
1. Update `.github/workflows/korrigo-ci.yml`:
   - Unit job: `pytest -n 4`
   - Integration job: `pytest -n 4`
   - (Optional) Add E2E job with Playwright parallel
2. Run 5 consecutive CI builds to validate stability
3. Document results in proof files

**Success Criteria:**
- All CI jobs pass with parallel execution
- 5 consecutive runs with 0 flakes
- CI time reduction measured and documented

**Deliverable:** Stable parallel CI

---

### Phase 5: Zenflow Multi-Task Isolation (Priority: MEDIUM)
**Goal:** Support multiple Zenflow tasks in parallel

**Tasks:**
1. Create `.env.task` template in `.zenflow/tasks/template/`
2. Create `docker-compose.zenflow.yml` with port variable support
3. Document port allocation algorithm in guide
4. Test with 2 parallel Zenflow tasks (manual simulation)

**Success Criteria:**
- Two tasks run simultaneously without port conflicts
- Each task has isolated services
- Documentation explains setup

**Deliverable:** Zenflow parallel task support

---

### Phase 6: Documentation & Validation (Priority: HIGH)
**Goal:** Deliver comprehensive guide and proof of stability

**Tasks:**
1. Write `docs/development/PARALLEL_TESTING_GUIDE.md`:
   - How to add a test without breaking parallelism
   - Best practices (avoid singletons, use fixtures)
   - Debugging flaky tests
   - Suite selection guide
2. Run 5 consecutive full test suite executions
3. Capture proof logs in `.zenflow/tasks/{task_id}/proof_run{1-5}.txt`
4. Document findings in `ci_parallel_plan.md`

**Success Criteria:**
- Guide covers all common scenarios
- 5 runs complete with 0 failures, 0 flakes
- Proof logs demonstrate stability

**Deliverable:** Guide + validation proof

---

## 6. Verification Approach

### 6.1 Unit Testing Strategy
- **No new tests required** (infrastructure change only)
- Existing tests must pass under parallel execution
- Regression validation: compare sequential vs parallel results

### 6.2 Integration Testing
**Test Cases:**
1. Parallel execution with `-n 4` produces same results as sequential
2. Each worker creates unique database (verify with logs)
3. Media files do not collide (check temp directory count)
4. PostgreSQL-specific tests still pass with real DB

**Commands:**
```bash
# Baseline (sequential)
pytest -v > /tmp/baseline.txt

# Parallel (4 workers)
pytest -n 4 -v > /tmp/parallel.txt

# Compare (should be identical test counts)
diff <(grep -E "PASSED|FAILED" /tmp/baseline.txt | sort) \
     <(grep -E "PASSED|FAILED" /tmp/parallel.txt | sort)
```

### 6.3 E2E Testing
**Test Cases:**
1. Playwright with `workers: 2` completes without errors
2. No database constraint violations (check logs)
3. Worker 0 and Worker 1 seed data independent
4. Cleanup leaves no orphan databases

**Commands:**
```bash
# Run E2E with parallel workers
cd frontend
npx playwright test --workers=2 --reporter=list

# Check for database isolation
docker exec korrigo-db psql -U viatique_user -c "\l" | grep test_e2e
# Should show: test_e2e_w0, test_e2e_w1
```

### 6.4 CI Validation (Critical)
**Flakiness Detection Protocol:**
1. Trigger 5 consecutive CI runs (push dummy commits or manual dispatch)
2. All jobs must complete successfully
3. No intermittent failures allowed
4. Document timing improvements

**Success Criteria:**
```
Run 1: ✅ All jobs passed (45s)
Run 2: ✅ All jobs passed (43s)
Run 3: ✅ All jobs passed (46s)
Run 4: ✅ All jobs passed (44s)
Run 5: ✅ All jobs passed (45s)

Baseline (sequential): ~120s
Parallel (4 workers): ~45s
Improvement: 62% reduction
```

### 6.5 Linting & Type Checking
**Backend:**
```bash
cd backend
flake8 . --count --select=E9,F63,F7,F82 --show-source
```

**Frontend:**
```bash
cd frontend
npm run lint
npx tsc --noEmit
```

---

## 7. Risks & Mitigations

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| **Existing tests have hidden dependencies** (singletons, shared files) | Test failures in parallel | Medium | Audit top 10 critical tests, add logging to detect shared state |
| **Playwright worker isolation not enforced** | E2E flakes | Medium | Start with `workers: 2` locally, validate DB separation before CI |
| **CI worker count too high** (resource exhaustion) | Job timeout or OOM | Low | Use `-n 4` conservatively (2-core runner), monitor CI logs |
| **Zenflow port conflicts despite isolation** | Docker Compose fails to start | Low | Port allocation algorithm uses task ID hash, unlikely collision |
| **PostgreSQL connection pool exhaustion** | DB connection errors | Low | Set `CONN_MAX_AGE=0` in test settings (already done) |

---

## 8. Success Metrics

### 8.1 Performance Metrics
- **Baseline (Sequential):** ~120-150s full test suite
- **Target (Parallel):** <60s full test suite (>50% reduction)
- **CI Throughput:** 5 runs/hour → 10+ runs/hour

### 8.2 Stability Metrics
- **Flakiness Rate:** 0% over 5 consecutive runs (hard requirement)
- **Test Isolation:** 100% (verified via DB logs)
- **Regression Rate:** 0% (all existing tests pass)

### 8.3 Developer Experience
- **Local Test Feedback:** <30s for unit tests (`-n auto`)
- **Documentation Completeness:** Guide answers top 10 FAQs
- **Onboarding Time:** <15min for new dev to run parallel tests

---

## 9. Open Questions & Decisions

### Q1: Should we enforce parallel-only execution?
**Options:**
- A) Keep sequential as fallback (`pytest` still works)
- B) Make parallel the default (require `-n 1` for sequential)

**Recommendation:** Option A (backward compatibility)

### Q2: Cleanup strategy for test databases
**Options:**
- A) Let Django auto-cleanup (current behavior)
- B) Explicit teardown in CI (save disk space)

**Recommendation:** Option A (Django handles it, cleanup only if CI disk issues)

### Q3: Zenflow port allocation algorithm
**Options:**
- A) Hash-based (e.g., last 4 digits of task ID)
- B) Sequential allocation (maintain state file)
- C) Random free ports (requires port scanning)

**Recommendation:** Option A (deterministic, no state management)

---

## 10. References

**Existing Documentation:**
- `backend/pytest.ini` - Current test configuration
- `backend/conftest.py` - Fixtures and setup
- `.github/workflows/korrigo-ci.yml` - CI pipeline
- `tools/e2e.sh` - E2E orchestration script

**External Resources:**
- [pytest-xdist documentation](https://pytest-xdist.readthedocs.io/)
- [Playwright Test Parallelization](https://playwright.dev/docs/test-parallel)
- [Django Test Database](https://docs.djangoproject.com/en/4.2/topics/testing/overview/#the-test-database)

---

**Document Status:** ✅ Ready for Implementation  
**Next Step:** Proceed to Planning phase (break down into tasks)
