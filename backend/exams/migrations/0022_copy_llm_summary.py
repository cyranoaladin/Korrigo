"""
Merge migration: unifies 0021_copy_llm_summary (applied on server via overlay)
and 0021_annotation_bank_and_documents (added in repo).

The llm_summary field already exists from 0021_copy_llm_summary, so no operations needed.
"""
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('exams', '0021_copy_llm_summary'),
        ('exams', '0021_annotation_bank_and_documents'),
    ]

    operations = [
        # No-op: llm_summary field already created by 0021_copy_llm_summary
    ]
