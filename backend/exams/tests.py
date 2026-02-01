from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from .models import Exam, Booklet, Copy
from django.contrib.auth.models import User, Group
from core.auth import UserRole
import json
from datetime import date

class ExamTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.exam_data = {
            'name': 'Bac Blanc Math 2026',
            'date': '2026-05-20'
        }
        self.exam = Exam.objects.create(**self.exam_data)

    def test_create_exam(self):
        """Test Creating an Exam via Upload (Simulation without file for now or with mockup)"""
        # Upload endpoint requires a file, so we test the Model logic first
        self.assertEqual(Exam.objects.count(), 1)
        self.assertEqual(self.exam.name, 'Bac Blanc Math 2026')

    def test_grading_structure_validation(self):
        """Test Grading Structure Logic"""
        structure = [
            {"id": "ex1", "label": "Ex 1", "points": 5}
        ]
        self.exam.grading_structure = structure
        self.exam.save()
        self.assertEqual(self.exam.grading_structure, structure)

    def test_booklet_creation(self):
        """Test simulating booklet creation"""
        Booklet.objects.create(exam=self.exam, start_page=1, end_page=2)
        self.assertEqual(self.exam.booklets.count(), 1)

class APITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.exam = Exam.objects.create(name='Test API', date='2026-01-01')

        # Create test user with teacher role
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.teacher_group, _ = Group.objects.get_or_create(name=UserRole.TEACHER)
        self.user.groups.add(self.teacher_group)

        # Authenticate the client
        self.client.force_login(self.user)

    def test_list_booklets(self):
        url = reverse('booklet-list', kwargs={'exam_id': self.exam.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class DispatchTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.exam = Exam.objects.create(name='Test Dispatch', date='2026-01-01')
        
        self.admin = User.objects.create_user(username='admin', password='admin')
        self.teacher_group, _ = Group.objects.get_or_create(name=UserRole.TEACHER)
        self.admin.groups.add(self.teacher_group)
        
        self.corrector1 = User.objects.create_user(username='corrector1', password='pass1')
        self.corrector1.groups.add(self.teacher_group)
        self.corrector2 = User.objects.create_user(username='corrector2', password='pass2')
        self.corrector2.groups.add(self.teacher_group)
        self.corrector3 = User.objects.create_user(username='corrector3', password='pass3')
        self.corrector3.groups.add(self.teacher_group)
        
        self.exam.correctors.add(self.corrector1, self.corrector2, self.corrector3)
        
        self.client.force_login(self.admin)

    def test_dispatch_no_correctors(self):
        exam_no_correctors = Exam.objects.create(name='No Correctors', date='2026-01-02')
        Copy.objects.create(exam=exam_no_correctors, anonymous_id='TEST001', status=Copy.Status.READY)
        
        url = reverse('exam-dispatch', kwargs={'exam_id': exam_no_correctors.id})
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)

    def test_dispatch_no_copies(self):
        url = reverse('exam-dispatch', kwargs={'exam_id': self.exam.id})
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('message', response.data)

    def test_dispatch_10_copies_3_correctors(self):
        for i in range(10):
            Copy.objects.create(
                exam=self.exam, 
                anonymous_id=f'TEST{i:03d}', 
                status=Copy.Status.READY
            )
        
        url = reverse('exam-dispatch', kwargs={'exam_id': self.exam.id})
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['copies_assigned'], 10)
        self.assertEqual(response.data['correctors_count'], 3)
        
        distribution = response.data['distribution']
        counts = list(distribution.values())
        
        self.assertEqual(sum(counts), 10)
        self.assertLessEqual(max(counts) - min(counts), 1)
        
        assigned_copies = Copy.objects.filter(exam=self.exam, assigned_corrector__isnull=False)
        self.assertEqual(assigned_copies.count(), 10)
        
        for copy in assigned_copies:
            self.assertIsNotNone(copy.assigned_corrector)
            self.assertIsNotNone(copy.dispatch_run_id)
            self.assertIsNotNone(copy.assigned_at)

    def test_dispatch_does_not_reassign_existing(self):
        copy1 = Copy.objects.create(
            exam=self.exam,
            anonymous_id='ASSIGNED001',
            status=Copy.Status.READY,
            assigned_corrector=self.corrector1
        )
        
        for i in range(5):
            Copy.objects.create(
                exam=self.exam,
                anonymous_id=f'NEW{i:03d}',
                status=Copy.Status.READY
            )
        
        url = reverse('exam-dispatch', kwargs={'exam_id': self.exam.id})
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['copies_assigned'], 5)
        
        copy1.refresh_from_db()
        self.assertEqual(copy1.assigned_corrector, self.corrector1)
        self.assertIsNone(copy1.dispatch_run_id)

    def test_dispatch_atomicity(self):
        for i in range(3):
            Copy.objects.create(
                exam=self.exam,
                anonymous_id=f'ATOMIC{i:03d}',
                status=Copy.Status.READY
            )
        
        url = reverse('exam-dispatch', kwargs={'exam_id': self.exam.id})
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        run_ids = set(
            Copy.objects.filter(exam=self.exam, assigned_corrector__isnull=False)
            .values_list('dispatch_run_id', flat=True)
        )
        
        self.assertEqual(len(run_ids), 1)
