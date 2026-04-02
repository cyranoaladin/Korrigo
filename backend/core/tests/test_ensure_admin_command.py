"""
Tests for ensure_admin management command.

The command reads ADMIN_USERNAME, ADMIN_PASSWORD, ADMIN_EMAIL from env vars
with fallback defaults.  Tests isolate from the host environment so they
remain deterministic regardless of production env vars being set.
"""
import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command
from core.models import UserProfile

User = get_user_model()


@pytest.fixture(autouse=True)
def _clean_admin_env(monkeypatch):
    """Remove any host env vars that the ensure_admin command reads."""
    monkeypatch.delenv('ADMIN_USERNAME', raising=False)
    monkeypatch.delenv('ADMIN_PASSWORD', raising=False)
    monkeypatch.delenv('ADMIN_EMAIL', raising=False)


@pytest.mark.django_db
def test_ensure_admin_creates_admin_user():
    assert not User.objects.filter(username='admin').exists()

    call_command('ensure_admin')

    admin_user = User.objects.get(username='admin')
    assert admin_user.is_staff is True
    assert admin_user.is_superuser is True
    # Default password when ADMIN_PASSWORD env var is not set
    assert admin_user.check_password('admin') is True


@pytest.mark.django_db
def test_ensure_admin_sets_must_change_password():
    call_command('ensure_admin')
    
    admin_user = User.objects.get(username='admin')
    assert hasattr(admin_user, 'profile')
    assert admin_user.profile.must_change_password is True


@pytest.mark.django_db
def test_ensure_admin_idempotent():
    call_command('ensure_admin')
    admin1 = User.objects.get(username='admin')
    admin1_id = admin1.id
    
    call_command('ensure_admin')
    admin2 = User.objects.get(username='admin')
    
    assert admin1_id == admin2.id
    assert User.objects.filter(username='admin').count() == 1


@pytest.mark.django_db
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


@pytest.mark.django_db
def test_ensure_admin_respects_env_password(monkeypatch):
    """When ADMIN_PASSWORD is set via env, the command must use that password."""
    monkeypatch.setenv('ADMIN_PASSWORD', 'custom-secret-42')

    call_command('ensure_admin')

    admin_user = User.objects.get(username='admin')
    assert admin_user.check_password('custom-secret-42') is True
    assert admin_user.check_password('admin') is False
