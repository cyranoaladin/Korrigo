from django.test import TransactionTestCase, Client
from django.contrib.auth import get_user_model
from rest_framework import status
from exams.models import Exam, Copy
from students.models import Student
from django.core.files.base import ContentFile
from datetime import date

User = get_user_model()

# TransactionTestCase required because tests involve I/O, streaming, and multiple
# transactions that fail with regular TestCase in a Docker environment.
class TestGate4StudentFlow(TransactionTestCase):
    
    def setUp(self):
        super().setUp()
        
        # 1. Setup Student with User account
        self.student_user = User.objects.create_user(
            username="student_e2e",
            email="student@test.com",
            password="studentpass123"
        )
        self.student = Student.objects.create(
            last_name="E2E_STUDENT",
            first_name="Jean",
            date_naissance=date(2005, 3, 15),
            class_name="TS1"
        )
        
        # 2. Setup Exam & Copies (results must be released for student visibility)
        from django.utils import timezone
        self.exam = Exam.objects.create(
            name="Gate 4 Exam", date="2025-06-15",
            results_released_at=timezone.now()
        )
        
        self.copy_graded = Copy.objects.create(
            exam=self.exam,
            anonymous_id="GATE4-GRADED",
            status=Copy.Status.GRADED,
            student=self.student,
            is_identified=True
        )
        self.copy_graded.final_pdf.save("test.pdf", ContentFile(b"%PDF-1.4 Mock"), save=True)
        
        self.copy_locked = Copy.objects.create(
            exam=self.exam,
            anonymous_id="GATE4-LOCKED",
            status=Copy.Status.LOCKED, # Not Graded
            student=self.student,
            is_identified=True
        )
        
        # Other student's copy
        self.other_student = Student.objects.create(
            last_name="OTHER",
            first_name="Paul",
            date_naissance=date(2005, 6, 20),
            class_name="TS2"
        )
        self.copy_other = Copy.objects.create(
            exam=self.exam,
            anonymous_id="GATE4-OTHER",
            status=Copy.Status.GRADED,
            student=self.other_student,
            is_identified=True
        )
        self.copy_other.final_pdf.save("other.pdf", ContentFile(b"%PDF-1.4 Other"), save=True)

        # Client for session management
        self.client = Client()

    def test_student_login_success(self):
        resp = self.client.post("/api/students/login/", {
            "last_name": "E2E_STUDENT",
            "first_name": "Jean",
            "date_naissance": "2005-03-15"
        })
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(self.client.session['student_id'], self.student.id)
        
    def test_student_copies_list_permissions(self):
        # Login
        self.client.post("/api/students/login/", {
            "last_name": "E2E_STUDENT",
            "first_name": "Jean",
            "date_naissance": "2005-03-15"
        })
        
        # Get List
        resp = self.client.get("/api/students/copies/")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        
        # Should contain ONLY the GRADED owned copy
        ids = [str(c['id']) for c in data]
        self.assertIn(str(self.copy_graded.id), ids)
        self.assertNotIn(str(self.copy_locked.id), ids) # Locked not visible
        self.assertNotIn(str(self.copy_other.id), ids)  # Other not visible
        
    def test_student_pdf_access_security(self):
        # Login
        self.client.post("/api/students/login/", {
            "last_name": "E2E_STUDENT",
            "first_name": "Jean",
            "date_naissance": "2005-03-15"
        })
        
        # 1. Access Own Graded -> 200
        # Endpoint: /api/grading/copies/{id}/final-pdf/
        resp = self.client.get(f"/api/grading/copies/{self.copy_graded.id}/final-pdf/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp['Content-Type'], 'application/pdf')
        if hasattr(resp, 'close'): resp.close()
        
        # 2. Access Own Locked -> 403 (Not Graded) OR 404 (Filtered)
        # MUST use canonical URL to test security, not routing
        resp = self.client.get(f"/api/grading/copies/{self.copy_locked.id}/final-pdf/")
        # 403 Forbidden (Permission) OR 404 Not Found (QuerySet filtering) are both valid security outcomes
        self.assertIn(resp.status_code, [403, 404])
        if hasattr(resp, 'close'): resp.close()
        
        # 3. Access Other's Graded -> 403 OR 404
        # MUST use canonical URL to test security, not routing
        resp = self.client.get(f"/api/grading/copies/{self.copy_other.id}/final-pdf/")
        # 403 Forbidden (Permission) OR 404 Not Found (QuerySet filtering) are both valid security outcomes
        self.assertIn(resp.status_code, [403, 404])
        if hasattr(resp, 'close'): resp.close()
        
    def tearDown(self):
        # Cleanup files
        if self.copy_graded.final_pdf: self.copy_graded.final_pdf.delete()
        if self.copy_other.final_pdf: self.copy_other.final_pdf.delete()
        super().tearDown()
