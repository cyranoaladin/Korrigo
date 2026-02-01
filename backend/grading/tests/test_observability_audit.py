"""
ZF-AUD-11: Observability + Audit Trail Tests
Tests for GradingEvent creation at key workflow moments.
"""
import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.utils import timezone
import datetime

from core.auth import UserRole, create_user_roles
from exams.models import Exam, Copy, Booklet
from grading.models import GradingEvent, Annotation, CopyLock
from grading.services import GradingService, AnnotationService

User = get_user_model()


@pytest.fixture
def setup_teacher(db):
    """Create a teacher user."""
    admin_group, teacher_group, _ = create_user_roles()
    teacher = User.objects.create_user(username='teacher_obs', password='pass123')
    teacher.groups.add(teacher_group)
    return teacher


@pytest.fixture
def setup_copy_ready(db, setup_teacher):
    """Create a copy in READY status."""
    teacher = setup_teacher
    exam = Exam.objects.create(name="Observability Test", date="2026-01-31")
    copy = Copy.objects.create(exam=exam, anonymous_id="OBS-001", status=Copy.Status.READY)
    
    # Add booklet with pages for validation
    booklet = Booklet.objects.create(exam=exam, start_page=1, end_page=2, pages_images=["page1.png"])
    copy.booklets.add(booklet)
    
    return copy, teacher


@pytest.mark.django_db
class TestGradingEventCreation:
    """Test GradingEvent creation at key workflow moments."""

    def test_lock_creates_grading_event(self, setup_copy_ready):
        """Locking a copy should create a LOCK GradingEvent."""
        copy, teacher = setup_copy_ready
        
        initial_count = GradingEvent.objects.filter(copy=copy, action=GradingEvent.Action.LOCK).count()
        
        # Lock the copy (returns tuple: lock, created)
        lock, created = GradingService.acquire_lock(copy, teacher)
        
        # Verify event created
        lock_events = GradingEvent.objects.filter(copy=copy, action=GradingEvent.Action.LOCK)
        assert lock_events.count() == initial_count + 1
        
        event = lock_events.latest('timestamp')
        assert event.actor == teacher
        assert 'token_prefix' in event.metadata

    def test_unlock_creates_grading_event(self, setup_copy_ready):
        """Unlocking a copy should create an UNLOCK GradingEvent."""
        copy, teacher = setup_copy_ready
        
        # First lock (returns tuple: lock, created)
        lock, _ = GradingService.acquire_lock(copy, teacher)
        
        initial_count = GradingEvent.objects.filter(copy=copy, action=GradingEvent.Action.UNLOCK).count()
        
        # Unlock
        GradingService.release_lock(copy, teacher, lock_token=str(lock.token))
        
        # Verify event created
        unlock_events = GradingEvent.objects.filter(copy=copy, action=GradingEvent.Action.UNLOCK)
        assert unlock_events.count() == initial_count + 1

    def test_create_annotation_creates_grading_event(self, setup_copy_ready):
        """Creating an annotation should create a CREATE_ANN GradingEvent."""
        copy, teacher = setup_copy_ready
        
        # Lock first (returns tuple: lock, created)
        lock, _ = GradingService.acquire_lock(copy, teacher)
        
        initial_count = GradingEvent.objects.filter(copy=copy, action=GradingEvent.Action.CREATE_ANN).count()
        
        # Create annotation
        AnnotationService.add_annotation(
            copy,
            {'page_index': 0, 'x': 0.1, 'y': 0.1, 'w': 0.1, 'h': 0.1, 'content': 'test'},
            teacher,
            lock_token=str(lock.token)
        )
        
        # Verify event created
        ann_events = GradingEvent.objects.filter(copy=copy, action=GradingEvent.Action.CREATE_ANN)
        assert ann_events.count() == initial_count + 1

    def test_update_annotation_creates_grading_event(self, setup_copy_ready):
        """Updating an annotation should create an UPDATE_ANN GradingEvent."""
        copy, teacher = setup_copy_ready
        
        # Lock and create annotation (returns tuple: lock, created)
        lock, _ = GradingService.acquire_lock(copy, teacher)
        copy.refresh_from_db()  # Refresh to get LOCKED status
        
        annotation = AnnotationService.add_annotation(
            copy,
            {'page_index': 0, 'x': 0.1, 'y': 0.1, 'w': 0.1, 'h': 0.1, 'content': 'original'},
            teacher,
            lock_token=str(lock.token)
        )
        
        initial_count = GradingEvent.objects.filter(copy=copy, action=GradingEvent.Action.UPDATE_ANN).count()
        
        # Update annotation
        AnnotationService.update_annotation(
            annotation,
            {'content': 'updated'},
            teacher,
            lock_token=str(lock.token)
        )
        
        # Verify event created
        update_events = GradingEvent.objects.filter(copy=copy, action=GradingEvent.Action.UPDATE_ANN)
        assert update_events.count() == initial_count + 1

    def test_delete_annotation_creates_grading_event(self, setup_copy_ready):
        """Deleting an annotation should create a DELETE_ANN GradingEvent."""
        copy, teacher = setup_copy_ready
        
        # Lock and create annotation (returns tuple: lock, created)
        lock, _ = GradingService.acquire_lock(copy, teacher)
        copy.refresh_from_db()  # Refresh to get LOCKED status
        
        annotation = AnnotationService.add_annotation(
            copy,
            {'page_index': 0, 'x': 0.1, 'y': 0.1, 'w': 0.1, 'h': 0.1, 'content': 'to delete'},
            teacher,
            lock_token=str(lock.token)
        )
        
        initial_count = GradingEvent.objects.filter(copy=copy, action=GradingEvent.Action.DELETE_ANN).count()
        
        # Delete annotation
        AnnotationService.delete_annotation(annotation, teacher, lock_token=str(lock.token))
        
        # Verify event created
        delete_events = GradingEvent.objects.filter(copy=copy, action=GradingEvent.Action.DELETE_ANN)
        assert delete_events.count() == initial_count + 1


@pytest.mark.django_db
class TestGradingEventMetadata:
    """Test GradingEvent metadata contains useful info without PII."""

    def test_lock_event_contains_token_prefix(self, setup_copy_ready):
        """Lock event metadata should contain token_prefix (for correlation)."""
        copy, teacher = setup_copy_ready
        
        lock, _ = GradingService.acquire_lock(copy, teacher)
        
        event = GradingEvent.objects.filter(copy=copy, action=GradingEvent.Action.LOCK).latest('timestamp')
        
        assert 'token_prefix' in event.metadata
        # Token prefix should be present for correlation (first 8 chars)

    def test_annotation_event_contains_annotation_id(self, setup_copy_ready):
        """Annotation events should contain annotation_id."""
        copy, teacher = setup_copy_ready
        
        lock, _ = GradingService.acquire_lock(copy, teacher)
        annotation = AnnotationService.add_annotation(
            copy,
            {'page_index': 0, 'x': 0.1, 'y': 0.1, 'w': 0.1, 'h': 0.1, 'content': 'test'},
            teacher,
            lock_token=str(lock.token)
        )
        
        event = GradingEvent.objects.filter(copy=copy, action=GradingEvent.Action.CREATE_ANN).latest('timestamp')
        
        assert 'annotation_id' in event.metadata
        assert str(event.metadata['annotation_id']) == str(annotation.id)


@pytest.mark.django_db
class TestAuditLogPIISuppression:
    """Test that audit logs don't contain PII."""

    def test_audit_log_anonymizes_ids(self):
        """Audit log should hash IDs for GDPR compliance."""
        from core.utils.audit import _anonymize_id
        
        # Test anonymization
        original_id = "12345"
        hashed = _anonymize_id(original_id)
        
        # Should be a hash, not the original
        assert hashed != original_id
        assert len(hashed) == 12  # SHA256 truncated to 12 chars

    def test_audit_log_none_handling(self):
        """Audit log should handle None values."""
        from core.utils.audit import _anonymize_id
        
        assert _anonymize_id(None) is None


@pytest.mark.django_db
class TestRequestIDCorrelation:
    """Test request ID correlation in logs."""

    def test_request_id_middleware_generates_uuid(self):
        """RequestIDMiddleware should generate UUID for each request."""
        from core.middleware.request_id import RequestIDMiddleware
        from django.test import RequestFactory
        
        factory = RequestFactory()
        request = factory.get('/test/')
        
        middleware = RequestIDMiddleware(get_response=lambda r: None)
        middleware.process_request(request)
        
        assert hasattr(request, 'request_id')
        assert len(request.request_id) == 36  # UUID format

    def test_request_id_accepts_client_provided(self):
        """RequestIDMiddleware should accept client-provided request ID."""
        from core.middleware.request_id import RequestIDMiddleware
        from django.test import RequestFactory
        
        factory = RequestFactory()
        client_request_id = "client-provided-id-12345"
        request = factory.get('/test/', HTTP_X_REQUEST_ID=client_request_id)
        
        middleware = RequestIDMiddleware(get_response=lambda r: None)
        middleware.process_request(request)
        
        assert request.request_id == client_request_id
