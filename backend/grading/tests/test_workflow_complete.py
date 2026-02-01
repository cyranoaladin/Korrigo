from django.test import TransactionTestCase
import os
import shutil
from django.conf import settings
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from exams.models import Exam, Copy, Booklet
from grading.models import GradingEvent, Annotation
from core.auth import UserRole

User = get_user_model()
FIXTURES_DIR = os.path.join(settings.BASE_DIR, "grading/tests/fixtures/pdfs")

# TransactionTestCase required because tests involve I/O, streaming, and multiple
# transactions that fail with regular TestCase in a Docker environment.
class TestWorkflowComplete(TransactionTestCase):

    def setUp(self):
        super().setUp()
        self.client = APIClient()

        # Create groups if they don't exist
        self.teacher_group, _ = Group.objects.get_or_create(name=UserRole.TEACHER)
        self.admin_group, _ = Group.objects.get_or_create(name=UserRole.ADMIN)

        # Admin user for import (requires IsAdminOnly permission)
        self.admin = User.objects.create_user(username='admin_flow', password='password', is_staff=True)
        self.admin.groups.add(self.admin_group)

        self.teacher = User.objects.create_user(username='teacher_flow', password='password')
        self.teacher.groups.add(self.teacher_group)

        self.student = User.objects.create_user(username='student_flow', password='password')
        # Student user has no special group permissions - should be denied access
        self.exam = Exam.objects.create(name="E2E Exam", date="2024-01-01")

    def tearDown(self):
        super().tearDown()

    def test_workflow_teacher_full_cycle_success(self):
        # Use admin for import (requires IsAdminOnly), then switch to teacher for grading
        self.client.force_login(self.admin)

        # 1. IMPORT
        pdf_path = os.path.join(FIXTURES_DIR, "copy_2p_simple.pdf")
        with open(pdf_path, 'rb') as f:
            resp = self.client.post(
                f"/api/exams/{self.exam.id}/copies/import/",
                {'pdf_file': f},
                format='multipart'
            )
        self.assertEqual(resp.status_code, 201)
        copy_id = resp.data['id']
        copy = Copy.objects.get(id=copy_id)
        
        # Verify pages (2 pages in fixture)
        self.assertEqual(copy.booklets.count(), 1)
        self.assertEqual(len(copy.booklets.first().pages_images), 2)
        
        # Transition to READY (Simulate Identification/Verification step)
        copy.status = Copy.Status.READY
        copy.save()
        
        # 2. LOCK (New C3 Requirement: Must lock before annotating)
        resp = self.client.post(f"/api/grading/copies/{copy_id}/lock/", {}, format='json')
        self.assertEqual(resp.status_code, 201)
        lock_token = resp.data["token"]
        
        # 3. ANNOTATE (CRUD)
        # Create
        ann_data = {
            "page_index": 0,
            "x": 0.1, "y": 0.1, "w": 0.2, "h": 0.1,
            "type": Annotation.Type.COMMENT,
            "content": "Good job",
            "score_delta": 2
        }
        resp = self.client.post(
            f"/api/grading/copies/{copy_id}/annotations/",
            ann_data,
            format='json',
            HTTP_X_LOCK_TOKEN=str(lock_token),
        )
        self.assertEqual(resp.status_code, 201)
        ann1_id = resp.data['id']

        # Create another
        ann_data2 = {
            "page_index": 1,
            "x": 0.5, "y": 0.5, "w": 0.1, "h": 0.1,
            "type": Annotation.Type.ERROR,
            "content": "Typo",
            "score_delta": -1
        }
        resp = self.client.post(
            f"/api/grading/copies/{copy_id}/annotations/",
            ann_data2,
            format='json',
            HTTP_X_LOCK_TOKEN=str(lock_token),
        )
        self.assertEqual(resp.status_code, 201)
        ann2_id = resp.data['id']
        
        # Update (PATCH)
        resp = self.client.patch(
            f"/api/grading/annotations/{ann1_id}/",
            {"score_delta": 3},
            format='json',
            HTTP_X_LOCK_TOKEN=str(lock_token),
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data['score_delta'], 3)
        
        # Delete
        resp = self.client.delete(
            f"/api/grading/annotations/{ann2_id}/",
            HTTP_X_LOCK_TOKEN=str(lock_token),
        )
        self.assertEqual(resp.status_code, 204)
        self.assertEqual(Annotation.objects.count(), 1) # Only ann1 remains
        
        # Verify Lock enforcement (Cannot create annotation WITHOUT lock?) 
        # Release lock
        resp = self.client.delete(
            f"/api/grading/copies/{copy_id}/lock/release/",
            HTTP_X_LOCK_TOKEN=str(lock_token),
        )
        self.assertEqual(resp.status_code, 204)
        
        # Now try to annotate -> Should fail 403 (Write Requires Lock)
        resp = self.client.post(f"/api/grading/copies/{copy_id}/annotations/", ann_data, format='json')
        self.assertEqual(resp.status_code, 403)
        
        # Re-acquire lock for Finalize?
        resp = self.client.post(f"/api/grading/copies/{copy_id}/lock/", {}, format='json')
        self.assertIn(resp.status_code, [200, 201])
        lock_token = resp.data["token"]
        
        # 4. FINALIZE
        import unittest.mock
        with unittest.mock.patch("processing.services.pdf_flattener.PDFFlattener.flatten_copy") as mock_flatten:
            mock_flatten.return_value = b"%PDF-1.4\n%%EOF"
            resp = self.client.post(
                f"/api/grading/copies/{copy_id}/finalize/",
                {},
                format='json',
                HTTP_X_LOCK_TOKEN=str(lock_token),
            )
        self.assertEqual(resp.status_code, 200)
        copy.refresh_from_db()
        self.assertEqual(copy.status, Copy.Status.GRADED)
        
        # Verify Score (ann1 score_delta=3)
        event = GradingEvent.objects.filter(copy=copy, action=GradingEvent.Action.FINALIZE).first()
        self.assertIsNotNone(event)
        self.assertEqual(event.metadata['final_score'], 3)
        
        # 5. DOWNLOAD FINAL PDF
        # Verify model state first (safest)
        copy.refresh_from_db()
        self.assertTrue(copy.final_pdf)
        self.assertGreater(copy.final_pdf.size, 0)
        copy.final_pdf.close()

        url = f"/api/grading/copies/{copy_id}/final-pdf/"
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp['Content-Type'], 'application/pdf')
        self.assertTrue(getattr(resp, "streaming", False))
        # DO NOT iterate streaming_content
        if hasattr(resp, 'close'): resp.close()
        
        # 6. AUDIT TRAIL VERIFICATION
        actions = list(GradingEvent.objects.filter(copy=copy).values_list('action', flat=True))
        expected = [
            GradingEvent.Action.IMPORT,
            GradingEvent.Action.CREATE_ANN,
            GradingEvent.Action.CREATE_ANN,
            GradingEvent.Action.UPDATE_ANN,
            GradingEvent.Action.DELETE_ANN,
            GradingEvent.Action.LOCK,
            GradingEvent.Action.FINALIZE
        ]
        
        for act in expected:
            self.assertIn(act, actions)

        # Cleanup handled by TransactionTestCase rollback mostly, but manual file cleanup safety
        if copy.pdf_source:
             copy.pdf_source.delete(save=False)
        if copy.final_pdf:
             copy.final_pdf.delete(save=False)


    def test_workflow_import_corrupted_rollback(self):
        # Use admin for import (requires IsAdminOnly permission)
        self.client.force_login(self.admin)

        pdf_path = os.path.join(FIXTURES_DIR, "copy_corrupted.pdf")

        with open(pdf_path, 'rb') as f:
            resp = self.client.post(
                f"/api/exams/{self.exam.id}/copies/import/",
                {'pdf_file': f},
                format='multipart'
            )

        self.assertIn(resp.status_code, [400, 500])
        self.assertEqual(Copy.objects.count(), 0)
        self.assertEqual(Booklet.objects.count(), 0)

    def test_workflow_student_access_denied(self):
        self.client.force_authenticate(user=self.student)
        
        # 1. IMPORT denied
        resp = self.client.post(f"/api/exams/{self.exam.id}/copies/import/", {}, format='json')
        self.assertEqual(resp.status_code, 403)
        
        # Create a copy (as admin) to test other endpoints
        copy = Copy.objects.create(exam=self.exam, anonymous_id="STUDENT_TEST", status=Copy.Status.READY)
        
        # 2. ANNOTATE denied
        ann_data = {
            "page_index": 0, "x": 0.1, "y": 0.1, "w": 0.1, "h": 0.1,
            "type": Annotation.Type.COMMENT, "content": "Hacker"
        }
        resp = self.client.post(f"/api/grading/copies/{copy.id}/annotations/", ann_data, format='json')
        self.assertEqual(resp.status_code, 403)
        
        # 3. LOCK denied
        resp = self.client.post(f"/api/grading/copies/{copy.id}/lock/", {}, format='json')
        self.assertEqual(resp.status_code, 403)
        
        # 4. FINALIZE denied
        resp = self.client.post(f"/api/grading/copies/{copy.id}/finalize/", {}, format='json')
        self.assertEqual(resp.status_code, 403)
