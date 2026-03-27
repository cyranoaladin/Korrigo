"""
Regression tests for C2 + M1:
  - UserListView, UserManageView, UserResetPasswordView now use permission_classes=[IsAdmin]
  - GlobalSettingsView.post() now uses _is_admin_user() (includes Admin group)
  - Admin-group users without is_staff must be able to manage users and settings.
"""
from django.test import TestCase
from django.contrib.auth.models import User, Group
from rest_framework.test import APIClient
from core.auth import UserRole, create_user_roles


class TestAdminGateRemediation(TestCase):
    """Admin-group users (no is_staff) must have full access to user-management endpoints."""

    def setUp(self):
        create_user_roles()
        self.admin_group = Group.objects.get(name=UserRole.ADMIN)
        self.teacher_group = Group.objects.get(name=UserRole.TEACHER)

        # Admin-group user without is_staff / is_superuser (the case that was broken)
        self.group_admin = User.objects.create_user(
            username="group_admin", password="pw_admin123"
        )
        self.group_admin.groups.add(self.admin_group)
        # Explicitly ensure no staff/superuser flags
        self.group_admin.is_staff = False
        self.group_admin.is_superuser = False
        self.group_admin.save()

        # Superuser (should also work — baseline)
        self.superuser = User.objects.create_superuser(
            username="superadmin", password="pw_super123"
        )

        # Teacher — must be blocked
        self.teacher = User.objects.create_user(username="teacher_x", password="pw_t")
        self.teacher.groups.add(self.teacher_group)

        # Target user to manage
        self.target = User.objects.create_user(
            username="target_user", password="pw_target"
        )
        self.target.groups.add(self.teacher_group)

        self.client = APIClient()

    # ─── UserListView.get ────────────────────────────────────────────────────

    def test_group_admin_can_list_users(self):
        self.client.force_authenticate(user=self.group_admin)
        resp = self.client.get("/api/users/")
        self.assertEqual(resp.status_code, 200)

    def test_superuser_can_list_users(self):
        self.client.force_authenticate(user=self.superuser)
        resp = self.client.get("/api/users/")
        self.assertEqual(resp.status_code, 200)

    def test_teacher_cannot_list_users(self):
        self.client.force_authenticate(user=self.teacher)
        resp = self.client.get("/api/users/")
        self.assertEqual(resp.status_code, 403)

    # ─── UserListView.post ───────────────────────────────────────────────────

    def test_group_admin_can_create_user(self):
        self.client.force_authenticate(user=self.group_admin)
        resp = self.client.post(
            "/api/users/",
            {"username": "new_teacher", "password": "pw_new123", "role": "Teacher"},
            format="json",
        )
        self.assertEqual(resp.status_code, 201)

    def test_teacher_cannot_create_user(self):
        self.client.force_authenticate(user=self.teacher)
        resp = self.client.post(
            "/api/users/",
            {"username": "hacker", "password": "pw_hacker", "role": "Teacher"},
            format="json",
        )
        self.assertEqual(resp.status_code, 403)

    # ─── UserManageView.put ──────────────────────────────────────────────────

    def test_group_admin_can_edit_user(self):
        self.client.force_authenticate(user=self.group_admin)
        resp = self.client.put(
            f"/api/users/{self.target.id}/",
            {"email": "updated@example.com"},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)

    def test_teacher_cannot_edit_user(self):
        self.client.force_authenticate(user=self.teacher)
        resp = self.client.put(
            f"/api/users/{self.target.id}/",
            {"email": "hack@example.com"},
            format="json",
        )
        self.assertEqual(resp.status_code, 403)

    # ─── UserManageView.delete ───────────────────────────────────────────────

    def test_group_admin_can_delete_other_user(self):
        victim = User.objects.create_user(username="to_delete", password="pw")
        self.client.force_authenticate(user=self.group_admin)
        resp = self.client.delete(f"/api/users/{victim.id}/")
        self.assertEqual(resp.status_code, 204)

    def test_group_admin_cannot_delete_self(self):
        self.client.force_authenticate(user=self.group_admin)
        resp = self.client.delete(f"/api/users/{self.group_admin.id}/")
        self.assertEqual(resp.status_code, 400)

    # ─── UserResetPasswordView ───────────────────────────────────────────────

    def test_group_admin_can_reset_password(self):
        self.client.force_authenticate(user=self.group_admin)
        resp = self.client.post(f"/api/users/{self.target.id}/reset-password/")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("temporary_password", resp.data)

    def test_teacher_cannot_reset_password(self):
        self.client.force_authenticate(user=self.teacher)
        resp = self.client.post(f"/api/users/{self.target.id}/reset-password/")
        self.assertEqual(resp.status_code, 403)

    # ─── GlobalSettingsView.post ─────────────────────────────────────────────

    def test_group_admin_can_save_settings(self):
        self.client.force_authenticate(user=self.group_admin)
        resp = self.client.post(
            "/api/settings/",
            {"institutionName": "Test School", "theme": "dark"},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)

    def test_superuser_can_save_settings(self):
        self.client.force_authenticate(user=self.superuser)
        resp = self.client.post(
            "/api/settings/",
            {"institutionName": "Super School"},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)

    def test_teacher_cannot_save_settings(self):
        self.client.force_authenticate(user=self.teacher)
        resp = self.client.post(
            "/api/settings/",
            {"institutionName": "Hacker School"},
            format="json",
        )
        self.assertEqual(resp.status_code, 403)
