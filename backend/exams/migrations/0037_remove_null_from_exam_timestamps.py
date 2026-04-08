import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("exams", "0036_add_default_exam_date"),
    ]

    operations = [
        # Backfill any NULLs before altering (safety net)
        migrations.RunSQL(
            sql="UPDATE exams_exam SET created_at = NOW() WHERE created_at IS NULL;",
            reverse_sql=migrations.RunSQL.noop,
        ),
        migrations.RunSQL(
            sql="UPDATE exams_exam SET updated_at = NOW() WHERE updated_at IS NULL;",
            reverse_sql=migrations.RunSQL.noop,
        ),
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
