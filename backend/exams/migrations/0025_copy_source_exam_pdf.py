# Generated migration for adding source_exam_pdf to Copy model

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('exams', '0024_exam_csv_parsed_at_exam_csv_student_count_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='copy',
            name='source_exam_pdf',
            field=models.ForeignKey(
                blank=True,
                help_text='Référence vers ExamPDF pour éviter le stockage dupliqué en mode INDIVIDUAL_A4',
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='copies',
                to='exams.exampdf',
                verbose_name='PDF Source (Mode INDIVIDUAL_A4)'
            ),
        ),
    ]
