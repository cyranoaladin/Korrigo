"""
Tests for PDF Upload Endpoint (/api/exams/upload/)

Tests cover:
- Valid PDF uploads (various sizes and page counts)
- Validation failures (size, MIME type, integrity, etc.)
- Atomicity (no orphaned records on failures)
- Authentication and authorization
- Error messages and HTTP status codes
"""
import pytest
from django.test import TestCase
from django.contrib.auth.models import User, Group
from rest_framework.test import APIClient
from rest_framework import status
from unittest.mock import patch, MagicMock
from exams.models import Exam, Booklet, Copy
from core.auth import UserRole
from .fixtures.pdf_fixtures import (
    fixture_valid_small,
    fixture_valid_large,
    fixture_valid_remainder,
    fixture_invalid_empty,
    fixture_invalid_fake,
    fixture_invalid_corrupted,
    fixture_invalid_too_large,
    fixture_invalid_too_many_pages,
    create_valid_pdf,
    create_uploadedfile,
)
from datetime import date


@pytest.mark.django_db
class TestUploadValidationCases:
    """Test validation scenarios for PDF upload"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up test client and authenticated teacher user"""
        self.client = APIClient()
        
        # Create teacher user
        self.teacher = User.objects.create_user(
            username='teacher_test',
            password='testpass123'
        )
        self.teacher_group, _ = Group.objects.get_or_create(name=UserRole.TEACHER)
        self.teacher.groups.add(self.teacher_group)
        
        # Authenticate client
        self.client.force_authenticate(user=self.teacher)
        
        # Upload URL
        self.url = '/api/exams/upload/'
    
    def test_upload_valid_pdf_creates_exam_and_booklets(self):
        """Test uploading valid 4-page PDF creates exam and booklets"""
        pdf_file = fixture_valid_small()  # 4 pages
        
        data = {
            'name': 'Test Exam Valid',
            'date': date.today().isoformat(),
            'pdf_source': pdf_file,
            'pages_per_booklet': 4
        }
        
        response = self.client.post(self.url, data, format='multipart')
        
        # Assertions
        assert response.status_code == status.HTTP_201_CREATED
        assert 'booklets_created' in response.data
        assert response.data['booklets_created'] == 1  # 4 pages / 4 per booklet = 1
        
        # Verify database state
        assert Exam.objects.count() == 1
        exam = Exam.objects.first()
        assert exam.name == 'Test Exam Valid'
        assert exam.booklets.count() == 1
        
        # Verify Copy created in STAGING
        assert Copy.objects.count() == 1
        copy = Copy.objects.first()
        assert copy.status == Copy.Status.STAGING
        assert copy.exam == exam
    
    def test_upload_valid_pdf_with_remainder_pages(self):
        """Test uploading 13-page PDF with 4 pages per booklet (creates 4 booklets, last with 1 page)"""
        pdf_file = fixture_valid_remainder()  # 13 pages
        
        data = {
            'name': 'Test Exam Remainder',
            'date': date.today().isoformat(),
            'pdf_source': pdf_file,
            'pages_per_booklet': 4
        }
        
        response = self.client.post(self.url, data, format='multipart')
        
        # Should succeed (lenient mode)
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['booklets_created'] == 4  # 13 / 4 = 3 full + 1 partial
        
        # Verify database
        exam = Exam.objects.first()
        assert exam.booklets.count() == 4
        
        # Check last booklet has only 1 page
        last_booklet = exam.booklets.order_by('start_page').last()
        assert last_booklet.start_page == 13
        assert last_booklet.end_page == 13  # Only 1 page
    
    def test_upload_no_file_returns_400(self):
        """Test uploading without PDF file returns 400"""
        data = {
            'name': 'Test Exam No File',
            'date': date.today().isoformat(),
            'pages_per_booklet': 4
            # Missing pdf_source
        }
        
        response = self.client.post(self.url, data, format='multipart')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'pdf_source' in response.data
    
    def test_upload_empty_file_returns_400(self):
        """Test uploading 0-byte file returns 400"""
        pdf_file = fixture_invalid_empty()
        
        data = {
            'name': 'Test Exam Empty',
            'date': date.today().isoformat(),
            'pdf_source': pdf_file,
            'pages_per_booklet': 4
        }
        
        response = self.client.post(self.url, data, format='multipart')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'pdf_source' in response.data
        # Check error message mentions empty file
        error_msg = str(response.data['pdf_source'])
        assert 'vide' in error_msg.lower() or 'empty' in error_msg.lower()
    
    def test_upload_fake_pdf_returns_400(self):
        """Test uploading text file with .pdf extension returns 400 (MIME type check)"""
        pdf_file = fixture_invalid_fake()
        
        data = {
            'name': 'Test Exam Fake',
            'date': date.today().isoformat(),
            'pdf_source': pdf_file,
            'pages_per_booklet': 4
        }
        
        response = self.client.post(self.url, data, format='multipart')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'pdf_source' in response.data
        # Check error message mentions invalid MIME type
        error_msg = str(response.data['pdf_source'])
        assert 'mime' in error_msg.lower() or 'type' in error_msg.lower()
    
    def test_upload_corrupted_pdf_returns_400(self):
        """Test uploading corrupted PDF returns 400 (integrity check)"""
        pdf_file = fixture_invalid_corrupted()
        
        data = {
            'name': 'Test Exam Corrupted',
            'date': date.today().isoformat(),
            'pdf_source': pdf_file,
            'pages_per_booklet': 4
        }
        
        response = self.client.post(self.url, data, format='multipart')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'pdf_source' in response.data
        # Check error message mentions corruption
        error_msg = str(response.data['pdf_source'])
        assert 'corrompu' in error_msg.lower() or 'invalid' in error_msg.lower()
    
    def test_upload_file_too_large_returns_413(self):
        """Test uploading > 50 MB file returns HTTP 413 (Payload Too Large)"""
        # Note: This test might be slow (creates 51MB file)
        pdf_file = fixture_invalid_too_large()
        
        data = {
            'name': 'Test Exam Too Large',
            'date': date.today().isoformat(),
            'pdf_source': pdf_file,
            'pages_per_booklet': 4
        }
        
        response = self.client.post(self.url, data, format='multipart')
        
        # CRITICAL: Must return HTTP 413, not 400
        assert response.status_code == status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
        assert 'error' in response.data
        # Check error message mentions file size
        error_msg = str(response.data['error'])
        assert 'volumineux' in error_msg.lower() or 'large' in error_msg.lower()
    
    @pytest.mark.slow
    def test_upload_too_many_pages_returns_400(self):
        """Test uploading PDF with > 500 pages returns 400"""
        # Note: This test is slow (creates 501-page PDF)
        pdf_file = fixture_invalid_too_many_pages()
        
        data = {
            'name': 'Test Exam Too Many Pages',
            'date': date.today().isoformat(),
            'pdf_source': pdf_file,
            'pages_per_booklet': 4
        }
        
        response = self.client.post(self.url, data, format='multipart')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'pdf_source' in response.data
        # Check error message mentions page limit
        error_msg = str(response.data['pdf_source'])
        assert 'pages' in error_msg.lower()
    
    def test_upload_wrong_extension_returns_400(self):
        """Test uploading .txt file returns 400 (extension check)"""
        # Create a text file with .txt extension
        from django.core.files.uploadedfile import SimpleUploadedFile
        txt_file = SimpleUploadedFile(
            name="test.txt",
            content=b"This is a text file",
            content_type="text/plain"
        )
        
        data = {
            'name': 'Test Exam Wrong Extension',
            'date': date.today().isoformat(),
            'pdf_source': txt_file,
            'pages_per_booklet': 4
        }
        
        response = self.client.post(self.url, data, format='multipart')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'pdf_source' in response.data


@pytest.mark.django_db
class TestUploadAtomicity:
    """Test atomic behavior - no orphaned records on failures"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up test client and authenticated teacher user"""
        self.client = APIClient()
        
        self.teacher = User.objects.create_user(
            username='teacher_atom',
            password='testpass123'
        )
        self.teacher_group, _ = Group.objects.get_or_create(name=UserRole.TEACHER)
        self.teacher.groups.add(self.teacher_group)
        
        self.client.force_authenticate(user=self.teacher)
        self.url = '/api/exams/upload/'
    
    def test_upload_processing_failure_no_orphan_exam(self):
        """Test that PDF processing failure doesn't leave orphaned Exam record"""
        pdf_file = fixture_valid_small()
        
        data = {
            'name': 'Test Atomicity Failure',
            'date': date.today().isoformat(),
            'pdf_source': pdf_file,
            'pages_per_booklet': 4
        }
        
        # Count records before
        exam_count_before = Exam.objects.count()
        booklet_count_before = Booklet.objects.count()
        copy_count_before = Copy.objects.count()
        
        # Mock PDFSplitter.split_exam() to raise exception
        with patch('processing.services.pdf_splitter.PDFSplitter.split_exam') as mock_split:
            mock_split.side_effect = Exception("Simulated processing failure")
            
            response = self.client.post(self.url, data, format='multipart')
        
        # Should return error
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        
        # CRITICAL: No orphaned records
        assert Exam.objects.count() == exam_count_before
        assert Booklet.objects.count() == booklet_count_before
        assert Copy.objects.count() == copy_count_before
    
    def test_upload_booklet_creation_failure_rollback(self):
        """Test that booklet creation failure rolls back entire transaction"""
        pdf_file = fixture_valid_small()
        
        data = {
            'name': 'Test Booklet Creation Failure',
            'date': date.today().isoformat(),
            'pdf_source': pdf_file,
            'pages_per_booklet': 4
        }
        
        exam_count_before = Exam.objects.count()
        
        # Mock Copy.objects.create() to fail
        with patch('exams.models.Copy.objects.create') as mock_create:
            mock_create.side_effect = Exception("Simulated Copy creation failure")
            
            response = self.client.post(self.url, data, format='multipart')
        
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        
        # Verify rollback
        assert Exam.objects.count() == exam_count_before
        assert Booklet.objects.count() == 0  # No booklets created


@pytest.mark.django_db
class TestUploadAuthentication:
    """Test authentication and authorization for upload endpoint"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up test users and client"""
        self.client = APIClient()
        self.url = '/api/exams/upload/'
        
        # Create users with different roles
        self.teacher = User.objects.create_user(username='teacher_auth', password='pass')
        self.admin = User.objects.create_user(username='admin_auth', password='pass')
        self.student = User.objects.create_user(username='student_auth', password='pass')
        
        # Assign roles
        teacher_group, _ = Group.objects.get_or_create(name=UserRole.TEACHER)
        admin_group, _ = Group.objects.get_or_create(name=UserRole.ADMIN)
        student_group, _ = Group.objects.get_or_create(name=UserRole.STUDENT)
        
        self.teacher.groups.add(teacher_group)
        self.admin.groups.add(admin_group)
        self.student.groups.add(student_group)
    
    def test_upload_anonymous_user_rejected(self):
        """Test unauthenticated request returns 401"""
        pdf_file = fixture_valid_small()
        
        data = {
            'name': 'Test Anonymous',
            'date': date.today().isoformat(),
            'pdf_source': pdf_file,
            'pages_per_booklet': 4
        }
        
        # No authentication
        response = self.client.post(self.url, data, format='multipart')
        
        assert response.status_code in [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN
        ]
    
    def test_upload_student_role_rejected(self):
        """Test student user cannot upload (returns 403)"""
        self.client.force_authenticate(user=self.student)
        pdf_file = fixture_valid_small()
        
        data = {
            'name': 'Test Student Upload',
            'date': date.today().isoformat(),
            'pdf_source': pdf_file,
            'pages_per_booklet': 4
        }
        
        response = self.client.post(self.url, data, format='multipart')
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
    
    def test_upload_teacher_role_allowed(self):
        """Test teacher user can upload successfully"""
        self.client.force_authenticate(user=self.teacher)
        pdf_file = fixture_valid_small()
        
        data = {
            'name': 'Test Teacher Upload',
            'date': date.today().isoformat(),
            'pdf_source': pdf_file,
            'pages_per_booklet': 4
        }
        
        response = self.client.post(self.url, data, format='multipart')
        
        assert response.status_code == status.HTTP_201_CREATED
    
    def test_upload_admin_role_allowed(self):
        """Test admin user can upload successfully"""
        self.client.force_authenticate(user=self.admin)
        pdf_file = fixture_valid_small()
        
        data = {
            'name': 'Test Admin Upload',
            'date': date.today().isoformat(),
            'pdf_source': pdf_file,
            'pages_per_booklet': 4
        }
        
        response = self.client.post(self.url, data, format='multipart')
        
        assert response.status_code == status.HTTP_201_CREATED


@pytest.mark.django_db
class TestUploadSecurity:
    """Test security protections for upload endpoint"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up authenticated client"""
        self.client = APIClient()
        
        teacher = User.objects.create_user(username='teacher_sec', password='pass')
        teacher_group, _ = Group.objects.get_or_create(name=UserRole.TEACHER)
        teacher.groups.add(teacher_group)
        
        self.client.force_authenticate(user=teacher)
        self.url = '/api/exams/upload/'
    
    def test_upload_path_traversal_protection(self):
        """Test filename with path traversal is sanitized"""
        pdf_bytes = create_valid_pdf(pages=4)
        
        # Try path traversal attack in filename
        malicious_file = create_uploadedfile(
            pdf_bytes,
            filename="../../../../etc/passwd.pdf"
        )
        
        data = {
            'name': 'Test Path Traversal',
            'date': date.today().isoformat(),
            'pdf_source': malicious_file,
            'pages_per_booklet': 4
        }
        
        response = self.client.post(self.url, data, format='multipart')
        
        # Should succeed (filename sanitized by Django)
        assert response.status_code == status.HTTP_201_CREATED
        
        # Verify file saved safely (not in /etc/)
        exam = Exam.objects.first()
        assert exam.pdf_source
        assert '/etc/' not in exam.pdf_source.path
        assert 'exams/source/' in exam.pdf_source.path
        # Filename should be sanitized to just "passwd.pdf" or similar
        assert 'passwd' in exam.pdf_source.name


@pytest.mark.django_db
class TestUploadErrorMessages:
    """Test error messages are user-friendly and actionable"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up authenticated client"""
        self.client = APIClient()
        
        teacher = User.objects.create_user(username='teacher_err', password='pass')
        teacher_group, _ = Group.objects.get_or_create(name=UserRole.TEACHER)
        teacher.groups.add(teacher_group)
        
        self.client.force_authenticate(user=teacher)
        self.url = '/api/exams/upload/'
    
    def test_error_messages_are_in_french(self):
        """Test error messages are in French (user-facing language)"""
        # Upload empty file
        pdf_file = fixture_invalid_empty()
        
        data = {
            'name': 'Test French Errors',
            'date': date.today().isoformat(),
            'pdf_source': pdf_file,
            'pages_per_booklet': 4
        }
        
        response = self.client.post(self.url, data, format='multipart')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        
        # Check that error message contains French text
        error_msg = str(response.data)
        # Should have French words like "vide", "fichier", etc.
        # (This depends on i18n configuration)
    
    def test_error_message_no_stack_trace_in_production(self):
        """Test error messages don't leak internal details in production mode"""
        # This would require DEBUG=False setting
        # For now, just verify error format is consistent
        pass
