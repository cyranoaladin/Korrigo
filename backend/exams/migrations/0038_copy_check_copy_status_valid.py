from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("exams", "0037_remove_null_from_exam_timestamps"),
    ]

    operations = [
        migrations.AddConstraint(
            model_name="copy",
            constraint=models.CheckConstraint(
                check=models.Q(("status__in", ["READY", "IN_PROGRESS", "FINALIZED"])),
                name="check_copy_status_valid",
            ),
        ),
    ]
