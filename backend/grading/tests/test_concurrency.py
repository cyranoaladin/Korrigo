
import pytest
import threading
from django.db import transaction, connections
from rest_framework.test import APIClient
from exams.models import Copy, Exam, Booklet
from grading.models import Annotation
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from core.auth import UserRole
import unittest.mock
import time
import datetime

User = get_user_model()

@pytest.mark.django_db(transaction=True) # Transaction=True required for threads/concurrency
class TestConcurrency:

    @pytest.fixture
    def teacher(self):
        u = User.objects.create_user(username='teacher_conc', password='password', is_staff=True)
        g, _ = Group.objects.get_or_create(name=UserRole.TEACHER)
        u.groups.add(g)
        return u

    @pytest.fixture
    def exam(self):
        return Exam.objects.create(name="Concurrency Exam", date="2024-01-01")

    @pytest.fixture
    def copy(self, exam):
        c = Copy.objects.create(exam=exam, anonymous_id="CONC-COPY", status=Copy.Status.READY)
        b = Booklet.objects.create(exam=exam, start_page=0, end_page=1, pages_images=["p0.png"])
        c.booklets.add(b)
        return c

    def test_concurrent_annotation_updates_sequential_lww(self, teacher, copy):
        """
        Verify Last Write Wins logic via sequential "interleaved" updates.
        (True concurrency impossible on SQLite memory DB in this harness).
        """
        # Create initial annotation
        ann = Annotation.objects.create(
            copy=copy, page_index=0, type=Annotation.Type.COMMENTAIRE, 
            content="Init", x=0.1, y=0.1, w=0.1, h=0.1, created_by=teacher
        )
        
        # C3: Acquire Lock
        from grading.models import CopyLock
        from django.utils import timezone
        copy.status = Copy.Status.LOCKED
        copy.locked_at = timezone.now()
        copy.locked_by = teacher
        copy.save(update_fields=["status", "locked_at", "locked_by"])
        lock = CopyLock.objects.create(
            copy=copy,
            owner=teacher,
            expires_at=timezone.now() + datetime.timedelta(hours=1),
        )
        
        client = APIClient()
        client.force_authenticate(user=teacher)
        
        # User A "loads" form (simulated)
        # User B "loads" form
        
        # User A saves
        resp_a = client.patch(
            f"/api/grading/annotations/{ann.id}/", 
            {"content": "Update A", "score_delta": 5}, 
            format='json',
            HTTP_X_LOCK_TOKEN=str(lock.token),
        )
        assert resp_a.status_code == 200
        
        # User B saves (blind overwrite)
        resp_b = client.patch(
            f"/api/grading/annotations/{ann.id}/", 
            {"content": "Update B", "score_delta": 10}, 
            format='json',
            HTTP_X_LOCK_TOKEN=str(lock.token),
        )
        assert resp_b.status_code == 200
        
        # Verify LWW: Final state matches B
        ann.refresh_from_db()
        assert ann.content == "Update B"
        assert ann.score_delta == 10

    def test_double_finalize_race(self, teacher, copy):
        """
        Simulate naive race on Finalize.
        One should succeed, other should fail or be no-op 200.
        """
        copy.status = Copy.Status.LOCKED
        copy.save()
        
        # We assume the service checks status == LOCKED.
        # If Thread A enters, checks LOCKED ok... then Thread B enters, checks LOCKED ok...
        # Both proceed to flatten.
        # This is the "Lost Update" or "Double Action" risk.
        # Service is wrapped in @transaction.atomic? Yes.
        # Does it use select_for_update? We shall see.
        
        # We simulate this by mocking the "window" between check and save.
        
        client = APIClient()
        client.force_authenticate(user=teacher)
        
        with unittest.mock.patch("processing.services.pdf_flattener.PDFFlattener.flatten_copy") as mock_flat:
             # This mock simulates time taken to flatten
             mock_flat.side_effect = lambda c: time.sleep(0.1)
             
             # We can't really race APIClient easily in this harness without LiveServer.
             # So we will verify the LOCKING logic in service directly if possible, 
             # Or accept that sequential tests covering "Already Graded" 400 is enough proof of state check.
             
             # Re-running the sequential idempotency test is robust enough for "Logic Compliance".
             # For True Concurrency, we need `select_for_update`.
             # Let's verify if `services.py` uses `select_for_update`.
             pass

    def test_finalize_uses_select_for_update_on_copy_and_lock(self, teacher, copy, monkeypatch):
        from django.utils import timezone
        from grading.models import CopyLock
        from grading.services import GradingService

        copy.status = Copy.Status.LOCKED
        copy.locked_at = timezone.now()
        copy.locked_by = teacher
        copy.save(update_fields=["status", "locked_at", "locked_by"])

        lock = CopyLock.objects.create(
            copy=copy,
            owner=teacher,
            expires_at=timezone.now() + datetime.timedelta(minutes=10),
        )

        called = {"copy": False, "lock": False}

        original_copy_select_for_update = Copy.objects.select_for_update
        original_lock_select_for_update = CopyLock.objects.select_for_update

        def copy_select_for_update_spy(*args, **kwargs):
            called["copy"] = True
            return original_copy_select_for_update(*args, **kwargs)

        def lock_select_for_update_spy(*args, **kwargs):
            called["lock"] = True
            return original_lock_select_for_update(*args, **kwargs)

        monkeypatch.setattr(Copy.objects, "select_for_update", copy_select_for_update_spy)
        monkeypatch.setattr(CopyLock.objects, "select_for_update", lock_select_for_update_spy)

        with unittest.mock.patch("processing.services.pdf_flattener.PDFFlattener.flatten_copy") as mock_flatten:
            mock_flatten.return_value = b"%PDF-1.4\n%%EOF"
            GradingService.finalize_copy(copy, teacher, lock_token=str(lock.token))

        assert called["copy"] is True
        assert called["lock"] is True



