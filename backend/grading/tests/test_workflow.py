"""
Tests for Copy workflow state machine (ADR-003).
"""
import pytest
from datetime import date


@pytest.fixture
def exam(db):
    """Creates a basic exam."""
    from exams.models import Exam
    return Exam.objects.create(name="Test Exam", date=date.today())


@pytest.fixture
def booklet_with_pages(exam):
    """Creates a booklet with 2 pages."""
    from exams.models import Booklet
    return Booklet.objects.create(
        exam=exam,
        start_page=0,
        end_page=1,
        pages_images=["page1.png", "page2.png"]
    )


@pytest.fixture
def staging_copy(exam, booklet_with_pages):
    """Creates a STAGING copy with booklet."""
    from exams.models import Copy
    copy = Copy.objects.create(
        exam=exam,
        anonymous_id="TEST-STAGING",
        status=Copy.Status.STAGING
    )
    copy.booklets.add(booklet_with_pages)
    return copy


@pytest.fixture
def ready_copy(exam, booklet_with_pages):
    """Creates a READY copy with booklet."""
    from exams.models import Copy
    copy = Copy.objects.create(
        exam=exam,
        anonymous_id="TEST-READY",
        status=Copy.Status.READY
    )
    copy.booklets.add(booklet_with_pages)
    return copy


@pytest.fixture
def graded_copy(exam, booklet_with_pages, admin_user):
    """Creates a GRADED copy."""
    from exams.models import Copy
    from django.utils import timezone
    copy = Copy.objects.create(
        exam=exam,
        anonymous_id="TEST-GRADED",
        status=Copy.Status.GRADED,
        graded_at=timezone.now(),
    )
    copy.booklets.add(booklet_with_pages)
    return copy


# ============================================================================
# C) Workflow état Copy (ADR-003)
# ============================================================================

@pytest.mark.unit
def test_ready_transition_requires_pages(authenticated_client, exam):
    """
    Test STAGING → READY transition rejects if no booklets with pages.
    """
    from exams.models import Copy

    # Create copy without booklet (or with empty booklet)
    copy = Copy.objects.create(
        exam=exam,
        anonymous_id="TEST-NO-PAGES",
        status=Copy.Status.STAGING
    )

    url = f"/api/grading/copies/{copy.id}/ready/"
    response = authenticated_client.post(url, {}, format="json")

    assert response.status_code == 400
    assert "detail" in response.data
    assert "No pages found, cannot validate." in response.data["detail"]

    # Verify copy status unchanged
    copy.refresh_from_db()
    assert copy.status == Copy.Status.STAGING


@pytest.mark.unit
def test_ready_transition_changes_status_and_creates_event(
    authenticated_client, staging_copy
):
    """
    Test STAGING → READY transition:
    - Changes Copy.status to READY
    - Sets Copy.validated_at
    - Creates GradingEvent with action=VALIDATE
    """
    from exams.models import Copy
    from grading.models import GradingEvent

    url = f"/api/grading/copies/{staging_copy.id}/ready/"

    # Check no events exist yet
    assert GradingEvent.objects.filter(copy=staging_copy).count() == 0

    response = authenticated_client.post(url, {}, format="json")

    assert response.status_code == 200
    assert response.data["status"] == "READY"
    # assert response.data["copy_id"] == str(staging_copy.id)

    # Verify DB state
    staging_copy.refresh_from_db()
    assert staging_copy.status == Copy.Status.READY
    assert staging_copy.validated_at is not None

    # Verify GradingEvent created
    events = GradingEvent.objects.filter(copy=staging_copy)
    assert events.count() == 1
    assert events.first().action == GradingEvent.Action.VALIDATE





@pytest.mark.unit
def test_finalize_works_from_ready(authenticated_client, ready_copy):
    """
    Test that FINALIZE transition allowed from READY status.
    Simplified workflow: no lock required.
    """
    from exams.models import Copy
    from unittest.mock import patch

    url = f"/api/grading/copies/{ready_copy.id}/finalize/"

    with patch('processing.services.pdf_flattener.PDFFlattener.flatten_copy') as mock_flatten:
        mock_flatten.return_value = b"%PDF-1.4\n%%EOF"
        response = authenticated_client.post(url, {}, format="json")

    assert response.status_code == 200
    assert response.data["status"] == "GRADED"

    ready_copy.refresh_from_db()
    assert ready_copy.status == Copy.Status.GRADED


@pytest.mark.unit
def test_lock_routes_return_404(authenticated_client, ready_copy):
    """
    Lock routes have been removed. Verify they return 404.
    """
    base = f"/api/grading/copies/{ready_copy.id}"
    for path in [f"{base}/lock/", f"{base}/lock/release/", f"{base}/lock/heartbeat/"]:
        response = authenticated_client.post(path, {}, format="json")
        assert response.status_code == 404, f"{path} should return 404"


@pytest.mark.unit
def test_finalize_graded_copy_rejected(authenticated_client, graded_copy):
    """
    Finalizing an already GRADED copy should be rejected.
    """
    from unittest.mock import patch
    url = f"/api/grading/copies/{graded_copy.id}/finalize/"

    with patch('processing.services.pdf_flattener.PDFFlattener.flatten_copy') as mock_flatten:
        mock_flatten.return_value = b"%PDF-1.4\n%%EOF"
        response = authenticated_client.post(url, {}, format="json")

    assert response.status_code in [400, 409]
    assert mock_flatten.call_count == 0

