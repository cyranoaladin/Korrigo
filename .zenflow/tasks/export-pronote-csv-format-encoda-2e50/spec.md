# Technical Specification: PRONOTE CSV Export

**Version**: 1.0  
**Date**: 2026-01-31  
**Task ID**: ZF-AUD-10  
**Based on**: `requirements.md` v1.0

---

## 1. Technical Context

### 1.1 Technology Stack
- **Backend Framework**: Django 5.2.10
- **Database**: PostgreSQL 15
- **API Framework**: Django REST Framework
- **Rate Limiting**: django-ratelimit
- **Python Version**: 3.11+
- **CSV Library**: Python stdlib `csv` module

### 1.2 Existing Components
- **Management Command**: `backend/exams/management/commands/export_pronote.py` (requires fixes)
- **Generic CSV Export**: `CSVExportView` in `backend/exams/views.py` (different format, teacher-accessible)
- **Permission Classes**: `IsAdminOnly` in `core.auth`
- **Audit System**: `log_audit()` in `core/utils/audit.py`
- **Rate Limiting**: `maybe_ratelimit()` wrapper in `core/utils/ratelimit.py`

### 1.3 Data Model Analysis

**Models Used**:
```python
# exams.models
Exam:
  - id (UUID)
  - name (CharField)
  - date (DateField)
  - grading_structure (JSONField)
  
Copy:
  - id (UUID)
  - exam (FK to Exam)
  - anonymous_id (CharField)
  - student (FK to Student, nullable)
  - is_identified (BooleanField)
  - status (TextChoices: STAGING, READY, LOCKED, GRADING_IN_PROGRESS, GRADING_FAILED, GRADED)
  - global_appreciation (TextField, nullable)

# students.models
Student:
  - id (AutoField)
  - ine (CharField, max_length=50, unique)
  - first_name (CharField)
  - last_name (CharField)
  - class_name (CharField)
  - email (EmailField)

# grading.models (Note: Score model does NOT exist)
Annotation:
  - copy (FK)
  - page_index (PositiveIntegerField)
  - score_delta (IntegerField, nullable) # Points added/subtracted
  - content (TextField)
  - type (COMMENT, HIGHLIGHT, ERROR, BONUS)
```

**Critical Finding**: The `Score` model referenced in `export_pronote.py:38` **does not exist**. It was in migration `0001_initial.py` but was never implemented. The current grading system uses:
- `Annotation.score_delta` for individual point adjustments
- `Exam.grading_structure` (JSON) for the grading rubric
- No centralized "total score" model

---

## 2. Implementation Architecture

### 2.1 Score Calculation Strategy

Since the `Score` model doesn't exist, we need to calculate the final grade from available data:

**Option 1: Annotation-based calculation** (Chosen)
```python
def calculate_copy_grade(copy: Copy) -> float:
    """
    Calculate total grade from annotation score deltas.
    Assumes grading_structure defines max_points per question.
    """
    # Get base score from grading structure (if defined)
    base_score = get_base_score_from_structure(copy.exam.grading_structure)
    
    # Sum all annotation score_delta values
    annotations = copy.annotations.all()
    total_delta = sum(a.score_delta for a in annotations if a.score_delta)
    
    final_score = base_score + total_delta
    return max(0, min(final_score, 20))  # Clamp to [0, 20]
```

**Option 2: Require Score model implementation** (Future)
- Create a proper `Score` model in `grading/models.py`
- Link it to `Copy` via FK
- Store final grade calculation results
- *Out of scope for this task*

**Decision**: Use Option 1 for MVP. Document the limitation and recommend Option 2 for future enhancement.

### 2.2 Component Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    API Layer (views.py)                     │
│  - PronoteExportView (NEW)                                  │
│    • POST /api/exams/<uuid:id>/export-pronote/              │
│    • Permission: IsAdminOnly                                │
│    • Rate Limit: 10/hour per user                           │
│    • Audit Logging: via log_data_access()                   │
└─────────────────┬───────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────┐
│              Service Layer (services/pronote_export.py)     │
│  - PronoteExporter (NEW)                                    │
│    • validate_export_eligibility()                          │
│    • calculate_grades()                                     │
│    • generate_csv()                                         │
│    • format_decimal_french()                                │
│    • sanitize_comment()                                     │
└─────────────────┬───────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────┐
│         Management Command (updated export_pronote.py)      │
│  - Uses PronoteExporter service                             │
│  - CLI options: --coefficient, --output, --validate-only    │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. Implementation Details

### 3.1 New API Endpoint

**File**: `backend/exams/views.py`

```python
class PronoteExportView(APIView):
    """
    PRONOTE CSV Export endpoint (Admin-only).
    
    POST /api/exams/<uuid:id>/export-pronote/
    
    Returns:
        - 200: CSV file download
        - 400: Validation errors (missing INE, ungraded copies)
        - 403: Permission denied
        - 404: Exam not found
    """
    permission_classes = [IsAdminOnly]
    
    @method_decorator(maybe_ratelimit(
        key='user',
        rate='10/h',
        method='POST',
        block=True
    ))
    def post(self, request, id):
        # Implementation details in section 3.3
        pass
```

**URL Registration**: `backend/exams/urls.py`
```python
# Add to urlpatterns:
path('<uuid:id>/export-pronote/', PronoteExportView.as_view(), name='export-pronote'),
```

### 3.2 Service Layer: PronoteExporter

**File**: `backend/exams/services/pronote_export.py` (NEW)

```python
class PronoteExporter:
    """
    Service for generating PRONOTE-compatible CSV exports.
    
    Format: INE;MATIERE;NOTE;COEFF;COMMENTAIRE
    - Encoding: UTF-8 with BOM
    - Delimiter: Semicolon (;)
    - Decimal: Comma (,)
    - Line ending: CRLF (\r\n)
    """
    
    def __init__(self, exam: Exam, coefficient: float = 1.0):
        self.exam = exam
        self.coefficient = coefficient
        
    def validate_export_eligibility(self) -> dict:
        """
        Validates that the exam is ready for export.
        
        Returns:
            dict: {
                'valid': bool,
                'errors': list[str],
                'warnings': list[str]
            }
        """
        
    def calculate_copy_grade(self, copy: Copy) -> float:
        """
        Calculate final grade for a copy.
        
        Strategy:
        1. Sum annotation score_delta values
        2. If grading_structure defines base score, use it
        3. Clamp to [0, 20] range
        
        Returns:
            float: Grade on /20 scale
        """
        
    def generate_csv(self) -> tuple[str, list[str]]:
        """
        Generate PRONOTE CSV content.
        
        Returns:
            (csv_content: str, warnings: list[str])
        """
        
    @staticmethod
    def format_decimal_french(value: float, precision: int = 2) -> str:
        """
        Format decimal with French locale (comma separator).
        
        Examples:
            15.5 -> "15,50"
            12.0 -> "12,00"
            15.555 -> "15,56" (rounded)
        """
        
    @staticmethod
    def sanitize_comment(comment: str) -> str:
        """
        Sanitize comment for CSV export.
        
        - Replace newlines with spaces
        - Escape quotes
        - Limit length to 500 chars
        """
```

### 3.3 Endpoint Implementation Flow

```python
def post(self, request, id):
    # 1. Get exam
    exam = get_object_or_404(Exam, id=id)
    
    # 2. Get coefficient (optional parameter)
    coefficient = float(request.data.get('coefficient', 1.0))
    
    # 3. Create exporter
    exporter = PronoteExporter(exam, coefficient=coefficient)
    
    # 4. Validate export eligibility
    validation = exporter.validate_export_eligibility()
    if not validation['valid']:
        log_audit(
            request,
            'export.pronote.failed',
            'Exam',
            exam.id,
            {'errors': validation['errors']}
        )
        return Response(
            {'errors': validation['errors']},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # 5. Generate CSV
    csv_content, warnings = exporter.generate_csv()
    
    # 6. Audit log success
    log_audit(
        request,
        'export.pronote.success',
        'Exam',
        exam.id,
        {
            'copy_count': exam.copies.filter(status=Copy.Status.GRADED).count(),
            'coefficient': coefficient,
            'warnings': warnings
        }
    )
    
    # 7. Create HTTP response
    response = HttpResponse(csv_content, content_type='text/csv; charset=utf-8')
    
    # 8. Set download headers
    filename = f"export_pronote_{exam.name}_{exam.date}.csv"
    safe_filename = "".join(c if c.isalnum() or c in "._- " else "_" for c in filename)
    response['Content-Disposition'] = f'attachment; filename="{safe_filename}"'
    
    return response
```

### 3.4 Validation Logic

**File**: `backend/exams/services/pronote_export.py`

```python
def validate_export_eligibility(self) -> dict:
    errors = []
    warnings = []
    
    # Get graded copies
    graded_copies = self.exam.copies.filter(status=Copy.Status.GRADED)
    
    # Check: No graded copies
    if graded_copies.count() == 0:
        errors.append("Aucune copie corrigée trouvée pour cet examen.")
        return {'valid': False, 'errors': errors, 'warnings': warnings}
    
    # Check: All graded copies must be identified
    unidentified = graded_copies.filter(is_identified=False)
    if unidentified.exists():
        errors.append(
            f"Impossible d'exporter : {unidentified.count()} copie(s) "
            f"corrigée(s) non identifiée(s)."
        )
    
    # Check: All identified copies must have valid INE
    identified_copies = graded_copies.filter(is_identified=True)
    missing_ine = []
    for copy in identified_copies:
        if not copy.student or not copy.student.ine:
            missing_ine.append(copy.anonymous_id)
    
    if missing_ine:
        errors.append(
            f"Impossible d'exporter : {len(missing_ine)} copie(s) "
            f"sans INE : {', '.join(missing_ine[:5])}"
            + ("..." if len(missing_ine) > 5 else "")
        )
    
    # Warning: Comments with delimiter
    for copy in identified_copies:
        if copy.global_appreciation and ';' in copy.global_appreciation:
            warnings.append(
                f"Copie {copy.anonymous_id} : commentaire contient ';' (échappé)"
            )
    
    return {
        'valid': len(errors) == 0,
        'errors': errors,
        'warnings': warnings
    }
```

### 3.5 CSV Generation Logic

```python
def generate_csv(self) -> tuple[str, list[str]]:
    import csv
    from io import StringIO
    
    warnings = []
    output = StringIO()
    
    # UTF-8 with BOM for Excel/PRONOTE compatibility
    output.write('\ufeff')
    
    # CSV writer with PRONOTE format
    writer = csv.writer(
        output,
        delimiter=';',
        quotechar='"',
        quoting=csv.QUOTE_MINIMAL,
        lineterminator='\r\n'  # CRLF for Windows
    )
    
    # Header
    writer.writerow(['INE', 'MATIERE', 'NOTE', 'COEFF', 'COMMENTAIRE'])
    
    # Data rows
    graded_copies = (
        self.exam.copies
        .filter(status=Copy.Status.GRADED, is_identified=True)
        .select_related('student')
        .prefetch_related('annotations')
        .order_by('student__last_name', 'student__first_name')
    )
    
    for copy in graded_copies:
        # Skip if no student or INE
        if not copy.student or not copy.student.ine:
            continue
        
        # Calculate grade
        grade = self.calculate_copy_grade(copy)
        
        # Format fields
        ine = copy.student.ine.strip()
        matiere = self.exam.name.upper()
        note = self.format_decimal_french(grade)
        coeff = self.format_decimal_french(self.coefficient)
        commentaire = self.sanitize_comment(copy.global_appreciation or "")
        
        writer.writerow([ine, matiere, note, coeff, commentaire])
    
    return output.getvalue(), warnings
```

### 3.6 Grade Calculation Implementation

```python
def calculate_copy_grade(self, copy: Copy) -> float:
    """
    Calculate grade from annotations.
    
    Current implementation: Sum of annotation score_delta values.
    
    Note: This is a simplified approach. For production use,
    consider implementing a Score model to store calculated grades.
    """
    # Get all annotations with score deltas
    annotations = copy.annotations.filter(score_delta__isnull=False)
    
    # Sum the deltas
    total_score = sum(a.score_delta for a in annotations)
    
    # Parse grading_structure to get max possible score
    grading_structure = copy.exam.grading_structure or []
    max_score = self._calculate_max_score(grading_structure)
    
    if max_score > 0:
        # Scale to /20
        grade = (total_score / max_score) * 20.0
    else:
        # No grading structure: assume total_score is already /20
        grade = total_score
    
    # Clamp to valid range [0, 20]
    return max(0.0, min(grade, 20.0))

def _calculate_max_score(self, grading_structure: list) -> float:
    """
    Calculate maximum score from grading structure.
    
    Expected format:
    [
        {"id": "q1", "points": 5.0},
        {"id": "q2", "points": 3.5, "subquestions": [...]},
        ...
    ]
    """
    total = 0.0
    for item in grading_structure:
        if isinstance(item, dict):
            points = item.get('points', 0.0)
            total += float(points) if points else 0.0
            
            # Recursively handle subquestions
            if 'subquestions' in item:
                total += self._calculate_max_score(item['subquestions'])
    
    return total
```

### 3.7 Decimal Formatting

```python
@staticmethod
def format_decimal_french(value: float, precision: int = 2) -> str:
    """
    Format decimal with French locale (comma separator).
    
    Uses standard mathematical rounding (half-up).
    """
    rounded = round(value, precision)
    formatted = f"{rounded:.{precision}f}"
    return formatted.replace('.', ',')

# Examples:
# format_decimal_french(15.5) -> "15,50"
# format_decimal_french(15.555, 2) -> "15,56"
# format_decimal_french(12.0) -> "12,00"
```

### 3.8 Comment Sanitization

```python
@staticmethod
def sanitize_comment(comment: str) -> str:
    """
    Sanitize comment for CSV export.
    """
    if not comment:
        return ""
    
    # Replace newlines with spaces
    sanitized = comment.replace('\n', ' ').replace('\r', ' ')
    
    # Limit length (PRONOTE may have limits)
    max_length = 500
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length-3] + "..."
    
    # CSV library will handle quote escaping automatically
    # when using QUOTE_MINIMAL
    
    return sanitized.strip()
```

---

## 4. Updated Management Command

**File**: `backend/exams/management/commands/export_pronote.py`

**Changes**:
1. Remove direct `Score` model reference (doesn't exist)
2. Use `PronoteExporter` service
3. Add new CLI options

```python
from django.core.management.base import BaseCommand
from exams.models import Exam
from exams.services.pronote_export import PronoteExporter
import sys

class Command(BaseCommand):
    help = 'Export exam grades to PRONOTE CSV format'

    def add_arguments(self, parser):
        parser.add_argument('exam_id', type=str, help='UUID of the exam')
        parser.add_argument(
            '--coefficient',
            type=float,
            default=1.0,
            help='Coefficient for the exam (default: 1.0)'
        )
        parser.add_argument(
            '--output',
            type=str,
            default=None,
            help='Output file path (default: stdout)'
        )
        parser.add_argument(
            '--validate-only',
            action='store_true',
            help='Only validate export eligibility, do not generate CSV'
        )

    def handle(self, *args, **options):
        exam_id = options['exam_id']
        coefficient = options['coefficient']
        
        try:
            exam = Exam.objects.get(id=exam_id)
        except Exam.DoesNotExist:
            self.stderr.write(self.style.ERROR(f"Exam {exam_id} not found"))
            return
        
        # Create exporter
        exporter = PronoteExporter(exam, coefficient=coefficient)
        
        # Validate
        validation = exporter.validate_export_eligibility()
        
        if not validation['valid']:
            self.stderr.write(self.style.ERROR("Validation failed:"))
            for error in validation['errors']:
                self.stderr.write(f"  - {error}")
            return
        
        # Show warnings
        if validation['warnings']:
            for warning in validation['warnings']:
                self.stderr.write(self.style.WARNING(f"Warning: {warning}"))
        
        # If validate-only, stop here
        if options['validate_only']:
            self.stdout.write(self.style.SUCCESS("Validation passed."))
            return
        
        # Generate CSV
        csv_content, warnings = exporter.generate_csv()
        
        # Output
        output_file = options['output']
        if output_file:
            with open(output_file, 'w', encoding='utf-8-sig') as f:
                f.write(csv_content)
            self.stdout.write(
                self.style.SUCCESS(f"Exported to {output_file}")
            )
        else:
            sys.stdout.write(csv_content)
        
        # Count
        count = csv_content.count('\n') - 1  # Exclude header
        self.stderr.write(
            self.style.SUCCESS(f"Exported {count} grades for PRONOTE.")
        )
```

---

## 5. Testing Strategy

### 5.1 Unit Tests

**File**: `backend/exams/tests/test_pronote_export.py` (NEW)

```python
class PronoteExporterTests(TestCase):
    """Unit tests for PRONOTE export service."""
    
    def test_format_decimal_french_typical_values(self):
        """Test French decimal formatting with typical values."""
        
    def test_format_decimal_french_edge_cases(self):
        """Test rounding: 15.555 -> 15,56"""
        
    def test_sanitize_comment_with_delimiter(self):
        """Test comment sanitization with semicolon."""
        
    def test_calculate_grade_with_annotations(self):
        """Test grade calculation from annotation deltas."""
        
    def test_validate_export_missing_ine(self):
        """Test validation fails when copies missing INE."""
        
    def test_validate_export_unidentified_copies(self):
        """Test validation fails with unidentified copies."""
        
    def test_csv_generation_format(self):
        """Test CSV format matches PRONOTE spec."""
```

### 5.2 Integration Tests

**File**: `backend/exams/tests/test_pronote_export_api.py` (NEW)

```python
class PronoteExportAPITests(APITestCase):
    """Integration tests for PRONOTE export API endpoint."""
    
    def test_export_requires_admin_permission(self):
        """Test teacher cannot export PRONOTE CSV."""
        
    def test_export_success_with_valid_data(self):
        """Test successful export with all valid copies."""
        
    def test_export_fails_with_missing_ine(self):
        """Test export fails with HTTP 400 when INE missing."""
        
    def test_export_rate_limiting(self):
        """Test rate limit of 10 exports per hour."""
        
    def test_export_audit_logging(self):
        """Test audit trail created for export."""
        
    def test_csv_encoding_utf8_bom(self):
        """Test CSV has UTF-8 BOM for Excel compatibility."""
        
    def test_csv_special_characters(self):
        """Test accents, quotes in student names and comments."""
```

### 5.3 Management Command Tests

**File**: `backend/exams/tests/test_export_pronote_command.py` (NEW)

```python
class ExportPronoteCommandTests(TestCase):
    """Tests for export_pronote management command."""
    
    def test_command_with_valid_exam(self):
        """Test command exports CSV to stdout."""
        
    def test_command_with_output_file(self):
        """Test --output option."""
        
    def test_command_validate_only(self):
        """Test --validate-only option."""
        
    def test_command_custom_coefficient(self):
        """Test --coefficient option."""
```

### 5.4 Manual Testing Checklist

Create `audit.md` with manual test cases:

1. **Import Test**: Export CSV and import into PRONOTE
2. **Special Characters**: Test with accents (é, è, à), quotes, semicolons
3. **Edge Values**: Test grades 0.00, 20.00, 19.995
4. **Large Export**: Test with 500+ copies
5. **Rate Limiting**: Verify 10 exports/hour limit
6. **Audit Log**: Verify entries in AuditLog table

---

## 6. Database Changes

**No database migrations required.**

All necessary models already exist:
- `Exam`, `Copy`, `Student` (existing)
- `Annotation` for grading (existing)
- `AuditLog` for audit trail (existing)

**Optional Enhancement** (out of scope):
- Add `Exam.coefficient` field (FloatField, default=1.0)
- Add `Score` model to cache calculated grades

---

## 7. Security Considerations

### 7.1 Access Control
- ✅ Admin-only permission via `IsAdminOnly` class
- ✅ Rate limiting: 10 exports/hour per user
- ✅ Audit logging via `log_audit()`

### 7.2 Data Protection
- ✅ No data leakage: Only required PRONOTE fields exported
- ✅ No sensitive data in filenames: Use exam UUID, not student names
- ✅ HTTPS-only in production (Django setting)

### 7.3 Input Validation
- ✅ UUID validation for exam ID
- ✅ Coefficient range validation (0.1 to 10.0)
- ✅ Comment length limit (500 chars)

### 7.4 CSV Injection Prevention
```python
def sanitize_comment(comment: str) -> str:
    """Prevent CSV injection attacks."""
    # Remove leading special characters that could trigger formulas
    dangerous_chars = ['=', '+', '-', '@', '\t', '\r']
    if comment and comment[0] in dangerous_chars:
        comment = "'" + comment  # Prefix with single quote
    return comment
```

---

## 8. Performance Considerations

### 8.1 Query Optimization
```python
# Use select_related and prefetch_related
graded_copies = (
    self.exam.copies
    .filter(status=Copy.Status.GRADED, is_identified=True)
    .select_related('student')
    .prefetch_related('annotations')
    .order_by('student__last_name')
)
```

### 8.2 Performance Targets
- **500 copies**: < 5 seconds
- **1000 copies**: < 10 seconds

### 8.3 Memory Efficiency
- Use `StringIO` for in-memory CSV generation
- Stream response (no temporary file storage)

---

## 9. Delivery Phases

### Phase 1: Core Service Layer (Day 1)
- [ ] Create `PronoteExporter` service class
- [ ] Implement validation logic
- [ ] Implement CSV generation
- [ ] Implement grade calculation
- [ ] Unit tests for service layer

### Phase 2: API Endpoint (Day 2)
- [ ] Create `PronoteExportView` API endpoint
- [ ] Add URL routing
- [ ] Add rate limiting
- [ ] Add audit logging
- [ ] Integration tests for API

### Phase 3: Management Command Update (Day 2)
- [ ] Refactor `export_pronote.py` command
- [ ] Add CLI options
- [ ] Remove Score model references
- [ ] Tests for management command

### Phase 4: Testing & Validation (Day 3)
- [ ] Create `audit.md` with manual test cases
- [ ] Manual PRONOTE import test
- [ ] Special characters testing
- [ ] Performance testing (500+ copies)
- [ ] Security audit

---

## 10. Verification Approach

### 10.1 Automated Tests
```bash
# Unit tests
pytest backend/exams/tests/test_pronote_export.py -v

# Integration tests
pytest backend/exams/tests/test_pronote_export_api.py -v

# Command tests
pytest backend/exams/tests/test_export_pronote_command.py -v
```

### 10.2 Manual Verification
1. Run management command: `python manage.py export_pronote <exam_id>`
2. Import CSV into PRONOTE test instance
3. Verify grades appear correctly
4. Check special characters render properly

### 10.3 Code Quality
```bash
# Linting (if configured)
ruff check backend/exams/services/pronote_export.py
ruff check backend/exams/views.py

# Type checking (if configured)
mypy backend/exams/services/pronote_export.py
```

---

## 11. Files to Create/Modify

### New Files
```
backend/exams/services/
└── pronote_export.py              (NEW - 300 lines)

backend/exams/tests/
├── test_pronote_export.py         (NEW - 200 lines)
├── test_pronote_export_api.py     (NEW - 250 lines)
└── test_export_pronote_command.py (NEW - 150 lines)

.zenflow/tasks/export-pronote-csv-format-encoda-2e50/
└── audit.md                        (NEW - manual test checklist)
```

### Modified Files
```
backend/exams/views.py
  - Add PronoteExportView class (~80 lines)

backend/exams/urls.py
  - Add export-pronote route (1 line)

backend/exams/management/commands/export_pronote.py
  - Complete rewrite (~100 lines)
```

**Estimated Total**: ~1100 lines of code (including tests)

---

## 12. Dependencies

### 12.1 Python Dependencies
All dependencies already installed:
- `django >= 5.2`
- `djangorestframework`
- `django-ratelimit`
- `psycopg2` (PostgreSQL)

### 12.2 System Dependencies
None required (uses stdlib `csv`)

---

## 13. Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Score calculation inaccurate | High | Extensive unit tests; document calculation logic clearly |
| PRONOTE rejects CSV format | High | Manual import test before delivery; follow spec strictly |
| Performance issues with large exports | Medium | Query optimization; performance tests with 1000+ copies |
| Rate limiting too strict | Low | Make rate configurable via settings |
| CSV injection vulnerability | Medium | Sanitize comments; escape leading special chars |

---

## 14. Open Questions & Assumptions

### 14.1 Assumptions
1. **Grade calculation**: Annotation-based approach is acceptable for MVP
2. **Coefficient**: Default 1.0 is acceptable; no UI needed for MVP
3. **PRONOTE version**: Target modern PRONOTE (2020+) with UTF-8 support
4. **Max score**: Derived from `grading_structure` JSON field

### 14.2 Clarifications Needed
None blocking at this stage. Implementation can proceed.

---

## 15. Future Enhancements (Post-MVP)

1. **Score Model**: Implement proper Score model to cache calculated grades
2. **Coefficient UI**: Admin interface to configure exam coefficient
3. **Bulk Export**: Export multiple exams as ZIP archive
4. **Historical Exports**: Track export versions over time
5. **PRONOTE API**: Direct integration if API available

---

## Appendix A: CSV Format Reference

### PRONOTE Standard Format
```csv
INE;MATIERE;NOTE;COEFF;COMMENTAIRE
12345678901;MATHEMATIQUES;15,50;1,0;Bon travail
98765432102;MATHEMATIQUES;12,00;1,0;
11223344503;MATHEMATIQUES;18,25;1,0;Excellent
```

### Format Specifications
- **Encoding**: UTF-8 with BOM (`\ufeff`)
- **Delimiter**: Semicolon (`;`)
- **Decimal Separator**: Comma (`,`)
- **Line Ending**: CRLF (`\r\n`)
- **Quoting**: Minimal (only when field contains delimiter or newline)

---

## Appendix B: Error Messages (French)

```python
ERROR_MESSAGES = {
    'no_graded_copies': "Aucune copie corrigée trouvée pour cet examen.",
    'unidentified_copies': "Impossible d'exporter : {count} copie(s) corrigée(s) non identifiée(s).",
    'missing_ine': "Impossible d'exporter : {count} copie(s) sans INE : {examples}",
    'exam_not_found': "Examen {exam_id} introuvable.",
    'invalid_coefficient': "Le coefficient doit être entre 0.1 et 10.0.",
    'rate_limit_exceeded': "Limite de 10 exports par heure atteinte. Réessayez plus tard.",
}
```

---

**Document Status**: Ready for Implementation  
**Next Step**: Implementation (Planning phase)  
**Review**: Requires validation from technical lead before proceeding
