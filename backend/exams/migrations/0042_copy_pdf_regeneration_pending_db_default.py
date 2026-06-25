from django.db import connection, migrations


def set_db_default(apps, schema_editor):
    if connection.vendor == "postgresql":
        schema_editor.execute(
            "ALTER TABLE exams_copy "
            "ALTER COLUMN pdf_regeneration_pending SET DEFAULT FALSE"
        )


def drop_db_default(apps, schema_editor):
    if connection.vendor == "postgresql":
        schema_editor.execute(
            "ALTER TABLE exams_copy "
            "ALTER COLUMN pdf_regeneration_pending DROP DEFAULT"
        )


class Migration(migrations.Migration):

    dependencies = [
        ("exams", "0041_merge_20260514_0001"),
    ]

    operations = [
        migrations.RunPython(set_db_default, drop_db_default),
    ]
