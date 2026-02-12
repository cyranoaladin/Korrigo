from django.test import TransactionTestCase, Client
from django.contrib.auth.models import User, Group
from rest_framework import status
from students.models import Student
from core.auth import UserRole
from datetime import date


class TestStudentAuthEmailPassword(TransactionTestCase):
    """Tests for student login via email + password."""
    
    def setUp(self):
        super().setUp()
        
        # Create Django User for the student
        self.user = User.objects.create_user(
            username='jean.dupont-e@ert.tn',
            email='jean.dupont-e@ert.tn',
            password='passe123',
            first_name='Jean',
            last_name='Dupont',
        )
        student_group, _ = Group.objects.get_or_create(name=UserRole.STUDENT)
        self.user.groups.add(student_group)
        
        self.student = Student.objects.create(
            first_name="Jean",
            last_name="Dupont",
            class_name="TG1",
            date_naissance=date(2005, 3, 15),
            email="jean.dupont-e@ert.tn",
            user=self.user,
        )
        
        self.client = Client()
    
    def test_login_with_valid_credentials(self):
        resp = self.client.post("/api/students/login/", {
            "email": "jean.dupont-e@ert.tn",
            "password": "passe123"
        }, content_type="application/json")
        
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn('message', resp.json())
        self.assertEqual(resp.json()['message'], 'Login successful')
        self.assertEqual(self.client.session['student_id'], self.student.id)
        self.assertEqual(self.client.session['role'], 'Student')
    
    def test_login_returns_must_change_password_for_default(self):
        resp = self.client.post("/api/students/login/", {
            "email": "jean.dupont-e@ert.tn",
            "password": "passe123"
        }, content_type="application/json")
        
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertTrue(resp.json()['must_change_password'])
    
    def test_login_returns_student_info(self):
        resp = self.client.post("/api/students/login/", {
            "email": "jean.dupont-e@ert.tn",
            "password": "passe123"
        }, content_type="application/json")
        
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        student_data = resp.json()['student']
        self.assertEqual(student_data['first_name'], 'Jean')
        self.assertEqual(student_data['last_name'], 'Dupont')
        self.assertEqual(student_data['email'], 'jean.dupont-e@ert.tn')
    
    def test_login_with_wrong_password(self):
        resp = self.client.post("/api/students/login/", {
            "email": "jean.dupont-e@ert.tn",
            "password": "wrongpassword"
        }, content_type="application/json")
        
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertIn('error', resp.json())
    
    def test_login_with_unknown_email(self):
        resp = self.client.post("/api/students/login/", {
            "email": "inconnu@ert.tn",
            "password": "passe123"
        }, content_type="application/json")
        
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertIn('error', resp.json())
    
    def test_login_with_missing_email(self):
        resp = self.client.post("/api/students/login/", {
            "password": "passe123"
        }, content_type="application/json")
        
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_login_with_missing_password(self):
        resp = self.client.post("/api/students/login/", {
            "email": "jean.dupont-e@ert.tn"
        }, content_type="application/json")
        
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_login_case_insensitive_email(self):
        resp = self.client.post("/api/students/login/", {
            "email": "Jean.Dupont-e@ERT.TN",
            "password": "passe123"
        }, content_type="application/json")
        
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
    
    def test_generic_error_messages_no_user_enumeration(self):
        wrong_email_resp = self.client.post("/api/students/login/", {
            "email": "inconnu@ert.tn",
            "password": "passe123"
        }, content_type="application/json")
        
        wrong_pass_resp = self.client.post("/api/students/login/", {
            "email": "jean.dupont-e@ert.tn",
            "password": "wrongpassword"
        }, content_type="application/json")
        
        self.assertEqual(wrong_email_resp.json()['error'], wrong_pass_resp.json()['error'])
        self.assertEqual(wrong_email_resp.json()['error'], 'Email ou mot de passe incorrect.')
    
    def test_user_without_student_profile_rejected(self):
        orphan_user = User.objects.create_user(
            username='orphan@ert.tn',
            email='orphan@ert.tn',
            password='passe123',
        )
        student_group, _ = Group.objects.get_or_create(name=UserRole.STUDENT)
        orphan_user.groups.add(student_group)
        
        resp = self.client.post("/api/students/login/", {
            "email": "orphan@ert.tn",
            "password": "passe123"
        }, content_type="application/json")
        
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertIn('profil', resp.json()['error'].lower())
    
    def test_must_change_password_false_after_change(self):
        self.user.set_password('MonNouveauMdp2026!')
        self.user.save()
        
        resp = self.client.post("/api/students/login/", {
            "email": "jean.dupont-e@ert.tn",
            "password": "MonNouveauMdp2026!"
        }, content_type="application/json")
        
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertFalse(resp.json()['must_change_password'])
