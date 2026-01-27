"""
Tests for Celery async tasks
P0-OP-03: Async PDF processing tests
"""
from unittest.mock import patch, Mock
from django.test import TestCase
from django.contrib.auth import get_user_model
from exams.models import Exam, Copy
from grading.tasks import async_finalize_copy, async_import_pdf, cleanup_orphaned_files
import uuid

User = get_user_model()


class AsyncFinalizeCopyTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testteacher',
            email='teacher@test.com',
            password='testpass123',
            role=User.Role.TEACHER
        )
        self.exam = Exam.objects.create(
            title='Test Exam',
            created_by=self.user
        )

    @patch('grading.tasks.GradingService.finalize_copy')
    def test_async_finalize_success(self, mock_finalize):
        """Task successfully calls finalize_copy service"""
        copy = Copy.objects.create(
            exam=self.exam,
            anonymous_id='TEST-001',
            status=Copy.Status.LOCKED,
            locked_by=self.user
        )
        mock_finalize.return_value = copy
        
        result = async_finalize_copy(str(copy.id), self.user.id)
        
        mock_finalize.assert_called_once()
        self.assertEqual(result['copy_id'], str(copy.id))
        self.assertEqual(result['status'], 'success')

    @patch('grading.tasks.GradingService.finalize_copy')
    def test_async_finalize_handles_errors(self, mock_finalize):
        """Task handles service exceptions gracefully"""
        copy = Copy.objects.create(
            exam=self.exam,
            anonymous_id='TEST-002',
            status=Copy.Status.LOCKED
        )
        mock_finalize.side_effect = Exception("PDF generation failed")
        
        result = async_finalize_copy(str(copy.id), self.user.id)
        
        self.assertEqual(result['status'], 'error')
        self.assertIn('PDF generation failed', result['error'])

    def test_async_finalize_copy_not_found(self):
        """Task handles non-existent copy"""
        fake_id = str(uuid.uuid4())
        
        result = async_finalize_copy(fake_id, self.user.id)
        
        self.assertEqual(result['status'], 'error')
        self.assertIn('not found', result['error'].lower())


class AsyncImportPDFTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testimporter',
            email='importer@test.com',
            password='testpass123',
            role=User.Role.TEACHER
        )
        self.exam = Exam.objects.create(
            title='Import Test Exam',
            created_by=self.user
        )

    @patch('grading.tasks.PDFProcessor.import_pdf')
    def test_async_import_success(self, mock_import):
        """Task successfully imports PDF"""
        mock_import.return_value = Mock(id=uuid.uuid4(), status=Copy.Status.READY)
        
        result = async_import_pdf(
            self.exam.id,
            '/tmp/test.pdf',
            self.user.id,
            'TEST-003'
        )
        
        self.assertEqual(result['status'], 'success')
        mock_import.assert_called_once()

    @patch('grading.tasks.PDFProcessor.import_pdf')
    def test_async_import_handles_errors(self, mock_import):
        """Task handles import failures"""
        mock_import.side_effect = ValueError("Invalid PDF format")
        
        result = async_import_pdf(
            self.exam.id,
            '/tmp/invalid.pdf',
            self.user.id,
            'TEST-004'
        )
        
        self.assertEqual(result['status'], 'error')
        self.assertIn('Invalid PDF format', result['error'])


class CleanupOrphanedFilesTests(TestCase):
    @patch('grading.tasks.os.path.exists')
    @patch('grading.tasks.os.listdir')
    @patch('grading.tasks.os.path.getmtime')
    @patch('grading.tasks.os.remove')
    def test_cleanup_removes_old_files(self, mock_remove, mock_getmtime, mock_listdir, mock_exists):
        """Cleanup task removes files older than 24 hours"""
        import time
        current_time = time.time()
        old_file_time = current_time - (25 * 3600)  # 25 hours ago
        
        mock_exists.return_value = True
        mock_listdir.return_value = ['old_temp_123.pdf', 'recent_temp_456.pdf']
        mock_getmtime.side_effect = [old_file_time, current_time]
        
        result = cleanup_orphaned_files()
        
        self.assertGreaterEqual(result['removed_count'], 1)
        mock_remove.assert_called()

    @patch('grading.tasks.os.path.exists')
    def test_cleanup_handles_missing_directory(self, mock_exists):
        """Cleanup handles missing temp directory gracefully"""
        mock_exists.return_value = False
        
        result = cleanup_orphaned_files()
        
        self.assertEqual(result['removed_count'], 0)
