#!/usr/bin/env python3
"""
Ciblage OCR Haute Précision (Header-Only)

Extraction optimisée des en-têtes d'identification avec:
- ROI précis: 75%-98% X, 0%-20% Y (coin supérieur droit uniquement)
- Pages impaires uniquement (1, 3, 5...)
- Validation Triple: Nom + Prénom (Fuzzy >80%) + DOB (exact match)
- Génération de mapping.json

Usage:
    python header_ocr_precision.py --pdf scan.pdf --csv students.csv --output ./output/

Author: Korrigo Team
PRD-19: Ciblage OCR Haute Précision
"""
import os
import sys
import csv
import json
import logging
import argparse
import unicodedata
import re
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional, Tuple
from difflib import SequenceMatcher

import fitz  # PyMuPDF
import cv2
import numpy as np

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


# ============================================================================
# Configuration ROI Haute Précision
# ============================================================================
# Note: Ces coordonnées s'appliquent à la PARTIE DROITE de la page A3
# (après division au milieu). L'en-tête CMEN occupe toute la largeur du header.
ROI_CONFIG = {
    'x_start': 0.00,  # 0% - début de la demi-page droite
    'x_end': 1.00,    # 100% - toute la largeur
    'y_start': 0.00,  # 0% de la hauteur (haut)
    'y_end': 0.25,    # 25% de la hauteur (header complet)
}

# Seuils de validation
THRESHOLD_NAME_FUZZY = 0.80  # 80% similarité pour Nom+Prénom
THRESHOLD_DATE_EXACT = True   # Date de naissance doit être exacte


@dataclass
class StudentRecord:
    """Enregistrement étudiant depuis le CSV (Source de Vérité)."""
    id: int
    raw_name: str
    last_name: str
    first_name: str
    last_name_normalized: str
    first_name_normalized: str
    date_of_birth: str
    date_normalized: str  # Format DDMMYYYY
    classe: str = ""


@dataclass
class OCRResult:
    """Résultat d'extraction OCR."""
    last_name: str
    first_name: str
    date_of_birth: str
    raw_response: str
    confidence: float


@dataclass
class MappingEntry:
    """Entrée du mapping.json."""
    scan_page: int           # Numéro de page dans le scan (1-indexed)
    student_id: int          # ID dans le CSV
    student_name: str        # Nom complet depuis le CSV
    classe: str              # Classe depuis le CSV
    ocr_extracted: dict      # Données brutes OCR
    validation: dict         # Détails de la validation
    status: str              # VALIDATED, AMBIGUOUS, NO_MATCH


class HeaderOCRPrecision:
    """
    Service OCR haute précision pour extraction d'en-têtes.
    """
    
    def __init__(self,
                 pdf_path: str,
                 csv_path: str,
                 output_dir: str,
                 api_key: str = None,
                 model: str = None,
                 dpi: int = 200):
        self.pdf_path = pdf_path
        self.csv_path = csv_path
        self.output_dir = output_dir
        self.api_key = api_key or os.environ.get('OPENAI_API_KEY')
        self.model = model or os.environ.get('OPENAI_MODEL', 'gpt-4.1-mini-2025-04-14')
        self.dpi = dpi
        
        self.students: List[StudentRecord] = []
        self.mappings: List[MappingEntry] = []
        
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        if not self.api_key:
            raise ValueError("OpenAI API key required. Set OPENAI_API_KEY env var.")
    
    def load_csv(self) -> List[StudentRecord]:
        """Charge le CSV comme Source de Vérité."""
        self.students = []
        
        with open(self.csv_path, 'r', encoding='utf-8-sig') as f:
            sample = f.read(2048)
            f.seek(0)
            delimiter = ';' if ';' in sample and ',' not in sample else ','
            reader = csv.DictReader(f, delimiter=delimiter)
            
            for idx, row in enumerate(reader):
                record = self._parse_csv_row(row, idx + 1)
                if record:
                    self.students.append(record)
        
        logger.info(f"CSV loaded: {len(self.students)} students")
        return self.students
    
    def _parse_csv_row(self, row: Dict[str, str], idx: int) -> Optional[StudentRecord]:
        """Parse une ligne CSV."""
        name_cols = ['Élèves', 'Eleves', 'NOM', 'Nom', 'name', 'full_name']
        date_cols = ['Né(e) le', 'DATE_NAISSANCE', 'Date de naissance', 'dob']
        class_cols = ['Classe', 'CLASSE', 'class']
        
        raw_name = next((row[c].strip() for c in name_cols if c in row and row[c].strip()), "")
        if not raw_name:
            return None
        
        parts = raw_name.split(' ', 1)
        last_name = parts[0].strip()
        first_name = parts[1].strip() if len(parts) > 1 else ""
        dob = next((row[c].strip() for c in date_cols if c in row and row[c].strip()), "")
        classe = next((row[c].strip() for c in class_cols if c in row and row[c].strip()), "")
        
        return StudentRecord(
            id=idx,
            raw_name=raw_name,
            last_name=last_name,
            first_name=first_name,
            last_name_normalized=self._normalize_text(last_name),
            first_name_normalized=self._normalize_text(first_name),
            date_of_birth=dob,
            date_normalized=self._normalize_date(dob),
            classe=classe
        )
    
    def _normalize_text(self, text: str) -> str:
        """Normalise le texte (majuscules, sans accents)."""
        if not text:
            return ""
        text = text.upper()
        text = unicodedata.normalize('NFD', text)
        text = ''.join(c for c in text if unicodedata.category(c) != 'Mn')
        text = re.sub(r'[^A-Z\s]', '', text)
        return ' '.join(text.split()).strip()
    
    def _normalize_date(self, date_str: str) -> str:
        """Normalise une date en DDMMYYYY."""
        if not date_str:
            return ""
        return re.sub(r'[^\d]', '', date_str)
    
    def process_pdf(self, max_pages: int = None) -> List[MappingEntry]:
        """
        Traite le PDF en extrayant uniquement les pages impaires.
        
        Args:
            max_pages: Nombre max de pages impaires à traiter (pour tests)
        """
        doc = fitz.open(self.pdf_path)
        self.mappings = []
        
        # Compter les pages impaires
        odd_pages = [i for i in range(doc.page_count) if i % 2 == 0]
        if max_pages:
            odd_pages = odd_pages[:max_pages]
        
        logger.info(f"Processing {len(odd_pages)} odd pages (out of {doc.page_count} total)")
        
        for page_idx in odd_pages:
            scan_page_num = page_idx + 1  # 1-indexed
            
            # Extraire le ROI haute précision
            page = doc.load_page(page_idx)
            header_img = self._extract_header_roi(page)
            
            # Sauvegarder le ROI pour debug
            roi_path = os.path.join(self.output_dir, f"roi_page_{scan_page_num:03d}.jpg")
            cv2.imwrite(roi_path, header_img)
            
            # OCR via GPT-4 Vision
            ocr_result = self._extract_ocr(header_img)
            
            # Validation Triple avec le CSV
            student, validation = self._validate_triple(ocr_result)
            
            # Déterminer le statut
            if validation['is_valid']:
                status = 'VALIDATED'
            elif validation['name_score'] >= 0.60:
                status = 'AMBIGUOUS'
            else:
                status = 'NO_MATCH'
            
            entry = MappingEntry(
                scan_page=scan_page_num,
                student_id=student.id if student else 0,
                student_name=student.raw_name if student else "",
                classe=student.classe if student else "",
                ocr_extracted={
                    'last_name': ocr_result.last_name,
                    'first_name': ocr_result.first_name,
                    'date_of_birth': ocr_result.date_of_birth
                },
                validation=validation,
                status=status
            )
            
            self.mappings.append(entry)
            
            # Log
            icon = '✅' if status == 'VALIDATED' else ('⚠️' if status == 'AMBIGUOUS' else '❌')
            logger.info(f"{icon} Page {scan_page_num}: "
                       f"{ocr_result.last_name} {ocr_result.first_name} ({ocr_result.date_of_birth}) -> "
                       f"{student.raw_name if student else 'NO_MATCH'} [{status}]")
        
        doc.close()
        return self.mappings
    
    def _extract_header_roi(self, page: fitz.Page) -> np.ndarray:
        """
        Extrait le ROI haute précision de l'en-tête.
        
        Coordonnées: X 75%-98%, Y 0%-20% de la partie droite de la page A3.
        """
        # Rendre la page en image
        mat = fitz.Matrix(self.dpi / 72, self.dpi / 72)
        pix = page.get_pixmap(matrix=mat)
        
        img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
        if pix.n == 3:
            img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
        elif pix.n == 4:
            img = cv2.cvtColor(img, cv2.COLOR_RGBA2BGR)
        
        h, w = img.shape[:2]
        
        # D'abord extraire la partie droite (page impaire dans le format A3)
        mid_x = w // 2
        right_page = img[:, mid_x:]
        
        rh, rw = right_page.shape[:2]
        
        # Appliquer le ROI haute précision sur la partie droite
        x1 = int(rw * ROI_CONFIG['x_start'])
        x2 = int(rw * ROI_CONFIG['x_end'])
        y1 = int(rh * ROI_CONFIG['y_start'])
        y2 = int(rh * ROI_CONFIG['y_end'])
        
        header_roi = right_page[y1:y2, x1:x2]
        
        # Améliorer le contraste
        return self._enhance_contrast(header_roi)
    
    def _enhance_contrast(self, img: np.ndarray) -> np.ndarray:
        """Améliore le contraste pour OCR."""
        if len(img.shape) == 3:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        else:
            gray = img
        
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)
        
        return cv2.cvtColor(enhanced, cv2.COLOR_GRAY2BGR)
    
    def _extract_ocr(self, header_img: np.ndarray) -> OCRResult:
        """Extraction OCR via GPT-4 Vision."""
        import base64
        import openai
        
        _, buffer = cv2.imencode('.jpg', header_img, [cv2.IMWRITE_JPEG_QUALITY, 95])
        base64_image = base64.b64encode(buffer).decode('utf-8')
        
        prompt = """Analyze this exam header image carefully. Extract the handwritten text from the boxes:

1. **NOM** (Last name): Read each letter from the boxes after "Nom de famille:"
2. **PRENOM** (First name): Read each letter from the boxes after "Prénom(s):"
3. **DATE_NAISSANCE** (Date of birth): Read the date after "Né(e) le:" in format DD/MM/YYYY

IMPORTANT:
- Read each handwritten letter carefully
- Text is typically in UPPERCASE
- Common confusions: O/0, I/1, S/5, B/8
- If unclear, provide your best interpretation

Return ONLY this JSON:
{"NOM": "LASTNAME", "PRENOM": "FIRSTNAME", "DATE_NAISSANCE": "DD/MM/YYYY"}"""

        try:
            client = openai.OpenAI(api_key=self.api_key)
            response = client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {
                        "url": f"data:image/jpeg;base64,{base64_image}",
                        "detail": "high"
                    }}
                ]}],
                max_tokens=200,
                temperature=0.1
            )
            
            raw = response.choices[0].message.content
            return self._parse_ocr_response(raw)
            
        except Exception as e:
            logger.error(f"OCR failed: {e}")
            return OCRResult("", "", "", str(e), 0.0)
    
    def _parse_ocr_response(self, response: str) -> OCRResult:
        """Parse la réponse GPT-4V."""
        try:
            json_match = re.search(r'\{[^}]+\}', response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
            else:
                data = json.loads(response)
            
            last_name = data.get('NOM', '').strip().upper()
            first_name = data.get('PRENOM', '').strip().upper()
            dob = data.get('DATE_NAISSANCE', '').strip()
            
            # Nettoyer les valeurs vides ou "UNKNOWN"
            if last_name in ["UNKNOWN", "N/A", ""]:
                last_name = ""
            if first_name in ["UNKNOWN", "N/A", ""]:
                first_name = ""
            if dob in ["UNKNOWN", "N/A", ""]:
                dob = ""
            
            confidence = (0.4 if last_name else 0) + (0.3 if first_name else 0) + (0.3 if dob else 0)
            
            return OCRResult(last_name, first_name, dob, response, confidence)
            
        except Exception as e:
            logger.warning(f"Failed to parse OCR response: {e}")
            return OCRResult("", "", "", response, 0.0)
    
    def _validate_triple(self, ocr: OCRResult) -> Tuple[Optional[StudentRecord], dict]:
        """
        Validation Triple: Nom + Prénom (Fuzzy >80%) + DOB (exact).
        
        La date de naissance sert de pivot pour confirmer l'identité
        en cas d'ambiguïté sur le nom.
        """
        if not ocr.last_name and not ocr.first_name:
            return None, {
                'is_valid': False,
                'name_score': 0.0,
                'date_match': False,
                'reason': 'No OCR data extracted'
            }
        
        ocr_last = self._normalize_text(ocr.last_name)
        ocr_first = self._normalize_text(ocr.first_name)
        ocr_date = self._normalize_date(ocr.date_of_birth)
        
        best_match = None
        best_validation = {
            'is_valid': False,
            'name_score': 0.0,
            'last_name_score': 0.0,
            'first_name_score': 0.0,
            'date_match': False,
            'reason': 'No match found'
        }
        
        for student in self.students:
            # Score Nom de famille
            last_score = SequenceMatcher(None, ocr_last, student.last_name_normalized).ratio()
            
            # Score Prénom
            first_score = SequenceMatcher(None, ocr_first, student.first_name_normalized).ratio()
            
            # Score combiné Nom+Prénom
            name_score = (last_score * 0.6 + first_score * 0.4)
            
            # Match Date de naissance (exact)
            date_match = (ocr_date == student.date_normalized) if ocr_date and student.date_normalized else False
            
            # Validation Triple
            # Cas 1: Nom+Prénom >= 80% ET Date exacte = VALIDATED
            # Cas 2: Nom+Prénom < 80% MAIS Date exacte = utiliser DOB comme pivot
            # Cas 3: Nom+Prénom >= 80% MAIS Date différente = AMBIGUOUS
            
            is_valid = False
            reason = ""
            
            if name_score >= THRESHOLD_NAME_FUZZY and date_match:
                # Cas idéal: tout correspond
                is_valid = True
                reason = "Triple validation: Name + DOB match"
            elif name_score < THRESHOLD_NAME_FUZZY and date_match:
                # DOB comme pivot pour confirmer malgré nom ambigu
                if name_score >= 0.50:  # Seuil minimum pour accepter avec DOB
                    is_valid = True
                    reason = f"DOB pivot validation (name score {name_score:.2f})"
            elif name_score >= THRESHOLD_NAME_FUZZY and not date_match:
                # Nom OK mais date différente - ambigu
                reason = f"Name match but DOB mismatch"
            else:
                reason = f"Low name score ({name_score:.2f})"
            
            # Garder le meilleur match
            current_score = name_score + (0.5 if date_match else 0)
            best_score = best_validation['name_score'] + (0.5 if best_validation['date_match'] else 0)
            
            if current_score > best_score:
                best_match = student
                best_validation = {
                    'is_valid': is_valid,
                    'name_score': round(name_score, 3),
                    'last_name_score': round(last_score, 3),
                    'first_name_score': round(first_score, 3),
                    'date_match': date_match,
                    'reason': reason
                }
        
        return best_match, best_validation
    
    def generate_mapping(self) -> str:
        """Génère le fichier mapping.json."""
        mapping_data = {
            'generated_at': datetime.now().isoformat(),
            'source_pdf': self.pdf_path,
            'source_csv': self.csv_path,
            'roi_config': ROI_CONFIG,
            'validation_thresholds': {
                'name_fuzzy': THRESHOLD_NAME_FUZZY,
                'date_exact': THRESHOLD_DATE_EXACT
            },
            'summary': {
                'total_pages': len(self.mappings),
                'validated': sum(1 for m in self.mappings if m.status == 'VALIDATED'),
                'ambiguous': sum(1 for m in self.mappings if m.status == 'AMBIGUOUS'),
                'no_match': sum(1 for m in self.mappings if m.status == 'NO_MATCH')
            },
            'mappings': [asdict(m) for m in self.mappings]
        }
        
        mapping_path = os.path.join(self.output_dir, 'mapping.json')
        with open(mapping_path, 'w', encoding='utf-8') as f:
            json.dump(mapping_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Mapping generated: {mapping_path}")
        return mapping_path
    
    def process(self, max_pages: int = None) -> dict:
        """Exécute le pipeline complet."""
        logger.info("="*60)
        logger.info("HEADER OCR PRECISION - High Accuracy Extraction")
        logger.info("="*60)
        logger.info(f"ROI: X {ROI_CONFIG['x_start']*100:.0f}%-{ROI_CONFIG['x_end']*100:.0f}%, "
                   f"Y {ROI_CONFIG['y_start']*100:.0f}%-{ROI_CONFIG['y_end']*100:.0f}%")
        
        # 1. Charger le CSV
        self.load_csv()
        
        # 2. Traiter le PDF (pages impaires uniquement)
        self.process_pdf(max_pages=max_pages)
        
        # 3. Générer le mapping
        mapping_path = self.generate_mapping()
        
        # Résumé
        validated = sum(1 for m in self.mappings if m.status == 'VALIDATED')
        ambiguous = sum(1 for m in self.mappings if m.status == 'AMBIGUOUS')
        no_match = sum(1 for m in self.mappings if m.status == 'NO_MATCH')
        
        logger.info("="*60)
        logger.info("PROCESSING COMPLETE")
        logger.info(f"  VALIDATED: {validated}")
        logger.info(f"  AMBIGUOUS: {ambiguous}")
        logger.info(f"  NO_MATCH: {no_match}")
        logger.info(f"  Accuracy: {100*validated/len(self.mappings):.1f}%")
        logger.info("="*60)
        
        return {
            'total': len(self.mappings),
            'validated': validated,
            'ambiguous': ambiguous,
            'no_match': no_match,
            'accuracy': validated / len(self.mappings) if self.mappings else 0,
            'mapping_path': mapping_path
        }


def main():
    parser = argparse.ArgumentParser(description='High-precision header OCR extraction')
    parser.add_argument('--pdf', required=True, help='Path to A3 scanned PDF')
    parser.add_argument('--csv', required=True, help='Path to students CSV')
    parser.add_argument('--output', required=True, help='Output directory')
    parser.add_argument('--max-pages', type=int, help='Max odd pages to process (for testing)')
    parser.add_argument('--api-key', help='OpenAI API key')
    parser.add_argument('--model', help='GPT-4 Vision model')
    
    args = parser.parse_args()
    
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass
    
    service = HeaderOCRPrecision(
        pdf_path=args.pdf,
        csv_path=args.csv,
        output_dir=args.output,
        api_key=args.api_key,
        model=args.model
    )
    
    result = service.process(max_pages=args.max_pages)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
