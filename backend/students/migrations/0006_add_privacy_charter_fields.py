from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('students', '0005_refactor_student_model'),
    ]

    operations = [
        migrations.AddField(
            model_name='student',
            name='privacy_charter_accepted',
            field=models.BooleanField(default=False, verbose_name='Charte de confidentialité acceptée'),
        ),
        migrations.AddField(
            model_name='student',
            name='privacy_charter_accepted_at',
            field=models.DateTimeField(blank=True, null=True, verbose_name="Date d'acceptation de la charte"),
        ),
    ]
