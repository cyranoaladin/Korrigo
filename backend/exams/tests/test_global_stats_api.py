import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from exams.models import Exam, Copy
from students.models import Student


@pytest.mark.django_db
def test_student_cannot_access_global_stats(student_user):
    client = APIClient()
    client.force_authenticate(user=student_user)

    response = client.get("/api/exams/global-stats/")

    assert response.status_code == 403


@pytest.mark.django_db
def test_admin_can_access_global_stats(admin_user, teacher_user):
    exam1 = Exam.objects.create(name="Exam 1", date="2026-04-01")
    exam2 = Exam.objects.create(name="Exam 2", date="2026-04-02", results_released_at=timezone.now())
    Student.objects.create(
        first_name="Alice",
        last_name="Stats",
        class_name="TG1",
        date_naissance="2007-01-01",
        email="alice.stats@ert.tn",
    )
    Copy.objects.create(exam=exam1, anonymous_id="GS1", status=Copy.Status.READY)
    Copy.objects.create(exam=exam1, anonymous_id="GS2", status=Copy.Status.IN_PROGRESS, assigned_corrector=teacher_user)
    Copy.objects.create(exam=exam2, anonymous_id="GS3", status=Copy.Status.FINALIZED, assigned_corrector=teacher_user)

    client = APIClient()
    client.force_authenticate(user=admin_user)

    response = client.get("/api/exams/global-stats/")

    assert response.status_code == 200
    assert response.data["total_exams"] == 2
    assert response.data["total_copies"] == 3
    assert response.data["copies_by_status"]["READY"] == 1
    assert response.data["copies_by_status"]["IN_PROGRESS"] == 1
    assert response.data["copies_by_status"]["FINALIZED"] == 1
    assert response.data["students_count"] == 1
    assert response.data["exams_with_results_released"] == 1
    assert response.data["correctors_count"] >= 1
