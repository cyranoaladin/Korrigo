import json

import pytest
from django.contrib.auth import get_user_model
from django.conf import settings as _settings
from django.contrib.auth.models import Group
from django.test import Client
from rest_framework.test import APIClient

from core.auth import UserRole
from exams.models import Copy, Exam
from grading.models import CopyLock
from students.models import Student

User = get_user_model()


@pytest.fixture
def exam(db):
    return Exam.objects.create(name="Exam V31", date="2026-04-02")


@pytest.fixture
def admin_group_user(db):
    group, _ = Group.objects.get_or_create(name=UserRole.ADMIN)
    user = User.objects.create_user(
        username="admin_group_v31",
        password="testpass123",
        is_staff=True,
        is_superuser=False,
    )
    user.groups.add(group)
    return user


@pytest.fixture
def admin_group_client(admin_group_user):
    client = APIClient()
    client.force_authenticate(user=admin_group_user)
    return client


@pytest.fixture
def teacher_client(teacher_user):
    client = APIClient()
    client.force_authenticate(user=teacher_user)
    return client


@pytest.fixture
def admin_client(admin_user):
    client = APIClient()
    client.force_authenticate(user=admin_user)
    return client


@pytest.fixture
def finalized_copy(db, exam, teacher_user):
    return Copy.objects.create(
        exam=exam,
        anonymous_id="FINAL001",
        status=Copy.Status.FINALIZED,
        assigned_corrector=teacher_user,
    )


@pytest.fixture
def copy_with_lock(db, exam, teacher_user):
    copy = Copy.objects.create(
        exam=exam,
        anonymous_id="LOCK001",
        status=Copy.Status.READY,
        assigned_corrector=teacher_user,
    )
    CopyLock.objects.create(copy=copy, owner=teacher_user, expires_at="2030-01-01T00:00:00Z")
    return copy


@pytest.fixture
def student_django_client(db):
    group, _ = Group.objects.get_or_create(name=UserRole.STUDENT)
    user = User.objects.create_user(
        username="student_stats_v31",
        password="testpass123",
        email="student.stats.v31@ert.tn",
    )
    user.groups.add(group)
    Student.objects.create(
        first_name="Student",
        last_name="Stats",
        class_name="TG1",
        date_naissance="2007-01-01",
        email="student.stats.profile.v31@ert.tn",
        user=user,
    )
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.fixture
def student_user_for_login(db):
    user = User.objects.create_user(
        username="student.login.v31",
        email="student.login.v31@ert.tn",
        password=_settings.DEFAULT_PASSWORD,
    )
    student_group, _ = Group.objects.get_or_create(name=UserRole.STUDENT)
    user.groups.add(student_group)
    student = Student.objects.create(
        first_name="Login",
        last_name="Student",
        class_name="TG1",
        date_naissance="2007-01-01",
        email="student.login.v31@ert.tn",
        user=user,
    )
    return student


@pytest.fixture
def two_users_same_email(db):
    email = "duplicate.v31@ert.tn"
    user1 = User.objects.create_user(username="dupv31_1", email=email, password="secret1")
    user2 = User.objects.create_user(username="dupv31_2", email=email, password="secret2")
    student_group, _ = Group.objects.get_or_create(name=UserRole.STUDENT)
    user1.groups.add(student_group)
    user2.groups.add(student_group)
    Student.objects.create(
        first_name="Dup",
        last_name="One",
        class_name="TG1",
        date_naissance="2007-01-01",
        email="dup.one.v31@ert.tn",
        user=user1,
    )
    return email


@pytest.mark.django_db
class TestPronoteExportPermissions:
    def test_teacher_cannot_export_pronote(self, teacher_client, exam):
        res = teacher_client.post(f"/api/exams/{exam.id}/export-pronote/")
        assert res.status_code == 403

    def test_admin_can_export_pronote(self, admin_client, exam):
        res = admin_client.post(f"/api/exams/{exam.id}/export-pronote/")
        assert res.status_code in (200, 400)


@pytest.mark.django_db
class TestForceUnlockPermissions:
    def test_teacher_cannot_force_unlock(self, teacher_client, copy_with_lock):
        res = teacher_client.post(f"/api/grading/copies/{copy_with_lock.id}/force-unlock/")
        assert res.status_code == 403

    def test_admin_group_can_force_unlock(self, admin_group_client, copy_with_lock):
        res = admin_group_client.post(f"/api/grading/copies/{copy_with_lock.id}/force-unlock/")
        assert res.status_code in (200, 204)


@pytest.mark.django_db
class TestCopyReopenPermissions:
    def test_teacher_cannot_reopen(self, teacher_client, finalized_copy):
        res = teacher_client.post(f"/api/grading/copies/{finalized_copy.id}/reopen/")
        assert res.status_code == 403

    def test_admin_group_can_reopen(self, admin_group_client, finalized_copy):
        res = admin_group_client.post(f"/api/grading/copies/{finalized_copy.id}/reopen/")
        assert res.status_code == 200


@pytest.mark.django_db
class TestCorrectorStatsPermissions:
    def test_authenticated_non_teacher_cannot_access_stats(self, student_django_client, exam):
        res = student_django_client.get(f"/api/grading/exams/{exam.id}/stats/")
        assert res.status_code == 403


@pytest.mark.django_db
class TestStudentLoginSessionCache:
    def test_must_change_password_cached_in_session_at_login(self, student_user_for_login):
        client = Client()
        res = client.post(
            "/api/students/login/",
            data=json.dumps({"email": student_user_for_login.email, "password": _settings.DEFAULT_PASSWORD}),
            content_type="application/json",
        )
        assert res.status_code == 200
        assert "must_change_password" in client.session
        assert res.json()["must_change_password"] is True


@pytest.mark.django_db
class TestDuplicateEmailLogin:
    def test_duplicate_email_does_not_crash_student_login(self, two_users_same_email):
        client = Client()
        res = client.post(
            "/api/students/login/",
            data=json.dumps({"email": two_users_same_email, "password": "wrongpass"}),
            content_type="application/json",
        )
        assert res.status_code in (400, 401)


@pytest.mark.django_db
class TestExamDeletePermissions:
    def test_teacher_cannot_delete_exam(self, teacher_client, exam):
        res = teacher_client.delete(f"/api/exams/{exam.id}/")
        assert res.status_code == 403

    def test_admin_can_delete_exam(self, admin_group_client, exam):
        res = admin_group_client.delete(f"/api/exams/{exam.id}/")
        assert res.status_code == 204
