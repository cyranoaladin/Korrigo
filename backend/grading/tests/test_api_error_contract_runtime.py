import pytest
from django.utils import timezone
import datetime


@pytest.fixture
def exam(db):
    from datetime import date
    from exams.models import Exam

    return Exam.objects.create(name="Contract Exam", date=date.today())


@pytest.fixture
def booklet_with_pages(exam):
    from exams.models import Booklet

    return Booklet.objects.create(
        exam=exam,
        start_page=0,
        end_page=0,
        pages_images=["p0.png"],
    )


@pytest.fixture
def locked_copy_with_lock(exam, booklet_with_pages, teacher_user):
    from exams.models import Copy
    from grading.models import CopyLock

    copy = Copy.objects.create(
        exam=exam,
        anonymous_id="CONTRACT-LOCKED",
        status=Copy.Status.LOCKED,
        locked_at=timezone.now(),
        locked_by=teacher_user,
    )
    copy.booklets.add(booklet_with_pages)

    lock = CopyLock.objects.create(
        copy=copy,
        owner=teacher_user,
        expires_at=timezone.now() + datetime.timedelta(minutes=10),
    )
    return copy, lock


@pytest.mark.django_db
def test_annotation_create_missing_token_returns_403_detail(teacher_client, locked_copy_with_lock):
    copy, _lock = locked_copy_with_lock

    url = f"/api/grading/copies/{copy.id}/annotations/"
    payload = {
        "page_index": 0,
        "x": 0.1,
        "y": 0.1,
        "w": 0.1,
        "h": 0.1,
        "type": "COMMENT",
        "content": "Test",
    }

    resp = teacher_client.post(url, payload, format="json")

    assert resp.status_code == 403
    assert "detail" in resp.data
    assert "error" not in resp.data


@pytest.mark.django_db
def test_annotation_delete_missing_token_returns_403_detail(teacher_client, locked_copy_with_lock, teacher_user):
    copy, _lock = locked_copy_with_lock

    from grading.models import Annotation

    ann = Annotation.objects.create(
        copy=copy,
        page_index=0,
        x=0.1,
        y=0.1,
        w=0.1,
        h=0.1,
        type=Annotation.Type.COMMENT,
        content="To delete",
        created_by=teacher_user,
    )

    url = f"/api/grading/annotations/{ann.id}/"
    resp = teacher_client.delete(url)

    assert resp.status_code == 403
    assert "detail" in resp.data
    assert "error" not in resp.data


@pytest.mark.django_db
def test_finalize_missing_token_returns_403_detail(teacher_client, locked_copy_with_lock, monkeypatch):
    copy, _lock = locked_copy_with_lock

    url = f"/api/grading/copies/{copy.id}/finalize/"

    import unittest.mock
    with unittest.mock.patch("processing.services.pdf_flattener.PDFFlattener.flatten_copy") as mock_flatten:
        mock_flatten.return_value = b"%PDF-1.4\n%%EOF"
        resp = teacher_client.post(url, {}, format="json")

    assert resp.status_code == 403
    assert "detail" in resp.data
    assert "error" not in resp.data


@pytest.mark.django_db
def test_finalize_expired_lock_returns_409_detail(teacher_client, locked_copy_with_lock):
    copy, lock = locked_copy_with_lock

    lock.expires_at = timezone.now() - datetime.timedelta(minutes=1)
    lock.save(update_fields=["expires_at"])

    url = f"/api/grading/copies/{copy.id}/finalize/"

    import unittest.mock
    with unittest.mock.patch("processing.services.pdf_flattener.PDFFlattener.flatten_copy") as mock_flatten:
        mock_flatten.return_value = b"%PDF-1.4\n%%EOF"
        resp = teacher_client.post(url, {}, format="json", HTTP_X_LOCK_TOKEN=str(lock.token))

    assert resp.status_code == 409
    assert "detail" in resp.data
    assert "error" not in resp.data


@pytest.mark.django_db
def test_lock_heartbeat_missing_token_returns_403_detail(teacher_client, locked_copy_with_lock):
    copy, _lock = locked_copy_with_lock

    url = f"/api/grading/copies/{copy.id}/lock/heartbeat/"
    resp = teacher_client.post(url, {}, format="json")

    assert resp.status_code == 403
    assert "detail" in resp.data
    assert "error" not in resp.data


@pytest.mark.django_db
def test_lock_release_bad_token_returns_403_detail(teacher_client, locked_copy_with_lock):
    copy, _lock = locked_copy_with_lock

    url = f"/api/grading/copies/{copy.id}/lock/release/"
    resp = teacher_client.delete(url, HTTP_X_LOCK_TOKEN="bad-token")

    assert resp.status_code == 403
    assert "detail" in resp.data
    assert "error" not in resp.data
