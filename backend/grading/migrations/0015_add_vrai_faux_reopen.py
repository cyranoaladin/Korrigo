from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('grading', '0014_questionnaire_response'),
    ]

    operations = [
        migrations.AlterField(
            model_name='annotation',
            name='type',
            field=models.CharField(
                choices=[
                    ('COMMENT', 'Commentaire'),
                    ('HIGHLIGHT', 'Surligné'),
                    ('ERROR', 'Erreur'),
                    ('BONUS', 'Bonus'),
                    ('VRAI', 'Vrai'),
                    ('FAUX', 'Faux'),
                ],
                default='COMMENT',
                max_length=20,
                verbose_name='Type',
            ),
        ),
        migrations.AlterField(
            model_name='gradingevent',
            name='action',
            field=models.CharField(
                choices=[
                    ('IMPORT', 'Import'),
                    ('VALIDATE', 'Validation'),
                    ('LOCK', 'Verrouillage'),
                    ('UNLOCK', 'Déverrouillage'),
                    ('CREATE_ANN', 'Création annotation'),
                    ('UPDATE_ANN', 'Modification annotation'),
                    ('DELETE_ANN', 'Suppression annotation'),
                    ('FINALIZE', 'Finalisation'),
                    ('EXPORT', 'Export'),
                    ('REOPEN', 'Réouverture'),
                ],
                max_length=20,
                verbose_name='Action',
            ),
        ),
    ]
