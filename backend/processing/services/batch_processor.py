"""
Batch A3 PDF Processor - Traitement complet d'un scan batch A3 recto/verso.

Ce service gère le workflow complet:
1. Détection format A3 (ratio > 1.2)
2. Découpage A3 → 2×A4 par page
3. Réordonnancement par feuille: A3#1=(P1,P4), A3#2=(P2,P3) → ordre final 1,2,3,4
4. Segmentation par élève via OCR + matching CSV
5. Création d'une Copy par élève avec toutes ses pages

Règles de reconstruction:
- Chaque feuille élève = 2 pages A3 consécutives = 4 pages A4
- A3#1 contient P1 (droite) et P4 (gauche)
- A3#2 contient P2 (gauche) et P3 (droite)
- Ordre final par feuille: P1, P2, P3, P4
- Un élève peut avoir plusieurs feuilles (multiples de 4 pages A4)
"""
import fitz  # PyMuPDF
import cv2
import numpy as np
import os
import tempfile
import logging
import unicodedata
import re
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from django.conf import settings
from django.db import transaction

logger = logging.getLogger(__name__)

# Seuil pour détecter un format A3 (landscape)
A3_ASPECT_RATIO_THRESHOLD = 1.2


@dataclass
class StudentMatch:
    """Résultat du matching OCR → CSV."""
    student_id: int
    last_name: str
    first_name: str
    date_of_birth: str
    email: str
    confidence: float
    ocr_text: str


@dataclass
class PageInfo:
    """Information sur une page A4 extraite."""
    page_number: int  # Numéro dans le batch (1-based)
    sheet_number: int  # Numéro de feuille (1-based)
    position_in_sheet: int  # Position dans la feuille (1-4)
    image: np.ndarray
    image_path: Optional[str] = None


@dataclass
class StudentCopy:
    """Copie d'un élève avec toutes ses pages."""
    student_match: Optional[StudentMatch]
    pages: List[PageInfo]
    needs_review: bool = False
    review_reason: str = ""
    header_crops: List[str] = None  # Chemins vers les crops d'en-tête
    
    def __post_init__(self):
        if self.header_crops is None:
            self.header_crops = []


class BatchA3Processor:
    """
    Processeur de batch A3 recto/verso avec segmentation par élève.
    """

    def __init__(self, dpi: int = 200, csv_path: Optional[str] = None):
        """
        Args:
            dpi: Résolution pour la rasterisation (200-300 recommandé)
            csv_path: Chemin vers le CSV des élèves (whitelist)
        """
        self.dpi = dpi
        self.csv_path = csv_path
        self.students_whitelist: List[Dict] = []
        
        if csv_path:
            self._load_csv_whitelist(csv_path)

    def _load_csv_whitelist(self, csv_path: str) -> None:
        """Charge le CSV des élèves comme whitelist pour l'OCR."""
        import csv
        
        self.students_whitelist = []
        
        try:
            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # Normaliser les noms de colonnes
                    student = {}
                    for key, value in row.items():
                        if not key or not value:
                            continue
                        key_lower = key.strip().lower()
                        value = value.strip()
                        
                        if 'élève' in key_lower or 'eleve' in key_lower:
                            # Format "NOM PRENOM"
                            parts = value.split(' ', 1)
                            student['last_name'] = parts[0] if parts else ''
                            student['first_name'] = parts[1] if len(parts) > 1 else ''
                            student['full_name'] = value
                        elif 'né' in key_lower or 'naissance' in key_lower:
                            student['date_of_birth'] = value
                        elif 'mail' in key_lower:
                            student['email'] = value
                        elif 'classe' in key_lower:
                            student['class_name'] = value
                    
                    if student.get('last_name'):
                        self.students_whitelist.append(student)
            
            logger.info(f"Loaded {len(self.students_whitelist)} students from CSV whitelist")
            
        except Exception as e:
            logger.error(f"Failed to load CSV whitelist: {e}")

    def _normalize_text(self, text: str) -> str:
        """Normalise le texte pour le matching (insensible casse, accents, tirets)."""
        if not text:
            return ""
        # Supprimer les accents
        text = unicodedata.normalize('NFD', text)
        text = ''.join(c for c in text if unicodedata.category(c) != 'Mn')
        # Minuscules
        text = text.lower()
        # Supprimer tirets et underscores (pas remplacer par espace)
        text = re.sub(r'[-_]+', '', text)
        # Normaliser espaces multiples
        text = re.sub(r'\s+', ' ', text)
        return text.strip()

    def _normalize_date(self, date_str: str) -> str:
        """Normalise une date pour le matching (tolérance aux séparateurs)."""
        if not date_str:
            return ""
        # Extraire les chiffres
        digits = re.findall(r'\d+', date_str)
        if len(digits) >= 3:
            # Assumer dd/mm/yyyy ou dd-mm-yyyy
            return f"{digits[0]:0>2}/{digits[1]:0>2}/{digits[2]}"
        return date_str

    def _match_student(self, ocr_name: str, ocr_date: str) -> Optional[StudentMatch]:
        """
        Fait le matching OCR → CSV avec scoring fuzzy.
        
        Args:
            ocr_name: Nom extrait par OCR
            ocr_date: Date de naissance extraite par OCR
            
        Returns:
            StudentMatch si trouvé avec confiance suffisante, None sinon
        """
        if not self.students_whitelist:
            return None
        
        ocr_name_norm = self._normalize_text(ocr_name)
        ocr_date_norm = self._normalize_date(ocr_date)
        
        best_match = None
        best_score = 0.0
        
        for student in self.students_whitelist:
            score = 0.0
            
            # Score nom (fuzzy)
            student_name_norm = self._normalize_text(
                f"{student.get('last_name', '')} {student.get('first_name', '')}"
            )
            
            # Calcul de similarité simple (Jaccard sur mots)
            ocr_words = set(ocr_name_norm.split())
            student_words = set(student_name_norm.split())
            
            if ocr_words and student_words:
                intersection = len(ocr_words & student_words)
                union = len(ocr_words | student_words)
                name_score = intersection / union if union > 0 else 0
                score += name_score * 0.6  # 60% du score
            
            # Score date (exact ou proche)
            student_date_norm = self._normalize_date(student.get('date_of_birth', ''))
            if ocr_date_norm and student_date_norm:
                if ocr_date_norm == student_date_norm:
                    score += 0.4  # 40% du score
                elif ocr_date_norm[:5] == student_date_norm[:5]:  # Même jour/mois
                    score += 0.2
            
            if score > best_score:
                best_score = score
                best_match = StudentMatch(
                    student_id=0,  # Will be set later from DB
                    last_name=student.get('last_name', ''),
                    first_name=student.get('first_name', ''),
                    date_of_birth=student.get('date_of_birth', ''),
                    email=student.get('email', ''),
                    confidence=score,
                    ocr_text=ocr_name
                )
        
        # Seuil de confiance minimum
        if best_match and best_match.confidence >= 0.5:
            return best_match
        
        return None

    def is_a3_format(self, pdf_path: str) -> bool:
        """Détecte si le PDF contient des pages A3 (landscape avec ratio > 1.2)."""
        try:
            doc = fitz.open(pdf_path)
            if doc.page_count == 0:
                doc.close()
                return False
            
            page = doc.load_page(0)
            rect = page.rect
            width, height = rect.width, rect.height
            doc.close()
            
            ratio = width / height if height > 0 else 0
            is_a3 = ratio > A3_ASPECT_RATIO_THRESHOLD
            
            logger.info(f"PDF format: width={width:.0f}, height={height:.0f}, ratio={ratio:.2f}, is_A3={is_a3}")
            return is_a3
            
        except Exception as e:
            logger.error(f"Error detecting PDF format: {e}")
            return False

    def _rasterize_page(self, doc: fitz.Document, page_idx: int) -> np.ndarray:
        """Rasterise une page PDF en image numpy BGR, avec correction de rotation."""
        page = doc.load_page(page_idx)
        
        # Rasteriser avec le DPI spécifié
        mat = fitz.Matrix(self.dpi / 72, self.dpi / 72)
        pix = page.get_pixmap(matrix=mat)
        
        img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
        
        if pix.n == 3:
            img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
        elif pix.n == 4:
            img = cv2.cvtColor(img, cv2.COLOR_RGBA2BGR)
        
        # Corriger la rotation selon les métadonnées PDF
        # La rotation PDF indique comment la page doit être affichée
        # On doit appliquer la rotation inverse pour obtenir l'image correcte
        rotation = page.rotation
        if rotation == 90:
            img = cv2.rotate(img, cv2.ROTATE_90_CLOCKWISE)
        elif rotation == 180:
            img = cv2.rotate(img, cv2.ROTATE_180)
        elif rotation == 270:
            img = cv2.rotate(img, cv2.ROTATE_90_COUNTERCLOCKWISE)
        
        # Assurer le format paysage A3
        height, width = img.shape[:2]
        if height > width:
            img = cv2.rotate(img, cv2.ROTATE_90_CLOCKWISE)
        
        return img

    def _split_a3_to_a4(self, a3_image: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        Découpe une image A3 en 2 images A4 (gauche et droite).
        
        Returns:
            Tuple (left_a4, right_a4)
        """
        height, width = a3_image.shape[:2]
        mid_x = width // 2
        
        left_a4 = a3_image[:, :mid_x]
        right_a4 = a3_image[:, mid_x:]
        
        return left_a4, right_a4

    def _extract_header_region(self, page_image: np.ndarray) -> np.ndarray:
        """Extrait la région d'en-tête (top 20% de la page)."""
        height = page_image.shape[0]
        header_height = int(height * 0.20)
        return page_image[:header_height, :]

    def _ocr_header(self, header_image: np.ndarray) -> Tuple[str, str]:
        """
        Extrait le nom et la date de naissance de l'en-tête via OCR.
        Format attendu: en-tête CMEN v2 avec champs structurés.
        
        Returns:
            Tuple (nom_complet, date_naissance)
        """
        try:
            import pytesseract
            
            # Prétraitement pour OCR
            gray = cv2.cvtColor(header_image, cv2.COLOR_BGR2GRAY)
            
            # Améliorer le contraste
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            enhanced = clahe.apply(gray)
            
            # Binarisation adaptative pour mieux gérer les variations
            binary = cv2.adaptiveThreshold(
                enhanced, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                cv2.THRESH_BINARY, 11, 2
            )
            
            # OCR avec configuration optimisée pour texte structuré
            config = '--psm 6 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789/-. '
            text = pytesseract.image_to_string(binary, lang='fra', config='--psm 6')
            
            logger.debug(f"OCR raw text: {text[:200]}")
            
            name = ""
            first_name = ""
            date = ""
            
            lines = text.split('\n')
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                # Chercher "Nom de famille" suivi du nom
                if 'nom' in line.lower() and 'famille' in line.lower():
                    # Le nom est souvent sur la même ligne après ":"
                    parts = line.split(':')
                    if len(parts) > 1:
                        name_part = parts[1].strip()
                        # Extraire les lettres majuscules
                        name_chars = re.findall(r'[A-ZÉÈÊËÀÂÄÙÛÜÔÖÎÏÇ]', name_part)
                        if name_chars:
                            name = ''.join(name_chars)
                
                # Chercher "Prénom"
                elif 'prénom' in line.lower() or 'prenom' in line.lower():
                    parts = line.split(':')
                    if len(parts) > 1:
                        first_part = parts[1].strip()
                        first_chars = re.findall(r'[A-ZÉÈÊËÀÂÄÙÛÜÔÖÎÏÇ]', first_part)
                        if first_chars:
                            first_name = ''.join(first_chars)
                
                # Chercher une date (format dd/mm/yyyy ou similaire)
                date_match = re.search(r'(\d{1,2})[/\-\.](\d{1,2})[/\-\.](\d{2,4})', line)
                if date_match:
                    d, m, y = date_match.groups()
                    date = f"{d}/{m}/{y}"
            
            # Si on n'a pas trouvé via les labels, chercher des patterns
            if not name:
                # Chercher des séquences de lettres majuscules isolées (cases remplies)
                all_caps = re.findall(r'\b[A-Z]{2,}\b', text)
                if all_caps:
                    # Prendre le premier groupe significatif
                    for caps in all_caps:
                        if len(caps) >= 3 and caps not in ['CMEN', 'NEOPTEC', 'CONSIGNES']:
                            name = caps
                            break
            
            if not date:
                # Chercher n'importe quelle date dans le texte
                date_match = re.search(r'(\d{1,2})[/\-\.](\d{1,2})[/\-\.](\d{2,4})', text)
                if date_match:
                    d, m, y = date_match.groups()
                    date = f"{d}/{m}/{y}"
            
            # Combiner nom et prénom
            full_name = f"{name} {first_name}".strip() if name else ""
            
            logger.info(f"OCR extracted: name='{full_name}', date='{date}'")
            return full_name, date
            
        except Exception as e:
            logger.warning(f"OCR failed: {e}")
            return "", ""

    def _detect_header_on_page(self, page_image: np.ndarray) -> bool:
        """
        Détecte si la page contient un en-tête (marqueur de début de copie).
        Utilise la détection de zones de texte structurées.
        """
        try:
            from processing.services.vision import HeaderDetector
            
            # Sauvegarder temporairement pour le détecteur
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
                temp_path = f.name
                cv2.imwrite(temp_path, page_image)
            
            try:
                detector = HeaderDetector()
                has_header = detector.detect_header(temp_path)
                return has_header
            finally:
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
                    
        except Exception as e:
            logger.warning(f"Header detection failed: {e}")
            # Fallback: chercher des lignes horizontales dans le top 20%
            return self._fallback_header_detection(page_image)

    def _fallback_header_detection(self, page_image: np.ndarray) -> bool:
        """Détection de fallback basée sur la densité de texte en haut."""
        header = self._extract_header_region(page_image)
        gray = cv2.cvtColor(header, cv2.COLOR_BGR2GRAY)
        _, binary = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY_INV)
        
        # Compter les pixels noirs (texte)
        text_density = np.sum(binary > 0) / binary.size
        
        # Un en-tête a généralement plus de texte
        return text_density > 0.02

    def process_batch_pdf(self, pdf_path: str, exam_id: str) -> List[StudentCopy]:
        """
        Traite un PDF batch A3 et retourne les copies segmentées par élève.
        
        Args:
            pdf_path: Chemin vers le PDF batch
            exam_id: ID de l'examen
            
        Returns:
            Liste de StudentCopy avec les pages ordonnées
        """
        if not self.is_a3_format(pdf_path):
            raise ValueError("Le PDF n'est pas au format A3")
        
        doc = fitz.open(pdf_path)
        total_a3_pages = doc.page_count
        
        logger.info(f"Processing batch PDF: {total_a3_pages} A3 pages")
        
        # Vérifier que le nombre de pages A3 est pair
        if total_a3_pages % 2 != 0:
            logger.warning(f"Odd number of A3 pages ({total_a3_pages}), last page may be incomplete")
        
        # Étape 1: Extraire toutes les pages A4 avec réordonnancement
        all_a4_pages: List[PageInfo] = []
        sheet_number = 0
        
        for a3_idx in range(0, total_a3_pages, 2):
            sheet_number += 1
            
            # A3 #1 (recto): contient P1 (droite) et P4 (gauche)
            a3_1_img = self._rasterize_page(doc, a3_idx)
            left_1, right_1 = self._split_a3_to_a4(a3_1_img)
            
            p1 = PageInfo(
                page_number=a3_idx * 2 + 1,
                sheet_number=sheet_number,
                position_in_sheet=1,
                image=right_1  # P1 est à droite
            )
            p4 = PageInfo(
                page_number=a3_idx * 2 + 4,
                sheet_number=sheet_number,
                position_in_sheet=4,
                image=left_1  # P4 est à gauche
            )
            
            # A3 #2 (verso): contient P2 (gauche) et P3 (droite)
            if a3_idx + 1 < total_a3_pages:
                a3_2_img = self._rasterize_page(doc, a3_idx + 1)
                left_2, right_2 = self._split_a3_to_a4(a3_2_img)
                
                p2 = PageInfo(
                    page_number=a3_idx * 2 + 2,
                    sheet_number=sheet_number,
                    position_in_sheet=2,
                    image=left_2  # P2 est à gauche
                )
                p3 = PageInfo(
                    page_number=a3_idx * 2 + 3,
                    sheet_number=sheet_number,
                    position_in_sheet=3,
                    image=right_2  # P3 est à droite
                )
            else:
                # Page verso manquante
                p2 = None
                p3 = None
            
            # Ajouter dans l'ordre correct: P1, P2, P3, P4
            all_a4_pages.append(p1)
            if p2:
                all_a4_pages.append(p2)
            if p3:
                all_a4_pages.append(p3)
            all_a4_pages.append(p4)
        
        doc.close()
        
        logger.info(f"Extracted {len(all_a4_pages)} A4 pages from {total_a3_pages} A3 pages")
        
        # Étape 2: Segmenter par élève
        student_copies = self._segment_by_student(all_a4_pages, exam_id)
        
        return student_copies

    def _is_same_student(self, student1: Optional[StudentMatch], student2: Optional[StudentMatch]) -> bool:
        """
        Vérifie si deux StudentMatch représentent le même élève.
        Utilisé pour fusionner les feuilles multiples d'un même élève.
        """
        if student1 is None or student2 is None:
            return False
        
        # Comparaison par email (identifiant unique)
        if student1.email and student2.email:
            return student1.email.lower() == student2.email.lower()
        
        # Fallback: comparaison par nom + prénom normalisés
        name1 = self._normalize_text(f"{student1.last_name} {student1.first_name}")
        name2 = self._normalize_text(f"{student2.last_name} {student2.first_name}")
        return name1 == name2

    def _segment_by_student(self, pages: List[PageInfo], exam_id: str) -> List[StudentCopy]:
        """
        Segmente les pages par élève en détectant les en-têtes.
        
        RÈGLE CRITIQUE (multi-feuilles):
        - Chaque feuille (4 pages A4) commence par une page avec en-tête.
        - Si l'en-tête détecté correspond AU MÊME élève que la copie courante,
          on CONCATÈNE les 4 pages à la copie existante.
        - Si l'en-tête correspond à un AUTRE élève, on ferme la copie courante
          et on en démarre une nouvelle.
        - Si l'en-tête est illisible/incertain, on crée une copie en STAGING.
        
        Résultat: 1 Copy par élève, même si l'élève a rendu plusieurs feuilles.
        """
        student_copies: List[StudentCopy] = []
        current_pages: List[PageInfo] = []
        current_student: Optional[StudentMatch] = None
        current_header_crops: List[str] = []  # Pour stocker les crops d'en-tête
        
        # Créer le dossier de sortie
        output_dir = Path(settings.MEDIA_ROOT) / 'batch_processing' / exam_id
        output_dir.mkdir(parents=True, exist_ok=True)
        headers_dir = output_dir / 'headers'
        headers_dir.mkdir(parents=True, exist_ok=True)
        
        sheet_count = 0  # Compteur de feuilles pour le rapport
        
        for i, page in enumerate(pages):
            is_first_of_sheet = page.position_in_sheet == 1
            
            if is_first_of_sheet:
                sheet_count += 1
                
                # Détecter si c'est un nouvel élève
                has_header = self._detect_header_on_page(page.image)
                
                if has_header:
                    # Extraire et sauvegarder l'en-tête
                    header_region = self._extract_header_region(page.image)
                    header_filename = f"header_sheet_{sheet_count:04d}.png"
                    header_path = headers_dir / header_filename
                    cv2.imwrite(str(header_path), header_region)
                    
                    # OCR sur l'en-tête
                    ocr_name, ocr_date = self._ocr_header(header_region)
                    
                    # Matcher avec le CSV
                    new_student = self._match_student(ocr_name, ocr_date)
                    
                    # LOGIQUE MULTI-FEUILLES: vérifier si c'est le même élève
                    if current_pages and self._is_same_student(current_student, new_student):
                        # MÊME ÉLÈVE: on continue à accumuler les pages
                        logger.info(f"Sheet {sheet_count}: Same student ({new_student.last_name if new_student else 'unknown'}), concatenating pages")
                        current_header_crops.append(str(header_path.relative_to(settings.MEDIA_ROOT)))
                    else:
                        # NOUVEL ÉLÈVE ou premier élève
                        if current_pages:
                            # Sauvegarder la copie précédente
                            student_copies.append(StudentCopy(
                                student_match=current_student,
                                pages=current_pages.copy(),
                                needs_review=current_student is None,
                                review_reason="No student match found" if current_student is None else "",
                                header_crops=current_header_crops.copy()
                            ))
                            current_pages = []
                            current_header_crops = []
                        
                        current_student = new_student
                        current_header_crops = [str(header_path.relative_to(settings.MEDIA_ROOT))]
                        
                        if new_student:
                            logger.info(f"Sheet {sheet_count}: New student detected: {new_student.last_name} {new_student.first_name} (confidence: {new_student.confidence:.2f})")
                        else:
                            logger.warning(f"Sheet {sheet_count}: Could not match student from OCR: name='{ocr_name}', date='{ocr_date}'")
            
            # Sauvegarder l'image de la page
            page_filename = f"page_{i+1:04d}.png"
            page_path = output_dir / page_filename
            cv2.imwrite(str(page_path), page.image)
            page.image_path = str(page_path.relative_to(settings.MEDIA_ROOT))
            
            current_pages.append(page)
        
        # Ajouter la dernière copie
        if current_pages:
            student_copies.append(StudentCopy(
                student_match=current_student,
                pages=current_pages.copy(),
                needs_review=current_student is None,
                review_reason="No student match found" if current_student is None else "",
                header_crops=current_header_crops.copy()
            ))
        
        # Vérifier les invariants et générer le rapport
        anomalies = []
        for idx, copy in enumerate(student_copies):
            if len(copy.pages) % 4 != 0:
                copy.needs_review = True
                copy.review_reason = f"Page count not multiple of 4: {len(copy.pages)}"
                anomalies.append(f"Copy {idx+1}: {len(copy.pages)} pages (not multiple of 4)")
                logger.warning(f"Copy {idx+1} has {len(copy.pages)} pages (not multiple of 4)")
        
        # Rapport de segmentation
        logger.info(f"=== SEGMENTATION REPORT ===")
        logger.info(f"Total sheets processed: {sheet_count}")
        logger.info(f"Total A4 pages: {len(pages)}")
        logger.info(f"Students detected: {len(student_copies)}")
        for idx, copy in enumerate(student_copies):
            student_name = f"{copy.student_match.last_name} {copy.student_match.first_name}" if copy.student_match else "UNKNOWN"
            sheets_count = len(copy.pages) // 4
            logger.info(f"  Copy {idx+1}: {student_name} - {len(copy.pages)} pages ({sheets_count} sheets), needs_review={copy.needs_review}")
        if anomalies:
            logger.warning(f"Anomalies: {anomalies}")
        logger.info(f"=== END REPORT ===")
        
        return student_copies

    @transaction.atomic
    def create_copies_from_batch(self, exam, student_copies: List[StudentCopy]) -> List:
        """
        Crée les objets Copy en base de données à partir des copies segmentées.
        
        Args:
            exam: Instance Exam
            student_copies: Liste de StudentCopy
            
        Returns:
            Liste des Copy créées
        """
        from exams.models import Copy, Booklet
        from students.models import Student
        import uuid
        
        created_copies = []
        
        for sc in student_copies:
            # Trouver ou créer le Student
            student = None
            if sc.student_match:
                student = Student.objects.filter(
                    email=sc.student_match.email
                ).first()
                
                if not student:
                    # Chercher par nom + date de naissance
                    student = Student.objects.filter(
                        last_name__iexact=sc.student_match.last_name,
                        first_name__iexact=sc.student_match.first_name
                    ).first()
            
            # Créer le Booklet avec les pages
            pages_images = [p.image_path for p in sc.pages if p.image_path]
            
            booklet = Booklet.objects.create(
                exam=exam,
                start_page=1,
                end_page=len(pages_images),
                pages_images=pages_images,
                student_name_guess=f"{sc.student_match.last_name} {sc.student_match.first_name}" if sc.student_match else "Unknown"
            )
            
            # Créer la Copy
            status = Copy.Status.STAGING if sc.needs_review else Copy.Status.READY
            
            copy = Copy.objects.create(
                exam=exam,
                anonymous_id=str(uuid.uuid4())[:8].upper(),
                status=status,
                is_identified=student is not None,
                student=student
            )
            copy.booklets.add(booklet)
            
            created_copies.append(copy)
            
            logger.info(f"Created copy {copy.anonymous_id}: {len(pages_images)} pages, student={student}, status={status}")
        
        return created_copies
