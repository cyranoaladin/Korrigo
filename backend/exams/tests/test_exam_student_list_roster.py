import pytest
from datetime import date

from django.core.files.base import ContentFile
from rest_framework.test import APIClient

from exams.models import Copy, Exam
from students.models import Student


@pytest.mark.django_db
def test_exam_student_list_includes_roster_students_without_copies(admin_user):
    exam = Exam.objects.create(name="DNB_2026", date=date(2026, 3, 15))
    exam.students_csv.save(
        "dnb_students.csv",
        ContentFile(
            (
                "Nom;Prenom;Date_Naissance;Mail;Classe\n"
                "KAAK;MAYA;02/10/2011;maya.kaak@ert.tn;3.4\n"
                "DUPONT;ALICE;03/10/2011;alice.dupont@ert.tn;3.4\n"
            ).encode("utf-8")
        ),
        save=True,
    )

    student = Student.objects.create(
        first_name="MAYA",
        last_name="KAAK",
        date_naissance=date(2011, 10, 2),
        class_name="3.4",
        email="maya.kaak@ert.tn",
    )
    copy = Copy.objects.create(
        exam=exam,
        anonymous_id="KAAK-001",
        student=student,
        status=Copy.Status.READY,
        assigned_corrector=admin_user,
    )

    client = APIClient()
    client.force_authenticate(user=admin_user)

    response = client.get(f"/api/exams/{exam.id}/student-list/")

    assert response.status_code == 200
    data = response.data["copies"]

    assert len(data) == 2

    kaak = next(row for row in data if row["student_name"] == "KAAK MAYA")
    assert kaak["has_copy"] is True
    assert kaak["copy_id"] == str(copy.id)
    assert kaak["anonymous_id"] == "KAAK-001"
    assert kaak["status"] == Copy.Status.READY

    missing = next(row for row in data if row["student_name"] == "DUPONT ALICE")
    assert missing["has_copy"] is False
    assert missing["copy_id"] is None
    assert missing["status"] == "NO_COPY"
