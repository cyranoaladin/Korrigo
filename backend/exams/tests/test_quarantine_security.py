"""
Tests: QUARANTINE exclusion from dispatch/corrector views + anonymisation.
CI-BLOCKING.
"""
import uuid as uuid_lib
from django.test import TestCase
from django.contrib.auth.models import User, Group
from rest_framework.test import APIClient
from exams.models import Exam, Copy


class QuarantineExclusionTest(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser('admin_q', 'a@e.fr', 'pass12345678')
        self.teacher = User.objects.create_user('teacher_q', 't@e.fr', 'pass12345678')
        teacher_group, _ = Group.objects.get_or_create(name='teacher')
        self.teacher.groups.add(teacher_group)
        self.teacher.is_staff = True
        self.teacher.save()

        self.exam = Exam.objects.create(name='QTest', date='2025-01-01')
        self.exam.correctors.add(self.teacher)

        self.q_copy = Copy.objects.create(
            exam=self.exam,
            anonymous_id=f'Q-{uuid_lib.uuid4().hex[:8]}',
            status='QUARANTINE',
        )
        self.r_copy = Copy.objects.create(
            exam=self.exam,
            anonymous_id=f'R-{uuid_lib.uuid4().hex[:8]}',
            status='READY',
            assigned_corrector=self.teacher,
        )
        self.client = APIClient()

    def test_quarantine_excluded_from_corrector_copies(self):
        self.client.force_authenticate(user=self.teacher)
        response = self.client.get('/api/copies/')
        self.assertEqual(response.status_code, 200)
        ids = [str(c['id']) for c in response.data]
        self.assertNotIn(str(self.q_copy.id), ids)
        self.assertIn(str(self.r_copy.id), ids)

    def test_quarantine_excluded_from_dispatch(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.post(f'/api/exams/{self.exam.id}/dispatch/')
        self.assertEqual(response.status_code, 200)
        self.q_copy.refresh_from_db()
        self.assertIsNone(self.q_copy.assigned_corrector)

    def test_quarantine_to_ready(self):
        self.q_copy.transition_to('READY')
        self.assertEqual(self.q_copy.status, 'READY')

    def test_quarantine_to_staging(self):
        self.q_copy.transition_to('STAGING')
        self.assertEqual(self.q_copy.status, 'STAGING')

    def test_staging_to_quarantine(self):
        s = Copy.objects.create(
            exam=self.exam, anonymous_id=f'S-{uuid_lib.uuid4().hex[:8]}',
            status='STAGING',
        )
        s.transition_to('QUARANTINE')
        self.assertEqual(s.status, 'QUARANTINE')


class CorrectorAnonymisationTest(TestCase):
    def setUp(self):
        from students.models import Student
        self.teacher = User.objects.create_user('teacher_anon', 't2@e.fr', 'pass12345678')
        teacher_group, _ = Group.objects.get_or_create(name='teacher')
        self.teacher.groups.add(teacher_group)
        self.teacher.is_staff = True
        self.teacher.save()

        self.exam = Exam.objects.create(name='AnonTest', date='2025-01-01')
        self.exam.correctors.add(self.teacher)

        self.student = Student.objects.create(
            full_name='DUPONT Marie', date_of_birth='2008-03-15', email='marie@test.fr'
        )
        self.copy = Copy.objects.create(
            exam=self.exam, anonymous_id=f'A-{uuid_lib.uuid4().hex[:8]}',
            status='READY', student=self.student, is_identified=True,
            assigned_corrector=self.teacher,
        )
        self.client = APIClient()

    def test_corrector_copies_list_no_student(self):
        self.client.force_authenticate(user=self.teacher)
        response = self.client.get('/api/copies/')
        self.assertEqual(response.status_code, 200)
        for copy_data in response.data:
            self.assertNotIn('student', copy_data)
            self.assertNotIn('is_identified', copy_data)

    def test_corrector_copy_detail_no_student(self):
        self.client.force_authenticate(user=self.teacher)
        response = self.client.get(f'/api/copies/{self.copy.id}/')
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('student', response.data)
        self.assertNotIn('is_identified', response.data)
