# PRONOTE CSV Export - Quick Test Reference

**Task**: ZF-AUD-10  
**Quick Reference for Manual Testing**

---

## Quick Start

```bash
# 1. Start environment
docker-compose up -d

# 2. Create test data
cd backend
python ../.zenflow/tasks/export-pronote-csv-format-encoda-2e50/manual_verification_test.py

# Output will show exam UUID - save it!
EXAM_UUID="<uuid-from-output>"
```

---

## Essential Tests

### Test 1: Basic Export
```bash
python manage.py export_pronote $EXAM_UUID --output /tmp/test.csv
cat /tmp/test.csv
```

**✓ Check**: Header is `INE;MATIERE;NOTE;COEFF;COMMENTAIRE`

---

### Test 2: Format Validation
```bash
# UTF-8 BOM (should show: ef bb bf)
hexdump -C /tmp/test.csv | head -1

# CRLF line endings
file /tmp/test.csv

# Decimal format (should use comma: 15,50)
cat /tmp/test.csv | grep -o '[0-9]\+,[0-9]\{2\}'
```

**✓ Check**: BOM present, CRLF endings, comma decimals

---

### Test 3: API Export
```bash
# Get admin token
curl -X POST http://localhost:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"username": "admin_test", "password": "adminpass123"}'

# Export (replace TOKEN and UUID)
curl -X POST \
  -H "Authorization: Bearer <TOKEN>" \
  http://localhost:8000/api/exams/$EXAM_UUID/export-pronote/ \
  --output /tmp/api_export.csv \
  -i
```

**✓ Check**: HTTP 200, Content-Type: text/csv, file downloaded

---

### Test 4: Permission Test
```bash
# As teacher (should fail with 403)
curl -X POST http://localhost:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"username": "teacher_test", "password": "teacherpass123"}'

curl -X POST \
  -H "Authorization: Bearer <TEACHER_TOKEN>" \
  http://localhost:8000/api/exams/$EXAM_UUID/export-pronote/ \
  -i
```

**✓ Check**: HTTP 403 Forbidden

---

### Test 5: Validation Errors
```bash
# Should show validation errors (missing INE, unidentified copies)
python manage.py export_pronote $EXAM_UUID --validate-only
```

**✓ Check**: French error messages, mentions "sans INE" and "non identifiée"

---

### Test 6: Custom Coefficient
```bash
python manage.py export_pronote $EXAM_UUID --coefficient 2.5 --output /tmp/coeff.csv
cat /tmp/coeff.csv | cut -d';' -f4 | tail -n +2
```

**✓ Check**: All rows show `2,5`

---

## Quick Validation Checklist

Copy `/tmp/test.csv` and verify:

- [ ] First 3 bytes: `ef bb bf` (UTF-8 BOM)
- [ ] Header: `INE;MATIERE;NOTE;COEFF;COMMENTAIRE`
- [ ] Delimiter: `;` (semicolon)
- [ ] Decimal: `,` (comma, e.g., `15,50`)
- [ ] Line ending: `\r\n` (CRLF)
- [ ] Decimal places: Exactly 2 for grades (e.g., `12,00`)
- [ ] No trailing semicolons
- [ ] Accents preserved (François, not Fran├ºois)

---

## Expected Output Example

```csv
INE;MATIERE;NOTE;COEFF;COMMENTAIRE
11111111111;MATHEMATIQUES;15,50;1,0;Excellent travail
22222222222;MATHEMATIQUES;12,00;1,0;Bien; peut mieux faire
33333333333;MATHEMATIQUES;18,25;1,0;Très "bon" travail!
```

---

## Common Issues

| Issue | Check | Fix |
|-------|-------|-----|
| No BOM | `hexdump -C file \| head -1` | Add `\ufeff` prefix |
| LF not CRLF | `file test.csv` | Use `lineterminator='\r\n'` |
| Period not comma | `grep '\.' test.csv` | Check `format_decimal_french()` |
| Excel encoding error | Open in Excel | Verify BOM present |

---

## Test Users

- **Admin**: `admin_test` / `adminpass123`
- **Teacher**: `teacher_test` / `teacherpass123`

---

## Files Created

1. **Test Script**: `manual_verification_test.py`
2. **Full Guide**: `MANUAL_VERIFICATION_GUIDE.md` (detailed instructions)
3. **Quick Reference**: `QUICK_TEST_REFERENCE.md` (this file)
4. **Audit Document**: `audit.md` (test results tracking)

---

**For detailed testing**: See `MANUAL_VERIFICATION_GUIDE.md`  
**For test results**: Update `audit.md`  
**Task**: ZF-AUD-10
