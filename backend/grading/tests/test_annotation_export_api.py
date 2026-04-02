import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from rest_framework.test import APIClient

from core.auth import UserRole
from exams.models import Exam, Copy
from grading.models import Annotation, QuestionRemark, Score

User = get_user_model()


@pytest.fixture
def export_exam(db):
    return Exam.objects.create(name="Export Exam", date="2026-04-02")


@pytest.fixture
def finalized_copy(db, export_exam, teacher_user):
    copy = Copy.objects.create(
        exam=export_exam,
        anonymous_id="EXP001",
        status=Copy.Status.FINALIZED,
        assigned_corrector=teacher_user,
        global_appreciation="Bonne copie",
    )
    Annotation.objects.create(
        copy=copy,
        page_index=0,
        x=0.1,
        y=0.2,
        w=0.3,
        h=0.4,
        content="Bien",
        type=Annotation.Type.COMMENTAIRE,
        created_by=teacher_user,
    )
    QuestionRemark.objects.create(
        copy=copy,
        question_id="Q1",
        remark="Remarque",
        created_by=teacher_user,
    )
    Score.objects.create(copy=copy, scores_data={"Q1": 7}, final_comment="Continue")
    return copy


@pytest.mark.django_db
def test_teacher_can_export_assigned_copy_annotations(teacher_user, finalized_copy):
    client = APIClient()
    client.force_authenticate(user=teacher_user)

    response = client.get(f"/api/grading/copies/{finalized_copy.id}/export-annotations/")

    assert response.status_code == 200
    assert response.data["copy_id"] == str(finalized_copy.id)
    assert response.data["scores"] == {"Q1": 7}
    assert response.data["global_appreciation"] == "Bonne copie"
    assert len(response.data["annotations"]) == 1
    assert len(response.data["remarks"]) == 1


@pytest.mark.django_db
def test_other_teacher_cannot_export_copy_annotations(finalized_copy):
    teacher = User.objects.create_user(
        username="other_export_teacher",
        password="testpass123",
        is_staff=True,
    )
    teacher_group, _ = Group.objects.get_or_create(name=UserRole.TEACHER)
    teacher.groups.add(teacher_group)
    client = APIClient()
    client.force_authenticate(user=teacher)

    response = client.get(f"/api/grading/copies/{finalized_copy.id}/export-annotations/")

    assert response.status_code == 403


@pytest.mark.django_db
def test_admin_can_export_exam_annotations_as_json(admin_user, finalized_copy, export_exam):
    client = APIClient()
    client.force_authenticate(user=admin_user)

    response = client.get(f"/api/grading/exams/{export_exam.id}/export-all-annotations/?format=json")

    assert response.status_code == 200
    assert response.data["exam_id"] == str(export_exam.id)
    assert response.data["copies_count"] == 1
    assert response.data["copies"][0]["anonymous_id"] == finalized_copy.anonymous_id


@pytest.mark.django_db
def test_admin_can_export_exam_annotations_as_zip(admin_user, finalized_copy, export_exam):
    client = APIClient()
    client.force_authenticate(user=admin_user)

    response = client.get(f"/api/grading/exams/{export_exam.id}/export-all-annotations/?format=zip")

    assert response.status_code == 200
    assert response["Content-Type"] == "application/zip"
    assert "attachment;" in response["Content-Disposition"]
