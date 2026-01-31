# Technical Specification: Production Hardening

**Task ID**: ZF-AUD-12  
**Created**: 2026-01-31  
**Status**: Draft  
**Version**: 1.0

---

## 1. Technical Context

### 1.1 Technology Stack

**Backend**:
- Django 4.2 with Django REST Framework
- Python 3.9
- WSGI Server: Gunicorn (3 workers, 120s timeout)
- Database: PostgreSQL 15
- Cache/Message Broker: Redis 7
- Task Queue: Celery + Celery Beat

**Frontend**:
- Vue.js 3 with Vite
- Served as SPA from nginx

**Infrastructure**:
- Reverse Proxy: Nginx (Alpine-based Docker image)
- Orchestration: Docker Compose (production mode: image-based with SHA tags)
- Health Checks: Built-in Docker healthcheck directives

**Existing Security Stack**:
- `django-csp`: Content Security Policy middleware
- `django-cors-headers`: CORS configuration
- Django Security Middleware: XSS, clickjacking, MIME sniffing protection
- Custom middleware: Request ID correlation, metrics collection

### 1.2 Current Architecture Patterns

**Settings Configuration Pattern**:
- Base settings: `backend/core/settings.py` (512 lines)
  - Conditional logic based on `DJANGO_ENV` and `DEBUG`
  - Helper function `csv_env()` for parsing comma-separated env vars
  - SSL-aware configuration via `SSL_ENABLED` flag
- Production overrides: `backend/core/settings_prod.py` (69 lines)
  - Imports from base settings
  - Required env var validation via `_get_required_env()`
  - Forces `DJANGO_ENV=production` and `DEBUG=False`

**Security Configuration Pattern** (settings.py:98-130):
- Three-tier security model:
  1. **Development** (`DEBUG=True`): No HTTPS enforcement, insecure cookies
  2. **Prod-like** (`DEBUG=False`, `SSL_ENABLED=False`): Enforced security headers but HTTP-only
  3. **Production** (`DEBUG=False`, `SSL_ENABLED=True`): Full HTTPS enforcement

**Nginx Configuration Pattern** (infra/nginx/nginx.conf:1-58):
- Dynamic upstream resolution for backend (prevents 502 on container restart)
- Security headers at server level
- Static/media file serving with Docker volume mounts
- SPA fallback routing
- Client max body size: 100MB (for PDF uploads)

**Backup Pattern**:
- Shell script: `scripts/backup_db.sh` (PostgreSQL pg_dump + gzip, 30-day retention)
- Django management command: `backend/core/management/commands/backup.py` (JSON serialization + media zip)
- Restore command: `backend/core/management/commands/restore.py`

**Testing Pattern**:
- Smoke tests: `scripts/smoke.sh` (health check + media access validation)
- Staging smoke: `scripts/smoke_staging.sh`
- E2E smoke: `frontend/tests/e2e/smoke-check.sh`

### 1.3 Dependencies Already in Use

**Python Packages**:
- `django==4.2.*`
- `djangorestframework`
- `django-csp` (CSP middleware)
- `django-cors-headers` (CORS configuration)
- `dj-database-url` (database URL parsing)
- `gunicorn` (WSGI server)
- `celery` (task queue)
- `python-dotenv` (environment variable loading)
- `psycopg2-binary` (PostgreSQL adapter)

**Docker Images**:
- `postgres:15-alpine`
- `redis:7-alpine`
- `ghcr.io/${GITHUB_REPOSITORY_OWNER}/korrigo-backend:${KORRIGO_SHA}`
- `ghcr.io/${GITHUB_REPOSITORY_OWNER}/korrigo-nginx:${KORRIGO_SHA}`

### 1.4 Existing Security Measures

**Already Implemented** ✅:
- DEBUG forced to False in production (settings.py:28-33)
- SECRET_KEY validation (settings.py:15-19)
- ALLOWED_HOSTS wildcard prevention (settings.py:42-44)
- Session/CSRF cookie security conditional on SSL (settings.py:107-108)
- HSTS headers in Django when SSL_ENABLED=true (settings.py:109-111)
- Basic security headers in nginx (X-Frame-Options, X-Content-Type-Options, X-XSS-Protection)
- CORS explicit origins (no wildcard)
- CSP middleware installed (settings.py:150, middleware:178)

**Missing** ❌:
- HSTS header in nginx
- CSP header in nginx
- Permissions-Policy header
- Django deployment check (`--deploy`) results analysis
- Consolidated backup/restore runbook
- Production smoke tests for static/media availability

---

## 2. Implementation Approach

### 2.1 Design Principles

1. **Zero Breaking Changes**: All modifications must be backward compatible with dev/staging/prod-like environments
2. **Documentation First**: Deliver audit and runbook before any code changes
3. **Conditional Security**: Respect existing SSL_ENABLED flag for HTTPS-specific settings
4. **Validation Over Enforcement**: Provide scripts and procedures; let operators decide when to apply
5. **French Documentation**: Match existing documentation language (MANUEL_SECURITE.md, RUNBOOK_PRODUCTION.md)

### 2.2 Three-Phase Approach

#### Phase 1: Audit & Analysis (Documentation Only)
**Objective**: Understand current state and identify all hardening gaps

**Actions**:
1. Execute `python manage.py check --deploy` with production settings
2. Analyze all warnings and classify by priority (P0-P3)
3. Document findings in `audit.md`
4. Document security headers current vs. recommended state
5. Document cookie security configuration validation

**Deliverable**: `audit.md` - Comprehensive audit report

**No code changes**: Pure documentation phase

#### Phase 2: Backup/Restore Consolidation (Documentation Only)
**Objective**: Create unified operational runbook for backup/restore procedures

**Actions**:
1. Document database backup procedures (shell script method)
2. Document database backup procedures (Django command method)
3. Document media backup procedures
4. Document restore procedures with pre-restore validation
5. Document critical Docker volumes (postgres_data, media_volume, static_volume)
6. Add volume destruction warnings
7. Reference existing test: `test_backup_restore_real_fixed.py`

**Deliverable**: `runbook_backup_restore.md` - Operational runbook

**No code changes**: Pure documentation phase

#### Phase 3: Minimal Patch (Optional, User Authorization Required)
**Objective**: Implement minimal security hardening changes if authorized

**Potential Changes** (only if user approves):
1. **nginx.conf**: Add HSTS, CSP, Permissions-Policy headers (conditional on SSL)
2. **scripts/smoke_prod.sh**: Create production smoke test script
3. **.env.prod.example**: Add missing environment variables documentation
4. **settings_prod.py**: Fix any P0 deployment check warnings

**Constraints**:
- No database migrations
- No application logic changes
- All changes gated by environment variables
- Backward compatible with existing deployments

### 2.3 Nginx Security Headers Strategy

**Approach**: Add headers conditionally based on SSL context

**Implementation Pattern** (aligned with existing nginx.conf):
```nginx
# In SSL-enabled production block (port 443)
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;
add_header Content-Security-Policy "default-src 'self'; ..." always;
add_header Permissions-Policy "camera=(), microphone=(), geolocation=()" always;

# Keep existing headers in both HTTP and HTTPS blocks
add_header X-Frame-Options "DENY" always;
add_header X-Content-Type-Options "nosniff" always;
add_header X-XSS-Protection "1; mode=block" always;
add_header Referrer-Policy "strict-origin-when-cross-origin" always;
```

**Rationale**: 
- HSTS should only be sent over HTTPS (spec requirement)
- CSP can be sent over HTTP (safe, recommended)
- Existing headers are duplicated in Django middleware (defense in depth)

**CSP Alignment**: Nginx CSP must match Django CSP settings to avoid conflicts:
- Django CSP in settings.py lines 400-480 (existing, commented analysis needed)
- Match directives: `default-src`, `script-src`, `style-src`, `img-src`, `connect-src`, `font-src`
- Add `frame-ancestors 'none'` (equivalent to X-Frame-Options: DENY)
- Add `upgrade-insecure-requests` for mixed content prevention

### 2.4 Django Deployment Check Strategy

**Execution Method**:
```bash
# In Docker container
docker compose -f infra/docker/docker-compose.prod.yml exec backend \
  python manage.py check --deploy --settings=core.settings_prod
```

**Expected Warnings Categories**:
1. **Security** (P0/P1): CSRF, Session, Cookie settings
2. **Database** (P2): Connection pooling, index optimization
3. **Static Files** (P1): Collectstatic verification
4. **Middleware** (P2): Order and configuration
5. **Template** (P3): Debug template tags

**Classification Criteria**:
- **P0 (Critical)**: Must fix before production (security vulnerabilities)
- **P1 (High)**: Should fix before production (best practices)
- **P2 (Medium)**: Recommended improvements (performance/reliability)
- **P3 (Low)**: Optional enhancements (code quality)

**Resolution Strategy**:
- P0: Fix in code or document explicit acceptance with risk assessment
- P1: Fix in code or add to roadmap
- P2/P3: Document as recommendations

### 2.5 Smoke Test Strategy

**Objective**: Validate critical production endpoints

**Test Scope**:
1. **Health Check**: `GET /api/health/` → 200 OK
2. **Static Files**: `GET /static/<sample-file>` → 200 OK + correct MIME type
3. **Media Files**: `GET /media/<authenticated-access-pattern>` → Proper access control

**Implementation Pattern** (extend existing `scripts/smoke.sh`):
```bash
#!/bin/bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8088}"
API_URL="$BASE_URL/api"

# Test 1: Health Check
test_health() {
  HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" $API_URL/health/)
  if [ "$HTTP_CODE" == "200" ]; then
    echo "✅ Health check: OK"
    return 0
  else
    echo "❌ Health check: FAIL ($HTTP_CODE)"
    return 1
  fi
}

# Test 2: Static Files
test_static() {
  # Try to fetch a known static file (e.g., admin CSS)
  HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" $BASE_URL/static/admin/css/base.css)
  if [ "$HTTP_CODE" == "200" ]; then
    echo "✅ Static files: OK"
    return 0
  else
    echo "❌ Static files: FAIL ($HTTP_CODE)"
    return 1
  fi
}

# Test 3: Media Access Control
test_media() {
  # Verify media is NOT publicly accessible (existing test in smoke.sh)
  HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" $BASE_URL/media/marker.txt)
  if [[ "$HTTP_CODE" == "403" || "$HTTP_CODE" == "404" ]]; then
    echo "✅ Media access control: OK (blocked)"
    return 0
  else
    echo "❌ Media access control: FAIL (should be 403/404, got $HTTP_CODE)"
    return 1
  fi
}

# Run all tests
test_health && test_static && test_media
```

**Integration Point**: Create `scripts/smoke_prod.sh` following existing pattern in `scripts/smoke.sh`

### 2.6 Backup/Restore Documentation Strategy

**Consolidation Approach**: Merge information from:
- `scripts/backup_db.sh` (shell script method)
- `backend/core/management/commands/backup.py` (Django command method)
- `backend/core/management/commands/restore.py` (restoration logic)
- `infra/docker/docker-compose.prod.yml` (volume definitions)
- Existing test: `test_backup_restore_real_fixed.py` (validation approach)

**Runbook Structure**:
1. **Overview**: Purpose, prerequisites, safety warnings
2. **Critical Volumes**: 
   - `postgres_data` → PostgreSQL database files
   - `media_volume` → User-uploaded files (exams, students, PDFs)
   - `static_volume` → Collected static files (recreatable via collectstatic)
3. **Backup Procedures**:
   - Method A: Shell script (`backup_db.sh`)
   - Method B: Django command (`python manage.py backup`)
   - Retention policy: 30 days (existing in backup_db.sh:19)
4. **Restore Procedures**:
   - Pre-restore checklist (⚠️ STOP containers, ⚠️ backup current state first)
   - Database restoration
   - Media restoration
   - Post-restore validation (smoke tests, data integrity checks)
5. **Testing**: Reference to `test_backup_restore_real_fixed.py`
6. **Troubleshooting**: Common errors and solutions

**Warning Pattern** (existing in codebase comments):
```markdown
⚠️ **ATTENTION**: Cette opération est destructive et irréversible.
- Arrêtez tous les services avant de restaurer
- Créez une sauvegarde de l'état actuel avant toute restauration
- Vérifiez l'intégrité de la sauvegarde avant de supprimer les données actuelles
```

---

## 3. Source Code Structure Changes

### 3.1 File Modifications (Phase 3 - Optional)

#### Modified Files (if authorized):

**1. infra/nginx/nginx.conf**
- **Current**: 58 lines, basic security headers
- **Change**: Add HSTS, CSP, Permissions-Policy headers
- **Location**: Inside `server` block (lines 5-57)
- **Condition**: Should be conditional on SSL/HTTPS configuration
- **Pattern**: Use existing `add_header` pattern (lines 13-16)

**2. .env.prod.example**
- **Current**: 51 lines, production env template
- **Change**: Add missing environment variables with documentation
- **Additions**:
  - `CSRF_TRUSTED_ORIGINS` (referenced in settings.py:47-50)
  - `METRICS_TOKEN` (referenced in settings.py:86)
  - `E2E_SEED_TOKEN` (referenced in settings.py:78, but only for prod-like)
  - Comments explaining SSL_ENABLED vs DJANGO_ENV

**3. backend/core/settings_prod.py** (if deployment check reveals issues)
- **Current**: 69 lines, minimal production overrides
- **Potential Changes**: Based on `manage.py check --deploy` results
- **Example**: If HSTS settings are flagged, ensure they're properly configured

#### New Files (if authorized):

**1. scripts/smoke_prod.sh**
- **Purpose**: Production-specific smoke tests
- **Pattern**: Extends existing `scripts/smoke.sh` (31 lines)
- **Tests**: Health, static files, media access control, security headers
- **Usage**: `BASE_URL=https://production-domain.com ./scripts/smoke_prod.sh`

### 3.2 Documentation Files (Phase 1 & 2 - Required)

**1. .zenflow/tasks/hardening-prod-settings-headers-ac7f/audit.md**
- **New file**: Comprehensive audit report
- **Sections**: 
  1. Executive Summary
  2. Django Deployment Check Results
  3. Security Headers Analysis
  4. Cookie Security Configuration
  5. ALLOWED_HOSTS Validation
  6. Critical Volumes Documentation
  7. Action Items with Prioritization
- **Language**: French (matching existing docs)
- **References**: MANUEL_SECURITE.md patterns, RUNBOOK_PRODUCTION.md structure

**2. .zenflow/tasks/hardening-prod-settings-headers-ac7f/runbook_backup_restore.md**
- **New file**: Consolidated backup/restore operational runbook
- **Sections**:
  1. Vue d'ensemble (Overview)
  2. Architecture et volumes critiques
  3. Procédures de sauvegarde
  4. Procédures de restauration
  5. Tests et validation
  6. Dépannage (Troubleshooting)
  7. Rétention et stockage
- **Language**: French
- **Pattern**: Follow existing RUNBOOK_PRODUCTION.md style

### 3.3 No Changes Required

**Files NOT modified**:
- `backend/core/settings.py`: No changes (already has conditional security logic)
- `docker-compose.prod.yml`: No changes (volume definitions are correct)
- Any application code (models, views, serializers, etc.)
- Any frontend code (Vue.js components, CSP nonces)
- Any test files (except potentially adding new smoke tests)
- CI/CD workflows (GitHub Actions)

---

## 4. Data Model / API / Interface Changes

### 4.1 No Data Model Changes
- No database migrations required
- No model field additions or modifications
- Existing data remains unchanged

### 4.2 No API Changes
- No new endpoints
- No endpoint signature changes
- Existing `/api/health/` endpoint used as-is for smoke tests

### 4.3 Environment Variable Interface

**New Environment Variables** (documentation only, optional in code):

| Variable | Required | Default | Purpose | Example |
|----------|----------|---------|---------|---------|
| `METRICS_TOKEN` | No | None | Secure /metrics endpoint | `random-token-123` |
| `CSRF_TRUSTED_ORIGINS` | Yes (prod) | localhost | Trusted CSRF origins | `https://domain.com` |
| `CORS_ALLOWED_ORIGINS` | Yes (prod) | localhost | Allowed CORS origins | `https://domain.com` |

**Existing Variables** (documented in audit):

| Variable | Current Usage | Validation |
|----------|---------------|------------|
| `SECRET_KEY` | Required in prod | settings_prod.py:16 |
| `DJANGO_ALLOWED_HOSTS` | Required in prod | settings_prod.py:18-21 |
| `SSL_ENABLED` | Controls HTTPS | settings.py:100 |
| `DJANGO_ENV` | Environment mode | settings.py:13 |
| `DEBUG` | Debug mode | settings.py:26-33 |

### 4.4 Configuration Interface

**Nginx Configuration Interface** (if modified):
- Headers applied at server level
- No changes to proxy behavior
- No changes to upstream resolution
- No changes to static/media serving

**Django Settings Interface**:
- No breaking changes to settings structure
- settings_prod.py continues to import from settings.py
- Conditional logic remains unchanged

---

## 5. Delivery Phases

### Phase 1: Audit Documentation (Priority: P0)

**Duration**: Estimated 1-2 hours  
**Deliverable**: `audit.md`

**Tasks**:
1. ✅ Run `python manage.py check --deploy` in production settings
2. ✅ Document all warnings with code references
3. ✅ Classify warnings by priority (P0-P3)
4. ✅ Document security headers current vs. recommended
5. ✅ Document cookie security configuration
6. ✅ Document ALLOWED_HOSTS validation
7. ✅ Document critical Docker volumes
8. ✅ Create prioritized action items list

**Verification**:
- Document completeness: All sections filled
- Accuracy: Code references verified
- Actionability: Each warning has clear resolution path
- Language: French, professional tone

**Dependencies**: None (analysis of existing code)

---

### Phase 2: Backup/Restore Runbook (Priority: P0)

**Duration**: Estimated 1-2 hours  
**Deliverable**: `runbook_backup_restore.md`

**Tasks**:
1. ✅ Document database backup procedures (shell script)
2. ✅ Document database backup procedures (Django command)
3. ✅ Document media backup procedures
4. ✅ Document restore procedures with validation
5. ✅ Document critical volumes with destruction warnings
6. ✅ Reference existing test scripts
7. ✅ Add troubleshooting section
8. ✅ Document retention policy (30 days)

**Verification**:
- Procedure clarity: No ambiguous steps
- Completeness: Pre/post checklists included
- Safety: Destruction warnings present
- Reproducibility: Can be executed by qualified sysadmin

**Dependencies**: None (consolidation of existing scripts/commands)

---

### Phase 3: Minimal Patch (Priority: P1, User Authorization Required)

**Duration**: Estimated 2-3 hours  
**Deliverable**: Code patches (optional)

**Tasks** (only if authorized):
1. ⚠️ Modify `infra/nginx/nginx.conf` for security headers
2. ⚠️ Update `.env.prod.example` with missing variables
3. ⚠️ Create `scripts/smoke_prod.sh` smoke test script
4. ⚠️ Fix P0 warnings from deployment check (if any)
5. ⚠️ Test changes in prod-like environment
6. ⚠️ Verify no regression in dev/staging

**Verification**:
- Backward compatibility: Dev/staging environments unaffected
- Functionality: Smoke tests pass
- Security: Headers validated with online tools
- Documentation: Changes documented in audit.md

**Dependencies**: 
- User authorization for code changes
- Phase 1 audit completed (know what to fix)
- Access to prod-like environment for testing

**Risk Mitigation**:
- All changes gated by environment variables
- Test in prod-like before production
- Rollback plan: Revert commits, restart containers

---

## 6. Verification Approach

### 6.1 Audit Document Verification

**Automated Checks**:
```bash
# Verify deployment check was run
docker compose -f infra/docker/docker-compose.prod.yml exec backend \
  python manage.py check --deploy --settings=core.settings_prod

# Check exit code
echo $?  # Should be 0 or warnings documented
```

**Manual Review**:
- [ ] All sections of audit.md completed
- [ ] Priority classification (P0-P3) applied to all warnings
- [ ] Code references include file path and line numbers
- [ ] Action items have clear ownership and timeline
- [ ] French language, professional tone
- [ ] Cross-references to existing documentation accurate

**Acceptance Criteria**:
- Document is comprehensive (no TBD sections)
- All P0 warnings have resolution plan
- Document is actionable (operator can execute action items)

### 6.2 Runbook Document Verification

**Manual Review**:
- [ ] Procedures are step-by-step with no ambiguity
- [ ] Destructive operations have ⚠️ warnings
- [ ] Pre-requisites clearly stated
- [ ] Post-validation steps included
- [ ] Troubleshooting section covers common errors
- [ ] References to test scripts accurate
- [ ] French language consistency

**Practical Test** (optional but recommended):
```bash
# Execute backup procedure in prod-like environment
./scripts/backup_db.sh

# Verify backup created
ls -lh backups/db_backup_*.sql.gz

# Test restore procedure (in isolated environment)
# Follow runbook steps exactly
```

**Acceptance Criteria**:
- Runbook can be executed by qualified sysadmin without clarification
- All procedures tested in prod-like environment
- No ambiguous steps remaining

### 6.3 Code Changes Verification (if Phase 3 executed)

**Pre-Deployment Tests**:
```bash
# 1. Smoke tests in prod-like environment
BASE_URL=http://localhost:8088 ./scripts/smoke_prod.sh

# 2. Verify security headers (if nginx changed)
curl -I http://localhost:8088 | grep -E "(X-Frame-Options|Content-Security-Policy|Strict-Transport-Security)"

# 3. Django deployment check
docker compose -f infra/docker/docker-compose.prod.yml exec backend \
  python manage.py check --deploy --settings=core.settings_prod

# 4. Verify no regression in dev
docker compose up -d
./scripts/smoke.sh
```

**Security Headers Validation**:
- Use online tools: securityheaders.com, Mozilla Observatory
- Target score: A or A+
- Verify CSP doesn't block legitimate resources

**Backward Compatibility**:
- [ ] Dev environment works (`docker compose up`)
- [ ] Staging environment works
- [ ] Prod-like environment works (E2E tests pass)
- [ ] No new errors in logs

**Acceptance Criteria**:
- All smoke tests pass
- Security headers present and correct
- No regression in existing environments
- Django deployment check passes or warnings documented

### 6.4 Integration Tests

**Docker Compose Validation**:
```bash
# Test full stack startup
docker compose -f infra/docker/docker-compose.prod.yml up -d

# Wait for health checks
sleep 30

# Verify all services healthy
docker compose -f infra/docker/docker-compose.prod.yml ps

# Run smoke tests
BASE_URL=http://localhost:8088 ./scripts/smoke_prod.sh

# Cleanup
docker compose -f infra/docker/docker-compose.prod.yml down
```

**Volume Persistence Test**:
```bash
# 1. Create test data
docker compose -f infra/docker/docker-compose.prod.yml exec backend \
  python manage.py shell -c "from django.contrib.auth.models import User; User.objects.create_user('test', 'test@example.com', 'password')"

# 2. Stop containers
docker compose -f infra/docker/docker-compose.prod.yml down

# 3. Restart containers
docker compose -f infra/docker/docker-compose.prod.yml up -d

# 4. Verify data persists
docker compose -f infra/docker/docker-compose.prod.yml exec backend \
  python manage.py shell -c "from django.contrib.auth.models import User; print(User.objects.filter(username='test').exists())"
```

**Expected Output**: `True` (data persisted)

### 6.5 Linting and Type Checking

**Backend Python**:
```bash
# Run existing linting/type checking (if configured)
# Check for pyproject.toml, setup.cfg, or .flake8 config
cd backend
python -m flake8 core/ || echo "No flake8 config"
python -m mypy core/ || echo "No mypy config"
```

**Shell Scripts**:
```bash
# Lint new smoke_prod.sh script
shellcheck scripts/smoke_prod.sh
```

**Nginx Configuration**:
```bash
# Test nginx config syntax
docker compose -f infra/docker/docker-compose.prod.yml exec nginx nginx -t
```

### 6.6 Documentation Review Checklist

**Audit.md**:
- [ ] Executive summary captures key findings
- [ ] Django deployment check results complete
- [ ] Security headers analysis current vs. recommended
- [ ] Cookie security configuration validated
- [ ] ALLOWED_HOSTS patterns documented
- [ ] Critical volumes documented with warnings
- [ ] Action items prioritized and assigned

**Runbook_backup_restore.md**:
- [ ] Overview section complete
- [ ] Prerequisites clearly stated
- [ ] Backup procedures (both methods) documented
- [ ] Restore procedures with pre/post validation
- [ ] Volume documentation with destruction warnings
- [ ] Troubleshooting section complete
- [ ] Retention policy documented

**Language and Style**:
- [ ] French language throughout (matching existing docs)
- [ ] Professional technical tone
- [ ] Clear and actionable instructions
- [ ] ⚠️ warnings for destructive operations
- [ ] ✅/❌ indicators for current state
- [ ] Code blocks with syntax highlighting
- [ ] Cross-references accurate

---

## 7. Risk Mitigation

### 7.1 Technical Risks

**Risk**: Breaking existing dev/staging environments  
**Mitigation**: 
- All security headers conditional on SSL_ENABLED
- Extensive testing in prod-like before production
- Backward compatibility verification in all environments

**Risk**: Overly restrictive CSP breaks frontend  
**Mitigation**:
- Align CSP with existing Django CSP configuration
- Test in prod-like with full frontend E2E suite
- Document CSP in audit.md for review before implementation

**Risk**: Incorrect backup/restore procedure  
**Mitigation**:
- Reference existing tested scripts
- Link to existing test: `test_backup_restore_real_fixed.py`
- Include validation steps in runbook
- Test in isolated environment before documenting

### 7.2 Operational Risks

**Risk**: Administrator misunderstands procedure  
**Mitigation**:
- Step-by-step instructions with no ambiguity
- Pre-requisites and post-validation steps
- Visual warnings (⚠️) for destructive operations
- Troubleshooting section with common errors

**Risk**: Volume data loss during operations  
**Mitigation**:
- Explicit volume documentation in runbook
- "Backup before restore" mandatory step
- Clear warnings about volume destruction
- Test restore in isolated environment first

### 7.3 Security Risks

**Risk**: Security headers misconfiguration  
**Mitigation**:
- Provide tested examples in audit.md
- Validate with online tools (securityheaders.com)
- Align with OWASP recommendations
- Document rationale for each header

**Risk**: Secrets exposure in documentation  
**Mitigation**:
- Use placeholder values in examples
- Explicit warnings about changing defaults
- No actual secrets in .env.prod.example
- Reference secrets management best practices

---

## 8. Success Metrics

### 8.1 Documentation Quality Metrics
- [ ] Zero ambiguous steps in runbook
- [ ] All P0 warnings classified and addressed
- [ ] 100% French language consistency
- [ ] All cross-references verified

### 8.2 Security Metrics (if Phase 3 executed)
- [ ] Security headers score: A or A+ (securityheaders.com)
- [ ] Django deployment check: 0 P0 warnings
- [ ] All cookies have secure flags when SSL_ENABLED=true
- [ ] ALLOWED_HOSTS strictly configured (no wildcard)

### 8.3 Operational Metrics
- [ ] Backup/restore procedures tested successfully
- [ ] Smoke tests pass in all environments
- [ ] Zero regression in dev/staging/prod-like
- [ ] Volume persistence validated

---

## 9. Assumptions and Constraints

### 9.1 Assumptions
1. Production deployment uses Docker Compose (not Kubernetes)
2. Nginx is the reverse proxy (confirmed in infra/nginx/)
3. TLS termination happens at nginx
4. Backup storage is local disk or mounted volume
5. System administrator has Docker and SSH access
6. PostgreSQL is the only database (no MongoDB, etc.)

### 9.2 Constraints
1. No breaking changes to existing deployments
2. No database migrations
3. No frontend code changes (CSP nonces, etc.)
4. No CI/CD workflow changes
5. Documentation in French only
6. Follow existing code style and patterns
7. Reuse existing backup/restore scripts where possible

### 9.3 Out of Scope (Confirmed)
- Infrastructure as Code (Terraform, Ansible)
- Monitoring/alerting setup
- TLS certificate management (Let's Encrypt)
- Container image hardening
- Penetration testing
- Load testing
- Redis authentication
- Database connection encryption

---

## 10. Next Steps

### 10.1 Immediate Actions
1. ✅ User reviews and approves this technical specification
2. ✅ Proceed to Planning phase (break down into tasks)
3. ✅ Begin Phase 1: Audit documentation

### 10.2 User Decisions Required
1. **Authorize Phase 3**: Should we implement code changes, or documentation only?
2. **Production Domain**: Should we use real domain in examples, or generic placeholders?
3. **Backup Storage**: Any specific requirements for backup storage location?

### 10.3 Optional Clarifications
- Scheduled backup configuration (cron) required?
- Off-site backup solution preferences?
- Monitoring integration for smoke tests?
- HSTS preload submission to browsers?

---

## 11. References

### 11.1 Internal Documentation
- Current settings: `backend/core/settings.py`, `backend/core/settings_prod.py`
- Nginx config: `infra/nginx/nginx.conf`
- Existing runbook: `docs/deployment/RUNBOOK_PRODUCTION.md`
- Security manual: `docs/security/MANUEL_SECURITE.md`
- Backup scripts: `scripts/backup_db.sh`
- Backup commands: `backend/core/management/commands/{backup,restore}.py`

### 11.2 External References
- Django deployment checklist: https://docs.djangoproject.com/en/4.2/howto/deployment/checklist/
- OWASP Secure Headers: https://owasp.org/www-project-secure-headers/
- Mozilla Observatory: https://observatory.mozilla.org/
- Security Headers: https://securityheaders.com/
- CSP Reference: https://content-security-policy.com/

### 11.3 Existing Tests
- Backup/restore test: `test_backup_restore_real_fixed.py`
- Smoke tests: `scripts/smoke.sh`, `scripts/smoke_staging.sh`
- E2E smoke: `frontend/tests/e2e/smoke-check.sh`

---

**Document Status**: Ready for Review  
**Next Phase**: Planning (task breakdown)  
**Approver**: User/Product Owner
