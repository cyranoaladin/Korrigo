import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from rest_framework.test import APIClient

from core.auth import UserRole
from exams.models import Exam, Copy
from grading.models import Score
from students.models import Student

User = get_user_model()


@pytest.fixture
def exam(db):
    return Exam.objects.create(
        name="Stats Exam",
        date="2026-04-01",
        grading_structure=[
            {"label": "Ex1", "points": 10, "children": [{"label": "Q1", "points": 10}]}
        ],
    )


@pytest.fixture
def teacher_with_exam(db, exam):
    teacher_group, _ = Group.objects.get_or_create(name=UserRole.TEACHER)
    user = User.objects.create_user(
        username="stats_teacher",
        password="testpass123",
        is_staff=True,
    )
    user.groups.add(teacher_group)
    exam.correctors.add(user)
    return user


@pytest.fixture
def student_user_with_profile(db):
    student_group, _ = Group.objects.get_or_create(name=UserRole.STUDENT)
    user = User.objects.create_user(
        username="stats_student",
        password="testpass123",
        email="stats.student@ert.tn",
    )
    user.groups.add(student_group)
    Student.objects.create(
        first_name="Stats",
        last_name="Student",
        date_naissance="2007-01-01",
        class_name="TG1",
        email="stats.student.profile@ert.tn",
        user=user,
    )
    return user


@pytest.fixture
def graded_copy(db, exam, teacher_with_exam):
    copy = Copy.objects.create(
        exam=exam,
        anonymous_id="STATS001",
        status=Copy.Status.FINALIZED,
        assigned_corrector=teacher_with_exam,
    )
    Score.objects.create(copy=copy, scores_data={"Q1": 8})
    return copy


@pytest.mark.django_db
def test_student_cannot_access_stats(student_user_with_profile, exam):
    client = APIClient()
    client.force_authenticate(user=student_user_with_profile)

    response = client.get(f"/api/grading/exams/{exam.id}/stats/")

    assert response.status_code == 403


@pytest.mark.django_db
def test_teacher_can_access_own_stats(teacher_with_exam, exam, graded_copy):
    client = APIClient()
    client.force_authenticate(user=teacher_with_exam)

    response = client.get(f"/api/grading/exams/{exam.id}/stats/")

    assert response.status_code == 200
    assert response.data["exam_id"] == str(exam.id)
    assert response.data["total_copies"] == 1
    assert response.data["graded_copies"] == 1
    assert response.data["lot_stats"]["graded"] == 1
