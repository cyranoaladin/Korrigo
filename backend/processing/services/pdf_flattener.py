"""
Service pour générer le PDF final avec annotations.
Conforme ADR-002 (coordonnées normalisées [0,1]).
"""
import fitz  # PyMuPDF
import os
from tempfile import NamedTemporaryFile
from django.conf import settings
from django.core.files import File
from grading.models import Annotation, Score, QuestionRemark
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
            Annotation.Type.COMMENT: (0, 0, 1),   # Bleu
            Annotation.Type.HIGHLIGHT: (1, 1, 0),    # Jaune
            Annotation.Type.ERROR: (1, 0, 0),       # Rouge
            Annotation.Type.BONUS: (0, 0.5, 0),       # Vert
        }
        return colors.get(annotation_type, (0, 0, 0))  # Noir par défaut

    def _add_summary_page(self, doc, copy):
        """
        Ajoute des pages de synthèse complètes avec :
        - Notes détaillées du barème (Score.scores_data)
        - Note finale
        - Remarques par question (QuestionRemark)
        - Appréciation générale (Copy.global_appreciation)
        """
        PAGE_W, PAGE_H = 595, 842
        MARGIN_LEFT = 50
        MARGIN_RIGHT = 545
        LINE_HEIGHT = 18
        MAX_Y = 790

        summary_page = doc.new_page(width=PAGE_W, height=PAGE_H)
        text_writer = fitz.TextWriter(summary_page.rect)

        def new_page():
            nonlocal summary_page, text_writer
            text_writer.write_text(summary_page)
            summary_page = doc.new_page(width=PAGE_W, height=PAGE_H)
            text_writer = fitz.TextWriter(summary_page.rect)
            return 50

        def check_overflow(y, needed=LINE_HEIGHT):
            if y + needed > MAX_Y:
                return new_page()
            return y

        def write_wrapped(x, y, text, fontsize=10, max_width=480):
            """Écrit du texte avec retour à la ligne si trop long."""
            if not text:
                return y
            avg_char_width = fontsize * 0.5
            chars_per_line = max(int(max_width / avg_char_width), 20)
            lines = []
            for paragraph in text.split('\n'):
                while len(paragraph) > chars_per_line:
                    split_at = paragraph[:chars_per_line].rfind(' ')
                    if split_at <= 0:
                        split_at = chars_per_line
                    lines.append(paragraph[:split_at])
                    paragraph = paragraph[split_at:].lstrip()
                lines.append(paragraph)
            for line in lines:
                y = check_overflow(y, LINE_HEIGHT)
                text_writer.append(fitz.Point(x, y), line, fontsize=fontsize)
                y += LINE_HEIGHT
            return y

        # --- Titre ---
        y = 50
        text_writer.append(fitz.Point(MARGIN_LEFT, y), "Releve de Notes", fontsize=24)
        y += 35
        text_writer.append(
            fitz.Point(MARGIN_LEFT, y),
            f"Copie : {copy.anonymous_id}",
            fontsize=14
        )
        y += 30

        # --- 1. Notes detaillees du bareme ---
        score_obj = Score.objects.filter(copy=copy).first()
        scores_data = {}
        total_score = 0.0
        if score_obj and score_obj.scores_data:
            scores_data = score_obj.scores_data
            for val in scores_data.values():
                try:
                    total_score += float(val) if val not in (None, '') else 0
                except (TypeError, ValueError):
                    pass

        # Note finale en gros
        y = check_overflow(y, 35)
        text_writer.append(
            fitz.Point(MARGIN_LEFT, y),
            f"NOTE FINALE : {total_score:.2f} / 20",
            fontsize=20
        )
        y += 40

        # Détail par question
        if scores_data:
            y = check_overflow(y, 25)
            text_writer.append(fitz.Point(MARGIN_LEFT, y), "Detail des notes par question :", fontsize=14)
            y += 25

            def sort_key(item):
                parts = item[0].split('.')
                result = []
                for p in parts:
                    try:
                        result.append((0, int(p)))
                    except ValueError:
                        result.append((1, p))
                return result

            for q_id, q_score in sorted(scores_data.items(), key=sort_key):
                y = check_overflow(y)
                score_display = q_score if q_score not in (None, '') else '0'
                text_writer.append(
                    fitz.Point(70, y),
                    f"Q{q_id} : {score_display}",
                    fontsize=11
                )
                y += LINE_HEIGHT
        else:
            y = check_overflow(y)
            text_writer.append(fitz.Point(MARGIN_LEFT, y), "Aucune note de bareme enregistree.", fontsize=11)
            y += LINE_HEIGHT

        y += 15

        # --- 2. Remarques par question ---
        remarks = list(QuestionRemark.objects.filter(copy=copy).order_by('question_id'))
        remarks_with_text = [r for r in remarks if r.remark and r.remark.strip()]

        if remarks_with_text:
            y = check_overflow(y, 25)
            text_writer.append(fitz.Point(MARGIN_LEFT, y), "Remarques par question :", fontsize=14)
            y += 25

            for remark in remarks_with_text:
                y = check_overflow(y, LINE_HEIGHT * 2)
                text_writer.append(
                    fitz.Point(70, y),
                    f"Q{remark.question_id} :",
                    fontsize=11
                )
                y += LINE_HEIGHT
                y = write_wrapped(80, y, remark.remark.strip(), fontsize=10, max_width=460)
                y += 5

        y += 15

        # --- 3. Annotations visuelles (si presentes) ---
        annotations_with_score = copy.annotations.filter(
            score_delta__isnull=False
        ).order_by('page_index')

        if annotations_with_score.exists():
            y = check_overflow(y, 25)
            text_writer.append(fitz.Point(MARGIN_LEFT, y), "Annotations du correcteur :", fontsize=14)
            y += 25

            for annot in annotations_with_score:
                y = check_overflow(y)
                score_str = f"{annot.score_delta:+d}"
                display_content = annot.content[:60] + "..." if annot.content and len(annot.content) > 60 else (annot.content or '')
                line = f"Page {annot.page_index + 1} : {score_str} pts"
                if display_content:
                    line += f" - {display_content}"
                text_writer.append(fitz.Point(70, y), line, fontsize=10)
                y += LINE_HEIGHT

        y += 15

        # --- 4. Appreciation generale ---
        appreciation = copy.global_appreciation
        if appreciation and appreciation.strip():
            y = check_overflow(y, 25)
            text_writer.append(fitz.Point(MARGIN_LEFT, y), "Appreciation generale :", fontsize=14)
            y += 25
            y = write_wrapped(70, y, appreciation.strip(), fontsize=11, max_width=470)

        # Finaliser la dernière page
        text_writer.write_text(summary_page)
