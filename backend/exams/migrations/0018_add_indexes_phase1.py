# Phase 1 Critical Performance Fix - Add database indexes
# Generated manually on 2026-02-05

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('exams', '0017_perf_indexes_zf_aud_13'),
    ]

    operations = [
        migrations.AlterField(
            model_name='copy',
            name='status',
            field=models.CharField(
                choices=[
                    ('staging', 'En préparation'),
                    ('identified', 'Identifié'),
                    ('dispatched', 'Dispatché'),
                    ('locked', 'Verrouillé pour correction'),
                    ('corrected', 'Corrigé'),
                    ('finalized', 'Finalisé')
                ],
                db_index=True,
                default='staging',
                max_length=20,
                verbose_name='Statut'
            ),
        ),
        migrations.AlterField(
            model_name='copy',
            name='is_identified',
            field=models.BooleanField(
                db_index=True,
                default=False,
                help_text='Vrai si la copie a été associée à un élève.',
                verbose_name='Identifié ?'
            ),
        ),
    ]
