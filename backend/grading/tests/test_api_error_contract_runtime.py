"""
API error contract tests for the simplified (no-lock) workflow.
Verifies that annotation/finalize endpoints return correct status codes
and response shapes for various error conditions.
"""
import pytest
import unittest.mock


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
def ready_copy(exam, booklet_with_pages, teacher_user):
    from exams.models import Copy

    copy = Copy.objects.create(
        exam=exam,
        anonymous_id="CONTRACT-READY",
        status=Copy.Status.READY,
        assigned_corrector=teacher_user,
    )
    copy.booklets.add(booklet_with_pages)
    return copy


@pytest.fixture
def graded_copy(exam, booklet_with_pages, teacher_user):
    from exams.models import Copy

    copy = Copy.objects.create(
        exam=exam,
        anonymous_id="CONTRACT-GRADED",
        status=Copy.Status.GRADED,
        assigned_corrector=teacher_user,
    )
    copy.booklets.add(booklet_with_pages)
    return copy


@pytest.mark.django_db
def test_annotation_create_on_graded_returns_400(teacher_client, graded_copy):
    """Annotating a GRADED copy must return 400 with detail key."""
    url = f"/api/grading/copies/{graded_copy.id}/annotations/"
    payload = {
        "page_index": 0,
        "x": 0.1, "y": 0.1, "w": 0.1, "h": 0.1,
        "type": "COMMENT",
        "content": "Test",
    }

    resp = teacher_client.post(url, payload, format="json")

    assert resp.status_code == 400
    assert "detail" in resp.data


@pytest.mark.django_db
def test_annotation_delete_on_graded_returns_400(teacher_client, graded_copy, teacher_user):
    """Deleting an annotation on a GRADED copy must return 400."""
    from grading.models import Annotation

    ann = Annotation.objects.create(
        copy=graded_copy,
        page_index=0,
        x=0.1, y=0.1, w=0.1, h=0.1,
        type=Annotation.Type.COMMENT,
        content="To delete",
        created_by=teacher_user,
    )

    url = f"/api/grading/annotations/{ann.id}/"
    resp = teacher_client.delete(url)

    assert resp.status_code == 400
    assert "detail" in resp.data


@pytest.mark.django_db
def test_finalize_graded_copy_returns_error(teacher_client, graded_copy):
    """Finalizing an already GRADED copy must return 400 or 409."""
    url = f"/api/grading/copies/{graded_copy.id}/finalize/"

    with unittest.mock.patch("processing.services.pdf_flattener.PDFFlattener.flatten_copy") as mock_flatten:
        mock_flatten.return_value = b"%PDF-1.4\n%%EOF"
        resp = teacher_client.post(url, {}, format="json")

    assert resp.status_code in [400, 409]
    assert "detail" in resp.data
    assert mock_flatten.call_count == 0  # Must not attempt PDF generation


@pytest.mark.django_db
def test_annotation_create_on_ready_returns_201(teacher_client, ready_copy):
    """Annotating a READY copy should succeed (201)."""
    url = f"/api/grading/copies/{ready_copy.id}/annotations/"
    payload = {
        "page_index": 0,
        "x": 0.1, "y": 0.1, "w": 0.1, "h": 0.1,
        "type": "COMMENT",
        "content": "Valid annotation",
    }

    resp = teacher_client.post(url, payload, format="json")

    assert resp.status_code == 201


@pytest.mark.django_db
def test_finalize_ready_copy_returns_200(teacher_client, ready_copy):
    """Finalizing a READY copy should succeed (200)."""
    url = f"/api/grading/copies/{ready_copy.id}/finalize/"

    with unittest.mock.patch("processing.services.pdf_flattener.PDFFlattener.flatten_copy") as mock_flatten:
        mock_flatten.return_value = b"%PDF-1.4\n%%EOF"
        resp = teacher_client.post(url, {}, format="json")

    assert resp.status_code == 200


@pytest.mark.django_db
def test_lock_routes_return_404(teacher_client, ready_copy):
    """Lock routes must return 404 (removed from URL conf)."""
    base = f"/api/grading/copies/{ready_copy.id}"

    for path in [f"{base}/lock/", f"{base}/lock/heartbeat/", f"{base}/lock/release/", f"{base}/lock/status/"]:
        resp = teacher_client.post(path, {}, format="json")
        assert resp.status_code == 404, f"{path} should return 404, got {resp.status_code}"
