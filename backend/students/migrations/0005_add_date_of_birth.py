# Generated manually to add date_of_birth field

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('students', '0004_add_date_of_birth_eds_group'),
    ]

    operations = [
        migrations.AddField(
            model_name='student',
            name='date_of_birth',
            field=models.DateField(blank=True, null=True, verbose_name='Date de naissance'),
        ),
    ]
