"""
Tests for UserProfile model and must_change_password functionality
"""
import pytest
from django.contrib.auth import get_user_model
from core.models import UserProfile

User = get_user_model()


@pytest.mark.django_db
def test_user_profile_created_automatically():
    user = User.objects.create_user(username='testuser', password='testpass123')
    assert hasattr(user, 'profile')
    assert isinstance(user.profile, UserProfile)
    assert user.profile.must_change_password is False


@pytest.mark.django_db
def test_must_change_password_default():
    user = User.objects.create_user(username='testuser2', password='testpass123')
    profile = user.profile
    assert profile.must_change_password is False


@pytest.mark.django_db
def test_set_must_change_password():
    user = User.objects.create_user(username='testuser3', password='testpass123')
    profile = user.profile
    profile.must_change_password = True
    profile.save()
    
    user.refresh_from_db()
    assert user.profile.must_change_password is True


@pytest.mark.django_db
def test_login_returns_must_change_password(api_client):
    from rest_framework.test import APIClient
    
    user = User.objects.create_user(username='testuser4', password='testpass123')
    user.profile.must_change_password = True
    user.profile.save()
    
    client = APIClient()
    response = client.post('/api/login/', {
        'username': 'testuser4',
        'password': 'testpass123'
    }, format='json')
    
    assert response.status_code == 200
    assert 'must_change_password' in response.data
    assert response.data['must_change_password'] is True


@pytest.mark.django_db
def test_login_returns_false_when_not_set(api_client):
    from rest_framework.test import APIClient
    
    user = User.objects.create_user(username='testuser5', password='testpass123')
    
    client = APIClient()
    response = client.post('/api/login/', {
        'username': 'testuser5',
        'password': 'testpass123'
    }, format='json')
    
    assert response.status_code == 200
    assert 'must_change_password' in response.data
    assert response.data['must_change_password'] is False


@pytest.mark.django_db
def test_user_detail_includes_must_change_password(api_client):
    from rest_framework.test import APIClient
    
    user = User.objects.create_user(
        username='testuser6',
        password='testpass123',
        is_staff=True,
        is_superuser=True
    )
    user.profile.must_change_password = True
    user.profile.save()
    
    client = APIClient()
    client.force_authenticate(user=user)
    
    response = client.get('/api/me/')
    assert response.status_code == 200
    assert 'must_change_password' in response.data
    assert response.data['must_change_password'] is True


@pytest.mark.django_db
def test_change_password_clears_must_change_flag(api_client):
    from rest_framework.test import APIClient
    
    user = User.objects.create_user(
        username='testuser7',
        password='testpass123',
        is_staff=True
    )
    user.profile.must_change_password = True
    user.profile.save()
    
    client = APIClient()
    client.force_authenticate(user=user)
    
    response = client.post('/api/change-password/', {
        'password': 'newpassword123'
    }, format='json')
    
    assert response.status_code == 200
    user.refresh_from_db()
    assert user.profile.must_change_password is False
