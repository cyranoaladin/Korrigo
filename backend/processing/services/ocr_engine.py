"""
Multi-layer OCR Engine for robust text extraction from handwritten forms.

PRD-19: OCR Robustification
- Multiple OCR engines (Tesseract, EasyOCR, PaddleOCR)
- Enhanced preprocessing (deskew, denoising, binarization)
- Consensus voting for top-k candidates
"""
import logging
import re
import unicodedata
from collections import defaultdict
from dataclasses import dataclass
from typing import List, Optional, Tuple

import cv2
import numpy as np
import pytesseract

logger = logging.getLogger(__name__)


@dataclass
class OCRCandidate:
    """Single OCR result from one engine on one image variant."""
    engine: str  # 'tesseract', 'easyocr', 'paddleocr'
    variant: int  # Preprocessing variant index
    text: str  # Raw OCR text
    confidence: float  # Engine-reported confidence (0.0-1.0)


@dataclass
class StudentMatch:
    """Matched student from CSV whitelist with confidence."""
    student_id: int
    first_name: str
    last_name: str
    email: str
    date_of_birth: str
    confidence: float  # Consensus confidence (0.0-1.0)
    vote_count: int  # Number of OCR engines that voted for this student
    vote_agreement: float  # Proportion of engines agreeing (0.0-1.0)
    sources: List[dict]  # OCR sources that contributed [{engine, variant, text, score}]


@dataclass
class OCRResult:
    """Complete OCR result with top-k student candidates."""
    top_candidates: List[StudentMatch]
    ocr_mode: str  # 'AUTO', 'SEMI_AUTO', 'MANUAL'
    all_ocr_outputs: List[OCRCandidate]  # All raw OCR results for debugging


class ImagePreprocessor:
    """Advanced preprocessing for handwritten forms."""

    def preprocess_variants(self, image: np.ndarray) -> List[np.ndarray]:
        """
        Generate multiple preprocessing variants for robust OCR.

        Returns list of preprocessed images to run through OCR engines.
        """
        variants = []

        # Convert to grayscale if needed
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()

        # Variant 1: Deskew + Otsu binarization
        try:
            deskewed = self._deskew(gray)
            binary_otsu = cv2.threshold(deskewed, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
            variants.append(binary_otsu)
        except Exception as e:
            logger.warning(f"Deskew variant failed: {e}")

        # Variant 2: Denoising + CLAHE (enhanced contrast)
        try:
            denoised = cv2.fastNlMeansDenoising(gray, h=10)
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            enhanced = clahe.apply(denoised)
            variants.append(enhanced)
        except Exception as e:
            logger.warning(f"CLAHE variant failed: {e}")

        # Variant 3: Morphological cleanup
        try:
            morph_cleaned = self._morphological_cleanup(gray)
            variants.append(morph_cleaned)
        except Exception as e:
            logger.warning(f"Morphological variant failed: {e}")

        # Variant 4: Adaptive thresholding (existing approach)
        try:
            adaptive = cv2.adaptiveThreshold(
                gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
            )
            variants.append(adaptive)
        except Exception as e:
            logger.warning(f"Adaptive threshold variant failed: {e}")

        # If all variants failed, return original grayscale
        if not variants:
            logger.warning("All preprocessing variants failed, using grayscale")
            variants.append(gray)

        return variants

    def _deskew(self, image: np.ndarray) -> np.ndarray:
        """Detect and correct skew angle using Hough transform."""
        # Threshold image
        thresh = cv2.threshold(image, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]

        # Find coordinates of non-zero pixels
        coords = np.column_stack(np.where(thresh > 0))

        if len(coords) == 0:
            return image

        # Calculate minimum area rectangle
        angle = cv2.minAreaRect(coords)[-1]

        # Correct angle
        if angle < -45:
            angle = -(90 + angle)
        else:
            angle = -angle

        # Only deskew if angle is significant (> 0.5 degrees)
        if abs(angle) < 0.5:
            return image

        # Rotate image
        (h, w) = image.shape[:2]
        center = (w // 2, h // 2)
        M = cv2.getRotationMatrix2D(center, angle, 1.0)
        rotated = cv2.warpAffine(
            image, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE
        )

        return rotated

    def _morphological_cleanup(self, image: np.ndarray) -> np.ndarray:
        """Remove noise using morphological operations."""
        # Binarize
        binary = cv2.threshold(image, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]

        # Remove small noise with opening
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
        opening = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel, iterations=1)

        # Fill small holes with closing
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        closing = cv2.morphologyEx(opening, cv2.MORPH_CLOSE, kernel, iterations=1)

        return closing


class MultiLayerOCR:
    """
    Multi-layer OCR engine combining Tesseract, EasyOCR, and PaddleOCR.

    Uses consensus voting to select best student match from CSV whitelist.
    """

    def __init__(self):
        self.preprocessor = ImagePreprocessor()

        # Initialize OCR engines (lazy loading)
        self._easyocr_reader = None
        self._paddleocr_engine = None

    def _get_easyocr(self):
        """Lazy load EasyOCR (downloads models on first use)."""
        if self._easyocr_reader is None:
            try:
                import easyocr
                self._easyocr_reader = easyocr.Reader(['fr', 'en'], gpu=False, verbose=False)
                logger.info("EasyOCR loaded successfully")
            except ImportError:
                logger.warning("EasyOCR not available, skipping")
            except Exception as e:
                logger.error(f"Failed to load EasyOCR: {e}")
        return self._easyocr_reader

    def _get_paddleocr(self):
        """Lazy load PaddleOCR (downloads models on first use)."""
        if self._paddleocr_engine is None:
            try:
                from paddleocr import PaddleOCR
                self._paddleocr_engine = PaddleOCR(
                    lang='fr', use_angle_cls=True, use_gpu=False, show_log=False
                )
                logger.info("PaddleOCR loaded successfully")
            except ImportError:
                logger.warning("PaddleOCR not available, skipping")
            except Exception as e:
                logger.error(f"Failed to load PaddleOCR: {e}")
        return self._paddleocr_engine

    def extract_text_with_candidates(
        self, header_image: np.ndarray, csv_whitelist: List[dict]
    ) -> OCRResult:
        """
        Extract text using multiple OCR engines and match against CSV whitelist.

        Args:
            header_image: Header region image (BGR or grayscale)
            csv_whitelist: List of student dicts with keys: id, first_name, last_name, email, date_of_birth

        Returns:
            OCRResult with top-k student candidates and OCR mode
        """
        # Generate preprocessing variants
        variants = self.preprocessor.preprocess_variants(header_image)
        logger.info(f"Generated {len(variants)} preprocessing variants")

        # Run all OCR engines on all variants
        ocr_candidates = self._run_all_ocr_engines(variants)
        logger.info(f"Collected {len(ocr_candidates)} OCR candidates")

        # Consensus voting to match students
        top_matches = self._consensus_vote(ocr_candidates, csv_whitelist)

        # Determine OCR mode based on top candidate confidence
        if top_matches and top_matches[0].confidence > 0.7:
            ocr_mode = 'AUTO'
        elif top_matches and top_matches[0].confidence > 0.4:
            ocr_mode = 'SEMI_AUTO'
        else:
            ocr_mode = 'MANUAL'

        return OCRResult(
            top_candidates=top_matches,
            ocr_mode=ocr_mode,
            all_ocr_outputs=ocr_candidates
        )

    def _run_all_ocr_engines(self, preprocessed_images: List[np.ndarray]) -> List[OCRCandidate]:
        """Run all available OCR engines on all image variants."""
        candidates = []

        for variant_idx, img in enumerate(preprocessed_images):
            # Tesseract
            try:
                text = self._ocr_tesseract(img)
                confidence = self._estimate_tesseract_confidence(text)
                candidates.append(OCRCandidate(
                    engine='tesseract',
                    variant=variant_idx,
                    text=text,
                    confidence=confidence
                ))
            except Exception as e:
                logger.warning(f"Tesseract failed on variant {variant_idx}: {e}")

            # EasyOCR
            try:
                reader = self._get_easyocr()
                if reader:
                    results = reader.readtext(img, detail=1)
                    text = ' '.join([res[1] for res in results])
                    confidence = sum([res[2] for res in results]) / len(results) if results else 0.0
                    candidates.append(OCRCandidate(
                        engine='easyocr',
                        variant=variant_idx,
                        text=text,
                        confidence=confidence
                    ))
            except Exception as e:
                logger.warning(f"EasyOCR failed on variant {variant_idx}: {e}")

            # PaddleOCR
            try:
                paddle = self._get_paddleocr()
                if paddle:
                    results = paddle.ocr(img, cls=True)
                    if results and results[0]:
                        text = ' '.join([line[1][0] for line in results[0]])
                        confidence = sum([line[1][1] for line in results[0]]) / len(results[0])
                        candidates.append(OCRCandidate(
                            engine='paddleocr',
                            variant=variant_idx,
                            text=text,
                            confidence=confidence
                        ))
            except Exception as e:
                logger.warning(f"PaddleOCR failed on variant {variant_idx}: {e}")

        return candidates

    def _ocr_tesseract(self, image: np.ndarray) -> str:
        """Run Tesseract OCR (existing approach)."""
        config = '--psm 6'  # Assume single uniform block of text
        text = pytesseract.image_to_string(image, lang='fra', config=config)
        return text.strip()

    def _estimate_tesseract_confidence(self, text: str) -> float:
        """
        Estimate Tesseract confidence based on text quality.

        Heuristics:
        - Length > 10: likely has content
        - Has letters and numbers: good mix
        - Not too much garbage (special chars)
        """
        if not text or len(text) < 5:
            return 0.1

        has_letters = bool(re.search(r'[a-zA-Z]', text))
        has_numbers = bool(re.search(r'\d', text))
        special_char_ratio = len(re.findall(r'[^a-zA-Z0-9\s/-]', text)) / len(text)

        confidence = 0.5  # Base confidence
        if has_letters:
            confidence += 0.2
        if has_numbers:
            confidence += 0.1
        if special_char_ratio < 0.2:
            confidence += 0.2

        return min(confidence, 1.0)

    def _consensus_vote(
        self, ocr_candidates: List[OCRCandidate], csv_whitelist: List[dict]
    ) -> List[StudentMatch]:
        """
        Consensus voting: match each OCR candidate against CSV, aggregate scores.

        Returns top-5 student matches sorted by consensus confidence.
        """
        student_scores = defaultdict(lambda: {
            'total_score': 0.0,
            'vote_count': 0,
            'ocr_sources': []
        })

        for candidate in ocr_candidates:
            # Parse name + date from OCR text
            name, date = self._parse_ocr_text(candidate.text)

            # Skip if no name detected
            if not name:
                continue

            # Fuzzy match against CSV
            for student in csv_whitelist:
                match_score = self._fuzzy_match_student(
                    name, date, student['first_name'], student['last_name'], student.get('date_of_birth')
                )

                if match_score > 0.3:  # Lower threshold for voting
                    student_id = student['id']
                    # Weight by OCR engine confidence
                    weighted_score = match_score * candidate.confidence

                    student_scores[student_id]['total_score'] += weighted_score
                    student_scores[student_id]['vote_count'] += 1
                    student_scores[student_id]['ocr_sources'].append({
                        'engine': candidate.engine,
                        'variant': candidate.variant,
                        'text': candidate.text,
                        'score': weighted_score
                    })

        # Calculate final consensus confidence
        top_k_matches = []
        num_candidates = len(ocr_candidates) if ocr_candidates else 1

        for student_id, data in sorted(
            student_scores.items(), key=lambda x: x[1]['total_score'], reverse=True
        )[:5]:  # Top 5
            # Find student in whitelist
            student = next((s for s in csv_whitelist if s['id'] == student_id), None)
            if not student:
                continue

            consensus_confidence = data['total_score'] / num_candidates
            vote_agreement = data['vote_count'] / num_candidates

            top_k_matches.append(StudentMatch(
                student_id=student_id,
                first_name=student['first_name'],
                last_name=student['last_name'],
                email=student['email'],
                date_of_birth=student.get('date_of_birth', ''),
                confidence=consensus_confidence,
                vote_count=data['vote_count'],
                vote_agreement=vote_agreement,
                sources=data['ocr_sources']
            ))

        return top_k_matches

    def _parse_ocr_text(self, text: str) -> Tuple[str, str]:
        """
        Parse OCR text to extract name and date of birth.

        Returns:
            (name, date) tuple
        """
        # Extract name (uppercase letters, including accented characters)
        # Normalize text to handle accented uppercase letters (ÉMILIE, etc.)
        import unicodedata
        normalized_text = unicodedata.normalize('NFKD', text)

        # Match uppercase letters including accented characters
        name_pattern = r'[A-ZÀ-ÿ][A-ZÀ-ÿ\s-]+'
        name_matches = re.findall(name_pattern, text)  # Use original text to preserve accents
        name = ' '.join(name_matches).strip() if name_matches else ''

        # Extract date (DD/MM/YYYY or DD-MM-YYYY or DD.MM.YYYY)
        date_pattern = r'\b(\d{1,2})[/.-](\d{1,2})[/.-](\d{2,4})\b'
        date_match = re.search(date_pattern, text)
        date = ''
        if date_match:
            day, month, year = date_match.groups()
            # Normalize to DD/MM/YYYY
            day = day.zfill(2)
            month = month.zfill(2)
            if len(year) == 2:
                year = '20' + year if int(year) < 50 else '19' + year
            date = f"{day}/{month}/{year}"

        return name, date

    def _fuzzy_match_student(
        self, ocr_name: str, ocr_date: str,
        student_first: str, student_last: str, student_dob: Optional[str]
    ) -> float:
        """
        Fuzzy match OCR-extracted text against a student record.

        Returns match score 0.0-1.0
        """
        score = 0.0

        # Normalize texts
        ocr_name_norm = self._normalize_text(ocr_name)
        student_name_norm = self._normalize_text(f"{student_last} {student_first}")

        # Name matching: Jaccard similarity on words (60% weight)
        ocr_words = set(ocr_name_norm.split())
        student_words = set(student_name_norm.split())

        if ocr_words and student_words:
            intersection = ocr_words & student_words
            union = ocr_words | student_words
            jaccard = len(intersection) / len(union) if union else 0.0
            score += jaccard * 0.6

        # Date matching (40% weight)
        if ocr_date and student_dob:
            ocr_date_norm = self._normalize_date(ocr_date)
            student_date_norm = self._normalize_date(student_dob)

            if ocr_date_norm == student_date_norm:
                score += 0.4  # Exact match
            elif ocr_date_norm[:5] == student_date_norm[:5]:  # Same day/month
                score += 0.2

        return score

    def _normalize_text(self, text: str) -> str:
        """Normalize text for matching (case-insensitive, no accents, no hyphens)."""
        if not text:
            return ""
        # Remove accents
        text = unicodedata.normalize('NFD', text)
        text = ''.join(c for c in text if unicodedata.category(c) != 'Mn')
        # Lowercase
        text = text.lower()
        # Remove hyphens and underscores completely for name normalization
        text = re.sub(r'[-_]+', '', text)
        # Normalize multiple spaces
        text = re.sub(r'\s+', ' ', text)
        return text.strip()

    def _normalize_date(self, date_str: str) -> str:
        """Normalize date to DD/MM/YYYY format."""
        if not date_str:
            return ""
        # Extract digits only
        digits = re.findall(r'\d+', date_str)
        if len(digits) >= 3:
            day, month, year = digits[:3]
            day = day.zfill(2)
            month = month.zfill(2)
            if len(year) == 2:
                year = '20' + year if int(year) < 50 else '19' + year
            return f"{day}/{month}/{year}"
        return ""
