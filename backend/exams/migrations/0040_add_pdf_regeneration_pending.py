# Generated manually to add pdf_regeneration_pending field to Copy model
# Date: 2026-05-08
# Purpose: Track when PDF final needs regeneration after score correction

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('exams', '0039_alter_copy_status'),
    ]

    operations = [
        migrations.AddField(
            model_name='copy',
            name='pdf_regeneration_pending',
            field=models.BooleanField(
                default=False,
                verbose_name='Régénération PDF en attente',
                help_text="Indique que le PDF final doit être régénéré suite à une correction de note"
            ),
        ),
    ]
