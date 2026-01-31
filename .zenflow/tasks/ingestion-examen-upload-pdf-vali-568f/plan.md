# Full SDD workflow

## Configuration
- **Artifacts Path**: {@artifacts_path} → `.zenflow/tasks/{task_id}`

---

## Workflow Steps

### [x] Step: Requirements
<!-- chat-id: b3c2d40f-df18-497e-8016-ae778e488d5c -->

Create a Product Requirements Document (PRD) based on the feature description.

1. Review existing codebase to understand current architecture and patterns
2. Analyze the feature definition and identify unclear aspects
3. Ask the user for clarifications on aspects that significantly impact scope or user experience
4. Make reasonable decisions for minor details based on context and conventions
5. If user can't clarify, make a decision, state the assumption, and continue

Save the PRD to `{@artifacts_path}/requirements.md`.

### [x] Step: Technical Specification
<!-- chat-id: 0ea16b7d-abcf-4a29-ac22-2b4fab5ace3f -->

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
<!-- chat-id: 42b56667-a337-4310-93dd-e1244284a40d -->

Create a detailed implementation plan based on `{@artifacts_path}/spec.md`.

1. Break down the work into concrete tasks
2. Each task should reference relevant contracts and include verification steps
3. Replace the Implementation step below with the planned tasks

Rule of thumb for step size: each step should represent a coherent unit of work (e.g., implement a component, add an API endpoint, write tests for a module). Avoid steps that are too granular (single function) or too broad (entire feature).

If the feature is trivial and doesn't warrant full specification, update this workflow to remove unnecessary steps and explain the reasoning to the user.

Save to `{@artifacts_path}/plan.md`.

### [ ] Step: Fix Atomicity

**Objective**: Ensure upload operation is atomic - no orphaned records on failures.

**Files to modify**:
- `backend/exams/views.py` (lines 22-68, ExamUploadView.post method)

**Tasks**:
- [ ] Add `from django.db import transaction` import
- [ ] Wrap entire upload operation in `try-except` block with `transaction.atomic()`
- [ ] Move exam creation, PDFSplitter call, and Copy creation inside atomic block
- [ ] Add file cleanup in exception handler (delete uploaded file if exam exists)
- [ ] Add structured logging for upload initiation and completion

**Verification**:
- [ ] Manual test: Inject failure in PDFSplitter → verify no Exam record in DB
- [ ] Manual test: Check media/exams/source/ → verify no orphaned files
- [ ] Run `python backend/manage.py check` → no errors

**References**: 
- spec.md § 2.1 Fix Atomicity Issue
- spec.md Appendix A1 (code pattern)

### [ ] Step: Improve Error Handling

**Objective**: Return correct HTTP status codes with user-friendly error messages.

**Files to modify**:
- `backend/exams/views.py` (same method as above)

**Tasks**:
- [ ] Add validation error inspection after `serializer.is_valid()` call
- [ ] Check for `file_too_large` error code → return HTTP 413 instead of 400
- [ ] Update exception handler to use `safe_error_response()` from `core.utils.errors`
- [ ] Ensure all error responses include user-friendly French messages
- [ ] Add logging for all error scenarios with request context

**Verification**:
- [ ] Manual test: Upload 51 MB file → verify HTTP 413 response
- [ ] Manual test: Upload corrupted PDF → verify HTTP 400 with clear message
- [ ] Manual test: Upload empty file → verify HTTP 400 with clear message
- [ ] Review error messages → all are user-friendly and actionable

**References**:
- spec.md § 2.2 Improve Error Handling
- spec.md § 2.3 Add HTTP 413 Support
- requirements.md FR-4 Error Handling & User Messages

### [ ] Step: Create Test Fixtures

**Objective**: Create programmatic PDF fixture generation utilities.

**Files to create**:
- `backend/exams/tests/fixtures/pdf_fixtures.py` (NEW)

**Tasks**:
- [ ] Create `create_valid_pdf(pages=4)` - returns PDF bytes with N pages
- [ ] Create `create_large_pdf(size_mb=51)` - returns PDF > 50 MB
- [ ] Create `create_corrupted_pdf()` - returns invalid PDF bytes
- [ ] Create `create_fake_pdf()` - returns text file content (for MIME type test)
- [ ] Add helper: `create_uploadedfile(pdf_bytes, filename)` - wraps bytes in Django UploadedFile
- [ ] Test each fixture manually to ensure they work as expected

**Verification**:
- [ ] Run each fixture generator → verify outputs match expected behavior
- [ ] Verify valid PDF opens in PyMuPDF without errors
- [ ] Verify corrupted PDF raises exception when opened with PyMuPDF
- [ ] Verify fake PDF fails MIME type detection

**References**:
- spec.md § 3.2 Files to Create (pdf_fixtures.py)
- spec.md Appendix A2 Test Fixture Example
- requirements.md § 4.3 Test Fixtures

### [ ] Step: Write Upload Endpoint Tests - Validation Cases

**Objective**: Test all validation scenarios for the upload endpoint.

**Files to create**:
- `backend/exams/tests/test_upload_endpoint.py` (NEW)

**Tasks**:
- [ ] Set up test class with pytest fixtures (authenticated teacher user, API client)
- [ ] Write `test_upload_valid_pdf_creates_exam_and_booklets()` - 4-page PDF success
- [ ] Write `test_upload_valid_pdf_with_remainder_pages()` - 13-page PDF with partial booklet
- [ ] Write `test_upload_no_file_returns_400()` - missing file
- [ ] Write `test_upload_wrong_extension_returns_400()` - .txt file
- [ ] Write `test_upload_file_too_large_returns_413()` - 51 MB file
- [ ] Write `test_upload_empty_file_returns_400()` - 0-byte file
- [ ] Write `test_upload_fake_pdf_returns_400()` - text file renamed to .pdf
- [ ] Write `test_upload_corrupted_pdf_returns_400()` - invalid PDF structure
- [ ] Write `test_upload_too_many_pages_returns_400()` - 501-page PDF

**Verification**:
- [ ] Run `pytest backend/exams/tests/test_upload_endpoint.py -v`
- [ ] All validation tests pass
- [ ] Verify test output shows correct HTTP status codes

**References**:
- spec.md § 3.2 Files to Create (test_upload_endpoint.py)
- requirements.md § 4.1 Unit Tests

### [ ] Step: Write Upload Endpoint Tests - Atomicity Cases

**Objective**: Verify no orphaned records on processing failures.

**Files to modify**:
- `backend/exams/tests/test_upload_endpoint.py` (continue from previous step)

**Tasks**:
- [ ] Write `test_upload_processing_failure_no_orphan_exam()` - mock split_exam() failure
- [ ] Write `test_upload_booklet_creation_failure_rollback()` - mock Copy.create() failure
- [ ] Write `test_upload_file_cleanup_on_failure()` - verify file deleted on error
- [ ] Add assertions: verify Exam count = 0, Booklet count = 0, Copy count = 0 after failure
- [ ] Verify media/exams/source/ directory is empty after failures

**Verification**:
- [ ] Run atomicity tests → all pass
- [ ] Verify DB state after mocked failures (no records)
- [ ] Verify no orphaned files in media directories

**References**:
- spec.md § 3.2 Files to Create (atomicity tests)
- requirements.md FR-3 Atomicity Guarantee

### [ ] Step: Write Upload Endpoint Tests - Auth & Security

**Objective**: Verify authentication, authorization, and security protections.

**Files to modify**:
- `backend/exams/tests/test_upload_endpoint.py` (continue from previous step)

**Tasks**:
- [ ] Write `test_upload_anonymous_user_rejected()` - unauthenticated → 401
- [ ] Write `test_upload_student_role_rejected()` - student user → 403
- [ ] Write `test_upload_teacher_role_allowed()` - teacher user → 201
- [ ] Write `test_upload_admin_role_allowed()` - admin user → 201
- [ ] Write `test_upload_path_traversal_protection()` - filename: `../../../../etc/passwd.pdf`
- [ ] Write `test_upload_rate_limit_enforced()` - 21 uploads/hour → 429 (optional, if rate limiting is testable)

**Verification**:
- [ ] Run auth/security tests → all pass
- [ ] Verify path traversal test: file saved as `passwd.pdf` in correct directory

**References**:
- spec.md § 6.3 Security Verification
- requirements.md NFR-2 Security

### [ ] Step: Run Full Test Suite & Coverage

**Objective**: Achieve ≥95% test coverage for upload functionality.

**Tasks**:
- [ ] Run all upload tests: `pytest backend/exams/tests/test_upload_endpoint.py -v`
- [ ] Run with coverage: `pytest backend/exams/tests/test_upload_endpoint.py --cov=backend/exams/views --cov-report=term-missing`
- [ ] Review coverage report → identify any missed branches
- [ ] Add missing tests for uncovered code paths
- [ ] Run full exams test suite: `pytest backend/exams/tests/ -v`
- [ ] Verify all tests pass

**Verification**:
- [ ] Coverage report shows ≥95% for `backend/exams/views.py::ExamUploadView`
- [ ] All tests pass (0 failures)
- [ ] No flaky tests (run multiple times to verify)

**References**:
- spec.md § 6.1 Test Execution
- requirements.md § 4 Testing Requirements

### [ ] Step: Run Linting & Type Checking

**Objective**: Ensure code quality and consistency.

**Tasks**:
- [ ] Check project for linting tools: `cat backend/pyproject.toml` or `cat backend/requirements.txt`
- [ ] Run linter if configured (e.g., `ruff check backend/exams/` or `flake8 backend/exams/`)
- [ ] Run Django system checks: `python backend/manage.py check`
- [ ] Fix any linting errors or warnings
- [ ] Run type checker if configured (e.g., `mypy backend/exams/views.py`)

**Verification**:
- [ ] All linting checks pass (0 errors)
- [ ] Django system checks pass
- [ ] Type checking passes (if applicable)

**References**:
- spec.md § 6.5 Linting & Type Checking

### [ ] Step: Create Audit Documentation

**Objective**: Document findings, fixes, and test results.

**Files to create**:
- `audit.md` (in project root or task artifacts folder)

**Tasks**:
- [ ] Document current implementation review (what was found)
- [ ] Document atomicity issues and fixes applied
- [ ] Document error handling improvements
- [ ] List all test cases created (with counts)
- [ ] Include test results (all pass, coverage %)
- [ ] Document HTTP behavior reference table
- [ ] Add recommendations for future improvements (if any)

**Verification**:
- [ ] Review audit.md for completeness
- [ ] Ensure all findings are documented with file/line references
- [ ] Test results are clearly presented

**References**:
- spec.md Phase 4: Documentation & Audit Report
- Task description: "Livrables: audit.md + tests + fixtures PDFs minimaux"
