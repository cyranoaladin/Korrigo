"""
Tests for AdminForceUnlockView (POST /api/grading/copies/<uuid>/force-unlock/).
Covers admin force-unlock of CopyLock, permission checks, and audit trail.
"""
import pytest
import uuid
from django.utils import timezone
from datetime import timedelta
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group

from exams.models import Exam, Copy
from grading.models import CopyLock, GradingEvent
from core.auth import UserRole

User = get_user_model()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def exam(db):
    return Exam.objects.create(
        name="Test Exam",
        grading_structure=[
            {"label": "Ex1", "points": 10, "children": [
                {"label": "Q1", "points": 5},
                {"label": "Q2", "points": 5},
            ]}
        ],
    )


@pytest.fixture
def copy_ready(db, exam, teacher_user):
    return Copy.objects.create(
        exam=exam,
        status=Copy.Status.READY,
        assigned_corrector=teacher_user,
        anonymous_id=f"ANON-{uuid.uuid4().hex[:8]}",
    )


@pytest.fixture
def non_staff_teacher(db):
    """A teacher in the TEACHER group but NOT staff — passes IsTeacherOrAdmin
    via group membership but fails the view-level is_staff/is_superuser check."""
    user = User.objects.create_user(
        username="teacher_nostaff",
        password="testpass123",
        is_staff=False,
        is_superuser=False,
    )
    g, _ = Group.objects.get_or_create(name=UserRole.TEACHER)
    user.groups.add(g)
    return user


@pytest.fixture
def lock(db, copy_ready, teacher_user):
    """Create a CopyLock owned by teacher_user."""
    return CopyLock.objects.create(
        copy=copy_ready,
        owner=teacher_user,
        expires_at=timezone.now() + timedelta(hours=1),
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestAdminForceUnlock:

    def _url(self, copy_id):
        return f"/api/grading/copies/{copy_id}/force-unlock/"

    # -- happy paths --------------------------------------------------------

    def test_admin_can_force_unlock_locked_copy(self, admin_user, copy_ready, lock):
        """Admin (superuser+staff) force-unlocks: lock deleted, GradingEvent created."""
        client = APIClient()
        client.force_authenticate(user=admin_user)

        resp = client.post(self._url(copy_ready.id))
        assert resp.status_code == 200
        assert not CopyLock.objects.filter(copy=copy_ready).exists()
        event = GradingEvent.objects.filter(
            copy=copy_ready, action=GradingEvent.Action.UNLOCK
        ).first()
        assert event is not None
        assert event.metadata["admin_force"] is True
        assert event.metadata["had_lock"] is True

    def test_superuser_can_force_unlock(self, admin_user, copy_ready, lock):
        """Superuser can force-unlock (admin_user fixture is superuser)."""
        client = APIClient()
        client.force_authenticate(user=admin_user)

        resp = client.post(self._url(copy_ready.id))
        assert resp.status_code == 200
        assert "copy_id" in resp.data

    # -- permission denied --------------------------------------------------

    def test_teacher_cannot_force_unlock(self, non_staff_teacher, copy_ready, lock):
        """A teacher who is NOT staff gets 403 on force-unlock."""
        client = APIClient()
        client.force_authenticate(user=non_staff_teacher)

        resp = client.post(self._url(copy_ready.id))
        assert resp.status_code == 403

    def test_regular_user_cannot_force_unlock(self, regular_user, copy_ready, lock):
        """Non-staff, non-teacher user gets 403."""
        client = APIClient()
        client.force_authenticate(user=regular_user)

        resp = client.post(self._url(copy_ready.id))
        assert resp.status_code == 403

    # -- edge cases ---------------------------------------------------------

    def test_force_unlock_no_lock_returns_204(self, admin_user, copy_ready):
        """If no lock exists, the view returns 204 with an audit event."""
        client = APIClient()
        client.force_authenticate(user=admin_user)

        resp = client.post(self._url(copy_ready.id))
        assert resp.status_code == 204
        event = GradingEvent.objects.filter(
            copy=copy_ready, action=GradingEvent.Action.UNLOCK
        ).first()
        assert event is not None
        assert event.metadata["had_lock"] is False

    def test_force_unlock_nonexistent_copy_returns_404(self, admin_user):
        """Force-unlock on a non-existent copy UUID returns 404."""
        client = APIClient()
        client.force_authenticate(user=admin_user)

        fake_id = uuid.uuid4()
        resp = client.post(self._url(fake_id))
        assert resp.status_code == 404

    # -- audit trail --------------------------------------------------------

    def test_force_unlock_creates_audit_event(self, admin_user, copy_ready, lock):
        """GradingEvent is created with UNLOCK action and admin_force metadata."""
        client = APIClient()
        client.force_authenticate(user=admin_user)

        client.post(self._url(copy_ready.id))

        events = GradingEvent.objects.filter(
            copy=copy_ready, action=GradingEvent.Action.UNLOCK
        )
        assert events.count() == 1
        event = events.first()
        assert event.actor == admin_user
        assert event.metadata["admin_force"] is True

    def test_force_unlock_records_previous_owner(self, admin_user, copy_ready, lock, teacher_user):
        """Metadata contains 'previous_lock_owner' with the former lock holder's username."""
        client = APIClient()
        client.force_authenticate(user=admin_user)

        client.post(self._url(copy_ready.id))

        event = GradingEvent.objects.filter(
            copy=copy_ready, action=GradingEvent.Action.UNLOCK
        ).first()
        assert event.metadata["previous_lock_owner"] == teacher_user.username
