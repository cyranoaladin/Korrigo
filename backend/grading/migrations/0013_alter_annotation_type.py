from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('grading', '0012_annotation_bank_and_documents'),
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
                ],
                default='COMMENTAIRE',
                max_length=20,
                verbose_name="Type d'annotation",
            ),
        ),
    ]
