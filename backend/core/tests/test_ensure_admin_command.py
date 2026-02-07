"""
Tests for ensure_admin management command.

Requires ALLOW_ENSURE_ADMIN=true and DJANGO_ENV != 'production'.
"""
import os
import pytest
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.core.management import call_command
from core.models import UserProfile

User = get_user_model()

# Patch environment for all tests in this module
_ENSURE_ADMIN_ENV = {
    'ALLOW_ENSURE_ADMIN': 'true',
    'DJANGO_ENV': 'test',
    'ADMIN_DEFAULT_PASSWORD': 'admin',
}


@pytest.mark.django_db
@patch.dict(os.environ, _ENSURE_ADMIN_ENV)
def test_ensure_admin_creates_admin_user():
    assert not User.objects.filter(username='admin').exists()

    call_command('ensure_admin')

    admin_user = User.objects.get(username='admin')
    assert admin_user.is_staff is True
    assert admin_user.is_superuser is True
    assert admin_user.check_password('admin') is True


@pytest.mark.django_db
@patch.dict(os.environ, _ENSURE_ADMIN_ENV)
def test_ensure_admin_sets_must_change_password():
    call_command('ensure_admin')

    admin_user = User.objects.get(username='admin')
    assert hasattr(admin_user, 'profile')
    assert admin_user.profile.must_change_password is True


@pytest.mark.django_db
@patch.dict(os.environ, _ENSURE_ADMIN_ENV)
def test_ensure_admin_idempotent():
    call_command('ensure_admin')
    admin1 = User.objects.get(username='admin')
    admin1_id = admin1.id

    call_command('ensure_admin')
    admin2 = User.objects.get(username='admin')

    assert admin1_id == admin2.id
    assert User.objects.filter(username='admin').count() == 1


@pytest.mark.django_db
@patch.dict(os.environ, _ENSURE_ADMIN_ENV)
def test_ensure_admin_with_existing_admin_without_profile():
    admin = User.objects.create_superuser(
        username='admin',
        email='admin@example.com',
        password='oldpass'
    )

    if hasattr(admin, 'profile'):
        admin.profile.delete()

    call_command('ensure_admin')

    admin.refresh_from_db()
    assert hasattr(admin, 'profile')
    assert admin.profile.must_change_password is True
