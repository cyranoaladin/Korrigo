"""
Tests for QuestionRemark and Global Appreciation features.
"""
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from exams.models import Exam, Copy
from grading.models import QuestionRemark
from datetime import date

User = get_user_model()


@pytest.fixture
def admin_user(db):
    return User.objects.create_user(
        username='admin',
        password='admin123',
        is_superuser=True
    )


@pytest.fixture
def teacher_user(db):
    from django.contrib.auth.models import Group
    from core.auth import UserRole
    
    user = User.objects.create_user(
        username='teacher1',
        password='teacher123'
    )
    user.role = 'Teacher'
    user.save()
    
    # Add user to Teacher group for permissions
    teacher_group, _ = Group.objects.get_or_create(name=UserRole.TEACHER)
    user.groups.add(teacher_group)
    
    return user


@pytest.fixture
def exam_with_structure(db):
    return Exam.objects.create(
        name="Test Exam",
        date=date.today(),
        grading_structure=[
            {
                "id": "q1",
                "type": "question",
                "title": "Question 1",
                "maxScore": 10
            },
            {
                "id": "q2",
                "type": "question",
                "title": "Question 2",
                "maxScore": 15
            }
        ]
    )


@pytest.fixture
def copy_obj(db, exam_with_structure):
    return Copy.objects.create(
        exam=exam_with_structure,
        anonymous_id="COPY-001",
        status=Copy.Status.READY
    )


@pytest.mark.django_db
class TestQuestionRemarks:
    """Test QuestionRemark CRUD operations."""
    
    def test_create_remark(self, teacher_user, copy_obj):
        """Test creating a new remark."""
        client = APIClient()
        client.force_authenticate(user=teacher_user)
        
        response = client.post(
            f'/api/grading/copies/{copy_obj.id}/remarks/',
            {
                'question_id': 'q1',
                'remark': 'Good work on this question.'
            },
            format='json'
        )
        
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['question_id'] == 'q1'
        assert response.data['remark'] == 'Good work on this question.'
        assert QuestionRemark.objects.count() == 1
    
    def test_update_remark(self, teacher_user, copy_obj):
        """Test updating an existing remark."""
        client = APIClient()
        client.force_authenticate(user=teacher_user)
        
        client.post(
            f'/api/grading/copies/{copy_obj.id}/remarks/',
            {'question_id': 'q1', 'remark': 'Initial remark'},
            format='json'
        )
        
        response = client.post(
            f'/api/grading/copies/{copy_obj.id}/remarks/',
            {'question_id': 'q1', 'remark': 'Updated remark'},
            format='json'
        )
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['remark'] == 'Updated remark'
        assert QuestionRemark.objects.count() == 1
    
    def test_list_remarks(self, teacher_user, copy_obj):
        """Test listing all remarks for a copy."""
        client = APIClient()
        client.force_authenticate(user=teacher_user)
        
        client.post(
            f'/api/grading/copies/{copy_obj.id}/remarks/',
            {'question_id': 'q1', 'remark': 'Remark 1'},
            format='json'
        )
        client.post(
            f'/api/grading/copies/{copy_obj.id}/remarks/',
            {'question_id': 'q2', 'remark': 'Remark 2'},
            format='json'
        )
        
        response = client.get(f'/api/grading/copies/{copy_obj.id}/remarks/')
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 2
        assert len(response.data['results']) == 2
    
    def test_delete_remark(self, teacher_user, copy_obj):
        """Test deleting a remark."""
        client = APIClient()
        client.force_authenticate(user=teacher_user)
        
        create_response = client.post(
            f'/api/grading/copies/{copy_obj.id}/remarks/',
            {'question_id': 'q1', 'remark': 'Test remark'},
            format='json'
        )
        remark_id = create_response.data['id']
        
        delete_response = client.delete(f'/api/grading/remarks/{remark_id}/')
        
        assert delete_response.status_code == status.HTTP_204_NO_CONTENT
        assert QuestionRemark.objects.count() == 0
    
    def test_duplicate_remark_prevented(self, teacher_user, copy_obj):
        """Test that duplicate remarks for same question are prevented."""
        QuestionRemark.objects.create(
            copy=copy_obj,
            question_id='q1',
            remark='First remark',
            created_by=teacher_user
        )
        
        with pytest.raises(Exception):
            QuestionRemark.objects.create(
                copy=copy_obj,
                question_id='q1',
                remark='Second remark',
                created_by=teacher_user
            )
    
    def test_only_creator_can_edit_remark(self, teacher_user, copy_obj):
        """Test permission check: only creator can edit remark."""
        other_user = User.objects.create_user(
            username='teacher2',
            password='teacher123'
        )
        other_user.role = 'Teacher'
        other_user.save()
        
        remark = QuestionRemark.objects.create(
            copy=copy_obj,
            question_id='q1',
            remark='Original remark',
            created_by=teacher_user
        )
        
        client = APIClient()
        client.force_authenticate(user=other_user)
        
        response = client.patch(
            f'/api/grading/remarks/{remark.id}/',
            {'remark': 'Hacked remark'},
            format='json'
        )
        
        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
class TestGlobalAppreciation:
    """Test Global Appreciation functionality."""
    
    def test_save_global_appreciation(self, teacher_user, copy_obj):
        """Test saving global appreciation."""
        client = APIClient()
        client.force_authenticate(user=teacher_user)
        
        response = client.patch(
            f'/api/grading/copies/{copy_obj.id}/global-appreciation/',
            {'global_appreciation': 'Overall excellent work!'},
            format='json'
        )
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['global_appreciation'] == 'Overall excellent work!'
        
        copy_obj.refresh_from_db()
        assert copy_obj.global_appreciation == 'Overall excellent work!'
    
    def test_get_global_appreciation(self, teacher_user, copy_obj):
        """Test retrieving global appreciation."""
        copy_obj.global_appreciation = 'Test appreciation'
        copy_obj.save()
        
        client = APIClient()
        client.force_authenticate(user=teacher_user)
        
        response = client.get(
            f'/api/grading/copies/{copy_obj.id}/global-appreciation/'
        )
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['global_appreciation'] == 'Test appreciation'
    
    def test_empty_appreciation_returns_empty_string(self, teacher_user, copy_obj):
        """Test that empty appreciation returns empty string."""
        client = APIClient()
        client.force_authenticate(user=teacher_user)
        
        response = client.get(
            f'/api/grading/copies/{copy_obj.id}/global-appreciation/'
        )
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['global_appreciation'] == ''
