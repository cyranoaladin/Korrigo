# Full SDD workflow

## Configuration
- **Artifacts Path**: {@artifacts_path} → `.zenflow/tasks/{task_id}`

---

## Workflow Steps

### [x] Step: Requirements
<!-- chat-id: b614db07-bb4d-4961-a375-eb72d4d47e27 -->

Create a Product Requirements Document (PRD) based on the feature description.

1. Review existing codebase to understand current architecture and patterns
2. Analyze the feature definition and identify unclear aspects
3. Ask the user for clarifications on aspects that significantly impact scope or user experience
4. Make reasonable decisions for minor details based on context and conventions
5. If user can't clarify, make a decision, state the assumption, and continue

Save the PRD to `{@artifacts_path}/requirements.md`.

### [ ] Step: Technical Specification
<!-- chat-id: b13dfe28-9040-45b8-914b-57829922e194 -->

Create a technical specification based on the PRD in `{@artifacts_path}/requirements.md`.

1. Review existing codebase architecture and identify reusable components
2. Define the implementation approach

Save to `{@artifacts_path}/spec.md` with:
- Technical context (language, dependencies)
- Implementation approach referencing existing code patterns
- Source code structure changes
- Data model / API / interface changes
- Delivery phases (incremental, testable milestones)
- Verification approach using project lint/test commands

### [x] Step: Planning
<!-- chat-id: 730dd87a-3c8d-487f-8505-afbf3f4f605e -->

Create a detailed implementation plan based on `{@artifacts_path}/spec.md`.

1. Break down the work into concrete tasks
2. Each task should reference relevant contracts and include verification steps
3. Replace the Implementation step below with the planned tasks

Rule of thumb for step size: each step should represent a coherent unit of work (e.g., implement a component, add an API endpoint, write tests for a module). Avoid steps that are too granular (single function) or too broad (entire feature).

If the feature is trivial and doesn't warrant full specification, update this workflow to remove unnecessary steps and explain the reasoning to the user.

Save to `{@artifacts_path}/plan.md`.

---

## Implementation Steps

### [ ] Step: Database Migration - Add birth_date field

**Objective**: Add `birth_date` field to Student model and create migration

**Tasks**:
- [ ] Review current Student model in `backend/students/models.py`
- [ ] Add `birth_date` field as `DateField(null=True, blank=True)` (temporary, for migration)
- [ ] Add field validation: verbose_name, help_text
- [ ] Create Django migration: `python manage.py makemigrations students`
- [ ] Review generated migration file

**Verification**:
- Migration file created without errors
- Field added with correct type and constraints

**Files modified**:
- `backend/students/models.py`
- `backend/students/migrations/000X_add_birth_date.py` (new)

---

### [ ] Step: Update Student Serializer and Login Logic

**Objective**: Replace `last_name` with `birth_date` in login endpoint

**Tasks**:
- [ ] Review `backend/students/serializers.py` for login serializer
- [ ] Update login serializer: replace `last_name` field with `birth_date` field
- [ ] Add birth_date validation: ISO format (YYYY-MM-DD), date range (1990-01-01 to current_date - 10 years)
- [ ] Update `StudentLoginView` in `backend/students/views.py`
- [ ] Change authentication logic: `iexact` lookup on `ine` + exact match on `birth_date`
- [ ] Ensure generic error message: "Identifiants invalides" for all failure cases

**Verification**:
- Serializer validates birth_date correctly
- Login logic authenticates with INE + birth_date
- Error messages are generic (no user enumeration)

**Files modified**:
- `backend/students/serializers.py`
- `backend/students/views.py`

---

### [ ] Step: Enhance Rate Limiting with Composite Key

**Objective**: Add per-INE rate limiting in addition to per-IP

**Tasks**:
- [ ] Review current rate limiting in `StudentLoginView` (students/views.py:26)
- [ ] Create custom rate limit key function: composite of IP + INE from request body
- [ ] Update `@ratelimit` decorator to use composite key
- [ ] Ensure rate limit error message: "Trop de tentatives. Réessayez dans 15 minutes."
- [ ] Test edge cases: missing INE in body, malformed requests

**Verification**:
- Rate limiting works per IP (existing)
- Rate limiting works per INE (new)
- Combined protection prevents distributed attacks on single INE

**Files modified**:
- `backend/students/views.py`

---

### [ ] Step: Add Security Headers to PDF Download

**Objective**: Add Cache-Control and Content-Disposition headers to PDF responses

**Tasks**:
- [ ] Review `CopyFinalPdfView` in `backend/grading/views.py`
- [ ] Add `Cache-Control: private, no-store, no-cache, must-revalidate, max-age=0`
- [ ] Add `Pragma: no-cache`
- [ ] Add `Expires: 0`
- [ ] Add `X-Content-Type-Options: nosniff`
- [ ] Verify `Content-Disposition: attachment` already exists or add it
- [ ] Use filename pattern: `copy_{anonymous_id}.pdf`

**Verification**:
- PDF download response includes all security headers
- Browser does not cache PDF
- PDF downloads instead of displaying inline

**Files modified**:
- `backend/grading/views.py`

---

### [ ] Step: Enhance Audit Logging

**Objective**: Add comprehensive audit logging for student authentication and data access

**Tasks**:
- [ ] Review existing audit logging in `backend/core/utils/audit.py` (if exists) or create utility
- [ ] Ensure login success events logged: timestamp, student_id, IP, user_agent
- [ ] Ensure login failure events logged: timestamp, ine_attempted, IP, user_agent, reason
- [ ] Ensure rate limit events logged: timestamp, ine_attempted, IP
- [ ] Add audit logging to copy list view: timestamp, student_id, num_copies_returned
- [ ] Add audit logging to PDF download: timestamp, student_id, copy_id, exam_name, IP
- [ ] Verify audit logs use existing AuditLog model or create if needed

**Verification**:
- All authentication events logged
- All data access events logged
- Logs include required fields per requirements (NFR2.1)

**Files modified**:
- `backend/students/views.py`
- `backend/exams/views.py` (copy list endpoint)
- `backend/grading/views.py`
- `backend/core/utils/audit.py` (potentially new)

---

### [ ] Step: Unit Tests for Authentication

**Objective**: Write unit tests for updated login logic with birth_date

**Tasks**:
- [ ] Review existing test structure in `backend/students/tests/` or create directory
- [ ] Create/update `test_authentication.py`
- [ ] Test case: Valid INE + valid birth_date → login success
- [ ] Test case: Valid INE + invalid birth_date → login failure with generic error
- [ ] Test case: Invalid INE + valid birth_date → login failure with generic error
- [ ] Test case: Birth date validation - invalid format (DD/MM/YYYY) → validation error
- [ ] Test case: Birth date validation - future date → validation error
- [ ] Test case: Birth date validation - too recent (< 10 years ago) → validation error
- [ ] Test case: Session created on successful login
- [ ] Test case: Rate limiting - 6th attempt blocked with specific error message

**Verification**:
- Run `pytest backend/students/tests/test_authentication.py -v`
- All tests pass

**Files modified**:
- `backend/students/tests/test_authentication.py` (new or updated)

---

### [ ] Step: Integration Tests for Copy Access Control

**Objective**: Test that students only see their own GRADED copies

**Tasks**:
- [ ] Review existing test structure in `backend/exams/tests/` or create directory
- [ ] Create/update `test_copy_access.py`
- [ ] Test case: Student A logs in → list copies → sees only Student A's GRADED copies
- [ ] Test case: Student A's copy list excludes READY, LOCKED, STAGING statuses
- [ ] Test case: Student A cannot access Student B's copy via direct API call (403)
- [ ] Test case: Unauthenticated request to copy list → 401 Unauthorized
- [ ] Create test fixtures: 2 students with various copy statuses

**Verification**:
- Run `pytest backend/exams/tests/test_copy_access.py -v`
- All tests pass

**Files modified**:
- `backend/exams/tests/test_copy_access.py` (new or updated)
- `backend/exams/tests/fixtures.py` (potentially new for test data)

---

### [ ] Step: Security Tests for PDF Download

**Objective**: Test PDF download security gates (status, ownership, authentication)

**Tasks**:
- [ ] Review existing test structure in `backend/grading/tests/` or create directory
- [ ] Create/update `test_pdf_security.py`
- [ ] Test case: Student A downloads own GRADED copy → 200 OK with PDF
- [ ] Test case: Student A tries to download Student B's GRADED copy → 403 Forbidden
- [ ] Test case: Student A tries to download own READY copy → 403 Forbidden
- [ ] Test case: Student A tries to download own LOCKED copy → 403 Forbidden
- [ ] Test case: Unauthenticated request to PDF download → 401 Unauthorized
- [ ] Test case: Verify response headers (Cache-Control, Content-Disposition, etc.)
- [ ] Create test fixtures: students, copies with different statuses

**Verification**:
- Run `pytest backend/grading/tests/test_pdf_security.py -v`
- All tests pass

**Files modified**:
- `backend/grading/tests/test_pdf_security.py` (new or updated)
- `backend/grading/tests/fixtures.py` (potentially new for test data)

---

### [ ] Step: E2E Tests with Playwright

**Objective**: Test complete student workflow from login to PDF download

**Tasks**:
- [ ] Review existing E2E test structure (look for `playwright`, `e2e`, or `frontend/tests/`)
- [ ] Create E2E test file: `e2e/student_portal.spec.ts` (or .js)
- [ ] Test case: Full workflow - login with INE+birth_date → see copy list → download PDF
- [ ] Test case: Login failure - invalid credentials → see error message
- [ ] Test case: Rate limiting - 6 failed attempts → see rate limit message
- [ ] Test case: Cross-student isolation - Student A cannot see Student B's data
- [ ] Configure test environment with seed data (test students, copies)

**Verification**:
- Run `npm run test:e2e` (or equivalent command from package.json)
- All E2E tests pass

**Files modified**:
- `e2e/student_portal.spec.ts` (new)
- `e2e/fixtures/student_data.json` (potentially new for seed data)

---

### [ ] Step: Security Audit Report

**Objective**: Create comprehensive audit.md documenting findings and resolutions

**Tasks**:
- [ ] Create `audit.md` in artifacts folder
- [ ] Document audit scope: authentication, access control, PDF download
- [ ] Document findings:
  - Finding 1: last_name → birth_date migration (CRITICAL)
  - Finding 2: Rate limiting enhancement (MEDIUM)
  - Finding 3: PDF security headers (MEDIUM)
  - Finding 4: Audit logging gaps (LOW)
- [ ] Document test results: unit, integration, security, E2E
- [ ] Document resolutions: code changes, verification steps
- [ ] Document remaining risks and recommendations
- [ ] Include compliance section: RGPD, data minimization, audit retention

**Verification**:
- Audit report covers all requirements from task description
- All test results documented
- Report is comprehensive and actionable

**Files modified**:
- `.zenflow/tasks/portail-eleve-auth-ine-dob-acces-6a41/audit.md` (new)

---

### [ ] Step: Data Migration Script

**Objective**: Create script to populate birth_date from external data source

**Tasks**:
- [ ] Create `backend/students/management/commands/import_birth_dates.py`
- [ ] Implement CSV import: read INE + birth_date from Pronote/SCONET export
- [ ] Validate data: check date format, date range
- [ ] Update Student records: match by INE, set birth_date
- [ ] Error handling: log missing students, invalid dates, duplicate INEs
- [ ] Dry-run mode: preview changes without committing
- [ ] Create example CSV format documentation

**Verification**:
- Run command in dry-run mode: `python manage.py import_birth_dates --dry-run sample.csv`
- Verify output shows correct matching and validation
- Run command with real data: `python manage.py import_birth_dates sample.csv`
- Verify all students have birth_date populated

**Files modified**:
- `backend/students/management/commands/import_birth_dates.py` (new)
- `backend/students/management/commands/__init__.py` (potentially new)

---

### [ ] Step: Finalize Database Migration

**Objective**: Make birth_date field required after data import

**Tasks**:
- [ ] Verify all Student records have birth_date populated (query database)
- [ ] Update Student model: change `birth_date` to `null=False, blank=False`
- [ ] Create second migration: `python manage.py makemigrations students`
- [ ] Review migration: should alter column to NOT NULL
- [ ] Apply migrations: `python manage.py migrate`
- [ ] Verify schema: `python manage.py sqlmigrate students 000X`

**Verification**:
- All migrations applied successfully
- Database schema enforces birth_date NOT NULL
- No student records have null birth_date

**Files modified**:
- `backend/students/models.py`
- `backend/students/migrations/000X_birth_date_not_null.py` (new)

---

### [ ] Step: Run Full Test Suite and Lint

**Objective**: Verify all code changes pass tests and code quality checks

**Tasks**:
- [ ] Run full test suite: `pytest` (or equivalent from project)
- [ ] Fix any failing tests
- [ ] Run linter: `flake8` or `pylint` or `ruff` (check project config)
- [ ] Fix any linting errors
- [ ] Run type checker if configured: `mypy`
- [ ] Run frontend tests if applicable: `npm test`
- [ ] Run E2E tests: `npm run test:e2e`

**Verification**:
- All tests pass
- No linting errors
- No type errors
- Code quality meets project standards

**Commands to run**:
- `pytest -v`
- `flake8 backend/`
- `npm test` (if frontend changes)
- `npm run test:e2e`

---

### [ ] Step: Update API Documentation

**Objective**: Document API changes for student login endpoint

**Tasks**:
- [ ] Find API documentation (OpenAPI/Swagger, README, or docs folder)
- [ ] Update `/api/students/login/` endpoint documentation
- [ ] Change request body: remove `last_name`, add `birth_date`
- [ ] Document birth_date format: YYYY-MM-DD
- [ ] Document validation rules: date range, format requirements
- [ ] Update error response examples
- [ ] Add rate limiting documentation

**Verification**:
- Documentation accurately reflects API changes
- Examples are valid and testable

**Files modified**:
- `docs/API.md` or `backend/openapi.yaml` (or equivalent)

---

### [ ] Step: Create Student User Guide

**Objective**: Provide clear instructions for students using new login system

**Tasks**:
- [ ] Create student guide in French: `docs/guide_eleve.md`
- [ ] Section 1: How to find your INE (Identifiant National Élève)
- [ ] Section 2: How to find your birth date (format expected)
- [ ] Section 3: Login instructions with screenshots (if applicable)
- [ ] Section 4: Troubleshooting - rate limiting, invalid credentials
- [ ] Section 5: FAQ - "I forgot my INE", "Wrong birth date", "Account locked"
- [ ] Section 6: Contact information for help desk

**Verification**:
- Guide is clear and user-friendly
- Covers common issues and questions
- Available in French (primary language for students)

**Files modified**:
- `docs/guide_eleve.md` (new)

---

### [ ] Step: Final Verification and Sign-off

**Objective**: Comprehensive verification of all deliverables and success criteria

**Tasks**:
- [ ] Verify all success criteria from requirements.md:
  - ✅ Zero cross-student data leaks (E2E tests pass)
  - ✅ Status filtering (only GRADED copies visible)
  - ✅ Download protection (403 for invalid access)
  - ✅ Audit trail (all events logged)
  - ✅ Anti-brute-force (rate limiting works)
  - ✅ Generic error messages (no user enumeration)
  - ✅ Session security (4h timeout, secure cookies)
- [ ] Review all deliverables:
  - ✅ Database migration complete
  - ✅ API endpoint updated
  - ✅ Security headers added
  - ✅ Audit logging enhanced
  - ✅ Tests written and passing
  - ✅ audit.md created
  - ✅ Documentation updated
- [ ] Performance check: login < 200ms, copy list < 500ms, PDF download < 2s
- [ ] Security check: run security test suite, verify no vulnerabilities
- [ ] Update plan.md with final results

**Verification**:
- All acceptance criteria met
- All deliverables complete
- Ready for deployment

---

## Test Results

**Unit Tests**: [Pending]
**Integration Tests**: [Pending]
**Security Tests**: [Pending]
**E2E Tests**: [Pending]
**Linting**: [Pending]

---

## Deployment Checklist

- [ ] Database backup created
- [ ] Birth dates imported from Pronote CSV
- [ ] Migrations applied in staging environment
- [ ] Smoke tests passed in staging (20 test students)
- [ ] Student communication sent (new login instructions)
- [ ] Help desk prepared with FAQ
- [ ] Rollback plan documented
- [ ] Production deployment scheduled
- [ ] Post-deployment validation completed
