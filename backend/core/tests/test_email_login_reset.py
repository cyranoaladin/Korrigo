"""
Tests for email-based login and password reset functionality
"""
from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from core.models import UserProfile


class EmailLoginTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    def test_login_with_username_works(self):
        response = self.client.post('/api/login/', {
            'username': 'testuser',
            'password': 'testpass123'
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['message'], 'Connexion réussie.')
    
    def test_login_with_email_works(self):
        response = self.client.post('/api/login/', {
            'username': 'test@example.com',
            'password': 'testpass123'
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['message'], 'Connexion réussie.')
    
    def test_login_with_wrong_email_fails(self):
        response = self.client.post('/api/login/', {
            'username': 'wrong@example.com',
            'password': 'testpass123'
        })
        self.assertEqual(response.status_code, 401)


class PasswordResetTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_user(
            username='admin',
            email='admin@example.com',
            password='adminpass',
            is_staff=True,
            is_superuser=True
        )
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.client.force_authenticate(user=self.admin)
    
    def test_admin_can_reset_user_password(self):
        response = self.client.post(f'/api/users/{self.user.id}/reset-password/')
        self.assertEqual(response.status_code, 200)
        self.assertIn('temporary_password', response.data)
        self.assertEqual(len(response.data['temporary_password']), 12)
    
    def test_reset_sets_must_change_password_flag(self):
        response = self.client.post(f'/api/users/{self.user.id}/reset-password/')
        self.assertEqual(response.status_code, 200)
        
        self.user.refresh_from_db()
        profile = UserProfile.objects.get(user=self.user)
        self.assertTrue(profile.must_change_password)
    
    def test_non_admin_cannot_reset_password(self):
        regular_user = User.objects.create_user(
            username='regular',
            email='regular@example.com',
            password='regularpass'
        )
        self.client.force_authenticate(user=regular_user)
        
        response = self.client.post(f'/api/users/{self.user.id}/reset-password/')
        self.assertEqual(response.status_code, 403)
    
    def test_admin_cannot_reset_own_password(self):
        response = self.client.post(f'/api/users/{self.admin.id}/reset-password/')
        self.assertEqual(response.status_code, 400)


class EmailUniquenessTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_user(
            username='admin',
            email='admin@example.com',
            password='adminpass',
            is_staff=True,
            is_superuser=True
        )
        self.client.force_authenticate(user=self.admin)
        User.objects.create_user(
            username='existing',
            email='existing@example.com',
            password='pass123'
        )
    
    def test_duplicate_email_rejected(self):
        response = self.client.post('/api/users/', {
            'username': 'newuser',
            'email': 'existing@example.com',
            'password': 'newpass123',
            'role': 'Teacher'
        })
        self.assertEqual(response.status_code, 400)
        self.assertIn('Adresse email déjà utilisée.', response.data['error'])
    
    def test_unique_email_accepted(self):
        response = self.client.post('/api/users/', {
            'username': 'newuser',
            'email': 'new@example.com',
            'password': 'newpass123',
            'role': 'Teacher'
        })
        self.assertEqual(response.status_code, 201)
    
    def test_duplicate_email_rejected_on_update(self):
        user1 = User.objects.create_user(
            username='user1',
            email='user1@example.com',
            password='pass123'
        )
        user2 = User.objects.create_user(
            username='user2',
            email='user2@example.com',
            password='pass123'
        )
        
        response = self.client.put(f'/api/users/{user2.id}/', {
            'email': 'user1@example.com'
        })
        self.assertEqual(response.status_code, 400)
        self.assertIn('Adresse email déjà utilisée.', response.data['error'])
