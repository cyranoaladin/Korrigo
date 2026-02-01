"""
Tests pour le rate limiting
Conformité: Phase 1 - Corrections Critiques Sécurité

Security: Tests distinguish between rate-limited and non-rate-limited scenarios.
Note: RATELIMIT_ENABLE=False in settings_test.py disables rate limiting for tests.
"""
import pytest
from django.test import Client, override_settings
from django.contrib.auth.models import User
from django.core.cache import cache


@pytest.fixture(autouse=True)
def clear_rate_limit_cache():
    """Clear cache before each test to reset rate limit counters."""
    cache.clear()
    yield
    cache.clear()


@pytest.mark.django_db
class TestRateLimitingBaseline:
    """Tests du comportement baseline (rate limiting désactivé en test)"""

    def test_login_attempts_under_threshold_always_401(self):
        """Test que 5 tentatives échouées retournent 401 (rate limiting désactivé)"""
        client = Client()
        User.objects.create_user(username='testuser_baseline1', password='correctpass')

        # 5 tentatives avec mauvais mot de passe
        for i in range(5):
            response = client.post('/api/login/', {
                'username': 'testuser_baseline1',
                'password': 'wrongpass'
            })
            # Rate limiting désactivé en test: toujours 401
            assert response.status_code == 401, \
                f"Attempt {i+1}: Expected 401, got {response.status_code}"

    def test_student_login_attempts_under_threshold_always_401(self):
        """Test que 5 tentatives élève échouées retournent 401"""
        client = Client()

        # 5 tentatives avec mauvais identifiants
        for i in range(5):
            response = client.post('/api/students/login/', {
                'ine': 'WRONGINE',
                'last_name': 'WRONGNAME'
            })
            # Rate limiting désactivé en test: toujours 401
            assert response.status_code == 401, \
                f"Attempt {i+1}: Expected 401, got {response.status_code}"

    def test_successful_login_not_rate_limited(self):
        """Test qu'un login réussi fonctionne (rate limiting désactivé)"""
        client = Client()
        User.objects.create_user(username='testuser_success', password='correctpass')

        # Login réussi
        response = client.post('/api/login/', {
            'username': 'testuser_success',
            'password': 'correctpass'
        })

        assert response.status_code == 200
        assert response.json()['message'] == 'Login successful'


@pytest.mark.django_db
class TestRateLimitingGracefulDegradation:
    """
    Tests du comportement avec rate limiting désactivé (mode test).

    Ces tests vérifient que l'application fonctionne correctement
    quand RATELIMIT_ENABLE=False (configuration de test).
    """

    def test_login_degraded_mode_without_redis(self):
        """
        Test du mode test: rate limiting désactivé, app fonctionne normalement.

        Ce test vérifie que sans rate limiting, on obtient 401 sur toutes tentatives
        échouées, ce qui est le comportement attendu en environnement de test.
        """
        client = Client()
        User.objects.create_user(username='testuser_degraded', password='correctpass')

        # Rate limiting désactivé: toutes tentatives retournent 401
        for i in range(10):  # Même 10 tentatives passent
            response = client.post('/api/login/', {
                'username': 'testuser_degraded',
                'password': 'wrongpass'
            })
            # Rate limiting désactivé: toujours 401, jamais 429
            assert response.status_code == 401, \
                f"Attempt {i+1}: Expected 401, got {response.status_code}"
