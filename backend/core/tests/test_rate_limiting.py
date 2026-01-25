"""
Tests pour le rate limiting
Conformité: Phase 1 - Corrections Critiques Sécurité
"""
import pytest
from django.test import Client
from django.contrib.auth.models import User
from django.urls import reverse


@pytest.mark.django_db
class TestRateLimiting:
    """Tests du rate limiting sur endpoints login"""

    def test_login_rate_limit_under_threshold(self):
        """Test que 5 tentatives sont autorisées"""
        client = Client()
        User.objects.create_user(username='testuser', password='correctpass')
        
        # 5 tentatives avec mauvais mot de passe
        for i in range(5):
            response = client.post('/api/login/', {
                'username': 'testuser',
                'password': 'wrongpass'
            })
            # Devrait retourner 401 (unauthorized) mais pas 429 (rate limited)
            assert response.status_code == 401

    def test_student_login_rate_limit_under_threshold(self):
        """Test que 5 tentatives élève sont autorisées"""
        client = Client()
        
        # 5 tentatives avec mauvais identifiants
        for i in range(5):
            response = client.post('/api/students/login/', {
                'ine': 'WRONGINE',
                'last_name': 'WRONGNAME'
            })
            # Devrait retourner 401 mais pas 429
            assert response.status_code == 401

    @pytest.mark.skip(reason="Rate limiting nécessite Redis en test, skip pour CI/CD")
    def test_login_rate_limit_exceeded(self):
        """Test que la 6ème tentative est bloquée (HTTP 429)"""
        client = Client()
        User.objects.create_user(username='testuser', password='correctpass')
        
        # 6 tentatives avec mauvais mot de passe
        for i in range(6):
            response = client.post('/api/login/', {
                'username': 'testuser',
                'password': 'wrongpass'
            })
            
            if i < 5:
                assert response.status_code == 401
            else:
                # 6ème tentative devrait être rate limited
                assert response.status_code == 429

    @pytest.mark.skip(reason="Rate limiting nécessite Redis en test, skip pour CI/CD")
    def test_student_login_rate_limit_exceeded(self):
        """Test que la 6ème tentative élève est bloquée (HTTP 429)"""
        client = Client()
        
        # 6 tentatives avec mauvais identifiants
        for i in range(6):
            response = client.post('/api/students/login/', {
                'ine': 'WRONGINE',
                'last_name': 'WRONGNAME'
            })
            
            if i < 5:
                assert response.status_code == 401
            else:
                # 6ème tentative devrait être rate limited
                assert response.status_code == 429

    def test_successful_login_not_rate_limited(self):
        """Test qu'un login réussi n'est pas rate limited"""
        client = Client()
        User.objects.create_user(username='testuser', password='correctpass')
        
        # Login réussi
        response = client.post('/api/login/', {
            'username': 'testuser',
            'password': 'correctpass'
        })
        
        assert response.status_code == 200
        assert response.json()['message'] == 'Login successful'
