from django.test import TransactionTestCase, Client
from django.utils import timezone
from rest_framework import status
from students.models import Student
from exams.models import Exam, Copy
from django.core.files.base import ContentFile
from datetime import date


class TestCrossStudentAccessPrevention(TransactionTestCase):
    
    def setUp(self):
        super().setUp()
        
        self.student_a = Student.objects.create(
            first_name="Alice",
            last_name="Martin",
            class_name="TG1",
            date_naissance=date(2005, 1, 15)
        )
        
        self.student_b = Student.objects.create(
            first_name="Bob",
            last_name="Durant",
            class_name="TG2",
            date_naissance=date(2005, 2, 20)
        )
        
        self.exam = Exam.objects.create(name="Security Test Exam", date="2026-01-15", results_released_at=timezone.now())
        
        self.copy_a_graded = Copy.objects.create(
            exam=self.exam,
            anonymous_id="COPY-A-GRADED",
            status=Copy.Status.GRADED,
            student=self.student_a,
            is_identified=True
        )
        self.copy_a_graded.final_pdf.save("a_graded.pdf", ContentFile(b"%PDF-1.4 A"), save=True)
        
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
        
        self.copy_b_graded = Copy.objects.create(
            exam=self.exam,
            anonymous_id="COPY-B-GRADED",
            status=Copy.Status.GRADED,
            student=self.student_b,
            is_identified=True
        )
        self.copy_b_graded.final_pdf.save("b_graded.pdf", ContentFile(b"%PDF-1.4 B"), save=True)
        
        self.client_a = Client()
        self.client_b = Client()
    
    def login_student_a(self):
        self.client_a.post("/api/students/login/", {
            "last_name": "Martin",
            "first_name": "Alice",
            "date_naissance": "2005-01-15"
        }, content_type="application/json")
    
    def login_student_b(self):
        self.client_b.post("/api/students/login/", {
            "last_name": "Durant",
            "first_name": "Bob",
            "date_naissance": "2005-02-20"
        }, content_type="application/json")
    
    def test_student_sees_only_own_graded_copies(self):
        self.login_student_a()
        
        resp = self.client_a.get("/api/students/copies/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        
        data = resp.json()
        copy_ids = [str(c['id']) for c in data]
        
        self.assertIn(str(self.copy_a_graded.id), copy_ids)
        self.assertNotIn(str(self.copy_b_graded.id), copy_ids)
    
    def test_student_does_not_see_ready_or_locked_copies(self):
        self.login_student_a()
        
        resp = self.client_a.get("/api/students/copies/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        
        data = resp.json()
        copy_ids = [str(c['id']) for c in data]
        
        self.assertIn(str(self.copy_a_graded.id), copy_ids)
        self.assertNotIn(str(self.copy_a_ready.id), copy_ids)
        self.assertNotIn(str(self.copy_a_locked.id), copy_ids)
    
    def test_student_cannot_access_other_student_pdf(self):
        self.login_student_a()
        
        resp = self.client_a.get(f"/api/grading/copies/{self.copy_b_graded.id}/final-pdf/")
        
        self.assertIn(resp.status_code, [status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND])
        if hasattr(resp, 'close'):
            resp.close()
    
    def test_student_can_access_own_graded_pdf(self):
        self.login_student_a()
        
        resp = self.client_a.get(f"/api/grading/copies/{self.copy_a_graded.id}/final-pdf/")
        
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp['Content-Type'], 'application/pdf')
        if hasattr(resp, 'close'):
            resp.close()
    
    def test_student_cannot_access_own_ready_copy_pdf(self):
        self.login_student_a()
        
        resp = self.client_a.get(f"/api/grading/copies/{self.copy_a_ready.id}/final-pdf/")
        
        self.assertIn(resp.status_code, [status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND])
        if hasattr(resp, 'close'):
            resp.close()
    
    def test_student_cannot_access_own_locked_copy_pdf(self):
        self.login_student_a()
        
        resp = self.client_a.get(f"/api/grading/copies/{self.copy_a_locked.id}/final-pdf/")
        
        self.assertIn(resp.status_code, [status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND])
        if hasattr(resp, 'close'):
            resp.close()
    
    def test_unauthenticated_student_cannot_access_copies(self):
        resp = self.client_a.get("/api/students/copies/")
        
        self.assertIn(resp.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])
    
    def test_unauthenticated_student_cannot_access_pdf(self):
        resp = self.client_a.get(f"/api/grading/copies/{self.copy_a_graded.id}/final-pdf/")
        
        self.assertIn(resp.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])
        if hasattr(resp, 'close'):
            resp.close()
    
    def test_complete_isolation_student_a_and_b(self):
        self.login_student_a()
        resp_a = self.client_a.get("/api/students/copies/")
        data_a = resp_a.json()
        
        self.login_student_b()
        resp_b = self.client_b.get("/api/students/copies/")
        data_b = resp_b.json()
        
        copy_ids_a = [str(c['id']) for c in data_a]
        copy_ids_b = [str(c['id']) for c in data_b]
        
        self.assertIn(str(self.copy_a_graded.id), copy_ids_a)
        self.assertNotIn(str(self.copy_b_graded.id), copy_ids_a)
        
        self.assertIn(str(self.copy_b_graded.id), copy_ids_b)
        self.assertNotIn(str(self.copy_a_graded.id), copy_ids_b)
        
        for copy_id in copy_ids_a:
            self.assertNotIn(copy_id, copy_ids_b)
    
    def tearDown(self):
        if self.copy_a_graded.final_pdf:
            self.copy_a_graded.final_pdf.delete()
        if self.copy_b_graded.final_pdf:
            self.copy_b_graded.final_pdf.delete()
        super().tearDown()
