from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient

from core.auth import create_user_roles
from exams.models import Exam, Copy
from students.models import Student


class AuthSessionsRBACTests(TestCase):
    def setUp(self):
        self.admin_group, self.teacher_group, self.student_group = create_user_roles()

        self.admin_user = User.objects.create_user(
            username="admin_user",
            password="testpass123",
        )
        self.admin_user.groups.add(self.admin_group)

        self.teacher_user = User.objects.create_user(
            username="teacher_user",
            password="testpass123",
        )
        self.teacher_user.groups.add(self.teacher_group)

        self.student_a = Student.objects.create(
            ine="INE123456",
            first_name="Alice",
            last_name="Student",
            class_name="T1",
        )
        self.student_b = Student.objects.create(
            ine="INE654321",
            first_name="Bob",
            last_name="Other",
            class_name="T2",
        )

        self.exam = Exam.objects.create(
            name="Exam RBAC",
            date=timezone.now().date(),
        )
        self.copy_ready = Copy.objects.create(
            exam=self.exam,
            anonymous_id="READY1",
            status=Copy.Status.READY,
            student=self.student_a,
        )
        self.copy_graded_other = Copy.objects.create(
            exam=self.exam,
            anonymous_id="GRADED1",
            status=Copy.Status.GRADED,
            student=self.student_b,
        )

    def test_login_success_and_failure(self):
        client = APIClient()
        ok_response = client.post(
            "/api/login/",
            {"username": "admin_user", "password": "testpass123"},
            format="json",
        )
        self.assertEqual(ok_response.status_code, 200)

        ko_response = client.post(
            "/api/login/",
            {"username": "admin_user", "password": "wrongpass"},
            format="json",
        )
        self.assertEqual(ko_response.status_code, 401)

    def test_me_requires_authentication(self):
        client = APIClient()
        response = client.get("/api/me/")
        self.assertEqual(response.status_code, 403)

        client.force_login(self.admin_user)
        response = client.get("/api/me/")
        self.assertEqual(response.status_code, 200)

    def test_change_password_requires_csrf(self):
        client = APIClient(enforce_csrf_checks=True)
        client.force_login(self.admin_user)

        response = client.post(
            "/api/change-password/",
            {"password": "StrongPass123!"},
            format="json",
        )
        self.assertEqual(response.status_code, 403)

    def test_teacher_cannot_call_admin_endpoints(self):
        client = APIClient()
        client.force_login(self.teacher_user)

        upload_response = client.post("/api/exams/upload/")
        self.assertEqual(upload_response.status_code, 403)

        export_response = client.post(f"/api/exams/{self.exam.id}/export-pdf/")
        self.assertEqual(export_response.status_code, 403)

        dispatch_response = client.post(f"/api/exams/{self.exam.id}/dispatch/")
        # 403 if permission denied, 400 if no correctors assigned (but permission passed)
        # After RBAC fix, teacher should get 403
        self.assertEqual(dispatch_response.status_code, 403)

        merge_response = client.post(f"/api/exams/{self.exam.id}/merge-booklets/", {"booklet_ids": []})
        self.assertEqual(merge_response.status_code, 403)

    def test_student_copies_list_isolation_and_status(self):
        client = APIClient()
        login_response = client.post(
            "/api/students/login/",
            {"ine": self.student_a.ine, "last_name": self.student_a.last_name},
            format="json",
        )
        self.assertEqual(login_response.status_code, 200)

        response = client.get("/api/students/copies/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, [])

    def test_student_logout_clears_session(self):
        client = APIClient()
        login_response = client.post(
            "/api/students/login/",
            {"ine": self.student_a.ine, "last_name": self.student_a.last_name},
            format="json",
        )
        self.assertEqual(login_response.status_code, 200)

        logout_response = client.post("/api/students/logout/")
        self.assertEqual(logout_response.status_code, 200)

        me_response = client.get("/api/students/me/")
        # After logout, session cleared -> 401 or 403 (permission denied)
        self.assertIn(me_response.status_code, [401, 403])
