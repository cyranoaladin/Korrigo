from django.core.management.base import BaseCommand
from exams.models import ExamType


class Command(BaseCommand):
    help = "Crée les types d'examens principaux pour l'année scolaire 2026"

    def handle(self, *args, **options):
        exam_types = [
            {
                "code": "BAC_BLANC_MATHS_2026",
                "name": "Bac Blanc Maths 2026",
                "color": "#3B82F6",
                "icon": "graduation-cap",
                "sort_order": 1,
            },
            {
                "code": "DNB_BLANC_MATHS_2026",
                "name": "DNB Blanc Maths 2026",
                "color": "#10B981",
                "icon": "book-open",
                "sort_order": 2,
            },
            {
                "code": "EAM_2026",
                "name": "EAM 2026",
                "color": "#F59E0B",
                "icon": "clipboard-list",
                "sort_order": 3,
            },
        ]

        for data in exam_types:
            exam_type, created = ExamType.objects.get_or_create(
                code=data["code"],
                defaults={
                    "name": data["name"],
                    "color": data["color"],
                    "icon": data["icon"],
                    "sort_order": data["sort_order"],
                },
            )

            if created:
                self.stdout.write(
                    self.style.SUCCESS(f"Créé: {exam_type.name} ({exam_type.code})")
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f"Existait déjà: {exam_type.name} ({exam_type.code})")
                )
