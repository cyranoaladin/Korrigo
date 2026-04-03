"""
Purge RGPD des données d'examens anciens.
À exécuter manuellement en fin d'année scolaire.

Usage:
    python manage.py purge_old_exam_data --before 2025-09-01 --dry-run
    python manage.py purge_old_exam_data --before 2025-09-01 --confirm
"""
from django.core.management.base import BaseCommand
from django.utils.dateparse import parse_date


class Command(BaseCommand):
    help = "Purge les données d'examens antérieurs à une date (RGPD)"

    def add_arguments(self, parser):
        parser.add_argument("--before", required=True, help="Date limite YYYY-MM-DD")
        parser.add_argument("--dry-run", action="store_true", help="Prévisualiser sans supprimer")
        parser.add_argument("--confirm", action="store_true", help="Confirmer la suppression")

    def handle(self, *args, **options):
        from exams.models import Exam, Copy
        from grading.models import Annotation, Score, GradingEvent, DraftState, QuestionRemark

        cutoff = parse_date(options["before"])
        if not cutoff:
            self.stderr.write("Date invalide. Format: YYYY-MM-DD")
            return
        if not options["dry_run"] and not options["confirm"]:
            self.stderr.write("Utilisez --dry-run ou --confirm")
            return

        old_exams = Exam.objects.filter(date__lt=cutoff)
        old_copies = Copy.objects.filter(exam__in=old_exams)

        self.stdout.write(f"\nExamens avant {cutoff}: {old_exams.count()}")
        for exam in old_exams:
            self.stdout.write(f"  - {exam.name} ({exam.date})")

        counts = {
            "Copies": old_copies.count(),
            "Annotations": Annotation.objects.filter(copy__in=old_copies).count(),
            "Scores": Score.objects.filter(copy__in=old_copies).count(),
            "GradingEvents": GradingEvent.objects.filter(copy__in=old_copies).count(),
            "DraftStates": DraftState.objects.filter(copy__in=old_copies).count(),
            "QuestionRemarks": QuestionRemark.objects.filter(copy__in=old_copies).count(),
        }
        self.stdout.write("\nDonnées concernées:")
        for key, value in counts.items():
            self.stdout.write(f"  {key}: {value}")

        if options["dry_run"]:
            self.stdout.write(self.style.WARNING("\n[DRY RUN] Aucune donnée supprimée."))
            return

        self.stdout.write("\nSuppression en cours...")
        QuestionRemark.objects.filter(copy__in=old_copies).delete()
        DraftState.objects.filter(copy__in=old_copies).delete()
        GradingEvent.objects.filter(copy__in=old_copies).delete()
        Score.objects.filter(copy__in=old_copies).delete()
        Annotation.objects.filter(copy__in=old_copies).delete()
        old_copies.delete()
        self.stdout.write(self.style.SUCCESS("Purge terminée."))
