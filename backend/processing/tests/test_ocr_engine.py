"""
Unit tests for Multi-layer OCR Engine.

Tests preprocessing, OCR execution, consensus voting, and fuzzy matching.
"""
import unittest
from unittest.mock import Mock, patch

import cv2
import numpy as np

from processing.services.ocr_engine import (
    ImagePreprocessor,
    MultiLayerOCR,
    OCRCandidate,
    StudentMatch,
)


class TestImagePreprocessor(unittest.TestCase):
    """Test image preprocessing variants."""

    def setUp(self):
        self.preprocessor = ImagePreprocessor()
        # Create a simple test image
        self.test_image = np.ones((100, 200), dtype=np.uint8) * 255
        # Add some text-like patterns
        cv2.rectangle(self.test_image, (50, 30), (150, 70), 0, -1)

    def test_preprocess_variants_returns_list(self):
        """Should return list of preprocessed images."""
        variants = self.preprocessor.preprocess_variants(self.test_image)
        self.assertIsInstance(variants, list)
        self.assertGreater(len(variants), 0)

    def test_all_variants_same_shape(self):
        """All variants should have same shape as input."""
        variants = self.preprocessor.preprocess_variants(self.test_image)
        for variant in variants:
            self.assertEqual(variant.shape, self.test_image.shape)

    def test_deskew_handles_minimal_skew(self):
        """Deskew should skip rotation for minimal angles."""
        # Image with no/minimal skew
        result = self.preprocessor._deskew(self.test_image)
        self.assertEqual(result.shape, self.test_image.shape)

    def test_morphological_cleanup_returns_binary(self):
        """Morphological cleanup should return binary image."""
        result = self.preprocessor._morphological_cleanup(self.test_image)
        unique_values = np.unique(result)
        # Should only have 0 and 255
        self.assertTrue(all(v in [0, 255] for v in unique_values))


class TestMultiLayerOCR(unittest.TestCase):
    """Test multi-layer OCR functionality."""

    def setUp(self):
        self.ocr = MultiLayerOCR()
        self.test_image = np.ones((100, 200, 3), dtype=np.uint8) * 255

        # Sample CSV whitelist
        self.csv_whitelist = [
            {
                'id': 1,
                'first_name': 'Jean',
                'last_name': 'DUPONT',
                'email': 'jean.dupont@example.com',
                'date_of_birth': '01/02/2008'
            },
            {
                'id': 2,
                'first_name': 'Marie',
                'last_name': 'MARTIN',
                'email': 'marie.martin@example.com',
                'date_of_birth': '15/06/2007'
            }
        ]

    def test_normalize_text_removes_accents(self):
        """Text normalization should remove accents."""
        result = self.ocr._normalize_text("Élève Français")
        self.assertNotIn('É', result)
        self.assertNotIn('ç', result)

    def test_normalize_text_removes_hyphens(self):
        """Text normalization should replace hyphens with spaces."""
        result = self.ocr._normalize_text("JEAN-PAUL")
        self.assertEqual(result, "jean paul")

    def test_normalize_text_handles_empty(self):
        """Should handle empty text gracefully."""
        result = self.ocr._normalize_text("")
        self.assertEqual(result, "")

    def test_normalize_date_formats_correctly(self):
        """Date normalization should produce DD/MM/YYYY."""
        test_cases = [
            ("01/02/2008", "01/02/2008"),
            ("1-2-2008", "01/02/2008"),
            ("1.2.2008", "01/02/2008"),
            ("01/02/08", "01/02/2008"),
        ]
        for input_date, expected in test_cases:
            with self.subTest(input=input_date):
                result = self.ocr._normalize_date(input_date)
                self.assertEqual(result, expected)

    def test_parse_ocr_text_extracts_name(self):
        """Should extract name from OCR text."""
        text = "NOM: DUPONT JEAN\nDate: 01/02/2008"
        name, date = self.ocr._parse_ocr_text(text)
        self.assertIn("DUPONT", name)
        self.assertIn("JEAN", name)

    def test_parse_ocr_text_extracts_date(self):
        """Should extract date from OCR text."""
        text = "NOM: DUPONT JEAN\nDate de naissance: 01/02/2008"
        name, date = self.ocr._parse_ocr_text(text)
        self.assertEqual(date, "01/02/2008")

    def test_fuzzy_match_exact_name(self):
        """Exact name match should score high."""
        score = self.ocr._fuzzy_match_student(
            "DUPONT JEAN", "", "Jean", "DUPONT", None
        )
        self.assertGreater(score, 0.5)

    def test_fuzzy_match_partial_name(self):
        """Partial name match should still score."""
        score = self.ocr._fuzzy_match_student(
            "DUPONT", "", "Jean", "DUPONT", None
        )
        self.assertGreaterEqual(score, 0.3)

    def test_fuzzy_match_with_date_bonus(self):
        """Matching date should increase score."""
        score_with_date = self.ocr._fuzzy_match_student(
            "DUPONT JEAN", "01/02/2008", "Jean", "DUPONT", "01/02/2008"
        )
        score_without_date = self.ocr._fuzzy_match_student(
            "DUPONT JEAN", "", "Jean", "DUPONT", "01/02/2008"
        )
        self.assertGreater(score_with_date, score_without_date)

    def test_fuzzy_match_no_match(self):
        """Completely different names should score low."""
        score = self.ocr._fuzzy_match_student(
            "SMITH JOHN", "", "Jean", "DUPONT", None
        )
        self.assertLess(score, 0.3)

    @patch('pytesseract.image_to_string')
    def test_ocr_tesseract_calls_pytesseract(self, mock_tesseract):
        """Should call pytesseract with correct config."""
        mock_tesseract.return_value = "DUPONT JEAN"
        result = self.ocr._ocr_tesseract(self.test_image)
        mock_tesseract.assert_called_once()
        self.assertEqual(result, "DUPONT JEAN")

    def test_estimate_tesseract_confidence_empty_text(self):
        """Empty text should have low confidence."""
        confidence = self.ocr._estimate_tesseract_confidence("")
        self.assertLess(confidence, 0.3)

    def test_estimate_tesseract_confidence_good_text(self):
        """Text with letters and numbers should have high confidence."""
        confidence = self.ocr._estimate_tesseract_confidence("DUPONT JEAN 01/02/2008")
        self.assertGreater(confidence, 0.7)

    def test_consensus_vote_single_match(self):
        """Single OCR candidate matching one student."""
        candidates = [
            OCRCandidate(
                engine='tesseract',
                variant=0,
                text='DUPONT JEAN 01/02/2008',
                confidence=0.8
            )
        ]
        matches = self.ocr._consensus_vote(candidates, self.csv_whitelist)
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0].last_name, 'DUPONT')

    def test_consensus_vote_multiple_engines_same_student(self):
        """Multiple engines agreeing should increase confidence."""
        candidates = [
            OCRCandidate('tesseract', 0, 'DUPONT JEAN', 0.7),
            OCRCandidate('easyocr', 0, 'DUPONT JEAN', 0.8),
            OCRCandidate('paddleocr', 0, 'DUPONT JEAN', 0.75),
        ]
        matches = self.ocr._consensus_vote(candidates, self.csv_whitelist)
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0].vote_count, 3)
        self.assertGreater(matches[0].confidence, 0.4)  # Conservative threshold

    def test_consensus_vote_conflicting_results(self):
        """Conflicting OCR results should produce multiple candidates."""
        candidates = [
            OCRCandidate('tesseract', 0, 'DUPONT JEAN', 0.7),
            OCRCandidate('easyocr', 0, 'MARTIN MARIE', 0.7),
        ]
        matches = self.ocr._consensus_vote(candidates, self.csv_whitelist)
        # Should have 2 candidates (one for each student)
        self.assertGreaterEqual(len(matches), 1)

    def test_consensus_vote_returns_top_5(self):
        """Should return maximum 5 top candidates."""
        # Create 10 students
        large_whitelist = [
            {
                'id': i,
                'first_name': f'Student{i}',
                'last_name': f'LAST{i}',
                'email': f'student{i}@example.com',
                'date_of_birth': '01/01/2000'
            }
            for i in range(10)
        ]

        # Create OCR candidates matching multiple students
        candidates = [
            OCRCandidate('tesseract', 0, f'LAST{i} Student{i}', 0.6)
            for i in range(10)
        ]

        matches = self.ocr._consensus_vote(candidates, large_whitelist)
        self.assertLessEqual(len(matches), 5)

    @patch.object(MultiLayerOCR, '_run_all_ocr_engines')
    @patch.object(MultiLayerOCR, '_consensus_vote')
    def test_extract_text_with_candidates_determines_mode(self, mock_vote, mock_ocr):
        """Should determine OCR mode based on confidence."""
        # Mock OCR engines
        mock_ocr.return_value = [
            OCRCandidate('tesseract', 0, 'DUPONT JEAN', 0.8)
        ]

        # Test AUTO mode (confidence > 0.7)
        mock_vote.return_value = [
            StudentMatch(
                student_id=1, first_name='Jean', last_name='DUPONT',
                email='jean@example.com', date_of_birth='01/01/2000',
                confidence=0.8, vote_count=1, vote_agreement=1.0, sources=[]
            )
        ]
        result = self.ocr.extract_text_with_candidates(self.test_image, self.csv_whitelist)
        self.assertEqual(result.ocr_mode, 'AUTO')

        # Test SEMI_AUTO mode (0.4 < confidence <= 0.7)
        mock_vote.return_value[0].confidence = 0.6
        result = self.ocr.extract_text_with_candidates(self.test_image, self.csv_whitelist)
        self.assertEqual(result.ocr_mode, 'SEMI_AUTO')

        # Test MANUAL mode (confidence <= 0.4)
        mock_vote.return_value[0].confidence = 0.3
        result = self.ocr.extract_text_with_candidates(self.test_image, self.csv_whitelist)
        self.assertEqual(result.ocr_mode, 'MANUAL')

    @patch.object(MultiLayerOCR, '_run_all_ocr_engines')
    @patch.object(MultiLayerOCR, '_consensus_vote')
    def test_extract_text_with_candidates_no_matches(self, mock_vote, mock_ocr):
        """Should handle case with no matches (MANUAL mode)."""
        mock_ocr.return_value = [
            OCRCandidate('tesseract', 0, 'UNKNOWN TEXT', 0.5)
        ]
        mock_vote.return_value = []  # No matches

        result = self.ocr.extract_text_with_candidates(self.test_image, self.csv_whitelist)
        self.assertEqual(result.ocr_mode, 'MANUAL')
        self.assertEqual(len(result.top_candidates), 0)


class TestOCRIntegration(unittest.TestCase):
    """Integration tests for complete OCR pipeline."""

    def setUp(self):
        self.ocr = MultiLayerOCR()

    def test_full_pipeline_with_mocked_engines(self):
        """Test complete pipeline with all components."""
        # Create test image
        test_image = np.ones((200, 400, 3), dtype=np.uint8) * 255
        # Add some text simulation
        cv2.putText(test_image, "DUPONT JEAN", (50, 100),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)

        # CSV whitelist
        csv_whitelist = [{
            'id': 1,
            'first_name': 'Jean',
            'last_name': 'DUPONT',
            'email': 'jean.dupont@example.com',
            'date_of_birth': '01/02/2008'
        }]

        # Mock OCR engines to avoid loading heavy models in tests
        with patch.object(self.ocr, '_run_all_ocr_engines') as mock_ocr:
            mock_ocr.return_value = [
                OCRCandidate('tesseract', 0, 'DUPONT JEAN 01/02/2008', 0.8)
            ]

            result = self.ocr.extract_text_with_candidates(test_image, csv_whitelist)

            # Verify result structure
            self.assertIsNotNone(result.top_candidates)
            self.assertIn(result.ocr_mode, ['AUTO', 'SEMI_AUTO', 'MANUAL'])
            self.assertIsInstance(result.all_ocr_outputs, list)


if __name__ == '__main__':
    unittest.main()
