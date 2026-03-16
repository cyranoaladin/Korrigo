from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('grading', '0013_score_unique_copy_constraint'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='QuestionnaireResponse',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('payload', models.JSONField(default=dict, help_text='Réponses complètes du questionnaire', verbose_name='Réponses')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Date de création')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Date de mise à jour')),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='questionnaire_response', to=settings.AUTH_USER_MODEL, verbose_name='Répondant')),
            ],
            options={
                'verbose_name': 'Réponse questionnaire',
                'verbose_name_plural': 'Réponses questionnaire',
                'ordering': ['-updated_at'],
            },
        ),
        migrations.AddIndex(
            model_name='questionnaireresponse',
            index=models.Index(fields=['updated_at'], name='grading_que_updated_6d1d2b_idx'),
        ),
    ]
