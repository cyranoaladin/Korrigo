# Smoke Test Execution Report
**Date**: 2026-01-27  
**Environment**: Local Production-Like (docker-compose.local-prod.yml)  
**Base URL**: http://localhost:8088  
**Tester**: Zenflow Audit System

---

## Executive Summary

⚠️ **OVERALL STATUS**: **FAILED** - Critical issues discovered

### Key Findings
- ✅ **Infrastructure**: Basic services can start (db, redis, nginx)
- ✅ **Security**: Authentication controls working correctly
- ⚠️ **Configuration Mismatch**: Container image outdated vs source code
- ❌ **P0 BLOCKER**: Logging configuration prevents container startup after rebuild
- ⚠️ **Missing App**: Identification app not loaded in production container

### Production Readiness Verdict
**🚫 NOT READY FOR PRODUCTION**

**Blocking Issues**:
1. **P0**: Container crashes on startup due to audit log file path issue
2. **P1**: Configuration drift between source code and built container
3. **P1**: Identification workflow unavailable (app not loaded)

---

## Test Execution Timeline

### Phase 1: Initial Service Startup (18:43 UTC)
✅ Successfully started services with existing container images:
- PostgreSQL 15 (alpine) - **healthy**
- Redis 7 (alpine) - **healthy**  
- Django Backend (Gunicorn, 3 workers) - **healthy**
- Celery Worker - **running**
- Nginx (port 8088) - **healthy**

**Result**: All services started successfully with **existing** (pre-built) container images.

---

### Phase 2: Basic Smoke Tests (18:44 UTC)

#### Test 2.1: Health Check Endpoint
```bash
$ curl -s http://localhost:8088/api/health/
{"status":"healthy","database":"connected"}
```
**HTTP Status**: 200 OK  
✅ **PASSED**

---

#### Test 2.2: Media Gate Security
```bash
$ curl -s -o /dev/null -w "%{http_code}" http://localhost:8088/media/marker.txt
```
**Result**: 404 (Not Found / Blocked)  
✅ **PASSED** - Media files correctly blocked from public access

---

#### Test 2.3: Authentication Endpoints

**Teacher/Admin Login**:
```bash
$ curl -s -o /dev/null -w "%{http_code}" http://localhost:8088/api/login/ -X POST
```
**Result**: 401 Unauthorized (expects credentials)  
✅ **PASSED** - Login endpoint available and protected

**User Detail (requires auth)**:
```bash
$ curl -s -o /dev/null -w "%{http_code}" http://localhost:8088/api/me/
```
**Result**: 403 Forbidden  
✅ **PASSED** - User detail endpoint correctly protected

---

#### Test 2.4: Student Portal Endpoints

**Student Login**:
```bash
$ curl -s -o /dev/null -w "%{http_code}" http://localhost:8088/api/students/login/ -X POST
```
**Result**: 400 Bad Request (expects credentials)  
✅ **PASSED** - Student login endpoint available

**Student Copies List**:
```bash
$ curl -s -o /dev/null -w "%{http_code}" http://localhost:8088/api/students/copies/
```
**Result**: 403 Forbidden  
✅ **PASSED** - Student copies endpoint correctly protected

---

#### Test 2.5: Exam Management Endpoints

**Exams List**:
```bash
$ curl -s -o /dev/null -w "%{http_code}" http://localhost:8088/api/exams/
```
**Result**: 403 Forbidden  
✅ **PASSED** - Exams endpoint correctly protected

**Copies List**:
```bash
$ curl -s -o /dev/null -w "%{http_code}" http://localhost:8088/api/copies/
```
**Result**: 403 Forbidden  
✅ **PASSED** - Copies endpoint correctly protected

---

#### Test 2.6: Frontend Serving

```bash
$ curl -s -o /dev/null -w "%{http_code}" http://localhost:8088/
```
**Result**: 200 OK  
✅ **PASSED** - Frontend correctly served by Nginx

---

### Phase 3: Configuration Audit (18:45 UTC)

#### Test 3.1: Identification Workflow
```bash
$ curl -s -o /dev/null -w "%{http_code}" http://localhost:8088/api/identification/desk/
```
**Result**: 404 Not Found  
❌ **FAILED**

**Investigation**: Checked INSTALLED_APPS in running container
```python
# Inside running container
docker exec backend python -c "from django.conf import settings; print(settings.INSTALLED_APPS)"
```

**Result**:
```python
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    # ... standard apps ...
    'core',
    'exams',
    'grading',
    'processing',
    'students',
    # 'identification' is MISSING!
]
```

**Cross-check with source code** (`backend/core/settings.py:110`):
```python
INSTALLED_APPS = [
    # ... standard apps ...
    'core',
    'exams',
    'grading',
    'processing',
    'students',
    'identification',  # <-- Present in source code
]
```

⚠️ **FINDING**: **Configuration Drift Detected**
- **Issue**: Container running with outdated `settings.py`
- **Severity**: P1 (High)
- **Impact**: Identification workflow completely unavailable
- **Root Cause**: Container image built before 'identification' app was added to settings

---

### Phase 4: Container Rebuild Test (18:46 UTC)

**Action**: Attempted to rebuild backend container with latest code
```bash
$ docker compose -f infra/docker/docker-compose.local-prod.yml up -d --build backend
```

**Result**: ❌ **CONTAINER CRASH LOOP**

**Error Logs**:
```python
ValueError: Unable to configure handler 'audit_file'
...
FileNotFoundError: [Errno 2] No such file or directory: '/var/log/korrigo/audit.log'
```

**Root Cause Analysis**:
- Logging configuration in `settings.py` references `/var/log/korrigo/audit.log`
- Directory `/var/log/korrigo/` does not exist in container
- Container fails to start during Django initialization

🚨 **CRITICAL P0 BLOCKER**
- **Severity**: P0 (Blocker)
- **Impact**: **Container cannot start with current source code**
- **Workflow Blocked**: ALL workflows (complete application failure)
- **Production Risk**: **CRITICAL** - Application will not start in production if deployed from current source

---

## Findings Summary

### ✅ Passed Tests (8/10) - Using Old Container
1. Health check endpoint working
2. Media gate blocking public access (security)
3. Teacher/Admin login endpoint available
4. User detail endpoint protected
5. Student login endpoint available
6. Student copies endpoint protected
7. Exams endpoint protected
8. Frontend serving correctly

### ❌ Failed Tests (2/10)
1. **Identification workflow unavailable** (P1)
   - Endpoint returns 404
   - App not loaded in container
   - Configuration drift: source code ≠ running container

2. **Container rebuild fails** (P0)
   - Logging directory missing
   - Container crashes on startup
   - Application completely non-functional after rebuild

---

## Critical Issues Discovered

### 🚨 Issue #1: Logging Configuration Crash (P0 - BLOCKER)

**File**: `backend/core/settings.py` (LOGGING configuration)

**Problem**:
```python
LOGGING = {
    'handlers': {
        'audit_file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': '/var/log/korrigo/audit.log',  # <-- Directory doesn't exist
            ...
        },
    },
}
```

**Error**:
```
FileNotFoundError: [Errno 2] No such file or directory: '/var/log/korrigo/audit.log'
ValueError: Unable to configure handler 'audit_file'
```

**Impact**:
- Container **cannot start**
- Complete application failure
- Blocks ALL workflows
- **Production deployment impossible**

**Recommended Fix** (choose one):
1. **Option A** (Quick fix): Create log directory in Dockerfile
   ```dockerfile
   RUN mkdir -p /var/log/korrigo && chown -R app:app /var/log/korrigo
   ```

2. **Option B** (Best practice): Use container-friendly logging
   ```python
   # Use stdout/stderr for containerized environments
   'audit_file': {
       'class': 'logging.StreamHandler',
       'stream': sys.stdout,
   }
   ```

3. **Option C** (Conditional): Make file logging optional
   ```python
   if os.path.exists('/var/log/korrigo'):
       handlers['audit_file'] = {...}
   else:
       handlers['audit_console'] = {'class': 'logging.StreamHandler'}
   ```

**Priority**: **IMMEDIATE** - Must be fixed before any deployment

---

### ⚠️ Issue #2: Configuration Drift (P1 - HIGH)

**Problem**: Container image built with outdated source code

**Evidence**:
- Source code (`settings.py:110`): `'identification'` present
- Running container: `'identification'` missing
- Container created: 43 hours ago (stale image)

**Impact**:
- Identification workflow unavailable
- Admin cannot identify copies
- OCR functionality inaccessible
- Gate 1-2 (identification) blocked

**Root Cause**:
- Container images not rebuilt regularly
- No CI/CD enforcement of image freshness
- Manual deployment process allows drift

**Recommended Fix**:
1. Rebuild container images before deployment
2. Add CI check: compare source code hash with container label
3. Tag images with git commit SHA for traceability
4. Document rebuild process in deployment guide

**Priority**: **HIGH** - Must be fixed before production deployment

---

## Production Readiness Assessment

### Infrastructure ✅ (with caveats)
- Docker Compose configuration valid
- Service orchestration working
- Health checks configured
- Volume mounts correct

**Caveats**:
- Only tested with OLD container images
- New container build FAILS

---

### Security ✅
- Authentication enforced on all protected endpoints
- Media files blocked from public access
- No authentication bypass detected
- Proper 403/401 responses

---

### Configuration ❌ FAILED
- **P0**: Logging directory missing (crash on startup)
- **P1**: Container configuration drift
- **P1**: Missing app in production build

---

### Critical Workflows

#### Teacher/Admin Workflows
- Login: ✅ Available
- Exam management: ✅ Protected
- Copy management: ✅ Protected
- Grading: ⚠️ Not fully tested (endpoints protected)
- **Identification: ❌ UNAVAILABLE**

#### Student Workflows
- Login: ✅ Available
- View copies: ✅ Protected
- Download PDF: ⚠️ Not tested (service unavailable after rebuild)

#### Admin Workflows
- User management: ⚠️ Not tested
- **Identification desk: ❌ UNAVAILABLE**
- OCR processing: ❌ UNAVAILABLE

---

## Smoke Test Verdict

### Overall Status: 🚫 **NOT READY FOR PRODUCTION**

### Blocking Issues (Must Fix Before Deploy)
1. ❌ **P0**: Fix logging directory issue (container won't start)
2. ❌ **P1**: Ensure 'identification' app is loaded
3. ❌ **P1**: Resolve configuration drift

### Conditional Pass (if using OLD container)
- ✅ Basic functionality works with existing (stale) container
- ✅ Security controls functioning
- ⚠️ Missing critical workflow (identification)

---

## Recommendations

### Immediate Actions (P0)
1. **Fix logging configuration**
   - Create `/var/log/korrigo/` directory in Dockerfile
   - OR switch to stdout/stderr logging for containers
   - Test container rebuild succeeds

2. **Verify container build**
   ```bash
   docker compose -f infra/docker/docker-compose.local-prod.yml build backend
   docker compose -f infra/docker/docker-compose.local-prod.yml up -d backend
   docker compose -f infra/docker/docker-compose.local-prod.yml exec backend python manage.py check
   ```

3. **Rerun smoke tests**
   - Verify all endpoints work with NEW container
   - Verify identification endpoints are accessible
   - Document any new issues

---

### Short-Term Actions (P1)
1. **Document container rebuild process**
   - When to rebuild
   - How to verify build success
   - How to detect configuration drift

2. **Add health check for critical apps**
   ```python
   # In health check endpoint
   from django.conf import settings
   assert 'identification' in settings.INSTALLED_APPS
   ```

3. **Implement CI checks**
   - Fail CI if container build fails
   - Fail CI if smoke tests fail
   - Tag containers with git commit SHA

---

### Long-Term Actions (P2)
1. Implement automated smoke tests in CI/CD
2. Add monitoring for configuration drift
3. Implement blue-green deployment for safer rollouts
4. Add integration tests for critical workflows
5. Document all critical paths and their dependencies

---

## Test Commands to Reproduce

### Start Services (Old Container - Works)
```bash
cd /home/alaeddine/.zenflow/worktrees/audit-993a
docker compose -f infra/docker/docker-compose.local-prod.yml up -d
sleep 15  # Wait for health checks

# Run basic smoke tests
BASE_URL="http://localhost:8088"
curl -s $BASE_URL/api/health/ | jq .
curl -s -o /dev/null -w "Login: %{http_code}\n" $BASE_URL/api/login/ -X POST
curl -s -o /dev/null -w "Student copies: %{http_code}\n" $BASE_URL/api/students/copies/
curl -s -o /dev/null -w "Identification: %{http_code}\n" $BASE_URL/api/identification/desk/
```

### Rebuild Container (Fails - P0 Issue)
```bash
cd /home/alaeddine/.zenflow/worktrees/audit-993a
docker compose -f infra/docker/docker-compose.local-prod.yml up -d --build backend

# Check logs (will show FileNotFoundError)
docker logs docker-backend-1
```

---

## Files Referenced

### Configuration Files
- `infra/docker/docker-compose.local-prod.yml` - Service orchestration
- `backend/core/settings.py` - Django settings (INSTALLED_APPS, LOGGING)
- `backend/core/urls.py` - URL routing
- `.env` - Environment variables

### Application Code
- `backend/identification/` - Identification app (not loaded in container)
- `backend/grading/` - Grading app
- `backend/students/` - Student portal app
- `backend/exams/` - Exam management app

---

## Appendix: Detailed Test Logs

### Container Status Before Rebuild
```
NAME               IMAGE                STATUS
docker-backend-1   docker-backend       Up (healthy)
docker-celery-1    docker-celery        Up
docker-db-1        postgres:15-alpine   Up (healthy)
docker-nginx-1     docker-nginx         Up (healthy)
docker-redis-1     redis:7-alpine       Up (healthy)
```

### Container Status After Rebuild Attempt
```
NAME               IMAGE                STATUS
docker-backend-1   docker-backend       Restarting (1)
# Container crashes and restarts continuously
```

### Error Log Excerpt
```
ValueError: Unable to configure handler 'audit_file'
FileNotFoundError: [Errno 2] No such file or directory: '/var/log/korrigo/audit.log'
```

---

**Report Generated**: 2026-01-27 18:47 UTC  
**Tester**: Zenflow Audit System  
**Next Step**: Fix P0 blocking issue (logging configuration)
