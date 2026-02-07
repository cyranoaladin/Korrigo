"""
PDF Splitter Service - Découpe un PDF d'examen en booklets et extrait les pages.
"""
import fitz  # PyMuPDF
import os
import logging
from pathlib import Path
from django.conf import settings
from django.core.files.base import ContentFile
from django.db import transaction
from exams.models import Exam, Booklet

logger = logging.getLogger(__name__)


class PDFSplitter:
    """
    Service pour découper un PDF d'examen en fascicules (booklets) de N pages.

    Workflow:
    1. Ouvre le PDF source de l'exam
    2. Calcule le nombre de booklets (total_pages // pages_per_booklet)
    3. Pour chaque booklet:
       - Crée un objet Booklet avec start_page, end_page
       - Extrait chaque page individuelle en PNG
       - Stocke les chemins dans booklet.pages_images

    Idempotence: Si les booklets existent déjà pour cet exam, skip.
    """

    def __init__(self, pages_per_booklet=4, dpi=150):
        """
        Args:
            pages_per_booklet (int): Nombre de pages par fascicule (default: 4 pour PMF)
            dpi (int): DPI pour l'extraction PNG (default: 150)
        """
        self.pages_per_booklet = pages_per_booklet
        self.dpi = dpi

    @transaction.atomic
    def split_exam(self, exam: Exam, force=False):
        """
        Découpe le PDF de l'examen en booklets.
        Adapte le nombre de pages en fonction de exam.pages_per_booklet.
        Gère les reliquats (pages restantes).
        """
        # Idempotence check
        if not force and exam.booklets.exists():
            logger.info(f"Exam {exam.id} already has booklets, skipping split")
            return list(exam.booklets.all())

        if not exam.pdf_source:
            raise ValueError(f"Exam {exam.id} has no pdf_source")

        pdf_path = exam.pdf_source.path
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF not found: {pdf_path}")

        logger.info(f"Starting PDF split for exam {exam.id}: {pdf_path}")

        doc = fitz.open(pdf_path)
        try:
            total_pages = doc.page_count
            ppb = exam.pages_per_booklet or self.pages_per_booklet

            # Calculate chunks (ceil division)
            booklets_count = (total_pages + ppb - 1) // ppb

            logger.info(f"Total pages: {total_pages}, Pages/Booklet: {ppb}, Expected Booklets: {booklets_count}")

            booklets_created = []

            for i in range(booklets_count):
                start_page = i * ppb + 1  # 1-based
                end_page = min((i + 1) * ppb, total_pages) # Clamp to total

                logger.info(f"Creating booklet {i+1}/{booklets_count}: pages {start_page}-{end_page}")

                # Créer le booklet
                booklet = Booklet.objects.create(
                    exam=exam,
                    start_page=start_page,
                    end_page=end_page,
                    student_name_guess=f"Booklet {i+1}"
                )

                # Check for anomaly (orphan pages / partial booklet)
                actual_count = end_page - start_page + 1
                if actual_count != ppb:
                    logger.warning(f"Booklet {booklet.id} (Index {i}) has {actual_count} pages instead of {ppb}. Possible orphan/end of scan.")

                # Extraire les pages
                pages_images = self._extract_pages(doc, start_page, end_page, exam.id, booklet.id)

                # Sauvegarder les chemins
                booklet.pages_images = pages_images
                booklet.save()

                booklets_created.append(booklet)

                logger.info(f"Booklet {booklet.id} created with {len(pages_images)} pages")
        finally:
            doc.close()

        # Marquer l'exam comme traité
        exam.is_processed = True
        exam.save()

        logger.info(f"PDF split complete for exam {exam.id}: {len(booklets_created)} booklets created")
        return booklets_created

    @transaction.atomic
    def split_pdf_file(self, exam, pdf_path, source_pdf=None):
        """
        Découpe un fichier PDF arbitraire en booklets pour l'examen donné.
        Contrairement à split_exam(), accepte un chemin PDF au lieu de exam.pdf_source.

        Args:
            exam: Exam instance parente
            pdf_path (str): Chemin absolu vers le fichier PDF
            source_pdf: ExamSourcePDF instance optionnelle (FK de traçabilité)

        Returns:
            list[Booklet]: Liste des booklets créés
        """
        import os
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF not found: {pdf_path}")

        logger.info(f"Starting PDF split for exam {exam.id} from file: {pdf_path}")

        doc = fitz.open(pdf_path)
        try:
            total_pages = doc.page_count
            ppb = exam.pages_per_booklet or self.pages_per_booklet
            booklets_count = (total_pages + ppb - 1) // ppb

            logger.info(f"Total pages: {total_pages}, Pages/Booklet: {ppb}, Expected Booklets: {booklets_count}")

            booklets_created = []

            for i in range(booklets_count):
                start_page = i * ppb + 1
                end_page = min((i + 1) * ppb, total_pages)

                logger.info(f"Creating booklet {i+1}/{booklets_count}: pages {start_page}-{end_page}")

                booklet = Booklet.objects.create(
                    exam=exam,
                    start_page=start_page,
                    end_page=end_page,
                    source_pdf=source_pdf,
                    student_name_guess=f"Booklet {i+1}"
                )

                actual_count = end_page - start_page + 1
                if actual_count != ppb:
                    logger.warning(
                        f"Booklet {booklet.id} (Index {i}) has {actual_count} pages "
                        f"instead of {ppb}. Possible orphan/end of scan."
                    )

                pages_images = self._extract_pages(doc, start_page, end_page, exam.id, booklet.id)
                booklet.pages_images = pages_images
                booklet.save()

                booklets_created.append(booklet)
                logger.info(f"Booklet {booklet.id} created with {len(pages_images)} pages")
        finally:
            doc.close()

        logger.info(f"PDF file split complete: {len(booklets_created)} booklets created")
        return booklets_created

    def _extract_pages(self, doc: fitz.Document, start_page: int, end_page: int, exam_id, booklet_id):
        """
        Extrait les pages individuelles d'un booklet en PNG.

        Args:
            doc: PyMuPDF Document
            start_page (int): Page de début (1-based)
            end_page (int): Page de fin (1-based)
            exam_id: UUID de l'exam
            booklet_id: UUID du booklet

        Returns:
            list[str]: Liste des chemins relatifs à MEDIA_ROOT
        """
        pages_paths = []

        # Créer le dossier de destination
        output_dir = Path(settings.MEDIA_ROOT) / 'booklets' / str(exam_id) / str(booklet_id)
        output_dir.mkdir(parents=True, exist_ok=True)

        for page_num in range(start_page, end_page + 1):
            page_index = page_num - 1  # 0-based for fitz

            if page_index >= doc.page_count:
                logger.warning(f"Page {page_num} out of range, skipping")
                continue

            page = doc.load_page(page_index)

            # Render page to pixmap
            pix = page.get_pixmap(dpi=self.dpi)

            # Filename: page_001.png, page_002.png, etc.
            filename = f"page_{page_num:03d}.png"
            output_path = output_dir / filename

            # Save PNG
            pix.save(str(output_path))

            # Stocker le chemin relatif à MEDIA_ROOT
            relative_path = str(output_path.relative_to(settings.MEDIA_ROOT))
            pages_paths.append(relative_path)

            logger.debug(f"Extracted page {page_num} to {relative_path}")

        return pages_paths
