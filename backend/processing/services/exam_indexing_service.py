"""
Pipeline d'Indexation Automatisée des Copies d'Examen.

Ce service implémente un système robuste d'OCR et de réconciliation de données
(PDF Scan ↔ CSV Élèves) pour l'identification automatique des copies.

Author: Korrigo Team
PRD-19: Pipeline d'indexation automatisée
"""
import os
import re
import csv
import json
import logging
import unicodedata
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime
from difflib import SequenceMatcher

import cv2
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class StudentRecord:
    """Enregistrement étudiant normalisé depuis le CSV (SSOT)."""
    id: int
    raw_name: str
    last_name: str
    first_name: str
    full_name_normalized: str
    date_of_birth: str
    date_normalized: str
    email: str = ""
    classe: str = ""
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class OCRExtraction:
    """Résultat d'extraction OCR d'un en-tête."""
    last_name: str
    first_name: str
    date_of_birth: str
    raw_response: str
    confidence: float
    status: str


@dataclass
class CopyMatch:
    """Résultat de matching pour une copie."""
    page_start: int
    page_end: int
    ocr_extraction: OCRExtraction
    student: Optional[StudentRecord]
    match_score: float
    validation_status: str
    candidates: List[Tuple[StudentRecord, float]] = field(default_factory=list)


class ExamIndexingService:
    """Service d'indexation automatisée des copies d'examen."""
    
    THRESHOLD_VALIDATED = 0.80
    THRESHOLD_AMBIGUOUS = 0.60
    THRESHOLD_MANUAL = 0.40
    # ROI pour l'en-tête CMEN: haut de la page (25% hauteur), toute la largeur
    ROI_X_START = 0.0   # Début à gauche
    ROI_X_END = 1.0     # Fin à droite (toute la largeur)
    ROI_Y_END = 0.25    # 25% depuis le haut
    
    def __init__(self, csv_path: str = None, pdf_path: str = None,
                 api_key: str = None, model: str = None, debug: bool = False):
        self.csv_path = csv_path
        self.pdf_path = pdf_path
        self.api_key = api_key or os.environ.get('OPENAI_API_KEY')
        self.model = model or os.environ.get('OPENAI_MODEL', 'gpt-4.1-mini-2025-04-14')
        self.debug = debug
        self.students: List[StudentRecord] = []
        self.student_index: Dict[str, StudentRecord] = {}
        self.results: List[CopyMatch] = []
        
        if not self.api_key:
            raise ValueError("OpenAI API key required")
    
    def load_csv(self, csv_path: str = None) -> List[StudentRecord]:
        """Charge le CSV des élèves comme Source de Vérité (SSOT)."""
        path = csv_path or self.csv_path
        if not path:
            raise ValueError("CSV path required")
        
        self.students = []
        self.student_index = {}
        
        with open(path, 'r', encoding='utf-8-sig') as f:
            sample = f.read(2048)
            f.seek(0)
            delimiter = ';' if ';' in sample and ',' not in sample else ','
            reader = csv.DictReader(f, delimiter=delimiter)
            
            for idx, row in enumerate(reader):
                record = self._parse_csv_row(row, idx + 1)
                if record:
                    self.students.append(record)
                    self.student_index[record.full_name_normalized] = record
        
        logger.info(f"Loaded {len(self.students)} students from CSV")
        return self.students
    
    def _parse_csv_row(self, row: Dict[str, str], idx: int) -> Optional[StudentRecord]:
        """Parse une ligne CSV en StudentRecord."""
        name_cols = ['Élèves', 'Eleves', 'NOM', 'Nom', 'name', 'full_name']
        date_cols = ['Né(e) le', 'DATE_NAISSANCE', 'Date de naissance', 'dob']
        email_cols = ['Adresse E-mail', 'Email', 'email']
        class_cols = ['Classe', 'CLASSE', 'class']
        
        raw_name = next((row[c].strip() for c in name_cols if c in row and row[c].strip()), "")
        if not raw_name:
            return None
        
        parts = raw_name.split(' ', 1)
        last_name = parts[0].strip()
        first_name = parts[1].strip() if len(parts) > 1 else ""
        dob = next((row[c].strip() for c in date_cols if c in row and row[c].strip()), "")
        email = next((row[c].strip() for c in email_cols if c in row and row[c].strip()), "")
        classe = next((row[c].strip() for c in class_cols if c in row and row[c].strip()), "")
        
        return StudentRecord(
            id=idx, raw_name=raw_name, last_name=last_name, first_name=first_name,
            full_name_normalized=self._normalize_text(f"{last_name} {first_name}"),
            date_of_birth=dob, date_normalized=self._normalize_date(dob),
            email=email, classe=classe
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
        return re.sub(r'[^\d]', '', date_str) if date_str else ""
    
    def process_pdf(self, pdf_path: str = None, output_dir: str = None,
                    max_copies: int = None) -> List[CopyMatch]:
        """Traite le PDF complet avec OCR et matching."""
        import fitz
        
        path = pdf_path or self.pdf_path
        if not path:
            raise ValueError("PDF path required")
        if not self.students:
            raise ValueError("Students not loaded. Call load_csv() first.")
        
        if output_dir:
            Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        doc = fitz.open(path)
        self.results = []
        
        page = doc.load_page(0)
        is_a3 = (page.rect.width / page.rect.height) > 1.2
        
        logger.info(f"Processing PDF: {doc.page_count} pages, format={'A3' if is_a3 else 'A4'}")
        
        dpi = 200
        copy_count = 0
        
        for page_idx in range(doc.page_count):
            if max_copies and copy_count >= max_copies:
                break
            
            page = doc.load_page(page_idx)
            mat = fitz.Matrix(dpi / 72, dpi / 72)
            pix = page.get_pixmap(matrix=mat)
            
            img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
            if pix.n == 3:
                img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
            elif pix.n == 4:
                img = cv2.cvtColor(img, cv2.COLOR_RGBA2BGR)
            
            if is_a3:
                mid_x = img.shape[1] // 2
                right_page = img[:, mid_x:]
                page_start = page_idx * 2 + 1
                page_end = page_start + 1
                
                result = self._process_single_page(right_page, page_start, page_end,
                                                   output_dir, f"a3_{page_idx+1}_right")
                if result:
                    self.results.append(result)
                    copy_count += 1
            else:
                if (page_idx + 1) % 2 == 1:
                    result = self._process_single_page(img, page_idx + 1, page_idx + 2,
                                                       output_dir, f"a4_{page_idx+1}")
                    if result:
                        self.results.append(result)
                        copy_count += 1
        
        doc.close()
        self._log_summary()
        return self.results
    
    def _log_summary(self):
        """Log le résumé des résultats."""
        validated = sum(1 for r in self.results if r.validation_status == 'VALIDATED')
        ambiguous = sum(1 for r in self.results if r.validation_status == 'AMBIGUOUS')
        manual = sum(1 for r in self.results if r.validation_status == 'MANUAL_REVIEW')
        no_match = sum(1 for r in self.results if r.validation_status == 'NO_MATCH')
        
        logger.info(f"Complete: {len(self.results)} copies - "
                   f"VALIDATED:{validated} AMBIGUOUS:{ambiguous} MANUAL:{manual} NO_MATCH:{no_match}")
    
    def _process_single_page(self, page_img: np.ndarray, page_start: int, page_end: int,
                             output_dir: str = None, page_name: str = "") -> Optional[CopyMatch]:
        """Traite une page: ROI extraction + OCR + matching."""
        h, w = page_img.shape[:2]
        roi_x1 = int(w * self.ROI_X_START)
        roi_x2 = int(w * self.ROI_X_END)
        roi_y2 = int(h * self.ROI_Y_END)
        header_roi = page_img[:roi_y2, roi_x1:roi_x2]
        header_enhanced = self._enhance_contrast(header_roi)
        
        if output_dir and self.debug:
            cv2.imwrite(f"{output_dir}/{page_name}_header.png", header_enhanced)
        
        ocr_result = self._extract_with_gpt4v(header_enhanced)
        
        if ocr_result.status == 'FAILED':
            return CopyMatch(page_start=page_start, page_end=page_end, ocr_extraction=ocr_result,
                           student=None, match_score=0.0, validation_status='NO_MATCH', candidates=[])
        
        student, score, candidates = self._fuzzy_match(ocr_result)
        
        if score >= self.THRESHOLD_VALIDATED:
            status = 'VALIDATED'
        elif score >= self.THRESHOLD_AMBIGUOUS:
            status = 'AMBIGUOUS'
        elif score >= self.THRESHOLD_MANUAL:
            status = 'MANUAL_REVIEW'
        else:
            status = 'NO_MATCH'
        
        logger.info(f"Page {page_start}: {ocr_result.last_name} {ocr_result.first_name} -> "
                   f"{status} [{student.raw_name if student else 'None'}] score={score:.3f}")
        
        return CopyMatch(page_start=page_start, page_end=page_end, ocr_extraction=ocr_result,
                        student=student, match_score=score, validation_status=status,
                        candidates=candidates[:5])
    
    def _enhance_contrast(self, img: np.ndarray) -> np.ndarray:
        """Améliore le contraste pour OCR."""
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)
        return cv2.cvtColor(enhanced, cv2.COLOR_GRAY2BGR)
    
    def _extract_with_gpt4v(self, header_img: np.ndarray) -> OCRExtraction:
        """Extraction OCR via GPT-4 Vision."""
        import base64
        import openai
        
        _, buffer = cv2.imencode('.jpg', header_img, [cv2.IMWRITE_JPEG_QUALITY, 95])
        base64_image = base64.b64encode(buffer).decode('utf-8')
        
        prompt = """Extract from this exam header:
1. NOM_MANUSCRIT: Last name from boxes after "Nom de famille:"
2. PRENOM_MANUSCRIT: First name from boxes after "Prénom(s):"
3. DOB_MANUSCRIT: Date of birth after "Né(e) le:" (DD/MM/YYYY)

Return JSON: {"NOM_MANUSCRIT": "...", "PRENOM_MANUSCRIT": "...", "DOB_MANUSCRIT": "..."}
Use "UNKNOWN" if unreadable."""

        try:
            client = openai.OpenAI(api_key=self.api_key)
            response = client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}", "detail": "high"}}
                ]}],
                max_tokens=300, temperature=0.1
            )
            return self._parse_ocr_response(response.choices[0].message.content)
        except Exception as e:
            logger.error(f"GPT-4V failed: {e}")
            return OCRExtraction("", "", "", str(e), 0.0, "FAILED")
    
    def _parse_ocr_response(self, response: str) -> OCRExtraction:
        """Parse la réponse GPT-4V."""
        try:
            json_match = re.search(r'\{[^}]+\}', response, re.DOTALL)
            data = json.loads(json_match.group()) if json_match else json.loads(response)
            
            last_name = data.get('NOM_MANUSCRIT', '').strip().upper()
            first_name = data.get('PRENOM_MANUSCRIT', '').strip().upper()
            dob = data.get('DOB_MANUSCRIT', '').strip()
            
            if last_name == "UNKNOWN": last_name = ""
            if first_name == "UNKNOWN": first_name = ""
            if dob == "UNKNOWN": dob = ""
            
            confidence = (0.4 if last_name else 0) + (0.2 if first_name else 0) + (0.4 if dob else 0)
            status = "OK" if confidence >= 0.6 else ("PARTIAL" if confidence > 0 else "FAILED")
            
            return OCRExtraction(last_name, first_name, dob, response, confidence, status)
        except:
            return OCRExtraction("", "", "", response, 0.0, "FAILED")
    
    def _fuzzy_match(self, ocr: OCRExtraction) -> Tuple[Optional[StudentRecord], float, List]:
        """Fuzzy matching avec Levenshtein."""
        if not ocr.last_name and not ocr.first_name:
            return None, 0.0, []
        
        ocr_name = self._normalize_text(f"{ocr.last_name} {ocr.first_name}")
        ocr_date = self._normalize_date(ocr.date_of_birth)
        
        candidates = []
        for student in self.students:
            name_score = SequenceMatcher(None, ocr_name, student.full_name_normalized).ratio()
            date_score = self._date_similarity(ocr_date, student.date_normalized) if ocr_date else 0
            
            if name_score >= 0.80:
                total = 0.70 * name_score + 0.30 * date_score
            elif name_score >= 0.60 and date_score >= 0.90:
                total = 0.50 * name_score + 0.50 * date_score
            else:
                total = 0.50 * name_score + 0.50 * date_score
            
            candidates.append((student, total))
        
        candidates.sort(key=lambda x: x[1], reverse=True)
        
        if not candidates:
            return None, 0.0, []
        
        best, score = candidates[0]
        if len(candidates) > 1 and (score - candidates[1][1]) < 0.10:
            score *= 0.9
        
        return best, score, candidates
    
    def _date_similarity(self, d1: str, d2: str) -> float:
        """Similarité entre dates."""
        if not d1 or not d2: return 0.0
        if d1 == d2: return 1.0
        if len(d1) == 8 and len(d2) == 8:
            return sum(1 for a, b in zip(d1, d2) if a == b) / 8
        return SequenceMatcher(None, d1, d2).ratio()
    
    def generate_manifest(self, output_dir: str) -> str:
        """Génère manifest.json."""
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        manifest = {
            "generated_at": datetime.now().isoformat(),
            "source_csv": self.csv_path,
            "source_pdf": self.pdf_path,
            "total_copies": len(self.results),
            "summary": {
                "validated": sum(1 for r in self.results if r.validation_status == 'VALIDATED'),
                "ambiguous": sum(1 for r in self.results if r.validation_status == 'AMBIGUOUS'),
                "manual_review": sum(1 for r in self.results if r.validation_status == 'MANUAL_REVIEW'),
                "no_match": sum(1 for r in self.results if r.validation_status == 'NO_MATCH'),
            },
            "copies": [
                {
                    "student_id": f"{r.student.last_name}_{r.student.first_name}" if r.student else None,
                    "student_name": r.student.raw_name if r.student else None,
                    "validated": r.validation_status == 'VALIDATED',
                    "page_start": r.page_start,
                    "page_end": r.page_end,
                    "validation_status": r.validation_status,
                    "metadata": {
                        "ocr_raw": {"last_name": r.ocr_extraction.last_name,
                                   "first_name": r.ocr_extraction.first_name,
                                   "date_of_birth": r.ocr_extraction.date_of_birth},
                        "csv_match_score": round(r.match_score, 3)
                    }
                }
                for r in self.results
            ]
        }
        
        manifest_path = os.path.join(output_dir, "manifest.json")
        with open(manifest_path, 'w', encoding='utf-8') as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Manifest generated: {manifest_path}")
        return manifest_path
