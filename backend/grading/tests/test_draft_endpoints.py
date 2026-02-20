"""
Unit tests for DraftState API endpoints.
Task: AUTOSAVE + RECOVERY (DraftState DB + localStorage)
"""
import pytest
import uuid
import datetime
from django.utils import timezone
from django.contrib.auth import get_user_model

from exams.models import Exam, Copy
from grading.models import DraftState

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
        copy2 = copy_factory(exam=exam, status=Copy.Status.READY)
        assert copy2.exam == exam
        assert copy2.status == Copy.Status.READY
        
        # Verify teacher_user from conftest.py is available
        assert teacher_user.username == 'teacher_test'
        assert teacher_user.is_staff is True
    
    def test_save_draft_success(self, api_client, teacher_user, copy_factory):
        """AC-2.1: Save draft → 200 OK, version incremented"""
        copy = copy_factory(status=Copy.Status.READY)
        
        api_client.force_authenticate(teacher_user)
        client_id = uuid.uuid4()
        response = api_client.put(
            f'/api/grading/copies/{copy.id}/draft/',
            {
                'payload': {'rect': [10, 20, 100, 50], 'content': 'Test'},
                'client_id': str(client_id)
            },
            format='json',
        )
        
        assert response.status_code == 200
        assert response.data['status'] == 'SAVED'
        assert response.data['version'] == 1
        
        draft = DraftState.objects.get(copy=copy, owner=teacher_user)
        assert draft.payload['content'] == 'Test'
        assert draft.payload['rect'] == [10, 20, 100, 50]
    
    def test_load_draft_as_owner(self, api_client, teacher_user, copy_factory):
        """AC-2.2: Load draft as owner → 200 OK, payload returned"""
        copy = copy_factory()
        client_id = uuid.uuid4()
        DraftState.objects.create(
            copy=copy,
            owner=teacher_user,
            payload={'content': 'Draft content'},
            client_id=client_id,
            version=3
        )
        
        api_client.force_authenticate(teacher_user)
        response = api_client.get(f'/api/grading/copies/{copy.id}/draft/')
        
        assert response.status_code == 200
        assert response.data['payload']['content'] == 'Draft content'
        assert response.data['version'] == 3
        assert response.data['client_id'] == str(client_id)
    
    def test_load_non_existent_draft(self, api_client, teacher_user, copy_factory):
        """AC-2.3: Load non-existent draft → 204 No Content"""
        copy = copy_factory()
        
        api_client.force_authenticate(teacher_user)
        response = api_client.get(f'/api/grading/copies/{copy.id}/draft/')
        
        assert response.status_code == 204
    
    def test_save_without_client_id(self, api_client, teacher_user, copy_factory):
        """AC-2.4: Save without client_id → 400 Bad Request"""
        copy = copy_factory()
        
        api_client.force_authenticate(teacher_user)
        response = api_client.put(
            f'/api/grading/copies/{copy.id}/draft/',
            {
                'payload': {'content': 'Test'},
            },
            format='json'
        )
        
        assert response.status_code == 400
        assert 'client_id' in response.data['detail'].lower()
    
    def test_save_draft_by_different_user(self, api_client, teacher_user, copy_factory):
        """AC-2.5: Two users can each have their own draft on the same copy."""
        copy = copy_factory()
        other_user = User.objects.create_user(username='other', password='test')
        
        # Teacher saves a draft
        api_client.force_authenticate(teacher_user)
        client_id_t = uuid.uuid4()
        response = api_client.put(
            f'/api/grading/copies/{copy.id}/draft/',
            {'payload': {'content': 'Teacher draft'}, 'client_id': str(client_id_t)},
            format='json',
        )
        assert response.status_code == 200

        # Other user saves a draft
        api_client.force_authenticate(other_user)
        client_id_o = uuid.uuid4()
        response = api_client.put(
            f'/api/grading/copies/{copy.id}/draft/',
            {'payload': {'content': 'Other draft'}, 'client_id': str(client_id_o)},
            format='json',
        )
        assert response.status_code == 200

        assert DraftState.objects.filter(copy=copy).count() == 2
    
    def test_save_to_graded_copy_forbidden(self, api_client, teacher_user, copy_factory):
        """AC-2.6: Save to GRADED copy → 400 Bad Request"""
        copy = copy_factory(status=Copy.Status.GRADED)
        
        api_client.force_authenticate(teacher_user)
        response = api_client.put(
            f'/api/grading/copies/{copy.id}/draft/',
            {
                'payload': {'content': 'Test'},
                'client_id': str(uuid.uuid4())
            },
            format='json',
        )
        
        assert response.status_code == 400
        
        # Verify no draft was created
        assert not DraftState.objects.filter(copy=copy, owner=teacher_user).exists()
    
    def test_client_id_conflict(self, api_client, teacher_user, copy_factory):
        """AC-2.7: client_id conflict → 409 Conflict"""
        copy = copy_factory()
        
        # Create existing draft with different client_id
        existing_client_id = uuid.uuid4()
        DraftState.objects.create(
            copy=copy,
            owner=teacher_user,
            payload={'content': 'Old'},
            client_id=existing_client_id,
            version=1
        )
        
        # Try to save with different client_id
        new_client_id = uuid.uuid4()
        api_client.force_authenticate(teacher_user)
        response = api_client.put(
            f'/api/grading/copies/{copy.id}/draft/',
            {
                'payload': {'content': 'New'},
                'client_id': str(new_client_id)
            },
            format='json',
        )
        
        assert response.status_code == 409
    
    def test_unauthorized_access(self, api_client, copy_factory):
        """AC-2.8: Unauthorized access → 401/403 Forbidden"""
        copy = copy_factory()
        
        # No authentication
        response = api_client.get(f'/api/grading/copies/{copy.id}/draft/')
        
        assert response.status_code in [401, 403]
    
    def test_delete_draft_as_owner(self, api_client, teacher_user, copy_factory):
        """Delete draft as owner → 204 No Content"""
        copy = copy_factory()
        DraftState.objects.create(copy=copy, owner=teacher_user, payload={'content': 'Test'})
        
        api_client.force_authenticate(teacher_user)
        response = api_client.delete(f'/api/grading/copies/{copy.id}/draft/')
        
        assert response.status_code == 204
        assert not DraftState.objects.filter(copy=copy, owner=teacher_user).exists()
