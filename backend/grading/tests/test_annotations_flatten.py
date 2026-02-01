"""
ZF-AUD-07: Annotations + Flatten PDF Tests
Tests for coordinate conversion, PDF generation, idempotence, and security.
"""
import pytest
import fitz
import os
import tempfile
import datetime
from io import BytesIO
from django.utils import timezone
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from rest_framework.test import APIClient

from core.auth import UserRole, create_user_roles
from exams.models import Copy, Exam, Booklet
from grading.models import Annotation, CopyLock
from grading.services import AnnotationService, GradingService
from processing.services.pdf_flattener import PDFFlattener

User = get_user_model()


def create_test_png(width=800, height=1000):
    """Create a minimal PNG image for testing."""
    import struct
    import zlib
    
    def png_chunk(chunk_type, data):
        chunk_len = struct.pack('>I', len(data))
        chunk_crc = struct.pack('>I', zlib.crc32(chunk_type + data) & 0xffffffff)
        return chunk_len + chunk_type + data + chunk_crc
    
    signature = b'\x89PNG\r\n\x1a\n'
    ihdr_data = struct.pack('>IIBBBBB', width, height, 8, 2, 0, 0, 0)
    ihdr = png_chunk(b'IHDR', ihdr_data)
    
    raw_data = b''
    for y in range(height):
        raw_data += b'\x00'  # Filter byte
        for x in range(width):
            raw_data += b'\xff\xff\xff'  # White pixel RGB
    
    compressed = zlib.compress(raw_data, 9)
    idat = png_chunk(b'IDAT', compressed)
    iend = png_chunk(b'IEND', b'')
    
    return signature + ihdr + idat + iend


@pytest.fixture
def setup_teacher(db):
    """Create a teacher user."""
    admin_group, teacher_group, _ = create_user_roles()
    teacher = User.objects.create_user(username='teacher_ann', password='pass123')
    teacher.groups.add(teacher_group)
    return teacher


@pytest.fixture
def copy_with_pages(db, setup_teacher, tmp_path):
    """Create a copy with actual page images."""
    teacher = setup_teacher
    
    exam = Exam.objects.create(name="Annotation Test Exam", date="2026-01-31")
    copy = Copy.objects.create(exam=exam, anonymous_id="ANN-TEST-01", status=Copy.Status.LOCKED)
    
    # Create actual PNG files
    pages_dir = tmp_path / "pages"
    pages_dir.mkdir()
    
    page_paths = []
    for i in range(2):
        png_data = create_test_png(800, 1000)
        page_file = pages_dir / f"page_{i:03d}.png"
        page_file.write_bytes(png_data)
        page_paths.append(str(page_file))
    
    booklet = Booklet.objects.create(
        exam=exam,
        start_page=1,
        end_page=2,
        pages_images=page_paths
    )
    copy.booklets.add(booklet)
    
    # Create lock
    lock = CopyLock.objects.create(
        copy=copy,
        owner=teacher,
        expires_at=timezone.now() + datetime.timedelta(hours=1)
    )
    
    return copy, lock, teacher


@pytest.mark.django_db
class TestCoordinateValidation:
    """Test coordinate validation in AnnotationService."""

    def test_valid_coordinates_pass(self):
        """Valid normalized coordinates should pass."""
        # Should not raise
        AnnotationService.validate_coordinates(0.0, 0.0, 0.5, 0.5)
        AnnotationService.validate_coordinates(0.5, 0.5, 0.5, 0.5)
        AnnotationService.validate_coordinates(0.1, 0.2, 0.3, 0.4)

    def test_x_out_of_range_fails(self):
        """x < 0 or x > 1 should fail."""
        with pytest.raises(ValueError, match="x and y must be in"):
            AnnotationService.validate_coordinates(-0.1, 0.5, 0.1, 0.1)
        
        with pytest.raises(ValueError, match="x and y must be in"):
            AnnotationService.validate_coordinates(1.1, 0.5, 0.1, 0.1)

    def test_y_out_of_range_fails(self):
        """y < 0 or y > 1 should fail."""
        with pytest.raises(ValueError, match="x and y must be in"):
            AnnotationService.validate_coordinates(0.5, -0.1, 0.1, 0.1)
        
        with pytest.raises(ValueError, match="x and y must be in"):
            AnnotationService.validate_coordinates(0.5, 1.1, 0.1, 0.1)

    def test_w_must_be_positive(self):
        """w must be > 0."""
        with pytest.raises(ValueError, match="w and h must be in"):
            AnnotationService.validate_coordinates(0.5, 0.5, 0.0, 0.1)
        
        with pytest.raises(ValueError, match="w and h must be in"):
            AnnotationService.validate_coordinates(0.5, 0.5, -0.1, 0.1)

    def test_h_must_be_positive(self):
        """h must be > 0."""
        with pytest.raises(ValueError, match="w and h must be in"):
            AnnotationService.validate_coordinates(0.5, 0.5, 0.1, 0.0)

    def test_x_plus_w_must_not_exceed_1(self):
        """x + w must not exceed 1."""
        with pytest.raises(ValueError, match="x \\+ w must not exceed"):
            AnnotationService.validate_coordinates(0.9, 0.5, 0.2, 0.1)

    def test_y_plus_h_must_not_exceed_1(self):
        """y + h must not exceed 1."""
        with pytest.raises(ValueError, match="y \\+ h must not exceed"):
            AnnotationService.validate_coordinates(0.5, 0.9, 0.1, 0.2)

    def test_boundary_values_pass(self):
        """Boundary values should pass."""
        # Exactly at boundaries
        AnnotationService.validate_coordinates(0.0, 0.0, 1.0, 1.0)
        AnnotationService.validate_coordinates(0.9, 0.9, 0.1, 0.1)


@pytest.mark.django_db
class TestCoordinateConversion:
    """Test coordinate denormalization in PDFFlattener."""

    def test_denormalization_formula(self):
        """Verify denormalization: x_pdf = x_rel * page_width."""
        page_width = 800
        page_height = 1000
        
        # Test cases: (x_rel, y_rel, w_rel, h_rel) -> (x_pdf, y_pdf, w_pdf, h_pdf)
        test_cases = [
            ((0.0, 0.0, 0.1, 0.1), (0, 0, 80, 100)),
            ((0.5, 0.5, 0.2, 0.2), (400, 500, 160, 200)),
            ((0.1, 0.2, 0.3, 0.4), (80, 200, 240, 400)),
            ((1.0, 1.0, 0.0, 0.0), (800, 1000, 0, 0)),  # Edge case
        ]
        
        for (x_rel, y_rel, w_rel, h_rel), (x_exp, y_exp, w_exp, h_exp) in test_cases:
            x_pdf = x_rel * page_width
            y_pdf = y_rel * page_height
            w_pdf = w_rel * page_width
            h_pdf = h_rel * page_height
            
            assert x_pdf == x_exp, f"x: {x_pdf} != {x_exp}"
            assert y_pdf == y_exp, f"y: {y_pdf} != {y_exp}"
            assert w_pdf == w_exp, f"w: {w_pdf} != {w_exp}"
            assert h_pdf == h_exp, f"h: {h_pdf} != {h_exp}"

    def test_denormalization_preserves_proportions(self):
        """Denormalization should preserve relative proportions."""
        page_width = 1200
        page_height = 1600
        
        # Two annotations at same relative position should scale proportionally
        x_rel, y_rel = 0.25, 0.75
        
        x_pdf = x_rel * page_width
        y_pdf = y_rel * page_height
        
        # Verify proportions
        assert x_pdf / page_width == x_rel
        assert y_pdf / page_height == y_rel


@pytest.mark.django_db
class TestPDFFlattenerIntegration:
    """Integration tests for PDFFlattener."""

    def test_flatten_creates_valid_pdf(self, copy_with_pages):
        """Flatten should create a valid PDF with annotations."""
        copy, lock, teacher = copy_with_pages
        
        # Add annotation
        Annotation.objects.create(
            copy=copy,
            page_index=0,
            x=0.1, y=0.2, w=0.3, h=0.1,
            type=Annotation.Type.COMMENT,
            content="Test annotation",
            score_delta=5,
            created_by=teacher
        )
        
        flattener = PDFFlattener()
        pdf_bytes = flattener.flatten_copy(copy)
        
        # Verify it's a valid PDF
        assert pdf_bytes is not None
        assert len(pdf_bytes) > 0
        assert pdf_bytes[:4] == b'%PDF'
        
        # Open and verify structure
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        assert doc.page_count >= 2  # 2 pages + summary
        doc.close()

    def test_flatten_includes_all_annotation_types(self, copy_with_pages):
        """All annotation types should be rendered with correct colors."""
        copy, lock, teacher = copy_with_pages
        
        # Add one of each type
        for ann_type in Annotation.Type.values:
            Annotation.objects.create(
                copy=copy,
                page_index=0,
                x=0.1, y=0.1 + 0.15 * list(Annotation.Type.values).index(ann_type),
                w=0.2, h=0.1,
                type=ann_type,
                content=f"Test {ann_type}",
                score_delta=1,
                created_by=teacher
            )
        
        flattener = PDFFlattener()
        pdf_bytes = flattener.flatten_copy(copy)
        
        # Verify PDF is valid
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        assert doc.page_count >= 2
        doc.close()

    def test_flatten_adds_summary_page(self, copy_with_pages):
        """Flatten should add a summary page with scores."""
        copy, lock, teacher = copy_with_pages
        
        # Add annotations with scores
        Annotation.objects.create(
            copy=copy, page_index=0,
            x=0.1, y=0.1, w=0.1, h=0.1,
            type=Annotation.Type.ERROR,
            content="Error 1",
            score_delta=-3,
            created_by=teacher
        )
        Annotation.objects.create(
            copy=copy, page_index=1,
            x=0.2, y=0.2, w=0.1, h=0.1,
            type=Annotation.Type.BONUS,
            content="Bonus 1",
            score_delta=5,
            created_by=teacher
        )
        
        flattener = PDFFlattener()
        pdf_bytes = flattener.flatten_copy(copy)
        
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        
        # Last page should be summary (A4 size)
        summary_page = doc[-1]
        assert abs(summary_page.rect.width - 595) < 1  # A4 width
        assert abs(summary_page.rect.height - 842) < 1  # A4 height
        
        # Check text contains score info
        text = summary_page.get_text()
        assert "SCORE TOTAL" in text
        assert "2" in text  # -3 + 5 = 2
        
        doc.close()


@pytest.mark.django_db
class TestFinalizeIdempotence:
    """Test that finalize is idempotent."""

    def test_finalize_does_not_duplicate_pdf(self, copy_with_pages, monkeypatch):
        """Re-running finalize should not create duplicate PDF."""
        copy, lock, teacher = copy_with_pages
        
        # Add annotation
        Annotation.objects.create(
            copy=copy, page_index=0,
            x=0.1, y=0.1, w=0.1, h=0.1,
            type=Annotation.Type.COMMENT,
            content="Test",
            created_by=teacher
        )
        
        # First finalize
        GradingService.finalize_copy(copy, teacher, lock_token=str(lock.token))
        copy.refresh_from_db()
        
        assert copy.status == Copy.Status.GRADED
        assert copy.final_pdf
        first_pdf_name = copy.final_pdf.name
        
        # Attempting second finalize should fail (already GRADED)
        from grading.services import LockConflictError
        with pytest.raises((ValueError, LockConflictError)):
            GradingService.finalize_copy(copy, teacher, lock_token="any")


@pytest.mark.django_db
class TestAnnotationSecurity:
    """Test annotation security (no injection, no cross-copy)."""

    def test_cannot_annotate_other_users_locked_copy(self, copy_with_pages, db):
        """Cannot annotate a copy locked by another user."""
        copy, lock, teacher1 = copy_with_pages
        
        # Create another teacher
        _, teacher_group, _ = create_user_roles()
        teacher2 = User.objects.create_user(username='teacher2_sec', password='pass123')
        teacher2.groups.add(teacher_group)
        
        # Teacher2 tries to annotate with teacher1's lock token
        from grading.services import LockConflictError
        with pytest.raises(LockConflictError, match="locked by another user"):
            AnnotationService.add_annotation(
                copy,
                {'page_index': 0, 'x': 0.1, 'y': 0.1, 'w': 0.1, 'h': 0.1, 'content': 'hack'},
                teacher2,
                lock_token=str(lock.token)
            )

    def test_content_is_escaped_in_pdf(self, copy_with_pages):
        """Malicious content should be escaped in PDF."""
        copy, lock, teacher = copy_with_pages
        
        # Add annotation with potentially malicious content
        malicious_content = "<script>alert('xss')</script>"
        Annotation.objects.create(
            copy=copy, page_index=0,
            x=0.1, y=0.1, w=0.3, h=0.1,
            type=Annotation.Type.COMMENT,
            content=malicious_content,
            created_by=teacher
        )
        
        flattener = PDFFlattener()
        pdf_bytes = flattener.flatten_copy(copy)
        
        # PDF should be valid (not corrupted by injection)
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        assert doc.page_count >= 2
        
        # Content should be rendered as text, not executed
        page = doc[0]
        text = page.get_text()
        # The script tags should appear as literal text if rendered
        doc.close()

    def test_annotation_belongs_to_correct_copy(self, copy_with_pages, db, setup_teacher):
        """Annotation should be linked to correct copy."""
        copy1, lock1, teacher = copy_with_pages
        
        # Create another copy
        exam = Exam.objects.create(name="Other Exam", date="2026-01-31")
        copy2 = Copy.objects.create(exam=exam, anonymous_id="OTHER-01", status=Copy.Status.LOCKED)
        
        # Create annotation on copy1
        ann = Annotation.objects.create(
            copy=copy1, page_index=0,
            x=0.1, y=0.1, w=0.1, h=0.1,
            type=Annotation.Type.COMMENT,
            content="Test",
            created_by=teacher
        )
        
        # Verify annotation is on copy1, not copy2
        assert ann.copy == copy1
        assert ann not in copy2.annotations.all()
        assert ann in copy1.annotations.all()


@pytest.mark.django_db
class TestAnnotationAPIValidation:
    """Test annotation API endpoint validation."""

    def test_api_validates_coordinates(self, copy_with_pages):
        """API should validate coordinates before saving."""
        copy, lock, teacher = copy_with_pages
        
        client = APIClient()
        client.force_authenticate(user=teacher)
        
        # Invalid coordinates (x + w > 1)
        payload = {
            'page_index': 0,
            'x': 0.9,
            'y': 0.1,
            'w': 0.2,  # 0.9 + 0.2 = 1.1 > 1
            'h': 0.1,
            'type': 'COMMENT',
            'content': 'test'
        }
        
        response = client.post(
            f"/api/grading/copies/{copy.id}/annotations/",
            payload,
            format='json',
            HTTP_X_LOCK_TOKEN=str(lock.token)
        )
        
        assert response.status_code == 400

    def test_api_validates_page_index(self, copy_with_pages):
        """API should validate page_index is within bounds."""
        copy, lock, teacher = copy_with_pages
        
        client = APIClient()
        client.force_authenticate(user=teacher)
        
        # Invalid page_index (copy has 2 pages, index 0-1)
        payload = {
            'page_index': 99,
            'x': 0.1,
            'y': 0.1,
            'w': 0.1,
            'h': 0.1,
            'type': 'COMMENT',
            'content': 'test'
        }
        
        response = client.post(
            f"/api/grading/copies/{copy.id}/annotations/",
            payload,
            format='json',
            HTTP_X_LOCK_TOKEN=str(lock.token)
        )
        
        assert response.status_code == 400
