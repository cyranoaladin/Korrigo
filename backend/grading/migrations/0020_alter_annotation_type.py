from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('grading', '0019_reconcile_annotation_types_french'),
    ]

    operations = [
        migrations.AlterField(
            model_name='annotation',
            name='type',
            field=models.CharField(
                choices=[
                    ('COMMENTAIRE', 'Commentaire'),
                    ('SURLIGNAGE', 'Surligne'),
                    ('ERREUR', 'Erreur'),
                    ('BONUS', 'Bonus'),
                    ('VRAI', 'Vrai'),
                    ('FAUX', 'Faux'),
                ],
                default='COMMENTAIRE',
                max_length=20,
                verbose_name="Type d'annotation",
            ),
        ),
    ]
