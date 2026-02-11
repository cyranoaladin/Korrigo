# Product Requirements Document (PRD)
# PORTAIL ÉLÈVE: AUTH (INE+DOB) + ACCÈS "MES COPIES" + DOWNLOAD PDF

**Task ID**: ZF-AUD-09  
**Version**: 1.0  
**Date**: 31 January 2026  
**Status**: Draft

---

## 1. Executive Summary

### 1.1 Objective
Conduct a comprehensive security audit and enhancement of the student portal authentication and data access system to ensure:
- **Zero unauthorized access** to student examination data
- **Simple and secure UX** for student authentication
- **Stable and reliable** service availability

### 1.2 Scope
This audit and enhancement covers three critical areas:
1. **Student Authentication**: Transition from INE+LastName to INE+DateOfBirth with anti-brute-force protection
2. **Copy Access Control**: Strict enforcement that students can only view their GRADED copies
3. **PDF Download Security**: Secure PDF delivery with proper cache control and direct link protection

### 1.3 Success Criteria
- ✅ Complete data isolation: Student A **never** sees data from Student B
- ✅ Status filtering: Students only see GRADED copies (not READY, LOCKED, or STAGING)
- ✅ Download protection: PDF downloads only allowed for GRADED copies owned by the requesting student
- ✅ Audit trail: All authentication attempts and data access logged
- ✅ Anti-brute-force: Rate limiting prevents credential attacks
- ✅ Generic error messages: No user enumeration via error messages
- ✅ Session security: Proper timeout, secure cookies, HTTPS enforcement

---

## 2. Current State Analysis

### 2.1 Existing Architecture

**Authentication Method** (ADR-001):
- Session-based authentication (no Django User for students)
- Current credentials: `INE` + `last_name` (case-insensitive)
- Session timeout: 4 hours
- Session storage: Django sessions framework

**Authorization Pattern**:
- Custom permission class: `IsStudent`
- Session key: `request.session['student_id']`
- No privilege escalation possible to Django admin

**Existing Endpoints**:
```
POST   /api/students/login/          # Current: INE + last_name
POST   /api/students/logout/         # Session cleanup
GET    /api/students/me/             # Student profile
GET    /api/students/copies/         # List student's GRADED copies
GET    /api/grading/copies/{id}/final-pdf/  # Download PDF
```

**Current Security Measures**:
- ✅ Rate limiting on login: `5/15m` per IP (students/views.py:26)
- ✅ CSRF exemption on public login endpoint (appropriate for session-based auth)
- ✅ Audit logging for authentication attempts (students/views.py:41)
- ✅ Copy status filtering: Only GRADED copies visible (exams/views.py:371)
- ✅ PDF download gating: Status check + ownership check (grading/views.py:223-259)
- ✅ AllowAny permission with manual dual auth (teachers OR students)

### 2.2 Identified Gaps

**Authentication**:
1. **CRITICAL**: Using `last_name` instead of `date_of_birth` (easier to guess/enumerate)
2. **MEDIUM**: Error messages may reveal user enumeration ("Identifiants invalides" is generic - GOOD)
3. **LOW**: Session fixation protection needs verification

**Access Control**:
1. **VERIFY**: Ensure READY/LOCKED copies are truly filtered (current code looks good)
2. **VERIFY**: Ensure other students' GRADED copies are not accessible

**PDF Download**:
1. **MISSING**: Cache-Control headers for PDF responses (prevent browser caching of sensitive data)
2. **MISSING**: Content-Disposition header (force download, prevent inline rendering in browser)
3. **VERIFY**: Direct URL access protection (no token in URL)

**Audit & Monitoring**:
1. **GOOD**: Authentication attempts logged
2. **MISSING**: Data access logging for copy list and PDF downloads (partially implemented)
3. **MISSING**: Failed authentication alerts/monitoring

---

## 3. Requirements

### 3.1 Functional Requirements

#### FR1: Student Authentication with INE + Date of Birth

**FR1.1**: Change login credentials
- **Current**: `POST /api/students/login/ {"ine": "...", "last_name": "..."}`
- **Required**: `POST /api/students/login/ {"ine": "...", "birth_date": "YYYY-MM-DD"}`
- **Validation**:
  - `ine`: Required, 11 characters (10 digits + 1 letter), alphanumeric
  - `birth_date`: Required, ISO 8601 format (YYYY-MM-DD), must be a valid date
  - Date range: Must be between 1990-01-01 and current date minus 10 years (students must be at least 10 years old)

**FR1.2**: Database schema update
- Add `birth_date` field to `Student` model (backend/students/models.py)
- Type: `DateField`
- Required: `null=False, blank=False` (after migration)
- Migration strategy: Allow null temporarily, populate from external data source (Pronote/SCONET), then enforce NOT NULL

**FR1.3**: Backward compatibility
- **Decision**: NO backward compatibility with `last_name` authentication
- **Rationale**: Security improvement, clean break
- **Migration**: All students must use INE + birth_date after deployment

#### FR2: "Mes Copies" Access Control

**FR2.1**: List student's copies
- **Endpoint**: `GET /api/students/copies/`
- **Filter criteria** (strict):
  - `student_id` matches session `student_id`
  - `status` = `GRADED` (exclude STAGING, READY, LOCKED, GRADING_IN_PROGRESS, GRADING_FAILED)
- **Response fields**:
  ```json
  [
    {
      "id": "uuid",
      "exam_name": "Bac Blanc Maths TG",
      "date": "2026-01-15",
      "total_score": 15.5,
      "status": "GRADED",
      "final_pdf_url": "/api/grading/copies/{id}/final-pdf/",
      "scores_details": {}
    }
  ]
  ```

**FR2.2**: Isolation verification
- **Test case 1**: Student A logs in → sees only their GRADED copies
- **Test case 2**: Student A cannot see Student B's GRADED copies
- **Test case 3**: Student A cannot see their own READY/LOCKED copies
- **Test case 4**: Unauthenticated request → 401 Unauthorized

#### FR3: PDF Download Security

**FR3.1**: Download restrictions
- **Endpoint**: `GET /api/grading/copies/{id}/final-pdf/`
- **Security gates** (already implemented, needs verification):
  1. **Status gate**: `copy.status == GRADED` → else 403 Forbidden
  2. **Ownership gate**: 
     - Teachers/Admins: Allowed (Django authenticated + staff/teacher group)
     - Students: `copy.student_id == session['student_id']` → else 403 Forbidden
  3. **Authentication gate**: Student session or Django auth → else 401 Unauthorized

**FR3.2**: HTTP headers for security
- **Cache-Control**: `private, no-store, no-cache, must-revalidate, max-age=0`
  - Rationale: Prevent browser/proxy caching of sensitive student data
- **Content-Disposition**: `attachment; filename="copy_{anonymous_id}.pdf"`
  - Rationale: Force download instead of inline display (prevents accidental sharing via browser history)
- **X-Content-Type-Options**: `nosniff`
  - Rationale: Prevent MIME type sniffing attacks

**FR3.3**: Direct link protection
- **Current**: URL is `/api/grading/copies/{uuid}/final-pdf/` (no token required)
- **Decision**: Keep current approach (session-based authentication is sufficient)
- **Rationale**: 
  - Session cookie provides implicit authentication
  - UUID is not guessable
  - Ownership check prevents cross-student access
  - HTTPS prevents session hijacking
- **Alternative considered**: Signed URLs with expiry (REJECTED - adds complexity without significant security gain for session-based auth)

### 3.2 Non-Functional Requirements

#### NFR1: Security

**NFR1.1**: Anti-brute-force protection
- **Current**: 5 login attempts per 15 minutes per IP
- **Enhancement**: Add per-user rate limiting (5 attempts per 15 minutes per INE)
- **Implementation**: Django-ratelimit with composite key `ip_or_user`
- **Lockout behavior**: Temporary (15 min), not permanent
- **Error message**: Generic "Identifiants invalides" (no user enumeration)

**NFR1.2**: Error message policy
- **All authentication failures**: Return same message "Identifiants invalides"
- **Scenarios**:
  - Invalid INE: "Identifiants invalides"
  - Invalid birth_date: "Identifiants invalides"
  - Non-existent student: "Identifiants invalides"
  - Rate-limited: "Trop de tentatives. Réessayez dans 15 minutes."
- **Rationale**: Prevent user enumeration attacks

**NFR1.3**: Session security
- **Session timeout**: 4 hours (current, appropriate for student consultation)
- **Session cookie settings**:
  - `SESSION_COOKIE_HTTPONLY = True` (prevent XSS)
  - `SESSION_COOKIE_SECURE = True` (HTTPS only, production)
  - `SESSION_COOKIE_SAMESITE = 'Lax'` (CSRF protection)
- **Session fixation protection**: Django default (regenerate on login)

**NFR1.4**: HTTPS enforcement
- **Production**: Mandatory (nginx reverse proxy, SSL_ENABLED=true)
- **Development**: Optional (docker-compose.yml, port 8088)
- **Verification**: `SECURE_SSL_REDIRECT = True` in production settings

#### NFR2: Audit & Compliance

**NFR2.1**: Audit trail requirements
- **Event types** to log:
  1. `student.login.success` → (timestamp, student_id, IP, user_agent)
  2. `student.login.failure` → (timestamp, ine_attempted, IP, user_agent)
  3. `student.login.ratelimit` → (timestamp, ine_attempted, IP)
  4. `student.logout` → (timestamp, student_id, IP)
  5. `copy.list` → (timestamp, student_id, num_copies_returned)
  6. `copy.download` → (timestamp, student_id, copy_id, exam_name)
- **Storage**: Django model `AuditLog` (existing: core/utils/audit.py)
- **Retention**: 1 year (GDPR compliance, educational records)

**NFR2.2**: RGPD compliance
- **Data minimization**: Only collect INE + birth_date (no sensitive data)
- **Purpose limitation**: Authentication only
- **Student rights**:
  - Right to access: `/api/students/me/` shows profile
  - Right to rectification: Admin can update birth_date via Django admin
  - Right to erasure: Student deletion cascade to audit logs (SET_NULL on audit)
- **Parental consent**: Required for minors (<18 years) - documented in POLITIQUE_RGPD.md

#### NFR3: Performance & Availability

**NFR3.1**: Response time
- **Login endpoint**: < 200ms (p95)
- **Copy list endpoint**: < 500ms (p95)
- **PDF download**: < 2s for 5MB PDF (p95)

**NFR3.2**: Availability
- **Target**: 99.5% uptime during exam consultation periods
- **Downtime**: Scheduled maintenance outside peak hours (weekends)

**NFR3.3**: Scalability
- **Expected load**: 500 students, 10 concurrent logins, 50 concurrent PDF downloads
- **Database**: PostgreSQL with indexes on `student.ine`, `copy.student_id`, `copy.status`

---

## 4. Assumptions & Constraints

### 4.1 Assumptions

1. **Birth date data availability**: All students have birth_date in external system (Pronote/SCONET export)
2. **Student communication**: Establishment will communicate new login credentials (INE + birth_date) to students/parents
3. **No password reset**: Students contact school administration for credential issues (no self-service password reset - by design, no passwords)
4. **Browser compatibility**: Modern browsers (Chrome 90+, Firefox 88+, Safari 14+, Edge 90+)
5. **Network**: Students access portal from school network or home (no VPN required)

### 4.2 Constraints

1. **No Django User for students**: ADR-001 decision (session-only, no User model)
2. **No QR codes**: Manual identification workflow (ADR-001)
3. **Local deployment**: No cloud dependencies (local server or private cloud)
4. **Python 3.9 + Django 4.2 LTS**: No framework changes
5. **Backward compatibility**: INE field name cannot change (used in Pronote export)

### 4.3 Out of Scope

- ❌ Password-based authentication (by design)
- ❌ Email notifications for login
- ❌ Multi-factor authentication (MFA)
- ❌ Student self-registration
- ❌ Student profile editing (admin-only)
- ❌ PDF watermarking (future enhancement)
- ❌ Copy comparison/plagiarism detection

---

## 5. User Stories

### 5.1 Student Authentication

**US1**: As a **student**, I want to log in with my INE and birth date, so that I can securely access my graded copies.

**Acceptance Criteria**:
- Given I have valid INE "1234567890A" and birth_date "2005-03-15"
- When I submit login form
- Then I am authenticated and redirected to "Mes Copies" page
- And my session expires after 4 hours of inactivity

**US2**: As a **student**, I want to see a generic error message when login fails, so that attackers cannot enumerate student accounts.

**Acceptance Criteria**:
- Given I enter invalid INE or birth_date
- When I submit login form
- Then I see "Identifiants invalides" (same message for all error types)
- And no hint about which field was incorrect

**US3**: As a **student**, I want to be temporarily locked out after too many failed attempts, so that my account is protected from brute-force attacks.

**Acceptance Criteria**:
- Given I have failed login 5 times in 15 minutes
- When I attempt 6th login
- Then I see "Trop de tentatives. Réessayez dans 15 minutes."
- And I cannot log in even with correct credentials for 15 minutes
- And after 15 minutes, I can try again

### 5.2 Copy Access

**US4**: As a **student**, I want to see only my GRADED copies, so that I don't see incomplete corrections or other students' work.

**Acceptance Criteria**:
- Given I am logged in
- When I access "Mes Copies" page
- Then I see list of my copies where status = GRADED
- And I do NOT see copies in READY, LOCKED, or STAGING status
- And I do NOT see other students' copies (even if GRADED)

**US5**: As a **student**, I want to download my graded copy PDF, so that I can review my exam offline.

**Acceptance Criteria**:
- Given I am logged in
- And I have a GRADED copy
- When I click "Télécharger PDF"
- Then PDF downloads to my device
- And PDF is named "copy_{anonymous_id}.pdf"
- And PDF is not cached by browser (secure headers)

**US6**: As a **student**, I should NOT be able to download copies that are not mine or not graded.

**Acceptance Criteria**:
- Given I am logged in as Student A
- When I try to access Student B's PDF URL directly
- Then I receive 403 Forbidden error
- And when I try to access my own READY/LOCKED copy PDF
- Then I receive 403 Forbidden error

### 5.3 Security & Audit

**US7**: As a **security administrator**, I want all authentication attempts logged, so that I can detect attack patterns.

**Acceptance Criteria**:
- Given any login attempt (success or failure)
- When authentication occurs
- Then audit log records: timestamp, INE (if provided), IP, user_agent, success/failure
- And logs are retained for 1 year
- And logs are queryable via Django admin

**US8**: As a **security administrator**, I want all PDF downloads logged, so that I can track data access for compliance.

**Acceptance Criteria**:
- Given a student downloads a PDF
- When download occurs
- Then audit log records: timestamp, student_id, copy_id, exam_name, IP
- And logs are retained for 1 year

---

## 6. Technical Decisions & Clarifications

### 6.1 Key Decisions

**Decision 1**: Use `birth_date` instead of `last_name`
- **Rationale**: 
  - Birth date is harder to enumerate than last name
  - Birth date is stable (never changes, unlike name after marriage)
  - Birth date is already in school records (Pronote/SCONET)
- **Trade-off**: Requires data migration and student communication
- **Approved**: Yes (task requirement)

**Decision 2**: No signed URLs for PDF download
- **Rationale**: Session-based auth + ownership check is sufficient
- **Trade-off**: Direct URL sharing within session window (acceptable for 4h timeout)
- **Alternative considered**: Time-limited signed URLs (REJECTED - over-engineering)
- **Approved**: Yes (maintain current architecture)

**Decision 3**: Generic error messages for all auth failures
- **Rationale**: Prevent user enumeration attacks
- **Trade-off**: Slightly worse UX (student doesn't know which field is wrong)
- **Approved**: Yes (security > convenience)

**Decision 4**: Rate limiting by IP + INE (composite)
- **Rationale**: Prevent both distributed attacks (IP-based) and targeted attacks (INE-based)
- **Implementation**: Django-ratelimit with custom key function
- **Approved**: Yes (best practice)

### 6.2 Open Questions (for User Clarification)

**Q1**: Birth date format for students
- **Question**: Should students enter birth date as "DD/MM/YYYY" (European format) or "YYYY-MM-DD" (ISO)?
- **Recommendation**: Accept both formats, normalize to ISO on backend
- **User decision required**: Frontend UX format preference
- **Assumption if no answer**: Use European format "DD/MM/YYYY" in UI, convert to ISO 8601 for API

**Q2**: Migration strategy for existing students
- **Question**: Do all students already have `birth_date` in current database?
- **Scenario A**: Yes → Simple migration, add NOT NULL constraint immediately
- **Scenario B**: No → Need import from Pronote/SCONET before deployment
- **Assumption if no answer**: Scenario B (safer) - import required

**Q3**: Error message for rate limiting
- **Question**: Should rate-limited students see countdown timer ("Réessayez dans 12 minutes") or generic message ("Réessayez plus tard")?
- **Recommendation**: Generic message (no timing leak)
- **Assumption if no answer**: Generic "Réessayez dans 15 minutes" (no real-time countdown)

**Q4**: PDF download behavior
- **Question**: Should PDF open in new tab or force download?
- **Current**: `Content-Disposition: attachment` forces download
- **Alternative**: `inline` opens in browser
- **Assumption if no answer**: Force download (more secure, prevents accidental sharing via browser history)

---

## 7. Success Metrics

### 7.1 Security Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Zero cross-student data leaks | 100% (0 violations) | E2E test suite, security audit |
| Authentication attempts logged | 100% | Audit log coverage |
| PDF downloads logged | 100% | Audit log coverage |
| Rate limiting effectiveness | Block >90% brute-force attempts | Simulated attack test |
| Session timeout compliance | 100% (exactly 4h) | Functional test |

### 7.2 Functional Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Login success rate (valid credentials) | >99% | Production monitoring |
| Copy list accuracy (only GRADED, owned) | 100% | E2E test suite |
| PDF download success (valid requests) | >99.5% | Production monitoring |
| PDF download rejection (invalid requests) | 100% (403/401) | Security test suite |

### 7.3 Compliance Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| RGPD audit compliance | 100% | Legal review |
| Audit log retention | 1 year | Database query |
| Student data minimization | INE + birth_date only | Data model review |

---

## 8. Dependencies & Risks

### 8.1 Dependencies

1. **Student birth_date data source**: Pronote/SCONET export CSV with INE + birth_date
2. **Student communication**: Establishment sends email/letter to students with new login instructions
3. **Testing environment**: Populated test database with realistic student data (anonymized)
4. **Deployment window**: Scheduled maintenance for migration (2-hour window)

### 8.2 Risks & Mitigation

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| **Missing birth_date data** | High (students cannot log in) | Medium | Pre-deployment validation, import script with error reporting |
| **Student confusion** (new credentials) | Medium (support calls) | High | Clear communication, help desk prepared, FAQ document |
| **Session fixation vulnerability** | High (security breach) | Low | Django default protection, verify in security test |
| **Race condition** (concurrent PDF downloads) | Low (performance) | Low | FileResponse handles concurrency well |
| **Brute-force bypass** (distributed IPs) | Medium (account compromise) | Medium | IP + INE composite rate limiting |

---

## 9. Deliverables

### 9.1 Code Changes

1. **Database migration**: Add `birth_date` field to `Student` model
2. **API endpoint update**: Change `StudentLoginView` to accept `birth_date` instead of `last_name`
3. **Rate limiting enhancement**: Composite key (IP + INE)
4. **PDF response headers**: Add `Cache-Control`, `Content-Disposition`, `X-Content-Type-Options`
5. **Audit logging**: Enhance existing logs for copy list and PDF download

### 9.2 Tests

1. **Unit tests**: `StudentLoginView` with birth_date validation
2. **Integration tests**: End-to-end student authentication flow
3. **Security tests**: 
   - Cross-student data access attempts (expect 403)
   - Non-GRADED copy access attempts (expect 403)
   - Direct PDF URL access without session (expect 401)
   - Brute-force attack simulation (expect rate limiting)
4. **E2E tests** (Playwright): Full workflow from login to PDF download

### 9.3 Documentation

1. **audit.md**: Security audit report (findings, recommendations, resolutions)
2. **API documentation update**: `/api/students/login/` with new `birth_date` parameter
3. **User guide**: Student portal login instructions (French)
4. **Admin guide**: Birth date import procedure

### 9.4 Deployment

1. **Migration script**: Import birth_date from Pronote CSV
2. **Database backup**: Pre-deployment backup (critical)
3. **Rollback plan**: Restore backup + revert migration if critical failure
4. **Smoke tests**: Post-deployment validation (20 test students)

---

## 10. Approval & Sign-off

| Role | Name | Approval | Date |
|------|------|----------|------|
| Product Owner | [TBD] | ☐ Approved ☐ Rejected | [Date] |
| Security Lead | [TBD] | ☐ Approved ☐ Rejected | [Date] |
| Tech Lead | [TBD] | ☐ Approved ☐ Rejected | [Date] |
| DPO (RGPD) | [TBD] | ☐ Approved ☐ Rejected | [Date] |

---

## Appendix A: API Contract Changes

### Before (Current)
```http
POST /api/students/login/
Content-Type: application/json

{
  "ine": "1234567890A",
  "last_name": "Dupont"
}
```

### After (Required)
```http
POST /api/students/login/
Content-Type: application/json

{
  "ine": "1234567890A",
  "birth_date": "2005-03-15"
}
```

**Response (unchanged)**:
```json
{
  "message": "Login successful",
  "role": "Student"
}
```

**Error responses**:
```json
{
  "error": "Identifiants invalides."
}
```
```json
{
  "error": "Trop de tentatives. Réessayez dans 15 minutes."
}
```

---

## Appendix B: Database Schema Changes

```python
# students/models.py
class Student(models.Model):
    ine = models.CharField(max_length=50, unique=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    class_name = models.CharField(max_length=50)
    email = models.EmailField(blank=True, null=True)
    
    # NEW FIELD
    birth_date = models.DateField(
        verbose_name="Date de naissance",
        help_text="Format: YYYY-MM-DD",
        null=False,  # After migration
        blank=False
    )
```

**Migration checklist**:
1. Add field with `null=True` temporarily
2. Import birth_date from Pronote CSV
3. Validate all students have birth_date
4. Set `null=False` in second migration
5. Deploy code changes

---

## Appendix C: Security Headers Reference

```python
# grading/views.py - CopyFinalPdfView
response = FileResponse(copy.final_pdf.open('rb'), content_type='application/pdf')
response['Content-Disposition'] = f'attachment; filename="copy_{copy.anonymous_id}.pdf"'
response['Cache-Control'] = 'private, no-store, no-cache, must-revalidate, max-age=0'
response['Pragma'] = 'no-cache'
response['Expires'] = '0'
response['X-Content-Type-Options'] = 'nosniff'
return response
```

---

**End of PRD**
