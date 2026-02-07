"""
Générateur de PDF A4 par élève à partir de scans A3 recto-verso.

Adapté du script decoupe_copies_eleves.py au contexte Viatique.
Utilise GPT-4 Vision OCR pour l'identification des élèves et PyMuPDF
pour le traitement PDF.

Layout A3 recto/verso (livret plié):
  - Page impaire (recto): DROITE = page 1 (entête nom), GAUCHE = page 4
  - Page paire  (verso) : GAUCHE = page 2, DROITE = page 3
  Reconstruction: P1, P2, P3, P4

Usage:
    generator = StudentPDFGenerator(csv_path='eleves.csv')
    result = generator.generate(
        pdf_paths=['scan1.pdf', 'scan2.pdf'],
        annexe_path='annexes.pdf',
        output_dir='copies_par_eleve/'
    )
"""

import csv
import os
import io
import logging
import re
import unicodedata
from collections import OrderedDict
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from difflib import SequenceMatcher

import cv2
import fitz  # PyMuPDF
import numpy as np

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────
#  Prompts GPT-4V pour les deux formats d'en-tête
# ─────────────────────────────────────────────────────────────────────

PROMPT_CCYC = """\
Tu regardes l'entête d'une copie d'examen scannée (Modèle CCYC ©DNE).
Le nom et le prénom sont écrits à la main en MAJUSCULES dans des cases individuelles.
Les champs sont:
- "NOM DE FAMILLE (naissance):" suivi de cases avec les lettres
- "PRENOM:" suivi de cases avec les lettres
- "Né(e) le:" suivi d'une date DD/MM/YYYY dans des cases

Voici la liste EXACTE des élèves possibles avec leur date de naissance:
{liste_eleves}

Identifie quel élève de cette liste correspond à cette copie.
Utilise le nom ET la date de naissance pour identifier l'élève avec certitude.
L'écriture manuscrite peut être difficile à lire, cherche la meilleure correspondance.
Réponds UNIQUEMENT en JSON strict:
{{"numero": <numéro dans la liste>, "nom_lu": "<nom que tu lis>", "date_lue": "<date que tu lis>"}}
Si tu ne trouves vraiment aucune correspondance, réponds:
{{"numero": null, "nom_lu": "<ce que tu lis>", "date_lue": "<date lue>"}}"""

PROMPT_CMEN_V2 = """\
Tu regardes l'entête d'une page d'annexe d'examen scannée (Modèle CMEN v2 ONEOPTEC).
Le nom et le prénom sont écrits à la main en MAJUSCULES dans des cases individuelles.
Les champs sont:
- "Nom de famille:" suivi de cases avec les lettres
- "Prénom(s):" suivi de cases avec les lettres
- "Né(e) le:" suivi d'une date DD/MM/YYYY dans des cases

Voici la liste EXACTE des élèves possibles avec leur date de naissance:
{liste_eleves}

Identifie quel élève de cette liste correspond à cette annexe.
Utilise le nom ET la date de naissance pour identifier l'élève avec certitude.
L'écriture manuscrite peut être difficile à lire, cherche la meilleure correspondance.
Réponds UNIQUEMENT en JSON strict:
{{"numero": <numéro dans la liste>, "nom_lu": "<nom que tu lis>", "date_lue": "<date que tu lis>"}}
Si tu ne trouves vraiment aucune correspondance, réponds:
{{"numero": null, "nom_lu": "<ce que tu lis>", "date_lue": "<date lue>"}}"""


class StudentPDFGenerator:
    """
    Génère un PDF A4 par élève à partir de scans A3 + annexes optionnelles.

    Trois phases (comme le script original):
    1. Identification OCR de chaque feuille (recto header → GPT-4V)
    2. Post-correction des assignations (feuilles non-consécutives)
    3. Découpe A3→A4 + assemblage PDF par élève + annexes
    """

    A3_ASPECT_RATIO_THRESHOLD = 1.2

    def __init__(self, csv_path: str = None, api_key: str = None,
                 dpi_ocr: int = 150, dpi_render: int = 200):
        """
        Args:
            csv_path: Chemin vers le CSV des élèves.
            api_key: Clé API OpenAI. Si None, lit OPENAI_API_KEY.
            dpi_ocr: DPI pour la rasterisation OCR (basse résolution).
            dpi_render: DPI pour le rendu final des pages A4.
        """
        self.dpi_ocr = dpi_ocr
        self.dpi_render = dpi_render
        self.students = self._load_csv(csv_path) if csv_path else []
        self.api_key = api_key or os.environ.get('OPENAI_API_KEY')
        self._openai_client = None

    @property
    def openai_client(self):
        if self._openai_client is None:
            import openai
            self._openai_client = openai.OpenAI(api_key=self.api_key)
        return self._openai_client

    # ─────────────────────────────────────────────────────────────────
    #  Chargement CSV
    # ─────────────────────────────────────────────────────────────────

    def _load_csv(self, csv_path: str) -> List[Dict]:
        """Charge la liste des élèves depuis le CSV."""
        if not csv_path or not os.path.exists(csv_path):
            logger.warning(f"CSV introuvable: {csv_path}")
            return []

        students = []
        for encoding in ['utf-8-sig', 'utf-8', 'latin-1']:
            try:
                with open(csv_path, newline='', encoding=encoding) as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        # Support multiple column names
                        nom = (
                            row.get('\ufeffÉlèves') or row.get('Élèves')
                            or row.get('Elèves') or row.get('Nom et Prénom', '')
                        ).strip()
                        date_naissance = (
                            row.get('Né(e) le') or row.get('Date de naissance', '')
                        ).strip()
                        email = (
                            row.get('Adresse E-mail') or row.get('Email', '')
                        ).strip()
                        if nom:
                            students.append({
                                'nom': nom,
                                'date': date_naissance,
                                'email': email,
                            })
                break
            except (UnicodeDecodeError, UnicodeError):
                continue

        logger.info(f"CSV chargé: {len(students)} élèves depuis {csv_path}")
        return students

    # ─────────────────────────────────────────────────────────────────
    #  Rasterisation et découpe A3
    # ─────────────────────────────────────────────────────────────────

    def _rasterize_page(self, doc: fitz.Document, page_idx: int,
                        dpi: int) -> np.ndarray:
        """Rasterise une page PDF en image numpy BGR."""
        page = doc.load_page(page_idx)
        mat = fitz.Matrix(dpi / 72, dpi / 72)
        pix = page.get_pixmap(matrix=mat)

        img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(
            pix.height, pix.width, pix.n
        )
        if pix.n == 3:
            img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
        elif pix.n == 4:
            img = cv2.cvtColor(img, cv2.COLOR_RGBA2BGR)

        return img

    @staticmethod
    def _split_a3_to_a4(image: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """Coupe une image A3 paysage en deux moitiés A4 (gauche, droite)."""
        w = image.shape[1]
        mid = w // 2
        return image[:, :mid], image[:, mid:]

    def _is_a3(self, doc: fitz.Document) -> bool:
        """Détecte si un PDF est en format A3 (paysage, ratio > 1.2)."""
        page = doc.load_page(0)
        ratio = page.rect.width / page.rect.height
        return ratio > self.A3_ASPECT_RATIO_THRESHOLD

    # ─────────────────────────────────────────────────────────────────
    #  OCR avec GPT-4V
    # ─────────────────────────────────────────────────────────────────

    @staticmethod
    def _image_to_base64(image: np.ndarray) -> str:
        """Encode une image numpy en base64 JPEG."""
        _, buffer = cv2.imencode('.jpg', image, [cv2.IMWRITE_JPEG_QUALITY, 75])
        import base64
        return base64.b64encode(buffer).decode('utf-8')

    def _build_student_list_text(self) -> str:
        """Formate la liste des élèves pour le prompt."""
        return "\n".join(
            f"  {i + 1}. {s['nom']} (né(e) le {s['date']})"
            for i, s in enumerate(self.students)
        )

    def _ocr_identify_student(self, header_image: np.ndarray,
                              header_format: str = 'CCYC') -> Tuple[Optional[str], str]:
        """
        Identifie l'élève depuis l'en-tête via GPT-4V.

        Args:
            header_image: Image BGR de la zone en-tête.
            header_format: 'CCYC' (copies principales) ou 'CMEN_V2' (annexes).

        Returns:
            (nom_eleve_matché ou None, nom_lu_par_ocr)
        """
        import json as json_mod

        img_b64 = self._image_to_base64(header_image)
        liste_txt = self._build_student_list_text()

        prompt_template = PROMPT_CCYC if header_format == 'CCYC' else PROMPT_CMEN_V2
        prompt = prompt_template.format(liste_eleves=liste_txt)

        model = os.environ.get('OPENAI_MODEL', 'gpt-4o-mini')

        try:
            resp = self.openai_client.chat.completions.create(
                model=model,
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {
                            "url": f"data:image/jpeg;base64,{img_b64}",
                            "detail": "low"
                        }}
                    ]
                }],
                response_format={"type": "json_object"},
                max_tokens=150,
                temperature=0.1,
            )
            data = json_mod.loads(resp.choices[0].message.content)
            numero = data.get("numero")
            nom_lu = data.get("nom_lu", "")

            if numero and 1 <= numero <= len(self.students):
                eleve = self.students[numero - 1]["nom"]
                # Validation croisée (comme le script)
                eleve_valide = self._validate_gpt_choice(nom_lu, eleve)
                return eleve_valide, nom_lu
            else:
                return None, nom_lu

        except Exception as e:
            logger.error(f"[OCR] Erreur GPT-4V: {e}")
            return None, ""

    def _validate_gpt_choice(self, nom_lu: str, eleve_choisi: str) -> str:
        """
        Vérifie la cohérence du choix GPT avec le nom lu.
        Corrige si le nom lu correspond nettement mieux à un autre élève.
        """
        if not nom_lu or not eleve_choisi:
            return eleve_choisi

        nom_upper = self._normalize_text(nom_lu)
        ratio_choisi = SequenceMatcher(
            None, nom_upper, self._normalize_text(eleve_choisi)
        ).ratio()

        meilleur_nom = None
        meilleur_ratio = 0.0
        for s in self.students:
            ratio = SequenceMatcher(
                None, nom_upper, self._normalize_text(s['nom'])
            ).ratio()
            if ratio > meilleur_ratio:
                meilleur_ratio = ratio
                meilleur_nom = s['nom']

        if meilleur_nom and meilleur_nom != eleve_choisi and meilleur_ratio > ratio_choisi + 0.15:
            logger.info(f"[OCR] Correction: GPT={eleve_choisi} → {meilleur_nom} "
                        f"(ratio {meilleur_ratio:.2f} vs {ratio_choisi:.2f})")
            return meilleur_nom

        return eleve_choisi

    # ─────────────────────────────────────────────────────────────────
    #  Matching flou (fallback sans GPT)
    # ─────────────────────────────────────────────────────────────────

    @staticmethod
    def _normalize_text(text: str) -> str:
        """Normalise un texte pour la comparaison (sans accents, majuscules)."""
        if not text:
            return ''
        text = text.upper()
        text = unicodedata.normalize('NFD', text)
        text = ''.join(c for c in text if unicodedata.category(c) != 'Mn')
        return re.sub(r'[^A-Z\s]', '', text).strip()

    def _fuzzy_match(self, nom_ocr: str, seuil: float = 0.50) -> Tuple[Optional[str], float]:
        """Matching flou du nom OCR brut contre la liste CSV."""
        if not nom_ocr:
            return None, 0.0

        nom_upper = self._normalize_text(nom_ocr)
        best_name = None
        best_ratio = 0.0

        for s in self.students:
            ratio = SequenceMatcher(
                None, nom_upper, self._normalize_text(s['nom'])
            ).ratio()
            if ratio > best_ratio:
                best_ratio = ratio
                best_name = s['nom']

        if best_ratio >= seuil:
            return best_name, best_ratio
        return None, best_ratio

    # ─────────────────────────────────────────────────────────────────
    #  Post-correction (adapté du script)
    # ─────────────────────────────────────────────────────────────────

    def _post_correct_assignments(self, assignations: List[str]) -> List[str]:
        """
        Corrige les attributions douteuses.
        Règle: les feuilles d'un même élève sont toujours consécutives.
        Si un élève a des feuilles non-consécutives ET qu'un élève du CSV manque,
        la feuille isolée est réattribuée.
        """
        noms_csv = {s['nom'] for s in self.students}
        noms_trouves = set(assignations)
        manquants = list(noms_csv - noms_trouves)

        if not manquants:
            return assignations

        # Indices par élève
        eleve_indices = {}
        for idx, nom in enumerate(assignations):
            eleve_indices.setdefault(nom, []).append(idx)

        corrections = {}
        for nom, indices in eleve_indices.items():
            if len(indices) < 2:
                continue
            # Groupes consécutifs
            groupes = [[indices[0]]]
            for j in range(1, len(indices)):
                if indices[j] == indices[j - 1] + 1:
                    groupes[-1].append(indices[j])
                else:
                    groupes.append([indices[j]])

            if len(groupes) > 1 and manquants:
                groupes.sort(key=len)
                for groupe_suspect in groupes[:-1]:
                    if manquants:
                        nouveau = manquants.pop(0)
                        for idx in groupe_suspect:
                            corrections[idx] = (nom, nouveau)

        if corrections:
            logger.info(f"[POST-CORRECTION] {len(corrections)} feuille(s) corrigée(s)")
            for idx in sorted(corrections):
                ancien, nouveau = corrections[idx]
                assignations[idx] = nouveau
                logger.info(f"  Feuille {idx + 1}: {ancien} → {nouveau}")

        return assignations

    # ─────────────────────────────────────────────────────────────────
    #  Traitement des annexes
    # ─────────────────────────────────────────────────────────────────

    def _process_annexes(self, annexe_path: str) -> Dict[str, List[np.ndarray]]:
        """
        OCR chaque page d'annexe pour identifier l'élève, puis groupe par élève.

        Returns:
            Dict {nom_eleve: [image_annexe_1, image_annexe_2, ...]}
        """
        logger.info(f"[ANNEXES] Traitement de {annexe_path}")

        doc = fitz.open(annexe_path)
        nb_pages = doc.page_count
        logger.info(f"[ANNEXES] {nb_pages} pages à traiter")

        annexes_par_eleve: Dict[str, List[np.ndarray]] = {}
        matched = 0
        unmatched = 0

        for page_idx in range(nb_pages):
            logger.info(f"[ANNEXES] Page {page_idx + 1}/{nb_pages} ...", )

            img = self._rasterize_page(doc, page_idx, self.dpi_render)
            h = img.shape[0]

            # Extraire l'en-tête (top 25%)
            header = img[:int(h * 0.25), :]

            # OCR avec prompt CMEN_V2 (format annexes)
            eleve, nom_lu = self._ocr_identify_student(header, header_format='CMEN_V2')

            if not eleve:
                # Fallback flou
                eleve, ratio = self._fuzzy_match(nom_lu)
                if eleve:
                    logger.info(f"  → {eleve} (flou {ratio:.0%}, lu: \"{nom_lu}\")")
                else:
                    logger.warning(f"  → INCONNU (lu: \"{nom_lu}\")")
                    unmatched += 1
                    continue

            logger.info(f"  → {eleve}")
            annexes_par_eleve.setdefault(eleve, []).append(img)
            matched += 1

        doc.close()
        logger.info(f"[ANNEXES] Terminé: {matched} matchées, {unmatched} non matchées")
        return annexes_par_eleve

    # ─────────────────────────────────────────────────────────────────
    #  Assemblage PDF A4 par élève
    # ─────────────────────────────────────────────────────────────────

    @staticmethod
    def _image_to_pdf_page(doc: fitz.Document, image: np.ndarray):
        """
        Ajoute une image numpy comme page A4 dans le document PDF.
        Pattern issu de PDFFlattener.flatten_copy().
        """
        # Encode en PNG
        _, png_buf = cv2.imencode('.png', image)
        png_bytes = png_buf.tobytes()

        # Ouvrir comme image fitz
        img_doc = fitz.open(stream=png_bytes, filetype='png')
        rect = img_doc[0].rect
        pdfbytes = img_doc.convert_to_pdf()
        img_doc.close()

        # Insérer comme page PDF
        img_pdf = fitz.open("pdf", pdfbytes)
        page = doc.new_page(width=rect.width, height=rect.height)
        page.show_pdf_page(rect, img_pdf, 0)
        img_pdf.close()

    @staticmethod
    def _safe_filename(nom: str) -> str:
        """Convertit un nom en nom de fichier valide."""
        return "".join(
            c if c.isalnum() or c in (" ", "-", "_") else "_"
            for c in nom
        ).strip()

    # ─────────────────────────────────────────────────────────────────
    #  Méthode principale
    # ─────────────────────────────────────────────────────────────────

    def generate(self, pdf_paths: List[str],
                 annexe_path: str = None,
                 output_dir: str = None) -> dict:
        """
        Génère un PDF A4 par élève.

        Args:
            pdf_paths: Liste de chemins vers les PDFs source (A3 ou A4).
            annexe_path: Chemin optionnel vers le PDF des annexes.
            output_dir: Répertoire de sortie pour les PDFs. Si None, retourne
                        les bytes dans le résultat.

        Returns:
            dict avec clés:
                - student_pdfs: Dict[nom, bytes] si output_dir is None
                - generated_count: int
                - failed_count: int
                - annexes_matched: int
                - annexes_unmatched: int
                - missing_students: list[str]
        """
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)

        # ═══════════════════════════════════════════════════════════
        #  PHASE 1: Identification OCR de chaque feuille
        # ═══════════════════════════════════════════════════════════
        logger.info("=" * 55)
        logger.info("PHASE 1: Identification des élèves (OCR)")
        logger.info("=" * 55)

        # Collecter toutes les feuilles de tous les PDFs
        all_sheets = []  # (pdf_path, sheet_index, recto_page_idx)

        for pdf_path in pdf_paths:
            doc = fitz.open(pdf_path)
            is_a3 = self._is_a3(doc)
            nb_pages = doc.page_count

            if is_a3:
                # Chaque feuille = 2 pages A3 (recto + verso)
                for i in range(0, nb_pages, 2):
                    all_sheets.append((pdf_path, len(all_sheets), i))
            else:
                logger.info(f"[SKIP] {pdf_path}: format A4, non traité dans le flux A3")
                # Les PDFs A4 non-annexes sont ignorés dans ce service
            doc.close()

        nb_feuilles = len(all_sheets)
        logger.info(f"Total: {nb_feuilles} feuilles A3 à traiter")

        assignations = []
        eleve_precedent = None

        for sheet_idx, (pdf_path, _, recto_idx) in enumerate(all_sheets):
            doc = fitz.open(pdf_path)
            logger.info(f"  Feuille {sheet_idx + 1}/{nb_feuilles} "
                        f"({os.path.basename(pdf_path)}, page {recto_idx + 1})...")

            # Rasteriser le recto en basse résolution pour l'OCR
            img_recto = self._rasterize_page(doc, recto_idx, self.dpi_ocr)
            doc.close()

            # Extraire la moitié droite (P1 avec en-tête), zone en-tête (top 25%)
            w = img_recto.shape[1]
            h = img_recto.shape[0]
            header = img_recto[:int(h * 0.25), w // 2:]

            # OCR
            eleve, nom_lu = self._ocr_identify_student(header, header_format='CCYC')

            if eleve:
                # _validate_gpt_choice already called inside _ocr_identify_student
                logger.info(f"    → {eleve} (lu: \"{nom_lu}\")")
                eleve_precedent = eleve
            else:
                # Fallback flou
                eleve_flou, ratio = self._fuzzy_match(nom_lu)
                if eleve_flou:
                    eleve = eleve_flou
                    logger.info(f"    → {eleve} (flou {ratio:.0%}, lu: \"{nom_lu}\")")
                    eleve_precedent = eleve
                else:
                    eleve = eleve_precedent or "INCONNU"
                    logger.info(f"    → (suite de {eleve}, lu: \"{nom_lu}\")")

            assignations.append(eleve)
            del img_recto

        # ═══════════════════════════════════════════════════════════
        #  PHASE 2: Post-correction
        # ═══════════════════════════════════════════════════════════
        logger.info("=" * 55)
        logger.info("PHASE 2: Vérification et correction")
        logger.info("=" * 55)

        assignations = self._post_correct_assignments(assignations)

        noms_csv = {s['nom'] for s in self.students}
        noms_trouves = set(assignations)
        manquants = list(noms_csv - noms_trouves)

        logger.info(f"  Élèves identifiés: {len(noms_trouves)}")
        if manquants:
            logger.warning(f"  Élèves manquants: {manquants}")
        else:
            logger.info(f"  Tous les {len(noms_csv)} élèves du CSV sont présents")

        # ═══════════════════════════════════════════════════════════
        #  PHASE 2.5: Traitement annexes (si fourni)
        # ═══════════════════════════════════════════════════════════
        annexes_par_eleve: Dict[str, List[np.ndarray]] = {}
        annexes_matched = 0
        annexes_unmatched = 0

        if annexe_path and os.path.exists(annexe_path):
            logger.info("=" * 55)
            logger.info("PHASE 2.5: Traitement des annexes")
            logger.info("=" * 55)
            annexes_par_eleve = self._process_annexes(annexe_path)
            annexes_matched = sum(len(v) for v in annexes_par_eleve.values())
            # Count total pages - matched = unmatched
            doc_ann = fitz.open(annexe_path)
            annexes_unmatched = doc_ann.page_count - annexes_matched
            doc_ann.close()

        # ═══════════════════════════════════════════════════════════
        #  PHASE 3: Découpe A3→A4 et génération des PDF
        # ═══════════════════════════════════════════════════════════
        logger.info("=" * 55)
        logger.info("PHASE 3: Découpe A3→A4 et génération des PDF")
        logger.info("=" * 55)

        # {nom: [images_a4]}
        eleves_pages: OrderedDict[str, List[np.ndarray]] = OrderedDict()

        for sheet_idx, (pdf_path, _, recto_idx) in enumerate(all_sheets):
            nom = assignations[sheet_idx]
            doc = fitz.open(pdf_path)
            nb_pages = doc.page_count

            logger.info(f"  Feuille {sheet_idx + 1}/{nb_feuilles} → {nom} ...")

            # Rasteriser à haute résolution
            img_recto = self._rasterize_page(doc, recto_idx, self.dpi_render)
            verso_idx = recto_idx + 1
            img_verso = (
                self._rasterize_page(doc, verso_idx, self.dpi_render)
                if verso_idx < nb_pages else None
            )
            doc.close()

            if nom not in eleves_pages:
                eleves_pages[nom] = []

            # Recto: DROITE = P1, GAUCHE = P4
            recto_gauche, recto_droite = self._split_a3_to_a4(img_recto)
            p1 = recto_droite
            p4 = recto_gauche

            if img_verso is not None:
                # Verso: GAUCHE = P2, DROITE = P3
                verso_gauche, verso_droite = self._split_a3_to_a4(img_verso)
                p2 = verso_gauche
                p3 = verso_droite
                eleves_pages[nom].extend([p1, p2, p3, p4])
            else:
                eleves_pages[nom].extend([p1, p4])

            del img_recto
            if img_verso is not None:
                del img_verso

        # ═══════════════════════════════════════════════════════════
        #  Vérification + assemblage PDF
        # ═══════════════════════════════════════════════════════════
        logger.info("=" * 55)
        logger.info(f"GÉNÉRATION DE {len(eleves_pages)} FICHIERS PDF")
        logger.info("=" * 55)

        student_pdfs: Dict[str, bytes] = {}
        # Maps sanitized filename → original student name (for the view)
        filename_to_student: Dict[str, str] = {}
        generated = 0
        failed = 0

        for nom, pages in eleves_pages.items():
            try:
                doc = fitz.open()

                # Pages de la copie
                for img in pages:
                    self._image_to_pdf_page(doc, img)

                # Pages annexes (si disponibles)
                annexe_imgs = annexes_par_eleve.get(nom, [])
                for ann_img in annexe_imgs:
                    self._image_to_pdf_page(doc, ann_img)

                pdf_bytes = doc.write()
                doc.close()

                nb_total = len(pages) + len(annexe_imgs)
                ann_info = f" + {len(annexe_imgs)} annexe(s)" if annexe_imgs else ""

                if output_dir:
                    filename = f"{self._safe_filename(nom)}.pdf"
                    filepath = os.path.join(output_dir, filename)
                    with open(filepath, 'wb') as f:
                        f.write(pdf_bytes)
                    filename_to_student[filename] = nom
                    logger.info(f"  [OK] {filename} — {nb_total} pages A4{ann_info}")
                else:
                    student_pdfs[nom] = pdf_bytes
                    logger.info(f"  [OK] {nom} — {nb_total} pages A4{ann_info}")

                generated += 1

            except Exception as e:
                logger.error(f"  [ERREUR] {nom}: {e}")
                failed += 1

        logger.info(f"\nTerminé: {generated} PDFs générés, {failed} échecs")

        return {
            'student_pdfs': student_pdfs if not output_dir else {},
            'filename_to_student': filename_to_student,
            'generated_count': generated,
            'failed_count': failed,
            'annexes_matched': annexes_matched,
            'annexes_unmatched': annexes_unmatched,
            'missing_students': manquants,
        }
