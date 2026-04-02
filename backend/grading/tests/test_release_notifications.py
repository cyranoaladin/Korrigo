from unittest.mock import Mock, patch

import pytest
from django.core import mail
from django.test import override_settings
from rest_framework.test import APIClient

from exams.models import Exam, Copy
from students.models import Student
from grading.tasks import notify_students_results_released


@pytest.mark.django_db
def test_release_results_queues_notification_task(admin_user, teacher_user):
    exam = Exam.objects.create(name="Release Mail Exam", date="2026-04-02")
    copy = Copy.objects.create(
        exam=exam,
        anonymous_id="REL001",
        status=Copy.Status.FINALIZED,
        assigned_corrector=teacher_user,
    )
    Student.objects.create(
        first_name="Eleve",
        last_name="Mail",
        class_name="TG1",
        date_naissance="2007-01-01",
        email="eleve.mail@ert.tn",
        user=None,
    )
    copy.student = Student.objects.get(email="eleve.mail@ert.tn")
    copy.save(update_fields=["student"])

    client = APIClient()
    client.force_authenticate(user=admin_user)

    with patch("grading.tasks.notify_students_results_released.delay", return_value=Mock(id="task-123")) as mocked_delay:
        response = client.post(f"/api/grading/exams/{exam.id}/release-results/")

    assert response.status_code == 200
    assert response.data["notification_task"] == "queued"
    assert response.data["task_id"] == "task-123"
    mocked_delay.assert_called_once_with(str(exam.id))


@pytest.mark.django_db
@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    SERVER_EMAIL="noreply@korrigo.test",
    FRONTEND_URL="https://korrigo.labomaths.tn",
)
def test_notify_students_results_released_sends_mail(teacher_user):
    exam = Exam.objects.create(name="Release Mail Exam", date="2026-04-02")
    student = Student.objects.create(
        first_name="Eleve",
        last_name="Mail",
        class_name="TG1",
        date_naissance="2007-01-01",
        email="eleve.mail@ert.tn",
    )
    Copy.objects.create(
        exam=exam,
        anonymous_id="REL002",
        status=Copy.Status.FINALIZED,
        student=student,
        assigned_corrector=teacher_user,
    )

    result = notify_students_results_released(str(exam.id))

    assert result["sent"] == 1
    assert result["errors"] == []
    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == ["eleve.mail@ert.tn"]
    assert "Vos résultats" in mail.outbox[0].subject

