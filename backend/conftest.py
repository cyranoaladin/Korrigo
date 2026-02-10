"""
Pytest configuration and fixtures for Korrigo backend tests.
ZF-AUD-14: Parallel test execution support with isolation.
"""
import pytest
import shutil
import tempfile
import os
from django.conf import settings
from django.contrib.auth.models import Group
from core.auth import UserRole


def pytest_configure(config):
    """
    ZF-AUD-14: Configure pytest for parallel execution.
    Sets up worker-specific environment variables.
    """
    # Get worker ID for xdist parallel execution
    worker_id = os.environ.get('PYTEST_XDIST_WORKER', 'master')
    
    # Set worker-specific temp directory
    if worker_id != 'master':
        os.environ['PYTEST_WORKER_ID'] = worker_id


def get_worker_id():
    """Get current pytest-xdist worker ID or 'master' if not parallel."""
    return os.environ.get('PYTEST_XDIST_WORKER', 'master')


@pytest.fixture(scope='session')
def worker_id():
    """Fixture providing the current worker ID for parallel tests."""
    return get_worker_id()


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
        password="testpass123",  # nosec B106 - Test fixture password, not used in production
        is_staff=True,
        is_superuser=True
    )
    g, _ = Group.objects.get_or_create(name=UserRole.ADMIN)
    user.groups.add(g)
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
        password="testpass123",  # nosec B106 - Test fixture password, not used in production
        is_staff=True,
        is_superuser=False
    )
    g, _ = Group.objects.get_or_create(name=UserRole.TEACHER)
    user.groups.add(g)
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
        password="testpass123",  # nosec B106 - Test fixture password, not used in production
        is_staff=False,
        is_superuser=False
    )
    return user


@pytest.fixture
def student_user(db):
    """
    Creates and returns a student user (non-staff, in student group).
    """
    from django.contrib.auth import get_user_model
    User = get_user_model()
    user = User.objects.create_user(
        username="student_test",
        password="testpass123",  # nosec B106 - Test fixture password, not used in production
        is_staff=False,
        is_superuser=False
    )
    g, _ = Group.objects.get_or_create(name=UserRole.STUDENT)
    user.groups.add(g)
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


@pytest.fixture(autouse=True)
def mock_media(settings):
    """
    Automatically override MEDIA_ROOT for all tests to use a temporary directory.
    ZF-AUD-14: Worker-isolated temp directory for parallel execution.
    Cleans up after tests finish.
    """
    # Create worker-specific temp directory for parallel isolation
    worker_id = get_worker_id()
    temp_media_root = tempfile.mkdtemp(prefix=f"korrigo_test_media_{worker_id}_")
    settings.MEDIA_ROOT = temp_media_root
    
    yield temp_media_root
    
    # Cleanup
    shutil.rmtree(temp_media_root, ignore_errors=True)


@pytest.fixture
def isolated_temp_dir():
    """
    ZF-AUD-14: Provides an isolated temporary directory for tests that need file I/O.
    Worker-specific to avoid conflicts in parallel execution.
    """
    worker_id = get_worker_id()
    temp_dir = tempfile.mkdtemp(prefix=f"korrigo_test_{worker_id}_")
    
    yield temp_dir
    
    shutil.rmtree(temp_dir, ignore_errors=True)
