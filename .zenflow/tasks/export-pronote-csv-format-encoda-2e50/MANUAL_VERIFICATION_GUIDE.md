# PRONOTE CSV Export - Manual Verification Guide

**Task**: ZF-AUD-10  
**Date**: 2026-02-05  
**Status**: Ready for Manual Testing

---

## Overview

This guide provides step-by-step instructions for manually verifying the PRONOTE CSV export feature. It complements the automated test suite with real-world testing scenarios.

---

## Prerequisites

### 1. Environment Setup

```bash
# Navigate to project root
cd /home/alaeddine/.zenflow/worktrees/export-pronote-csv-format-encoda-2e50

# Start Docker services
docker-compose up -d

# Wait for services to be ready
docker-compose ps
```

### 2. Create Test Data

```bash
# Option A: Run the manual verification script
cd backend
python ../.zenflow/tasks/export-pronote-csv-format-encoda-2e50/manual_verification_test.py

# Option B: Use Django shell
python manage.py shell < ../.zenflow/tasks/export-pronote-csv-format-encoda-2e50/manual_verification_test.py
```

This creates:
- Admin user: `admin_test` / `adminpass123`
- Teacher user: `teacher_test` / `teacherpass123`
- 4 test students (including one without INE)
- 1 test exam "MATHEMATIQUES" with grading structure
- 5 test copies (including validation edge cases)

---

## Manual Test Execution

### Test 1: Basic CSV Export via Management Command

**Objective**: Verify basic export functionality and CSV format

**Steps**:
```bash
# Get exam UUID from previous step output or database
EXAM_UUID="<exam-uuid-from-test-data>"

# Export to file
cd backend
python manage.py export_pronote $EXAM_UUID --output /tmp/export_test.csv

# Verify file was created
ls -lh /tmp/export_test.csv
```

**Expected Results**:
- ✅ File created successfully
- ✅ No error messages
- ✅ File size > 0 bytes

**Verification**:
```bash
# 1. Check UTF-8 BOM (should show: ef bb bf)
hexdump -C /tmp/export_test.csv | head -1

# 2. Check line endings (should show: CRLF)
file /tmp/export_test.csv

# 3. View raw format (^M indicates CRLF)
cat -A /tmp/export_test.csv

# 4. View content
cat /tmp/export_test.csv
```

**Expected Output**:
```csv
INE;MATIERE;NOTE;COEFF;COMMENTAIRE
11111111111;MATHEMATIQUES;15,50;1,0;Excellent travail
22222222222;MATHEMATIQUES;12,00;1,0;Bien; peut mieux faire
33333333333;MATHEMATIQUES;18,25;1,0;Très "bon" travail!
```

**Actual Results**: ________________

---

### Test 2: CSV Format Validation

**Objective**: Verify CSV conforms to PRONOTE specification

**Validation Checklist**:

```bash
# Open file in text editor
cat /tmp/export_test.csv
```

- [ ] **UTF-8 BOM**: File starts with `\ufeff` (ef bb bf in hex)
- [ ] **Header**: Exactly `INE;MATIERE;NOTE;COEFF;COMMENTAIRE`
- [ ] **Delimiter**: Semicolon (`;`) used throughout
- [ ] **Decimal Separator**: Comma (`,`) for decimals (e.g., `15,50`)
- [ ] **Decimal Places**: All grades have exactly 2 decimal places
- [ ] **Coefficient**: Shows `1,0` (or custom value)
- [ ] **Line Endings**: CRLF (`\r\n`)
- [ ] **No Trailing Delimiters**: Lines don't end with `;`
- [ ] **No Empty Columns**: All required fields present

**Actual Results**: ________________

---

### Test 3: Encoding and Special Characters

**Objective**: Verify UTF-8 encoding and special character handling

**Steps**:
```bash
# 1. View in terminal (should show accents correctly)
cat /tmp/export_test.csv

# 2. Open in LibreOffice/Excel
libreoffice /tmp/export_test.csv
# or
excel /tmp/export_test.csv
```

**Expected Results**:
- [ ] `François` appears correctly (not `Fran├ºois` or `FranÃ§ois`)
- [ ] `Müller` appears correctly
- [ ] `O'Connor` appears correctly
- [ ] Quotes in comments are properly escaped
- [ ] Semicolons in comments don't break columns (`Bien; peut mieux faire`)
- [ ] Excel opens file without "Import Wizard" dialog

**Actual Results**: ________________

---

### Test 4: Custom Coefficient

**Objective**: Verify custom coefficient parameter

**Steps**:
```bash
# Export with custom coefficient
python manage.py export_pronote $EXAM_UUID --coefficient 2.5 --output /tmp/export_coeff.csv

# Check coefficient column
cat /tmp/export_coeff.csv | cut -d';' -f4 | tail -n +2
```

**Expected Results**:
- [ ] All rows show `2,5` in COEFF column
- [ ] Decimal uses comma separator
- [ ] 1 decimal place for coefficient

**Actual Results**: ________________

---

### Test 5: Validation - Missing INE

**Objective**: Verify export fails when student has no INE

**Steps**:
```bash
# The test data includes student "Jean Sans-INE" with empty INE
# Export should show validation error
python manage.py export_pronote $EXAM_UUID --validate-only
```

**Expected Results**:
- [ ] Validation error message appears
- [ ] Message mentions "sans INE valide" (in French)
- [ ] Export does not proceed
- [ ] Error indicates which student(s) are affected

**Actual Results**: ________________

---

### Test 6: Validation - Unidentified Copy

**Objective**: Verify export handles unidentified copies

**Steps**:
```bash
# Test data includes 1 unidentified copy
python manage.py export_pronote $EXAM_UUID --validate-only
```

**Expected Results**:
- [ ] Warning or error about unidentified copy
- [ ] Message in French: "copie non identifiée"
- [ ] Export either excludes unidentified copies or shows warning

**Actual Results**: ________________

---

### Test 7: API Endpoint - Admin Access

**Objective**: Verify API endpoint works and enforces admin-only access

**Steps**:

1. **Get Admin Token**:
```bash
# Login as admin via API
curl -X POST http://localhost:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"username": "admin_test", "password": "adminpass123"}'
  
# Copy the token from response
ADMIN_TOKEN="<token>"
```

2. **Test Export as Admin**:
```bash
# Export with admin token
curl -X POST \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  http://localhost:8000/api/exams/$EXAM_UUID/export-pronote/ \
  --output /tmp/api_export.csv \
  -i
```

**Expected Results**:
- [ ] HTTP 200 OK status
- [ ] `Content-Type: text/csv; charset=utf-8` header
- [ ] `Content-Disposition: attachment; filename="export_pronote_MATHEMATIQUES_*.csv"` header
- [ ] CSV file downloaded successfully
- [ ] File content matches command-line export

**Actual Results**: ________________

---

### Test 8: API Endpoint - Permission Denied

**Objective**: Verify non-admin users cannot export

**Steps**:

1. **Get Teacher Token**:
```bash
curl -X POST http://localhost:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"username": "teacher_test", "password": "teacherpass123"}'
  
TEACHER_TOKEN="<token>"
```

2. **Attempt Export as Teacher**:
```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TEACHER_TOKEN" \
  http://localhost:8000/api/exams/$EXAM_UUID/export-pronote/ \
  -i
```

**Expected Results**:
- [ ] HTTP 403 Forbidden status
- [ ] Error message in French: "Seuls les administrateurs..."
- [ ] No CSV file returned

3. **Test Anonymous Access**:
```bash
curl -X POST \
  http://localhost:8000/api/exams/$EXAM_UUID/export-pronote/ \
  -i
```

**Expected Results**:
- [ ] HTTP 401 Unauthorized status
- [ ] Authentication required message

**Actual Results**: ________________

---

### Test 9: API Endpoint - Custom Coefficient

**Objective**: Test custom coefficient via API

**Steps**:
```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d '{"coefficient": 3.5}' \
  http://localhost:8000/api/exams/$EXAM_UUID/export-pronote/ \
  --output /tmp/api_export_coeff.csv

# Verify coefficient
cat /tmp/api_export_coeff.csv | cut -d';' -f4 | tail -n +2
```

**Expected Results**:
- [ ] All rows show `3,5` in COEFF column
- [ ] Decimal format correct (comma separator)

**Actual Results**: ________________

---

### Test 10: Grade Calculation Verification

**Objective**: Verify grade calculation from annotations

**Steps**:
```bash
# Inspect grades in CSV
cat /tmp/export_test.csv | cut -d';' -f3 | tail -n +2
```

**Expected Results**:
- [ ] Grades match annotation score_delta values
- [ ] All grades formatted with 2 decimal places
- [ ] Grades use comma as decimal separator
- [ ] Grades are clamped to [0.00, 20.00]

**Manual Verification**:
```bash
# Check grades in database vs CSV
cd backend
python manage.py shell

>>> from exams.models import Exam, ExamCopy
>>> exam = Exam.objects.get(id='<exam-uuid>')
>>> for copy in exam.copies.filter(status='GRADED', is_identified=True):
...     annotations = copy.annotations.all()
...     total = sum(a.score_delta for a in annotations)
...     print(f"{copy.student.ine}: {total}")
```

Compare with CSV NOTE column.

**Actual Results**: ________________

---

### Test 11: Excel Compatibility

**Objective**: Verify CSV opens correctly in Microsoft Excel

**Steps**:
1. Copy `/tmp/export_test.csv` to Windows machine (if testing on Linux)
2. Double-click file to open in Excel
3. Verify display

**Expected Results**:
- [ ] Excel opens without "Import Wizard" dialog
- [ ] Columns correctly separated (5 columns visible)
- [ ] French accents display correctly
- [ ] Decimal numbers show comma separator
- [ ] No encoding errors (mojibake)

**Actual Results**: ________________

---

### Test 12: Audit Logging

**Objective**: Verify exports are logged for audit trail

**Steps**:
```bash
# After performing an export, check audit logs
cd backend
python manage.py shell

>>> from core.models import AuditLog  # Adjust import based on actual model
>>> logs = AuditLog.objects.filter(action__contains='pronote').order_by('-created_at')[:10]
>>> for log in logs:
...     print(f"{log.created_at} - {log.user.username} - {log.action} - {log.resource_id}")
```

**Expected Results**:
- [ ] Successful export logged with action like `export.pronote.success`
- [ ] Failed export logged with action like `export.pronote.failed`
- [ ] Log includes: user, exam_id, timestamp
- [ ] Log includes export count (number of rows)

**Actual Results**: ________________

---

### Test 13: Rate Limiting (If Enabled)

**Objective**: Verify rate limiting prevents abuse

**Steps**:
```bash
# Make 11 requests in quick succession
for i in {1..11}; do
  echo "Request $i"
  curl -X POST \
    -H "Authorization: Bearer $ADMIN_TOKEN" \
    http://localhost:8000/api/exams/$EXAM_UUID/export-pronote/ \
    -o /dev/null -w "HTTP %{http_code}\n"
done
```

**Expected Results**:
- [ ] First 10 requests: HTTP 200 OK
- [ ] 11th request: HTTP 429 Too Many Requests
- [ ] Error message indicates rate limit exceeded

**Note**: Rate limiting may be disabled in development. Check settings.

**Actual Results**: ________________

---

### Test 14: PRONOTE Import (If Available)

**Objective**: Verify CSV can be imported into actual PRONOTE software

**Prerequisites**:
- Access to PRONOTE software
- Test institution/class configured

**Steps**:
1. Export CSV file
2. Open PRONOTE
3. Navigate to grade import feature
4. Select the CSV file
5. Complete import process

**Expected Results**:
- [ ] PRONOTE accepts file without errors
- [ ] No encoding warnings
- [ ] Student matching via INE works
- [ ] All grades imported correctly
- [ ] Comments appear with correct accents
- [ ] Coefficient applied correctly

**Actual Results**: ________________

**Note**: This test may be marked N/A if PRONOTE access is unavailable.

---

## CSV Inspection Commands

### Quick Validation Commands

```bash
# 1. Check UTF-8 BOM (should see: ef bb bf)
xxd /tmp/export_test.csv | head -1

# 2. Check line endings (should see CRLF)
dos2unix -ic /tmp/export_test.csv  # If installed
# or
file /tmp/export_test.csv

# 3. Count rows (should be header + N graded copies)
wc -l /tmp/export_test.csv

# 4. View raw format with line ending markers
cat -A /tmp/export_test.csv | head -5

# 5. Extract just grades
cat /tmp/export_test.csv | cut -d';' -f3 | tail -n +2

# 6. Extract just INE numbers
cat /tmp/export_test.csv | cut -d';' -f1 | tail -n +2

# 7. Verify delimiter consistency (all rows should have 4 semicolons)
awk -F';' '{print NF}' /tmp/export_test.csv | sort | uniq -c

# 8. Check for trailing semicolons (should be empty)
grep ';$' /tmp/export_test.csv
```

---

## Expected vs Actual CSV Format

### Expected Format
```
[UTF-8 BOM]INE;MATIERE;NOTE;COEFF;COMMENTAIRE\r\n
11111111111;MATHEMATIQUES;15,50;1,0;Excellent travail\r\n
22222222222;MATHEMATIQUES;12,00;1,0;Bien; peut mieux faire\r\n
33333333333;MATHEMATIQUES;18,25;1,0;Très "bon" travail!\r\n
```

### Hexdump of First Line (with BOM)
```
00000000  ef bb bf 49 4e 45 3b 4d  41 54 49 45 52 45 3b 4e  |...INE;MATIERE;N|
00000010  4f 54 45 3b 43 4f 45 46  46 3b 43 4f 4d 4d 45 4e  |OTE;COEFF;COMMEN|
00000020  54 41 49 52 45 0d 0a                              |TAIRE..|
```

---

## Troubleshooting

### Issue: No UTF-8 BOM detected

**Diagnosis**:
```bash
hexdump -C /tmp/export_test.csv | head -1
# Should start with: ef bb bf
```

**Fix**: Check PronoteExporter.generate_csv() method adds BOM:
```python
csv_content = '\ufeff' + csv_content
```

---

### Issue: Wrong line endings (LF instead of CRLF)

**Diagnosis**:
```bash
file /tmp/export_test.csv
# Should show: "with CRLF line terminators"
```

**Fix**: Check csv.writer uses `lineterminator='\r\n'`

---

### Issue: Decimal uses period instead of comma

**Diagnosis**:
```bash
cat /tmp/export_test.csv | grep '\.'
# Should not find any periods in numeric columns
```

**Fix**: Check format_decimal_french() method implementation

---

### Issue: Excel shows encoding errors

**Diagnosis**: Missing UTF-8 BOM or wrong encoding

**Fix**: 
1. Verify BOM is present (hexdump)
2. Ensure file is saved as UTF-8, not Latin-1

---

### Issue: PRONOTE import fails

**Common Causes**:
- Missing UTF-8 BOM → PRONOTE can't detect encoding
- Wrong decimal separator (period instead of comma)
- Invalid INE format (not 11 digits)
- Wrong delimiter (comma instead of semicolon)

---

## Test Results Summary

### Overall Status

- [ ] ✅ All critical tests passing
- [ ] ⚠️  Some warnings or minor issues
- [ ] ❌ Critical failures

### Test Categories

| Category | Status | Notes |
|----------|--------|-------|
| CSV Format | __ | |
| Encoding | __ | |
| Decimal Format | __ | |
| Special Characters | __ | |
| Validation Logic | __ | |
| API Endpoint | __ | |
| Management Command | __ | |
| Permissions | __ | |
| Grade Calculation | __ | |
| Excel Compatibility | __ | |
| PRONOTE Import | __ | |
| Audit Logging | __ | |
| Rate Limiting | __ | |

### Issues Found

| # | Test | Severity | Description | Status |
|---|------|----------|-------------|--------|
| 1 | | | | |
| 2 | | | | |
| 3 | | | | |

---

## Sign-Off

- **Tester**: ___________________
- **Date**: ___________________
- **Environment**: Development / Staging / Production
- **Approval**: ___________________

---

## Next Steps

After manual verification:

1. [ ] Update `audit.md` with actual test results
2. [ ] Address any issues found
3. [ ] Re-test after fixes
4. [ ] Mark Step 13 (Manual Verification) as complete in `plan.md`
5. [ ] Prepare for production deployment (if all tests pass)

---

**Document Version**: 1.0  
**Last Updated**: 2026-02-05  
**Task**: ZF-AUD-10  
**Related Files**: `audit.md`, `spec.md`, `requirements.md`, `plan.md`
