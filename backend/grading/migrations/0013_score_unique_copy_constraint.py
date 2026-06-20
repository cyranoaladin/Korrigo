"""
LOT 8: Add UniqueConstraint on Score.copy to enforce one score per copy at DB level.

IMPORTANT — Pre-deployment check required:
    Before running this migration on production, verify no duplicate scores exist:

    SELECT copy_id, COUNT(*) FROM grading_score GROUP BY copy_id HAVING COUNT(*) > 1;

    If any rows are returned, duplicates MUST be resolved manually before migrating.
    Failure to do so will cause django.db.utils.IntegrityError and block all future migrations.

Reversibility: Fully reversible via RunSQL reverse or RemoveConstraint.
Destructive: NO — adds a constraint, does not delete or modify data.
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('grading', '0013_alter_annotation_type'),
    ]

    operations = [
        migrations.AddConstraint(
            model_name='score',
            constraint=models.UniqueConstraint(
                fields=['copy'],
                name='uniq_score_per_copy',
            ),
        ),
    ]
