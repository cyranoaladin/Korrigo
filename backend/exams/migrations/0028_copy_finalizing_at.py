from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('exams', '0027_rename_copy_statuses'),
    ]

    operations = [
        migrations.AddField(
            model_name='copy',
            name='finalizing_at',
            field=models.DateTimeField(
                blank=True,
                null=True,
                verbose_name='Finalisation en cours depuis',
                help_text='Marqueur atomique anti-doublon : sert de mutex pour éviter deux finalisations simultanées',
            ),
        ),
    ]
