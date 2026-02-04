"""
Tests for Grid-Based OCR Service (PRD-19).

These tests validate the core functionality of the grid-based OCR system
for CMEN v2 headers.

Test categories:
1. Grid line removal
2. Cell segmentation
3. Character recognition
4. Date strictness
5. CSV matching with strict margin
"""
import pytest
import numpy as np
import cv2
from unittest.mock import patch, MagicMock

from processing.services.grid_ocr import (
    ImagePreprocessor,
    CellSegmenter,
    CharacterRecognizer,
    FieldExtractor,
    GridOCRService,
    FieldType,
    GridOCRResult,
    MatchResult,
    MatchCandidate,
    THRESHOLD_STRICT,
    MARGIN_STRICT,
)


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def sample_binary_image():
    """Create a simple binary image with grid lines and content."""
    # 200x100 image
    img = np.zeros((100, 200), dtype=np.uint8)
    
    # Add horizontal grid lines
    img[20, :] = 255
    img[40, :] = 255
    img[60, :] = 255
    img[80, :] = 255
    
    # Add vertical grid lines (every 20 pixels)
    for x in range(0, 200, 20):
        img[:, x] = 255
    
    # Add some "handwriting" content (thick strokes)
    cv2.circle(img, (30, 50), 8, 255, -1)  # Letter in cell 1
    cv2.circle(img, (70, 50), 8, 255, -1)  # Letter in cell 3
    
    return img


@pytest.fixture
def sample_cell_image():
    """Create a sample cell with a character."""
    img = np.zeros((40, 30), dtype=np.uint8)
    # Draw a simple "A" shape
    cv2.line(img, (15, 35), (5, 5), 255, 2)
    cv2.line(img, (15, 35), (25, 5), 255, 2)
    cv2.line(img, (10, 20), (20, 20), 255, 2)
    return img


@pytest.fixture
def empty_cell_image():
    """Create an empty cell (no content)."""
    return np.zeros((40, 30), dtype=np.uint8)


@pytest.fixture
def sample_header_image():
    """Create a mock header image with grid structure."""
    # 800x200 header image
    img = np.ones((200, 800, 3), dtype=np.uint8) * 255
    
    # Add grid structure for name field (top third)
    for y in [10, 50]:
        cv2.line(img, (160, y), (780, y), (200, 200, 200), 1)
    for x in range(160, 780, 25):
        cv2.line(img, (x, 10), (x, 50), (200, 200, 200), 1)
    
    # Add some "handwritten" letters
    cv2.putText(img, "D", (165, 45), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)
    cv2.putText(img, "U", (190, 45), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)
    cv2.putText(img, "P", (215, 45), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)
    
    return img


@pytest.fixture
def sample_students():
    """Sample student records for matching tests."""
    return [
        {
            'id': 1,
            'last_name': 'DUPONT',
            'first_name': 'JEAN',
            'date_of_birth': '15/03/2008',
            'email': 'jean.dupont@test.com',
            'class_name': '3A'
        },
        {
            'id': 2,
            'last_name': 'DURAND',
            'first_name': 'MARIE',
            'date_of_birth': '22/07/2008',
            'email': 'marie.durand@test.com',
            'class_name': '3A'
        },
        {
            'id': 3,
            'last_name': 'MARTIN',
            'first_name': 'PIERRE',
            'date_of_birth': '10/01/2008',
            'email': 'pierre.martin@test.com',
            'class_name': '3B'
        },
        {
            'id': 4,
            'last_name': 'DUPONT',
            'first_name': 'PAUL',
            'date_of_birth': '15/03/2008',
            'email': 'paul.dupont@test.com',
            'class_name': '3B'
        },
    ]


# =============================================================================
# TEST: GRID LINE REMOVAL
# =============================================================================

class TestGridLineRemoval:
    """Tests for grid line removal without destroying handwriting."""
    
    def test_grid_line_removal_preserves_content(self, sample_binary_image):
        """Grid line removal should not erase handwriting."""
        preprocessor = ImagePreprocessor(debug=False)
        
        # Count content pixels before
        content_before = np.sum(sample_binary_image > 0)
        
        # Remove grid lines
        result = preprocessor._remove_grid_lines(sample_binary_image)
        
        # Content should still exist (circles we drew)
        content_after = np.sum(result > 0)
        
        # Grid lines are removed, but content remains
        # Content should be less than before (grid removed) but not zero
        assert content_after > 0, "Content was completely erased"
        assert content_after < content_before, "Grid lines were not removed"
    
    def test_grid_line_removal_removes_horizontal_lines(self):
        """Horizontal grid lines should be removed."""
        preprocessor = ImagePreprocessor(debug=False)
        
        # Create image with only horizontal lines
        img = np.zeros((100, 200), dtype=np.uint8)
        img[25, :] = 255
        img[50, :] = 255
        img[75, :] = 255
        
        result = preprocessor._remove_grid_lines(img)
        
        # Lines should be mostly removed
        assert np.sum(result) < np.sum(img) * 0.3
    
    def test_grid_line_removal_removes_vertical_lines(self):
        """Vertical grid lines should be removed."""
        preprocessor = ImagePreprocessor(debug=False)
        
        # Create image with only vertical lines
        img = np.zeros((100, 200), dtype=np.uint8)
        for x in range(0, 200, 25):
            img[:, x] = 255
        
        result = preprocessor._remove_grid_lines(img)
        
        # Lines should be mostly removed
        assert np.sum(result) < np.sum(img) * 0.3


# =============================================================================
# TEST: CELL SEGMENTATION
# =============================================================================

class TestCellSegmentation:
    """Tests for cell segmentation accuracy."""
    
    def test_cell_segmentation_count_geometric(self):
        """Geometric segmentation should produce expected cell count."""
        segmenter = CellSegmenter(debug=False)
        
        # Create a 500px wide image
        img = np.zeros((50, 500), dtype=np.uint8)
        
        # Segment with expected 20 cells
        cells = segmenter._detect_cells_geometric(img, expected_cells=20)
        
        assert len(cells) == 20, f"Expected 20 cells, got {len(cells)}"
    
    def test_cell_segmentation_sorted_left_to_right(self):
        """Cells should be sorted left to right."""
        segmenter = CellSegmenter(debug=False)
        
        img = np.zeros((50, 500), dtype=np.uint8)
        cells = segmenter._detect_cells_geometric(img, expected_cells=10)
        
        # Check cells are sorted by x position
        x_positions = [c[0] for c in cells]
        assert x_positions == sorted(x_positions), "Cells not sorted left to right"
    
    def test_cell_segmentation_no_overlap(self):
        """Segmented cells should not overlap."""
        segmenter = CellSegmenter(debug=False)
        
        img = np.zeros((50, 500), dtype=np.uint8)
        cells = segmenter._detect_cells_geometric(img, expected_cells=10)
        
        # Check no overlap
        for i in range(len(cells) - 1):
            x1, _, w1, _ = cells[i]
            x2, _, _, _ = cells[i + 1]
            assert x1 + w1 <= x2, f"Cells {i} and {i+1} overlap"
    
    def test_cell_segmentation_handles_empty_image(self):
        """Segmentation should handle empty images gracefully."""
        segmenter = CellSegmenter(debug=False)
        
        img = np.zeros((10, 10), dtype=np.uint8)
        cells = segmenter.segment_cells(img)
        
        # Should return empty or minimal cells, not crash
        assert isinstance(cells, list)


# =============================================================================
# TEST: CHARACTER RECOGNITION
# =============================================================================

class TestCharacterRecognition:
    """Tests for character recognition accuracy."""
    
    def test_empty_cell_detection(self, empty_cell_image):
        """Empty cells should be detected as empty."""
        recognizer = CharacterRecognizer(debug=False)
        
        result = recognizer.recognize_cell(empty_cell_image, FieldType.LAST_NAME)
        
        assert result.is_empty, "Empty cell not detected as empty"
        assert result.character == '', "Empty cell should have no character"
    
    def test_cell_with_content_not_empty(self, sample_cell_image):
        """Cells with content should not be marked as empty."""
        recognizer = CharacterRecognizer(debug=False)
        
        result = recognizer.recognize_cell(sample_cell_image, FieldType.LAST_NAME)
        
        # May or may not recognize correctly, but should not be empty
        assert not result.is_empty or result.confidence < 0.1
    
    def test_date_field_uses_digit_whitelist(self):
        """Date field recognition should use digit whitelist."""
        recognizer = CharacterRecognizer(debug=False)
        
        # Create image with digit-like shape
        img = np.zeros((40, 30), dtype=np.uint8)
        cv2.putText(img, "5", (5, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, 255, 2)
        
        result = recognizer.recognize_cell(img, FieldType.DATE_OF_BIRTH)
        
        # If recognized, should be a digit
        if result.character:
            assert result.character in "0123456789", \
                f"Date field returned non-digit: {result.character}"
    
    def test_name_field_uses_letter_whitelist(self):
        """Name field recognition should use letter whitelist."""
        recognizer = CharacterRecognizer(debug=False)
        
        # Create image with letter-like shape
        img = np.zeros((40, 30), dtype=np.uint8)
        cv2.putText(img, "A", (5, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, 255, 2)
        
        result = recognizer.recognize_cell(img, FieldType.LAST_NAME)
        
        # If recognized, should be a letter
        if result.character:
            assert result.character in "ABCDEFGHIJKLMNOPQRSTUVWXYZ", \
                f"Name field returned non-letter: {result.character}"


# =============================================================================
# TEST: DATE STRICTNESS
# =============================================================================

class TestDateStrictness:
    """Tests for date validation strictness."""
    
    def test_valid_date_format(self):
        """Valid dates should be accepted."""
        extractor = FieldExtractor(debug=False)
        
        assert extractor._format_date("15032008") == "15/03/2008"
        assert extractor._format_date("01012000") == "01/01/2000"
        assert extractor._format_date("31121999") == "31/12/1999"
    
    def test_invalid_day_rejected(self):
        """Invalid days (>31) should not produce valid date."""
        extractor = FieldExtractor(debug=False)
        
        result = extractor._format_date("32032008")
        # Should return raw digits, not formatted date
        assert result == "32032008" or "/" not in result
    
    def test_invalid_month_rejected(self):
        """Invalid months (>12) should not produce valid date."""
        extractor = FieldExtractor(debug=False)
        
        result = extractor._format_date("15132008")
        assert result == "15132008" or "/" not in result
    
    def test_future_year_rejected(self):
        """Future years should not produce valid date."""
        extractor = FieldExtractor(debug=False)
        
        result = extractor._format_date("15032025")
        assert result == "15032025" or "/" not in result
    
    def test_dob_score_exact_match(self):
        """Exact DOB match should score 1.0."""
        service = GridOCRService(debug=False)
        
        score = service._calculate_dob_score("15032008", "15032008")
        assert score == 1.0
    
    def test_dob_score_one_digit_error(self):
        """One digit error should score ~0.9."""
        service = GridOCRService(debug=False)
        
        score = service._calculate_dob_score("15032008", "15032009")
        assert 0.85 <= score <= 0.95
    
    def test_dob_score_two_digit_errors(self):
        """Two digit errors should score ~0.7."""
        service = GridOCRService(debug=False)
        
        score = service._calculate_dob_score("15032008", "16042008")
        assert 0.65 <= score <= 0.75
    
    def test_dob_score_completely_different(self):
        """Completely different DOB should score low."""
        service = GridOCRService(debug=False)
        
        score = service._calculate_dob_score("15032008", "22071999")
        assert score < 0.5


# =============================================================================
# TEST: CSV MATCHING WITH STRICT MARGIN
# =============================================================================

class TestCSVMatchingStrictMargin:
    """Tests for CSV matching with strict threshold and margin."""
    
    def test_no_auto_assign_when_ambiguous(self, sample_students):
        """Should not auto-assign when two candidates are close."""
        service = GridOCRService(debug=False)
        
        # Create OCR result that matches both DUPONT JEAN and DUPONT PAUL
        ocr_result = GridOCRResult(
            last_name="DUPONT",
            first_name="",  # Empty firstname - ambiguous
            date_of_birth="15/03/2008",  # Same DOB for both
            overall_confidence=0.8,
            fields=[],
            status="PARTIAL"
        )
        
        match = service.match_student(ocr_result, sample_students)
        
        # Should be AMBIGUOUS, not AUTO_MATCH
        assert match.status == "AMBIGUOUS_OCR", \
            f"Expected AMBIGUOUS_OCR, got {match.status}"
    
    def test_auto_assign_with_clear_margin(self, sample_students):
        """Should auto-assign when there's a clear winner."""
        service = GridOCRService(debug=False)
        
        # Create OCR result that clearly matches MARTIN PIERRE
        ocr_result = GridOCRResult(
            last_name="MARTIN",
            first_name="PIERRE",
            date_of_birth="10/01/2008",
            overall_confidence=0.9,
            fields=[],
            status="OK"
        )
        
        match = service.match_student(ocr_result, sample_students)
        
        # Should be AUTO_MATCH with MARTIN PIERRE
        assert match.status == "AUTO_MATCH", \
            f"Expected AUTO_MATCH, got {match.status}"
        assert match.best_match.last_name == "MARTIN"
        assert match.best_match.first_name == "PIERRE"
    
    def test_no_match_when_below_threshold(self, sample_students):
        """Should return NO_MATCH when best score is below threshold."""
        service = GridOCRService(debug=False)
        
        # Create OCR result that doesn't match anyone
        ocr_result = GridOCRResult(
            last_name="ZZZZZ",
            first_name="XXXXX",
            date_of_birth="01/01/1990",
            overall_confidence=0.5,
            fields=[],
            status="OK"
        )
        
        match = service.match_student(ocr_result, sample_students)
        
        # Should be NO_MATCH
        assert match.status == "NO_MATCH", \
            f"Expected NO_MATCH, got {match.status}"
    
    def test_margin_calculation(self, sample_students):
        """Margin should be correctly calculated."""
        service = GridOCRService(debug=False)
        
        ocr_result = GridOCRResult(
            last_name="DURAND",
            first_name="MARIE",
            date_of_birth="22/07/2008",
            overall_confidence=0.9,
            fields=[],
            status="OK"
        )
        
        match = service.match_student(ocr_result, sample_students)
        
        # Margin should be positive (best > second)
        assert match.margin > 0
        
        # Margin should equal best - second
        if match.second_best:
            expected_margin = match.best_match.total_score - match.second_best.total_score
            assert abs(match.margin - expected_margin) < 0.001
    
    def test_ocr_fail_returns_ocr_fail_status(self, sample_students):
        """OCR failure should return OCR_FAIL status."""
        service = GridOCRService(debug=False)
        
        ocr_result = GridOCRResult(
            last_name="",
            first_name="",
            date_of_birth="",
            overall_confidence=0.0,
            fields=[],
            status="FAILED"
        )
        
        match = service.match_student(ocr_result, sample_students)
        
        assert match.status == "OCR_FAIL"
    
    def test_empty_students_returns_no_match(self):
        """Empty student list should return NO_MATCH."""
        service = GridOCRService(debug=False)
        
        ocr_result = GridOCRResult(
            last_name="DUPONT",
            first_name="JEAN",
            date_of_birth="15/03/2008",
            overall_confidence=0.9,
            fields=[],
            status="OK"
        )
        
        match = service.match_student(ocr_result, [])
        
        assert match.status == "NO_MATCH"


# =============================================================================
# TEST: NORMALIZATION
# =============================================================================

class TestNormalization:
    """Tests for text normalization consistency."""
    
    def test_normalize_removes_accents(self):
        """Normalization should remove accents."""
        service = GridOCRService(debug=False)
        
        assert service._normalize_for_match("ÉLÉONORE") == "ELEONORE"
        assert service._normalize_for_match("FRANÇOIS") == "FRANCOIS"
        assert service._normalize_for_match("MÜLLER") == "MULLER"
    
    def test_normalize_handles_hyphens(self):
        """Normalization should handle hyphens consistently."""
        service = GridOCRService(debug=False)
        
        result = service._normalize_for_match("JEAN-PIERRE")
        # Should convert hyphen to space or remove it
        assert "-" not in result
        assert "JEAN" in result and "PIERRE" in result
    
    def test_normalize_handles_apostrophes(self):
        """Normalization should handle apostrophes consistently."""
        service = GridOCRService(debug=False)
        
        result = service._normalize_for_match("D'ARTAGNAN")
        # Should convert apostrophe to space or remove it
        assert "'" not in result
    
    def test_normalize_uppercase(self):
        """Normalization should convert to uppercase."""
        service = GridOCRService(debug=False)
        
        assert service._normalize_for_match("dupont") == "DUPONT"
        assert service._normalize_for_match("DuPont") == "DUPONT"
    
    def test_normalize_compacts_spaces(self):
        """Normalization should compact multiple spaces."""
        service = GridOCRService(debug=False)
        
        result = service._normalize_for_match("JEAN   PIERRE")
        assert "  " not in result
        assert result == "JEAN PIERRE"


# =============================================================================
# TEST: INTEGRATION
# =============================================================================

class TestIntegration:
    """Integration tests for the complete OCR pipeline."""
    
    def test_extract_header_returns_result(self, sample_header_image):
        """extract_header should return a GridOCRResult."""
        service = GridOCRService(debug=False)
        
        result = service.extract_header(sample_header_image)
        
        assert isinstance(result, GridOCRResult)
        assert hasattr(result, 'last_name')
        assert hasattr(result, 'first_name')
        assert hasattr(result, 'date_of_birth')
        assert hasattr(result, 'overall_confidence')
        assert hasattr(result, 'status')
    
    def test_extract_header_status_values(self, sample_header_image):
        """Status should be one of OK, PARTIAL, FAILED."""
        service = GridOCRService(debug=False)
        
        result = service.extract_header(sample_header_image)
        
        assert result.status in ["OK", "PARTIAL", "FAILED"]
    
    def test_full_pipeline_with_matching(self, sample_header_image, sample_students):
        """Full pipeline: extract + match should work."""
        service = GridOCRService(debug=False)
        
        # Extract
        ocr_result = service.extract_header(sample_header_image)
        
        # Match
        match_result = service.match_student(ocr_result, sample_students)
        
        assert isinstance(match_result, MatchResult)
        assert match_result.status in ["AUTO_MATCH", "AMBIGUOUS_OCR", "NO_MATCH", "OCR_FAIL"]


# =============================================================================
# MARKERS FOR PYTEST
# =============================================================================

pytestmark = [
    pytest.mark.unit,
    pytest.mark.ocr,
]
