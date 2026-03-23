"""
Tests for CopyReopenView (POST /api/grading/copies/<uuid>/reopen/).
Covers superuser-only reopen of GRADED copies, field clearing, preservation
of child data (scores, annotations, remarks), and audit trail.
"""
import pytest
import uuid
from django.utils import timezone
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group

from exams.models import Exam, Copy
from grading.models import GradingEvent, Annotation, Score, QuestionRemark
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
def copy_graded(db, exam, teacher_user):
    """A copy in GRADED status with final_pdf, graded_at and retries set."""
    return Copy.objects.create(
        exam=exam,
        status=Copy.Status.GRADED,
        assigned_corrector=teacher_user,
        anonymous_id=f"ANON-{uuid.uuid4().hex[:8]}",
        final_pdf="copies/final/test.pdf",
        graded_at=timezone.now(),
        grading_retries=3,
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
def copy_staging(db, exam, teacher_user):
    return Copy.objects.create(
        exam=exam,
        status=Copy.Status.STAGING,
        assigned_corrector=teacher_user,
        anonymous_id=f"ANON-{uuid.uuid4().hex[:8]}",
    )


@pytest.fixture
def staff_non_superuser(db):
    """Staff user who is NOT superuser — should be rejected by CopyReopenView."""
    user = User.objects.create_user(
        username="staff_nosuperuser",
        password="testpass123",
        is_staff=True,
        is_superuser=False,
    )
    g, _ = Group.objects.get_or_create(name=UserRole.ADMIN)
    user.groups.add(g)
    return user


@pytest.fixture
def score(db, copy_graded):
    return Score.objects.create(
        copy=copy_graded,
        scores_data={"Q1": 4, "Q2": 3},
        final_comment="Bon travail",
    )


@pytest.fixture
def annotation(db, copy_graded, teacher_user):
    return Annotation.objects.create(
        copy=copy_graded,
        page_index=0,
        x=0.1, y=0.1, w=0.2, h=0.1,
        type=Annotation.Type.COMMENT,
        content="Bien",
        score_delta=2,
        created_by=teacher_user,
    )


@pytest.fixture
def question_remark(db, copy_graded, teacher_user):
    return QuestionRemark.objects.create(
        copy=copy_graded,
        question_id="Q1",
        remark="Attention a la methode",
        created_by=teacher_user,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestCopyReopen:

    def _url(self, copy_id):
        return f"/api/grading/copies/{copy_id}/reopen/"

    # -- happy path ---------------------------------------------------------

    def test_superuser_can_reopen_graded_copy(self, admin_user, copy_graded):
        """Superuser reopens GRADED copy: status becomes READY, fields cleared."""
        client = APIClient()
        client.force_authenticate(user=admin_user)

        resp = client.post(self._url(copy_graded.id))
        assert resp.status_code == 200
        copy_graded.refresh_from_db()
        assert copy_graded.status == Copy.Status.READY

    # -- permission denied --------------------------------------------------

    def test_admin_staff_cannot_reopen(self, staff_non_superuser, copy_graded):
        """Non-superuser staff gets 403."""
        client = APIClient()
        client.force_authenticate(user=staff_non_superuser)

        resp = client.post(self._url(copy_graded.id))
        assert resp.status_code == 403

    def test_teacher_cannot_reopen(self, teacher_user, copy_graded):
        """Teacher (staff but not superuser) gets 403."""
        client = APIClient()
        client.force_authenticate(user=teacher_user)

        resp = client.post(self._url(copy_graded.id))
        assert resp.status_code == 403

    # -- invalid statuses ---------------------------------------------------

    def test_reopen_non_graded_copy_returns_400(self, admin_user, copy_ready):
        """READY copy cannot be reopened — returns 400."""
        client = APIClient()
        client.force_authenticate(user=admin_user)

        resp = client.post(self._url(copy_ready.id))
        assert resp.status_code == 400

    def test_reopen_staging_copy_returns_400(self, admin_user, copy_staging):
        """STAGING copy cannot be reopened — returns 400."""
        client = APIClient()
        client.force_authenticate(user=admin_user)

        resp = client.post(self._url(copy_staging.id))
        assert resp.status_code == 400

    # -- field clearing -----------------------------------------------------

    def test_reopen_clears_final_pdf(self, admin_user, copy_graded):
        """After reopen, final_pdf is None."""
        client = APIClient()
        client.force_authenticate(user=admin_user)

        client.post(self._url(copy_graded.id))
        copy_graded.refresh_from_db()
        assert not copy_graded.final_pdf

    def test_reopen_clears_graded_at(self, admin_user, copy_graded):
        """After reopen, graded_at is None."""
        client = APIClient()
        client.force_authenticate(user=admin_user)

        client.post(self._url(copy_graded.id))
        copy_graded.refresh_from_db()
        assert copy_graded.graded_at is None

    def test_reopen_resets_grading_retries(self, admin_user, copy_graded):
        """After reopen, grading_retries is 0."""
        client = APIClient()
        client.force_authenticate(user=admin_user)

        client.post(self._url(copy_graded.id))
        copy_graded.refresh_from_db()
        assert copy_graded.grading_retries == 0

    # -- preservation of child data -----------------------------------------

    def test_reopen_preserves_scores(self, admin_user, copy_graded, score):
        """Score records still exist after reopen."""
        client = APIClient()
        client.force_authenticate(user=admin_user)

        client.post(self._url(copy_graded.id))
        assert Score.objects.filter(copy=copy_graded).exists()

    def test_reopen_preserves_annotations(self, admin_user, copy_graded, annotation):
        """Annotation records still exist after reopen."""
        client = APIClient()
        client.force_authenticate(user=admin_user)

        client.post(self._url(copy_graded.id))
        assert Annotation.objects.filter(copy=copy_graded).exists()

    def test_reopen_preserves_remarks(self, admin_user, copy_graded, question_remark):
        """QuestionRemark records still exist after reopen."""
        client = APIClient()
        client.force_authenticate(user=admin_user)

        client.post(self._url(copy_graded.id))
        assert QuestionRemark.objects.filter(copy=copy_graded).exists()

    # -- audit trail --------------------------------------------------------

    def test_reopen_creates_audit_event(self, admin_user, copy_graded):
        """GradingEvent REOPEN is created with metadata."""
        client = APIClient()
        client.force_authenticate(user=admin_user)

        client.post(self._url(copy_graded.id))

        events = GradingEvent.objects.filter(
            copy=copy_graded, action=GradingEvent.Action.REOPEN
        )
        assert events.count() == 1
        event = events.first()
        assert event.actor == admin_user
        assert event.metadata["previous_status"] == Copy.Status.GRADED

    # -- 404 ---------------------------------------------------------------

    def test_reopen_nonexistent_copy_returns_404(self, admin_user):
        """Reopen on a non-existent copy UUID returns 404."""
        client = APIClient()
        client.force_authenticate(user=admin_user)

        fake_id = uuid.uuid4()
        resp = client.post(self._url(fake_id))
        assert resp.status_code == 404
