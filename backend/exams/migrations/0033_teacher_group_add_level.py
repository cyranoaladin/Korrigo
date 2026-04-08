"""
Migration: Add level and assignment_type to TeacherGroupAssignment.
Migrates existing data to the correct level based on group_name patterns.
"""
import django.db.models
from django.db import migrations, models


def migrate_existing_assignments(apps, schema_editor):
    """Assign level and assignment_type to existing TeacherGroupAssignment rows."""
    TGA = apps.get_model('exams', 'TeacherGroupAssignment')

    for tga in TGA.objects.all():
        gn = tga.group_name

        # 3.x → troisième / classe
        if gn.startswith('3.'):
            tga.level = 'troisieme'
            tga.assignment_type = 'classe'

        # T.xx → terminale / groupe  (Student.groupe stores 'T.04' etc.)
        elif gn.startswith('T.'):
            tga.level = 'terminale'
            tga.assignment_type = 'groupe'

        # G1-G6 currently belong to Terminale (existing BB data)
        elif gn.startswith('G'):
            tga.level = 'terminale'
            tga.assignment_type = 'groupe'

        else:
            # Fallback
            tga.level = 'terminale'
            tga.assignment_type = 'groupe'

        tga.save(update_fields=['level', 'assignment_type'])


def reverse_noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('exams', '0032_copy_student_status_index'),
    ]

    operations = [
        # 1. Add columns with defaults
        migrations.AddField(
            model_name='teachergroupassignment',
            name='level',
            field=models.CharField(
                choices=[('terminale', 'Terminale'), ('premiere', 'Première'), ('troisieme', 'Troisième')],
                default='terminale',
                help_text='terminale, premiere, troisieme',
                max_length=20,
                verbose_name='Niveau',
            ),
        ),
        migrations.AddField(
            model_name='teachergroupassignment',
            name='assignment_type',
            field=models.CharField(
                choices=[('groupe', 'Groupe'), ('classe', 'Classe')],
                default='groupe',
                help_text="'groupe' → filtre Student.groupe ; 'classe' → filtre Student.class_name",
                max_length=10,
                verbose_name="Type d'assignation",
            ),
        ),
        # 2. Migrate existing data
        migrations.RunPython(migrate_existing_assignments, reverse_noop),
        # 3. Change unique_together from (teacher, group_name) to (teacher, level, group_name)
        migrations.AlterUniqueTogether(
            name='teachergroupassignment',
            unique_together={('teacher', 'level', 'group_name')},
        ),
    ]
