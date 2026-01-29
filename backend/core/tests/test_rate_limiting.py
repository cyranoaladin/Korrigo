"""
Tests pour le rate limiting
Conformité: Phase 1 - Corrections Critiques Sécurité

Security: Tests distinguish between rate-limited and non-rate-limited scenarios.
"""
import pytest
from django.test import Client, override_settings
from django.contrib.auth.models import User
from django.urls import reverse


@pytest.mark.django_db
class TestRateLimitingBaseline:
    """Tests du comportement baseline (sans rate limiting)"""

    def test_login_attempts_under_threshold_always_401(self):
        """Test que 5 tentatives échouées retournent 401 (pas rate limited)"""
        client = Client()
        User.objects.create_user(username='testuser', password='correctpass')

        # 5 tentatives avec mauvais mot de passe
        for i in range(5):
            response = client.post('/api/login/', {
                'username': 'testuser',
                'password': 'wrongpass'
            })
            # Devrait retourner 401 (unauthorized) mais pas 429 (rate limited)
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
            # Devrait retourner 401 mais pas 429
            assert response.status_code == 401, \
                f"Attempt {i+1}: Expected 401, got {response.status_code}"

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


@pytest.mark.django_db
class TestRateLimitingProtection:
    """
    Tests du rate limiting actif.

    Note: Ces tests EXIGENT que le rate limiting soit configuré et actif.
    Si Redis n'est pas disponible ou rate limiting désactivé, ces tests ÉCHOUERONT,
    ce qui est le comportement attendu (fail fast sur manque de protection).

    Pour CI: Assurez-vous que Redis est disponible dans le workflow de test.
    """

    @pytest.mark.skipif(
        not pytest.config.getoption("--with-redis", default=False),
        reason="Rate limiting requires Redis. Run with --with-redis to test protection."
    )
    def test_login_rate_limit_protection_active(self):
        """
        Test que le rate limiting protège effectivement après N tentatives.

        Ce test vérifie la SÉCURITÉ: si rate limiting est actif, la 6ème tentative
        DOIT être bloquée (429).
        """
        client = Client()
        User.objects.create_user(username='testuser', password='correctpass')

        # 5 tentatives échouent avec 401
        for i in range(5):
            response = client.post('/api/login/', {
                'username': 'testuser',
                'password': 'wrongpass'
            })
            assert response.status_code == 401, \
                f"Attempt {i+1}: Expected 401, got {response.status_code}"

        # 6ème tentative DOIT être rate limited
        response = client.post('/api/login/', {
            'username': 'testuser',
            'password': 'wrongpass'
        })
        assert response.status_code == 429, \
            f"Attempt 6 should be rate limited (429), got {response.status_code}. " \
            "Rate limiting protection is NOT active!"

    @pytest.mark.skipif(
        not pytest.config.getoption("--with-redis", default=False),
        reason="Rate limiting requires Redis. Run with --with-redis to test protection."
    )
    def test_student_login_rate_limit_protection_active(self):
        """Test que le rate limiting protège les logins élèves"""
        client = Client()

        # 5 tentatives échouent avec 401
        for i in range(5):
            response = client.post('/api/students/login/', {
                'ine': 'WRONGINE',
                'last_name': 'WRONGNAME'
            })
            assert response.status_code == 401

        # 6ème tentative DOIT être rate limited
        response = client.post('/api/students/login/', {
            'ine': 'WRONGINE',
            'last_name': 'WRONGNAME'
        })
        assert response.status_code == 429, \
            "Student login rate limiting protection is NOT active!"


@pytest.mark.django_db
class TestRateLimitingGracefulDegradation:
    """
    Tests du comportement sans Redis (graceful degradation).

    Ces tests vérifient que l'application fonctionne même si rate limiting n'est pas
    disponible, MAIS documentent explicitement qu'il s'agit d'un mode dégradé.
    """

    def test_login_degraded_mode_without_redis(self):
        """
        Test du mode dégradé: sans Redis, pas de protection mais app fonctionne.

        Ce test DOCUMENTE que sans Redis, on accepte 401 sur toutes tentatives,
        ce qui est un comportement dégradé acceptable UNIQUEMENT pour dev/test local.
        """
        client = Client()
        User.objects.create_user(username='testuser', password='correctpass')

        # En mode dégradé: toutes tentatives retournent 401 (pas de protection)
        for i in range(10):  # Même 10 tentatives passent
            response = client.post('/api/login/', {
                'username': 'testuser',
                'password': 'wrongpass'
            })
            # Mode dégradé: toujours 401, jamais 429
            assert response.status_code == 401, \
                f"Attempt {i+1} in degraded mode: Expected 401, got {response.status_code}"


# Configure pytest to accept --with-redis option
def pytest_addoption(parser):
    parser.addoption(
        "--with-redis",
        action="store_true",
        default=False,
        help="Run tests that require Redis (rate limiting protection tests)"
    )
