import django.utils.timezone
from django.db import migrations, models


def backfill_timestamps(apps, schema_editor):
    """Backfill NULLs with current time — works on both SQLite and PostgreSQL."""
    Exam = apps.get_model("exams", "Exam")
    now = django.utils.timezone.now()
    Exam.objects.filter(created_at__isnull=True).update(created_at=now)
    Exam.objects.filter(updated_at__isnull=True).update(updated_at=now)


class Migration(migrations.Migration):

    dependencies = [
        ("exams", "0036_add_default_exam_date"),
    ]

    operations = [
        migrations.RunPython(backfill_timestamps, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="exam",
            name="created_at",
            field=models.DateTimeField(
                auto_now_add=True,
                verbose_name="Date de création",
            ),
        ),
        migrations.AlterField(
            model_name="exam",
            name="updated_at",
            field=models.DateTimeField(
                auto_now=True,
                verbose_name="Date de modification",
            ),
        ),
    ]
