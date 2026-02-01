from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('exams', '0013_copy_grading_error_tracking'),
    ]

    operations = [
        migrations.AddIndex(
            model_name='copy',
            index=models.Index(fields=['status'], name='exams_copy_status_idx'),
        ),
        migrations.AddIndex(
            model_name='copy',
            index=models.Index(fields=['exam', 'status'], name='exams_copy_exam_status_idx'),
        ),
    ]
