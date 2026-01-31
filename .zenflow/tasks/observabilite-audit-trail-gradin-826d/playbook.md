# Incident Response Playbook: Grading Workflow

**Task**: ZF-AUD-11  
**Date**: 31 janvier 2026  
**Audience**: DevOps Engineers, SRE, Support Engineers  
**Status**: Production Ready

---

## Overview

This playbook provides diagnostic procedures for production incidents related to the grading workflow (PDF import, annotation, finalization). Each scenario follows the structure:

1. **Symptoms** - Observable behavior indicating the issue
2. **Diagnosis** - Step-by-step investigation using logs, metrics, database
3. **Root Causes** - Common underlying problems
4. **Actions** - Remediation steps and escalation paths

**Prerequisites**:
- SSH access to production server
- Access to application logs (`/opt/korrigo/backend/logs/`)
- Access to Prometheus metrics (`/metrics` endpoint)
- Database access (read-only recommended)
- Familiarity with Django ORM and Celery

**Cross-Reference**: See `docs/support/DEPANNAGE.md` for general troubleshooting.

---

## Scenario 1: Import Stuck (PDF Not Processing)

### Symptoms
- Copy remains in `STAGING` status for >5 minutes
- No pages generated (`Booklet.pages_images` is empty)
- Users report "PDF upload successful but no preview available"
- GradingEvent shows `IMPORT` action but no subsequent events

### Diagnosis

#### Step 1: Check Copy Status
```bash
# SSH to server
ssh admin@serveur-korrigo
cd /opt/korrigo/backend

# Check Copy status in database
docker-compose exec backend python manage.py shell
```

```python
from exams.models import Copy
from grading.models import GradingEvent

# Find stuck copies
stuck_copies = Copy.objects.filter(status='STAGING', created_at__lt=timezone.now() - timedelta(minutes=5))
print(f"Found {stuck_copies.count()} stuck copies")

for copy in stuck_copies[:5]:
    print(f"Copy {copy.id} - Created: {copy.created_at}")
    
    # Check if import event exists
    import_event = GradingEvent.objects.filter(copy=copy, action='IMPORT').first()
    if import_event:
        print(f"  Import event: {import_event.metadata}")
    
    # Check booklets
    booklets = copy.booklets.all()
    print(f"  Booklets: {booklets.count()}")
    for b in booklets:
        print(f"    Pages: {len(b.pages_images) if b.pages_images else 0}")
```

#### Step 2: Check Celery Queue
```bash
# Check if Celery worker is running
docker-compose ps celery
# Expected: "Up" status

# Check Celery logs for async_import_pdf task
docker-compose logs --tail=100 celery | grep "async_import_pdf"

# Check for errors
docker-compose logs --tail=100 celery | grep -i "error\|failed\|exception"
```

#### Step 3: Check Application Logs
```bash
# Check import-related logs (JSON format)
grep "Import failed for copy" logs/django.log | tail -10

# Check for rasterization errors
grep "Rasterization failed" logs/django.log | tail -10

# Check for OCR/PyMuPDF errors
grep "fitz\|PyMuPDF" logs/django.log | tail -10
```

#### Step 4: Check Prometheus Metrics (After Phase 2)
```bash
# Query import duration metric
curl http://localhost:8088/metrics | grep grading_import_duration

# Check OCR error counter
curl http://localhost:8088/metrics | grep grading_ocr_errors_total

# Example output:
# grading_ocr_errors_total{error_type="timeout"} 5
# grading_ocr_errors_total{error_type="invalid_pdf"} 2
```

### Root Causes

1. **Celery Worker Down**
   - Symptom: No Celery logs, `docker-compose ps celery` shows "Exit"
   - Diagnosis: Check `docker-compose logs celery` for crash reason
   - Action: Restart Celery worker
   ```bash
   docker-compose restart celery
   ```

2. **OCR Timeout (Large PDF)**
   - Symptom: Logs show "Rasterization failed" after 60+ seconds
   - Diagnosis: Check PDF file size and page count
   ```python
   copy.pdf_source.size  # In bytes
   ```
   - Action: Increase Celery task timeout (environment variable)

3. **Corrupted PDF File**
   - Symptom: Logs show `fitz.FileDataError: invalid_pdf`
   - Diagnosis: Attempt manual PDF open
   ```bash
   # Download PDF and check with PyMuPDF
   python -c "import fitz; fitz.open('/path/to/copy.pdf')"
   ```
   - Action: Ask user to re-upload PDF

4. **Disk Space Exhausted**
   - Symptom: Logs show `OSError: [Errno 28] No space left on device`
   - Diagnosis: Check disk usage
   ```bash
   df -h /opt/korrigo/media
   ```
   - Action: Clean up orphaned files, expand disk

5. **Transaction Rollback**
   - Symptom: Copy created but no booklet, no import event
   - Diagnosis: Check for exception in service layer
   ```bash
   grep "Import failed for copy" logs/django.log | grep -A 5 "Traceback"
   ```
   - Action: Fix underlying exception (check error details)

### Actions

**Immediate**:
1. Restart Celery worker if down: `docker-compose restart celery`
2. Check disk space: `df -h`
3. Review last 10 error logs: `tail -50 logs/django.log | grep ERROR`

**Short-term** (Next 24 hours):
1. Monitor Celery health via Prometheus
2. Set up alerts for OCR errors > 5/minute
3. Implement automatic worker restart (Celery Beat health check)

**Long-term**:
1. Add timeout configuration for large PDFs
2. Implement PDF pre-validation (file size, page count limits)
3. Add disk space monitoring and alerts

---

## Scenario 2: Finalization Failing (PDF Generation Errors)

### Symptoms
- Copy stuck in `GRADING_IN_PROGRESS` or `GRADING_FAILED` status
- `Copy.grading_error_message` contains error details
- Users report "Finalization failed" or HTTP 500 errors
- GradingEvent shows `FINALIZE` action with `success: false`

### Diagnosis

#### Step 1: Check Copy Status and Error Message
```python
from exams.models import Copy
from grading.models import GradingEvent

# Find failed copies
failed_copies = Copy.objects.filter(status='GRADING_FAILED').order_by('-updated_at')[:10]

for copy in failed_copies:
    print(f"Copy {copy.id}:")
    print(f"  Error: {copy.grading_error_message}")
    print(f"  Retries: {copy.grading_retries}")
    
    # Check finalize event metadata
    finalize_event = GradingEvent.objects.filter(
        copy=copy, 
        action='FINALIZE'
    ).order_by('-created_at').first()
    
    if finalize_event:
        print(f"  Event metadata: {finalize_event.metadata}")
```

#### Step 2: Check Logs for Exception Details
```bash
# Check for PDF generation failures
grep "PDF generation failed" logs/django.log | tail -10

# Check for PyMuPDF errors
grep "fitz\|PyMuPDF\|flatten" logs/django.log | grep -i error | tail -20

# Get full stack trace for specific copy
COPY_ID="e5f6g7h8-..."
grep "$COPY_ID" logs/django.log | grep -A 10 "Traceback"
```

#### Step 3: Check Prometheus Metrics (After Phase 2)
```bash
# Check finalize duration and failures
curl http://localhost:8088/metrics | grep grading_finalize_duration

# Example output showing failures:
# grading_finalize_duration_seconds_count{status="failed",retry_attempt="1"} 3
# grading_finalize_duration_seconds_count{status="failed",retry_attempt="3"} 1  # Max retries reached!
```

#### Step 4: Check for CRITICAL Alerts
```bash
# Check for max retries exceeded
grep "CRITICAL" logs/django.log | grep "manual intervention required"

# Expected output:
# Copy {copy_id} failed 3 times - manual intervention required
```

### Root Causes

1. **PyMuPDF Rendering Error**
   - Symptom: Error message contains "flatten_copy failed: fitz error"
   - Diagnosis: Check annotation coordinates (out of bounds)
   ```python
   from grading.models import Annotation
   annotations = Annotation.objects.filter(copy_id=copy_id)
   for ann in annotations:
       if ann.x + ann.w > 1.0 or ann.y + ann.h > 1.0:
           print(f"Invalid annotation: {ann.id}")
   ```
   - Action: Delete invalid annotations, retry finalization

2. **Timeout (Large PDF)**
   - Symptom: Error message contains "timeout" or logs show >90s duration
   - Diagnosis: Check PDF page count and file size
   ```python
   copy.booklets.first().pages_images  # Page count
   copy.pdf_source.size  # Bytes
   ```
   - Action: Increase Celery task timeout, optimize PDF flattening

3. **Missing PDF Source**
   - Symptom: Error message contains "pdf_source not found"
   - Diagnosis: Check if file exists on disk
   ```python
   copy.pdf_source.path  # Expected: /opt/korrigo/media/copies/...
   import os
   os.path.exists(copy.pdf_source.path)  # Should be True
   ```
   - Action: Restore from backup, or ask user to re-upload

4. **Concurrent Finalization (Race Condition)**
   - Symptom: Error message contains "Copy already finalized"
   - Diagnosis: Check for duplicate finalize requests
   ```python
   finalize_events = GradingEvent.objects.filter(
       copy_id=copy_id, 
       action='FINALIZE'
   ).order_by('created_at')
   
   for event in finalize_events:
       print(f"{event.created_at}: {event.metadata}")
   ```
   - Action: No action needed (system correctly rejected duplicate)

5. **Max Retries Exceeded**
   - Symptom: `copy.grading_retries >= 3`, status = `GRADING_FAILED`
   - Diagnosis: Check if underlying issue is fixed
   - Action: Manually reset retries and retry
   ```python
   copy.grading_retries = 0
   copy.status = 'LOCKED'  # Or 'READY' if no lock
   copy.save()
   # Then trigger finalization again via API
   ```

### Actions

**Immediate**:
1. Check for CRITICAL alerts: `grep CRITICAL logs/django.log`
2. Identify copies with max retries: Query `Copy.objects.filter(grading_retries__gte=3)`
3. Review error messages and stack traces

**Short-term** (Next 24 hours):
1. Fix invalid annotations (delete or correct coordinates)
2. Restore missing PDF files from backup
3. Manually retry failed copies after fixing root cause

**Long-term**:
1. Add annotation validation at creation time (prevent invalid coordinates)
2. Implement automatic retry with exponential backoff
3. Add alerting for max retries exceeded (CRITICAL logs)

---

## Scenario 3: Lock Conflicts (Users Blocked from Editing)

### Symptoms
- Users receive "Copy is locked by another user" error
- Users report "Cannot acquire lock" or HTTP 409 Conflict
- Copy status is `LOCKED` but user claims they closed the browser
- Expired locks not being cleaned up

### Diagnosis

#### Step 1: Check CopyLock Table
```python
from grading.models import CopyLock
from django.utils import timezone

# Find active locks
active_locks = CopyLock.objects.select_related('copy', 'owner').all()
print(f"Total active locks: {active_locks.count()}")

now = timezone.now()
for lock in active_locks[:10]:
    expired = "EXPIRED" if lock.expires_at < now else "ACTIVE"
    print(f"Copy {lock.copy.id} - Owner: {lock.owner.username} - {expired}")
    print(f"  Expires: {lock.expires_at} (in {(lock.expires_at - now).total_seconds()}s)")
```

#### Step 2: Check Lock Conflict Events
```python
from grading.models import GradingEvent

# Check for lock/unlock events
lock_events = GradingEvent.objects.filter(
    action__in=['LOCK', 'UNLOCK']
).order_by('-created_at')[:20]

for event in lock_events:
    print(f"{event.created_at}: {event.action} by {event.actor.username}")
```

#### Step 3: Check Prometheus Metrics (After Phase 2)
```bash
# Check lock conflict counter
curl http://localhost:8088/metrics | grep grading_lock_conflicts_total

# Example output:
# grading_lock_conflicts_total{conflict_type="already_locked"} 12
# grading_lock_conflicts_total{conflict_type="expired"} 3
# grading_lock_conflicts_total{conflict_type="token_mismatch"} 1
```

#### Step 4: Check Application Logs
```bash
# Check for lock-related errors
grep "Lock" logs/django.log | grep -i "conflict\|expired\|mismatch" | tail -20

# Check for specific copy
COPY_ID="e5f6g7h8-..."
grep "$COPY_ID" logs/django.log | grep -i "lock"
```

### Root Causes

1. **Expired Lock Not Cleaned**
   - Symptom: CopyLock exists with `expires_at < now`, but Copy status still `LOCKED`
   - Diagnosis: Check heartbeat mechanism
   ```python
   lock = CopyLock.objects.get(copy_id=copy_id)
   print(lock.expires_at < timezone.now())  # True = expired
   ```
   - Action: Force-release lock
   ```python
   lock.delete()
   from grading.services import GradingService
   GradingService._reconcile_lock_state(copy)
   ```

2. **User Didn't Release Lock (Browser Crash)**
   - Symptom: Lock is active, but user is not in application
   - Diagnosis: Check lock expiration time (should auto-expire in 10 minutes)
   - Action: Wait for automatic expiration, or force-release if urgent

3. **Heartbeat Failing (Frontend Issue)**
   - Symptom: Lock expires prematurely (before 10 minutes)
   - Diagnosis: Check frontend heartbeat requests (network logs)
   - Action: Fix frontend heartbeat implementation

4. **Concurrent Lock Acquisition (Race Condition)**
   - Symptom: Two users get lock simultaneously (before P0-DI-001 fix)
   - Diagnosis: Check for duplicate LOCK events
   ```python
   lock_events = GradingEvent.objects.filter(
       copy_id=copy_id, 
       action='LOCK'
   ).order_by('created_at')
   # Should only see one LOCK event per lock/unlock cycle
   ```
   - Action: Verify `select_for_update()` is used (should be fixed in P0-DI-001)

5. **Token Mismatch (Client-Side Issue)**
   - Symptom: Error message "Invalid lock token"
   - Diagnosis: Check if client is sending correct X-Lock-Token header
   - Action: Instruct user to refresh page, re-acquire lock

### Actions

**Immediate**:
1. Force-release expired locks:
   ```python
   from grading.models import CopyLock
   from django.utils import timezone
   
   expired_locks = CopyLock.objects.filter(expires_at__lt=timezone.now())
   print(f"Deleting {expired_locks.count()} expired locks")
   expired_locks.delete()
   ```

2. Check for locks older than 1 hour (likely abandoned):
   ```python
   old_locks = CopyLock.objects.filter(
       created_at__lt=timezone.now() - timedelta(hours=1)
   )
   for lock in old_locks:
       print(f"Copy {lock.copy.id} locked by {lock.owner.username} for {timezone.now() - lock.created_at}")
   ```

**Short-term** (Next 24 hours):
1. Monitor lock conflict metrics
2. Set up alerts for `conflict_type="already_locked"` > 10/hour
3. Review heartbeat implementation in frontend

**Long-term**:
1. Implement automatic lock cleanup (Celery periodic task)
2. Add "Force Unlock" button in admin UI for support
3. Reduce lock TTL from 10 minutes to 5 minutes (faster recovery)

---

## Scenario 4: High Latency (Slow Response Times)

### Symptoms
- API requests taking >5 seconds
- Users report "Application is slow"
- Timeout errors (HTTP 504 Gateway Timeout)
- Prometheus metrics show `http_request_duration_seconds` p95 > 5s

### Diagnosis

#### Step 1: Check Prometheus Metrics
```bash
# Check request duration histogram
curl http://localhost:8088/metrics | grep http_request_duration_seconds

# Look for high p95/p99 percentiles
# Example output:
# http_request_duration_seconds_bucket{method="POST",path="/api/copies/{id}/finalize/",status="200",le="5.0"} 45
# http_request_duration_seconds_bucket{method="POST",path="/api/copies/{id}/finalize/",status="200",le="+Inf"} 52
# ^ 7 requests took >5 seconds!
```

#### Step 2: Check Database Query Times
```bash
# Enable PostgreSQL slow query logging
docker-compose exec db psql -U postgres -d korrigo

# Check slow queries (>1s)
SELECT query, calls, total_time, mean_time 
FROM pg_stat_statements 
WHERE mean_time > 1000 
ORDER BY total_time DESC 
LIMIT 10;

# Check for lock contention
SELECT * FROM pg_locks WHERE NOT granted;
```

#### Step 3: Check Active Database Connections
```python
from django.db import connection

# Show active queries
with connection.cursor() as cursor:
    cursor.execute("""
        SELECT pid, usename, state, query_start, 
               now() - query_start AS duration,
               left(query, 100) AS query
        FROM pg_stat_activity
        WHERE state != 'idle'
        ORDER BY duration DESC;
    """)
    for row in cursor.fetchall():
        print(row)
```

#### Step 4: Check Celery Queue Backlog
```bash
# Check Celery queue length (Redis)
docker-compose exec redis redis-cli

# Count pending tasks
LLEN celery

# Expected: <10 for normal operation
# If >100, Celery worker is overwhelmed
```

#### Step 5: Check Application Logs for Slow Operations
```bash
# Check for import/finalize operations (naturally slow)
grep "Starting async" logs/django.log | tail -20

# Check for retries (indicate failures)
grep "attempt" logs/django.log | tail -20
```

### Root Causes

1. **Database Lock Contention**
   - Symptom: Multiple `select_for_update()` on same Copy
   - Diagnosis: Check `pg_locks` for waiting queries
   - Action: Optimize query patterns, reduce lock hold time

2. **Large PDF Processing (Import/Finalize)**
   - Symptom: Requests to `/api/copies/{id}/finalize/` take >30s
   - Diagnosis: Check PDF page count
   ```python
   copy.booklets.first().pages_images  # >50 pages = slow
   ```
   - Action: Move to async task (should already be in Celery for P0-OP-03)

3. **High Load (Too Many Concurrent Users)**
   - Symptom: All endpoints slow, database connections maxed out
   - Diagnosis: Check active connections
   ```sql
   SELECT count(*) FROM pg_stat_activity WHERE state != 'idle';
   -- If >50, database is overwhelmed
   ```
   - Action: Scale horizontally (add more backend workers)

4. **Missing Database Indexes**
   - Symptom: Queries on `Copy.status`, `CopyLock.expires_at` are slow
   - Diagnosis: Check query plan
   ```sql
   EXPLAIN ANALYZE SELECT * FROM exams_copy WHERE status = 'READY';
   -- Look for "Seq Scan" (bad) vs "Index Scan" (good)
   ```
   - Action: Add indexes via Django migration

5. **Celery Worker Starvation**
   - Symptom: Tasks queued but not executing
   - Diagnosis: Check Celery worker count
   ```bash
   docker-compose ps celery
   # Check concurrency setting (default: 4 workers)
   ```
   - Action: Increase Celery concurrency

### Actions

**Immediate**:
1. Check for blocking queries:
   ```sql
   SELECT * FROM pg_locks WHERE NOT granted;
   ```
2. Kill long-running queries if safe:
   ```sql
   SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE state != 'idle' AND query_start < now() - interval '5 minutes';
   ```
3. Restart Celery workers: `docker-compose restart celery`

**Short-term** (Next 24 hours):
1. Add database indexes for frequently queried fields
2. Monitor Prometheus metrics for latency trends
3. Set up alerts for p95 > 3 seconds

**Long-term**:
1. Implement query optimization (select_related, prefetch_related)
2. Add database read replicas for queries
3. Implement caching for frequently accessed data (Redis)
4. Scale horizontally (load balancer + multiple backend instances)

---

## Scenario 5: Missing Audit Events (Events Not Recorded)

### Symptoms
- Expected GradingEvent not found in database
- Audit trail incomplete (missing IMPORT, CREATE_ANN, or FINALIZE events)
- Compliance reports show gaps in event log
- `GradingEvent.objects.filter(copy=copy).count()` < expected

### Diagnosis

#### Step 1: Check Expected vs Actual Events
```python
from exams.models import Copy
from grading.models import GradingEvent

# Check specific copy
copy = Copy.objects.get(id='e5f6g7h8-...')

# Expected workflow: IMPORT → VALIDATE → LOCK → CREATE_ANN → FINALIZE
events = GradingEvent.objects.filter(copy=copy).order_by('created_at')

print(f"Total events: {events.count()}")
for event in events:
    print(f"{event.created_at}: {event.action} by {event.actor.username}")

# Check for missing events
expected_actions = ['IMPORT', 'VALIDATE', 'LOCK', 'CREATE_ANN', 'FINALIZE']
actual_actions = [e.action for e in events]
missing = set(expected_actions) - set(actual_actions)
print(f"Missing events: {missing}")
```

#### Step 2: Check for Transaction Rollbacks
```bash
# Check logs for exceptions that caused rollback
grep "Traceback" logs/django.log | grep -B 10 -A 10 "GradingEvent"

# Check for database errors
grep "IntegrityError\|DatabaseError" logs/django.log | tail -20
```

#### Step 3: Check Application Code for Event Creation
```bash
# Verify event creation in services.py
grep "GradingEvent.objects.create" backend/grading/services.py

# Expected locations:
# - import_pdf() line 416
# - add_annotation() line 113
# - finalize_copy() line 584/599
```

#### Step 4: Check Database Constraints
```python
from grading.models import GradingEvent

# Check if events are being created but deleted
# (should not happen - audit events are immutable)

# Check for duplicate events (idempotency issue)
from django.db.models import Count
duplicates = GradingEvent.objects.values('copy', 'action', 'actor').annotate(
    count=Count('id')
).filter(count__gt=1)

print(f"Duplicate events: {duplicates.count()}")
```

### Root Causes

1. **Transaction Rollback (Exception Before Event Creation)**
   - Symptom: Exception in service method before `GradingEvent.objects.create()`
   - Diagnosis: Check exception stack trace
   ```bash
   grep "Import failed for copy" logs/django.log | grep -A 20 "Traceback"
   ```
   - Action: Fix underlying exception, ensure event creation happens early

2. **Exception During Event Creation**
   - Symptom: Logs show `IntegrityError` or `DatabaseError` at event creation
   - Diagnosis: Check for null constraints, foreign key issues
   ```python
   # Try creating event manually
   GradingEvent.objects.create(
       copy=copy,
       action='IMPORT',
       actor=user,
       metadata={'test': 'manual'}
   )
   ```
   - Action: Fix data model issues, ensure all required fields provided

3. **Idempotency Issue (get_or_create Not Used)**
   - Symptom: Duplicate FINALIZE events (before P0-DI-007 fix)
   - Diagnosis: Check for multiple events with same action
   ```python
   finalize_events = GradingEvent.objects.filter(
       copy=copy, 
       action='FINALIZE'
   )
   print(f"Finalize events: {finalize_events.count()}")  # Should be 1
   ```
   - Action: Verify `get_or_create` is used for FINALIZE (line 584)

4. **Missing Event Creation Code**
   - Symptom: Code path doesn't create event (regression)
   - Diagnosis: Review service code for event creation
   ```bash
   # Check if event creation was accidentally removed
   git log -p backend/grading/services.py | grep "GradingEvent.objects.create"
   ```
   - Action: Restore event creation code, add test coverage

5. **Permission Denied (Actor Not Provided)**
   - Symptom: Event creation raises `IntegrityError: actor_id cannot be null`
   - Diagnosis: Check if `user` parameter is missing
   - Action: Ensure all service methods receive `user` parameter

### Actions

**Immediate**:
1. Check for recent exceptions:
   ```bash
   grep "ERROR\|Traceback" logs/django.log | tail -50
   ```

2. Verify event creation code is present:
   ```bash
   grep "GradingEvent.objects.create" backend/grading/services.py
   ```

3. Test event creation manually for affected copy

**Short-term** (Next 24 hours):
1. Review all GradingEvent creation sites for consistency
2. Add database constraints to enforce audit event creation (if possible)
3. Implement monitoring alert for missing events (Prometheus gauge)

**Long-term**:
1. Add comprehensive test coverage for all 9 GradingEvent actions
2. Implement event creation as a decorator/context manager (DRY)
3. Add automatic audit trail completeness check (Celery periodic task)
4. Consider event sourcing pattern for immutable audit trail

---

## Appendix A: Useful Queries

### Check System Health
```bash
# All services up
docker-compose ps

# Recent errors
docker-compose logs --tail=100 backend | grep ERROR

# Database connections
docker-compose exec db psql -U postgres -c "SELECT count(*) FROM pg_stat_activity;"
```

### Check Grading Workflow State
```python
from exams.models import Copy
from django.utils import timezone

# Copies by status
from django.db.models import Count
Copy.objects.values('status').annotate(count=Count('id'))

# Stuck copies (STAGING >10 minutes)
stuck = Copy.objects.filter(
    status='STAGING',
    created_at__lt=timezone.now() - timedelta(minutes=10)
)

# Failed copies (recent)
failed = Copy.objects.filter(
    status='GRADING_FAILED',
    updated_at__gte=timezone.now() - timedelta(hours=24)
)
```

### Check Locks
```python
from grading.models import CopyLock
from django.utils import timezone

# Active locks
active = CopyLock.objects.count()

# Expired locks (should be 0)
expired = CopyLock.objects.filter(expires_at__lt=timezone.now()).count()

# Old locks (>1 hour, likely abandoned)
old = CopyLock.objects.filter(
    created_at__lt=timezone.now() - timedelta(hours=1)
)
```

### Check Audit Events
```python
from grading.models import GradingEvent
from django.utils import timezone

# Events in last hour
recent = GradingEvent.objects.filter(
    created_at__gte=timezone.now() - timedelta(hours=1)
).count()

# Events by action type
from django.db.models import Count
GradingEvent.objects.values('action').annotate(count=Count('id'))

# Events for specific copy
copy_events = GradingEvent.objects.filter(
    copy_id='e5f6g7h8-...'
).order_by('created_at')
```

---

## Appendix B: Escalation Paths

### Severity Levels

**P0 - Critical** (Immediate escalation):
- All copies stuck (Celery worker down)
- Database down or corrupted
- Data loss or corruption
- Security breach

**P1 - High** (Escalate within 2 hours):
- Multiple copies stuck (>10)
- High error rate (>10% of requests failing)
- Performance degradation affecting all users

**P2 - Medium** (Escalate within 24 hours):
- Individual copy stuck
- Lock conflicts for specific user
- Missing audit events (isolated)

**P3 - Low** (Track in backlog):
- Slow response times (occasional)
- Expired locks (automatic cleanup works)

### Escalation Contacts
- **DevOps Lead**: [contact info]
- **Backend Lead**: [contact info]
- **Database Admin**: [contact info]
- **On-Call Engineer**: [pager/phone]

---

## Appendix C: Monitoring Dashboards

### Grafana Panels (Recommended)

**Grading Workflow Dashboard**:
1. Import Duration (p50, p95, p99) - by pages_bucket
2. Finalize Duration (p50, p95, p99) - by retry_attempt
3. OCR Errors Rate (errors/minute) - by error_type
4. Lock Conflicts Rate (conflicts/minute) - by conflict_type
5. Copies by Status (gauge) - STAGING, READY, LOCKED, GRADING_IN_PROGRESS, GRADED, GRADING_FAILED
6. Celery Queue Length (gauge)
7. Database Connection Count (gauge)
8. HTTP Request Latency (p95, p99)

### Alerting Rules (Recommended)

```yaml
# Prometheus alerting rules
groups:
  - name: grading_workflow
    rules:
      - alert: ImportStuck
        expr: grading_copies_by_status{status="STAGING"} > 10
        for: 5m
        annotations:
          summary: "More than 10 copies stuck in STAGING"
          
      - alert: FinalizationFailureHigh
        expr: rate(grading_finalize_duration_seconds_count{status="failed"}[5m]) > 0.1
        for: 5m
        annotations:
          summary: "Finalization failure rate > 10%"
          
      - alert: LockConflictsHigh
        expr: rate(grading_lock_conflicts_total[5m]) > 10
        for: 5m
        annotations:
          summary: "Lock conflicts > 10/5min"
          
      - alert: HighLatency
        expr: histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 5
        for: 5m
        annotations:
          summary: "API p95 latency > 5s"
```

---

**Document Version**: 1.0  
**Last Updated**: 2026-01-31  
**Next Review**: 2026-03-31  
**Maintained By**: DevOps Team
