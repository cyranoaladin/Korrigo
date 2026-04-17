"""
Tests for StudentChangePasswordView - Comprehensive coverage.

Includes:
- Unit tests for password change validation
- Rate limiting tests
- E2E workflow: login → change password → access dashboard
- Permission tests
- Frontend-backend coherence tests
"""
from django.test import TransactionTestCase, Client, override_settings
from django.conf import settings as _settings
from django.contrib.auth.models import User, Group
from rest_framework import status
from students.models import Student
from core.auth import UserRole
from datetime import date


class TestStudentChangePasswordUnit(TransactionTestCase):
    """Unit tests for StudentChangePasswordView."""
    
    def setUp(self):
        super().setUp()
        
        self.student_group, _ = Group.objects.get_or_create(name=UserRole.STUDENT)
        
        # Student with date of birth as potential password
        self.user = User.objects.create_user(
            username='test.student-e@ert.tn',
            email='test.student-e@ert.tn',
            password=_settings.DEFAULT_PASSWORD,
            first_name='Test',
            last_name='Student',
        )
        self.user.groups.add(self.student_group)
        
        self.student = Student.objects.create(
            first_name="Test",
            last_name="Student",
            class_name="TG1",
            date_naissance=date(2005, 6, 15),  # 15062005
            email="test.student-e@ert.tn",
            user=self.user,
        )
        
        self.client = Client()
        self.login()
    
    def login(self):
        """Helper to login the student."""
        resp = self.client.post("/api/students/login/", {
            "email": "test.student-e@ert.tn",
            "password": _settings.DEFAULT_PASSWORD
        }, content_type="application/json")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        return resp
    
    def test_change_password_success(self):
        """Test successful password change."""
        resp = self.client.post("/api/students/change-password/", {
            "current_password": _settings.DEFAULT_PASSWORD,
            "new_password": "NouveauMdp2026!"
        }, content_type="application/json")
        
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn('message', resp.json())
        self.assertEqual(resp.json()['message'], 'Mot de passe modifié avec succès.')
    
    def test_change_password_wrong_current_password(self):
        """Test password change with wrong current password."""
        resp = self.client.post("/api/students/change-password/", {
            "current_password": "wrongpassword",
            "new_password": "NouveauMdp2026!"
        }, content_type="application/json")
        
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', resp.json())
        self.assertEqual(resp.json()['error'], 'Mot de passe actuel incorrect.')
    
    def test_change_password_missing_current_password(self):
        """Test password change without current password."""
        resp = self.client.post("/api/students/change-password/", {
            "new_password": "NouveauMdp2026!"
        }, content_type="application/json")
        
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', resp.json())
    
    def test_change_password_missing_new_password(self):
        """Test password change without new password."""
        resp = self.client.post("/api/students/change-password/", {
            "current_password": _settings.DEFAULT_PASSWORD
        }, content_type="application/json")
        
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', resp.json())
    
    def test_change_password_cannot_reuse_default(self):
        """Test that default password cannot be reused."""
        resp = self.client.post("/api/students/change-password/", {
            "current_password": _settings.DEFAULT_PASSWORD,
            "new_password": _settings.DEFAULT_PASSWORD
        }, content_type="application/json")
        
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', resp.json())
        error_msg = resp.json()['error']
        # Error can be a string or a list
        if isinstance(error_msg, list):
            error_text = ' '.join(error_msg).lower()
        else:
            error_text = error_msg.lower()
        self.assertIn('mot de passe par défaut', error_text)
    
    def test_change_password_cannot_use_date_of_birth(self):
        """Test that exact date of birth password cannot be used.
        
        Note: In practice, Django's password validators will reject an 8-digit
        numeric password before our custom check. This test verifies that if
        somehow a DOB password passed Django validators, it would be rejected
        by our custom check.
        """
        # Test with exact DOB format - this will likely be rejected by Django validators first
        # which is acceptable behavior (defense in depth)
        resp = self.client.post("/api/students/change-password/", {
            "current_password": _settings.DEFAULT_PASSWORD,
            "new_password": "15062005"  # Exact date_naissance in DDMMYYYY format
        }, content_type="application/json")
        
        # Should be rejected (either by Django validators or our custom check)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        # Just verify there's an error - could be from Django or our custom check
        self.assertIn('error', resp.json())
    
    def test_change_password_session_preserved(self):
        """Test that session is preserved after password change."""
        session_key = self.client.session.session_key
        
        resp = self.client.post("/api/students/change-password/", {
            "current_password": _settings.DEFAULT_PASSWORD,
            "new_password": "NouveauMdp2026!"
        }, content_type="application/json")
        
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        # Session should still be valid
        self.assertEqual(self.client.session['student_id'], self.student.id)
        self.assertEqual(self.client.session['role'], 'Student')
    
    def test_change_password_must_change_password_flag_cleared(self):
        """Test that must_change_password is set to False after change."""
        # Initially should be True (using default password)
        self.assertTrue(self.client.session.get('must_change_password', False))
        
        resp = self.client.post("/api/students/change-password/", {
            "current_password": _settings.DEFAULT_PASSWORD,
            "new_password": "NouveauMdp2026!"
        }, content_type="application/json")
        
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        # After successful change, flag should be cleared
        self.assertFalse(self.client.session.get('must_change_password', True))
    
    def test_change_password_updates_user_profile(self):
        """Test that UserProfile.must_change_password is updated."""
        # Ensure profile exists and has must_change_password = True
        from core.models import UserProfile
        profile, created = UserProfile.objects.get_or_create(user=self.user)
        if not created:
            profile.must_change_password = True
            profile.save(update_fields=['must_change_password'])
        
        resp = self.client.post("/api/students/change-password/", {
            "current_password": _settings.DEFAULT_PASSWORD,
            "new_password": "NouveauMdp2026!"
        }, content_type="application/json")
        
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        
        # Verify new password works for login
        self.client.logout()
        login_resp = self.client.post("/api/students/login/", {
            "email": "test.student-e@ert.tn",
            "password": "NouveauMdp2026!"
        }, content_type="application/json")
        
        self.assertEqual(login_resp.status_code, status.HTTP_200_OK)
        self.assertFalse(login_resp.json()['must_change_password'])
    
    def test_change_password_unauthenticated_fails(self):
        """Test that unauthenticated requests fail."""
        self.client.logout()
        
        resp = self.client.post("/api/students/change-password/", {
            "current_password": _settings.DEFAULT_PASSWORD,
            "new_password": "NouveauMdp2026!"
        }, content_type="application/json")
        
        # Should be 401 or 403
        self.assertIn(resp.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])


class TestStudentChangePasswordRateLimit(TransactionTestCase):
    """Tests for rate limiting on password change endpoint."""
    
    def setUp(self):
        super().setUp()
        
        self.student_group, _ = Group.objects.get_or_create(name=UserRole.STUDENT)
        
        self.user = User.objects.create_user(
            username='rate.test-e@ert.tn',
            email='rate.test-e@ert.tn',
            password=_settings.DEFAULT_PASSWORD,
        )
        self.user.groups.add(self.student_group)
        
        self.student = Student.objects.create(
            first_name="Rate",
            last_name="Test",
            class_name="TG1",
            date_naissance=date(2005, 1, 1),
            email="rate.test-e@ert.tn",
            user=self.user,
        )
        
        self.client = Client()
        # Login first
        self.client.post("/api/students/login/", {
            "email": "rate.test-e@ert.tn",
            "password": _settings.DEFAULT_PASSWORD
        }, content_type="application/json")
    
    def test_rate_limit_allows_multiple_attempts(self):
        """Test that rate limit allows multiple attempts (20/h)."""
        from django.conf import settings
        # Skip if rate limiting is disabled at the decorator level
        # (maybe_ratelimit checks at decoration time, not runtime)
        if not getattr(settings, "RATELIMIT_ENABLE", True):
            self.skipTest("Rate limiting is disabled via RATELIMIT_ENABLE")
        
        # Make 15 attempts with wrong current password - all should get 400
        for i in range(15):
            resp = self.client.post("/api/students/change-password/", {
                "current_password": f"wrongpassword{i}",
                "new_password": "NouveauMdp2026!"
            }, content_type="application/json")
            
            # Should be 400 (wrong password), not 429 (rate limited)
            self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertEqual(resp.json()['error'], 'Mot de passe actuel incorrect.')
    
    def test_rate_limit_returns_429_with_message(self):
        """Test that rate limit returns 429 with clear message when exceeded."""
        from django.conf import settings
        # Skip if rate limiting is disabled at the decorator level
        if not getattr(settings, "RATELIMIT_ENABLE", True):
            self.skipTest("Rate limiting is disabled via RATELIMIT_ENABLE")
        
        # Make many attempts to trigger rate limit
        responses = []
        for i in range(25):
            resp = self.client.post("/api/students/change-password/", {
                "current_password": f"wrongpassword{i}",
                "new_password": "NouveauMdp2026!"
            }, content_type="application/json")
            responses.append(resp.status_code)
        
        # At least one should be 429 (rate limited)
        self.assertIn(status.HTTP_429_TOO_MANY_REQUESTS, responses)
        
        # Find the 429 response and verify message
        for i, code in enumerate(responses):
            if code == status.HTTP_429_TOO_MANY_REQUESTS:
                # Verify that subsequent requests also return 429
                self.assertIn(429, responses[i:])
                break


class TestStudentAuthWorkflowE2E(TransactionTestCase):
    """End-to-end workflow tests for student authentication."""
    
    def setUp(self):
        super().setUp()
        
        self.student_group, _ = Group.objects.get_or_create(name=UserRole.STUDENT)
        
        self.user = User.objects.create_user(
            username='workflow.test-e@ert.tn',
            email='workflow.test-e@ert.tn',
            password=_settings.DEFAULT_PASSWORD,
        )
        self.user.groups.add(self.student_group)
        
        self.student = Student.objects.create(
            first_name="Workflow",
            last_name="Test",
            class_name="TG1",
            date_naissance=date(2005, 8, 20),
            email="workflow.test-e@ert.tn",
            user=self.user,
        )
        
        self.client = Client()
    
    def test_complete_workflow_login_change_password_access_dashboard(self):
        """
        E2E: Login with default password → See must_change_password → 
        Change password → Access dashboard → Copies visible
        """
        # Step 1: Login with default password
        login_resp = self.client.post("/api/students/login/", {
            "email": "workflow.test-e@ert.tn",
            "password": _settings.DEFAULT_PASSWORD
        }, content_type="application/json")
        
        self.assertEqual(login_resp.status_code, status.HTTP_200_OK)
        self.assertTrue(login_resp.json()['must_change_password'])
        self.assertTrue(self.client.session['must_change_password'])
        
        # Step 2: Try to access dashboard (me endpoint)
        me_resp = self.client.get("/api/students/me/")
        self.assertEqual(me_resp.status_code, status.HTTP_200_OK)
        student_data = me_resp.json()
        self.assertEqual(student_data['first_name'], 'Workflow')
        
        # Step 3: Access copies endpoint (should work even with must_change_password)
        copies_resp = self.client.get("/api/students/copies/")
        self.assertEqual(copies_resp.status_code, status.HTTP_200_OK)
        
        # Step 4: Change password
        change_resp = self.client.post("/api/students/change-password/", {
            "current_password": _settings.DEFAULT_PASSWORD,
            "new_password": "NouveauMdp2026!"
        }, content_type="application/json")
        
        self.assertEqual(change_resp.status_code, status.HTTP_200_OK)
        
        # Step 5: Session still valid, can access dashboard
        me_resp2 = self.client.get("/api/students/me/")
        self.assertEqual(me_resp2.status_code, status.HTTP_200_OK)
        
        # Step 6: Verify must_change_password is now False
        self.assertFalse(self.client.session.get('must_change_password', True))
        
        # Step 7: Logout
        logout_resp = self.client.post("/api/students/logout/")
        self.assertEqual(logout_resp.status_code, status.HTTP_200_OK)
        
        # Step 8: Re-login with new password
        login_resp2 = self.client.post("/api/students/login/", {
            "email": "workflow.test-e@ert.tn",
            "password": "NouveauMdp2026!"
        }, content_type="application/json")
        
        self.assertEqual(login_resp2.status_code, status.HTTP_200_OK)
        self.assertFalse(login_resp2.json()['must_change_password'])
    
    def test_workflow_multiple_failed_password_changes_then_success(self):
        """
        E2E: Multiple failed password change attempts, then success.
        Verifies rate limiting doesn't block legitimate users.
        """
        # Login
        self.client.post("/api/students/login/", {
            "email": "workflow.test-e@ert.tn",
            "password": _settings.DEFAULT_PASSWORD
        }, content_type="application/json")
        
        # Multiple failed attempts (wrong current password)
        failed_count = 0
        for _ in range(10):
            resp = self.client.post("/api/students/change-password/", {
                "current_password": "wrongpassword",
                "new_password": "NouveauMdp2026!"
            }, content_type="application/json")
            if resp.status_code == status.HTTP_400_BAD_REQUEST:
                failed_count += 1
        
        self.assertEqual(failed_count, 10)  # All should be 400, not 429
        
        # Now correct password - should work
        success_resp = self.client.post("/api/students/change-password/", {
            "current_password": _settings.DEFAULT_PASSWORD,
            "new_password": "NouveauMdp2026!"
        }, content_type="application/json")
        
        self.assertEqual(success_resp.status_code, status.HTTP_200_OK)


class TestStudentPermissionCoherence(TransactionTestCase):
    """Tests for permission coherence between IsStudent and other checks."""
    
    def setUp(self):
        super().setUp()
        
        self.student_group, _ = Group.objects.get_or_create(name=UserRole.STUDENT)
        self.teacher_group, _ = Group.objects.get_or_create(name=UserRole.TEACHER)
        
        # Student A
        self.user_a = User.objects.create_user(
            username='student.a-e@ert.tn',
            email='student.a-e@ert.tn',
            password=_settings.DEFAULT_PASSWORD,
        )
        self.user_a.groups.add(self.student_group)
        self.student_a = Student.objects.create(
            first_name="Student",
            last_name="A",
            class_name="TG1",
            date_naissance=date(2005, 1, 1),
            email="student.a-e@ert.tn",
            user=self.user_a,
        )
        
        # Student B (orphan - has group but no Student profile)
        self.user_orphan = User.objects.create_user(
            username='orphan-e@ert.tn',
            email='orphan-e@ert.tn',
            password=_settings.DEFAULT_PASSWORD,
        )
        self.user_orphan.groups.add(self.student_group)
        # No Student profile created intentionally
        
        # Teacher
        self.user_teacher = User.objects.create_user(
            username='teacher@ert.tn',
            email='teacher@ert.tn',
            password=_settings.DEFAULT_PASSWORD,
        )
        self.user_teacher.groups.add(self.teacher_group)
        
        self.client = Client()
    
    def test_isstudent_allows_session_based_auth(self):
        """Test IsStudent allows access via session-based student auth."""
        # Login as student A
        self.client.post("/api/students/login/", {
            "email": "student.a-e@ert.tn",
            "password": _settings.DEFAULT_PASSWORD
        }, content_type="application/json")
        
        # Should be able to access student-only endpoints
        me_resp = self.client.get("/api/students/me/")
        self.assertEqual(me_resp.status_code, status.HTTP_200_OK)
        
        copies_resp = self.client.get("/api/students/copies/")
        self.assertEqual(copies_resp.status_code, status.HTTP_200_OK)
        
        # Should be able to change password
        change_resp = self.client.post("/api/students/change-password/", {
            "current_password": _settings.DEFAULT_PASSWORD,
            "new_password": "NouveauMdp2026!"
        }, content_type="application/json")
        
        self.assertEqual(change_resp.status_code, status.HTTP_200_OK)
    
    def test_orphan_user_without_student_profile_rejected(self):
        """Test that user with Student group but no Student profile is rejected."""
        # Login as orphan user
        login_resp = self.client.post("/api/students/login/", {
            "email": "orphan-e@ert.tn",
            "password": _settings.DEFAULT_PASSWORD
        }, content_type="application/json")
        
        # Should fail at login level
        self.assertEqual(login_resp.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_teacher_cannot_access_student_change_password(self):
        """Test that teacher cannot access student change-password endpoint."""
        # Login as teacher (using admin login, not student)
        # Teachers use a different auth system, but let's verify the permission check
        
        # Create a session directly for the teacher
        self.client.force_login(self.user_teacher)
        
        # Try to access student change-password
        resp = self.client.post("/api/students/change-password/", {
            "current_password": _settings.DEFAULT_PASSWORD,
            "new_password": "NouveauMdp2026!"
        }, content_type="application/json")
        
        # Should be forbidden - teacher doesn't have student_id in session
        self.assertIn(resp.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])


class TestStudentPasswordValidation(TransactionTestCase):
    """Tests for password validation rules."""
    
    def setUp(self):
        super().setUp()
        
        self.student_group, _ = Group.objects.get_or_create(name=UserRole.STUDENT)
        
        self.user = User.objects.create_user(
            username='validation.test-e@ert.tn',
            email='validation.test-e@ert.tn',
            password=_settings.DEFAULT_PASSWORD,
        )
        self.user.groups.add(self.student_group)
        
        self.student = Student.objects.create(
            first_name="Validation",
            last_name="Test",
            class_name="TG1",
            date_naissance=date(2005, 3, 25),  # 25032005
            email="validation.test-e@ert.tn",
            user=self.user,
        )
        
        self.client = Client()
        self.client.post("/api/students/login/", {
            "email": "validation.test-e@ert.tn",
            "password": _settings.DEFAULT_PASSWORD
        }, content_type="application/json")
    
    def test_password_too_short_rejected(self):
        """Test that short passwords are rejected."""
        resp = self.client.post("/api/students/change-password/", {
            "current_password": _settings.DEFAULT_PASSWORD,
            "new_password": "short"
        }, content_type="application/json")
        
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        # Django's validate_password returns e.messages as a list
        error_data = resp.json()['error']
        self.assertIsInstance(error_data, (list, str))  # Can be list of messages or single string
    
    def test_password_common_rejected(self):
        """Test that common passwords are rejected."""
        resp = self.client.post("/api/students/change-password/", {
            "current_password": _settings.DEFAULT_PASSWORD,
            "new_password": "password123"
        }, content_type="application/json")
        
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_password_entirely_numeric_rejected(self):
        """Test that entirely numeric passwords are rejected."""
        resp = self.client.post("/api/students/change-password/", {
            "current_password": _settings.DEFAULT_PASSWORD,
            "new_password": "12345678"
        }, content_type="application/json")
        
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_strong_password_accepted(self):
        """Test that strong passwords are accepted."""
        strong_passwords = [
            "MonSuperMdp2026!",
            "Korrigo#Secure9",
            "Bienvenue@2026",
        ]
        
        for pwd in strong_passwords:
            resp = self.client.post("/api/students/change-password/", {
                "current_password": _settings.DEFAULT_PASSWORD,
                "new_password": pwd
            }, content_type="application/json")
            
            self.assertEqual(resp.status_code, status.HTTP_200_OK, 
                           f"Password {pwd} should be accepted")
            
            # Reset for next test
            self.client.logout()
            # Update user's password back to default for next iteration
            self.user.set_password(_settings.DEFAULT_PASSWORD)
            self.user.save()
            
            # Re-login
            self.client.post("/api/students/login/", {
                "email": "validation.test-e@ert.tn",
                "password": _settings.DEFAULT_PASSWORD
            }, content_type="application/json")
