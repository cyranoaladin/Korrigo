"""
Tests for admin release/unrelease workflow.

Verifies:
- Admin can release and unrelease results
- Non-admin cannot release
- Students only see copies from released exams
"""
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status as http_status
from django.contrib.auth.models import User, Group
from exams.models import Exam, Copy
from students.models import Student


@override_settings(RATELIMIT_ENABLE=False)
class TestReleaseResultsEndpoint(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_superuser('admin', 'a@t.fr', 'admin')
        self.exam = Exam.objects.create(name='Release Test', date='2026-01-01')

    def test_url_resolves(self):
        url = reverse('release-results', kwargs={'exam_id': self.exam.id})
        self.assertIn('release-results', url)

    def test_admin_can_release(self):
        self.client.force_login(self.admin)
        url = reverse('release-results', kwargs={'exam_id': self.exam.id})
        response = self.client.post(url)
        self.assertEqual(response.status_code, http_status.HTTP_200_OK)
        self.exam.refresh_from_db()
        self.assertIsNotNone(self.exam.results_released_at)

    def test_release_idempotent(self):
        self.client.force_login(self.admin)
        url = reverse('release-results', kwargs={'exam_id': self.exam.id})
        self.client.post(url)
        response = self.client.post(url)
        self.assertEqual(response.status_code, http_status.HTTP_200_OK)
        self.assertIn('released_at', response.data)

    def test_admin_can_unrelease(self):
        self.client.force_login(self.admin)
        # Release first
        self.client.post(reverse('release-results', kwargs={'exam_id': self.exam.id}))
        self.exam.refresh_from_db()
        self.assertIsNotNone(self.exam.results_released_at)
        # Unrelease
        url = reverse('unrelease-results', kwargs={'exam_id': self.exam.id})
        response = self.client.post(url)
        self.assertEqual(response.status_code, http_status.HTTP_200_OK)
        self.exam.refresh_from_db()
        self.assertIsNone(self.exam.results_released_at)

    def test_non_admin_cannot_release(self):
        teacher = User.objects.create_user('teacher', 't@t.fr', 'pass')
        self.client.force_login(teacher)
        url = reverse('release-results', kwargs={'exam_id': self.exam.id})
        response = self.client.post(url)
        self.assertEqual(response.status_code, http_status.HTTP_403_FORBIDDEN)

    def test_unauthenticated_cannot_release(self):
        url = reverse('release-results', kwargs={'exam_id': self.exam.id})
        response = self.client.post(url)
        self.assertIn(response.status_code, [
            http_status.HTTP_401_UNAUTHORIZED,
            http_status.HTTP_403_FORBIDDEN,
        ])


@override_settings(RATELIMIT_ENABLE=False)
class TestStudentVisibilityWithRelease(TestCase):
    """Students should only see copies from exams where results are released."""

    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_superuser('admin', 'a@t.fr', 'admin')

        # Create student with user account in "Student" group
        self.student_user = User.objects.create_user('student1', 's@t.fr', 'pass')
        student_group, _ = Group.objects.get_or_create(name='student')
        self.student_user.groups.add(student_group)
        self.student = Student.objects.create(
            full_name='DUPONT Jean',
            date_of_birth='2006-01-01',
            user=self.student_user,
        )

        # Exam 1: released
        self.exam_released = Exam.objects.create(name='Released', date='2026-01-01')
        self.copy_released = Copy.objects.create(
            exam=self.exam_released,
            anonymous_id='REL001',
            status=Copy.Status.GRADED,
            student=self.student,
            is_identified=True,
        )

        # Exam 2: not released
        self.exam_not_released = Exam.objects.create(name='Not Released', date='2026-01-02')
        self.copy_not_released = Copy.objects.create(
            exam=self.exam_not_released,
            anonymous_id='NRL001',
            status=Copy.Status.GRADED,
            student=self.student,
            is_identified=True,
        )

        # Release exam 1
        self.client.force_login(self.admin)
        self.client.post(reverse('release-results', kwargs={'exam_id': self.exam_released.id}))

    def test_student_sees_only_released_copies(self):
        self.client.force_login(self.student_user)
        url = reverse('student-copies')
        response = self.client.get(url)
        self.assertEqual(response.status_code, http_status.HTTP_200_OK)
        data = response.data
        # Should only see 1 copy (from released exam)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['exam_name'], 'Released')

    def test_student_sees_nothing_when_no_release(self):
        # Unrelease exam 1
        self.client.force_login(self.admin)
        self.client.post(reverse('unrelease-results', kwargs={'exam_id': self.exam_released.id}))

        self.client.force_login(self.student_user)
        url = reverse('student-copies')
        response = self.client.get(url)
        self.assertEqual(response.status_code, http_status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)

    def test_release_then_student_sees_copies(self):
        # Release exam 2
        self.client.force_login(self.admin)
        self.client.post(reverse('release-results', kwargs={'exam_id': self.exam_not_released.id}))

        self.client.force_login(self.student_user)
        url = reverse('student-copies')
        response = self.client.get(url)
        self.assertEqual(response.status_code, http_status.HTTP_200_OK)
        # Should see both copies now
        self.assertEqual(len(response.data), 2)


@override_settings(RATELIMIT_ENABLE=False)
class TestExamSerializerIncludesReleasedAt(TestCase):
    """ExamSerializer should expose results_released_at."""

    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_superuser('admin', 'a@t.fr', 'admin')
        self.exam = Exam.objects.create(name='Serializer Test', date='2026-01-01')

    def test_exam_list_includes_released_at(self):
        self.client.force_login(self.admin)
        url = reverse('exam-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, http_status.HTTP_200_OK)
        data = response.data
        exams = data.get('results', data) if isinstance(data, dict) else data
        if isinstance(exams, list) and len(exams) > 0:
            self.assertIn('results_released_at', exams[0])
