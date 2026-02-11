"""
Tests for audit fixes P1-P15.
Validates all critical corrections applied to the exam creation workflow.
"""
import pytest
import uuid
from unittest.mock import patch
from rest_framework import status
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.utils import timezone

from exams.models import Exam, Booklet, Copy, ExamPDF
from exams.views import generate_anonymous_id
from core.auth import UserRole
from exams.tests.fixtures.pdf_fixtures import (
    create_valid_pdf,
    create_uploadedfile,
    get_valid_pdf_file,
)

User = get_user_model()


# ============================================================================
# P2 FIX: Test generate_anonymous_id collision-free generation
# ============================================================================

@pytest.mark.django_db
class TestGenerateAnonymousId:
    """Test the sequential anonymous ID generator (P2 fix)."""

    def test_generates_sequential_ids(self):
        """IDs should be sequential within an exam."""
        exam = Exam.objects.create(name='Test Exam', date='2024-01-15')
        
        id0 = generate_anonymous_id(exam, 0)
        id1 = generate_anonymous_id(exam, 1)
        id2 = generate_anonymous_id(exam, 2)
        
        # All should be unique
        assert len({id0, id1, id2}) == 3
        
        # Should follow XXXX-NNN format
        prefix = str(exam.id).replace('-', '')[:4].upper()
        assert id0.startswith(prefix + '-')
        assert id1.startswith(prefix + '-')
        assert id2.startswith(prefix + '-')

    def test_no_collision_with_existing_copies(self):
        """Should not collide with existing copy anonymous_ids."""
        exam = Exam.objects.create(name='Test Exam', date='2024-01-15')
        prefix = str(exam.id).replace('-', '')[:4].upper()
        
        # Pre-create a copy with the expected sequential ID
        Copy.objects.create(
            exam=exam,
            anonymous_id=f"{prefix}-001",
            status=Copy.Status.STAGING
        )
        
        # generate_anonymous_id should detect collision and use fallback
        new_id = generate_anonymous_id(exam, 0)
        assert new_id != f"{prefix}-001"
        assert not Copy.objects.filter(anonymous_id=new_id).exclude(
            anonymous_id=f"{prefix}-001"
        ).exists() or new_id.startswith(prefix)

    def test_handles_many_copies(self):
        """Should generate unique IDs even with many existing copies."""
        exam = Exam.objects.create(name='Test Exam', date='2024-01-15')
        
        ids = set()
        for i in range(50):
            new_id = generate_anonymous_id(exam, i)
            assert new_id not in ids, f"Collision detected at index {i}: {new_id}"
            ids.add(new_id)
            # Create the copy so the count increases
            Copy.objects.create(
                exam=exam,
                anonymous_id=new_id,
                status=Copy.Status.STAGING
            )


# ============================================================================
# P1 FIX: Test auto-validation (STAGING → READY) after split
# ============================================================================

@pytest.mark.django_db
class TestAutoValidation:
    """Test that copies are auto-validated to READY after successful PDF split (P1 fix)."""

    def test_batch_upload_creates_ready_copies(self, teacher_client):
        """Copies should be READY (not STAGING) after successful BATCH_A3 upload."""
        pdf_bytes = create_valid_pdf(pages=8)
        pdf_file = create_uploadedfile(pdf_bytes, filename="exam_8pages.pdf")
        
        data = {
            'name': 'Auto-Validate Test',
            'date': '2024-01-15',
            'upload_mode': 'BATCH_A3',
            'pdf_source': pdf_file,
            'pages_per_booklet': 4
        }
        
        response = teacher_client.post('/api/exams/upload/', data, format='multipart')
        
        assert response.status_code == status.HTTP_201_CREATED
        
        exam = Exam.objects.first()
        copies = Copy.objects.filter(exam=exam)
        
        # All copies should be READY since pages exist after split
        for copy in copies:
            assert copy.status == Copy.Status.READY, \
                f"Copy {copy.anonymous_id} should be READY, got {copy.status}"
            assert copy.validated_at is not None, \
                f"Copy {copy.anonymous_id} should have validated_at set"

    def test_bulk_validation_endpoint(self, teacher_client):
        """POST /api/exams/<id>/validate-all/ should validate all STAGING copies."""
        exam = Exam.objects.create(name='Bulk Validate Test', date='2024-01-15')
        
        # Create booklets with pages so validation succeeds
        booklet = Booklet.objects.create(
            exam=exam, start_page=1, end_page=4,
            pages_images=['page1.png', 'page2.png']
        )
        
        copy = Copy.objects.create(
            exam=exam,
            anonymous_id='TEST-001',
            status=Copy.Status.STAGING
        )
        copy.booklets.add(booklet)
        
        response = teacher_client.post(f'/api/exams/{exam.id}/validate-all/')
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['validated'] == 1
        
        copy.refresh_from_db()
        assert copy.status == Copy.Status.READY

    def test_single_copy_validation_endpoint(self, teacher_client):
        """POST /api/exams/copies/<id>/validate/ should validate a single copy."""
        exam = Exam.objects.create(name='Single Validate Test', date='2024-01-15')
        
        booklet = Booklet.objects.create(
            exam=exam, start_page=1, end_page=4,
            pages_images=['page1.png', 'page2.png']
        )
        
        copy = Copy.objects.create(
            exam=exam,
            anonymous_id='TEST-002',
            status=Copy.Status.STAGING
        )
        copy.booklets.add(booklet)
        
        response = teacher_client.post(f'/api/exams/copies/{copy.id}/validate/')
        
        assert response.status_code == status.HTTP_200_OK
        
        copy.refresh_from_db()
        assert copy.status == Copy.Status.READY


# ============================================================================
# P3 FIX: Test ExamSourceUploadView duplicate protection
# ============================================================================

@pytest.mark.django_db
class TestExamSourceUploadProtection:
    """Test that re-uploading PDF doesn't create duplicate copies (P3 fix)."""

    def test_reupload_blocked_when_non_staging_copies_exist(self, teacher_client):
        """Re-upload should be blocked if copies are already being corrected."""
        exam = Exam.objects.create(
            name='Re-upload Block Test',
            date='2024-01-15',
            upload_mode='BATCH_A3'
        )
        
        # Create a READY copy (simulating already validated)
        Copy.objects.create(
            exam=exam,
            anonymous_id='BLOCK-001',
            status=Copy.Status.READY
        )
        
        pdf_bytes = create_valid_pdf(pages=4)
        pdf_file = create_uploadedfile(pdf_bytes, filename="reupload.pdf")
        
        response = teacher_client.post(
            f'/api/exams/{exam.id}/upload/',
            {'pdf_source': pdf_file},
            format='multipart'
        )
        
        assert response.status_code == status.HTTP_409_CONFLICT

    def test_reupload_allowed_when_only_staging_copies(self, teacher_client):
        """Re-upload should be allowed if only STAGING copies exist."""
        pdf_bytes = create_valid_pdf(pages=4)
        
        exam = Exam.objects.create(
            name='Re-upload Allow Test',
            date='2024-01-15',
            upload_mode='BATCH_A3'
        )
        
        # Create STAGING copies
        Copy.objects.create(
            exam=exam,
            anonymous_id='ALLOW-001',
            status=Copy.Status.STAGING
        )
        
        pdf_file = create_uploadedfile(pdf_bytes, filename="reupload.pdf")
        
        def mock_split_fn(exam_obj, force=False):
            """Create booklet inside mock so it's created after cleanup."""
            booklet = Booklet.objects.create(
                exam=exam_obj, start_page=1, end_page=4,
                pages_images=['page1.png', 'page2.png']
            )
            return [booklet]
        
        with patch('processing.services.pdf_splitter.PDFSplitter.split_exam', side_effect=mock_split_fn):
            response = teacher_client.post(
                f'/api/exams/{exam.id}/upload/',
                {'pdf_source': pdf_file},
                format='multipart'
            )
        
        assert response.status_code == status.HTTP_201_CREATED
        
        # Old STAGING copy should be deleted, new one created
        assert Copy.objects.filter(exam=exam, anonymous_id='ALLOW-001').count() == 0


# ============================================================================
# P12 FIX: Test dispatch only dispatches READY/STAGING copies
# ============================================================================

@pytest.mark.django_db
class TestDispatchFilter:
    """Test that dispatch only assigns READY/STAGING copies (P12 fix)."""

    def test_dispatch_skips_graded_copies(self, teacher_client):
        """Already graded copies should not be re-dispatched."""
        exam = Exam.objects.create(name='Dispatch Filter Test', date='2024-01-15')
        
        teacher = User.objects.create_user(username='corrector1', password='test123')
        teacher_group, _ = Group.objects.get_or_create(name=UserRole.TEACHER)
        teacher.groups.add(teacher_group)
        exam.correctors.add(teacher)
        
        # Create one READY and one GRADED copy
        Copy.objects.create(
            exam=exam,
            anonymous_id='DISP-001',
            status=Copy.Status.READY
        )
        Copy.objects.create(
            exam=exam,
            anonymous_id='DISP-002',
            status=Copy.Status.GRADED,
            graded_at=timezone.now()
        )
        
        response = teacher_client.post(f'/api/exams/{exam.id}/dispatch/')
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['copies_assigned'] == 1  # Only READY copy

    def test_dispatch_no_copies_returns_message(self, teacher_client):
        """When no unassigned copies exist, should return informative message."""
        exam = Exam.objects.create(name='No Copies Test', date='2024-01-15')
        
        teacher = User.objects.create_user(username='corrector2', password='test123')
        teacher_group, _ = Group.objects.get_or_create(name=UserRole.TEACHER)
        teacher.groups.add(teacher_group)
        exam.correctors.add(teacher)
        
        response = teacher_client.post(f'/api/exams/{exam.id}/dispatch/')
        
        assert response.status_code == status.HTTP_200_OK
        assert 'message' in response.data


# ============================================================================
# P7 FIX: Test Exam timestamps
# ============================================================================

@pytest.mark.django_db
class TestExamTimestamps:
    """Test that Exam model has created_at/updated_at timestamps (P7 fix)."""

    def test_exam_has_created_at(self):
        """Exam should have created_at auto-set on creation."""
        exam = Exam.objects.create(name='Timestamp Test', date='2024-01-15')
        exam.refresh_from_db()
        assert exam.created_at is not None

    def test_exam_has_updated_at(self):
        """Exam should have updated_at auto-set on save."""
        exam = Exam.objects.create(name='Timestamp Test', date='2024-01-15')
        exam.refresh_from_db()
        assert exam.updated_at is not None
        
        old_updated = exam.updated_at
        exam.name = 'Updated Name'
        exam.save()
        exam.refresh_from_db()
        assert exam.updated_at >= old_updated


# ============================================================================
# P14 FIX: Test Exam.__init__ safety
# ============================================================================

@pytest.mark.django_db
class TestExamInitSafety:
    """Test that Exam.__init__ override doesn't break ORM operations (P14 fix)."""

    def test_exam_queryset_works(self):
        """Exam.objects.all() should work without errors."""
        Exam.objects.create(name='Init Test 1', date='2024-01-15')
        Exam.objects.create(name='Init Test 2', date='2024-01-16')
        
        exams = list(Exam.objects.all())
        assert len(exams) == 2

    def test_exam_filter_works(self):
        """Exam.objects.filter() should work without errors."""
        Exam.objects.create(name='Filter Test', date='2024-01-15')
        
        result = Exam.objects.filter(name='Filter Test')
        assert result.count() == 1

    def test_exam_title_alias_works(self):
        """Legacy 'title' kwarg should be mapped to 'name'."""
        exam = Exam(title='Legacy Title', date='2024-01-15')
        assert exam.name == 'Legacy Title'

    def test_exam_default_date(self):
        """Exam without date should get today's date."""
        exam = Exam(name='No Date Exam')
        assert exam.date == timezone.now().date()
