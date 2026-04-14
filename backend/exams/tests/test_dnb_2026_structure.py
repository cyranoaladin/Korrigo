from django.core.management import call_command
from django.test import TestCase

from exams.dnb_2026_structure import build_dnb_2026_grading_structure
from exams.grading_utils import build_q_max, extract_leaf_questions
from exams.models import Exam
from exams.score_constraints import Q_MAX_BY_EXAM


class TestDnb2026Structure(TestCase):
    def test_canonical_structure_matches_fallback_constraints(self):
        structure = build_dnb_2026_grading_structure()

        leaves = extract_leaf_questions(structure)
        q_max = build_q_max(structure)
        explicit_q_max = {leaf["id"]: q_max[leaf["id"]] for leaf in leaves}

        self.assertEqual(len(leaves), 22)
        self.assertEqual(sum(leaf["points"] for leaf in leaves), 20.0)
        self.assertEqual(explicit_q_max, Q_MAX_BY_EXAM["DNB_2026"])

    def test_backfill_command_populates_only_missing_structure(self):
        exam = Exam.objects.create(name="DNB_2026", grading_structure=[])

        call_command("backfill_dnb_grading_structure")

        exam.refresh_from_db()
        self.assertEqual(exam.grading_structure, build_dnb_2026_grading_structure())

    def test_backfill_command_is_noop_when_structure_already_exists(self):
        existing_structure = [{"id": "custom", "label": "Custom", "points": 20}]
        exam = Exam.objects.create(name="DNB_2026", grading_structure=existing_structure)

        call_command("backfill_dnb_grading_structure")

        exam.refresh_from_db()
        self.assertEqual(exam.grading_structure, existing_structure)
