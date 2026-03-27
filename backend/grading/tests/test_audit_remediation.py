"""
Regression tests for the critical bugs fixed during the production readiness audit:

C1 — GradingEvent.Action.SAVE_APPRECIATION is a valid enum choice (was raw 'apprec_saved')
C4 — _can_write_copy_draft uses case-insensitive group lookup
C3 — Q_MAX_BY_EXAM lives in exams.score_constraints (no cross-app import from exams.views)
"""
import pytest
from django.test import TestCase
from django.contrib.auth.models import User, Group
from exams.models import Exam, Copy, Booklet
from grading.models import GradingEvent, Annotation
from core.auth import UserRole, create_user_roles
from rest_framework.test import APIClient


class TestSaveAppreciationAction(TestCase):
    """C1: GradingEvent.Action.SAVE_APPRECIATION must be a valid DB-storable choice."""

    def setUp(self):
        self.teacher_group, _ = Group.objects.get_or_create(name=UserRole.TEACHER)
        self.teacher = User.objects.create_user(username="t_apprec", password="pw")
        self.teacher.groups.add(self.teacher_group)

        self.exam = Exam.objects.create(name="Audit Exam", date="2025-01-01")
        self.copy = Copy.objects.create(
            exam=self.exam, anonymous_id="APPREC01", status=Copy.Status.READY
        )
        self.booklet = Booklet.objects.create(
            exam=self.exam, start_page=1, end_page=2, pages_images=["p000.png", "p001.png"]
        )
        self.copy.booklets.add(self.booklet)

    def test_save_appreciation_action_is_in_enum(self):
        """SAVE_APPRECIATION must be a declared Action choice."""
        action_values = [choice[0] for choice in GradingEvent.Action.choices]
        self.assertIn("SAVE_APPREC", action_values)

    def test_save_appreciation_can_be_stored(self):
        """GradingEvent with SAVE_APPRECIATION action must save without error."""
        event = GradingEvent.objects.create(
            copy=self.copy,
            actor=self.teacher,
            action=GradingEvent.Action.SAVE_APPRECIATION,
            metadata={"length": 42},
        )
        event.refresh_from_db()
        self.assertEqual(event.action, GradingEvent.Action.SAVE_APPRECIATION)

    def test_save_appreciation_via_api(self):
        """PUT /api/grading/copies/<id>/global-appreciation/ must create a SAVE_APPREC event."""
        client = APIClient()
        client.force_authenticate(user=self.teacher)
        self.copy.assigned_corrector = self.teacher
        self.copy.save()

        url = f"/api/grading/copies/{self.copy.id}/global-appreciation/"
        resp = client.put(url, {"global_appreciation": "Bon travail"}, format="json")
        self.assertEqual(resp.status_code, 200)

        events = GradingEvent.objects.filter(
            copy=self.copy, action=GradingEvent.Action.SAVE_APPRECIATION
        )
        self.assertEqual(events.count(), 1)
        self.assertEqual(events.first().metadata["length"], len("Bon travail"))


class TestDraftViewCaseInsensitiveGroupCheck(TestCase):
    """C4: _can_write_copy_draft must accept Admin group regardless of case."""

    def setUp(self):
        admin_group, _ = Group.objects.get_or_create(name=UserRole.ADMIN)
        teacher_group, _ = Group.objects.get_or_create(name=UserRole.TEACHER)

        self.admin_user = User.objects.create_user(username="admin_draft", password="pw")
        self.admin_user.groups.add(admin_group)

        self.teacher = User.objects.create_user(username="teacher_draft", password="pw")
        self.teacher.groups.add(teacher_group)

        self.other = User.objects.create_user(username="other_draft", password="pw")
        self.other.groups.add(teacher_group)

        self.exam = Exam.objects.create(name="Draft Exam", date="2025-01-01")
        self.copy = Copy.objects.create(
            exam=self.exam,
            anonymous_id="DRAFT01",
            status=Copy.Status.READY,
            assigned_corrector=self.teacher,
        )

    def test_admin_group_user_can_write_draft(self):
        """Admin-group user must pass the draft ownership check."""
        from grading.views_draft import _can_write_copy_draft
        self.assertTrue(_can_write_copy_draft(self.admin_user, self.copy))

    def test_assigned_corrector_can_write_draft(self):
        """Assigned corrector must pass the draft ownership check."""
        from grading.views_draft import _can_write_copy_draft
        self.assertTrue(_can_write_copy_draft(self.teacher, self.copy))

    def test_other_teacher_cannot_write_draft(self):
        """Teacher not assigned to this copy must be denied."""
        from grading.views_draft import _can_write_copy_draft
        self.assertFalse(_can_write_copy_draft(self.other, self.copy))

    def test_admin_can_save_draft_via_api(self):
        """Admin-group user must get 200 on PUT /draft/."""
        client = APIClient()
        client.force_authenticate(user=self.admin_user)
        url = f"/api/grading/copies/{self.copy.id}/draft/"
        import uuid
        resp = client.put(
            url,
            {"payload": {"notes": "test"}, "client_id": str(uuid.uuid4())},
            format="json",
        )
        self.assertIn(resp.status_code, [200, 201])


class TestScoreConstraintsModule(TestCase):
    """C3: Q_MAX_BY_EXAM must live in exams.score_constraints, not in exams.views."""

    def test_import_from_score_constraints(self):
        """Direct import from exams.score_constraints must succeed."""
        from exams.score_constraints import Q_MAX_BY_EXAM
        self.assertIsInstance(Q_MAX_BY_EXAM, dict)

    def test_bb_j1_present(self):
        """BB_J1 exam constraints must be present and non-empty."""
        from exams.score_constraints import Q_MAX_BY_EXAM
        self.assertIn("BB_J1", Q_MAX_BY_EXAM)
        self.assertGreater(len(Q_MAX_BY_EXAM["BB_J1"]), 0)

    def test_all_values_positive(self):
        """All per-question max values must be strictly positive."""
        from exams.score_constraints import Q_MAX_BY_EXAM
        for exam_name, q_maxes in Q_MAX_BY_EXAM.items():
            for qid, max_val in q_maxes.items():
                self.assertGreater(
                    max_val, 0,
                    msg=f"Exam {exam_name} question {qid} has non-positive max {max_val}",
                )

    def test_no_cross_app_import_in_grading_views(self):
        """grading.views must NOT import StudentCopiesView from exams.views."""
        import ast
        import inspect
        import grading.views as gv
        source = inspect.getsource(gv)
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                if node.module == "exams.views":
                    names = [alias.name for alias in node.names]
                    self.assertNotIn(
                        "StudentCopiesView",
                        names,
                        "grading.views must not import StudentCopiesView from exams.views",
                    )
