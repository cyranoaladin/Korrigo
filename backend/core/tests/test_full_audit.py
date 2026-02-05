import pytest
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from rest_framework import status
from core.models import GlobalSettings
from students.models import Student
import io

@pytest.mark.django_db
class TestFullSystemAudit:
    """
    Audit complet du système : Authentification, Settings, Import.
    """

    def setup_method(self):
        self.client = APIClient()
        # Create Admin
        self.admin_user = User.objects.create_superuser('admin', 'admin@example.com', 'adminpass')
        # Create Teacher
        self.teacher_user = User.objects.create_user('teacher', 'teacher@example.com', 'teacherpass')
        # Create Student with associated User for authentication
        self.student_user = User.objects.create_user('student_amine', 'amine@test.com', 'studentpass123')
        self.student = Student.objects.create(
            email="amine@test.com", 
            full_name="BENALI Amine", 
            date_of_birth="2008-01-15", 
            class_name="T1",
            user=self.student_user
        )

    def test_01_authentication_admin(self):
        """Vérifie le login/logout ADMIN et l'accès aux infos (ME)"""
        # Login
        response = self.client.post('/api/login/', {'username': 'admin', 'password': 'adminpass'})
        assert response.status_code == 200, "Admin Login Failed"
        
        # Access Protected Route
        response = self.client.get('/api/me/')
        assert response.status_code == 200
        assert response.data['username'] == 'admin'
        assert response.data['is_superuser'] is True

        # Global Settings Access (Write)
        response = self.client.post('/api/settings/', {'institutionName': 'Audit School'})
        assert response.status_code == 200

        # Logout
        response = self.client.post('/api/logout/')
        assert response.status_code == 200

    def test_02_authentication_teacher(self):
        """Vérifie le login Teacher et les restrictions d'accès"""
        response = self.client.post('/api/login/', {'username': 'teacher', 'password': 'teacherpass'})
        assert response.status_code == 200

        # Teacher should NOT be able to write restricted settings (if enforced)
        # Note: Current implementation allows 'IsAuthenticated', might want to strictly check 'IsAdminUser' for POST
        # But for now, audit current behavior.
        # Actually view says: "if not request.user.is_superuser... return 403"
        response = self.client.post('/api/settings/', {'institutionName': 'Hacked School'})
        assert response.status_code == 403, "Teacher should be forbidden from changing settings"

    def test_03_authentication_student(self):
        """Vérifie le login Élève via endpoint dédié"""
        response = self.client.post('/api/students/login/', {'email': 'amine@test.com', 'password': 'studentpass123'})
        assert response.status_code == 200, f"Student Login Failed: {response.data}"
        
        # Access Student Me
        # Note: session auth might need passing session cookie, failing that check if client handles it
        response = self.client.get('/api/students/me/')
        if response.status_code == 403:
             # If 403, it means IsStudent failed. We fixed IsStudent to check session.
             pass
        assert response.status_code == 200
        assert response.data['email'] == 'amine@test.com'

    def test_04_global_settings_persistence(self):
        """Vérifie que les settings sont bien sauvegardés en DB"""
        self.client.force_authenticate(user=self.admin_user)
        
        payload = {
            "institutionName": "Lycée Audit",
            "theme": "dark",
            "defaultDuration": 90,
            "notifications": False
        }
        res = self.client.post('/api/settings/', payload, format='json')
        assert res.status_code == 200
        
        # Reload from DB
        settings = GlobalSettings.load()
        assert settings.institution_name == "Lycée Audit"
        assert settings.theme == "dark"
        assert settings.default_exam_duration == 90
        assert settings.notifications_enabled is False

    def test_05_student_import_csv(self):
        """Vérifie l'import de fichier CSV (async avec CELERY_TASK_ALWAYS_EAGER)"""
        self.client.force_authenticate(user=self.admin_user)
        
        # CSV format: Élèves (FULL_NAME), Né(e) le (DATE_NAISSANCE), Adresse E-mail (EMAIL)
        csv_content = b"\xc3\x89l\xc3\xa8ves,N\xc3\xa9(e) le,Adresse E-mail,Classe\nTEST User,15/01/2008,test@test.com,T1"
        file = io.BytesIO(csv_content)
        file.name = "import.csv"
        
        response = self.client.post('/api/students/import/', {'file': file}, format='multipart')
        
        # Phase 3: Import is now async, returns 202 with task_id
        assert response.status_code == 202, f"Expected 202 Accepted, got {response.status_code}: {response.data}"
        assert 'task_id' in response.data
        
        # With CELERY_TASK_ALWAYS_EAGER=True, task runs synchronously
        # Check task status endpoint for result
        task_id = response.data['task_id']
        status_response = self.client.get(f'/api/tasks/{task_id}/status/')
        assert status_response.status_code == 200
        assert status_response.data['ready'] is True
        assert status_response.data['result']['created'] == 1
        
        # Verify student exists
        assert Student.objects.filter(email="test@test.com").exists()

    def test_06_change_password(self):
        """Vérifie le changement de mot de passe"""
        self.client.force_authenticate(user=self.teacher_user)
        
        new_pass = "NewPassword123!"
        res = self.client.post('/api/change-password/', {
            'current_password': 'teacherpass',
            'new_password': new_pass
        })
        assert res.status_code == 200, f"Change password failed: {res.data}"
        
        # Logout and try login with new pass
        self.client.logout()
        res = self.client.post('/api/login/', {'username': 'teacher', 'password': new_pass})
        assert res.status_code == 200
