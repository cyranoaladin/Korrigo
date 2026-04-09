"""
Regression tests for LOT 1 & LOT 2 audit fixes.
Covers: DEFAULT_PASSWORD, CSRF logout, email fallbacks, anonymous_id uniqueness,
        __init__ removal, Score.scores_data validation, Exam timestamps.
"""
import os
from datetime import date
from unittest.mock import patch

from django.conf import settings
from django.contrib.auth.models import User, Group
from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings
from django.utils import timezone

from exams.models import Exam, Copy
from grading.models import Annotation, Score, validate_scores_data
from students.models import Student


class TestDefaultPasswordSetting(TestCase):
    """LOT 1.1: DEFAULT_PASSWORD is configurable and not trivial in prod."""

    def test_default_password_exists_in_settings(self):
        self.assertTrue(hasattr(settings, 'DEFAULT_PASSWORD'))

    def test_default_password_not_empty_in_dev(self):
        # In dev/test mode DEFAULT_PASSWORD should have a usable value
        self.assertTrue(len(settings.DEFAULT_PASSWORD) > 0)

    def test_trivial_passwords_blocklist_in_prod_module(self):
        """settings_prod.py source contains a blocklist of trivial passwords."""
        import importlib.util
        spec = importlib.util.find_spec('core.settings_prod')
        with open(spec.origin) as f:
            source = f.read()
        self.assertIn("'passe123'", source)
        self.assertIn('_TRIVIAL_PASSWORDS', source)


class TestStudentLogoutPermission(TestCase):
    """LOT 1.3: StudentLogoutView requires IsStudent, not AllowAny."""

    def test_logout_requires_authentication(self):
        from students.views import StudentLogoutView
        from exams.permissions import IsStudent
        perms = StudentLogoutView.permission_classes
        self.assertIn(IsStudent, perms)

    def test_unauthenticated_logout_rejected(self):
        response = self.client.post('/api/students/logout/')
        self.assertIn(response.status_code, [401, 403])


class TestEmailFallbacks(TestCase):
    """LOT 1.4: No example.com fallbacks in email settings."""

    def test_email_host_user_not_example_dot_com(self):
        val = getattr(settings, 'EMAIL_HOST_USER', '') or ''
        self.assertNotIn('example.com', val)

    def test_default_from_email_not_example_dot_com(self):
        val = getattr(settings, 'DEFAULT_FROM_EMAIL', '') or ''
        self.assertNotIn('example.com', val)


class TestAnonymousIdUniquePerExam(TestCase):
    """LOT 2.1: Copy.anonymous_id is unique per exam, not globally."""

    def setUp(self):
        self.exam1 = Exam.objects.create(name='Exam A', date=date(2024, 1, 15))
        self.exam2 = Exam.objects.create(name='Exam B', date=date(2024, 1, 16))

    def test_same_anonymous_id_different_exams_ok(self):
        Copy.objects.create(exam=self.exam1, anonymous_id='CODE-001')
        # Should NOT raise — different exam
        copy2 = Copy.objects.create(exam=self.exam2, anonymous_id='CODE-001')
        self.assertEqual(copy2.anonymous_id, 'CODE-001')

    def test_duplicate_anonymous_id_same_exam_rejected(self):
        from django.db import IntegrityError
        Copy.objects.create(exam=self.exam1, anonymous_id='CODE-DUP')
        with self.assertRaises(IntegrityError):
            Copy.objects.create(exam=self.exam1, anonymous_id='CODE-DUP')


class TestInitOverridesRemoved(TestCase):
    """LOT 2.2: Exam and Annotation no longer have __init__ overrides."""

    def test_exam_has_no_custom_init(self):
        # Exam.__init__ should be the default Model.__init__ (no override)
        self.assertNotIn('__init__', Exam.__dict__)

    def test_exam_rejects_legacy_title_kwarg(self):
        """Legacy 'title' kwarg should raise TypeError (no alias anymore)."""
        with self.assertRaises(TypeError):
            Exam(title='Legacy Name', date=date(2024, 1, 1))

    def test_exam_default_date(self):
        """Exam without date uses field default (timezone.now)."""
        exam = Exam(name='Test')
        self.assertIsNotNone(exam.date)

    def test_annotation_default_w_h(self):
        """Annotation w/h fields have default=0.1."""
        self.assertEqual(Annotation._meta.get_field('w').default, 0.1)
        self.assertEqual(Annotation._meta.get_field('h').default, 0.1)


class TestScoresDataValidator(TestCase):
    """LOT 2.3: Score.scores_data is validated as {str: number>=0}."""

    def test_valid_scores_data(self):
        data = {'q1': 2.5, 'q2': 0, 'q3': 1}
        validate_scores_data(data)  # Should not raise

    def test_invalid_not_dict(self):
        with self.assertRaises(ValidationError):
            validate_scores_data([1, 2, 3])

    def test_invalid_non_string_key(self):
        with self.assertRaises(ValidationError):
            validate_scores_data({1: 2.0})

    def test_invalid_non_numeric_value(self):
        with self.assertRaises(ValidationError):
            validate_scores_data({'q1': 'bad'})

    def test_invalid_negative_score(self):
        with self.assertRaises(ValidationError):
            validate_scores_data({'q1': -1.0})

    def test_empty_dict_valid(self):
        validate_scores_data({})  # Edge case: no questions scored yet


class TestExamTimestamps(TestCase):
    """LOT 2.4: Exam.created_at is NOT NULL."""

    def test_created_at_not_nullable(self):
        field = Exam._meta.get_field('created_at')
        self.assertFalse(field.null)

    def test_updated_at_not_nullable(self):
        field = Exam._meta.get_field('updated_at')
        self.assertFalse(field.null)

    def test_new_exam_gets_timestamps(self):
        exam = Exam.objects.create(name='Ts Test', date=date(2024, 6, 1))
        self.assertIsNotNone(exam.created_at)
        self.assertIsNotNone(exam.updated_at)


class TestNoPasse123InCode(TestCase):
    """LOT 1.1: Verify no hardcoded 'passe123' leaks into runtime."""

    def test_student_views_uses_settings(self):
        """StudentLoginView should reference settings.DEFAULT_PASSWORD, not literal."""
        import inspect
        from students.views import StudentLoginView
        source = inspect.getsource(StudentLoginView)
        self.assertNotIn("'passe123'", source)
        self.assertIn('settings.DEFAULT_PASSWORD', source)

    def test_student_change_password_uses_settings(self):
        import inspect
        from students.views import StudentChangePasswordView
        source = inspect.getsource(StudentChangePasswordView)
        self.assertNotIn("'passe123'", source)
