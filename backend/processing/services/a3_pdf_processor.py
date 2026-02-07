"""
A3 PDF Processor Service - Détecte et traite les PDFs A3 recto/verso automatiquement.

Workflow pour scans A3 recto/verso:
1. Détecte si le PDF contient des pages A3 (ratio largeur/hauteur > 1.2)
2. Si A3: découpe chaque page en 2 pages A4, reconstruit l'ordre livret
3. Sinon: fallback sur PDFSplitter standard

Structure A3 recto/verso (livret plié):
- Page 1 du scan (RECTO): [P4 | P1] - P1 a l'en-tête
- Page 2 du scan (VERSO): [P2 | P3]
"""
import fitz  # PyMuPDF
import cv2
import numpy as np
import os
import tempfile
import logging
from pathlib import Path
from django.conf import settings
from django.db import transaction
from exams.models import Exam, Booklet, Copy
from .splitter import A3Splitter

logger = logging.getLogger(__name__)

# Seuil pour détecter un format A3 (landscape)
A3_ASPECT_RATIO_THRESHOLD = 1.2


class A3PDFProcessor:
    """
    Processeur intelligent de PDFs qui détecte automatiquement les scans A3
    et les traite correctement.
    """

    def __init__(self, dpi=150):
        self.dpi = dpi
        self.a3_splitter = A3Splitter()

    def is_a3_format(self, pdf_path: str) -> bool:
        """
        Détecte si le PDF contient des pages A3 (landscape avec ratio > 1.2).
        
        Args:
            pdf_path: Chemin vers le fichier PDF
            
        Returns:
            True si le PDF est en format A3, False sinon
        """
        doc = None
        try:
            doc = fitz.open(pdf_path)
            if doc.page_count == 0:
                return False

            page = doc.load_page(0)
            rect = page.rect
            width, height = rect.width, rect.height

            ratio = width / height if height > 0 else 0
            is_a3 = ratio > A3_ASPECT_RATIO_THRESHOLD

            logger.info(f"PDF format detection: width={width:.0f}, height={height:.0f}, ratio={ratio:.2f}, is_A3={is_a3}")
            return is_a3

        except Exception as e:
            logger.error(f"Error detecting PDF format: {e}")
            return False
        finally:
            if doc is not None:
                doc.close()

    @transaction.atomic
    def process_exam(self, exam: Exam, force=False) -> list:
        """
        Traite le PDF d'un examen, détecte le format et applique le bon pipeline.
        
        Args:
            exam: L'examen à traiter
            force: Forcer le retraitement même si des booklets existent
            
        Returns:
            Liste des booklets créés
        """
        # Idempotence check
        if not force and exam.booklets.exists():
            logger.info(f"Exam {exam.id} already has booklets, skipping")
            return list(exam.booklets.all())

        if not exam.pdf_source:
            raise ValueError(f"Exam {exam.id} has no pdf_source")

        pdf_path = exam.pdf_source.path
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF not found: {pdf_path}")

        # Détecter le format
        if self.is_a3_format(pdf_path):
            logger.info(f"A3 format detected for exam {exam.id}, using A3 pipeline")
            return self._process_a3_pdf(exam, pdf_path)
        else:
            logger.info(f"Standard format for exam {exam.id}, using standard pipeline")
            from .pdf_splitter import PDFSplitter
            splitter = PDFSplitter(dpi=self.dpi)
            return splitter.split_exam(exam, force=force)

    def _process_a3_pdf(self, exam: Exam, pdf_path: str) -> list:
        """
        Traite un PDF A3 recto/verso:
        1. Rasterise chaque page A3
        2. Découpe en 2 pages A4
        3. Reconstruit l'ordre du livret (P1, P2, P3, P4)
        4. Crée les booklets et copies
        
        Args:
            exam: L'examen
            pdf_path: Chemin du PDF
            
        Returns:
            Liste des booklets créés
        """
        doc = fitz.open(pdf_path)
        total_a3_pages = doc.page_count
        
        logger.info(f"Processing A3 PDF: {total_a3_pages} A3 pages")
        
        # Chaque paire de pages A3 (recto + verso) = 1 copie de 4 pages A4
        # Nombre de copies = total_a3_pages / 2
        expected_copies = total_a3_pages // 2
        
        logger.info(f"Expected copies: {expected_copies} (from {total_a3_pages} A3 pages)")
        
        # Créer le dossier de sortie
        output_dir = Path(settings.MEDIA_ROOT) / 'booklets' / str(exam.id)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        booklets_created = []
        
        # Traiter par paires (recto + verso)
        for copy_index in range(expected_copies):
            recto_page_idx = copy_index * 2      # Page A3 recto (0-based)
            verso_page_idx = copy_index * 2 + 1  # Page A3 verso (0-based)
            
            logger.info(f"Processing copy {copy_index + 1}/{expected_copies}: A3 pages {recto_page_idx + 1} and {verso_page_idx + 1}")
            
            try:
                # Rasteriser les pages A3
                recto_img = self._rasterize_page(doc, recto_page_idx)
                verso_img = self._rasterize_page(doc, verso_page_idx) if verso_page_idx < total_a3_pages else None
                
                # Découper et reconstruire l'ordre
                a4_pages = self._split_and_reconstruct(recto_img, verso_img, copy_index)
                
                # Créer le booklet
                booklet = self._create_booklet_from_a4_pages(
                    exam, a4_pages, copy_index, output_dir
                )
                booklets_created.append(booklet)
                
            except Exception as e:
                logger.error(f"Error processing copy {copy_index + 1}: {e}")
                # Continuer avec les autres copies
                continue
        
        doc.close()
        
        # Marquer l'exam comme traité
        exam.is_processed = True
        exam.save()
        
        logger.info(f"A3 PDF processing complete: {len(booklets_created)} booklets created")
        return booklets_created

    def _rasterize_page(self, doc: fitz.Document, page_idx: int) -> np.ndarray:
        """
        Rasterise une page PDF en image numpy.
        """
        page = doc.load_page(page_idx)
        pix = page.get_pixmap(dpi=self.dpi)
        
        # Convertir en numpy array (RGB)
        img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
        
        # Convertir RGB en BGR pour OpenCV
        if pix.n == 3:
            img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
        elif pix.n == 4:
            img = cv2.cvtColor(img, cv2.COLOR_RGBA2BGR)
        
        return img

    def _split_and_reconstruct(self, recto_img: np.ndarray, verso_img: np.ndarray, copy_index: int) -> list:
        """
        Découpe les images A3 en A4 et reconstruit l'ordre du livret.
        
        Structure A3:
        - RECTO: [P4 | P1] (P1 a l'en-tête à droite)
        - VERSO: [P2 | P3]
        
        Ordre final: [P1, P2, P3, P4]
        """
        # Sauvegarder temporairement pour A3Splitter
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
            recto_path = f.name
            cv2.imwrite(recto_path, recto_img)
        
        try:
            # Traiter le recto
            recto_result = self.a3_splitter.process_scan(recto_path)
            
            if verso_img is not None:
                with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
                    verso_path = f.name
                    cv2.imwrite(verso_path, verso_img)
                
                try:
                    verso_result = self.a3_splitter.process_scan(verso_path)
                finally:
                    if os.path.exists(verso_path):
                        os.unlink(verso_path)
            else:
                # Pas de verso (dernière copie incomplète)
                verso_result = {'type': 'VERSO', 'pages': {'p2': None, 'p3': None}}
            
            # Reconstruire l'ordre [P1, P2, P3, P4]
            pages = []
            
            # P1 (depuis recto)
            if 'pages' in recto_result and 'p1' in recto_result['pages']:
                pages.append(('p1', recto_result['pages']['p1']))
            elif 'pages' in recto_result and 'p4' in recto_result['pages']:
                # Fallback si détection inversée
                pages.append(('p1', recto_result['pages'].get('p1') or recto_result['pages'].get('p4')))
            
            # P2 (depuis verso)
            if 'pages' in verso_result and verso_result['pages'].get('p2') is not None:
                pages.append(('p2', verso_result['pages']['p2']))
            
            # P3 (depuis verso)
            if 'pages' in verso_result and verso_result['pages'].get('p3') is not None:
                pages.append(('p3', verso_result['pages']['p3']))
            
            # P4 (depuis recto)
            if 'pages' in recto_result and 'p4' in recto_result['pages']:
                pages.append(('p4', recto_result['pages']['p4']))
            
            logger.info(f"Copy {copy_index + 1}: reconstructed {len(pages)} A4 pages")
            return pages
            
        finally:
            if os.path.exists(recto_path):
                os.unlink(recto_path)

    def _create_booklet_from_a4_pages(self, exam: Exam, a4_pages: list, copy_index: int, output_dir: Path) -> Booklet:
        """
        Crée un booklet à partir des pages A4 reconstruites.
        """
        import uuid
        
        booklet_id = uuid.uuid4()
        booklet_dir = output_dir / str(booklet_id)
        booklet_dir.mkdir(parents=True, exist_ok=True)
        
        pages_paths = []
        
        for i, (page_name, page_img) in enumerate(a4_pages):
            if page_img is None:
                continue
                
            filename = f"{page_name}.png"
            output_path = booklet_dir / filename
            
            cv2.imwrite(str(output_path), page_img)
            
            relative_path = str(output_path.relative_to(settings.MEDIA_ROOT))
            pages_paths.append(relative_path)
            
            logger.debug(f"Saved {page_name} to {relative_path}")
        
        # Créer le booklet
        booklet = Booklet.objects.create(
            id=booklet_id,
            exam=exam,
            start_page=copy_index * 4 + 1,
            end_page=copy_index * 4 + len(pages_paths),
            pages_images=pages_paths,
            student_name_guess=f"Copy {copy_index + 1}"
        )
        
        logger.info(f"Created booklet {booklet.id} with {len(pages_paths)} pages")
        return booklet
