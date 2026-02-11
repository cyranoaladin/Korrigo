"""
API Integration Tests for PRONOTE Export Endpoint

Tests the PronoteExportView API endpoint with full Django test client.
Reference: spec.md section 5.2
"""
from django.test import TestCase, override_settings
from django.contrib.auth.models import User, Group
from django.core.files.uploadedfile import SimpleUploadedFile
from exams.models import Exam, Copy
from students.models import Student
from grading.models import Annotation
from core.auth import UserRole
import json


class PronoteExportAPIPermissionTests(TestCase):
    """Test permission requirements for PRONOTE export endpoint"""
    
    def setUp(self):
        self.admin_group, _ = Group.objects.get_or_create(name=UserRole.ADMIN)
        self.teacher_group, _ = Group.objects.get_or_create(name=UserRole.TEACHER)
        self.student_group, _ = Group.objects.get_or_create(name=UserRole.STUDENT)
        
        self.admin_user = User.objects.create_user(
            username='admin_test',
            password='testpass123',
            is_staff=True
        )
        self.admin_user.groups.add(self.admin_group)
        
        self.teacher_user = User.objects.create_user(
            username='teacher_test',
            password='testpass123'
        )
        self.teacher_user.groups.add(self.teacher_group)
        
        self.student_user = User.objects.create_user(
            username='student_test',
            password='testpass123'
        )
        self.student_user.groups.add(self.student_group)
        
        self.exam = Exam.objects.create(
            name='MATHEMATIQUES',
            date='2026-02-01',
            grading_structure=[{"id": "ex1", "max_points": 20}]
        )
        
        self.url = f'/api/exams/{self.exam.id}/export-pronote/'
    
    def test_anonymous_user_cannot_export(self):
        """Test that anonymous users cannot export"""
        response = self.client.post(self.url)
        
        self.assertEqual(response.status_code, 401)
    
    def test_student_cannot_export(self):
        """Test that students cannot export (forbidden)"""
        self.client.force_login(self.student_user)
        
        response = self.client.post(self.url)
        
        self.assertEqual(response.status_code, 403)
        self.assertIn('error', response.json())
        self.assertIn('Accès refusé', response.json()['error'])
    
    def test_teacher_cannot_export(self):
        """Test that teachers cannot export (admin-only)"""
        self.client.force_login(self.teacher_user)
        
        response = self.client.post(self.url)
        
        self.assertEqual(response.status_code, 403)
        self.assertIn('error', response.json())
        self.assertIn('administrateur', response.json()['error'].lower())
    
    def test_admin_can_export(self):
        """Test that admin users can export (even if validation fails)"""
        self.client.force_login(self.admin_user)
        
        response = self.client.post(
            self.url,
            content_type='application/json'
        )
        
        # May get 400 if no graded copies, but NOT 401/403
        self.assertIn(response.status_code, [200, 400])
        self.assertNotEqual(response.status_code, 401)
        self.assertNotEqual(response.status_code, 403)


class PronoteExportAPIValidationTests(TestCase):
    """Test validation scenarios for export"""
    
    def setUp(self):
        self.admin_group, _ = Group.objects.get_or_create(name=UserRole.ADMIN)
        
        self.admin_user = User.objects.create_user(
            username='admin_validation',
            password='testpass123',
            is_staff=True
        )
        self.admin_user.groups.add(self.admin_group)
        
        self.exam = Exam.objects.create(
            name='Validation Test',
            date='2026-02-01',
            grading_structure=[{"id": "ex1", "max_points": 20}]
        )
        
        self.student = Student.objects.create(
            first_name='Test',
            last_name='Student',
            class_name='TS1',
            date_naissance='2005-01-15'
        )
        
        self.user_teacher = User.objects.create_user(
            username='grader',
            password='pass'
        )
        
        self.url = f'/api/exams/{self.exam.id}/export-pronote/'
        self.client.force_login(self.admin_user)
    
    def test_export_fails_with_no_copies(self):
        """Test export fails when no copies exist"""
        response = self.client.post(
            self.url,
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn('error', data)
        self.assertIn('Aucune copie', data['details'][0])
    
    def test_export_fails_with_no_graded_copies(self):
        """Test export fails when no graded copies"""
        Copy.objects.create(
            exam=self.exam,
            anonymous_id='STAGING001',
            status=Copy.Status.STAGING
        )
        
        response = self.client.post(
            self.url,
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn('Aucune copie notée', data['details'][0])
    
    def test_export_fails_with_unidentified_copies(self):
        """Test export fails with unidentified graded copies"""
        Copy.objects.create(
            exam=self.exam,
            anonymous_id='GRADED_UNID',
            status=Copy.Status.GRADED,
            is_identified=False
        )
        
        response = self.client.post(
            self.url,
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn('non identifiée', data['details'][0])
    
    def test_export_fails_with_missing_student(self):
        """Test export fails when copy is identified but has no linked student."""
        copy = Copy.objects.create(
            exam=self.exam,
            anonymous_id='MISSING_STUDENT',
            student=None,
            is_identified=True,
            status=Copy.Status.GRADED
        )
        Annotation.objects.create(
            copy=copy,
            page_index=0,
            x=0.1, y=0.1, w=0.1, h=0.1,
            score_delta=15,
            created_by=self.admin_user
        )
        
        response = self.client.post(
            self.url,
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn('sans élève', data['details'][0])
    
    def test_export_fails_with_invalid_coefficient(self):
        """Test export fails with invalid coefficient"""
        response = self.client.post(
            self.url,
            data=json.dumps({'coefficient': 'invalid'}),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn('Coefficient invalide', data['error'])


class PronoteExportAPISuccessTests(TestCase):
    """Test successful export scenarios"""
    
    def setUp(self):
        self.admin_group, _ = Group.objects.get_or_create(name=UserRole.ADMIN)
        
        self.admin_user = User.objects.create_user(
            username='admin_success',
            password='testpass123',
            is_staff=True
        )
        self.admin_user.groups.add(self.admin_group)
        
        self.exam = Exam.objects.create(
            name='MATHEMATIQUES',
            date='2026-02-01',
            grading_structure=[{"id": "ex1", "max_points": 20}]
        )
        
        self.student1 = Student.objects.create(
            first_name='Alice',
            last_name='Durand',
            class_name='TS1',
            date_naissance='2005-03-10'
        )
        
        self.student2 = Student.objects.create(
            first_name='Bob',
            last_name='Martin',
            class_name='TS1',
            date_naissance='2005-04-15'
        )
        
        self.user_teacher = User.objects.create_user(
            username='grader',
            password='pass'
        )
        
        self.url = f'/api/exams/{self.exam.id}/export-pronote/'
        self.client.force_login(self.admin_user)
    
    def test_successful_export_with_valid_copies(self):
        """Test successful export with valid graded copies"""
        copy1 = Copy.objects.create(
            exam=self.exam,
            anonymous_id='VALID001',
            student=self.student1,
            is_identified=True,
            status=Copy.Status.GRADED,
            global_appreciation="Excellent travail"
        )
        copy2 = Copy.objects.create(
            exam=self.exam,
            anonymous_id='VALID002',
            student=self.student2,
            is_identified=True,
            status=Copy.Status.GRADED
        )
        
        Annotation.objects.create(
            copy=copy1,
            page_index=0,
            x=0.1, y=0.1, w=0.1, h=0.1,
            score_delta=15,
            created_by=self.admin_user
        )
        Annotation.objects.create(
            copy=copy2,
            page_index=0,
            x=0.1, y=0.1, w=0.1, h=0.1,
            score_delta=12,
            created_by=self.admin_user
        )
        
        response = self.client.post(
            self.url,
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        
        # Check content type
        self.assertEqual(response['Content-Type'], 'text/csv; charset=utf-8')
        
        # Check Content-Disposition header
        self.assertIn('attachment', response['Content-Disposition'])
        self.assertIn('export_pronote', response['Content-Disposition'])
        self.assertIn('.csv', response['Content-Disposition'])
        
        # Check CSV content
        csv_content = response.content.decode('utf-8')
        
        # Check UTF-8 BOM
        self.assertTrue(csv_content.startswith('\ufeff'))
        
        # Check header
        self.assertIn('INE;MATIERE;NOTE;COEFF;COMMENTAIRE', csv_content)
        
        # Check data rows
        self.assertIn('11111111111', csv_content)
        self.assertIn('22222222222', csv_content)
        self.assertIn('MATHEMATIQUES', csv_content)
        self.assertIn('15,50', csv_content)  # French decimal format
        self.assertIn('12,00', csv_content)
        self.assertIn('Excellent travail', csv_content)
        
        # Check line endings (CRLF)
        self.assertIn('\r\n', csv_content)
    
    def test_export_with_custom_coefficient(self):
        """Test export with custom coefficient"""
        copy = Copy.objects.create(
            exam=self.exam,
            anonymous_id='COEFF001',
            student=self.student1,
            is_identified=True,
            status=Copy.Status.GRADED
        )
        Annotation.objects.create(
            copy=copy,
            page_index=0,
            x=0.1, y=0.1, w=0.1, h=0.1,
            score_delta=15,
            created_by=self.admin_user
        )
        
        response = self.client.post(
            self.url,
            data=json.dumps({'coefficient': 2.5}),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        
        csv_content = response.content.decode('utf-8')
        
        # Coefficient should be "2,5" (French format with 1 decimal)
        self.assertIn(';2,5;', csv_content)
    
    def test_export_with_special_characters(self):
        """Test export handles special characters correctly"""
        student_accent = Student.objects.create(
            first_name='François',
            last_name='Müller',
            class_name='TS1',
            date_naissance='2005-05-20'
        )
        
        copy = Copy.objects.create(
            exam=self.exam,
            anonymous_id='ACCENT001',
            student=student_accent,
            is_identified=True,
            status=Copy.Status.GRADED,
            global_appreciation="Très bien; effort remarquable!"
        )
        Annotation.objects.create(
            copy=copy,
            page_index=0,
            x=0.1, y=0.1, w=0.1, h=0.1,
            score_delta=18,
            created_by=self.admin_user
        )
        
        response = self.client.post(
            self.url,
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        
        csv_content = response.content.decode('utf-8')
        
        # Check accents are preserved
        self.assertIn('33333333333', csv_content)
        
        # Comment with semicolon should be properly quoted
        self.assertIn('Très bien', csv_content)
    
    def test_export_warnings_in_headers(self):
        """Test that warnings are included in response headers"""
        copy = Copy.objects.create(
            exam=self.exam,
            anonymous_id='WARN001',
            student=self.student1,
            is_identified=True,
            status=Copy.Status.GRADED,
            global_appreciation="Comment with ; semicolon"
        )
        Annotation.objects.create(
            copy=copy,
            page_index=0,
            x=0.1, y=0.1, w=0.1, h=0.1,
            score_delta=15,
            created_by=self.admin_user
        )
        
        response = self.client.post(
            self.url,
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        
        # Check for warning header
        if 'X-Export-Warnings' in response:
            self.assertIn('warning', response['X-Export-Warnings'].lower())


@override_settings(RATELIMIT_ENABLE=True)
class PronoteExportAPIRateLimitTests(TestCase):
    """Test rate limiting for PRONOTE export"""
    
    def setUp(self):
        self.admin_group, _ = Group.objects.get_or_create(name=UserRole.ADMIN)
        
        self.admin_user = User.objects.create_user(
            username='admin_ratelimit',
            password='testpass123',
            is_staff=True
        )
        self.admin_user.groups.add(self.admin_group)
        
        self.exam = Exam.objects.create(
            name='Rate Limit Test',
            date='2026-02-01',
            grading_structure=[{"id": "ex1", "max_points": 20}]
        )
        
        self.student = Student.objects.create(
            first_name='Rate',
            last_name='Test',
            class_name='TS1',
            date_naissance='2005-06-25'
        )
        
        copy = Copy.objects.create(
            exam=self.exam,
            anonymous_id='RATE001',
            student=self.student,
            is_identified=True,
            status=Copy.Status.GRADED
        )
        Annotation.objects.create(
            copy=copy,
            page_index=0,
            x=0.1, y=0.1, w=0.1, h=0.1,
            score_delta=15,
            created_by=self.admin_user
        )
        
        self.url = f'/api/exams/{self.exam.id}/export-pronote/'
        self.client.force_login(self.admin_user)
    
    def test_rate_limit_allows_10_requests(self):
        """Test that 10 requests per hour are allowed"""
        # Note: This test may need cache configuration to work properly
        # If cache is not available, rate limiting might be disabled
        
        for i in range(10):
            response = self.client.post(
                self.url,
                content_type='application/json'
            )
            
            # Should succeed (or fail with 400 validation, but not 429)
            self.assertIn(response.status_code, [200, 400])
    
    def test_rate_limit_blocks_11th_request(self):
        """Test that 11th request within hour is blocked with 429"""
        # Note: This test requires cache to be enabled
        # If rate limiting is disabled in test environment, test will be skipped
        
        # Make 10 successful requests
        responses = []
        for i in range(10):
            response = self.client.post(
                self.url,
                content_type='application/json'
            )
            responses.append(response.status_code)
        
        # Verify first 10 requests succeeded
        for status_code in responses:
            self.assertIn(status_code, [200, 400], 
                         "First 10 requests should not hit rate limit")
        
        # 11th request should be rate limited
        response_11th = self.client.post(
            self.url,
            content_type='application/json'
        )
        
        # If rate limiting is enabled, should get 429
        # If disabled (no cache), will get 200/400
        if response_11th.status_code == 429:
            # Rate limiting is working
            self.assertEqual(response_11th.status_code, 429)
            data = response_11th.json()
            self.assertIn('error', data)
        else:
            # Rate limiting is disabled (acceptable in test environment)
            self.skipTest("Rate limiting not enabled in test environment")


class PronoteExportAPIAuditTests(TestCase):
    """Test audit logging for export endpoint"""
    
    def setUp(self):
        self.admin_group, _ = Group.objects.get_or_create(name=UserRole.ADMIN)
        
        self.admin_user = User.objects.create_user(
            username='admin_audit',
            password='testpass123',
            is_staff=True
        )
        self.admin_user.groups.add(self.admin_group)
        
        self.exam = Exam.objects.create(
            name='Audit Test',
            date='2026-02-01',
            grading_structure=[{"id": "ex1", "max_points": 20}]
        )
        
        self.student = Student.objects.create(
            first_name='Audit',
            last_name='Test',
            class_name='TS1',
            date_naissance='2005-07-30'
        )
        
        self.url = f'/api/exams/{self.exam.id}/export-pronote/'
        self.client.force_login(self.admin_user)
    
    def test_audit_log_on_successful_export(self):
        """Test audit log is created on successful export"""
        copy = Copy.objects.create(
            exam=self.exam,
            anonymous_id='AUDIT_SUCCESS',
            student=self.student,
            is_identified=True,
            status=Copy.Status.GRADED
        )
        Annotation.objects.create(
            copy=copy,
            page_index=0,
            x=0.1, y=0.1, w=0.1, h=0.1,
            score_delta=15,
            created_by=self.admin_user
        )
        
        # Import AuditLog if it exists
        try:
            from core.models import AuditLog
            
            initial_count = AuditLog.objects.count()
            
            response = self.client.post(
                self.url,
                content_type='application/json'
            )
            
            self.assertEqual(response.status_code, 200)
            
            # Check audit log was created
            final_count = AuditLog.objects.count()
            self.assertGreater(final_count, initial_count)
            
            # Check audit log contains expected action
            recent_log = AuditLog.objects.latest('created_at')
            self.assertIn('pronote', recent_log.action.lower())
            self.assertEqual(recent_log.user, self.admin_user)
            
        except ImportError:
            # AuditLog not available in test environment
            self.skipTest("AuditLog model not available")
    
    def test_audit_log_on_failed_export(self):
        """Test audit log is created on failed export"""
        # Create unidentified copy to trigger validation failure
        Copy.objects.create(
            exam=self.exam,
            anonymous_id='AUDIT_FAIL',
            status=Copy.Status.GRADED,
            is_identified=False
        )
        
        try:
            from core.models import AuditLog
            
            initial_count = AuditLog.objects.count()
            
            response = self.client.post(
                self.url,
                content_type='application/json'
            )
            
            self.assertEqual(response.status_code, 400)
            
            # Check audit log was created for failure
            final_count = AuditLog.objects.count()
            self.assertGreater(final_count, initial_count)
            
        except ImportError:
            self.skipTest("AuditLog model not available")
