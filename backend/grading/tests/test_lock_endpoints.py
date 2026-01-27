import datetime

import pytest
from django.utils import timezone


@pytest.fixture
def ready_copy(db, exam):
    from exams.models import Booklet, Copy

    booklet = Booklet.objects.create(
        exam=exam,
        start_page=0,
        end_page=0,
        pages_images=["p0.png"],
    )
    copy = Copy.objects.create(exam=exam, anonymous_id="LOCK-READY", status=Copy.Status.READY)
    copy.booklets.add(booklet)
    return copy


@pytest.fixture
def exam(db):
    from datetime import date
    from exams.models import Exam

    return Exam.objects.create(name="Lock Exam", date=date.today())


@pytest.mark.django_db
def test_lock_acquire_ttl_invalid_returns_400_detail(teacher_client, ready_copy):
    url = f"/api/grading/copies/{ready_copy.id}/lock/"
    resp = teacher_client.post(url, {"ttl_seconds": "abc"}, format="json")

    assert resp.status_code == 400
    assert "detail" in resp.data
    assert "error" not in resp.data


@pytest.mark.django_db
def test_lock_acquire_ttl_negative_returns_400_detail(teacher_client, ready_copy):
    url = f"/api/grading/copies/{ready_copy.id}/lock/"
    resp = teacher_client.post(url, {"ttl_seconds": -5}, format="json")

    assert resp.status_code == 400
    assert "detail" in resp.data
    assert "error" not in resp.data


@pytest.mark.django_db
def test_lock_acquire_ttl_too_big_is_clamped_to_3600(teacher_client, ready_copy):
    url = f"/api/grading/copies/{ready_copy.id}/lock/"
    before = timezone.now()
    resp = teacher_client.post(url, {"ttl_seconds": 999999}, format="json")

    assert resp.status_code == 201
    assert "expires_at" in resp.data

    expires_at = resp.data["expires_at"]
    # DRF returns ISO string, but may already be parsed depending on settings
    if isinstance(expires_at, str):
        expires_at = datetime.datetime.fromisoformat(expires_at.replace("Z", "+00:00"))

    delta = expires_at - before
    assert delta <= datetime.timedelta(seconds=3600 + 5)


@pytest.mark.django_db
def test_lock_release_missing_token_returns_403_detail(teacher_client, ready_copy):
    # acquire
    lock_resp = teacher_client.post(f"/api/grading/copies/{ready_copy.id}/lock/", {}, format="json")
    assert lock_resp.status_code == 201

    resp = teacher_client.delete(f"/api/grading/copies/{ready_copy.id}/lock/release/")
    assert resp.status_code == 403
    assert "detail" in resp.data
    assert "error" not in resp.data


@pytest.mark.django_db
def test_lock_release_absent_lock_returns_204(teacher_client, ready_copy):
    resp = teacher_client.delete(
        f"/api/grading/copies/{ready_copy.id}/lock/release/",
        HTTP_X_LOCK_TOKEN="deadbeef",
    )
    assert resp.status_code == 204


@pytest.mark.django_db
def test_lock_heartbeat_owner_mismatch_returns_409_detail(teacher_client, teacher_user, ready_copy, regular_user):
    # teacher_client owns lock
    lock_resp = teacher_client.post(f"/api/grading/copies/{ready_copy.id}/lock/", {}, format="json")
    assert lock_resp.status_code == 201
    token = lock_resp.data["token"]

    from rest_framework.test import APIClient

    other = APIClient()
    other.force_authenticate(user=regular_user)
    resp = other.post(
        f"/api/grading/copies/{ready_copy.id}/lock/heartbeat/",
        {},
        format="json",
        HTTP_X_LOCK_TOKEN=str(token),
    )
    # regular_user is not teacher/admin, permission gate fires first
    assert resp.status_code == 403
    assert "detail" in resp.data
    assert "error" not in resp.data
