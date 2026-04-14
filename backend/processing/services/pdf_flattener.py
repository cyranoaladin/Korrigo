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

    UNICODE_FONT_REGULAR = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    UNICODE_FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    UNICODE_FONT_REGULAR_NAME = "korrigo_dejavu"
    UNICODE_FONT_BOLD_NAME = "korrigo_dejavu_bold"

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

    def _register_unicode_fonts(self, page):
        """
        Register Unicode-capable fonts on a page so French punctuation / accents
        are embedded correctly in the generated PDF.
        """
        regular = "helv"
        bold = "helv"

        if os.path.exists(self.UNICODE_FONT_REGULAR):
            page.insert_font(
                fontname=self.UNICODE_FONT_REGULAR_NAME,
                fontfile=self.UNICODE_FONT_REGULAR,
            )
            regular = self.UNICODE_FONT_REGULAR_NAME
        else:
            logger.warning("Unicode regular font not found: %s", self.UNICODE_FONT_REGULAR)

        if os.path.exists(self.UNICODE_FONT_BOLD):
            page.insert_font(
                fontname=self.UNICODE_FONT_BOLD_NAME,
                fontfile=self.UNICODE_FONT_BOLD,
            )
            bold = self.UNICODE_FONT_BOLD_NAME
        else:
            logger.warning("Unicode bold font not found: %s", self.UNICODE_FONT_BOLD)

        return regular, bold

    def _annotation_type_label(self, annotation_type):
        labels = {
            Annotation.Type.COMMENTAIRE: "Commentaire",
            Annotation.Type.SURLIGNAGE: "Surlignage",
            Annotation.Type.ERREUR: "Erreur",
            Annotation.Type.BONUS: "Bonus",
            Annotation.Type.VRAI: "Validation",
            Annotation.Type.FAUX: "Correction",
        }
        return labels.get(annotation_type, annotation_type or "Annotation")

    def _draw_annotations_on_page(self, page, annotations, page_width, page_height):
        """
        Dessine les annotations sur une page PDF.
        Dénormalise les coordonnées [0,1] → coordonnées PDF (ADR-002).
        """
        shape = page.new_shape()
        font_regular, font_bold = self._register_unicode_fonts(page)

        for annot in annotations:
            # Dénormalisation ADR-002
            x_pdf = annot.x * page_width
            y_pdf = annot.y * page_height
            w_pdf = annot.w * page_width
            h_pdf = annot.h * page_height

            # Couleur selon type
            color = self._get_annotation_color(annot.type)

            # Coordonnées du rectangle
            rect = fitz.Rect(x_pdf, y_pdf, x_pdf + w_pdf, y_pdf + h_pdf)

            # Rendu spécial pour les tampons V/X
            is_stamp = annot.type in (Annotation.Type.VRAI, Annotation.Type.FAUX)

            if is_stamp:
                # Tampons V/X : dessiner le symbole centré, pas de rectangle pointillé
                cx = x_pdf + w_pdf / 2
                cy = y_pdf + h_pdf / 2
                size = min(w_pdf, h_pdf) * 0.35

                if annot.type == Annotation.Type.VRAI:
                    # Dessiner un checkmark ✓
                    shape.draw_line(fitz.Point(cx - size, cy), fitz.Point(cx - size * 0.3, cy + size * 0.7))
                    shape.finish(color=color, width=3)
                    shape.draw_line(fitz.Point(cx - size * 0.3, cy + size * 0.7), fitz.Point(cx + size, cy - size * 0.5))
                    shape.finish(color=color, width=3)
                else:
                    # Dessiner un X ✗
                    shape.draw_line(fitz.Point(cx - size, cy - size), fitz.Point(cx + size, cy + size))
                    shape.finish(color=color, width=3)
                    shape.draw_line(fitz.Point(cx + size, cy - size), fitz.Point(cx - size, cy + size))
                    shape.finish(color=color, width=3)
            else:
                # Annotations normales : rectangle pointillé + texte
                shape.draw_rect(rect)
                shape.finish(color=color, width=2, dashes="[3 3]")  # Pointillé

                # Ajouter texte si content non vide
                if annot.content:
                    # Position texte légèrement décalée
                    text_point = fitz.Point(x_pdf + 5, y_pdf - 5 if y_pdf > 20 else y_pdf + h_pdf + 15)
                    # Limiter longueur du texte affiché
                    display_text = annot.content[:50] + "..." if len(annot.content) > 50 else annot.content
                    shape.insert_text(
                        text_point,
                        display_text,
                        fontsize=10,
                        color=color,
                        fontname=font_regular,
                    )

            # Ajouter score_delta si présent
            if annot.score_delta is not None:
                score_text = f"{annot.score_delta:+d}"  # Format +5 ou -3
                score_point = fitz.Point(x_pdf + w_pdf - 20, y_pdf + 15)
                shape.insert_text(
                    score_point,
                    score_text,
                    fontsize=12,
                    color=(1, 0, 0),
                    fontname=font_bold,
                )

        shape.commit()

    def _get_annotation_color(self, annotation_type):
        """
        Retourne la couleur RGB selon le type d'annotation.
        """
        colors = {
            Annotation.Type.COMMENTAIRE: (0, 0, 1),   # Bleu
            Annotation.Type.SURLIGNAGE: (1, 1, 0),    # Jaune
            Annotation.Type.ERREUR: (1, 0, 0),       # Rouge
            Annotation.Type.BONUS: (0, 0.5, 0),       # Vert
            Annotation.Type.VRAI: (0, 0.6, 0),       # Vert (tampon V)
            Annotation.Type.FAUX: (1, 0, 0),         # Rouge (tampon X)
        }
        return colors.get(annotation_type, (0, 0, 0))  # Noir par défaut

    def _add_summary_page(self, doc, copy):
        """
        Ajoute des pages de synthèse avec un design soigné :
        - En-tête coloré avec note finale
        - Détail des notes groupées par exercice
        - Remarques par question
        - Appréciation générale
        """
        PAGE_W, PAGE_H = 595, 842
        ML = 50          # margin left
        MR = 545         # margin right
        LH = 17          # line height
        MAX_Y = 800

        # Couleurs (RGB 0-1)
        C_PRIMARY = (0.22, 0.27, 0.55)    # indigo foncé
        C_ACCENT  = (0.30, 0.50, 0.90)    # bleu vif
        C_GREEN   = (0.10, 0.60, 0.30)    # vert
        C_RED     = (0.80, 0.15, 0.15)    # rouge
        C_ORANGE  = (0.85, 0.50, 0.10)    # orange
        C_GRAY    = (0.40, 0.40, 0.45)    # gris texte
        C_LGRAY   = (0.75, 0.78, 0.82)    # gris clair
        C_WHITE   = (1, 1, 1)
        C_BG_BLUE = (0.93, 0.95, 1.0)     # fond bleu pâle

        summary_page = doc.new_page(width=PAGE_W, height=PAGE_H)
        shape = summary_page.new_shape()
        font_regular, font_bold = self._register_unicode_fonts(summary_page)

        def txt(x, y, text, fontsize=10, color=C_GRAY, bold=False):
            summary_page.insert_text(
                fitz.Point(x, y),
                text,
                fontsize=fontsize,
                color=color,
                fontname=font_bold if bold else font_regular,
            )

        def new_page():
            nonlocal summary_page, shape, font_regular, font_bold
            shape.commit()
            summary_page = doc.new_page(width=PAGE_W, height=PAGE_H)
            shape = summary_page.new_shape()
            font_regular, font_bold = self._register_unicode_fonts(summary_page)
            txt(ML, 36, "Relevé de notes (suite)", fontsize=13, color=C_PRIMARY, bold=True)
            return 68

        def ck(y, needed=LH):
            return new_page() if y + needed > MAX_Y else y

        def wrap(x, y, text, fs=10, mw=460, color=C_GRAY, bold=False):
            if not text:
                return y
            cpl = max(int(mw / (fs * 0.5)), 20)
            for para in text.split('\n'):
                while len(para) > cpl:
                    sp = para[:cpl].rfind(' ')
                    if sp <= 0:
                        sp = cpl
                    y = ck(y, LH)
                    txt(x, y, para[:sp], fontsize=fs, color=color, bold=bold)
                    y += LH
                    para = para[sp:].lstrip()
                y = ck(y, LH)
                txt(x, y, para, fontsize=fs, color=color, bold=bold)
                y += LH
            return y

        def draw_rect(x, y, w, h, fill=None, border=None):
            r = fitz.Rect(x, y, x + w, y + h)
            shape.draw_rect(r)
            shape.finish(fill=fill, color=border, width=0.5 if border else 0)

        def score_color(score, mx):
            if mx <= 0:
                return C_GRAY
            pct = score / mx
            if pct >= 0.8:
                return C_GREEN
            if pct >= 0.5:
                return C_ORANGE
            return C_RED

        # ── Données ──
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

        # Build exercise structure from grading_utils
        from exams.grading_utils import extract_leaf_questions, build_exercise_config
        exercises_cfg = {}
        leaf_map = {}   # qid -> {exercise_idx, label, points}
        if copy.exam and copy.exam.grading_structure:
            exercises_cfg = build_exercise_config(copy.exam.grading_structure)
            for leaf in extract_leaf_questions(copy.exam.grading_structure):
                leaf_map[leaf['id']] = {
                    **leaf,
                    'display_label': leaf.get('short_label') or leaf['label'],
                }

        # Group scores by exercise
        ex_groups = {}  # {ex_idx: [(label, score, max_pts), ...]}
        for qid, qscore in scores_data.items():
            info = leaf_map.get(qid)
            if info:
                eidx = info['exercise_idx']
                qlabel = info['display_label']
                qmax = info['points']
            else:
                eidx = 0
                qlabel = qid
                qmax = 0
            ex_groups.setdefault(eidx, []).append((qlabel, float(qscore or 0), qmax))

        # ══════════════ EN-TÊTE ══════════════
        # Bandeau indigo en haut
        draw_rect(0, 0, PAGE_W, 110, fill=C_PRIMARY)

        y = 38
        txt(ML, y, "Relevé de notes", fontsize=22, color=C_WHITE, bold=True)
        y += 28
        exam_name = copy.exam.name if copy.exam else "Examen"
        txt(ML, y, exam_name, fontsize=13, color=(0.75, 0.80, 1.0))
        txt(ML + 200, y, f"Copie : {copy.anonymous_id}", fontsize=13, color=(0.75, 0.80, 1.0))

        # Encadré note finale (à droite dans le bandeau)
        note_x = 390
        draw_rect(note_x, 18, 170, 74, fill=(0.15, 0.20, 0.45))
        txt(note_x + 15, 48, f"{total_score:.2f}", fontsize=28, color=C_WHITE, bold=True)
        txt(note_x + 105, 48, "/ 20", fontsize=14, color=(0.65, 0.70, 0.90))
        txt(note_x + 15, 72, "Note finale", fontsize=10, color=(0.65, 0.70, 0.90))

        y = 130

        # ══════════════ DÉTAIL DES NOTES PAR EXERCICE ══════════════
        y = ck(y, 25)
        txt(ML, y, "Détail des notes", fontsize=16, color=C_PRIMARY, bold=True)
        y += 8
        shape.draw_line(fitz.Point(ML, y), fitz.Point(MR, y))
        shape.finish(color=C_ACCENT, width=1.5)
        y += 15

        for eidx in sorted(ex_groups.keys(), key=lambda value: (value == 0, value)):
            questions = ex_groups[eidx]
            ecfg = exercises_cfg.get(eidx, {})
            ex_name = ecfg.get('name', f'Exercice {eidx}')
            ex_max = ecfg.get('max', sum(q[2] for q in questions))
            ex_total = sum(q[1] for q in questions)

            # En-tête exercice (fond coloré)
            y = ck(y, 30)
            draw_rect(ML, y - 12, MR - ML, 22, fill=C_BG_BLUE)
            txt(ML + 8, y + 2, ex_name, fontsize=11, color=C_PRIMARY, bold=True)
            sc_txt = f"{ex_total:.2f} / {ex_max:.2f}"
            txt(MR - 100, y + 2, sc_txt, fontsize=11, color=score_color(ex_total, ex_max))
            y += 18

            # Sort questions by label naturally
            import re as _re
            def natural_key(item):
                return [int(c) if c.isdigit() else c.lower() for c in _re.split(r'(\d+)', item[0])]
            questions.sort(key=natural_key)

            for qlabel, qscore, qmax in questions:
                y = ck(y)
                # Bullet
                txt(ML + 20, y, "-", fontsize=10, color=C_LGRAY)
                # Label
                display_label = f"Question {qlabel}" if len(qlabel) <= 3 else qlabel
                txt(ML + 32, y, display_label, fontsize=10, color=C_GRAY)
                # Score
                sc_str = f"{qscore:.2f} / {qmax:.2f}"
                txt(MR - 90, y, sc_str, fontsize=10, color=score_color(qscore, qmax))
                y += LH

            y += 8  # espacement entre exercices

        if not ex_groups:
            y = ck(y, LH)
            txt(ML, y, "Aucune note détaillée disponible.", fontsize=10, color=C_GRAY)
            y += LH

        y += 10

        # ══════════════ REMARQUES ══════════════
        remarks = list(QuestionRemark.objects.filter(copy=copy).order_by('question_id'))
        remarks_with_text = [r for r in remarks if r.remark and r.remark.strip()]

        if remarks_with_text:
            y = ck(y, 30)
            txt(ML, y, "Remarques du correcteur", fontsize=16, color=C_PRIMARY, bold=True)
            y += 8
            shape.draw_line(fitz.Point(ML, y), fitz.Point(MR, y))
            shape.finish(color=C_ORANGE, width=1.5)
            y += 15

            for remark in remarks_with_text:
                info = leaf_map.get(remark.question_id)
                if info:
                    ex_cfg = exercises_cfg.get(info['exercise_idx'], {})
                    r_label = f"{ex_cfg.get('name', 'Exercice')} \u2014 Question {info['display_label']}"
                else:
                    r_label = f"Question {remark.question_id}"

                y = ck(y, LH * 2)
                # Ligne de fond orange pâle pour le label
                draw_rect(ML, y - 11, MR - ML, 16, fill=(1.0, 0.96, 0.90))
                txt(ML + 8, y, r_label, fontsize=10, color=C_ORANGE)
                y += LH
                y = wrap(ML + 16, y, remark.remark.strip(), fs=10, color=C_GRAY)
                y += 6

        y += 10

        # ══════════════ ANNOTATIONS ══════════════
        annotations = list(copy.annotations.all().order_by('page_index', 'created_at'))
        visible_annotations = annotations

        if visible_annotations:
            y = ck(y, 30)
            txt(ML, y, "Annotations sur la copie", fontsize=16, color=C_PRIMARY, bold=True)
            y += 8
            shape.draw_line(fitz.Point(ML, y), fitz.Point(MR, y))
            shape.finish(color=C_ACCENT, width=1.5)
            y += 15

            for annot in visible_annotations:
                label = f"Page {annot.page_index + 1} — {self._annotation_type_label(annot.type)}"
                if annot.score_delta is not None:
                    label += f" ({annot.score_delta:+d} pt)"

                y = ck(y, LH * 2)
                draw_rect(ML, y - 11, MR - ML, 16, fill=(0.94, 0.97, 1.0))
                txt(ML + 8, y, label, fontsize=10, color=C_ACCENT)
                y += LH

                if annot.content and annot.content.strip():
                    y = wrap(ML + 16, y, annot.content.strip(), fs=10, color=C_GRAY)
                else:
                    txt(ML + 16, y, "Sans texte associé.", fontsize=10, color=C_GRAY)
                    y += LH

                y += 6

            y += 10

        # ══════════════ APPRÉCIATION GÉNÉRALE ══════════════
        appreciation = copy.global_appreciation
        if appreciation and appreciation.strip():
            y = ck(y, 40)
            txt(ML, y, "Appréciation générale", fontsize=16, color=C_PRIMARY, bold=True)
            y += 8
            shape.draw_line(fitz.Point(ML, y), fitz.Point(MR, y))
            shape.finish(color=C_GREEN, width=1.5)
            y += 15
            # Fond vert pâle
            text_h = max(30, len(appreciation) // 2)
            draw_rect(ML, y - 12, MR - ML, min(text_h, MAX_Y - y + 10), fill=(0.93, 1.0, 0.95))
            y = wrap(ML + 10, y, appreciation.strip(), fs=11, color=(0.15, 0.40, 0.20))

        # ══════════════ COMMENTAIRE FINAL ══════════════
        final_comment = score_obj.final_comment if score_obj and score_obj.final_comment else ''
        if final_comment and final_comment.strip():
            y += 15
            y = ck(y, 40)
            txt(ML, y, "Commentaire du correcteur", fontsize=16, color=C_PRIMARY, bold=True)
            y += 8
            shape.draw_line(fitz.Point(ML, y), fitz.Point(MR, y))
            shape.finish(color=C_ACCENT, width=1.5)
            y += 15
            y = wrap(ML + 10, y, final_comment.strip(), fs=11, color=C_GRAY)

        # Pied de page
        y = ck(MAX_Y - 20)
        shape.draw_line(fitz.Point(ML, MAX_Y - 5), fitz.Point(MR, MAX_Y - 5))
        shape.finish(color=C_LGRAY, width=0.5)
        txt(ML, MAX_Y + 8, "Korrigo \u2014 Plateforme de correction", fontsize=8, color=C_LGRAY)

        # Finaliser les formes
        shape.commit()
