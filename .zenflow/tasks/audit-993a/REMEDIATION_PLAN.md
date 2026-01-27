# Production Readiness - Remediation Plan

**Generated**: 2026-01-27  
**Audit Scope**: Korrigo Exam Grading Platform  
**Total Issues**: 41 (8 P0 Data Integrity + 8 P0 Operational + 7 P1 Security + 18 P1 Reliability)  
**Status**: READY FOR IMPLEMENTATION

---

## Executive Summary

This remediation plan addresses **41 production readiness issues** identified across 4 categories:
- **P0 Data Integrity**: 8 critical issues (BLOCKER)
- **P0 Operational**: 8 critical issues (BLOCKER)
- **P1 Security**: 7 high-severity issues (MUST-FIX before production)
- **P1 Reliability**: 18 high-severity issues (SHOULD-FIX for production quality)

**Overall Risk Score**: **HIGH** (16 P0 blockers must be resolved)

**Estimated Total Effort**: 18-22 person-days

**Recommended Phasing**:
1. **Phase 1 (Critical)**: P0 Data Integrity - 4-5 days (BLOCKING)
2. **Phase 2 (Critical)**: P0 Operational - 5-6 days (BLOCKING)
3. **Phase 3 (High)**: P1 Security - 3-4 days (REQUIRED)
4. **Phase 4 (High)**: P1 Reliability - 6-7 days (RECOMMENDED)

---

## Risk Scoring Methodology

**Risk Score** = Impact (1-5) × Likelihood (1-5) × Urgency (1-3)

- **Impact**: 1 (Negligible) → 5 (Catastrophic data loss)
- **Likelihood**: 1 (Rare) → 5 (Frequent in production)
- **Urgency**: 1 (Can defer) → 3 (Blocker)

**Priority Thresholds**:
- **CRITICAL**: Risk Score ≥ 30 (P0 - Must fix before deployment)
- **HIGH**: Risk Score 15-29 (P1 - Should fix before deployment)
- **MEDIUM**: Risk Score 5-14 (P2 - Can defer to post-launch)

---

## Phase 1: P0 Data Integrity Fixes (CRITICAL - 4-5 days)

### Group A: Race Conditions (3 issues)

#### P0-DI-001: Race Condition in Lock Acquisition
**Risk Score**: 45 (Impact: 5, Likelihood: 3, Urgency: 3)  
**Effort**: M (4-6 hours)  
**Priority**: 1 (BLOCKER)

**Symptom**: Multiple teachers can acquire lock simultaneously → concurrent edits → data loss

**Root Cause**: Non-atomic check-then-create in `grading/views_lock.py:10-77`

**Fix Strategy**:
```python
# Apply select_for_update() + get_or_create pattern
@transaction.atomic
def post(self, request, copy_id):
    copy = Copy.objects.select_for_update().get(id=copy_id)
    
    # Atomic cleanup + check
    CopyLock.objects.filter(copy=copy, expires_at__lt=timezone.now()).delete()
    
    # Atomic lock acquisition
    lock, created = CopyLock.objects.get_or_create(
        copy=copy,
        defaults={'owner': request.user, 'expires_at': expires_at}
    )
    
    if not created and lock.owner != request.user:
        return Response({"status": "LOCKED_BY_OTHER"}, status=409)
    
    # Refresh expiration if already owned
    if lock.owner == request.user:
        lock.expires_at = expires_at
        lock.save()
```

**Files to Modify**:
- `backend/grading/views_lock.py` (lines 10-77)

**Tests to Add**:
- `backend/grading/tests/test_concurrency.py::test_concurrent_lock_acquisition_race()`
- Use threading to simulate 2 simultaneous lock requests
- Verify only one succeeds, other gets 409

**Dependencies**: None

**Verification**:
```bash
# Run concurrency test
pytest backend/grading/tests/test_concurrency.py::test_concurrent_lock_acquisition_race -v

# Manual test with 2 curl commands in parallel
curl -X POST /api/grading/copies/{id}/lock/ & 
curl -X POST /api/grading/copies/{id}/lock/ &
# Verify only one returns 200, other returns 409
```

---

#### P0-DI-002: DraftState.get_or_create Race Condition
**Risk Score**: 40 (Impact: 4, Likelihood: 4, Urgency: 2.5)  
**Effort**: M (4-6 hours)  
**Priority**: 2 (BLOCKER)

**Symptom**: Concurrent autosaves create duplicate drafts or lose data

**Root Cause**: Non-atomic `version += 1` in `grading/views_draft.py:67-84`

**Fix Strategy**:
```python
# Use F() expression for atomic version increment
from django.db.models import F

@transaction.atomic
def put(self, request, copy_id):
    draft, created = DraftState.objects.get_or_create(
        copy=copy,
        owner=request.user,
        defaults={'payload': payload, 'version': 1, ...}
    )
    
    if not created:
        # Atomic version increment
        updated = DraftState.objects.filter(
            id=draft.id,
            client_id=draft.client_id  # Prevent cross-tab conflicts
        ).update(
            payload=payload,
            version=F('version') + 1,  # ATOMIC
            updated_at=timezone.now()
        )
        
        if updated == 0:
            return Response({"error": "Draft conflict"}, status=409)
        
        draft.refresh_from_db()
```

**Files to Modify**:
- `backend/grading/views_draft.py` (lines 67-84)

**Tests to Add**:
- `backend/grading/tests/test_concurrency.py::test_concurrent_autosave_race()`
- Simulate 2 autosaves 50ms apart
- Verify both succeed, version increments correctly (v1 → v2 → v3)

**Dependencies**: None

**Verification**:
```bash
pytest backend/grading/tests/test_concurrency.py::test_concurrent_autosave_race -v
```

---

#### P0-DI-003: Copy State Transition Race Condition (Double Finalization)
**Risk Score**: 42 (Impact: 5, Likelihood: 3, Urgency: 2.8)  
**Effort**: L (8-10 hours)  
**Priority**: 3 (BLOCKER)

**Symptom**: Two finalization requests generate 2 PDFs, second overwrites first

**Root Cause**: State check before slow PDF generation in `grading/services.py:316-342`

**Fix Strategy**:
```python
@transaction.atomic
def finalize_copy(copy: Copy, user):
    # Row lock + idempotency check
    copy = Copy.objects.select_for_update().get(id=copy.id)
    
    # Idempotent: if already GRADED, return success
    if copy.status == Copy.Status.GRADED:
        logger.info(f"Copy {copy.id} already graded, returning existing result")
        return copy
    
    if copy.status not in [Copy.Status.LOCKED, Copy.Status.READY]:
        raise ValueError("Only LOCKED/READY can be finalized")
    
    # Atomic state transition BEFORE slow PDF operation
    copy.status = Copy.Status.GRADING_IN_PROGRESS
    copy.save()
    
    try:
        # Compute score
        final_score = GradingService.compute_score(copy)
        
        # Generate PDF (idempotent check inside)
        if not copy.final_pdf:
            flattener = PDFFlattener()
            flattener.flatten_copy(copy)
        
        # Mark as GRADED
        copy.status = Copy.Status.GRADED
        copy.graded_at = timezone.now()
        copy.save()
        
        # Idempotent audit event
        GradingEvent.objects.get_or_create(
            copy=copy,
            action=GradingEvent.Action.FINALIZE,
            defaults={'actor': user, 'metadata': {'score': final_score}}
        )
        
    except Exception as e:
        # Rollback to LOCKED on failure
        copy.status = Copy.Status.LOCKED
        copy.grading_error_message = str(e)[:500]
        copy.save()
        raise
```

**Files to Modify**:
- `backend/grading/services.py` (lines 316-342)
- `backend/exams/models.py` (add `Copy.Status.GRADING_IN_PROGRESS`, `grading_error_message`)

**Migration Required**: YES
```bash
python manage.py makemigrations -n add_grading_in_progress_status
```

**Tests to Add**:
- `test_double_finalization_idempotent()` - Call finalize twice, verify single PDF
- `test_finalize_rollback_on_pdf_failure()` - Mock PDF failure, verify rollback

**Dependencies**: 
- Requires `Copy.Status.GRADING_IN_PROGRESS` enum value
- Requires `Copy.grading_error_message` field

**Verification**:
```bash
pytest backend/grading/tests/test_finalization.py::test_double_finalization_idempotent -v
```

---

### Group B: Cascade Deletion & File Integrity (2 issues)

#### P0-DI-005: Cascade Deletion Risk - Exam Deletion Destroys All Data
**Risk Score**: 50 (Impact: 5, Likelihood: 2, Urgency: 5)  
**Effort**: M (6-8 hours)  
**Priority**: 4 (BLOCKER)

**Symptom**: Admin deletes Exam → ALL copies + annotations + grades PERMANENTLY LOST

**Root Cause**: `on_delete=models.CASCADE` in `exams/models.py:108`

**Fix Strategy**:
```python
# Step 1: Add soft-delete to Exam model
class Exam(models.Model):
    # ... existing fields
    deleted_at = models.DateTimeField(null=True, blank=True)
    deleted_by = models.ForeignKey(User, null=True, on_delete=models.SET_NULL, related_name='deleted_exams')
    
    objects = models.Manager()  # Default manager (includes deleted)
    active_objects = ActiveExamManager()  # Excludes deleted
    
    def soft_delete(self, user):
        self.deleted_at = timezone.now()
        self.deleted_by = user
        self.save()
    
    class Meta:
        # ... existing
        ordering = ['deleted_at', '-created_at']

# Step 2: Add ActiveExamManager
class ActiveExamManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(deleted_at__isnull=True)

# Step 3: Protect Copy cascade (CRITICAL)
class Copy(models.Model):
    exam = models.ForeignKey(
        Exam,
        on_delete=models.PROTECT,  # ✅ Prevent cascade deletion
        related_name='copies',
    )
```

**Alternative** (if soft-delete too complex for this phase):
```python
# Minimal fix: Change CASCADE to PROTECT
class Copy(models.Model):
    exam = models.ForeignKey(
        Exam,
        on_delete=models.PROTECT,  # Prevent deletion if copies exist
        related_name='copies',
    )
```

**Files to Modify**:
- `backend/exams/models.py` (Exam model, Copy.exam FK)
- `backend/exams/managers.py` (NEW - ActiveExamManager)
- `backend/exams/views.py` (use `active_objects` in querysets)

**Migration Required**: YES
```bash
python manage.py makemigrations -n protect_exam_cascade_deletion
```

**Tests to Add**:
- `test_exam_deletion_blocked_if_copies_exist()` - Verify ProtectedError raised
- `test_soft_delete_exam()` (if soft-delete approach)

**Dependencies**: None

**Verification**:
```bash
# Test cascade protection
python manage.py shell
>>> from exams.models import Exam, Copy
>>> exam = Exam.objects.first()
>>> Copy.objects.create(exam=exam, ...)
>>> exam.delete()
# Should raise: django.db.models.deletion.ProtectedError
```

---

#### P0-DI-006: File Orphaning on PDF Generation Failure
**Risk Score**: 35 (Impact: 3, Likelihood: 4, Urgency: 3)  
**Effort**: S (3-4 hours)  
**Priority**: 5

**Symptom**: PDF generation fails mid-process → orphaned files in media/copies/

**Root Cause**: No cleanup on exception in `processing/services/pdf_flattener.py`

**Fix Strategy**:
```python
# Add cleanup wrapper
def flatten_copy(self, copy: Copy):
    output_path = None
    temp_files = []
    
    try:
        # ... existing flatten logic
        output_path = self._generate_output_path(copy)
        temp_files = self._extract_pages(copy)  # Track temp files
        
        # Flatten and save
        final_pdf = self._merge_and_flatten(temp_files)
        
        # Atomic file save
        with transaction.atomic():
            copy.final_pdf.save(f"{copy.id}.pdf", final_pdf, save=True)
        
    except Exception as e:
        # Cleanup orphaned files
        if output_path and os.path.exists(output_path):
            os.unlink(output_path)
        
        for temp_file in temp_files:
            if os.path.exists(temp_file):
                os.unlink(temp_file)
        
        logger.error(f"PDF flatten failed for copy {copy.id}: {e}", exc_info=True)
        raise
    
    finally:
        # Always cleanup temp files
        for temp_file in temp_files:
            if os.path.exists(temp_file):
                os.unlink(temp_file)
```

**Files to Modify**:
- `backend/processing/services/pdf_flattener.py` (flatten_copy method)

**Tests to Add**:
- `test_orphaned_file_cleanup_on_flatten_failure()` - Mock PDF error, verify cleanup

**Dependencies**: None

**Verification**:
```bash
# Monitor media folder before/after failed flatten
du -sh media/copies/
# Trigger error
# Verify folder size unchanged (no orphans)
```

---

### Group C: Annotation & State Integrity (3 issues)

#### P0-DI-004: Missing Transaction Rollback on PDF Generation Failure
**Risk Score**: 38 (Impact: 4, Likelihood: 3, Urgency: 3.2)  
**Effort**: M (covered by P0-DI-003)  
**Priority**: 6

**Note**: This issue is resolved by P0-DI-003's fix (state transition before PDF, rollback on failure).

**Dependencies**: P0-DI-003 (blocker)

---

#### P0-DI-007: Annotation Update Race Condition (Lost Updates)
**Risk Score**: 36 (Impact: 4, Likelihood: 3, Urgency: 3)  
**Effort**: M (5-6 hours)  
**Priority**: 7

**Symptom**: Concurrent annotation updates overwrite each other (last-write-wins)

**Root Cause**: No optimistic locking on Annotation model

**Fix Strategy**:
```python
# Add version field to Annotation model
class Annotation(models.Model):
    # ... existing fields
    version = models.IntegerField(default=1)
    
    def save(self, *args, **kwargs):
        if self.pk:
            # Optimistic locking on update
            rows_updated = Annotation.objects.filter(
                pk=self.pk,
                version=self.version
            ).update(
                data=self.data,
                version=F('version') + 1,
                updated_at=timezone.now()
            )
            
            if rows_updated == 0:
                raise AnnotationConflictError(
                    f"Annotation {self.pk} was modified by another user"
                )
            
            self.refresh_from_db()
        else:
            super().save(*args, **kwargs)
```

**Files to Modify**:
- `backend/grading/models.py` (Annotation model)
- `backend/grading/views.py` (handle AnnotationConflictError → 409)
- `backend/grading/exceptions.py` (NEW - AnnotationConflictError)

**Migration Required**: YES

**Tests to Add**:
- `test_annotation_optimistic_locking()` - Update with stale version → 409

**Dependencies**: None

**Verification**:
```bash
pytest backend/grading/tests/test_annotations.py::test_annotation_optimistic_locking -v
```

---

#### P0-DI-008: Missing Atomic State Transition in Copy Status Changes
**Risk Score**: 34 (Impact: 4, Likelihood: 3, Urgency: 2.8)  
**Effort**: S (3-4 hours)  
**Priority**: 8

**Symptom**: Copy status changes can be interleaved with lock operations

**Root Cause**: No row-level locking on Copy updates in status transitions

**Fix Strategy**:
```python
# Wrap all status transitions with select_for_update()
def transition_copy_status(copy_id, from_status, to_status, actor):
    with transaction.atomic():
        copy = Copy.objects.select_for_update().get(id=copy_id)
        
        if copy.status != from_status:
            raise InvalidStateTransition(
                f"Cannot transition from {copy.status} to {to_status}"
            )
        
        copy.status = to_status
        copy.save()
        
        # Audit event
        GradingEvent.objects.create(
            copy=copy,
            action=f"status_change_{to_status}",
            actor=actor
        )
```

**Files to Modify**:
- `backend/grading/services.py` (add `transition_copy_status` helper)
- `backend/grading/views.py` (use helper in all status transitions)

**Tests to Add**:
- `test_invalid_state_transition_rejected()` - READY → LOCKED fails if already GRADED

**Dependencies**: None

---

## Phase 2: P0 Operational Fixes (CRITICAL - 5-6 days)

### Group D: Observability & Incident Response (3 issues)

#### P0-OP-01: Missing Logging Configuration (CRITICAL)
**Risk Score**: 48 (Impact: 5, Likelihood: 5, Urgency: 3.2)  
**Effort**: M (4-5 hours)  
**Priority**: 9 (BLOCKER)

**Symptom**: No structured logging → cannot diagnose incidents

**Root Cause**: No `LOGGING` dict in `settings.py`

**Fix Strategy**:
```python
# Add to backend/core/settings.py
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'json': {
            '()': 'pythonjsonlogger.jsonlogger.JsonFormatter',
            'format': '%(asctime)s %(name)s %(levelname)s %(message)s'
        },
        'verbose': {
            'format': '[{asctime}] {levelname} {name} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'json' if not DEBUG else 'verbose',
        },
        'audit_file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': '/var/log/korrigo/audit.log',
            'maxBytes': 10485760,  # 10MB
            'backupCount': 10,
            'formatter': 'json',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
        },
        'audit': {
            'handlers': ['console', 'audit_file'],
            'level': 'INFO',
            'propagate': False,
        },
        'grading': {
            'handlers': ['console'],
            'level': 'DEBUG' if DEBUG else 'INFO',
        },
        'processing': {
            'handlers': ['console'],
            'level': 'DEBUG' if DEBUG else 'INFO',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    }
}
```

**Files to Modify**:
- `backend/core/settings.py` (add LOGGING dict)
- `requirements.txt` (add `python-json-logger`)
- `docker-compose.yml` (mount /var/log/korrigo volume)

**Dependencies**: None

**Verification**:
```bash
python manage.py check --deploy
python manage.py shell -c "import logging; logging.getLogger('audit').info('Test log')"
```

---

#### P0-OP-02: No Error Alerting/Notification System (CRITICAL)
**Risk Score**: 46 (Impact: 5, Likelihood: 4, Urgency: 3)  
**Effort**: M (4-6 hours)  
**Priority**: 10 (BLOCKER)

**Symptom**: Silent failures in production, no alerts

**Root Cause**: No error notification configured

**Fix Strategy** (Sentry - Recommended):
```python
# Install: pip install sentry-sdk
# Add to backend/core/settings.py
import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration

SENTRY_DSN = os.environ.get('SENTRY_DSN')
if SENTRY_DSN and not DEBUG:
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[DjangoIntegration()],
        traces_sample_rate=0.1,  # 10% performance monitoring
        send_default_pii=False,  # GDPR compliance
        environment=DJANGO_ENV,
        release=os.environ.get('GIT_SHA', 'unknown'),
    )
```

**Alternative** (Email):
```python
# Add to backend/core/settings.py
ADMINS = [('Admin', os.environ.get('ADMIN_EMAIL', 'admin@example.com'))]

EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = os.environ.get('EMAIL_HOST', 'smtp.example.com')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', 587))
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD')

if not DEBUG:
    LOGGING['handlers']['mail_admins'] = {
        'level': 'ERROR',
        'class': 'django.utils.log.AdminEmailHandler',
    }
```

**Files to Modify**:
- `backend/core/settings.py`
- `requirements.txt` (add `sentry-sdk`)
- `.env.example` (add SENTRY_DSN)

**Dependencies**: P0-OP-01 (logging configuration)

**Verification**:
```bash
python manage.py shell -c "import sentry_sdk; sentry_sdk.capture_message('Test alert')"
```

---

#### P0-OP-08: No Metrics/Monitoring Instrumentation (HIGH)
**Risk Score**: 28 (Impact: 4, Likelihood: 4, Urgency: 1.75)  
**Effort**: L (8-10 hours)  
**Priority**: 11

**Symptom**: No metrics on API latency, PDF processing time, queue depth

**Root Cause**: No instrumentation library

**Fix Strategy** (Prometheus - Recommended):
```python
# Install: pip install django-prometheus
# Add to INSTALLED_APPS
INSTALLED_APPS = [
    'django_prometheus',
    # ... rest
]

# Add to MIDDLEWARE (at top and bottom)
MIDDLEWARE = [
    'django_prometheus.middleware.PrometheusBeforeMiddleware',
    # ... existing middleware
    'django_prometheus.middleware.PrometheusAfterMiddleware',
]

# Use Prometheus database wrapper
DATABASES = {
    'default': {
        'ENGINE': 'django_prometheus.db.backends.postgresql',
        # ... rest
    }
}

# Expose metrics endpoint
urlpatterns = [
    path('metrics/', include('django_prometheus.urls')),
]
```

**Files to Modify**:
- `backend/core/settings.py`
- `backend/core/urls.py`
- `requirements.txt` (add `django-prometheus`)
- `docker-compose.yml` (add Prometheus + Grafana containers)

**Dependencies**: None

**Verification**:
```bash
curl http://localhost:8088/metrics/
# Should return Prometheus metrics
```

---

### Group E: Async Processing & Performance (2 issues)

#### P0-OP-03: Synchronous PDF Processing (Blocking Operations)
**Risk Score**: 44 (Impact: 5, Likelihood: 4, Urgency: 2.2)  
**Effort**: XL (12-16 hours)  
**Priority**: 12 (BLOCKER)

**Symptom**: PDF import/flatten blocks HTTP workers → service unavailable

**Root Cause**: No Celery tasks defined, all PDF ops synchronous

**Fix Strategy**:
```python
# Create backend/grading/tasks.py
from celery import shared_task
from grading.services import GradingService
from exams.models import Copy

@shared_task(bind=True, max_retries=3)
def async_import_pdf(self, exam_id, pdf_path, user_id):
    try:
        exam = Exam.objects.get(id=exam_id)
        user = User.objects.get(id=user_id)
        
        with open(pdf_path, 'rb') as f:
            copy = GradingService.import_pdf(exam, f, user)
        
        return {'copy_id': str(copy.id), 'status': 'success'}
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60)

@shared_task(bind=True, max_retries=3)
def async_finalize_copy(self, copy_id, user_id):
    try:
        copy = Copy.objects.get(id=copy_id)
        user = User.objects.get(id=user_id)
        GradingService.finalize_copy(copy, user)
        return {'copy_id': str(copy.id), 'status': 'graded'}
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60)

# Modify views to return task ID
from grading.tasks import async_finalize_copy

def finalize(self, request, copy_id):
    task = async_finalize_copy.delay(copy_id, request.user.id)
    return Response({'task_id': task.id, 'status': 'processing'}, 202)

# Add task status endpoint
@api_view(['GET'])
def task_status(request, task_id):
    result = AsyncResult(task_id)
    return Response({
        'task_id': task_id,
        'status': result.state,
        'result': result.result if result.ready() else None
    })
```

**Files to Modify**:
- `backend/grading/tasks.py` (NEW)
- `backend/grading/views.py` (convert to async)
- `backend/grading/urls.py` (add /tasks/<id>/ endpoint)
- `frontend/src/services/api.js` (poll task status)
- `frontend/src/views/GradingView.vue` (show progress spinner)

**Dependencies**: 
- Redis running (already configured)
- Celery worker deployed (`celery -A core worker`)

**Verification**:
```bash
# Start Celery worker
celery -A core worker -l info

# Submit task
curl -X POST /api/copies/finalize/
# Returns: {"task_id": "abc123", "status": "processing"}

# Poll status
curl /api/tasks/abc123/
# Returns: {"status": "SUCCESS", "result": {...}}
```

---

#### P0-OP-04: No Database Lock Timeout Protection (CRITICAL)
**Risk Score**: 42 (Impact: 5, Likelihood: 3, Urgency: 2.8)  
**Effort**: S (2-3 hours)  
**Priority**: 13

**Symptom**: Deadlocks hang indefinitely, blocking all requests

**Root Cause**: No PostgreSQL timeouts configured

**Fix Strategy**:
```python
# Add to backend/core/settings.py
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'OPTIONS': {
            'connect_timeout': 10,
            'options': '-c lock_timeout=5000 -c statement_timeout=30000',
            # lock_timeout: 5s max wait for lock acquisition
            # statement_timeout: 30s max query execution
        },
        'CONN_MAX_AGE': 600,
        'CONN_HEALTH_CHECKS': True,  # Django 4.1+
    }
}
```

**Files to Modify**:
- `backend/core/settings.py` (DATABASES config)

**Dependencies**: None

**Verification**:
```bash
# Connect to DB and verify settings
python manage.py dbshell
\echo :options
# Should show: -c lock_timeout=5000 -c statement_timeout=30000
```

---

### Group F: Crash Recovery & Deployment Safety (3 issues)

#### P0-OP-05: No Crash Recovery for PDF Processing (CRITICAL)
**Risk Score**: 36 (Impact: 4, Likelihood: 3, Urgency: 3)  
**Effort**: M (6-8 hours)  
**Priority**: 14

**Symptom**: PDF generation crashes → Copy stuck in inconsistent state

**Root Cause**: No recovery mechanism for interrupted PDF operations

**Fix Strategy**:
```python
# Add recovery command: backend/grading/management/commands/recover_stuck_copies.py
from django.core.management.base import BaseCommand
from exams.models import Copy
from django.utils import timezone
from datetime import timedelta

class Command(BaseCommand):
    help = 'Recover stuck copies from failed PDF operations'
    
    def handle(self, *args, **kwargs):
        # Find copies stuck in GRADING_IN_PROGRESS > 30 min
        threshold = timezone.now() - timedelta(minutes=30)
        stuck_copies = Copy.objects.filter(
            status=Copy.Status.GRADING_IN_PROGRESS,
            updated_at__lt=threshold
        )
        
        for copy in stuck_copies:
            self.stdout.write(f"Recovering copy {copy.id}")
            
            # Rollback to LOCKED
            copy.status = Copy.Status.LOCKED
            copy.grading_error_message = "Recovered from stuck state"
            copy.save()
            
            # Clean up orphaned PDF files
            if copy.final_pdf and os.path.exists(copy.final_pdf.path):
                os.unlink(copy.final_pdf.path)
                copy.final_pdf = None
                copy.save()
        
        self.stdout.write(self.style.SUCCESS(f'Recovered {stuck_copies.count()} copies'))

# Add cron job to run every 15 minutes
# */15 * * * * cd /app && python manage.py recover_stuck_copies
```

**Files to Modify**:
- `backend/grading/management/commands/recover_stuck_copies.py` (NEW)
- `docs/OPERATIONS.md` (document recovery procedure)

**Dependencies**: P0-DI-003 (GRADING_IN_PROGRESS status)

**Verification**:
```bash
# Manually create stuck copy
python manage.py shell -c "Copy.objects.filter(id=...).update(status='GRADING_IN_PROGRESS', updated_at=now()-timedelta(hours=1))"

# Run recovery
python manage.py recover_stuck_copies

# Verify status reset to LOCKED
```

---

#### P0-OP-06: No Migration Rollback Strategy (HIGH)
**Risk Score**: 30 (Impact: 5, Likelihood: 2, Urgency: 3)  
**Effort**: M (4-6 hours)  
**Priority**: 15

**Symptom**: Failed migrations leave DB in inconsistent state

**Root Cause**: No documented rollback procedures

**Fix Strategy**:
1. **Document rollback procedure** in `docs/DEPLOYMENT_GUIDE.md`
2. **Test all migrations for reversibility**:
   ```bash
   python manage.py migrate grading 0023  # forward
   python manage.py migrate grading 0022  # backward (test rollback)
   ```
3. **Add migration tests**:
   ```python
   # backend/tests/test_migrations.py
   from django.test import TransactionTestCase
   from django_migrate_sql_deux.management.commands.migrate import Command
   
   class MigrationRollbackTest(TransactionTestCase):
       def test_all_migrations_reversible(self):
           # Get all migration files
           # For each migration: migrate forward, then backward
           # Verify no errors
   ```

**Files to Modify**:
- `docs/DEPLOYMENT_GUIDE.md` (add rollback section)
- `backend/tests/test_migrations.py` (NEW)

**Dependencies**: None

**Verification**:
```bash
# Test rollback for recent migrations
python manage.py migrate grading 0025
python manage.py migrate grading 0024  # Should succeed
```

---

#### P0-OP-07: No Readiness/Liveness Probe Strategy (HIGH)
**Risk Score**: 27 (Impact: 4, Likelihood: 3, Urgency: 2.25)  
**Effort**: S (3-4 hours)  
**Priority**: 16

**Symptom**: Orchestrator restarts healthy containers, leaves unhealthy ones running

**Root Cause**: No separate readiness vs liveness endpoints

**Fix Strategy**:
```python
# Enhance health check endpoint
# backend/core/views_health.py
from django.http import JsonResponse
from django.db import connection
from django.core.cache import cache

@api_view(['GET'])
def liveness(request):
    """Liveness probe - is the app running?"""
    return Response({"status": "alive"}, status=200)

@api_view(['GET'])
def readiness(request):
    """Readiness probe - can the app serve traffic?"""
    checks = {}
    overall_healthy = True
    
    # Check 1: Database connection
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        checks['database'] = 'ok'
    except Exception as e:
        checks['database'] = f'error: {str(e)}'
        overall_healthy = False
    
    # Check 2: Cache connection (Redis)
    try:
        cache.set('health_check', 'ok', 10)
        if cache.get('health_check') == 'ok':
            checks['cache'] = 'ok'
        else:
            checks['cache'] = 'error'
            overall_healthy = False
    except Exception as e:
        checks['cache'] = f'error: {str(e)}'
        overall_healthy = False
    
    # Check 3: Media directory writable
    try:
        test_file = settings.MEDIA_ROOT / '.health_check'
        test_file.write_text('ok')
        test_file.unlink()
        checks['media'] = 'ok'
    except Exception as e:
        checks['media'] = f'error: {str(e)}'
        overall_healthy = False
    
    status_code = 200 if overall_healthy else 503
    return Response({
        'status': 'ready' if overall_healthy else 'not_ready',
        'checks': checks
    }, status=status_code)

# Add to urls.py
urlpatterns = [
    path('health/live/', liveness),
    path('health/ready/', readiness),
]
```

**Files to Modify**:
- `backend/core/views_health.py` (split into liveness + readiness)
- `backend/core/urls.py` (add /health/live/ and /health/ready/)
- `docker-compose.yml` (add healthcheck configs)

**Dependencies**: None

**Verification**:
```bash
curl http://localhost:8088/health/live/   # Always 200 if app running
curl http://localhost:8088/health/ready/  # 200 if DB+cache+media OK, 503 otherwise
```

---

## Phase 3: P1 Security Fixes (HIGH - 3-4 days)

### P1.1: Missing Structured Logging Configuration
**Covered by P0-OP-01** ✅

---

### P1.2: Weak Password Validation
**Risk Score**: 24 (Impact: 4, Likelihood: 4, Urgency: 1.5)  
**Effort**: S (2-3 hours)  
**Priority**: 17

**Fix Strategy**:
```python
# backend/core/settings.py
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', 'OPTIONS': {'min_length': 12}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# backend/core/views.py - Update ChangePasswordView
from django.contrib.auth.password_validation import validate_password

def post(self, request):
    password = request.data.get('password')
    try:
        validate_password(password, user=request.user)
    except ValidationError as e:
        return Response({"error": e.messages}, status=400)
    
    request.user.set_password(password)
    request.user.save()
    update_session_auth_hash(request, request.user)
    return Response({"message": "Password updated"})
```

**Files to Modify**:
- `backend/core/settings.py` (AUTH_PASSWORD_VALIDATORS)
- `backend/core/views.py` (ChangePasswordView)

**Tests to Add**:
- `test_weak_password_rejected()` - "123456" fails
- `test_common_password_rejected()` - "password" fails

---

### P1.3: Missing Session Security Configuration
**Risk Score**: 22 (Impact: 4, Likelihood: 3, Urgency: 1.8)  
**Effort**: S (2-3 hours)  
**Priority**: 18

**Fix Strategy**:
```python
# backend/core/settings.py
SESSION_ENGINE = 'django.contrib.sessions.backends.cached_db'
SESSION_COOKIE_AGE = 14400  # 4 hours
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SESSION_SAVE_EVERY_REQUEST = True  # Refresh expiry on activity
```

**Files to Modify**:
- `backend/core/settings.py`

---

### P1.4: Information Disclosure in Error Messages
**Risk Score**: 21 (Impact: 3, Likelihood: 4, Urgency: 1.75)  
**Effort**: M (4-6 hours)  
**Priority**: 19

**Fix Strategy**:
```python
# Create generic error handler
def safe_error_response(exception, log_context=None):
    logger.error(f"Error: {exception}", exc_info=True, extra=log_context or {})
    
    if settings.DEBUG:
        return Response({"error": str(exception)}, status=500)
    else:
        return Response({"error": "An error occurred. Please contact support."}, status=500)

# Replace all `str(e)` with safe_error_response(e)
```

**Files to Modify**: 22 locations across views.py files

---

### P1.5: CSP 'unsafe-inline' in Production
**Risk Score**: 20 (Impact: 4, Likelihood: 2, Urgency: 2.5)  
**Effort**: M (4-6 hours)  
**Priority**: 20

**Fix Strategy**:
```python
# backend/core/settings.py
CSP_STYLE_SRC = ("'self'", "'nonce-{nonce}'")  # Remove 'unsafe-inline'
CSP_SCRIPT_SRC = ("'self'", "'nonce-{nonce}'")

# Use django-csp nonce in templates
```

---

### P1.6: Missing Rate Limiting on Sensitive Endpoints
**Risk Score**: 18 (Impact: 3, Likelihood: 3, Urgency: 2)  
**Effort**: M (4-5 hours)  
**Priority**: 21

**Fix Strategy**: Extend rate limiting to all POST/PUT/DELETE endpoints

---

### P1.7: Database Query Optimization (N+1 Queries)
**Risk Score**: 16 (Impact: 2, Likelihood: 4, Urgency: 2)  
**Effort**: M (4-6 hours)  
**Priority**: 22

**Fix Strategy**: Add `select_related()` and `prefetch_related()` to critical querysets

---

## Phase 4: P1 Reliability Fixes (HIGH - 6-7 days)

**Note**: 18 P1 Reliability issues documented in P1_RELIABILITY_ISSUES.md

**Effort Summary**:
- Error Handling: 5 issues × 2-4 hours = 10-20 hours
- Resource Leaks: 3 issues × 3-4 hours = 9-12 hours
- Performance: 4 issues × 4-6 hours = 16-24 hours
- Timeouts: 3 issues × 2-3 hours = 6-9 hours
- Observability: Covered by P0-OP-01, P0-OP-02, P0-OP-08

**Total**: ~40-60 hours (5-7 days with testing)

**Priority Range**: 23-40 (defer to post-launch for non-critical)

---

## Implementation Roadmap

### Week 1: P0 Data Integrity (Critical Path)
**Days 1-2**: Race Conditions
- P0-DI-001: Lock acquisition race
- P0-DI-002: DraftState race
- P0-DI-003: Finalization race

**Days 3-4**: File & Cascade Protection
- P0-DI-005: Cascade deletion protection
- P0-DI-006: File orphaning cleanup
- P0-DI-007: Annotation race condition

**Day 5**: State Integrity
- P0-DI-008: Atomic state transitions
- Testing & verification

---

### Week 2: P0 Operational + P1 Security
**Days 1-2**: Observability
- P0-OP-01: Logging configuration
- P0-OP-02: Error alerting (Sentry)
- P0-OP-08: Metrics (Prometheus)

**Days 3-4**: Async Processing
- P0-OP-03: Celery tasks for PDF operations
- Frontend polling integration
- Testing with background workers

**Day 5**: Hardening + Security
- P0-OP-04: DB lock timeouts
- P0-OP-05: Crash recovery command
- P0-OP-06: Migration rollback docs
- P0-OP-07: Readiness/liveness probes
- P1.2-P1.7: Security fixes (password, session, CSP, rate limiting)

---

### Week 3: P1 Reliability (Optional but Recommended)
**Days 1-2**: Error Handling & Retry Logic
- P1-REL-001 to P1-REL-005

**Days 3-4**: Resource Management & Performance
- P1-REL-006 to P1-REL-012

**Day 5**: Timeouts & Final Testing
- P1-REL-013 to P1-REL-015
- Full regression testing

---

## Testing Strategy

### Unit Tests (Added Per Fix)
- Concurrency tests: `test_concurrency.py` (threading, multiprocessing)
- State machine tests: `test_state_transitions.py`
- Idempotency tests: `test_idempotent_operations.py`

### Integration Tests
- PDF pipeline end-to-end: Upload → Split → Identify → Grade → Finalize
- Multi-user scenarios: 3 teachers, 50 students, 200 copies
- Failure recovery: Crash mid-operation, verify recovery

### Load Tests (Critical for P0-OP-03)
```bash
# Use Locust or Apache Bench
locust -f tests/load/test_grading.py --host=http://localhost:8088
# Scenarios:
# - 10 concurrent PDF uploads
# - 20 concurrent finalizations
# - 100 concurrent autosaves
# Verify: No 500s, no deadlocks, all operations complete
```

### Regression Tests
- Run full test suite after each phase
- Verify E2E tests still pass
- Check for new N+1 queries (`django-debug-toolbar`)

---

## Rollback Plan

For each fix, document rollback procedure:

**Example: P0-DI-003 (Finalization race)**
```bash
# Rollback migration
python manage.py migrate grading 0024  # Revert to before GRADING_IN_PROGRESS

# Revert code changes
git revert <commit-hash>

# Restart services
docker-compose restart backend

# Verify health
curl http://localhost:8088/health/ready/
```

---

## Success Criteria

### Phase 1 (P0 Data Integrity) - DONE when:
- ✅ All 8 P0-DI issues resolved
- ✅ Concurrency tests pass (100 runs, 0 failures)
- ✅ Load test: 10 concurrent finalizations, 0 race conditions
- ✅ Manual verification: 2 teachers cannot lock same copy

### Phase 2 (P0 Operational) - DONE when:
- ✅ All 8 P0-OP issues resolved
- ✅ Logging outputs JSON to console in production mode
- ✅ Sentry receives test alert
- ✅ Prometheus metrics endpoint returns data
- ✅ PDF finalization returns task ID (not blocking)
- ✅ Readiness probe fails when DB down

### Phase 3 (P1 Security) - DONE when:
- ✅ All 7 P1 Security issues resolved
- ✅ Weak password "123456" rejected
- ✅ Session expires after 4 hours
- ✅ Error messages don't expose internals in production
- ✅ CSP headers present (no unsafe-inline)

### Phase 4 (P1 Reliability) - DONE when:
- ✅ All 18 P1 Reliability issues resolved
- ✅ PDF processing retries on transient errors (3 max)
- ✅ Image resources closed properly (file descriptor count stable)
- ✅ N+1 queries eliminated (Django Debug Toolbar)
- ✅ Bulk operations show progress

---

## Deployment Checklist

Before deploying fixes to production:

- [ ] All P0 issues resolved (16 total)
- [ ] All P1 Security issues resolved (7 total)
- [ ] All migrations tested (forward + backward)
- [ ] Load tests pass (no degradation)
- [ ] Logging configured and tested
- [ ] Error alerting configured (Sentry DSN in .env)
- [ ] Metrics exposed (/metrics/ endpoint)
- [ ] Celery workers deployed (celery -A core worker)
- [ ] Redis cache available
- [ ] Database backups configured
- [ ] Rollback plan documented
- [ ] Incident response runbook updated
- [ ] Smoke tests pass in staging environment

---

## Dependencies Graph

```
P0-DI-003 (Finalization race)
  └─ Requires: Copy.Status.GRADING_IN_PROGRESS (migration)
  └─ Blocks: P0-DI-004 (rollback on PDF failure)
  └─ Blocks: P0-OP-05 (crash recovery)

P0-OP-01 (Logging)
  └─ Blocks: P0-OP-02 (Error alerting - needs log handlers)

P0-OP-03 (Async PDF)
  └─ Requires: Redis running
  └─ Requires: Celery worker deployed
  └─ Affects: Frontend (needs polling logic)

P0-DI-005 (Cascade deletion)
  └─ Requires: Migration (on_delete=PROTECT)
  └─ Optional: Soft-delete implementation

All P1 issues:
  └─ Can proceed in parallel after P0 issues resolved
```

---

## Effort Summary

| Phase | Issues | Effort (days) | Priority |
|-------|--------|---------------|----------|
| Phase 1: P0 Data Integrity | 8 | 4-5 | BLOCKER |
| Phase 2: P0 Operational | 8 | 5-6 | BLOCKER |
| Phase 3: P1 Security | 7 | 3-4 | REQUIRED |
| Phase 4: P1 Reliability | 18 | 6-7 | RECOMMENDED |
| **Total** | **41** | **18-22** | - |

---

## Next Steps

1. **Review this plan** with stakeholders
2. **Prioritize phases** based on deployment timeline
3. **Assign owners** for each issue
4. **Create tracking tickets** (Jira, GitHub Issues)
5. **Start Phase 1** (P0 Data Integrity) immediately
6. **Daily standups** during implementation
7. **Code review** for each fix before merge
8. **Continuous testing** after each merge

---

**Plan Status**: ✅ READY FOR APPROVAL  
**Last Updated**: 2026-01-27  
**Next Review**: After Phase 1 completion
