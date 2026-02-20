
import pytest
from django.db import transaction
from rest_framework.test import APIClient
from exams.models import Copy, Exam, Booklet
from grading.models import Annotation, GradingEvent
from django.contrib.auth.models import Group
from core.auth import UserRole
from django.contrib.auth import get_user_model
from django.utils import timezone
import unittest.mock
import datetime

User = get_user_model()

@pytest.mark.django_db
class TestAntiLoss:

    @pytest.fixture
    def teacher(self):
        u = User.objects.create_user(username='teacher_safe', password='password', is_staff=True)
        g, _ = Group.objects.get_or_create(name=UserRole.TEACHER)
        u.groups.add(g)
        return u

    @pytest.fixture
    def exam(self):
        return Exam.objects.create(name="Safe Exam", date="2024-01-01")

    @pytest.fixture
    def copy(self, exam):
        c = Copy.objects.create(exam=exam, anonymous_id="SAFE-COPY", status=Copy.Status.READY)
        Booklet.objects.create(exam=exam, start_page=0, end_page=2, pages_images=["p0.png", "p1.png"])
        c.booklets.add(Booklet.objects.get(exam=exam))
        return c

    def test_finalize_idempotency_or_safety(self, teacher, copy):
        """
        Finalizing an already finalized copy should be safe (Idempotent 200 or Safe 400/409).
        It MUST NOT re-run flattening or corrupt data.
        Simplified workflow: finalize from READY, no lock required.
        """
        copy.status = Copy.Status.READY
        copy.assigned_corrector = teacher
        copy.save(update_fields=["status", "assigned_corrector"])

        client = APIClient()
        client.force_authenticate(user=teacher)

        with unittest.mock.patch("processing.services.pdf_flattener.PDFFlattener.flatten_copy") as mock_flatten:
            mock_flatten.return_value = b"%PDF-1.4\n%%EOF"
            resp1 = client.post(f"/api/grading/copies/{copy.id}/finalize/")
            assert resp1.status_code == 200
            assert mock_flatten.call_count == 1

            resp2 = client.post(f"/api/grading/copies/{copy.id}/finalize/")
            assert resp2.status_code in [400, 403, 409]
            assert mock_flatten.call_count == 1

    def test_annotation_on_graded_copy_rejected(self, teacher, copy):
        """
        Annotating a GRADED copy must be rejected (400).
        Replaces old lock idempotency test — locks removed.
        """
        copy.status = Copy.Status.GRADED
        copy.save(update_fields=["status"])

        client = APIClient()
        client.force_authenticate(user=teacher)

        resp = client.post(f"/api/grading/copies/{copy.id}/annotations/", {
            "page_index": 0, "x": 0.1, "y": 0.1, "w": 0.1, "h": 0.1,
            "type": "COMMENT", "content": "Should fail"
        }, format='json')
        assert resp.status_code == 400
    def test_annotation_create_atomicity(self, teacher, copy):
        """
        If creating an annotation fails (e.g. at DB level),
        verify no partial data or side effects.
        Simplified workflow: READY copy, no lock required.
        """
        client = APIClient()
        client.force_authenticate(user=teacher)

        copy.status = Copy.Status.READY
        copy.assigned_corrector = teacher
        copy.save(update_fields=["status", "assigned_corrector"])

        ann_data = {
            "page_index": 0, "x": 0.1, "y": 0.1, "w": 0.1, "h": 0.1,
            "type": Annotation.Type.COMMENT, "content": "Atomic"
        }

        # Simulate DB error during save
        with unittest.mock.patch("grading.models.Annotation.save", side_effect=Exception("DB Crash")):
            resp = client.post(
                f"/api/grading/copies/{copy.id}/annotations/",
                ann_data,
                format='json',
            )

        assert resp.status_code == 500
        assert Annotation.objects.count() == 0 # Must be 0
        
    def test_import_transaction_atomicity(self, teacher, exam):
        """
        If import fails halfway (e.g. after Copy creation but before Booklet/Pages),
        Rollback must ensure 0 orphaned objects.
        """
        client = APIClient()
        client.force_authenticate(user=teacher)
        
        # We need to simulate failure AFTER Copy creation but BEFORE Booklet/Image commit.
        # This is tricky via API Client without hooking into Service.
        # But we verified `test_import_pdf_rollback_on_raster_failure` in unit tests.
        # Here we verify it via API if possible, or skip if redundant.
        pass # Covered by grading/tests/test_services_strict_unit.py

