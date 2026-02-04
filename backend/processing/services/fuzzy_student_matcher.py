"""
Fuzzy Student Matcher for CMEN Headers.

This service uses a different approach for CMEN V2 headers with handwritten text:
1. Extract ALL text from the header using multiple OCR engines
2. Search for student names from CSV within the extracted text
3. Use fuzzy matching to handle OCR errors

This is more robust than trying to segment individual characters.

Author: Korrigo Team
PRD-19: Adapted for real CMEN V2 scans
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
class FuzzyMatchResult:
    """Result of fuzzy matching."""
    student_id: Any
    last_name: str
    first_name: str
    full_name: str
    date_of_birth: str
    email: str
    score: float
    name_found_in_text: bool
    date_found_in_text: bool
    matched_text: str


@dataclass
class HeaderExtractionResult:
    """Result of header text extraction."""
    raw_text: str
    cleaned_text: str
    detected_names: List[str]
    detected_dates: List[str]
    best_match: Optional[FuzzyMatchResult]
    all_matches: List[FuzzyMatchResult]
    confidence: float
    status: str  # AUTO_MATCH, AMBIGUOUS, NO_MATCH, FAILED


class FuzzyStudentMatcher:
    """
    Matches students from CSV against OCR text from CMEN headers.
    
    Strategy:
    1. Extract all text from header image
    2. For each student in CSV, check if their name appears in the text
    3. Score matches based on name similarity and date presence
    4. Return best match if confidence is high enough
    """
    
    # Noise words to filter out
    NOISE_WORDS = {
        'CMEN', 'NEOPTEC', 'NOM', 'FAMILLE', 'PRENOM', 'PRENOMS',
        'NUMERO', 'INSCRIPTION', 'SUIVI', 'USAGE', 'LIEU', 'CONSIGNES',
        'EPREUVE', 'MATIERE', 'SESSION', 'CONCOURS', 'EXAMEN', 'SECTION',
        'MAJUSCULES', 'CHAQUE', 'FEUILLE', 'OFFICIELLE', 'REMPLIR',
        'PAGE', 'CADRE', 'DROITE', 'STYLO', 'ENCRE', 'MODELE',
        'RIEN', 'ECRIRE', 'DANS', 'ZONE', 'IDENTIFICATION',
    }
    
    def __init__(self, students: List[Dict[str, Any]], debug: bool = False):
        """
        Args:
            students: List of student records from CSV
            debug: Enable debug logging
        """
        self.students = students
        self.debug = debug
        
        # Pre-process student names for faster matching
        self._prepare_student_index()
    
    def _prepare_student_index(self):
        """Prepare normalized student names for matching."""
        self.student_index = []
        
        for student in self.students:
            last_name = self._normalize(student.get('last_name', ''))
            first_name = self._normalize(student.get('first_name', ''))
            full_name = self._normalize(student.get('full_name', f"{last_name} {first_name}"))
            
            # Also create variants (first letter of first name, etc.)
            variants = [last_name, full_name]
            if first_name:
                variants.append(f"{last_name} {first_name[0]}")
                variants.append(f"{last_name}{first_name[0]}")
            
            self.student_index.append({
                'student': student,
                'last_name': last_name,
                'first_name': first_name,
                'full_name': full_name,
                'variants': variants,
                'date': student.get('date_of_birth', ''),
            })
    
    def _normalize(self, text: str) -> str:
        """Normalize text for matching."""
        if not text:
            return ''
        
        # Uppercase
        text = text.upper()
        
        # Remove accents
        text = unicodedata.normalize('NFD', text)
        text = ''.join(c for c in text if unicodedata.category(c) != 'Mn')
        
        # Keep only letters and spaces
        text = re.sub(r'[^A-Z\s]', '', text)
        
        # Compact spaces
        text = ' '.join(text.split())
        
        return text.strip()
    
    def extract_and_match(self, header_image: np.ndarray) -> HeaderExtractionResult:
        """
        Extract text from header and match against students.
        
        Args:
            header_image: BGR image of the header
            
        Returns:
            HeaderExtractionResult with best match
        """
        # Step 1: Extract text with multiple approaches
        raw_text = self._extract_text(header_image)
        cleaned_text = self._clean_text(raw_text)
        
        logger.debug(f"Raw text: {raw_text[:200]}")
        logger.debug(f"Cleaned text: {cleaned_text[:200]}")
        
        # Step 2: Extract potential names and dates
        detected_names = self._extract_potential_names(cleaned_text)
        detected_dates = self._extract_dates(raw_text)
        
        logger.info(f"Detected names: {detected_names[:5]}")
        logger.info(f"Detected dates: {detected_dates}")
        
        # Step 3: Match against students
        matches = self._match_students(cleaned_text, detected_dates)
        
        # Step 4: Determine result
        if not matches:
            return HeaderExtractionResult(
                raw_text=raw_text,
                cleaned_text=cleaned_text,
                detected_names=detected_names,
                detected_dates=detected_dates,
                best_match=None,
                all_matches=[],
                confidence=0.0,
                status="NO_MATCH"
            )
        
        best = matches[0]
        second = matches[1] if len(matches) > 1 else None
        
        margin = best.score - (second.score if second else 0)
        
        # Determine status based on confidence and margin
        if best.score >= 0.70 and margin >= 0.10:
            status = "AUTO_MATCH"
            confidence = best.score
        elif best.score >= 0.50:
            status = "AMBIGUOUS"
            confidence = best.score
        else:
            status = "NO_MATCH"
            confidence = best.score
        
        logger.info(f"Best match: {best.full_name} (score={best.score:.3f}, margin={margin:.3f})")
        
        return HeaderExtractionResult(
            raw_text=raw_text,
            cleaned_text=cleaned_text,
            detected_names=detected_names,
            detected_dates=detected_dates,
            best_match=best if status != "NO_MATCH" else None,
            all_matches=matches[:10],
            confidence=confidence,
            status=status
        )
    
    def _extract_text(self, image: np.ndarray) -> str:
        """Extract text from image using multiple OCR approaches."""
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()
        
        texts = []
        
        # Approach 1: Standard OCR
        try:
            text1 = pytesseract.image_to_string(gray, lang='fra', config='--psm 6')
            texts.append(text1)
        except Exception as e:
            logger.warning(f"OCR approach 1 failed: {e}")
        
        # Approach 2: With CLAHE enhancement
        try:
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            enhanced = clahe.apply(gray)
            text2 = pytesseract.image_to_string(enhanced, lang='fra', config='--psm 6')
            texts.append(text2)
        except Exception as e:
            logger.warning(f"OCR approach 2 failed: {e}")
        
        # Approach 3: With binarization
        try:
            _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            text3 = pytesseract.image_to_string(binary, lang='fra', config='--psm 6')
            texts.append(text3)
        except Exception as e:
            logger.warning(f"OCR approach 3 failed: {e}")
        
        # Combine all texts
        return '\n'.join(texts)
    
    def _clean_text(self, text: str) -> str:
        """Clean OCR text for matching."""
        # Uppercase
        text = text.upper()
        
        # Remove accents
        text = unicodedata.normalize('NFD', text)
        text = ''.join(c for c in text if unicodedata.category(c) != 'Mn')
        
        # Remove noise words
        words = text.split()
        words = [w for w in words if w not in self.NOISE_WORDS]
        
        return ' '.join(words)
    
    def _extract_potential_names(self, text: str) -> List[str]:
        """Extract potential names from text."""
        # Find sequences of uppercase letters (potential names)
        names = re.findall(r'[A-Z]{3,}', text)
        
        # Filter out noise
        names = [n for n in names if n not in self.NOISE_WORDS and len(n) >= 3]
        
        return names
    
    def _extract_dates(self, text: str) -> List[str]:
        """Extract dates from text."""
        patterns = [
            r'(\d{1,2})\s*[/\-\.]\s*(\d{1,2})\s*[/\-\.]\s*(\d{2,4})',
            r'(\d{2})(\d{2})(\d{4})',  # DDMMYYYY without separators
        ]
        
        dates = []
        for pattern in patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                day, month, year = match
                day = day.zfill(2)
                month = month.zfill(2)
                if len(year) == 2:
                    year = '20' + year if int(year) < 50 else '19' + year
                
                try:
                    d, m, y = int(day), int(month), int(year)
                    if 1 <= d <= 31 and 1 <= m <= 12 and 1900 <= y <= 2025:
                        dates.append(f"{day}/{month}/{year}")
                except ValueError:
                    pass
        
        return list(set(dates))
    
    def _match_students(self, text: str, detected_dates: List[str]) -> List[FuzzyMatchResult]:
        """Match students against extracted text."""
        matches = []
        
        for entry in self.student_index:
            student = entry['student']
            
            # Check if name appears in text
            name_score = 0.0
            name_found = False
            matched_text = ""
            
            for variant in entry['variants']:
                if not variant:
                    continue
                
                # Direct substring match
                if variant in text:
                    name_score = max(name_score, 0.9)
                    name_found = True
                    matched_text = variant
                    break
                
                # Fuzzy match
                ratio = self._fuzzy_match_in_text(variant, text)
                if ratio > name_score:
                    name_score = ratio
                    if ratio > 0.7:
                        name_found = True
                        matched_text = variant
            
            # Check date
            date_score = 0.0
            date_found = False
            student_date = entry['date']
            
            if student_date:
                student_date_clean = re.sub(r'[^\d]', '', student_date)
                
                for detected_date in detected_dates:
                    detected_clean = re.sub(r'[^\d]', '', detected_date)
                    
                    if student_date_clean == detected_clean:
                        date_score = 1.0
                        date_found = True
                        break
                    elif len(student_date_clean) == 8 and len(detected_clean) == 8:
                        # Count matching digits
                        matching = sum(1 for a, b in zip(student_date_clean, detected_clean) if a == b)
                        ratio = matching / 8
                        if ratio > date_score:
                            date_score = ratio
                            if ratio >= 0.75:
                                date_found = True
            
            # Combined score
            # Date is very important for disambiguation
            if name_found and date_found:
                total_score = 0.4 * name_score + 0.6 * date_score
            elif name_found:
                total_score = 0.7 * name_score
            elif date_found:
                total_score = 0.5 * date_score
            else:
                total_score = 0.3 * name_score + 0.2 * date_score
            
            if total_score > 0.1:
                matches.append(FuzzyMatchResult(
                    student_id=student.get('id'),
                    last_name=student.get('last_name', ''),
                    first_name=student.get('first_name', ''),
                    full_name=student.get('full_name', ''),
                    date_of_birth=student.get('date_of_birth', ''),
                    email=student.get('email', ''),
                    score=total_score,
                    name_found_in_text=name_found,
                    date_found_in_text=date_found,
                    matched_text=matched_text
                ))
        
        # Sort by score
        matches.sort(key=lambda x: x.score, reverse=True)
        
        return matches
    
    def _fuzzy_match_in_text(self, pattern: str, text: str) -> float:
        """Find best fuzzy match of pattern in text."""
        if not pattern or not text:
            return 0.0
        
        pattern_len = len(pattern)
        best_ratio = 0.0
        
        # Slide window over text
        words = text.split()
        
        # Check individual words
        for word in words:
            if len(word) >= pattern_len - 2:
                ratio = SequenceMatcher(None, pattern, word).ratio()
                best_ratio = max(best_ratio, ratio)
        
        # Check word combinations
        for i in range(len(words)):
            for j in range(i + 1, min(i + 4, len(words) + 1)):
                combined = ''.join(words[i:j])
                if len(combined) >= pattern_len - 2:
                    ratio = SequenceMatcher(None, pattern, combined).ratio()
                    best_ratio = max(best_ratio, ratio)
        
        return best_ratio


def process_pdf_with_fuzzy_matcher(pdf_path: str, csv_students: List[Dict], 
                                    output_dir: str = None) -> List[Dict]:
    """
    Process a PDF using fuzzy student matching.
    
    Args:
        pdf_path: Path to PDF file
        csv_students: List of student records from CSV
        output_dir: Optional output directory for debug images
        
    Returns:
        List of results per page
    """
    import fitz
    from pathlib import Path
    
    if output_dir:
        Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    doc = fitz.open(pdf_path)
    matcher = FuzzyStudentMatcher(csv_students, debug=True)
    
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
            
            # Match
            result = matcher.extract_and_match(header)
            
            results.append({
                'page_num': page_num,
                'page_name': page_name,
                'status': result.status,
                'confidence': result.confidence,
                'best_match': result.best_match,
                'all_matches': result.all_matches[:5],
                'detected_dates': result.detected_dates,
            })
            
            if output_dir:
                cv2.imwrite(f"{output_dir}/{page_name}_header.png", header)
            
            match_info = f"✓ {result.best_match.full_name}" if result.best_match else "✗"
            logger.info(f"Page {page_num} ({page_name}): {result.status} - {match_info}")
    
    doc.close()
    return results
