import pytest
from django.db import connection


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
