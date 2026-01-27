import threading
import datetime

import pytest
from django.db import connection
from django.utils import timezone


pytestmark = pytest.mark.django_db(transaction=True)


@pytest.mark.postgres
@pytest.mark.skipif(
    connection.vendor != "postgresql",
    reason="PostgreSQL required for real row-level locking semantics.",
)
def test_finalize_concurrent_requests_flatten_called_once_postgres(teacher_user, exam):
    """Postgres-only: two concurrent finalize attempts on same Copy.

    Run locally:
        pytest -q -m postgres backend/grading/tests/test_concurrency_postgres.py

    Expectations:
    - exactly one finalize succeeds
    - exactly one fails (ValueError/PermissionError/LockConflictError)
    - flatten_copy called exactly once
    """

    from exams.models import Booklet, Copy
    from grading.models import CopyLock
    from grading.services import GradingService

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

    calls = {"count": 0}
    barrier = threading.Barrier(2)

    def flatten_side_effect(_copy):
        barrier.wait(timeout=5)
        calls["count"] += 1
        return b"%PDF-1.4\n%%EOF"

    results = []

    def worker():
        import unittest.mock

        try:
            with unittest.mock.patch(
                "processing.services.pdf_flattener.PDFFlattener.flatten_copy",
                side_effect=flatten_side_effect,
            ):
                GradingService.finalize_copy(copy, teacher_user, lock_token=str(lock.token))
            results.append("ok")
        except Exception as e:
            results.append(type(e).__name__)

    t1 = threading.Thread(target=worker)
    t2 = threading.Thread(target=worker)
    t1.start()
    t2.start()
    t1.join(timeout=10)
    t2.join(timeout=10)

    assert results.count("ok") == 1
    assert calls["count"] == 1

    copy.refresh_from_db()
    assert copy.status == Copy.Status.GRADED
    assert bool(copy.final_pdf) is True
    assert copy.final_pdf.size and copy.final_pdf.size > 0
