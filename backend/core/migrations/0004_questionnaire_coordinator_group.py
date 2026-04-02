"""
Data migration: create the questionnaire_coordinator group and assign
the user previously identified by a hardcoded email.
"""
from django.db import migrations


def create_group_and_assign(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    User = apps.get_model('auth', 'User')

    group, _ = Group.objects.get_or_create(name='questionnaire_coordinator')

    # Migrate the previously hardcoded user into the new group.
    try:
        user = User.objects.get(email='laroussi.laroussi@ert.tn')
        user.groups.add(group)
    except User.DoesNotExist:
        pass  # User may not exist in this environment (dev, CI, etc.)


def remove_group(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    Group.objects.filter(name__iexact='questionnaire_coordinator').delete()


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0003_userprofile'),
    ]

    operations = [
        migrations.RunPython(create_group_and_assign, remove_group),
    ]
