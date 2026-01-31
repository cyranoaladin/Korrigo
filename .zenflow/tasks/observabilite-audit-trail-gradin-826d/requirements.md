# Product Requirements Document: Observabilité + Audit Trail

**Task**: ZF-AUD-11  
**Version**: 1.0  
**Date**: 31 janvier 2026  
**Status**: Requirements Complete

---

## 1. Executive Summary

### 1.1 Objective

Enable production diagnostics and troubleshooting capabilities without exposing sensitive data (PII, student information). The system must provide comprehensive observability through:
- Audit trail of all grading workflow events (GradingEvent model)
- Structured logging with request correlation
- Metrics for performance monitoring
- Incident response playbook for operators

### 1.2 Success Criteria

- ✅ Production debugging possible without exposing PII
- ✅ All workflow events (IMPORT, CREATE_ANN, FINALIZE) are logged and auditable
- ✅ Request correlation works across Django and Celery
- ✅ Metrics exposed for monitoring (durations, errors, conflicts)
- ✅ Tests verify event creation at key moments
- ✅ Incident playbook provides clear diagnostic paths

---

## 2. Context and Current State

### 2.1 Existing Infrastructure

**Audit Trail (GradingEvent Model)**:
- ✅ Model exists with actions: IMPORT, VALIDATE, LOCK, UNLOCK, CREATE_ANN, UPDATE_ANN, DELETE_ANN, FINALIZE, EXPORT
- ✅ Events created at key workflow moments in `services.py` and `tasks.py`
- ✅ Events include metadata (JSON field), actor (user), timestamp, copy reference

**Logging Infrastructure**:
- ✅ RequestIDMiddleware: Generates UUID for each request, adds X-Request-ID header
- ✅ RequestContextLogFilter: Injects request_id, path, method, user_id into all logs
- ✅ ViatiqueJSONFormatter: Structured JSON logs for production
- ✅ Separate loggers: `django`, `audit`, `grading`, `metrics`, `django.security`
- ✅ Log files: `django.log` (general), `audit.log` (audit trail), rotating (10MB, 10 backups)

**Metrics Infrastructure**:
- ✅ Prometheus metrics via `core/prometheus.py`
- ✅ HTTP request counter (method, path, status)
- ✅ HTTP request duration histogram
- ✅ Process metrics (CPU, memory, GC, file descriptors)
- ✅ MetricsMiddleware: Records all HTTP requests

**Celery Tasks**:
- ✅ `async_finalize_copy`: Background PDF finalization with retry (3 attempts)
- ✅ `async_import_pdf`: Background PDF rasterization
- ✅ Logging in Celery tasks with logger name 'grading'
- ⚠️ No request_id correlation from HTTP request to Celery task

### 2.2 Reference Workflow Events

From the task description and codebase analysis, the key workflow events are:

1. **IMPORT**: PDF uploaded and rasterized into pages
   - Location: `GradingService.import_pdf()` → line 416-421
   - Metadata: `filename`, `pages`

2. **CREATE_ANN**: Annotation created on a copy
   - Location: `AnnotationService.add_annotation()` → line 113-118
   - Metadata: `annotation_id`, `page`

3. **FINALIZE**: Copy graded and PDF generated
   - Location: `GradingService.finalize_copy()` → line 584-608
   - Metadata: `final_score`, `retries`, `success` (bool)

Additional events already tracked:
- VALIDATE (STAGING→READY), LOCK, UNLOCK, UPDATE_ANN, DELETE_ANN, EXPORT

---

## 3. Requirements

### 3.1 Audit Logs: PII Removal and Security

**REQ-1.1: PII Removal Audit**
- Audit all logging statements in `grading/`, `processing/`, `exams/`, `identification/`, `students/`
- Identify and remove any logging of:
  - Student names, emails, phone numbers
  - User emails (log user_id only)
  - Exam content, annotation content
  - PDF paths with identifiable information
- **Current State**: System already logs user_id (not email), anonymous_id (not student name)
- **Action**: Verify no PII leakage in exception messages, debug logs, or Celery task logs

**REQ-1.2: Log Levels Standardization**
- INFO: Normal workflow events (copy imported, locked, finalized)
- WARNING: Recoverable issues (lock conflicts, optimistic locking conflicts, retry attempts)
- ERROR: Failures requiring investigation (PDF generation failed, OCR errors, import failures)
- CRITICAL: System-level failures requiring immediate action (max retries exceeded, database deadlocks)
- **Current State**: Mixed usage of log levels
- **Action**: Standardize levels across all modules

**REQ-1.3: Exception Handling and Stack Traces**
- All exceptions must include `exc_info=True` for stack traces
- Exception messages must not contain PII
- **Current State**: Some exceptions already logged with exc_info (e.g., line 610 in services.py)
- **Action**: Audit all exception handlers for consistency

**REQ-1.4: Celery Task Correlation**
- Celery tasks must log with correlation to originating request_id
- Pass request_id as task argument when task initiated from HTTP request
- **Current State**: No request_id propagation to Celery tasks
- **Action**: Modify task signatures to accept and log request_id

### 3.2 Metrics: Performance and Error Monitoring

**REQ-2.1: Import Duration Metric**
- Metric: `grading_import_duration_seconds` (histogram)
- Labels: `status` (success/failed), `pages` (bucket: 1-10, 11-50, 51-100, 100+)
- Purpose: Monitor PDF import performance, detect slow imports

**REQ-2.2: Finalize Duration Metric**
- Metric: `grading_finalize_duration_seconds` (histogram)
- Labels: `status` (success/failed), `retry_attempt` (1, 2, 3+)
- Purpose: Monitor PDF flattening performance, detect failures

**REQ-2.3: OCR Errors Metric**
- Metric: `grading_ocr_errors_total` (counter)
- Labels: `error_type` (timeout, invalid_pdf, empty_result)
- Purpose: Track OCR service reliability
- **Note**: OCR is performed during rasterization (PyMuPDF), not separate service in current implementation

**REQ-2.4: Lock Conflicts Metric**
- Metric: `grading_lock_conflicts_total` (counter)
- Labels: `conflict_type` (already_locked, expired, token_mismatch)
- Purpose: Monitor concurrent editing issues, detect lock contention

**REQ-2.5: Copy Status Gauge**
- Metric: `grading_copies_by_status` (gauge)
- Labels: `status` (STAGING, READY, LOCKED, GRADING_IN_PROGRESS, GRADED, GRADING_FAILED)
- Purpose: Monitor workflow backlog and stuck copies

### 3.3 Testing: Event Creation Verification

**REQ-3.1: Test IMPORT Event**
- Test that `GradingEvent.Action.IMPORT` is created when PDF imported
- Verify metadata includes `filename`, `pages`
- Test location: New test in `grading/tests/test_audit_events.py`

**REQ-3.2: Test CREATE_ANN Event**
- Test that `GradingEvent.Action.CREATE_ANN` is created when annotation added
- Verify metadata includes `annotation_id`, `page`
- Test location: New test in `grading/tests/test_audit_events.py`

**REQ-3.3: Test FINALIZE Event**
- Test that `GradingEvent.Action.FINALIZE` is created when copy finalized
- Verify metadata includes `final_score`, `retries`
- Test for both success and failure cases
- Test location: Existing test in `grading/tests/test_finalize.py` (line 223, 250)

**REQ-3.4: Test Event Ordering**
- Test that events are created in correct order for complete workflow
- Verify: IMPORT → VALIDATE → LOCK → CREATE_ANN* → FINALIZE → EXPORT
- Test location: Existing test in `grading/tests/test_workflow_complete.py` (line 170)

### 3.4 Documentation: Incident Playbook

**REQ-4.1: Playbook Structure**
- Format: Markdown file at `.zenflow/tasks/observabilite-audit-trail-gradin-826d/playbook.md`
- Sections: Symptoms → Diagnosis → Root Causes → Actions
- Cross-reference existing documentation: `docs/support/DEPANNAGE.md`

**REQ-4.2: Playbook Scenarios**

**Scenario 1: Import Stuck (PDF not processing)**
- Symptoms: Copy in STAGING status, no pages generated
- Diagnosis: Check Celery queue, check logs for import errors
- Root Causes: OCR timeout, corrupted PDF, disk space, Celery worker down
- Actions: Retry import, check Celery health, verify PDF validity

**Scenario 2: Finalization Failing (PDF generation errors)**
- Symptoms: Copy in GRADING_FAILED status, grading_error_message set
- Diagnosis: Check GradingEvent.metadata for error details
- Root Causes: PyMuPDF error, annotation rendering issue, timeout
- Actions: Check logs for exception, verify annotations, retry finalization

**Scenario 3: Lock Conflicts (Users blocked from editing)**
- Symptoms: "Copy is locked by another user" error
- Diagnosis: Check CopyLock table, check lock expiration
- Root Causes: Expired lock not cleaned, user didn't release lock, browser crash
- Actions: Force-release lock via admin, check heartbeat mechanism

**Scenario 4: High Latency (Slow response times)**
- Symptoms: Requests taking >5s, timeout errors
- Diagnosis: Check Prometheus metrics, check database query times
- Root Causes: Database lock contention, large PDF processing, high load
- Actions: Check active queries, optimize slow endpoints, scale resources

**Scenario 5: Missing Audit Events (Events not recorded)**
- Symptoms: GradingEvent.objects.filter() returns no results for expected action
- Diagnosis: Check transaction rollback, check exception in service method
- Root Causes: Exception before event creation, transaction rolled back
- Actions: Check logs for exceptions, verify transaction atomicity

### 3.5 Audit Report Documentation

**REQ-5.1: Audit Report Structure**
- Format: Markdown file at `.zenflow/tasks/observabilite-audit-trail-gradin-826d/audit.md`
- Sections:
  1. Current Logging State (inventory of all loggers and levels)
  2. PII Audit Results (list of files checked, findings)
  3. Log Level Compliance (adherence to standards)
  4. Request Correlation Coverage (Django vs Celery)
  5. Metrics Coverage (existing vs required)
  6. Recommendations (improvements and next steps)

---

## 4. Non-Functional Requirements

### 4.1 Performance

- Logging must not impact request latency by >5ms
- Metrics collection must not block requests (fire-and-forget)
- GradingEvent creation must be within transaction (atomic with business operation)

### 4.2 Security

- No PII in logs (user_id only, not email/username)
- No secrets in logs (passwords, tokens, API keys)
- Logs must be accessible only to administrators (file permissions)
- Audit trail (GradingEvent) must be immutable (no UPDATE/DELETE permissions)

### 4.3 Reliability

- Log rotation to prevent disk exhaustion (10MB files, 10 backups)
- Metrics endpoint must not fail even if metrics recording fails
- GradingEvent creation failure must not block business operations (logged as warning)

---

## 5. Out of Scope

### 5.1 Explicitly Excluded

- **Log aggregation infrastructure**: No ELK/Splunk/CloudWatch integration (operator responsibility)
- **Alerting system**: No PagerDuty/Opsgenie integration (operator responsibility)
- **Distributed tracing**: No OpenTelemetry/Jaeger spans (P1 enhancement)
- **Metrics dashboard**: No Grafana setup (operator responsibility)
- **Anomaly detection**: No ML-based anomaly detection (future enhancement)

### 5.2 Assumptions

- Operators have access to server logs via SSH or log aggregation tool
- Operators can scrape Prometheus `/metrics` endpoint
- Database backups include GradingEvent table (audit trail preservation)
- Log retention policy defined by operator (default 10 rotations ≈ 100MB per logger)

---

## 6. Dependencies

### 6.1 Existing Components (No Changes)

- `core/middleware/request_id.py`: RequestIDMiddleware, RequestContextLogFilter
- `core/logging.py`: ViatiqueJSONFormatter
- `core/prometheus.py`: Prometheus metrics registry, record_request_metrics()
- `core/middleware/metrics.py`: MetricsMiddleware
- `grading/models.py`: GradingEvent model

### 6.2 Components to Modify

- `grading/services.py`: Add metrics recording for import/finalize
- `grading/tasks.py`: Add request_id correlation, add metrics
- `grading/views.py`: Audit logging statements for PII
- All modules: Standardize log levels

### 6.3 New Components

- `grading/tests/test_audit_events.py`: Tests for event creation
- `grading/metrics.py`: New module for grading-specific Prometheus metrics
- `.zenflow/tasks/observabilite-audit-trail-gradin-826d/audit.md`: Audit report
- `.zenflow/tasks/observabilite-audit-trail-gradin-826d/playbook.md`: Incident playbook

---

## 7. Acceptance Criteria

### 7.1 Audit Report Complete

- [ ] audit.md created with all sections
- [ ] All modules audited for PII (grading, processing, exams, identification, students)
- [ ] PII findings documented with file:line references
- [ ] Log level compliance documented
- [ ] Recommendations provided

### 7.2 Metrics Implemented

- [ ] Import duration metric exposed
- [ ] Finalize duration metric exposed
- [ ] Lock conflicts counter exposed
- [ ] Copy status gauge exposed
- [ ] Metrics verified via `/metrics` endpoint

### 7.3 Tests Added

- [ ] Test for IMPORT event creation
- [ ] Test for CREATE_ANN event creation
- [ ] Test for FINALIZE event creation (success and failure)
- [ ] Tests pass in CI pipeline

### 7.4 Playbook Complete

- [ ] playbook.md created with all scenarios
- [ ] Each scenario includes: Symptoms → Diagnosis → Root Causes → Actions
- [ ] Playbook cross-references existing docs (DEPANNAGE.md)
- [ ] Playbook includes example queries (log grep, DB queries, Prometheus queries)

### 7.5 Production Ready

- [ ] No PII in logs (verified by code review)
- [ ] Request correlation works for Django and Celery
- [ ] Metrics scraping tested
- [ ] Log rotation verified
- [ ] Documentation reviewed by operator

---

## 8. Risks and Mitigations

### 8.1 Risk: PII Leakage in Exception Messages

**Likelihood**: Medium  
**Impact**: High (GDPR violation)  
**Mitigation**: 
- Code review of all exception handlers
- Automated tests for log output inspection
- Regular audit of production logs

### 8.2 Risk: Metrics Cardinality Explosion

**Likelihood**: Low  
**Impact**: Medium (Prometheus performance degradation)  
**Mitigation**:
- Limit metric labels to low-cardinality values
- Use histogram buckets instead of exact values
- Document metric design in code comments

### 8.3 Risk: Log Volume Explosion

**Likelihood**: Medium  
**Impact**: Medium (disk space, cost)  
**Mitigation**:
- Log rotation configured (10MB × 10 backups)
- INFO level for normal operations (not DEBUG)
- Operators configure external log retention

---

## 9. Open Questions

### 9.1 Clarifications Needed

**Q1: Log Retention Policy**  
Current: 10 rotations (≈100MB per logger)  
Question: Is this sufficient for production audit requirements? Should we recommend external log aggregation?  
**Decision**: Accepted as-is. Operators can configure external aggregation if needed.

**Q2: Metrics Scraping Frequency**  
Question: What is the expected Prometheus scraping interval (15s, 30s, 60s)?  
**Decision**: Metrics designed for standard 15-30s interval. Operators configure.

**Q3: Celery Request Correlation**  
Question: Should we propagate request_id to ALL Celery tasks, or only grading-related tasks?  
**Decision**: Only grading tasks (async_finalize_copy, async_import_pdf) for this iteration. Expand in future if needed.

---

## 10. Implementation Notes

### 10.1 Phased Approach

**Phase 1: Audit and Documentation** (Estimated: 4 hours)
- Audit logs for PII
- Create audit.md report
- Create playbook.md

**Phase 2: Metrics Implementation** (Estimated: 3 hours)
- Add grading/metrics.py module
- Instrument import/finalize with metrics
- Add lock conflict counter
- Add copy status gauge

**Phase 3: Testing** (Estimated: 2 hours)
- Add test_audit_events.py
- Verify event creation tests
- Verify metrics recording

**Phase 4: Request Correlation** (Estimated: 2 hours)
- Modify Celery task signatures
- Pass request_id from views to tasks
- Update task logging

**Total Estimated Effort**: 11 hours

### 10.2 Rollout Strategy

1. Deploy audit.md and playbook.md (no code changes)
2. Deploy metrics implementation (backward compatible, no breaking changes)
3. Deploy tests (CI pipeline only)
4. Deploy request correlation (backward compatible, optional request_id parameter)
5. Validate in staging environment
6. Deploy to production
7. Train operators on playbook usage

---

## 11. Success Metrics

### 11.1 Quantitative

- **Audit Coverage**: 100% of modules audited (grading, processing, exams, identification, students)
- **Test Coverage**: 3+ new tests for event creation
- **Metrics Coverage**: 4+ new metrics exposed
- **Documentation**: 2 new documents (audit.md, playbook.md)

### 11.2 Qualitative

- Operators can diagnose production issues without accessing sensitive data
- Incident resolution time reduced (baseline: TBD, target: -30%)
- No GDPR violations from log exposure
- Developer confidence in observability increased

---

## 12. Appendix

### 12.1 Terminology

- **PII**: Personally Identifiable Information (names, emails, phone numbers)
- **GradingEvent**: Audit trail model for grading workflow actions
- **Request Correlation**: Linking log entries across requests via request_id
- **Prometheus**: Time-series metrics database and monitoring system
- **Celery**: Distributed task queue for async operations

### 12.2 References

- ADR-003: Grading workflow state machine
- Phase S5-A: Observability (logging and request correlation)
- Phase S5-B: Metrics (Prometheus integration)
- RGPD Compliance: `docs/security/POLITIQUE_RGPD.md`
- Existing Playbook: `docs/support/DEPANNAGE.md`
- Architecture: `docs/technical/ARCHITECTURE.md`

---

**Document Status**: Requirements Complete - Ready for Technical Specification  
**Next Step**: Create Technical Specification in `spec.md`
