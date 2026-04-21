import pytest
from rest_framework.test import APIClient

from students.models import Student


@pytest.mark.django_db
def test_auth_status_returns_student_identity_from_session_fallback():
    student = Student.objects.create(
        first_name="YASMINE",
        last_name="MNIF",
        email="yasmine.mnif-e@ert.tn",
        class_name="3.3",
        date_naissance="2011-03-28",
    )

    client = APIClient()
    session = client.session
    session["student_id"] = student.id
    session["role"] = "Student"
    session.save()

    response = client.get("/api/auth/status/")

    assert response.status_code == 200
    assert response.data == {
        "authenticated": True,
        "role": "Student",
        "user": {
            "id": student.id,
            "first_name": "YASMINE",
            "last_name": "MNIF",
            "email": "yasmine.mnif-e@ert.tn",
        },
    }
