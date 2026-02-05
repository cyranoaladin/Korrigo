# Production Hardening Implementation Plan

## Configuration
- **Artifacts Path**: `.zenflow/tasks/hardening-prod-settings-headers-ac7f`
- **Task ID**: ZF-AUD-12
- **Priority**: P0 (Critical - Production Security)

---

## Workflow Steps

### [x] Step: Requirements
<!-- chat-id: 73ba879d-08ae-430a-9167-d7f91859a586 -->

Product Requirements Document (PRD) completed.

**Status**: ✅ Complete
- Comprehensive requirements analysis done
- Current state documented
- Gaps identified
- Success criteria defined

**Deliverable**: `requirements.md` (616 lines)

### [x] Step: Technical Specification
<!-- chat-id: 18233a99-5edc-459e-ba43-9702cf8e16dd -->

**Status**: ⚠️ Skipped - Directly proceeding to planning
- Task scope is primarily audit, documentation, and configuration
- No complex architectural decisions required
- Requirements document is comprehensive enough for planning

### [x] Step: Planning
<!-- chat-id: d66e8b8a-f35a-446e-b179-646619f16839 -->

Create detailed implementation plan with concrete tasks.

**Status**: ✅ Complete (current step)

---

## Implementation Tasks

### [x] Step: Django Deployment Check Audit
<!-- chat-id: 324993ed-4597-4296-83d0-e2f225925fbf -->
<!-- Expected duration: 1-2 hours -->

**Objective**: Execute Django deployment check and document all warnings by criticality.

**Actions**:
1. Run `python manage.py check --deploy` with production settings
2. Capture all warnings and recommendations
3. Classify each warning by priority (P0-P3)
4. Document resolution status and recommendations
5. Check for security middleware order and configuration

**Files to analyze**:
- `backend/core/settings.py` (512 lines)
- `backend/core/settings_prod.py` (69 lines)
- Django middleware configuration
- Installed apps configuration

**Expected warnings to investigate**:
- HSTS settings (SECURE_HSTS_SECONDS)
- SECURE_SSL_REDIRECT configuration
- Cookie secure flags verification
- ALLOWED_HOSTS validation
- SECRET_KEY strength
- SECURE_CONTENT_TYPE_NOSNIFF
- SECURE_BROWSER_XSS_FILTER

**Verification**:
- [x] All warnings captured and documented
- [x] Each warning classified with priority
- [x] Resolution recommendations provided
- [x] No P0 warnings remain unaddressed

**Output**: Section in `audit.md` with deployment check results

**Status**: ✅ Complete
- Django deployment check executed successfully
- 50 warnings identified and classified:
  - P0 (Critical): 0 warnings
  - P1 (High): 2 warnings (HSTS, SSL redirect - both expected due to conditional configuration)
  - P2 (Medium): 0 warnings
  - P3 (Low): 48 warnings (drf_spectacular - API documentation, non-blocking)
- Complete audit report generated: `audit.md` (899 lines)
- All security configurations analyzed and documented
- Action plan with prioritized recommendations created

---

### [x] Step: Security Headers Analysis and Configuration
<!-- chat-id: 2d313712-2fe9-41d4-a286-1649646c6e96 -->
<!-- Expected duration: 2-3 hours -->

**Objective**: Analyze current security headers and propose production-hardened configuration.

**Current State** (from nginx.conf):
- ✅ X-Frame-Options: DENY
- ✅ X-Content-Type-Options: nosniff
- ✅ X-XSS-Protection: 1; mode=block
- ✅ Referrer-Policy: strict-origin-when-cross-origin
- ❌ Missing: HSTS (Strict-Transport-Security)
- ❌ Missing: Content-Security-Policy
- ❌ Missing: Permissions-Policy

**Actions**:
1. Document current header configuration in nginx and Django
2. Analyze Django CSP settings (django-csp middleware)
3. Propose nginx header additions for production
4. Define HSTS configuration (max-age, includeSubDomains, preload)
5. Define CSP directives aligned with frontend requirements
6. Define Permissions-Policy for unused browser features
7. Document header precedence (nginx vs Django)
8. Create conditional configuration for SSL_ENABLED flag

**Files to analyze**:
- `infra/nginx/nginx.conf` (58 lines)
- `backend/core/settings.py` (CSP_* settings)
- `backend/core/middleware.py` (if exists)

**Configuration to propose**:
```nginx
# HTTPS Enforcement (only when SSL_ENABLED=true)
Strict-Transport-Security: max-age=31536000; includeSubDomains; preload

# Content Security Policy
Content-Security-Policy: default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data: blob:; font-src 'self'; connect-src 'self'; frame-ancestors 'none'; upgrade-insecure-requests

# Permissions Policy
Permissions-Policy: camera=(), microphone=(), geolocation=()
```

**Verification**:
- [x] All security headers documented
- [x] Nginx configuration aligned with Django
- [x] No conflicts between layers
- [x] Conditional logic for SSL_ENABLED explained

**Output**: Section in `audit.md` with security headers analysis and proposed configuration

**Status**: ✅ Complete
- Enhanced audit.md section 3 with 4 new subsections (3.5-3.8)
- Section 3.5: Header precedence and defense-in-depth analysis
- Section 3.6: Conditional SSL_ENABLED configuration explained
- Section 3.7: Complete nginx configs for HTTP (prod-like) and HTTPS (production)
- Section 3.8: Validation methods (curl, DevTools, online tools, automated script)
- Total: 467 lines added to comprehensive security headers documentation

---

### [x] Step: Cookie Security Audit
<!-- chat-id: 452ffcf9-41b7-4447-8663-2c0425b4e8a1 -->
<!-- Expected duration: 1 hour -->

**Objective**: Verify and document cookie security settings for production.

**Current Settings** (from settings_prod.py):
- SESSION_COOKIE_SECURE = True
- CSRF_COOKIE_SECURE = True
- SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

**Actions**:
1. Document all cookie security settings
2. Verify SESSION_COOKIE_HTTPONLY configuration
3. Verify SESSION_COOKIE_SAMESITE and CSRF_COOKIE_SAMESITE
4. Document relationship between SSL_ENABLED and cookie security
5. Validate that settings_prod.py enforces all security flags
6. Check for any cookie-related deployment check warnings

**Files to review**:
- `backend/core/settings.py` (lines 58-63)
- `backend/core/settings_prod.py` (lines 41-43)

**Verification**:
- [x] All cookie security flags documented
- [x] Production settings enforce secure cookies
- [x] Environment variable requirements clear

**Output**: Section in `audit.md` with cookie security configuration

**Status**: ✅ Complete
- Enhanced audit.md section 4 with 5 new subsections (4.4-4.8)
- Section 4.4: Complete inventory of session and CSRF cookie parameters
- Section 4.5: Django deployment check validation (no cookie warnings)
- Section 4.6: SSL_ENABLED configuration impact documented
- Section 4.7: Environment variable requirements specified
- Section 4.8: Recommendations and validation checklist
- **Key finding**: Identified configuration conflict between settings.py and settings_prod.py (P1)
- Total: 204 lines added to comprehensive cookie security documentation

---

### [x] Step: ALLOWED_HOSTS Configuration Analysis
<!-- chat-id: 6e42036c-bb52-4b95-b8bb-8c0c9180f0d9 -->
<!-- Expected duration: 1 hour -->

**Objective**: Document ALLOWED_HOSTS validation and provide deployment examples.

**Current Implementation** (from settings.py):
```python
ALLOWED_HOSTS = csv_env("ALLOWED_HOSTS", "localhost,127.0.0.1")
if "*" in ALLOWED_HOSTS and DJANGO_ENV == "production":
    raise ValueError("ALLOWED_HOSTS cannot contain '*' in production")
```

**Current Implementation** (from settings_prod.py):
```python
DJANGO_ALLOWED_HOSTS = os.environ.get("DJANGO_ALLOWED_HOSTS", "")
ALLOWED_HOSTS = [h.strip() for h in DJANGO_ALLOWED_HOSTS.split(",") if h.strip()]
if not ALLOWED_HOSTS:
    raise ValueError("DJANGO_ALLOWED_HOSTS must be set (comma-separated)")
```

**Actions**:
1. Document current validation logic
2. Provide examples for common scenarios:
   - Single domain: `example.com`
   - Domain + www: `example.com,www.example.com`
   - IP-based staging: `192.168.1.100`
   - Multiple domains: `app.example.com,api.example.com`
3. Document the difference between ALLOWED_HOSTS (base) and DJANGO_ALLOWED_HOSTS (prod)
4. Update `.env.prod.example` recommendations

**Verification**:
- [x] Clear examples documented
- [x] Environment variable naming explained
- [x] Validation logic documented

**Output**: Section in `audit.md` with ALLOWED_HOSTS configuration guide

**Status**: ✅ Complete
- Enhanced audit.md section 5 with 5 new subsections (5.4-5.8)
- Section 5.4: Detailed comparison between ALLOWED_HOSTS and DJANGO_ALLOWED_HOSTS variables
- Section 5.5: Django validation behavior and Host Header Attack protection
- Section 5.6: Advanced use cases (multi-region, domain migration, load balancer)
- Section 5.7: Common pitfalls and solutions (whitespace, ports, IPv6, undefined vs empty)
- Section 5.8: Comprehensive recommendations and pre-deployment checklist
- Enhanced .env.prod.example with detailed DJANGO_ALLOWED_HOSTS documentation
- Total: 314 lines added to section 5 covering all configuration scenarios

---

### [x] Step: Docker Volumes and Data Safety Documentation
<!-- chat-id: 5b5c8035-9ae1-46d1-808b-c4dc528f8ce3 -->
<!-- Expected duration: 1 hour -->

**Objective**: Document critical Docker volumes and backup requirements.

**Actions**:
1. Identify critical volumes from docker-compose files:
   - postgres_data (database)
   - media_volume (user uploads)
   - static_volume (collected static files)
   - redis_data (cache, not critical)
2. Document volume destruction risks
3. Document backup requirements for each volume
4. Create warning checklist for destructive operations
5. Document volume mount locations

**Files to analyze**:
- `infra/docker/docker-compose.prod.yml`
- `docker-compose.yml` (if exists)
- `.env.prod.example`

**Verification**:
- [x] All critical volumes identified
- [x] Destruction risks documented
- [x] Clear warnings for operators

**Output**: Section in `audit.md` with volumes documentation

**Status**: ✅ Complete
- Enhanced audit.md section 6 with 4 new subsections (6.6-6.9)
- Section 6.6: Detailed volume mount locations for all containers (postgres_data, media_volume, static_volume, redis_data)
- Section 6.7: Comprehensive backup requirements per volume with frequencies, methods, and validation procedures
- Section 6.8: Volume growth estimation and capacity planning (small/medium/large platforms)
- Section 6.9: Enhanced warning checklist for destructive operations with pre/during/post checklists
- Total: 474 lines added covering volume mapping, backup strategies, capacity planning, and operational safety
- All critical volumes identified with detailed mount points, content description, and size estimates
- Destruction risks extensively documented with safe vs destructive commands
- Clear operational warnings with STOP-BACKUP-VERIFY-DOCUMENT-COMMUNICATE-TEST-APPROVE workflow

---

### [x] Step: Backup Procedures Documentation
<!-- chat-id: d284ca55-bba2-41f8-92e0-276ab96a3031 -->
<!-- Expected duration: 2-3 hours -->

**Objective**: Create comprehensive backup/restore runbook.

**Existing Resources**:
- `scripts/backup_db.sh` (815 bytes)
- `backend/core/management/commands/backup.py`
- `backend/core/management/commands/restore.py`
- Test files for validation

**Actions**:
1. **Analyze existing backup scripts**:
   - Read `scripts/backup_db.sh`
   - Read `backend/core/management/commands/backup.py`
   - Understand backup output format and location
   - Document retention policy (30 days)

2. **Document backup procedures**:
   - Pre-backup checklist
   - Method 1: Shell script approach
   - Method 2: Django management command approach
   - Backup verification steps
   - Scheduled backup setup (cron example)

3. **Document what gets backed up**:
   - PostgreSQL database (structure + data)
   - Media files (user uploads)
   - Static files (optional, can be regenerated)
   - Configuration files (environment variables - WARNING: contains secrets)

4. **Document backup storage**:
   - Default location
   - Storage requirements
   - Off-site backup recommendations
   - Retention policy

**Files to read**:
- `scripts/backup_db.sh`
- `backend/core/management/commands/backup.py`
- `backend/core/management/commands/restore.py`
- Related test files

**Verification**:
- [x] Both backup methods documented
- [x] Clear step-by-step instructions
- [x] Pre-flight checklist included
- [x] Verification procedure included

**Output**: Backup section in `runbook_backup_restore.md`

**Status**: ✅ Complete
- Created comprehensive runbook_backup_restore.md (520 lines)
- Section 1: Vue d'ensemble (objectives, scope, recommended frequencies)
- Section 2: Prérequis et accès (access, tools, environment variables)
- Section 3: Architecture et composants (volumes mapping, sensitive data warnings)
- Section 4: Procédures de backup (complete documentation):
  - Pre-backup checklist
  - Method 1: Shell script (backup_db.sh) - fast DB-only backups
  - Method 2: Django command - complete backup (DB + media)
  - Comparison table of both methods
  - Independent media backup procedures
  - Cron automation (user crontab + systemd timers)
  - Storage and archiving strategies (local, external, 3-2-1 rule)
  - Post-backup validation checklist and scripts
  - Notifications and alerting (email, Slack, Healthchecks.io)
- Section 7: Politique de rétention (retention policies, automatic cleanup)
- Section 8: Troubleshooting (common backup errors)
- Section 9: Référence rapide (essential commands, checklists, contacts)
- All backup methods documented with examples, outputs, and verification steps
- Automation via cron and systemd timers fully documented
- Off-site backup strategies and 3-2-1 rule explained
- Total: 520 lines of comprehensive operational documentation

---

### [ ] Step: Restore Procedures Documentation
<!-- Expected duration: 2-3 hours -->

**Objective**: Document comprehensive restore procedures with safety warnings.

**Actions**:
1. **Analyze existing restore scripts**:
   - Read `backend/core/management/commands/restore.py`
   - Understand restore process and validation
   - Document destructive operations

2. **Create pre-restore checklist**:
   - ⚠️ STOP all application services
   - ⚠️ Backup current state before restore
   - Verify backup file integrity
   - Confirm backup timestamp is correct
   - Document who authorized the restore
   - Verify sufficient disk space

3. **Document restore procedures**:
   - Method 1: Database restore from shell script backup
   - Method 2: Full restore from Django command backup
   - Step-by-step instructions with warnings
   - Expected output at each step

4. **Document post-restore validation**:
   - Database connection test
   - Data integrity checks
   - Media file availability
   - Application smoke tests
   - User authentication test

5. **Document rollback procedures**:
   - If restore fails mid-process
   - How to return to pre-restore state
   - Emergency contacts

6. **Common issues and troubleshooting**:
   - Permission errors
   - Disk space issues
   - Database connection failures
   - Corrupted backup files

**Verification**:
- [ ] Pre-restore checklist complete
- [ ] Destructive operations clearly marked with ⚠️
- [ ] Post-restore validation steps clear
- [ ] Rollback procedures documented
- [ ] Troubleshooting section comprehensive

**Output**: Restore section in `runbook_backup_restore.md`

---

### [ ] Step: Backup/Restore Runbook Assembly
<!-- Expected duration: 1 hour -->

**Objective**: Assemble complete operational runbook from backup and restore documentation.

**Actions**:
1. Create document structure:
   - Overview and purpose
   - Prerequisites and access requirements
   - Architecture overview (components, volumes)
   - Backup procedures (from previous step)
   - Restore procedures (from previous step)
   - Testing procedures
   - Retention and storage policy
   - Troubleshooting guide
   - Quick reference cheatsheet

2. Add cross-references:
   - Link to existing documentation
   - Reference test files
   - Link to audit.md for volume safety

3. Format for operational use:
   - Clear hierarchy
   - Copy-paste friendly commands
   - Warning callouts (⚠️)
   - Verification checkboxes
   - French language (matching existing docs)

**Verification**:
- [ ] Document is complete and self-contained
- [ ] All procedures are reproducible
- [ ] Cross-references are accurate
- [ ] No ambiguous steps

**Output**: Complete `runbook_backup_restore.md`

---

### [ ] Step: Production Smoke Tests Enhancement
<!-- Expected duration: 2 hours -->

**Objective**: Enhance existing smoke tests for production validation.

**Current State**:
- `scripts/smoke.sh` exists with:
  - Health check test (GET /api/health/)
  - Media block test (403/404 check)

**Actions**:
1. **Analyze existing smoke test**:
   - Read `scripts/smoke.sh`
   - Understand test structure and patterns
   - Identify what's already tested

2. **Create enhanced smoke test script** (`scripts/smoke_prod.sh`):
   - Reuse health check test
   - Add static files availability test
   - Add authenticated media access test (if applicable)
   - Add security headers validation
   - Add SSL/TLS check (if SSL_ENABLED)
   - Clear pass/fail reporting
   - Exit codes: 0 for success, 1 for failure

3. **Test categories**:
   ```bash
   # 1. Core functionality
   - Health endpoint: GET /api/health/ → 200
   - API availability: GET /api/ → 401/403/404 (not 500)
   
   # 2. Static/Media serving
   - Static files: GET /static/[known-file] → 200
   - Media protection: GET /media/[file] → 403/404 (public block)
   
   # 3. Security validation
   - Security headers present
   - HTTPS redirect (if SSL_ENABLED)
   - HSTS header (if SSL_ENABLED)
   ```

4. **Documentation**:
   - Usage instructions in runbook
   - How to run in Docker environment
   - How to interpret results

**Files to create/modify**:
- Create: `scripts/smoke_prod.sh` (new production smoke test)
- Read: `scripts/smoke.sh` (existing smoke test)
- Read: `backend/tests/test_smoke.py` (Python smoke tests)

**Verification**:
- [ ] Smoke test script executable
- [ ] Tests cover health, static, media
- [ ] Clear output with pass/fail
- [ ] Exit codes correct
- [ ] Documented in runbook

**Output**: 
- New file: `scripts/smoke_prod.sh` (if authorized)
- Documentation in `runbook_backup_restore.md`

---

### [ ] Step: Audit Report Assembly
<!-- Expected duration: 2 hours -->

**Objective**: Assemble comprehensive audit.md document from all analysis tasks.

**Actions**:
1. **Create document structure**:
   - Executive Summary
     - Current security posture
     - Critical findings summary
     - Priority recommendations
   
   - Django Deployment Check Results
     - Full output from check --deploy
     - Warnings classified by P0-P3
     - Resolution status for each
   
   - Security Headers Configuration
     - Current vs recommended state
     - Proposed nginx changes
     - Rationale for each header
     - Implementation guidance
   
   - Cookie Security Configuration
     - Current settings analysis
     - Production recommendations
     - Environment variables required
   
   - ALLOWED_HOSTS Configuration
     - Current validation
     - Configuration examples
     - Best practices
   
   - Volumes and Data Safety
     - Critical volumes identified
     - Backup requirements
     - Destruction warnings
   
   - Action Items
     - Prioritized list of changes
     - Owner/timeline recommendations
     - Risk assessment for each

2. **Quality checks**:
   - All sections complete
   - Cross-references accurate
   - Code examples correct
   - French language (matching existing docs)
   - Professional tone
   - No ambiguity

3. **Create summary checklist**:
   - Pre-deployment validation checklist
   - Post-deployment validation checklist
   - Security validation checklist

**Verification**:
- [ ] All analysis sections integrated
- [ ] Executive summary accurate
- [ ] Action items prioritized
- [ ] Document is comprehensive
- [ ] Ready for operational use

**Output**: Complete `audit.md`

---

### [ ] Step: Documentation Review and Validation
<!-- Expected duration: 1 hour -->

**Objective**: Review all deliverables for completeness, accuracy, and quality.

**Actions**:
1. **Validate audit.md**:
   - [ ] All sections complete
   - [ ] All warnings documented
   - [ ] Recommendations actionable
   - [ ] Cross-references valid
   - [ ] French language correct

2. **Validate runbook_backup_restore.md**:
   - [ ] Procedures reproducible
   - [ ] No ambiguous steps
   - [ ] Warnings clearly marked
   - [ ] Commands copy-paste ready
   - [ ] French language correct

3. **Validate smoke tests** (if created):
   - [ ] Scripts executable
   - [ ] Tests comprehensive
   - [ ] Documentation clear

4. **Cross-document consistency**:
   - [ ] audit.md references runbook correctly
   - [ ] runbook references audit for context
   - [ ] No conflicting recommendations
   - [ ] Consistent terminology

5. **Completeness check against requirements**:
   - [ ] FR-1: Django deployment audit → Complete
   - [ ] FR-2: Security headers configuration → Complete
   - [ ] FR-3: Cookie security → Complete
   - [ ] FR-4: Backup/restore procedures → Complete
   - [ ] FR-5: Smoke tests → Complete
   - [ ] FR-6: ALLOWED_HOSTS validation → Complete

**Verification**:
- [ ] All deliverables complete
- [ ] Quality standards met
- [ ] Ready for user review

**Output**: Final validation report

---

### [ ] Step: Optional Implementation (If Authorized)
<!-- Expected duration: 2-3 hours -->
<!-- NOTE: Only execute if user explicitly authorizes code changes -->

**Objective**: Implement minimal patch for production hardening based on audit findings.

**Scope** (pending user authorization):
1. **nginx.conf updates**:
   - Add HSTS header (conditional on HTTPS)
   - Add CSP header (aligned with Django CSP)
   - Add Permissions-Policy header

2. **settings_prod.py fixes**:
   - Address any P0 deployment warnings
   - Add any missing security settings

3. **smoke_prod.sh creation**:
   - Production smoke test script

4. **.env.prod.example updates**:
   - Add missing environment variables
   - Improve documentation

**Constraints**:
- ❌ No changes to core application logic
- ❌ No database migrations
- ❌ No breaking changes
- ✅ All changes backward compatible
- ✅ Changes must pass existing tests

**Verification**:
- [ ] User authorization obtained
- [ ] Changes align with audit recommendations
- [ ] No breaking changes introduced
- [ ] Existing tests pass
- [ ] Changes documented in audit.md

**Output**: Code patches (only if authorized)

---

## Success Criteria

### Documentation Deliverables
- [x] `requirements.md` - Comprehensive PRD (616 lines) ✅
- [ ] `audit.md` - Complete security audit report
- [ ] `runbook_backup_restore.md` - Operational runbook

### Technical Requirements
- [ ] Django `check --deploy` executed and all warnings documented
- [ ] All P0 warnings addressed or risk-accepted
- [ ] Security headers configuration proposed
- [ ] Cookie security validated
- [ ] Backup/restore procedures documented and tested
- [ ] Smoke tests enhanced (if authorized)

### Quality Standards
- [ ] All documentation in French
- [ ] No ambiguous steps in procedures
- [ ] All procedures reproducible
- [ ] Cross-references accurate
- [ ] Professional tone maintained

---

## Notes

### Environment Setup for Testing
```bash
# Run Django deployment check
cd backend
DJANGO_SETTINGS_MODULE=core.settings_prod python manage.py check --deploy

# Test existing smoke tests
./scripts/smoke.sh

# Test backup procedures
./scripts/backup_db.sh
python backend/manage.py backup

# Test restore procedures
python backend/manage.py restore --help
```

### Risk Mitigation
- Documentation-first approach minimizes risk
- No code changes without explicit authorization
- All procedures validated against existing tests
- Clear warnings for destructive operations

### Timeline Estimate
- **Documentation tasks**: 10-15 hours
- **Optional implementation**: 2-3 hours
- **Total**: 12-18 hours

---

## References
- Task description: ZF-AUD-12
- Requirements: `requirements.md`
- Django docs: https://docs.djangoproject.com/en/4.2/howto/deployment/checklist/
- OWASP Security Headers: https://owasp.org/www-project-secure-headers/
- Mozilla Observatory: https://observatory.mozilla.org/
