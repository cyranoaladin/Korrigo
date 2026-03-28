"""
Regression tests for dashboard feature flags (A2 / A3 / A4):
  - /me/ returns assigned_exam_type_codes for correctors
  - show_jury_report_bac_blanc is True only for correctors assigned to BBM2026 copies
  - show_questionnaire is True only for laroussi.laroussi@ert.tn
  - JuryReportListView scopes to assigned exam types for non-admins
  - JuryReportListView accepts ?exam_type_code= filter
"""
import uuid
from django.test import TestCase
from django.contrib.auth.models import User, Group
from rest_framework.test import APIClient
from core.auth import UserRole, create_user_roles
from exams.models import ExamType, Exam
from grading.models import Copy


def _make_exam_type(code, name):
    return ExamType.objects.get_or_create(
        code=code,
        defaults={'name': name, 'color': '#000000', 'icon': 'book-open'},
    )[0]


def _make_exam(exam_type):
    import datetime
    return Exam.objects.create(
        name=f"Examen {exam_type.code}",
        date=datetime.date.today(),
        exam_type=exam_type,
    )


def _make_copy(exam, corrector):
    return Copy.objects.create(
        exam=exam,
        anonymous_id=f"ANON-{uuid.uuid4().hex[:6].upper()}",
        assigned_corrector=corrector,
    )


class TestMeFeatureFlags(TestCase):
    """Backend feature flags in /me/ response."""

    def setUp(self):
        create_user_roles()
        teacher_group = Group.objects.get(name=UserRole.TEACHER)

        self.bbm = _make_exam_type('BBM2026', 'BAC BLANC MATHS 2026')
        self.dnb = _make_exam_type('DNBM2026', 'DNB BLANC MATHS 2026')

        bbm_exam = _make_exam(self.bbm)
        dnb_exam = _make_exam(self.dnb)

        # BBM corrector
        self.bbm_corrector = User.objects.create_user('bbm_corrector', 'bbm@test.fr', 'pw123456')
        self.bbm_corrector.groups.add(teacher_group)
        _make_copy(bbm_exam, self.bbm_corrector)

        # DNB corrector
        self.dnb_corrector = User.objects.create_user('dnb_corrector', 'dnb@test.fr', 'pw123456')
        self.dnb_corrector.groups.add(teacher_group)
        _make_copy(dnb_exam, self.dnb_corrector)

        # Questionnaire coordinator
        self.laroussi = User.objects.create_user(
            'laroussi.laroussi@ert.tn', 'laroussi.laroussi@ert.tn', 'pw123456'
        )
        self.laroussi.email = 'laroussi.laroussi@ert.tn'
        self.laroussi.save()
        self.laroussi.groups.add(teacher_group)
        _make_copy(bbm_exam, self.laroussi)

        self.client = APIClient()

    def _me(self, user):
        self.client.force_authenticate(user=user)
        resp = self.client.get('/api/me/')
        self.assertEqual(resp.status_code, 200)
        return resp.data

    def test_bbm_corrector_has_bbm_code(self):
        data = self._me(self.bbm_corrector)
        self.assertIn('BBM2026', data['assigned_exam_type_codes'])
        self.assertNotIn('DNBM2026', data['assigned_exam_type_codes'])

    def test_bbm_corrector_sees_jury_report(self):
        data = self._me(self.bbm_corrector)
        self.assertTrue(data['features']['show_jury_report_bac_blanc'])

    def test_dnb_corrector_does_not_see_bbm_jury_report(self):
        data = self._me(self.dnb_corrector)
        self.assertFalse(data['features']['show_jury_report_bac_blanc'])

    def test_only_laroussi_sees_questionnaire(self):
        laroussi_data = self._me(self.laroussi)
        bbm_data = self._me(self.bbm_corrector)
        self.assertTrue(laroussi_data['features']['show_questionnaire'])
        self.assertFalse(bbm_data['features']['show_questionnaire'])

    def test_features_key_present_for_all_users(self):
        for user in [self.bbm_corrector, self.dnb_corrector, self.laroussi]:
            data = self._me(user)
            self.assertIn('features', data)
            self.assertIn('show_jury_report_bac_blanc', data['features'])
            self.assertIn('show_questionnaire', data['features'])


class TestJuryReportScoping(TestCase):
    """JuryReportListView must scope to assigned exam types for non-admins."""

    def setUp(self):
        create_user_roles()
        teacher_group = Group.objects.get(name=UserRole.TEACHER)
        admin_group = Group.objects.get(name=UserRole.ADMIN)

        from exams.models import JuryReport

        self.bbm = _make_exam_type('BBM2026T', 'BAC BLANC MATHS 2026 (test)')
        self.dnb = _make_exam_type('DNBM2026T', 'DNB BLANC MATHS 2026 (test)')

        bbm_exam = _make_exam(self.bbm)

        # BBM corrector
        self.corrector = User.objects.create_user('scope_corrector', 'sc@test.fr', 'pw123456')
        self.corrector.groups.add(teacher_group)
        _make_copy(bbm_exam, self.corrector)

        # Admin
        self.admin = User.objects.create_user('scope_admin', 'sa@test.fr', 'pw123456')
        self.admin.groups.add(admin_group)

        created_by = self.admin

        # Published BBM report
        self.bbm_report = JuryReport.objects.create(
            exam_type=self.bbm,
            title='Rapport BBM',
            content='...',
            is_published=True,
            created_by=created_by,
        )
        # Published DNB report
        self.dnb_report = JuryReport.objects.create(
            exam_type=self.dnb,
            title='Rapport DNB',
            content='...',
            is_published=True,
            created_by=created_by,
        )
        # Unpublished BBM report
        self.bbm_draft = JuryReport.objects.create(
            exam_type=self.bbm,
            title='Rapport BBM brouillon',
            content='...',
            is_published=False,
            created_by=created_by,
        )

        self.client = APIClient()

    @staticmethod
    def _items(resp):
        """Return the list of report dicts regardless of pagination."""
        data = resp.data
        if isinstance(data, dict) and 'results' in data:
            return data['results']
        return list(data)

    def test_non_admin_sees_only_own_exam_type_published(self):
        self.client.force_authenticate(user=self.corrector)
        resp = self.client.get('/api/exams/reports/')
        self.assertEqual(resp.status_code, 200)
        ids = [str(r['id']) for r in self._items(resp)]
        self.assertIn(str(self.bbm_report.id), ids)
        self.assertNotIn(str(self.dnb_report.id), ids)
        self.assertNotIn(str(self.bbm_draft.id), ids)

    def test_admin_sees_all_reports(self):
        self.client.force_authenticate(user=self.admin)
        resp = self.client.get('/api/exams/reports/')
        self.assertEqual(resp.status_code, 200)
        ids = [str(r['id']) for r in self._items(resp)]
        self.assertIn(str(self.bbm_report.id), ids)
        self.assertIn(str(self.dnb_report.id), ids)
        self.assertIn(str(self.bbm_draft.id), ids)

    def test_exam_type_code_filter(self):
        self.client.force_authenticate(user=self.admin)
        resp = self.client.get('/api/exams/reports/', {'exam_type_code': 'BBM2026T'})
        self.assertEqual(resp.status_code, 200)
        ids = [str(r['id']) for r in self._items(resp)]
        self.assertIn(str(self.bbm_report.id), ids)
        self.assertNotIn(str(self.dnb_report.id), ids)

    def test_response_includes_exam_type_code_field(self):
        self.client.force_authenticate(user=self.admin)
        resp = self.client.get('/api/exams/reports/')
        self.assertEqual(resp.status_code, 200)
        items = self._items(resp)
        if items:
            self.assertIn('exam_type_code', items[0])
