import pytest
from django.contrib.auth.models import User
from django.core import mail
from django.test import override_settings
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.contrib.auth.tokens import default_token_generator
from rest_framework.test import APIClient


@pytest.mark.django_db
@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    SERVER_EMAIL="noreply@korrigo.test",
    FRONTEND_URL="https://frontend.korrigo.test",
)
def test_password_reset_request_returns_generic_message_and_sends_mail():
    user = User.objects.create_user(
        username="resetuser",
        email="reset@example.com",
        password="OldPassword123!",
    )
    client = APIClient()

    response = client.post("/api/password-reset/", {"email": "reset@example.com"}, format="json")

    assert response.status_code == 200
    assert "Si un compte existe" in response.data["message"]
    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == [user.email]
    assert "frontend.korrigo.test/reset-password" in mail.outbox[0].body


@pytest.mark.django_db
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_password_reset_request_unknown_email_stays_generic():
    client = APIClient()

    response = client.post("/api/password-reset/", {"email": "unknown@example.com"}, format="json")

    assert response.status_code == 200
    assert "Si un compte existe" in response.data["message"]
    assert len(mail.outbox) == 0


@pytest.mark.django_db
def test_password_reset_confirm_updates_password_and_clears_flag():
    user = User.objects.create_user(
        username="confirmuser",
        email="confirm@example.com",
        password="OldPassword123!",
    )
    user.profile.must_change_password = True
    user.profile.save(update_fields=["must_change_password"])
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    client = APIClient()

    response = client.post(
        "/api/password-reset/confirm/",
        {"uid": uid, "token": token, "new_password": "NewPassword123!"},
        format="json",
    )

    assert response.status_code == 200
    user.refresh_from_db()
    assert user.check_password("NewPassword123!")
    assert user.profile.must_change_password is False


@pytest.mark.django_db
def test_password_reset_confirm_rejects_invalid_token():
    user = User.objects.create_user(
        username="badtokenuser",
        email="badtoken@example.com",
        password="OldPassword123!",
    )
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    client = APIClient()

    response = client.post(
        "/api/password-reset/confirm/",
        {"uid": uid, "token": "invalid-token", "new_password": "NewPassword123!"},
        format="json",
    )

    assert response.status_code == 400
    assert "invalide" in str(response.data["error"]).lower()
