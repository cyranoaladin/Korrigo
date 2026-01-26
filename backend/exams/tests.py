from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from .models import Exam, Booklet
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
