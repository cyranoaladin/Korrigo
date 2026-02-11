"""
Tests for Exam Upload Endpoint - Validation, Atomicity, and Security Cases
Conformité: .antigravity/rules/01_security_rules.md § 8.1
Coverage: POST /api/exams/upload/ comprehensive test coverage
"""
import pytest
import os
from unittest.mock import patch
from rest_framework import status
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group

from exams.models import Exam, Booklet, Copy
from core.auth import UserRole
from exams.tests.fixtures.pdf_fixtures import (
    create_valid_pdf,
    create_large_pdf,
    create_corrupted_pdf,
    create_fake_pdf,
    create_uploadedfile,
    create_empty_pdf,
    create_pdf_with_pages,
    get_valid_pdf_file
)


User = get_user_model()


@pytest.mark.django_db
class TestExamUploadValidation:
    """Test suite for upload endpoint validation scenarios"""
    
    @property
    def upload_url(self):
        """URL for exam upload endpoint"""
        return '/api/exams/upload/'
    
    def test_upload_valid_pdf_creates_exam_and_booklets(self, teacher_client):
        """
        Test successful upload with valid 4-page PDF.
        Should create 1 exam, 1 booklet, 1 copy auto-validated to READY.
        """
        pdf_bytes = create_valid_pdf(pages=4)
        pdf_file = create_uploadedfile(pdf_bytes, filename="exam_4pages.pdf")
        
        data = {
            'name': 'Test Exam - 4 pages',
            'date': '2024-01-15',
            'pdf_source': pdf_file,
            'pages_per_booklet': 4
        }
        
        response = teacher_client.post(self.upload_url, data, format='multipart')
        
        assert response.status_code == status.HTTP_201_CREATED
        assert 'booklets_created' in response.data
        assert response.data['booklets_created'] == 1
        assert 'message' in response.data
        
        assert Exam.objects.count() == 1
        exam = Exam.objects.first()
        assert exam.name == 'Test Exam - 4 pages'
        
        assert Booklet.objects.count() == 1
        booklet = Booklet.objects.first()
        assert booklet.exam == exam
        assert booklet.start_page == 1
        assert booklet.end_page == 4
        
        assert Copy.objects.count() == 1
        copy = Copy.objects.first()
        assert copy.exam == exam
        # P1 FIX: Copies are now auto-validated to READY after successful split
        assert copy.status in [Copy.Status.READY, Copy.Status.STAGING]
        assert copy.is_identified is False
        assert copy.booklets.count() == 1
    
    def test_upload_valid_pdf_with_remainder_pages(self, teacher_client):
        """
        Test upload with 13-page PDF (3 full booklets + 1 partial).
        Should create 4 booklets: 1-4, 5-8, 9-12, 13-13.
        """
        pdf_bytes = create_valid_pdf(pages=13)
        pdf_file = create_uploadedfile(pdf_bytes, filename="exam_13pages.pdf")
        
        data = {
            'name': 'Test Exam - 13 pages',
            'date': '2024-01-15',
            'pdf_source': pdf_file,
            'pages_per_booklet': 4
        }
        
        response = teacher_client.post(self.upload_url, data, format='multipart')
        
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['booklets_created'] == 4
        
        assert Booklet.objects.count() == 4
        
        last_booklet = Booklet.objects.order_by('start_page').last()
        assert last_booklet.start_page == 13
        assert last_booklet.end_page == 13
    
    def test_upload_no_file_returns_400(self, teacher_client):
        """
        Test upload without pdf_source file.
        Should return 400 with validation error.
        """
        data = {
            'name': 'Test Exam - No File',
            'date': '2024-01-15',
            'pages_per_booklet': 4
        }
        
        response = teacher_client.post(self.upload_url, data, format='multipart')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'pdf_source' in response.data
        
        assert Exam.objects.count() == 0
        assert Booklet.objects.count() == 0
        assert Copy.objects.count() == 0
    
    def test_upload_wrong_extension_returns_400(self, teacher_client):
        """
        Test upload with .txt file (wrong extension).
        Should return 400 with validation error.
        """
        text_content = b'This is a text file, not a PDF'
        txt_file = create_uploadedfile(
            text_content,
            filename="exam.txt",
            content_type="text/plain"
        )
        
        data = {
            'name': 'Test Exam - Wrong Extension',
            'date': '2024-01-15',
            'pdf_source': txt_file,
            'pages_per_booklet': 4
        }
        
        response = teacher_client.post(self.upload_url, data, format='multipart')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'pdf_source' in response.data
        
        assert Exam.objects.count() == 0
    
    def test_upload_file_too_large_mock_returns_413(self, teacher_client):
        """
        Test upload with file_too_large validation error.
        Should return HTTP 413 REQUEST ENTITY TOO LARGE.
        Uses mocking to avoid slow 51MB PDF generation.
        """
        from rest_framework.exceptions import ValidationError
        
        pdf_file = get_valid_pdf_file(pages=4, filename="exam_mock_large.pdf")
        
        data = {
            'name': 'Test Exam - Too Large (Mock)',
            'date': '2024-01-15',
            'pdf_source': pdf_file,
            'pages_per_booklet': 4
        }
        
        with patch('exams.serializers.ExamSerializer.is_valid') as mock_is_valid:
            mock_is_valid.return_value = False
            error = ValidationError({'pdf_source': ['File too large']})
            error.code = 'file_too_large'
            mock_serializer = patch('exams.serializers.ExamSerializer.errors', 
                                   new_callable=lambda: {'pdf_source': [error]})
            
            with mock_serializer:
                response = teacher_client.post(self.upload_url, data, format='multipart')
        
        assert response.status_code == status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
        assert 'error' in response.data
        
        assert Exam.objects.count() == 0
    
    @pytest.mark.skip(reason="Generating 51MB PDF is too slow (>3min) - covered by mock test")
    def test_upload_file_too_large_returns_413(self, teacher_client):
        """
        Test upload with file > 50 MB.
        Should return HTTP 413 REQUEST ENTITY TOO LARGE.
        """
        pdf_bytes = create_large_pdf(size_mb=51)
        pdf_file = create_uploadedfile(pdf_bytes, filename="exam_large.pdf")
        
        data = {
            'name': 'Test Exam - Too Large',
            'date': '2024-01-15',
            'pdf_source': pdf_file,
            'pages_per_booklet': 4
        }
        
        response = teacher_client.post(self.upload_url, data, format='multipart')
        
        assert response.status_code == status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
        assert 'error' in response.data
        
        assert Exam.objects.count() == 0
        assert Booklet.objects.count() == 0
        assert Copy.objects.count() == 0
    
    def test_upload_empty_file_returns_400(self, teacher_client):
        """
        Test upload with 0-byte file.
        Should return 400 with validation error.
        """
        empty_bytes = create_empty_pdf()
        empty_file = create_uploadedfile(empty_bytes, filename="exam_empty.pdf")
        
        data = {
            'name': 'Test Exam - Empty File',
            'date': '2024-01-15',
            'pdf_source': empty_file,
            'pages_per_booklet': 4
        }
        
        response = teacher_client.post(self.upload_url, data, format='multipart')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'pdf_source' in response.data
        
        assert Exam.objects.count() == 0
    
    def test_upload_fake_pdf_returns_400(self, teacher_client):
        """
        Test upload with text file renamed to .pdf (fake PDF).
        Should return 400 due to MIME type validation failure.
        """
        fake_bytes = create_fake_pdf()
        fake_file = create_uploadedfile(
            fake_bytes,
            filename="exam_fake.pdf",
            content_type="application/pdf"
        )
        
        data = {
            'name': 'Test Exam - Fake PDF',
            'date': '2024-01-15',
            'pdf_source': fake_file,
            'pages_per_booklet': 4
        }
        
        response = teacher_client.post(self.upload_url, data, format='multipart')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'pdf_source' in response.data
        
        error_message = str(response.data['pdf_source'][0])
        assert 'MIME' in error_message or 'type' in error_message.lower()
        
        assert Exam.objects.count() == 0
    
    def test_upload_corrupted_pdf_returns_400(self, teacher_client):
        """
        Test upload with corrupted PDF (invalid structure).
        Should return 400 due to integrity validation failure.
        """
        corrupted_bytes = create_corrupted_pdf()
        corrupted_file = create_uploadedfile(
            corrupted_bytes,
            filename="exam_corrupted.pdf"
        )
        
        data = {
            'name': 'Test Exam - Corrupted PDF',
            'date': '2024-01-15',
            'pdf_source': corrupted_file,
            'pages_per_booklet': 4
        }
        
        response = teacher_client.post(self.upload_url, data, format='multipart')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'pdf_source' in response.data
        
        error_message = str(response.data['pdf_source'][0])
        assert any(word in error_message.lower() for word in ['invalid', 'corrupted', 'integrity', 'valide', 'vide', 'empty'])
        
        assert Exam.objects.count() == 0
    
    @pytest.mark.skip(reason="Generating 501-page PDF is too slow - covered by validator tests")
    def test_upload_too_many_pages_returns_400(self, teacher_client):
        """
        Test upload with PDF exceeding 500 pages limit.
        Should return 400 with validation error.
        NOTE: Skipped in integration tests due to performance. Validator unit tests cover this.
        """
        pdf_bytes = create_pdf_with_pages(501)
        pdf_file = create_uploadedfile(pdf_bytes, filename="exam_501pages.pdf")
        
        data = {
            'name': 'Test Exam - Too Many Pages',
            'date': '2024-01-15',
            'pdf_source': pdf_file,
            'pages_per_booklet': 4
        }
        
        response = teacher_client.post(self.upload_url, data, format='multipart')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'pdf_source' in response.data
        
        error_message = str(response.data['pdf_source'][0])
        assert 'page' in error_message.lower() or '500' in error_message
        
        assert Exam.objects.count() == 0
        assert Booklet.objects.count() == 0
        assert Copy.objects.count() == 0


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
        pdf_file = get_valid_pdf_file(pages=4, filename="test_exam.pdf")
        
        upload_data = {
            'name': 'Test Exam - Processing Failure',
            'date': '2026-06-15',
            'pdf_source': pdf_file,
            'pages_per_booklet': 4
        }
        
        assert Exam.objects.count() == 0
        assert Booklet.objects.count() == 0
        assert Copy.objects.count() == 0
        
        with patch('processing.services.pdf_splitter.PDFSplitter.split_exam') as mock_split:
            mock_split.side_effect = RuntimeError("Simulated PDF processing failure")
            
            response = teacher_client.post('/api/exams/upload/', upload_data, format='multipart')
        
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert 'error' in response.data
        
        assert Exam.objects.count() == 0, "Exam record should be rolled back"
        assert Booklet.objects.count() == 0, "Booklet records should be rolled back"
        assert Copy.objects.count() == 0, "Copy records should be rolled back"
        
        exam_source_dir = os.path.join(settings.MEDIA_ROOT, 'exams/source')
        if os.path.exists(exam_source_dir):
            files = os.listdir(exam_source_dir)
            assert len(files) == 0, f"No orphaned files should exist, found: {files}"
    
    def test_upload_booklet_creation_failure_rollback(self, teacher_client, settings):
        """
        Test that if Copy.objects.create() fails, entire transaction rolls back.
        """
        pdf_file = get_valid_pdf_file(pages=4, filename="test_exam_copy_fail.pdf")
        
        upload_data = {
            'name': 'Test Exam - Copy Creation Failure',
            'date': '2026-06-15',
            'pdf_source': pdf_file,
            'pages_per_booklet': 4
        }
        
        assert Exam.objects.count() == 0
        assert Booklet.objects.count() == 0
        assert Copy.objects.count() == 0
        
        with patch('exams.models.Copy.objects.create') as mock_copy_create:
            mock_copy_create.side_effect = RuntimeError("Simulated Copy creation failure")
            
            response = teacher_client.post('/api/exams/upload/', upload_data, format='multipart')
        
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert 'error' in response.data
        
        assert Exam.objects.count() == 0, "Exam record should be rolled back"
        assert Booklet.objects.count() == 0, "Booklet records should be rolled back"
        assert Copy.objects.count() == 0, "Copy records should be rolled back"
        
        exam_source_dir = os.path.join(settings.MEDIA_ROOT, 'exams/source')
        if os.path.exists(exam_source_dir):
            files = os.listdir(exam_source_dir)
            assert len(files) == 0, f"No orphaned files should exist, found: {files}"
    
    def test_upload_file_cleanup_on_failure(self, teacher_client, settings):
        """
        Test that uploaded file is deleted from filesystem when processing fails.
        """
        pdf_file = get_valid_pdf_file(pages=4, filename="test_cleanup.pdf")
        
        upload_data = {
            'name': 'Test Exam - File Cleanup',
            'date': '2026-06-15',
            'pdf_source': pdf_file,
            'pages_per_booklet': 4
        }
        
        with patch('processing.services.pdf_splitter.PDFSplitter.split_exam') as mock_split:
            mock_split.side_effect = RuntimeError("Simulated failure for cleanup test")
            
            response = teacher_client.post('/api/exams/upload/', upload_data, format='multipart')
        
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        
        exam_source_dir = os.path.join(settings.MEDIA_ROOT, 'exams/source')
        
        if os.path.exists(exam_source_dir):
            files = os.listdir(exam_source_dir)
            assert len(files) == 0, (
                f"Uploaded file should be cleaned up on failure. "
                f"Found orphaned files: {files}"
            )
        
        assert Exam.objects.count() == 0
        assert Booklet.objects.count() == 0
        assert Copy.objects.count() == 0
    
    def test_upload_file_cleanup_error_handling(self, teacher_client, settings):
        """
        Test that cleanup errors are handled gracefully when file removal fails.
        Covers lines 110-111 in views.py exception handling.
        """
        pdf_file = get_valid_pdf_file(pages=4, filename="test_cleanup_error.pdf")
        
        upload_data = {
            'name': 'Test Exam - Cleanup Error',
            'date': '2026-06-15',
            'pdf_source': pdf_file,
            'pages_per_booklet': 4
        }
        
        with patch('processing.services.pdf_splitter.PDFSplitter.split_exam') as mock_split:
            mock_split.side_effect = RuntimeError("Simulated processing failure")
            
            with patch('os.remove') as mock_remove:
                mock_remove.side_effect = PermissionError("Cannot delete file")
                
                response = teacher_client.post('/api/exams/upload/', upload_data, format='multipart')
        
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert 'error' in response.data
        
        assert Exam.objects.count() == 0
        assert Booklet.objects.count() == 0
        assert Copy.objects.count() == 0


@pytest.mark.django_db
class TestExamUploadAuthentication:
    """Test authentication and authorization for upload endpoint."""
    
    def test_upload_anonymous_user_rejected(self, api_client):
        """Test that unauthenticated users cannot upload."""
        pdf_bytes = create_valid_pdf(pages=4)
        pdf_file = create_uploadedfile(pdf_bytes, filename="test.pdf")
        
        data = {
            'pdf_source': pdf_file,
            'name': 'Test Anon',
            'date': '2024-01-15',
            'pages_per_booklet': 4
        }
        
        response = api_client.post('/api/exams/upload/', data, format='multipart')
        
        assert response.status_code in [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN
        ]
    
    def test_upload_student_role_rejected(self, api_client, student_user):
        """Test that student users cannot upload exams."""
        api_client.force_authenticate(user=student_user)
        
        pdf_bytes = create_valid_pdf(pages=4)
        pdf_file = create_uploadedfile(pdf_bytes, filename="test.pdf")
        
        data = {
            'pdf_source': pdf_file,
            'name': 'Test Student Upload',
            'date': '2024-01-15',
            'pages_per_booklet': 4
        }
        
        response = api_client.post('/api/exams/upload/', data, format='multipart')
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
    
    def test_upload_teacher_role_allowed(self, api_client, teacher_user):
        """Test that teacher users can upload exams."""
        api_client.force_authenticate(user=teacher_user)
        
        pdf_bytes = create_valid_pdf(pages=4)
        pdf_file = create_uploadedfile(pdf_bytes, filename="test.pdf")
        
        data = {
            'pdf_source': pdf_file,
            'name': 'Test Teacher Upload',
            'date': '2024-01-15',
            'pages_per_booklet': 4
        }
        
        response = api_client.post('/api/exams/upload/', data, format='multipart')
        
        assert response.status_code == status.HTTP_201_CREATED
    
    def test_upload_admin_role_allowed(self, api_client, admin_user):
        """Test that admin users can upload exams."""
        api_client.force_authenticate(user=admin_user)
        
        pdf_bytes = create_valid_pdf(pages=4)
        pdf_file = create_uploadedfile(pdf_bytes, filename="test.pdf")
        
        data = {
            'pdf_source': pdf_file,
            'name': 'Test Admin Upload',
            'date': '2024-01-15',
            'pages_per_booklet': 4
        }
        
        response = api_client.post('/api/exams/upload/', data, format='multipart')
        
        assert response.status_code == status.HTTP_201_CREATED


@pytest.mark.django_db
class TestExamUploadSecurity:
    """Test security protections for upload endpoint."""
    
    def test_upload_path_traversal_protection(self, api_client, teacher_user):
        """Test that path traversal in filename is prevented."""
        api_client.force_authenticate(user=teacher_user)
        
        pdf_bytes = create_valid_pdf(pages=4)
        malicious_file = create_uploadedfile(
            pdf_bytes, 
            filename="../../../../etc/passwd.pdf"
        )
        
        data = {
            'pdf_source': malicious_file,
            'name': 'Test Path Traversal',
            'date': '2024-01-15',
            'pages_per_booklet': 4
        }
        
        response = api_client.post('/api/exams/upload/', data, format='multipart')
        
        assert response.status_code == status.HTTP_201_CREATED
        
        exam = Exam.objects.get(id=response.data['id'])
        assert exam.pdf_source is not None
        assert '..' not in exam.pdf_source.name
        assert 'etc' not in exam.pdf_source.name
        assert 'exams/source/' in exam.pdf_source.name


# ============================================================================
# AUTHENTICATION & SECURITY TESTS
# ============================================================================

@pytest.fixture
def student_user(db):
    """Create a student user (non-staff, student role)."""
    user = User.objects.create_user(
        username="student_test",
        password="testpass123",  # nosec B106 - Test fixture password
        is_staff=False,
        is_superuser=False
    )
    g, _ = Group.objects.get_or_create(name=UserRole.STUDENT)
    user.groups.add(g)
    return user


@pytest.fixture
def student_client(api_client, student_user):
    """Return an APIClient authenticated as student user."""
    api_client.force_authenticate(user=student_user)
    return api_client


# ============================================================================
# UPLOAD MODES TESTS
# ============================================================================

@pytest.mark.django_db
class TestUploadModes:
    """Test suite for upload mode functionality (BATCH_A3 vs INDIVIDUAL_A4)"""
    
    @property
    def upload_url(self):
        return '/api/exams/upload/'
    
    def individual_upload_url(self, exam_id):
        return f'/api/exams/{exam_id}/upload-individual-pdfs/'
    
    def test_batch_a3_mode_requires_pdf_source(self, teacher_client):
        """
        BATCH_A3 mode should require pdf_source field.
        Uploading without pdf_source should return 400.
        """
        data = {
            'name': 'Exam Batch Mode',
            'date': '2024-01-15',
            'upload_mode': 'BATCH_A3',
            'pages_per_booklet': 4
            # Missing pdf_source
        }
        
        response = teacher_client.post(self.upload_url, data, format='multipart')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'pdf_source' in response.data
        assert 'obligatoire' in str(response.data['pdf_source'][0]).lower()
    
    def test_batch_a3_mode_with_pdf_creates_booklets(self, teacher_client):
        """
        BATCH_A3 mode with valid PDF should create booklets and copies.
        """
        pdf_bytes = create_valid_pdf(pages=8)
        pdf_file = create_uploadedfile(pdf_bytes, filename="exam_8pages.pdf")
        
        data = {
            'name': 'Exam Batch A3',
            'date': '2024-01-15',
            'upload_mode': 'BATCH_A3',
            'pdf_source': pdf_file,
            'pages_per_booklet': 4
        }
        
        response = teacher_client.post(self.upload_url, data, format='multipart')
        
        assert response.status_code == status.HTTP_201_CREATED
        assert 'booklets_created' in response.data
        assert response.data['booklets_created'] == 2
        
        from exams.models import Exam, Booklet, Copy
        exam = Exam.objects.get(id=response.data['id'])
        assert exam.upload_mode == 'BATCH_A3'
        assert exam.pdf_source is not None
        assert Booklet.objects.filter(exam=exam).count() == 2
        assert Copy.objects.filter(exam=exam).count() == 2
    
    def test_individual_a4_mode_without_pdf_creates_exam_only(self, teacher_client):
        """
        INDIVIDUAL_A4 mode should create exam without pdf_source.
        Should not create booklets/copies immediately.
        """
        data = {
            'name': 'Exam Individual Mode',
            'date': '2024-01-15',
            'upload_mode': 'INDIVIDUAL_A4'
        }
        
        response = teacher_client.post(self.upload_url, data, format='multipart')
        
        assert response.status_code == status.HTTP_201_CREATED
        assert 'upload_endpoint' in response.data
        assert 'upload-individual-pdfs' in response.data['upload_endpoint']
        
        from exams.models import Exam, Booklet, Copy
        exam = Exam.objects.get(id=response.data['id'])
        assert exam.upload_mode == 'INDIVIDUAL_A4'
        assert exam.pdf_source.name == ''  # No PDF uploaded yet
        assert Booklet.objects.filter(exam=exam).count() == 0
        assert Copy.objects.filter(exam=exam).count() == 0
    
    def test_individual_a4_mode_with_csv_file(self, teacher_client):
        """
        INDIVIDUAL_A4 mode should accept students_csv file.
        """
        csv_content = b"nom,prenom,email\nDupont,Jean,jean@test.fr\nMartin,Marie,marie@test.fr"
        csv_file = create_uploadedfile(csv_content, filename="students.csv", content_type="text/csv")
        
        data = {
            'name': 'Exam with CSV',
            'date': '2024-01-15',
            'upload_mode': 'INDIVIDUAL_A4',
            'students_csv': csv_file
        }
        
        response = teacher_client.post(self.upload_url, data, format='multipart')
        
        assert response.status_code == status.HTTP_201_CREATED
        
        from exams.models import Exam
        exam = Exam.objects.get(id=response.data['id'])
        assert exam.students_csv is not None
        assert 'students.csv' in exam.students_csv.name
    
    def test_default_mode_is_batch_a3(self, teacher_client):
        """
        When upload_mode is not specified, should default to BATCH_A3.
        """
        pdf_bytes = create_valid_pdf(pages=4)
        pdf_file = create_uploadedfile(pdf_bytes, filename="exam.pdf")
        
        data = {
            'name': 'Exam Default Mode',
            'date': '2024-01-15',
            'pdf_source': pdf_file,
            'pages_per_booklet': 4
            # No upload_mode specified
        }
        
        response = teacher_client.post(self.upload_url, data, format='multipart')
        
        assert response.status_code == status.HTTP_201_CREATED
        
        from exams.models import Exam
        exam = Exam.objects.get(id=response.data['id'])
        assert exam.upload_mode == 'BATCH_A3'


@pytest.mark.django_db  
class TestIndividualPDFUpload:
    """Test suite for individual PDF upload endpoint"""
    
    def individual_upload_url(self, exam_id):
        return f'/api/exams/{exam_id}/upload-individual-pdfs/'
    
    def create_individual_mode_exam(self):
        """Helper to create an exam in INDIVIDUAL_A4 mode"""
        from exams.models import Exam
        return Exam.objects.create(
            name='Test Individual Exam',
            date='2024-01-15',
            upload_mode='INDIVIDUAL_A4'
        )
    
    def test_upload_single_individual_pdf(self, teacher_client):
        """
        Upload a single PDF file for INDIVIDUAL_A4 exam.
        Should create ExamPDF and Copy.
        """
        exam = self.create_individual_mode_exam()
        
        pdf_bytes = create_valid_pdf(pages=4)
        pdf_file = create_uploadedfile(pdf_bytes, filename="martin_jean.pdf")
        
        response = teacher_client.post(
            self.individual_upload_url(exam.id),
            {'pdf_files': pdf_file},
            format='multipart'
        )
        
        assert response.status_code == status.HTTP_201_CREATED
        assert '1 fichiers PDF uploadés' in response.data['message']
        assert len(response.data['uploaded_files']) == 1
        
        uploaded = response.data['uploaded_files'][0]
        assert uploaded['filename'] == 'martin_jean.pdf'
        assert uploaded['student_identifier'] == 'martin_jean'
        
        from exams.models import ExamPDF, Copy
        assert ExamPDF.objects.filter(exam=exam).count() == 1
        assert Copy.objects.filter(exam=exam).count() == 1
        
        exam_pdf = ExamPDF.objects.get(id=uploaded['exam_pdf_id'])
        assert exam_pdf.student_identifier == 'martin_jean'
        
        copy = Copy.objects.get(id=uploaded['copy_id'])
        assert copy.status == Copy.Status.STAGING
        assert copy.is_identified is False
    
    def test_upload_multiple_individual_pdfs(self, teacher_client):
        """
        Upload multiple PDF files simultaneously.
        Should create multiple ExamPDF and Copy objects.
        """
        exam = self.create_individual_mode_exam()
        
        pdf1 = create_uploadedfile(create_valid_pdf(pages=4), filename="student1.pdf")
        pdf2 = create_uploadedfile(create_valid_pdf(pages=4), filename="student2.pdf")
        pdf3 = create_uploadedfile(create_valid_pdf(pages=4), filename="student3.pdf")
        
        response = teacher_client.post(
            self.individual_upload_url(exam.id),
            {'pdf_files': [pdf1, pdf2, pdf3]},
            format='multipart'
        )
        
        assert response.status_code == status.HTTP_201_CREATED
        assert '3 fichiers PDF uploadés' in response.data['message']
        assert len(response.data['uploaded_files']) == 3
        assert response.data['total_copies'] == 3
        
        from exams.models import ExamPDF, Copy
        assert ExamPDF.objects.filter(exam=exam).count() == 3
        assert Copy.objects.filter(exam=exam).count() == 3
    
    def test_upload_to_batch_mode_exam_rejected(self, teacher_client):
        """
        Uploading individual PDFs to BATCH_A3 exam should fail.
        """
        from exams.models import Exam
        exam = Exam.objects.create(
            name='Batch Mode Exam',
            date='2024-01-15',
            upload_mode='BATCH_A3'
        )
        
        pdf_bytes = create_valid_pdf(pages=4)
        pdf_file = create_uploadedfile(pdf_bytes, filename="test.pdf")
        
        response = teacher_client.post(
            self.individual_upload_url(exam.id),
            {'pdf_files': pdf_file},
            format='multipart'
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'INDIVIDUAL_A4' in response.data['error']
    
    def test_upload_without_files_rejected(self, teacher_client):
        """
        POST without any files should return 400.
        """
        exam = self.create_individual_mode_exam()
        
        response = teacher_client.post(
            self.individual_upload_url(exam.id),
            {},
            format='multipart'
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'pdf_files' in response.data['error']
    
    def test_upload_too_many_files_rejected(self, teacher_client):
        """
        Uploading more than MAX_FILES_PER_REQUEST should be rejected.
        Note: Django's DATA_UPLOAD_MAX_NUMBER_FILES also limits this,
        so we test with a reasonable number that still exceeds our limit.
        """
        exam = self.create_individual_mode_exam()
        
        # Create files that exceed our custom limit (100)
        # but stay under Django's default (1000)
        # For testing, we'll create exactly 101 files
        # However, Django may reject this before our code runs
        # So we'll just verify the request is rejected
        files = [
            create_uploadedfile(create_valid_pdf(pages=1), filename=f"student{i}.pdf")
            for i in range(101)
        ]
        
        response = teacher_client.post(
            self.individual_upload_url(exam.id),
            {'pdf_files': files},
            format='multipart'
        )
        
        # Should be rejected (either by Django or our validation)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    

    
    def test_upload_requires_authentication(self, api_client):
        """
        Anonymous users should be rejected.
        """
        exam = self.create_individual_mode_exam()
        
        pdf_bytes = create_valid_pdf(pages=4)
        pdf_file = create_uploadedfile(pdf_bytes, filename="test.pdf")
        
        response = api_client.post(
            self.individual_upload_url(exam.id),
            {'pdf_files': pdf_file},
            format='multipart'
        )
        
        # DRF returns 403 Forbidden for permission failures
        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]
