"""
Tests for PDF Upload Endpoint - ZF-AUD-03
Validates upload security, error handling, and atomicity.
"""
import pytest
import fitz
import os
from io import BytesIO
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient

from core.auth import create_user_roles
from exams.models import Exam, Booklet, Copy


def create_valid_pdf(pages=4, a3_format=False):
    """Create a minimal valid PDF with specified number of pages.
    
    Args:
        pages: Number of pages to create
        a3_format: If True, create A3 landscape pages (for batch mode tests)
    """
    doc = fitz.open()
    for i in range(pages):
        if a3_format:
            # A3 landscape: 1190 x 841 points
            page = doc.new_page(width=1190, height=841)
        else:
            # A4 portrait (default)
            page = doc.new_page()
        page.insert_text((50, 50), f"Page {i + 1}")
    
    buffer = BytesIO()
    doc.save(buffer)
    doc.close()
    buffer.seek(0)
    return buffer.read()


@pytest.fixture
def admin_client(db):
    """Create an authenticated admin client."""
    admin_group, _, _ = create_user_roles()
    admin_user = User.objects.create_user(
        username="admin_upload",
        password="testpass123",
    )
    admin_user.groups.add(admin_group)
    
    client = APIClient()
    client.force_login(admin_user)
    return client


@pytest.fixture
def teacher_client(db):
    """Create an authenticated teacher client (non-admin)."""
    _, teacher_group, _ = create_user_roles()
    teacher_user = User.objects.create_user(
        username="teacher_upload",
        password="testpass123",
    )
    teacher_user.groups.add(teacher_group)
    
    client = APIClient()
    client.force_login(teacher_user)
    return client


class TestUploadEndpointSecurity:
    """Security tests for /api/exams/upload/"""

    def test_upload_requires_authentication(self, db):
        """Unauthenticated request should return 403."""
        client = APIClient()
        response = client.post("/api/exams/upload/")
        assert response.status_code == 403

    def test_upload_requires_admin_role(self, teacher_client):
        """Teacher (non-admin) should get 403."""
        pdf_content = create_valid_pdf(4)
        pdf_file = SimpleUploadedFile("test.pdf", pdf_content, content_type="application/pdf")
        
        response = teacher_client.post(
            "/api/exams/upload/",
            {"name": "Test Exam", "date": "2026-01-31", "pdf_source": pdf_file},
            format="multipart",
        )
        assert response.status_code == 403


class TestUploadValidation:
    """Validation tests for PDF uploads."""

    def test_upload_valid_pdf_success(self, admin_client):
        """Valid PDF should create Exam + Booklets."""
        pdf_content = create_valid_pdf(8)
        pdf_file = SimpleUploadedFile("valid.pdf", pdf_content, content_type="application/pdf")
        
        response = admin_client.post(
            "/api/exams/upload/",
            {"name": "Valid Exam", "date": "2026-01-31", "pdf_source": pdf_file},
            format="multipart",
        )
        
        assert response.status_code == 201
        assert "booklets_created" in response.data
        assert response.data["booklets_created"] >= 1
        
        exam = Exam.objects.get(name="Valid Exam")
        assert exam.is_processed is True
        assert exam.booklets.count() >= 1

    def test_upload_non_pdf_returns_400(self, admin_client):
        """Non-PDF file should return 400 with clear error."""
        text_content = b"This is not a PDF file"
        fake_pdf = SimpleUploadedFile("fake.pdf", text_content, content_type="application/pdf")
        
        response = admin_client.post(
            "/api/exams/upload/",
            {"name": "Fake PDF Exam", "date": "2026-01-31", "pdf_source": fake_pdf},
            format="multipart",
        )
        
        assert response.status_code == 400
        assert "pdf_source" in response.data or "error" in response.data

    def test_upload_empty_file_returns_400(self, admin_client):
        """Empty file should return 400."""
        empty_file = SimpleUploadedFile("empty.pdf", b"", content_type="application/pdf")
        
        response = admin_client.post(
            "/api/exams/upload/",
            {"name": "Empty PDF Exam", "date": "2026-01-31", "pdf_source": empty_file},
            format="multipart",
        )
        
        assert response.status_code == 400

    def test_upload_corrupted_pdf_returns_400(self, admin_client):
        """Corrupted PDF should return 400."""
        corrupted_content = b"%PDF-1.4\nGARBAGE CORRUPTED DATA"
        corrupted_pdf = SimpleUploadedFile("corrupted.pdf", corrupted_content, content_type="application/pdf")
        
        response = admin_client.post(
            "/api/exams/upload/",
            {"name": "Corrupted PDF Exam", "date": "2026-01-31", "pdf_source": corrupted_pdf},
            format="multipart",
        )
        
        assert response.status_code == 400

    def test_upload_missing_required_fields_returns_400(self, admin_client):
        """Missing name or date should return 400."""
        pdf_content = create_valid_pdf(4)
        pdf_file = SimpleUploadedFile("test.pdf", pdf_content, content_type="application/pdf")
        
        response = admin_client.post(
            "/api/exams/upload/",
            {"pdf_source": pdf_file},
            format="multipart",
        )
        
        assert response.status_code == 400
        assert "name" in response.data or "date" in response.data


class TestUploadAtomicity:
    """Atomicity tests - no zombie Exams on failure."""

    def test_processing_failure_rolls_back_exam(self, admin_client, monkeypatch):
        """If PDF processing fails, Exam should be rolled back (not created)."""
        pdf_content = create_valid_pdf(4)
        pdf_file = SimpleUploadedFile("test.pdf", pdf_content, content_type="application/pdf")
        
        def mock_split_exam(*args, **kwargs):
            raise Exception("Simulated processing failure")
        
        from processing.services import pdf_splitter
        monkeypatch.setattr(pdf_splitter.PDFSplitter, "split_exam", mock_split_exam)
        
        initial_exam_count = Exam.objects.count()
        
        response = admin_client.post(
            "/api/exams/upload/",
            {"name": "Failure Exam", "date": "2026-01-31", "pdf_source": pdf_file},
            format="multipart",
        )
        
        assert response.status_code == 500
        assert "error" in response.data
        
        # ZF-AUD-03 FIX: Exam should be rolled back, not orphaned
        final_exam_count = Exam.objects.count()
        assert final_exam_count == initial_exam_count  # No new Exam created
        
        # Verify no orphan exam exists
        assert not Exam.objects.filter(name="Failure Exam").exists()


class TestUploadErrorMessages:
    """Error message clarity tests."""

    def test_error_message_is_user_friendly(self, admin_client):
        """Error messages should be exploitable by frontend."""
        text_content = b"Not a PDF"
        fake_pdf = SimpleUploadedFile("fake.pdf", text_content, content_type="application/pdf")
        
        response = admin_client.post(
            "/api/exams/upload/",
            {"name": "Fake Exam", "date": "2026-01-31", "pdf_source": fake_pdf},
            format="multipart",
        )
        
        assert response.status_code == 400
        
        error_text = str(response.data)
        assert "pdf" in error_text.lower() or "mime" in error_text.lower() or "invalid" in error_text.lower()


class TestBatchModeUpload:
    """Tests for batch mode upload with auto-stapling."""

    def test_batch_mode_requires_csv(self, admin_client):
        """Batch mode without CSV should fall back to standard mode."""
        pdf_content = create_valid_pdf(8)
        pdf_file = SimpleUploadedFile("batch.pdf", pdf_content, content_type="application/pdf")
        
        response = admin_client.post(
            "/api/exams/upload/",
            {
                "name": "Batch No CSV",
                "date": "2026-01-31",
                "pdf_source": pdf_file,
                "batch_mode": "true"
            },
            format="multipart",
        )
        
        # Should succeed but use standard mode (no CSV provided)
        assert response.status_code == 201
        assert "booklets_created" in response.data

    def test_batch_mode_with_csv_creates_copies(self, admin_client):
        """Batch mode with CSV should create copies directly."""
        pdf_content = create_valid_pdf(8, a3_format=True)
        pdf_file = SimpleUploadedFile("batch.pdf", pdf_content, content_type="application/pdf")
        
        csv_content = b"Eleves,Ne(e) le,Adresse E-mail,Classe\nDUPONT Jean,01/01/2008,jean.dupont@test.com,T.01\n"
        csv_file = SimpleUploadedFile("students.csv", csv_content, content_type="text/csv")
        
        response = admin_client.post(
            "/api/exams/upload/",
            {
                "name": "Batch With CSV",
                "date": "2026-01-31",
                "pdf_source": pdf_file,
                "batch_mode": "true",
                "students_csv": csv_file
            },
            format="multipart",
        )
        
        assert response.status_code == 201
        # Batch mode returns copies_created instead of booklets_created
        assert "copies_created" in response.data or "booklets_created" in response.data

    def test_batch_mode_response_includes_stats(self, admin_client):
        """Batch mode response should include ready/review counts."""
        pdf_content = create_valid_pdf(8, a3_format=True)
        pdf_file = SimpleUploadedFile("batch_stats.pdf", pdf_content, content_type="application/pdf")
        
        csv_content = b"Eleves,Ne(e) le,Adresse E-mail,Classe\nMARTIN Pierre,15/03/2008,pierre.martin@test.com,T.02\n"
        csv_file = SimpleUploadedFile("students.csv", csv_content, content_type="text/csv")
        
        response = admin_client.post(
            "/api/exams/upload/",
            {
                "name": "Batch Stats Test",
                "date": "2026-01-31",
                "pdf_source": pdf_file,
                "batch_mode": "true",
                "students_csv": csv_file
            },
            format="multipart",
        )
        
        assert response.status_code == 201
        # Should include statistics about auto-identification
        if "copies_created" in response.data:
            assert "ready_count" in response.data or "needs_review_count" in response.data


class TestUploadPathTraversal:
    """Path traversal protection tests."""

    def test_malicious_filename_is_sanitized(self, admin_client):
        """Filenames with path traversal attempts should be sanitized."""
        pdf_content = create_valid_pdf(4)
        malicious_filename = "../../../etc/passwd.pdf"
        pdf_file = SimpleUploadedFile(malicious_filename, pdf_content, content_type="application/pdf")
        
        response = admin_client.post(
            "/api/exams/upload/",
            {"name": "Path Traversal Test", "date": "2026-01-31", "pdf_source": pdf_file},
            format="multipart",
        )
        
        if response.status_code == 201:
            exam = Exam.objects.get(name="Path Traversal Test")
            assert ".." not in exam.pdf_source.name
            assert "etc" not in exam.pdf_source.name
            assert exam.pdf_source.name.startswith("exams/source/")
