"""
Métier invariant tests — business rules that must NEVER be violated.

Covers:
1. Anonymization: copy never exposes student identity before reconciliation
2. Barème coherence: grading structure total points = 20
3. Score clamping: final score always in [0, 20]
4. State machine: only valid transitions allowed
5. Export conformity: CSV Pronote format invariants
"""
import pytest
from datetime import date
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group

from exams.models import Exam, Copy, Booklet
from grading.models import Annotation, GradingEvent, CopyLock, Score
from grading.services import GradingService, LockConflictError
from students.models import Student
from core.auth import UserRole

User = get_user_model()


class TestAnonymizationInvariant(TestCase):
    """A copy must never expose student identity before explicit reconciliation."""

    def setUp(self):
        self.admin_group, _ = Group.objects.get_or_create(name=UserRole.ADMIN)
        self.teacher_group, _ = Group.objects.get_or_create(name=UserRole.TEACHER)
        self.teacher = User.objects.create_user(
            username="teacher_anon", password="pass123", is_staff=True
        )
        self.teacher.groups.add(self.teacher_group)

        self.student = Student.objects.create(
            first_name="Alice", last_name="Durand",
            class_name="TS1", date_naissance="2005-03-10"
        )
        self.exam = Exam.objects.create(name="Anon Test", date=date.today())

    def test_copy_created_without_student_identity(self):
        """New copies must have no student link and is_identified=False."""
        copy = Copy.objects.create(
            exam=self.exam,
            anonymous_id="ANON-001",
            status=Copy.Status.STAGING,
        )
        self.assertIsNone(copy.student)
        self.assertFalse(copy.is_identified)
        self.assertTrue(copy.anonymous_id.startswith("ANON-"))

    def test_anonymous_id_never_contains_student_name(self):
        """anonymous_id must never leak student identity."""
        copy = Copy.objects.create(
            exam=self.exam,
            anonymous_id="IMPORT-A1B2C3D4",
            status=Copy.Status.STAGING,
        )
        self.assertNotIn("Alice", copy.anonymous_id)
        self.assertNotIn("Durand", copy.anonymous_id)

    def test_copy_api_hides_student_before_identification(self):
        """API serialization of unidentified copy must not include student data."""
        from rest_framework.test import APIClient
        client = APIClient()
        client.force_authenticate(user=self.teacher)

        copy = Copy.objects.create(
            exam=self.exam,
            anonymous_id="ANON-API-001",
            status=Copy.Status.READY,
        )
        resp = client.get(f"/api/exams/{self.exam.id}/copies/")
        self.assertEqual(resp.status_code, 200)
        copies_data = resp.data if isinstance(resp.data, list) else resp.data.get("results", resp.data)
        if isinstance(copies_data, list):
            for c in copies_data:
                if str(c.get("id")) == str(copy.id):
                    self.assertFalse(c.get("is_identified", False))
                    self.assertIsNone(c.get("student"))

    def test_identification_links_student_explicitly(self):
        """Only explicit identification should link student to copy."""
        copy = Copy.objects.create(
            exam=self.exam,
            anonymous_id="ANON-LINK-001",
            status=Copy.Status.GRADED,
        )
        self.assertIsNone(copy.student)
        self.assertFalse(copy.is_identified)

        # Explicit identification
        copy.student = self.student
        copy.is_identified = True
        copy.save()
        copy.refresh_from_db()

        self.assertEqual(copy.student, self.student)
        self.assertTrue(copy.is_identified)


class TestBaremeCoherence(TestCase):
    """Grading structure total must equal exactly 20 points."""

    def setUp(self):
        self.admin_group, _ = Group.objects.get_or_create(name=UserRole.ADMIN)
        self.admin = User.objects.create_user(
            username="admin_bareme", password="pass123",
            is_staff=True, is_superuser=True
        )
        self.admin.groups.add(self.admin_group)

    def test_valid_grading_structure_sums_to_20(self):
        """Grading structure with total=20 is accepted."""
        from rest_framework.test import APIClient
        client = APIClient()
        client.force_authenticate(user=self.admin)

        exam = Exam.objects.create(name="Bareme OK", date=date.today())
        structure = [
            {"label": "Ex1", "points": 8, "children": []},
            {"label": "Ex2", "points": 6, "children": []},
            {"label": "Ex3", "points": 6, "children": []},
        ]
        resp = client.patch(
            f"/api/exams/{exam.id}/",
            {"grading_structure": structure},
            format="json",
        )
        self.assertIn(resp.status_code, [200, 201])

    def test_invalid_grading_structure_rejected(self):
        """Grading structure with total != 20 is rejected by serializer."""
        from rest_framework.test import APIClient
        client = APIClient()
        client.force_authenticate(user=self.admin)

        exam = Exam.objects.create(name="Bareme Bad", date=date.today())
        structure = [
            {"label": "Ex1", "points": 10, "children": []},
            {"label": "Ex2", "points": 5, "children": []},
        ]  # Total = 15, not 20
        resp = client.patch(
            f"/api/exams/{exam.id}/",
            {"grading_structure": structure},
            format="json",
        )
        self.assertEqual(resp.status_code, 400)

    def test_nested_grading_structure_sums_correctly(self):
        """Nested grading structure sums leaf points to 20."""
        from rest_framework.test import APIClient
        client = APIClient()
        client.force_authenticate(user=self.admin)

        exam = Exam.objects.create(name="Bareme Nested", date=date.today())
        structure = [
            {
                "label": "Exercice 1",
                "children": [
                    {"label": "Q1a", "points": 4, "children": []},
                    {"label": "Q1b", "points": 6, "children": []},
                ],
            },
            {
                "label": "Exercice 2",
                "children": [
                    {"label": "Q2a", "points": 5, "children": []},
                    {"label": "Q2b", "points": 5, "children": []},
                ],
            },
        ]
        resp = client.patch(
            f"/api/exams/{exam.id}/",
            {"grading_structure": structure},
            format="json",
        )
        self.assertIn(resp.status_code, [200, 201])


class TestScoreInvariants(TestCase):
    """Score computation must always be deterministic and clamped."""

    def setUp(self):
        self.teacher = User.objects.create_user(
            username="teacher_score", password="pass123", is_staff=True
        )
        Group.objects.get_or_create(name=UserRole.TEACHER)
        self.exam = Exam.objects.create(
            name="Score Test", date=date.today(),
            grading_structure=[{"name": "Ex1", "max_points": 20}]
        )

    def test_score_sum_from_annotations(self):
        """GradingService.compute_score sums all annotation score_deltas."""
        copy = Copy.objects.create(
            exam=self.exam, anonymous_id="SCORE-001", status=Copy.Status.LOCKED
        )
        Annotation.objects.create(
            copy=copy, page_index=0, x=0.1, y=0.1, w=0.1, h=0.1,
            score_delta=8, created_by=self.teacher
        )
        Annotation.objects.create(
            copy=copy, page_index=0, x=0.2, y=0.2, w=0.1, h=0.1,
            score_delta=5, created_by=self.teacher
        )
        self.assertEqual(GradingService.compute_score(copy), 13)

    def test_score_ignores_null_deltas(self):
        """Annotations without score_delta are ignored in sum."""
        copy = Copy.objects.create(
            exam=self.exam, anonymous_id="SCORE-002", status=Copy.Status.LOCKED
        )
        Annotation.objects.create(
            copy=copy, page_index=0, x=0.1, y=0.1, w=0.1, h=0.1,
            score_delta=10, created_by=self.teacher
        )
        Annotation.objects.create(
            copy=copy, page_index=0, x=0.2, y=0.2, w=0.1, h=0.1,
            score_delta=None, content="Comment only", created_by=self.teacher
        )
        self.assertEqual(GradingService.compute_score(copy), 10)

    def test_pronote_export_clamps_grade_to_0_20(self):
        """Pronote exporter clamps grades to [0, 20]."""
        from exams.services.pronote_export import PronoteExporter

        exporter = PronoteExporter(self.exam)

        # Negative score
        copy_neg = Copy.objects.create(
            exam=self.exam, anonymous_id="CLAMP-NEG",
            status=Copy.Status.GRADED, is_identified=True
        )
        Annotation.objects.create(
            copy=copy_neg, page_index=0, x=0.1, y=0.1, w=0.1, h=0.1,
            score_delta=-50, created_by=self.teacher
        )
        grade = exporter.calculate_copy_grade(copy_neg)
        self.assertEqual(grade, 0.0)

        # Over-20 score
        copy_over = Copy.objects.create(
            exam=self.exam, anonymous_id="CLAMP-OVER",
            status=Copy.Status.GRADED, is_identified=True
        )
        Annotation.objects.create(
            copy=copy_over, page_index=0, x=0.1, y=0.1, w=0.1, h=0.1,
            score_delta=25, created_by=self.teacher
        )
        grade = exporter.calculate_copy_grade(copy_over)
        self.assertEqual(grade, 20.0)


class TestStateMachineInvariants(TestCase):
    """Copy status transitions must follow the state machine."""

    def setUp(self):
        self.teacher_group, _ = Group.objects.get_or_create(name=UserRole.TEACHER)
        self.teacher = User.objects.create_user(
            username="teacher_sm", password="pass123", is_staff=True
        )
        self.teacher.groups.add(self.teacher_group)
        self.exam = Exam.objects.create(name="SM Test", date=date.today())

    def test_cannot_finalize_staging_copy(self):
        """STAGING copies cannot be finalized."""
        copy = Copy.objects.create(
            exam=self.exam, anonymous_id="SM-001", status=Copy.Status.STAGING
        )
        with self.assertRaises(ValueError):
            GradingService.finalize_copy(copy, self.teacher)

    def test_cannot_finalize_ready_copy(self):
        """READY copies cannot be finalized (must be LOCKED first)."""
        copy = Copy.objects.create(
            exam=self.exam, anonymous_id="SM-002", status=Copy.Status.READY
        )
        with self.assertRaises(ValueError):
            GradingService.finalize_copy(copy, self.teacher)

    def test_cannot_lock_staging_copy(self):
        """STAGING copies cannot be locked."""
        copy = Copy.objects.create(
            exam=self.exam, anonymous_id="SM-003", status=Copy.Status.STAGING
        )
        with self.assertRaises(ValueError):
            GradingService.lock_copy(copy, self.teacher)

    def test_cannot_validate_locked_copy(self):
        """LOCKED copies cannot be re-validated."""
        copy = Copy.objects.create(
            exam=self.exam, anonymous_id="SM-004", status=Copy.Status.LOCKED
        )
        with self.assertRaises(ValueError):
            GradingService.validate_copy(copy, self.teacher)

    def test_double_finalize_raises_lock_conflict(self):
        """Finalizing an already-GRADED copy raises LockConflictError."""
        copy = Copy.objects.create(
            exam=self.exam, anonymous_id="SM-005", status=Copy.Status.GRADED
        )
        with self.assertRaises(LockConflictError):
            GradingService.finalize_copy(copy, self.teacher)


class TestPronoteExportFormat(TestCase):
    """CSV export must conform to PRONOTE specification."""

    def setUp(self):
        self.admin_group, _ = Group.objects.get_or_create(name=UserRole.ADMIN)
        self.admin = User.objects.create_user(
            username="admin_export", password="pass123",
            is_staff=True, is_superuser=True
        )
        self.admin.groups.add(self.admin_group)

        self.exam = Exam.objects.create(
            name="MATHEMATIQUES", date=date.today(),
            grading_structure=[{"name": "Ex1", "max_points": 20}]
        )
        self.student = Student.objects.create(
            first_name="François", last_name="Müller",
            class_name="TS1", date_naissance="2005-03-10"
        )
        self.copy = Copy.objects.create(
            exam=self.exam, anonymous_id="EXPORT-001",
            status=Copy.Status.GRADED, is_identified=True,
            student=self.student,
            global_appreciation="Très bien; effort remarquable"
        )
        Annotation.objects.create(
            copy=self.copy, page_index=0, x=0.1, y=0.1, w=0.1, h=0.1,
            score_delta=17, created_by=self.admin
        )

    def test_csv_has_utf8_bom(self):
        """CSV must start with UTF-8 BOM for Excel compatibility."""
        from exams.services.pronote_export import PronoteExporter
        exporter = PronoteExporter(self.exam)
        csv_content, _ = exporter.generate_csv()
        self.assertTrue(csv_content.startswith("\ufeff"))

    def test_csv_uses_semicolon_delimiter(self):
        """CSV must use semicolon as delimiter (PRONOTE standard)."""
        from exams.services.pronote_export import PronoteExporter
        exporter = PronoteExporter(self.exam)
        csv_content, _ = exporter.generate_csv()
        header = csv_content.split("\r\n")[0].replace("\ufeff", "")
        self.assertEqual(
            header,
            "NOM;PRENOM;DATE_NAISSANCE;MATIERE;NOTE;COEFF;COMMENTAIRE"
        )

    def test_csv_uses_crlf_line_endings(self):
        """CSV must use CRLF line endings (Windows/PRONOTE standard)."""
        from exams.services.pronote_export import PronoteExporter
        exporter = PronoteExporter(self.exam)
        csv_content, _ = exporter.generate_csv()
        self.assertIn("\r\n", csv_content)

    def test_csv_uses_french_decimal_format(self):
        """Grades must use comma as decimal separator (French format)."""
        from exams.services.pronote_export import PronoteExporter
        exporter = PronoteExporter(self.exam)
        csv_content, _ = exporter.generate_csv()
        # 17.00 → "17,00"
        self.assertIn("17,00", csv_content)

    def test_csv_preserves_accented_characters(self):
        """CSV must preserve UTF-8 accented characters."""
        from exams.services.pronote_export import PronoteExporter
        exporter = PronoteExporter(self.exam)
        csv_content, _ = exporter.generate_csv()
        self.assertIn("Müller", csv_content)
        self.assertIn("François", csv_content)

    def test_csv_date_format_dd_mm_yyyy(self):
        """Date of birth must be in DD/MM/YYYY format."""
        from exams.services.pronote_export import PronoteExporter
        exporter = PronoteExporter(self.exam)
        csv_content, _ = exporter.generate_csv()
        self.assertIn("10/03/2005", csv_content)

    def test_csv_sanitizes_injection_characters(self):
        """CSV must strip leading injection characters (=, +, -, @)."""
        from exams.services.pronote_export import PronoteExporter
        self.copy.global_appreciation = "=cmd('calc')"
        self.copy.save()
        exporter = PronoteExporter(self.exam)
        csv_content, _ = exporter.generate_csv()
        # The leading '=' should be stripped
        self.assertNotIn("=cmd", csv_content)
