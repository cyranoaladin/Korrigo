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
def locked_copy(exam, booklet_with_pages, admin_user):
    """Creates a LOCKED copy."""
    from exams.models import Copy
    from django.utils import timezone
    copy = Copy.objects.create(
        exam=exam,
        anonymous_id="TEST-LOCKED",
        status=Copy.Status.LOCKED,
        locked_at=timezone.now(),
        locked_by=admin_user
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

    url = f"/api/copies/{copy.id}/ready/"
    response = authenticated_client.post(url, {}, format="json")

    assert response.status_code == 400
    assert "detail" in response.data
    assert "no booklets with pages found" in response.data["detail"]

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

    url = f"/api/copies/{staging_copy.id}/ready/"

    # Check no events exist yet
    assert GradingEvent.objects.filter(copy=staging_copy).count() == 0

    response = authenticated_client.post(url, {}, format="json")

    assert response.status_code == 200
    assert response.data["status"] == "READY"
    assert response.data["copy_id"] == str(staging_copy.id)

    # Verify DB state
    staging_copy.refresh_from_db()
    assert staging_copy.status == Copy.Status.READY
    assert staging_copy.validated_at is not None

    # Verify GradingEvent created
    events = GradingEvent.objects.filter(copy=staging_copy)
    assert events.count() == 1
    assert events.first().action == GradingEvent.Action.VALIDATE


@pytest.mark.unit
def test_lock_only_allowed_from_ready(authenticated_client, staging_copy):
    """
    Test that LOCK transition only works from READY status.
    Attempting to lock a STAGING copy should return 400.
    """
    from exams.models import Copy

    url = f"/api/copies/{staging_copy.id}/lock/"
    response = authenticated_client.post(url, {}, format="json")

    assert response.status_code == 400
    assert "detail" in response.data
    assert "Cannot lock copy in status STAGING" in response.data["detail"]

    # Verify status unchanged
    staging_copy.refresh_from_db()
    assert staging_copy.status == Copy.Status.STAGING


@pytest.mark.unit
def test_finalize_only_allowed_from_locked(authenticated_client, ready_copy):
    """
    Test that FINALIZE transition only works from LOCKED status.
    Attempting to finalize a READY copy should return 400.
    """
    from exams.models import Copy

    url = f"/api/copies/{ready_copy.id}/finalize/"
    response = authenticated_client.post(url, {}, format="json")

    assert response.status_code == 400
    assert "detail" in response.data
    assert "Cannot finalize copy in status READY" in response.data["detail"]

    # Verify status unchanged
    ready_copy.refresh_from_db()
    assert ready_copy.status == Copy.Status.READY


@pytest.mark.unit
def test_lock_transition_success(authenticated_client, ready_copy, admin_user):
    """
    Test successful READY → LOCKED transition:
    - Changes status to LOCKED
    - Sets locked_at and locked_by
    - Creates GradingEvent
    """
    from exams.models import Copy
    from grading.models import GradingEvent

    url = f"/api/copies/{ready_copy.id}/lock/"
    response = authenticated_client.post(url, {}, format="json")

    assert response.status_code == 200
    assert response.data["status"] == "LOCKED"

    # Verify DB state
    ready_copy.refresh_from_db()
    assert ready_copy.status == Copy.Status.LOCKED
    assert ready_copy.locked_at is not None
    assert ready_copy.locked_by == admin_user

    # Verify GradingEvent created
    events = GradingEvent.objects.filter(copy=ready_copy, action=GradingEvent.Action.LOCK)
    assert events.count() == 1


@pytest.mark.unit
def test_unlock_transition_success(authenticated_client, locked_copy):
    """
    Test successful LOCKED → READY transition:
    - Changes status to READY
    - Clears locked_at and locked_by
    - Creates GradingEvent
    """
    from exams.models import Copy
    from grading.models import GradingEvent

    url = f"/api/copies/{locked_copy.id}/unlock/"
    response = authenticated_client.post(url, {}, format="json")

    assert response.status_code == 200
    assert response.data["status"] == "READY"

    # Verify DB state
    locked_copy.refresh_from_db()
    assert locked_copy.status == Copy.Status.READY
    assert locked_copy.locked_at is None
    assert locked_copy.locked_by is None

    # Verify GradingEvent created
    events = GradingEvent.objects.filter(copy=locked_copy, action=GradingEvent.Action.UNLOCK)
    assert events.count() == 1
