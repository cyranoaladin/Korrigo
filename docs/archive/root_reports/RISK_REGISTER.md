# Korrigo Risk Register

## Document Information
- **Version**: 1.0
- **Date**: 2026-02-02
- **Owner**: DevOps Team

---

## Risk Matrix

| ID | Risk | Probability | Impact | Severity | Mitigation | Owner | Status |
|----|------|-------------|--------|----------|------------|-------|--------|
| R01 | Database data loss | Low | Critical | High | Daily backups to external storage, tested restore procedure | DevOps | Mitigated |
| R02 | Unauthorized access to student data | Low | Critical | High | Rate limiting, strong passwords, session management, HTTPS only | Security | Mitigated |
| R03 | Service unavailability during exams | Medium | High | High | Health checks, auto-restart, monitoring alerts | DevOps | Mitigated |
| R04 | PDF processing failure | Medium | Medium | Medium | Validation on upload, error handling, manual retry option | Backend | Mitigated |
| R05 | Concurrent editing conflicts | Low | Medium | Low | Soft lock mechanism with heartbeat, conflict detection | Backend | Mitigated |
| R06 | A3 scan format not auto-processed | High | Medium | Medium | Pre-processing script documented in runbook | Backend | Accepted |
| R07 | OCR identification errors | Medium | Low | Low | Manual validation required, OCR is assistance only | Backend | Accepted |
| R08 | Lock expiration during correction | Low | Medium | Low | Draft autosave to localStorage, restore on reconnect | Frontend | Mitigated |

---

## Risk Details

### R01: Database Data Loss
**Description**: PostgreSQL database corruption or accidental deletion.

**Mitigation**:
- Daily automated backups via `pg_dump`
- Backup retention: 30 days
- Tested restore procedure documented in PROD_RUNBOOK.md
- Docker volume persistence

**Residual Risk**: Low - backups tested and verified.

---

### R02: Unauthorized Access
**Description**: Malicious access to student grades or personal data.

**Mitigation**:
- Rate limiting: 5 requests/15min on login
- Strong password policy (12+ chars in production)
- Session-based authentication with CSRF protection
- HTTPS enforced via nginx
- Security headers (XFO, CSP, X-XSS-Protection)

**Residual Risk**: Low - multiple layers of protection.

---

### R03: Service Unavailability
**Description**: System downtime during critical exam periods.

**Mitigation**:
- Docker health checks on all services
- Auto-restart policy in Docker Compose
- Monitoring via health endpoints
- Documented restart procedures

**Residual Risk**: Medium - single-server deployment, no HA.

---

### R04: PDF Processing Failure
**Description**: Uploaded PDF cannot be processed (corrupt, wrong format).

**Mitigation**:
- PDF validation on upload (size, page count, format)
- Graceful error handling with user-friendly messages
- Manual retry option
- Logs for debugging

**Residual Risk**: Low - validation catches most issues.

---

### R05: Concurrent Editing Conflicts
**Description**: Two correctors editing the same copy simultaneously.

**Mitigation**:
- Soft lock mechanism with 5-minute TTL
- Heartbeat to maintain lock
- Conflict detection on save
- Read-only mode for non-lock holders

**Residual Risk**: Low - mechanism tested and functional.

---

### R06: A3 Scan Format Not Auto-Processed
**Description**: A3 recto-verso scans require manual pre-processing.

**Current State**:
- `A3Splitter` service exists but not integrated in upload workflow
- Pre-processing script documented in runbook

**Mitigation**:
- Document pre-processing steps in PROD_RUNBOOK.md
- Provide command-line tools for operators

**Residual Risk**: Medium - requires operator training.

**Future Improvement**: Integrate A3Splitter in automatic upload pipeline.

---

### R07: OCR Identification Errors
**Description**: OCR may misread student names/IDs.

**Mitigation**:
- OCR is assistance only, not authoritative
- Manual validation required for all identifications
- Clear UI showing OCR suggestions vs confirmed data

**Residual Risk**: Low - human validation is mandatory.

---

### R08: Lock Expiration During Correction
**Description**: Corrector loses work if lock expires mid-session.

**Mitigation**:
- Autosave to localStorage every 30 seconds
- Draft restoration modal on page reload
- Heartbeat maintains lock while active
- Clear UI indication of lock status

**Residual Risk**: Low - drafts are preserved locally.

---

## Accepted Risks

| ID | Risk | Reason for Acceptance |
|----|------|----------------------|
| R06 | A3 scan pre-processing | Documented workaround exists, full automation is P2 feature |
| R07 | OCR errors | By design - OCR is assistance, not replacement for human judgment |

---

## Review Schedule

- **Monthly**: Review all risks and update status
- **After incidents**: Add new risks identified
- **Before major releases**: Full risk assessment

---

*Last updated: 2026-02-02*
