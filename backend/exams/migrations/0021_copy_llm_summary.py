"""
Migration: Add llm_summary field to Copy model.
This migration was previously applied on the production server via overlay.
It must remain in the repo to match the server's django_migrations table.
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('exams', '0020_add_subject_variant_to_copy'),
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
