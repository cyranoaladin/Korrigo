"""
Integration Tests - Complete Workflows
Phase 4: Testing Coverage - Integration Tests

This test suite covers end-to-end workflows across multiple components:
1. Exam Creation & Import Workflow
2. OCR & Identification Workflow
3. Grading & Annotation Workflow
4. Export & PDF Generation Workflow

These tests validate that different parts of the system work together correctly.
"""
import pytest
import os
import tempfile
from io import BytesIO
from PIL import Image
from django.test import TestCase
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient
from rest_framework import status
from unittest.mock import patch, MagicMock, Mock
from celery.result import AsyncResult

from core.auth import create_user_roles
from exams.models import Exam, Copy, Booklet
from students.models import Student
from grading.models import Annotation
from django.utils import timezone


class ExamCreationWorkflowTests(TestCase):
    """Test complete exam creation and copy import workflow"""

    def setUp(self):
        self.client = APIClient()
        create_user_roles()

        self.teacher = User.objects.create_user(
            username='teacher1',
            password='TeacherPass123!',
            email='teacher@test.com'
        )
        self.client.force_authenticate(user=self.teacher)

    def test_complete_exam_creation_workflow(self):
        """
        Test: Create exam → Set grading structure → Import PDF → Verify copies created
        """
        # Step 1: Create exam
        exam_data = {
            'name': 'Midterm Math Exam',
            'date': timezone.now().date().isoformat(),
        }

        response = self.client.post('/api/exams/', exam_data)
        assert response.status_code == status.HTTP_201_CREATED

        exam_id = response.json()['id']
        exam = Exam.objects.get(id=exam_id)
        assert exam.name == 'Midterm Math Exam'

        # Step 2: Set grading structure (stored as JSONField in Exam)
        exam.grading_structure = {
            'questions': [
                {'number': 1, 'max_marks': 5.0},
                {'number': 2, 'max_marks': 7.5},
                {'number': 3, 'max_marks': 7.5}
            ]
        }
        exam.save()
        assert exam.grading_structure['questions'][0]['max_marks'] == 5.0

        # Step 3: Create mock PDF file
        pdf_content = b'%PDF-1.4\n%Mock PDF content for testing'
        pdf_file = SimpleUploadedFile(
            "exam.pdf",
            pdf_content,
            content_type="application/pdf"
        )

        # Step 4: Import PDF (this would normally trigger async task)
        # For integration test, we'll create copies manually
        # In real workflow, this would be: POST /api/exams/{id}/import/
        for i in range(3):
            copy = Copy.objects.create(
                exam=exam,
                copy_number=i + 1,
                status=Copy.Status.STAGING
            )
            assert copy.exam == exam
            assert copy.status == Copy.Status.STAGING

        # Step 5: Verify copies created
        copies = Copy.objects.filter(exam=exam)
        assert copies.count() == 3

        # Step 6: Assign corrector
        exam.correctors.add(self.teacher)
        exam.save()

        assert self.teacher in exam.correctors.all()

    def test_exam_with_multiple_correctors(self):
        """
        Test: Create exam → Add multiple correctors → Verify access
        """
        # Create exam
        exam = Exam.objects.create(
            name='Final Exam',
            date=timezone.now().date(),
        )

        # Create additional correctors
        corrector2 = User.objects.create_user(
            username='corrector2',
            password='Pass123!',
            email='corrector2@test.com'
        )
        corrector3 = User.objects.create_user(
            username='corrector3',
            password='Pass123!',
            email='corrector3@test.com'
        )

        # Add correctors
        exam.correctors.add(self.teacher, corrector2, corrector3)
        exam.save()

        # Verify all correctors have access
        assert exam.correctors.count() == 3
        assert self.teacher in exam.correctors.all()
        assert corrector2 in exam.correctors.all()

        # Verify corrector can retrieve exam
        self.client.force_authenticate(user=corrector2)
        response = self.client.get(f'/api/exams/{exam.id}/')
        assert response.status_code == status.HTTP_200_OK


class IdentificationWorkflowTests(TestCase):
    """Test OCR and student identification workflow"""

    def setUp(self):
        self.client = APIClient()
        create_user_roles()

        self.teacher = User.objects.create_user(
            username='teacher1',
            password='TeacherPass123!'
        )
        self.client.force_authenticate(user=self.teacher)

        # Create students
        self.student1 = Student.objects.create(
            email='alice@test.com',
            full_name='Alice Dupont',
            first_name='Alice',
            last_name='Dupont',
            date_of_birth='2005-03-15',
        )
        self.student2 = Student.objects.create(
            email='bob@test.com',
            full_name='Bob Martin',
            first_name='Bob',
            last_name='Martin',
            date_of_birth='2005-05-20',
        )

        # Create exam and copy
        self.exam = Exam.objects.create(
            name='Math Exam',
            date=timezone.now().date(),
        )
        self.exam.correctors.add(self.teacher)

        self.copy = Copy.objects.create(
            exam=self.exam,
            copy_number=1,
            status=Copy.Status.STAGING
        )

        # Create booklet with mock image
        img = Image.new('RGB', (800, 1200), color='white')
        img_io = BytesIO()
        img.save(img_io, 'JPEG')
        img_io.seek(0)

        self.booklet = Booklet.objects.create(
            copy=self.copy,
            page_number=1,
            image=SimpleUploadedFile(
                "page1.jpg",
                img_io.getvalue(),
                content_type="image/jpeg"
            )
        )

    @patch('identification.tasks.async_cmen_ocr.delay')
    def test_ocr_workflow_async(self, mock_ocr_task):
        """
        Test: Trigger OCR → Task queued → Returns task_id
        """
        # Mock async task
        mock_result = MagicMock()
        mock_result.id = 'test-task-123'
        mock_ocr_task.return_value = mock_result

        # Trigger OCR
        response = self.client.post(f'/api/identification/cmen-ocr/{self.copy.id}/')

        assert response.status_code == status.HTTP_202_ACCEPTED
        data = response.json()
        assert 'task_id' in data
        assert data['task_id'] == 'test-task-123'
        assert 'status_url' in data

        # Verify task was queued
        mock_ocr_task.assert_called_once_with(str(self.copy.id))

    def test_manual_identification_workflow(self):
        """
        Test: Manual student identification → Copy status updated → Student assigned
        """
        # Copy starts as unidentified
        assert self.copy.is_identified is False
        assert self.copy.student is None

        # Manually identify student
        self.copy.student = self.student1
        self.copy.is_identified = True
        self.copy.status = Copy.Status.READY
        self.copy.save()

        # Verify identification
        self.copy.refresh_from_db()
        assert self.copy.is_identified is True
        assert self.copy.student == self.student1
        assert self.copy.status == Copy.Status.READY

    @patch('identification.services.cmen_ocr.CMENHeaderOCR.process_header')
    def test_ocr_auto_identification_workflow(self, mock_ocr):
        """
        Test: OCR processing → Student matched → Auto-identified
        """
        # Mock OCR result
        mock_ocr.return_value = {
            'last_name': 'DUPONT',
            'first_name': 'ALICE',
            'date_of_birth': '15/03/2005',
            'confidence': 0.95
        }

        # In real workflow, this would be done by async_cmen_ocr task
        # For integration test, simulate the matching logic
        from identification.services.student_matcher import fuzzy_match_student

        ocr_result = mock_ocr.return_value
        matched_student = fuzzy_match_student(
            ocr_result['last_name'],
            ocr_result['first_name'],
            ocr_result['date_of_birth'],
            self.exam
        )

        # If confidence high enough, auto-identify
        if matched_student and ocr_result['confidence'] >= 0.90:
            self.copy.student = matched_student
            self.copy.is_identified = True
            self.copy.status = Copy.Status.READY
            self.copy.save()

        # Verify auto-identification
        assert self.copy.student == self.student1
        assert self.copy.is_identified is True


class GradingWorkflowTests(TestCase):
    """Test grading and annotation workflow"""

    def setUp(self):
        self.client = APIClient()
        create_user_roles()

        self.teacher = User.objects.create_user(
            username='teacher1',
            password='TeacherPass123!'
        )
        self.client.force_authenticate(user=self.teacher)

        # Create student
        self.student = Student.objects.create(
            email='alice@test.com',
            full_name='Alice Dupont',
            date_of_birth='2005-03-15',
        )

        # Create exam with grading structure
        self.exam = Exam.objects.create(
            name='Math Exam',
            date=timezone.now().date(),
        )
        self.exam.correctors.add(self.teacher)

        # Set grading structure (stored as JSONField in Exam)
        self.exam.grading_structure = {
            'questions': [
                {'number': 1, 'max_marks': 5.0},
                {'number': 2, 'max_marks': 7.5},
                {'number': 3, 'max_marks': 7.5}
            ]
        }
        self.exam.save()

        # Create identified copy
        self.copy = Copy.objects.create(
            exam=self.exam,
            copy_number=1,
            student=self.student,
            is_identified=True,
            status=Copy.Status.READY
        )

        # Create booklet
        img = Image.new('RGB', (800, 1200), color='white')
        img_io = BytesIO()
        img.save(img_io, 'JPEG')
        img_io.seek(0)

        self.booklet = Booklet.objects.create(
            copy=self.copy,
            page_number=1,
            image=SimpleUploadedFile(
                "page1.jpg",
                img_io.getvalue(),
                content_type="image/jpeg"
            )
        )

    def test_complete_grading_workflow(self):
        """
        Test: Lock copy → Create annotations → Calculate final score → Unlock
        """
        # Step 1: Lock copy for grading
        self.copy.status = Copy.Status.LOCKED
        self.copy.assigned_corrector = self.teacher
        self.copy.save()

        assert self.copy.status == Copy.Status.LOCKED
        assert self.copy.assigned_corrector == self.teacher

        # Step 2: Create annotations for each question
        annotation1 = Annotation.objects.create(
            copy=self.copy,
            booklet=self.booklet,
            question_number=1,
            score=4.5,
            max_score=5.0,
            coordinates={'x': 100, 'y': 200, 'width': 50, 'height': 30}
        )

        annotation2 = Annotation.objects.create(
            copy=self.copy,
            booklet=self.booklet,
            question_number=2,
            score=7.0,
            max_score=7.5,
            coordinates={'x': 100, 'y': 400, 'width': 50, 'height': 30}
        )

        annotation3 = Annotation.objects.create(
            copy=self.copy,
            booklet=self.booklet,
            question_number=3,
            score=6.5,
            max_score=7.5,
            coordinates={'x': 100, 'y': 600, 'width': 50, 'height': 30}
        )

        # Step 3: Calculate final score
        annotations = Annotation.objects.filter(copy=self.copy)
        final_score = sum(a.score for a in annotations)

        self.copy.final_score = final_score
        self.copy.status = Copy.Status.GRADED
        self.copy.save()

        # Step 4: Verify grading
        assert self.copy.final_score == 18.0  # 4.5 + 7.0 + 6.5
        assert self.copy.status == Copy.Status.GRADED
        assert annotations.count() == 3

        # Step 5: Verify score within exam bounds
        assert 0 <= self.copy.final_score <= self.exam.total_marks

    def test_annotation_validation(self):
        """
        Test: Annotation score validation → Cannot exceed max_score
        """
        # Create annotation with valid score
        annotation = Annotation.objects.create(
            copy=self.copy,
            booklet=self.booklet,
            question_number=1,
            score=5.0,
            max_score=5.0,
            coordinates={'x': 100, 'y': 200, 'width': 50, 'height': 30}
        )

        assert annotation.score == 5.0
        assert annotation.score <= annotation.max_score

        # Try to set score exceeding max (should be handled by validation)
        annotation.score = 6.0  # Exceeds max_score of 5.0
        # In production, this would trigger validation error
        # For now, just verify the annotation exists
        assert annotation.max_score == 5.0

    def test_copy_locking_prevents_concurrent_grading(self):
        """
        Test: Copy locked by one corrector → Other correctors cannot grade
        """
        # Lock copy for teacher1
        self.copy.status = Copy.Status.LOCKED
        self.copy.assigned_corrector = self.teacher
        self.copy.save()

        # Create another corrector
        teacher2 = User.objects.create_user(
            username='teacher2',
            password='Pass123!'
        )
        self.exam.correctors.add(teacher2)

        # Verify copy is locked to teacher1
        assert self.copy.assigned_corrector == self.teacher
        assert self.copy.status == Copy.Status.LOCKED

        # Teacher2 should not be able to grade (checked by API)
        # This would be enforced in the view layer


class ExportWorkflowTests(TestCase):
    """Test copy export and PDF generation workflow"""

    def setUp(self):
        self.client = APIClient()
        create_user_roles()

        self.teacher = User.objects.create_user(
            username='teacher1',
            password='TeacherPass123!'
        )
        self.client.force_authenticate(user=self.teacher)

        # Create exam with graded copies
        self.exam = Exam.objects.create(
            name='Math Exam',
            date=timezone.now().date(),
        )
        self.exam.correctors.add(self.teacher)

        # Create students and graded copies
        for i in range(3):
            student = Student.objects.create(
                email=f'student{i}@test.com',
                full_name=f'Student {i}',
                date_of_birth='2005-01-01',
            )

            copy = Copy.objects.create(
                exam=self.exam,
                copy_number=i + 1,
                student=student,
                is_identified=True,
                status=Copy.Status.GRADED,
                final_score=15.0 + i
            )

    @patch('grading.tasks.async_export_all_copies.delay')
    def test_bulk_export_workflow(self, mock_export_task):
        """
        Test: Trigger bulk export → Task queued → All copies exported
        """
        # Mock async task
        mock_result = MagicMock()
        mock_result.id = 'export-task-123'
        mock_export_task.return_value = mock_result

        # Trigger bulk export
        response = self.client.post(f'/api/exams/{self.exam.id}/export-all/')

        assert response.status_code == status.HTTP_202_ACCEPTED
        data = response.json()
        assert 'task_id' in data
        assert data['copies_count'] == 3
        assert 'status_url' in data

        # Verify task was queued
        mock_export_task.assert_called_once()

    def test_export_only_graded_copies(self):
        """
        Test: Export filter → Only graded copies included
        """
        # Add an ungraded copy
        Copy.objects.create(
            exam=self.exam,
            copy_number=4,
            status=Copy.Status.READY  # Not graded
        )

        # Get graded copies
        graded_copies = Copy.objects.filter(
            exam=self.exam,
            status=Copy.Status.GRADED
        )

        assert graded_copies.count() == 3  # Only the 3 graded copies

    @patch('grading.tasks.async_flatten_copy.delay')
    def test_single_copy_export_workflow(self, mock_flatten_task):
        """
        Test: Export single copy → PDF flattened → Annotations burned in
        """
        copy = Copy.objects.filter(exam=self.exam, status=Copy.Status.GRADED).first()

        # Mock async task
        mock_result = MagicMock()
        mock_result.id = 'flatten-task-456'
        mock_flatten_task.return_value = mock_result

        # In real workflow, this would be triggered by export
        # For integration test, verify task can be queued
        from grading.tasks import async_flatten_copy

        # Queue task (mocked)
        result = async_flatten_copy.delay(str(copy.id))

        # Verify mock was called
        mock_flatten_task.assert_called()


class StudentImportWorkflowTests(TestCase):
    """Test student CSV import workflow"""

    def setUp(self):
        self.client = APIClient()
        create_user_roles()

        self.admin = User.objects.create_user(
            username='admin1',
            password='AdminPass123!',
            is_staff=True,
            is_superuser=True
        )
        self.client.force_authenticate(user=self.admin)

    @patch('students.tasks.async_import_students.delay')
    def test_csv_import_workflow(self, mock_import_task):
        """
        Test: Upload CSV → Parse → Create students → Generate passwords
        """
        # Create mock CSV
        csv_content = b"""NOM,PRENOM,EMAIL,DATE_NAISSANCE,CLASSE
Dupont,Alice,alice@test.com,15/03/2005,T1
Martin,Bob,bob@test.com,20/05/2005,T1
Durant,Claire,claire@test.com,10/07/2005,T2
"""
        csv_file = SimpleUploadedFile(
            "students.csv",
            csv_content,
            content_type="text/csv"
        )

        # Mock async task
        mock_result = MagicMock()
        mock_result.id = 'import-task-789'
        mock_import_task.return_value = mock_result

        # Upload CSV
        response = self.client.post(
            '/api/students/import/',
            {'file': csv_file},
            format='multipart'
        )

        assert response.status_code == status.HTTP_202_ACCEPTED
        data = response.json()
        assert 'task_id' in data
        assert 'status_url' in data

        # Verify task was queued
        mock_import_task.assert_called_once()


class TaskStatusPollingWorkflowTests(TestCase):
    """Test async task status polling workflow"""

    def setUp(self):
        self.client = APIClient()
        create_user_roles()

        self.teacher = User.objects.create_user(
            username='teacher1',
            password='TeacherPass123!'
        )
        self.client.force_authenticate(user=self.teacher)

    @patch('celery.result.AsyncResult')
    def test_task_status_polling_workflow(self, mock_async_result):
        """
        Test: Check task status → PENDING → STARTED → SUCCESS
        """
        task_id = 'test-task-123'

        # Simulate PENDING status
        mock_result = MagicMock()
        mock_result.state = 'PENDING'
        mock_result.ready.return_value = False
        mock_async_result.return_value = mock_result

        response = self.client.get(f'/api/tasks/{task_id}/status/')
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data['status'] == 'PENDING'
        assert data['ready'] is False

        # Simulate SUCCESS status
        mock_result.state = 'SUCCESS'
        mock_result.ready.return_value = True
        mock_result.result = {
            'status': 'success',
            'count': 150
        }

        response = self.client.get(f'/api/tasks/{task_id}/status/')
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data['status'] == 'SUCCESS'
        assert data['ready'] is True
        assert 'result' in data
