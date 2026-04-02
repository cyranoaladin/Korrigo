from django.db import migrations


def normalize_group_name(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    Group.objects.filter(name='QUESTIONNAIRE_COORDINATOR').update(name='questionnaire_coordinator')


def reverse(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    Group.objects.filter(name='questionnaire_coordinator').update(name='QUESTIONNAIRE_COORDINATOR')


class Migration(migrations.Migration):
    dependencies = [
        ('core', '0004_questionnaire_coordinator_group'),
    ]
    operations = [
        migrations.RunPython(normalize_group_name, reverse),
    ]
