"""Tests verifying that lock routes have been removed (return 404)."""
import pytest


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
def test_lock_acquire_returns_404(teacher_client, ready_copy):
    """Lock routes have been removed; POST /lock/ returns 404."""
    url = f"/api/grading/copies/{ready_copy.id}/lock/"
    resp = teacher_client.post(url, {}, format="json")
    assert resp.status_code == 404


@pytest.mark.django_db
def test_lock_release_returns_404(teacher_client, ready_copy):
    """Lock routes have been removed; DELETE /lock/release/ returns 404."""
    resp = teacher_client.delete(f"/api/grading/copies/{ready_copy.id}/lock/release/")
    assert resp.status_code == 404


@pytest.mark.django_db
def test_lock_heartbeat_returns_404(teacher_client, ready_copy):
    """Lock routes have been removed; POST /lock/heartbeat/ returns 404."""
    resp = teacher_client.post(
        f"/api/grading/copies/{ready_copy.id}/lock/heartbeat/",
        {},
        format="json",
    )
    assert resp.status_code == 404
