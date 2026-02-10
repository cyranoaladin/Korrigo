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

### [x] Step: Fix Atomicity
<!-- chat-id: 11c8eace-f76b-4714-aeb4-ba552f72054f -->

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

### [x] Step: Improve Error Handling
<!-- chat-id: 8cbcbd0e-dbe2-4592-bf31-7c3cd4a8edc1 -->

**Objective**: Return correct HTTP status codes with user-friendly error messages.

**Files to modify**:
- `backend/exams/views.py` (same method as above)

**Tasks**:
- [x] Add validation error inspection after `serializer.is_valid()` call
- [x] Check for `file_too_large` error code → return HTTP 413 instead of 400
- [x] Update exception handler to use `safe_error_response()` from `core.utils.errors`
- [x] Ensure all error responses include user-friendly French messages
- [x] Add logging for all error scenarios with request context

**Verification**:
- [x] Manual test: Upload 51 MB file → verify HTTP 413 response
- [x] Manual test: Upload corrupted PDF → verify HTTP 400 with clear message
- [x] Manual test: Upload empty file → verify HTTP 400 with clear message
- [x] Review error messages → all are user-friendly and actionable

**References**:
- spec.md § 2.2 Improve Error Handling
- spec.md § 2.3 Add HTTP 413 Support
- requirements.md FR-4 Error Handling & User Messages

### [x] Step: Create Test Fixtures
<!-- chat-id: 4b8b67da-c2e1-41a7-8eb1-5999a6773c0a -->

**Objective**: Create programmatic PDF fixture generation utilities.

**Files to create**:
- `backend/exams/tests/fixtures/pdf_fixtures.py` (NEW)

**Tasks**:
- [x] Create `create_valid_pdf(pages=4)` - returns PDF bytes with N pages
- [x] Create `create_large_pdf(size_mb=51)` - returns PDF > 50 MB
- [x] Create `create_corrupted_pdf()` - returns invalid PDF bytes
- [x] Create `create_fake_pdf()` - returns text file content (for MIME type test)
- [x] Add helper: `create_uploadedfile(pdf_bytes, filename)` - wraps bytes in Django UploadedFile
- [x] Test each fixture manually to ensure they work as expected

**Verification**:
- [x] Run each fixture generator → verify outputs match expected behavior
- [x] Verify valid PDF opens in PyMuPDF without errors
- [x] Verify corrupted PDF raises exception when opened with PyMuPDF
- [x] Verify fake PDF fails MIME type detection

**References**:
- spec.md § 3.2 Files to Create (pdf_fixtures.py)
- spec.md Appendix A2 Test Fixture Example
- requirements.md § 4.3 Test Fixtures

### [x] Step: Write Upload Endpoint Tests - Validation Cases
<!-- chat-id: 85d71758-c122-4672-8a89-ffbc36dfac35 -->

**Objective**: Test all validation scenarios for the upload endpoint.

**Files to create**:
- `backend/exams/tests/test_upload_endpoint.py` (NEW)

**Tasks**:
- [x] Set up test class with pytest fixtures (authenticated teacher user, API client)
- [x] Write `test_upload_valid_pdf_creates_exam_and_booklets()` - 4-page PDF success
- [x] Write `test_upload_valid_pdf_with_remainder_pages()` - 13-page PDF with partial booklet
- [x] Write `test_upload_no_file_returns_400()` - missing file
- [x] Write `test_upload_wrong_extension_returns_400()` - .txt file
- [x] Write `test_upload_file_too_large_returns_413()` - 51 MB file
- [x] Write `test_upload_empty_file_returns_400()` - 0-byte file
- [x] Write `test_upload_fake_pdf_returns_400()` - text file renamed to .pdf
- [x] Write `test_upload_corrupted_pdf_returns_400()` - invalid PDF structure
- [x] Write `test_upload_too_many_pages_returns_400()` - 501-page PDF

**Verification**:
- [x] Run `pytest backend/exams/tests/test_upload_endpoint.py -v`
- [x] All validation tests pass
- [x] Verify test output shows correct HTTP status codes

**References**:
- spec.md § 3.2 Files to Create (test_upload_endpoint.py)
- requirements.md § 4.1 Unit Tests

### [x] Step: Write Upload Endpoint Tests - Atomicity Cases
<!-- chat-id: 7073334b-47fc-4565-a2ec-5a37d95fee53 -->

**Objective**: Verify no orphaned records on processing failures.

**Files to modify**:
- `backend/exams/tests/test_upload_endpoint.py` (continue from previous step)

**Tasks**:
- [x] Write `test_upload_processing_failure_no_orphan_exam()` - mock split_exam() failure
- [x] Write `test_upload_booklet_creation_failure_rollback()` - mock Copy.create() failure
- [x] Write `test_upload_file_cleanup_on_failure()` - verify file deleted on error
- [x] Add assertions: verify Exam count = 0, Booklet count = 0, Copy count = 0 after failure
- [x] Verify media/exams/source/ directory is empty after failures

**Verification**:
- [x] Run atomicity tests → all pass
- [x] Verify DB state after mocked failures (no records)
- [x] Verify no orphaned files in media directories

**References**:
- spec.md § 3.2 Files to Create (atomicity tests)
- requirements.md FR-3 Atomicity Guarantee

### [x] Step: Write Upload Endpoint Tests - Auth & Security
<!-- chat-id: e0ffce03-6e9b-492a-9063-a3f19ec79c6f -->

**Objective**: Verify authentication, authorization, and security protections.

**Files to modify**:
- `backend/exams/tests/test_upload_endpoint.py` (continue from previous step)

**Tasks**:
- [x] Write `test_upload_anonymous_user_rejected()` - unauthenticated → 401
- [x] Write `test_upload_student_role_rejected()` - student user → 403
- [x] Write `test_upload_teacher_role_allowed()` - teacher user → 201
- [x] Write `test_upload_admin_role_allowed()` - admin user → 201
- [x] Write `test_upload_path_traversal_protection()` - filename: `../../../../etc/passwd.pdf`
- [x] Write `test_upload_dangerous_filename_sanitized()` - filename with dangerous characters
- [x] Write `test_upload_rate_limit_enforced()` - 21 uploads/hour → 429 (optional, skipped with documentation)

**Verification**:
- [x] Run auth/security tests → all pass
- [x] Verify path traversal test: file saved as `passwd.pdf` in correct directory

**References**:
- spec.md § 6.3 Security Verification
- requirements.md NFR-2 Security

### [x] Step: Run Full Test Suite & Coverage
<!-- chat-id: 9f1ae6df-7c07-4834-a5d5-ded7bd75abcf -->

**Objective**: Achieve ≥95% test coverage for upload functionality.

**Tasks**:
- [x] Run all upload tests: `pytest backend/exams/tests/test_upload_endpoint.py -v`
- [x] Run with coverage: `pytest backend/exams/tests/test_upload_endpoint.py --cov=exams.views --cov-report=term-missing`
- [x] Review coverage report → identify any missed branches
- [x] Add missing tests for uncovered code paths
- [x] Run full exams test suite: `pytest backend/exams/tests/ -v`
- [x] Verify all tests pass

**Verification**:
- [x] Coverage report shows ≥95% for `backend/exams/views.py::ExamUploadView` - **100% achieved**
- [x] All tests pass (0 failures) - **17 passed, 1 skipped**
- [x] No flaky tests (run multiple times to verify)

**References**:
- spec.md § 6.1 Test Execution
- requirements.md § 4 Testing Requirements

### [x] Step: Run Linting & Type Checking
<!-- chat-id: ff363dfe-d6d6-45e2-af6b-f4311b924120 -->

**Objective**: Ensure code quality and consistency.

**Tasks**:
- [x] Check project for linting tools: `cat backend/pyproject.toml` or `cat backend/requirements.txt`
- [x] Run linter if configured (e.g., `ruff check backend/exams/` or `flake8 backend/exams/`)
- [x] Run Django system checks: `python backend/manage.py check`
- [x] Fix any linting errors or warnings
- [x] Run type checker if configured (e.g., `mypy backend/exams/views.py`)

**Verification**:
- [x] All linting checks pass (0 errors)
- [x] Django system checks pass
- [x] Type checking passes (if applicable)

**References**:
- spec.md § 6.5 Linting & Type Checking

### [x] Step: Create Audit Documentation
<!-- chat-id: ea9963ff-6d5e-4fbc-a3b1-962e56369602 -->

**Objective**: Document findings, fixes, and test results.

**Files to create**:
- `audit.md` (in project root or task artifacts folder)

**Tasks**:
- [x] Document current implementation review (what was found)
- [x] Document atomicity issues and fixes applied
- [x] Document error handling improvements
- [x] List all test cases created (with counts)
- [x] Include test results (all pass, coverage %)
- [x] Document HTTP behavior reference table
- [x] Add recommendations for future improvements (if any)

**Verification**:
- [x] Review audit.md for completeness
- [x] Ensure all findings are documented with file/line references
- [x] Test results are clearly presented

**References**:
- spec.md Phase 4: Documentation & Audit Report
- Task description: "Livrables: audit.md + tests + fixtures PDFs minimaux"
