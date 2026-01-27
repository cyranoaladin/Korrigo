"""
Tests for annotation coordinate validation (ADR-002) and page_index validation.
"""
import pytest
from django.utils import timezone
import datetime
from datetime import date


@pytest.fixture
def exam_with_copy(db, admin_user):
    """Creates an exam with a READY copy that has 2 pages AND IS LOCKED by admin."""
    from exams.models import Exam, Booklet, Copy
    from grading.models import CopyLock
    from django.utils import timezone

    exam = Exam.objects.create(
        name="Test Exam",
        date=date.today()
    )

    booklet = Booklet.objects.create(
        exam=exam,
        start_page=0,
        end_page=1,
        pages_images=["page1.png", "page2.png"]
    )

    copy = Copy.objects.create(
        exam=exam,
        anonymous_id="TEST-001",
        status=Copy.Status.READY
    )
    copy.booklets.add(booklet)
    
    # Auto-lock for C3
    CopyLock.objects.create(
        copy=copy,
        owner=admin_user,
        expires_at=timezone.now() + datetime.timedelta(hours=1),
    )

    return copy


# ============================================================================
# A) Validation coordonnées (ADR-002)
# ============================================================================

@pytest.mark.unit
def test_reject_annotation_with_w_zero(authenticated_client, exam_with_copy):
    """
    ADR-002: w must be in (0, 1] (strictly positive).
    Test that w=0 is rejected with 400.
    """
    copy = exam_with_copy
    url = f"/api/grading/copies/{copy.id}/annotations/"

    payload = {
        "page_index": 0,
        "x": 0.1,
        "y": 0.1,
        "w": 0,  # Invalid: w=0
        "h": 0.2,
        "type": "COMMENT",
        "content": "Test"
    }

    response = authenticated_client.post(url, payload, format="json")

    assert response.status_code == 400
    assert "detail" in response.data
    assert "w and h must be in (0, 1]" in response.data["detail"]


@pytest.mark.unit
def test_reject_annotation_with_overflow_x_plus_w(authenticated_client, exam_with_copy):
    """
    ADR-002: x + w must not exceed 1.
    Test that x=0.9, w=0.2 (x+w=1.1) is rejected with 400.
    """
    copy = exam_with_copy
    url = f"/api/grading/copies/{copy.id}/annotations/"

    payload = {
        "page_index": 0,
        "x": 0.9,
        "y": 0.1,
        "w": 0.2,  # Invalid: x + w = 1.1 > 1
        "h": 0.2,
        "type": "COMMENT",
        "content": "Test"
    }

    response = authenticated_client.post(url, payload, format="json")

    assert response.status_code == 400
    assert "detail" in response.data
    assert "x + w must not exceed 1" in response.data["detail"]


@pytest.mark.unit
def test_reject_annotation_with_overflow_y_plus_h(authenticated_client, exam_with_copy):
    """
    ADR-002: y + h must not exceed 1.
    Test that y=0.8, h=0.3 (y+h=1.1) is rejected with 400.
    """
    copy = exam_with_copy
    url = f"/api/grading/copies/{copy.id}/annotations/"

    payload = {
        "page_index": 0,
        "x": 0.1,
        "y": 0.8,
        "w": 0.2,
        "h": 0.3,  # Invalid: y + h = 1.1 > 1
        "type": "COMMENT",
        "content": "Test"
    }

    response = authenticated_client.post(url, payload, format="json")

    assert response.status_code == 400
    assert "detail" in response.data
    assert "y + h must not exceed 1" in response.data["detail"]


@pytest.mark.unit
def test_reject_annotation_with_negative_values(authenticated_client, exam_with_copy):
    """
    ADR-002: x, y must be in [0, 1].
    Test that negative values are rejected with 400.
    """
    copy = exam_with_copy
    url = f"/api/grading/copies/{copy.id}/annotations/"

    payload = {
        "page_index": 0,
        "x": -0.1,  # Invalid: negative
        "y": 0.1,
        "w": 0.2,
        "h": 0.2,
        "type": "COMMENT",
        "content": "Test"
    }

    response = authenticated_client.post(url, payload, format="json")

    assert response.status_code == 400
    assert "detail" in response.data
    assert "x and y must be in [0, 1]" in response.data["detail"]


# ============================================================================
# B) Validation page_index
# ============================================================================

@pytest.mark.unit
def test_reject_page_index_out_of_bounds(authenticated_client, exam_with_copy):
    """
    Test that page_index >= total_pages is rejected with 400.
    Copy has 2 pages (indices 0, 1), so page_index=2 should fail.
    """
    copy = exam_with_copy
    url = f"/api/grading/copies/{copy.id}/annotations/"

    payload = {
        "page_index": 2,  # Invalid: only pages 0,1 exist
        "x": 0.1,
        "y": 0.1,
        "w": 0.2,
        "h": 0.2,
        "type": "COMMENT",
        "content": "Test"
    }

    response = authenticated_client.post(url, payload, format="json")

    assert response.status_code == 400
    assert "detail" in response.data
    assert "page_index must be in [0, 1]" in response.data["detail"]


@pytest.mark.unit
def test_accept_page_index_as_string_int(authenticated_client, exam_with_copy):
    """
    Test that page_index as string "0" or "1" is accepted (int-like handling).
    """
    copy = exam_with_copy
    url = f"/api/grading/copies/{copy.id}/annotations/"

    payload = {
        "page_index": "1",  # String but convertible to int
        "x": 0.1,
        "y": 0.1,
        "w": 0.2,
        "h": 0.2,
        "type": "COMMENT",
        "content": "Test"
    }

    response = authenticated_client.post(url, payload, format="json")

    assert response.status_code == 201
    assert response.data["page_index"] == 1  # Converted to int
