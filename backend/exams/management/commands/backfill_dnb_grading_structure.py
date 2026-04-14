from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from exams.dnb_2026_structure import build_dnb_2026_grading_structure
from exams.models import Exam


class Command(BaseCommand):
    help = (
        "Backfill the canonical DNB_2026 grading_structure when it is missing. "
        "Only updates the exam JSON barème, never copies, scores, remarks, or statuses."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--exam-name",
            default="DNB_2026",
            help="Exam name to backfill (default: DNB_2026).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be changed without writing to the database.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        exam_name = options["exam_name"]
        dry_run = options["dry_run"]

        exam = Exam.objects.filter(name=exam_name).first()
        if exam is None:
            raise CommandError(f"Exam '{exam_name}' not found.")

        if exam.grading_structure:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Exam '{exam_name}' already has a grading_structure; no change applied."
                )
            )
            return

        structure = build_dnb_2026_grading_structure()
        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f"[DRY-RUN] Would backfill grading_structure for '{exam_name}' with {len(structure)} top-level nodes."
                )
            )
            return

        exam.grading_structure = structure
        exam.save(update_fields=["grading_structure"])
        self.stdout.write(
            self.style.SUCCESS(
                f"Backfilled grading_structure for '{exam_name}' with {len(structure)} top-level nodes."
            )
        )
