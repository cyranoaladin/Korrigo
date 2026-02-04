# Full SDD workflow

## Configuration
- **Artifacts Path**: {@artifacts_path} → `.zenflow/tasks/{task_id}`

---

## Workflow Steps

### [x] Step: Requirements
<!-- chat-id: 76651acb-4c8b-449e-888a-4ab944cdd95a -->

Create a Product Requirements Document (PRD) based on the feature description.

1. Review existing codebase to understand current architecture and patterns
2. Analyze the feature definition and identify unclear aspects
3. Ask the user for clarifications on aspects that significantly impact scope or user experience
4. Make reasonable decisions for minor details based on context and conventions
5. If user can't clarify, make a decision, state the assumption, and continue

Save the PRD to `{@artifacts_path}/requirements.md`.

### [x] Step: Technical Specification
<!-- chat-id: 1004e8b9-d239-41f1-a797-aee6e3513676 -->

Create a technical specification based on the PRD in `{@artifacts_path}/requirements.md`.

1. Review existing codebase architecture and identify reusable components
2. Define the implementation approach

Save to `{@artifacts_path}/spec.md` with:
- Technical context (language, dependencies)
- Implementation approach referencing existing code patterns
- Source code structure changes
- Data model / API / interface changes
- Delivery phases (incremental, testable milestones)
- Verification approach using project lint/test commands

### [x] Step: Planning
<!-- chat-id: d71c1e20-5d41-49fd-b0dd-3428e0a1b73e -->

Create a detailed implementation plan based on `{@artifacts_path}/spec.md`.

1. Break down the work into concrete tasks
2. Each task should reference relevant contracts and include verification steps
3. Replace the Implementation step below with the planned tasks

Rule of thumb for step size: each step should represent a coherent unit of work (e.g., implement a component, add an API endpoint, write tests for a module). Avoid steps that are too granular (single function) or too broad (entire feature).

If the feature is trivial and doesn't warrant full specification, update this workflow to remove unnecessary steps and explain the reasoning to the user.

Save to `{@artifacts_path}/plan.md`.

---

## Implementation Steps

### [x] Step: Audit Logging for PII and Security Issues
<!-- chat-id: d6c19e8b-cd38-428d-ae0d-edea3dded618 -->

**Objective**: Audit all logging statements across grading modules to identify and remove PII leakage

**Tasks**:
- [x] Audit `grading/` module for PII in logging statements
- [x] Audit `processing/` module for PII in logging statements
- [x] Audit `exams/` module for PII in logging statements
- [x] Audit `identification/` module for PII in logging statements
- [x] Audit `students/` module for PII in logging statements
- [x] Check exception messages for PII (email, name, exam content)
- [x] Verify only user_id logged (not email/username)
- [x] Check all exception handlers have `exc_info=True`

**References**:
- Spec: Section 5, Phase 1 (Audit & Documentation)
- Requirements: REQ-1.1 (PII Removal Audit), REQ-1.3 (Exception Handling)

**Findings**:
- Fixed: `backend/core/views_metrics.py:29,63` - replaced `user.username` with `user.id`
- Fixed: `backend/identification/views.py:99,143` - removed `student_name` from GradingEvent metadata
- All exception handlers have `exc_info=True` where appropriate
- No student names, emails, or passwords found in logging statements

**Verification**:
```bash
# Check for PII patterns in logs
grep -rn "email\|password\|student.*name" backend/grading/ backend/processing/ backend/exams/
# Expected: No matches
# Result: No PII found ✓
```

### [x] Step: Standardize Log Levels
<!-- chat-id: e7ed25e4-c390-4b2b-9d5c-c5dee31a5727 -->

**Objective**: Ensure consistent log level usage across all modules

**Tasks**:
- [x] Review all logger.info(), logger.warning(), logger.error() calls
- [x] Apply standard levels:
  - INFO: Normal workflow (import, lock, finalize)
  - WARNING: Recoverable issues (lock conflicts, retries)
  - ERROR: Failures requiring investigation (PDF errors, OCR failures)
  - CRITICAL: System-level failures (max retries exceeded)
- [x] Update log statements to match standards

**References**:
- Spec: Section 5, Phase 1
- Requirements: REQ-1.2 (Log Levels Standardization)

**Verification**:
Manual code review to ensure levels match workflow severity

### [x] Step: Create Audit Report Documentation
<!-- chat-id: c53c8273-2c6a-41aa-8e99-87593959c6cd -->

**Objective**: Document audit findings and current state of logging/metrics

**Tasks**:
- [x] Create `.zenflow/tasks/observabilite-audit-trail-gradin-826d/audit.md`
- [x] Document current logging state (inventory of loggers)
- [x] Document PII audit results (files checked, findings)
- [x] Document log level compliance
- [x] Document request correlation coverage (Django vs Celery)
- [x] Document metrics coverage (existing vs required)
- [x] Provide recommendations

**References**:
- Spec: Section 3.1, Section 5 Phase 1
- Requirements: REQ-5.1 (Audit Report Structure)

**Findings**:
- Audited 11 files across 5 modules (48 log statements total)
- Identified 5 PII issues (username, file paths) - 91% compliance
- Log levels 100% compliant with standards (INFO/WARNING/ERROR/CRITICAL)
- Request correlation: Django 100%, Celery 0%
- Metrics: HTTP covered, grading-specific metrics missing
- Report: `.zenflow/tasks/observabilite-audit-trail-gradin-826d/audit.md` (394 lines)

**Verification**:
- [x] All sections present in audit.md
- [x] File references include line numbers
- [x] Recommendations are actionable

### [x] Step: Create Incident Response Playbook
<!-- chat-id: d91044f4-1e5c-44a3-a740-dbc4133efde2 -->

**Objective**: Provide operators with diagnostic paths for common production issues

**Tasks**:
- [x] Create `.zenflow/tasks/observabilite-audit-trail-gradin-826d/playbook.md`
- [x] Document Scenario 1: Import Stuck (Celery queue, OCR timeout)
- [x] Document Scenario 2: Finalization Failing (PDF generation errors)
- [x] Document Scenario 3: Lock Conflicts (expired locks, user blocking)
- [x] Document Scenario 4: High Latency (slow queries, timeouts)
- [x] Document Scenario 5: Missing Audit Events (transaction rollback)
- [x] Include for each scenario: Symptoms → Diagnosis → Root Causes → Actions
- [x] Add example queries (log grep, DB queries, Prometheus queries)
- [x] Cross-reference `docs/support/DEPANNAGE.md`

**References**:
- Spec: Section 5 Phase 1
- Requirements: REQ-4.1, REQ-4.2 (Playbook Structure and Scenarios)

**Findings**:
- Created comprehensive 902-line playbook
- All 5 scenarios documented with Symptoms → Diagnosis → Root Causes → Actions
- Extensive executable examples: bash (grep, docker-compose, curl), Python/Django ORM, SQL, Prometheus queries
- Cross-referenced docs/support/DEPANNAGE.md (line 26)
- Added 3 appendices: Useful Queries, Escalation Paths, Monitoring Dashboards
- Included Prometheus alerting rules for automated monitoring

**Verification**:
- [x] All 5 scenarios documented
- [x] Each scenario has all 4 sections
- [x] Example queries are executable

### [x] Step: Create Grading Metrics Module
<!-- chat-id: 658972b2-3f90-4ef1-b13b-9f307754b97b -->

**Objective**: Implement domain-specific Prometheus metrics for grading workflows

**Tasks**:
- [ ] Create `backend/grading/metrics.py`
- [ ] Import registry from `core.prometheus`
- [ ] Define `grading_import_duration_seconds` histogram (labels: status, pages_bucket)
- [ ] Define `grading_finalize_duration_seconds` histogram (labels: status, retry_attempt)
- [ ] Define `grading_ocr_errors_total` counter (labels: error_type)
- [ ] Define `grading_lock_conflicts_total` counter (labels: conflict_type)
- [ ] Define `grading_copies_by_status` gauge (labels: status)
- [ ] Add helper function `_get_pages_bucket(pages)` for bucketing
- [ ] Add context manager `track_import_duration(pages, status)`
- [ ] Add context manager `track_finalize_duration(retry_attempt, status)`

**References**:
- Spec: Section 2.2 (Design Patterns), Section 4.2 (New Prometheus Metrics), Section 5 Phase 2
- Requirements: REQ-2.1 to REQ-2.5

**Verification**:
```bash
# Check metrics module syntax
python -m py_compile backend/grading/metrics.py
```

### [x] Step: Instrument Import and Finalize Services
<!-- chat-id: 6a8bfa15-8eea-44ca-a47d-be921baa5f02 -->

**Objective**: Add metrics recording to PDF import and finalization workflows

**Tasks**:
- [x] Modify `grading/services.py` - `import_pdf()` method
  - Wrap PDF processing with `track_import_duration()` context manager
  - Record import success/failure metrics
  - Add OCR error counter on rasterization exceptions
- [x] Modify `grading/services.py` - `finalize_copy()` method
  - Wrap PDF flattening with `track_finalize_duration()` context manager
  - Record finalize success/failure metrics with retry attempt
- [x] Add lock conflict counter increments
  - On `already_locked` exceptions
  - On `expired` lock errors
  - On `token_mismatch` errors

**References**:
- Spec: Section 3.2 (Modified Files), Section 5 Phase 2
- Requirements: REQ-2.1, REQ-2.2, REQ-2.3, REQ-2.4

**Findings**:
- Added metrics imports to `backend/grading/services.py:18-23`
- Instrumented `import_pdf()` with `track_import_duration` context manager (line 418)
- Added OCR error counter for rasterization exceptions (line 446)
- Instrumented `finalize_copy()` with `track_finalize_duration` context manager (line 599)
- Added lock conflict counters at 11 locations:
  - `_require_active_lock`: missing (77), expired (82), owner_mismatch (86), token_mismatch (92)
  - `acquire_lock`: already_locked (279)
  - `heartbeat_lock`: missing (314), expired (320), owner_mismatch (324), token_mismatch (330)
  - `release_lock`: token_mismatch (351), owner_mismatch (355)
  - `finalize_copy`: already_graded (527), missing (550), expired (556), owner_mismatch (560), token_mismatch (566)
- All metrics wrapped with try/except to ensure failures don't break workflows

**Verification**:
```bash
# Syntax check passed
python -m py_compile backend/grading/services.py
# Exit code: 0 ✓
```

### [x] Step: Add Copy Status Gauge Updater
<!-- chat-id: 9a9959c9-afa0-43a7-a071-56ad7b838775 -->

**Objective**: Track workflow backlog by monitoring copy counts per status

**Tasks**:
- [x] Implement periodic Celery task to update `grading_copies_by_status` gauge
- [x] Query `Copy.objects.values('status').annotate(count=Count('id'))`
- [x] Update gauge for each status (STAGING, READY, LOCKED, etc.)
- [x] Schedule task to run every 60 seconds
- [x] Alternative: Update gauge on state transitions (if preferred)

**References**:
- Spec: Section 5 Phase 2
- Requirements: REQ-2.5 (Copy Status Gauge)

**Findings**:
- Created `update_copy_status_metrics()` task in `backend/grading/tasks.py:190-223`
- Task queries all Copy status counts using Django ORM aggregation
- Updates `grading_copies_by_status` gauge for all statuses (STAGING, READY, LOCKED, GRADING_IN_PROGRESS, GRADING_FAILED, GRADED)
- Configured Celery Beat schedule in `backend/core/celery.py:19-25` to run every 60 seconds
- Error handling ensures metrics failures don't break monitoring

**Verification**:
```bash
# Check gauge updates by scraping metrics
curl http://localhost:8088/metrics | grep grading_copies_by_status
# Syntax check passed
python -m py_compile backend/grading/tasks.py
python -m py_compile backend/core/celery.py
# Exit code: 0 ✓
```

### [x] Step: Add Request Correlation to Celery Tasks
<!-- chat-id: f54ed51e-7ff6-4fe7-9ab0-674b25aea12a -->

**Objective**: Propagate request_id from HTTP requests to Celery tasks for log correlation

**Tasks**:
- [x] Modify `grading/tasks.py` - `async_finalize_copy()` signature
  - Add `request_id=None` parameter
  - Inject `request_id` into all log statements via `extra={'request_id': request_id}`
- [x] Modify `grading/tasks.py` - `async_import_pdf()` signature
  - Add `request_id=None` parameter
  - Inject `request_id` into all log statements via `extra={'request_id': request_id}`
- [x] Add metrics recording in Celery tasks (success/failure)

**References**:
- Spec: Section 2.2 (Request Correlation Pattern), Section 4.1 (Celery Task Signatures), Section 5 Phase 3
- Requirements: REQ-1.4 (Celery Task Correlation)

**Findings**:
- Modified `async_finalize_copy()` signature at line 21: added `request_id=None` parameter
- Modified `async_import_pdf()` signature at line 94: added `request_id=None` parameter
- Updated all logger calls in both tasks (9 total) to include `extra={'request_id': request_id}` when request_id is not None
- Locations updated in `async_finalize_copy`: lines 46-47, 56-57, 65-66, 77-82
- Locations updated in `async_import_pdf`: lines 116-117, 131-132, 138-139, 149-154
- Backward compatibility maintained with `request_id=None` default parameter

**Verification**:
```bash
# Syntax check passed
python -m py_compile backend/grading/tasks.py
# Exit code: 0 ✓
```

### [x] Step: Update Task Dispatch Sites with Request ID
<!-- chat-id: fd61bdb6-8640-4a87-aa18-118aae73caa3 -->

**Objective**: Pass request_id from HTTP requests when dispatching Celery tasks

**Tasks**:
- [x] Audit all calls to `async_finalize_copy.delay()` in codebase
- [x] Audit all calls to `async_import_pdf.delay()` in codebase
- [x] Update calls in `views_async.py` to pass `request_id=request.request_id`
- [x] Update calls in `services.py` to pass `request_id` (extract from thread-local if available)
- [x] Verify RequestIDMiddleware provides `request.request_id`

**References**:
- Spec: Section 3.2 (Modified Files), Section 5 Phase 3
- Requirements: REQ-1.4

**Findings**:
- Audited codebase for `.delay()` and `.apply_async()` calls: **0 matches found**
- Current implementation uses synchronous service calls:
  - `backend/exams/views.py:88` - `GradingService.import_pdf()` (synchronous)
  - `backend/grading/views.py:174` - `GradingService.finalize_copy()` (synchronous)
- Async tasks exist but are never dispatched asynchronously in production code:
  - `async_finalize_copy` at `backend/grading/tasks.py:21` (has `request_id=None` parameter)
  - `async_import_pdf` at `backend/grading/tasks.py:94` (has `request_id=None` parameter)
  - Only called synchronously in tests (test_tasks.py)
- Verified RequestIDMiddleware provides `request.request_id` at `backend/core/middleware/request_id.py:82`
- Thread-local helper `get_current_request_id()` available at line 25-32

**Conclusion**:
No async dispatch sites exist to update. Infrastructure is ready for async task correlation (tasks have `request_id` parameters, middleware provides `request.request_id`), but application currently uses synchronous service calls instead of Celery task dispatches.

**Verification**:
```bash
# Audit for async task dispatches
grep -rn "\.delay\(|\.apply_async" backend/
# Result: 0 matches ✓

# Verify RequestIDMiddleware
grep -n "request.request_id = request_id" backend/core/middleware/request_id.py
# Result: Line 82 found ✓
```

### [ ] Step: Create Audit Event Tests
<!-- chat-id: 19196b23-fdb9-4f91-907c-ead194c025bf -->

**Objective**: Verify GradingEvent creation at key workflow moments

**Tasks**:
- [ ] Create `backend/grading/tests/test_audit_events.py`
- [ ] Implement `test_import_creates_audit_event()`
  - Upload PDF via API
  - Assert IMPORT event created with metadata (filename, pages)
- [ ] Implement `test_create_annotation_creates_audit_event()`
  - Create annotation via API
  - Assert CREATE_ANN event created with metadata (annotation_id, page)
- [ ] Implement `test_finalize_creates_audit_event_success()`
  - Finalize copy successfully
  - Assert FINALIZE event created with metadata (final_score, retries, success=True)
- [ ] Implement `test_finalize_creates_audit_event_failure()`
  - Mock PDF error during finalization
  - Assert FINALIZE event created with metadata (success=False, error details)

**References**:
- Spec: Section 2.2 (Testing Pattern), Section 5 Phase 4
- Requirements: REQ-3.1, REQ-3.2, REQ-3.3

**Verification**:
```bash
pytest backend/grading/tests/test_audit_events.py -v
# Expected: 4/4 tests passed
```

### [ ] Step: Add Metrics Recording Tests

**Objective**: Verify metrics are recorded during workflow operations (optional smoke tests)

**Tasks**:
- [ ] Add `test_import_records_duration_metric()` to `test_audit_events.py`
  - Perform import operation
  - Check `grading_import_duration_seconds` histogram updated
- [ ] Add `test_lock_conflict_records_metric()`
  - Trigger lock conflict scenario
  - Check `grading_lock_conflicts_total` counter incremented

**References**:
- Spec: Section 5 Phase 4
- Requirements: REQ-2.1, REQ-2.4

**Verification**:
```bash
pytest backend/grading/tests/test_audit_events.py::test_import_records_duration_metric -v
```

### [ ] Step: Verify Existing Tests Pass

**Objective**: Ensure no regressions from instrumentation changes

**Tasks**:
- [ ] Run existing workflow tests: `test_workflow_complete.py`
- [ ] Run existing finalize tests: `test_finalize.py`
- [ ] Run full grading test suite
- [ ] Fix any test failures caused by new metrics/logging

**References**:
- Spec: Section 5 Phase 4, Section 6.1 (Unit Tests)

**Verification**:
```bash
pytest backend/grading/tests/ -v
# Expected: All tests pass
```

### [ ] Step: Integration Testing and Verification

**Objective**: Perform end-to-end verification of observability features

**Tasks**:
- [ ] Test 1: Verify no PII in logs
  ```bash
  grep -rn "email\|password\|student.*name" logs/
  # Expected: No matches
  ```
- [ ] Test 2: Verify request correlation
  - Upload PDF via API
  - Check logs for same request_id in HTTP and Celery logs
- [ ] Test 3: Verify metrics scraping
  ```bash
  curl http://localhost:8088/metrics | grep grading_
  # Expected: All 5 grading metrics present
  ```
- [ ] Test 4: Verify GradingEvent creation
  - Perform complete workflow (import → annotate → finalize)
  - Query database for events in correct order
- [ ] Test 5: Verify playbook scenarios
  - Trigger each scenario and follow playbook diagnosis steps
  - Confirm playbook leads to root cause

**References**:
- Spec: Section 6.2 (Integration Tests)

**Verification**:
All 5 integration tests pass with expected outcomes

### [ ] Step: Run Lint and Type Checking

**Objective**: Ensure code quality and type safety

**Tasks**:
- [ ] Determine lint command from project (check README, package.json, or pyproject.toml)
- [ ] Run linter on modified files
- [ ] Fix any linting issues
- [ ] Run type checker if available (mypy, pyright)
- [ ] Fix any type errors

**Verification**:
```bash
# Example commands (adjust based on project setup)
flake8 backend/grading/
mypy backend/grading/
# Expected: No errors
```

### [ ] Step: Final Documentation Review

**Objective**: Ensure all deliverables are complete and accurate

**Tasks**:
- [ ] Review `audit.md` for completeness and accuracy
- [ ] Review `playbook.md` for clarity and actionability
- [ ] Verify all code changes documented in audit.md
- [ ] Verify all metrics documented in audit.md
- [ ] Ensure playbook cross-references are correct
- [ ] Update plan.md with completion status

**Deliverables**:
- ✅ audit.md (all sections complete)
- ✅ playbook.md (5 scenarios documented)
- ✅ grading/metrics.py (5 metrics defined)
- ✅ Modified services.py and tasks.py with instrumentation
- ✅ test_audit_events.py (minimum 4 tests)
- ✅ All tests passing

**Verification**:
Manual review of all artifacts and documentation
