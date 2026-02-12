"""
Service pour générer le PDF final avec annotations.
Conforme ADR-002 (coordonnées normalisées [0,1]).
"""
import fitz  # PyMuPDF
import os
from tempfile import NamedTemporaryFile
from django.conf import settings
from django.core.files import File
from grading.models import Annotation
from exams.models import Copy
import logging

logger = logging.getLogger(__name__)


class PDFFlattener:
    """
    Service pour aplatir les annotations et générer le rendu final du PDF.
    Étape 3 : Conforme ADR-002 (coordonnées normalisées).
    """

    def flatten_copy(self, copy: Copy):
        """
        Génère un PDF final pour la copie donnée.
        1. Crée un nouveau PDF.
        2. Ajoute chaque page (image PNG) du fascicule.
        3. Dessine les annotations avec dénormalisation coordonnées (ADR-002).
        4. Ajoute une page de synthèse avec scores.
        5. Retourne les bytes du PDF final (sans side-effects DB).

        NOTE: Le statut de la copy est géré par GradingService.finalize_copy(),
        pas ici (respect de la séparation des responsabilités).
        """
        doc = fitz.open()

        # Récupérer les images des pages
        all_pages_images = []
        for booklet in copy.booklets.all().order_by('start_page'):
            if booklet.pages_images:
                all_pages_images.extend(booklet.pages_images)

        if not all_pages_images:
            logger.warning(f"Copy {copy.id} has no pages to flatten.")
            raise ValueError("No pages found to flatten")

        # Charger toutes les annotations
        annotations = list(copy.annotations.all().order_by('page_index'))

        # Traiter chaque page
        for page_idx, img_path in enumerate(all_pages_images):
            # Construire chemin complet
            full_path = os.path.join(settings.MEDIA_ROOT, img_path) if not img_path.startswith('/') else img_path

            if not os.path.exists(full_path):
                logger.error(f"Image not found: {full_path}")
                continue

            # Ouvrir l'image et la convertir en page PDF
            img = fitz.open(full_path)
            rect = img[0].rect
            pdfbytes = img.convert_to_pdf()
            img.close()

            img_pdf = fitz.open("pdf", pdfbytes)
            page = doc.new_page(width=rect.width, height=rect.height)
            page.show_pdf_page(rect, img_pdf, 0)

            # Filtrer annotations pour cette page (page_index 0-based)
            page_annotations = [a for a in annotations if a.page_index == page_idx]

            if page_annotations:
                self._draw_annotations_on_page(page, page_annotations, rect.width, rect.height)

        # Ajouter page de synthèse
        self._add_summary_page(doc, copy)

        # Sauvegarder le PDF dans un fichier temporaire (storage-agnostic)
        # Sauvegarder le PDF en mémoire
        output_filename = f"copy_{copy.id}_corrected.pdf"
        pdf_bytes = doc.write()
        doc.close()

        logger.info(f"Copy {copy.id} flattened successfully: {output_filename}")
        return pdf_bytes

    def _draw_annotations_on_page(self, page, annotations, page_width, page_height):
        """
        Dessine les annotations sur une page PDF.
        Dénormalise les coordonnées [0,1] → coordonnées PDF (ADR-002).
        """
        shape = page.new_shape()

        for annot in annotations:
            # Dénormalisation ADR-002
            x_pdf = annot.x * page_width
            y_pdf = annot.y * page_height
            w_pdf = annot.w * page_width
            h_pdf = annot.h * page_height

            # Couleur selon type
            color = self._get_annotation_color(annot.type)

            # Dessiner rectangle d'annotation
            rect = fitz.Rect(x_pdf, y_pdf, x_pdf + w_pdf, y_pdf + h_pdf)
            shape.draw_rect(rect)
            shape.finish(color=color, width=2, dashes="[3 3]")  # Pointillé

            # Ajouter texte si content non vide
            if annot.content:
                # Position texte légèrement décalée
                text_point = fitz.Point(x_pdf + 5, y_pdf - 5 if y_pdf > 20 else y_pdf + h_pdf + 15)
                # Limiter longueur du texte affiché
                display_text = annot.content[:50] + "..." if len(annot.content) > 50 else annot.content
                shape.insert_text(text_point, display_text, fontsize=10, color=color)

            # Ajouter score_delta si présent
            if annot.score_delta is not None:
                score_text = f"{annot.score_delta:+d}"  # Format +5 ou -3
                score_point = fitz.Point(x_pdf + w_pdf - 20, y_pdf + 15)
                shape.insert_text(score_point, score_text, fontsize=12, color=(1, 0, 0))

        shape.commit()

    def _get_annotation_color(self, annotation_type):
        """
        Retourne la couleur RGB selon le type d'annotation.
        """
        colors = {
            Annotation.Type.COMMENTAIRE: (0, 0, 1),   # Bleu
            Annotation.Type.SURLIGNAGE: (1, 1, 0),    # Jaune
            Annotation.Type.ERREUR: (1, 0, 0),        # Rouge
            Annotation.Type.BONUS: (0, 0.5, 0),       # Vert
        }
        return colors.get(annotation_type, (0, 0, 0))  # Noir par défaut

    def _add_summary_page(self, doc, copy):
        """
        Ajoute une page de synthèse avec le score total et les détails.
        """
        summary_page = doc.new_page(width=595, height=842)  # A4
        text_writer = fitz.TextWriter(summary_page.rect)

        # Titre
        text_writer.append(fitz.Point(50, 50), "Relevé de Notes", fontsize=24)
        text_writer.append(
            fitz.Point(50, 80),
            f"Copie : {copy.anonymous_id}",
            fontsize=14
        )

        # Récupérer toutes les annotations avec score_delta
        annotations_with_score = copy.annotations.filter(
            score_delta__isnull=False
        ).order_by('page_index')

        y = 120
        total_score = 0

        # Détail par annotation
        if annotations_with_score.exists():
            text_writer.append(fitz.Point(50, y), "Détail des points :", fontsize=14)
            y += 30

            for annot in annotations_with_score:
                score = annot.score_delta
                total_score += score
                score_str = f"{score:+d}"  # Format +5 ou -3

                # Limiter le texte affiché
                display_content = annot.content[:40] + "..." if len(annot.content) > 40 else annot.content
                line = f"Page {annot.page_index + 1} : {score_str} pts"
                if display_content:
                    line += f" ({display_content})"

                text_writer.append(fitz.Point(60, y), line, fontsize=11)
                y += 20

                # Nouvelle page si débordement
                if y > 800:
                    text_writer.write_text(summary_page)
                    summary_page = doc.new_page(width=595, height=842)
                    text_writer = fitz.TextWriter(summary_page.rect)
                    y = 50
        else:
            text_writer.append(
                fitz.Point(50, y),
                "Aucune annotation avec score.",
                fontsize=12
            )
            y += 30

        # Total
        y += 20
        text_writer.append(
            fitz.Point(50, y),
            f"SCORE TOTAL : {total_score} points",
            fontsize=18
        )

        text_writer.write_text(summary_page)
