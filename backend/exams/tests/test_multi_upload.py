"""
Tests pour ExamMultiUploadView - Upload multi-fichiers PDF.
"""
import io
import fitz  # PyMuPDF
from django.test import TestCase, override_settings
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient
from rest_framework import status
from django.contrib.auth.models import User
from exams.models import Exam, Booklet, Copy, ExamSourcePDF


def make_pdf(pages=4, page_width=595, page_height=842):
    """Crée un PDF de test en mémoire (A4 par défaut)."""
    doc = fitz.open()
    for i in range(pages):
        page = doc.new_page(width=page_width, height=page_height)
        page.insert_text((72, 72), f"Page {i+1}", fontsize=24)
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


def make_a3_pdf(pages=2):
    """Crée un PDF A3 landscape (ratio > 1.2)."""
    # A3 landscape: width > height * 1.2
    return make_pdf(pages=pages, page_width=1190, page_height=842)


def make_csv():
    """Crée un CSV de test."""
    content = "Nom et Prénom,Date de naissance,Email\nDupont Jean,01/01/2005,jean@test.fr\n"
    return content.encode('utf-8')


@override_settings(RATELIMIT_ENABLE=False)
class TestMultiUploadEndpoint(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_superuser(
            username='admin', password='admin', email='admin@test.fr'
        )
        self.client.force_login(self.admin)
        self.url = reverse('exam-multi-upload')

    def test_url_resolves(self):
        """L'URL multi-upload/ existe et est accessible."""
        self.assertEqual(self.url, '/api/exams/multi-upload/')

    def test_missing_name_returns_400(self):
        """Nom obligatoire."""
        pdf = SimpleUploadedFile("scan.pdf", make_pdf(), content_type="application/pdf")
        response = self.client.post(self.url, {'date': '2026-01-15', 'pdf_files': pdf}, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Exam.objects.count(), 0)

    def test_missing_pdf_returns_400(self):
        """Au moins un PDF obligatoire."""
        response = self.client.post(self.url, {'name': 'Test', 'date': '2026-01-15'}, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Exam.objects.count(), 0)

    def test_single_a4_pdf_upload(self):
        """Upload d'un seul PDF A4 crée l'examen, les booklets et copies."""
        pdf_bytes = make_pdf(pages=8)
        pdf_file = SimpleUploadedFile("scan_a4.pdf", pdf_bytes, content_type="application/pdf")
        response = self.client.post(self.url, {
            'name': 'Test A4',
            'date': '2026-06-15',
            'pdf_files': pdf_file,
        }, format='multipart')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        data = response.data

        # Exam créé
        self.assertEqual(Exam.objects.count(), 1)
        exam = Exam.objects.first()
        self.assertEqual(exam.name, 'Test A4')
        self.assertTrue(exam.is_processed)

        # ExamSourcePDF créé
        self.assertEqual(ExamSourcePDF.objects.filter(exam=exam).count(), 1)
        source = ExamSourcePDF.objects.first()
        self.assertEqual(source.original_filename, 'scan_a4.pdf')
        self.assertEqual(source.detected_format, 'A4')
        self.assertEqual(source.page_count, 8)

        # Booklets créés (8 pages / 4 ppb = 2 booklets)
        booklets = Booklet.objects.filter(exam=exam)
        self.assertEqual(booklets.count(), 2)

        # Chaque booklet a le source_pdf FK
        for b in booklets:
            self.assertEqual(b.source_pdf, source)
            self.assertTrue(len(b.pages_images) > 0)

        # Copies créées en STAGING
        copies = Copy.objects.filter(exam=exam)
        self.assertEqual(copies.count(), 2)
        for c in copies:
            self.assertEqual(c.status, Copy.Status.STAGING)

        # Response contient les stats
        self.assertEqual(data['files_processed'], 1)
        self.assertEqual(len(data['per_file_results']), 1)
        self.assertEqual(data['per_file_results'][0]['format'], 'A4')

    def test_multiple_a4_pdfs_upload(self):
        """Upload de plusieurs PDFs A4 crée des booklets distincts pour chaque fichier."""
        pdf1 = SimpleUploadedFile("scan1.pdf", make_pdf(pages=4), content_type="application/pdf")
        pdf2 = SimpleUploadedFile("scan2.pdf", make_pdf(pages=8), content_type="application/pdf")

        response = self.client.post(self.url, {
            'name': 'Test Multi A4',
            'date': '2026-06-15',
            'pdf_files': [pdf1, pdf2],
        }, format='multipart')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        data = response.data

        exam = Exam.objects.first()
        self.assertEqual(ExamSourcePDF.objects.filter(exam=exam).count(), 2)

        # 4 pages / 4 ppb = 1 booklet + 8 pages / 4 ppb = 2 booklets = 3 total
        self.assertEqual(Booklet.objects.filter(exam=exam).count(), 3)
        self.assertEqual(Copy.objects.filter(exam=exam).count(), 3)

        self.assertEqual(data['files_processed'], 2)
        self.assertEqual(len(data['per_file_results']), 2)

    def test_csv_upload_with_pdf(self):
        """Le CSV est sauvegardé même sans mode batch."""
        pdf = SimpleUploadedFile("scan.pdf", make_pdf(), content_type="application/pdf")
        csv = SimpleUploadedFile("eleves.csv", make_csv(), content_type="text/csv")

        response = self.client.post(self.url, {
            'name': 'Test CSV',
            'date': '2026-06-15',
            'pdf_files': pdf,
            'students_csv': csv,
        }, format='multipart')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        exam = Exam.objects.first()
        self.assertTrue(bool(exam.student_csv))

    def test_invalid_pdf_rejected_with_file_errors(self):
        """Un PDF invalide retourne 400 avec file_errors structurées."""
        invalid_pdf = SimpleUploadedFile("bad.pdf", b"not a pdf", content_type="application/pdf")
        response = self.client.post(self.url, {
            'name': 'Test Bad',
            'date': '2026-06-15',
            'pdf_files': invalid_pdf,
        }, format='multipart')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('file_errors', response.data)
        self.assertIn('bad.pdf', response.data['file_errors'])
        # Aucun exam créé
        self.assertEqual(Exam.objects.count(), 0)

    def test_one_bad_one_good_rejects_all(self):
        """Si un fichier est invalide, AUCUN exam n'est créé (atomicité de la pré-validation)."""
        good_pdf = SimpleUploadedFile("good.pdf", make_pdf(), content_type="application/pdf")
        bad_pdf = SimpleUploadedFile("bad.pdf", b"corrupt", content_type="application/pdf")

        response = self.client.post(self.url, {
            'name': 'Test Mixed',
            'date': '2026-06-15',
            'pdf_files': [good_pdf, bad_pdf],
        }, format='multipart')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('file_errors', response.data)
        self.assertIn('bad.pdf', response.data['file_errors'])
        # Le bon fichier n'est PAS dans les erreurs
        self.assertNotIn('good.pdf', response.data['file_errors'])
        # Aucun exam créé
        self.assertEqual(Exam.objects.count(), 0)

    def test_backward_compat_pdf_source_key(self):
        """Fallback: la clé 'pdf_source' (ancien format) fonctionne."""
        pdf = SimpleUploadedFile("old_scan.pdf", make_pdf(), content_type="application/pdf")
        response = self.client.post(self.url, {
            'name': 'Backward Compat',
            'date': '2026-06-15',
            'pdf_source': pdf,
        }, format='multipart')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Exam.objects.count(), 1)
        self.assertEqual(ExamSourcePDF.objects.count(), 1)

    def test_unauthenticated_rejected(self):
        """Les utilisateurs non authentifiés sont rejetés."""
        self.client.logout()
        pdf = SimpleUploadedFile("scan.pdf", make_pdf(), content_type="application/pdf")
        response = self.client.post(self.url, {
            'name': 'No Auth',
            'date': '2026-06-15',
            'pdf_files': pdf,
        }, format='multipart')
        self.assertIn(response.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])

    def test_source_pdf_display_order(self):
        """Les ExamSourcePDF ont le bon display_order."""
        pdf1 = SimpleUploadedFile("first.pdf", make_pdf(pages=4), content_type="application/pdf")
        pdf2 = SimpleUploadedFile("second.pdf", make_pdf(pages=4), content_type="application/pdf")

        self.client.post(self.url, {
            'name': 'Order Test',
            'date': '2026-06-15',
            'pdf_files': [pdf1, pdf2],
        }, format='multipart')

        sources = ExamSourcePDF.objects.order_by('display_order')
        self.assertEqual(sources[0].original_filename, 'first.pdf')
        self.assertEqual(sources[0].display_order, 0)
        self.assertEqual(sources[1].original_filename, 'second.pdf')
        self.assertEqual(sources[1].display_order, 1)


class TestExamSourcePDFModel(TestCase):
    """Tests unitaires pour le modèle ExamSourcePDF."""

    def test_create_source_pdf(self):
        exam = Exam.objects.create(name='Test', date='2026-01-01')
        source = ExamSourcePDF.objects.create(
            exam=exam,
            pdf_file=SimpleUploadedFile("test.pdf", make_pdf(), content_type="application/pdf"),
            original_filename='test.pdf',
            detected_format=ExamSourcePDF.Format.A4,
            page_count=4,
        )
        self.assertEqual(source.exam, exam)
        self.assertEqual(source.detected_format, 'A4')
        self.assertEqual(str(source), 'test.pdf (A4, 4p)')

    def test_booklet_source_pdf_fk(self):
        exam = Exam.objects.create(name='Test FK', date='2026-01-01')
        source = ExamSourcePDF.objects.create(
            exam=exam,
            pdf_file=SimpleUploadedFile("src.pdf", make_pdf(), content_type="application/pdf"),
            original_filename='src.pdf',
        )
        booklet = Booklet.objects.create(
            exam=exam, start_page=1, end_page=4, source_pdf=source
        )
        self.assertEqual(booklet.source_pdf, source)
        self.assertIn(booklet, source.booklets.all())

    def test_booklet_source_pdf_nullable(self):
        """Les anciens booklets sans source_pdf restent valides."""
        exam = Exam.objects.create(name='Legacy', date='2026-01-01')
        booklet = Booklet.objects.create(exam=exam, start_page=1, end_page=4)
        self.assertIsNone(booklet.source_pdf)

    def test_cascade_delete(self):
        """Supprimer un exam supprime ses ExamSourcePDF (CASCADE)."""
        exam = Exam.objects.create(name='Cascade', date='2026-01-01')
        ExamSourcePDF.objects.create(
            exam=exam,
            pdf_file=SimpleUploadedFile("del.pdf", make_pdf(), content_type="application/pdf"),
            original_filename='del.pdf',
        )
        self.assertEqual(ExamSourcePDF.objects.count(), 1)
        exam.delete()
        self.assertEqual(ExamSourcePDF.objects.count(), 0)

    def test_source_pdf_ordering(self):
        exam = Exam.objects.create(name='Order', date='2026-01-01')
        s2 = ExamSourcePDF.objects.create(
            exam=exam, pdf_file=SimpleUploadedFile("b.pdf", make_pdf(), content_type="application/pdf"),
            original_filename='b.pdf', display_order=1
        )
        s1 = ExamSourcePDF.objects.create(
            exam=exam, pdf_file=SimpleUploadedFile("a.pdf", make_pdf(), content_type="application/pdf"),
            original_filename='a.pdf', display_order=0
        )
        sources = list(exam.source_pdfs.all())
        self.assertEqual(sources[0], s1)
        self.assertEqual(sources[1], s2)
