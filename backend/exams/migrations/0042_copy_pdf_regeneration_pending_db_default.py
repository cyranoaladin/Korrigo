from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("exams", "0041_merge_20260514_0001"),
    ]

    operations = [
        migrations.RunSQL(
            sql=(
                "ALTER TABLE exams_copy "
                "ALTER COLUMN pdf_regeneration_pending SET DEFAULT FALSE"
            ),
            reverse_sql=(
                "ALTER TABLE exams_copy "
                "ALTER COLUMN pdf_regeneration_pending DROP DEFAULT"
            ),
        ),
    ]
