from django.db import migrations


def set_pdf_regeneration_pending_default(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    schema_editor.execute(
        "ALTER TABLE exams_copy "
        "ALTER COLUMN pdf_regeneration_pending SET DEFAULT FALSE"
    )


def drop_pdf_regeneration_pending_default(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    schema_editor.execute(
        "ALTER TABLE exams_copy "
        "ALTER COLUMN pdf_regeneration_pending DROP DEFAULT"
    )


class Migration(migrations.Migration):

    dependencies = [
        ("exams", "0041_merge_20260514_0001"),
    ]

    operations = [
        migrations.RunPython(
            set_pdf_regeneration_pending_default,
            reverse_code=drop_pdf_regeneration_pending_default,
        ),
    ]
