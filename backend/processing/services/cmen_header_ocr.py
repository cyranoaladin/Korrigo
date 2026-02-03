"""
CMEN Header OCR Service - Extraction de NOM, PRÉNOM et DATE DE NAISSANCE.

Ce service est spécialisé pour les en-têtes CMEN v2 avec écriture manuscrite
dans des cases individuelles. Il extrait les 3 champs clés qui forment
la clé primaire d'identification de l'élève.

Structure de l'en-tête CMEN v2:
- Ligne 1: "Nom de famille :" suivi de cases pour les lettres
- Ligne 2: "Prénom(s) :" suivi de cases pour les lettres  
- Ligne 3: "Numéro Inscription :" et "Né(e) le :" avec format JJ/MM/AAAA

Clé primaire: NOM + PRÉNOM + DATE_NAISSANCE
"""
import cv2
import numpy as np
import logging
import re
from dataclasses import dataclass
from typing import List, Optional, Tuple, Dict
from difflib import SequenceMatcher
import unicodedata

logger = logging.getLogger(__name__)


@dataclass
class CMENHeaderField:
    """Champ extrait de l'en-tête CMEN."""
    field_name: str  # 'last_name', 'first_name', 'date_of_birth'
    value: str
    confidence: float
    bbox: Optional[Tuple[int, int, int, int]] = None  # x, y, w, h


@dataclass
class CMENHeaderResult:
    """Résultat complet de l'extraction de l'en-tête CMEN."""
    last_name: str
    first_name: str
    date_of_birth: str
    overall_confidence: float
    fields: List[CMENHeaderField]
    
    def get_primary_key(self) -> str:
        """Retourne la clé primaire normalisée: NOM|PRENOM|DATE."""
        return f"{self.last_name.upper()}|{self.first_name.upper()}|{self.date_of_birth}"


@dataclass
class StudentCSVRecord:
    """Enregistrement d'un élève du fichier CSV."""
    student_id: int
    last_name: str
    first_name: str
    date_of_birth: str
    email: Optional[str] = None
    class_name: Optional[str] = None
    
    def get_primary_key(self) -> str:
        """Retourne la clé primaire normalisée."""
        return f"{self.last_name.upper()}|{self.first_name.upper()}|{self.date_of_birth}"


@dataclass 
class StudentMatchResult:
    """Résultat de la correspondance élève."""
    student: StudentCSVRecord
    confidence: float
    match_details: Dict[str, float]  # Scores par champ


class CMENHeaderOCR:
    """
    Service OCR spécialisé pour les en-têtes CMEN v2.
    
    Extrait NOM, PRÉNOM et DATE DE NAISSANCE des cases manuscrites
    et fait correspondre avec la liste des élèves du CSV.
    """
    
    # Régions approximatives de l'en-tête (en % de la largeur/hauteur)
    REGIONS = {
        'last_name': {'y_start': 0.05, 'y_end': 0.25, 'x_start': 0.25, 'x_end': 0.95},
        'first_name': {'y_start': 0.25, 'y_end': 0.45, 'x_start': 0.15, 'x_end': 0.95},
        'date_of_birth': {'y_start': 0.45, 'y_end': 0.65, 'x_start': 0.55, 'x_end': 0.95},
    }
    
    def __init__(self, debug: bool = False):
        self.debug = debug
        self._tesseract_available = self._check_tesseract()
        self._easyocr_reader = None
        self._paddleocr = None
        
    def _check_tesseract(self) -> bool:
        """Vérifie si Tesseract est disponible."""
        try:
            import pytesseract
            pytesseract.get_tesseract_version()
            return True
        except Exception:
            return False
    
    def _get_easyocr(self):
        """Lazy load EasyOCR."""
        if self._easyocr_reader is None:
            try:
                import easyocr
                self._easyocr_reader = easyocr.Reader(['fr', 'en'], gpu=False)
            except Exception as e:
                logger.warning(f"EasyOCR not available: {e}")
        return self._easyocr_reader
    
    def _get_paddleocr(self):
        """Lazy load PaddleOCR."""
        if self._paddleocr is None:
            try:
                from paddleocr import PaddleOCR
                self._paddleocr = PaddleOCR(use_angle_cls=True, lang='fr', use_gpu=False)
            except Exception as e:
                logger.warning(f"PaddleOCR not available: {e}")
        return self._paddleocr
    
    def preprocess_image(self, image: np.ndarray) -> List[np.ndarray]:
        """
        Prétraitement de l'image avec plusieurs variantes.
        
        Returns:
            Liste d'images prétraitées pour améliorer l'OCR.
        """
        variants = []
        
        # Convertir en niveaux de gris si nécessaire
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()
        
        # Variante 1: Image originale en gris
        variants.append(gray)
        
        # Variante 2: Binarisation Otsu
        _, binary_otsu = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        variants.append(binary_otsu)
        
        # Variante 3: Binarisation adaptative
        binary_adaptive = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
        )
        variants.append(binary_adaptive)
        
        # Variante 4: Débruitage + Otsu
        denoised = cv2.fastNlMeansDenoising(gray, None, 10, 7, 21)
        _, binary_denoised = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        variants.append(binary_denoised)
        
        # Variante 5: Contraste amélioré (CLAHE)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)
        _, binary_enhanced = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        variants.append(binary_enhanced)
        
        return variants
    
    def extract_region(self, image: np.ndarray, region_name: str) -> np.ndarray:
        """
        Extrait une région spécifique de l'en-tête.
        
        Args:
            image: Image de l'en-tête complet
            region_name: 'last_name', 'first_name', ou 'date_of_birth'
            
        Returns:
            Image de la région extraite
        """
        h, w = image.shape[:2]
        region = self.REGIONS[region_name]
        
        x1 = int(w * region['x_start'])
        x2 = int(w * region['x_end'])
        y1 = int(h * region['y_start'])
        y2 = int(h * region['y_end'])
        
        return image[y1:y2, x1:x2]
    
    def ocr_with_tesseract(self, image: np.ndarray, config: str = '') -> Tuple[str, float]:
        """OCR avec Tesseract."""
        if not self._tesseract_available:
            return '', 0.0
        
        try:
            import pytesseract
            
            # Configuration pour écriture manuscrite
            custom_config = f'--oem 3 --psm 7 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789/ {config}'
            
            # Obtenir le texte avec données détaillées
            data = pytesseract.image_to_data(image, config=custom_config, output_type=pytesseract.Output.DICT)
            
            texts = []
            confidences = []
            for i, text in enumerate(data['text']):
                if text.strip():
                    texts.append(text.strip())
                    conf = data['conf'][i]
                    if conf > 0:
                        confidences.append(conf / 100.0)
            
            result_text = ''.join(texts)
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
            
            return result_text, avg_confidence
            
        except Exception as e:
            logger.warning(f"Tesseract OCR failed: {e}")
            return '', 0.0
    
    def ocr_with_easyocr(self, image: np.ndarray) -> Tuple[str, float]:
        """OCR avec EasyOCR."""
        reader = self._get_easyocr()
        if reader is None:
            return '', 0.0
        
        try:
            results = reader.readtext(image, detail=1)
            
            texts = []
            confidences = []
            for bbox, text, conf in results:
                if text.strip():
                    texts.append(text.strip().upper())
                    confidences.append(conf)
            
            result_text = ''.join(texts)
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
            
            return result_text, avg_confidence
            
        except Exception as e:
            logger.warning(f"EasyOCR failed: {e}")
            return '', 0.0
    
    def ocr_with_paddleocr(self, image: np.ndarray) -> Tuple[str, float]:
        """OCR avec PaddleOCR."""
        ocr = self._get_paddleocr()
        if ocr is None:
            return '', 0.0
        
        try:
            results = ocr.ocr(image, cls=True)
            
            if not results or not results[0]:
                return '', 0.0
            
            texts = []
            confidences = []
            for line in results[0]:
                if line and len(line) >= 2:
                    text, conf = line[1]
                    if text.strip():
                        texts.append(text.strip().upper())
                        confidences.append(conf)
            
            result_text = ''.join(texts)
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
            
            return result_text, avg_confidence
            
        except Exception as e:
            logger.warning(f"PaddleOCR failed: {e}")
            return '', 0.0
    
    def extract_field(self, image: np.ndarray, field_name: str) -> CMENHeaderField:
        """
        Extrait un champ spécifique avec consensus multi-moteur.
        
        Args:
            image: Image de l'en-tête complet
            field_name: 'last_name', 'first_name', ou 'date_of_birth'
            
        Returns:
            CMENHeaderField avec la valeur extraite
        """
        # Extraire la région
        region_img = self.extract_region(image, field_name)
        
        # Prétraiter avec plusieurs variantes
        variants = self.preprocess_image(region_img)
        
        # Collecter les résultats de tous les moteurs sur toutes les variantes
        all_results = []
        
        for variant_idx, variant in enumerate(variants):
            # Tesseract
            text, conf = self.ocr_with_tesseract(variant)
            if text:
                all_results.append({'text': text, 'confidence': conf, 'engine': 'tesseract', 'variant': variant_idx})
            
            # EasyOCR (seulement sur quelques variantes pour la performance)
            if variant_idx < 2:
                text, conf = self.ocr_with_easyocr(variant)
                if text:
                    all_results.append({'text': text, 'confidence': conf, 'engine': 'easyocr', 'variant': variant_idx})
            
            # PaddleOCR (seulement sur quelques variantes)
            if variant_idx < 2:
                text, conf = self.ocr_with_paddleocr(variant)
                if text:
                    all_results.append({'text': text, 'confidence': conf, 'engine': 'paddleocr', 'variant': variant_idx})
        
        # Consensus voting
        best_text, best_confidence = self._consensus_vote(all_results, field_name)
        
        # Post-traitement selon le type de champ
        if field_name == 'date_of_birth':
            best_text = self._normalize_date(best_text)
        else:
            best_text = self._normalize_name(best_text)
        
        return CMENHeaderField(
            field_name=field_name,
            value=best_text,
            confidence=best_confidence
        )
    
    def _consensus_vote(self, results: List[dict], field_name: str) -> Tuple[str, float]:
        """
        Vote de consensus entre les différents résultats OCR.
        
        Returns:
            (meilleur_texte, confiance)
        """
        if not results:
            return '', 0.0
        
        # Normaliser les textes pour le vote
        normalized_results = []
        for r in results:
            if field_name == 'date_of_birth':
                norm_text = self._normalize_date(r['text'])
            else:
                norm_text = self._normalize_name(r['text'])
            
            if norm_text:
                normalized_results.append({
                    'text': norm_text,
                    'confidence': r['confidence'],
                    'original': r['text']
                })
        
        if not normalized_results:
            return '', 0.0
        
        # Compter les votes (textes similaires)
        vote_counts = {}
        for r in normalized_results:
            text = r['text']
            found_match = False
            
            for existing_text in vote_counts:
                similarity = SequenceMatcher(None, text, existing_text).ratio()
                if similarity > 0.8:
                    vote_counts[existing_text]['count'] += 1
                    vote_counts[existing_text]['total_conf'] += r['confidence']
                    found_match = True
                    break
            
            if not found_match:
                vote_counts[text] = {'count': 1, 'total_conf': r['confidence']}
        
        # Trouver le meilleur candidat
        best_text = ''
        best_score = 0
        
        for text, data in vote_counts.items():
            score = data['count'] * (data['total_conf'] / data['count'])
            if score > best_score:
                best_score = score
                best_text = text
        
        # Calculer la confiance finale
        total_votes = sum(d['count'] for d in vote_counts.values())
        if best_text in vote_counts:
            confidence = vote_counts[best_text]['count'] / total_votes
        else:
            confidence = 0.0
        
        return best_text, confidence
    
    def _normalize_name(self, text: str) -> str:
        """Normalise un nom/prénom."""
        if not text:
            return ''
        
        # Supprimer les caractères non alphabétiques sauf espaces et tirets
        text = re.sub(r'[^A-Za-zÀ-ÿ\s\-]', '', text)
        
        # Normaliser les espaces
        text = ' '.join(text.split())
        
        # Mettre en majuscules
        text = text.upper()
        
        # Supprimer les accents pour la comparaison
        text = unicodedata.normalize('NFD', text)
        text = ''.join(c for c in text if unicodedata.category(c) != 'Mn')
        
        return text.strip()
    
    def _normalize_date(self, text: str) -> str:
        """Normalise une date au format JJ/MM/AAAA."""
        if not text:
            return ''
        
        # Extraire les chiffres
        digits = re.sub(r'[^0-9]', '', text)
        
        # Essayer de former une date valide
        if len(digits) >= 8:
            day = digits[:2]
            month = digits[2:4]
            year = digits[4:8]
            
            # Validation basique
            try:
                d = int(day)
                m = int(month)
                y = int(year)
                
                if 1 <= d <= 31 and 1 <= m <= 12 and 1900 <= y <= 2020:
                    return f"{day}/{month}/{year}"
            except ValueError:
                pass
        
        # Si on a 6 chiffres, essayer avec année sur 2 chiffres
        if len(digits) == 6:
            day = digits[:2]
            month = digits[2:4]
            year_short = digits[4:6]
            
            try:
                d = int(day)
                m = int(month)
                y = int(year_short)
                
                if 1 <= d <= 31 and 1 <= m <= 12:
                    # Assumer 20xx pour les années < 30, 19xx sinon
                    full_year = f"20{year_short}" if y < 30 else f"19{year_short}"
                    return f"{day}/{month}/{full_year}"
            except ValueError:
                pass
        
        return ''
    
    def extract_header(self, header_image: np.ndarray) -> CMENHeaderResult:
        """
        Extrait tous les champs de l'en-tête CMEN.
        
        Args:
            header_image: Image de l'en-tête (environ 25% supérieur de la page)
            
        Returns:
            CMENHeaderResult avec NOM, PRÉNOM et DATE DE NAISSANCE
        """
        logger.info("Extracting CMEN header fields...")
        
        fields = []
        
        # Extraire chaque champ
        for field_name in ['last_name', 'first_name', 'date_of_birth']:
            field = self.extract_field(header_image, field_name)
            fields.append(field)
            logger.info(f"  {field_name}: '{field.value}' (conf: {field.confidence:.2f})")
        
        # Calculer la confiance globale
        overall_confidence = sum(f.confidence for f in fields) / len(fields) if fields else 0.0
        
        return CMENHeaderResult(
            last_name=fields[0].value if fields else '',
            first_name=fields[1].value if len(fields) > 1 else '',
            date_of_birth=fields[2].value if len(fields) > 2 else '',
            overall_confidence=overall_confidence,
            fields=fields
        )
    
    def match_student(
        self, 
        header_result: CMENHeaderResult, 
        students: List[StudentCSVRecord],
        threshold: float = 0.6
    ) -> Optional[StudentMatchResult]:
        """
        Fait correspondre le résultat OCR avec un élève du CSV.
        
        Args:
            header_result: Résultat de l'extraction OCR
            students: Liste des élèves du CSV
            threshold: Seuil minimum de correspondance
            
        Returns:
            StudentMatchResult si une correspondance est trouvée, None sinon
        """
        if not students:
            return None
        
        best_match = None
        best_score = 0.0
        best_details = {}
        
        for student in students:
            # Calculer les scores de similarité pour chaque champ
            name_score = SequenceMatcher(
                None, 
                header_result.last_name.upper(), 
                student.last_name.upper()
            ).ratio()
            
            firstname_score = SequenceMatcher(
                None, 
                header_result.first_name.upper(), 
                student.first_name.upper()
            ).ratio()
            
            # La date doit correspondre exactement ou presque
            date_score = 1.0 if header_result.date_of_birth == student.date_of_birth else 0.0
            if date_score == 0.0 and header_result.date_of_birth and student.date_of_birth:
                # Essayer une correspondance partielle sur la date
                date_score = SequenceMatcher(
                    None,
                    header_result.date_of_birth.replace('/', ''),
                    student.date_of_birth.replace('/', '')
                ).ratio()
            
            # Score global pondéré (la date est très importante)
            overall_score = (name_score * 0.35 + firstname_score * 0.35 + date_score * 0.30)
            
            if overall_score > best_score:
                best_score = overall_score
                best_match = student
                best_details = {
                    'last_name': name_score,
                    'first_name': firstname_score,
                    'date_of_birth': date_score
                }
        
        if best_match and best_score >= threshold:
            return StudentMatchResult(
                student=best_match,
                confidence=best_score,
                match_details=best_details
            )
        
        return None


def load_students_from_csv(csv_path: str) -> List[StudentCSVRecord]:
    """
    Charge la liste des élèves depuis un fichier CSV.
    
    Le CSV doit contenir les colonnes: NOM, PRENOM, DATE_NAISSANCE
    (ou variations comme: last_name, first_name, date_of_birth, nom, prenom, etc.)
    """
    import csv
    
    students = []
    
    # Mappings possibles des colonnes
    name_columns = ['nom', 'last_name', 'nom_famille', 'family_name', 'surname']
    firstname_columns = ['prenom', 'first_name', 'firstname', 'given_name']
    date_columns = ['date_naissance', 'date_of_birth', 'birthdate', 'dob', 'naissance']
    email_columns = ['email', 'mail', 'courriel']
    
    def find_column(headers: List[str], possible_names: List[str]) -> Optional[int]:
        """Trouve l'index d'une colonne parmi les noms possibles."""
        for i, h in enumerate(headers):
            h_lower = h.lower().strip()
            for name in possible_names:
                if name in h_lower:
                    return i
        return None
    
    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            # Détecter le délimiteur
            sample = f.read(1024)
            f.seek(0)
            
            if ';' in sample:
                delimiter = ';'
            elif '\t' in sample:
                delimiter = '\t'
            else:
                delimiter = ','
            
            reader = csv.reader(f, delimiter=delimiter)
            headers = next(reader)
            
            # Trouver les colonnes
            name_idx = find_column(headers, name_columns)
            firstname_idx = find_column(headers, firstname_columns)
            date_idx = find_column(headers, date_columns)
            email_idx = find_column(headers, email_columns)
            
            if name_idx is None or firstname_idx is None:
                logger.warning(f"CSV missing required columns. Headers: {headers}")
                return []
            
            for i, row in enumerate(reader):
                if len(row) <= max(name_idx, firstname_idx):
                    continue
                
                last_name = row[name_idx].strip() if name_idx < len(row) else ''
                first_name = row[firstname_idx].strip() if firstname_idx < len(row) else ''
                date_of_birth = row[date_idx].strip() if date_idx and date_idx < len(row) else ''
                email = row[email_idx].strip() if email_idx and email_idx < len(row) else ''
                
                if last_name and first_name:
                    students.append(StudentCSVRecord(
                        student_id=i + 1,
                        last_name=last_name,
                        first_name=first_name,
                        date_of_birth=date_of_birth,
                        email=email
                    ))
        
        logger.info(f"Loaded {len(students)} students from CSV")
        return students
        
    except Exception as e:
        logger.error(f"Failed to load CSV: {e}")
        return []
