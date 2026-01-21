# Generated manually for Étape 3

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('exams', '0004_alter_booklet_header_image_alter_copy_final_pdf'),
        ('grading', '0001_initial'),
    ]

    operations = [
        # 1. Supprimer les anciens modèles (Score et Annotation)
        migrations.DeleteModel(
            name='Score',
        ),
        migrations.DeleteModel(
            name='Annotation',
        ),

        # 2. Créer le nouveau modèle Annotation (ADR-002 compliant)
        migrations.CreateModel(
            name='Annotation',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('page_index', models.PositiveIntegerField(help_text="Index de la page (0 = première page)", verbose_name='Index de page (0-based)')),
                ('x', models.FloatField(help_text="Position X dans l'intervalle [0,1]", verbose_name='Position X normalisée')),
                ('y', models.FloatField(help_text="Position Y dans l'intervalle [0,1]", verbose_name='Position Y normalisée')),
                ('w', models.FloatField(help_text="Largeur dans l'intervalle [0,1]", verbose_name='Largeur normalisée')),
                ('h', models.FloatField(help_text="Hauteur dans l'intervalle [0,1]", verbose_name='Hauteur normalisée')),
                ('content', models.TextField(blank=True, help_text="Texte ou données JSON de l'annotation", verbose_name='Contenu')),
                ('type', models.CharField(choices=[('COMMENT', 'Commentaire'), ('HIGHLIGHT', 'Surligné'), ('ERROR', 'Erreur'), ('BONUS', 'Bonus')], default='COMMENT', max_length=20, verbose_name="Type d'annotation")),
                ('score_delta', models.IntegerField(blank=True, help_text='Points ajoutés/retirés (peut être négatif)', null=True, verbose_name='Variation de score')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Date de création')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Date de modification')),
                ('copy', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='annotations', to='exams.copy', verbose_name='Copie')),
                ('created_by', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='annotations_created', to=settings.AUTH_USER_MODEL, verbose_name='Créé par')),
            ],
            options={
                'verbose_name': 'Annotation',
                'verbose_name_plural': 'Annotations',
                'ordering': ['page_index', 'created_at'],
            },
        ),

        # 3. Créer le modèle GradingEvent (ADR-003)
        migrations.CreateModel(
            name='GradingEvent',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('action', models.CharField(choices=[('VALIDATE', 'Validation (STAGING→READY)'), ('LOCK', 'Verrouillage (READY→LOCKED)'), ('UNLOCK', 'Déverrouillage (LOCKED→READY)'), ('GRADE', 'Notation en cours'), ('FINALIZE', 'Finalisation (LOCKED→GRADED)')], max_length=20, verbose_name='Action')),
                ('timestamp', models.DateTimeField(auto_now_add=True, verbose_name='Horodatage')),
                ('metadata', models.JSONField(blank=True, default=dict, help_text='Données contextuelles (score, raison, etc.)', verbose_name='Métadonnées')),
                ('actor', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='grading_actions', to=settings.AUTH_USER_MODEL, verbose_name='Acteur')),
                ('copy', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='grading_events', to='exams.copy', verbose_name='Copie')),
            ],
            options={
                'verbose_name': 'Événement de correction',
                'verbose_name_plural': 'Événements de correction',
                'ordering': ['-timestamp'],
            },
        ),

        # 4. Ajouter les indexes
        migrations.AddIndex(
            model_name='annotation',
            index=models.Index(fields=['copy', 'page_index'], name='grading_ann_copy_id_f6ec3e_idx'),
        ),
        migrations.AddIndex(
            model_name='gradingevent',
            index=models.Index(fields=['copy', '-timestamp'], name='grading_gra_copy_id_c7a0e0_idx'),
        ),
    ]
