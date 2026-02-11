# Product Requirements Document: Production Hardening

**Task ID**: ZF-AUD-12  
**Created**: 2026-01-31  
**Status**: Draft  
**Priority**: High (Production Security)

---

## 1. Executive Summary

### 1.1 Objective
Transition the Korrigo platform from "prod-like local" environment to a fully hardened production deployment by implementing comprehensive security measures, operational procedures, and validation tests.

### 1.2 Background
The current codebase has production-oriented settings (settings_prod.py) but requires:
- Comprehensive audit of Django deployment warnings
- Hardened security headers (HSTS, CSP, X-Frame-Options)
- Validated backup/restore procedures
- Smoke tests for critical production endpoints

### 1.3 Success Criteria
- All critical Django `--deploy` warnings resolved
- Security headers properly configured in nginx
- Backup/restore procedures documented and tested
- Health check and static/media availability smoke tests implemented
- Complete audit report and operational runbook delivered

---

## 2. Current State Analysis

### 2.1 Existing Infrastructure

**Architecture Components**:
- Backend: Django 4.2 + DRF (Python 3.9)
- Frontend: Vue.js 3 + Vite
- Database: PostgreSQL 15
- Cache/Queue: Redis + Celery
- Reverse Proxy: Nginx
- Orchestration: Docker Compose

**Existing Settings Files**:
- `backend/core/settings.py` - Base settings with conditional logic for DEBUG/DJANGO_ENV
- `backend/core/settings_prod.py` - Production overrides (imports from base)
- `.env.prod.example` - Production environment variable template

**Current Security Measures** (from settings.py analysis):
- ✅ DEBUG forced to False when DJANGO_ENV=production
- ✅ SECRET_KEY validation in production
- ✅ ALLOWED_HOSTS validation (no wildcard in prod)
- ✅ Session/CSRF cookie security (conditional on SSL_ENABLED)
- ✅ HSTS headers (conditional on SSL_ENABLED)
- ✅ CORS configuration with explicit origins
- ✅ CSP middleware installed (django-csp)
- ✅ Basic security headers (X-Frame-Options, X-Content-Type-Options, XSS-Filter)

**Nginx Configuration** (infra/nginx/nginx.conf):
- ✅ Basic security headers (X-Frame-Options: DENY, X-Content-Type-Options: nosniff)
- ❌ Missing: HSTS header
- ❌ Missing: Content-Security-Policy header
- ❌ Missing: Referrer-Policy (currently "strict-origin-when-cross-origin")
- ❌ Missing: Permissions-Policy

**Existing Backup Infrastructure**:
- `scripts/backup_db.sh` - PostgreSQL dump script
- `backend/core/management/commands/backup.py` - Django command for DB + media backup
- `backend/core/management/commands/restore.py` - Django restore command
- Multiple test files for backup/restore validation

**Existing Documentation**:
- `docs/deployment/DEPLOY_PRODUCTION.md` - Deployment guide
- `docs/deployment/RUNBOOK_PRODUCTION.md` - Operational runbook
- `docs/security/MANUEL_SECURITE.md` - Security manual (1422 lines)

### 2.2 Gaps Identified

**Configuration Gaps**:
1. Django `--deploy` check has not been run to identify production warnings
2. CSP headers defined in Django settings but not in nginx
3. HSTS headers missing in nginx (only in Django when SSL_ENABLED=true)
4. No centralized environment variable validation for production
5. No smoke test scripts for health/static/media endpoints

**Documentation Gaps**:
1. No comprehensive audit document listing all hardening changes
2. Backup/restore procedures exist but not consolidated in a single runbook
3. No classification of deployment warnings by criticality
4. No validation checklist for production deployment

**Operational Gaps**:
1. No automated health check smoke tests
2. No validation of static/media file availability
3. No documented procedure for validating security headers in production

---

## 3. Requirements

### 3.1 Functional Requirements

#### FR-1: Django Deployment Audit
**Priority**: P0 (Critical)

- **FR-1.1**: Execute `python manage.py check --deploy` with production settings
- **FR-1.2**: Document all warnings and recommendations
- **FR-1.3**: Classify warnings by criticality:
  - **P0 (Critical)**: Security issues that must be fixed before production
  - **P1 (High)**: Significant issues that should be addressed
  - **P2 (Medium)**: Recommendations for best practices
  - **P3 (Low)**: Optional improvements
- **FR-1.4**: Provide resolution plan for each warning

**Acceptance Criteria**:
- All P0 warnings resolved or explicitly accepted with risk assessment
- All P1 warnings addressed or scheduled for resolution
- Audit report documents each warning with: code reference, impact, resolution status

#### FR-2: Security Headers Configuration
**Priority**: P0 (Critical)

- **FR-2.1**: Configure HSTS in nginx for production
  - `Strict-Transport-Security: max-age=31536000; includeSubDomains; preload`
- **FR-2.2**: Configure CSP in nginx (aligned with Django CSP settings)
  - Directives: default-src, script-src, style-src, img-src, connect-src, font-src
  - Frame-ancestors: 'none'
  - Upgrade-insecure-requests
- **FR-2.3**: Configure Referrer-Policy
  - `Referrer-Policy: strict-origin-when-cross-origin`
- **FR-2.4**: Configure Permissions-Policy (optional but recommended)
  - Disable unused browser features: camera, microphone, geolocation
- **FR-2.5**: Maintain X-Frame-Options: DENY
- **FR-2.6**: Maintain X-Content-Type-Options: nosniff
- **FR-2.7**: Maintain X-XSS-Protection: 1; mode=block

**Acceptance Criteria**:
- All headers present in nginx configuration
- Headers validated with security scanning tool (e.g., securityheaders.com)
- No conflicts between nginx and Django header configuration
- Headers only applied in production (SSL_ENABLED=true)

#### FR-3: Cookie Security
**Priority**: P0 (Critical)

- **FR-3.1**: Validate SESSION_COOKIE_SECURE=True in production
- **FR-3.2**: Validate CSRF_COOKIE_SECURE=True in production
- **FR-3.3**: Ensure SESSION_COOKIE_HTTPONLY=True
- **FR-3.4**: Ensure SESSION_COOKIE_SAMESITE='Lax'
- **FR-3.5**: Validate CSRF_COOKIE_SAMESITE='Lax'

**Acceptance Criteria**:
- All cookie security settings enforced when DJANGO_ENV=production
- Settings validated via Django check --deploy
- Documentation clearly explains SSL_ENABLED vs DJANGO_ENV=production

#### FR-4: Backup/Restore Procedures
**Priority**: P0 (Critical)

- **FR-4.1**: Document complete backup procedure
  - PostgreSQL database dump
  - Media files archive (tar.gz)
  - Backup retention policy (existing: 30 days)
  - Backup location and storage requirements
- **FR-4.2**: Document complete restore procedure
  - Database restoration from dump
  - Media files restoration from archive
  - Post-restore validation steps
- **FR-4.3**: Create unified backup/restore runbook
  - Pre-backup checklist
  - Backup execution steps
  - Verification steps
  - Restore execution steps (with warnings)
  - Rollback procedures
  - Common issues and troubleshooting
- **FR-4.4**: Document critical volumes for Docker setup
  - postgres_data (database persistence)
  - media_volume (user-uploaded files)
  - static_volume (collected static files)
  - Volume destruction warnings

**Acceptance Criteria**:
- Runbook document created: `runbook_backup_restore.md`
- Procedures include both shell scripts and Django management commands
- Clear warnings about destructive operations (⚠️ markers)
- Procedures tested with existing test scripts
- Reference to existing backup test: `test_backup_restore_real_fixed.py`

#### FR-5: Smoke Tests
**Priority**: P1 (High)

- **FR-5.1**: Create health check smoke test
  - Test endpoint: `GET /api/health/`
  - Expected: HTTP 200 OK
  - Validate response structure
- **FR-5.2**: Create static files availability test
  - Test static files endpoint
  - Expected: HTTP 200 OK for sample static file
  - Validate MIME types
- **FR-5.3**: Create media files availability test
  - Test media files endpoint
  - Expected: HTTP 200 OK for sample media file
  - Validate file serving
- **FR-5.4**: Create combined smoke test script
  - Execute all tests in sequence
  - Clear pass/fail reporting
  - Exit code 0 for success, non-zero for failure

**Acceptance Criteria**:
- Smoke test script created (bash or Python)
- Tests executable in Docker environment
- Integration with existing scripts structure (`scripts/smoke.sh` already exists)
- Documentation in runbook

#### FR-6: ALLOWED_HOSTS Validation
**Priority**: P0 (Critical)

- **FR-6.1**: Document ALLOWED_HOSTS requirements for production
- **FR-6.2**: Ensure validation prevents wildcard (*) in production
- **FR-6.3**: Provide examples for common deployment scenarios
  - Single domain
  - Multiple domains (www + apex)
  - IP-based access (development/staging)

**Acceptance Criteria**:
- Validation in settings_prod.py raises error for invalid hosts
- Documentation includes examples in audit report
- .env.prod.example updated with clear instructions

### 3.2 Non-Functional Requirements

#### NFR-1: Security
- All changes must maintain or improve security posture
- No security regression in existing functionality
- Follow OWASP best practices for web application security

#### NFR-2: Backward Compatibility
- Changes must not break existing dev/staging environments
- SSL_ENABLED flag must continue to control HTTPS-specific settings
- Existing backup scripts must continue to function

#### NFR-3: Documentation Quality
- All documentation in French (matching existing docs)
- Clear, actionable instructions
- No ambiguous steps
- Use existing documentation structure and style

#### NFR-4: Operational Safety
- All destructive operations must have clear warnings
- Backup procedures must be tested before restore procedures
- Rollback procedures documented for all changes

---

## 4. Deliverables

### 4.1 Required Deliverables

#### D-1: audit.md
**Location**: `.zenflow/tasks/hardening-prod-settings-headers-ac7f/audit.md`

**Contents**:
1. **Executive Summary**
   - Current security posture
   - Critical findings
   - Recommended actions
2. **Django Deployment Check Results**
   - All warnings from `manage.py check --deploy`
   - Classification by priority (P0-P3)
   - Resolution status for each warning
3. **Security Headers Configuration**
   - Current state vs. recommended state
   - Proposed nginx configuration changes
   - Rationale for each header
4. **Cookie Security Configuration**
   - Current settings
   - Recommended settings for production
   - Environment variable requirements
5. **ALLOWED_HOSTS Configuration**
   - Current validation logic
   - Recommended configuration patterns
   - Examples for common scenarios
6. **Volumes and Data Safety**
   - Critical Docker volumes
   - Backup requirements
   - Volume destruction warnings
7. **Action Items**
   - Prioritized list of changes
   - Owner and timeline for each

#### D-2: runbook_backup_restore.md
**Location**: `.zenflow/tasks/hardening-prod-settings-headers-ac7f/runbook_backup_restore.md`

**Contents**:
1. **Overview**
   - Purpose and scope
   - Prerequisites
   - Safety warnings
2. **Architecture**
   - Components to backup (DB, media, static)
   - Docker volumes
   - Backup storage location
3. **Backup Procedures**
   - Manual backup via shell script
   - Manual backup via Django command
   - Scheduled backup configuration
   - Verification steps
4. **Restore Procedures**
   - Pre-restore checklist
   - Restore from shell script backup
   - Restore from Django command backup
   - Post-restore validation
5. **Testing Backup/Restore**
   - Using existing test scripts
   - Validation procedures
6. **Troubleshooting**
   - Common issues
   - Error messages and solutions
7. **Retention and Storage**
   - Current retention policy (30 days)
   - Storage requirements
   - Off-site backup recommendations

#### D-3: Minimal Patch (Optional, if authorized)
**Scope**: Only if explicitly requested by user

**Potential Changes**:
- nginx.conf: Add missing security headers
- settings_prod.py: Fix any P0 deployment check warnings
- scripts/smoke_prod.sh: New smoke test script
- .env.prod.example: Add missing environment variables

**Constraints**:
- No changes to core application logic
- No database migrations
- No breaking changes to existing deployments
- All changes must be backward compatible

### 4.2 Documentation Standards

**Language**: French (matching existing documentation)

**Structure**: Markdown with:
- Clear hierarchy (H1 for title, H2 for sections, H3 for subsections)
- Code blocks with syntax highlighting
- Warning callouts: `⚠️ **ATTENTION**: ...`
- Success indicators: `✅`
- Issue indicators: `❌`
- Tables for structured data
- Cross-references to existing documentation

**Tone**:
- Professional and technical
- Clear and actionable
- No ambiguity in procedures
- Assumptions explicitly stated

---

## 5. Technical Constraints

### 5.1 Environment Constraints
- Must support both HTTP (prod-like/E2E) and HTTPS (real production)
- SSL_ENABLED flag controls HTTPS-specific settings
- DJANGO_ENV=production controls production-mode behavior
- Docker Compose for orchestration

### 5.2 Compatibility Constraints
- Django 4.2
- Python 3.9
- PostgreSQL 15
- Nginx (version from docker image)
- Existing middleware stack (CSP, CORS, Security)

### 5.3 Security Constraints
- Follow OWASP Top 10 2021 guidelines
- Align with existing security documentation (MANUEL_SECURITE.md)
- Maintain RGPD/GDPR compliance
- No exposure of secrets in logs or configuration files

---

## 6. Out of Scope

### 6.1 Explicitly Excluded
- **Infrastructure as Code**: No Terraform/Ansible automation
- **Monitoring/Alerting**: No Prometheus/Grafana setup (metrics endpoint exists)
- **CI/CD Changes**: No modifications to GitHub Actions workflows
- **Application Features**: No new functional capabilities
- **Database Optimization**: No query performance tuning
- **Frontend Security**: No changes to Vue.js CSP nonces
- **TLS Certificate Management**: No Let's Encrypt automation
- **Container Image Hardening**: No Dockerfile security review
- **Penetration Testing**: No active security assessment
- **Load Testing**: No performance validation

### 6.2 Deferred to Future
- Migration from django-csp to nginx-only CSP (requires frontend changes)
- Redis authentication and encryption
- Database connection encryption (SSL mode)
- Automated security scanning integration
- Secrets management with Vault/similar

---

## 7. Assumptions

### 7.1 Environment Assumptions
- Production deployment uses Docker Compose
- Nginx is the reverse proxy (not Caddy/Traefik)
- PostgreSQL is the only database
- TLS termination happens at nginx
- Backend does not directly handle HTTPS

### 7.2 Operational Assumptions
- System administrator has SSH access to production server
- Docker and Docker Compose are installed
- Backup storage is available (local disk or mounted volume)
- Production server has sufficient disk space for backups
- System administrator can run privileged Docker commands

### 7.3 User Knowledge Assumptions
- User understands Docker Compose basics
- User can read and execute bash scripts
- User understands environment variables
- User has basic Django knowledge
- User follows documentation carefully

---

## 8. Risk Assessment

### 8.1 Technical Risks

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| Breaking existing dev/staging | Low | High | Thorough testing, conditional configuration |
| Incorrect backup/restore procedure | Low | Critical | Reference existing tests, validation steps |
| Overly restrictive CSP breaks frontend | Medium | High | Aligned with existing CSP config, testing required |
| Missing environment variable in production | Medium | High | Comprehensive validation in settings_prod.py |
| Volume data loss during deployment | Low | Critical | Clear warnings, backup before changes |

### 8.2 Operational Risks

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| Administrator misunderstands procedure | Medium | High | Clear documentation, step-by-step instructions |
| Backup not tested before disaster | High | Critical | Explicit testing procedures in runbook |
| Incomplete restore procedure | Low | Critical | Post-restore validation checklist |
| Security headers misconfiguration | Low | Medium | Reference examples, validation tools |

---

## 9. Success Metrics

### 9.1 Technical Success Criteria
- [ ] Zero P0 Django deployment warnings remaining
- [ ] All security headers present and correct in nginx
- [ ] Backup/restore procedures executed successfully in test
- [ ] Smoke tests pass in prod-like environment
- [ ] No regression in existing functionality

### 9.2 Documentation Success Criteria
- [ ] audit.md is comprehensive and actionable
- [ ] runbook_backup_restore.md has no ambiguous steps
- [ ] All procedures are reproducible by a qualified administrator
- [ ] Cross-references to existing documentation are accurate

### 9.3 Security Success Criteria
- [ ] Security headers validation score A or A+ (securityheaders.com)
- [ ] All cookies have secure flags in production
- [ ] No secrets exposed in configuration or logs
- [ ] ALLOWED_HOSTS strictly configured

---

## 10. Dependencies

### 10.1 External Dependencies
- Django documentation for deployment checks
- OWASP guidelines for security headers
- Mozilla Observatory / securityheaders.com for validation

### 10.2 Internal Dependencies
- Existing codebase (no changes expected during this task)
- Existing documentation structure
- Existing backup/restore scripts
- Existing test infrastructure

### 10.3 Team Dependencies
- User approval for any code changes (if patch is requested)
- User validation of backup/restore procedures
- User confirmation of deployment scenarios (single domain, multiple domains, etc.)

---

## 11. Open Questions

### 11.1 Deployment Configuration
1. **Production URL**: What is the actual production domain?
   - Needed for: CSP connect-src, ALLOWED_HOSTS examples
   - **Assumption**: Will use example domains in documentation

2. **SSL Certificate Provider**: Let's Encrypt, commercial, or self-signed?
   - Needed for: HSTS preload recommendations
   - **Assumption**: Will document requirements for standard HTTPS setup

3. **Backup Storage**: Local disk, NFS, S3, or other?
   - Needed for: Backup retention and storage recommendations
   - **Assumption**: Will document local disk with notes on alternatives

### 11.2 Operational Requirements
4. **Scheduled Backups**: Should we provide cron configuration?
   - **Assumption**: Will document manual backup, mention cron as option

5. **Off-site Backups**: Required for disaster recovery?
   - **Assumption**: Will recommend but not implement

6. **Monitoring Integration**: Should smoke tests integrate with monitoring?
   - **Assumption**: Will provide standalone scripts, note integration possibilities

### 11.3 Security Requirements
7. **CSP Report-Only Mode**: Should CSP be report-only initially?
   - **Assumption**: Will use enforce mode (aligned with existing Django config)

8. **HSTS Preload**: Should domain be submitted to HSTS preload list?
   - **Assumption**: Will configure for preload but note submission is optional

9. **Permissions-Policy**: Required or optional?
   - **Assumption**: Will include as optional/recommended

---

## 12. Next Steps

### 12.1 Clarifications Needed (from User)
Before proceeding to Technical Specification:

**Critical Questions**:
1. Should we include the minimal patch, or only documentation?
2. Are there specific deployment scenarios to document (e.g., behind additional proxy)?
3. Are there specific compliance requirements beyond RGPD (e.g., ISO 27001)?

**Nice-to-Have Clarifications**:
4. Production URL domain (for specific examples)?
5. Backup storage location preferences?
6. Scheduled backup requirements?

**Assumptions if no clarifications provided**:
- Will provide documentation only (no patch)
- Will document standard Docker Compose deployment
- Will use generic examples for domains and storage

### 12.2 Recommended Approach
1. User reviews and approves this requirements document
2. Proceed to Technical Specification phase
3. Implementation (if patch authorized)
4. User validates deliverables

---

## 13. Appendix

### A.1 Reference Documents
- Task description: `.zenflow/tasks/hardening-prod-settings-headers-ac7f/plan.md`
- Current settings: `backend/core/settings.py`, `backend/core/settings_prod.py`
- Nginx config: `infra/nginx/nginx.conf`
- Existing runbook: `docs/deployment/RUNBOOK_PRODUCTION.md`
- Security manual: `docs/security/MANUEL_SECURITE.md`
- Existing backup script: `scripts/backup_db.sh`
- Backup command: `backend/core/management/commands/backup.py`
- Restore command: `backend/core/management/commands/restore.py`

### A.2 Key Files Analyzed
```
backend/core/settings.py              (512 lines) - Base settings
backend/core/settings_prod.py         (69 lines)  - Production overrides
infra/nginx/nginx.conf                (58 lines)  - Reverse proxy config
infra/docker/docker-compose.prod.yml  (121 lines) - Production orchestration
.env.prod.example                     (51 lines)  - Production env template
scripts/backup_db.sh                  (26 lines)  - Database backup script
backend/core/management/commands/backup.py    (101 lines) - Backup command
backend/core/management/commands/restore.py   (?)          - Restore command
docs/security/MANUEL_SECURITE.md      (1422 lines) - Security manual
docs/deployment/RUNBOOK_PRODUCTION.md (94 lines)   - Operational runbook
```

### A.3 Security Headers Reference
**Recommended Production Headers**:
```nginx
# HTTPS Enforcement
Strict-Transport-Security: max-age=31536000; includeSubDomains; preload

# Content Security Policy
Content-Security-Policy: default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data: blob:; font-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'; upgrade-insecure-requests

# Clickjacking Protection
X-Frame-Options: DENY

# MIME Type Sniffing Protection
X-Content-Type-Options: nosniff

# XSS Filter (legacy but harmless)
X-XSS-Protection: 1; mode=block

# Referrer Policy
Referrer-Policy: strict-origin-when-cross-origin

# Permissions Policy (optional)
Permissions-Policy: camera=(), microphone=(), geolocation=()
```

---

**Document Status**: Ready for Review  
**Next Phase**: Technical Specification (after user approval)
