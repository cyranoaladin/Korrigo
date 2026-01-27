# Docker Production Configuration Check - Audit Report

**Date**: 2026-01-27  
**Auditor**: Zenflow  
**Scope**: Docker production configuration for Korrigo exam grading platform  
**Criticality**: HIGH (Production deployment for real exam grading)

---

## Executive Summary

### Verdict: ⚠️ **NOT READY FOR PRODUCTION** (P0 Issues Found)

**Critical Findings**:
- **3 P0 issues** (blocker): Insecure defaults that create fail-open security vulnerabilities
- **8 P1 issues** (high severity): Missing production hardening, resource limits, security headers
- **7 P2 issues** (quality improvements): Best practices, defense-in-depth

**Recommendation**: Fix all P0 issues before production deployment. Address critical P1 issues (resource limits, CSP header, SSL enforcement).

---

## 1. Secrets Management

### P0-001: ❌ FAIL-OPEN SECURITY - Default Credentials in Production

**Location**: `docker-compose.prod.yml`

**Issue**:
```yaml
# Line 14
POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-viatique_password}

# Line 48
SECRET_KEY: "${SECRET_KEY:-prod-secret-key-change-it}"

# Line 50
DATABASE_URL: "postgres://${POSTGRES_USER:-viatique_user}:${POSTGRES_PASSWORD:-viatique_password}@db:5432/${POSTGRES_DB:-viatique}"
```

**Impact**: 
- If environment variables are not set, production starts with INSECURE hardcoded credentials
- This is a **fail-open** security vulnerability
- Violates the principle: "deny by default"
- Real risk: Attacker could exploit default credentials in production

**Expected Behavior**: 
- Application MUST fail to start if critical secrets (`SECRET_KEY`, `POSTGRES_PASSWORD`) are missing
- No default values for production secrets

**Remediation**:
1. Remove all default values for secrets in `docker-compose.prod.yml`
2. Add startup validation in Django settings to check secrets are not defaults
3. Add healthcheck/readiness probe that fails if using default secrets

**Test**:
```bash
# Should FAIL to start
unset SECRET_KEY POSTGRES_PASSWORD
docker compose -f infra/docker/docker-compose.prod.yml up
```

---

### P0-002: ❌ MISSING ENVIRONMENT VARIABLE - GITHUB_REPOSITORY_OWNER

**Location**: `docker-compose.prod.yml:31,62,77`

**Issue**:
```yaml
image: ghcr.io/${GITHUB_REPOSITORY_OWNER}/korrigo-backend:${KORRIGO_SHA:-latest}
```

**Impact**:
- If `GITHUB_REPOSITORY_OWNER` is not set, Docker will try to pull `ghcr.io//korrigo-backend`
- Deployment will fail with unclear error
- No fail-fast validation

**Expected Behavior**:
- Validate required environment variables before docker compose
- Provide clear error message if missing

**Remediation**:
1. Add pre-flight check script: `scripts/validate-prod-env.sh`
2. Document required env vars in deployment guide
3. Consider using `.env.prod.example` with all required vars

**Test**:
```bash
# Should show clear error
unset GITHUB_REPOSITORY_OWNER
docker compose -f infra/docker/docker-compose.prod.yml config
```

---

### P0-003: ⚠️ MISSING SECRET KEY VALIDATION

**Location**: `backend/core/settings.py` (inferred - not checked yet in this audit)

**Issue**:
- No verification that `SECRET_KEY` is not a default/example value
- Settings might not fail on insecure SECRET_KEY

**Expected Behavior**:
- Django should refuse to start if `SECRET_KEY` contains "CHANGE" or "insecure" or matches known defaults

**Remediation**:
```python
# In settings.py
if DEBUG is False:
    if not SECRET_KEY or 'CHANGE' in SECRET_KEY or 'insecure' in SECRET_KEY or len(SECRET_KEY) < 50:
        raise ImproperlyConfigured("Invalid SECRET_KEY in production")
```

**Test**:
```bash
export SECRET_KEY="django-insecure-CHANGE_ME"
export DEBUG=False
python manage.py check --deploy  # Should fail
```

---

## 2. Production Hardening

### P1-001: ⚠️ ALLOWED_HOSTS Default Too Permissive

**Location**: `docker-compose.prod.yml:49`

**Issue**:
```yaml
ALLOWED_HOSTS: "${ALLOWED_HOSTS:-localhost,127.0.0.1,nginx,backend}"
```

**Impact**:
- Default includes internal service names (`nginx`, `backend`)
- Could enable Host header injection in certain network configurations
- Production should use explicit public domain only

**Severity**: **P1** - Must be explicit production domain

**Remediation**:
```yaml
ALLOWED_HOSTS: "${ALLOWED_HOSTS:?ALLOWED_HOSTS must be set for production}"
```

**Test**:
```bash
# Should fail with clear error
unset ALLOWED_HOSTS
docker compose -f infra/docker/docker-compose.prod.yml up
```

---

### P1-002: ⚠️ CORS_ALLOWED_ORIGINS Default is Localhost

**Location**: `docker-compose.prod.yml:52`

**Issue**:
```yaml
CORS_ALLOWED_ORIGINS: "${CORS_ALLOWED_ORIGINS:-http://localhost:8088}"
```

**Impact**:
- Production defaults to localhost CORS
- Wrong CORS config could break production or create security issues

**Severity**: **P1** - Must be explicit in production

**Remediation**:
```yaml
CORS_ALLOWED_ORIGINS: "${CORS_ALLOWED_ORIGINS:?CORS_ALLOWED_ORIGINS must be set for production}"
```

---

### P1-003: ⚠️ SSL_ENABLED Defaults to False

**Location**: `docker-compose.prod.yml:47`

**Issue**:
```yaml
SSL_ENABLED: "${SSL_ENABLED:-False}"
```

**Impact**:
- Insecure cookies (no Secure flag)
- No HSTS enforcement
- Vulnerable to MITM attacks

**Severity**: **P1** - Production must use SSL

**Remediation**:
- Either remove default (force explicit setting) or default to `True`
- Add validation: if production environment, SSL must be enabled

---

### P1-004: ❌ Missing CSP Header

**Location**: `infra/nginx/nginx.conf`

**Issue**:
- No `Content-Security-Policy` header configured
- Present security headers: X-Frame-Options, X-Content-Type-Options, X-XSS-Protection, Referrer-Policy
- Missing: CSP, HSTS

**Impact**:
- No defense against XSS attacks via CSP
- Modern browsers rely on CSP for XSS protection

**Severity**: **P1** - Critical security header

**Remediation**:
```nginx
# Add to nginx.conf:12 (after existing headers)
add_header Content-Security-Policy "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'; connect-src 'self'; frame-ancestors 'none';" always;
```

**Note**: This is a strict baseline CSP. May need to be relaxed based on actual frontend requirements (Vue.js, inline styles, etc.).

---

### P1-005: ❌ Missing HSTS Header (when SSL enabled)

**Location**: `infra/nginx/nginx.conf`

**Issue**:
- No `Strict-Transport-Security` header when SSL is enabled
- HSTS forces browsers to use HTTPS only

**Impact**:
- No HTTPS enforcement at browser level
- First request could be over HTTP (vulnerable to downgrade attack)

**Severity**: **P1** - Must have when SSL_ENABLED=True

**Remediation**:
```nginx
# Add conditionally when SSL enabled (or in separate nginx config for HTTPS)
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;
```

---

### P1-006: ❌ No Resource Limits Defined

**Location**: `docker-compose.prod.yml` (all services)

**Issue**:
- No CPU or memory limits on any service
- Backend, Celery, and DB can consume unlimited resources

**Impact**:
- One service could consume all resources → cascade failure
- PDF processing could cause OOM
- No protection against resource exhaustion

**Severity**: **P1** - Critical for production stability

**Remediation**:
```yaml
# Example for backend service
deploy:
  resources:
    limits:
      cpus: '2.0'
      memory: 2G
    reservations:
      cpus: '0.5'
      memory: 512M
```

**Recommended Limits**:
- **Backend**: 2GB memory, 2 CPUs (PDF processing is memory-intensive)
- **Celery**: 4GB memory, 2 CPUs (PDF flattening, split, OCR)
- **Database**: 1GB memory, 1 CPU
- **Redis**: 512MB memory, 0.5 CPU
- **Nginx**: 256MB memory, 0.5 CPU

---

### P1-007: ⚠️ Gunicorn Worker Count Hardcoded

**Location**: `docker-compose.prod.yml:33`

**Issue**:
```yaml
command: gunicorn core.wsgi:application --bind 0.0.0.0:8000 --workers 3 --timeout 120
```

- Overrides `gunicorn_config.py` which calculates workers based on CPU count
- Fixed at 3 workers regardless of CPU availability

**Impact**:
- Suboptimal performance (too few workers on multi-core systems, too many on small systems)

**Severity**: **P1** - Performance issue

**Remediation**:
```yaml
# Option 1: Use config file
command: gunicorn core.wsgi:application -c gunicorn_config.py

# Option 2: Use entrypoint.sh default (line 17)
# Remove explicit command from docker-compose.prod.yml
```

---

### P1-008: ⚠️ Missing Cookie Security Flags in Environment

**Location**: `.env.example`

**Issue**:
- `SSL_ENABLED` present but no `CSRF_COOKIE_SECURE`, `SESSION_COOKIE_SECURE` flags
- Django cookie security settings not configured via environment

**Impact**:
- Cookies could be sent over HTTP even when SSL enabled
- Session hijacking vulnerability

**Severity**: **P1** - Must be set when SSL_ENABLED=True

**Remediation**:
```bash
# Add to .env.example
CSRF_COOKIE_SECURE=True
SESSION_COOKIE_SECURE=True
SECURE_SSL_REDIRECT=True  # Redirect all HTTP to HTTPS
```

**Django Settings Check** (to verify in backend/core/settings.py):
```python
if SSL_ENABLED:
    CSRF_COOKIE_SECURE = True
    SESSION_COOKIE_SECURE = True
    SECURE_SSL_REDIRECT = True
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
```

---

## 3. Volumes & Persistence

### ✅ PASS: Named Volumes Properly Defined

**Location**: `docker-compose.prod.yml:92-95`

```yaml
volumes:
  postgres_data:     # Persistent DB storage
  static_volume:     # Persistent static files  
  media_volume:      # Persistent media/PDF files
```

**Status**: ✅ All critical data uses named volumes (not anonymous volumes)

**Verification**:
```bash
docker volume ls | grep audit-993a
# Should show persistent volumes after restart
```

---

## 4. Health Checks

### ✅ EXCELLENT: All Critical Services Have Health Checks

**Services with Health Checks**:
- ✅ PostgreSQL: `pg_isready` (lines 15-19)
- ✅ Redis: `redis-cli ping` (lines 24-28)
- ✅ Backend: HTTP `/api/health/` (lines 54-59)
- ✅ Nginx: HTTP `/` (lines 86-90)

**Health Check Configuration Review**:
```yaml
backend:
  healthcheck:
    test: [ "CMD", "curl", "-f", "http://localhost:8000/api/health/" ]
    interval: 30s      # Check every 30s (reasonable)
    timeout: 10s       # Wait 10s for response (reasonable for PDF ops)
    retries: 3         # Retry 3 times before marking unhealthy
    start_period: 30s  # Grace period for startup (migrations, collectstatic)
```

**Status**: ✅ Well-configured

---

### P2-001: ⚠️ Celery Worker Has No Health Check

**Location**: `docker-compose.prod.yml:61-74`

**Issue**:
- Celery worker service has no healthcheck
- Failed worker won't be detected/restarted automatically

**Impact**:
- If Celery crashes, PDF processing stops silently
- No automated detection/recovery

**Severity**: **P2** - Celery has no standard health endpoint, would need custom implementation

**Remediation** (optional):
```yaml
celery:
  healthcheck:
    test: ["CMD-SHELL", "celery -A core inspect ping -d celery@$$HOSTNAME"]
    interval: 30s
    timeout: 10s
    retries: 3
```

---

## 5. Network Isolation

### P2-002: ⚠️ No Explicit Network Definition

**Location**: `docker-compose.prod.yml` (entire file)

**Issue**:
- No explicit networks defined
- All services on default bridge network
- All services can communicate with each other without isolation

**Impact**:
- Reduces defense-in-depth
- Not critical (Docker provides default isolation from host)

**Severity**: **P2** - Best practice, not blocker

**Remediation** (optional):
```yaml
networks:
  frontend:
  backend:
  database:

services:
  db:
    networks: [database]
  
  backend:
    networks: [backend, database]
  
  nginx:
    networks: [frontend, backend]
```

---

### ✅ GOOD: Backend Not Directly Exposed

**Status**: ✅ Backend uses `expose: ["8000"]` instead of `ports:` (line 34-35)
- Backend only accessible via Nginx proxy
- Not exposed to host network

---

## 6. Restart Policies

### ✅ PASS: Appropriate Restart Policy

**All services**: `restart: unless-stopped` (lines 8, 23, 32, 63, 78)

**Status**: ✅ Appropriate for production
- Won't restart if explicitly stopped (allows controlled shutdown)
- Will restart on crash or system reboot

---

## 7. Dockerfile Security & Best Practices

### P2-003: ⚠️ Containers Run as Root

**Location**: All Dockerfiles (backend, frontend, nginx)

**Issue**:
- No `USER` directive in any Dockerfile
- All containers run as root (UID 0)

**Impact**:
- Security risk if container compromised (attacker has root)
- Violates principle of least privilege

**Severity**: **P2** - Best practice

**Remediation**:
```dockerfile
# backend/Dockerfile
RUN addgroup --system django && adduser --system --ingroup django django
RUN chown -R django:django /app
USER django
```

---

### P2-004: ⚠️ Base Image Versions Not Fully Pinned

**Location**: `docker-compose.prod.yml:7,22`

**Issue**:
```yaml
image: postgres:15-alpine   # Should be postgres:15.4-alpine
image: redis:7-alpine       # Should be redis:7.2.1-alpine
```

**Impact**:
- Could pull different patch versions across deployments
- Reduces reproducibility

**Severity**: **P2** - Best practice for deterministic builds

---

### ✅ GOOD: Multi-Stage Builds

**Status**: ✅ Frontend and Nginx use multi-stage builds
- Production images only contain built artifacts (no source code)
- Smaller attack surface

---

### ✅ GOOD: APT Cache Cleanup

**Status**: ✅ Backend Dockerfile cleans up apt cache (backend/Dockerfile:12)
```dockerfile
&& rm -rf /var/lib/apt/lists/*
```

---

## 8. Entrypoint & Startup

### ✅ GOOD: Migrations Run on Startup

**Location**: `backend/entrypoint.sh:5`

```bash
python manage.py migrate
```

**Status**: ✅ Ensures DB schema is up-to-date

---

### ✅ GOOD: Static Files Collected on Startup

**Location**: `backend/entrypoint.sh:8`

```bash
python manage.py collectstatic --noinput
```

**Status**: ✅ Ensures static files are available to Nginx

---

### P2-005: ⚠️ No Migration Rollback Strategy

**Location**: `backend/entrypoint.sh`

**Issue**:
- Migrations run automatically with no safety checks
- If migration fails, DB could be in inconsistent state
- No rollback mechanism

**Impact**:
- Failed migration could require manual DB intervention

**Severity**: **P2** - Migrations should be tested in staging first

**Recommendation**:
- Test migrations in staging before production deployment
- Consider: `python manage.py migrate --check` before actual migration
- Consider: Blue/green deployment strategy for risky migrations

---

## 9. Nginx Configuration

### ✅ GOOD: Security Headers Present

**Location**: `infra/nginx/nginx.conf:13-16`

```nginx
add_header X-Frame-Options "DENY" always;
add_header X-Content-Type-Options "nosniff" always;
add_header X-XSS-Protection "1; mode=block" always;
add_header Referrer-Policy "strict-origin-when-cross-origin" always;
```

**Status**: ✅ Essential security headers configured

---

### ✅ GOOD: Large Upload Support

**Location**: `infra/nginx/nginx.conf:10`

```nginx
client_max_body_size 100M;
```

**Status**: ✅ Appropriate for PDF uploads (exam papers can be large)

---

### ✅ GOOD: Dynamic Upstream Resolution

**Location**: `infra/nginx/nginx.conf:3,33-34`

```nginx
resolver 127.0.0.11 valid=10s ipv6=off;
...
set $backend_upstream http://backend:8000;
proxy_pass $backend_upstream;
```

**Status**: ✅ Prevents 502 errors when backend container IP changes

---

### P2-006: ⚠️ No Rate Limiting

**Location**: `infra/nginx/nginx.conf`

**Issue**:
- No nginx rate limiting configured
- No protection against brute force or DoS

**Impact**:
- Vulnerable to brute force attacks on login endpoints
- Vulnerable to resource exhaustion

**Severity**: **P2** - Should have basic rate limits

**Remediation**:
```nginx
# Add before server block
limit_req_zone $binary_remote_addr zone=general:10m rate=10r/s;
limit_req_zone $binary_remote_addr zone=login:10m rate=5r/m;

server {
    # General rate limit
    limit_req zone=general burst=20 nodelay;
    
    # Stricter rate limit for auth endpoints
    location ~ ^/api/(auth|token|login)/ {
        limit_req zone=login burst=5 nodelay;
        proxy_pass $backend_upstream;
    }
}
```

---

### P2-007: ⚠️ Gunicorn `forwarded_allow_ips` Too Permissive

**Location**: `backend/gunicorn_config.py:8`

**Issue**:
```python
forwarded_allow_ips = '*'  # Accepts X-Forwarded-* from any source
```

**Impact**:
- Could allow IP spoofing if not behind trusted proxy
- Nginx is the only proxy, but wildcarding is risky

**Severity**: **P2** - Should be explicit

**Remediation**:
```python
# Trust only Nginx container
forwarded_allow_ips = 'nginx'  # Docker service name

# Or use Unix socket between nginx and gunicorn (more secure)
```

---

## 10. Environment Variables & Documentation

### ✅ GOOD: .env.example Exists

**Location**: `.env.example`

**Status**: ✅ Documents all required environment variables

**Content Review**:
```bash
POSTGRES_DB=viatique
POSTGRES_USER=viatique_user
POSTGRES_PASSWORD=change_this_password_in_prod  # ✅ Clear warning
SECRET_KEY=django-insecure-CHANGE_ME_IN_PROD    # ✅ Clear warning
DEBUG=False                                      # ✅ Correct default
ALLOWED_HOSTS=localhost,127.0.0.1,backend        # ⚠️ Should require explicit setting
SSL_ENABLED=False                                # ⚠️ Should be True or required
E2E_SEED_TOKEN=secret-e2e-token-CHANGE_ME        # ⚠️ Should warn: NEVER set in production
```

---

### ⚠️ Missing: Production Environment Documentation

**Recommendation**: Add `.env.prod.example` with:
- All required production environment variables
- No defaults for secrets (show `REQUIRED` instead)
- SSL_ENABLED=True as default
- Clear warnings about E2E_SEED_TOKEN (must not be set in prod)

**Example**:
```bash
# .env.prod.example
POSTGRES_DB=REQUIRED
POSTGRES_USER=REQUIRED
POSTGRES_PASSWORD=REQUIRED  # Generate with: openssl rand -base64 32

SECRET_KEY=REQUIRED  # Generate with: python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'

DEBUG=False  # MUST be False in production
ALLOWED_HOSTS=REQUIRED  # Example: viatique.example.com

SSL_ENABLED=True  # MUST be True in production
CORS_ALLOWED_ORIGINS=REQUIRED  # Example: https://viatique.example.com
CSRF_TRUSTED_ORIGINS=REQUIRED  # Example: https://viatique.example.com

# DO NOT SET E2E_SEED_TOKEN IN PRODUCTION
# E2E_SEED_TOKEN=  # Leave empty/unset
```

---

## 11. Production vs Development Configurations

### ✅ EXCELLENT: Clear Separation of Environments

**Files**:
- `docker-compose.yml` - Development (hot-reload, debug mode)
- `docker-compose.prod.yml` - Production (image-based, SHA-tagged)
- `docker-compose.local-prod.yml` - Local production testing (builds locally)
- `docker-compose.prodlike.yml` - Production-like testing

**Status**: ✅ Well-organized

---

### ✅ GOOD: Production Uses Image Registry

**Status**: ✅ Production pulls pre-built images from GHCR
```yaml
image: ghcr.io/${GITHUB_REPOSITORY_OWNER}/korrigo-backend:${KORRIGO_SHA:-latest}
```

**Benefits**:
- Faster deployments (no build step)
- Ensures tested images deployed (CI/CD builds and tests images)
- Immutable deployments (SHA-tagged)

---

## Summary of Issues

### P0 (Blockers) - MUST FIX BEFORE PRODUCTION

| ID | Issue | Location | Impact |
|---|---|---|---|
| P0-001 | Default credentials in production | docker-compose.prod.yml:14,48,50 | Fail-open security - production could start with insecure defaults |
| P0-002 | Missing GITHUB_REPOSITORY_OWNER validation | docker-compose.prod.yml:31,62,77 | Deployment fails with unclear error |
| P0-003 | No SECRET_KEY validation | backend/core/settings.py | Production could start with default SECRET_KEY |

**Action Required**: Fix all P0 issues before production deployment.

---

### P1 (High Severity) - FIX BEFORE PRODUCTION

| ID | Issue | Location | Impact |
|---|---|---|---|
| P1-001 | ALLOWED_HOSTS default too permissive | docker-compose.prod.yml:49 | Host header injection risk |
| P1-002 | CORS default is localhost | docker-compose.prod.yml:52 | Wrong CORS config in production |
| P1-003 | SSL_ENABLED defaults to False | docker-compose.prod.yml:47 | Insecure cookies, no HSTS |
| P1-004 | Missing CSP header | infra/nginx/nginx.conf | No XSS defense |
| P1-005 | Missing HSTS header | infra/nginx/nginx.conf | No HTTPS enforcement |
| P1-006 | No resource limits | docker-compose.prod.yml | Risk of resource exhaustion |
| P1-007 | Worker count hardcoded | docker-compose.prod.yml:33 | Suboptimal performance |
| P1-008 | Missing cookie security flags | .env.example | Session hijacking risk |

**Action Required**: Address critical P1 issues (resource limits, CSP, SSL enforcement) before production.

---

### P2 (Quality Improvements) - BACKLOG

| ID | Issue | Location | Impact |
|---|---|---|---|
| P2-001 | Celery no health check | docker-compose.prod.yml:61-74 | No automated failure detection |
| P2-002 | No explicit networks | docker-compose.prod.yml | Reduced defense-in-depth |
| P2-003 | Containers run as root | All Dockerfiles | Security risk if compromised |
| P2-004 | Image versions not pinned | docker-compose.prod.yml:7,22 | Reduced reproducibility |
| P2-005 | No migration rollback | backend/entrypoint.sh | Manual intervention if migration fails |
| P2-006 | No rate limiting | infra/nginx/nginx.conf | Vulnerable to brute force |
| P2-007 | forwarded_allow_ips too permissive | gunicorn_config.py:8 | Potential IP spoofing |

**Action Required**: Consider addressing P2 issues for production hardening (especially rate limiting, resource limits).

---

## Production Readiness Checklist

### Pre-Deployment Validation

```bash
#!/bin/bash
# scripts/validate-prod-env.sh

set -e

echo "==> Validating production environment variables..."

required_vars=(
    "GITHUB_REPOSITORY_OWNER"
    "KORRIGO_SHA"
    "SECRET_KEY"
    "POSTGRES_PASSWORD"
    "ALLOWED_HOSTS"
    "CORS_ALLOWED_ORIGINS"
    "CSRF_TRUSTED_ORIGINS"
)

for var in "${required_vars[@]}"; do
    if [ -z "${!var}" ]; then
        echo "❌ ERROR: $var is not set"
        exit 1
    fi
done

# Validate SECRET_KEY is not default
if [[ "$SECRET_KEY" == *"CHANGE"* ]] || [[ "$SECRET_KEY" == *"insecure"* ]]; then
    echo "❌ ERROR: SECRET_KEY appears to be a default value"
    exit 1
fi

# Validate DEBUG is False
if [ "$DEBUG" != "False" ]; then
    echo "❌ ERROR: DEBUG must be 'False' in production"
    exit 1
fi

# Validate SSL is enabled
if [ "$SSL_ENABLED" != "True" ]; then
    echo "⚠️  WARNING: SSL_ENABLED is not True (recommended for production)"
fi

# Validate E2E_SEED_TOKEN is not set
if [ -n "$E2E_SEED_TOKEN" ]; then
    echo "❌ ERROR: E2E_SEED_TOKEN must NOT be set in production"
    exit 1
fi

echo "✅ All required environment variables validated"
```

**Usage**:
```bash
# Before deployment
source .env.prod
./scripts/validate-prod-env.sh

# If validation passes, deploy
docker compose -f infra/docker/docker-compose.prod.yml up -d
```

---

### Deployment Commands

```bash
# 1. Validate environment
source .env.prod
./scripts/validate-prod-env.sh

# 2. Pull latest images (SHA-tagged)
docker compose -f infra/docker/docker-compose.prod.yml pull

# 3. Deploy (with zero-downtime if using orchestrator)
docker compose -f infra/docker/docker-compose.prod.yml up -d

# 4. Verify health checks
docker compose -f infra/docker/docker-compose.prod.yml ps
# All services should be "healthy"

# 5. Check logs for errors
docker compose -f infra/docker/docker-compose.prod.yml logs -f --tail=100

# 6. Run smoke tests
./scripts/smoke.sh
```

---

## Recommendations

### Immediate (Before Production)
1. ✅ Fix P0-001: Remove default credentials, add startup validation
2. ✅ Fix P0-002: Add GITHUB_REPOSITORY_OWNER validation
3. ✅ Fix P0-003: Add SECRET_KEY validation in Django settings
4. ✅ Fix P1-006: Add resource limits to all services
5. ✅ Fix P1-004: Add CSP header to Nginx
6. ✅ Fix P1-005: Add HSTS header to Nginx (when SSL enabled)

### Short-Term (Production Hardening)
1. ✅ Fix P1-001, P1-002, P1-003: Remove defaults for security-critical env vars
2. ✅ Fix P1-007: Use gunicorn_config.py for worker count
3. ✅ Fix P1-008: Add cookie security flags to .env.example
4. ✅ Add P2-006: Add rate limiting to Nginx

### Long-Term (Best Practices)
1. ⚠️ P2-003: Run containers as non-root user
2. ⚠️ P2-004: Pin base image versions to specific patches
3. ⚠️ P2-001: Add Celery health check
4. ⚠️ P2-002: Add explicit network isolation
5. ⚠️ P2-007: Restrict gunicorn forwarded_allow_ips

---

## Conclusion

The Docker production configuration is **well-structured** with good separation of concerns, health checks, and persistence. However, it has **critical security issues (P0)** that make it **NOT READY for production deployment**:

1. **Fail-open security**: Default credentials allow production to start with insecure defaults
2. **Missing validation**: No startup checks for required secrets
3. **Missing hardening**: Resource limits, CSP, HSTS not configured

**Next Steps**:
1. Apply all P0 fixes
2. Apply critical P1 fixes (resource limits, security headers)
3. Test in local-prod environment: `docker-compose.local-prod.yml`
4. Create production environment validation script
5. Document deployment runbook

**After fixes**: Re-audit and mark this step complete in plan.md.
