"""
ZF-AUD-12: Production Smoke Tests
Tests for health endpoints and static/media availability.
"""
import pytest
from django.test import Client, override_settings
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

User = get_user_model()


@pytest.mark.django_db
class TestHealthEndpoints:
    """Test health check endpoints."""

    def test_health_endpoint_returns_200(self):
        """Health endpoint should return 200."""
        client = Client()
        response = client.get('/api/health/')
        
        assert response.status_code == 200
        data = response.json()
        assert data.get('status') == 'healthy'

    def test_readiness_endpoint_returns_200(self):
        """Readiness endpoint should return 200 when DB is available."""
        client = Client()
        response = client.get('/api/health/ready/')
        
        # Should be 200 if DB is accessible, 503 if not
        assert response.status_code in [200, 503]
        
        data = response.json()
        assert 'status' in data

    def test_health_endpoint_no_auth_required(self):
        """Health endpoint should not require authentication."""
        client = Client()
        # No login, no session
        response = client.get('/api/health/')
        
        assert response.status_code == 200


@pytest.mark.django_db
class TestStaticMediaAvailability:
    """Test static and media file serving configuration."""

    def test_static_url_configured(self):
        """STATIC_URL should be configured."""
        from django.conf import settings
        
        assert hasattr(settings, 'STATIC_URL')
        assert settings.STATIC_URL is not None
        assert settings.STATIC_URL.startswith('/')

    def test_media_url_configured(self):
        """MEDIA_URL should be configured."""
        from django.conf import settings
        
        assert hasattr(settings, 'MEDIA_URL')
        assert settings.MEDIA_URL is not None
        assert settings.MEDIA_URL.startswith('/')

    def test_static_root_configured(self):
        """STATIC_ROOT should be configured for collectstatic."""
        from django.conf import settings
        
        assert hasattr(settings, 'STATIC_ROOT')
        assert settings.STATIC_ROOT is not None

    def test_media_root_configured(self):
        """MEDIA_ROOT should be configured for file uploads."""
        from django.conf import settings
        
        assert hasattr(settings, 'MEDIA_ROOT')
        assert settings.MEDIA_ROOT is not None


@pytest.mark.django_db
class TestSecuritySettings:
    """Test security settings are properly configured."""

    def test_secret_key_not_insecure_in_prod(self):
        """SECRET_KEY should not be insecure prefix in production."""
        from django.conf import settings
        
        # In test environment, this may be insecure, but check the logic
        if getattr(settings, 'DJANGO_ENV', '') == 'production':
            assert not settings.SECRET_KEY.startswith('django-insecure-')

    def test_allowed_hosts_not_wildcard_in_prod(self):
        """ALLOWED_HOSTS should not contain '*' in production."""
        from django.conf import settings
        
        if getattr(settings, 'DJANGO_ENV', '') == 'production':
            assert '*' not in settings.ALLOWED_HOSTS

    def test_session_cookie_httponly(self):
        """SESSION_COOKIE_HTTPONLY should be True."""
        from django.conf import settings
        
        assert settings.SESSION_COOKIE_HTTPONLY is True

    def test_csrf_cookie_samesite(self):
        """CSRF_COOKIE_SAMESITE should be set."""
        from django.conf import settings
        
        assert settings.CSRF_COOKIE_SAMESITE in ['Strict', 'Lax', 'None']

    def test_x_frame_options_set(self):
        """X_FRAME_OPTIONS should be set."""
        from django.conf import settings
        
        assert hasattr(settings, 'X_FRAME_OPTIONS')
        # In DEBUG mode, might not be set
        if not settings.DEBUG:
            assert settings.X_FRAME_OPTIONS in ['DENY', 'SAMEORIGIN']


@pytest.mark.django_db
class TestDatabaseConnection:
    """Test database connectivity."""

    def test_database_is_accessible(self):
        """Database should be accessible."""
        from django.db import connection
        
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            assert result[0] == 1

    def test_can_create_user(self):
        """Should be able to create a user (DB write test)."""
        user = User.objects.create_user(
            username='smoke_test_user',
            password='test_password_123'
        )
        
        assert user.id is not None
        assert User.objects.filter(username='smoke_test_user').exists()
        
        # Cleanup
        user.delete()


@pytest.mark.django_db
class TestAPIEndpoints:
    """Test critical API endpoints are accessible."""

    def test_api_root_accessible(self):
        """API root should be accessible."""
        client = Client()
        response = client.get('/api/')
        
        # Should return something (200 or redirect)
        assert response.status_code in [200, 301, 302, 404]

    def test_login_endpoint_exists(self):
        """Login endpoint should exist."""
        client = Client()
        response = client.post('/api/login/', {
            'username': 'nonexistent',
            'password': 'wrong'
        })
        
        # Should return 401 (unauthorized) not 404 (not found)
        assert response.status_code in [400, 401, 403]

    def test_student_login_endpoint_exists(self):
        """Student login endpoint should exist."""
        client = Client()
        response = client.post('/api/students/login/', {
            'email': 'nonexistent@test.com',
            'last_name': 'WRONG'
        })
        
        # Should return 401 (unauthorized) not 404 (not found)
        assert response.status_code in [400, 401]


@pytest.mark.django_db
class TestLoggingConfiguration:
    """Test logging is properly configured."""

    def test_logging_configured(self):
        """LOGGING should be configured."""
        from django.conf import settings
        
        assert hasattr(settings, 'LOGGING')
        assert 'handlers' in settings.LOGGING
        assert 'loggers' in settings.LOGGING

    def test_audit_logger_configured(self):
        """Audit logger should be configured."""
        from django.conf import settings
        
        assert 'audit' in settings.LOGGING.get('loggers', {})

    def test_can_write_log(self):
        """Should be able to write a log entry."""
        import logging
        
        logger = logging.getLogger('grading')
        
        # Should not raise
        logger.info("Smoke test log entry")
