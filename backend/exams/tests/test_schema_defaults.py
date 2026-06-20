import pytest
from django.db import connection

from exams.models import Copy


def test_copy_status_choices_match_live_schema():
    assert [choice[0] for choice in Copy.Status.choices] == [
        "READY",
        "IN_PROGRESS",
        "FINALIZED",
    ]


@pytest.mark.django_db
def test_copy_pdf_regeneration_pending_has_database_default():
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT column_default
            FROM information_schema.columns
            WHERE table_name = 'exams_copy'
              AND column_name = 'pdf_regeneration_pending'
            """
        )
        row = cursor.fetchone()

    assert row is not None
    assert row[0] in ("false", "false::boolean")
