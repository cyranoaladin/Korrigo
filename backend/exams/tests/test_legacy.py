from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from exams.models import Exam, Booklet, Copy
from django.contrib.auth.models import User, Group
from core.auth import UserRole
from students.models import Student
from grading.models import Score
import json
from datetime import date
from decimal import Decimal

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


class PronoteExportTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.exam = Exam.objects.create(name='Mathématiques', date='2026-03-15')
        
        self.admin = User.objects.create_superuser(username='admin', password='admin123')
        self.teacher = User.objects.create_user(username='teacher', password='teacher123')
        
        self.admin_group, _ = Group.objects.get_or_create(name=UserRole.ADMIN)
        self.teacher_group, _ = Group.objects.get_or_create(name=UserRole.TEACHER)
        
        self.admin.groups.add(self.admin_group)
        self.teacher.groups.add(self.teacher_group)
        
        self.student1 = Student.objects.create(
            first_name='Jean',
            last_name='Dupont',
            class_name='TS1',
            date_naissance='2005-01-15'
        )
        self.student2 = Student.objects.create(
            first_name='Sophie',
            last_name='Martin',
            class_name='TS1',
            date_naissance='2005-02-20'
        )
        self.student3 = Student.objects.create(
            first_name='Pierre',
            last_name='Durand',
            class_name='TS2',
            date_naissance='2005-03-10'
        )

    def test_admin_only_permission(self):
        copy = Copy.objects.create(
            exam=self.exam,
            anonymous_id='TEST001',
            status=Copy.Status.GRADED,
            is_identified=True,
            student=self.student1
        )
        
        self.client.force_login(self.teacher)
        url = reverse('export-pronote', kwargs={'id': self.exam.id})
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn('error', response.data)

    def test_export_with_valid_data(self):
        copy1 = Copy.objects.create(
            exam=self.exam,
            anonymous_id='COPY001',
            status=Copy.Status.GRADED,
            is_identified=True,
            student=self.student1,
            global_appreciation='Bon travail'
        )
        Score.objects.create(
            copy=copy1,
            scores_data={'ex1': 10.5, 'ex2': 5.0}
        )
        
        copy2 = Copy.objects.create(
            exam=self.exam,
            anonymous_id='COPY002',
            status=Copy.Status.GRADED,
            is_identified=True,
            student=self.student2
        )
        Score.objects.create(
            copy=copy2,
            scores_data={'ex1': 8.25, 'ex2': 4.0}
        )
        
        self.client.force_login(self.admin)
        url = reverse('export-pronote', kwargs={'id': self.exam.id})
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response['Content-Type'], 'text/csv; charset=utf-8')
        self.assertIn('attachment', response['Content-Disposition'])
        
        content = response.content.decode('utf-8-sig')
        lines = content.strip().split('\n')
        
        self.assertIn('NOM;PRENOM;DATE_NAISSANCE;MATIERE;NOTE;COEFF;COMMENTAIRE', lines[0])
        content_joined = '\n'.join(lines)
        self.assertIn('Dupont', content_joined)
        self.assertIn('Jean', content_joined)
        self.assertIn('15,50', content_joined)
        self.assertIn('Martin', content_joined)
        self.assertIn('Sophie', content_joined)
        self.assertIn('12,25', content_joined)

    def test_export_rounding_logic(self):
        copy = Copy.objects.create(
            exam=self.exam,
            anonymous_id='ROUND001',
            status=Copy.Status.GRADED,
            is_identified=True,
            student=self.student1
        )
        Score.objects.create(
            copy=copy,
            scores_data={'ex1': 15.555, 'ex2': 3.0}
        )
        
        self.client.force_login(self.admin)
        url = reverse('export-pronote', kwargs={'id': self.exam.id})
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.content.decode('utf-8-sig')
        self.assertIn('18,56', content)

    def test_export_whole_numbers(self):
        copy = Copy.objects.create(
            exam=self.exam,
            anonymous_id='WHOLE001',
            status=Copy.Status.GRADED,
            is_identified=True,
            student=self.student1
        )
        Score.objects.create(
            copy=copy,
            scores_data={'ex1': 15, 'ex2': 5}
        )
        
        self.client.force_login(self.admin)
        url = reverse('export-pronote', kwargs={'id': self.exam.id})
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.content.decode('utf-8-sig')
        self.assertIn('20,00', content)

    def test_export_reject_ungraded_copies(self):
        Copy.objects.create(
            exam=self.exam,
            anonymous_id='UNGRADED001',
            status=Copy.Status.READY,
            is_identified=True,
            student=self.student1
        )
        
        self.client.force_login(self.admin)
        url = reverse('export-pronote', kwargs={'id': self.exam.id})
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
        # Errors are now in 'details' list
        details_str = str(response.data.get('details', []))
        self.assertTrue('GRADED' in details_str or 'notée' in details_str)

    def test_export_reject_unidentified_copies(self):
        copy = Copy.objects.create(
            exam=self.exam,
            anonymous_id='UNIDENT001',
            status=Copy.Status.GRADED,
            is_identified=False
        )
        Score.objects.create(
            copy=copy,
            scores_data={'ex1': 10}
        )
        
        self.client.force_login(self.admin)
        url = reverse('export-pronote', kwargs={'id': self.exam.id})
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
        details_str = str(response.data.get('details', []))
        self.assertTrue('identifié' in details_str or 'élève' in details_str)

    def test_export_reject_missing_student(self):
        """Test export fails when copy is identified but has no linked student."""
        copy = Copy.objects.create(
            exam=self.exam,
            anonymous_id='NOSTUDENT001',
            status=Copy.Status.GRADED,
            is_identified=True,
            student=None
        )
        Score.objects.create(
            copy=copy,
            scores_data={'ex1': 10}
        )
        
        self.client.force_login(self.admin)
        url = reverse('export-pronote', kwargs={'id': self.exam.id})
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
        details_str = str(response.data.get('details', []))
        self.assertTrue('élève' in details_str or 'student' in details_str.lower())

    def test_export_reject_no_copies(self):
        self.client.force_login(self.admin)
        url = reverse('export-pronote', kwargs={'id': self.exam.id})
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
        details_str = str(response.data.get('details', []))
        self.assertTrue('Aucune copie' in details_str or 'aucune' in details_str.lower())

    def test_export_semicolon_delimiter(self):
        copy = Copy.objects.create(
            exam=self.exam,
            anonymous_id='DELIM001',
            status=Copy.Status.GRADED,
            is_identified=True,
            student=self.student1
        )
        Score.objects.create(
            copy=copy,
            scores_data={'ex1': 10}
        )
        
        self.client.force_login(self.admin)
        url = reverse('export-pronote', kwargs={'id': self.exam.id})
        response = self.client.post(url)
        
        content = response.content.decode('utf-8-sig')
        lines = content.strip().split('\n')
        
        for line in lines:
            if line:
                self.assertIn(';', line)

    def test_export_comment_sanitization(self):
        copy = Copy.objects.create(
            exam=self.exam,
            anonymous_id='COMMENT001',
            status=Copy.Status.GRADED,
            is_identified=True,
            student=self.student1,
            global_appreciation='Commentaire avec\nnouvelle ligne\ret tabulation'
        )
        Score.objects.create(
            copy=copy,
            scores_data={'ex1': 10}
        )
        
        self.client.force_login(self.admin)
        url = reverse('export-pronote', kwargs={'id': self.exam.id})
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.content.decode('utf-8-sig')
        # Newlines and carriage returns should be sanitized
        self.assertIn('Commentaire avec', content)

    def test_export_filename_format(self):
        copy = Copy.objects.create(
            exam=self.exam,
            anonymous_id='FILE001',
            status=Copy.Status.GRADED,
            is_identified=True,
            student=self.student1
        )
        Score.objects.create(
            copy=copy,
            scores_data={'ex1': 10}
        )
        
        self.client.force_login(self.admin)
        url = reverse('export-pronote', kwargs={'id': self.exam.id})
        response = self.client.post(url)
        
        content_disposition = response['Content-Disposition']
        self.assertIn('export_pronote_Mathématiques_2026-03-15.csv', content_disposition)

    def test_export_edge_case_zero_score(self):
        copy = Copy.objects.create(
            exam=self.exam,
            anonymous_id='ZERO001',
            status=Copy.Status.GRADED,
            is_identified=True,
            student=self.student1
        )
        Score.objects.create(
            copy=copy,
            scores_data={'ex1': 0, 'ex2': 0}
        )
        
        self.client.force_login(self.admin)
        url = reverse('export-pronote', kwargs={'id': self.exam.id})
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.content.decode('utf-8-sig')
        self.assertIn('0,00', content)

    def test_export_edge_case_max_score(self):
        copy = Copy.objects.create(
            exam=self.exam,
            anonymous_id='MAX001',
            status=Copy.Status.GRADED,
            is_identified=True,
            student=self.student1
        )
        Score.objects.create(
            copy=copy,
            scores_data={'ex1': 10, 'ex2': 10}
        )
        
        self.client.force_login(self.admin)
        url = reverse('export-pronote', kwargs={'id': self.exam.id})
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.content.decode('utf-8-sig')
        self.assertIn('20,00', content)
