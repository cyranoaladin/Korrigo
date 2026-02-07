"""
Tests d'intégration pour GenerateStudentPDFsView.

Teste l'endpoint POST /api/exams/<id>/generate-student-pdfs/
avec le StudentPDFGenerator mocké.
"""
import os
from unittest.mock import patch, MagicMock

import fitz
from django.test import TestCase, override_settings
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient
from rest_framework import status
from django.contrib.auth.models import User

from exams.models import Exam, Copy, ExamSourcePDF


def make_pdf(pages=4, page_width=595, page_height=842):
    """Crée un PDF de test en mémoire."""
    doc = fitz.open()
    for i in range(pages):
        page = doc.new_page(width=page_width, height=page_height)
        page.insert_text((72, 72), f"Page {i + 1}", fontsize=24)
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


def make_a3_pdf(pages=2):
    """Crée un PDF A3 landscape."""
    return make_pdf(pages=pages, page_width=1190, page_height=842)


def make_csv_bytes():
    """CSV de test."""
    content = "Élèves,Né(e) le,Adresse E-mail\nDUPONT Jean,01/01/2005,jean@test.fr\nMARTIN Alice,02/02/2005,alice@test.fr\n"
    return content.encode('utf-8-sig')


@override_settings(RATELIMIT_ENABLE=False)
class TestGenerateStudentPDFsURL(TestCase):
    """URL resolution tests."""

    def setUp(self):
        self.exam = Exam.objects.create(name='Test', date='2026-01-01')

    def test_url_resolves(self):
        url = reverse('generate-student-pdfs', kwargs={'exam_id': self.exam.id})
        expected = f'/api/exams/{self.exam.id}/generate-student-pdfs/'
        self.assertEqual(url, expected)


@override_settings(RATELIMIT_ENABLE=False)
class TestGenerateStudentPDFsAuth(TestCase):
    """Auth/permission tests."""

    def setUp(self):
        self.client = APIClient()
        self.exam = Exam.objects.create(name='Test', date='2026-01-01')
        self.url = reverse('generate-student-pdfs', kwargs={'exam_id': self.exam.id})

    def test_unauthenticated_rejected(self):
        response = self.client.post(self.url)
        self.assertIn(response.status_code, [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        ])

    def test_non_admin_rejected(self):
        user = User.objects.create_user('teacher', 'teacher@test.fr', 'pass')
        self.client.force_login(user)
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


@override_settings(RATELIMIT_ENABLE=False)
class TestGenerateStudentPDFsValidation(TestCase):
    """Validation and error cases."""

    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_superuser(
            'admin', 'admin@test.fr', 'admin'
        )
        self.client.force_login(self.admin)

    def test_no_source_pdfs_returns_400(self):
        exam = Exam.objects.create(name='Empty', date='2026-01-01')
        url = reverse('generate-student-pdfs', kwargs={'exam_id': exam.id})
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)

    def test_no_csv_returns_400(self):
        exam = Exam.objects.create(name='No CSV', date='2026-01-01')
        # Add a source PDF
        ExamSourcePDF.objects.create(
            exam=exam,
            pdf_file=SimpleUploadedFile("scan.pdf", make_a3_pdf(), content_type="application/pdf"),
            original_filename='scan.pdf',
            pdf_type=ExamSourcePDF.PDFType.COPY,
        )
        url = reverse('generate-student-pdfs', kwargs={'exam_id': exam.id})
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('CSV', str(response.data['error']))

    @patch.dict(os.environ, {"OPENAI_API_KEY": ""}, clear=False)
    @override_settings(OPENAI_API_KEY=None)
    def test_no_api_key_returns_500(self):
        exam = Exam.objects.create(name='No API Key', date='2026-01-01')
        ExamSourcePDF.objects.create(
            exam=exam,
            pdf_file=SimpleUploadedFile("scan.pdf", make_a3_pdf(), content_type="application/pdf"),
            original_filename='scan.pdf',
            pdf_type=ExamSourcePDF.PDFType.COPY,
        )
        exam.student_csv.save('eleves.csv', SimpleUploadedFile("eleves.csv", make_csv_bytes()))

        url = reverse('generate-student-pdfs', kwargs={'exam_id': exam.id})

        # Remove OPENAI_API_KEY from environ for this test
        env_backup = os.environ.pop('OPENAI_API_KEY', None)
        try:
            response = self.client.post(url)
            self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        finally:
            if env_backup is not None:
                os.environ['OPENAI_API_KEY'] = env_backup

    def test_nonexistent_exam_returns_404(self):
        import uuid
        url = reverse('generate-student-pdfs', kwargs={'exam_id': uuid.uuid4()})
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


@override_settings(RATELIMIT_ENABLE=False)
class TestGenerateStudentPDFsSuccess(TestCase):
    """Successful generation with mocked generator."""

    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_superuser(
            'admin', 'admin@test.fr', 'admin'
        )
        self.client.force_login(self.admin)

    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"})
    @patch('processing.services.student_pdf_generator.StudentPDFGenerator')
    def test_successful_generation(self, MockGenerator):
        exam = Exam.objects.create(name='Generate Test', date='2026-01-01')
        ExamSourcePDF.objects.create(
            exam=exam,
            pdf_file=SimpleUploadedFile("scan.pdf", make_a3_pdf(), content_type="application/pdf"),
            original_filename='scan.pdf',
            pdf_type=ExamSourcePDF.PDFType.COPY,
        )
        exam.student_csv.save('eleves.csv', SimpleUploadedFile("eleves.csv", make_csv_bytes()))

        # Mock the generator to write PDFs to the temp dir
        def fake_generate(pdf_paths, annexe_path=None, output_dir=None):
            if output_dir:
                # Write a fake PDF file
                for name in ['DUPONT Jean', 'MARTIN Alice']:
                    safe = "".join(c if c.isalnum() or c in " -_" else "_" for c in name).strip()
                    filepath = os.path.join(output_dir, f"{safe}.pdf")
                    with open(filepath, 'wb') as f:
                        f.write(make_pdf(pages=4))
            return {
                'student_pdfs': {},
                'filename_to_student': {
                    'DUPONT Jean.pdf': 'DUPONT Jean',
                    'MARTIN Alice.pdf': 'MARTIN Alice',
                },
                'generated_count': 2,
                'failed_count': 0,
                'annexes_matched': 0,
                'annexes_unmatched': 0,
                'missing_students': [],
            }

        mock_instance = MockGenerator.return_value
        mock_instance.generate.side_effect = fake_generate

        url = reverse('generate-student-pdfs', kwargs={'exam_id': exam.id})
        response = self.client.post(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['generated'], 2)
        self.assertEqual(response.data['stored'], 2)
        self.assertEqual(response.data['failed'], 0)

        # Verify copies were created
        copies = Copy.objects.filter(exam=exam)
        self.assertEqual(copies.count(), 2)

    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"})
    @patch('processing.services.student_pdf_generator.StudentPDFGenerator')
    def test_annexe_pdf_passed_to_generator(self, MockGenerator):
        """Vérifie que le PDF d'annexes est correctement passé au générateur."""
        exam = Exam.objects.create(name='Annexe Test', date='2026-01-01')
        ExamSourcePDF.objects.create(
            exam=exam,
            pdf_file=SimpleUploadedFile("scan.pdf", make_a3_pdf(), content_type="application/pdf"),
            original_filename='scan.pdf',
            pdf_type=ExamSourcePDF.PDFType.COPY,
        )
        annexe_source = ExamSourcePDF.objects.create(
            exam=exam,
            pdf_file=SimpleUploadedFile("annexes.pdf", make_pdf(pages=2), content_type="application/pdf"),
            original_filename='annexes.pdf',
            pdf_type=ExamSourcePDF.PDFType.ANNEXE,
        )
        exam.student_csv.save('eleves.csv', SimpleUploadedFile("eleves.csv", make_csv_bytes()))

        mock_instance = MockGenerator.return_value
        mock_instance.generate.return_value = {
            'student_pdfs': {},
            'filename_to_student': {},
            'generated_count': 0,
            'failed_count': 0,
            'annexes_matched': 0,
            'annexes_unmatched': 0,
            'missing_students': [],
        }

        url = reverse('generate-student-pdfs', kwargs={'exam_id': exam.id})
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify generator was called with annexe_path
        call_args = mock_instance.generate.call_args
        self.assertIsNotNone(call_args.kwargs.get('annexe_path') or call_args[1].get('annexe_path'))


@override_settings(RATELIMIT_ENABLE=False)
class TestFindOrCreateCopy(TestCase):
    """Tests pour _find_or_create_copy."""

    def setUp(self):
        self.exam = Exam.objects.create(name='Test', date='2026-01-01')

    def test_creates_new_copy_for_unknown_student(self):
        copy = GenerateStudentPDFsView._find_or_create_copy(self.exam, "UNKNOWN Student")
        self.assertIsNotNone(copy)
        self.assertEqual(copy.exam, self.exam)
        self.assertEqual(copy.status, Copy.Status.READY)
        self.assertFalse(copy.is_identified)

    def test_creates_copy_linked_to_student(self):
        from students.models import Student
        student = Student.objects.create(
            full_name="DUPONT Jean",
            date_of_birth="2006-01-01",
        )
        copy = GenerateStudentPDFsView._find_or_create_copy(self.exam, "DUPONT Jean")
        self.assertEqual(copy.student, student)
        self.assertTrue(copy.is_identified)

    def test_returns_existing_copy_if_found(self):
        from students.models import Student
        student = Student.objects.create(
            full_name="DUPONT Jean",
            date_of_birth="2006-01-01",
        )
        existing = Copy.objects.create(
            exam=self.exam,
            student=student,
            anonymous_id="TEST1234",
            status=Copy.Status.READY,
        )
        copy = GenerateStudentPDFsView._find_or_create_copy(self.exam, "DUPONT Jean")
        self.assertEqual(copy.id, existing.id)

    def test_fuzzy_match_student(self):
        """Fuzzy matching finds student even with slight name difference."""
        from students.models import Student
        student = Student.objects.create(
            full_name="BÉNÉDICTE Léa",
            date_of_birth="2006-03-03",
        )
        copy = GenerateStudentPDFsView._find_or_create_copy(self.exam, "BENEDICTE Lea")
        # Should fuzzy match (ratio ~0.85 for accent-stripped)
        self.assertEqual(copy.student, student)
        self.assertTrue(copy.is_identified)


# Import at module level for test class access
from exams.views import GenerateStudentPDFsView


# ─── Test annexe upload in multi-upload ──────────────────────────────


@override_settings(RATELIMIT_ENABLE=False)
class TestMultiUploadAnnexe(TestCase):
    """Tests pour l'upload d'annexes via ExamMultiUploadView."""

    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_superuser(
            'admin', 'admin@test.fr', 'admin'
        )
        self.client.force_login(self.admin)
        self.url = reverse('exam-multi-upload')

    def test_annexe_saved_as_annexe_type(self):
        """Le PDF d'annexe est sauvé avec pdf_type=ANNEXE."""
        pdf = SimpleUploadedFile("scan.pdf", make_a3_pdf(pages=2), content_type="application/pdf")
        annexe = SimpleUploadedFile("annexes.pdf", make_pdf(pages=3), content_type="application/pdf")

        response = self.client.post(self.url, {
            'name': 'Annexe Test',
            'date': '2026-06-15',
            'pdf_files': pdf,
            'annexe_pdf': annexe,
        }, format='multipart')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data.get('has_annexe'))

        exam = Exam.objects.first()
        annexe_sources = exam.source_pdfs.filter(pdf_type=ExamSourcePDF.PDFType.ANNEXE)
        self.assertEqual(annexe_sources.count(), 1)
        annexe_src = annexe_sources.first()
        self.assertEqual(annexe_src.original_filename, 'annexes.pdf')
        self.assertEqual(annexe_src.page_count, 3)
        self.assertEqual(annexe_src.detected_format, 'A4')

    def test_no_annexe_has_annexe_false(self):
        """Sans annexe, has_annexe est False."""
        pdf = SimpleUploadedFile("scan.pdf", make_pdf(), content_type="application/pdf")
        response = self.client.post(self.url, {
            'name': 'No Annexe',
            'date': '2026-06-15',
            'pdf_files': pdf,
        }, format='multipart')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertFalse(response.data.get('has_annexe'))

    def test_annexe_with_csv(self):
        """Upload combiné: PDF + CSV + Annexe."""
        pdf = SimpleUploadedFile("scan.pdf", make_a3_pdf(pages=2), content_type="application/pdf")
        csv_file = SimpleUploadedFile("eleves.csv", make_csv_bytes(), content_type="text/csv")
        annexe = SimpleUploadedFile("annexes.pdf", make_pdf(pages=2), content_type="application/pdf")

        response = self.client.post(self.url, {
            'name': 'Full Upload',
            'date': '2026-06-15',
            'pdf_files': pdf,
            'students_csv': csv_file,
            'annexe_pdf': annexe,
        }, format='multipart')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data.get('has_annexe'))

        exam = Exam.objects.first()
        self.assertTrue(bool(exam.student_csv))
        self.assertEqual(exam.source_pdfs.filter(pdf_type=ExamSourcePDF.PDFType.ANNEXE).count(), 1)
        self.assertEqual(exam.source_pdfs.filter(pdf_type=ExamSourcePDF.PDFType.COPY).count(), 1)
