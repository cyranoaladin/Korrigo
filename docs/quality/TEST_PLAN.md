# Test Plan: "Swiss Clock" Quality Bar

## 1. Test Pyramid Strategy

We allow no flakes, no skipped tests without strict justification, and no warnings allowed in CI.

### A. Unit Tests (Base)
**Goal**: Isolation, Speed, Determinism.
- **Scope**: Services (`GradingService`), Serializers, Models, Utilities.
- **Mocks**: Heavy use of mocks for External Systems (Filesystem, PDF Engine).
- **Location**: `backend/*/tests/test_unit_*.py`
- **Cmd**: `pytest -m unit`

### B. Integration Tests (Middle)
**Goal**: Verified interactions with "Real" components.
- **Scope**: API Views, DB Transactions, FileSystem Writes (via TempDir), PDF Engine (Real PyMuPDF).
- **Mocks**: Minimal. Allowed for S3/Email but NOT for Local FS/DB in this layer.
- **Location**: `backend/*/tests/test_integration_*.py` or `test_api_*.py`
- **Cmd**: `pytest -m api`

### C. Contract Tests
**Goal**: API Stability.
- **Scope**: Schema drift checks.
- **Tool**: `drf-spectacular` generation check.

### D. E2E Tests (Top)
**Goal**: User Journey Verification.
- **Scope**: Full Stack (Browser -> Nginx -> Django -> DB).
- **Tool**: Playwright.
- **Scenarios**:
  - Teacher Import -> Grade -> Finalize.
  - Student security blocks.
  - Concurrent locking.

## 2. Coverage Requirements
- **Global**: >80%
- **Critical Modules** (`grading`, `exams`): >85%

## 3. Strict Policies
- `pytest -W error`: Treat warnings as errors.
- `0 skip`: Skips are technical debt. Fix or delete.
