# PRONOTE CSV Export - Manual Testing Documentation

**Task**: ZF-AUD-10  
**Date**: 2026-02-01  
**Tester**: [Name]  
**Environment**: [Development / Staging / Production]

---

## Overview

This document provides manual testing procedures to verify the PRONOTE CSV export feature meets all requirements specified in `requirements.md` and `spec.md`.

---

## Prerequisites

### Test Data Setup

Before testing, ensure you have:

1. **Admin User Account**
   - Username: `admin_test`
   - Role: Admin (IsAdminOnly permission)

2. **Teacher User Account** (for permission testing)
   - Username: `teacher_test`
   - Role: Teacher

3. **Test Exam**
   - Name: "MATHEMATIQUES"
   - Date: 2026-02-01
   - Grading structure: /20 scale

4. **Test Students with Valid INE**
   ```
   Student 1:
     - INE: 11111111111
     - First Name: Alice
     - Last Name: Durand
     - Class: TS1
   
   Student 2:
     - INE: 22222222222
     - First Name: François
     - Last Name: Müller
     - Class: TS1
   ```

5. **Graded Copies**
   - Copy 1: Student 1, Grade 15.5/20, Comment: "Excellent travail"
   - Copy 2: Student 2, Grade 12.0/20, Comment: "Bien; peut mieux faire"

---

## Test Cases

### TC-1: Format Validation

**Objective**: Verify CSV format matches PRONOTE specification

**Steps**:
1. Login as admin
2. Export exam via API: `POST /api/exams/<exam_id>/export-pronote/`
3. Download the CSV file
4. Open in a text editor (NOT Excel)

**Expected Results**:
- [ ] File starts with UTF-8 BOM (`\ufeff` - appears as  in some editors)
- [ ] Header line: `INE;MATIERE;NOTE;COEFF;COMMENTAIRE`
- [ ] Delimiter: semicolon (`;`)
- [ ] Line endings: CRLF (`\r\n` - shows as `^M` in vim, or check with `cat -A`)
- [ ] No trailing semicolons or empty columns

**Example Expected Output**:
```csv
INE;MATIERE;NOTE;COEFF;COMMENTAIRE
11111111111;MATHEMATIQUES;15,50;1,0;Excellent travail
22222222222;MATHEMATIQUES;12,00;1,0;Bien; peut mieux faire
```

**Verification Commands**:
```bash
# Check BOM
hexdump -C export.csv | head -1
# Should show: ef bb bf (UTF-8 BOM)

# Check line endings
file export.csv
# Should show: "with CRLF line terminators"

# View raw file
cat -A export.csv
# Should show ^M at end of lines
```

**Status**: [ ] Pass / [ ] Fail  
**Notes**: _______________

---

### TC-2: Encoding Test

**Objective**: Verify UTF-8 encoding with BOM for Excel/PRONOTE compatibility

**Steps**:
1. Export exam with student names containing accents (François, Müller)
2. Open CSV in:
   - Text editor (UTF-8 mode)
   - Microsoft Excel
   - LibreOffice Calc
   - Import into PRONOTE (if available)

**Expected Results**:
- [ ] Text editor shows correct accents
- [ ] Excel displays accents correctly (without manual encoding selection)
- [ ] LibreOffice displays accents correctly
- [ ] PRONOTE imports without encoding errors

**Test Data**:
```
François Müller → Should appear as-is, not Fran├ºois or FranÃ§ois
```

**Status**: [ ] Pass / [ ] Fail  
**Notes**: _______________

---

### TC-3: Decimal Format

**Objective**: Verify French decimal format (comma separator, 2 decimal places)

**Steps**:
1. Export exam with various grade values:
   - 15.5 → "15,50"
   - 12.0 → "12,00"
   - 18.25 → "18,25"
   - 19.995 → "20,00" (rounding half-up)
   - 0.0 → "0,00"
   - 20.0 → "20,00"

**Expected Results**:
- [ ] All grades use comma (`,`) as decimal separator
- [ ] All grades have exactly 2 decimal places
- [ ] Whole numbers show ".00" (e.g., "15,00" not "15")
- [ ] Rounding follows half-up rule (19.995 → 20.00, not 19.99)
- [ ] Coefficient uses comma with 1 decimal place (e.g., "1,0" or "2,5")

**Status**: [ ] Pass / [ ] Fail  
**Notes**: _______________

---

### TC-4: Special Characters Handling

**Objective**: Verify CSV handles special characters, quotes, and delimiters

**Test Data**:
```
Comment 1: "Bon travail!" (quotes)
Comment 2: "Bien; peut mieux faire" (semicolon)
Comment 3: "Line 1\nLine 2" (newline)
Comment 4: "=FORMULA()" (CSV injection)
Comment 5: "Very long comment..." (500+ chars)
```

**Expected Results**:
- [ ] Quotes are properly escaped (doubled or CSV-quoted)
- [ ] Semicolons in comments don't break columns
- [ ] Newlines are replaced with spaces
- [ ] Leading `=`, `+`, `-`, `@` are removed (CSV injection prevention)
- [ ] Long comments are truncated to 500 chars + "..."

**Status**: [ ] Pass / [ ] Fail  
**Notes**: _______________

---

### TC-5: Edge Values

**Objective**: Test boundary conditions for grades

**Steps**:
1. Create copies with edge-case grades:
   - Negative score (should clamp to 0.00)
   - Score > 20 (should clamp to 20.00)
   - Exactly 0.00
   - Exactly 20.00
   - 19.995 (should round to 20.00)

**Expected Results**:
- [ ] Grades are clamped to [0.00, 20.00] range
- [ ] Rounding works correctly for edge values
- [ ] No negative or > 20 grades in export

**Status**: [ ] Pass / [ ] Fail  
**Notes**: _______________

---

### TC-6: Validation - Missing INE

**Objective**: Verify export fails when students lack valid INE

**Steps**:
1. Create student with empty INE (`ine = ""`)
2. Create graded, identified copy for this student
3. Attempt export via API

**Expected Results**:
- [ ] HTTP 400 Bad Request
- [ ] Error message in French: "sans INE valide"
- [ ] Export does not proceed

**Status**: [ ] Pass / [ ] Fail  
**Notes**: _______________

---

### TC-7: Validation - Unidentified Copies

**Objective**: Verify export fails with unidentified graded copies

**Steps**:
1. Create graded copy with `is_identified = False`
2. Attempt export via API

**Expected Results**:
- [ ] HTTP 400 Bad Request
- [ ] Error message in French: "non identifiée"
- [ ] Export does not proceed

**Status**: [ ] Pass / [ ] Fail  
**Notes**: _______________

---

### TC-8: Validation - No Graded Copies

**Objective**: Verify export fails when no graded copies exist

**Steps**:
1. Create exam with only STAGING copies (no GRADED)
2. Attempt export via API

**Expected Results**:
- [ ] HTTP 400 Bad Request
- [ ] Error message in French: "Aucune copie notée"
- [ ] Export does not proceed

**Status**: [ ] Pass / [ ] Fail  
**Notes**: _______________

---

### TC-9: Permission - Admin Only

**Objective**: Verify only admin users can export

**Steps**:
1. Attempt export as anonymous user
2. Attempt export as student user
3. Attempt export as teacher user
4. Attempt export as admin user

**Expected Results**:
- [ ] Anonymous: HTTP 401 Unauthorized
- [ ] Student: HTTP 403 Forbidden (French message)
- [ ] Teacher: HTTP 403 Forbidden ("Seuls les administrateurs...")
- [ ] Admin: HTTP 200 OK (or 400 validation error, not 403)

**Status**: [ ] Pass / [ ] Fail  
**Notes**: _______________

---

### TC-10: Custom Coefficient

**Objective**: Test custom coefficient parameter

**Steps**:
1. Export with default coefficient (should be 1.0 → "1,0")
2. Export with custom coefficient: `{"coefficient": 2.5}`
3. Export with invalid coefficient: `{"coefficient": "invalid"}`

**Expected Results**:
- [ ] Default: Coefficient column shows "1,0"
- [ ] Custom: Coefficient column shows "2,5"
- [ ] Invalid: HTTP 400 Bad Request with French error message

**Status**: [ ] Pass / [ ] Fail  
**Notes**: _______________

---

### TC-11: Rate Limiting

**Objective**: Verify 10 exports/hour rate limit per user

**Steps**:
1. Make 10 successful export requests within 1 hour
2. Attempt 11th request

**Expected Results**:
- [ ] First 10 requests: HTTP 200 OK
- [ ] 11th request: HTTP 429 Too Many Requests
- [ ] After 1 hour: Rate limit resets

**Note**: This test requires cache to be enabled. If rate limiting is disabled in test environment, mark as N/A.

**Status**: [ ] Pass / [ ] Fail / [ ] N/A  
**Notes**: _______________

---

### TC-12: Audit Logging

**Objective**: Verify all export attempts are logged

**Steps**:
1. Perform successful export
2. Check `AuditLog` table or audit logs
3. Perform failed export (e.g., missing INE)
4. Check audit logs again

**Expected Results**:
- [ ] Successful export: Log entry with action "export.pronote.success"
- [ ] Failed export: Log entry with action "export.pronote.failed"
- [ ] Forbidden access: Log entry with action "export.pronote.forbidden"
- [ ] Logs include: user, exam_id, timestamp, export_count (if success)

**Verification Query**:
```sql
SELECT * FROM audit_log 
WHERE action LIKE '%pronote%' 
ORDER BY created_at DESC 
LIMIT 10;
```

**Status**: [ ] Pass / [ ] Fail  
**Notes**: _______________

---

### TC-13: HTTP Response Headers

**Objective**: Verify correct HTTP headers for CSV download

**Steps**:
1. Export via API and inspect response headers

**Expected Results**:
- [ ] `Content-Type: text/csv; charset=utf-8`
- [ ] `Content-Disposition: attachment; filename="export_pronote_MATHEMATIQUES_2026-02-01.csv"`
- [ ] `X-Export-Warnings` header present if warnings exist

**Verification**:
```bash
curl -i -X POST \
  -H "Authorization: Bearer <token>" \
  http://localhost:8000/api/exams/<exam_id>/export-pronote/
```

**Status**: [ ] Pass / [ ] Fail  
**Notes**: _______________

---

### TC-14: Management Command - Basic Usage

**Objective**: Test CLI command for export

**Steps**:
```bash
# Basic export to stdout
python manage.py export_pronote <exam_uuid>

# Export to file
python manage.py export_pronote <exam_uuid> --output /tmp/export.csv

# Validation only
python manage.py export_pronote <exam_uuid> --validate-only

# Custom coefficient
python manage.py export_pronote <exam_uuid> --coefficient 2.5
```

**Expected Results**:
- [ ] Stdout export: CSV printed to terminal
- [ ] File export: File created with correct content
- [ ] Validation only: No CSV generated, validation results shown
- [ ] Custom coefficient: CSV contains specified coefficient
- [ ] Colored output: ✅ for success, ❌ for errors, ⚠️ for warnings

**Status**: [ ] Pass / [ ] Fail  
**Notes**: _______________

---

### TC-15: PRONOTE Import (If Available)

**Objective**: Verify actual import into PRONOTE software

**Prerequisites**:
- Access to PRONOTE software
- Test institution/class configured

**Steps**:
1. Export grades via API
2. Save CSV file
3. Open PRONOTE
4. Navigate to grade import feature
5. Import the CSV file

**Expected Results**:
- [ ] PRONOTE accepts file without encoding errors
- [ ] All grades imported correctly
- [ ] Student matching via INE works
- [ ] Comments appear correctly (accents, special chars)
- [ ] No import warnings or errors

**Status**: [ ] Pass / [ ] Fail / [ ] N/A  
**Notes**: _______________

---

### TC-16: Excel Compatibility

**Objective**: Verify CSV opens correctly in Microsoft Excel

**Steps**:
1. Export CSV file
2. Double-click to open in Excel (default handler)
3. Verify data display

**Expected Results**:
- [ ] Excel opens file without "Import Wizard"
- [ ] Columns are correctly separated (semicolon delimiter recognized)
- [ ] French accents display correctly (no Ã© instead of é)
- [ ] Decimal numbers show comma separator
- [ ] No mojibake or encoding issues

**Note**: Excel on Windows should recognize UTF-8 BOM and use correct delimiter.

**Status**: [ ] Pass / [ ] Fail  
**Notes**: _______________

---

### TC-17: Grade Calculation - Score Model

**Objective**: Test grade calculation from Score.scores_data

**Steps**:
1. Create copy with Score object:
   ```json
   {
     "ex1": 8.0,
     "ex2": 7.5
   }
   ```
2. Exam max_score: 20
3. Export and verify grade

**Expected Results**:
- [ ] Calculated grade: 8.0 + 7.5 = 15.5 → "15,50"
- [ ] Correct scaling if exam not /20

**Status**: [ ] Pass / [ ] Fail  
**Notes**: _______________

---

### TC-18: Grade Calculation - Annotations Fallback

**Objective**: Test grade calculation from annotations when no Score

**Steps**:
1. Create copy WITHOUT Score object
2. Add annotations with score_delta: +8, +7
3. Export and verify grade

**Expected Results**:
- [ ] Calculated grade: 8 + 7 = 15 → "15,00"
- [ ] Fallback works when Score unavailable

**Status**: [ ] Pass / [ ] Fail  
**Notes**: _______________

---

### TC-19: Scaling from Non-/20 Exams

**Objective**: Test grade scaling for exams not on /20 scale

**Steps**:
1. Create exam with grading_structure max_points = 40
2. Student score: 30/40
3. Export and verify scaled grade

**Expected Results**:
- [ ] Grade scaled to /20: 30/40 → 15/20 → "15,00"
- [ ] Scaling preserves precision

**Status**: [ ] Pass / [ ] Fail  
**Notes**: _______________

---

### TC-20: Multiple Copies Export

**Objective**: Test bulk export with multiple students

**Steps**:
1. Create exam with 10+ graded, identified copies
2. Export via API
3. Verify CSV content

**Expected Results**:
- [ ] All graded copies included
- [ ] Correct row count (header + N data rows)
- [ ] No duplicate rows
- [ ] Performance acceptable (< 5 seconds for 100 copies)

**Status**: [ ] Pass / [ ] Fail  
**Notes**: _______________

---

## Performance Testing

### Load Test - Large Export

**Objective**: Verify performance with realistic data volume

**Test Data**:
- Exam with 500 graded copies
- All students identified with valid INE

**Steps**:
1. Create test dataset
2. Time the export operation
3. Verify memory usage stays reasonable

**Expected Results**:
- [ ] Export completes in < 30 seconds
- [ ] Memory usage < 500 MB
- [ ] No timeout errors
- [ ] CSV file size reasonable (< 5 MB)

**Status**: [ ] Pass / [ ] Fail  
**Notes**: _______________

---

## Security Testing

### SQL Injection Prevention

**Objective**: Verify no SQL injection vulnerabilities

**Steps**:
1. Create student with INE: `'; DROP TABLE students; --`
2. Create comment: `'; DELETE FROM exams; --`
3. Export CSV

**Expected Results**:
- [ ] No SQL errors
- [ ] Data sanitized in CSV
- [ ] Database integrity maintained

**Status**: [ ] Pass / [ ] Fail  
**Notes**: _______________

### CSV Injection Prevention

**Objective**: Verify CSV formula injection is prevented

**Steps**:
1. Create comments starting with:
   - `=1+1`
   - `+cmd|'/c calc.exe'!A1`
   - `-2+3+cmd|' /c calc.exe'!A1`
   - `@SUM(1+1)`

**Expected Results**:
- [ ] Leading special chars are stripped
- [ ] No formulas execute when opened in Excel
- [ ] CSV is safe for PRONOTE import

**Status**: [ ] Pass / [ ] Fail  
**Notes**: _______________

---

## Regression Testing

### Existing Functionality Not Broken

**Objective**: Ensure new feature doesn't break existing features

**Areas to Check**:
- [ ] Generic CSV export still works (`/export-csv/`)
- [ ] PDF export still works (`/export-pdf/`)
- [ ] Copy grading workflow unaffected
- [ ] Student identification workflow unaffected
- [ ] Admin dashboard loads correctly

**Status**: [ ] Pass / [ ] Fail  
**Notes**: _______________

---

## Summary

### Test Results Overview

| Category | Passed | Failed | N/A | Total |
|----------|--------|--------|-----|-------|
| Format Validation | ___ | ___ | ___ | 1 |
| Encoding | ___ | ___ | ___ | 1 |
| Decimal Format | ___ | ___ | ___ | 1 |
| Special Characters | ___ | ___ | ___ | 1 |
| Edge Values | ___ | ___ | ___ | 1 |
| Validation Logic | ___ | ___ | ___ | 3 |
| Permissions | ___ | ___ | ___ | 1 |
| Custom Coefficient | ___ | ___ | ___ | 1 |
| Rate Limiting | ___ | ___ | ___ | 1 |
| Audit Logging | ___ | ___ | ___ | 1 |
| HTTP Headers | ___ | ___ | ___ | 1 |
| Management Command | ___ | ___ | ___ | 1 |
| PRONOTE Import | ___ | ___ | ___ | 1 |
| Excel Compatibility | ___ | ___ | ___ | 1 |
| Grade Calculation | ___ | ___ | ___ | 3 |
| Multiple Copies | ___ | ___ | ___ | 1 |
| Performance | ___ | ___ | ___ | 1 |
| Security | ___ | ___ | ___ | 2 |
| Regression | ___ | ___ | ___ | 1 |
| **TOTAL** | **___** | **___** | **___** | **22** |

### Issues Found

| # | Test Case | Severity | Description | Status |
|---|-----------|----------|-------------|--------|
| 1 | | | | |
| 2 | | | | |
| 3 | | | | |

### Sign-Off

- **Tester**: ___________________  
- **Date**: ___________________  
- **Approval**: ___________________  

---

## Appendix: Sample Test Data

### Sample Exam JSON

```json
{
  "name": "MATHEMATIQUES",
  "date": "2026-02-01",
  "grading_structure": [
    {
      "id": "ex1",
      "name": "Exercice 1",
      "max_points": 10
    },
    {
      "id": "ex2",
      "name": "Exercice 2",
      "max_points": 10
    }
  ]
}
```

### Sample API Request

```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <admin_token>" \
  -d '{"coefficient": 1.0}' \
  http://localhost:8000/api/exams/<exam_uuid>/export-pronote/ \
  --output export_test.csv
```

### Expected CSV Output

```csv
INE;MATIERE;NOTE;COEFF;COMMENTAIRE
11111111111;MATHEMATIQUES;15,50;1,0;Excellent travail
22222222222;MATHEMATIQUES;12,00;1,0;Bien; peut mieux faire
33333333333;MATHEMATIQUES;18,25;1,0;
```

---

**Document Version**: 1.0  
**Last Updated**: 2026-02-01  
**Related Documents**: `requirements.md`, `spec.md`, `plan.md`
