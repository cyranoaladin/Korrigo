from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("exams", "0038_copy_check_copy_status_valid"),
    ]

    operations = [
        migrations.AlterField(
            model_name="copy",
            name="status",
            field=models.CharField(
                choices=[
                    ("READY", "Pret"),
                    ("LOCKED", "Verrouillee"),
                    ("IN_PROGRESS", "En cours"),
                    ("GRADED", "Notee"),
                    ("FINALIZED", "Finalisee"),
                ],
                default="READY",
                max_length=20,
                verbose_name="Statut",
            ),
        ),
    ]
