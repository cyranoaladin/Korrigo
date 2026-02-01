"""
API Integration Tests for PRONOTE CSV Export

Tests the PronoteExportView endpoint.
Reference: spec.md section 5.2
"""
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User, Group
from rest_framework.test import APIClient
from rest_framework import status
from exams.models import Exam, Copy
from students.models import Student
from grading.models import Score, Annotation
from core.models import AuditLog
from core.auth import UserRole
from decimal import Decimal


class PronoteExportAPIPermissionTests(TestCase):
    """Test permission requirements for PRONOTE export"""
    
    def setUp(self):
        self.client = APIClient()
        
        self.exam = Exam.objects.create(
            name='Permission Test Exam',
            date='2026-01-31',
            grading_structure=[{"id": "ex1", "max_points": 20}]
        )
        
        # Create users with different roles
        self.admin = User.objects.create_user(
            username='admin',
            password='admin123'
        )
        self.admin_group, _ = Group.objects.get_or_create(name=UserRole.ADMIN)
        self.admin.groups.add(self.admin_group)
        
        self.teacher = User.objects.create_user(
            username='teacher',
            password='teacher123'
        )
        self.teacher_group, _ = Group.objects.get_or_create(name=UserRole.TEACHER)
        self.teacher.groups.add(self.teacher_group)
        
        self.student_user = User.objects.create_user(
            username='student',
            password='student123'
        )
        self.student_group, _ = Group.objects.get_or_create(name=UserRole.STUDENT)
        self.student_user.groups.add(self.student_group)
        
        self.url = reverse('export-pronote', kwargs={'id': self.exam.id})
    
    def test_admin_can_export(self):
        """Test admin user can access export endpoint"""
        self.client.force_login(self.admin)
        
        # Create valid graded copy
        student = Student.objects.create(
            ine='12345678901',
            first_name='Test',
            last_name='Student',
            class_name='TS1'
        )
        copy = Copy.objects.create(
            exam=self.exam,
            anonymous_id='ADM001',
            student=student,
            is_identified=True,
            status=Copy.Status.GRADED
        )
        Score.objects.create(
            copy=copy,
            scores_data={"ex1": 15}
        )
        
        response = self.client.post(self.url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response['Content-Type'], 'text/csv; charset=utf-8')
    
    def test_teacher_cannot_export(self):
        """Test teacher user cannot access export (403 Forbidden)"""
        self.client.force_login(self.teacher)
        
        response = self.client.post(self.url)
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn('error', response.json())
    
    def test_student_cannot_export(self):
        """Test student user cannot access export (403 Forbidden)"""
        self.client.force_login(self.student_user)
        
        response = self.client.post(self.url)
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    
    def test_anonymous_cannot_export(self):
        """Test anonymous user cannot access export (401 or 403)"""
        response = self.client.post(self.url)
        
        # Should be 401 Unauthorized or 403 Forbidden
        self.assertIn(
            response.status_code,
            [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]
        )


class PronoteExportAPIValidationTests(TestCase):
    """Test validation scenarios"""
    
    def setUp(self):
        self.client = APIClient()
        
        self.admin = User.objects.create_user(
            username='admin',
            password='admin123'
        )
        admin_group, _ = Group.objects.get_or_create(name=UserRole.ADMIN)
        self.admin.groups.add(admin_group)
        
        self.client.force_login(self.admin)
        
        self.exam = Exam.objects.create(
            name='Validation Test',
            date='2026-01-31',
            grading_structure=[{"id": "ex1", "max_points": 20}]
        )
        
        self.url = reverse('export-pronote', kwargs={'id': self.exam.id})
        
        self.user = User.objects.create_user(
            username='teacher',
            password='pass'
        )
    
    def test_export_fails_with_no_graded_copies(self):
        """Test export returns 400 when no graded copies exist"""
        response = self.client.post(self.url)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        data = response.json()
        self.assertIn('error', data)
        self.assertIn('details', data)
    
    def test_export_fails_with_unidentified_copies(self):
        """Test export returns 400 with unidentified graded copies"""
        Copy.objects.create(
            exam=self.exam,
            anonymous_id='UNID001',
            is_identified=False,
            status=Copy.Status.GRADED
        )
        
        response = self.client.post(self.url)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        data = response.json()
        self.assertIn('non identifiée', str(data))
    
    def test_export_fails_with_missing_ine(self):
        """Test export returns 400 when students missing INE"""
        student_no_ine = Student.objects.create(
            ine='',  # Empty INE
            first_name='No',
            last_name='INE',
            class_name='TS1'
        )
        
        copy = Copy.objects.create(
            exam=self.exam,
            anonymous_id='NOINE001',
            student=student_no_ine,
            is_identified=True,
            status=Copy.Status.GRADED
        )
        Score.objects.create(
            copy=copy,
            scores_data={"ex1": 12}
        )
        
        response = self.client.post(self.url)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        data = response.json()
        self.assertIn('sans INE', str(data))
    
    def test_export_fails_with_invalid_coefficient(self):
        """Test export returns 400 with invalid coefficient"""
        response = self.client.post(self.url, {'coefficient': 'invalid'})
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        data = response.json()
        self.assertIn('Coefficient invalide', data['error'])


class PronoteExportAPISuccessTests(TestCase):
    """Test successful export scenarios"""
    
    def setUp(self):
        self.client = APIClient()
        
        self.admin = User.objects.create_user(
            username='admin',
            password='admin123'
        )
        admin_group, _ = Group.objects.get_or_create(name=UserRole.ADMIN)
        self.admin.groups.add(admin_group)
        
        self.client.force_login(self.admin)
        
        self.exam = Exam.objects.create(
            name='MATHEMATIQUES',
            date='2026-01-31',
            grading_structure=[{"id": "ex1", "max_points": 20}]
        )
        
        self.student1 = Student.objects.create(
            ine='11111111111',
            first_name='Alice',
            last_name='Dupont',
            class_name='TS1'
        )
        self.student2 = Student.objects.create(
            ine='22222222222',
            first_name='Bob',
            last_name='Martin',
            class_name='TS1'
        )
        
        self.url = reverse('export-pronote', kwargs={'id': self.exam.id})
        
        self.user = User.objects.create_user(
            username='teacher',
            password='pass'
        )
    
    def test_successful_export_returns_csv(self):
        """Test successful export returns CSV file"""
        copy = Copy.objects.create(
            exam=self.exam,
            anonymous_id='SUCCESS001',
            student=self.student1,
            is_identified=True,
            status=Copy.Status.GRADED,
            global_appreciation="Bon travail"
        )
        Score.objects.create(
            copy=copy,
            scores_data={"ex1": 15.5}
        )
        
        response = self.client.post(self.url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response['Content-Type'], 'text/csv; charset=utf-8')
        self.assertIn('attachment', response['Content-Disposition'])
        self.assertIn('export_pronote', response['Content-Disposition'])
    
    def test_csv_has_utf8_bom(self):
        """Test CSV response has UTF-8 BOM"""
        copy = Copy.objects.create(
            exam=self.exam,
            anonymous_id='BOM001',
            student=self.student1,
            is_identified=True,
            status=Copy.Status.GRADED
        )
        Score.objects.create(
            copy=copy,
            scores_data={"ex1": 14}
        )
        
        response = self.client.post(self.url)
        
        content = response.content.decode('utf-8')
        self.assertTrue(content.startswith('\ufeff'))
    
    def test_csv_format_correct(self):
        """Test CSV has correct format (delimiter, decimal, line ending)"""
        copy = Copy.objects.create(
            exam=self.exam,
            anonymous_id='FMT001',
            student=self.student1,
            is_identified=True,
            status=Copy.Status.GRADED,
            global_appreciation="Excellent"
        )
        Score.objects.create(
            copy=copy,
            scores_data={"ex1": 15.5}
        )
        
        response = self.client.post(self.url)
        content = response.content.decode('utf-8')
        
        # Check header
        self.assertIn('INE;MATIERE;NOTE;COEFF;COMMENTAIRE', content)
        
        # Check data row format
        self.assertIn('11111111111;MATHEMATIQUES;15,50;1,0;Excellent', content)
        
        # Check CRLF line endings
        self.assertIn('\r\n', content)
    
    def test_csv_with_custom_coefficient(self):
        """Test CSV with custom coefficient parameter"""
        copy = Copy.objects.create(
            exam=self.exam,
            anonymous_id='COEFF001',
            student=self.student1,
            is_identified=True,
            status=Copy.Status.GRADED
        )
        Score.objects.create(
            copy=copy,
            scores_data={"ex1": 16}
        )
        
        response = self.client.post(self.url, {'coefficient': 2.0})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.content.decode('utf-8')
        
        # Coefficient should be "2,0"
        self.assertIn(';2,0;', content)
    
    def test_csv_with_multiple_students(self):
        """Test CSV export with multiple students"""
        copy1 = Copy.objects.create(
            exam=self.exam,
            anonymous_id='MULTI001',
            student=self.student1,
            is_identified=True,
            status=Copy.Status.GRADED
        )
        copy2 = Copy.objects.create(
            exam=self.exam,
            anonymous_id='MULTI002',
            student=self.student2,
            is_identified=True,
            status=Copy.Status.GRADED
        )
        
        Score.objects.create(copy=copy1, scores_data={"ex1": 15})
        Score.objects.create(copy=copy2, scores_data={"ex1": 12})
        
        response = self.client.post(self.url)
        content = response.content.decode('utf-8')
        
        lines = content.strip().split('\r\n')
        # Header + 2 data rows
        self.assertEqual(len(lines), 3)
        
        # Check both students present
        self.assertIn('11111111111', content)
        self.assertIn('22222222222', content)
    
    def test_csv_special_characters_in_name(self):
        """Test CSV with accented characters in student names"""
        student_accents = Student.objects.create(
            ine='33333333333',
            first_name='François',
            last_name='Müller',
            class_name='TS1'
        )
        
        copy = Copy.objects.create(
            exam=self.exam,
            anonymous_id='ACCENT001',
            student=student_accents,
            is_identified=True,
            status=Copy.Status.GRADED
        )
        Score.objects.create(
            copy=copy,
            scores_data={"ex1": 14}
        )
        
        response = self.client.post(self.url)
        
        # Should successfully export (names not in CSV, only INE)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.content.decode('utf-8')
        self.assertIn('33333333333', content)
    
    def test_csv_comment_with_delimiter(self):
        """Test CSV with comment containing semicolon"""
        copy = Copy.objects.create(
            exam=self.exam,
            anonymous_id='DELIM001',
            student=self.student1,
            is_identified=True,
            status=Copy.Status.GRADED,
            global_appreciation="Bien; mais peut mieux faire"
        )
        Score.objects.create(
            copy=copy,
            scores_data={"ex1": 13}
        )
        
        response = self.client.post(self.url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.content.decode('utf-8')
        
        # Comment should be preserved (CSV writer handles quoting)
        self.assertIn('mais peut mieux faire', content)


class PronoteExportAPIAuditTests(TestCase):
    """Test audit logging for export operations"""
    
    def setUp(self):
        self.client = APIClient()
        
        self.admin = User.objects.create_user(
            username='admin',
            password='admin123'
        )
        admin_group, _ = Group.objects.get_or_create(name=UserRole.ADMIN)
        self.admin.groups.add(admin_group)
        
        self.client.force_login(self.admin)
        
        self.exam = Exam.objects.create(
            name='Audit Test',
            date='2026-01-31',
            grading_structure=[{"id": "ex1", "max_points": 20}]
        )
        
        self.student = Student.objects.create(
            ine='99999999999',
            first_name='Audit',
            last_name='Test',
            class_name='TS1'
        )
        
        self.url = reverse('export-pronote', kwargs={'id': self.exam.id})
        
        self.user = User.objects.create_user(
            username='teacher',
            password='pass'
        )
    
    def test_successful_export_creates_audit_log(self):
        """Test successful export creates audit log entry"""
        copy = Copy.objects.create(
            exam=self.exam,
            anonymous_id='AUDIT001',
            student=self.student,
            is_identified=True,
            status=Copy.Status.GRADED
        )
        Score.objects.create(
            copy=copy,
            scores_data={"ex1": 17}
        )
        
        audit_count_before = AuditLog.objects.count()
        
        response = self.client.post(self.url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Check audit log created
        audit_count_after = AuditLog.objects.count()
        self.assertGreater(audit_count_after, audit_count_before)
        
        # Get latest audit entry
        latest_audit = AuditLog.objects.latest('id')
        self.assertEqual(latest_audit.action, 'export.pronote.success')
        self.assertEqual(latest_audit.resource_type, 'Exam')
        self.assertEqual(latest_audit.resource_id, str(self.exam.id))
        self.assertEqual(latest_audit.user, self.admin)
    
    def test_failed_export_creates_audit_log(self):
        """Test failed export creates audit log entry"""
        audit_count_before = AuditLog.objects.count()
        
        # Try to export with no graded copies (will fail)
        response = self.client.post(self.url)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
        # Check audit log created
        audit_count_after = AuditLog.objects.count()
        self.assertGreater(audit_count_after, audit_count_before)
        
        latest_audit = AuditLog.objects.latest('id')
        self.assertEqual(latest_audit.action, 'export.pronote.failed')
    
    def test_forbidden_export_creates_audit_log(self):
        """Test forbidden export attempt creates audit log"""
        # Login as teacher (non-admin)
        teacher = User.objects.create_user(
            username='teacher_audit',
            password='pass'
        )
        teacher_group, _ = Group.objects.get_or_create(name=UserRole.TEACHER)
        teacher.groups.add(teacher_group)
        
        self.client.force_login(teacher)
        
        audit_count_before = AuditLog.objects.count()
        
        response = self.client.post(self.url)
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        
        # Check audit log created
        audit_count_after = AuditLog.objects.count()
        self.assertGreater(audit_count_after, audit_count_before)
        
        latest_audit = AuditLog.objects.latest('id')
        self.assertEqual(latest_audit.action, 'export.pronote.forbidden')


class PronoteExportAPIRateLimitTests(TestCase):
    """Test rate limiting (10 exports per hour)"""
    
    def setUp(self):
        self.client = APIClient()
        
        self.admin = User.objects.create_user(
            username='admin',
            password='admin123'
        )
        admin_group, _ = Group.objects.get_or_create(name=UserRole.ADMIN)
        self.admin.groups.add(admin_group)
        
        self.client.force_login(self.admin)
        
        self.exam = Exam.objects.create(
            name='Rate Limit Test',
            date='2026-01-31',
            grading_structure=[{"id": "ex1", "max_points": 20}]
        )
        
        self.student = Student.objects.create(
            ine='88888888888',
            first_name='Rate',
            last_name='Limit',
            class_name='TS1'
        )
        
        copy = Copy.objects.create(
            exam=self.exam,
            anonymous_id='RATE001',
            student=self.student,
            is_identified=True,
            status=Copy.Status.GRADED
        )
        Score.objects.create(
            copy=copy,
            scores_data={"ex1": 14}
        )
        
        self.url = reverse('export-pronote', kwargs={'id': self.exam.id})
    
    def test_rate_limit_enforced(self):
        """Test that rate limiting is enforced (10/hour)
        
        Note: This test may be skipped in CI/test environments where
        RATELIMIT_ENABLE=False. Check settings.RATELIMIT_ENABLE.
        """
        from django.conf import settings
        
        if not getattr(settings, 'RATELIMIT_ENABLE', True):
            self.skipTest("Rate limiting disabled in test environment")
        
        # Make 10 requests (should all succeed)
        for i in range(10):
            response = self.client.post(self.url)
            self.assertEqual(
                response.status_code,
                status.HTTP_200_OK,
                f"Request {i+1} should succeed"
            )
        
        # 11th request should be rate limited
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
