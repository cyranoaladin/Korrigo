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

### [ ] Step: Audit Logging for PII and Security Issues
<!-- chat-id: d6c19e8b-cd38-428d-ae0d-edea3dded618 -->

**Objective**: Audit all logging statements across grading modules to identify and remove PII leakage

**Tasks**:
- [ ] Audit `grading/` module for PII in logging statements
- [ ] Audit `processing/` module for PII in logging statements
- [ ] Audit `exams/` module for PII in logging statements
- [ ] Audit `identification/` module for PII in logging statements
- [ ] Audit `students/` module for PII in logging statements
- [ ] Check exception messages for PII (email, name, exam content)
- [ ] Verify only user_id logged (not email/username)
- [ ] Check all exception handlers have `exc_info=True`

**References**:
- Spec: Section 5, Phase 1 (Audit & Documentation)
- Requirements: REQ-1.1 (PII Removal Audit), REQ-1.3 (Exception Handling)

**Verification**:
```bash
# Check for PII patterns in logs
grep -rn "email\|password\|student.*name" backend/grading/ backend/processing/ backend/exams/
# Expected: No matches
```

### [ ] Step: Standardize Log Levels

**Objective**: Ensure consistent log level usage across all modules

**Tasks**:
- [ ] Review all logger.info(), logger.warning(), logger.error() calls
- [ ] Apply standard levels:
  - INFO: Normal workflow (import, lock, finalize)
  - WARNING: Recoverable issues (lock conflicts, retries)
  - ERROR: Failures requiring investigation (PDF errors, OCR failures)
  - CRITICAL: System-level failures (max retries exceeded)
- [ ] Update log statements to match standards

**References**:
- Spec: Section 5, Phase 1
- Requirements: REQ-1.2 (Log Levels Standardization)

**Verification**:
Manual code review to ensure levels match workflow severity

### [ ] Step: Create Audit Report Documentation

**Objective**: Document audit findings and current state of logging/metrics

**Tasks**:
- [ ] Create `.zenflow/tasks/observabilite-audit-trail-gradin-826d/audit.md`
- [ ] Document current logging state (inventory of loggers)
- [ ] Document PII audit results (files checked, findings)
- [ ] Document log level compliance
- [ ] Document request correlation coverage (Django vs Celery)
- [ ] Document metrics coverage (existing vs required)
- [ ] Provide recommendations

**References**:
- Spec: Section 3.1, Section 5 Phase 1
- Requirements: REQ-5.1 (Audit Report Structure)

**Verification**:
- [ ] All sections present in audit.md
- [ ] File references include line numbers
- [ ] Recommendations are actionable

### [ ] Step: Create Incident Response Playbook

**Objective**: Provide operators with diagnostic paths for common production issues

**Tasks**:
- [ ] Create `.zenflow/tasks/observabilite-audit-trail-gradin-826d/playbook.md`
- [ ] Document Scenario 1: Import Stuck (Celery queue, OCR timeout)
- [ ] Document Scenario 2: Finalization Failing (PDF generation errors)
- [ ] Document Scenario 3: Lock Conflicts (expired locks, user blocking)
- [ ] Document Scenario 4: High Latency (slow queries, timeouts)
- [ ] Document Scenario 5: Missing Audit Events (transaction rollback)
- [ ] Include for each scenario: Symptoms → Diagnosis → Root Causes → Actions
- [ ] Add example queries (log grep, DB queries, Prometheus queries)
- [ ] Cross-reference `docs/support/DEPANNAGE.md`

**References**:
- Spec: Section 5 Phase 1
- Requirements: REQ-4.1, REQ-4.2 (Playbook Structure and Scenarios)

**Verification**:
- [ ] All 5 scenarios documented
- [ ] Each scenario has all 4 sections
- [ ] Example queries are executable

### [ ] Step: Create Grading Metrics Module

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

### [ ] Step: Instrument Import and Finalize Services

**Objective**: Add metrics recording to PDF import and finalization workflows

**Tasks**:
- [ ] Modify `grading/services.py` - `import_pdf()` method
  - Wrap PDF processing with `track_import_duration()` context manager
  - Record import success/failure metrics
  - Add OCR error counter on rasterization exceptions
- [ ] Modify `grading/services.py` - `finalize_copy()` method
  - Wrap PDF flattening with `track_finalize_duration()` context manager
  - Record finalize success/failure metrics with retry attempt
- [ ] Add lock conflict counter increments
  - On `already_locked` exceptions
  - On `expired` lock errors
  - On `token_mismatch` errors

**References**:
- Spec: Section 3.2 (Modified Files), Section 5 Phase 2
- Requirements: REQ-2.1, REQ-2.2, REQ-2.3, REQ-2.4

**Verification**:
```bash
# Run grading tests to ensure no regressions
pytest backend/grading/tests/test_services.py -v
```

### [ ] Step: Add Copy Status Gauge Updater

**Objective**: Track workflow backlog by monitoring copy counts per status

**Tasks**:
- [ ] Implement periodic Celery task to update `grading_copies_by_status` gauge
- [ ] Query `Copy.objects.values('status').annotate(count=Count('id'))`
- [ ] Update gauge for each status (STAGING, READY, LOCKED, etc.)
- [ ] Schedule task to run every 60 seconds
- [ ] Alternative: Update gauge on state transitions (if preferred)

**References**:
- Spec: Section 5 Phase 2
- Requirements: REQ-2.5 (Copy Status Gauge)

**Verification**:
```bash
# Check gauge updates by scraping metrics
curl http://localhost:8088/metrics | grep grading_copies_by_status
```

### [ ] Step: Add Request Correlation to Celery Tasks

**Objective**: Propagate request_id from HTTP requests to Celery tasks for log correlation

**Tasks**:
- [ ] Modify `grading/tasks.py` - `async_finalize_copy()` signature
  - Add `request_id=None` parameter
  - Inject `request_id` into all log statements via `extra={'request_id': request_id}`
- [ ] Modify `grading/tasks.py` - `async_import_pdf()` signature
  - Add `request_id=None` parameter
  - Inject `request_id` into all log statements via `extra={'request_id': request_id}`
- [ ] Add metrics recording in Celery tasks (success/failure)

**References**:
- Spec: Section 2.2 (Request Correlation Pattern), Section 4.1 (Celery Task Signatures), Section 5 Phase 3
- Requirements: REQ-1.4 (Celery Task Correlation)

**Verification**:
Backward compatibility maintained with `request_id=None` default parameter

### [ ] Step: Update Task Dispatch Sites with Request ID

**Objective**: Pass request_id from HTTP requests when dispatching Celery tasks

**Tasks**:
- [ ] Audit all calls to `async_finalize_copy.delay()` in codebase
- [ ] Audit all calls to `async_import_pdf.delay()` in codebase
- [ ] Update calls in `views_async.py` to pass `request_id=request.request_id`
- [ ] Update calls in `services.py` to pass `request_id` (extract from thread-local if available)
- [ ] Verify RequestIDMiddleware provides `request.request_id`

**References**:
- Spec: Section 3.2 (Modified Files), Section 5 Phase 3
- Requirements: REQ-1.4

**Verification**:
```bash
# Upload PDF and check logs for request_id correlation
grep "<request_id>" logs/django.log
# Expected: Same request_id in HTTP request and Celery task logs
```

### [ ] Step: Create Audit Event Tests

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
