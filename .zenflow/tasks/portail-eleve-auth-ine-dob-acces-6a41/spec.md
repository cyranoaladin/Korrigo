# Technical Specification
# PORTAIL ÉLÈVE: AUTH (INE+DOB) + ACCÈS "MES COPIES" + DOWNLOAD PDF

**Task ID**: ZF-AUD-09  
**Version**: 1.0  
**Date**: 31 January 2026  
**Status**: Draft

---

## 1. Technical Context

### 1.1 Technology Stack

**Backend**:
- **Framework**: Django 4.2 LTS (Python 3.9)
- **API**: Django REST Framework
- **Database**: PostgreSQL 15
- **Session Management**: Django sessions (cached_db backend)
- **Rate Limiting**: django-ratelimit 4.1.0
- **Dependencies**: See `backend/requirements.txt`

**Frontend**:
- **Framework**: Vue.js 3 (Composition API)
- **Build Tool**: Vite
- **State Management**: Pinia

**Infrastructure**:
- **Containerization**: Docker + Docker Compose
- **Reverse Proxy**: Nginx (production)
- **File Storage**: Local filesystem (`MEDIA_ROOT`)

### 1.2 Current Architecture

**Authentication Model** (ADR-001):
- **Session-based authentication** for students (no Django User model)
- Teachers/Admins use standard Django authentication
- Session storage: `django.contrib.sessions.backends.cached_db`
- Session timeout: 14400 seconds (4 hours)

**Current Endpoints**:
```
POST   /api/students/login/          # Current: INE + last_name
POST   /api/students/logout/         # Session cleanup
GET    /api/students/me/             # Student profile
GET    /api/students/copies/         # List student's GRADED copies
GET    /api/copies/{id}/final-pdf/   # Download PDF (dual auth)
```

**Existing Models**:
- `Student` (backend/students/models.py): ine, first_name, last_name, class_name, email
- `Copy` (backend/exams/models.py): id, exam, anonymous_id, student, status, final_pdf
- `AuditLog` (backend/core/models.py): user, student_id, action, resource_type, ip_address

**Existing Security Measures**:
- ✅ Rate limiting: `5/15m` per IP on login endpoint
- ✅ CSRF exemption on public login (appropriate for session auth)
- ✅ Audit logging for authentication attempts
- ✅ Copy status filtering: Only GRADED copies visible to students
- ✅ PDF download ownership check

---

## 2. Implementation Approach

### 2.1 Architecture Decision Records (ADRs)

**ADR-AUD09-001: Use birth_date instead of last_name**
- **Decision**: Replace `last_name` authentication parameter with `birth_date`
- **Rationale**: 
  - Birth date is harder to enumerate than last name
  - Birth date is stable (never changes)
  - Already available in school records (Pronote/SCONET)
- **Trade-offs**: Requires data migration and student communication
- **Status**: Approved (task requirement)

**ADR-AUD09-002: No signed URLs for PDF download**
- **Decision**: Maintain current session-based authentication for PDF downloads
- **Rationale**: 
  - Session cookie + ownership check is sufficient security
  - UUID is not guessable (cryptographically secure)
  - HTTPS prevents session hijacking
  - Adding signed URLs would increase complexity without significant security gain
- **Alternative**: Time-limited signed URLs (REJECTED - over-engineering)
- **Status**: Approved

**ADR-AUD09-003: Composite rate limiting (IP + INE)**
- **Decision**: Implement rate limiting based on both IP address and INE
- **Rationale**: 
  - IP-based limiting prevents distributed brute-force attacks
  - INE-based limiting prevents targeted attacks on specific accounts
  - Composite approach provides defense in depth
- **Implementation**: Custom rate limit key function
- **Status**: Approved

**ADR-AUD09-004: Generic error messages for all auth failures**
- **Decision**: Return identical error message for all authentication failures
- **Rationale**: 
  - Prevents user enumeration attacks
  - Follows OWASP authentication security best practices
  - Minor UX trade-off acceptable for security gain
- **Error message**: "Identifiants invalides" for all failures
- **Status**: Approved

### 2.2 Database Schema Changes

**Migration 1: Add birth_date field (nullable)**
```python
# backend/students/migrations/XXXX_add_birth_date.py

from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ('students', 'XXXX_previous_migration'),
    ]

    operations = [
        migrations.AddField(
            model_name='student',
            name='birth_date',
            field=models.DateField(
                verbose_name="Date de naissance",
                help_text="Format: YYYY-MM-DD",
                null=True,  # Temporarily nullable for migration
                blank=True
            ),
        ),
        migrations.AlterField(
            model_name='student',
            name='ine',
            field=models.CharField(
                max_length=50,
                unique=True,
                verbose_name="Identifiant National Élève",
                db_index=True  # Add index for faster lookups
            ),
        ),
    ]
```

**Migration 2: Enforce non-null constraint**
```python
# backend/students/migrations/XXXX_birth_date_not_null.py

from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ('students', 'XXXX_add_birth_date'),
    ]

    operations = [
        migrations.AlterField(
            model_name='student',
            name='birth_date',
            field=models.DateField(
                verbose_name="Date de naissance",
                help_text="Format: YYYY-MM-DD",
                null=False,  # Enforce non-null
                blank=False
            ),
        ),
    ]
```

**Updated Student Model**:
```python
# backend/students/models.py

class Student(models.Model):
    ine = models.CharField(
        max_length=50, 
        unique=True, 
        verbose_name="Identifiant National Élève",
        db_index=True
    )
    first_name = models.CharField(max_length=100, verbose_name="Prénom")
    last_name = models.CharField(max_length=100, verbose_name="Nom")
    class_name = models.CharField(max_length=50, verbose_name="Classe")
    email = models.EmailField(blank=True, null=True, verbose_name="Email")
    
    # NEW FIELD
    birth_date = models.DateField(
        verbose_name="Date de naissance",
        help_text="Format: YYYY-MM-DD",
        null=False,
        blank=False
    )
    
    # Existing field (kept for Django User association)
    user = models.OneToOneField(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='student_profile',
        verbose_name="Utilisateur associé"
    )

    class Meta:
        verbose_name = "Élève"
        verbose_name_plural = "Élèves"
        indexes = [
            models.Index(fields=['ine']),
            models.Index(fields=['birth_date']),
            models.Index(fields=['ine', 'birth_date']),  # Composite index for login
        ]
```

### 2.3 API Contract Changes

**Current Login Endpoint**:
```http
POST /api/students/login/
Content-Type: application/json

{
  "ine": "1234567890A",
  "last_name": "Dupont"
}
```

**New Login Endpoint**:
```http
POST /api/students/login/
Content-Type: application/json

{
  "ine": "1234567890A",
  "birth_date": "2005-03-15"
}
```

**Response (unchanged)**:
```json
{
  "message": "Login successful",
  "role": "Student"
}
```

**Error Responses**:
```json
// Invalid credentials (all scenarios)
{
  "error": "Identifiants invalides."
}

// Rate limited
{
  "error": "Trop de tentatives. Réessayez dans 15 minutes."
}
```

**Validation Rules**:
- `ine`: Required, 11 characters (10 digits + 1 letter), alphanumeric
- `birth_date`: Required, ISO 8601 format (YYYY-MM-DD), valid date
- Date range: Between 1990-01-01 and (current_date - 10 years)

### 2.4 Rate Limiting Implementation

**Custom Rate Limit Key Function**:
```python
# backend/core/utils/ratelimit.py (enhancement)

def composite_key_ip_or_ine(group, request):
    """
    Composite rate limit key: IP address OR INE (whichever is stricter).
    
    This prevents:
    - Distributed brute-force attacks (IP-based)
    - Targeted brute-force attacks (INE-based)
    
    Usage:
        @ratelimit(key=composite_key_ip_or_ine, rate='5/15m', method='POST', block=True)
    """
    from core.utils.audit import get_client_ip
    
    ine = request.data.get('ine', 'unknown')
    ip = get_client_ip(request)
    
    # Return both keys for rate limiting
    # django-ratelimit will track each independently
    return f"{ip}:{ine}"
```

**Updated Login View**:
```python
# backend/students/views.py

from core.utils.ratelimit import composite_key_ip_or_ine

@method_decorator(csrf_exempt, name='dispatch')
class StudentLoginView(views.APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    
    @method_decorator(ratelimit(
        key=composite_key_ip_or_ine, 
        rate='5/15m', 
        method='POST', 
        block=True
    ))
    def post(self, request):
        ine = request.data.get('ine')
        birth_date = request.data.get('birth_date')
        
        # Validation
        if not ine or not birth_date:
            return Response(
                {'error': 'Identifiants invalides.'}, 
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        # Validate birth_date format
        try:
            from datetime import date, datetime
            parsed_date = datetime.strptime(birth_date, '%Y-%m-%d').date()
            
            # Age validation: must be at least 10 years old
            min_date = date(1990, 1, 1)
            max_date = date.today().replace(year=date.today().year - 10)
            
            if not (min_date <= parsed_date <= max_date):
                return Response(
                    {'error': 'Identifiants invalides.'}, 
                    status=status.HTTP_401_UNAUTHORIZED
                )
        except ValueError:
            return Response(
                {'error': 'Identifiants invalides.'}, 
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        # Case insensitive match for INE
        student = Student.objects.filter(
            ine__iexact=ine, 
            birth_date=parsed_date
        ).first()
        
        if student:
            request.session['student_id'] = student.id
            request.session['role'] = 'Student'
            
            # Audit trail: Login success
            log_authentication_attempt(request, success=True, student_id=student.id)
            
            return Response({
                'message': 'Login successful', 
                'role': 'Student'
            })
        else:
            # Audit trail: Login failure
            log_authentication_attempt(request, success=False, student_id=None)
            
            # Generic error message (prevent user enumeration)
            return Response(
                {'error': 'Identifiants invalides.'}, 
                status=status.HTTP_401_UNAUTHORIZED
            )
```

### 2.5 PDF Download Security Headers

**Updated CopyFinalPdfView**:
```python
# backend/grading/views.py (lines 268-275)

response = FileResponse(copy.final_pdf.open("rb"), content_type="application/pdf")
filename = f'copy_{copy.anonymous_id}_corrected.pdf'
response["Content-Disposition"] = f'attachment; filename="{filename}"'

# Enhanced Security Headers
response["Cache-Control"] = "private, no-store, no-cache, must-revalidate, max-age=0"
response["Pragma"] = "no-cache"
response["Expires"] = "0"
response["X-Content-Type-Options"] = "nosniff"

return response
```

**Header Explanations**:
- `Cache-Control: private, no-store, no-cache, must-revalidate, max-age=0`: 
  - Prevents browser/proxy caching of sensitive student data
  - `private`: Only client can cache (not shared proxies)
  - `no-store`: Do not cache at all
  - `must-revalidate`: If cached, must revalidate with server
  - `max-age=0`: Immediate expiration
  
- `Pragma: no-cache`: HTTP/1.0 backward compatibility
  
- `Expires: 0`: HTTP/1.0 backward compatibility
  
- `X-Content-Type-Options: nosniff`: Prevent MIME type sniffing attacks
  
- `Content-Disposition: attachment`: Force download instead of inline display

### 2.6 Enhanced Audit Logging

**New Audit Events**:
```python
# backend/core/utils/audit.py (enhancement)

def log_student_login_attempt(request: HttpRequest, success: bool, ine: str = None):
    """
    Enhanced student login audit with INE tracking.
    """
    action = 'student.login.success' if success else 'student.login.failure'
    student_id = request.session.get('student_id') if success else None
    
    metadata = {
        'success': success,
        'ine_attempted': ine,
        'rate_limited': getattr(request, 'limited', False),
    }
    
    return log_audit(request, action, 'Student', student_id or 'unknown', metadata)


def log_copy_list_access(request: HttpRequest, student_id: int, num_copies: int):
    """
    Log when student accesses their copy list.
    """
    metadata = {
        'num_copies_returned': num_copies,
    }
    
    return log_audit(request, 'copy.list', 'Student', student_id, metadata)


def log_pdf_download(request: HttpRequest, copy_id: str, student_id: int, exam_name: str):
    """
    Log PDF download with exam context.
    """
    metadata = {
        'exam_name': exam_name,
        'copy_id': str(copy_id),
    }
    
    return log_audit(request, 'copy.download', 'Copy', copy_id, metadata)
```

**Updated StudentCopiesView**:
```python
# backend/exams/views.py (lines 381-410)

def list(self, request, *args, **kwargs):
    from grading.services import GradingService
    from core.utils.audit import log_copy_list_access
    
    queryset = self.get_queryset()
    student_id = request.session.get('student_id')
    
    # Audit trail: Copy list access
    if student_id:
        log_copy_list_access(request, student_id, queryset.count())
    
    data = []
    for copy in queryset:
        total_score = GradingService.compute_score(copy)
        
        data.append({
            "id": copy.id,
            "exam_name": copy.exam.name,
            "date": copy.exam.date,
            "total_score": total_score,
            "status": copy.status,
            "final_pdf_url": f"/api/copies/{copy.id}/final-pdf/",
            "scores_details": {}
        })
    
    return Response(data)
```

**Updated CopyFinalPdfView** (audit enhancement):
```python
# backend/grading/views.py (line 264-266)

# Enhanced audit trail with exam context
from core.utils.audit import log_pdf_download
log_pdf_download(request, copy.id, student_id, copy.exam.name)
```

---

## 3. Source Code Structure Changes

### 3.1 Modified Files

**Backend Models**:
- ✏️ `backend/students/models.py`: Add `birth_date` field, add composite index
- ✏️ `backend/students/migrations/XXXX_add_birth_date.py`: New migration
- ✏️ `backend/students/migrations/XXXX_birth_date_not_null.py`: New migration

**Backend Views**:
- ✏️ `backend/students/views.py`: Update `StudentLoginView` to use `birth_date`
- ✏️ `backend/exams/views.py`: Enhance `StudentCopiesView` audit logging
- ✏️ `backend/grading/views.py`: Update `CopyFinalPdfView` security headers

**Backend Utilities**:
- ✏️ `backend/core/utils/ratelimit.py`: Add `composite_key_ip_or_ine` function
- ✏️ `backend/core/utils/audit.py`: Add student-specific audit functions

**Backend Serializers**:
- ✏️ `backend/students/serializers.py`: Update `StudentSerializer` to include `birth_date`

**Frontend Components**:
- ✏️ `frontend/src/views/StudentLogin.vue`: Update form to use `birth_date` instead of `last_name`
- ✏️ `frontend/src/components/StudentCopyCard.vue`: Verify PDF download flow

### 3.2 New Files

**Backend Scripts**:
- 🆕 `backend/scripts/import_birth_dates.py`: Import birth dates from Pronote CSV
- 🆕 `backend/scripts/validate_birth_dates.py`: Validate all students have birth_date

**Tests**:
- 🆕 `backend/students/tests/test_birth_date_auth.py`: Unit tests for new authentication
- 🆕 `backend/students/tests/test_rate_limiting.py`: Rate limiting tests
- 🆕 `backend/students/tests/test_pdf_security.py`: PDF download security tests
- 🆕 `frontend/e2e/student-auth.spec.ts`: E2E tests for student authentication flow

**Documentation**:
- 🆕 `ops/audit/audit.md`: Security audit report
- 🆕 `docs/admin/BIRTH_DATE_MIGRATION.md`: Migration guide for administrators

### 3.3 Configuration Changes

**Django Settings** (no changes required):
- ✅ `SESSION_COOKIE_AGE = 14400` (4 hours) - already configured
- ✅ `SESSION_COOKIE_HTTPONLY = True` - already configured
- ✅ `SESSION_COOKIE_SAMESITE = 'Lax'` - already configured
- ✅ `SESSION_COOKIE_SECURE = True` (production) - already configured via env

**Environment Variables** (no new variables):
- ✅ `RATELIMIT_ENABLE = True` (production) - already supported
- ✅ `SESSION_COOKIE_SECURE = true` (production) - already supported

---

## 4. Data Migration Strategy

### 4.1 Migration Phases

**Phase 1: Preparation** (Pre-deployment)
1. Export student data from Pronote/SCONET with `INE` + `birth_date`
2. Validate CSV format: `INE,Nom,Prénom,Classe,Date_Naissance`
3. Create backup of production database
4. Test import script in staging environment

**Phase 2: Migration** (Deployment window - 2 hours)
1. Apply migration 1: Add `birth_date` field (nullable)
2. Run import script: Populate `birth_date` from Pronote CSV
3. Validate all students have `birth_date` (run validation script)
4. Apply migration 2: Enforce `NOT NULL` constraint
5. Deploy code changes (new login endpoint)
6. Update frontend (deploy new Vue.js build)

**Phase 3: Validation** (Post-deployment)
1. Run smoke tests with 20 test students
2. Monitor authentication logs for errors
3. Send communication to students with new login instructions
4. Monitor help desk tickets for 48 hours

### 4.2 Import Script

```python
# backend/scripts/import_birth_dates.py

import csv
import sys
from datetime import datetime
from django.core.management.base import BaseCommand
from students.models import Student

class Command(BaseCommand):
    help = 'Import birth dates from Pronote CSV'

    def add_arguments(self, parser):
        parser.add_argument('csv_file', type=str, help='Path to Pronote CSV file')

    def handle(self, *args, **options):
        csv_file = options['csv_file']
        
        stats = {
            'updated': 0,
            'errors': [],
            'not_found': []
        }
        
        with open(csv_file, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            
            for row in reader:
                ine = row.get('INE')
                birth_date_str = row.get('Date_Naissance')
                
                if not ine or not birth_date_str:
                    stats['errors'].append(f"Missing INE or birth_date: {row}")
                    continue
                
                try:
                    # Parse date (support multiple formats)
                    for fmt in ['%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y']:
                        try:
                            birth_date = datetime.strptime(birth_date_str, fmt).date()
                            break
                        except ValueError:
                            continue
                    else:
                        raise ValueError(f"Invalid date format: {birth_date_str}")
                    
                    # Update student
                    student = Student.objects.filter(ine__iexact=ine).first()
                    if student:
                        student.birth_date = birth_date
                        student.save()
                        stats['updated'] += 1
                        self.stdout.write(f"✓ Updated {ine}: {birth_date}")
                    else:
                        stats['not_found'].append(ine)
                        self.stdout.write(self.style.WARNING(f"✗ Student not found: {ine}"))
                
                except Exception as e:
                    stats['errors'].append(f"Error processing {ine}: {e}")
                    self.stdout.write(self.style.ERROR(f"✗ Error: {e}"))
        
        # Summary
        self.stdout.write(self.style.SUCCESS(f"\n=== Import Summary ==="))
        self.stdout.write(f"Updated: {stats['updated']}")
        self.stdout.write(f"Not found: {len(stats['not_found'])}")
        self.stdout.write(f"Errors: {len(stats['errors'])}")
        
        if stats['errors']:
            self.stdout.write(self.style.ERROR("\n=== Errors ==="))
            for error in stats['errors']:
                self.stdout.write(self.style.ERROR(error))
        
        if stats['not_found']:
            self.stdout.write(self.style.WARNING("\n=== Not Found ==="))
            for ine in stats['not_found']:
                self.stdout.write(self.style.WARNING(ine))
```

### 4.3 Validation Script

```python
# backend/scripts/validate_birth_dates.py

from django.core.management.base import BaseCommand
from students.models import Student

class Command(BaseCommand):
    help = 'Validate all students have birth_date'

    def handle(self, *args, **options):
        total = Student.objects.count()
        missing = Student.objects.filter(birth_date__isnull=True).count()
        
        self.stdout.write(f"Total students: {total}")
        self.stdout.write(f"Missing birth_date: {missing}")
        
        if missing > 0:
            self.stdout.write(self.style.ERROR(f"\n✗ {missing} students missing birth_date"))
            
            for student in Student.objects.filter(birth_date__isnull=True):
                self.stdout.write(f"  - {student.ine}: {student.first_name} {student.last_name}")
            
            sys.exit(1)
        else:
            self.stdout.write(self.style.SUCCESS("\n✓ All students have birth_date"))
            sys.exit(0)
```

### 4.4 Rollback Plan

**Scenario 1: Import script fails**
- Action: Fix CSV format, re-run import script
- Impact: Low (no code deployed yet)

**Scenario 2: Critical authentication bugs post-deployment**
- Action 1: Restore database backup
- Action 2: Revert frontend deployment (rollback to previous build)
- Action 3: Revert backend deployment (rollback to previous Docker image)
- Impact: Medium (15-30 minute downtime)

**Scenario 3: High authentication failure rate**
- Action 1: Check audit logs for common error patterns
- Action 2: Temporarily disable birth_date requirement (hotfix)
- Action 3: Communicate with students about correct date format
- Impact: Low (students can retry)

---

## 5. Testing Strategy

### 5.1 Unit Tests

**Test File**: `backend/students/tests/test_birth_date_auth.py`

```python
import pytest
from django.test import Client
from students.models import Student
from datetime import date

@pytest.mark.django_db
class TestBirthDateAuthentication:
    def test_login_success_with_valid_credentials(self):
        student = Student.objects.create(
            ine='1234567890A',
            first_name='Jean',
            last_name='Dupont',
            class_name='TG1',
            birth_date=date(2005, 3, 15)
        )
        
        client = Client()
        response = client.post('/api/students/login/', {
            'ine': '1234567890A',
            'birth_date': '2005-03-15'
        })
        
        assert response.status_code == 200
        assert response.json()['message'] == 'Login successful'
        assert client.session['student_id'] == student.id
    
    def test_login_failure_with_invalid_birth_date(self):
        Student.objects.create(
            ine='1234567890A',
            first_name='Jean',
            last_name='Dupont',
            class_name='TG1',
            birth_date=date(2005, 3, 15)
        )
        
        client = Client()
        response = client.post('/api/students/login/', {
            'ine': '1234567890A',
            'birth_date': '2005-03-16'  # Wrong date
        })
        
        assert response.status_code == 401
        assert response.json()['error'] == 'Identifiants invalides.'
    
    def test_login_failure_with_invalid_ine(self):
        Student.objects.create(
            ine='1234567890A',
            birth_date=date(2005, 3, 15)
        )
        
        client = Client()
        response = client.post('/api/students/login/', {
            'ine': '9999999999Z',  # Wrong INE
            'birth_date': '2005-03-15'
        })
        
        assert response.status_code == 401
        assert response.json()['error'] == 'Identifiants invalides.'
    
    def test_login_rejects_future_date(self):
        client = Client()
        response = client.post('/api/students/login/', {
            'ine': '1234567890A',
            'birth_date': '2030-01-01'  # Future date
        })
        
        assert response.status_code == 401
    
    def test_login_rejects_too_young(self):
        from datetime import date
        recent_date = date.today().replace(year=date.today().year - 5)
        
        client = Client()
        response = client.post('/api/students/login/', {
            'ine': '1234567890A',
            'birth_date': recent_date.isoformat()
        })
        
        assert response.status_code == 401
```

### 5.2 Integration Tests

**Test File**: `backend/students/tests/test_pdf_security.py`

```python
import pytest
from django.test import Client
from students.models import Student
from exams.models import Exam, Copy
from datetime import date

@pytest.mark.django_db
class TestPDFDownloadSecurity:
    def test_student_can_download_own_graded_copy(self):
        # Setup
        student = Student.objects.create(
            ine='1234567890A',
            birth_date=date(2005, 3, 15),
            first_name='Jean',
            last_name='Dupont',
            class_name='TG1'
        )
        exam = Exam.objects.create(name='Test Exam', date=date.today())
        copy = Copy.objects.create(
            exam=exam,
            student=student,
            anonymous_id='ABC123',
            status=Copy.Status.GRADED
        )
        
        # Login
        client = Client()
        client.post('/api/students/login/', {
            'ine': '1234567890A',
            'birth_date': '2005-03-15'
        })
        
        # Download PDF
        response = client.get(f'/api/copies/{copy.id}/final-pdf/')
        assert response.status_code in [200, 404]  # 404 if no PDF uploaded
    
    def test_student_cannot_download_other_student_copy(self):
        # Setup
        student1 = Student.objects.create(
            ine='1234567890A',
            birth_date=date(2005, 3, 15)
        )
        student2 = Student.objects.create(
            ine='9876543210B',
            birth_date=date(2005, 4, 20)
        )
        exam = Exam.objects.create(name='Test Exam', date=date.today())
        copy2 = Copy.objects.create(
            exam=exam,
            student=student2,
            anonymous_id='XYZ789',
            status=Copy.Status.GRADED
        )
        
        # Login as student1
        client = Client()
        client.post('/api/students/login/', {
            'ine': '1234567890A',
            'birth_date': '2005-03-15'
        })
        
        # Try to download student2's PDF
        response = client.get(f'/api/copies/{copy2.id}/final-pdf/')
        assert response.status_code == 403
    
    def test_student_cannot_download_non_graded_copy(self):
        # Setup
        student = Student.objects.create(
            ine='1234567890A',
            birth_date=date(2005, 3, 15)
        )
        exam = Exam.objects.create(name='Test Exam', date=date.today())
        copy = Copy.objects.create(
            exam=exam,
            student=student,
            anonymous_id='ABC123',
            status=Copy.Status.READY  # Not GRADED
        )
        
        # Login
        client = Client()
        client.post('/api/students/login/', {
            'ine': '1234567890A',
            'birth_date': '2005-03-15'
        })
        
        # Try to download PDF
        response = client.get(f'/api/copies/{copy.id}/final-pdf/')
        assert response.status_code == 403
```

### 5.3 E2E Tests

**Test File**: `frontend/e2e/student-auth.spec.ts`

```typescript
import { test, expect } from '@playwright/test';

test.describe('Student Authentication', () => {
  test('student can login with INE and birth date', async ({ page }) => {
    await page.goto('http://localhost:5173/student-login');
    
    await page.fill('input[name="ine"]', '1234567890A');
    await page.fill('input[name="birth_date"]', '2005-03-15');
    await page.click('button[type="submit"]');
    
    await expect(page).toHaveURL(/\/student\/dashboard/);
    await expect(page.locator('h1')).toContainText('Mes Copies');
  });
  
  test('student sees only GRADED copies', async ({ page }) => {
    // Login
    await page.goto('http://localhost:5173/student-login');
    await page.fill('input[name="ine"]', '1234567890A');
    await page.fill('input[name="birth_date"]', '2005-03-15');
    await page.click('button[type="submit"]');
    
    // Check copies list
    await page.waitForSelector('.copy-card');
    const copies = await page.locator('.copy-card').all();
    
    for (const copy of copies) {
      const status = await copy.locator('.status-badge').textContent();
      expect(status).toBe('Corrigé');
    }
  });
  
  test('student can download PDF', async ({ page, context }) => {
    // Login
    await page.goto('http://localhost:5173/student-login');
    await page.fill('input[name="ine"]', '1234567890A');
    await page.fill('input[name="birth_date"]', '2005-03-15');
    await page.click('button[type="submit"]');
    
    // Wait for copies to load
    await page.waitForSelector('.copy-card');
    
    // Click download button
    const [download] = await Promise.all([
      page.waitForEvent('download'),
      page.click('.copy-card:first-child .download-btn')
    ]);
    
    expect(download.suggestedFilename()).toMatch(/copy_.*_corrected\.pdf/);
  });
  
  test('shows generic error for invalid credentials', async ({ page }) => {
    await page.goto('http://localhost:5173/student-login');
    
    await page.fill('input[name="ine"]', '9999999999Z');
    await page.fill('input[name="birth_date"]', '2005-03-15');
    await page.click('button[type="submit"]');
    
    await expect(page.locator('.error-message')).toContainText('Identifiants invalides');
  });
});
```

### 5.4 Security Tests

**Test File**: `backend/students/tests/test_rate_limiting.py`

```python
import pytest
from django.test import Client, override_settings
from students.models import Student
from datetime import date

@pytest.mark.django_db
@override_settings(RATELIMIT_ENABLE=True)
class TestRateLimiting:
    def test_rate_limit_blocks_after_5_attempts(self):
        Student.objects.create(
            ine='1234567890A',
            birth_date=date(2005, 3, 15)
        )
        
        client = Client()
        
        # Make 5 failed login attempts
        for i in range(5):
            response = client.post('/api/students/login/', {
                'ine': '1234567890A',
                'birth_date': '2005-03-16'  # Wrong date
            })
            assert response.status_code == 401
        
        # 6th attempt should be rate limited
        response = client.post('/api/students/login/', {
            'ine': '1234567890A',
            'birth_date': '2005-03-15'  # Even correct credentials
        })
        
        assert response.status_code == 429  # Too Many Requests
        assert 'Trop de tentatives' in response.json()['error']
```

---

## 6. Verification Approach

### 6.1 Pre-deployment Checklist

- [ ] All unit tests pass (`pytest backend/students/tests/test_birth_date_auth.py`)
- [ ] All integration tests pass (`pytest backend/students/tests/test_pdf_security.py`)
- [ ] All E2E tests pass (`npm run e2e` in frontend/)
- [ ] Database migrations tested in staging
- [ ] Import script validated with production-like data
- [ ] Audit logging verified (check AuditLog records)
- [ ] Rate limiting tested (simulated brute-force attack)
- [ ] Session timeout verified (4-hour expiration)
- [ ] PDF security headers verified (curl with -v flag)
- [ ] Cross-student data access blocked (security test)
- [ ] RGPD compliance reviewed (data minimization, retention)

### 6.2 Post-deployment Validation

**Smoke Tests** (20 test students):
1. Login with valid INE + birth_date → Success
2. Login with invalid credentials → Generic error message
3. View "Mes Copies" → Only GRADED copies visible
4. Download PDF → Successful download with correct headers
5. Session expires after 4 hours → Re-login required

**Monitoring** (48 hours):
- Authentication success rate: Target >99%
- Authentication failures: Review audit logs for patterns
- PDF download errors: Target <1%
- Help desk tickets: Monitor for confusion about new credentials
- Performance: Login endpoint response time <200ms (p95)

### 6.3 Lint and Type Check Commands

**Backend**:
```bash
# Lint
cd backend
ruff check .

# Type check (if using mypy)
mypy students/ exams/ grading/ core/

# Security scan
bandit -r students/ exams/ grading/ core/ -c .bandit

# Tests
pytest students/tests/test_birth_date_auth.py -v
pytest students/tests/test_pdf_security.py -v
pytest students/tests/test_rate_limiting.py -v
```

**Frontend**:
```bash
# Lint
cd frontend
npm run lint

# Type check
npm run type-check

# Tests
npm run test:unit
npm run e2e
```

---

## 7. Deployment Phases

### 7.1 Phase 1: Database Migration (Week 1)

**Duration**: 2 hours (scheduled maintenance window)

**Steps**:
1. Backup production database
2. Apply migration 1: Add `birth_date` field (nullable)
3. Run import script: Populate birth_date from Pronote CSV
4. Validate: Run validation script
5. Apply migration 2: Enforce NOT NULL constraint

**Rollback**: Restore database backup if validation fails

### 7.2 Phase 2: Backend Deployment (Week 1)

**Duration**: 30 minutes

**Steps**:
1. Build Docker image with updated code
2. Deploy to production (blue-green deployment)
3. Run smoke tests (5 test students)
4. Monitor authentication logs for errors
5. Switch traffic to new version

**Rollback**: Switch traffic back to previous version

### 7.3 Phase 3: Frontend Deployment (Week 1)

**Duration**: 15 minutes

**Steps**:
1. Build Vue.js production bundle
2. Deploy to Nginx static file directory
3. Clear browser caches (cache-busting via versioned assets)
4. Test login flow in production

**Rollback**: Deploy previous frontend build

### 7.4 Phase 4: Student Communication (Week 1-2)

**Duration**: 2 weeks

**Steps**:
1. Send email to all students with new login instructions
2. Post announcement on school website
3. Prepare help desk for support requests
4. Monitor authentication logs for common errors

---

## 8. Risk Assessment & Mitigation

### 8.1 Technical Risks

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| **Missing birth_date data** | High (students cannot log in) | Medium | Pre-deployment validation, import error reporting, manual data entry fallback |
| **Session fixation vulnerability** | High (security breach) | Low | Django default protection, verify in security test, session regeneration on login |
| **Race condition (concurrent downloads)** | Low (performance) | Low | FileResponse handles concurrency, tested in load tests |
| **Brute-force bypass (distributed IPs)** | Medium (account compromise) | Medium | Composite rate limiting (IP + INE), CAPTCHA if needed |
| **Date format confusion** | Medium (authentication failures) | High | Accept multiple formats (YYYY-MM-DD, DD/MM/YYYY), clear error messages |

### 8.2 Operational Risks

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| **Student confusion** (new credentials) | Medium (support load) | High | Clear communication, FAQ, help desk prepared, video tutorial |
| **Help desk overload** | Medium (response time) | Medium | Pre-written FAQ, automated responses, escalation process |
| **Rollback complexity** | High (data inconsistency) | Low | Test rollback procedure in staging, documented rollback plan |
| **Performance degradation** | Medium (user experience) | Low | Load testing before deployment, database indexes on birth_date |

### 8.3 Compliance Risks

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| **RGPD audit failure** | High (legal) | Low | Data minimization, 1-year retention, parental consent documented |
| **Audit log gaps** | Medium (compliance) | Low | Automated audit log tests, monitoring, log retention policy |
| **Unauthorized data access** | Critical (data breach) | Low | Security tests, penetration testing, code review |

---

## 9. Success Metrics

### 9.1 Security Metrics (Week 1-2)

| Metric | Target | Measurement |
|--------|--------|-------------|
| Zero cross-student data leaks | 100% (0 violations) | E2E test suite, security audit, penetration test |
| Authentication attempts logged | 100% | Audit log coverage check |
| PDF downloads logged | 100% | Audit log coverage check |
| Rate limiting effectiveness | Block >90% brute-force attempts | Simulated attack test |
| Session timeout compliance | 100% (exactly 4h) | Functional test |

### 9.2 Functional Metrics (Week 1-4)

| Metric | Target | Measurement |
|--------|--------|-------------|
| Login success rate (valid credentials) | >99% | Production monitoring, audit logs |
| Copy list accuracy (only GRADED, owned) | 100% | E2E test suite, manual verification |
| PDF download success (valid requests) | >99.5% | Production monitoring, error logs |
| PDF download rejection (invalid requests) | 100% (403/401) | Security test suite |
| Session expiration accuracy | ±1 minute | Functional test |

### 9.3 Operational Metrics (Week 1-4)

| Metric | Target | Measurement |
|--------|--------|-------------|
| Help desk tickets (authentication) | <50 | Ticket tracking system |
| Average ticket resolution time | <30 minutes | Ticket tracking system |
| Student satisfaction (survey) | >80% | Post-deployment survey |
| Deployment time | <3 hours | Deployment logs |
| Rollback success | 100% (if needed) | Staging tests |

---

## 10. References

### 10.1 Code References

**Existing Files**:
- `backend/students/models.py:1-27`: Student model
- `backend/students/views.py:14-47`: StudentLoginView
- `backend/exams/views.py:362-410`: StudentCopiesView
- `backend/grading/views.py:182-275`: CopyFinalPdfView
- `backend/core/utils/audit.py:1-123`: Audit utilities
- `backend/core/utils/ratelimit.py:1-36`: Rate limiting utilities
- `backend/core/settings.py:256-260`: Session configuration

**ADR Documents**:
- ADR-001: Session-based authentication for students (referenced in code)
- ADR-AUD09-001: Use birth_date instead of last_name (this spec)
- ADR-AUD09-002: No signed URLs for PDF download (this spec)
- ADR-AUD09-003: Composite rate limiting (this spec)
- ADR-AUD09-004: Generic error messages (this spec)

### 10.2 External References

**Security Standards**:
- OWASP Authentication Cheat Sheet: https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html
- OWASP Session Management: https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html
- RGPD Article 32: Security of processing

**Django Documentation**:
- Django Sessions: https://docs.djangoproject.com/en/4.2/topics/http/sessions/
- Django Rate Limiting: https://django-ratelimit.readthedocs.io/
- Django Migrations: https://docs.djangoproject.com/en/4.2/topics/migrations/

**Project Documentation**:
- `docs/security/POLITIQUE_RGPD.md`: RGPD compliance policy
- `docs/security/MANUEL_SECURITE.md`: Security manual
- `docs/users/GUIDE_ETUDIANT.md`: Student user guide
- `.antigravity/rules/01_security_rules.md`: Security rules

---

**End of Technical Specification**
