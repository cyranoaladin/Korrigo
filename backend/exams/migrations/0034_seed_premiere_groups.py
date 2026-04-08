"""
Migration: Seed TeacherGroupAssignment rows for Première (EAM BLANCHE 20226).
"""
from django.db import migrations


PREMIERE_ASSIGNMENTS = {
    # username                        → (group_name, assignment_type)
    'fatma.abid@ert.tn':              ('G4', 'groupe'),
    'alaeddine.benrhouma@ert.tn':     ('G6', 'groupe'),
    'sami.bentiba@ert.tn':            ('G1', 'groupe'),
    'gilles.colly@ert.tn':            ('G7', 'groupe'),
    'fatma.gouider@ert.tn':           ('G8', 'groupe'),
    'mohamed.lamine@ert.tn':          ('G5', 'groupe'),
    'amandine.mouttapa@ert.tn':       ('1.02', 'classe'),
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
