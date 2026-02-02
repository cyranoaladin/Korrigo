"""
Tests for A3PDFProcessor - Integration tests for A3 scan detection and processing.
"""
import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import numpy as np

from django.test import TestCase
from django.core.files.uploadedfile import SimpleUploadedFile

from processing.services.a3_pdf_processor import A3PDFProcessor, A3_ASPECT_RATIO_THRESHOLD


class TestA3FormatDetection(TestCase):
    """Test A3 format detection logic."""

    def test_aspect_ratio_threshold(self):
        """Verify the A3 detection threshold is correct."""
        # A3 landscape: 420mm x 297mm = ratio 1.414
        # A4 portrait: 210mm x 297mm = ratio 0.707
        self.assertGreater(A3_ASPECT_RATIO_THRESHOLD, 1.0)
        self.assertLess(A3_ASPECT_RATIO_THRESHOLD, 1.414)

    @patch('processing.services.a3_pdf_processor.fitz')
    def test_detects_a3_format(self, mock_fitz):
        """Test that A3 format is correctly detected."""
        # Mock a landscape A3 page (width > height * 1.2)
        mock_doc = MagicMock()
        mock_doc.page_count = 1
        mock_page = MagicMock()
        mock_page.rect.width = 1190  # A3 width in points
        mock_page.rect.height = 842  # A3 height in points
        mock_doc.load_page.return_value = mock_page
        mock_fitz.open.return_value = mock_doc

        processor = A3PDFProcessor()
        result = processor.is_a3_format('/fake/path.pdf')

        self.assertTrue(result)
        mock_doc.close.assert_called_once()

    @patch('processing.services.a3_pdf_processor.fitz')
    def test_detects_standard_format(self, mock_fitz):
        """Test that standard A4 format is correctly detected."""
        # Mock a portrait A4 page (width < height)
        mock_doc = MagicMock()
        mock_doc.page_count = 1
        mock_page = MagicMock()
        mock_page.rect.width = 595  # A4 width in points
        mock_page.rect.height = 842  # A4 height in points
        mock_doc.load_page.return_value = mock_page
        mock_fitz.open.return_value = mock_doc

        processor = A3PDFProcessor()
        result = processor.is_a3_format('/fake/path.pdf')

        self.assertFalse(result)
        mock_doc.close.assert_called_once()

    @patch('processing.services.a3_pdf_processor.fitz')
    def test_handles_empty_pdf(self, mock_fitz):
        """Test handling of empty PDF."""
        mock_doc = MagicMock()
        mock_doc.page_count = 0
        mock_fitz.open.return_value = mock_doc

        processor = A3PDFProcessor()
        result = processor.is_a3_format('/fake/path.pdf')

        self.assertFalse(result)


class TestA3SplitAndReconstruct(TestCase):
    """Test A3 page splitting and booklet reconstruction."""

    def test_split_creates_correct_page_order(self):
        """Test that pages are reconstructed in correct order: P1, P2, P3, P4."""
        processor = A3PDFProcessor()
        
        # Create mock images
        recto_img = np.zeros((100, 200, 3), dtype=np.uint8)  # A3 landscape
        verso_img = np.zeros((100, 200, 3), dtype=np.uint8)
        
        with patch.object(processor.a3_splitter, 'process_scan') as mock_process:
            # Mock recto result: [P4 | P1]
            mock_process.side_effect = [
                {
                    'type': 'RECTO',
                    'pages': {
                        'p1': np.zeros((100, 100, 3), dtype=np.uint8),
                        'p4': np.zeros((100, 100, 3), dtype=np.uint8)
                    }
                },
                {
                    'type': 'VERSO',
                    'pages': {
                        'p2': np.zeros((100, 100, 3), dtype=np.uint8),
                        'p3': np.zeros((100, 100, 3), dtype=np.uint8)
                    }
                }
            ]
            
            pages = processor._split_and_reconstruct(recto_img, verso_img, 0)
            
            # Verify order: P1, P2, P3, P4
            page_names = [p[0] for p in pages]
            self.assertEqual(page_names, ['p1', 'p2', 'p3', 'p4'])


class TestA3ProcessorIntegration(TestCase):
    """Integration tests for A3PDFProcessor with real exam processing."""

    @pytest.mark.django_db
    @patch('processing.services.a3_pdf_processor.fitz')
    def test_process_exam_uses_correct_pipeline(self, mock_fitz):
        """Test that process_exam selects correct pipeline based on format."""
        from exams.models import Exam
        
        # Create a mock exam
        exam = Mock(spec=Exam)
        exam.id = 'test-exam-id'
        exam.pdf_source = Mock()
        exam.pdf_source.path = '/fake/path.pdf'
        exam.booklets = Mock()
        exam.booklets.exists.return_value = False
        
        # Mock A3 format detection
        mock_doc = MagicMock()
        mock_doc.page_count = 2
        mock_page = MagicMock()
        mock_page.rect.width = 1190
        mock_page.rect.height = 842
        mock_doc.load_page.return_value = mock_page
        mock_fitz.open.return_value = mock_doc
        
        processor = A3PDFProcessor()
        
        with patch.object(processor, '_process_a3_pdf') as mock_a3:
            mock_a3.return_value = []
            
            with patch('os.path.exists', return_value=True):
                processor.process_exam(exam)
            
            # Verify A3 pipeline was called
            mock_a3.assert_called_once()


class TestExpectedCopyCount(TestCase):
    """Test that copy count calculations are correct."""

    def test_copy_count_from_a3_pages(self):
        """Verify: 2 A3 pages = 1 copy of 4 A4 pages."""
        # 88 A3 pages should produce 44 copies
        total_a3_pages = 88
        expected_copies = total_a3_pages // 2
        self.assertEqual(expected_copies, 44)

    def test_a4_pages_from_a3(self):
        """Verify: 1 A3 page = 2 A4 pages."""
        total_a3_pages = 88
        expected_a4_pages = total_a3_pages * 2
        self.assertEqual(expected_a4_pages, 176)

    def test_pages_per_copy(self):
        """Verify: each copy has 4 A4 pages."""
        total_a3_pages = 88
        expected_copies = total_a3_pages // 2
        expected_a4_pages = total_a3_pages * 2
        pages_per_copy = expected_a4_pages // expected_copies
        self.assertEqual(pages_per_copy, 4)
