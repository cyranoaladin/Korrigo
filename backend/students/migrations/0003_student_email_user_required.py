# Generated manually for clean state on empty database

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('students', '0002_student_user'),
    ]

    operations = [
        # Add date_of_birth field
        migrations.AddField(
            model_name='student',
            name='date_of_birth',
            field=models.DateField(blank=True, null=True, verbose_name='Date de naissance'),
        ),

        # Make email non-nullable and unique
        migrations.AlterField(
            model_name='student',
            name='email',
            field=models.EmailField(unique=True, verbose_name='Email'),
        ),

        # Make user required (non-nullable) and change on_delete to CASCADE
        migrations.AlterField(
            model_name='student',
            name='user',
            field=models.OneToOneField(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='student_profile',
                to=settings.AUTH_USER_MODEL,
                verbose_name='Utilisateur associé'
            ),
        ),
    ]
