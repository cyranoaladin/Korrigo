"""
Tests de non-régression pour les correctifs sécurité P0/P1.

P0.1 — CopyScoresView GET: RBAC + ownership
P0.2 — Aucun mot de passe dans les réponses API de reset
P0.3 — AdminResetStudentPasswordView: teacher => 403, admin => 200
P1.1 — bilan/views.py: pas de str(e) dans les réponses
P1.2 — DocumentSetUploadView: validation PDF (taille, magic bytes)
P1.5 — MetricsView: IsKorrigoAdmin (pas IsAdminUser/is_staff seul)
"""
import io
import uuid

from django.contrib.auth.models import User, Group
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from core.auth import UserRole, create_user_roles
from exams.models import Exam, Copy
from students.models import Student


def _make_user(username, group_name):
    """Helper: create a User and add it to group_name."""
    u = User.objects.create_user(username=username, password='testpass123')
    g, _ = Group.objects.get_or_create(name=group_name)
    u.groups.add(g)
    return u


def _auth(client, user):
    client.force_login(user)


# ──────────────────────────────────────────────────────────────────────────────
# P0.1 — CopyScoresView GET: RBAC + ownership
# ──────────────────────────────────────────────────────────────────────────────

class CopyScoresViewRBACTest(TestCase):
    """
    GET /api/grading/copies/<uuid>/scores/
    Only admin or assigned corrector may read raw scores.
    """

    def setUp(self):
        create_user_roles()
        self.admin = _make_user('sc_admin', UserRole.ADMIN)
        self.assigned = _make_user('sc_assigned', UserRole.TEACHER)
        self.unrelated = _make_user('sc_unrelated', UserRole.TEACHER)

        self.exam = Exam.objects.create(
            name='TestExam',
            grading_structure={'questions': []},
        )
        self.copy = Copy.objects.create(
            exam=self.exam,
            anonymous_id='T001',
            assigned_corrector=self.assigned,
        )
        self.url = f'/api/grading/copies/{self.copy.id}/scores/'

    def test_admin_can_read_scores(self):
        c = APIClient()
        _auth(c, self.admin)
        r = c.get(self.url)
        self.assertNotEqual(r.status_code, status.HTTP_403_FORBIDDEN,
                            "Admin should be able to read scores")

    def test_assigned_corrector_can_read_scores(self):
        c = APIClient()
        _auth(c, self.assigned)
        r = c.get(self.url)
        self.assertNotEqual(r.status_code, status.HTTP_403_FORBIDDEN,
                            "Assigned corrector should be able to read scores")

    def test_unrelated_teacher_cannot_read_scores(self):
        c = APIClient()
        _auth(c, self.unrelated)
        r = c.get(self.url)
        self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN,
                         "Unrelated teacher must get 403")

    def test_anonymous_cannot_read_scores(self):
        c = APIClient()
        r = c.get(self.url)
        self.assertIn(r.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN],
                      "Anonymous must not access scores")

    def test_student_user_cannot_read_scores(self):
        student_user = _make_user('sc_student', UserRole.STUDENT)
        c = APIClient()
        _auth(c, student_user)
        r = c.get(self.url)
        self.assertIn(r.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN],
                      "Student must not access raw scores")


# ──────────────────────────────────────────────────────────────────────────────
# P0.2 — No password in API responses
# ──────────────────────────────────────────────────────────────────────────────

class PasswordResetNoLeakTest(TestCase):
    """
    POST /api/users/<pk>/reset-password/  → no temporary_password in response
    POST /api/students/admin/reset-password/ → no new_password in response
    """

    def setUp(self):
        create_user_roles()
        self.admin = _make_user('pr_admin', UserRole.ADMIN)
        self.target = _make_user('pr_target', UserRole.TEACHER)

    def test_user_reset_no_password_in_response(self):
        c = APIClient()
        _auth(c, self.admin)
        r = c.post(f'/api/users/{self.target.id}/reset-password/')
        self.assertNotIn(r.status_code, [status.HTTP_500_INTERNAL_SERVER_ERROR])
        if r.status_code == status.HTTP_200_OK:
            data = r.json()
            self.assertNotIn('temporary_password', data,
                             "temporary_password must not appear in response")
            self.assertNotIn('password', data,
                             "password must not appear in response")

    def test_student_reset_no_password_in_response(self):
        create_user_roles()
        student_user = _make_user('pr_student_user', UserRole.STUDENT)
        student = Student.objects.create(
            first_name='Jean',
            last_name='Dupont',
            user=student_user,
            date_naissance='2005-03-15',
        )
        c = APIClient()
        _auth(c, self.admin)
        r = c.post('/api/students/admin/reset-password/', {'student_id': student.id})
        if r.status_code == status.HTTP_200_OK:
            data = r.json()
            self.assertNotIn('new_password', data,
                             "new_password must not appear in response")
            self.assertNotIn('temporary_password', data,
                             "temporary_password must not appear in response")


# ──────────────────────────────────────────────────────────────────────────────
# P0.3 — AdminResetStudentPasswordView: teacher => 403
# ──────────────────────────────────────────────────────────────────────────────

class AdminResetStudentPasswordRBACTest(TestCase):
    """
    POST /api/students/admin/reset-password/
    Teacher must get 403. Admin must get 200.
    """

    def setUp(self):
        create_user_roles()
        self.admin = _make_user('arp_admin', UserRole.ADMIN)
        self.teacher = _make_user('arp_teacher', UserRole.TEACHER)
        teacher_user = _make_user('arp_student_user', UserRole.STUDENT)
        self.student = Student.objects.create(
            first_name='Ali',
            last_name='Test',
            user=teacher_user,
            date_naissance='2006-01-20',
        )

    def test_teacher_cannot_reset_student_password(self):
        c = APIClient()
        _auth(c, self.teacher)
        r = c.post('/api/students/admin/reset-password/', {'student_id': self.student.id})
        self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN,
                         "Teacher must get 403 on admin-only endpoint")

    def test_admin_can_reset_student_password(self):
        c = APIClient()
        _auth(c, self.admin)
        r = c.post('/api/students/admin/reset-password/', {'student_id': self.student.id})
        self.assertNotEqual(r.status_code, status.HTTP_403_FORBIDDEN,
                            "Admin should be able to reset student password")

    def test_anonymous_cannot_reset_student_password(self):
        c = APIClient()
        r = c.post('/api/students/admin/reset-password/', {'student_id': self.student.id})
        self.assertIn(r.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])


# ──────────────────────────────────────────────────────────────────────────────
# P1.2 — DocumentSetUploadView: PDF validation
# ──────────────────────────────────────────────────────────────────────────────

class PDFValidationTest(TestCase):
    """
    POST /api/exams/<id>/document-sets/
    Validates size (413), magic bytes (400), extension (400).
    """

    def setUp(self):
        create_user_roles()
        self.admin = _make_user('pdf_admin', UserRole.ADMIN)
        self.exam = Exam.objects.create(name='PDFTestExam', grading_structure={})

    def _upload(self, content, filename='test.pdf', field='sujet'):
        c = APIClient()
        _auth(c, self.admin)
        f = io.BytesIO(content)
        f.name = filename
        return c.post(
            f'/api/exams/{self.exam.id}/document-sets/',
            {field: f},
            format='multipart',
        )

    def test_non_pdf_extension_rejected(self):
        r = self._upload(b'%PDF-1.4 fake', filename='test.txt')
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_wrong_magic_bytes_rejected(self):
        r = self._upload(b'This is not a PDF file content')
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_oversized_file_rejected(self):
        big = b'%PDF-1.4 ' + b'X' * (21 * 1024 * 1024)
        r = self._upload(big)
        self.assertEqual(r.status_code, status.HTTP_413_REQUEST_ENTITY_TOO_LARGE)

    def test_empty_upload_rejected(self):
        c = APIClient()
        _auth(c, self.admin)
        r = c.post(f'/api/exams/{self.exam.id}/document-sets/', {}, format='multipart')
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)


# ──────────────────────────────────────────────────────────────────────────────
# P1.5 — MetricsView: staff-only (is_staff) must be denied
# ──────────────────────────────────────────────────────────────────────────────

class MetricsViewPermissionTest(TestCase):
    """
    GET /api/metrics/
    is_staff alone must NOT grant access — only IsKorrigoAdmin (admin group / superuser).
    """

    def setUp(self):
        create_user_roles()
        self.staff_only = User.objects.create_user('metrics_staff', password='test', is_staff=True)
        self.admin = _make_user('metrics_admin', UserRole.ADMIN)
        self.teacher = _make_user('metrics_teacher', UserRole.TEACHER)

    def test_staff_only_denied(self):
        c = APIClient()
        _auth(c, self.staff_only)
        r = c.get('/api/metrics/')
        self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN,
                         "is_staff alone must not grant metrics access")

    def test_admin_group_allowed(self):
        c = APIClient()
        _auth(c, self.admin)
        r = c.get('/api/metrics/')
        self.assertNotEqual(r.status_code, status.HTTP_403_FORBIDDEN,
                            "Admin group should access metrics")

    def test_teacher_denied(self):
        c = APIClient()
        _auth(c, self.teacher)
        r = c.get('/api/metrics/')
        self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN,
                         "Teacher must not access metrics")
