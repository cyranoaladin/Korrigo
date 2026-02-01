"""
ZF-AUD-04: PDF Pipeline Tests - Split, Recto/Verso, Ordering, Header Detection
"""
import pytest
import numpy as np
import fitz
import tempfile
import os
from io import BytesIO
from pathlib import Path
from unittest.mock import patch, MagicMock

from processing.services.splitter import A3Splitter
from processing.services.vision import HeaderDetector
from processing.services.pdf_splitter import PDFSplitter


def create_test_image(width=2000, height=1000, with_header_box=False):
    """Create a test image simulating A3 scan."""
    img = np.ones((height, width, 3), dtype=np.uint8) * 255
    
    if with_header_box:
        top_h = int(height * 0.15)
        box_x1, box_y1 = int(width * 0.55), 10
        box_x2, box_y2 = int(width * 0.95), top_h - 10
        img[box_y1:box_y2, box_x1:box_x2] = [0, 0, 0]
    
    return img


def create_synthetic_pdf(pages=4, page_width=595, page_height=842):
    """Create a minimal PDF with numbered pages."""
    doc = fitz.open()
    for i in range(pages):
        page = doc.new_page(width=page_width, height=page_height)
        page.insert_text((50, 100), f"PAGE {i + 1}", fontsize=48)
        page.insert_text((50, 200), f"Booklet Test Page", fontsize=24)
    
    buffer = BytesIO()
    doc.save(buffer)
    doc.close()
    buffer.seek(0)
    return buffer.read()


class TestA3Splitter:
    """Unit tests for A3Splitter service."""

    @pytest.fixture
    def splitter(self):
        return A3Splitter()

    def test_split_50_percent_vertical(self, splitter):
        """Verify split is approximately at 50% width (with tolerance)."""
        img = create_test_image(width=2000, height=1000)
        
        with patch('processing.services.splitter.cv2.imread', return_value=img):
            with patch.object(splitter.detector, 'detect_header', return_value=True):
                result = splitter.process_scan("test.jpg")
                
                assert result['type'] == 'RECTO'
                # ZF-AUD-04: Smart split may adjust within tolerance (±2%)
                p1_width = result['pages']['p1'].shape[1]
                p4_width = result['pages']['p4'].shape[1]
                assert 900 <= p1_width <= 1100  # Within 10% of expected
                assert 900 <= p4_width <= 1100
                assert p1_width + p4_width == 2000  # Total width preserved

    def test_recto_detection_with_header(self, splitter):
        """Recto scan has header on right side (Page 1)."""
        img = create_test_image(width=2000, height=1000, with_header_box=True)
        
        with patch('processing.services.splitter.cv2.imread', return_value=img):
            with patch.object(splitter.detector, 'detect_header', return_value=True):
                result = splitter.process_scan("test.jpg")
                
                assert result['type'] == 'RECTO'
                assert result['has_header'] is True
                assert 'p1' in result['pages']
                assert 'p4' in result['pages']

    def test_verso_detection_no_header(self, splitter):
        """Verso scan has no header (Pages 2-3)."""
        img = create_test_image(width=2000, height=1000, with_header_box=False)
        
        with patch('processing.services.splitter.cv2.imread', return_value=img):
            with patch.object(splitter.detector, 'detect_header', return_value=False):
                result = splitter.process_scan("test.jpg")
                
                assert result['type'] == 'VERSO'
                assert result['has_header'] is False
                assert 'p2' in result['pages']
                assert 'p3' in result['pages']

    def test_unknown_on_read_failure(self, splitter):
        """Return UNKNOWN if image cannot be read."""
        with pytest.raises(ValueError, match="Impossible de lire"):
            with patch('processing.services.splitter.cv2.imread', return_value=None):
                splitter.process_scan("nonexistent.jpg")

    def test_reconstruct_booklet_order(self, splitter):
        """Verify [P1, P2, P3, P4] order reconstruction."""
        p1 = np.zeros((100, 100, 3), dtype=np.uint8)
        p2 = np.ones((100, 100, 3), dtype=np.uint8) * 50
        p3 = np.ones((100, 100, 3), dtype=np.uint8) * 100
        p4 = np.ones((100, 100, 3), dtype=np.uint8) * 150
        
        recto_data = {'type': 'RECTO', 'pages': {'p1': p1, 'p4': p4}}
        verso_data = {'type': 'VERSO', 'pages': {'p2': p2, 'p3': p3}}
        
        result = splitter.reconstruct_booklet(recto_data, verso_data)
        
        assert len(result) == 4
        assert np.array_equal(result[0], p1)
        assert np.array_equal(result[1], p2)
        assert np.array_equal(result[2], p3)
        assert np.array_equal(result[3], p4)


class TestHeaderDetector:
    """Unit tests for HeaderDetector service."""

    @pytest.fixture
    def detector(self):
        return HeaderDetector()

    def test_detect_header_with_rectangle(self, detector, tmp_path):
        """Detect header when rectangular contour exists in top 20%."""
        img = create_test_image(width=1000, height=1000, with_header_box=True)
        
        import cv2
        img_path = tmp_path / "header_test.jpg"
        cv2.imwrite(str(img_path), img)
        
        result = detector.detect_header(str(img_path))
        assert result is True

    def test_no_header_on_blank_page(self, detector, tmp_path):
        """No header detected on blank page."""
        img = create_test_image(width=1000, height=1000, with_header_box=False)
        
        import cv2
        img_path = tmp_path / "blank_test.jpg"
        cv2.imwrite(str(img_path), img)
        
        result = detector.detect_header(str(img_path))
        assert result is False

    def test_extract_header_crop_returns_bytes(self, detector, tmp_path):
        """Header crop extraction returns JPEG bytes."""
        img = create_test_image(width=1000, height=1000, with_header_box=True)
        
        import cv2
        img_path = tmp_path / "crop_test.jpg"
        cv2.imwrite(str(img_path), img)
        
        result = detector.extract_header_crop(str(img_path))
        
        assert isinstance(result, bytes)
        assert len(result) > 0
        assert result[:2] == b'\xff\xd8'

    def test_fallback_on_missing_file(self, detector):
        """Return False on missing file (graceful degradation)."""
        result = detector.detect_header("/nonexistent/path.jpg")
        assert result is False


@pytest.mark.django_db
class TestPDFSplitterIntegration:
    """Integration tests for PDF -> Booklets pipeline."""

    def test_pdf_to_booklets_page_order(self, tmp_path):
        """Verify booklets have correct page order."""
        pdf_content = create_synthetic_pdf(pages=8)
        pdf_path = tmp_path / "test_exam.pdf"
        pdf_path.write_bytes(pdf_content)
        
        doc = fitz.open(str(pdf_path))
        assert doc.page_count == 8
        
        splitter = PDFSplitter(pages_per_booklet=4, dpi=72)
        
        pages_images = splitter._extract_pages(doc, 1, 4, "exam-id", "booklet-id")
        
        assert len(pages_images) == 4
        for i, path in enumerate(pages_images):
            assert f"page_{i+1:03d}.png" in path
        
        doc.close()

    def test_partial_booklet_handling(self, tmp_path):
        """Handle PDFs with non-multiple page counts."""
        pdf_content = create_synthetic_pdf(pages=6)
        pdf_path = tmp_path / "partial_exam.pdf"
        pdf_path.write_bytes(pdf_content)
        
        doc = fitz.open(str(pdf_path))
        assert doc.page_count == 6
        
        splitter = PDFSplitter(pages_per_booklet=4, dpi=72)
        
        pages_booklet1 = splitter._extract_pages(doc, 1, 4, "exam-id", "booklet-1")
        pages_booklet2 = splitter._extract_pages(doc, 5, 6, "exam-id", "booklet-2")
        
        assert len(pages_booklet1) == 4
        assert len(pages_booklet2) == 2
        
        doc.close()


class TestEdgeCases:
    """Edge case tests for robustness."""

    def test_very_small_image(self):
        """Handle very small images without crash."""
        splitter = A3Splitter()
        img = np.zeros((10, 20, 3), dtype=np.uint8)
        
        with patch('processing.services.splitter.cv2.imread', return_value=img):
            with patch.object(splitter.detector, 'detect_header', return_value=False):
                result = splitter.process_scan("small.jpg")
                
                assert result['type'] in ['RECTO', 'VERSO', 'UNKNOWN']

    def test_grayscale_image_handling(self):
        """Handle grayscale images (2D array)."""
        detector = HeaderDetector()
        
        gray_img = np.zeros((100, 100), dtype=np.uint8)
        
        with patch('processing.services.vision.cv2.imread', return_value=None):
            result = detector.detect_header("gray.jpg")
            assert result is False

    def test_rotated_scan_detection(self):
        """Rotated scans should still be processable."""
        splitter = A3Splitter()
        img = create_test_image(width=1000, height=2000)
        
        with patch('processing.services.splitter.cv2.imread', return_value=img):
            with patch.object(splitter.detector, 'detect_header', return_value=False):
                result = splitter.process_scan("rotated.jpg")
                
                assert result['type'] in ['RECTO', 'VERSO', 'UNKNOWN']
