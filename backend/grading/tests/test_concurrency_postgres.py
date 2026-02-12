import threading
import datetime
import unittest.mock

import pytest
from django.utils import timezone


pytestmark = pytest.mark.django_db(transaction=True)


@pytest.mark.postgres
def test_finalize_concurrent_requests_flatten_called_once_postgres(teacher_user):
    """Postgres-only: two concurrent finalize attempts on same Copy.

    Run locally:
        pytest -q -m postgres backend/grading/tests/test_concurrency_postgres.py

    Expectations:
    - exactly one finalize succeeds
    - exactly one fails (LockConflictError/ValueError/PermissionError)
    - flatten_copy called exactly once
    - no OperationalError (DB contention handled gracefully)
    """

    from datetime import date
    from exams.models import Booklet, Copy, Exam
    from grading.models import CopyLock
    from grading.services import GradingService

    exam = Exam.objects.create(name="Postgres Concurrency", date=date.today())
    b = Booklet.objects.create(exam=exam, start_page=0, end_page=0, pages_images=["p0.png"])
    copy = Copy.objects.create(
        exam=exam,
        anonymous_id="PG-CONC",
        status=Copy.Status.LOCKED,
        locked_at=timezone.now(),
        locked_by=teacher_user,
    )
    copy.booklets.add(b)

    lock = CopyLock.objects.create(
        copy=copy,
        owner=teacher_user,
        expires_at=timezone.now() + datetime.timedelta(minutes=10),
    )

    # Shared mutable state protected by a threading lock
    call_lock = threading.Lock()
    calls = {"count": 0}

    def flatten_side_effect(_copy):
        with call_lock:
            calls["count"] += 1
        return b"%PDF-1.4\n%%EOF"

    results = []
    results_lock = threading.Lock()
    ready_barrier = threading.Barrier(2)

    # Patch at module level ONCE so both threads share the same mock
    mock_flattener = unittest.mock.Mock()
    mock_flattener.flatten_copy.side_effect = flatten_side_effect

    def worker():
        from django.db import connections

        try:
            ready_barrier.wait(timeout=5)
            GradingService.finalize_copy(copy, teacher_user, lock_token=str(lock.token))
            with results_lock:
                results.append("ok")
        except Exception as e:
            with results_lock:
                results.append(type(e).__name__)
        finally:
            connections.close_all()

    with unittest.mock.patch(
        "processing.services.pdf_flattener.PDFFlattener",
        return_value=mock_flattener,
    ):
        t1 = threading.Thread(target=worker)
        t2 = threading.Thread(target=worker)
        t1.start()
        t2.start()
        t1.join(timeout=15)
        t2.join(timeout=15)

    # Exactly one thread succeeds, the other gets a business-level error
    assert results.count("ok") == 1, f"Expected 1 success, got: {results}"
    failure_types = {"LockConflictError", "ValueError", "PermissionError"}
    failures = [r for r in results if r != "ok"]
    assert len(failures) == 1, f"Expected 1 failure, got: {results}"
    assert failures[0] in failure_types, (
        f"Expected business error, got {failures[0]}. "
        f"OperationalError means DB contention was not handled."
    )
    assert calls["count"] == 1, f"flatten_copy called {calls['count']} times, expected 1"

    copy.refresh_from_db()
    assert copy.status == Copy.Status.GRADED
    assert bool(copy.final_pdf) is True
    assert copy.final_pdf.size and copy.final_pdf.size > 0
