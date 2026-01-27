# P1 High-Severity Security Issues - Korrigo Platform

**Audit Date**: 2026-01-27  
**Audit Type**: Production Readiness - P1 Security Issues  
**Scope**: High-severity security issues (serious but not blocking production)  
**Priority**: P1 (Must fix before production deployment)

---

## Executive Summary

This document lists **7 P1 (High-Severity) security issues** identified during the production readiness audit. While these issues are not immediately blocking (P0), they represent serious security gaps that must be addressed before production deployment.

**Risk Assessment**:
- **0 P0 issues** (critical blockers) - ✅ All resolved in previous phases
- **7 P1 issues** (high-severity) - ⚠️ Require immediate attention
- Impact: Information disclosure, weak authentication, insufficient observability

---

## P1.1: Missing Structured Logging Configuration

### Severity: P1 - High

### Symptom
No `LOGGING` configuration in `settings.py`. Application relies on default Django logging which is insufficient for production monitoring, incident response, and security auditing.

### Location
- **File**: `backend/core/settings.py`
- **Evidence**: `grep -r "LOGGING" backend/core/settings.py` returns no results

### Risk
- **Production Impact**: Cannot detect security incidents, performance issues, or errors in real-time
- **GDPR/Compliance**: Insufficient audit trail for compliance requirements
- **Incident Response**: Cannot diagnose production issues without structured logs
- **Observability**: No integration with monitoring systems (CloudWatch, Datadog, Sentry)

### Proof
```bash
# No LOGGING configuration found
$ grep -i "^LOGGING" backend/core/settings.py
# (no output)

# Audit logger exists but no handlers/formatters configured
$ grep "audit_logger" backend/core/utils/audit.py
audit_logger = logging.getLogger('audit')
```

### Current State
- Audit trail writes to database via `AuditLog` model (✅ good)
- `audit_logger.info()` calls exist but no structured output configured
- No log aggregation, rotation, or retention policy
- No separation between dev/prod logging levels

### Recommended Fix

**Add comprehensive LOGGING configuration to `settings.py`**:

```python
# Production Logging Configuration
import os

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'json': {
            '()': 'pythonjsonlogger.jsonlogger.JsonFormatter',
            'format': '%(asctime)s %(name)s %(levelname)s %(message)s %(pathname)s %(lineno)d'
        },
        'verbose': {
            'format': '[{asctime}] {levelname} {name} {module} {message}',
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
            'filename': os.path.join(BASE_DIR, 'logs', 'audit.log'),
            'maxBytes': 10485760,  # 10MB
            'backupCount': 10,
            'formatter': 'json',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': os.environ.get('DJANGO_LOG_LEVEL', 'INFO'),
        },
        'audit': {
            'handlers': ['console', 'audit_file'],
            'level': 'INFO',
            'propagate': False,
        },
        'django.security': {
            'handlers': ['console'],
            'level': 'WARNING',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    }
}
```

**Dependencies**:
```bash
pip install python-json-logger
```

### Test Verification
```bash
# Verify logging configuration loads
python manage.py check --deploy

# Verify audit logs are structured
python manage.py shell -c "from core.utils.audit import audit_logger; audit_logger.info('test', extra={'action': 'test'})"
```

---

## P1.2: Weak Password Validation (Empty AUTH_PASSWORD_VALIDATORS)

### Severity: P1 - High

### Symptom
`AUTH_PASSWORD_VALIDATORS = []` (empty list). No password strength requirements enforced by Django. Only custom validation is `len(password) >= 6` in `ChangePasswordView`.

### Location
- **File**: `backend/core/settings.py:182`
- **Evidence**: `AUTH_PASSWORD_VALIDATORS = []`
- **File**: `backend/core/views.py:112`
- **Evidence**: `if not password or len(password) < 6:`

### Risk
- **Brute Force**: Users can set weak passwords (e.g., "123456", "password")
- **Credential Stuffing**: Common passwords from breaches can be reused
- **Compliance**: Violates ANSSI/CNIL password security recommendations

### Proof
```python
# backend/core/settings.py:182
AUTH_PASSWORD_VALIDATORS = []

# backend/core/views.py:112 - Only validation is length >= 6
if not password or len(password) < 6:
    return Response({"error": "Password too short"}, status=status.HTTP_400_BAD_REQUEST)
```

**Test**:
```bash
# User can set weak password "123456" (6 chars, all digits)
curl -X POST http://localhost:8088/api/change-password/ \
  -H "Cookie: sessionid=..." \
  -d '{"password": "123456"}' \
  # Returns 200 OK - weak password accepted
```

### Current State
- Minimum length: 6 characters (weak - industry standard is 12+)
- No complexity requirements (uppercase, digits, special chars)
- No common password checking (Django's CommonPasswordValidator)
- No user attribute similarity check (username in password)

### Recommended Fix

**Update `settings.py` to enforce strong passwords**:

```python
# Password Validation (ANSSI/CNIL compliant)
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {
            'min_length': 12,  # ANSSI recommends 12+ characters
        }
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]
```

**Remove custom validation in `views.py` (Django validators will handle it)**:

```python
# backend/core/views.py - Remove manual length check (lines 112-113)
# Django's password_validation.validate_password() will handle all checks

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

def post(self, request):
    user = request.user
    password = request.data.get('password')
    
    try:
        validate_password(password, user=user)
    except ValidationError as e:
        return Response({"error": e.messages}, status=status.HTTP_400_BAD_REQUEST)
    
    user.set_password(password)
    user.save()
    update_session_auth_hash(request, user)
    
    return Response({"message": "Password updated successfully"})
```

### Test Verification
```python
# Test weak password rejection
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.models import User

user = User.objects.first()

# Should raise ValidationError
validate_password("123456", user=user)  # Too short, all numeric
validate_password("password", user=user)  # Common password
validate_password("john.doe", user=user)  # Similar to username
```

---

## P1.3: Missing Session Security Configuration

### Severity: P1 - High

### Symptom
No session timeout (`SESSION_COOKIE_AGE`), no session expiry on browser close (`SESSION_EXPIRE_AT_BROWSER_CLOSE`), no session engine configuration. Sessions persist indefinitely by default (Django default: 2 weeks).

### Location
- **File**: `backend/core/settings.py`
- **Missing Settings**: `SESSION_COOKIE_AGE`, `SESSION_EXPIRE_AT_BROWSER_CLOSE`, `SESSION_ENGINE`

### Risk
- **Session Hijacking**: Long-lived sessions increase attack window
- **Unauthorized Access**: Student sessions persist across browser restarts (shared computers in schools)
- **Compliance**: CNIL recommends session timeout for sensitive data

### Proof
```bash
# No session timeout configured
$ grep "SESSION_COOKIE_AGE\|SESSION_EXPIRE_AT_BROWSER_CLOSE\|SESSION_ENGINE" backend/core/settings.py
# (no output - uses Django defaults)

# Django default: SESSION_COOKIE_AGE = 1209600 (2 weeks)
```

**Scenario**:
1. Student logs in on shared library computer
2. Student views exam results (GDPR-sensitive data)
3. Student closes browser (but doesn't logout)
4. Session persists for 2 weeks
5. Next user can access previous student's data

### Current State
- **Django Defaults** (implicit):
  - `SESSION_COOKIE_AGE = 1209600` (14 days)
  - `SESSION_EXPIRE_AT_BROWSER_CLOSE = False`
  - `SESSION_ENGINE = 'django.contrib.sessions.backends.db'`
- Student portal uses session-based auth (no JWT)
- No automatic session invalidation

### Recommended Fix

**Add session security configuration to `settings.py`**:

```python
# Session Security Configuration
SESSION_ENGINE = 'django.contrib.sessions.backends.cached_db'  # Faster than pure DB

# Session timeout: 4 hours (reasonable for exam grading workflow)
SESSION_COOKIE_AGE = 14400  # 4 hours in seconds

# Student sessions expire on browser close (GDPR best practice)
# Note: This is global, but student sessions should be short-lived
# For production, consider separate session backend for student portal
SESSION_EXPIRE_AT_BROWSER_CLOSE = True

# Session security (already configured, verify)
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
# SESSION_COOKIE_SECURE = True (already handled via SSL_ENABLED logic)

# Optional: Clear expired sessions periodically (add to cron/Celery)
# python manage.py clearsessions
```

**Alternative: Dual Session Timeout**:

For differentiated timeout (teacher vs student):
```python
# Teacher/Admin: 8 hours (long grading sessions)
# Student: Browser close + 1 hour max

# Implement middleware to set different session timeouts
# backend/core/middleware.py
class DualSessionTimeoutMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        if request.session.get('role') == 'Student':
            request.session.set_expiry(3600)  # 1 hour for students
        else:
            request.session.set_expiry(28800)  # 8 hours for teachers
        
        return self.get_response(request)
```

### Test Verification
```python
# Verify session timeout
from django.test import Client
from django.utils import timezone
from datetime import timedelta

client = Client()
client.post('/api/students/login/', {'ine': '...'})

# Session should expire after SESSION_COOKIE_AGE
session = client.session
session['last_activity'] = timezone.now() - timedelta(hours=5)
session.save()

# Request should require re-login
response = client.get('/api/students/me/')
assert response.status_code == 401
```

---

## P1.4: Information Disclosure in Error Messages

### Severity: P1 - Medium-High

### Symptom
Multiple API endpoints expose internal exception details via `str(e)` in error responses. This can leak sensitive information (file paths, database schema, library versions) to attackers.

### Location
**22 instances found across the codebase**:

1. `backend/core/views_health.py:25` - Health check exposes DB errors
2. `backend/grading/views.py:35` - Service errors expose internal details
3. `backend/exams/views.py:63` - PDF processing errors expose file paths
4. `backend/exams/views.py:90-92` - Import errors expose internal state
5. `backend/identification/views.py:203` - OCR errors expose details
6. `backend/students/views.py:130` - CSV import errors expose details

### Risk
- **Information Disclosure**: Attackers can learn about:
  - Internal file paths (`/app/media/...`)
  - Database schema (`relation "..." does not exist`)
  - Library versions (`PyMuPDF 1.23.8 error ...`)
  - Business logic details
- **Reconnaissance**: Helps attackers plan targeted attacks
- **Compliance**: OWASP A01:2021 - Broken Access Control / Information Disclosure

### Proof

**Example 1: Health Check Leak** (`backend/core/views_health.py:22-26`):
```python
except Exception as e:
    return Response({
        'status': 'unhealthy',
        'error': str(e)  # ⚠️ Exposes internal DB errors
    }, status=503)
```

**Attack Scenario**:
```bash
# If DB is misconfigured, attacker learns DB type & version
$ curl http://example.com/api/health/
{
  "status": "unhealthy",
  "error": "FATAL:  password authentication failed for user \"postgres\""
}
# Attacker now knows: PostgreSQL, username, auth method
```

**Example 2: PDF Processing Leak** (`backend/exams/views.py:58-64`):
```python
except Exception as e:
    logger.error(f"Error processing PDF: {e}", exc_info=True)
    return Response({
        "error": f"PDF processing failed: {str(e)}"  # ⚠️ Exposes file paths, library errors
    }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
```

**Attack Scenario**:
```bash
# Malformed PDF reveals internal paths
$ curl -F "pdf_source=@malformed.pdf" http://example.com/api/exams/upload/
{
  "error": "PDF processing failed: [Errno 2] No such file or directory: '/app/media/exams/temp_123.pdf'"
}
# Attacker now knows: file system structure, temp file naming
```

### Current State
- 22 instances of `str(e)` in error responses
- Some instances log full exception (`exc_info=True`) ✅ but still expose to user
- No distinction between dev/prod error verbosity

### Recommended Fix

**1. Create generic error handler** (`backend/core/utils/errors.py`):
```python
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

def safe_error_response(exception, context="Operation", user_message=None):
    """
    Return safe error response that doesn't leak internal details.
    
    - Production: Generic message
    - Development: Full exception details
    - Always log full exception for debugging
    """
    # Log full exception for debugging (secure logs)
    logger.error(f"{context} failed: {exception}", exc_info=True)
    
    if settings.DEBUG:
        # Development: show details
        return {"error": f"{context} failed: {str(exception)}"}
    else:
        # Production: generic message
        return {
            "error": user_message or f"{context} failed. Please contact support.",
            "error_code": "INTERNAL_ERROR"
        }
```

**2. Update all error handlers**:

```python
# backend/core/views_health.py
except Exception as e:
    logger.error(f"Health check failed: {e}", exc_info=True)
    return Response({
        'status': 'unhealthy',
        'error': 'Service unavailable'  # Generic message
    }, status=503)

# backend/exams/views.py
except Exception as e:
    from core.utils.errors import safe_error_response
    return Response(
        safe_error_response(e, context="PDF processing", user_message="PDF upload failed. Please verify the file is valid."),
        status=status.HTTP_500_INTERNAL_SERVER_ERROR
    )
```

**3. Update existing error handlers**:

Files to update:
- `backend/core/views_health.py:25`
- `backend/exams/views.py:63, 90, 92, 169, 438, 453, 455`
- `backend/identification/views.py:203`
- `backend/students/views.py:130`
- `backend/grading/services.py:216`

### Test Verification
```python
# Verify no internal details leaked
response = client.post('/api/exams/upload/', {'pdf_source': malformed_pdf})
assert response.status_code == 500
assert '/app/media/' not in response.json()['error']  # No file paths
assert 'PyMuPDF' not in response.json()['error']  # No library names
assert 'Traceback' not in response.json()['error']  # No stack traces
```

---

## P1.5: CSP 'unsafe-inline' in Production

### Severity: P1 - Medium

### Symptom
Content Security Policy (CSP) allows `'unsafe-inline'` for `script-src` and `style-src` even in production mode. This significantly weakens XSS protection.

### Location
- **File**: `backend/core/settings.py:258-272`
- **Evidence**: `'script-src': ["'self'", "'unsafe-inline'"]` in production CSP

### Risk
- **XSS Vulnerability**: Inline scripts can execute if XSS vulnerability exists
- **Defense-in-Depth**: CSP is meant as last line of defense against XSS
- **Compliance**: OWASP recommends strict CSP without unsafe-inline

### Proof
```python
# backend/core/settings.py:258-272
if not DEBUG:
    # CSP stricte en production
    CONTENT_SECURITY_POLICY = {
        'DIRECTIVES': {
            'default-src': ["'self'"],
            'script-src': ["'self'", "'unsafe-inline'"],  # ⚠️ Weak
            'style-src': ["'self'", "'unsafe-inline'"],   # ⚠️ Weak
            'img-src': ["'self'", "data:", "blob:"],
            'font-src': ["'self'"],
            'connect-src': ["'self'"],
            'frame-ancestors': ["'none'"],
            'base-uri': ["'self'"],
            'form-action': ["'self'"],
            'upgrade-insecure-requests': True,
        }
    }
```

### Current State
- CSP is enabled via `django-csp` ✅
- Middleware is configured ✅
- But `unsafe-inline` weakens protection significantly
- Vue.js SPA may require inline scripts (need to verify)

### Recommended Fix

**Option 1: Use Nonces (Recommended for Vue.js SPA)**

Django-CSP supports nonces for inline scripts:

```python
# backend/core/settings.py
if not DEBUG:
    CONTENT_SECURITY_POLICY = {
        'DIRECTIVES': {
            'default-src': ["'self'"],
            'script-src': ["'self'"],  # Remove unsafe-inline
            'style-src': ["'self'"],   # Remove unsafe-inline
            'img-src': ["'self'", "data:", "blob:"],
            'font-src': ["'self'"],
            'connect-src': ["'self'"],
            'frame-ancestors': ["'none'"],
            'base-uri': ["'self'"],
            'form-action': ["'self'"],
            'upgrade-insecure-requests': True,
        }
    }
    
    # Enable nonce generation
    CSP_INCLUDE_NONCE_IN = ['script-src', 'style-src']
```

**Frontend Changes Required**:
If Vue.js uses inline scripts in `index.html`, add nonce:
```html
<!-- frontend/index.html -->
<script nonce="{{ request.csp_nonce }}">
  // Inline initialization code
</script>
```

**Option 2: Hash-based CSP (if no dynamic inline scripts)**

If inline scripts are static, use hash-based CSP:
```bash
# Generate hash for inline script
echo -n "console.log('hello')" | openssl dgst -sha256 -binary | openssl base64
# Output: Zxy1x2y3...

# Add to CSP
'script-src': ["'self'", "'sha256-Zxy1x2y3...'"]
```

**Option 3: Accept Risk with Justification**

If Vue.js build process requires unsafe-inline (verify first):
- Document justification in code comment
- Implement strict input validation & output encoding
- Add CSP violation reporting endpoint

```python
# If unsafe-inline is truly required, add violation reporting
CONTENT_SECURITY_POLICY = {
    'DIRECTIVES': {
        # ... existing directives
        'script-src': ["'self'", "'unsafe-inline'"],  # JUSTIFIED: Vue.js SPA build requirement
        'report-uri': ['/api/csp-report/'],
    }
}
```

### Test Verification
```bash
# Verify CSP header
curl -I http://localhost:8088/
# Should see: Content-Security-Policy: script-src 'self'; style-src 'self'; ...

# Verify inline scripts blocked (if nonce not used)
# Browser console should show CSP violation if inline script without nonce
```

### Investigation Required
**Action**: Check if Vue.js build actually requires unsafe-inline
```bash
cd frontend
npm run build
# Inspect dist/index.html for inline scripts
grep -E "<script[^>]*>" dist/index.html
```

If no inline scripts, remove `unsafe-inline` immediately.

---

## P1.6: Missing Rate Limiting on Sensitive Endpoints

### Severity: P1 - Medium

### Symptom
Rate limiting is implemented for login endpoints (`@maybe_ratelimit(key='ip', rate='5/15m')`), but **missing on other sensitive endpoints**:
- Password change (`/api/change-password/`)
- User creation (`/api/users/` POST)
- Student import (`/api/students/import/` POST)
- File uploads (PDF processing endpoints)

### Location
- **Protected**: `core/views.py:LoginView`, `students/views.py:StudentLoginView` ✅
- **Missing**: `core/views.py:ChangePasswordView`, `core/views.py:UserListView.post`, `students/views.py:StudentImportView`, `exams/views.py:ExamUploadView`

### Risk
- **Brute Force**: Attacker can enumerate users via user creation endpoint
- **DoS**: Bulk student import or PDF uploads can exhaust resources
- **Resource Exhaustion**: Unlimited PDF processing requests
- **Credential Stuffing**: Password change without rate limit

### Proof

**Login is protected** ✅:
```python
# backend/core/views.py:26
@method_decorator(maybe_ratelimit(key='ip', rate='5/15m', method='POST', block=True))
def post(self, request):
    # Login logic
```

**Password change is NOT protected** ⚠️:
```python
# backend/core/views.py:106-120
class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request):  # No rate limiting!
        # Password change logic
```

**Attack Scenario**:
```bash
# Attacker can try unlimited passwords for authenticated user
for i in {1..1000}; do
  curl -X POST http://example.com/api/change-password/ \
    -H "Cookie: sessionid=stolen_session" \
    -d "{\"password\": \"password$i\"}"
done
# No rate limit, all 1000 attempts processed
```

### Current State
- Rate limiting implemented via `django-ratelimit` ✅
- Configurable via `RATELIMIT_ENABLE` setting ✅
- Applied to login endpoints only ⚠️
- Other sensitive endpoints unprotected

### Recommended Fix

**Apply rate limiting to all sensitive endpoints**:

```python
# backend/core/views.py
from core.utils.ratelimit import maybe_ratelimit
from django.utils.decorators import method_decorator

class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]
    
    @method_decorator(maybe_ratelimit(key='user', rate='5/h', method='POST', block=True))
    def post(self, request):
        # Password change logic
        pass

class UserListView(APIView):
    # ... existing code
    
    @method_decorator(maybe_ratelimit(key='user', rate='10/h', method='POST', block=True))
    def post(self, request):
        # User creation logic
        pass

# backend/students/views.py
class StudentImportView(views.APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    
    @method_decorator(maybe_ratelimit(key='user', rate='10/h', method='POST', block=True))
    def post(self, request):
        # CSV import logic
        pass

# backend/exams/views.py
class ExamUploadView(APIView):
    permission_classes = [IsTeacherOrAdmin]
    parser_classes = (MultiPartParser, FormParser)
    
    @method_decorator(maybe_ratelimit(key='user', rate='20/h', method='POST', block=True))
    def post(self, request, *args, **kwargs):
        # PDF upload logic
        pass
```

**Rate Limits Rationale**:
- **Login**: `5/15m` per IP (existing) - prevents brute force
- **Password change**: `5/h` per user - legitimate use ~1/day
- **User creation**: `10/h` per admin - bulk user creation is rare
- **Student import**: `10/h` per user - imports are batch operations
- **PDF upload**: `20/h` per user - teachers may upload multiple exams

### Test Verification
```python
# Test rate limiting
from django.test import Client

client = Client()
client.login(username='teacher', password='...')

# Exceed rate limit
for i in range(10):
    response = client.post('/api/change-password/', {'password': f'newpass{i}'})

# 6th request should be blocked (rate: 5/h)
assert response.status_code == 429  # Too Many Requests
assert 'rate limit' in response.json()['detail'].lower()
```

---

## P1.7: Missing Database Query Optimization (Potential N+1 Queries)

### Severity: P1 - Medium (Performance/DoS)

### Symptom
No evidence of `select_related()` or `prefetch_related()` in views that serialize nested relationships. Potential N+1 query problems in:
- Copy list views (Copy → Student, Exam, Booklets)
- Annotation list views (Annotation → Copy → Student)
- Exam detail views (Exam → Copies → Student)

### Location
- `backend/exams/views.py:181` - `CopyListView`
- `backend/grading/views.py:48` - `AnnotationListCreateView`
- `backend/exams/views.py:104` - `ExamListView`

### Risk
- **Performance**: Slow page loads for large exams (100+ copies)
- **DoS**: Attacker can request large datasets to exhaust DB connections
- **Scalability**: Production database overload under normal load

### Proof

**Example: CopyListView** (`backend/exams/views.py:181-191`):
```python
class CopyListView(generics.ListAPIView):
    permission_classes = [IsTeacherOrAdmin]
    serializer_class = CopySerializer
    
    def get_queryset(self):
        exam_id = self.kwargs['exam_id']
        exam = get_object_or_404(Exam, id=exam_id)
        return Copy.objects.filter(exam=exam)
        # ⚠️ No select_related/prefetch_related
        # Serializer accesses copy.student, copy.exam, copy.booklets
        # = N+1 queries for N copies
```

**Attack Scenario**:
```bash
# Exam with 100 copies
# Each copy serialized triggers:
# - 1 query for copy.student
# - 1 query for copy.exam (cached after first)
# - M queries for copy.booklets.all()
# Total: ~100 + 100*M queries instead of 1-3 queries

# Attacker requests large exam
curl http://example.com/api/exams/123/copies/
# Backend executes 500+ queries
# DB connection pool exhausted
# Other requests blocked
```

### Current State
- Models have ForeignKey/ManyToMany relationships ✅
- Serializers access nested relationships
- No query optimization in views ⚠️
- No pagination on some list views ⚠️

### Recommended Fix

**1. Add query optimization to list views**:

```python
# backend/exams/views.py
class CopyListView(generics.ListAPIView):
    permission_classes = [IsTeacherOrAdmin]
    serializer_class = CopySerializer
    
    def get_queryset(self):
        exam_id = self.kwargs['exam_id']
        exam = get_object_or_404(Exam, id=exam_id)
        return Copy.objects.filter(exam=exam).select_related(
            'student',  # ForeignKey
            'exam'      # ForeignKey
        ).prefetch_related(
            'booklets',     # ManyToMany
            'annotations'   # Reverse ForeignKey (if serialized)
        )

# backend/grading/views.py
class AnnotationListCreateView(generics.ListCreateAPIView):
    # ... existing code
    
    def get_queryset(self):
        copy_id = self.kwargs['copy_id']
        copy = get_object_or_404(Copy, id=copy_id)
        return Annotation.objects.filter(copy=copy).select_related(
            'copy',         # ForeignKey
            'copy__student', # Nested ForeignKey
            'copy__exam'    # Nested ForeignKey
        )
```

**2. Add pagination to all list views**:

Already configured globally in `settings.py`:
```python
REST_FRAMEWORK = {
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 50,
}
```

Verify it's applied:
```bash
curl http://localhost:8088/api/exams/123/copies/
# Should return: {"count": 150, "next": "...", "results": [...]}
```

**3. Add database indexes** (check models):

```python
# backend/exams/models.py
class Copy(models.Model):
    # ... existing fields
    
    class Meta:
        indexes = [
            models.Index(fields=['exam', 'status']),  # Common filter
            models.Index(fields=['student', 'exam']),  # Student lookup
            models.Index(fields=['status']),           # Status filter
        ]
```

### Test Verification

**Enable query logging**:
```python
# settings.py (dev only)
LOGGING = {
    'loggers': {
        'django.db.backends': {
            'level': 'DEBUG',
            'handlers': ['console'],
        },
    }
}
```

**Test query count**:
```python
from django.test import TestCase
from django.test.utils import override_settings
from django.db import connection
from django.test.utils import CaptureQueriesContext

class QueryOptimizationTest(TestCase):
    def test_copy_list_queries(self):
        # Create exam with 10 copies
        exam = Exam.objects.create(...)
        for i in range(10):
            Copy.objects.create(exam=exam, student=...)
        
        # Count queries
        with CaptureQueriesContext(connection) as ctx:
            response = self.client.get(f'/api/exams/{exam.id}/copies/')
        
        # Should be ~3-5 queries (select_related/prefetch_related)
        # Without optimization: 20-30 queries (N+1)
        assert len(ctx.captured_queries) < 10, f"Too many queries: {len(ctx.captured_queries)}"
```

---

## Summary Table

| ID | Issue | Severity | Impact | Files Affected | Fix Effort |
|----|-------|----------|--------|----------------|------------|
| P1.1 | Missing LOGGING config | High | Observability, Incident Response | `settings.py` | 2h |
| P1.2 | Weak password validation | High | Authentication Security | `settings.py`, `views.py` | 1h |
| P1.3 | Missing session timeout | High | Session Security, GDPR | `settings.py` | 1h |
| P1.4 | Info disclosure in errors | Med-High | Information Leakage | 22 files | 4h |
| P1.5 | CSP unsafe-inline | Medium | XSS Defense-in-Depth | `settings.py`, `index.html` | 2-4h* |
| P1.6 | Missing rate limits | Medium | DoS, Brute Force | 4 views | 2h |
| P1.7 | N+1 query problems | Medium | Performance, DoS | 3+ views | 3h |

**Total Estimated Effort**: 15-17 hours

\* P1.5 effort depends on Vue.js build investigation

---

## Recommended Remediation Priority

**Phase 1 (Critical - Fix First)**:
1. ✅ P1.2 - Password validation (1h) - Quick win, high security impact
2. ✅ P1.3 - Session timeout (1h) - GDPR compliance, quick fix
3. ✅ P1.1 - Logging configuration (2h) - Required for production monitoring

**Phase 2 (High Priority)**:
4. ✅ P1.4 - Error message sanitization (4h) - Moderate effort, prevents recon
5. ✅ P1.6 - Rate limiting (2h) - DoS prevention

**Phase 3 (Medium Priority)**:
6. ✅ P1.7 - Query optimization (3h) - Performance, can be done incrementally
7. ✅ P1.5 - CSP hardening (2-4h) - Requires frontend investigation first

---

## Production Readiness Gate Impact

**Current Status**: ⚠️ **NOT READY** for production deployment

**Blocking Issues**:
- P1.1, P1.2, P1.3 must be fixed before production (security baseline)
- P1.4, P1.6 should be fixed (defense-in-depth)
- P1.5, P1.7 can be deferred to post-launch (with documented risk acceptance)

**Minimum Fixes Required for Production**:
- [ ] P1.1 - Logging (monitoring requirement)
- [ ] P1.2 - Password validation (ANSSI/CNIL compliance)
- [ ] P1.3 - Session timeout (GDPR requirement)
- [ ] P1.4 - Error sanitization (at minimum: health check, login errors)

**After Fixes**:
- ✅ Re-run security audit
- ✅ Verify fixes with automated tests
- ✅ Update production deployment checklist

---

## Next Steps

1. **Review this report with team** - Validate findings and priority
2. **Create remediation tickets** - One ticket per issue (P1.1-P1.7)
3. **Implement fixes in main repo** - NOT in worktree (per audit constraints)
4. **Add regression tests** - Prevent reintroduction of issues
5. **Update plan.md** - Mark P1 audit step as complete

---

**Audit Completed By**: Zenflow AI Assistant  
**Review Required**: Security Lead, Tech Lead  
**Next Audit Phase**: P1 Reliability Issues (after security fixes applied)
