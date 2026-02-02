# Migration to remove INE and add eds_group
# Note: date_of_birth and email already handled in 0003

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('students', '0003_student_email_user_required'),
    ]

    operations = [
        # Add eds_group field
        migrations.AddField(
            model_name='student',
            name='eds_group',
            field=models.CharField(blank=True, default='', max_length=100, verbose_name='Groupe EDS'),
        ),
        # Remove INE field
        migrations.RemoveField(
            model_name='student',
            name='ine',
        ),
    ]
