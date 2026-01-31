# Technical Specification: Observabilité + Audit Trail

**Task**: ZF-AUD-11  
**Version**: 1.0  
**Date**: 31 janvier 2026  
**Status**: Ready for Implementation

---

## 1. Technical Context

### 1.1 Technology Stack

- **Framework**: Django 4.2 + Django REST Framework
- **Database**: PostgreSQL (with Django ORM)
- **Task Queue**: Celery + Redis
- **Testing**: pytest + pytest-django + pytest-cov
- **Logging**: python-json-logger (ViatiqueJSONFormatter)
- **Metrics**: prometheus-client 0.19.0
- **Python**: 3.11+

### 1.2 Existing Infrastructure (Reusable Components)

**Logging & Request Correlation:**
- `core/middleware/request_id.py`: RequestIDMiddleware, RequestContextLogFilter
- `core/logging.py`: ViatiqueJSONFormatter for structured JSON logs
- Thread-local storage for request_id across log statements

**Metrics:**
- `core/prometheus.py`: Prometheus registry, HTTP request metrics
- `core/middleware/metrics.py`: MetricsMiddleware (records all HTTP requests)
- Exposed via `/metrics` endpoint (assumed from Prometheus standards)

**Audit Trail:**
- `grading/models.py`: GradingEvent model with 9 action types
- `grading/services.py`: Business logic creates GradingEvents at key workflow moments
- Events include: timestamp, actor (user), copy reference, metadata (JSON)

**Celery Tasks:**
- `grading/tasks.py`: async_finalize_copy, async_import_pdf
- Background processing for heavy PDF operations (rasterization, flattening)

---

## 2. Implementation Approach

### 2.1 Architecture Principles

1. **Non-Intrusive**: Leverage existing infrastructure, minimal refactoring
2. **Security-First**: No PII in logs (user_id only, not email/name)
3. **Performance**: Metrics collection fire-and-forget (no blocking)
4. **Separation of Concerns**: Domain metrics in `grading/metrics.py`, core metrics in `core/prometheus.py`
5. **Testability**: All instrumentation points covered by unit tests

### 2.2 Design Patterns

**Prometheus Metrics Pattern:**
```python
# grading/metrics.py (new file)
from prometheus_client import Counter, Histogram, Gauge
from core.prometheus import registry  # Reuse existing registry

# Metric definitions
grading_import_duration = Histogram(
    'grading_import_duration_seconds',
    'PDF import duration',
    ['status', 'pages_bucket'],
    registry=registry
)

# Instrumentation decorator/context manager
from contextlib import contextmanager
@contextmanager
def track_import_duration(pages):
    start = time.time()
    status = 'failed'
    try:
        yield
        status = 'success'
    finally:
        duration = time.time() - start
        bucket = _get_pages_bucket(pages)
        grading_import_duration.labels(status=status, pages_bucket=bucket).observe(duration)
```

**Request Correlation Pattern (Celery):**
```python
# Modify task signatures to accept request_id
@shared_task(bind=True, max_retries=3)
def async_finalize_copy(self, copy_id, user_id, lock_token=None, request_id=None):
    # Inject request_id into logger context
    logger = logging.getLogger('grading')
    logger.info(f"Starting finalization", extra={'request_id': request_id})
```

**Testing Pattern:**
```python
# grading/tests/test_audit_events.py
@pytest.mark.api
def test_import_creates_audit_event(client, teacher, exam):
    # Upload PDF
    response = client.post(...)
    
    # Assert GradingEvent created
    assert GradingEvent.objects.filter(
        copy=copy,
        action=GradingEvent.Action.IMPORT,
        actor=teacher
    ).exists()
    
    # Assert metadata
    event = GradingEvent.objects.get(...)
    assert 'filename' in event.metadata
    assert 'pages' in event.metadata
```

---

## 3. Source Code Structure Changes

### 3.1 New Files

```
backend/grading/
├── metrics.py                           # NEW: Domain-specific Prometheus metrics
└── tests/
    └── test_audit_events.py             # NEW: Tests for event creation

.zenflow/tasks/observabilite-audit-trail-gradin-826d/
├── audit.md                             # NEW: PII audit report
└── playbook.md                          # NEW: Incident response playbook
```

### 3.2 Modified Files

**grading/services.py**:
- Add metrics instrumentation for `import_pdf()` (lines ~370-420)
- Add metrics instrumentation for `finalize_copy()` (lines ~520-610)
- Standardize log levels (INFO for success, ERROR for failures, WARNING for retries)
- Audit exception handlers for PII (ensure exc_info=True)

**grading/tasks.py**:
- Add `request_id` parameter to `async_finalize_copy()` signature (line 21)
- Add `request_id` parameter to `async_import_pdf()` signature (line 88)
- Inject `request_id` into log statements via `extra={'request_id': ...}`
- Add metrics recording for task success/failure

**grading/views.py** (and views_async.py):
- Pass `request.request_id` to Celery tasks when dispatching
- No other changes needed (logging already has RequestIDMiddleware)

**core/prometheus.py** (optional enhancement):
- Add helper function `get_registry()` for consistency (if needed)

---

## 4. Data Model / API / Interface Changes

### 4.1 Celery Task Signatures (Breaking Change)

**Before:**
```python
async_finalize_copy.delay(copy_id, user_id, lock_token)
async_import_pdf.delay(exam_id, pdf_path, user_id, anonymous_id)
```

**After:**
```python
async_finalize_copy.delay(copy_id, user_id, lock_token, request_id=request.request_id)
async_import_pdf.delay(exam_id, pdf_path, user_id, anonymous_id, request_id=request.request_id)
```

**Migration Strategy**: Add `request_id` as optional parameter with default `None`, deploy backend, then update all call sites.

### 4.2 New Prometheus Metrics

All metrics registered in `grading/metrics.py`, exposed via existing `/metrics` endpoint:

| Metric Name | Type | Labels | Purpose |
|------------|------|--------|---------|
| `grading_import_duration_seconds` | Histogram | `status`, `pages_bucket` | PDF import performance |
| `grading_finalize_duration_seconds` | Histogram | `status`, `retry_attempt` | PDF finalization performance |
| `grading_ocr_errors_total` | Counter | `error_type` | OCR/rasterization failures |
| `grading_lock_conflicts_total` | Counter | `conflict_type` | Lock contention issues |
| `grading_copies_by_status` | Gauge | `status` | Workflow backlog monitoring |

**Label Values:**
- `status`: `success`, `failed`
- `pages_bucket`: `1-10`, `11-50`, `51-100`, `100+`
- `retry_attempt`: `1`, `2`, `3+`
- `error_type`: `timeout`, `invalid_pdf`, `empty_result`, `unknown`
- `conflict_type`: `already_locked`, `expired`, `token_mismatch`
- `status` (gauge): `STAGING`, `READY`, `LOCKED`, `GRADING_IN_PROGRESS`, `GRADED`, `GRADING_FAILED`

### 4.3 Logging Context Enhancement

**Current**: Request context injected by RequestContextLogFilter (request_id, path, method, user_id)

**New**: Celery tasks log with `extra={'request_id': request_id}` to correlate with originating HTTP request

**Example Log Output (JSON)**:
```json
{
  "timestamp": "2026-01-31T14:00:00.000Z",
  "level": "INFO",
  "logger": "grading",
  "message": "Starting async finalization",
  "request_id": "a1b2c3d4-...",
  "user_id": 42,
  "copy_id": "e5f6g7h8-...",
  "module": "tasks",
  "function": "async_finalize_copy"
}
```

---

## 5. Delivery Phases

### Phase 1: Audit & Documentation (4 hours)

**Objectives**: Establish security baseline, create incident response playbook

**Tasks**:
1. Audit all logging statements in `grading/`, `processing/`, `exams/`, `identification/`, `students/`
   - Grep for `logger.info`, `logger.error`, `logger.warning`, `logger.debug`
   - Check exception messages for PII (student names, emails, exam content)
   - Verify user_id logged (not email/username)
2. Standardize log levels:
   - INFO: Normal workflow (copy imported, locked, finalized)
   - WARNING: Recoverable issues (lock conflicts, retries)
   - ERROR: Failures requiring investigation (PDF errors, OCR failures)
   - CRITICAL: System-level failures (max retries exceeded)
3. Create `audit.md` report with:
   - Files checked (list)
   - PII findings (file:line references)
   - Log level compliance matrix
   - Recommendations
4. Create `playbook.md` with 5 scenarios:
   - Import Stuck (Celery queue, OCR timeout)
   - Finalization Failing (PDF generation errors)
   - Lock Conflicts (expired locks, user blocking)
   - High Latency (slow queries, timeouts)
   - Missing Audit Events (transaction rollback)

**Deliverables**:
- `audit.md` (all sections complete)
- `playbook.md` (5 scenarios with diagnosis steps)

**Verification**:
- Code review: No grep matches for `logger.*email`, `logger.*password`
- Manual review: All exception handlers have `exc_info=True`

---

### Phase 2: Metrics Implementation (3 hours)

**Objectives**: Expose grading-specific metrics for Prometheus scraping

**Tasks**:
1. Create `grading/metrics.py`:
   - Define 5 metrics (import, finalize, OCR, locks, status gauge)
   - Import `registry` from `core.prometheus`
   - Add helper functions: `_get_pages_bucket()`, `record_import()`, `record_finalize()`
2. Instrument `grading/services.py`:
   - `import_pdf()`: Wrap PDF processing with `track_import_duration()` context manager
   - `finalize_copy()`: Wrap PDF flattening with `track_finalize_duration()` context manager
   - Lock conflict handlers: Increment `grading_lock_conflicts_total` counter
3. Instrument `grading/tasks.py`:
   - Record task success/failure in metrics
   - Add OCR error counter (on rasterization exceptions)
4. Add status gauge updater:
   - Option A: Periodic Celery task (every 60s) to query Copy.objects counts
   - Option B: Update gauge on state transitions (STAGING→READY, etc.)
   - **Recommendation**: Option A (simpler, less intrusive)

**Deliverables**:
- `grading/metrics.py` (5 metrics defined)
- Modified `services.py` and `tasks.py` with instrumentation
- Metrics verified via `/metrics` endpoint (manual curl test)

**Verification**:
```bash
# Start server, perform import/finalize, then check metrics
curl http://localhost:8088/metrics | grep grading_
# Expected output:
# grading_import_duration_seconds_bucket{...}
# grading_finalize_duration_seconds_bucket{...}
# grading_lock_conflicts_total{...}
```

---

### Phase 3: Request Correlation (2 hours)

**Objectives**: Propagate request_id from HTTP requests to Celery tasks

**Tasks**:
1. Modify Celery task signatures:
   - Add `request_id=None` parameter to `async_finalize_copy()` and `async_import_pdf()`
   - Accept as optional argument (backward compatible)
2. Update task implementations:
   - Inject `request_id` into all log statements via `extra={'request_id': request_id}`
   - Pass `request_id` to child function calls (if any)
3. Update task dispatch sites:
   - `views_async.py`: Pass `request.request_id` when calling `.delay()`
   - `services.py`: Pass `request_id` if available (extract from thread-local)
4. Test correlation:
   - Upload PDF via API
   - Check logs: HTTP request_id should match Celery task request_id

**Deliverables**:
- Modified `tasks.py` (request_id parameter)
- Modified `views_async.py` and `services.py` (pass request_id)
- Correlation verified in logs

**Verification**:
```bash
# Upload PDF, grep logs for request_id
grep "a1b2c3d4-..." logs/django.log
# Expected: Multiple lines (HTTP request + Celery task) with same request_id
```

---

### Phase 4: Testing (2 hours)

**Objectives**: Ensure event creation and metrics recording are reliable

**Tasks**:
1. Create `grading/tests/test_audit_events.py`:
   - `test_import_creates_audit_event()`: Upload PDF, assert IMPORT event created with metadata
   - `test_create_annotation_creates_audit_event()`: Add annotation, assert CREATE_ANN event
   - `test_finalize_creates_audit_event_success()`: Finalize copy, assert FINALIZE event with success metadata
   - `test_finalize_creates_audit_event_failure()`: Mock PDF error, assert FINALIZE event with failure metadata
2. Add metrics tests (optional, in same file):
   - `test_import_records_duration_metric()`: Check Prometheus metric updated
   - `test_lock_conflict_records_metric()`: Trigger lock conflict, check counter
3. Verify existing tests still pass:
   - `test_workflow_complete.py`: Already checks event ordering (line 170)
   - `test_finalize.py`: Already checks FINALIZE event (lines 223, 250)
4. Run full test suite:
   ```bash
   pytest backend/grading/tests/test_audit_events.py -v
   pytest backend/grading/tests/ -v  # Full suite
   ```

**Deliverables**:
- `test_audit_events.py` (4 tests minimum)
- All tests passing (green CI)

**Verification**:
```bash
pytest backend/grading/tests/test_audit_events.py -v --cov=grading
# Expected: 100% coverage for event creation, 4/4 tests passed
```

---

## 6. Verification Approach

### 6.1 Unit Tests

**Test Framework**: pytest + pytest-django  
**Test Configuration**: `backend/pytest.ini` (DJANGO_SETTINGS_MODULE = core.settings_test)

**Test Coverage Requirements**:
- All new code in `grading/metrics.py`: 100% coverage
- Event creation tests: All 9 GradingEvent actions covered (minimum: IMPORT, CREATE_ANN, FINALIZE)
- Metrics recording: Smoke tests for all 5 metrics

**Test Commands**:
```bash
# Run audit event tests only
pytest backend/grading/tests/test_audit_events.py -v

# Run all grading tests
pytest backend/grading/tests/ -v

# Run with coverage report
pytest backend/grading/tests/ --cov=grading --cov-report=term-missing
```

### 6.2 Integration Tests

**Manual Verification Steps**:

1. **Logging Audit**:
   - Grep logs for PII: `grep -rn "email\|password\|student.*name" logs/`
   - Expected: No matches (only user_id logged)

2. **Request Correlation**:
   - Upload PDF via API
   - Check `logs/django.log` for request_id in HTTP request and Celery task
   - Expected: Same request_id in both

3. **Metrics Scraping**:
   - Start server: `python manage.py runserver`
   - Scrape metrics: `curl http://localhost:8088/metrics`
   - Expected: All 5 grading metrics present

4. **Incident Playbook**:
   - Simulate stuck import (kill Celery worker)
   - Follow playbook diagnosis steps
   - Expected: Playbook accurately identifies root cause

### 6.3 Lint and Type Checking

**Assumed Commands** (not found in project, standard Django practice):
```bash
# Linting
flake8 backend/grading/metrics.py backend/grading/tasks.py

# Type checking (if mypy configured)
mypy backend/grading/

# Django checks
python manage.py check --deploy
```

**Note**: If project uses different lint/typecheck commands, they will be discovered from:
- `Makefile` (check for `make lint`, `make test` targets)
- `README.md` (check for development workflow)
- CI configuration (`.github/workflows/`)

---

## 7. Dependencies and Constraints

### 7.1 External Dependencies

**No new packages required**. All dependencies already in `requirements.txt`:
- `prometheus-client==0.19.0` (already installed)
- `python-json-logger==2.0.7` (already installed)
- `celery` (already installed)

### 7.2 Database Migrations

**No migrations required**. GradingEvent model already exists with all needed fields.

### 7.3 Configuration Changes

**No settings changes required**. Logging and metrics infrastructure already configured in `core/settings.py`:
- LOGGING dict (lines 271-348)
- MIDDLEWARE includes RequestIDMiddleware (line 176)

**Optional**: Add environment variable for metrics update frequency:
```python
# core/settings.py
GRADING_METRICS_UPDATE_INTERVAL = int(os.environ.get('GRADING_METRICS_UPDATE_INTERVAL', '60'))  # seconds
```

### 7.4 Performance Constraints

1. **Metrics Collection**:
   - Must not block requests (fire-and-forget)
   - Prometheus client is already non-blocking (in-memory counters)
   - Status gauge updater runs in background (Celery periodic task)

2. **Logging**:
   - JSON formatter adds ~1ms per log statement (negligible)
   - Log rotation prevents disk exhaustion (10MB × 10 backups)

3. **Audit Events**:
   - GradingEvent creation within transaction (atomic with business operation)
   - No performance impact (single INSERT per workflow action)

---

## 8. Security Considerations

### 8.1 PII Protection

**Requirements**:
- No student names, emails, phone numbers in logs
- No exam content or annotation content in logs
- User ID logged (integer), not email/username
- Exception messages sanitized (no PII in error details)

**Verification Strategy**:
- Automated grep in CI: `grep -rn "email\|password" logs/` → fail if matches
- Code review: All `logger.*` calls checked for PII
- Example audit report in `audit.md`

### 8.2 Log Access Control

**Assumptions**:
- Log files accessible only to administrators (file permissions)
- Prometheus `/metrics` endpoint requires authentication (DRF IsAuthenticated)
- Audit trail (GradingEvent) immutable (no UPDATE/DELETE permissions in Django Admin)

**Recommendations** (for operators):
- Set log file permissions: `chmod 600 logs/*.log`
- Configure log aggregation with RBAC (ELK, Splunk, CloudWatch)

### 8.3 Secrets Management

**No secrets in logs**:
- API keys, tokens, passwords never logged
- Lock tokens logged (UUID only, not sensitive)
- Request IDs logged (UUID only, not sensitive)

---

## 9. Rollback Strategy

### 9.1 Backward Compatibility

**Phase 1 (Audit)**: Read-only, no code changes → No rollback needed

**Phase 2 (Metrics)**: Additive changes only
- New file `grading/metrics.py` → Safe to remove
- Instrumentation in `services.py` → Metrics recording wrapped in try/except (non-breaking)

**Phase 3 (Request Correlation)**: **Breaking change** (task signatures)
- Mitigation: Add `request_id` as optional parameter with default `None`
- Deploy sequence: (1) Update task signatures, (2) Update call sites, (3) Make required
- Rollback: Revert commits, restart Celery workers

**Phase 4 (Testing)**: Tests only → No rollback needed

### 9.2 Feature Flags

**Not required**. All changes are operational improvements (logging, metrics), not user-facing features.

**Optional**: Disable metrics recording via environment variable:
```python
# grading/metrics.py
METRICS_ENABLED = os.environ.get('GRADING_METRICS_ENABLED', 'true').lower() == 'true'

def record_import_duration(...):
    if not METRICS_ENABLED:
        return
    # ... record metric
```

---

## 10. Open Questions and Decisions

### 10.1 Celery Request Correlation Implementation

**Question**: How to pass request_id from HTTP to Celery task?

**Options**:
1. Task parameter (explicit): `async_finalize.delay(copy_id, user_id, lock_token, request_id)`
2. Celery headers (implicit): Use Celery's built-in `task.request.headers` to pass metadata
3. Thread-local (fragile): Extract from `get_current_request_id()` in task dispatch

**Decision**: **Option 1 (Task Parameter)**  
**Rationale**:
- Explicit is better than implicit (PEP 20)
- Easy to test (pass request_id directly in tests)
- No Celery version-specific behavior (headers API may change)
- Thread-local may not work across async boundaries

### 10.2 Status Gauge Update Mechanism

**Question**: How to update `grading_copies_by_status` gauge?

**Options**:
1. Periodic Celery task (every 60s): Query `Copy.objects.values('status').annotate(count=Count('id'))`
2. Signal-based (on state transitions): Update gauge in `post_save` signal
3. Manual update (in services): Increment/decrement gauge on status change

**Decision**: **Option 1 (Periodic Task)**  
**Rationale**:
- Simplest implementation (single SELECT query)
- No risk of missed updates (eventually consistent)
- Low overhead (60s interval acceptable for monitoring)
- Signals add complexity and can break atomicity

**Implementation**:
```python
# grading/tasks.py
@shared_task
def update_copy_status_metrics():
    from exams.models import Copy
    from grading.metrics import grading_copies_by_status
    
    counts = Copy.objects.values('status').annotate(count=Count('id'))
    for entry in counts:
        grading_copies_by_status.labels(status=entry['status']).set(entry['count'])
```

**Celery Beat Configuration** (not in scope, documented in playbook):
```python
# core/settings.py (operators to add)
CELERY_BEAT_SCHEDULE = {
    'update-copy-status-metrics': {
        'task': 'grading.tasks.update_copy_status_metrics',
        'schedule': 60.0,  # every 60 seconds
    },
}
```

### 10.3 OCR Errors Metric Scope

**Question**: OCR is not a separate service (PyMuPDF rasterization). What counts as "OCR error"?

**Decision**: **Track rasterization failures**  
**Rationale**:
- Requirements mention "OCR errors" in context of PDF import
- PyMuPDF rasterization failures are equivalent (PDF → image conversion)
- Error types: `invalid_pdf`, `empty_result`, `timeout`, `unknown`

**Implementation**:
```python
# grading/pdf_processor.py (import_pdf method)
try:
    doc = fitz.open(stream=pdf_file.read(), filetype="pdf")
    # ... rasterization
except fitz.FileDataError:
    grading_ocr_errors_total.labels(error_type='invalid_pdf').inc()
    raise
except Exception as e:
    grading_ocr_errors_total.labels(error_type='unknown').inc()
    raise
```

---

## 11. Out of Scope

### 11.1 Infrastructure (Operator Responsibility)

- Log aggregation setup (ELK, Splunk, CloudWatch)
- Prometheus server setup and scraping configuration
- Grafana dashboards for metrics visualization
- Alerting rules (PagerDuty, Opsgenie)
- Celery Beat scheduler configuration (for periodic tasks)

### 11.2 Future Enhancements (Not P0)

- Distributed tracing (OpenTelemetry spans)
- Anomaly detection (ML-based)
- Real-time dashboards (WebSocket push)
- Multi-process Prometheus metrics (Gunicorn workers)

---

## 12. References

### 12.1 ADRs and Documentation

- ADR-003: Audit Trail (GradingEvent model design)
- Phase S5-A: Observability (request correlation, structured logging)
- Phase S5-B: Prometheus metrics (HTTP instrumentation)
- `docs/support/DEPANNAGE.md`: Existing troubleshooting guide (to be cross-referenced in playbook)

### 12.2 Code References

**Key Files**:
- `backend/grading/models.py:109-165` - GradingEvent model
- `backend/grading/services.py:113-118` - CREATE_ANN event creation
- `backend/grading/services.py:584-608` - FINALIZE event creation
- `backend/grading/tasks.py:21-85` - async_finalize_copy implementation
- `backend/core/prometheus.py:52-67` - HTTP metrics definitions
- `backend/core/middleware/request_id.py:45-136` - Request correlation

**Test References**:
- `backend/grading/tests/test_workflow_complete.py:170-182` - Event ordering verification
- `backend/grading/tests/test_finalize.py:223,250` - FINALIZE event tests

---

## 13. Success Criteria

### 13.1 Functional Requirements

- [ ] All 5 grading metrics exposed via `/metrics` endpoint
- [ ] Request correlation works: Same request_id in HTTP logs and Celery task logs
- [ ] Audit events created for IMPORT, CREATE_ANN, FINALIZE (verified by tests)
- [ ] No PII in logs (verified by grep audit)
- [ ] Incident playbook complete with 5 scenarios

### 13.2 Quality Requirements

- [ ] All new code covered by unit tests (>90% coverage)
- [ ] All existing tests pass (no regressions)
- [ ] Metrics collection does not impact latency (verified by load test)
- [ ] Log rotation prevents disk exhaustion (verified manually)
- [ ] Documentation reviewed by operators (playbook accuracy)

### 13.3 Deliverables Checklist

- [ ] `grading/metrics.py` - 5 Prometheus metrics defined
- [ ] `grading/tests/test_audit_events.py` - 4 tests minimum
- [ ] `audit.md` - PII audit report (all sections)
- [ ] `playbook.md` - Incident response playbook (5 scenarios)
- [ ] Modified `grading/services.py` - Instrumented import/finalize
- [ ] Modified `grading/tasks.py` - Request correlation added
- [ ] Modified `grading/views_async.py` - Pass request_id to tasks

---

## 14. Implementation Notes

### 14.1 Development Workflow

1. Create feature branch: `git checkout -b feat/observability-audit-trail`
2. Implement phases sequentially (1→2→3→4)
3. Run tests after each phase: `pytest backend/grading/tests/ -v`
4. Manual verification: Start server, test metrics endpoint, check logs
5. Create PR with checklist: Link to `spec.md`, `audit.md`, `playbook.md`

### 14.2 Testing Strategy

**Unit Tests** (fast, isolated):
- Mock PDF operations, focus on event creation
- Mock Prometheus client, verify metric labels

**Integration Tests** (slow, real DB):
- Full workflow: Upload → Annotate → Finalize → Export
- Verify events in correct order (already covered by `test_workflow_complete.py`)

**Manual Tests** (production-like):
- Import 100-page PDF, check metrics (pages_bucket=100+)
- Simulate lock conflict, check metrics (conflict_type=already_locked)
- Kill Celery worker, follow playbook (Import Stuck scenario)

### 14.3 Deployment Checklist

**Pre-Deployment**:
- [ ] All tests passing (CI green)
- [ ] Code review approved (2+ reviewers)
- [ ] Audit report reviewed by security team
- [ ] Playbook reviewed by operations team

**Deployment**:
- [ ] Deploy backend (Django + Celery workers)
- [ ] Restart Celery workers (pick up new task signatures)
- [ ] Verify metrics endpoint: `curl https://prod.example.com/metrics`
- [ ] Monitor logs for errors (10 minutes post-deployment)

**Post-Deployment**:
- [ ] Configure Prometheus scraping (operations)
- [ ] Import Grafana dashboards (operations)
- [ ] Set up alerting rules (operations)
- [ ] Schedule Celery Beat tasks (operations, if status gauge used)

---

**End of Technical Specification**
