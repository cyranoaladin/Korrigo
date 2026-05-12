"""
Tests unitaires : accès Direction à l'endpoint /api/exams/{exam_id}/student-list/
"""
import pytest
from datetime import date
from django.contrib.auth.models import Group
from rest_framework.test import APIClient

from exams.models import Copy, Exam
from students.models import Student


@pytest.fixture
def direction_user(db):
    from django.contrib.auth import get_user_model
    User = get_user_model()
    user = User.objects.create_user(
        username="direction_test",
        password="testpass123",  # nosec B106
        is_staff=False,
        is_superuser=False
    )
    g, _ = Group.objects.get_or_create(name="direction_all")
    user.groups.add(g)
    return user


@pytest.fixture
def exam_with_copies(db, admin_user):
    exam = Exam.objects.create(name="EAM_TEST", date=date(2026, 4, 4))
    student = Student.objects.create(
        first_name="YASMINE",
        last_name="TEST",
        date_naissance=date(2009, 1, 1),
        class_name="1.01",
        email="yasmine.test@ert.tn",
    )
    Copy.objects.create(
        exam=exam,
        anonymous_id="EAM-T-001",
        student=student,
        status=Copy.Status.FINALIZED,
        assigned_corrector=admin_user,
    )
    Copy.objects.create(
        exam=exam,
        anonymous_id="EAM-T-002",
        student=None,
        status=Copy.Status.READY,
        assigned_corrector=admin_user,
    )
    return exam


@pytest.mark.django_db
def test_direction_user_can_access_student_list(direction_user, exam_with_copies):
    client = APIClient()
    client.force_authenticate(user=direction_user)
    response = client.get(f"/api/exams/{exam_with_copies.id}/student-list/")
    assert response.status_code == 200
    assert "copies" in response.data


@pytest.mark.django_db
def test_direction_user_sees_all_copies_not_only_finalized(direction_user, exam_with_copies):
    """Direction = vue admin complète (pas filtrée par classe/groupe)."""
    client = APIClient()
    client.force_authenticate(user=direction_user)
    response = client.get(f"/api/exams/{exam_with_copies.id}/student-list/")
    assert response.status_code == 200
    copies = response.data["copies"]
    # Les 2 copies (FINALIZED + READY) doivent être visibles
    assert len(copies) == 2


@pytest.mark.django_db
def test_anonymous_user_gets_401_or_403(exam_with_copies):
    client = APIClient()
    response = client.get(f"/api/exams/{exam_with_copies.id}/student-list/")
    assert response.status_code in (401, 403)


@pytest.mark.django_db
def test_admin_still_works(admin_user, exam_with_copies):
    """Pas de régression pour Admin."""
    client = APIClient()
    client.force_authenticate(user=admin_user)
    response = client.get(f"/api/exams/{exam_with_copies.id}/student-list/")
    assert response.status_code == 200


@pytest.mark.django_db
def test_teacher_still_works(teacher_user, exam_with_copies):
    """Pas de régression pour Teacher (filtrage par ses classes/groupes)."""
    client = APIClient()
    client.force_authenticate(user=teacher_user)
    response = client.get(f"/api/exams/{exam_with_copies.id}/student-list/")
    assert response.status_code == 200
