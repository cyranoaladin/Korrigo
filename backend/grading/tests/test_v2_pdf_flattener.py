"""
Tests for PDFFlattener handling of VRAI/FAUX stamp annotations.
Uses mocks for fitz (PyMuPDF) to avoid needing actual PDF files.
"""
import pytest
import uuid
from unittest.mock import MagicMock, patch, PropertyMock
from django.contrib.auth import get_user_model

from exams.models import Exam, Copy, Booklet
from grading.models import Annotation

User = get_user_model()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def exam(db):
    return Exam.objects.create(
        name="Test Exam",
        grading_structure=[
            {"label": "Ex1", "points": 10, "children": [
                {"label": "Q1", "points": 5},
                {"label": "Q2", "points": 5},
            ]}
        ],
    )


@pytest.fixture
def copy_with_booklet(db, exam, teacher_user, mock_media, settings):
    """Copy with a booklet pointing to a fake image path that we mock away."""
    import os
    copy = Copy.objects.create(
        exam=exam,
        status=Copy.Status.READY,
        assigned_corrector=teacher_user,
        anonymous_id=f"ANON-{uuid.uuid4().hex[:8]}",
    )
    booklet = Booklet.objects.create(
        exam=exam,
        start_page=1,
        end_page=2,
        pages_images=["page_001.png", "page_002.png"],
    )
    copy.booklets.add(booklet)

    # Create stub image files so os.path.exists passes
    for img in booklet.pages_images:
        full = os.path.join(settings.MEDIA_ROOT, img)
        with open(full, "wb") as f:
            f.write(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)

    return copy


def _create_annotation(copy, teacher_user, ann_type, page_index=0, **kwargs):
    defaults = dict(
        x=0.2, y=0.3, w=0.1, h=0.1,
        content="", score_delta=None,
    )
    defaults.update(kwargs)
    return Annotation.objects.create(
        copy=copy,
        page_index=page_index,
        type=ann_type,
        created_by=teacher_user,
        **defaults,
    )


# ---------------------------------------------------------------------------
# Mock helpers
# ---------------------------------------------------------------------------

def _build_mock_fitz():
    """Return a mock fitz module with enough surface for PDFFlattener."""
    mock_fitz = MagicMock()

    # fitz.Rect
    mock_rect = MagicMock()
    mock_rect.width = 595
    mock_rect.height = 842

    # fitz.open for images
    mock_img_doc = MagicMock()
    mock_img_page = MagicMock()
    mock_img_page.rect = mock_rect
    mock_img_doc.__getitem__ = MagicMock(return_value=mock_img_page)
    mock_img_doc.convert_to_pdf.return_value = b"%PDF-fake"

    # fitz.open for the img_pdf intermediate
    mock_img_pdf = MagicMock()

    # Main doc
    mock_doc = MagicMock()
    mock_page = MagicMock()
    mock_shape = MagicMock()
    mock_page.new_shape.return_value = mock_shape
    mock_page.rect = mock_rect
    mock_doc.new_page.return_value = mock_page
    mock_doc.write.return_value = b"%PDF-flattened"

    # fitz.open dispatcher: called without args for doc, with path for image, with "pdf" for img_pdf
    call_count = {"n": 0}

    def fitz_open_side_effect(*args, **kwargs):
        if not args:
            return mock_doc
        if args[0] == "pdf":
            return mock_img_pdf
        # It's an image path
        return mock_img_doc

    mock_fitz.open.side_effect = fitz_open_side_effect
    mock_fitz.Rect = lambda *a: MagicMock(width=595, height=842)
    mock_fitz.Point = lambda x, y: (x, y)
    # TextWriter must be a callable that returns a simple mock (not a spec'd one)
    mock_fitz.TextWriter = lambda *a, **kw: MagicMock()

    return mock_fitz, mock_shape, mock_doc


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestPDFFlattenerVraiFaux:

    @patch("processing.services.pdf_flattener.fitz")
    @patch("processing.services.pdf_flattener.os.path.exists", return_value=True)
    def test_flattener_handles_vrai_annotation(
        self, mock_exists, mock_fitz_module, copy_with_booklet, teacher_user
    ):
        """PDFFlattener does not crash when processing a VRAI annotation."""
        mock_fitz, mock_shape, mock_doc = _build_mock_fitz()
        mock_fitz_module.open = mock_fitz.open
        mock_fitz_module.Rect = mock_fitz.Rect
        mock_fitz_module.Point = mock_fitz.Point
        mock_fitz_module.TextWriter = mock_fitz.TextWriter

        _create_annotation(copy_with_booklet, teacher_user, Annotation.Type.VRAI, page_index=0)

        from processing.services.pdf_flattener import PDFFlattener
        flattener = PDFFlattener()
        result = flattener.flatten_copy(copy_with_booklet)
        assert result is not None

    @patch("processing.services.pdf_flattener.fitz")
    @patch("processing.services.pdf_flattener.os.path.exists", return_value=True)
    def test_flattener_handles_faux_annotation(
        self, mock_exists, mock_fitz_module, copy_with_booklet, teacher_user
    ):
        """PDFFlattener does not crash when processing a FAUX annotation."""
        mock_fitz, mock_shape, mock_doc = _build_mock_fitz()
        mock_fitz_module.open = mock_fitz.open
        mock_fitz_module.Rect = mock_fitz.Rect
        mock_fitz_module.Point = mock_fitz.Point
        mock_fitz_module.TextWriter = mock_fitz.TextWriter

        _create_annotation(copy_with_booklet, teacher_user, Annotation.Type.FAUX, page_index=0)

        from processing.services.pdf_flattener import PDFFlattener
        flattener = PDFFlattener()
        result = flattener.flatten_copy(copy_with_booklet)
        assert result is not None

    def test_flattener_stamp_uses_correct_colors(self):
        """VRAI uses green (0, 0.6, 0), FAUX uses red (1, 0, 0)."""
        from processing.services.pdf_flattener import PDFFlattener
        flattener = PDFFlattener()

        vrai_color = flattener._get_annotation_color(Annotation.Type.VRAI)
        faux_color = flattener._get_annotation_color(Annotation.Type.FAUX)

        assert vrai_color == (0, 0.6, 0), f"Expected green for VRAI, got {vrai_color}"
        assert faux_color == (1, 0, 0), f"Expected red for FAUX, got {faux_color}"

    @patch("processing.services.pdf_flattener.fitz")
    @patch("processing.services.pdf_flattener.os.path.exists", return_value=True)
    def test_flattener_mixed_annotation_types(
        self, mock_exists, mock_fitz_module, copy_with_booklet, teacher_user
    ):
        """A page with COMMENT + VRAI + FAUX annotations renders without error."""
        mock_fitz, mock_shape, mock_doc = _build_mock_fitz()
        mock_fitz_module.open = mock_fitz.open
        mock_fitz_module.Rect = mock_fitz.Rect
        mock_fitz_module.Point = mock_fitz.Point
        mock_fitz_module.TextWriter = mock_fitz.TextWriter

        _create_annotation(copy_with_booklet, teacher_user, Annotation.Type.COMMENT, content="Good")
        _create_annotation(copy_with_booklet, teacher_user, Annotation.Type.VRAI, y=0.5)
        _create_annotation(copy_with_booklet, teacher_user, Annotation.Type.FAUX, y=0.7)

        from processing.services.pdf_flattener import PDFFlattener
        flattener = PDFFlattener()
        result = flattener.flatten_copy(copy_with_booklet)
        assert result is not None
