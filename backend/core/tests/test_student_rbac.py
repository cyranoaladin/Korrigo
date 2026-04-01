"""
Tests RBAC spécifiques aux rôles élèves.
Vérifie l'isolation des données et les permissions strictes.
"""
import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from rest_framework.test import APIClient

from core.auth import UserRole, create_user_roles, IsStudent
from students.models import Student
from exams.models import Exam, Copy

User = get_user_model()


@pytest.fixture
def roles(db):
    return create_user_roles()


@pytest.fixture
def teacher_user(db, roles):
    u = User.objects.create_user(username='teacher_rbac', password='pass', is_staff=True)
    u.groups.add(roles[1])  # teacher group
    return u


@pytest.fixture
def student_terminale(db, roles):
    u = User.objects.create_user(username='eleve_tle', password='pass')
    u.groups.add(roles[2])  # student group
    s = Student.objects.create(
        first_name='Alice', last_name='Dupont',
        date_naissance='2007-05-10', class_name='Terminale S',
        email='alice@ert.tn', user=u
    )
    return u, s


@pytest.fixture
def student_troisieme(db, roles):
    u = User.objects.create_user(username='eleve_3eme', password='pass')
    u.groups.add(roles[2])
    s = Student.objects.create(
        first_name='Bob', last_name='Martin',
        date_naissance='2011-08-22', class_name='3.5',
        email='bob@ert.tn', user=u
    )
    return u, s


@pytest.mark.django_db
class TestStudentRBAC:

    def test_student_cannot_access_corrector_endpoint(self, student_terminale):
        """Un élève ne peut pas accéder aux endpoints Teacher (copies correcteur)."""
        user, _ = student_terminale
        client = APIClient()
        client.force_authenticate(user=user)
        response = client.get('/api/copies/')
        assert response.status_code in [403, 401]

    def test_teacher_fallback_role_unknown_not_teacher(self, roles):
        """Un user sans groupe reçoit role='Unknown', pas 'Teacher'."""
        u = User.objects.create_user(username='nobody', password='pass')
        client = APIClient()
        client.force_authenticate(user=u)
        response = client.get('/api/me/')
        assert response.status_code == 200
        assert response.data['role'] == 'Unknown'

    def test_student_without_profile_denied(self, roles):
        """Un user dans le groupe Student SANS profil Student lié est refusé."""
        u = User.objects.create_user(username='fake_student', password='pass')
        u.groups.add(roles[2])
        perm = IsStudent()
        mock_request = type('MockRequest', (), {'user': u})()
        assert perm.has_permission(mock_request, None) is False

    def test_student_with_profile_allowed(self, student_terminale):
        """Un user dans le groupe Student AVEC profil Student lié est autorisé."""
        user, _ = student_terminale
        perm = IsStudent()
        mock_request = type('MockRequest', (), {'user': user})()
        assert perm.has_permission(mock_request, None) is True

    def test_corrector_serializer_hides_student_field(self, teacher_user):
        """CorrectorCopySerializer n'expose pas le champ student."""
        from exams.serializers import CorrectorCopySerializer
        exam = Exam.objects.create(name='Test', date='2026-01-01')
        student_obj = Student.objects.create(
            first_name='Hidden', last_name='Student',
            date_naissance='2007-01-01', class_name='TG1'
        )
        copy = Copy.objects.create(
            exam=exam, anonymous_id='TEST-HIDE-001',
            status=Copy.Status.READY, student=student_obj,
            is_identified=True
        )
        serializer = CorrectorCopySerializer(copy)
        data = serializer.data
        assert 'student' not in data
        assert 'student_name' not in data
        assert 'is_identified' not in data
