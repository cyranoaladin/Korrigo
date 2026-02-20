# Verification Report - Korrigo/Korrigo Production-Like Stack
**Date**: 2026-01-24
**Environment**: Docker Compose local-prod stack

---

## Executive Summary

| Component | Status | Details |
|-----------|--------|---------|
| **Backend Tests** | ✅ PASS | 86 passed, 2 skipped |
| **Stack Health** | ✅ PASS | All 5 services healthy |
| **Frontend Build** | ✅ PASS | Vite build successful |
| **Security Headers** | ✅ PASS | All headers present |
| **E2E Tests** | ✅ 3/4 PASS | Student flow 100%, corrector needs booklet fixtures |

---

## PHASE 0: Inventory

### Compose Files
- `infra/docker/docker-compose.local-prod.yml` (main target)
- `infra/docker/docker-compose.prod.yml`
- `infra/docker/docker-compose.yml` (dev)

### Backend Stack
- **Python**: 3.11-slim (Docker)
- **Framework**: Django 4.2+, DRF
- **Test Framework**: pytest~=8.0, pytest-django~=4.8
- **Settings Module**: `core.settings_test`

### Frontend Stack
- **Node**: v20-alpine (Docker), v18.19.1 (local)
- **Framework**: Vue 3.4.15, Vite 5.1.0
- **E2E**: Playwright 1.57.0

### Local Tooling
- Docker: 29.1.5
- Docker Compose: v5.0.2

---

## PHASE 1: Clean Environment

```bash
docker compose -f infra/docker/docker-compose.local-prod.yml down -v
```
**Result**: All containers, volumes, and networks removed successfully.

---

## PHASE 2: Stack Up

```bash
docker compose -f infra/docker/docker-compose.local-prod.yml up -d --build
```

### Services Status
| Service | Image | Status | Port |
|---------|-------|--------|------|
| db | postgres:15-alpine | healthy | 5432 |
| redis | redis:7-alpine | healthy | 6379 |
| backend | docker-backend | healthy | 8000 |
| celery | docker-celery | running | - |
| nginx | docker-nginx | healthy | 8088:80 |

### Health Verification
```bash
curl -s http://127.0.0.1:8088/api/health/
# {"status":"healthy","database":"connected"}
```

---

## PHASE 3: Build

### Backend
- Migrations: Applied successfully
- Collectstatic: 161 static files

### Frontend
- `npm ci`: 188 packages installed
- Vite build: Successful (assets bundled)

---

## PHASE 4A: Backend Tests

### Command
```bash
docker compose -f infra/docker/docker-compose.local-prod.yml run --rm backend pytest -vv --trace-config
```

### Result: 86 passed, 2 skipped in 7.13s

### Proof Excerpt (First 10 lines)
```
PLUGIN registered: pytest-django
DJANGO_SETTINGS_MODULE = core.settings_test
collected 88 items
```

### Proof Excerpt (Last 10 lines)
```
grading/tests/test_serializers_strict.py::TestSerializersStrict::test_booklet_serializer_integrity PASSED [98%]
grading/tests/test_serializers_strict.py::TestSerializersStrict::test_copy_serializer_embedding PASSED [100%]

======================== 86 passed, 2 skipped in 7.13s =========================
```

### Test Categories Passed
- Rate limiting tests
- PDF validators tests
- Gate 4 student flow tests
- Grading workflow tests
- Concurrency tests
- Security hardening tests
- Integration tests

---

## PHASE 4B: E2E Tests

### Command
```bash
# Using E2E override to disable rate limiting
docker compose -f infra/docker/docker-compose.local-prod.yml -f infra/docker/docker-compose.e2e.yml up -d --build
cd frontend && npx playwright test --reporter=list
```

### Result: 3/4 passed ✅

| Test | Status |
|------|--------|
| Full Student Cycle: Login -> List -> PDF | ✅ PASS |
| Security: Student cannot access another student's PDF | ✅ PASS |
| Security: LOCKED copies not visible in list | ✅ PASS |
| Corrector Flow: Annotate -> Autosave -> Restore | ⚠️ Needs fixtures |

### Corrector Flow Issue
- **Root Cause**: Test copy has `"booklets":[]` (empty) - no pages to render canvas
- **Fix Needed**: E2E seed script should create copy with booklet/pages for annotation testing
- **Not a code bug**: Canvas layer correctly requires page image to render

---

## PHASE 5: Security Headers Validation

### Nginx Root Response
```
HTTP/1.1 200 OK
X-Frame-Options: DENY
X-Content-Type-Options: nosniff
X-XSS-Protection: 1; mode=block
Referrer-Policy: strict-origin-when-cross-origin
```

### API Response Headers
```
X-Frame-Options: DENY
X-Content-Type-Options: nosniff
Referrer-Policy: same-origin
Cross-Origin-Opener-Policy: same-origin
Content-Security-Policy: default-src 'self'; frame-ancestors 'none'; ...
```

### Security Gates Verified
- ✅ X-Frame-Options: DENY
- ✅ X-Content-Type-Options: nosniff
- ✅ X-XSS-Protection: 1; mode=block
- ✅ Referrer-Policy: strict-origin-when-cross-origin
- ✅ CSP with frame-ancestors 'none'

---

## Fixes Applied

### 1. Backend Dockerfile - libmagic
**File**: `backend/Dockerfile`
**Rationale**: python-magic requires libmagic1 system library
```dockerfile
RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    poppler-utils \
    curl \
    libmagic1 \  # Added
    && rm -rf /var/lib/apt/lists/*
```

### 2. Redis Cache Configuration
**File**: `backend/core/settings.py`
**Rationale**: django-ratelimit requires proper cache backend
```python
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': os.environ.get("CELERY_BROKER_URL", "redis://redis:6379/0"),
    }
}
RATELIMIT_USE_CACHE = 'default'
```

### 3. Test Rate Limiting Disabled
**File**: `backend/core/settings_test.py`
**Rationale**: Allow login tests to work without hitting rate limits
```python
RATELIMIT_ENABLE = False
```

### 4. MIME Validation Fix
**File**: `backend/exams/validators.py`
**Rationale**: ValidationError was being swallowed instead of propagated
```python
except ValidationError:
    raise  # Re-raise instead of logging
```

### 5. CSRF Exemption for Login Endpoints
**Files**: `backend/core/views.py`, `backend/students/views.py`
**Rationale**: Public login endpoints need CSRF exemption
```python
@method_decorator(csrf_exempt, name='dispatch')
class LoginView(APIView):
    authentication_classes = []
```

### 6. Frontend API Base URLs
**Files**: `frontend/src/services/api.js`, `frontend/src/services/gradingApi.js`
**Rationale**: Use relative URLs for nginx proxy
```javascript
baseURL: import.meta.env.VITE_API_URL || '/api',
```

### 7. Frontend Pagination Handling
**File**: `frontend/src/services/gradingApi.js`
**Rationale**: DRF returns paginated responses
```javascript
if (data && typeof data === 'object' && Array.isArray(data.results)) {
    return data.results;
}
```

### 8. Frontend Endpoint Fix
**File**: `frontend/src/views/student/ResultView.vue`
**Rationale**: URL mismatch /api/student/copies/ vs /api/students/copies/

### 9. Test ID Attributes
**File**: `frontend/src/views/CorrectorDashboard.vue`
**Rationale**: E2E tests need data-testid selectors

### 10. Rate Limiting Environment Toggle
**File**: `backend/core/settings.py`
**Rationale**: Allow E2E tests to bypass rate limiting without affecting production
```python
# Enable/disable django-ratelimit via env (default: enabled)
RATELIMIT_ENABLE = os.environ.get("RATELIMIT_ENABLE", "true").lower() == "true"

# Production guard: prevent accidental disable in production
DJANGO_ENV = os.environ.get("DJANGO_ENV", "development")
if DJANGO_ENV == "production" and not RATELIMIT_ENABLE:
    raise ValueError("RATELIMIT_ENABLE cannot be false in production environment")
```

### 11. E2E Docker Compose Override
**File**: `infra/docker/docker-compose.e2e.yml`
**Rationale**: Dedicated override for E2E testing environment
```yaml
services:
  backend:
    environment:
      DJANGO_ENV: "e2e"
      RATELIMIT_ENABLE: "false"
```

---

## Proof Logs

- `verification_proof_backend.txt` - Backend pytest output
- `verification_proof_e2e.txt` - E2E Playwright output

---

## Recommendations

1. ~~**Rate Limiting in E2E**~~: ✅ Fixed with `RATELIMIT_ENABLE` env var and `docker-compose.e2e.yml`
2. **Corrector E2E Fixtures**: Update `seed_e2e.py` to create copy with booklets/pages for annotation testing
3. **CI/CD Integration**: Add these verification steps to deploy.yml workflow
   ```bash
   docker compose -f docker-compose.local-prod.yml -f docker-compose.e2e.yml up -d --build
   npx playwright test
   ```

---

## Conclusion

The production-like stack is **operational** with:
- ✅ 100% backend tests passing (86/86 + 2 skipped)
- ✅ All services healthy
- ✅ Security headers properly configured
- ✅ E2E Student Flow: 3/3 tests passing
- ⚠️ E2E Corrector Flow: Requires booklet fixtures in seed script
