"""
Tests for CopyScoreCorrectionView (POST /api/grading/copies/<uuid>/score-correction/).
Covers score correction on FINALIZED copies with mandatory justification, permission checks,
barème validation, audit logging, and PDF invalidation.
"""
import pytest
import uuid
from unittest.mock import patch
from django.utils import timezone
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group

from exams.models import Exam, Copy
from grading.models import GradingEvent, Score
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
def copy_finalized(db, exam, teacher_user):
    """A copy in FINALIZED status with final_pdf and scores."""
    copy = Copy.objects.create(
        exam=exam,
        status=Copy.Status.FINALIZED,
        assigned_corrector=teacher_user,
        anonymous_id=f"ANON-{uuid.uuid4().hex[:8]}",
        final_pdf="copies/final/test.pdf",
        graded_at=timezone.now(),
    )
    # Create initial score
    Score.objects.create(
        copy=copy,
        scores_data={"Q1": 4, "Q2": 3},
        final_comment="Bon travail",
    )
    return copy


@pytest.fixture
def copy_ready(db, exam, teacher_user):
    """A copy in READY status (should not be correctable via this endpoint)."""
    return Copy.objects.create(
        exam=exam,
        status=Copy.Status.READY,
        assigned_corrector=teacher_user,
        anonymous_id=f"ANON-{uuid.uuid4().hex[:8]}",
    )


@pytest.fixture
def admin_user(db):
    user = User.objects.create_user(
        username="admin_test",
        password="testpass123",
        is_staff=True,
        is_superuser=True,
    )
    g, _ = Group.objects.get_or_create(name=UserRole.ADMIN)
    user.groups.add(g)
    return user


@pytest.fixture
def staff_non_superuser(db):
    """Admin-group staff user who is NOT superuser."""
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
def teacher_user(db):
    user = User.objects.create_user(
        username="teacher_test",
        password="testpass123",
        is_staff=True,
    )
    g, _ = Group.objects.get_or_create(name=UserRole.TEACHER)
    user.groups.add(g)
    return user


@pytest.fixture
def other_teacher(db):
    """A teacher not assigned to the copy."""
    user = User.objects.create_user(
        username="other_teacher",
        password="testpass123",
        is_staff=True,
    )
    g, _ = Group.objects.get_or_create(name=UserRole.TEACHER)
    user.groups.add(g)
    return user


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestCopyScoreCorrection:

    def _url(self, copy_id):
        return f"/api/grading/copies/{copy_id}/score-correction/"

    # -- happy path ---------------------------------------------------------

    def test_admin_can_correct_finalized_copy(self, admin_user, copy_finalized):
        """Admin can correct a FINALIZED copy with justification."""
        client = APIClient()
        client.force_authenticate(user=admin_user)

        payload = {
            "scores_data": {"Q1": 5, "Q2": 4},
            "final_comment": "Très bon travail",
            "reason": "Erreur de calcul détectée lors de la revue"
        }

        resp = client.post(self._url(copy_finalized.id), payload, format='json')
        assert resp.status_code == 200
        
        data = resp.json()
        assert data['copy_id'] == str(copy_finalized.id)
        assert data['scores_data'] == {"Q1": 5, "Q2": 4}
        assert data['old_total'] == 7.0  # 4 + 3
        assert data['new_total'] == 9.0  # 5 + 4
        assert data['pdf_regeneration_pending'] is True

    def test_assigned_corrector_can_correct(self, teacher_user, copy_finalized):
        """Assigned corrector can correct their own FINALIZED copy."""
        client = APIClient()
        client.force_authenticate(user=teacher_user)

        payload = {
            "scores_data": {"Q1": 5, "Q2": 4},
            "final_comment": "Très bon travail",
            "reason": "Correction après relecture"
        }

        resp = client.post(self._url(copy_finalized.id), payload, format='json')
        assert resp.status_code == 200

    def test_staff_admin_can_correct(self, staff_non_superuser, copy_finalized):
        """Admin group user can correct even without superuser flag."""
        client = APIClient()
        client.force_authenticate(user=staff_non_superuser)

        payload = {
            "scores_data": {"Q1": 5, "Q2": 4},
            "final_comment": "Très bon travail",
            "reason": "Correction admin"
        }

        resp = client.post(self._url(copy_finalized.id), payload, format='json')
        assert resp.status_code == 200

    # -- permission denied --------------------------------------------------

    def test_unassigned_teacher_cannot_correct(self, other_teacher, copy_finalized):
        """Teacher not assigned to copy gets 403."""
        client = APIClient()
        client.force_authenticate(user=other_teacher)

        payload = {
            "scores_data": {"Q1": 5, "Q2": 4},
            "final_comment": "Très bon travail",
            "reason": "Tentative non autorisée"
        }

        resp = client.post(self._url(copy_finalized.id), payload, format='json')
        assert resp.status_code == 403

    def test_unauthenticated_cannot_correct(self, copy_finalized):
        """Unauthenticated user gets 401/403."""
        client = APIClient()
        
        payload = {
            "scores_data": {"Q1": 5, "Q2": 4},
            "final_comment": "Très bon travail",
            "reason": "Test"
        }

        resp = client.post(self._url(copy_finalized.id), payload, format='json')
        assert resp.status_code in (401, 403)

    # -- invalid statuses ---------------------------------------------------

    def test_cannot_correct_non_finalized_copy(self, admin_user, copy_ready):
        """READY copy cannot be corrected via this endpoint."""
        client = APIClient()
        client.force_authenticate(user=admin_user)

        payload = {
            "scores_data": {"Q1": 5, "Q2": 4},
            "final_comment": "Très bon travail",
            "reason": "Test"
        }

        resp = client.post(self._url(copy_ready.id), payload, format='json')
        assert resp.status_code == 400
        assert "finalisées" in resp.json()['detail'].lower()

    # -- mandatory reason ----------------------------------------------------

    def test_reason_is_mandatory(self, admin_user, copy_finalized):
        """Reason field is mandatory."""
        client = APIClient()
        client.force_authenticate(user=admin_user)

        payload = {
            "scores_data": {"Q1": 5, "Q2": 4},
            "final_comment": "Très bon travail",
            "reason": ""
        }

        resp = client.post(self._url(copy_finalized.id), payload, format='json')
        assert resp.status_code == 400
        assert "justification" in resp.json()['detail'].lower() or "reason" in resp.json()['detail'].lower()

    def test_missing_reason_rejected(self, admin_user, copy_finalized):
        """Missing reason field is rejected."""
        client = APIClient()
        client.force_authenticate(user=admin_user)

        payload = {
            "scores_data": {"Q1": 5, "Q2": 4},
            "final_comment": "Très bon travail",
        }

        resp = client.post(self._url(copy_finalized.id), payload, format='json')
        assert resp.status_code == 400

    # -- barème validation ---------------------------------------------------

    def test_score_cannot_exceed_max_per_question(self, admin_user, copy_finalized):
        """Score exceeding max per question is rejected."""
        client = APIClient()
        client.force_authenticate(user=admin_user)

        payload = {
            "scores_data": {"Q1": 10, "Q2": 4},  # Q1 max is 5
            "final_comment": "Très bon travail",
            "reason": "Test"
        }

        resp = client.post(self._url(copy_finalized.id), payload, format='json')
        assert resp.status_code == 400
        assert "dépasse" in resp.json()['detail'].lower() or "maximum" in resp.json()['detail'].lower()

    def test_negative_score_rejected(self, admin_user, copy_finalized):
        """Negative score is rejected."""
        client = APIClient()
        client.force_authenticate(user=admin_user)

        payload = {
            "scores_data": {"Q1": -1, "Q2": 4},
            "final_comment": "Très bon travail",
            "reason": "Test"
        }

        resp = client.post(self._url(copy_finalized.id), payload, format='json')
        assert resp.status_code == 400
        assert "négative" in resp.json()['detail'].lower() or "négatif" in resp.json()['detail'].lower()

    def test_total_cannot_exceed_exam_max(self, admin_user, copy_finalized):
        """Total score exceeding exam max is rejected."""
        client = APIClient()
        client.force_authenticate(user=admin_user)

        payload = {
            "scores_data": {"Q1": 5, "Q2": 6},  # Total 11, max is 10
            "final_comment": "Très bon travail",
            "reason": "Test"
        }

        resp = client.post(self._url(copy_finalized.id), payload, format='json')
        assert resp.status_code == 400
        assert "total" in resp.json()['detail'].lower() and "dépasse" in resp.json()['detail'].lower()

    # -- audit trail --------------------------------------------------------

    def test_correction_creates_grading_event(self, admin_user, copy_finalized):
        """GradingEvent SCORE_CORRECTED is created with complete metadata."""
        client = APIClient()
        client.force_authenticate(user=admin_user)

        payload = {
            "scores_data": {"Q1": 5, "Q2": 4},
            "final_comment": "Très bon travail",
            "reason": "Erreur de calcul détectée"
        }

        resp = client.post(self._url(copy_finalized.id), payload, format='json')
        assert resp.status_code == 200

        events = GradingEvent.objects.filter(
            copy=copy_finalized,
            action=GradingEvent.Action.SCORE_CORRECTED
        )
        assert events.count() == 1
        event = events.first()
        assert event.actor == admin_user
        assert event.metadata['old_scores_data'] == {"Q1": 4, "Q2": 3}
        assert event.metadata['new_scores_data'] == {"Q1": 5, "Q2": 4}
        assert event.metadata['old_total'] == 7.0
        assert event.metadata['new_total'] == 9.0
        assert 'Erreur de calcul détectée' in event.metadata['reason']

    # -- PDF regeneration flag ----------------------------------------------------

    def test_correction_sets_pdf_regeneration_pending(self, admin_user, copy_finalized):
        """pdf_regeneration_pending is set to True after correction."""
        client = APIClient()
        client.force_authenticate(user=admin_user)

        assert copy_finalized.pdf_regeneration_pending is False

        payload = {
            "scores_data": {"Q1": 5, "Q2": 4},
            "final_comment": "Très bon travail",
            "reason": "Test"
        }

        resp = client.post(self._url(copy_finalized.id), payload, format='json')
        assert resp.status_code == 200

        copy_finalized.refresh_from_db()
        assert copy_finalized.pdf_regeneration_pending is True
        # final_pdf should still exist (not deleted)
        assert copy_finalized.final_pdf is not None

    def test_correction_when_already_pending_still_works(self, admin_user, copy_finalized):
        """Correction works even if pdf_regeneration_pending was already True."""
        copy_finalized.pdf_regeneration_pending = True
        copy_finalized.save()

        client = APIClient()
        client.force_authenticate(user=admin_user)

        payload = {
            "scores_data": {"Q1": 5, "Q2": 4},
            "final_comment": "Très bon travail",
            "reason": "Test"
        }

        resp = client.post(self._url(copy_finalized.id), payload, format='json')
        assert resp.status_code == 200
        assert resp.json()['pdf_regeneration_pending'] is True

    # -- PDF endpoint behavior when regeneration pending ----------------------

    def test_pdf_endpoint_returns_503_when_regeneration_pending(self, admin_user, copy_finalized):
        """CopyFinalPdfView returns 503 when pdf_regeneration_pending is True."""
        copy_finalized.pdf_regeneration_pending = True
        copy_finalized.save()

        client = APIClient()
        client.force_authenticate(user=admin_user)

        resp = client.get(f"/api/grading/copies/{copy_finalized.id}/final-pdf/")
        assert resp.status_code == 503

    # -- PDF regeneration ------------------------------------------------------

    @patch('processing.services.pdf_flattener.PDFFlattener.flatten_copy')
    def test_admin_can_regenerate_pdf_when_pending(self, mock_flatten, admin_user, copy_finalized):
        """Admin can regenerate PDF when pdf_regeneration_pending=True."""
        mock_flatten.return_value = b"fake pdf content"
        copy_finalized.pdf_regeneration_pending = True
        copy_finalized.save()

        client = APIClient()
        client.force_authenticate(user=admin_user)

        resp = client.post(f"/api/grading/copies/{copy_finalized.id}/regenerate-final-pdf/")
        assert resp.status_code == 200
        assert resp.json()['pdf_regenerated'] is True

        copy_finalized.refresh_from_db()
        assert copy_finalized.pdf_regeneration_pending is False

    @patch('processing.services.pdf_flattener.PDFFlattener.flatten_copy')
    def test_regenerate_pdf_creates_grading_event(self, mock_flatten, admin_user, copy_finalized):
        """PDF regeneration creates a GradingEvent with PDF_REGENERATED action."""
        mock_flatten.return_value = b"fake pdf content"
        copy_finalized.pdf_regeneration_pending = True
        copy_finalized.save()

        client = APIClient()
        client.force_authenticate(user=admin_user)

        resp = client.post(f"/api/grading/copies/{copy_finalized.id}/regenerate-final-pdf/")
        assert resp.status_code == 200

        events = GradingEvent.objects.filter(
            copy=copy_finalized,
            action=GradingEvent.Action.PDF_REGENERATED
        )
        assert events.count() == 1
        event = events.first()
        assert event.actor == admin_user
        assert 'regenerated_at' in event.metadata

    def test_regenerate_pdf_fails_when_not_pending(self, admin_user, copy_finalized):
        """PDF regeneration fails when pdf_regeneration_pending=False."""
        assert copy_finalized.pdf_regeneration_pending is False

        client = APIClient()
        client.force_authenticate(user=admin_user)

        resp = client.post(f"/api/grading/copies/{copy_finalized.id}/regenerate-final-pdf/")
        assert resp.status_code == 400
        assert "en attente" in resp.json()['detail'].lower()

    def test_regenerate_pdf_fails_for_non_finalized_copy(self, admin_user, copy_ready):
        """PDF regeneration fails for non-FINALIZED copy."""
        copy_ready.pdf_regeneration_pending = True
        copy_ready.save()

        client = APIClient()
        client.force_authenticate(user=admin_user)

        resp = client.post(f"/api/grading/copies/{copy_ready.id}/regenerate-final-pdf/")
        assert resp.status_code == 400
        assert "finalisées" in resp.json()['detail'].lower()

    @patch('processing.services.pdf_flattener.PDFFlattener.flatten_copy')
    def test_regenerate_pdf_accessible_after_regeneration(self, mock_flatten, admin_user, copy_finalized):
        """PDF final is accessible after regeneration."""
        mock_flatten.return_value = b"fake pdf content"
        copy_finalized.pdf_regeneration_pending = True
        copy_finalized.save()

        client = APIClient()
        client.force_authenticate(user=admin_user)

        # Regenerate PDF
        resp = client.post(f"/api/grading/copies/{copy_finalized.id}/regenerate-final-pdf/")
        assert resp.status_code == 200

        copy_finalized.refresh_from_db()
        assert copy_finalized.pdf_regeneration_pending is False

        # PDF should now be accessible
        resp = client.get(f"/api/grading/copies/{copy_finalized.id}/final-pdf/")
        assert resp.status_code == 200

    # -- Permissions endpoint PDF régénération ---------------------------------

    @patch('processing.services.pdf_flattener.PDFFlattener.flatten_copy')
    def test_superuser_can_regenerate_pdf(self, mock_flatten, copy_finalized):
        """Superuser can regenerate PDF."""
        mock_flatten.return_value = b"fake pdf content"
        copy_finalized.pdf_regeneration_pending = True
        copy_finalized.save()

        superuser = User.objects.create_superuser(username='superuser', password='superpass')
        client = APIClient()
        client.force_authenticate(user=superuser)

        resp = client.post(f"/api/grading/copies/{copy_finalized.id}/regenerate-final-pdf/")
        assert resp.status_code == 200
        assert resp.json()['pdf_regenerated'] is True

    @patch('processing.services.pdf_flattener.PDFFlattener.flatten_copy')
    def test_assigned_corrector_non_admin_cannot_regenerate_pdf(self, mock_flatten, copy_finalized):
        """Assigned corrector without admin role cannot regenerate PDF."""
        mock_flatten.return_value = b"fake pdf content"
        copy_finalized.pdf_regeneration_pending = True
        copy_finalized.save()

        # Create teacher user (not admin)
        teacher_group, _ = Group.objects.get_or_create(name='teacher')
        teacher = User.objects.create_user(username='teacher', password='teacherpass')
        teacher.groups.add(teacher_group)
        copy_finalized.exam.correctors.add(teacher)

        client = APIClient()
        client.force_authenticate(user=teacher)

        resp = client.post(f"/api/grading/copies/{copy_finalized.id}/regenerate-final-pdf/")
        assert resp.status_code == 403

    @patch('processing.services.pdf_flattener.PDFFlattener.flatten_copy')
    def test_unassigned_teacher_cannot_regenerate_pdf(self, mock_flatten, copy_finalized):
        """Unassigned teacher cannot regenerate PDF."""
        mock_flatten.return_value = b"fake pdf content"
        copy_finalized.pdf_regeneration_pending = True
        copy_finalized.save()

        # Create teacher user (not admin, not assigned)
        teacher_group, _ = Group.objects.get_or_create(name='teacher')
        teacher = User.objects.create_user(username='teacher2', password='teacherpass')
        teacher.groups.add(teacher_group)

        client = APIClient()
        client.force_authenticate(user=teacher)

        resp = client.post(f"/api/grading/copies/{copy_finalized.id}/regenerate-final-pdf/")
        assert resp.status_code == 403

    # -- Bilan dynamique après correction --------------------------------------

    def test_bilan_dynamique_reflects_corrected_score(self, admin_user, copy_finalized):
        """Test that the student bilan reflects the corrected score."""
        # Initial score
        initial_score = Score.objects.get(copy=copy_finalized)
        assert initial_score.scores_data == {"Q1": 4, "Q2": 3}
        initial_total = sum(initial_score.scores_data.values())

        # Correct score
        client = APIClient()
        client.force_authenticate(user=admin_user)

        payload = {
            "scores_data": {"Q1": 5, "Q2": 4},
            "final_comment": "Très bon travail",
            "reason": "Correction après relecture"
        }

        resp = client.post(self._url(copy_finalized.id), payload, format='json')
        assert resp.status_code == 200

        # Refresh score
        corrected_score = Score.objects.get(copy=copy_finalized)
        assert corrected_score.scores_data == {"Q1": 5, "Q2": 4}
        corrected_total = sum(corrected_score.scores_data.values())

        # Verify that the total has changed
        assert corrected_total != initial_total
        assert corrected_total == 9.0  # 5 + 4

    # -- Workflow E2E complet -------------------------------------------------

    @patch('processing.services.pdf_flattener.PDFFlattener.flatten_copy')
    def test_e2e_complete_workflow(self, mock_flatten, admin_user, copy_finalized):
        """Test complete E2E workflow: correction → PDF invalidation → regeneration → verification."""
        mock_flatten.return_value = b"fake pdf content"
        client = APIClient()
        client.force_authenticate(user=admin_user)

        # 1. Copie FINALIZED avec PDF accessible
        assert copy_finalized.status == Copy.Status.FINALIZED
        assert copy_finalized.pdf_regeneration_pending is False
        resp = client.get(f"/api/grading/copies/{copy_finalized.id}/final-pdf/")
        assert resp.status_code == 200

        # 2. Correction de note
        initial_score = Score.objects.get(copy=copy_finalized)
        assert initial_score.scores_data == {"Q1": 4, "Q2": 3}

        payload = {
            "scores_data": {"Q1": 5, "Q2": 4},
            "final_comment": "Très bon travail",
            "reason": "Correction après relecture"
        }
        resp = client.post(self._url(copy_finalized.id), payload, format='json')
        assert resp.status_code == 200

        # 3. pdf_regeneration_pending=True
        copy_finalized.refresh_from_db()
        assert copy_finalized.pdf_regeneration_pending is True

        # 4. PDF inaccessible avec 503
        resp = client.get(f"/api/grading/copies/{copy_finalized.id}/final-pdf/")
        assert resp.status_code == 503

        # 5. Régénération admin
        resp = client.post(f"/api/grading/copies/{copy_finalized.id}/regenerate-final-pdf/")
        assert resp.status_code == 200
        assert resp.json()['pdf_regenerated'] is True

        # 6. pdf_regeneration_pending=False
        copy_finalized.refresh_from_db()
        assert copy_finalized.pdf_regeneration_pending is False

        # 7. PDF de nouveau accessible
        resp = client.get(f"/api/grading/copies/{copy_finalized.id}/final-pdf/")
        assert resp.status_code == 200

        # 8. Note corrigée visible dans Score
        corrected_score = Score.objects.get(copy=copy_finalized)
        assert corrected_score.scores_data == {"Q1": 5, "Q2": 4}
        assert sum(corrected_score.scores_data.values()) == 9.0

        # 9. GradingEvent PDF_REGENERATED créé
        events = GradingEvent.objects.filter(
            copy=copy_finalized,
            action=GradingEvent.Action.PDF_REGENERATED
        )
        assert events.count() == 1
        assert events.first().actor == admin_user

    # -- 404 ---------------------------------------------------------------

    def test_correction_nonexistent_copy_returns_404(self, admin_user):
        """Correction on non-existent copy UUID returns 404."""
        client = APIClient()
        client.force_authenticate(user=admin_user)

        payload = {
            "scores_data": {"Q1": 5, "Q2": 4},
            "final_comment": "Très bon travail",
            "reason": "Test"
        }

        fake_id = uuid.uuid4()
        resp = client.post(self._url(fake_id), payload, format='json')
        assert resp.status_code == 404
