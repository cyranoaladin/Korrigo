from django.db import migrations


def fix_group_name(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')

    old = Group.objects.filter(name='QUESTIONNAIRE_COORDINATOR').first()
    if not old:
        Group.objects.get_or_create(name='questionnaire_coordinator')
        return

    new, _ = Group.objects.get_or_create(name='questionnaire_coordinator')
    for user in old.user_set.all():
        user.groups.add(new)
    old.delete()


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ('core', '0005_normalize_questionnaire_group'),
    ]

    operations = [
        migrations.RunPython(fix_group_name, noop),
    ]
