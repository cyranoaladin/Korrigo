"""
Migration: Seed TeacherGroupAssignment rows for Première (EAM BLANCHE 20226).
"""
from django.db import migrations


PREMIERE_ASSIGNMENTS = {
    # username                        → (group_name, assignment_type)
    'migration-sanitized-001@example.test':              ('G4', 'groupe'),
    'migration-sanitized-002@example.test':     ('G6', 'groupe'),
    'migration-sanitized-003@example.test':            ('G1', 'groupe'),
    'migration-sanitized-004@example.test':            ('G7', 'groupe'),
    'migration-sanitized-005@example.test':           ('G8', 'groupe'),
    'migration-sanitized-006@example.test':          ('G5', 'groupe'),
    'migration-sanitized-007@example.test':       ('1.02', 'classe'),
}


def seed_premiere(apps, schema_editor):
    TGA = apps.get_model('exams', 'TeacherGroupAssignment')
    User = apps.get_model('auth', 'User')

    for username, (group_name, atype) in PREMIERE_ASSIGNMENTS.items():
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            continue

        TGA.objects.get_or_create(
            teacher=user,
            level='premiere',
            group_name=group_name,
            defaults={'assignment_type': atype},
        )


def reverse_premiere(apps, schema_editor):
    TGA = apps.get_model('exams', 'TeacherGroupAssignment')
    TGA.objects.filter(level='premiere').delete()


class Migration(migrations.Migration):

    dependencies = [
        ('exams', '0033_teacher_group_add_level'),
    ]

    operations = [
        migrations.RunPython(seed_premiere, reverse_premiere),
    ]
