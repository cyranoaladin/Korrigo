# PRONOTE CSV Export Implementation Plan

## Configuration
- **Artifacts Path**: `.zenflow/tasks/export-pronote-csv-format-encoda-2e50`
- **Task ID**: ZF-AUD-10
- **Based on**: `spec.md` v1.0

---

## Workflow Steps

### [x] Step: Requirements
<!-- chat-id: 09921a05-60d0-4d99-92ec-ce77ff9d6312 -->

Create a Product Requirements Document (PRD) based on the feature description.

**Status**: ✅ Completed
**Deliverable**: `requirements.md` (397 lines)

### [x] Step: Technical Specification
<!-- chat-id: 56c83e72-372d-41ba-bc4b-9edafacd744b -->

Create a technical specification based on the PRD.

**Status**: ✅ Completed
**Deliverable**: `spec.md` (954 lines)

### [x] Step: Planning
<!-- chat-id: 805d5a5a-1de0-4b22-93f8-823a31deaa05 -->

Create a detailed implementation plan based on `spec.md`.

**Status**: ✅ Completed
**Deliverable**: This plan document

---

## Implementation Steps

### [x] Step 1: Create Service Layer Infrastructure
<!-- chat-id: 851f8498-6723-4db3-a64e-a0d44a1d52ed -->

Create the PRONOTE export service with core functionality.

**Files to create**:
- `backend/exams/services/__init__.py`
- `backend/exams/services/pronote_export.py`

**Tasks**:
- [x] Create services directory structure
- [x] Implement `PronoteExporter` class with:
  - `__init__(exam, coefficient)` 
  - `format_decimal_french(value, precision)` - convert float to French decimal format
  - `sanitize_comment(comment)` - clean CSV comments
  - `_calculate_max_score(grading_structure)` - extract max score from JSON

**Verification**:
```bash
python -m pytest backend/exams/tests/test_pronote_export.py::test_format_decimal_french -v
python -m pytest backend/exams/tests/test_pronote_export.py::test_sanitize_comment -v
```

**References**: 
- spec.md sections 3.2, 3.7, 3.8
- Existing CSV handling in `students/services/csv_import.py`

---

### [x] Step 2: Implement Grade Calculation Logic
<!-- chat-id: 33a174ee-5059-48e1-b541-2527913d82e9 -->

Implement annotation-based grade calculation since Score model doesn't exist.

**Files to modify**:
- `backend/exams/services/pronote_export.py`

**Tasks**:
- [x] Implement `calculate_copy_grade(copy)` method:
  - Sum `annotation.score_delta` values from `copy.annotations`
  - Parse `exam.grading_structure` JSON to get max_score
  - Scale to /20 if needed
  - Clamp result to [0, 20] range
- [x] Add error handling for edge cases (no annotations, invalid structure)

**Verification**:
```bash
python -m pytest backend/exams/tests/test_pronote_export.py::test_calculate_grade -v
```

**References**:
- spec.md section 3.6
- `grading/models.py:60` - Annotation.score_delta field

---

### [x] Step 3: Implement Export Validation Logic
<!-- chat-id: e0f50cf6-b31f-40b3-a707-40f52bf4926c -->

Add pre-export validation to ensure data quality.

**Files to modify**:
- `backend/exams/services/pronote_export.py`

**Tasks**:
- [x] Implement `validate_export_eligibility()` method:
  - Check for graded copies (status=GRADED)
  - Validate all copies are identified (is_identified=True)
  - Verify all students have valid INE
  - Detect comments with delimiter (warning)
- [x] Return structured validation result with errors and warnings
- [x] Use French error messages

**Verification**:
```bash
python -m pytest backend/exams/tests/test_pronote_export.py::test_validate_* -v
```

**References**:
- spec.md section 3.4
- requirements.md section 3.1 FR-5 (Data Validation)

---

### [x] Step 4: Implement CSV Generation
<!-- chat-id: 3529f9ae-3e03-4349-8e53-3c80d58c6192 -->

Build PRONOTE-format CSV generator.

**Files to modify**:
- `backend/exams/services/pronote_export.py`

**Tasks**:
- [ ] Implement `generate_csv()` method:
  - Use UTF-8 BOM (`\ufeff`) for Excel compatibility
  - Delimiter: semicolon (`;`)
  - Decimal separator: comma (`,`)  
  - Line ending: CRLF (`\r\n`)
  - Header: `INE;MATIERE;NOTE;COEFF;COMMENTAIRE`
- [ ] Query graded, identified copies with proper joins (select_related, prefetch_related)
- [ ] Format each row with proper decimal/comment sanitization
- [ ] Return CSV content and warnings list

**Verification**:
```bash
python -m pytest backend/exams/tests/test_pronote_export.py::test_csv_generation -v
```

**References**:
- spec.md section 3.5
- requirements.md section 3.1 FR-1, FR-2

---

### [x] Step 5: Write Unit Tests for Service Layer
<!-- chat-id: a2fdd763-779e-44a0-bb82-87cd259e0d79 -->

Create comprehensive unit tests for PronoteExporter.

**Files to create**:
- `backend/exams/tests/test_pronote_export.py`

**Tasks**:
- [ ] Test `format_decimal_french()`:
  - Typical: 15.5 → "15,50"
  - Whole: 12.0 → "12,00"
  - Rounding: 15.555 → "15,56"
- [ ] Test `sanitize_comment()`:
  - Delimiter handling
  - Newline replacement
  - Length limiting (500 chars)
  - CSV injection prevention
- [ ] Test `calculate_copy_grade()`:
  - Valid annotations with deltas
  - Scaling from different max scores
  - Clamping to [0, 20]
- [ ] Test `validate_export_eligibility()`:
  - Missing INE rejection
  - Unidentified copies rejection
  - No graded copies error
- [ ] Test `generate_csv()`:
  - Format validation
  - Encoding (UTF-8 BOM)
  - Delimiter/decimal separator

**Verification**:
```bash
python -m pytest backend/exams/tests/test_pronote_export.py -v --tb=short
```

**References**:
- spec.md section 5.1
- Existing test patterns in `exams/tests/`

---

### [x] Step 6: Create API Endpoint
<!-- chat-id: a86b97b4-3df8-4eae-b0a0-1c51dfe38d52 -->

Add admin-only PRONOTE export endpoint.

**Files to modify**:
- `backend/exams/views.py`
- `backend/exams/urls.py`

**Tasks**:
- [ ] Create `PronoteExportView(APIView)` in views.py:
  - Permission: `IsAdminOnly` (from core.auth or exams.permissions)
  - Rate limit: 10/hour per user via `@maybe_ratelimit`
  - Method: POST only
- [ ] Implement `post(request, id)`:
  - Get exam by UUID or 404
  - Parse optional `coefficient` from request.data
  - Create PronoteExporter instance
  - Validate export eligibility → 400 if invalid
  - Generate CSV
  - Log audit trail via `log_audit()`
  - Return CSV as file download with proper headers
- [ ] Add URL route: `path('<uuid:id>/export-pronote/', PronoteExportView.as_view())`

**Verification**:
```bash
python -m pytest backend/exams/tests/test_pronote_export_api.py -v
```

**References**:
- spec.md sections 3.1, 3.3
- `exams/views.py:265` - CSVExportView pattern
- `core/utils/audit.py` - log_audit function
- `core/utils/ratelimit.py` - maybe_ratelimit decorator

---

### [ ] Step 7: Write API Integration Tests

Test the export endpoint with API client.

**Files to create**:
- `backend/exams/tests/test_pronote_export_api.py`

**Tasks**:
- [ ] Test permission requirements:
  - Admin can export → 200
  - Teacher cannot export → 403
  - Anonymous cannot export → 401
- [ ] Test validation scenarios:
  - Missing INE → 400 with error message
  - Unidentified copies → 400
  - No graded copies → 400
- [ ] Test successful export:
  - Valid exam → 200 with CSV
  - Check Content-Type, Content-Disposition headers
  - Verify CSV format (BOM, delimiter, encoding)
- [ ] Test rate limiting:
  - 11th request within hour → 429
- [ ] Test audit logging:
  - Success/failure logged to AuditLog table
- [ ] Test special characters:
  - Accents in student names
  - Quotes in comments
  - Semicolons in comments

**Verification**:
```bash
python -m pytest backend/exams/tests/test_pronote_export_api.py -v --tb=short
```

**References**:
- spec.md section 5.2
- requirements.md section 9 (Testing Requirements)

---

### [ ] Step 8: Update Management Command

Refactor export_pronote command to use PronoteExporter service.

**Files to modify**:
- `backend/exams/management/commands/export_pronote.py`

**Tasks**:
- [ ] Remove Score model references (line 38-43)
- [ ] Import and use `PronoteExporter` service
- [ ] Add CLI arguments:
  - `--coefficient` (float, default=1.0)
  - `--output` (file path, optional)
  - `--validate-only` (flag)
- [ ] Implement new command flow:
  - Get exam by UUID
  - Create exporter with coefficient
  - Validate eligibility → print errors and exit if invalid
  - Print warnings to stderr
  - Generate CSV if not validate-only
  - Output to file or stdout
- [ ] Use UTF-8 with BOM for file output

**Verification**:
```bash
python manage.py export_pronote <exam_uuid> --validate-only
python manage.py export_pronote <exam_uuid> --output /tmp/test.csv
```

**References**:
- spec.md section 4
- Current implementation in `export_pronote.py:1-64`

---

### [ ] Step 9: Write Management Command Tests

Test CLI interface for export command.

**Files to create**:
- `backend/exams/tests/test_export_pronote_command.py`

**Tasks**:
- [ ] Test basic command execution:
  - Valid exam → success output
  - Invalid UUID → error message
- [ ] Test `--output` option:
  - File created with correct content
  - UTF-8 BOM present
- [ ] Test `--validate-only` option:
  - No CSV generated
  - Validation errors shown
- [ ] Test `--coefficient` option:
  - Custom coefficient appears in CSV
- [ ] Use Django's `call_command()` helper

**Verification**:
```bash
python -m pytest backend/exams/tests/test_export_pronote_command.py -v
```

**References**:
- spec.md section 5.3
- Django docs: testing management commands

---

### [ ] Step 10: Create Manual Testing Documentation

Document manual test procedures for PRONOTE import verification.

**Files to create**:
- `.zenflow/tasks/export-pronote-csv-format-encoda-2e50/audit.md`

**Tasks**:
- [ ] Document test cases:
  - **Format validation**: Check CSV structure matches spec
  - **Encoding test**: Verify UTF-8 BOM, CRLF line endings
  - **Decimal format**: Confirm comma separator (15,50 not 15.50)
  - **Special characters**: Test accents, quotes, semicolons
  - **Edge values**: Test 0.00, 20.00, 19.995 rounding
  - **PRONOTE import**: Actual import test (if PRONOTE available)
  - **Rate limiting**: Verify 10/hour limit
  - **Audit log**: Check AuditLog entries
- [ ] Include test data examples
- [ ] Document expected vs actual results template

**References**:
- spec.md section 5.4
- requirements.md section 10 (Testing Requirements)

---

### [ ] Step 11: Run Full Test Suite

Execute all tests and verify coverage.

**Tasks**:
- [ ] Run unit tests:
  ```bash
  python -m pytest backend/exams/tests/test_pronote_export.py -v
  ```
- [ ] Run API tests:
  ```bash
  python -m pytest backend/exams/tests/test_pronote_export_api.py -v
  ```
- [ ] Run command tests:
  ```bash
  python -m pytest backend/exams/tests/test_export_pronote_command.py -v
  ```
- [ ] Run all exams tests to ensure no regressions:
  ```bash
  python -m pytest backend/exams/tests/ -v
  ```
- [ ] Check test coverage (if configured):
  ```bash
  pytest backend/exams/ --cov=exams --cov-report=term-missing
  ```

**Success Criteria**:
- All tests passing
- No regressions in existing tests
- Coverage for new code > 90%

---

### [ ] Step 12: Code Quality & Linting

Run code quality tools if configured in project.

**Tasks**:
- [ ] Check if ruff/flake8 is configured:
  ```bash
  ruff check backend/exams/services/pronote_export.py backend/exams/views.py
  ```
- [ ] Check if mypy is configured:
  ```bash
  mypy backend/exams/services/pronote_export.py
  ```
- [ ] Fix any linting errors
- [ ] Ensure code follows project conventions

**Note**: Skip if linting tools not configured in project

**References**:
- spec.md section 10.3

---

### [ ] Step 13: Manual Verification

Perform manual end-to-end testing.

**Tasks**:
- [ ] Create test exam with:
  - Graded copies with annotations
  - Student records with valid INE
  - Comments with special characters
- [ ] Test API endpoint:
  - Export via POST /api/exams/<id>/export-pronote/
  - Verify download headers
- [ ] Test management command:
  - Export to file: `python manage.py export_pronote <uuid> --output test.csv`
  - Validate-only mode
- [ ] Inspect generated CSV:
  - Open in text editor → verify UTF-8 BOM, semicolons, commas
  - Open in Excel → check proper display
  - (If PRONOTE available) Import into PRONOTE → verify success
- [ ] Document results in `audit.md`

**References**:
- spec.md section 10.2
- requirements.md Appendix A (CSV Format Examples)

---

## Test Commands Summary

**Unit Tests**:
```bash
python -m pytest backend/exams/tests/test_pronote_export.py -v
```

**API Tests**:
```bash
python -m pytest backend/exams/tests/test_pronote_export_api.py -v
```

**Command Tests**:
```bash
python -m pytest backend/exams/tests/test_export_pronote_command.py -v
```

**All Tests**:
```bash
python -m pytest backend/exams/tests/ -v
```

**Linting** (if configured):
```bash
ruff check backend/exams/
```

---

## Deliverables Checklist

- [ ] `backend/exams/services/pronote_export.py` (~300 lines)
- [ ] `backend/exams/views.py` (PronoteExportView added, ~80 lines)
- [ ] `backend/exams/urls.py` (1 route added)
- [ ] `backend/exams/management/commands/export_pronote.py` (refactored, ~100 lines)
- [ ] `backend/exams/tests/test_pronote_export.py` (~200 lines)
- [ ] `backend/exams/tests/test_pronote_export_api.py` (~250 lines)
- [ ] `backend/exams/tests/test_export_pronote_command.py` (~150 lines)
- [ ] `.zenflow/tasks/export-pronote-csv-format-encoda-2e50/audit.md` (manual test documentation)

**Estimated Total**: ~1100 lines of code

---

## Success Criteria

✅ **Functional**:
- CSV format matches PRONOTE specification exactly
- UTF-8 BOM, semicolon delimiter, comma decimal separator, CRLF line endings
- Admin-only access enforced
- Validation prevents export of incomplete data
- Grade calculation works correctly from annotations

✅ **Security**:
- Admin-only permission via IsAdminOnly
- Rate limiting: 10 exports/hour per user
- Audit logging for all export attempts
- No data leakage beyond required fields

✅ **Quality**:
- All unit tests passing (>90% coverage)
- All integration tests passing
- No regressions in existing tests
- Code follows project conventions
- Manual PRONOTE import successful (if PRONOTE available)

---

**Plan Status**: ✅ Complete - Ready for Implementation
**Next Action**: Begin Step 1 (Create Service Layer Infrastructure)
