import pytest
from django.urls import reverse
from rest_framework import status
from exams.models import Exam, Copy, ExamType
from students.models import Student
from core.auth import UserRole
from django.contrib.auth import get_user_model
from grading.models import Score

User = get_user_model()

@pytest.fixture
def corrector_user(db):
    from django.contrib.auth.models import Group
    user = User.objects.create_user(username='corrector', password='password')
    teacher_group, _ = Group.objects.get_or_create(name='teacher')
    user.groups.add(teacher_group)
    return user

@pytest.fixture
def exam_setup(db, corrector_user):
    exam_type = ExamType.objects.create(name='Bac Blanc', code='BB')
    exam = Exam.objects.create(name='BB Maths J1', exam_type=exam_type)
    exam.correctors.add(corrector_user)
    
    # Create students
    from datetime import date
    s1 = Student.objects.create(first_name='Jean', last_name='Dupont', class_name='T.01', groupe='G1', date_naissance=date(2005, 3, 15))
    s2 = Student.objects.create(first_name='Marie', last_name='Curie', class_name='T.01', groupe='G2', date_naissance=date(2005, 1, 1))
    
    # Create finalized copies
    c1 = Copy.objects.create(exam=exam, student=s1, status=Copy.Status.FINALIZED, is_identified=True, anonymous_id='ANON1')
    c2 = Copy.objects.create(exam=exam, student=s2, status=Copy.Status.FINALIZED, is_identified=True, anonymous_id='ANON2')
    
    # Add scores
    Score.objects.create(copy=c1, scores_data={'q1': 15})
    Score.objects.create(copy=c2, scores_data={'q1': 18})
    
    return exam, s1, s2

@pytest.mark.django_db
class TestPronoteExport:
    def test_export_all_exam(self, corrector_user, exam_setup):
        from rest_framework.test import APIClient
        client = APIClient()
        exam, s1, s2 = exam_setup
        client.force_authenticate(user=corrector_user)
        
        url = reverse('my-students-export-csv')
        response = client.get(url, {'exam_id': str(exam.id)})
        
        assert response.status_code == status.HTTP_200_OK
        assert response['Content-Type'] == 'text/csv'
        content = response.content.decode('utf-8-sig') # with BOM
        assert 'Dupont;Jean' in content
        assert 'Curie;Marie' in content

    def test_export_by_group(self, corrector_user, exam_setup):
        from rest_framework.test import APIClient
        client = APIClient()
        exam, s1, s2 = exam_setup
        client.force_authenticate(user=corrector_user)
        
        url = reverse('my-students-export-csv')
        # Filter by class_name (group_name='T.01')
        response = client.get(url, {
            'exam_id': str(exam.id),
            'group_name': 'T.01',
            'assignment_type': 'classe',
            'level': 'terminale'
        })
        
        assert response.status_code == status.HTTP_200_OK
        content = response.content.decode('utf-8-sig')
        assert 'Dupont;Jean' in content
        assert 'Curie;Marie' in content # Both are T01

        # Filter by group (G1)
        response = client.get(url, {
            'exam_id': str(exam.id),
            'group_name': 'G1',
            'assignment_type': 'groupe',
            'level': 'terminale'
        })
        assert response.status_code == status.HTTP_200_OK
        content = response.content.decode('utf-8-sig')
        assert 'Dupont;Jean' in content
        assert 'Curie;Marie' not in content
