"""
Tests for Exam Upload Endpoint - Validation and Atomicity Cases
Conformité: .antigravity/rules/01_security_rules.md § 8.1
Coverage: POST /api/exams/upload/ validation and atomicity scenarios
"""
import pytest
import os
from unittest.mock import patch, MagicMock
from rest_framework import status
from django.contrib.auth import get_user_model

from exams.models import Exam, Booklet, Copy
from exams.tests.fixtures.pdf_fixtures import (
    create_valid_pdf,
    create_large_pdf,
    create_corrupted_pdf,
    create_fake_pdf,
    create_uploadedfile,
    create_empty_pdf,
    create_pdf_with_pages
)


User = get_user_model()


@pytest.mark.django_db
class TestExamUploadAtomicity:
    """
    Test suite for upload endpoint atomicity guarantees.
    
    Verifies that upload failures leave no orphaned database records or files.
    """
    
    def test_upload_processing_failure_no_orphan_exam(self, teacher_client, settings):
        """
        Test that if PDFSplitter.split_exam() fails, no orphaned Exam record is created.
        
        Expected behavior:
        - Transaction rolls back completely
        - Exam count remains 0
        - Booklet count remains 0
        - Copy count remains 0
        - No orphaned file in media/exams/source/
        """
        # Arrange: Create valid PDF file
        pdf_file = get_valid_pdf_file(pages=4, filename="test_exam.pdf")
        
        upload_data = {
            'name': 'Test Exam - Processing Failure',
            'date': '2026-06-15',
            'pdf_source': pdf_file,
            'pages_per_booklet': 4
        }
        
        # Verify initial state
        assert Exam.objects.count() == 0
        assert Booklet.objects.count() == 0
        assert Copy.objects.count() == 0
        
        # Act: Mock PDFSplitter.split_exam() to raise exception
        with patch('processing.services.pdf_splitter.PDFSplitter.split_exam') as mock_split:
            mock_split.side_effect = RuntimeError("Simulated PDF processing failure")
            
            response = teacher_client.post('/api/exams/upload/', upload_data, format='multipart')
        
        # Assert: Verify response indicates failure
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert 'error' in response.data
        
        # Assert: Verify NO orphaned records in database
        assert Exam.objects.count() == 0, "Exam record should be rolled back"
        assert Booklet.objects.count() == 0, "Booklet records should be rolled back"
        assert Copy.objects.count() == 0, "Copy records should be rolled back"
        
        # Assert: Verify NO orphaned files in media directory
        exam_source_dir = os.path.join(settings.MEDIA_ROOT, 'exams/source')
        if os.path.exists(exam_source_dir):
            files = os.listdir(exam_source_dir)
            assert len(files) == 0, f"No orphaned files should exist, found: {files}"
    
    def test_upload_booklet_creation_failure_rollback(self, teacher_client, settings):
        """
        Test that if Copy.objects.create() fails, entire transaction rolls back.
        
        Expected behavior:
        - Transaction rolls back completely
        - Exam count remains 0
        - Booklet count remains 0
        - Copy count remains 0
        - No orphaned file in media
        """
        # Arrange: Create valid PDF file
        pdf_file = get_valid_pdf_file(pages=4, filename="test_exam_copy_fail.pdf")
        
        upload_data = {
            'name': 'Test Exam - Copy Creation Failure',
            'date': '2026-06-15',
            'pdf_source': pdf_file,
            'pages_per_booklet': 4
        }
        
        # Verify initial state
        assert Exam.objects.count() == 0
        assert Booklet.objects.count() == 0
        assert Copy.objects.count() == 0
        
        # Act: Mock Copy.objects.create() to raise exception
        with patch('exams.models.Copy.objects.create') as mock_copy_create:
            mock_copy_create.side_effect = RuntimeError("Simulated Copy creation failure")
            
            response = teacher_client.post('/api/exams/upload/', upload_data, format='multipart')
        
        # Assert: Verify response indicates failure
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert 'error' in response.data
        
        # Assert: Verify NO orphaned records in database
        assert Exam.objects.count() == 0, "Exam record should be rolled back"
        assert Booklet.objects.count() == 0, "Booklet records should be rolled back"
        assert Copy.objects.count() == 0, "Copy records should be rolled back"
        
        # Assert: Verify NO orphaned files in media directory
        exam_source_dir = os.path.join(settings.MEDIA_ROOT, 'exams/source')
        if os.path.exists(exam_source_dir):
            files = os.listdir(exam_source_dir)
            assert len(files) == 0, f"No orphaned files should exist, found: {files}"
    
    def test_upload_file_cleanup_on_failure(self, teacher_client, settings):
        """
        Test that uploaded file is deleted from filesystem when processing fails.
        
        Expected behavior:
        - If exception occurs after file upload, file should be cleaned up
        - media/exams/source/ directory should be empty
        - No orphaned PDF files
        """
        # Arrange: Create valid PDF file
        pdf_file = get_valid_pdf_file(pages=4, filename="test_cleanup.pdf")
        
        upload_data = {
            'name': 'Test Exam - File Cleanup',
            'date': '2026-06-15',
            'pdf_source': pdf_file,
            'pages_per_booklet': 4
        }
        
        # Act: Mock processing to fail after file upload
        with patch('processing.services.pdf_splitter.PDFSplitter.split_exam') as mock_split:
            mock_split.side_effect = RuntimeError("Simulated failure for cleanup test")
            
            response = teacher_client.post('/api/exams/upload/', upload_data, format='multipart')
        
        # Assert: Verify failure response
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        
        # Assert: Verify file was cleaned up
        exam_source_dir = os.path.join(settings.MEDIA_ROOT, 'exams/source')
        
        if os.path.exists(exam_source_dir):
            files = os.listdir(exam_source_dir)
            assert len(files) == 0, (
                f"Uploaded file should be cleaned up on failure. "
                f"Found orphaned files: {files}"
            )
        
        # Assert: Verify no orphaned database records
        assert Exam.objects.count() == 0
        assert Booklet.objects.count() == 0
        assert Copy.objects.count() == 0
    
    def test_upload_serializer_save_failure_rollback(self, teacher_client, settings):
        """
        Test that if serializer.save() fails unexpectedly, transaction rolls back.
        
        Expected behavior:
        - No Exam record created
        - No files left in media directory
        """
        # Arrange: Create valid PDF file
        pdf_file = get_valid_pdf_file(pages=4, filename="test_serializer_fail.pdf")
        
        upload_data = {
            'name': 'Test Exam - Serializer Save Failure',
            'date': '2026-06-15',
            'pdf_source': pdf_file,
            'pages_per_booklet': 4
        }
        
        # Verify initial state
        assert Exam.objects.count() == 0
        
        # Act: Mock Exam.save() to raise exception during serializer.save()
        with patch('exams.models.Exam.save') as mock_exam_save:
            mock_exam_save.side_effect = RuntimeError("Database save failure")
            
            response = teacher_client.post('/api/exams/upload/', upload_data, format='multipart')
        
        # Assert: Verify failure response
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        
        # Assert: Verify no orphaned records
        assert Exam.objects.count() == 0, "Exam should not be created"
        assert Booklet.objects.count() == 0
        assert Copy.objects.count() == 0
        
        # Assert: Verify no orphaned files
        exam_source_dir = os.path.join(settings.MEDIA_ROOT, 'exams/source')
        if os.path.exists(exam_source_dir):
            files = os.listdir(exam_source_dir)
            assert len(files) == 0, f"No orphaned files should exist, found: {files}"
    
    def test_upload_booklet_add_failure_rollback(self, teacher_client, settings):
        """
        Test that if copy.booklets.add() fails, entire transaction rolls back.
        
        Expected behavior:
        - Transaction rolls back completely
        - All records and files cleaned up
        """
        # Arrange: Create valid PDF file
        pdf_file = get_valid_pdf_file(pages=4, filename="test_booklet_add_fail.pdf")
        
        upload_data = {
            'name': 'Test Exam - Booklet Add Failure',
            'date': '2026-06-15',
            'pdf_source': pdf_file,
            'pages_per_booklet': 4
        }
        
        # Verify initial state
        assert Exam.objects.count() == 0
        assert Booklet.objects.count() == 0
        assert Copy.objects.count() == 0
        
        # Act: Mock copy.booklets.add() to raise exception
        # We need to mock the ManyToManyField's add method
        original_create = Copy.objects.create
        
        def create_with_failing_add(*args, **kwargs):
            copy = original_create(*args, **kwargs)
            # Patch the add method to fail
            original_add = copy.booklets.add
            def failing_add(*add_args, **add_kwargs):
                raise RuntimeError("Simulated booklet.add() failure")
            copy.booklets.add = failing_add
            return copy
        
        with patch('exams.models.Copy.objects.create', side_effect=create_with_failing_add):
            response = teacher_client.post('/api/exams/upload/', upload_data, format='multipart')
        
        # Assert: Verify failure response
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        
        # Assert: Verify no orphaned records
        assert Exam.objects.count() == 0, "Exam should be rolled back"
        assert Booklet.objects.count() == 0, "Booklets should be rolled back"
        assert Copy.objects.count() == 0, "Copies should be rolled back"
        
        # Assert: Verify no orphaned files
        exam_source_dir = os.path.join(settings.MEDIA_ROOT, 'exams/source')
        if os.path.exists(exam_source_dir):
            files = os.listdir(exam_source_dir)
            assert len(files) == 0, f"No orphaned files should exist, found: {files}"
    
    def test_upload_partial_booklet_creation_rollback(self, teacher_client, settings):
        """
        Test that if PDFSplitter creates some booklets but then fails, all are rolled back.
        
        Expected behavior:
        - Even partial booklet creation is rolled back
        - Database is clean (0 records)
        """
        # Arrange: Create valid PDF with multiple booklets (8 pages = 2 booklets)
        pdf_file = get_valid_pdf_file(pages=8, filename="test_partial_booklets.pdf")
        
        upload_data = {
            'name': 'Test Exam - Partial Booklet Creation',
            'date': '2026-06-15',
            'pdf_source': pdf_file,
            'pages_per_booklet': 4
        }
        
        # Verify initial state
        assert Exam.objects.count() == 0
        assert Booklet.objects.count() == 0
        assert Copy.objects.count() == 0
        
        # Act: Mock PDFSplitter to create one booklet successfully, then fail
        with patch('processing.services.pdf_splitter.PDFSplitter.split_exam') as mock_split:
            # Simulate creating one booklet then failing
            def partial_split(exam):
                # Create one booklet (this should be rolled back)
                Booklet.objects.create(
                    exam=exam,
                    start_page=1,
                    end_page=4
                )
                # Then raise exception
                raise RuntimeError("Failed after creating partial booklets")
            
            mock_split.side_effect = partial_split
            
            response = teacher_client.post('/api/exams/upload/', upload_data, format='multipart')
        
        # Assert: Verify failure response
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        
        # Assert: Verify ALL records rolled back (including partially created booklet)
        assert Exam.objects.count() == 0, "Exam should be rolled back"
        assert Booklet.objects.count() == 0, "Partial booklets should be rolled back"
        assert Copy.objects.count() == 0, "Copies should be rolled back"
        
        # Assert: Verify no orphaned files
        exam_source_dir = os.path.join(settings.MEDIA_ROOT, 'exams/source')
        if os.path.exists(exam_source_dir):
            files = os.listdir(exam_source_dir)
            assert len(files) == 0, f"No orphaned files should exist, found: {files}"
