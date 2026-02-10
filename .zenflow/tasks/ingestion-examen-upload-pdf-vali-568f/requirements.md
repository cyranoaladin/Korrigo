# Product Requirements Document: PDF Exam Upload Validation & Error Handling

**Task ID**: ZF-AUD-03  
**Title**: INGESTION EXAMEN: UPLOAD PDF + VALIDATIONS + ERREURS (Backend)  
**Date**: January 31, 2026  
**Status**: Requirements  

---

## 1. Executive Summary

### Objective
Secure and validate the primary system entry point: PDF exam upload with strict validations (size, MIME type, pages, integrity) and comprehensive error handling to ensure system stability and data integrity.

### Scope
- **Endpoint**: `POST /api/exams/upload/`
- **Storage**: `media/exams/source/` and derived paths
- **Models**: Exam, Booklet, Copy creation with IMPORT event
- **Validations**: File size, MIME type, integrity, page count, path traversal protection
- **Error Handling**: User-friendly messages for all failure scenarios
- **Testing**: Comprehensive test coverage for valid and invalid scenarios
- **Atomicity**: No orphaned database records on processing failures

---

## 2. Current State Analysis

### 2.1 Existing Implementation

#### Upload Endpoint
- **Location**: `backend/exams/views.py::ExamUploadView`
- **Method**: POST
- **Permissions**: `IsTeacherOrAdmin`
- **Rate Limiting**: 20 requests/hour per user
- **Parsers**: MultiPartParser, FormParser

#### Current Validation Layers
1. **Extension Validation**: `.pdf` only (Django FileExtensionValidator)
2. **Size Validation**: Maximum 50 MB (`validate_pdf_size`)
3. **Empty File Check**: Reject 0-byte files (`validate_pdf_not_empty`)
4. **MIME Type Check**: Verify actual PDF signature using python-magic (`validate_pdf_mime_type`)
5. **Integrity Check**: PyMuPDF validation + max 500 pages (`validate_pdf_integrity`)

#### Processing Flow
```
1. Upload PDF → Serializer validation
2. Save Exam record with pdf_source
3. PDFSplitter.split_exam() → Create Booklets
4. Create Copy objects in STAGING status
5. Return success response with booklet count
```

#### Storage Structure
```
media/
├── exams/source/          # Original uploaded PDFs
├── booklets/
│   └── {exam_id}/
│       └── {booklet_id}/
│           ├── page_001.png
│           ├── page_002.png
│           └── ...
└── copies/
    ├── source/            # Individual copy PDFs
    └── final/             # Graded/annotated PDFs
```

### 2.2 Identified Gaps

1. **Atomicity Concerns**
   - If PDFSplitter fails after Exam creation, orphaned Exam record remains
   - No explicit rollback mechanism in current implementation
   - Need to verify transaction handling

2. **Page Count Validation**
   - Pages per booklet divisibility not validated
   - User could upload 13-page PDF with pages_per_booklet=4
   - Need to clarify business rules for handling remainder pages

3. **Error Message Clarity**
   - Generic 500 errors for processing failures
   - Need specific user-facing messages for each error type
   - HTTP status codes need to be consistent

4. **Path Traversal Protection**
   - Django FileField inherently safe (sanitizes filenames)
   - Need to verify no custom path manipulation introduces vulnerabilities

5. **Timeout Handling**
   - Rasterization timeout not explicitly handled
   - Large PDFs might cause request timeouts
   - Need to verify behavior with 500-page PDFs at 150 DPI

6. **Test Coverage**
   - Validator unit tests exist (`test_pdf_validators.py`)
   - Missing integration tests for upload endpoint
   - No tests for atomicity/rollback scenarios
   - No fixture PDFs for reproducible testing

---

## 3. Requirements

### 3.1 Functional Requirements

#### FR-1: File Upload Validation
**Priority**: P0 (Critical)

The system MUST validate all uploaded PDF files through the following checks:

1. **Extension Check**
   - MUST accept only `.pdf` extension
   - MUST reject: `.txt`, `.exe`, `.docx`, etc.
   - Error: HTTP 400 with message "Invalid file extension. Only PDF files are allowed."

2. **Size Check**
   - MUST accept files ≤ 50 MB
   - MUST reject files > 50 MB
   - Error: HTTP 413 (Payload Too Large) with message "File too large. Maximum size: 50 MB. Your file: {size} MB."

3. **Empty File Check**
   - MUST reject 0-byte files
   - Error: HTTP 400 with message "Empty file. Please upload a valid PDF."

4. **MIME Type Check**
   - MUST verify actual file signature matches PDF MIME type
   - MUST reject text files renamed to `.pdf`
   - Error: HTTP 400 with message "Invalid file type. Expected PDF but received {detected_type}."

5. **Integrity Check**
   - MUST verify PDF structure with PyMuPDF
   - MUST reject corrupted PDFs
   - MUST reject PDFs with 0 pages
   - MUST reject PDFs with > 500 pages
   - Errors:
     - Corrupted: HTTP 400 "Corrupted or invalid PDF file."
     - Too many pages: HTTP 400 "PDF has {count} pages. Maximum allowed: 500 pages."

#### FR-2: Page Count Business Rules
**Priority**: P1 (High)

**Decision Required**: How to handle PDFs where total pages is not evenly divisible by `pages_per_booklet`?

**Options**:
1. **Strict Mode**: Reject upload if `total_pages % pages_per_booklet != 0`
   - Error: HTTP 400 "PDF has {total} pages which is not divisible by {ppb} pages per booklet. Expected multiple of {ppb}."
   
2. **Lenient Mode**: Accept and create smaller last booklet
   - Current implementation uses this approach
   - PDFSplitter handles remainder pages (line 88-89 in pdf_splitter.py)
   - Logs warning for partial booklets

**Recommendation**: **Lenient Mode** (Option 2)
- Real-world scans may have cover pages or partial booklets
- System already handles this correctly
- Add validation warnings but don't block upload

**Acceptance Criteria**:
- Document the behavior in user-facing messages
- Warn user if remainder pages detected
- Response: HTTP 201 with warning message "PDF uploaded successfully. Note: Last booklet has {n} pages instead of {ppb}."

#### FR-3: Atomicity Guarantee
**Priority**: P0 (Critical)

**Requirement**: Upload operation MUST be atomic - either fully succeed or fully fail with no partial state.

**Current Implementation Issues**:
```python
# In ExamUploadView.post()
exam = serializer.save()  # Exam saved to DB
try:
    booklets = splitter.split_exam(exam)  # If this fails, exam is orphaned
    # Create Copy objects
except Exception:
    # Exam already saved - ORPHANED!
    return error
```

**Required Fix**:
```python
try:
    with transaction.atomic():
        exam = serializer.save()
        booklets = splitter.split_exam(exam)
        # Create copies
        return success
except Exception as e:
    # Automatic rollback - no orphans
    return error
```

**Acceptance Criteria**:
- Upload failures MUST NOT leave Exam records in database
- Upload failures MUST NOT leave partial Booklet records
- Upload failures MUST NOT leave orphaned files in media/exams/source/
- All database operations wrapped in transaction.atomic()
- Test: Inject failure in split_exam() → verify no Exam created

#### FR-4: Error Handling & User Messages
**Priority**: P0 (Critical)

All error scenarios MUST provide clear, actionable messages to frontend users.

**Error Scenarios & Expected Responses**:

| Scenario | HTTP Status | Error Message | Action |
|----------|-------------|---------------|--------|
| No file provided | 400 | "No PDF file uploaded. Please select a file." | Retry with file |
| Wrong extension (.txt) | 400 | "Invalid file type. Only PDF files are accepted." | Upload PDF |
| File > 50 MB | 413 | "File too large ({size} MB). Maximum: 50 MB." | Compress or split |
| Empty file (0 bytes) | 400 | "Empty file. Please upload a valid PDF." | Check file |
| Fake PDF (renamed .txt) | 400 | "Invalid file format. The file is not a valid PDF." | Upload real PDF |
| Corrupted PDF | 400 | "PDF file is corrupted or unreadable." | Re-export PDF |
| 0 pages | 400 | "PDF contains no pages." | Check source |
| > 500 pages | 400 | "PDF too large ({n} pages). Maximum: 500 pages." | Split into multiple |
| Processing timeout | 504 | "PDF processing timeout. Please try a smaller file." | Reduce size/pages |
| Disk space full | 500 | "Server error. Please contact support." (logged) | Admin action |
| Database error | 500 | "Server error. Please try again later." (logged) | Admin action |

**Implementation**:
- Use `safe_error_response()` from `core.utils.errors`
- Production: Generic messages for 500 errors
- Development: Full stack traces for debugging
- All errors logged with request context

#### FR-5: Path Traversal Protection
**Priority**: P0 (Critical)

**Requirement**: System MUST prevent path traversal attacks via filename manipulation.

**Current Protection**:
- Django FileField automatically sanitizes filenames
- `upload_to='exams/source/'` is static, not user-controlled
- No custom path manipulation in codebase

**Acceptance Criteria**:
- Test upload with filename: `../../../../etc/passwd.pdf`
- Verify file saved as `passwd.pdf` in `media/exams/source/`
- No directory traversal occurs
- Document that Django handles this automatically

#### FR-6: Storage Event Logging
**Priority**: P1 (High)

**Requirement**: Log all upload events for audit trail.

**Events to Log**:
- Upload initiated (user, timestamp, filename, size)
- Validation failures (which validator, reason)
- Processing start (exam_id, pages, booklets)
- Processing completion (duration, booklet count)
- Processing failures (exception type, context)

**Log Format** (using structured logging):
```json
{
  "timestamp": "2026-01-31T14:18:55Z",
  "level": "INFO",
  "event": "exam_upload_success",
  "user_id": 123,
  "exam_id": "uuid",
  "filename": "bac_math_2026.pdf",
  "size_mb": 12.5,
  "pages": 100,
  "booklets_created": 25,
  "processing_time_ms": 3450
}
```

### 3.2 Non-Functional Requirements

#### NFR-1: Performance
- Upload validation MUST complete within 5 seconds for 50MB files
- PDF splitting MUST handle 500 pages within 60 seconds
- System MUST support concurrent uploads (5 teachers simultaneously)
- Rasterization timeout: 60 seconds per PDF

#### NFR-2: Security
- Rate limiting: 20 uploads per hour per user (existing)
- Authentication required: Teacher or Admin roles only
- No sensitive data in error messages (production)
- File permissions: Uploaded files readable only by application user

#### NFR-3: Reliability
- 99.9% upload success rate for valid PDFs
- Zero data loss on failures (atomic transactions)
- Graceful degradation: If MIME detection fails, continue with other validations
- Automatic cleanup of temporary files on errors

---

## 4. Testing Requirements

### 4.1 Unit Tests

**File**: `backend/exams/tests/test_upload_endpoint.py` (new)

**Required Test Cases**:

1. **Valid Upload Success**
   - `test_upload_valid_pdf_small()`: 4-page PDF, 4 pages/booklet → 1 booklet
   - `test_upload_valid_pdf_large()`: 100-page PDF, 4 pages/booklet → 25 booklets
   - `test_upload_valid_pdf_remainder()`: 13-page PDF, 4 pages/booklet → 4 booklets (last has 1 page)

2. **Validation Failures**
   - `test_upload_no_file()`: No file provided → 400
   - `test_upload_wrong_extension()`: `.txt` file → 400
   - `test_upload_file_too_large()`: 51 MB file → 413
   - `test_upload_empty_file()`: 0 bytes → 400
   - `test_upload_fake_pdf()`: Text file renamed to `.pdf` → 400
   - `test_upload_corrupted_pdf()`: Invalid PDF structure → 400
   - `test_upload_too_many_pages()`: 501-page PDF → 400

3. **Atomicity Tests**
   - `test_upload_processing_failure_no_orphan()`: Mock split_exam() failure → No Exam in DB
   - `test_upload_booklet_creation_failure_rollback()`: Mock Copy.create() failure → Rollback
   - `test_upload_disk_full_no_partial_files()`: Mock storage full → No files left

4. **Authentication/Authorization**
   - `test_upload_anonymous_user_rejected()`: Not authenticated → 401
   - `test_upload_student_role_rejected()`: Student user → 403
   - `test_upload_teacher_role_allowed()`: Teacher user → 201
   - `test_upload_admin_role_allowed()`: Admin user → 201

5. **Rate Limiting**
   - `test_upload_rate_limit_enforced()`: 21st request/hour → 429

### 4.2 Integration Tests

**File**: `backend/exams/tests/test_upload_integration.py` (new)

**Required Test Cases**:
1. `test_upload_end_to_end_workflow()`: Upload → Booklets → Copies → Database verification
2. `test_upload_concurrent_users()`: 3 users upload simultaneously → All succeed
3. `test_upload_storage_verification()`: Verify files in correct media paths

### 4.3 Test Fixtures

**Required Fixtures** (in `backend/exams/tests/fixtures/`):

| Fixture | Description | Size | Pages | Expected Result |
|---------|-------------|------|-------|-----------------|
| `valid_small.pdf` | Valid 4-page PDF | 100 KB | 4 | Success |
| `valid_large.pdf` | Valid 100-page PDF | 5 MB | 100 | Success |
| `valid_remainder.pdf` | Valid 13-page PDF | 500 KB | 13 | Success (warning) |
| `invalid_empty.pdf` | 0-byte file | 0 B | 0 | 400 error |
| `invalid_fake.txt` | Text file renamed | 1 KB | 0 | 400 error |
| `invalid_corrupted.pdf` | Corrupted PDF | 50 KB | N/A | 400 error |
| `invalid_large_size.pdf` | 51 MB PDF | 51 MB | 100 | 413 error |
| `invalid_too_many_pages.pdf` | 501-page PDF | 40 MB | 501 | 400 error |

**Fixture Generation Script**:
```bash
# Create test fixtures
python backend/exams/tests/generate_fixtures.py
```

---

## 5. Acceptance Criteria

### 5.1 Validation Success Criteria

✅ **Upload succeeds** when:
- File is valid PDF
- Size ≤ 50 MB
- Pages ≤ 500
- MIME type = application/pdf
- PDF structure valid
- User authenticated as Teacher/Admin

Response:
```json
{
  "id": "exam-uuid",
  "name": "Bac Math 2026",
  "date": "2026-05-20",
  "booklets_created": 25,
  "message": "25 booklets created successfully"
}
```

### 5.2 Validation Failure Criteria

❌ **Upload fails** with appropriate HTTP status and message for:
- Invalid file type
- File too large
- Corrupted PDF
- Too many pages
- Authentication failure
- Rate limit exceeded

### 5.3 Atomicity Criteria

✅ **No zombie records** when:
- PDF splitting fails
- Booklet creation fails
- Copy creation fails
- Rasterization timeout
- Disk space exhausted

**Verification**:
```python
# Before upload
exam_count_before = Exam.objects.count()
booklet_count_before = Booklet.objects.count()

# Upload fails (any reason)
response = client.post('/api/exams/upload/', {'pdf_source': bad_file})
assert response.status_code >= 400

# After failed upload
assert Exam.objects.count() == exam_count_before  # No new exams
assert Booklet.objects.count() == booklet_count_before  # No new booklets
```

### 5.4 Error Message Criteria

✅ **User-friendly messages** that:
- Clearly state what went wrong
- Suggest how to fix the problem
- Don't expose internal details (production)
- Are translated (French)

---

## 6. Implementation Notes

### 6.1 Database Transaction Wrapping

**Required Change** in `backend/exams/views.py`:

```python
from django.db import transaction

class ExamUploadView(APIView):
    @method_decorator(maybe_ratelimit(key='user', rate='20/h', method='POST', block=True))
    def post(self, request, *args, **kwargs):
        serializer = ExamSerializer(data=request.data)
        if serializer.is_valid():
            try:
                with transaction.atomic():  # CRITICAL: Wrap all DB ops
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
                    
                    return Response({
                        **serializer.data,
                        "booklets_created": len(booklets),
                        "message": f"{len(booklets)} booklets created successfully"
                    }, status=status.HTTP_201_CREATED)
                    
            except Exception as e:
                # Automatic rollback on any exception
                logger.error(f"Upload failed: {e}", exc_info=True)
                return Response(
                    safe_error_response(e, context="PDF upload", 
                                      user_message="Upload failed. Please verify your PDF is valid."),
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
```

### 6.2 File Cleanup on Errors

**Issue**: If upload saves file but transaction rolls back, orphaned file remains in media/exams/source/

**Solution**: Use Django's file field cleanup or manual cleanup in exception handler.

```python
except Exception as e:
    # If exam was partially created, clean up its file
    if 'exam' in locals() and exam.pdf_source:
        exam.pdf_source.delete(save=False)
    raise
```

### 6.3 Improved Error Messages

**Create** `backend/exams/exceptions.py`:

```python
class PDFValidationError(Exception):
    """Base class for PDF validation errors"""
    def __init__(self, user_message, http_status=400):
        self.user_message = user_message
        self.http_status = http_status
        super().__init__(user_message)

class PDFTooLargeError(PDFValidationError):
    def __init__(self, size_mb):
        super().__init__(
            f"File too large ({size_mb:.1f} MB). Maximum: 50 MB.",
            http_status=413
        )

class PDFCorruptedError(PDFValidationError):
    def __init__(self):
        super().__init__("PDF file is corrupted or unreadable.")
```

---

## 7. Out of Scope

The following are explicitly **NOT** in scope for this task:

- ❌ Frontend changes (error display handled by existing error handling)
- ❌ PDF content analysis (OCR, header detection) - separate task
- ❌ Antivirus scanning (ClamAV integration) - optional future enhancement
- ❌ Async/Celery processing - current sync processing is acceptable for MVP
- ❌ UI/UX improvements to upload interface
- ❌ Migration to S3/cloud storage
- ❌ PDF compression or optimization
- ❌ Multi-file batch upload

---

## 8. Open Questions & Decisions

### Q1: Page Count Divisibility
**Question**: Should we reject PDFs where `total_pages % pages_per_booklet != 0`?

**Decision**: **Lenient mode** - Accept and create smaller last booklet with warning message.

**Rationale**: Real-world scanning produces variable page counts (cover pages, partial scans). Current implementation handles this correctly.

### Q2: File Cleanup on Rollback
**Question**: Should we auto-delete uploaded files when transactions roll back?

**Decision**: **Yes** - Delete file in exception handler to prevent orphaned files.

**Implementation**: Add cleanup in exception handler before re-raising.

### Q3: Test Fixture Maintenance
**Question**: How to maintain test PDF fixtures in version control?

**Decision**: **Generate fixtures programmatically** using PyMuPDF in test setup.

**Rationale**: Binary PDFs in git increase repo size. Generated fixtures are consistent and reproducible.

---

## 9. Success Metrics

After implementation, the following metrics should be achieved:

1. **Validation Coverage**: 100% of invalid PDFs rejected with correct error codes
2. **Atomicity**: 0% orphaned Exam/Booklet records on failures
3. **Test Coverage**: ≥ 95% code coverage for upload endpoint and validators
4. **Error Clarity**: 100% of errors have user-facing messages (no raw exceptions)
5. **Performance**: < 5 seconds for validation of 50MB PDFs
6. **Reliability**: 0 data loss incidents in production

---

## 10. Dependencies

- **Existing**: PyMuPDF (1.23.26), python-magic (0.4.27)
- **Testing**: pytest, pytest-django, factory-boy (for fixtures)
- **None**: No new external dependencies required

---

## 11. Timeline

This is an audit/verification task, not new feature development:

1. **Day 1**: Review implementation, identify gaps → Create audit.md
2. **Day 2**: Write comprehensive tests → Fixtures + test suite
3. **Day 3**: Fix atomicity issues, improve error handling
4. **Day 4**: Run tests, document findings, verify HTTP contracts

**Total**: 2-3 days

---

## Appendix A: Current Validator Code

See:
- `backend/exams/validators.py` - All validation functions
- `backend/exams/tests/test_pdf_validators.py` - Existing unit tests
- `docs/technical/PDF_PROCESSING.md` - Detailed documentation

---

## Appendix B: References

- Django Validators: https://docs.djangoproject.com/en/4.2/ref/validators/
- PyMuPDF: https://pymupdf.readthedocs.io/
- ADR-003: Copy Status State Machine
- Security Rules: `.antigravity/rules/01_security_rules.md § 8.1`
