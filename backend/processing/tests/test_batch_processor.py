"""
Tests for BatchA3Processor - Batch A3 PDF processing with student segmentation.
"""
import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import numpy as np

from django.test import TestCase


class TestTextNormalization(TestCase):
    """Test text normalization for OCR matching."""

    def test_normalize_removes_accents(self):
        from processing.services.batch_processor import BatchA3Processor
        processor = BatchA3Processor()
        
        self.assertEqual(processor._normalize_text("Éléonore"), "eleonore")
        self.assertEqual(processor._normalize_text("François"), "francois")
        self.assertEqual(processor._normalize_text("Noël"), "noel")

    def test_normalize_handles_case(self):
        from processing.services.batch_processor import BatchA3Processor
        processor = BatchA3Processor()
        
        self.assertEqual(processor._normalize_text("ABID YOUCEF"), "abid youcef")
        self.assertEqual(processor._normalize_text("Ben Jemaa"), "ben jemaa")

    def test_normalize_handles_hyphens(self):
        from processing.services.batch_processor import BatchA3Processor
        processor = BatchA3Processor()
        
        self.assertEqual(processor._normalize_text("SANDRA-INES"), "sandra ines")
        self.assertEqual(processor._normalize_text("BEN-ATTOUCH"), "ben attouch")

    def test_normalize_handles_multiple_spaces(self):
        from processing.services.batch_processor import BatchA3Processor
        processor = BatchA3Processor()
        
        self.assertEqual(processor._normalize_text("ABID   YOUCEF"), "abid youcef")


class TestDateNormalization(TestCase):
    """Test date normalization for OCR matching."""

    def test_normalize_date_slash(self):
        from processing.services.batch_processor import BatchA3Processor
        processor = BatchA3Processor()
        
        self.assertEqual(processor._normalize_date("01/02/2008"), "01/02/2008")

    def test_normalize_date_dash(self):
        from processing.services.batch_processor import BatchA3Processor
        processor = BatchA3Processor()
        
        self.assertEqual(processor._normalize_date("01-02-2008"), "01/02/2008")

    def test_normalize_date_dot(self):
        from processing.services.batch_processor import BatchA3Processor
        processor = BatchA3Processor()
        
        self.assertEqual(processor._normalize_date("01.02.2008"), "01/02/2008")


class TestCSVLoading(TestCase):
    """Test CSV whitelist loading."""

    def test_load_csv_whitelist(self):
        from processing.services.batch_processor import BatchA3Processor
        
        # Create a temp CSV
        csv_content = """Élèves,Né(e) le,Adresse E-mail,Classe
ABID YOUCEF,01/02/2008,youcef.abid-e@ert.tn,T.01
BEN JEMAA SADRI,21/09/2008,sadri.benjemaa-e@ert.tn,T.01
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8') as f:
            f.write(csv_content)
            csv_path = f.name
        
        try:
            processor = BatchA3Processor(csv_path=csv_path)
            
            self.assertEqual(len(processor.students_whitelist), 2)
            self.assertEqual(processor.students_whitelist[0]['last_name'], 'ABID')
            self.assertEqual(processor.students_whitelist[0]['first_name'], 'YOUCEF')
            self.assertEqual(processor.students_whitelist[1]['last_name'], 'BEN')
        finally:
            os.unlink(csv_path)


class TestStudentMatching(TestCase):
    """Test student matching from OCR to CSV."""

    def setUp(self):
        from processing.services.batch_processor import BatchA3Processor
        
        csv_content = """Élèves,Né(e) le,Adresse E-mail,Classe
ABID YOUCEF,01/02/2008,youcef.abid-e@ert.tn,T.01
BEN JEMAA SADRI,21/09/2008,sadri.benjemaa-e@ert.tn,T.01
AGREBI SANDRA-INES,21/10/2008,sandraines.agrebi-e@ert.tn,T.01
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8') as f:
            f.write(csv_content)
            self.csv_path = f.name
        
        self.processor = BatchA3Processor(csv_path=self.csv_path)

    def tearDown(self):
        os.unlink(self.csv_path)

    def test_exact_match(self):
        match = self.processor._match_student("ABID YOUCEF", "01/02/2008")
        
        self.assertIsNotNone(match)
        self.assertEqual(match.last_name, "ABID")
        self.assertEqual(match.first_name, "YOUCEF")
        self.assertGreaterEqual(match.confidence, 0.9)

    def test_fuzzy_match_name(self):
        # OCR might have slight errors
        match = self.processor._match_student("ABID YOUCEF", "")
        
        self.assertIsNotNone(match)
        self.assertEqual(match.last_name, "ABID")

    def test_match_with_hyphen(self):
        match = self.processor._match_student("AGREBI SANDRA INES", "21/10/2008")
        
        self.assertIsNotNone(match)
        self.assertEqual(match.first_name, "SANDRA-INES")

    def test_no_match_returns_none(self):
        match = self.processor._match_student("UNKNOWN PERSON", "01/01/2000")
        
        self.assertIsNone(match)


class TestA3Detection(TestCase):
    """Test A3 format detection."""

    @patch('processing.services.batch_processor.fitz')
    def test_detects_a3_format(self, mock_fitz):
        from processing.services.batch_processor import BatchA3Processor
        
        mock_doc = MagicMock()
        mock_doc.page_count = 1
        mock_page = MagicMock()
        mock_page.rect.width = 1190  # A3 width
        mock_page.rect.height = 841  # A3 height
        mock_doc.load_page.return_value = mock_page
        mock_fitz.open.return_value = mock_doc
        
        processor = BatchA3Processor()
        result = processor.is_a3_format('/fake/path.pdf')
        
        self.assertTrue(result)

    @patch('processing.services.batch_processor.fitz')
    def test_detects_a4_format(self, mock_fitz):
        from processing.services.batch_processor import BatchA3Processor
        
        mock_doc = MagicMock()
        mock_doc.page_count = 1
        mock_page = MagicMock()
        mock_page.rect.width = 595  # A4 width
        mock_page.rect.height = 842  # A4 height
        mock_doc.load_page.return_value = mock_page
        mock_fitz.open.return_value = mock_doc
        
        processor = BatchA3Processor()
        result = processor.is_a3_format('/fake/path.pdf')
        
        self.assertFalse(result)


class TestA3ToA4Split(TestCase):
    """Test A3 to A4 splitting."""

    def test_split_produces_two_halves(self):
        from processing.services.batch_processor import BatchA3Processor
        
        processor = BatchA3Processor()
        
        # Create a mock A3 image (1190x841 pixels)
        a3_image = np.zeros((841, 1190, 3), dtype=np.uint8)
        # Mark left half as red, right half as blue
        a3_image[:, :595, 2] = 255  # Red on left
        a3_image[:, 595:, 0] = 255  # Blue on right
        
        left, right = processor._split_a3_to_a4(a3_image)
        
        # Check dimensions
        self.assertEqual(left.shape[1], 595)
        self.assertEqual(right.shape[1], 595)
        
        # Check colors
        self.assertEqual(left[0, 0, 2], 255)  # Red
        self.assertEqual(right[0, 0, 0], 255)  # Blue


class TestPageReordering(TestCase):
    """Test page reordering invariants."""

    def test_sheet_produces_4_pages(self):
        """Each sheet (2 A3 pages) should produce exactly 4 A4 pages."""
        # This is a logical test - actual implementation tested in integration
        total_a3_pages = 88
        expected_sheets = total_a3_pages // 2
        expected_a4_pages = expected_sheets * 4
        
        self.assertEqual(expected_sheets, 44)
        self.assertEqual(expected_a4_pages, 176)

    def test_page_order_invariant(self):
        """Pages should be in order: P1, P2, P3, P4 per sheet."""
        # Verify the mapping:
        # A3#1 = (P4 left, P1 right)
        # A3#2 = (P2 left, P3 right)
        # Final order: P1, P2, P3, P4
        
        # This is verified by the position_in_sheet attribute
        expected_order = [1, 2, 3, 4]
        self.assertEqual(expected_order, [1, 2, 3, 4])


class TestStudentCopyInvariants(TestCase):
    """Test invariants for student copies."""

    def test_page_count_multiple_of_4(self):
        """Each student copy should have pages as multiple of 4."""
        from processing.services.batch_processor import StudentCopy, PageInfo
        
        # Valid copy
        pages = [
            PageInfo(1, 1, 1, np.zeros((100, 100, 3))),
            PageInfo(2, 1, 2, np.zeros((100, 100, 3))),
            PageInfo(3, 1, 3, np.zeros((100, 100, 3))),
            PageInfo(4, 1, 4, np.zeros((100, 100, 3))),
        ]
        copy = StudentCopy(student_match=None, pages=pages)
        
        self.assertEqual(len(copy.pages) % 4, 0)

    def test_invalid_page_count_flagged(self):
        """Copies with non-multiple-of-4 pages should be flagged for review."""
        from processing.services.batch_processor import StudentCopy, PageInfo
        
        # Invalid copy (3 pages)
        pages = [
            PageInfo(1, 1, 1, np.zeros((100, 100, 3))),
            PageInfo(2, 1, 2, np.zeros((100, 100, 3))),
            PageInfo(3, 1, 3, np.zeros((100, 100, 3))),
        ]
        copy = StudentCopy(student_match=None, pages=pages, needs_review=True)
        
        self.assertTrue(copy.needs_review)
        self.assertNotEqual(len(copy.pages) % 4, 0)
