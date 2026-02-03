from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('exams', '0001_initial'),
        ('grading', '0010_perf_indexes_zf_aud_13'),
    ]

    operations = [
        migrations.CreateModel(
            name='QuestionScore',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('question_id', models.CharField(help_text="Identifiant de la question dans le barème", max_length=255, verbose_name="ID de la question")),
                ('score', models.DecimalField(decimal_places=2, help_text="Note attribuée à cette question", max_digits=5, verbose_name="Note")),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name="Date de création")),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name="Date de modification")),
                ('copy', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='question_scores', to='exams.copy', verbose_name="Copie")),
                ('created_by', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='question_scores_created', to=settings.AUTH_USER_MODEL, verbose_name="Créé par")),
            ],
            options={
                'verbose_name': 'Note de question',
                'verbose_name_plural': 'Notes de questions',
            },
        ),
        migrations.AddIndex(
            model_name='questionscore',
            index=models.Index(fields=['copy', 'question_id'], name='grading_que_copy_id_8a1b2c_idx'),
        ),
        migrations.AddConstraint(
            model_name='questionscore',
            constraint=models.UniqueConstraint(fields=('copy', 'question_id'), name='unique_copy_question_score'),
        ),
    ]
