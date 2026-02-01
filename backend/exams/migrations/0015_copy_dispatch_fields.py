from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('exams', '0014_copy_performance_indexes'),
    ]

    operations = [
        migrations.AddField(
            model_name='copy',
            name='assigned_corrector',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='assigned_copies',
                to=settings.AUTH_USER_MODEL,
                verbose_name='Correcteur assigné'
            ),
        ),
        migrations.AddField(
            model_name='copy',
            name='dispatch_run_id',
            field=models.UUIDField(
                blank=True,
                help_text="UUID généré lors du dispatch pour traçabilité",
                null=True,
                verbose_name="ID d'exécution du dispatch"
            ),
        ),
        migrations.AddField(
            model_name='copy',
            name='assigned_at',
            field=models.DateTimeField(
                blank=True,
                help_text="Timestamp de l'assignation au correcteur",
                null=True,
                verbose_name="Date d'assignation"
            ),
        ),
        migrations.AddIndex(
            model_name='copy',
            index=models.Index(fields=['assigned_corrector'], name='exams_copy_assigned_corrector_idx'),
        ),
        migrations.AddIndex(
            model_name='copy',
            index=models.Index(fields=['dispatch_run_id'], name='exams_copy_dispatch_run_idx'),
        ),
    ]
