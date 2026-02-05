"""
CMEN V2 Text-Based OCR Service.

This module implements OCR for CMEN V2 NEOPTEC headers using text extraction
rather than grid-based cell recognition. Adapted for real scanned documents
where handwritten text in boxes is recognized as continuous text.

The CMEN V2 header structure:
- Line 1: "Nom de famille:" followed by handwritten name in boxes
- Line 2: "Prénom(s):" followed by handwritten first name in boxes
- Line 3: "Numéro Inscription:" and "Né(e) le:" with date DD/MM/YYYY

Author: Korrigo Team
PRD-19: Adapted OCR for real CMEN V2 scans
"""
import cv2
import numpy as np
import pytesseract
import re
import unicodedata
import logging
from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple, Any
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)


@dataclass
class CMENTextOCRResult:
    """Result of CMEN text-based OCR extraction."""
    last_name: str
    first_name: str
    date_of_birth: str
    raw_text: str
    confidence: float
    status: str  # OK, PARTIAL, FAILED


@dataclass
class StudentMatch:
    """A matched student from the whitelist."""
    student_id: Any
    last_name: str
    first_name: str
    full_name: str
    date_of_birth: str
    email: str
    score: float
    name_score: float
    date_score: float


class CMENTextOCRService:
    """
    OCR service for CMEN V2 headers using text extraction.
    
    This service is designed for real scanned CMEN V2 documents where
    handwritten text appears in individual boxes but is recognized
    as continuous text by OCR.
    
    Strategy: Extract all text from header, then use fuzzy matching
    against the student CSV to find the best match. The CSV acts as
    a closed-world whitelist.
    """
    
    # Regions in the header (as percentage of header height)
    # Calibrated for CMEN V2 NEOPTEC format
    REGIONS = {
        'nom': {'y_start': 0.12, 'y_end': 0.40, 'x_start': 0.15, 'x_end': 0.95},
        'prenom': {'y_start': 0.35, 'y_end': 0.55, 'x_start': 0.15, 'x_end': 0.70},
        'date': {'y_start': 0.35, 'y_end': 0.65, 'x_start': 0.70, 'x_end': 0.98},
    }
    
    # Known noise patterns to filter out
    NOISE_PATTERNS = [
        'CMEN', 'NEOPTEC', 'NOM', 'FAMILLE', 'PRENOM', 'PRENOMS',
        'NUMERO', 'INSCRIPTION', 'SUIVI', 'USAGE', 'LIEU', 'CONSIGNES',
        'EPREUVE', 'MATIERE', 'SESSION', 'CONCOURS', 'EXAMEN', 'SECTION',
        'MAJUSCULES', 'CHAQUE', 'FEUILLE', 'OFFICIELLE', 'REMPLIR',
        'PAGE', 'CADRE', 'DROITE', 'STYLO', 'ENCRE', 'MODELE',
    ]
    
    def __init__(self, debug: bool = False):
        self.debug = debug
    
    def extract_from_header(self, header_image: np.ndarray) -> CMENTextOCRResult:
        """
        Extract student information from a CMEN V2 header image.
        
        Args:
            header_image: BGR image of the header (top ~25% of page)
            
        Returns:
            CMENTextOCRResult with extracted fields
        """
        logger.info("Starting CMEN text-based OCR extraction...")
        
        # Convert to grayscale
        if len(header_image.shape) == 3:
            gray = cv2.cvtColor(header_image, cv2.COLOR_BGR2GRAY)
        else:
            gray = header_image.copy()
        
        h, w = gray.shape
        
        # Get full text first for context
        raw_text = self._ocr_region(gray, 0, 0, w, h)
        logger.debug(f"Raw header text: {raw_text[:200]}")
        
        # Extract each field
        last_name = self._extract_name(gray, raw_text)
        first_name = self._extract_first_name(gray, raw_text)
        date_of_birth = self._extract_date(gray, raw_text)
        
        # Calculate confidence
        confidence = self._calculate_confidence(last_name, first_name, date_of_birth)
        
        # Determine status
        if last_name and date_of_birth:
            status = "OK"
        elif last_name or first_name or date_of_birth:
            status = "PARTIAL"
        else:
            status = "FAILED"
        
        logger.info(f"Extracted: name='{last_name}', firstname='{first_name}', "
                   f"dob='{date_of_birth}', confidence={confidence:.2f}")
        
        return CMENTextOCRResult(
            last_name=last_name,
            first_name=first_name,
            date_of_birth=date_of_birth,
            raw_text=raw_text,
            confidence=confidence,
            status=status
        )
    
    def _ocr_region(self, gray: np.ndarray, x: int, y: int, w: int, h: int) -> str:
        """Apply OCR to a specific region."""
        region = gray[y:y+h, x:x+w]
        
        # Preprocessing
        # Apply CLAHE for better contrast
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(region)
        
        # Adaptive threshold
        binary = cv2.adaptiveThreshold(
            enhanced, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY, 11, 2
        )
        
        # OCR
        try:
            text = pytesseract.image_to_string(binary, lang='fra', config='--psm 6')
            return text
        except Exception as e:
            logger.warning(f"OCR failed: {e}")
            return ""
    
    def _extract_name(self, gray: np.ndarray, raw_text: str) -> str:
        """Extract last name from header."""
        h, w = gray.shape
        
        # Method 1: Look for pattern after "Nom de famille"
        name_match = re.search(
            r'Nom\s*de\s*famille\s*[:\s]*([A-ZÉÈÊËÀÂÄÙÛÜÔÖÎÏÇ\s\-]+)',
            raw_text, re.IGNORECASE
        )
        if name_match:
            name = name_match.group(1).strip()
            name = self._clean_name(name)
            if len(name) >= 2:
                return name
        
        # Method 2: Extract from specific region with multiple OCR attempts
        region = self.REGIONS['nom']
        x1 = int(w * region['x_start'])
        x2 = int(w * region['x_end'])
        y1 = int(h * region['y_start'])
        y2 = int(h * region['y_end'])
        
        region_img = gray[y1:y2, x1:x2]
        
        # Try multiple preprocessing approaches
        candidates = []
        
        # Approach 1: Standard OCR
        region_text = self._ocr_region(gray, x1, y1, x2-x1, y2-y1)
        caps_matches = re.findall(r'[A-ZÉÈÊËÀÂÄÙÛÜÔÖÎÏÇ]{2,}', region_text)
        for match in caps_matches:
            if match not in ['CMEN', 'NEOPTEC', 'NOM', 'FAMILLE', 'PRENOM', 'SUIVI', 'USAGE', 'LIEU']:
                candidates.append(match)
        
        # Approach 2: Try with inverted image
        _, binary = cv2.threshold(region_img, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        text2 = pytesseract.image_to_string(binary, lang='fra', config='--psm 6 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ')
        caps2 = re.findall(r'[A-Z]{2,}', text2)
        for match in caps2:
            if match not in ['CMEN', 'NEOPTEC', 'NOM', 'FAMILLE', 'PRENOM'] and match not in candidates:
                candidates.append(match)
        
        # Approach 3: Try with CLAHE enhancement
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(region_img)
        text3 = pytesseract.image_to_string(enhanced, lang='fra', config='--psm 6')
        caps3 = re.findall(r'[A-Z]{2,}', text3)
        for match in caps3:
            if match not in ['CMEN', 'NEOPTEC', 'NOM', 'FAMILLE', 'PRENOM'] and match not in candidates:
                candidates.append(match)
        
        # Return the longest valid candidate
        valid_candidates = [c for c in candidates if len(c) >= 3]
        if valid_candidates:
            return self._clean_name(max(valid_candidates, key=len))
        
        return ""
    
    def _extract_first_name(self, gray: np.ndarray, raw_text: str) -> str:
        """Extract first name from header."""
        h, w = gray.shape
        
        # Method 1: Look for pattern after "Prénom"
        prenom_match = re.search(
            r'Pr[ée]nom[s]?\s*[:\s]*([A-ZÉÈÊËÀÂÄÙÛÜÔÖÎÏÇ][a-zéèêëàâäùûüôöîïç\-]+)',
            raw_text, re.IGNORECASE
        )
        if prenom_match:
            name = prenom_match.group(1).strip()
            return self._clean_name(name)
        
        # Method 2: Extract from specific region
        region = self.REGIONS['prenom']
        x1 = int(w * region['x_start'])
        x2 = int(w * region['x_end'])
        y1 = int(h * region['y_start'])
        y2 = int(h * region['y_end'])
        
        region_text = self._ocr_region(gray, x1, y1, x2-x1, y2-y1)
        
        # Look for capitalized words
        word_matches = re.findall(r'[A-ZÉÈÊËÀÂÄÙÛÜÔÖÎÏÇ][a-zéèêëàâäùûüôöîïç]+', region_text)
        for match in word_matches:
            if match.lower() not in ['prenom', 'prenoms', 'nom', 'famille', 'numero']:
                return self._clean_name(match)
        
        return ""
    
    def _extract_date(self, gray: np.ndarray, raw_text: str) -> str:
        """Extract date of birth from header."""
        # Method 1: Look for date pattern in raw text
        # Format: DD/MM/YYYY or DD/MM/YY
        date_patterns = [
            r'N[ée]\s*\(?e?\)?\s*le\s*[:\s]*(\d{1,2})\s*[/\-\.]\s*(\d{1,2})\s*[/\-\.]\s*(\d{2,4})',
            r'(\d{1,2})\s*[/\-\.]\s*(\d{1,2})\s*[/\-\.]\s*((?:19|20)\d{2})',
            r'(\d{1,2})\s*[/\-\.]\s*(\d{1,2})\s*[/\-\.]\s*(\d{2})',
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, raw_text, re.IGNORECASE)
            if match:
                day, month, year = match.groups()
                day = day.zfill(2)
                month = month.zfill(2)
                if len(year) == 2:
                    year = '20' + year if int(year) < 50 else '19' + year
                
                # Validate
                try:
                    d, m, y = int(day), int(month), int(year)
                    if 1 <= d <= 31 and 1 <= m <= 12 and 1900 <= y <= 2025:
                        return f"{day}/{month}/{year}"
                except ValueError:
                    pass
        
        # Method 2: Extract from date region
        h, w = gray.shape
        region = self.REGIONS['date']
        x1 = int(w * region['x_start'])
        x2 = int(w * region['x_end'])
        y1 = int(h * region['y_start'])
        y2 = int(h * region['y_end'])
        
        region_text = self._ocr_region(gray, x1, y1, x2-x1, y2-y1)
        
        for pattern in date_patterns:
            match = re.search(pattern, region_text, re.IGNORECASE)
            if match:
                day, month, year = match.groups()
                day = day.zfill(2)
                month = month.zfill(2)
                if len(year) == 2:
                    year = '20' + year if int(year) < 50 else '19' + year
                
                try:
                    d, m, y = int(day), int(month), int(year)
                    if 1 <= d <= 31 and 1 <= m <= 12 and 1900 <= y <= 2025:
                        return f"{day}/{month}/{year}"
                except ValueError:
                    pass
        
        return ""
    
    def _clean_name(self, name: str) -> str:
        """Clean and normalize a name."""
        if not name:
            return ""
        
        # Remove non-alphabetic characters except space and hyphen
        name = re.sub(r'[^A-Za-zÀ-ÿ\s\-]', '', name)
        
        # Normalize spaces
        name = ' '.join(name.split())
        
        # Uppercase
        name = name.upper()
        
        # Remove accents for matching
        name = unicodedata.normalize('NFD', name)
        name = ''.join(c for c in name if unicodedata.category(c) != 'Mn')
        
        return name.strip()
    
    def _calculate_confidence(self, last_name: str, first_name: str, date: str) -> float:
        """Calculate overall confidence score."""
        score = 0.0
        
        if last_name and len(last_name) >= 2:
            score += 0.4
        if first_name and len(first_name) >= 2:
            score += 0.2
        if date and re.match(r'\d{2}/\d{2}/\d{4}', date):
            score += 0.4
        
        return score
    
    def match_student(self, 
                      ocr_result: CMENTextOCRResult,
                      students: List[Dict[str, Any]],
                      threshold: float = 0.60,
                      margin: float = 0.08) -> Tuple[Optional[StudentMatch], List[StudentMatch]]:
        """
        Match OCR result against student whitelist.
        
        Args:
            ocr_result: Result from extract_from_header()
            students: List of student records
            threshold: Minimum score for auto-match
            margin: Minimum margin between best and second-best
            
        Returns:
            Tuple of (best_match or None, all_candidates)
        """
        if not students or ocr_result.status == "FAILED":
            return None, []
        
        candidates = []
        
        for student in students:
            # Get student data
            s_last = self._clean_name(student.get('last_name', ''))
            s_first = self._clean_name(student.get('first_name', ''))
            s_full = student.get('full_name', f"{s_last} {s_first}")
            s_date = student.get('date_of_birth', '')
            
            # Calculate name similarity
            ocr_name = ocr_result.last_name
            ocr_first = ocr_result.first_name
            ocr_full = f"{ocr_name} {ocr_first}".strip()
            
            # Try matching full name
            name_score = max(
                self._similarity(ocr_name, s_last),
                self._similarity(ocr_full, self._clean_name(s_full)),
                self._similarity(ocr_name, self._clean_name(s_full.split()[0])) if s_full else 0
            )
            
            # Calculate date similarity
            date_score = self._date_similarity(ocr_result.date_of_birth, s_date)
            
            # Combined score (date is more important for disambiguation)
            total_score = 0.45 * name_score + 0.55 * date_score
            
            candidates.append(StudentMatch(
                student_id=student.get('id'),
                last_name=student.get('last_name', ''),
                first_name=student.get('first_name', ''),
                full_name=s_full,
                date_of_birth=s_date,
                email=student.get('email', ''),
                score=total_score,
                name_score=name_score,
                date_score=date_score
            ))
        
        # Sort by score
        candidates.sort(key=lambda x: x.score, reverse=True)
        
        # Check if best match meets threshold and margin
        if candidates:
            best = candidates[0]
            second = candidates[1] if len(candidates) > 1 else None
            
            actual_margin = best.score - (second.score if second else 0)
            
            if best.score >= threshold and actual_margin >= margin:
                logger.info(f"Match found: {best.full_name} (score={best.score:.3f}, margin={actual_margin:.3f})")
                return best, candidates[:10]
            else:
                logger.info(f"No confident match: best={best.full_name} (score={best.score:.3f}, margin={actual_margin:.3f})")
        
        return None, candidates[:10]
    
    def _similarity(self, s1: str, s2: str) -> float:
        """Calculate string similarity."""
        if not s1 or not s2:
            return 0.0
        if s1 == s2:
            return 1.0
        return SequenceMatcher(None, s1, s2).ratio()
    
    def _date_similarity(self, d1: str, d2: str) -> float:
        """Calculate date similarity."""
        if not d1 or not d2:
            return 0.0
        
        # Normalize dates
        d1_clean = re.sub(r'[^\d]', '', d1)
        d2_clean = re.sub(r'[^\d]', '', d2)
        
        if d1_clean == d2_clean:
            return 1.0
        
        if len(d1_clean) == 8 and len(d2_clean) == 8:
            # Count matching digits
            matches = sum(1 for a, b in zip(d1_clean, d2_clean) if a == b)
            return matches / 8
        
        return self._similarity(d1_clean, d2_clean)


def process_pdf_with_text_ocr(pdf_path: str, csv_students: List[Dict], output_dir: str = None):
    """
    Process a PDF using text-based OCR.
    
    Args:
        pdf_path: Path to PDF file
        csv_students: List of student records from CSV
        output_dir: Optional output directory for debug images
        
    Returns:
        List of (page_number, ocr_result, match) tuples
    """
    import fitz
    from pathlib import Path
    
    if output_dir:
        Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    doc = fitz.open(pdf_path)
    service = CMENTextOCRService(debug=True)
    
    results = []
    dpi = 200
    
    # Check if A3
    page = doc.load_page(0)
    ratio = page.rect.width / page.rect.height
    is_a3 = ratio > 1.2
    
    logger.info(f"Processing PDF: {doc.page_count} pages, format={'A3' if is_a3 else 'A4'}")
    
    page_num = 0
    for page_idx in range(doc.page_count):
        page = doc.load_page(page_idx)
        mat = fitz.Matrix(dpi / 72, dpi / 72)
        pix = page.get_pixmap(matrix=mat)
        
        img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
        if pix.n == 3:
            img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
        elif pix.n == 4:
            img = cv2.cvtColor(img, cv2.COLOR_RGBA2BGR)
        
        pages_to_process = []
        
        if is_a3:
            mid_x = img.shape[1] // 2
            pages_to_process = [
                (img[:, :mid_x], f"A3_{page_idx+1}_left"),
                (img[:, mid_x:], f"A3_{page_idx+1}_right")
            ]
        else:
            pages_to_process = [(img, f"A4_{page_idx+1}")]
        
        for page_img, page_name in pages_to_process:
            page_num += 1
            
            # Extract header (top 25%)
            header_h = int(page_img.shape[0] * 0.25)
            header = page_img[:header_h, :]
            
            # Run OCR
            ocr_result = service.extract_from_header(header)
            
            # Match against students
            match, candidates = service.match_student(ocr_result, csv_students)
            
            results.append({
                'page_num': page_num,
                'page_name': page_name,
                'ocr_result': ocr_result,
                'match': match,
                'candidates': candidates[:5]
            })
            
            if output_dir:
                cv2.imwrite(f"{output_dir}/{page_name}_header.png", header)
            
            logger.info(f"Page {page_num} ({page_name}): "
                       f"name='{ocr_result.last_name}', "
                       f"match={'✓ ' + match.full_name if match else '✗'}")
    
    doc.close()
    return results
