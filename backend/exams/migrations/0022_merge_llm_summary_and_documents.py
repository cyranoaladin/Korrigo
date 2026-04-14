# Generated manually to resolve leaf migration conflict
# between 0021_annotation_bank_and_documents and 0021_copy_llm_summary

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('exams', '0021_annotation_bank_and_documents'),
        ('exams', '0021_copy_llm_summary'),
    ]

    operations = [
    ]
