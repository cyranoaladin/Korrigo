import pytest
import os
import fitz # PyMuPDF
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from exams.models import Exam, Copy, Booklet
from grading.models import GradingEvent
from django.contrib.auth.models import Group
from core.auth import UserRole

User = get_user_model()

@pytest.mark.api
@pytest.mark.django_db
class TestIntegrationReal:
    """
    Real Integration Tests adapting the hardening script logic.
    Uses REAL PyMuPDF, REAL DB, and TEMP FILESYSTEM.
    """

    @pytest.fixture(autouse=True)
    def setup_env(self, settings, tmpdir):
        # Temp Media Root for Real Writes
        settings.MEDIA_ROOT = str(tmpdir.mkdir('media'))
        settings.SECURE_SSL_REDIRECT = False
        settings.SESSION_COOKIE_SECURE = False
        settings.CSRF_COOKIE_SECURE = False
        return settings.MEDIA_ROOT

    @pytest.fixture
    def real_pdf_path(self, tmpdir):
        """Create a real valid PDF using PyMuPDF"""
        path = str(tmpdir.join("test_real.pdf"))
        doc = fitz.open()
        for i in range(3):
            page = doc.new_page()
            page.insert_text((50, 50), f"Page {i+1} - Real Content", fontsize=20)
        doc.save(path)
        doc.close()
        return path

    @pytest.fixture
    def teacher(self):
        u = User.objects.create_user(username='teacher_real', password='password', is_staff=True)
        g, _ = Group.objects.get_or_create(name=UserRole.TEACHER)
        u.groups.add(g)
        return u

    @pytest.fixture
    def exam(self):
        return Exam.objects.create(name="Real Integration Exam", date="2024-01-01")

    def test_full_import_flow_real_fs(self, teacher, exam, real_pdf_path, settings):
        """
        End-to-End API Flow with Real Filesystem side effects.
        """
        client = APIClient()
        client.force_authenticate(user=teacher)

        # 1. IMPORT
        # Use simple open/close or context manager, but ensure it's closed before assertion if needed
        # Client.post reads the file.
        with open(real_pdf_path, 'rb') as f:
            resp = client.post(
                f"/api/exams/{exam.id}/copies/import/",
                {'pdf_file': f},
                format='multipart'
            )
        # File is auto-closed by 'with' block here
        
        assert resp.status_code == 201
        copy_id = resp.data['id']
        
        # 2. VERIFY DB
        copy = Copy.objects.get(id=copy_id)
        assert copy.status == Copy.Status.STAGING
        assert copy.booklets.count() == 1
        booklet = copy.booklets.first()
        assert len(booklet.pages_images) == 3
        
        # 3. VERIFY FILESYSTEM (No Mocks!)
        media_root = settings.MEDIA_ROOT
        for rel_path in booklet.pages_images:
            full_path = os.path.join(media_root, rel_path)
            assert os.path.exists(full_path), f"File missing: {full_path}"
            assert os.path.getsize(full_path) > 1000, "File too small (ghost file?)"

        # 4. VERIFY AUDIT
        assert GradingEvent.objects.filter(copy=copy, action=GradingEvent.Action.IMPORT).exists()

    def test_security_gates_real(self, teacher, exam):
        """
        Verify Security Gates logic with DB state integration.
        """
        client = APIClient()
        client.force_authenticate(user=teacher)
        
        # Setup Copy
        copy = Copy.objects.create(exam=exam, anonymous_id="SECURE_TEST")
        
        # 1. Final PDF Gate
        copy.status = Copy.Status.LOCKED
        copy.save()
        resp = client.get(f"/api/grading/copies/{copy.id}/final-pdf/")
        assert resp.status_code == 403
        
        # 2. Audit Gate (Teacher OK)
        resp = client.get(f"/api/grading/copies/{copy.id}/audit/")
        assert resp.status_code == 200

    def test_student_block_real(self, exam):
        """
        Verify Student blocks on real endpoints.
        """
        student = User.objects.create_user(username='student_real', password='password', is_staff=False)
        client = APIClient()
        client.force_authenticate(user=student)
        
        resp = client.post(f"/api/exams/{exam.id}/copies/import/", {})
        assert resp.status_code == 403
