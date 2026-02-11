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
        # Create Student
        self.student = Student.objects.create(
            date_naissance="2005-03-15",
            last_name="BEN ALI",
            first_name="Amine",
            class_name="TG1"
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
        response = self.client.post('/api/students/login/', {
            'first_name': 'Amine',
            'last_name': 'BEN ALI',
            'date_naissance': '2005-03-15'
        })
        assert response.status_code == 200, "Student Login Failed"
        
        # Access Student Me
        # Note: session auth might need passing session cookie, failing that check if client handles it
        response = self.client.get('/api/students/me/')
        if response.status_code == 403:
             # If 403, it means IsStudent failed. We fixed IsStudent to check session.
             pass
        assert response.status_code == 200
        assert response.data['first_name'] == 'Amine'
        assert response.data['last_name'] == 'BEN ALI'

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
        """Vérifie l'import de fichier CSV"""
        self.client.force_authenticate(user=self.admin_user)
        
        csv_content = b"\xc3\x89l\xc3\xa8ves,N\xc3\xa9(e) le,Email,Classe,Groupe\nTEST User,15/05/2005,test@test.com,TG3,G1"
        file = io.BytesIO(csv_content)
        file.name = "import.csv"
        
        response = self.client.post('/api/students/import/', {'file': file}, format='multipart')
        assert response.status_code == 200
        assert response.data['created'] == 1
        
        # Verify student exists (importer splits "TEST User" → last_name=TEST, first_name=User)
        assert Student.objects.filter(
            first_name="User",
            last_name="TEST",
            date_naissance="2005-05-15"
        ).exists()

    def test_06_change_password(self):
        """Vérifie le changement de mot de passe"""
        self.client.force_authenticate(user=self.teacher_user)
        
        new_pass = "newpassword123"
        res = self.client.post('/api/change-password/', {'password': new_pass})
        assert res.status_code == 200
        
        # Logout and try login with new pass
        self.client.logout()
        res = self.client.post('/api/login/', {'username': 'teacher', 'password': new_pass})
        assert res.status_code == 200
