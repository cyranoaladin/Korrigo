# Technical Specification: PDF Exam Upload Validation & Error Handling

**Task ID**: ZF-AUD-03  
**Title**: INGESTION EXAMEN: UPLOAD PDF + VALIDATIONS + ERREURS (Backend)  
**Date**: January 31, 2026  
**Status**: Technical Specification  
**PRD**: requirements.md

---

## 1. Technical Context

### 1.1 Technology Stack

**Backend Framework**:
- Django 4.2+ with Django REST Framework
- Python 3.11+
- PostgreSQL (production) / SQLite (testing)

**PDF Processing**:
- PyMuPDF (fitz) 1.23.26 - PDF validation and page extraction
- python-magic 0.4.27 - MIME type detection

**File Storage**:
- Django FileField with local filesystem storage
- Media root: `media/` directory
- Upload paths:
  - `media/exams/source/` - Original uploaded PDFs
  - `media/booklets/{exam_id}/{booklet_id}/` - Extracted page images
  - `media/copies/source/` - Individual copy PDFs

**Testing**:
- pytest + pytest-django for test execution
- Factory pattern for test fixtures (programmatic PDF generation)

### 1.2 Current Architecture

**Upload Flow** (current):
```
POST /api/exams/upload/
├─ ExamUploadView.post()
│  ├─ ExamSerializer.is_valid() → Runs validators on pdf_source field
│  ├─ serializer.save() → Creates Exam record ⚠️ BEFORE processing
│  ├─ PDFSplitter.split_exam() → Creates Booklet records + extracts pages
│  ├─ Copy.objects.create() → Creates Copy records in STAGING status
│  └─ Response 201 Created
```

**Validation Chain** (current):
```
Exam.pdf_source (FileField)
├─ FileExtensionValidator(['pdf'])
├─ validate_pdf_size (50 MB max)
├─ validate_pdf_not_empty (> 0 bytes)
├─ validate_pdf_mime_type (python-magic check)
└─ validate_pdf_integrity (PyMuPDF validation, 500 pages max)
```

### 1.3 Identified Issues

1. **Atomicity Violation** (`backend/exams/views.py:30-66`):
   - `exam = serializer.save()` commits to DB immediately
   - If `PDFSplitter.split_exam()` fails afterward, orphaned Exam record remains
   - No transaction wrapping around the full operation

2. **Error Message Inconsistency**:
   - Generic 500 errors for processing failures
   - Validation errors from Django validators are technical (e.g., "Fichier trop volumineux")
   - Need consistent, user-friendly messages aligned with HTTP status codes

3. **HTTP Status Code Issues**:
   - File size errors return 400 instead of 413 (Payload Too Large)
   - Need to map validation errors to proper HTTP codes

4. **File Cleanup Gap**:
   - If transaction rolls back, uploaded file may remain orphaned in `media/exams/source/`
   - No explicit cleanup logic

5. **Test Coverage Gaps**:
   - Unit tests exist for validators (`test_pdf_validators.py`)
   - Missing integration tests for upload endpoint
   - No atomicity/rollback tests
   - No test fixtures for reproducible testing

---

## 2. Implementation Approach

### 2.1 Fix Atomicity Issue

**Objective**: Ensure upload is atomic - either fully succeeds or fully fails with rollback.

**Solution**: Wrap entire upload flow in `transaction.atomic()` block.

**File**: `backend/exams/views.py`

**Changes**:
1. Import `transaction` from `django.db`
2. Wrap `exam.save() + PDFSplitter + Copy creation` in atomic block
3. Move try-except to wrap the entire transaction
4. Add file cleanup in exception handler

**Code Pattern** (from codebase analysis):
```python
from django.db import transaction

@transaction.atomic
def post(self, request, *args, **kwargs):
    # All DB operations inside atomic block
    # Automatic rollback on any exception
```

**Note**: `PDFSplitter.split_exam()` already has `@transaction.atomic` decorator (line 40 of `pdf_splitter.py`), but this only covers booklet creation, not the parent Exam creation.

### 2.2 Improve Error Handling

**Objective**: Provide user-friendly error messages with correct HTTP status codes.

**Approach**:
1. Catch `ValidationError` from serializer and map to appropriate HTTP codes
2. Distinguish between validation errors (400/413) and processing errors (500)
3. Use existing `safe_error_response()` from `core.utils.errors` for 500 errors
4. Return structured error responses for all failure scenarios

**Error Mapping Table**:
| Validation Error Code | HTTP Status | User Message |
|-----------------------|-------------|--------------|
| `file_too_large` | 413 | "Fichier trop volumineux ({size} Mo). Taille maximale: 50 Mo." |
| `empty_file` | 400 | "Fichier vide. Veuillez téléverser un PDF valide." |
| `invalid_mime_type` | 400 | "Type de fichier invalide. Attendu: PDF." |
| `corrupted_pdf` | 400 | "Fichier PDF corrompu ou illisible." |
| `too_many_pages` | 400 | "PDF trop volumineux ({n} pages). Maximum: 500 pages." |
| Processing exception | 500 | "Échec du traitement PDF. Veuillez réessayer." |

### 2.3 Add HTTP 413 Support

**Current Issue**: Django validators raise `ValidationError` which DRF maps to 400.

**Solution**: Catch size validation errors specifically and return 413.

**Implementation**:
```python
if not serializer.is_valid():
    errors = serializer.errors
    # Check if pdf_source has file_too_large error
    if 'pdf_source' in errors:
        for error in errors['pdf_source']:
            if hasattr(error, 'code') and error.code == 'file_too_large':
                return Response({
                    "error": str(error)
                }, status=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE)
    return Response(errors, status=status.HTTP_400_BAD_REQUEST)
```

### 2.4 File Cleanup on Rollback

**Issue**: Transaction rollback doesn't delete uploaded files (FileField behavior).

**Solution**: 
1. Django's transaction rollback only affects DB, not filesystem
2. Add explicit file cleanup in exception handler
3. Delete file before re-raising exception or returning error

**Implementation Pattern**:
```python
except Exception as e:
    # Cleanup uploaded file if exam was created
    if 'exam' in locals() and exam.pdf_source:
        exam.pdf_source.delete(save=False)
    # Log and return error
    logger.error(f"Upload failed: {e}", exc_info=True)
    return Response(...)
```

**Note**: This cleanup happens AFTER transaction rollback, so Exam record won't exist in DB.

---

## 3. Source Code Structure Changes

### 3.1 Files to Modify

#### `backend/exams/views.py`
**Lines to change**: 22-68 (ExamUploadView.post method)

**Changes**:
1. Add `from django.db import transaction` import
2. Wrap entire operation in `try-except` with `transaction.atomic()`
3. Add validation error inspection for 413 status code
4. Add file cleanup in exception handler
5. Improve error response messages

#### `backend/exams/validators.py`
**Optional enhancement**: Update error messages to be more user-friendly (French)

**No changes required** - Messages are already translated with `gettext_lazy`.

### 3.2 Files to Create

#### `backend/exams/tests/test_upload_endpoint.py` (NEW)
**Purpose**: Integration tests for upload endpoint

**Structure**:
```python
@pytest.mark.django_db
class TestExamUploadEndpoint:
    """Integration tests for POST /api/exams/upload/"""
    
    # Success cases
    def test_upload_valid_pdf_creates_exam_and_booklets()
    def test_upload_valid_pdf_with_remainder_pages()
    
    # Validation failures
    def test_upload_no_file_returns_400()
    def test_upload_wrong_extension_returns_400()
    def test_upload_file_too_large_returns_413()
    def test_upload_empty_file_returns_400()
    def test_upload_fake_pdf_returns_400()
    def test_upload_corrupted_pdf_returns_400()
    def test_upload_too_many_pages_returns_400()
    
    # Atomicity tests
    def test_upload_processing_failure_no_orphan_exam()
    def test_upload_booklet_creation_failure_rollback()
    
    # Authentication/Authorization
    def test_upload_anonymous_user_rejected()
    def test_upload_student_role_rejected()
    def test_upload_teacher_role_allowed()
```

#### `backend/exams/tests/fixtures/pdf_fixtures.py` (NEW)
**Purpose**: Programmatic PDF fixture generation

**Functions**:
- `create_valid_pdf(pages=4)` → Returns PDF bytes
- `create_large_pdf(size_mb=51)` → Returns PDF bytes > 50 MB
- `create_corrupted_pdf()` → Returns invalid PDF bytes
- `create_fake_pdf()` → Returns text file with .pdf extension

**Pattern** (from existing tests):
```python
import fitz
def create_valid_pdf(pages=4):
    doc = fitz.open()
    for _ in range(pages):
        doc.new_page()
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes
```

#### `backend/exams/tests/test_upload_integration.py` (NEW)
**Purpose**: End-to-end workflow tests

**Tests**:
- Full upload → booklet creation → copy creation → verify DB state
- Concurrent upload scenarios (if needed)
- Storage path verification

### 3.3 Files to Reference (No Changes)

These files are referenced but don't need modifications:

- `backend/exams/models.py` - Exam, Booklet, Copy models (already correct)
- `backend/exams/serializers.py` - ExamSerializer (already has validators)
- `backend/processing/services/pdf_splitter.py` - PDFSplitter (already atomic)
- `backend/core/utils/errors.py` - safe_error_response() (reuse as-is)
- `backend/exams/tests/test_pdf_validators.py` - Validator unit tests (already comprehensive)

---

## 4. Data Model / API / Interface Changes

### 4.1 Database Schema
**No changes required** - Existing models are sufficient.

### 4.2 API Contract
**No changes required** - Endpoint remains `POST /api/exams/upload/`

**Updated Response Codes** (documentation only):
- `201 Created` - Success
- `400 Bad Request` - Validation failure (invalid file, corrupted, etc.)
- `413 Payload Too Large` - File > 50 MB (NEW - was returning 400)
- `500 Internal Server Error` - Processing failure

**Response Body** (unchanged):
```json
{
  "id": "uuid",
  "name": "Exam name",
  "date": "2026-05-20",
  "booklets_created": 25,
  "message": "25 booklets created successfully"
}
```

**Error Response** (improved):
```json
{
  "error": "Fichier trop volumineux (51.2 Mo). Taille maximale: 50 Mo."
}
```

### 4.3 File Storage Structure
**No changes** - Existing structure is correct:
```
media/
├── exams/source/          # Original PDFs
├── booklets/
│   └── {exam_id}/
│       └── {booklet_id}/
│           ├── page_001.png
│           └── ...
└── copies/
    ├── source/
    └── final/
```

---

## 5. Delivery Phases

### Phase 1: Fix Atomicity (Critical - P0)
**Objective**: Ensure no orphaned records on upload failures.

**Tasks**:
1. Modify `ExamUploadView.post()` to wrap all operations in `transaction.atomic()`
2. Add file cleanup in exception handler
3. Verify with manual testing (inject failure in PDFSplitter)

**Acceptance**:
- Upload failure leaves zero DB records
- No orphaned files in media folder

### Phase 2: Improve Error Handling (Critical - P0)
**Objective**: Return correct HTTP codes and user-friendly messages.

**Tasks**:
1. Add validation error inspection for 413 status code
2. Improve error messages in exception handler
3. Ensure all error paths return structured responses

**Acceptance**:
- File > 50 MB returns HTTP 413
- All errors have clear, actionable messages
- No raw exceptions exposed to users

### Phase 3: Comprehensive Testing (High - P1)
**Objective**: Achieve ≥95% test coverage for upload flow.

**Tasks**:
1. Create `pdf_fixtures.py` with programmatic PDF generators
2. Write `test_upload_endpoint.py` with all success/failure scenarios
3. Write atomicity tests that verify no orphans on failures
4. Run tests and verify coverage with pytest-cov

**Acceptance**:
- All validation scenarios tested (8+ test cases)
- Atomicity tests pass (verify DB counts before/after)
- Test coverage ≥95% for `views.ExamUploadView`

### Phase 4: Documentation & Audit Report (Medium - P2)
**Objective**: Document findings and behavior.

**Tasks**:
1. Create `audit.md` documenting:
   - Current implementation review
   - Issues found and fixes applied
   - Test results
   - HTTP behavior reference
2. Update inline code comments if needed

**Acceptance**:
- `audit.md` clearly explains all findings
- HTTP contract documented
- Code is self-documenting

---

## 6. Verification Approach

### 6.1 Test Execution

**Command**:
```bash
# Run all exam upload tests
pytest backend/exams/tests/test_upload_endpoint.py -v

# Run with coverage
pytest backend/exams/tests/test_upload_endpoint.py --cov=backend/exams/views --cov-report=term-missing

# Run all PDF-related tests
pytest backend/exams/tests/ -k "upload or pdf" -v
```

### 6.2 Manual Verification Checklist

**Upload Success Cases**:
- ✅ 4-page PDF → 1 booklet created
- ✅ 100-page PDF → 25 booklets created (4 pages each)
- ✅ 13-page PDF → 4 booklets (last has 1 page) with warning

**Upload Failure Cases**:
- ✅ File > 50 MB → HTTP 413 + clear message
- ✅ Empty file → HTTP 400 + clear message
- ✅ Text file renamed .pdf → HTTP 400 + MIME type error
- ✅ Corrupted PDF → HTTP 400 + corruption message
- ✅ 501-page PDF → HTTP 400 + too many pages message

**Atomicity Verification**:
```bash
# Inject failure in PDFSplitter (comment out booklet save)
# Upload PDF
# Verify: SELECT COUNT(*) FROM exams_exam; → Should be 0
# Verify: ls media/exams/source/ → Should be empty
```

### 6.3 Security Verification

**Path Traversal**:
```python
# Test filename: ../../../../etc/passwd.pdf
# Expected: File saved as passwd.pdf in media/exams/source/
# Verify: No directory traversal occurred
```

**Rate Limiting**:
```python
# Upload 21 PDFs in 1 hour from same user
# Expected: 21st request returns HTTP 429
```

**Authentication**:
```python
# Anonymous user → HTTP 401
# Student user → HTTP 403
# Teacher user → HTTP 201
```

### 6.4 Performance Verification

**Benchmarks** (reference from requirements):
- 50 MB PDF validation: < 5 seconds
- 500-page PDF splitting: < 60 seconds

**Measurement**:
```python
import time
start = time.time()
response = client.post('/api/exams/upload/', {'pdf_source': large_file})
elapsed = time.time() - start
assert elapsed < 5.0  # 5 second threshold
```

### 6.5 Linting & Type Checking

**Commands** (check if these exist in project):
```bash
# Linting (if ruff or flake8 configured)
ruff check backend/exams/

# Type checking (if mypy configured)
mypy backend/exams/views.py

# Django system checks
python backend/manage.py check
```

**Note**: Check `backend/requirements.txt` or `pyproject.toml` for configured linters.

---

## 7. Technical Constraints & Considerations

### 7.1 Transaction Boundaries

**PostgreSQL Behavior**:
- `transaction.atomic()` creates a savepoint in nested transactions
- PDFSplitter has its own `@transaction.atomic` → nested savepoint
- If PDFSplitter fails, inner savepoint rolls back, then outer transaction catches exception and rolls back Exam creation

**SQLite Testing**:
- Test database uses SQLite (per `settings_test.py`)
- SQLite transaction behavior differs from PostgreSQL
- Ensure tests run with `CONN_MAX_AGE = 0` to avoid connection pooling issues

### 7.2 File Field Cleanup

**Django FileField Behavior**:
- `FileField.delete(save=False)` deletes file without saving model
- Must be called explicitly - Django doesn't auto-delete on rollback
- Race condition possible: file saved before transaction commits

**Best Practice**:
```python
try:
    with transaction.atomic():
        exam = serializer.save()  # Saves file + DB record
        # ... processing ...
except Exception as e:
    # File already on disk, but DB rolled back
    if hasattr(exam, 'pdf_source') and exam.pdf_source:
        exam.pdf_source.delete(save=False)  # Clean up file
    raise
```

### 7.3 Rate Limiting

**Current Implementation** (`@maybe_ratelimit(key='user', rate='20/h')`):
- Uses django-ratelimit or custom middleware
- Applies to authenticated users only
- Decorator is already in place - no changes needed

### 7.4 Media File Permissions

**Security Consideration**:
- Uploaded files should be readable only by application
- Django's FileSystemStorage uses `FILE_UPLOAD_PERMISSIONS` setting
- Verify: `ls -la media/exams/source/` → Files should be `rw-r--r--` (644) or more restrictive

**No changes needed** if settings are correct.

---

## 8. Dependencies

### 8.1 Existing Dependencies (Confirmed)
From `backend/requirements.txt` analysis:
- Django ≥ 4.2
- djangorestframework
- PyMuPDF (fitz) ≥ 1.23
- python-magic ≥ 0.4

### 8.2 Testing Dependencies (Required)
- pytest
- pytest-django
- pytest-cov (for coverage reporting)

**Verify installation**:
```bash
pip list | grep -E "pytest|coverage"
```

### 8.3 No New Dependencies Required
All required libraries are already in use.

---

## 9. Risks & Mitigations

### Risk 1: Transaction Rollback Performance
**Risk**: Large PDFs cause long-running transactions.

**Impact**: Database locks, slow rollbacks.

**Mitigation**:
- Keep transaction scope minimal (just DB ops, not file processing)
- PDFSplitter file extraction happens inside transaction - acceptable for MVP
- Future: Move to async Celery task if needed

**Likelihood**: Low (50 MB / 500 pages is reasonable for sync processing)

### Risk 2: File System Out of Sync with DB
**Risk**: Rollback leaves orphaned files despite cleanup.

**Impact**: Disk space waste, media folder clutter.

**Mitigation**:
- Explicit file cleanup in exception handler
- Manual cleanup script if needed: `python manage.py clean_orphaned_media`
- Future: Use pre-save signal to prevent file save until after processing

**Likelihood**: Low (cleanup logic is straightforward)

### Risk 3: Test Fixtures Inconsistency
**Risk**: Programmatic PDF generation produces different results across environments.

**Impact**: Flaky tests.

**Mitigation**:
- Use fixed parameters for PyMuPDF (DPI, page size)
- Commit small known-good PDFs for critical tests
- Document fixture generation logic

**Likelihood**: Low (PyMuPDF is deterministic)

---

## 10. Open Questions

### Q1: Should we log all upload attempts for audit?
**Proposal**: Log every upload (success + failure) with user, filename, size.

**Decision**: Yes - add structured logging in `ExamUploadView.post()`.

**Implementation**:
```python
logger.info("PDF upload initiated", extra={
    "user_id": request.user.id,
    "filename": request.FILES.get('pdf_source').name,
    "size_mb": request.FILES.get('pdf_source').size / (1024*1024)
})
```

### Q2: Do we need a fixture cleanup management command?
**Proposal**: `python manage.py generate_test_fixtures` to create PDF test files.

**Decision**: Not needed - generate fixtures programmatically in test setup.

### Q3: Should we implement retry logic for processing failures?
**Proposal**: If PDFSplitter fails, retry 2-3 times before giving up.

**Decision**: Out of scope - current implementation is sufficient for MVP. Future enhancement.

---

## 11. Success Criteria Summary

After implementation, verify:

✅ **Atomicity**:
- Upload failures leave zero DB records (Exam, Booklet, Copy)
- No orphaned files in media folder

✅ **Error Handling**:
- File > 50 MB returns HTTP 413 (not 400)
- All errors have user-friendly French messages
- No raw exception messages exposed

✅ **Testing**:
- ≥95% test coverage for ExamUploadView
- All validation scenarios tested (8+ cases)
- Atomicity tests verify no orphans

✅ **Security**:
- Path traversal protection verified
- Rate limiting works (429 on 21st request)
- Authentication enforced (401/403 for unauthorized)

✅ **Documentation**:
- `audit.md` created with findings
- HTTP contract documented
- Test results recorded

---

## 12. References

**Codebase Files**:
- `backend/exams/views.py:22-68` - ExamUploadView (to modify)
- `backend/exams/validators.py` - Validation functions (reference)
- `backend/exams/serializers.py` - ExamSerializer (reference)
- `backend/processing/services/pdf_splitter.py` - PDFSplitter (reference)
- `backend/core/utils/errors.py` - safe_error_response (reuse)
- `backend/exams/tests/test_pdf_validators.py` - Validator tests (reference pattern)

**Django Documentation**:
- [Database Transactions](https://docs.djangoproject.com/en/4.2/topics/db/transactions/)
- [File Uploads](https://docs.djangoproject.com/en/4.2/topics/http/file-uploads/)
- [Validators](https://docs.djangoproject.com/en/4.2/ref/validators/)

**Libraries**:
- [PyMuPDF Documentation](https://pymupdf.readthedocs.io/)
- [python-magic](https://github.com/ahupp/python-magic)

**Project Documents**:
- `requirements.md` - Product requirements
- `.antigravity/rules/01_security_rules.md § 8.1` - Security validation rules

---

## Appendix: Code Snippets

### A1: Updated ExamUploadView (Pseudocode)

```python
from django.db import transaction
import logging

logger = logging.getLogger(__name__)

class ExamUploadView(APIView):
    permission_classes = [IsTeacherOrAdmin]
    parser_classes = (MultiPartParser, FormParser)

    @method_decorator(maybe_ratelimit(key='user', rate='20/h', method='POST', block=True))
    def post(self, request, *args, **kwargs):
        serializer = ExamSerializer(data=request.data)
        
        # Validation
        if not serializer.is_valid():
            # Check for file size error → return 413
            if 'pdf_source' in serializer.errors:
                for error in serializer.errors['pdf_source']:
                    if hasattr(error, 'code') and error.code == 'file_too_large':
                        return Response({
                            "error": str(error)
                        }, status=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        # Atomic upload + processing
        exam = None
        try:
            with transaction.atomic():
                logger.info("Upload initiated", extra={...})
                
                exam = serializer.save()
                
                from processing.services.pdf_splitter import PDFSplitter
                splitter = PDFSplitter(dpi=150)
                booklets = splitter.split_exam(exam)
                
                # Create Copy objects
                for booklet in booklets:
                    copy = Copy.objects.create(
                        exam=exam,
                        anonymous_id=str(uuid.uuid4())[:8].upper(),
                        status=Copy.Status.STAGING,
                        is_identified=False
                    )
                    copy.booklets.add(booklet)
                
                logger.info("Upload successful", extra={...})
                
                return Response({
                    **serializer.data,
                    "booklets_created": len(booklets),
                    "message": f"{len(booklets)} booklets created successfully"
                }, status=status.HTTP_201_CREATED)
                
        except Exception as e:
            # Cleanup uploaded file (transaction already rolled back)
            if exam and exam.pdf_source:
                exam.pdf_source.delete(save=False)
            
            logger.error(f"Upload failed: {e}", exc_info=True)
            
            from core.utils.errors import safe_error_response
            return Response(
                safe_error_response(e, context="PDF processing", 
                                  user_message="Échec du traitement PDF. Veuillez vérifier que le fichier est valide."),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
```

### A2: Test Fixture Example

```python
# backend/exams/tests/fixtures/pdf_fixtures.py
import fitz

def create_valid_pdf(pages=4):
    """Generate a valid PDF with N pages."""
    doc = fitz.open()
    for i in range(pages):
        page = doc.new_page(width=595, height=842)  # A4 size
        page.insert_text((50, 50), f"Page {i+1}")
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes

def create_large_pdf(size_mb=51):
    """Generate a PDF exceeding size limit."""
    # Create PDF with padding to reach target size
    doc = fitz.open()
    page = doc.new_page()
    # Add large image or repeated content
    padding = b'0' * (size_mb * 1024 * 1024)
    # ... implementation ...
    return pdf_bytes
```

---

**End of Technical Specification**
