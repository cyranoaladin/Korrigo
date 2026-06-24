from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from exams.models import Copy, Exam
from students.models import Student


class CopyIntegrityAuditLoggingTests(TestCase):
    def test_finalized_copy_missing_pdf_output_is_redacted(self):
        student = Student.objects.create(
            first_name="Synthetic",
            last_name="Learner",
            date_naissance="2010-01-02",
            email="synthetic.learner@example.test",
            class_name="E2E",
        )
        exam = Exam.objects.create(name="Synthetic Integrity Exam")
        copy = Copy.objects.create(
            exam=exam,
            student=student,
            anonymous_id="SYNTH-001",
            status=Copy.Status.FINALIZED,
        )

        out = StringIO()
        call_command("check_copy_integrity", "--copy-id", str(copy.pk), stdout=out)

        output = out.getvalue()
        assert "scanned=1" in output
        assert "issues=1" in output
        assert "repaired=0" in output
        assert "FINALIZED_WITHOUT_FINAL_PDF" in output
        assert "copy_pk=" in output
        assert "exam_pk=" in output
        assert "status=FINALIZED" in output
        assert "has_final_pdf=False" in output

        assert "student_email" not in output
        assert "synthetic.learner" not in output
        assert "@example.test" not in output
        assert "Synthetic" not in output
        assert "Learner" not in output
        assert "anonymous_id" not in output
        assert "SYNTH-001" not in output
