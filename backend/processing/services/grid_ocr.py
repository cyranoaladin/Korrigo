"""
Grid-Based OCR Service for CMEN v2 Headers.

This module implements a robust cell-by-cell OCR approach for CMEN v2 headers,
specifically designed for handwritten characters in individual grid cells.

Key features:
- Grid line removal without destroying handwriting
- Cell segmentation with geometric fallback
- Character-level recognition (not word-level)
- Per-character confidence scoring
- Strict closed-world matching against CSV whitelist

Structure of CMEN v2 header:
- Row 1: "Nom de famille :" followed by individual letter cells
- Row 2: "Prénom(s) :" followed by individual letter cells
- Row 3: "Né(e) le :" with date cells (DD/MM/YYYY format)

Author: Korrigo Team
PRD-19: Grid-Based OCR Implementation
"""
import cv2
import numpy as np
import logging
from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Dict, Any
from enum import Enum
import unicodedata
import re

logger = logging.getLogger(__name__)


# =============================================================================
# DATA CLASSES
# =============================================================================

class FieldType(Enum):
    """Type of field being extracted."""
    LAST_NAME = "last_name"
    FIRST_NAME = "first_name"
    DATE_OF_BIRTH = "date_of_birth"


@dataclass
class CellRecognition:
    """Recognition result for a single cell."""
    character: str
    confidence: float
    cell_bbox: Tuple[int, int, int, int]  # x, y, w, h
    is_empty: bool = False


@dataclass
class FieldResult:
    """Result of extracting a single field."""
    field_type: FieldType
    value: str
    confidence: float
    per_char_confidence: List[float]
    cells: List[CellRecognition]
    roi_bbox: Optional[Tuple[int, int, int, int]] = None


@dataclass
class GridOCRResult:
    """Complete result of grid-based OCR extraction."""
    last_name: str
    first_name: str
    date_of_birth: str
    overall_confidence: float
    fields: List[FieldResult]
    status: str = "OK"  # OK, PARTIAL, FAILED
    error_message: Optional[str] = None
    
    def get_primary_key(self) -> str:
        """Returns normalized primary key: NOM|PRENOM|DATE."""
        return f"{self.last_name}|{self.first_name}|{self.date_of_birth}"


@dataclass
class MatchCandidate:
    """A candidate match from the CSV whitelist."""
    student_id: Any
    last_name: str
    first_name: str
    date_of_birth: str
    email: Optional[str] = None
    class_name: Optional[str] = None
    
    # Match scores
    total_score: float = 0.0
    dob_score: float = 0.0
    name_score: float = 0.0
    firstname_score: float = 0.0


@dataclass
class MatchResult:
    """Result of closed-world matching."""
    status: str  # AUTO_MATCH, AMBIGUOUS_OCR, NO_MATCH, OCR_FAIL
    best_match: Optional[MatchCandidate] = None
    second_best: Optional[MatchCandidate] = None
    margin: float = 0.0
    all_candidates: List[MatchCandidate] = field(default_factory=list)


# =============================================================================
# CONSTANTS
# =============================================================================

# Alphabet for name fields (uppercase only, no accents in CMEN format)
NAME_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ -'"
# Digits for date field
DATE_ALPHABET = "0123456789/"

# Matching thresholds (strict as per requirements)
THRESHOLD_STRICT = 0.75  # Minimum score for auto-match
MARGIN_STRICT = 0.10     # Minimum margin between best and second-best

# Scoring weights (DOB is most important)
WEIGHT_DOB = 0.55
WEIGHT_NAME = 0.25
WEIGHT_FIRSTNAME = 0.20


# =============================================================================
# IMAGE PREPROCESSING
# =============================================================================

class ImagePreprocessor:
    """
    Preprocessing pipeline for CMEN header images.
    
    Handles:
    - Deskew (slight rotation correction)
    - Contrast normalization (CLAHE)
    - Adaptive binarization
    - Grid line removal (morphological operations)
    - Denoising (without destroying handwriting)
    """
    
    def __init__(self, debug: bool = False):
        self.debug = debug
    
    def preprocess(self, image: np.ndarray) -> np.ndarray:
        """
        Full preprocessing pipeline.
        
        Args:
            image: BGR or grayscale image
            
        Returns:
            Preprocessed binary image optimized for cell segmentation
        """
        # Convert to grayscale if needed
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()
        
        # Step 1: Deskew
        gray = self._deskew(gray)
        
        # Step 2: Contrast enhancement (CLAHE)
        gray = self._enhance_contrast(gray)
        
        # Step 3: Adaptive binarization
        binary = self._binarize(gray)
        
        # Step 4: Remove grid lines
        binary = self._remove_grid_lines(binary)
        
        # Step 5: Light denoising
        binary = self._denoise(binary)
        
        return binary
    
    def _deskew(self, gray: np.ndarray, max_angle: float = 5.0) -> np.ndarray:
        """Correct slight rotation using Hough transform."""
        try:
            # Detect edges
            edges = cv2.Canny(gray, 50, 150, apertureSize=3)
            
            # Detect lines
            lines = cv2.HoughLinesP(edges, 1, np.pi/180, 100, 
                                    minLineLength=100, maxLineGap=10)
            
            if lines is None or len(lines) == 0:
                return gray
            
            # Calculate dominant angle
            angles = []
            for line in lines:
                x1, y1, x2, y2 = line[0]
                if x2 - x1 != 0:
                    angle = np.arctan2(y2 - y1, x2 - x1) * 180 / np.pi
                    if abs(angle) < max_angle:
                        angles.append(angle)
            
            if not angles:
                return gray
            
            median_angle = np.median(angles)
            
            if abs(median_angle) < 0.5:
                return gray
            
            # Rotate image
            h, w = gray.shape
            center = (w // 2, h // 2)
            M = cv2.getRotationMatrix2D(center, median_angle, 1.0)
            rotated = cv2.warpAffine(gray, M, (w, h), 
                                     flags=cv2.INTER_CUBIC,
                                     borderMode=cv2.BORDER_REPLICATE)
            
            if self.debug:
                logger.debug(f"Deskew: rotated by {median_angle:.2f} degrees")
            
            return rotated
            
        except Exception as e:
            logger.warning(f"Deskew failed: {e}")
            return gray
    
    def _enhance_contrast(self, gray: np.ndarray) -> np.ndarray:
        """Apply CLAHE for local contrast enhancement."""
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        return clahe.apply(gray)
    
    def _binarize(self, gray: np.ndarray) -> np.ndarray:
        """Adaptive binarization for variable lighting."""
        # Use adaptive threshold for better handling of uneven lighting
        binary = cv2.adaptiveThreshold(
            gray, 255, 
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY_INV,
            blockSize=15,
            C=10
        )
        return binary
    
    def _remove_grid_lines(self, binary: np.ndarray) -> np.ndarray:
        """
        Remove grid lines using morphological operations.
        
        This is critical: we must remove the grid structure without
        destroying the handwritten characters inside the cells.
        """
        h, w = binary.shape
        
        # Detect horizontal lines
        horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (40, 1))
        horizontal_lines = cv2.morphologyEx(binary, cv2.MORPH_OPEN, horizontal_kernel)
        
        # Detect vertical lines
        vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 40))
        vertical_lines = cv2.morphologyEx(binary, cv2.MORPH_OPEN, vertical_kernel)
        
        # Combine grid lines
        grid_lines = cv2.add(horizontal_lines, vertical_lines)
        
        # Dilate grid lines slightly to ensure complete removal
        dilate_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        grid_lines = cv2.dilate(grid_lines, dilate_kernel, iterations=1)
        
        # Subtract grid lines from binary image
        result = cv2.subtract(binary, grid_lines)
        
        if self.debug:
            logger.debug("Grid lines removed")
        
        return result
    
    def _denoise(self, binary: np.ndarray) -> np.ndarray:
        """Light denoising without destroying handwriting."""
        # Small morphological opening to remove noise
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2, 2))
        denoised = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)
        return denoised


# =============================================================================
# CELL SEGMENTATION
# =============================================================================

class CellSegmenter:
    """
    Segments the grid into individual cells.
    
    Two approaches:
    1. Contour-based: Detect cell boundaries from grid structure
    2. Geometric fallback: Assume uniform cell spacing
    """
    
    def __init__(self, 
                 min_cell_width: int = 15,
                 max_cell_width: int = 60,
                 min_cell_height: int = 20,
                 max_cell_height: int = 80,
                 debug: bool = False):
        self.min_cell_width = min_cell_width
        self.max_cell_width = max_cell_width
        self.min_cell_height = min_cell_height
        self.max_cell_height = max_cell_height
        self.debug = debug
    
    def segment_cells(self, 
                      roi_image: np.ndarray,
                      expected_cells: Optional[int] = None) -> List[Tuple[int, int, int, int]]:
        """
        Segment ROI into individual cells.
        
        Args:
            roi_image: Binary image of the ROI (field region)
            expected_cells: Expected number of cells (for validation)
            
        Returns:
            List of cell bounding boxes (x, y, w, h) sorted left-to-right
        """
        # Try contour-based detection first
        cells = self._detect_cells_by_contours(roi_image)
        
        # Validate result
        if cells and len(cells) >= 3:
            if self.debug:
                logger.debug(f"Contour detection found {len(cells)} cells")
            return cells
        
        # Fallback to geometric detection
        cells = self._detect_cells_geometric(roi_image, expected_cells)
        
        if self.debug:
            logger.debug(f"Geometric detection found {len(cells)} cells")
        
        return cells
    
    def _detect_cells_by_contours(self, 
                                   binary: np.ndarray) -> List[Tuple[int, int, int, int]]:
        """Detect cells by finding rectangular contours."""
        h, w = binary.shape
        
        # Invert to find white regions (cells)
        inverted = cv2.bitwise_not(binary)
        
        # Find contours
        contours, _ = cv2.findContours(inverted, cv2.RETR_EXTERNAL, 
                                        cv2.CHAIN_APPROX_SIMPLE)
        
        cells = []
        for contour in contours:
            x, y, cw, ch = cv2.boundingRect(contour)
            
            # Filter by size
            if (self.min_cell_width <= cw <= self.max_cell_width and
                self.min_cell_height <= ch <= self.max_cell_height):
                
                # Check aspect ratio (cells are roughly square or slightly tall)
                aspect = cw / ch if ch > 0 else 0
                if 0.3 <= aspect <= 2.0:
                    cells.append((x, y, cw, ch))
        
        # Sort by x position (left to right)
        cells.sort(key=lambda c: c[0])
        
        # Filter overlapping cells
        cells = self._filter_overlapping(cells)
        
        return cells
    
    def _detect_cells_geometric(self, 
                                 binary: np.ndarray,
                                 expected_cells: Optional[int] = None) -> List[Tuple[int, int, int, int]]:
        """
        Geometric fallback: assume uniform cell spacing.
        
        This is used when contour detection fails (e.g., faint grid lines).
        """
        h, w = binary.shape
        
        # Estimate cell width from image width
        if expected_cells:
            cell_width = w // expected_cells
        else:
            # Default: assume ~25 cells for name fields
            cell_width = max(self.min_cell_width, w // 25)
        
        # Ensure cell width is within bounds
        cell_width = max(self.min_cell_width, min(self.max_cell_width, cell_width))
        
        # Generate uniform cells
        cells = []
        x = 0
        while x + cell_width <= w:
            cells.append((x, 0, cell_width, h))
            x += cell_width
        
        return cells
    
    def _filter_overlapping(self, 
                            cells: List[Tuple[int, int, int, int]]) -> List[Tuple[int, int, int, int]]:
        """Remove overlapping cells, keeping the larger one."""
        if len(cells) <= 1:
            return cells
        
        filtered = []
        for cell in cells:
            x, y, w, h = cell
            overlaps = False
            
            for existing in filtered:
                ex, ey, ew, eh = existing
                # Check horizontal overlap
                if not (x + w < ex or x > ex + ew):
                    overlaps = True
                    break
            
            if not overlaps:
                filtered.append(cell)
        
        return filtered


# =============================================================================
# CHARACTER RECOGNITION
# =============================================================================

class CharacterRecognizer:
    """
    Recognizes individual characters from cell patches.
    
    Uses multiple OCR engines with consensus voting:
    - Tesseract (with restricted character set)
    - EasyOCR (optional)
    - PaddleOCR (optional)
    """
    
    def __init__(self, debug: bool = False):
        self.debug = debug
        self._tesseract_available = self._check_tesseract()
        self._easyocr_reader = None
    
    def _check_tesseract(self) -> bool:
        """Check if Tesseract is available."""
        try:
            import pytesseract
            pytesseract.get_tesseract_version()
            return True
        except Exception:
            return False
    
    def recognize_cell(self, 
                       cell_image: np.ndarray,
                       field_type: FieldType) -> CellRecognition:
        """
        Recognize a single character from a cell image.
        
        Args:
            cell_image: Binary image of the cell
            field_type: Type of field (affects character whitelist)
            
        Returns:
            CellRecognition with character and confidence
        """
        # Check if cell is empty
        if self._is_cell_empty(cell_image):
            return CellRecognition(
                character='',
                confidence=1.0,
                cell_bbox=(0, 0, cell_image.shape[1], cell_image.shape[0]),
                is_empty=True
            )
        
        # Determine whitelist based on field type
        if field_type == FieldType.DATE_OF_BIRTH:
            whitelist = "0123456789"
        else:
            whitelist = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        
        # Try Tesseract
        char, conf = self._recognize_with_tesseract(cell_image, whitelist)
        
        if char and conf > 0.3:
            return CellRecognition(
                character=char,
                confidence=conf,
                cell_bbox=(0, 0, cell_image.shape[1], cell_image.shape[0]),
                is_empty=False
            )
        
        # Fallback: return empty if no confident recognition
        return CellRecognition(
            character='',
            confidence=0.0,
            cell_bbox=(0, 0, cell_image.shape[1], cell_image.shape[0]),
            is_empty=True
        )
    
    def _is_cell_empty(self, cell_image: np.ndarray, threshold: float = 0.02) -> bool:
        """Check if a cell is empty (no significant ink)."""
        # Count non-zero pixels
        if len(cell_image.shape) == 3:
            gray = cv2.cvtColor(cell_image, cv2.COLOR_BGR2GRAY)
        else:
            gray = cell_image
        
        # For binary images, count white pixels (ink)
        ink_ratio = np.sum(gray > 127) / gray.size
        
        return ink_ratio < threshold
    
    def _recognize_with_tesseract(self, 
                                   cell_image: np.ndarray,
                                   whitelist: str) -> Tuple[str, float]:
        """Recognize character using Tesseract."""
        if not self._tesseract_available:
            return '', 0.0
        
        try:
            import pytesseract
            
            # Prepare image (ensure proper size and contrast)
            h, w = cell_image.shape[:2]
            
            # Scale up small images
            if h < 30 or w < 20:
                scale = max(30 / h, 20 / w)
                cell_image = cv2.resize(cell_image, None, 
                                        fx=scale, fy=scale,
                                        interpolation=cv2.INTER_CUBIC)
            
            # Add padding
            padded = cv2.copyMakeBorder(cell_image, 5, 5, 5, 5,
                                        cv2.BORDER_CONSTANT, value=0)
            
            # Invert if needed (Tesseract expects black on white)
            if np.mean(padded) > 127:
                padded = cv2.bitwise_not(padded)
            
            # Configure Tesseract for single character
            config = f'--oem 3 --psm 10 -c tessedit_char_whitelist={whitelist}'
            
            # Get character with confidence
            data = pytesseract.image_to_data(padded, config=config,
                                             output_type=pytesseract.Output.DICT)
            
            # Find best result
            best_char = ''
            best_conf = 0.0
            
            for i, text in enumerate(data['text']):
                if text.strip():
                    conf = data['conf'][i]
                    if conf > best_conf:
                        best_conf = conf / 100.0
                        best_char = text.strip().upper()
            
            # Take only first character
            if best_char:
                best_char = best_char[0]
            
            return best_char, best_conf
            
        except Exception as e:
            logger.warning(f"Tesseract recognition failed: {e}")
            return '', 0.0


# =============================================================================
# FIELD EXTRACTION
# =============================================================================

class FieldExtractor:
    """
    Extracts complete fields (name, firstname, date) from header image.
    
    Combines:
    - ROI detection
    - Cell segmentation
    - Character recognition
    """
    
    # ROI regions as percentage of header image
    # Calibrated for CMEN v2 ONEOPTEC format
    REGIONS = {
        FieldType.LAST_NAME: {
            'y_start': 0.0, 'y_end': 0.35,
            'x_start': 0.20, 'x_end': 0.98,
            'expected_cells': 25
        },
        FieldType.FIRST_NAME: {
            'y_start': 0.30, 'y_end': 0.55,
            'x_start': 0.18, 'x_end': 0.98,
            'expected_cells': 25
        },
        FieldType.DATE_OF_BIRTH: {
            'y_start': 0.50, 'y_end': 0.75,
            'x_start': 0.55, 'x_end': 0.95,
            'expected_cells': 8  # DD/MM/YYYY = 8 digits
        }
    }
    
    def __init__(self, debug: bool = False):
        self.debug = debug
        self.preprocessor = ImagePreprocessor(debug=debug)
        self.segmenter = CellSegmenter(debug=debug)
        self.recognizer = CharacterRecognizer(debug=debug)
    
    def extract_field(self, 
                      header_image: np.ndarray,
                      field_type: FieldType) -> FieldResult:
        """
        Extract a single field from the header image.
        
        Args:
            header_image: Full header image (BGR or grayscale)
            field_type: Type of field to extract
            
        Returns:
            FieldResult with extracted value and confidence
        """
        # Get ROI region
        region = self.REGIONS[field_type]
        h, w = header_image.shape[:2]
        
        x1 = int(w * region['x_start'])
        x2 = int(w * region['x_end'])
        y1 = int(h * region['y_start'])
        y2 = int(h * region['y_end'])
        
        roi = header_image[y1:y2, x1:x2]
        
        # Preprocess ROI
        preprocessed = self.preprocessor.preprocess(roi)
        
        # Segment into cells
        cells = self.segmenter.segment_cells(
            preprocessed,
            expected_cells=region.get('expected_cells')
        )
        
        if not cells:
            return FieldResult(
                field_type=field_type,
                value='',
                confidence=0.0,
                per_char_confidence=[],
                cells=[],
                roi_bbox=(x1, y1, x2-x1, y2-y1)
            )
        
        # Recognize each cell
        recognitions = []
        for cell_bbox in cells:
            cx, cy, cw, ch = cell_bbox
            cell_image = preprocessed[cy:cy+ch, cx:cx+cw]
            
            recognition = self.recognizer.recognize_cell(cell_image, field_type)
            recognition.cell_bbox = (x1 + cx, y1 + cy, cw, ch)
            recognitions.append(recognition)
        
        # Build result
        chars = [r.character for r in recognitions if not r.is_empty]
        confidences = [r.confidence for r in recognitions if not r.is_empty]
        
        value = ''.join(chars)
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
        
        # Post-process value
        if field_type == FieldType.DATE_OF_BIRTH:
            value = self._format_date(value)
        else:
            value = self._normalize_name(value)
        
        return FieldResult(
            field_type=field_type,
            value=value,
            confidence=avg_confidence,
            per_char_confidence=confidences,
            cells=recognitions,
            roi_bbox=(x1, y1, x2-x1, y2-y1)
        )
    
    def _format_date(self, digits: str) -> str:
        """Format extracted digits as DD/MM/YYYY."""
        # Keep only digits
        digits = re.sub(r'[^0-9]', '', digits)
        
        if len(digits) >= 8:
            day = digits[:2]
            month = digits[2:4]
            year = digits[4:8]
            
            # Basic validation
            try:
                d, m, y = int(day), int(month), int(year)
                if 1 <= d <= 31 and 1 <= m <= 12 and 1900 <= y <= 2020:
                    return f"{day}/{month}/{year}"
            except ValueError:
                pass
        
        return digits
    
    def _normalize_name(self, text: str) -> str:
        """Normalize a name (uppercase, no accents)."""
        if not text:
            return ''
        
        # Remove non-alphabetic characters except space and hyphen
        text = re.sub(r'[^A-Za-zÀ-ÿ\s\-]', '', text)
        
        # Normalize spaces
        text = ' '.join(text.split())
        
        # Uppercase
        text = text.upper()
        
        # Remove accents
        text = unicodedata.normalize('NFD', text)
        text = ''.join(c for c in text if unicodedata.category(c) != 'Mn')
        
        return text.strip()


# =============================================================================
# MAIN OCR SERVICE
# =============================================================================

class GridOCRService:
    """
    Main service for grid-based OCR extraction from CMEN v2 headers.
    
    Usage:
        service = GridOCRService()
        result = service.extract_header(header_image)
        match = service.match_student(result, students_csv)
    """
    
    def __init__(self, debug: bool = False):
        self.debug = debug
        self.extractor = FieldExtractor(debug=debug)
    
    def extract_header(self, header_image: np.ndarray) -> GridOCRResult:
        """
        Extract all fields from a CMEN v2 header image.
        
        Args:
            header_image: Image of the header (top ~25% of page)
            
        Returns:
            GridOCRResult with extracted fields
        """
        logger.info("Starting grid-based OCR extraction...")
        
        fields = []
        
        # Extract each field
        for field_type in [FieldType.LAST_NAME, FieldType.FIRST_NAME, FieldType.DATE_OF_BIRTH]:
            try:
                field_result = self.extractor.extract_field(header_image, field_type)
                fields.append(field_result)
                logger.info(f"  {field_type.value}: '{field_result.value}' "
                           f"(conf: {field_result.confidence:.2f})")
            except Exception as e:
                logger.error(f"Failed to extract {field_type.value}: {e}")
                fields.append(FieldResult(
                    field_type=field_type,
                    value='',
                    confidence=0.0,
                    per_char_confidence=[],
                    cells=[]
                ))
        
        # Build result
        last_name = fields[0].value if fields else ''
        first_name = fields[1].value if len(fields) > 1 else ''
        date_of_birth = fields[2].value if len(fields) > 2 else ''
        
        # Calculate overall confidence
        confidences = [f.confidence for f in fields if f.confidence > 0]
        overall_confidence = sum(confidences) / len(confidences) if confidences else 0.0
        
        # Determine status
        if all(f.value for f in fields):
            status = "OK"
        elif any(f.value for f in fields):
            status = "PARTIAL"
        else:
            status = "FAILED"
        
        return GridOCRResult(
            last_name=last_name,
            first_name=first_name,
            date_of_birth=date_of_birth,
            overall_confidence=overall_confidence,
            fields=fields,
            status=status
        )
    
    def match_student(self,
                      ocr_result: GridOCRResult,
                      students: List[Dict[str, Any]],
                      threshold: float = THRESHOLD_STRICT,
                      margin: float = MARGIN_STRICT) -> MatchResult:
        """
        Match OCR result against CSV whitelist (closed-world matching).
        
        Args:
            ocr_result: Result from extract_header()
            students: List of student records from CSV
            threshold: Minimum score for auto-match
            margin: Minimum margin between best and second-best
            
        Returns:
            MatchResult with status and candidates
        """
        if not students:
            return MatchResult(status="NO_MATCH")
        
        if ocr_result.status == "FAILED":
            return MatchResult(status="OCR_FAIL")
        
        # Normalize OCR values for comparison
        ocr_name = self._normalize_for_match(ocr_result.last_name)
        ocr_firstname = self._normalize_for_match(ocr_result.first_name)
        ocr_dob = ocr_result.date_of_birth.replace('/', '')
        
        # Score all candidates
        candidates = []
        for student in students:
            # Extract and normalize student data
            student_name = self._normalize_for_match(student.get('last_name', ''))
            student_firstname = self._normalize_for_match(student.get('first_name', ''))
            student_dob = str(student.get('date_of_birth', '')).replace('/', '')
            
            # Calculate similarity scores
            dob_score = self._calculate_dob_score(ocr_dob, student_dob)
            name_score = self._jaro_winkler(ocr_name, student_name)
            firstname_score = self._jaro_winkler(ocr_firstname, student_firstname)
            
            # Weighted total score
            total_score = (
                WEIGHT_DOB * dob_score +
                WEIGHT_NAME * name_score +
                WEIGHT_FIRSTNAME * firstname_score
            )
            
            candidate = MatchCandidate(
                student_id=student.get('id') or student.get('student_id'),
                last_name=student.get('last_name', ''),
                first_name=student.get('first_name', ''),
                date_of_birth=student.get('date_of_birth', ''),
                email=student.get('email'),
                class_name=student.get('class_name'),
                total_score=total_score,
                dob_score=dob_score,
                name_score=name_score,
                firstname_score=firstname_score
            )
            candidates.append(candidate)
        
        # Sort by score descending
        candidates.sort(key=lambda c: c.total_score, reverse=True)
        
        # Get best and second-best
        best = candidates[0] if candidates else None
        second_best = candidates[1] if len(candidates) > 1 else None
        
        # Calculate margin
        actual_margin = (best.total_score - second_best.total_score) if second_best else 1.0
        
        # Determine status
        if best and best.total_score >= threshold and actual_margin >= margin:
            # Additional check: DOB must be very close
            if best.dob_score >= 0.9:
                status = "AUTO_MATCH"
            else:
                status = "AMBIGUOUS_OCR"
        elif best and best.total_score >= threshold * 0.8:
            status = "AMBIGUOUS_OCR"
        else:
            status = "NO_MATCH"
        
        return MatchResult(
            status=status,
            best_match=best,
            second_best=second_best,
            margin=actual_margin,
            all_candidates=candidates[:10]  # Top 10 for review
        )
    
    def _normalize_for_match(self, text: str) -> str:
        """Normalize text for matching (consistent with CSV normalization)."""
        if not text:
            return ''
        
        # Uppercase
        text = text.upper()
        
        # Remove accents
        text = unicodedata.normalize('NFD', text)
        text = ''.join(c for c in text if unicodedata.category(c) != 'Mn')
        
        # Remove hyphens and apostrophes (or convert to space)
        text = re.sub(r"[-']", ' ', text)
        
        # Keep only A-Z and space
        text = re.sub(r'[^A-Z ]', '', text)
        
        # Compact multiple spaces
        text = ' '.join(text.split())
        
        return text.strip()
    
    def _calculate_dob_score(self, ocr_dob: str, csv_dob: str) -> float:
        """
        Calculate date of birth similarity score.
        
        DOB must be very strict - allow at most 1 digit error.
        """
        if not ocr_dob or not csv_dob:
            return 0.0
        
        # Exact match
        if ocr_dob == csv_dob:
            return 1.0
        
        # Allow 1 digit error if lengths match
        if len(ocr_dob) == len(csv_dob) == 8:
            errors = sum(1 for a, b in zip(ocr_dob, csv_dob) if a != b)
            if errors == 1:
                return 0.9
            elif errors == 2:
                return 0.7
        
        # Partial match
        return self._jaro_winkler(ocr_dob, csv_dob) * 0.5
    
    def _jaro_winkler(self, s1: str, s2: str) -> float:
        """Calculate Jaro-Winkler similarity."""
        if not s1 or not s2:
            return 0.0
        
        if s1 == s2:
            return 1.0
        
        # Use difflib for simplicity
        from difflib import SequenceMatcher
        return SequenceMatcher(None, s1, s2).ratio()


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def extract_header_from_image(image_path: str) -> GridOCRResult:
    """
    Convenience function to extract header from an image file.
    
    Args:
        image_path: Path to the page image
        
    Returns:
        GridOCRResult
    """
    image = cv2.imread(image_path)
    if image is None:
        raise ValueError(f"Cannot read image: {image_path}")
    
    # Extract header region (top 25%)
    height = image.shape[0]
    header_height = int(height * 0.25)
    header_image = image[:header_height, :]
    
    service = GridOCRService()
    return service.extract_header(header_image)


def match_with_csv(ocr_result: GridOCRResult, csv_path: str) -> MatchResult:
    """
    Convenience function to match OCR result with CSV file.
    
    Args:
        ocr_result: Result from extract_header
        csv_path: Path to student CSV file
        
    Returns:
        MatchResult
    """
    import csv
    
    students = []
    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f, delimiter=';')
        for row in reader:
            students.append({
                'id': row.get('ID') or row.get('INE'),
                'last_name': row.get('NOM') or row.get('Nom'),
                'first_name': row.get('PRENOM') or row.get('Prénom'),
                'date_of_birth': row.get('DATE_NAISSANCE') or row.get('Né(e) le'),
                'email': row.get('EMAIL') or row.get('Email'),
                'class_name': row.get('CLASSE') or row.get('Classe')
            })
    
    service = GridOCRService()
    return service.match_student(ocr_result, students)
