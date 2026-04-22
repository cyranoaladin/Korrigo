import os
from pathlib import Path

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.db import transaction

from core.models import AuditLog
from exams.models import Copy
from processing.services.pdf_flattener import PDFFlattener


class Command(BaseCommand):
    help = "Check grading copy integrity and optionally repair FINALIZED copies missing final_pdf."

    def add_arguments(self, parser):
        parser.add_argument(
            "--copy-id",
            help="Restrict the check to a single copy UUID.",
        )
        parser.add_argument(
            "--repair-missing-final-pdf",
            action="store_true",
            help="Regenerate final_pdf for FINALIZED copies when the source pages still exist.",
        )
        parser.add_argument(
            "--fail-on-issues",
            action="store_true",
            help="Return exit code 1 if any integrity issue is detected.",
        )
        parser.add_argument(
            "--actor-username",
            help="Optional username recorded in AuditLog for repairs.",
        )

    def handle(self, *args, **options):
        copy_id = options.get("copy_id")
        repair = options.get("repair_missing_final_pdf", False)
        fail_on_issues = options.get("fail_on_issues", False)
        actor_username = options.get("actor_username")

        actor = None
        if actor_username:
            from django.contrib.auth import get_user_model

            actor = get_user_model().objects.filter(username=actor_username).first()

        qs = Copy.objects.select_related("exam", "student").prefetch_related("booklets")
        if copy_id:
            qs = qs.filter(id=copy_id)

        issues = []
        repaired = 0
        scanned = 0
        flattener = PDFFlattener()

        # Explicit chunk_size keeps prefetch_related() compatible with Django 4.2+
        # and avoids RemovedInDjango50 warnings turning into test failures.
        for copy in qs.iterator(chunk_size=100):
            scanned += 1

            if copy.status == Copy.Status.FINALIZED and not copy.final_pdf:
                issue = {
                    "copy_id": str(copy.id),
                    "exam": copy.exam.name if copy.exam else None,
                    "anonymous_id": copy.anonymous_id,
                    "student_id": copy.student_id,
                    "student_email": copy.student.email if copy.student else None,
                    "problem": "FINALIZED without final_pdf",
                }

                if repair:
                    result = self._repair_missing_final_pdf(copy, flattener, actor)
                    issue["repair"] = result
                    if result["status"] == "repaired":
                        repaired += 1
                    else:
                        issues.append(issue)
                else:
                    issues.append(issue)

            if (
                copy.status == Copy.Status.FINALIZED
                and copy.exam
                and copy.exam.results_released_at
                and copy.student_id is None
            ):
                issues.append(
                    {
                        "copy_id": str(copy.id),
                        "exam": copy.exam.name if copy.exam else None,
                        "anonymous_id": copy.anonymous_id,
                        "problem": "released FINALIZED copy without student",
                    }
                )

        self.stdout.write(
            self.style.SUCCESS(
                f"Integrity scan completed: scanned={scanned} issues={len(issues)} repaired={repaired}"
            )
        )
        for issue in issues:
            self.stdout.write(self.style.WARNING(str(issue)))

        if fail_on_issues and issues:
            raise SystemExit(1)

    def _repair_missing_final_pdf(self, copy: Copy, flattener: PDFFlattener, actor):
        missing_pages = []
        for booklet in copy.booklets.all():
            for relative_path in booklet.pages_images or []:
                full_path = os.path.join(settings.MEDIA_ROOT, relative_path)
                if not os.path.exists(full_path):
                    missing_pages.append(relative_path)

        if missing_pages:
            return {
                "status": "blocked",
                "reason": "missing_page_images",
                "missing_pages": missing_pages,
            }

        try:
            pdf_bytes = flattener.flatten_copy(copy)
            if not pdf_bytes:
                return {"status": "blocked", "reason": "empty_pdf_bytes"}

            with transaction.atomic():
                locked_copy = Copy.objects.select_for_update().get(id=copy.id)
                if locked_copy.final_pdf:
                    return {
                        "status": "skipped",
                        "reason": "already_repaired_concurrently",
                        "final_pdf": locked_copy.final_pdf.name,
                    }

                output_filename = f"copy_{locked_copy.id}_corrected.pdf"
                target_dir = Path(settings.MEDIA_ROOT) / "copies" / "final"
                target_dir.mkdir(parents=True, exist_ok=True)
                locked_copy.final_pdf.save(output_filename, ContentFile(pdf_bytes), save=False)
                locked_copy.save(update_fields=["final_pdf"])

            AuditLog.objects.create(
                user=actor,
                action="integrity.repair.final_pdf",
                resource_type="Copy",
                resource_id=str(copy.id),
                ip_address="127.0.0.1",
                user_agent="management-command/check_copy_integrity",
                metadata={
                    "repair": "missing_final_pdf",
                    "bytes": len(pdf_bytes),
                    "exam": copy.exam.name if copy.exam else None,
                    "anonymous_id": copy.anonymous_id,
                },
            )
            return {
                "status": "repaired",
                "final_pdf": f"copies/final/copy_{copy.id}_corrected.pdf",
                "bytes": len(pdf_bytes),
            }
        except Exception as exc:
            return {"status": "blocked", "reason": "repair_failed", "error": str(exc)}
