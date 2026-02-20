"""
Tests for PDF Download Security Gates.

Tests verify that CopyFinalPdfView enforces:
1. Status gate: Only GRADED copies accessible
2. Authentication gate: Requires teacher/admin OR student session
3. Authorization gate: Students can only access their OWN copies
4. Security headers: Cache-Control, Content-Disposition, etc.

Conformité: docs/security/MANUEL_SECURITE.md — Accès PDF Final
Référence: Portail Élève Security Audit
"""
from django.test import TransactionTestCase, Client
from django.contrib.auth.models import User, Group
from rest_framework import status
from students.models import Student
from exams.models import Exam, Copy
from django.core.files.base import ContentFile
from core.auth import UserRole
from datetime import date


class TestPDFDownloadSecurity(TransactionTestCase):
    """
    Test PDF download security gates for CopyFinalPdfView.
    
    Covers status validation, authentication, authorization, and security headers.
    """
    
    def setUp(self):
        super().setUp()
        
        # Create student group and Django Users
        student_group, _ = Group.objects.get_or_create(name=UserRole.STUDENT)
        
        self.user_a = User.objects.create_user(
            username='alice.martin-e@ert.tn',
            email='alice.martin-e@ert.tn',
            password='passe123',
        )
        self.user_a.groups.add(student_group)
        
        self.student_a = Student.objects.create(
            first_name="Alice",
            last_name="Martin",
            class_name="TG1",
            date_naissance=date(2005, 1, 15),
            email="alice.martin-e@ert.tn",
            user=self.user_a,
        )
        
        self.user_b = User.objects.create_user(
            username='bob.durant-e@ert.tn',
            email='bob.durant-e@ert.tn',
            password='passe123',
        )
        self.user_b.groups.add(student_group)
        
        self.student_b = Student.objects.create(
            first_name="Bob",
            last_name="Durant",
            class_name="TG2",
            date_naissance=date(2005, 2, 20),
            email="bob.durant-e@ert.tn",
            user=self.user_b,
        )
        
        # Create teacher user
        self.teacher = User.objects.create_user(
            username="teacher1",
            password="password123",
            is_staff=True
        )
        teacher_group, _ = Group.objects.get_or_create(name=UserRole.TEACHER)
        self.teacher.groups.add(teacher_group)
        
        # Create admin user
        self.admin = User.objects.create_user(
            username="admin1",
            password="password123",
            is_superuser=True,
            is_staff=True
        )
        
        # Create exam
        self.exam = Exam.objects.create(
            name="PDF Security Test Exam",
            date=date(2026, 1, 15)
        )
        
        # Create copies for Student A with different statuses
        self.copy_a_graded = Copy.objects.create(
            exam=self.exam,
            anonymous_id="COPY-A-GRADED",
            status=Copy.Status.GRADED,
            student=self.student_a,
            is_identified=True
        )
        # Create actual PDF content
        self.copy_a_graded.final_pdf.save(
            "a_graded.pdf",
            ContentFile(b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n>>\nendobj\n%%EOF"),
            save=True
        )
        
        self.copy_a_ready = Copy.objects.create(
            exam=self.exam,
            anonymous_id="COPY-A-READY",
            status=Copy.Status.READY,
            student=self.student_a,
            is_identified=True
        )
        
        self.copy_a_locked = Copy.objects.create(
            exam=self.exam,
            anonymous_id="COPY-A-LOCKED",
            status=Copy.Status.LOCKED,
            student=self.student_a,
            is_identified=True
        )
        
        # Create GRADED copy for Student B
        self.copy_b_graded = Copy.objects.create(
            exam=self.exam,
            anonymous_id="COPY-B-GRADED",
            status=Copy.Status.GRADED,
            student=self.student_b,
            is_identified=True
        )
        self.copy_b_graded.final_pdf.save(
            "b_graded.pdf",
            ContentFile(b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n>>\nendobj\n%%EOF"),
            save=True
        )
        
        # Create GRADED copy without PDF file (for 404 test)
        self.copy_no_pdf = Copy.objects.create(
            exam=self.exam,
            anonymous_id="COPY-NO-PDF",
            status=Copy.Status.GRADED,
            student=self.student_a,
            is_identified=True
        )
        
        # Initialize clients
        self.client_student_a = Client()
        self.client_student_b = Client()
        self.client_teacher = Client()
        self.client_admin = Client()
        self.client_anonymous = Client()
    
    def login_student_a(self):
        """Authenticate student A via email+password login."""
        self.client_student_a.post(
            "/api/students/login/",
            {"email": "alice.martin-e@ert.tn", "password": "passe123"},
            content_type="application/json"
        )
    
    def login_student_b(self):
        """Authenticate student B via email+password login."""
        self.client_student_b.post(
            "/api/students/login/",
            {"email": "bob.durant-e@ert.tn", "password": "passe123"},
            content_type="application/json"
        )
    
    def login_teacher(self):
        """Authenticate teacher via Django auth."""
        self.client_teacher.login(username="teacher1", password="password123")
    
    def login_admin(self):
        """Authenticate admin via Django auth."""
        self.client_admin.login(username="admin1", password="password123")
    
    # ========================================================================
    # Test Case 1: Student downloads own GRADED copy (SUCCESS)
    # ========================================================================
    
    def test_student_downloads_own_graded_copy_success(self):
        """
        GIVEN: Student A authenticated with valid session
        AND: Copy A is GRADED with final_pdf
        WHEN: Student A requests PDF download
        THEN: Return 200 OK with PDF content
        AND: Content-Type is application/pdf
        """
        self.login_student_a()
        
        resp = self.client_student_a.get(
            f"/api/grading/copies/{self.copy_a_graded.id}/final-pdf/"
        )
        
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp['Content-Type'], 'application/pdf')
        self.assertIn('Content-Disposition', resp)
        
        if hasattr(resp, 'close'):
            resp.close()
    
    # ========================================================================
    # Test Case 2: Student tries to download another student's copy (FORBIDDEN)
    # ========================================================================
    
    def test_student_cannot_download_other_student_copy(self):
        """
        GIVEN: Student A authenticated
        AND: Copy B belongs to Student B (GRADED)
        WHEN: Student A requests Copy B PDF
        THEN: Return 403 FORBIDDEN
        """
        self.login_student_a()
        
        resp = self.client_student_a.get(
            f"/api/grading/copies/{self.copy_b_graded.id}/final-pdf/"
        )
        
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)
        
        if hasattr(resp, 'close'):
            resp.close()
    
    # ========================================================================
    # Test Case 3: Student tries to download own READY copy (FORBIDDEN)
    # ========================================================================
    
    def test_student_cannot_download_own_ready_copy(self):
        """
        GIVEN: Student A authenticated
        AND: Copy A is READY (not yet graded)
        WHEN: Student A requests PDF
        THEN: Return 403 FORBIDDEN (status gate blocks)
        """
        self.login_student_a()
        
        resp = self.client_student_a.get(
            f"/api/grading/copies/{self.copy_a_ready.id}/final-pdf/"
        )
        
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn('GRADED', str(resp.data.get('detail', '')))
        
        if hasattr(resp, 'close'):
            resp.close()
    
    # ========================================================================
    # Test Case 4: Student tries to download own LOCKED copy (FORBIDDEN)
    # ========================================================================
    
    def test_student_cannot_download_own_locked_copy(self):
        """
        GIVEN: Student A authenticated
        AND: Copy A is LOCKED (grading in progress)
        WHEN: Student A requests PDF
        THEN: Return 403 FORBIDDEN (status gate blocks)
        """
        self.login_student_a()
        
        resp = self.client_student_a.get(
            f"/api/grading/copies/{self.copy_a_locked.id}/final-pdf/"
        )
        
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn('GRADED', str(resp.data.get('detail', '')))
        
        if hasattr(resp, 'close'):
            resp.close()
    
    # ========================================================================
    # Test Case 5: Unauthenticated request (UNAUTHORIZED)
    # ========================================================================
    
    def test_unauthenticated_request_returns_401(self):
        """
        GIVEN: No authentication (no session, no Django user)
        WHEN: Anonymous user requests PDF
        THEN: Return 401 UNAUTHORIZED
        """
        resp = self.client_anonymous.get(
            f"/api/grading/copies/{self.copy_a_graded.id}/final-pdf/"
        )
        
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)
        
        if hasattr(resp, 'close'):
            resp.close()
    
    # ========================================================================
    # Test Case 6: Verify security headers on successful download
    # ========================================================================
    
    def test_pdf_download_includes_security_headers(self):
        """
        GIVEN: Student A authenticated and downloads PDF
        WHEN: Request is successful
        THEN: Response includes security headers:
            - Cache-Control: private, no-store, no-cache, must-revalidate, max-age=0
            - Pragma: no-cache
            - Expires: 0
            - X-Content-Type-Options: nosniff
            - Content-Disposition: attachment
        """
        self.login_student_a()
        
        resp = self.client_student_a.get(
            f"/api/grading/copies/{self.copy_a_graded.id}/final-pdf/"
        )
        
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        
        # Verify Cache-Control header
        cache_control = resp.get('Cache-Control', '')
        self.assertIn('no-store', cache_control)
        self.assertIn('no-cache', cache_control)
        self.assertIn('must-revalidate', cache_control)
        self.assertIn('max-age=0', cache_control)
        
        # Verify Pragma header
        self.assertEqual(resp.get('Pragma', ''), 'no-cache')
        
        # Verify Expires header
        self.assertEqual(resp.get('Expires', ''), '0')
        
        # Verify X-Content-Type-Options header
        self.assertEqual(resp.get('X-Content-Type-Options', ''), 'nosniff')
        
        # Verify Content-Disposition header (inline by default, attachment with ?download=1)
        content_disposition = resp.get('Content-Disposition', '')
        self.assertIn('inline', content_disposition)
        self.assertIn(f'copy_{self.copy_a_graded.anonymous_id}_corrected.pdf', content_disposition)
        
        if hasattr(resp, 'close'):
            resp.close()
    
    # ========================================================================
    # Test Case 7: Teacher can download any GRADED copy
    # ========================================================================
    
    def test_teacher_can_download_any_graded_copy(self):
        """
        GIVEN: Teacher authenticated (is_staff + Teachers group)
        WHEN: Teacher requests any student's GRADED copy
        THEN: Return 200 OK (authorization gate allows teachers)
        """
        self.login_teacher()
        
        # Teacher downloads Student A's copy
        resp_a = self.client_teacher.get(
            f"/api/grading/copies/{self.copy_a_graded.id}/final-pdf/"
        )
        self.assertEqual(resp_a.status_code, status.HTTP_200_OK)
        if hasattr(resp_a, 'close'):
            resp_a.close()
        
        # Teacher downloads Student B's copy
        resp_b = self.client_teacher.get(
            f"/api/grading/copies/{self.copy_b_graded.id}/final-pdf/"
        )
        self.assertEqual(resp_b.status_code, status.HTTP_200_OK)
        if hasattr(resp_b, 'close'):
            resp_b.close()
    
    # ========================================================================
    # Test Case 8: Admin can download any GRADED copy
    # ========================================================================
    
    def test_admin_can_download_any_graded_copy(self):
        """
        GIVEN: Admin authenticated (is_superuser)
        WHEN: Admin requests any student's GRADED copy
        THEN: Return 200 OK (authorization gate allows admins)
        """
        self.login_admin()
        
        resp = self.client_admin.get(
            f"/api/grading/copies/{self.copy_a_graded.id}/final-pdf/"
        )
        
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        
        if hasattr(resp, 'close'):
            resp.close()
    
    # ========================================================================
    # Test Case 9: Teacher cannot download non-GRADED copy
    # ========================================================================
    
    def test_teacher_cannot_download_non_graded_copy(self):
        """
        GIVEN: Teacher authenticated
        AND: Copy is READY (not GRADED)
        WHEN: Teacher requests PDF
        THEN: Return 403 FORBIDDEN (status gate blocks even for teachers)
        """
        self.login_teacher()
        
        resp = self.client_teacher.get(
            f"/api/grading/copies/{self.copy_a_ready.id}/final-pdf/"
        )
        
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)
        
        if hasattr(resp, 'close'):
            resp.close()
    
    # ========================================================================
    # Test Case 10: Request for copy without PDF file returns 404
    # ========================================================================
    
    def test_copy_without_pdf_file_returns_404(self):
        """
        GIVEN: Copy is GRADED but has no final_pdf file
        WHEN: User requests PDF
        THEN: Return 404 NOT FOUND
        """
        self.login_student_a()
        
        resp = self.client_student_a.get(
            f"/api/grading/copies/{self.copy_no_pdf.id}/final-pdf/"
        )
        
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)
        
        if hasattr(resp, 'close'):
            resp.close()
    
    # ========================================================================
    # Test Case 11: Cross-student validation with both students
    # ========================================================================
    
    def test_complete_isolation_between_students(self):
        """
        GIVEN: Student A and Student B both authenticated
        WHEN: Each tries to download the other's GRADED copy
        THEN: Both receive 403 FORBIDDEN
        AND: Each can download their own copy successfully
        """
        self.login_student_a()
        self.login_student_b()
        
        # Student A cannot access Student B's copy
        resp_a_tries_b = self.client_student_a.get(
            f"/api/grading/copies/{self.copy_b_graded.id}/final-pdf/"
        )
        self.assertEqual(resp_a_tries_b.status_code, status.HTTP_403_FORBIDDEN)
        if hasattr(resp_a_tries_b, 'close'):
            resp_a_tries_b.close()
        
        # Student B cannot access Student A's copy
        resp_b_tries_a = self.client_student_b.get(
            f"/api/grading/copies/{self.copy_a_graded.id}/final-pdf/"
        )
        self.assertEqual(resp_b_tries_a.status_code, status.HTTP_403_FORBIDDEN)
        if hasattr(resp_b_tries_a, 'close'):
            resp_b_tries_a.close()
        
        # Student A CAN access own copy
        resp_a_own = self.client_student_a.get(
            f"/api/grading/copies/{self.copy_a_graded.id}/final-pdf/"
        )
        self.assertEqual(resp_a_own.status_code, status.HTTP_200_OK)
        if hasattr(resp_a_own, 'close'):
            resp_a_own.close()
        
        # Student B CAN access own copy
        resp_b_own = self.client_student_b.get(
            f"/api/grading/copies/{self.copy_b_graded.id}/final-pdf/"
        )
        self.assertEqual(resp_b_own.status_code, status.HTTP_200_OK)
        if hasattr(resp_b_own, 'close'):
            resp_b_own.close()
    
    # ========================================================================
    # Cleanup
    # ========================================================================
    
    def tearDown(self):
        """Clean up file resources."""
        if self.copy_a_graded.final_pdf:
            self.copy_a_graded.final_pdf.delete()
        if self.copy_b_graded.final_pdf:
            self.copy_b_graded.final_pdf.delete()
        super().tearDown()
