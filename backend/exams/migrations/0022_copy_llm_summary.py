"""
Migration: Add llm_summary field to Copy model.
Nullable TextField — zero risk for existing data.
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('exams', '0021_annotation_bank_and_documents'),
    ]

    operations = [
        migrations.AddField(
            model_name='copy',
            name='llm_summary',
            field=models.TextField(
                blank=True,
                null=True,
                verbose_name='Bilan LLM',
                help_text='Bilan personnalisé généré par LLM après finalisation',
            ),
        ),
    ]
