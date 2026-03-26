from django.core.management.base import BaseCommand
from exams.models import Exam, ExamType


class Command(BaseCommand):
    help = "Asssocie les examens existants au type BAC_BLANC_MATHS_2026"

    def handle(self, *args, **options):
        try:
            exam_type = ExamType.objects.get(code="BAC_BLANC_MATHS_2026")
        except ExamType.DoesNotExist:
            self.stdout.write(
                self.style.WARNING("L'ExamType BAC_BLANC_MATHS_2026 n'existe pas encore. Exécutez create_exam_types d'abord.")
            )
            return

        exams_to_update = Exam.objects.filter(
            name__icontains="bb_j1"
        ) | Exam.objects.filter(
            name__icontains="bb_j2"
        ) | Exam.objects.filter(
            name__icontains="bac blanc"
        )

        for exam in exams_to_update:
            if exam.exam_type == exam_type:
                self.stdout.write(
                    self.style.WARNING(f"Déjà associé: {exam.name}")
                )
            else:
                old_type = exam.exam_type.name if exam.exam_type else "Aucun"
                exam.exam_type = exam_type
                exam.save()
                self.stdout.write(
                    self.style.SUCCESS(f"Associé: {exam.name} (ancien type: {old_type} → {exam_type.name})")
                )
