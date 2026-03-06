"""
LOT 8: Add performance indexes on Copy for frequent query patterns.

Indexes added:
    - idx_copy_status: Copy.status (filter by status)
    - idx_copy_exam_status: Copy(exam, status) (copies per exam filtered by status)
    - idx_copy_corrector_status: Copy(assigned_corrector, status) (corrector workload)

Reversibility: Fully reversible via RemoveIndex.
Destructive: NO — adds indexes only, does not modify data.
Risk: LOW — additive operation, may take a few seconds on large tables.
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('exams', '0022_copy_llm_summary'),
    ]

    operations = [
        migrations.AddIndex(
            model_name='copy',
            index=models.Index(
                fields=['status'],
                name='idx_copy_status',
            ),
        ),
        migrations.AddIndex(
            model_name='copy',
            index=models.Index(
                fields=['exam', 'status'],
                name='idx_copy_exam_status',
            ),
        ),
        migrations.AddIndex(
            model_name='copy',
            index=models.Index(
                fields=['assigned_corrector', 'status'],
                name='idx_copy_corrector_status',
            ),
        ),
    ]
