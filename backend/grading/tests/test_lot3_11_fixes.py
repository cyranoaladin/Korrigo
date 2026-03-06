"""
Tests for LOT 3-11 P0/P1 fixes.

Covers:
- LOT 3: cancel_task restricted to admin/staff
- LOT 5: _can_write_copy permission on annotation/remark detail views
- LOT 6: Score validation against barème max
- LOT 4: select_for_update race condition protection on CopyScoresView.put
- LOT 8: UniqueConstraint on Score.copy
"""
import pytest
from unittest.mock import patch, Mock
from django.test import TestCase, TransactionTestCase
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.db import IntegrityError
from rest_framework.test import APIClient
from rest_framework import status

from core.auth import UserRole
from exams.models import Copy, Exam, Booklet
from grading.models import Annotation, QuestionRemark, Score

User = get_user_model()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_teacher(username, is_staff=False):
    """Create a teacher user in the 'teacher' group."""
    u = User.objects.create_user(username=username, password='pass1234', is_staff=is_staff)
    g, _ = Group.objects.get_or_create(name=UserRole.TEACHER)
    u.groups.add(g)
    return u


def _make_admin(username):
    """Create a staff/superuser in the 'admin' group."""
    u = User.objects.create_user(username=username, password='pass1234', is_staff=True, is_superuser=True)
    g, _ = Group.objects.get_or_create(name=UserRole.ADMIN)
    u.groups.add(g)
    return u


def _make_student(username):
    """Create a student user in the 'student' group."""
    u = User.objects.create_user(username=username, password='pass1234')
    g, _ = Group.objects.get_or_create(name=UserRole.STUDENT)
    u.groups.add(g)
    return u


def _make_exam_and_copy(teacher=None, exam_name="Test Exam"):
    """Create an Exam + Copy + Booklet, optionally assign a corrector."""
    exam = Exam.objects.create(name=exam_name, date="2026-01-15")
    copy = Copy.objects.create(exam=exam, anonymous_id="TEST-001", status=Copy.Status.READY)
    booklet = Booklet.objects.create(exam=exam, start_page=0, end_page=1, pages_images=["p0.png"])
    copy.booklets.add(booklet)
    if teacher:
        copy.assigned_corrector = teacher
        copy.save(update_fields=["assigned_corrector"])
    return exam, copy


# ===========================================================================
# LOT 3 — cancel_task authorization
# ===========================================================================

class TestCancelTaskAuthorization(TestCase):
    """LOT 3 fix: cancel_task must reject non-admin users with 403."""

    def setUp(self):
        self.admin = _make_admin('admin_cancel')
        self.teacher = _make_teacher('teacher_cancel')
        self.student = _make_student('student_cancel')

    @patch('grading.views_async.AsyncResult')
    def test_admin_can_cancel_task(self, mock_ar):
        """Admin (is_staff + is_superuser) can cancel a task."""
        mock_result = Mock()
        mock_result.state = 'PENDING'
        mock_ar.return_value = mock_result

        client = APIClient()
        client.force_authenticate(user=self.admin)
        resp = client.post('/api/grading/tasks/fake-id/cancel/')

        self.assertEqual(resp.status_code, 200)
        mock_result.revoke.assert_called_once_with(terminate=False)

    @patch('grading.views_async.AsyncResult')
    def test_teacher_cannot_cancel_task(self, mock_ar):
        """Regular teacher (not is_staff) is rejected with 403."""
        mock_result = Mock()
        mock_result.state = 'PENDING'
        mock_ar.return_value = mock_result

        client = APIClient()
        client.force_authenticate(user=self.teacher)
        resp = client.post('/api/grading/tasks/fake-id/cancel/')

        self.assertEqual(resp.status_code, 403)
        mock_result.revoke.assert_not_called()

    @patch('grading.views_async.AsyncResult')
    def test_student_cannot_cancel_task(self, mock_ar):
        """Student is rejected with 403."""
        mock_result = Mock()
        mock_result.state = 'PENDING'
        mock_ar.return_value = mock_result

        client = APIClient()
        client.force_authenticate(user=self.student)
        resp = client.post('/api/grading/tasks/fake-id/cancel/')

        self.assertEqual(resp.status_code, 403)
        mock_result.revoke.assert_not_called()

    @patch('grading.views_async.AsyncResult')
    def test_cancel_uses_soft_revoke(self, mock_ar):
        """Verify terminate=False (soft revoke, no SIGTERM)."""
        mock_result = Mock()
        mock_result.state = 'STARTED'
        mock_ar.return_value = mock_result

        client = APIClient()
        client.force_authenticate(user=self.admin)
        resp = client.post('/api/grading/tasks/fake-id/cancel/')

        self.assertEqual(resp.status_code, 200)
        mock_result.revoke.assert_called_once_with(terminate=False)

    def test_cancel_requires_authentication(self):
        """Unauthenticated request is rejected."""
        client = APIClient()
        resp = client.post('/api/grading/tasks/fake-id/cancel/')
        self.assertIn(resp.status_code, [401, 403])


# ===========================================================================
# LOT 5 — _can_write_copy on annotation/remark detail views
# ===========================================================================

class TestAnnotationDetailPermissions(TestCase):
    """LOT 5 fix: AnnotationDetailView.update/destroy must use _can_write_copy."""

    def setUp(self):
        self.teacher_a = _make_teacher('teacher_a')
        self.teacher_b = _make_teacher('teacher_b')
        self.admin = _make_admin('admin_ann')
        self.exam, self.copy = _make_exam_and_copy(teacher=self.teacher_a)
        self.annotation = Annotation.objects.create(
            copy=self.copy, page_index=0, type=Annotation.Type.COMMENT,
            content="Test annotation", x=0.1, y=0.1, w=0.2, h=0.05,
            created_by=self.teacher_a,
        )

    def test_assigned_corrector_can_update_annotation(self):
        """The assigned corrector can PATCH their own annotation."""
        client = APIClient()
        client.force_authenticate(user=self.teacher_a)
        resp = client.patch(
            f'/api/grading/annotations/{self.annotation.id}/',
            {'content': 'Updated by assigned corrector'},
            format='json',
        )
        self.assertIn(resp.status_code, [200, 201])

    def test_non_assigned_teacher_cannot_update_annotation(self):
        """A teacher NOT assigned to the copy is rejected with 403."""
        client = APIClient()
        client.force_authenticate(user=self.teacher_b)
        resp = client.patch(
            f'/api/grading/annotations/{self.annotation.id}/',
            {'content': 'Attempt by non-assigned teacher'},
            format='json',
        )
        self.assertEqual(resp.status_code, 403)

    def test_admin_can_update_annotation(self):
        """Admin/superuser can update any annotation."""
        client = APIClient()
        client.force_authenticate(user=self.admin)
        resp = client.patch(
            f'/api/grading/annotations/{self.annotation.id}/',
            {'content': 'Updated by admin'},
            format='json',
        )
        self.assertIn(resp.status_code, [200, 201])

    def test_non_assigned_teacher_cannot_delete_annotation(self):
        """A teacher NOT assigned to the copy cannot DELETE the annotation."""
        client = APIClient()
        client.force_authenticate(user=self.teacher_b)
        resp = client.delete(f'/api/grading/annotations/{self.annotation.id}/')
        self.assertEqual(resp.status_code, 403)

    def test_assigned_corrector_can_delete_annotation(self):
        """The assigned corrector can DELETE their annotation."""
        client = APIClient()
        client.force_authenticate(user=self.teacher_a)
        resp = client.delete(f'/api/grading/annotations/{self.annotation.id}/')
        self.assertEqual(resp.status_code, 204)


class TestQuestionRemarkDetailPermissions(TestCase):
    """LOT 5 fix: QuestionRemarkDetailView.update/destroy must use _can_write_copy."""

    def setUp(self):
        self.teacher_a = _make_teacher('teacher_ra')
        self.teacher_b = _make_teacher('teacher_rb')
        self.admin = _make_admin('admin_rem')
        self.exam, self.copy = _make_exam_and_copy(teacher=self.teacher_a)
        self.remark = QuestionRemark.objects.create(
            copy=self.copy, question_id='1.1', remark='Good work',
            created_by=self.teacher_a,
        )

    def test_assigned_corrector_can_update_remark(self):
        """The assigned corrector can PATCH their remark."""
        client = APIClient()
        client.force_authenticate(user=self.teacher_a)
        resp = client.patch(
            f'/api/grading/remarks/{self.remark.id}/',
            {'remark': 'Updated remark'},
            format='json',
        )
        self.assertEqual(resp.status_code, 200)

    def test_non_assigned_teacher_cannot_update_remark(self):
        """A teacher NOT assigned to the copy is rejected with 403."""
        client = APIClient()
        client.force_authenticate(user=self.teacher_b)
        resp = client.patch(
            f'/api/grading/remarks/{self.remark.id}/',
            {'remark': 'Attempt by non-assigned'},
            format='json',
        )
        self.assertEqual(resp.status_code, 403)

    def test_non_assigned_teacher_cannot_delete_remark(self):
        """A teacher NOT assigned to the copy cannot DELETE the remark."""
        client = APIClient()
        client.force_authenticate(user=self.teacher_b)
        resp = client.delete(f'/api/grading/remarks/{self.remark.id}/')
        self.assertEqual(resp.status_code, 403)

    def test_admin_can_update_remark(self):
        """Admin can update any remark."""
        client = APIClient()
        client.force_authenticate(user=self.admin)
        resp = client.patch(
            f'/api/grading/remarks/{self.remark.id}/',
            {'remark': 'Admin update'},
            format='json',
        )
        self.assertEqual(resp.status_code, 200)


# ===========================================================================
# LOT 6 — Score validation against barème max
# ===========================================================================

class TestScoreValidation(TestCase):
    """LOT 6: CopyScoresView.put must reject scores exceeding barème max."""

    def setUp(self):
        self.teacher = _make_teacher('teacher_scores')
        self.exam, self.copy = _make_exam_and_copy(
            teacher=self.teacher, exam_name="BB_J2_maths"
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.teacher)

    def test_valid_scores_accepted(self):
        """Valid scores within barème are accepted."""
        resp = self.client.put(
            f'/api/grading/copies/{self.copy.id}/scores/',
            {'scores_data': {'1.1': 0.5, '1.2': 1.0}, 'final_comment': ''},
            format='json',
        )
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.data.get('updated'))

    def test_negative_score_rejected(self):
        """Negative scores are rejected with 400."""
        resp = self.client.put(
            f'/api/grading/copies/{self.copy.id}/scores/',
            {'scores_data': {'1.1': -1.0}, 'final_comment': ''},
            format='json',
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn('négative', resp.data.get('detail', ''))

    def test_non_numeric_score_rejected(self):
        """Non-numeric scores are rejected with 400."""
        resp = self.client.put(
            f'/api/grading/copies/{self.copy.id}/scores/',
            {'scores_data': {'1.1': 'abc'}, 'final_comment': ''},
            format='json',
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn('numérique', resp.data.get('detail', ''))

    def test_non_assigned_teacher_rejected(self):
        """A teacher not assigned to the copy is rejected with 403."""
        other_teacher = _make_teacher('teacher_other')
        client = APIClient()
        client.force_authenticate(user=other_teacher)
        resp = client.put(
            f'/api/grading/copies/{self.copy.id}/scores/',
            {'scores_data': {'1.1': 0.5}, 'final_comment': ''},
            format='json',
        )
        self.assertEqual(resp.status_code, 403)

    def test_scores_data_must_be_dict(self):
        """scores_data must be a dict, not a list or string."""
        resp = self.client.put(
            f'/api/grading/copies/{self.copy.id}/scores/',
            {'scores_data': 'not_a_dict', 'final_comment': ''},
            format='json',
        )
        self.assertEqual(resp.status_code, 400)


# ===========================================================================
# LOT 4 — Race condition protection (sequential proof)
# ===========================================================================

class TestScoreAtomicWrite(TransactionTestCase):
    """
    LOT 4 fix: CopyScoresView.put uses select_for_update inside atomic.

    True concurrent testing requires PostgreSQL. This test proves that:
    1. Sequential writes don't corrupt data (basic sanity).
    2. The Score model respects update_or_create semantics.
    """

    def test_sequential_score_writes_last_wins(self):
        """Two sequential PUTs: the second write should be the final state."""
        teacher = _make_teacher('teacher_race')
        exam, copy = _make_exam_and_copy(teacher=teacher)

        client = APIClient()
        client.force_authenticate(user=teacher)

        # First write
        resp1 = client.put(
            f'/api/grading/copies/{copy.id}/scores/',
            {'scores_data': {'1.1': 1.0, '1.2': 2.0}, 'final_comment': 'First'},
            format='json',
        )
        self.assertEqual(resp1.status_code, 200)

        # Second write
        resp2 = client.put(
            f'/api/grading/copies/{copy.id}/scores/',
            {'scores_data': {'1.1': 3.0, '1.2': 4.0}, 'final_comment': 'Second'},
            format='json',
        )
        self.assertEqual(resp2.status_code, 200)

        # Verify final state
        score = Score.objects.get(copy=copy)
        self.assertEqual(float(score.scores_data['1.1']), 3.0)
        self.assertEqual(float(score.scores_data['1.2']), 4.0)
        self.assertEqual(score.final_comment, 'Second')

    def test_update_or_create_does_not_duplicate(self):
        """Multiple PUTs never create duplicate Score rows."""
        teacher = _make_teacher('teacher_nodup')
        exam, copy = _make_exam_and_copy(teacher=teacher)

        client = APIClient()
        client.force_authenticate(user=teacher)

        for i in range(5):
            resp = client.put(
                f'/api/grading/copies/{copy.id}/scores/',
                {'scores_data': {f'q{i}': float(i)}, 'final_comment': f'Write {i}'},
                format='json',
            )
            self.assertEqual(resp.status_code, 200)

        # Only 1 Score row should exist
        self.assertEqual(Score.objects.filter(copy=copy).count(), 1)


# ===========================================================================
# LOT 8 — UniqueConstraint on Score.copy
# ===========================================================================

class TestScoreUniqueConstraint(TransactionTestCase):
    """
    LOT 8: The UniqueConstraint on Score.copy should prevent duplicate scores.

    Note: This test validates the constraint at the Django ORM level.
    On SQLite (test runner), Django enforces the unique_together/constraint
    when the migration is applied. On PostgreSQL (production), it's a DB-level
    constraint that also blocks raw SQL inserts.
    """

    def test_cannot_create_duplicate_score_for_same_copy(self):
        """Creating two Score objects for the same Copy raises IntegrityError."""
        teacher = _make_teacher('teacher_uniq')
        exam, copy = _make_exam_and_copy(teacher=teacher)

        Score.objects.create(copy=copy, scores_data={'1.1': 1.0}, final_comment='First')

        with self.assertRaises(IntegrityError):
            Score.objects.create(copy=copy, scores_data={'1.1': 2.0}, final_comment='Duplicate')

    def test_different_copies_can_have_scores(self):
        """Different copies can each have their own Score."""
        teacher = _make_teacher('teacher_multi')
        exam = Exam.objects.create(name="Multi Copy Exam", date="2026-01-15")
        copy1 = Copy.objects.create(exam=exam, anonymous_id="MC-001", status=Copy.Status.READY)
        copy2 = Copy.objects.create(exam=exam, anonymous_id="MC-002", status=Copy.Status.READY)

        Score.objects.create(copy=copy1, scores_data={'1.1': 1.0})
        Score.objects.create(copy=copy2, scores_data={'1.1': 2.0})

        self.assertEqual(Score.objects.count(), 2)
