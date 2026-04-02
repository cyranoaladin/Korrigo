import json

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import Client, override_settings

from core.auth import UserRole
from students.models import Student

User = get_user_model()


@pytest.mark.django_db
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_student_account_cannot_request_password_reset():
    user = User.objects.create_user(
        username="student_reset_test",
        email="student_reset@ert.tn",
        password="passe123",
        is_active=True,
    )
    Student.objects.create(
        first_name="Reset",
        last_name="Test",
        class_name="TG1",
        date_naissance="2007-01-01",
        email="student_reset_profile@ert.tn",
        user=user,
    )

    from django.core import mail

    client = Client()
    response = client.post(
        "/api/password-reset/",
        data=json.dumps({"email": "student_reset@ert.tn"}),
        content_type="application/json",
    )

    assert response.status_code == 200
    assert "Si un compte existe" in response.json()["message"]
    assert len(mail.outbox) == 0


@pytest.mark.django_db
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_smtp_failure_returns_generic_response(monkeypatch):
    user = User.objects.create_user(
        username="smtp_fail_teacher",
        email="smtp_fail@ert.tn",
        password="Secret!1234",
        is_active=True,
    )
    teacher_group, _ = Group.objects.get_or_create(name=UserRole.TEACHER)
    user.groups.add(teacher_group)

    def raise_smtp(*args, **kwargs):
        raise ConnectionRefusedError("SMTP unavailable")

    from core import views_password_reset

    monkeypatch.setattr(views_password_reset, "send_mail", raise_smtp)

    client = Client()
    response = client.post(
        "/api/password-reset/",
        data=json.dumps({"email": "smtp_fail@ert.tn"}),
        content_type="application/json",
    )

    assert response.status_code == 200
    assert "Si un compte existe" in response.json()["message"]
