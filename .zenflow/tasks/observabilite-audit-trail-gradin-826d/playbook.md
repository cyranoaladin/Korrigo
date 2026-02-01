# Incident Response Playbook - Grading System Observability

**Date**: 1 février 2026  
**Version**: 1.0  
**Status**: Complete  
**Audience**: Production Support, DevOps, SRE

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [Diagnostic Tools Reference](#2-diagnostic-tools-reference)
3. [Scenario 1: Import Stuck](#3-scenario-1-import-stuck)
4. [Scenario 2: Finalization Failing](#4-scenario-2-finalization-failing)
5. [Scenario 3: Lock Conflicts](#5-scenario-3-lock-conflicts)
6. [Scenario 4: High Latency](#6-scenario-4-high-latency)
7. [Scenario 5: Missing Audit Events](#7-scenario-5-missing-audit-events)
8. [Escalation Paths](#8-escalation-paths)

---

## 1. Introduction

### 1.1 Purpose

This playbook provides step-by-step diagnostic procedures for common production incidents in the grading system. Each scenario follows a consistent structure:

- **Symptoms**: Observable indicators reported by users or monitoring
- **Diagnosis**: Step-by-step investigation commands
- **Root Causes**: Common underlying issues
- **Actions**: Remediation steps and preventive measures

### 1.2 Prerequisites

**Access Required**:
- SSH access to production server
- Database read access (PostgreSQL)
- Log file access (`/path/to/backend/logs/`)
- Prometheus metrics endpoint (`http://localhost:8088/metrics`)
- Celery worker management (systemctl or supervisor)

**Tools Required**:
- `grep`, `jq` for log analysis
- `psql` or Django shell for database queries
- `curl` for metrics scraping
- `celery` CLI for queue inspection

### 1.3 Log Correlation

All logs include a **request_id** (UUID) for correlation:

```json
{
  "timestamp": "2026-02-01T14:30:45.123Z",
  "level": "INFO",
  "logger": "grading",
  "message": "Starting async finalization for copy...",
  "request_id": "a1b2c3d4-5678-90ab-cdef-1234567890ab",
  "user_id": 42
}
```

Use `request_id` to trace a request from HTTP entry → service layer → Celery task.

---

## 2. Diagnostic Tools Reference

### 2.1 Log Files

| File | Content | Rotation |
|------|---------|----------|
| `logs/django.log` | General application logs (grading, processing, exams) | 10MB × 10 backups |
| `logs/audit.log` | Audit trail (GradingEvent creation) | 10MB × 10 backups |

**Log Format**:
- **Development**: Human-readable verbose format
- **Production**: Structured JSON (ViatiqueJSONFormatter)

### 2.2 Database Tables

| Table | Purpose | Key Fields |
|-------|---------|------------|
| `grading_gradingevent` | Audit trail of workflow actions | `copy_id`, `action`, `timestamp`, `metadata` |
| `exams_copy` | Copy state and status | `id`, `status`, `anonymous_id`, `final_score` |
| `grading_copylock` | Active locks on copies | `copy_id`, `locked_by_id`, `expires_at`, `token` |
| `grading_annotation` | Annotations on copies | `copy_id`, `page`, `score` |

### 2.3 Prometheus Metrics

**Current Metrics** (HTTP-level):
- `http_requests_total{method, path, status}`
- `http_request_duration_seconds{method, path}`
- Process metrics (CPU, memory, GC)

**Missing Metrics** (domain-specific - see audit.md):
- `grading_import_duration_seconds`
- `grading_finalize_duration_seconds`
- `grading_lock_conflicts_total`
- `grading_copies_by_status`

### 2.4 Celery Queues

**Tasks**:
- `grading.tasks.async_finalize_copy` - Background PDF finalization (3 retries)
- `grading.tasks.async_import_pdf` - Background PDF rasterization

**Inspection Commands**:
```bash
# Check active tasks
celery -A core inspect active

# Check scheduled tasks
celery -A core inspect scheduled

# Check registered tasks
celery -A core inspect registered

# Purge queue (DANGER: use only in emergencies)
celery -A core purge
```

---

## 3. Scenario 1: Import Stuck

### 3.1 Symptoms

- User uploads PDF but copy remains in `STAGING` status
- No pages appear in copy after several minutes
- Import progress indicator stalled at 0%

### 3.2 Diagnosis

**Step 1: Identify the affected copy**

```bash
# Search logs for recent import attempts
grep -E "import_pdf|IMPORT" logs/django.log | tail -50

# Look for copy_id and user_id in the logs
```

**Step 2: Check copy status in database**

```python
# Django shell
from exams.models import Copy

copy = Copy.objects.get(id='<copy_id>')
print(f"Status: {copy.status}")
print(f"Booklets: {copy.booklets.count()}")
print(f"Total pages: {sum(len(b.pages_images or []) for b in copy.booklets.all())}")
```

**Step 3: Check for IMPORT event**

```python
from grading.models import GradingEvent

events = GradingEvent.objects.filter(
    copy_id='<copy_id>',
    action='IMPORT'
).order_by('-timestamp')

for event in events:
    print(f"{event.timestamp} - {event.metadata}")
```

**Step 4: Check Celery task status**

```bash
# Check if async_import_pdf task is running or failed
celery -A core inspect active | grep async_import_pdf

# Check worker logs for exceptions
grep "async_import_pdf" logs/django.log | grep -E "ERROR|CRITICAL"
```

**Step 5: Check for PDF processing errors**

```bash
# Search for OCR/rasterization errors
grep -E "rasterize|OCR|PyMuPDF|fitz" logs/django.log | grep ERROR

# Check for file permission issues
grep -E "PermissionError|FileNotFoundError" logs/django.log
```

### 3.3 Root Causes

| Root Cause | Indicators | Frequency |
|------------|------------|-----------|
| **Celery worker down** | No active tasks, worker not responding | Common |
| **OCR timeout** | Task killed after 10+ minutes | Rare (large PDFs) |
| **Corrupted PDF** | PyMuPDF exception in logs | Occasional |
| **Disk space exhausted** | OSError in logs, /tmp full | Rare |
| **Memory exhaustion** | Worker killed by OOM | Rare (very large PDFs) |

### 3.4 Actions

**Action 1: Restart Celery worker** (if worker down)

```bash
# Check worker status
systemctl status celery-worker
# or
supervisorctl status celery

# Restart worker
sudo systemctl restart celery-worker
# or
supervisorctl restart celery

# Verify worker is running
celery -A core inspect ping
```

**Action 2: Retry import** (if task failed)

```python
# Django shell
from exams.models import Copy
from grading.tasks import async_import_pdf

copy = Copy.objects.get(id='<copy_id>')
user_id = <user_id>

# Re-trigger async import
async_import_pdf.delay(copy_id=str(copy.id), user_id=user_id)
```

**Action 3: Check disk space**

```bash
df -h
du -sh /tmp/*
du -sh /var/lib/postgresql/*
```

**Action 4: Validate PDF manually**

```bash
# Try to open PDF with PyMuPDF
python3 << EOF
import fitz
doc = fitz.open('/path/to/uploaded/file.pdf')
print(f"Pages: {doc.page_count}")
doc.close()
EOF
```

**Preventive Measures**:
- Monitor Celery worker health (add heartbeat check)
- Add timeout for OCR operations (configurable per exam)
- Validate PDF on upload (page count, file size limits)
- Implement `grading_import_duration_seconds` metric for alerting

---

## 4. Scenario 2: Finalization Failing

### 4.1 Symptoms

- Copy status stuck in `LOCKED` after finalization attempt
- User receives "Finalization failed" error
- Final PDF not generated (`final_copy_pdf` field is null)

### 4.2 Diagnosis

**Step 1: Check copy status and final PDF**

```python
# Django shell
from exams.models import Copy

copy = Copy.objects.get(id='<copy_id>')
print(f"Status: {copy.status}")
print(f"Final score: {copy.final_score}")
print(f"Final PDF: {copy.final_copy_pdf}")
```

**Step 2: Check FINALIZE events**

```python
from grading.models import GradingEvent

events = GradingEvent.objects.filter(
    copy_id='<copy_id>',
    action='FINALIZE'
).order_by('-timestamp')

for event in events:
    metadata = event.metadata
    print(f"{event.timestamp} - success: {metadata.get('success')}, retries: {metadata.get('retries')}")
    if 'error' in metadata:
        print(f"  Error: {metadata['error']}")
```

**Step 3: Check finalization logs**

```bash
# Search for finalization errors for specific copy
grep "<copy_id>" logs/django.log | grep -E "finalize|FINALIZE" | tail -50

# Look for PyMuPDF errors
grep "finalize" logs/django.log | grep -E "ERROR|CRITICAL|exc_info"
```

**Step 4: Check Celery task retries**

```bash
# Search for async_finalize_copy task
grep "async_finalize_copy" logs/django.log | grep "<copy_id>"

# Check for retry attempts
grep "attempt" logs/django.log | grep "<copy_id>"
```

**Step 5: Check lock status**

```python
from grading.models import CopyLock

try:
    lock = CopyLock.objects.get(copy_id='<copy_id>')
    print(f"Locked by: {lock.locked_by_id}")
    print(f"Expires at: {lock.expires_at}")
    print(f"Is expired: {lock.is_expired()}")
except CopyLock.DoesNotExist:
    print("No active lock")
```

### 4.3 Root Causes

| Root Cause | Indicators | Frequency |
|------------|------------|-----------|
| **PyMuPDF error** | Exception in `flatten_pdf_with_annotations()` | Common |
| **Missing annotations** | Annotations deleted during finalization | Rare |
| **Lock token mismatch** | Lock verification failed | Occasional |
| **Disk space full** | Cannot write final PDF to storage | Rare |
| **Memory error** | Large PDF causes OOM during flattening | Occasional |

### 4.4 Actions

**Action 1: Check PyMuPDF exception details**

```bash
# Extract full stack trace
grep -A 20 "async_finalize_copy.*ERROR" logs/django.log | grep -A 20 "<copy_id>"
```

**Action 2: Verify annotations exist**

```python
from grading.models import Annotation

annotations = Annotation.objects.filter(copy_id='<copy_id>')
print(f"Annotation count: {annotations.count()}")
for ann in annotations:
    print(f"  Page {ann.page}: {ann.annotation_type} = {ann.score} points")
```

**Action 3: Clear stale lock** (if lock expired)

```python
from grading.models import CopyLock

try:
    lock = CopyLock.objects.get(copy_id='<copy_id>')
    if lock.is_expired():
        lock.delete()
        print("Stale lock cleared")
    else:
        print(f"Lock still valid, expires at {lock.expires_at}")
except CopyLock.DoesNotExist:
    print("No lock found")
```

**Action 4: Retry finalization** (after clearing lock)

```python
from exams.models import Copy
from grading.tasks import async_finalize_copy
from django.contrib.auth import get_user_model

User = get_user_model()

copy = Copy.objects.get(id='<copy_id>')
user = User.objects.get(id='<user_id>')

# Trigger finalization without lock token (will fail if locked)
async_finalize_copy.delay(
    copy_id=str(copy.id),
    user_id=user.id,
    lock_token=None
)
```

**Action 5: Manual finalization** (emergency only)

```python
from grading.services import GradingService
from exams.models import Copy
from django.contrib.auth import get_user_model

User = get_user_model()

copy = Copy.objects.get(id='<copy_id>')
user = User.objects.get(id='<user_id>')

# Clear lock if needed
CopyLock.objects.filter(copy=copy).delete()

# Synchronous finalization (use with caution in production)
finalized_copy = GradingService.finalize_copy(copy, user, lock_token=None)
print(f"Finalized: {finalized_copy.final_score} points")
```

**Preventive Measures**:
- Implement `grading_finalize_duration_seconds` metric with alerting on P95 > 60s
- Add automatic lock cleanup cron job (clear locks older than 1 hour)
- Test PDF flattening with sample PDFs of different sizes
- Add retry logic with exponential backoff

---

## 5. Scenario 3: Lock Conflicts

### 5.1 Symptoms

- User cannot edit copy, receives "Copy is locked by another user"
- Copy appears locked in UI but no one is editing
- Lock conflicts reported in logs

### 5.2 Diagnosis

**Step 1: Check active locks**

```python
# Django shell
from grading.models import CopyLock
from django.utils import timezone

# All active locks
locks = CopyLock.objects.all()
for lock in locks:
    print(f"Copy {lock.copy.anonymous_id} locked by user {lock.locked_by_id}")
    print(f"  Expires: {lock.expires_at}")
    print(f"  Expired: {lock.is_expired()}")
```

**Step 2: Check lock for specific copy**

```python
from grading.models import CopyLock

try:
    lock = CopyLock.objects.get(copy_id='<copy_id>')
    print(f"Locked by: {lock.locked_by.username} (ID: {lock.locked_by_id})")
    print(f"Locked at: {lock.created_at}")
    print(f"Expires at: {lock.expires_at}")
    print(f"Token prefix: {lock.token[:8]}...")
    print(f"Is expired: {lock.is_expired()}")
except CopyLock.DoesNotExist:
    print("No active lock - copy should be editable")
```

**Step 3: Check lock conflict events**

```python
from grading.models import GradingEvent

events = GradingEvent.objects.filter(
    copy_id='<copy_id>',
    action__in=['LOCK', 'UNLOCK']
).order_by('-timestamp')[:20]

for event in events:
    print(f"{event.timestamp} - {event.action} by user {event.actor_id}")
    print(f"  Metadata: {event.metadata}")
```

**Step 4: Check lock conflict logs**

```bash
# Search for lock conflicts
grep -E "LockConflictError|already_locked|lock conflict" logs/django.log | tail -30

# Check warnings for lock-related issues
grep -E "LOCK|UNLOCK" logs/django.log | grep WARNING
```

**Step 5: Identify lock expiration issues**

```python
from grading.models import CopyLock
from django.utils import timezone
from datetime import timedelta

# Find expired locks still in database
expired_locks = CopyLock.objects.filter(
    expires_at__lt=timezone.now()
)
print(f"Expired locks: {expired_locks.count()}")
for lock in expired_locks:
    age = timezone.now() - lock.expires_at
    print(f"  Copy {lock.copy.anonymous_id}: expired {age} ago")
```

### 5.3 Root Causes

| Root Cause | Indicators | Frequency |
|------------|------------|-----------|
| **Expired lock not cleaned** | Lock exists with `expires_at < now()` | Common |
| **Client didn't unlock** | User closed browser without unlocking | Very Common |
| **Token mismatch** | Unlock attempted with wrong token | Occasional |
| **Race condition** | Two users locked simultaneously | Rare |
| **Lock cleanup cron failed** | Many expired locks in database | Rare |

### 5.4 Actions

**Action 1: Clear expired locks**

```python
from grading.models import CopyLock
from django.utils import timezone

expired_locks = CopyLock.objects.filter(
    expires_at__lt=timezone.now()
)
count = expired_locks.count()
expired_locks.delete()
print(f"Cleared {count} expired locks")
```

**Action 2: Force unlock specific copy** (emergency only)

```python
from grading.models import CopyLock

lock = CopyLock.objects.filter(copy_id='<copy_id>')
if lock.exists():
    lock.delete()
    print("Lock forcibly removed")
else:
    print("No lock found")
```

**Action 3: Check for lock cleanup task**

```bash
# Check if lock cleanup cron job exists
crontab -l | grep lock

# If not, create cleanup script
# /opt/grading/scripts/cleanup_expired_locks.py
```

**Action 4: Investigate race conditions** (if multiple locks created)

```bash
# Check for simultaneous LOCK events
grep "LOCK" logs/django.log | grep "<copy_id>" | grep -A 5 -B 5 "already_locked"
```

**Action 5: Add lock conflict metric** (proactive monitoring)

```python
# Add to grading/metrics.py (when implemented)
# grading_lock_conflicts_total.labels(conflict_type='already_locked').inc()
# grading_lock_conflicts_total.labels(conflict_type='expired').inc()
# grading_lock_conflicts_total.labels(conflict_type='token_mismatch').inc()
```

**Preventive Measures**:
- Implement scheduled lock cleanup task (every 5 minutes)
- Add client-side heartbeat to extend lock expiration
- Implement `grading_lock_conflicts_total` counter for monitoring
- Add lock age gauge to track oldest lock in system
- Document lock lifecycle in operator runbook

---

## 6. Scenario 4: High Latency

### 6.1 Symptoms

- Users report slow page loads (> 5 seconds)
- PDF finalization takes > 2 minutes
- Database query timeouts in logs
- HTTP 504 Gateway Timeout errors

### 6.2 Diagnosis

**Step 1: Check Prometheus HTTP metrics**

```bash
# Scrape metrics endpoint
curl http://localhost:8088/metrics | grep http_request_duration_seconds

# Look for P95/P99 latencies
# http_request_duration_seconds{method="POST",path="/api/copies/finalize/",quantile="0.95"} 12.5
```

**Step 2: Identify slow endpoints**

```bash
# Search for slow requests in logs (assuming duration logged)
grep -E "duration|took|elapsed" logs/django.log | awk '{if ($NF > 5) print}'

# Check for database query timeouts
grep -E "timeout|too long|slow query" logs/django.log
```

**Step 3: Check database performance**

```sql
-- PostgreSQL slow query log
-- Requires: log_min_duration_statement = 1000 (1 second) in postgresql.conf

-- Check active queries
SELECT pid, now() - pg_stat_activity.query_start AS duration, query
FROM pg_stat_activity
WHERE state = 'active'
ORDER BY duration DESC;

-- Check database size
SELECT pg_size_pretty(pg_database_size('viatique'));

-- Check table sizes
SELECT schemaname, tablename, pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
LIMIT 10;
```

**Step 4: Check for N+1 queries**

```python
# Django shell - enable query logging
from django.db import connection
from django.test.utils import override_settings

with override_settings(DEBUG=True):
    from exams.models import Copy
    copies = Copy.objects.all()[:10]
    for copy in copies:
        _ = copy.booklets.all()  # Potential N+1
    print(f"Queries executed: {len(connection.queries)}")
    for q in connection.queries:
        print(f"{q['time']}s: {q['sql'][:100]}")
```

**Step 5: Check Celery queue backlog**

```bash
# Check queue length
celery -A core inspect active | grep -c "async_finalize_copy"

# Check if workers are overwhelmed
celery -A core inspect stats
```

### 6.3 Root Causes

| Root Cause | Indicators | Frequency |
|------------|------------|-----------|
| **N+1 query problem** | Many identical queries in logs | Common |
| **Missing database index** | Sequential scans in query plan | Occasional |
| **Large PDF processing** | Finalization > 60s | Occasional |
| **Celery queue backlog** | > 50 tasks waiting | Rare |
| **Insufficient workers** | All workers busy | Occasional |
| **Database connection exhaustion** | "too many clients" error | Rare |

### 6.4 Actions

**Action 1: Identify slow queries**

```bash
# Enable PostgreSQL slow query log
# Edit /etc/postgresql/.../postgresql.conf
# log_min_duration_statement = 1000  # Log queries > 1s

# Restart PostgreSQL
sudo systemctl restart postgresql

# Monitor slow query log
tail -f /var/log/postgresql/postgresql-*.log | grep "duration:"
```

**Action 2: Analyze query plans**

```sql
-- Get query plan for slow query
EXPLAIN ANALYZE
SELECT * FROM exams_copy
WHERE status = 'LOCKED'
ORDER BY created_at DESC;

-- Look for "Seq Scan" (bad) vs "Index Scan" (good)
```

**Action 3: Add missing indexes**

```python
# Django shell - check existing indexes
from django.db import connection
cursor = connection.cursor()
cursor.execute("""
    SELECT indexname, tablename, indexdef
    FROM pg_indexes
    WHERE schemaname = 'public'
    AND tablename LIKE '%copy%';
""")
for row in cursor.fetchall():
    print(row)
```

**Action 4: Optimize N+1 queries with select_related/prefetch_related**

```python
# Bad: N+1 queries
copies = Copy.objects.all()
for copy in copies:
    print(copy.exam.title)  # N queries

# Good: 1 query with JOIN
copies = Copy.objects.select_related('exam').all()
for copy in copies:
    print(copy.exam.title)  # No extra queries
```

**Action 5: Scale Celery workers**

```bash
# Check current worker count
celery -A core inspect stats | grep concurrency

# Increase worker concurrency (temporary)
celery -A core worker --concurrency=8

# Permanent: Edit systemd service or supervisor config
# ExecStart=/usr/bin/celery -A core worker --concurrency=8
```

**Action 6: Add database connection pooling**

```python
# settings.py - add pgbouncer or increase CONN_MAX_AGE
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'CONN_MAX_AGE': 600,  # 10 minutes
        # ... other settings
    }
}
```

**Preventive Measures**:
- Implement `grading_finalize_duration_seconds` histogram with P95/P99 alerting
- Add database query monitoring (django-silk or django-debug-toolbar in staging)
- Create database index review checklist
- Set up automatic query plan analysis for slow endpoints
- Monitor Celery queue length with alerting

---

## 7. Scenario 5: Missing Audit Events

### 7.1 Symptoms

- GradingEvent missing for known workflow action
- Audit log incomplete when investigating user action
- Event timeline has gaps (e.g., IMPORT → FINALIZE without LOCK)

### 7.2 Diagnosis

**Step 1: Verify expected events exist**

```python
# Django shell
from grading.models import GradingEvent

# Check all events for a copy
events = GradingEvent.objects.filter(
    copy_id='<copy_id>'
).order_by('timestamp')

print(f"Total events: {events.count()}")
for event in events:
    print(f"{event.timestamp} - {event.action} by user {event.actor_id}")
```

**Step 2: Check audit log file**

```bash
# Search audit.log for specific copy
grep "<copy_id>" logs/audit.log

# Check for event creation logs
grep "GradingEvent" logs/django.log | grep "<copy_id>"
```

**Step 3: Identify missing event types**

```python
from grading.models import GradingEvent
from django.db.models import Count

# Count events by action type
event_counts = GradingEvent.objects.values('action').annotate(count=Count('id'))
for ec in event_counts:
    print(f"{ec['action']}: {ec['count']}")

# Check if specific action type is never recorded
missing_actions = set(GradingEvent.Action.values) - set(event_counts.values_list('action', flat=True))
if missing_actions:
    print(f"Never recorded: {missing_actions}")
```

**Step 4: Check for transaction rollbacks**

```bash
# Search for database errors during event creation
grep -E "transaction.*aborted|IntegrityError|OperationalError" logs/django.log | tail -20

# Check for rollback logs
grep -E "rollback|transaction.*failed" logs/django.log
```

**Step 5: Verify event creation in code**

```bash
# Find all GradingEvent.objects.create() calls
grep -rn "GradingEvent.objects.create" backend/grading/

# Expected locations:
# - services.py:116 (CREATE_ANN)
# - services.py:166 (UPDATE_ANN)
# - services.py:187 (DELETE_ANN)
# - services.py:289 (LOCK)
# - services.py:346 (UNLOCK)
# - services.py:419 (IMPORT)
# - services.py:477 (VALIDATE)
# - services.py:587 (FINALIZE)
```

### 7.3 Root Causes

| Root Cause | Indicators | Frequency |
|------------|------------|-----------|
| **Transaction rollback** | Database error in logs | Occasional |
| **Exception before event creation** | Service method failed early | Common |
| **Missing event creation call** | Code path doesn't create event | Rare (regression) |
| **Duplicate key error** | GradingEvent UUID collision | Extremely Rare |
| **Database constraint violation** | Foreign key or NOT NULL error | Rare |

### 7.4 Actions

**Action 1: Check for exceptions in service layer**

```bash
# Find exceptions during workflow actions
grep -E "ERROR|CRITICAL" logs/django.log | grep -E "import_pdf|finalize_copy|add_annotation"

# Look for stack traces
grep -A 10 "exc_info" logs/django.log
```

**Action 2: Verify transaction boundaries**

```python
# Check if event creation is inside @transaction.atomic
# services.py example:

from django.db import transaction

@transaction.atomic
def finalize_copy(copy, user, lock_token=None):
    # ... validation logic ...
    
    # Event creation MUST be inside transaction
    GradingEvent.objects.create(
        copy=copy,
        action=GradingEvent.Action.FINALIZE,
        actor=user,
        metadata={'final_score': final_score}
    )
    
    return copy
```

**Action 3: Manually create missing event** (data correction only)

```python
from grading.models import GradingEvent
from exams.models import Copy
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()

copy = Copy.objects.get(id='<copy_id>')
user = User.objects.get(id='<user_id>')

# Create missing IMPORT event (example)
GradingEvent.objects.create(
    copy=copy,
    action=GradingEvent.Action.IMPORT,
    actor=user,
    timestamp=timezone.now(),  # Will be auto-set
    metadata={'filename': 'reconstructed', 'pages': 10}
)
print("Event created manually for data correction")
```

**Action 4: Check event creation during testing**

```bash
# Run audit event tests
pytest backend/grading/tests/test_audit_events.py -v

# Expected tests:
# - test_import_creates_audit_event
# - test_create_annotation_creates_audit_event
# - test_finalize_creates_audit_event_success
# - test_finalize_creates_audit_event_failure
```

**Action 5: Add event creation verification**

```python
# Add assertion in service methods
def finalize_copy(copy, user, lock_token=None):
    # ... finalization logic ...
    
    event = GradingEvent.objects.create(
        copy=copy,
        action=GradingEvent.Action.FINALIZE,
        actor=user,
        metadata={'final_score': final_score, 'success': True}
    )
    
    # Verify event was persisted
    assert event.pk is not None
    logger.info(f"FINALIZE event created: {event.id}")
    
    return copy
```

**Preventive Measures**:
- Add unit tests for event creation in all workflow actions
- Implement event creation counter metric: `grading_events_created_total{action}`
- Add database constraint checks in CI/CD pipeline
- Monitor audit log completeness with scheduled verification job
- Document event creation requirements in developer guide

---

## 8. Escalation Paths

### 8.1 Severity Levels

| Severity | Definition | Response Time | Example |
|----------|-----------|---------------|---------|
| **P0 - Critical** | Complete system outage, data loss risk | < 15 minutes | Database down, all workers crashed |
| **P1 - High** | Major feature broken, many users affected | < 1 hour | All finalizations failing, import broken |
| **P2 - Medium** | Feature degraded, few users affected | < 4 hours | Single copy stuck, lock conflict |
| **P3 - Low** | Minor issue, workaround available | < 24 hours | Slow query, missing audit event |

### 8.2 Escalation Contacts

**First Responder** (Production Support):
- Check this playbook for known scenarios
- Gather diagnostic information
- Attempt remediation actions

**Escalate to Development Team** if:
- Scenario not covered in playbook
- Remediation actions fail after 2 attempts
- Data corruption suspected
- Security incident detected

**Escalate to Database Admin** if:
- Database connection issues
- Slow queries not resolved by index creation
- Database disk space > 90%
- Replication lag detected

### 8.3 Communication Template

**Incident Report**:
```
Subject: [P{severity}] {Brief Description}

Incident ID: INC-{timestamp}
Severity: P{0-3}
Start Time: {YYYY-MM-DD HH:MM:SS UTC}
Affected Users: {count or "all"}

Symptoms:
- {observable symptom 1}
- {observable symptom 2}

Investigation:
- {diagnostic step 1 result}
- {diagnostic step 2 result}

Actions Taken:
- {remediation attempt 1}
- {remediation attempt 2}

Current Status: {ongoing/resolved/escalated}
Next Steps: {what will happen next}

Diagnostic Data:
- Request ID: {request_id}
- Copy ID: {copy_id}
- User ID: {user_id}
- Logs: {attachment or link}
```

### 8.4 Post-Incident Review

After resolving a P0/P1 incident:

1. **Document root cause** in incident report
2. **Update playbook** if new scenario discovered
3. **Add monitoring** to detect similar issues earlier
4. **Create preventive tasks** in backlog
5. **Conduct blameless postmortem** with team

**Postmortem Template**:
- Timeline of events
- Root cause analysis (5 Whys)
- What went well
- What went poorly
- Action items (with owners and due dates)

---

## Appendix A: Useful Commands Cheat Sheet

### A.1 Log Analysis

```bash
# Find all logs for a request_id
grep "{request_id}" logs/django.log

# Find all logs for a copy_id
grep "{copy_id}" logs/django.log

# Find all ERROR logs in last hour
find logs/ -name "*.log" -mmin -60 -exec grep -H "ERROR" {} \;

# Count events by level
grep -o '"level":"[A-Z]*"' logs/django.log | sort | uniq -c

# Extract all request_ids from last 100 lines
tail -100 logs/django.log | grep -o '"request_id":"[^"]*"' | sort | uniq
```

### A.2 Database Queries

```python
# Django shell quick queries
from exams.models import Copy
from grading.models import GradingEvent, CopyLock

# Count copies by status
Copy.objects.values('status').annotate(count=Count('id'))

# Find copies without events
Copy.objects.exclude(grading_events__isnull=False).count()

# Find oldest locked copy
CopyLock.objects.order_by('created_at').first()

# Event timeline for copy
GradingEvent.objects.filter(copy_id='...').order_by('timestamp').values('timestamp', 'action', 'actor__username')
```

### A.3 Metrics Queries

```bash
# Scrape all metrics
curl -s http://localhost:8088/metrics

# Filter HTTP request metrics
curl -s http://localhost:8088/metrics | grep http_requests_total

# Calculate request rate (5-minute window)
curl -s http://localhost:8088/metrics | grep http_requests_total | awk '{print $NF}'

# Check process memory
curl -s http://localhost:8088/metrics | grep process_resident_memory_bytes
```

---

## Appendix B: Cross-References

### B.1 Related Documentation

- **Technical Specification**: `.zenflow/tasks/observabilite-audit-trail-gradin-826d/spec.md`
- **Requirements**: `.zenflow/tasks/observabilite-audit-trail-gradin-826d/requirements.md`
- **Audit Report**: `.zenflow/tasks/observabilite-audit-trail-gradin-826d/audit.md`
- **Support Guide** (if exists): `docs/support/DEPANNAGE.md`

### B.2 Code References

- **GradingEvent Model**: `backend/grading/models.py:109-165`
- **GradingService**: `backend/grading/services.py`
- **Celery Tasks**: `backend/grading/tasks.py`
- **Request ID Middleware**: `backend/core/middleware/request_id.py`
- **Prometheus Metrics**: `backend/core/prometheus.py`
- **Logging Configuration**: `backend/core/settings.py:272-348`

### B.3 Monitoring Links

- **Prometheus Metrics**: `http://localhost:8088/metrics` (or production URL)
- **Grafana Dashboards** (if configured): TBD
- **Celery Flower** (if configured): `http://localhost:5555`

---

## Document History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-02-01 | Automated Review | Initial playbook creation |

---

**End of Playbook**
