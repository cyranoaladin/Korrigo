# Product Requirements Document (PRD)
## Export Pronote CSV: Format, Encodage, Arrondis, Coefficients

**Version**: 1.0  
**Date**: 2026-01-31  
**Task ID**: ZF-AUD-10

---

## 1. Executive Summary

### 1.1 Objective
Create a robust, PRONOTE-compatible CSV export feature for exam grades that ensures frictionless import into PRONOTE without manual data corrections or format adjustments.

### 1.2 Success Criteria
- CSV exports are importable into PRONOTE without errors
- Format strictly adheres to PRONOTE specifications
- Admin-only access with proper audit trail
- Explicit error handling for missing or invalid data
- No data leakage beyond required fields

---

## 2. Current State Analysis

### 2.1 Existing Infrastructure

**Management Command**: `backend/exams/management/commands/export_pronote.py`
- Format: `INE;MATIERE;NOTE;COEFF;COMMENTAIRE`
- Delimiter: Semicolon (`;`)
- Decimal separator: Comma (`,`)
- Rounding: 2 decimal places
- Issues: 
  - References `Score` model that may not exist in current codebase
  - Coefficient hardcoded to "1"
  - No validation for missing INE

**API Endpoint**: `CSVExportView` at `/api/exams/<id>/export-csv/`
- Current permission: `IsTeacherOrAdmin` ❌ (should be admin-only)
- Format: Generic CSV (not PRONOTE format)
- Different column structure

### 2.2 Data Model
- **Student**: `ine`, `first_name`, `last_name`, `class_name`, `email`
- **Exam**: `name`, `date`, `grading_structure` (JSON)
- **Copy**: `exam`, `anonymous_id`, `student`, `is_identified`, `status`
- **Score** (in migrations): `scores_data` (JSON), `final_comment`

### 2.3 Documentation Inconsistencies
- Admin guide shows: `INE,MATIERE,NOTE,COEFFICIENT` (commas)
- Code implementation uses: `INE;MATIERE;NOTE;COEFF;COMMENTAIRE` (semicolons)
- **Resolution**: Semicolon is correct for French CSV standards

---

## 3. Requirements

### 3.1 Functional Requirements

#### FR-1: CSV Format Specification
**PRONOTE CSV Format** (strict):
```csv
INE;MATIERE;NOTE;COEFF;COMMENTAIRE
12345678901;MATHS;15,5;1,0;
98765432102;MATHS;12,0;1,0;
11223344503;MATHS;18,25;1,0;Excellent travail
```

**Field Specifications**:
- **INE**: Student national identifier (required, 11 characters alphanumeric)
- **MATIERE**: Subject name from `Exam.name` (required, uppercase recommended)
- **NOTE**: Grade on scale /20 (required, French decimal format with comma)
- **COEFF**: Coefficient for the exam (required, French decimal format with comma)
- **COMMENTAIRE**: Optional global comment from `Copy.global_appreciation`

#### FR-2: Encoding & Delimiters
- **Encoding**: UTF-8 with BOM (`utf-8-sig`) for Excel/PRONOTE compatibility
- **Delimiter**: Semicolon (`;`)
- **Decimal separator**: Comma (`,`)
- **Line ending**: CRLF (`\r\n`) for Windows compatibility
- **Quoting**: Minimal (only when field contains delimiter or newline)

#### FR-3: Rounding & Precision
- **Decimal places**: 2 places maximum (e.g., `15,50`)
- **Rounding method**: Half-up (standard mathematical rounding)
  - `15.5 → 15,50`
  - `15.555 → 15,56`
  - `15.0 → 15,00`
- **Whole numbers**: Display with 2 decimal places (e.g., `15 → 15,00`)

#### FR-4: Coefficient Handling
**Priority order** (first available wins):
1. Exam-level coefficient (if `Exam` model has `coefficient` field)
2. Subject-level default (configurable in admin settings)
3. Default fallback: `1,0`

**Future consideration**: Per-exam coefficient configuration UI (not in current scope)

#### FR-5: Data Validation
**Before export, system MUST validate**:
- All copies have `status = GRADED`
- All copies have `is_identified = True`
- All identified copies have valid `student.ine` (not null, not empty)
- All copies have valid score data

**Rejection criteria** (export fails with explicit error):
- Any copy with missing INE → Error: `"Cannot export: X copies missing student identification"`
- Any copy not in GRADED status → Error: `"Cannot export: X copies not yet graded"`
- No copies to export → Error: `"No graded copies found for this exam"`

**Warning criteria** (export succeeds but logs warning):
- Copies with `global_appreciation` containing delimiter → Sanitize and log warning

#### FR-6: API Endpoint Requirements
- **Route**: `POST /api/exams/<uuid:id>/export-pronote/`
- **Permission**: `IsAdminOnly` (admin group membership required)
- **HTTP Method**: POST (not GET, to prevent accidental exports via URL sharing)
- **Response**:
  - Success: `200 OK` with CSV file attachment
  - Validation failure: `400 Bad Request` with error details
  - Permission denied: `403 Forbidden`
  - Exam not found: `404 Not Found`
- **Rate limiting**: 10 exports per hour per admin user
- **Audit logging**: Log every export attempt (success/failure) with user, timestamp, exam ID

#### FR-7: Command-Line Interface
**Update existing command**: `python manage.py export_pronote <exam_id>`
- Add `--coefficient` option to override default
- Add `--output` option to save to file (default: stdout)
- Add `--validate-only` option to check without exporting
- Fix Score model reference issue

### 3.2 Non-Functional Requirements

#### NFR-1: Security
- ✅ Admin-only access (no teacher access)
- ✅ Audit trail for all exports (who, when, which exam)
- ✅ No data leakage: only export required PRONOTE fields
- ✅ Rate limiting to prevent abuse
- ❌ No sensitive data in filenames (use exam UUID, not student names)

#### NFR-2: Reliability
- Handle edge cases gracefully (missing data, special characters)
- Transaction safety (read-only operation)
- Idempotent (same export generates same output)

#### NFR-3: Usability
- Clear error messages in French (target audience)
- Download filename format: `export_pronote_<EXAM_NAME>_<DATE>.csv`
  - Example: `export_pronote_MATHS_BAC_BLANC_2026-03-15.csv`
- HTTP headers set correctly for browser download

#### NFR-4: Performance
- Export of 500 copies: < 5 seconds
- Export of 1000 copies: < 10 seconds

---

## 4. Out of Scope (Explicitly Not Included)

- ❌ UI for configuring exam coefficient (future enhancement)
- ❌ Bulk export of multiple exams at once
- ❌ Export scheduling/automation
- ❌ Email delivery of export
- ❌ Integration with PRONOTE API (only CSV file export)
- ❌ Support for custom grade scales (only /20 scale)
- ❌ Historical export tracking/versioning

---

## 5. Edge Cases & Special Handling

### 5.1 Special Characters in Data
- **Student name with delimiter**: Already handled by student identifier (INE)
- **Comment with semicolon**: Wrap in quotes: `"Comment; with semicolon"`
- **Comment with newline**: Replace with space
- **Comment with quote**: Escape with double quote: `"He said ""hello"""`

### 5.2 Missing or Invalid Data

| Condition | Action |
|-----------|--------|
| Copy not identified | **Reject export** with error message |
| Student missing INE | **Reject export** with error message |
| Copy not graded | **Reject export** with error message |
| Missing score data | **Reject export** with error message |
| Empty comment field | Export empty string (valid) |
| Null coefficient | Use default `1,0` |

### 5.3 Typical Values

| Field | Typical Example | Edge Case |
|-------|----------------|-----------|
| NOTE | `15,5` | `0,00`, `20,00` |
| COEFF | `1,0` | `0,5`, `2,0` |
| INE | `12345678901` | `1234567890A` (alphanumeric allowed) |

---

## 6. User Stories

### US-1: Admin exports grades for PRONOTE import
**As** an admin,  
**I want** to export exam grades in PRONOTE CSV format,  
**So that** I can import them into PRONOTE without manual corrections.

**Acceptance Criteria**:
- Click "Export PRONOTE" button on exam detail page
- Download CSV file with correct format
- Import CSV into PRONOTE without errors
- All grades appear correctly in PRONOTE

### US-2: Admin prevented from exporting incomplete exam
**As** an admin,  
**I want** to be prevented from exporting an exam with ungraded or unidentified copies,  
**So that** I don't accidentally import incomplete data into PRONOTE.

**Acceptance Criteria**:
- Export button disabled if exam has ungraded copies
- Clear error message: "Cannot export: 5 copies not yet graded"
- Tooltip shows which copies are incomplete

### US-3: Admin troubleshoots export issues via audit log
**As** an admin,  
**I want** to see a log of all export attempts,  
**So that** I can verify who exported what and when.

**Acceptance Criteria**:
- Audit log shows: timestamp, user, exam, status (success/failure)
- Accessible from admin dashboard
- Filterable by date, user, exam

---

## 7. Technical Decisions & Assumptions

### 7.1 Assumptions
1. **PRONOTE version**: Assumes modern PRONOTE (2020+) that supports UTF-8 CSV
2. **Score model**: Assumes `Copy.scores` relationship exists or will be fixed
3. **Coefficient source**: Assumes coefficient is exam-level (not per-student)
4. **Grade scale**: Assumes all grades are on /20 scale (French standard)

### 7.2 Design Decisions

| Decision | Rationale |
|----------|-----------|
| POST instead of GET | Prevents accidental exports, better audit trail |
| Admin-only permission | Sensitive operation, aligns with RGPD compliance |
| UTF-8 with BOM | Ensures Excel/PRONOTE compatibility on Windows |
| Strict validation | Prevents data quality issues in PRONOTE |
| 2 decimal places | PRONOTE standard, matches French grading precision |

---

## 8. Dependencies & Constraints

### 8.1 Dependencies
- Django >= 4.2
- PostgreSQL 15
- Python CSV library (stdlib)
- Django REST Framework
- Existing permission system (`core.auth.IsAdminOnly`)

### 8.2 Constraints
- Must maintain backward compatibility with existing management command
- Must not break existing generic CSV export for teachers
- Must respect existing RBAC (role-based access control) system

---

## 9. Success Metrics

### 9.1 Functional Metrics
- ✅ 100% of exports importable into PRONOTE without errors
- ✅ 0% data loss or corruption
- ✅ 100% of invalid export attempts blocked with clear error messages

### 9.2 Security Metrics
- ✅ 100% of export attempts logged in audit trail
- ✅ 0 unauthorized access attempts succeed

### 9.3 Usability Metrics
- ✅ Admin can export exam in < 3 clicks
- ✅ Error messages are actionable (tell user what to fix)

---

## 10. Testing Requirements

### 10.1 Unit Tests
- CSV format validation (delimiter, encoding, decimal separator)
- Rounding logic (typical values, edge cases)
- Field mapping (INE, MATIERE, NOTE, COEFF, COMMENTAIRE)
- Missing data handling (validation errors)

### 10.2 Integration Tests
- End-to-end export flow (API endpoint)
- Permission checks (admin-only)
- Audit logging
- File download headers

### 10.3 Manual Testing
- Import exported CSV into actual PRONOTE instance
- Verify grades appear correctly
- Test with special characters (accents, quotes, semicolons)
- Test with edge cases (whole numbers, zeros, max grades)

### 10.4 Test Data
**Typical values**:
- INE: `12345678901`, `98765432102`
- Names: `DUPONT Jean`, `MARTIN Sophie`
- Grades: `15.5`, `12.0`, `18.25`, `0.0`, `20.0`
- Comments: Empty, short text, text with accents, text with quotes

**Edge cases**:
- Grade: `0.00`, `20.00`, `19.995` (rounds to 20.00)
- Comment with semicolon: `Bien; mais peut mieux faire`
- Missing INE (should reject export)

---

## 11. Open Questions & Clarifications Needed

### 11.1 Clarifications Needed from User
1. **Coefficient configuration**: Should admins be able to configure exam coefficient via UI, or is default `1,0` always acceptable?
   - **Assumption**: Default `1,0` is acceptable for MVP; UI configuration is future enhancement
   
2. **PRONOTE version**: Which version of PRONOTE is the target school using?
   - **Assumption**: Modern version (2020+) with UTF-8 support

3. **Reference CSV**: The task mentioned "Référence format CSV" but the link was not accessible. Should we validate against a specific PRONOTE documentation?
   - **Assumption**: Standard PRONOTE CSV format as documented in French educational forums

### 11.2 Technical Clarifications
1. **Score model**: The `Score` model exists in migrations but not in current `grading/models.py`. This needs investigation.
   - **Action**: Technical Specification phase will investigate and document solution

2. **Coefficient field**: Should we add a `coefficient` field to `Exam` model, or use a different approach?
   - **Decision**: Will be addressed in Technical Specification

---

## 12. Risks & Mitigations

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| PRONOTE rejects CSV due to format mismatch | High | Medium | Validate format against PRONOTE docs; manual test import |
| Score model missing causes runtime errors | High | High | Investigate in tech spec; fix or implement workaround |
| Special characters break CSV parsing | Medium | Medium | Comprehensive CSV escaping; test with real data |
| Admin exports wrong exam by mistake | Medium | Low | Confirmation dialog; clear exam name in download |

---

## 13. Future Enhancements (Post-MVP)

1. **Coefficient UI configuration**: Admin interface to set exam coefficient
2. **Bulk export**: Export multiple exams at once (ZIP of CSV files)
3. **Export templates**: Customizable export formats for different grading systems
4. **Automated export**: Schedule exports and email to admin
5. **PRONOTE API integration**: Direct push to PRONOTE (if API available)
6. **Historical exports**: Track and version exports over time

---

## Appendix A: CSV Format Examples

### A.1 Complete Example
```csv
INE;MATIERE;NOTE;COEFF;COMMENTAIRE
12345678901;MATHEMATIQUES;15,50;1,0;Bon travail
98765432102;MATHEMATIQUES;12,00;1,0;
11223344503;MATHEMATIQUES;18,25;1,0;Excellent
44556677804;MATHEMATIQUES;09,75;1,0;Peut mieux faire
```

### A.2 Edge Cases Example
```csv
INE;MATIERE;NOTE;COEFF;COMMENTAIRE
12345678901;MATHS;20,00;1,0;
98765432102;MATHS;00,00;1,0;Absent
11223344503;MATHS;19,99;2,0;
44556677804;MATHS;10,50;0,5;"Commentaire avec ; et ""guillemets"""
```

---

## Appendix B: Related Documentation
- Admin Guide: `docs/admin/GUIDE_UTILISATEUR_ADMIN.md` (Section 6.1)
- Operational Procedures: `docs/admin/PROCEDURES_OPERATIONNELLES.md` (Section 2.8)
- API Documentation: `docs/API_REFERENCE.md` (to be updated)
- CSV Import Service: `backend/students/services/csv_import.py` (reference for CSV handling)

---

**Document Status**: Ready for Technical Specification  
**Next Step**: Create Technical Specification Document (`spec.md`)
