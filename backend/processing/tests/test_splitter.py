
import pytest
import numpy as np
from unittest.mock import MagicMock, patch
from processing.services.splitter import A3Splitter

@pytest.fixture
def splitter():
    return A3Splitter()

@pytest.fixture
def mock_image():
    # Create a dummy image (100x200) A3-like landscape
    return np.zeros((100, 200, 3), dtype=np.uint8)

def test_process_scan_recto(splitter, mock_image):
    with patch('processing.services.splitter.cv2.imread', return_value=mock_image):
        with patch.object(splitter.detector, 'detect_header', return_value=True):
            # If detecting header on right crop returns True -> RECTO
            result = splitter.process_scan("dummy_path.jpg")
            
            assert result['type'] == 'RECTO'
            assert result['has_header'] is True
            assert 'p1' in result['pages'] # Header page
            assert 'p4' in result['pages'] # Last page

def test_process_scan_verso(splitter, mock_image):
    with patch('processing.services.splitter.cv2.imread', return_value=mock_image):
        with patch.object(splitter.detector, 'detect_header', return_value=False):
            # If detecting header returns False -> VERSO
            result = splitter.process_scan("dummy_path.jpg")
            
            assert result['type'] == 'VERSO'
            assert result['has_header'] is False
            assert 'p2' in result['pages']
            assert 'p3' in result['pages']
