from django.db import migrations


class Migration(migrations.Migration):
    """
    Merge migration — résout le conflit de leaf nodes dans le graphe exams.

    Situation :
      - 0021_merge_20260513_0001 (merge des deux 0021 dupliqués)
      - 0040_add_pdf_regeneration_pending  (via 0022→…→0039→0040)

    Les deux sont des leaf nodes car la chaîne 0022-0040 descend d'un seul
    des 0021 originaux, pas du merge. Cette migration ferme le graphe.
    """

    dependencies = [
        ('exams', '0021_merge_20260513_0001'),
        ('exams', '0040_add_pdf_regeneration_pending'),
    ]

    operations = []
