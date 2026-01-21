"""
Pytest configuration and fixtures for Viatique backend tests.
"""
import pytest


@pytest.fixture
def api_client():
    """
    Provides a DRF APIClient instance for making API requests in tests.
    """
    from rest_framework.test import APIClient
    return APIClient()


@pytest.fixture
def admin_user(db):
    """
    Creates and returns an admin user (superuser + staff).
    """
    from django.contrib.auth import get_user_model
    User = get_user_model()
    user = User.objects.create_user(
        username="admin_test",
        password="testpass123",
        is_staff=True,
        is_superuser=True
    )
    return user


@pytest.fixture
def teacher_user(db):
    """
    Creates and returns a teacher user (staff but not superuser).
    """
    from django.contrib.auth import get_user_model
    User = get_user_model()
    user = User.objects.create_user(
        username="teacher_test",
        password="testpass123",
        is_staff=True,
        is_superuser=False
    )
    return user


@pytest.fixture
def regular_user(db):
    """
    Creates and returns a regular non-staff user.
    """
    from django.contrib.auth import get_user_model
    User = get_user_model()
    user = User.objects.create_user(
        username="user_test",
        password="testpass123",
        is_staff=False,
        is_superuser=False
    )
    return user


@pytest.fixture
def authenticated_client(api_client, admin_user):
    """
    Returns an APIClient authenticated as admin user.
    """
    api_client.force_authenticate(user=admin_user)
    return api_client


@pytest.fixture
def teacher_client(api_client, teacher_user):
    """
    Returns an APIClient authenticated as teacher user.
    """
    api_client.force_authenticate(user=teacher_user)
    return api_client
