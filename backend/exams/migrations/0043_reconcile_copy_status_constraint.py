from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("exams", "0042_copy_pdf_regeneration_pending_db_default"),
    ]

    operations = [
        migrations.AlterField(
            model_name="copy",
            name="status",
            field=models.CharField(
                choices=[
                    ("READY", "Pret"),
                    ("IN_PROGRESS", "En cours"),
                    ("FINALIZED", "Finalisee"),
                ],
                default="READY",
                max_length=20,
                verbose_name="Statut",
            ),
        ),
        migrations.RemoveConstraint(
            model_name="copy",
            name="check_copy_status_valid",
        ),
        migrations.AddConstraint(
            model_name="copy",
            constraint=models.CheckConstraint(
                check=models.Q(("status__in", ["READY", "IN_PROGRESS", "FINALIZED"])),
                name="check_copy_status_valid",
            ),
        ),
    ]
