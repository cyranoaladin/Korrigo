from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.management import call_command
from django.test import TestCase

from core.models import AuditLog
from exams.models import Booklet, Copy, Exam


class CopyIntegrityCommandTests(TestCase):
    def setUp(self):
        self.actor = get_user_model().objects.create_user(
            username="integrity-admin",
            password="pw-test-12345",
        )
        self.exam = Exam.objects.create(name="Integrity Exam")
        self.copy = Copy.objects.create(
            exam=self.exam,
            anonymous_id="INTEGRITY-001",
            status=Copy.Status.FINALIZED,
        )
        booklet = Booklet.objects.create(
            exam=self.exam,
            start_page=1,
            end_page=1,
            pages_images=["copies/pages/test/page_1.png"],
        )
        self.copy.booklets.add(booklet)

    @patch("os.path.exists", return_value=True)
    @patch("processing.services.pdf_flattener.PDFFlattener.flatten_copy", return_value=b"%PDF-1.4\n%%EOF")
    def test_repairs_finalized_copy_missing_pdf(self, _mock_flatten, _mock_exists):
        call_command(
            "check_copy_integrity",
            "--copy-id",
            str(self.copy.id),
            "--repair-missing-final-pdf",
            "--actor-username",
            self.actor.username,
        )

        self.copy.refresh_from_db()
        self.assertTrue(self.copy.final_pdf)
        self.assertTrue(
            AuditLog.objects.filter(
                action="integrity.repair.final_pdf",
                resource_id=str(self.copy.id),
            ).exists()
        )

    @patch("os.path.exists", return_value=False)
    def test_reports_missing_page_images_as_issue(self, _mock_exists):
        with self.assertRaises(SystemExit):
            call_command(
                "check_copy_integrity",
                "--copy-id",
                str(self.copy.id),
                "--repair-missing-final-pdf",
                "--fail-on-issues",
            )

        self.copy.refresh_from_db()
        self.assertFalse(self.copy.final_pdf)
