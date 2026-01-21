import pytest
from rest_framework import status
from django.core.files.base import ContentFile
from django.contrib.auth import get_user_model
from exams.models import Exam, Copy
from grading.models import GradingEvent
from rest_framework.test import APIClient
import io

User = get_user_model()

@pytest.fixture
def api_client():
    return APIClient()

@pytest.fixture(autouse=True)
def media_root(settings, tmpdir):
    settings.MEDIA_ROOT = str(tmpdir.mkdir('media'))
    settings.SECURE_SSL_REDIRECT = False
    return settings.MEDIA_ROOT

@pytest.fixture
def teacher_user(db):
    user = User.objects.create_user(username='teacher', password='password123', is_staff=True)
    return user

@pytest.fixture
def student_user(db):
    user = User.objects.create_user(username='student_user', password='password123', is_staff=False)
    return user

@pytest.fixture
def exam(db):
    return Exam.objects.create(name="Test Exam", date="2024-06-01", is_processed=False)

@pytest.mark.django_db
def test_import_permissions_forbidden_for_non_staff(api_client, student_user, exam):
    """
    Ensure non-staff users cannot access the import endpoint.
    """
    api_client.force_authenticate(user=student_user)
    # Prefer hard path to avoid reverse ambiguity if names vary
    # Note: URL structure verified in urls.py
    url = f"/api/exams/{exam.id}/copies/import/"
    
    # Fake PDF
    pdf_file = io.BytesIO(b"%PDF-1.4 empty pdf")
    pdf_file.name = "test.pdf"
    
    response = api_client.post(url, {'pdf_file': pdf_file}, format='multipart')
    
    # Close explicit
    pdf_file.close()
    
    assert response.status_code == status.HTTP_403_FORBIDDEN

@pytest.mark.django_db
def test_import_success_for_teacher_creates_copy_booklet_and_audit(api_client, teacher_user, exam, monkeypatch):
    """
    Ensure teacher can import and it creates Copy/Booklet/Audit.
    Mocks rasterization to avoid fitz usage and filesystem dependency.
    """
    api_client.force_authenticate(user=teacher_user)
    url = f"/api/exams/{exam.id}/copies/import/"
    
    # Mock rasterization to avoid fitz and filesystem dependency
    from grading.services import GradingService
    def fake_rasterize(copy):
        return [f"copies/pages/{copy.id}/p000.png", f"copies/pages/{copy.id}/p001.png"]
    monkeypatch.setattr(GradingService, "_rasterize_pdf", staticmethod(fake_rasterize))
    
    pdf_file = io.BytesIO(b"%PDF-1.4 Fake Content")
    pdf_file.name = "real.pdf"
    
    response = api_client.post(url, {'pdf_file': pdf_file}, format='multipart')
    
    # Close explict
    pdf_file.close()
    
    assert response.status_code == status.HTTP_201_CREATED
    assert response.data['status'] == 'STAGING'
    
    copy = Copy.objects.get(id=response.data['id'])
    assert copy.exam == exam
    assert copy.booklets.count() == 1
    
    # Verify P0.1 & P0.2 fixes
    booklet = copy.booklets.first()
    assert booklet.pages_images == [f"copies/pages/{copy.id}/p000.png", f"copies/pages/{copy.id}/p001.png"]
    assert booklet.start_page == 1 # 1-indexed fix
    assert booklet.end_page == 2
    
    # Check Audit
    event = GradingEvent.objects.filter(copy=copy, action=GradingEvent.Action.IMPORT).first()
    assert event is not None
    assert event.actor == teacher_user

@pytest.mark.django_db
def test_audit_endpoint_requires_staff(api_client, student_user, teacher_user, exam):
    """
    Ensure audit log is protected.
    """
    copy = Copy.objects.create(exam=exam, anonymous_id="AUDIT-TEST", status=Copy.Status.READY)
    url = f"/api/copies/{copy.id}/audit/"
    
    # Student -> 403
    api_client.force_authenticate(user=student_user)
    response = api_client.get(url)
    assert response.status_code == status.HTTP_403_FORBIDDEN
    
    # Teacher -> 200
    api_client.force_authenticate(user=teacher_user)
    response = api_client.get(url)
    assert response.status_code == status.HTTP_200_OK

@pytest.mark.django_db
def test_final_pdf_security_gate(api_client, teacher_user, exam):
    """
    Teacher cannot download final PDF unless GRADED.
    """
    copy = Copy.objects.create(exam=exam, anonymous_id="SECURE-PDF", status=Copy.Status.LOCKED)
    # Attach a fake file
    content = ContentFile(b"PDF CONTENT")
    copy.final_pdf.save("final.pdf", content)
    copy.save()
    # Explicit close not needed as ContentFile is memory, but let's be safe if backend opens it
    if copy.final_pdf:
        copy.final_pdf.close()
    
    url = f"/api/copies/{copy.id}/final-pdf/"
    api_client.force_authenticate(user=teacher_user)
    
    # LOCKED -> 403
    response = api_client.get(url)
    assert response.status_code == status.HTTP_403_FORBIDDEN
    
    # GRADED -> 200
    copy.status = Copy.Status.GRADED
    copy.save()
    response = api_client.get(url)
    assert response.status_code == status.HTTP_200_OK
    assert response['Content-Disposition'].startswith('attachment; filename=')
