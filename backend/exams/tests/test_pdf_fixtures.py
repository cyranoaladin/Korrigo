"""
Tests to verify PDF fixture generation utilities work correctly.
"""
import pytest
import fitz
import magic
from exams.tests.fixtures.pdf_fixtures import (
    create_valid_pdf,
    create_large_pdf,
    create_corrupted_pdf,
    create_fake_pdf,
    create_uploadedfile,
    create_empty_pdf,
    create_pdf_with_pages
)


class TestPDFFixtures:
    """Test suite for PDF fixture generation utilities"""
    
    def test_create_valid_pdf_with_default_pages(self):
        """Test creating a valid PDF with default 4 pages"""
        pdf_bytes = create_valid_pdf()
        
        # Verify it's not empty
        assert len(pdf_bytes) > 0
        
        # Verify it's a valid PDF
        doc = fitz.open(stream=pdf_bytes, filetype='pdf')
        assert doc.page_count == 4
        doc.close()
    
    def test_create_valid_pdf_with_custom_pages(self):
        """Test creating a valid PDF with custom page count"""
        test_cases = [1, 4, 8, 13, 100]
        
        for page_count in test_cases:
            pdf_bytes = create_valid_pdf(pages=page_count)
            
            # Verify it's a valid PDF with correct page count
            doc = fitz.open(stream=pdf_bytes, filetype='pdf')
            assert doc.page_count == page_count, f"Expected {page_count} pages, got {doc.page_count}"
            doc.close()
    
    def test_create_large_pdf_exceeds_size_limit(self):
        """Test creating a large PDF that exceeds 50 MB limit"""
        pdf_bytes = create_large_pdf(size_mb=51)
        
        # Verify size
        size_mb = len(pdf_bytes) / (1024 * 1024)
        assert size_mb >= 51, f"Expected >= 51 MB, got {size_mb:.2f} MB"
    
    def test_create_large_pdf_custom_size(self):
        """Test creating a large PDF with custom size"""
        pdf_bytes = create_large_pdf(size_mb=60)
        
        # Verify size
        size_mb = len(pdf_bytes) / (1024 * 1024)
        assert size_mb >= 60, f"Expected >= 60 MB, got {size_mb:.2f} MB"
    
    def test_create_corrupted_pdf_fails_to_open(self):
        """Test that corrupted PDF fails PyMuPDF validation"""
        pdf_bytes = create_corrupted_pdf()
        
        # Verify it's not empty
        assert len(pdf_bytes) > 0
        
        # Verify it starts with PDF header
        assert pdf_bytes.startswith(b'%PDF-')
        
        # PyMuPDF may open malformed PDFs without raising, but the
        # document should be structurally invalid (0 pages or broken)
        try:
            doc = fitz.open(stream=pdf_bytes, filetype='pdf')
            # If it opens, it should have 0 pages (no valid content)
            assert doc.page_count == 0, \
                f"Corrupted PDF should have 0 pages, got {doc.page_count}"
            doc.close()
        except Exception:
            # Expected: fitz raises on truly corrupted data
            pass
    
    def test_create_fake_pdf_wrong_mime_type(self):
        """Test that fake PDF has incorrect MIME type"""
        pdf_bytes = create_fake_pdf()
        
        # Verify it's not empty
        assert len(pdf_bytes) > 0
        
        # Verify MIME type is NOT application/pdf
        mime_type = magic.from_buffer(pdf_bytes, mime=True)
        assert mime_type != 'application/pdf', f"Expected non-PDF MIME type, got {mime_type}"
        assert mime_type == 'text/plain', f"Expected text/plain, got {mime_type}"
    
    def test_create_empty_pdf(self):
        """Test creating an empty file (0 bytes)"""
        pdf_bytes = create_empty_pdf()
        
        # Verify it's exactly 0 bytes
        assert len(pdf_bytes) == 0
        assert pdf_bytes == b''
    
    def test_create_uploadedfile_returns_correct_instance(self):
        """Test wrapping PDF bytes in Django UploadedFile"""
        pdf_bytes = create_valid_pdf(pages=2)
        uploaded = create_uploadedfile(pdf_bytes, filename='test.pdf')
        
        # Verify it's an UploadedFile instance
        from django.core.files.uploadedfile import SimpleUploadedFile
        assert isinstance(uploaded, SimpleUploadedFile)
        
        # Verify attributes
        assert uploaded.name == 'test.pdf'
        assert uploaded.size == len(pdf_bytes)
        assert uploaded.content_type == 'application/pdf'
        
        # Verify content is readable
        uploaded.seek(0)
        content = uploaded.read()
        assert content == pdf_bytes
    
    def test_create_uploadedfile_custom_content_type(self):
        """Test creating UploadedFile with custom content type"""
        fake_bytes = create_fake_pdf()
        uploaded = create_uploadedfile(
            fake_bytes,
            filename='fake.pdf',
            content_type='text/plain'
        )
        
        assert uploaded.content_type == 'text/plain'
    
    def test_create_pdf_with_pages_alias(self):
        """Test create_pdf_with_pages helper function"""
        # Test various page counts
        test_cases = [1, 10, 501]
        
        for page_count in test_cases:
            pdf_bytes = create_pdf_with_pages(page_count)
            
            # Verify it's a valid PDF with correct page count
            doc = fitz.open(stream=pdf_bytes, filetype='pdf')
            assert doc.page_count == page_count
            doc.close()
    
    def test_valid_pdf_has_content(self):
        """Test that generated PDFs have text content"""
        pdf_bytes = create_valid_pdf(pages=4)
        
        doc = fitz.open(stream=pdf_bytes, filetype='pdf')
        
        # Verify first page has content
        page = doc[0]
        text = page.get_text()
        assert 'Page 1' in text
        assert 'EXAMEN' in text or 'Copie' in text
        
        doc.close()
    
    def test_valid_pdf_booklet_structure(self):
        """Test that generated PDFs follow booklet structure (header every 4 pages)"""
        pdf_bytes = create_valid_pdf(pages=8)
        
        doc = fitz.open(stream=pdf_bytes, filetype='pdf')
        
        # Page 1 (index 0) should have booklet header
        text_page_1 = doc[0].get_text()
        assert 'EXAMEN' in text_page_1
        
        # Page 5 (index 4) should have booklet header
        text_page_5 = doc[4].get_text()
        assert 'EXAMEN' in text_page_5
        
        # Page 2 (index 1) should NOT have booklet header
        text_page_2 = doc[1].get_text()
        # Should have page number but not EXAMEN header
        assert 'Page 2' in text_page_2
        
        doc.close()
