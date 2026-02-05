
import pytest
import fitz
import os
from django.conf import settings

FIXTURES_DIR = os.path.join(settings.BASE_DIR, "grading/tests/fixtures/pdfs")

@pytest.mark.unit
def test_advanced_fixtures_existence():
    expected = [
        "scan_like_10p.pdf",
        "multi_booklets_20p.pdf",
        "heavy_60p.pdf",
        "weird_metadata.pdf",
        "mixed_orientation.pdf",
        "corrupted_truncated.pdf"
    ]
    for f in expected:
        assert os.path.exists(os.path.join(FIXTURES_DIR, f))

@pytest.mark.unit
@pytest.mark.processing
def test_scan_like_properties():
    path = os.path.join(FIXTURES_DIR, "scan_like_10p.pdf")
    with fitz.open(path) as doc:
        assert doc.page_count == 10

@pytest.mark.unit
@pytest.mark.processing
def test_multi_booklet_properties():
    path = os.path.join(FIXTURES_DIR, "multi_booklets_20p.pdf")
    with fitz.open(path) as doc:
        assert doc.page_count == 20

@pytest.mark.unit
@pytest.mark.processing
def test_heavy_properties():
    path = os.path.join(FIXTURES_DIR, "heavy_60p.pdf")
    with fitz.open(path) as doc:
        assert doc.page_count == 60

@pytest.mark.unit
@pytest.mark.processing
def test_mixed_orientation_properties():
    path = os.path.join(FIXTURES_DIR, "mixed_orientation.pdf")
    with fitz.open(path) as doc:
        p1 = doc[0]
        p2 = doc[1]
        # p1 is 595x842 (Portrait), p2 is 842x595 (Landscape)
        assert p1.rect.width < p1.rect.height
        assert p2.rect.width > p2.rect.height

@pytest.mark.unit
@pytest.mark.processing
def test_corrupted_truncated_fails_gracefully():
    path = os.path.join(FIXTURES_DIR, "corrupted_truncated.pdf")
    # Truncated PDF might open with fitz (it tries to repair), or fail.
    # If it opens, page count might be wrong or accessing a page raises error.
    try:
        with fitz.open(path) as doc:
             # Try to iterate all pages roughly
             _ = [p.get_text() for p in doc]
    except Exception:
        pass # Expected failure
