from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('students', '0003_student_birth_date'),
    ]

    operations = [
        migrations.AlterField(
            model_name='student',
            name='birth_date',
            field=models.DateField(help_text='Format: YYYY-MM-DD', verbose_name='Date de naissance'),
        ),
    ]
