"""
Migration: Reconcile annotation types to French.
- Data migration: COMMENT→COMMENTAIRE, HIGHLIGHT→SURLIGNAGE, ERROR→ERREUR
- Schema migration: update choices to French
"""
from django.db import migrations, models


def convert_english_to_french(apps, schema_editor):
    Annotation = apps.get_model('grading', 'Annotation')
    mapping = {
        'COMMENT': 'COMMENTAIRE',
        'HIGHLIGHT': 'SURLIGNAGE',
        'ERROR': 'ERREUR',
    }
    for eng, fra in mapping.items():
        n = Annotation.objects.filter(type=eng).update(type=fra)
        if n:
            print(f"  Migrated {n} annotations: {eng} → {fra}")


def convert_french_to_english(apps, schema_editor):
    Annotation = apps.get_model('grading', 'Annotation')
    mapping = {
        'COMMENTAIRE': 'COMMENT',
        'SURLIGNAGE': 'HIGHLIGHT',
        'ERREUR': 'ERROR',
    }
    for fra, eng in mapping.items():
        Annotation.objects.filter(type=fra).update(type=eng)


class Migration(migrations.Migration):

    dependencies = [
        ('grading', '0018_alter_gradingevent_action'),
    ]

    operations = [
        # Data migration first
        migrations.RunPython(
            convert_english_to_french,
            reverse_code=convert_french_to_english,
        ),
        # Then update choices
        migrations.AlterField(
            model_name='annotation',
            name='type',
            field=models.CharField(
                choices=[
                    ('COMMENTAIRE', 'Commentaire'),
                    ('SURLIGNAGE', 'Surligné'),
                    ('ERREUR', 'Erreur'),
                    ('BONUS', 'Bonus'),
                    ('VRAI', 'Vrai'),
                    ('FAUX', 'Faux'),
                ],
                default='COMMENTAIRE',
                max_length=20,
                verbose_name='Type d\u2019annotation',
            ),
        ),
    ]
