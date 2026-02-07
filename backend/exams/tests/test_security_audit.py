"""
Tests de sécurité pour l'anonymisation et les permissions des copies.

Vérifie:
- CopyListView utilise le bon serializer selon le rôle
- CorrectorCopyDetailView vérifie l'assignation
- CorrectorCopiesView retourne un tableau plat (pas de pagination)
- CopyIdentificationView empêche les doublons
- CopyValidationView est accessible via URL
"""
import fitz
from django.test import TestCase, override_settings
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient
from rest_framework import status as http_status
from django.contrib.auth.models import User, Group
from exams.models import Exam, Copy, Booklet
from students.models import Student


def make_pdf():
    doc = fitz.open()
    doc.new_page(width=595, height=842)
    b = doc.tobytes()
    doc.close()
    return b


@override_settings(RATELIMIT_ENABLE=False)
class TestCopyListViewSecurity(TestCase):
    """CopyListView should use CorrectorCopySerializer for teachers."""

    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_superuser('admin', 'a@t.fr', 'admin')
        self.teacher = User.objects.create_user('teacher', 't@t.fr', 'pass', is_staff=False)
        teacher_group = Group.objects.create(name='teacher')
        self.teacher.groups.add(teacher_group)

        self.exam = Exam.objects.create(name='Sec Test', date='2026-01-01')
        self.student = Student.objects.create(full_name='DUPONT Jean', date_of_birth='2006-01-01')
        self.copy = Copy.objects.create(
            exam=self.exam,
            anonymous_id='SEC001',
            status=Copy.Status.READY,
            student=self.student,
            is_identified=True,
            assigned_corrector=self.teacher,
        )
        self.url = reverse('copy-list', kwargs={'exam_id': self.exam.id})

    def test_admin_sees_student_info(self):
        """Admin receives full CopySerializer with student field."""
        self.client.force_login(self.admin)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, http_status.HTTP_200_OK)
        data = response.data
        # Admin serializer: paginated or flat
        copies = data.get('results', data) if isinstance(data, dict) else data
        if isinstance(copies, list) and len(copies) > 0:
            self.assertIn('student', copies[0])
            self.assertIn('is_identified', copies[0])

    def test_teacher_does_not_see_student_info(self):
        """Teacher receives CorrectorCopySerializer WITHOUT student field."""
        self.client.force_login(self.teacher)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, http_status.HTTP_200_OK)
        data = response.data
        copies = data.get('results', data) if isinstance(data, dict) else data
        if isinstance(copies, list) and len(copies) > 0:
            self.assertNotIn('student', copies[0])
            self.assertNotIn('is_identified', copies[0])

    def test_teacher_only_sees_assigned_copies(self):
        """Teacher only sees copies assigned to them."""
        other_teacher = User.objects.create_user('other_teacher', 'ot@t.fr', 'pass')
        teacher_group = Group.objects.get(name='teacher')
        other_teacher.groups.add(teacher_group)

        Copy.objects.create(
            exam=self.exam,
            anonymous_id='SEC002',
            status=Copy.Status.READY,
            assigned_corrector=other_teacher,
        )

        self.client.force_login(self.teacher)
        response = self.client.get(self.url)
        data = response.data
        copies = data.get('results', data) if isinstance(data, dict) else data
        self.assertEqual(len(copies), 1)
        self.assertEqual(copies[0]['anonymous_id'], 'SEC001')


@override_settings(RATELIMIT_ENABLE=False)
class TestCorrectorCopyDetailSecurity(TestCase):
    """CorrectorCopyDetailView should enforce object-level permissions."""

    def setUp(self):
        self.client = APIClient()
        teacher_group, _ = Group.objects.get_or_create(name='teacher')
        self.teacher1 = User.objects.create_user('t1', 't1@t.fr', 'pass')
        self.teacher1.groups.add(teacher_group)
        self.teacher2 = User.objects.create_user('t2', 't2@t.fr', 'pass')
        self.teacher2.groups.add(teacher_group)

        self.exam = Exam.objects.create(name='Detail Sec', date='2026-01-01')
        self.copy = Copy.objects.create(
            exam=self.exam,
            anonymous_id='DET001',
            status=Copy.Status.READY,
            assigned_corrector=self.teacher1,
        )

    def test_assigned_teacher_can_access(self):
        self.client.force_login(self.teacher1)
        url = reverse('corrector-copy-detail', kwargs={'id': self.copy.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, http_status.HTTP_200_OK)

    def test_other_teacher_cannot_access(self):
        self.client.force_login(self.teacher2)
        url = reverse('corrector-copy-detail', kwargs={'id': self.copy.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, http_status.HTTP_403_FORBIDDEN)

    def test_admin_can_access_any_copy(self):
        admin = User.objects.create_superuser('admin2', 'a2@t.fr', 'admin')
        self.client.force_login(admin)
        url = reverse('corrector-copy-detail', kwargs={'id': self.copy.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, http_status.HTTP_200_OK)


@override_settings(RATELIMIT_ENABLE=False)
class TestCorrectorCopiesNoPagination(TestCase):
    """CorrectorCopiesView should return a flat array (no pagination wrapper)."""

    def setUp(self):
        self.client = APIClient()
        teacher_group, _ = Group.objects.get_or_create(name='teacher')
        self.teacher = User.objects.create_user('flat_t', 'ft@t.fr', 'pass')
        self.teacher.groups.add(teacher_group)
        self.exam = Exam.objects.create(name='Flat Test', date='2026-01-01')
        # Create 3 copies
        for i in range(3):
            Copy.objects.create(
                exam=self.exam,
                anonymous_id=f'FLAT{i:03d}',
                status=Copy.Status.READY,
                assigned_corrector=self.teacher,
            )
        self.client.force_login(self.teacher)

    def test_returns_flat_array(self):
        url = reverse('corrector-copy-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, http_status.HTTP_200_OK)
        # Must be a flat list, NOT a paginated dict with "results" key
        self.assertIsInstance(response.data, list)
        self.assertEqual(len(response.data), 3)


@override_settings(RATELIMIT_ENABLE=False)
class TestCopyIdentificationDuplicate(TestCase):
    """CopyIdentificationView prevents duplicate student assignment."""

    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_superuser('admin3', 'a3@t.fr', 'admin')
        self.client.force_login(self.admin)
        self.exam = Exam.objects.create(name='Dup Test', date='2026-01-01')
        self.student = Student.objects.create(full_name='DUPONT Jean', date_of_birth='2006-01-01')

    def test_duplicate_identification_rejected(self):
        copy1 = Copy.objects.create(
            exam=self.exam, anonymous_id='DUP001',
            status=Copy.Status.READY, student=self.student, is_identified=True,
        )
        copy2 = Copy.objects.create(
            exam=self.exam, anonymous_id='DUP002', status=Copy.Status.READY,
        )
        url = reverse('copy-identify', kwargs={'id': copy2.id})
        response = self.client.post(url, {'student_id': str(self.student.id)})
        self.assertEqual(response.status_code, http_status.HTTP_400_BAD_REQUEST)
        self.assertIn('already assigned', str(response.data['error']))


@override_settings(RATELIMIT_ENABLE=False)
class TestCopyValidationURL(TestCase):
    """CopyValidationView should be accessible at the expected URL."""

    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_superuser('admin4', 'a4@t.fr', 'admin')
        self.client.force_login(self.admin)
        self.exam = Exam.objects.create(name='Val URL', date='2026-01-01')
        self.copy = Copy.objects.create(
            exam=self.exam, anonymous_id='VAL001', status=Copy.Status.STAGING,
        )

    def test_url_resolves(self):
        url = reverse('copy-validate', kwargs={'id': self.copy.id})
        self.assertEqual(url, f'/api/exams/copies/{self.copy.id}/validate/')

    def test_validation_transitions_staging_to_ready(self):
        # validate_copy requires pages_images on booklet (M2M with Copy)
        booklet = Booklet.objects.create(
            exam=self.exam,
            start_page=1,
            end_page=4,
            pages_images=['page1.png', 'page2.png'],
        )
        self.copy.booklets.add(booklet)
        url = reverse('copy-validate', kwargs={'id': self.copy.id})
        response = self.client.post(url)
        self.assertEqual(response.status_code, http_status.HTTP_200_OK)
        self.copy.refresh_from_db()
        self.assertEqual(self.copy.status, Copy.Status.READY)
