"""
Data migration: convert annotation type values from English to French.
COMMENT → COMMENTAIRE, HIGHLIGHT → SURLIGNAGE, ERROR → ERREUR
(BONUS stays the same)
"""
from django.db import migrations, models


def convert_types_to_french(apps, schema_editor):
    Annotation = apps.get_model('grading', 'Annotation')
    mapping = {
        'COMMENT': 'COMMENTAIRE',
        'HIGHLIGHT': 'SURLIGNAGE',
        'ERROR': 'ERREUR',
    }
    for old_val, new_val in mapping.items():
        Annotation.objects.filter(type=old_val).update(type=new_val)


def convert_types_to_english(apps, schema_editor):
    Annotation = apps.get_model('grading', 'Annotation')
    mapping = {
        'COMMENTAIRE': 'COMMENT',
        'SURLIGNAGE': 'HIGHLIGHT',
        'ERREUR': 'ERROR',
    }
    for old_val, new_val in mapping.items():
        Annotation.objects.filter(type=old_val).update(type=new_val)


class Migration(migrations.Migration):

    dependencies = [
        ('grading', '0010_score'),
    ]

    operations = [
        # 1. Data migration: convert existing rows
        migrations.RunPython(convert_types_to_french, convert_types_to_english),
        # 2. Schema migration: update choices and default
        migrations.AlterField(
            model_name='annotation',
            name='type',
            field=models.CharField(
                choices=[
                    ('COMMENTAIRE', 'Commentaire'),
                    ('SURLIGNAGE', 'Surlignage'),
                    ('ERREUR', 'Erreur'),
                    ('BONUS', 'Bonus'),
                ],
                default='COMMENTAIRE',
                max_length=20,
                verbose_name="Type d'annotation",
            ),
        ),
    ]
