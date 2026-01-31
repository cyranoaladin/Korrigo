"""
Unit tests for DraftState API endpoints.
Task: ZF-AUD-06 AUTOSAVE + RECOVERY (DraftState DB + localStorage)
"""
import pytest
import uuid
from django.utils import timezone
from django.contrib.auth import get_user_model

from exams.models import Exam, Copy
from grading.models import DraftState, CopyLock

User = get_user_model()


@pytest.fixture
def exam_factory(db):
    """Factory fixture for creating Exam instances."""
    def create_exam(**kwargs):
        defaults = {
            'name': 'Test Exam',
            'date': timezone.now().date(),
            'grading_structure': {}
        }
        defaults.update(kwargs)
        return Exam.objects.create(**defaults)
    return create_exam


@pytest.fixture
def copy_factory(db, exam_factory):
    """Factory fixture for creating Copy instances."""
    def create_copy(**kwargs):
        exam = kwargs.pop('exam', None) or exam_factory()
        defaults = {
            'exam': exam,
            'anonymous_id': f'TEST-{uuid.uuid4().hex[:8]}',
            'status': Copy.Status.READY
        }
        defaults.update(kwargs)
        return Copy.objects.create(**defaults)
    return create_copy


@pytest.mark.django_db
class TestDraftEndpoints:
    """Test suite for DraftState CRUD operations."""
    
    def test_fixtures_integration(self, exam_factory, copy_factory, teacher_user):
        """Verify fixtures integrate correctly with existing conftest.py fixtures."""
        # Test exam_factory
        exam = exam_factory(name='Integration Test Exam')
        assert exam.name == 'Integration Test Exam'
        assert Exam.objects.count() == 1
        
        # Test copy_factory with default exam
        copy1 = copy_factory()
        assert copy1.status == Copy.Status.READY
        assert copy1.exam is not None
        
        # Test copy_factory with custom exam
        copy2 = copy_factory(exam=exam, status=Copy.Status.LOCKED)
        assert copy2.exam == exam
        assert copy2.status == Copy.Status.LOCKED
        
        # Verify teacher_user from conftest.py is available
        assert teacher_user.username == 'teacher_test'
        assert teacher_user.is_staff is True
