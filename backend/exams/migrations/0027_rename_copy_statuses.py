from django.db import migrations


def migrate_copy_statuses(apps, schema_editor):
    Copy = apps.get_model('exams', 'Copy')
    db_alias = schema_editor.connection.alias
    Copy.objects.using(db_alias).filter(status='GRADING_IN_PROGRESS').update(status='IN_PROGRESS')
    Copy.objects.using(db_alias).filter(status='GRADED').update(status='FINALIZED')


def reverse_migrate_copy_statuses(apps, schema_editor):
    Copy = apps.get_model('exams', 'Copy')
    db_alias = schema_editor.connection.alias
    Copy.objects.using(db_alias).filter(status='IN_PROGRESS').update(status='GRADING_IN_PROGRESS')
    Copy.objects.using(db_alias).filter(status='FINALIZED').update(status='GRADED')


class Migration(migrations.Migration):

    dependencies = [
        ('exams', '0026_simplify_copy_status'),
    ]

    operations = [
        migrations.RunPython(migrate_copy_statuses, reverse_migrate_copy_statuses),
        migrations.AlterField(
            model_name='copy',
            name='status',
            field=__import__('django.db.models', fromlist=['CharField']).CharField(
                choices=[
                    ('READY', 'Prêt'),
                    ('IN_PROGRESS', 'En cours'),
                    ('FINALIZED', 'Finalisée'),
                ],
                default='READY',
                max_length=20,
                verbose_name='Statut',
            ),
        ),
    ]
