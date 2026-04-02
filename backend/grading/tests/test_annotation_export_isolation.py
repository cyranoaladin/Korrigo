import io
import zipfile

import pytest
from rest_framework.test import APIClient

from exams.models import Copy, Exam
from grading.models import Annotation, QuestionRemark, Score
from students.models import Student


@pytest.fixture
def export_exam(db):
    return Exam.objects.create(name="Export Isolation Exam", date="2026-04-02")


@pytest.fixture
def finalized_copy(db, export_exam, teacher_user):
    student = Student.objects.create(
        first_name="Export",
        last_name="Isolation",
        class_name="TG1",
        date_naissance="2007-01-01",
        email="export.isolation@ert.tn",
    )
    copy = Copy.objects.create(
        exam=export_exam,
        student=student,
        anonymous_id="EXPISO001",
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
def test_teacher_export_does_not_include_student_id(teacher_user, finalized_copy):
    client = APIClient()
    client.force_authenticate(user=teacher_user)

    response = client.get(f"/api/grading/copies/{finalized_copy.id}/export-annotations/")

    assert response.status_code == 200
    assert "student_id" not in response.data


@pytest.mark.django_db
def test_admin_export_includes_student_id(admin_user, finalized_copy):
    client = APIClient()
    client.force_authenticate(user=admin_user)

    response = client.get(f"/api/grading/copies/{finalized_copy.id}/export-annotations/")

    assert response.status_code == 200
    assert response.data["student_id"] == finalized_copy.student_id


@pytest.mark.django_db
def test_exam_zip_export_one_file_per_copy(admin_user, finalized_copy, export_exam):
    client = APIClient()
    client.force_authenticate(user=admin_user)

    response = client.get(
        f"/api/grading/exams/{export_exam.id}/export-all-annotations/?format=zip"
    )

    assert response.status_code == 200
    archive = zipfile.ZipFile(io.BytesIO(response.content))
    names = archive.namelist()
    assert "meta.json" in names
    copy_files = [name for name in names if name.startswith("copies/")]
    assert len(copy_files) == 1
