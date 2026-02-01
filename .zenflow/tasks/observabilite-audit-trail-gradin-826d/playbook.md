# Incident Response Playbook: Observability & Audit Trail

**Task**: ZF-AUD-11  
**Version**: 1.0  
**Date**: 31 janvier 2026  
**Audience**: Operations Team, Production Support Engineers  
**Related**: See `docs/support/DEPANNAGE.md` for general troubleshooting

---

## Overview

This playbook provides diagnostic procedures for **observability and grading workflow** incidents in production. Each scenario follows a structured approach:

1. **Symptoms**: How the issue manifests  
2. **Diagnosis**: Steps to identify root cause  
3. **Root Causes**: Likely explanations  
4. **Actions**: Remediation steps

**Pre-requisites**:
- SSH access to production server
- Docker access: `docker-compose exec backend <command>`
- Database access: `docker-compose exec db psql -U postgres -d viatique`
- Prometheus access: `http://<server>:9090` (if configured)

**Key Infrastructure**:
- **Logs**: `logs/django.log`, `logs/audit.log` (JSON format in production)
- **Metrics**: `/metrics` endpoint (Prometheus format)
- **Audit Trail**: `GradingEvent` table in database
- **Celery**: Redis broker, background workers for PDF operations

---

## Scenario 1: Import Stuck (PDF Not Processing)

### 1.1 Symptoms

- User uploads PDF, but copy remains in `STAGING` status indefinitely
- No pages generated in `booklet.pages_images` field
- Copy status never progresses to `READY`
- Frontend shows "Processing..." spinner forever

### 1.2 Diagnosis Steps

**Step 1: Check Celery Queue Status**
```bash
# Connect to Redis (Celery broker)
docker-compose exec redis redis-cli

# Check queue length
LLEN celery

# Expected: 0 or low number (<10)
# If high (>100), workers are backed up

# Check for stuck tasks
KEYS celery-task-meta-*
# Shows pending task IDs

# Exit Redis
exit
```

**Step 2: Check Celery Worker Health**
```bash
# Verify Celery workers are running
docker-compose ps celery

# Expected: "Up" status
# If "Exit" or "Restarting", worker crashed

# Check worker logs
docker-compose logs --tail=100 celery | grep -i "import\|error\|exception"

# Look for:
# - "Async PDF import failed" (line pattern from tasks.py:139)
# - "FileNotFoundError: PDF file not found"
# - "Rasterization failed"
```

**Step 3: Check Audit Trail for Import Event**
```bash
# Connect to database
docker-compose exec db psql -U postgres -d viatique

# Query GradingEvent for this copy
SELECT action, timestamp, metadata 
FROM grading_gradingevent 
WHERE copy_id = '<copy_uuid>' 
ORDER BY timestamp;

# Expected: IMPORT event with metadata {"filename": "...", "pages": N}
# If missing, import never started or failed before event creation
```

**Step 4: Check Application Logs**
```bash
# Search logs for copy UUID
docker-compose logs backend | grep "<copy_uuid>"

# Look for:
# - "Starting async PDF import for exam..."
# - "Import failed for copy..."
# - "Rasterization failed: ..."

# Check for OCR/PyMuPDF errors
docker-compose logs backend | grep -i "pymupdf\|fitz\|rasterization"
```

**Step 5: Verify Disk Space**
```bash
# Check available disk space
df -h

# Expected: >10% free on /opt/korrigo volume
# If <5%, disk full may block PDF operations

# Check temp upload directory
du -sh /opt/korrigo/media/temp_uploads/

# If >1GB, orphaned files from failed uploads
```

### 1.3 Root Causes

| Cause | Evidence | Likelihood |
|-------|----------|------------|
| **Celery worker down** | `docker-compose ps celery` shows "Exit" | High |
| **Corrupted PDF** | Logs show "FileDataError: invalid PDF" | Medium |
| **OCR timeout** | Logs show "Rasterization timeout" or hung worker | Medium |
| **Disk space exhausted** | `df -h` shows 0% available | Low |
| **Redis connection lost** | Logs show "ConnectionError: Redis unavailable" | Low |

### 1.4 Actions

#### Action 1.1: Restart Celery Worker
```bash
# Restart Celery service
docker-compose restart celery

# Wait 10 seconds
sleep 10

# Verify worker is up
docker-compose ps celery

# Check logs for startup
docker-compose logs --tail=50 celery

# Expected: "celery@worker ready" message
```

#### Action 1.2: Retry Failed Import
```bash
# Connect to Django shell
docker-compose exec backend python manage.py shell

# Python code to retry import
from exams.models import Copy
from grading.tasks import async_import_pdf

copy = Copy.objects.get(id='<copy_uuid>')
# Trigger retry (if PDF still exists in temp directory)
async_import_pdf.delay(
    exam_id=str(copy.exam.id),
    pdf_path=f"/path/to/temp/{copy.id}.pdf",
    user_id=copy.created_by.id,
    anonymous_id=copy.anonymous_id
)

# Exit shell
exit()
```

**Alternative**: Re-upload PDF via API (if temp file lost)

#### Action 1.3: Clean Up Orphaned Files
```bash
# Run cleanup task manually
docker-compose exec backend python manage.py shell

from grading.tasks import cleanup_orphaned_files
result = cleanup_orphaned_files()
print(result)  # {'removed_count': N}

exit()
```

#### Action 1.4: Add Disk Space (if exhausted)
```bash
# Remove old logs
cd /opt/korrigo/logs
ls -lh

# Delete old rotated logs
rm -f django.log.* audit.log.*

# Or: Configure external log aggregation to reduce local storage
```

---

## Scenario 2: Finalization Failing (PDF Generation Errors)

### 2.1 Symptoms

- Copy status changes to `GRADING_FAILED`
- `copy.grading_error_message` field contains error details
- Multiple failed attempts visible in `GradingEvent` metadata
- Frontend shows "Finalization failed, please retry"

### 2.2 Diagnosis Steps

**Step 1: Check Copy Status**
```bash
# Query database
docker-compose exec db psql -U postgres -d viatique

SELECT id, status, grading_retries, grading_error_message 
FROM exams_copy 
WHERE id = '<copy_uuid>';

# Expected fields:
# - status: GRADING_FAILED
# - grading_retries: 1-3
# - grading_error_message: <error details>
```

**Step 2: Check GradingEvent Metadata**
```bash
# Query audit trail
SELECT action, timestamp, metadata 
FROM grading_gradingevent 
WHERE copy_id = '<copy_uuid>' AND action = 'FINALIZE'
ORDER BY timestamp DESC 
LIMIT 5;

# Metadata should include:
# - "final_score": null (if failed)
# - "retries": N
# - "success": false
# - Potentially: "error": "<error message>"
```

**Step 3: Check Celery Task Logs**
```bash
# Search for finalization attempts
docker-compose logs celery | grep "<copy_uuid>" | grep finalize

# Look for:
# - "Async finalization failed for copy... (attempt 1/3)"
# - "PDF generation failed for copy..."
# - "ValueError: Failed to generate final PDF: ..."
```

**Step 4: Check Application Logs for Details**
```bash
# Search backend logs with context
docker-compose logs backend | grep -A 10 "PDF generation failed for copy <copy_uuid>"

# Look for stack traces indicating:
# - PyMuPDF errors (e.g., "fitz.EmptyFileError")
# - Missing annotation data
# - Invalid image paths
# - Memory errors
```

**Step 5: Verify Annotations Exist**
```bash
# Query database
docker-compose exec db psql -U postgres -d viatique

SELECT COUNT(*) FROM grading_annotation WHERE copy_id = '<copy_uuid>';

# Expected: >0 annotations
# If 0, finalization may fail due to empty PDF generation
```

### 2.3 Root Causes

| Cause | Evidence | Likelihood |
|-------|----------|------------|
| **PyMuPDF rendering error** | Logs show "fitz.EmptyFileError" or "PDF generation failed" | High |
| **Missing page images** | Error message mentions "Image not found: ..." | Medium |
| **Invalid annotation coordinates** | Logs show "Annotation out of bounds" or rendering crash | Medium |
| **Memory exhaustion** | Logs show "MemoryError" or worker OOM killed | Low |
| **Lock token expired** | Error message mentions "Invalid lock token" | Low |

### 2.4 Actions

#### Action 2.1: Inspect Error Message Details
```bash
# Get full error message
docker-compose exec db psql -U postgres -d viatique

SELECT grading_error_message FROM exams_copy WHERE id = '<copy_uuid>';

# Error patterns:
# - "Failed to generate final PDF: ..." → PyMuPDF issue
# - "Image not found: ..." → Missing page file
# - "Invalid lock token" → Lock expired (user must re-lock)
```

#### Action 2.2: Verify Page Images Exist
```bash
# Check media directory
ls -la /opt/korrigo/media/copies/pages/<copy_uuid>/

# Expected: PNG files (page_0.png, page_1.png, etc.)
# If missing, rasterization failed (see Scenario 1)
```

#### Action 2.3: Retry Finalization Manually
```bash
# Connect to Django shell
docker-compose exec backend python manage.py shell

from exams.models import Copy
from grading.services import GradingService
from django.contrib.auth import get_user_model

User = get_user_model()
copy = Copy.objects.get(id='<copy_uuid>')
user = User.objects.get(id=<user_id>)  # Original user

# Reset retry counter
copy.grading_retries = 0
copy.status = Copy.Status.LOCKED
copy.save()

# Retry finalization (synchronous, for debugging)
try:
    finalized = GradingService.finalize_copy(copy, user, lock_token=None)
    print(f"Success: {finalized.status}")
except Exception as e:
    print(f"Failed: {e}")

exit()
```

#### Action 2.4: Check for Critical Alert (Max Retries)
```bash
# Search logs for CRITICAL level
docker-compose logs backend | grep "CRITICAL"

# Look for:
# - "Copy <copy_uuid> failed 3 times - manual intervention required"
# This indicates max retries exceeded (action required: manual fix or escalation)
```

#### Action 2.5: Manual PDF Generation (Last Resort)
```bash
# If automatic finalization fails repeatedly:
# 1. Export annotations as JSON
# 2. Generate PDF manually using PyMuPDF CLI
# 3. Upload final PDF via admin interface

# Step 1: Export annotations
docker-compose exec backend python manage.py dumpdata grading.annotation \
  --pks=<annotation_ids> > annotations.json

# Step 2: Generate PDF (requires custom script)
# See: scripts/manual_pdf_generation.py (if available)

# Step 3: Upload via Django Admin
# http://<server>/admin/exams/copy/<copy_uuid>/change/
# Upload final_pdf field manually
```

---

## Scenario 3: Lock Conflicts (Users Blocked from Editing)

### 3.1 Symptoms

- User sees "Copy is locked by another user" error
- Cannot acquire lock even though no one is editing
- Lock appears expired but not released
- Frontend lock indicator shows "Locked by [User]"

### 3.2 Diagnosis Steps

**Step 1: Check Current Lock Status**
```bash
# Query database
docker-compose exec db psql -U postgres -d viatique

SELECT 
    cl.copy_id,
    cl.owner_id,
    u.username AS owner_username,
    cl.locked_at,
    cl.expires_at,
    NOW() AS current_time,
    (cl.expires_at < NOW()) AS is_expired
FROM grading_copylock cl
JOIN auth_user u ON cl.owner_id = u.id
WHERE cl.copy_id = '<copy_uuid>';

# Expected:
# - is_expired = true (lock should be released automatically)
# - is_expired = false (lock still valid, another user editing)
```

**Step 2: Check Lock Heartbeat Activity**
```bash
# Check recent lock events in audit trail
docker-compose exec db psql -U postgres -d viatique

SELECT action, actor_id, timestamp 
FROM grading_gradingevent 
WHERE copy_id = '<copy_uuid>' 
  AND action IN ('LOCK', 'UNLOCK')
ORDER BY timestamp DESC 
LIMIT 10;

# Pattern analysis:
# - Multiple LOCKs without UNLOCKs → Browser crash (lock not released)
# - Last LOCK timestamp old (>30 min) → Expired lock not cleaned
```

**Step 3: Check Application Logs for Lock Conflicts**
```bash
# Search logs for lock-related errors
docker-compose logs backend | grep -i "lock" | grep "<copy_uuid>"

# Look for:
# - "Copy <copy_uuid> already graded (concurrent finalization detected)"
# - "OptimisticLockingException"
# - Lock acquisition failures
```

**Step 4: Verify Lock Cleanup Mechanism**
```bash
# Check if expired locks are cleaned automatically
# (Should be handled by middleware or periodic task)

docker-compose logs backend | grep "Expired lock" | tail -20

# If no cleanup logs found, expired locks may accumulate
```

### 3.3 Root Causes

| Cause | Evidence | Likelihood |
|-------|----------|------------|
| **Browser crash** | User closed browser without releasing lock | High |
| **Lock timeout expired** | `expires_at < NOW()` but not cleaned | Medium |
| **Heartbeat failure** | User lost connection, lock not renewed | Medium |
| **Token mismatch** | User has lock but wrong token (session issue) | Low |
| **Concurrent finalization** | Two users tried to finalize simultaneously | Low |

### 3.4 Actions

#### Action 3.1: Force-Release Expired Lock
```bash
# Delete expired lock manually
docker-compose exec db psql -U postgres -d viatique

DELETE FROM grading_copylock 
WHERE copy_id = '<copy_uuid>' AND expires_at < NOW();

# Affected rows: 1 (if lock was expired)
# Affected rows: 0 (if lock still valid)
```

#### Action 3.2: Check Lock Owner Identity
```bash
# Identify who holds the lock
docker-compose exec db psql -U postgres -d viatique

SELECT u.username, u.email, cl.expires_at 
FROM grading_copylock cl
JOIN auth_user u ON cl.owner_id = u.id
WHERE cl.copy_id = '<copy_uuid>';

# Contact user to ask if they're still editing
# If unreachable, proceed with force-release (Action 3.3)
```

#### Action 3.3: Force-Release Valid Lock (Emergency)
```bash
# Only use if lock owner unreachable and urgent
docker-compose exec db psql -U postgres -d viatique

DELETE FROM grading_copylock WHERE copy_id = '<copy_uuid>';

# WARNING: This may cause data loss if user was actively editing
# Log this action for audit purposes
```

#### Action 3.4: Verify Lock Cleanup Configuration
```bash
# Check settings for lock expiration time
docker-compose exec backend python manage.py shell

from django.conf import settings
# Check if LOCK_EXPIRATION setting exists (custom, not Django default)
# Typical value: 1800 seconds (30 minutes)

# If cleanup not working, consider adding periodic task
from grading.models import CopyLock
from django.utils import timezone

# Manual cleanup script
expired_locks = CopyLock.objects.filter(expires_at__lt=timezone.now())
count = expired_locks.count()
expired_locks.delete()
print(f"Deleted {count} expired locks")

exit()
```

#### Action 3.5: Monitor Lock Conflicts Metric (When Implemented)
```bash
# After Phase 2 (metrics implementation), check:
curl http://localhost:8088/metrics | grep grading_lock_conflicts_total

# Expected output:
# grading_lock_conflicts_total{conflict_type="already_locked"} 5
# grading_lock_conflicts_total{conflict_type="expired"} 12
# grading_lock_conflicts_total{conflict_type="token_mismatch"} 1

# High "already_locked" count → Users trying to edit simultaneously
# High "expired" count → Cleanup mechanism not working properly
```

---

## Scenario 4: High Latency (Slow Response Times)

### 4.1 Symptoms

- Requests take >5 seconds to complete
- Frontend shows timeout errors (504 Gateway Timeout)
- Slow page loads, laggy annotation rendering
- Prometheus alerts fire for `http_request_duration_seconds` p95 > 5s

### 4.2 Diagnosis Steps

**Step 1: Check Prometheus HTTP Metrics**
```bash
# Query metrics endpoint
curl http://localhost:8088/metrics | grep http_request_duration

# Look for high latency endpoints:
# http_request_duration_seconds{method="POST",path="/api/copies/<uuid>/finalize/"} ...
# High values (>5s) indicate slow operations
```

**Step 2: Check Slow Request Logs**
```bash
# Search for slow request warnings
docker-compose logs backend | grep "Slow request detected"

# Example output:
# "Slow request detected: POST /api/copies/.../finalize/ took 12.45s (status 200)"

# Analyze patterns:
# - Which endpoints are slow?
# - What time of day? (peak usage)
# - Specific users or all users?
```

**Step 3: Check Database Query Performance**
```bash
# Connect to PostgreSQL
docker-compose exec db psql -U postgres -d viatique

# Enable query timing
\timing on

# Check active queries
SELECT pid, now() - pg_stat_activity.query_start AS duration, query 
FROM pg_stat_activity 
WHERE state = 'active' AND query NOT LIKE '%pg_stat_activity%'
ORDER BY duration DESC;

# Look for long-running queries (>5s)
# Common slow queries:
# - SELECT with JOINs on large tables (Copy, Annotation)
# - UPDATE with lock contention
# - DELETE with cascading foreign keys
```

**Step 4: Check Database Lock Contention**
```bash
# Query database locks
docker-compose exec db psql -U postgres -d viatique

SELECT 
    locktype, 
    relation::regclass AS table_name, 
    mode, 
    COUNT(*) AS lock_count
FROM pg_locks 
GROUP BY locktype, relation, mode
ORDER BY lock_count DESC 
LIMIT 20;

# High lock counts indicate contention
# Common lock types:
# - RowExclusiveLock (normal writes)
# - AccessExclusiveLock (blocking all operations)
```

**Step 5: Check System Resources**
```bash
# Check CPU usage
docker stats --no-stream

# Expected:
# - backend: <80% CPU
# - celery: <50% CPU
# - db: <70% CPU

# If any service >90% CPU, resource exhaustion

# Check memory
free -h

# Expected: >1GB available
# If <500MB, memory pressure may cause swapping
```

### 4.3 Root Causes

| Cause | Evidence | Likelihood |
|-------|----------|------------|
| **Database lock contention** | Multiple slow queries, high lock count | High |
| **Large PDF processing** | Slow finalization for 50+ page copies | High |
| **High concurrent load** | Many active queries, CPU >80% | Medium |
| **Missing database indexes** | Full table scans in query plans | Low |
| **Network issues** | High latency to external services (if any) | Low |

### 4.4 Actions

#### Action 4.1: Identify Slow Queries
```bash
# Enable slow query logging (if not already enabled)
docker-compose exec db psql -U postgres -d viatique

# Set slow query threshold to 1 second
ALTER SYSTEM SET log_min_duration_statement = 1000;
SELECT pg_reload_conf();

# Check logs after 5-10 minutes
docker-compose logs db | grep "duration:"

# Example output:
# "LOG: duration: 3456.789 ms statement: SELECT * FROM exams_copy ..."
```

#### Action 4.2: Optimize Slow Queries
```bash
# Analyze query plan for slow query
docker-compose exec db psql -U postgres -d viatique

EXPLAIN ANALYZE SELECT * FROM exams_copy 
JOIN grading_annotation ON exams_copy.id = grading_annotation.copy_id 
WHERE exams_copy.exam_id = '<exam_uuid>';

# Look for:
# - "Seq Scan" (full table scan, bad)
# - "Index Scan" (good)
# - "Nested Loop" with high cost

# If missing indexes, contact dev team to add:
# CREATE INDEX idx_annotation_copy ON grading_annotation(copy_id);
```

#### Action 4.3: Restart Backend (If Resource Exhaustion)
```bash
# Restart backend service to clear memory/connections
docker-compose restart backend

# Wait 30 seconds
sleep 30

# Verify service is up
docker-compose ps backend

# Test endpoint
curl -I http://localhost:8088/api/health/

# Expected: 200 OK
```

#### Action 4.4: Scale Resources (Long-Term)
```bash
# Increase Docker resource limits
# Edit docker-compose.yml:

services:
  backend:
    deploy:
      resources:
        limits:
          cpus: '2.0'  # Increase from 1.0
          memory: 4G   # Increase from 2G

  db:
    deploy:
      resources:
        limits:
          memory: 4G   # Increase from 2G

# Apply changes
docker-compose up -d
```

#### Action 4.5: Check Celery Queue Backlog
```bash
# If slow requests are for async operations (finalize, import)
docker-compose exec redis redis-cli LLEN celery

# High value (>50) indicates backlog
# Solution: Scale Celery workers
docker-compose up -d --scale celery=3  # Run 3 workers instead of 1
```

---

## Scenario 5: Missing Audit Events (Events Not Recorded)

### 5.1 Symptoms

- `GradingEvent.objects.filter(copy=copy, action='IMPORT')` returns no results
- Expected events missing from audit trail
- Cannot trace workflow history for a copy
- Incident investigation blocked due to missing audit data

### 5.2 Diagnosis Steps

**Step 1: Verify Event Creation Code Paths**
```bash
# Check if events are created for this copy at all
docker-compose exec db psql -U postgres -d viatique

SELECT action, timestamp FROM grading_gradingevent 
WHERE copy_id = '<copy_uuid>' 
ORDER BY timestamp;

# If empty → No events ever created (likely transaction rollback)
# If partial → Some events created (identify missing action types)
```

**Step 2: Check Application Logs for Exceptions**
```bash
# Search for exceptions during workflow
docker-compose logs backend | grep "<copy_uuid>" | grep -i "exception\|error\|failed"

# Common patterns:
# - "Import failed for copy..." (exception before IMPORT event)
# - "PDF generation failed..." (exception before FINALIZE event)
# - "IntegrityError" (database constraint violation)
```

**Step 3: Check Transaction Rollbacks**
```bash
# Query database transaction logs (if enabled)
docker-compose exec db psql -U postgres -d viatique

# Check recent rollbacks (requires pg_stat_statements extension)
SELECT query, calls, mean_exec_time 
FROM pg_stat_statements 
WHERE query LIKE '%ROLLBACK%' 
ORDER BY calls DESC 
LIMIT 10;

# High ROLLBACK count indicates transaction failures
```

**Step 4: Verify Event Creation Happens Within Transactions**
```bash
# Code inspection (not diagnostic, but helps understand behavior)
# Services.py uses @transaction.atomic decorators
# If exception occurs before event creation, transaction rolls back

# Example code path:
# 1. @transaction.atomic
# 2. Copy.objects.create(...)  ← If fails here
# 3. GradingEvent.objects.create(...)  ← Never reached

# Check logs for step 2 failures:
docker-compose logs backend | grep "Copy.objects.create"
```

**Step 5: Check for Intentional Event Skipping**
```bash
# Some actions may not create events if:
# - Dry-run mode enabled (testing)
# - Admin actions bypassing services layer
# - Direct database modifications (SQL scripts)

# Check for admin actions in logs
docker-compose logs backend | grep "admin" | grep "<copy_uuid>"
```

### 5.3 Root Causes

| Cause | Evidence | Likelihood |
|-------|----------|------------|
| **Transaction rollback** | Exception before event creation, ROLLBACK in logs | High |
| **Service method bypassed** | Direct model save, admin edit, SQL script | Medium |
| **Event creation code commented out** | Missing events for all copies (code regression) | Low |
| **Database constraint violation** | IntegrityError for GradingEvent INSERT | Low |
| **Async task failure** | Celery task crashed before event creation | Medium |

### 5.4 Actions

#### Action 5.1: Identify Transaction Rollback Cause
```bash
# Search logs for exception details
docker-compose logs backend | grep -A 20 "Import failed for copy <copy_uuid>"

# Look for root cause:
# - "FileNotFoundError" → PDF file missing
# - "ValidationError" → Invalid data
# - "IntegrityError" → Database constraint violation
# - "OperationalError" → Database connection lost

# Fix root cause before retrying operation
```

#### Action 5.2: Manually Create Missing Audit Event (Post-Hoc)
```bash
# If event is missing but operation succeeded (e.g., import worked, no IMPORT event)
docker-compose exec backend python manage.py shell

from grading.models import GradingEvent
from exams.models import Copy
from django.contrib.auth import get_user_model

User = get_user_model()
copy = Copy.objects.get(id='<copy_uuid>')
user = User.objects.get(id=<user_id>)  # Original actor

# Create missing event
GradingEvent.objects.create(
    copy=copy,
    action=GradingEvent.Action.IMPORT,  # Or FINALIZE, etc.
    actor=user,
    metadata={'note': 'Manually created for audit compliance', 'pages': 10}
)

print("Event created")
exit()
```

**WARNING**: Manual event creation should be rare and logged for compliance.

#### Action 5.3: Verify Code Hasn't Regressed
```bash
# Check if event creation code is present
docker-compose exec backend cat /app/grading/services.py | grep -A 5 "GradingEvent.objects.create"

# Expected: Multiple matches (IMPORT, CREATE_ANN, UPDATE_ANN, FINALIZE)
# If missing, code regression (deployment issue)

# Verify deployment version
docker-compose exec backend cat /app/VERSION  # Or git rev-parse HEAD

# Compare with expected version
```

#### Action 5.4: Check for Async Task Failures (Celery)
```bash
# If events missing for async operations (finalize, import)
docker-compose logs celery | grep "<copy_uuid>"

# Look for:
# - "Async finalization failed" (task failed before event)
# - "Max retries exceeded" (task gave up)
# - Worker crash (no completion log)

# Check Celery task results in Redis
docker-compose exec redis redis-cli

KEYS celery-task-meta-*
GET celery-task-meta-<task_id>

# Result should include status: "SUCCESS" or "FAILURE"
exit
```

#### Action 5.5: Implement Missing Event Detection (Monitoring)
```bash
# After Phase 4 (testing), add monitoring query:
# Daily cron job to detect copies with incomplete audit trails

docker-compose exec backend python manage.py shell

from exams.models import Copy
from grading.models import GradingEvent

# Find copies missing IMPORT event
copies_missing_import = Copy.objects.exclude(
    grading_events__action=GradingEvent.Action.IMPORT
).filter(status__in=['READY', 'LOCKED', 'GRADED'])

print(f"Found {copies_missing_import.count()} copies missing IMPORT event")

# Log for investigation
for copy in copies_missing_import[:10]:
    print(f"Copy {copy.id}: status={copy.status}, created={copy.created_at}")

exit()
```

---

## Appendix A: Useful Commands Reference

### Database Queries

```sql
-- Check copy status and workflow history
SELECT 
    c.id,
    c.anonymous_id,
    c.status,
    c.grading_retries,
    COUNT(ge.id) AS event_count
FROM exams_copy c
LEFT JOIN grading_gradingevent ge ON c.id = ge.copy_id
WHERE c.id = '<copy_uuid>'
GROUP BY c.id;

-- Find all events for a copy (audit trail)
SELECT action, actor_id, timestamp, metadata 
FROM grading_gradingevent 
WHERE copy_id = '<copy_uuid>' 
ORDER BY timestamp;

-- Find stuck copies (STAGING for >1 hour)
SELECT id, anonymous_id, created_at 
FROM exams_copy 
WHERE status = 'STAGING' 
  AND created_at < NOW() - INTERVAL '1 hour';

-- Count copies by status (workflow backlog)
SELECT status, COUNT(*) 
FROM exams_copy 
GROUP BY status;

-- Find lock conflicts (expired but not released)
SELECT copy_id, owner_id, expires_at 
FROM grading_copylock 
WHERE expires_at < NOW();
```

### Prometheus Queries (PromQL)

```promql
# Request latency p95 (95th percentile)
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))

# Slow requests (>5s)
http_request_duration_seconds_bucket{le="5.0"}

# Error rate (4xx + 5xx)
rate(http_requests_total{status=~"4..|5.."}[5m])

# Import duration p95 (after Phase 2 implementation)
histogram_quantile(0.95, rate(grading_import_duration_seconds_bucket[5m]))

# Lock conflicts rate
rate(grading_lock_conflicts_total[5m])
```

### Log Analysis (grep patterns)

```bash
# Find all errors for a copy
docker-compose logs backend | grep "<copy_uuid>" | grep -i error

# Find slow requests
docker-compose logs backend | grep "Slow request detected"

# Find Celery failures
docker-compose logs celery | grep -i "failed\|error\|exception"

# Find transaction rollbacks
docker-compose logs backend | grep -i "rollback"

# Find audit events in JSON logs (production)
docker-compose logs backend | grep "GradingEvent.objects.create"
```

---

## Appendix B: Escalation Matrix

| Issue Type | Severity | First Response | Escalate To |
|-----------|----------|----------------|-------------|
| Import stuck (Celery down) | P1 - Critical | Restart Celery worker | DevOps team if persists >15 min |
| Finalization failing | P2 - High | Check error logs, retry | Dev team if error unknown |
| Lock conflicts | P3 - Medium | Force-release expired locks | Dev team if >10 conflicts/day |
| High latency | P2 - High | Check metrics, restart if needed | DevOps + Dev if persists >30 min |
| Missing audit events | P3 - Medium | Create manual event | Dev team for code inspection |

**On-Call Contacts**:
- DevOps: [Contact Info]
- Backend Dev: [Contact Info]
- Database Admin: [Contact Info]

---

## Appendix C: Health Check Script

```bash
#!/bin/bash
# health_check.sh - Quick diagnostic script

echo "=== Viatique Health Check ==="
echo ""

# Services
echo "1. Docker Services:"
docker-compose ps | grep -E "backend|celery|db|redis"
echo ""

# Celery Queue
echo "2. Celery Queue Length:"
docker-compose exec -T redis redis-cli LLEN celery
echo ""

# Database Connections
echo "3. Active Database Connections:"
docker-compose exec -T db psql -U postgres -d viatique -c "SELECT count(*) FROM pg_stat_activity;" -t
echo ""

# Disk Space
echo "4. Disk Space:"
df -h | grep -E "/$|/opt"
echo ""

# Recent Errors
echo "5. Recent Errors (last 1 hour):"
docker-compose logs --since 1h backend 2>&1 | grep -i error | wc -l
echo ""

# Stuck Copies
echo "6. Stuck Copies (STAGING >1 hour):"
docker-compose exec -T db psql -U postgres -d viatique -c "SELECT COUNT(*) FROM exams_copy WHERE status = 'STAGING' AND created_at < NOW() - INTERVAL '1 hour';" -t
echo ""

echo "=== Health Check Complete ==="
```

**Usage**:
```bash
chmod +x health_check.sh
./health_check.sh
```

---

## Appendix D: Related Documentation

- **General Troubleshooting**: `docs/support/DEPANNAGE.md`
- **Technical Specification**: `.zenflow/tasks/observabilite-audit-trail-gradin-826d/spec.md`
- **Requirements**: `.zenflow/tasks/observabilite-audit-trail-gradin-826d/requirements.md`
- **Audit Report**: `.zenflow/tasks/observabilite-audit-trail-gradin-826d/audit.md`

**Metrics Documentation** (after Phase 2):
- Prometheus metrics: `/metrics` endpoint
- Grafana dashboards: `http://<server>:3000` (if configured)

---

**Document Version**: 1.0  
**Last Updated**: 31 janvier 2026  
**Next Review**: After production incidents (update based on learnings)
