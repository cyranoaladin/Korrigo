from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('students', '0002_student_user'),
    ]

    operations = [
        migrations.AddField(
            model_name='student',
            name='birth_date',
            field=models.DateField(blank=True, help_text='Format: YYYY-MM-DD', null=True, verbose_name='Date de naissance'),
        ),
    ]
