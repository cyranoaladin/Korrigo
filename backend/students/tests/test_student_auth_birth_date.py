from django.test import TransactionTestCase, Client
from rest_framework import status
from students.models import Student
from datetime import date, timedelta


class TestStudentAuthBirthDate(TransactionTestCase):
    
    def setUp(self):
        super().setUp()
        
        self.student = Student.objects.create(
            ine="1234567890A",
            first_name="Jean",
            last_name="Dupont",
            class_name="TG1",
            birth_date=date(2005, 3, 15)
        )
        
        self.client = Client()
    
    def test_login_with_valid_credentials(self):
        resp = self.client.post("/api/students/login/", {
            "ine": "1234567890A",
            "birth_date": "2005-03-15"
        }, content_type="application/json")
        
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn('message', resp.json())
        self.assertEqual(resp.json()['message'], 'Login successful')
        self.assertEqual(self.client.session['student_id'], self.student.id)
        self.assertEqual(self.client.session['role'], 'Student')
    
    def test_login_with_case_insensitive_ine(self):
        resp = self.client.post("/api/students/login/", {
            "ine": "1234567890a",
            "birth_date": "2005-03-15"
        }, content_type="application/json")
        
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(self.client.session['student_id'], self.student.id)
    
    def test_login_with_invalid_ine(self):
        resp = self.client.post("/api/students/login/", {
            "ine": "9999999999Z",
            "birth_date": "2005-03-15"
        }, content_type="application/json")
        
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertIn('error', resp.json())
        self.assertEqual(resp.json()['error'], 'Identifiants invalides.')
        self.assertNotIn('student_id', self.client.session)
    
    def test_login_with_invalid_birth_date(self):
        resp = self.client.post("/api/students/login/", {
            "ine": "1234567890A",
            "birth_date": "2005-03-16"
        }, content_type="application/json")
        
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertIn('error', resp.json())
        self.assertEqual(resp.json()['error'], 'Identifiants invalides.')
    
    def test_login_with_missing_ine(self):
        resp = self.client.post("/api/students/login/", {
            "birth_date": "2005-03-15"
        }, content_type="application/json")
        
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', resp.json())
        self.assertEqual(resp.json()['error'], 'Identifiants invalides.')
    
    def test_login_with_missing_birth_date(self):
        resp = self.client.post("/api/students/login/", {
            "ine": "1234567890A"
        }, content_type="application/json")
        
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', resp.json())
        self.assertEqual(resp.json()['error'], 'Identifiants invalides.')
    
    def test_login_with_invalid_date_format(self):
        resp = self.client.post("/api/students/login/", {
            "ine": "1234567890A",
            "birth_date": "15/03/2005"
        }, content_type="application/json")
        
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertIn('error', resp.json())
        self.assertEqual(resp.json()['error'], 'Identifiants invalides.')
    
    def test_login_with_future_birth_date(self):
        future_date = (date.today() + timedelta(days=1)).strftime('%Y-%m-%d')
        resp = self.client.post("/api/students/login/", {
            "ine": "1234567890A",
            "birth_date": future_date
        }, content_type="application/json")
        
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertIn('error', resp.json())
        self.assertEqual(resp.json()['error'], 'Identifiants invalides.')
    
    def test_login_with_too_old_birth_date(self):
        resp = self.client.post("/api/students/login/", {
            "ine": "1234567890A",
            "birth_date": "1989-12-31"
        }, content_type="application/json")
        
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertIn('error', resp.json())
        self.assertEqual(resp.json()['error'], 'Identifiants invalides.')
    
    def test_generic_error_messages_no_user_enumeration(self):
        invalid_ine_resp = self.client.post("/api/students/login/", {
            "ine": "9999999999Z",
            "birth_date": "2005-03-15"
        }, content_type="application/json")
        
        invalid_date_resp = self.client.post("/api/students/login/", {
            "ine": "1234567890A",
            "birth_date": "2005-03-16"
        }, content_type="application/json")
        
        self.assertEqual(invalid_ine_resp.json()['error'], invalid_date_resp.json()['error'])
        self.assertEqual(invalid_ine_resp.json()['error'], 'Identifiants invalides.')
