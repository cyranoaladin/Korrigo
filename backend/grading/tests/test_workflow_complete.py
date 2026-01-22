
import pytest
import os
import shutil
from django.conf import settings
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from exams.models import Exam, Copy, Booklet
from grading.models import GradingEvent, Annotation

User = get_user_model()
FIXTURES_DIR = os.path.join(settings.BASE_DIR, "grading/tests/fixtures/pdfs")

@pytest.mark.api
@pytest.mark.django_db
class TestWorkflowComplete:
    
    @pytest.fixture(autouse=True)
    def setup_env(self, settings, tmpdir):
        # Temp Media Root
        from pathlib import Path
        settings.MEDIA_ROOT = Path(str(tmpdir.mkdir('media')))
        return settings.MEDIA_ROOT

    @pytest.fixture
    def teacher(self):
        return User.objects.create_user(username='teacher_flow', password='password', is_staff=True)

    @pytest.fixture
    def student(self):
        return User.objects.create_user(username='student_flow', password='password', is_staff=False)

    @pytest.fixture
    def exam(self):
        return Exam.objects.create(name="E2E Exam", date="2024-01-01")

    def test_workflow_teacher_full_cycle_success(self, teacher, exam):
        client = APIClient()
        client.force_authenticate(user=teacher)
        
        # 1. IMPORT
        pdf_path = os.path.join(FIXTURES_DIR, "copy_2p_simple.pdf")
        with open(pdf_path, 'rb') as f:
            resp = client.post(
                f"/api/exams/{exam.id}/copies/import/",
                {'pdf_file': f},
                format='multipart'
            )
        assert resp.status_code == 201
        copy_id = resp.data['id']
        copy = Copy.objects.get(id=copy_id)
        
        try:
            assert copy.status == Copy.Status.STAGING
            # Verify pages (2 pages in fixture)
            assert copy.booklets.count() == 1
            assert len(copy.booklets.first().pages_images) == 2
            
            # Transition to READY (Simulate Identification/Verification step)
            copy.status = Copy.Status.READY
            copy.save()
            
            # 2. ANNOTATE (CRUD)
            # Create
            ann_data = {
                "page_index": 0,
                "x": 0.1, "y": 0.1, "w": 0.2, "h": 0.1,
                "type": Annotation.Type.COMMENT,
                "content": "Good job",
                "score_delta": 2
            }
            resp = client.post(f"/api/copies/{copy_id}/annotations/", ann_data, format='json')
            assert resp.status_code == 201
            ann1_id = resp.data['id']

            # Create another
            ann_data2 = {
                "page_index": 1,
                "x": 0.5, "y": 0.5, "w": 0.1, "h": 0.1,
                "type": Annotation.Type.ERROR,
                "content": "Typo",
                "score_delta": -1
            }
            resp = client.post(f"/api/copies/{copy_id}/annotations/", ann_data2, format='json')
            assert resp.status_code == 201
            ann2_id = resp.data['id']
            
            # Update (PATCH)
            resp = client.patch(f"/api/annotations/{ann1_id}/", {"score_delta": 3}, format='json')
            assert resp.status_code == 200
            assert resp.data['score_delta'] == 3
            
            # Delete
            resp = client.delete(f"/api/annotations/{ann2_id}/")
            assert resp.status_code == 204
            assert Annotation.objects.count() == 1 # Only ann1 remains
            
            # 3. LOCK
            resp = client.post(f"/api/copies/{copy_id}/lock/", {}, format='json')
            assert resp.status_code == 200
            copy.refresh_from_db()
            assert copy.status == Copy.Status.LOCKED
            
            # Verify Lock enforcement (Cannot create annotation)
            resp = client.post(f"/api/copies/{copy_id}/annotations/", ann_data, format='json')
            assert resp.status_code == 400 
            
            # 4. FINALIZE
            resp = client.post(f"/api/copies/{copy_id}/finalize/", {}, format='json')
            assert resp.status_code == 200
            copy.refresh_from_db()
            assert copy.status == Copy.Status.GRADED
            
            # Verify Score (ann1 score_delta=3)
            # Find audit event for FINALIZE
            event = GradingEvent.objects.filter(copy=copy, action=GradingEvent.Action.FINALIZE).first()
            assert event is not None
            assert event.metadata['final_score'] == 3
            
            # 5. DOWNLOAD FINAL PDF
            url = f"/api/copies/{copy_id}/final-pdf/"
            resp = client.get(url)
            assert resp.status_code == 200
            assert resp['Content-Type'] == 'application/pdf'
            # Consume content to ensure closure?
            _ = b"".join(resp.streaming_content)
            if hasattr(resp, 'close'): resp.close()
            
            # 6. AUDIT TRAIL VERIFICATION
            actions = list(GradingEvent.objects.filter(copy=copy).values_list('action', flat=True))
            # Expected: IMPORT, ANNOTATE_CREATE (x2), ANNOTATE_UPDATE, ANNOTATE_DELETE, LOCK, FINALIZE
            # Expected: IMPORT, ANNOTATE_CREATE (x2), ANNOTATE_UPDATE, ANNOTATE_DELETE, LOCK, FINALIZE
            expected = [
                GradingEvent.Action.IMPORT,
                GradingEvent.Action.CREATE_ANN,
                GradingEvent.Action.CREATE_ANN,
                GradingEvent.Action.UPDATE_ANN,
                GradingEvent.Action.DELETE_ANN,
                GradingEvent.Action.LOCK,
                GradingEvent.Action.FINALIZE
            ]
            
            # Use distinct check or just ensure all expected are present
            # Since ordering might be reverse (timestamp desc), we check presence
            for act in expected:
                assert act in actions

        finally:
            # Cleanup
            if copy.final_pdf:
                 if hasattr(copy.final_pdf, 'close'): copy.final_pdf.close()
                 if hasattr(copy.final_pdf, 'file') and copy.final_pdf.file: copy.final_pdf.file.close()
                 copy.final_pdf.delete(save=False)
            
            # Also clean up source pdf if needed (it is closed by with block but file field might be open?)
            if copy.pdf_source:
                 if hasattr(copy.pdf_source, 'close'): copy.pdf_source.close()
                 if hasattr(copy.pdf_source, 'file') and copy.pdf_source.file: copy.pdf_source.file.close()
                 copy.pdf_source.delete(save=False)
            
            copy.delete()

    def test_workflow_import_corrupted_rollback(self, teacher, exam):
        client = APIClient()
        client.force_authenticate(user=teacher)
        
        pdf_path = os.path.join(FIXTURES_DIR, "copy_corrupted.pdf")
        
        with open(pdf_path, 'rb') as f:
            resp = client.post(
                f"/api/exams/{exam.id}/copies/import/",
                {'pdf_file': f},
                format='multipart'
            )
        
        assert resp.status_code in [400, 500]
        assert Copy.objects.count() == 0
        assert Booklet.objects.count() == 0

    def test_workflow_student_access_denied(self, student, exam):
        client = APIClient()
        client.force_authenticate(user=student)
        
        # 1. IMPORT denied
        resp = client.post(f"/api/exams/{exam.id}/copies/import/", {}, format='json')
        assert resp.status_code == 403
        
        # Create a copy (as admin) to test other endpoints
        copy = Copy.objects.create(exam=exam, anonymous_id="STUDENT_TEST", status=Copy.Status.READY)
        
        # 2. ANNOTATE denied
        ann_data = {
            "page_index": 0, "x": 0.1, "y": 0.1, "w": 0.1, "h": 0.1,
            "type": Annotation.Type.COMMENT, "content": "Hacker"
        }
        resp = client.post(f"/api/copies/{copy.id}/annotations/", ann_data, format='json')
        assert resp.status_code == 403
        
        # 3. LOCK denied
        resp = client.post(f"/api/copies/{copy.id}/lock/", {}, format='json')
        assert resp.status_code == 403
        
        # 4. FINALIZE denied
        resp = client.post(f"/api/copies/{copy.id}/finalize/", {}, format='json')
        assert resp.status_code == 403
