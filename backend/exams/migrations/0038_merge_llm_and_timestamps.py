# Generated manually to resolve leaf migration conflict
# between 0022_merge_llm_summary_and_documents and 0037_remove_null_from_exam_timestamps

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('exams', '0022_merge_llm_summary_and_documents'),
        ('exams', '0037_remove_null_from_exam_timestamps'),
    ]

    operations = [
    ]
