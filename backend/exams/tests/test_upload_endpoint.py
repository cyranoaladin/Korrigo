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

from exams.models import Exam, Booklet, Copy
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
        Should create 1 exam, 1 booklet, 1 copy in STAGING.
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
        assert copy.status == Copy.Status.STAGING
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
        assert any(word in error_message.lower() for word in ['invalid', 'corrupted', 'integrity', 'valide'])
        
        assert Exam.objects.count() == 0
    
    def test_upload_too_many_pages_returns_400(self, teacher_client):
        """
        Test upload with PDF exceeding 500 pages limit.
        Should return 400 with validation error.
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


@pytest.mark.django_db
class TestUploadEndpointAuth:
    """Test authentication and authorization for upload endpoint."""
    
    def test_upload_anonymous_user_rejected(self, api_client):
        """Anonymous (unauthenticated) user should receive 401 Unauthorized."""
        url = '/api/exams/upload/'
        pdf_file = fixture_valid_small()
        
        response = api_client.post(
            url,
            {
                'name': 'Test Exam',
                'pdf_source': pdf_file,
                'pages_per_booklet': 4,
                'date': date.today().isoformat()
            },
            format='multipart'
        )
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert Exam.objects.count() == 0
    
    def test_upload_student_role_rejected(self, student_client):
        """Student user should receive 403 Forbidden."""
        url = '/api/exams/upload/'
        pdf_file = fixture_valid_small()
        
        response = student_client.post(
            url,
            {
                'name': 'Test Exam',
                'pdf_source': pdf_file,
                'pages_per_booklet': 4,
                'date': date.today().isoformat()
            },
            format='multipart'
        )
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert Exam.objects.count() == 0
    
    def test_upload_teacher_role_allowed(self, teacher_client):
        """Teacher user should be allowed to upload (201 Created)."""
        url = '/api/exams/upload/'
        pdf_file = fixture_valid_small()
        
        response = teacher_client.post(
            url,
            {
                'name': 'Test Exam Teacher',
                'pdf_source': pdf_file,
                'pages_per_booklet': 4,
                'date': date.today().isoformat()
            },
            format='multipart'
        )
        
        assert response.status_code == status.HTTP_201_CREATED
        assert Exam.objects.count() == 1
        assert Exam.objects.first().name == 'Test Exam Teacher'
    
    def test_upload_admin_role_allowed(self, authenticated_client):
        """Admin user should be allowed to upload (201 Created)."""
        url = '/api/exams/upload/'
        pdf_file = fixture_valid_small()
        
        response = authenticated_client.post(
            url,
            {
                'name': 'Test Exam Admin',
                'pdf_source': pdf_file,
                'pages_per_booklet': 4,
                'date': date.today().isoformat()
            },
            format='multipart'
        )
        
        assert response.status_code == status.HTTP_201_CREATED
        assert Exam.objects.count() == 1
        assert Exam.objects.first().name == 'Test Exam Admin'


@pytest.mark.django_db
class TestUploadEndpointSecurity:
    """Test security protections for upload endpoint."""
    
    def test_upload_path_traversal_protection(self, teacher_client, settings):
        """Path traversal in filename should be sanitized."""
        url = '/api/exams/upload/'
        pdf_bytes = create_valid_pdf(pages=4)
        pdf_file = create_uploadedfile(pdf_bytes, filename="../../../../etc/passwd.pdf")
        
        response = teacher_client.post(
            url,
            {
                'name': 'Test Path Traversal',
                'pdf_source': pdf_file,
                'pages_per_booklet': 4,
                'date': date.today().isoformat()
            },
            format='multipart'
        )
        
        assert response.status_code == status.HTTP_201_CREATED
        
        # Verify file was saved in correct location (not traversed)
        exam = Exam.objects.first()
        saved_path = exam.pdf_source.path
        
        # Path should be inside MEDIA_ROOT/exams/source/
        assert settings.MEDIA_ROOT in saved_path
        assert 'exams/source' in saved_path
        
        # Filename should be sanitized (no path traversal)
        filename = os.path.basename(saved_path)
        assert 'passwd.pdf' in filename
        assert '..' not in saved_path
        assert '/etc/' not in saved_path
    
    def test_upload_dangerous_filename_sanitized(self, teacher_client, settings):
        """Dangerous characters in filename should be sanitized."""
        url = '/api/exams/upload/'
        pdf_bytes = create_valid_pdf(pages=4)
        pdf_file = create_uploadedfile(pdf_bytes, filename="exam<script>alert.pdf")
        
        response = teacher_client.post(
            url,
            {
                'name': 'Test Filename Sanitization',
                'pdf_source': pdf_file,
                'pages_per_booklet': 4,
                'date': date.today().isoformat()
            },
            format='multipart'
        )
        
        assert response.status_code == status.HTTP_201_CREATED
        
        # Verify filename is safe
        exam = Exam.objects.first()
        filename = os.path.basename(exam.pdf_source.path)
        
        # Django typically sanitizes or encodes dangerous characters
        assert '<' not in filename or 'script' not in filename
    
    @pytest.mark.skip(reason="Rate limiting requires time-based testing or mocking")
    def test_upload_rate_limit_enforced(self, teacher_client):
        """
        Rate limiting should enforce 20 uploads per hour.
        
        Note: This test is skipped by default as it requires:
        - Time-based testing (freezegun)
        - or Cache backend mocking
        - or 21 actual uploads which is slow
        
        Current rate limit: 20/h (@maybe_ratelimit decorator on ExamUploadView.post)
        """
        url = '/api/exams/upload/'
        
        # Attempt 21 uploads (exceeds 20/h limit)
        for i in range(21):
            pdf_file = fixture_valid_small()
            response = teacher_client.post(
                url,
                {
                    'name': f'Test Exam {i}',
                    'pdf_source': pdf_file,
                    'pages_per_booklet': 4,
                    'date': date.today().isoformat()
                },
                format='multipart'
            )
            
            if i < 20:
                assert response.status_code == status.HTTP_201_CREATED
            else:
                # 21st request should be rate limited
                assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
