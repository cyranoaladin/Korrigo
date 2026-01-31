"""
PDF Fixture Generation Utilities for Testing
Conformité: .antigravity/rules/01_security_rules.md § 8.1
"""
import io
import fitz  # PyMuPDF
from django.core.files.uploadedfile import SimpleUploadedFile


def create_valid_pdf(pages=4):
    """
    Create a valid PDF with N pages.
    
    Args:
        pages: Number of pages to create (default: 4)
        
    Returns:
        bytes: PDF file content as bytes
        
    Example:
        >>> pdf_bytes = create_valid_pdf(pages=8)
        >>> pdf_file = create_uploadedfile(pdf_bytes, "test.pdf")
    """
    doc = fitz.open()
    
    for i in range(1, pages + 1):
        page = doc.new_page(width=595, height=842)  # A4 size
        
        # Add page number
        text = f"Page {i} of {pages}"
        point = fitz.Point(250, 400)
        page.insert_text(point, text, fontsize=24)
        
        # Add header for first page of each booklet (every 4 pages)
        if (i - 1) % 4 == 0:
            booklet_num = (i - 1) // 4 + 1
            header_text = f"EXAMEN - Copie #{booklet_num}"
            header_point = fitz.Point(50, 50)
            page.insert_text(header_point, header_text, fontsize=18)
    
    # Convert to bytes
    pdf_bytes = doc.tobytes()
    doc.close()
    
    return pdf_bytes


def create_large_pdf(size_mb=51):
    """
    Create a PDF larger than the specified size in MB.
    
    Args:
        size_mb: Minimum size in megabytes (default: 51)
        
    Returns:
        bytes: Large PDF file content as bytes
        
    Note:
        Creates a PDF with enough pages and content to exceed the size limit.
        The actual size may be slightly larger than requested due to PDF overhead.
    """
    doc = fitz.open()
    target_bytes = size_mb * 1024 * 1024
    
    # Estimate: each complex page is roughly 100-200 KB
    # We need at least size_mb * 1024 / 200 pages
    estimated_pages = (size_mb * 1024) // 150
    
    for i in range(estimated_pages):
        page = doc.new_page(width=595, height=842)
        
        # Add text to make the page larger
        page.insert_text((50, 50), f"Large PDF - Page {i+1}", fontsize=20)
        
        # Draw many shapes to increase file size
        for j in range(1, 101):
            x = (j * 3) % 500
            y = (j * 5) % 800
            page.draw_rect(fitz.Rect(x, y, x+40, y+40), color=(0.2, 0.3, 0.8))
            page.draw_circle((x+20, y+20), 15, color=(0.8, 0.2, 0.3))
    
    pdf_bytes = doc.tobytes()
    doc.close()
    
    # Verify size
    actual_size_mb = len(pdf_bytes) / (1024 * 1024)
    if actual_size_mb < size_mb:
        # Pad with extra data if needed (append zeros at end)
        padding_needed = target_bytes - len(pdf_bytes)
        pdf_bytes += b'\x00' * padding_needed
    
    return pdf_bytes


def create_corrupted_pdf():
    """
    Create a corrupted PDF that fails integrity validation.
    
    Returns:
        bytes: Invalid PDF file content
        
    Note:
        Creates a file that starts with PDF header but has invalid structure.
        Will fail when opened with PyMuPDF.
    """
    # PDF header followed by garbage data
    corrupted_content = b'%PDF-1.4\n'
    corrupted_content += b'1 0 obj\n'
    corrupted_content += b'CORRUPTED TRUNCATED DATA WITHOUT PROPER STRUCTURE\n'
    corrupted_content += b'Random garbage: \x00\xFF\xAA\xBB\xCC\xDD\n'
    
    return corrupted_content


def create_fake_pdf():
    """
    Create a text file pretending to be a PDF (for MIME type testing).
    
    Returns:
        bytes: Text file content (not a real PDF)
        
    Note:
        This will fail MIME type detection as it's not actually a PDF,
        even though it might have a .pdf extension.
    """
    fake_content = b'This is just a plain text file, not a PDF.\n'
    fake_content += b'It should fail MIME type validation.\n'
    fake_content += b'MIME type will be detected as text/plain, not application/pdf.\n'
    
    return fake_content


def create_uploadedfile(pdf_bytes, filename="test.pdf", content_type="application/pdf"):
    """
    Wrap PDF bytes in Django SimpleUploadedFile for testing.
    
    Args:
        pdf_bytes: PDF content as bytes
        filename: Filename for the uploaded file (default: "test.pdf")
        content_type: MIME type (default: "application/pdf")
        
    Returns:
        SimpleUploadedFile: Django uploaded file instance ready for testing
        
    Example:
        >>> pdf_bytes = create_valid_pdf(pages=4)
        >>> uploaded_file = create_uploadedfile(pdf_bytes, "exam.pdf")
        >>> # Use in tests with serializers or validators
    """
    return SimpleUploadedFile(
        name=filename,
        content=pdf_bytes,
        content_type=content_type
    )


def create_empty_pdf():
    """
    Create an empty file (0 bytes) for testing empty file validation.
    
    Returns:
        bytes: Empty bytes object
    """
    return b''


def create_pdf_with_pages(page_count):
    """
    Create a PDF with exactly the specified number of pages.
    Useful for testing page count limits.
    
    Args:
        page_count: Exact number of pages to create
        
    Returns:
        bytes: PDF file content with specified page count
        
    Example:
        >>> # Test too many pages scenario
        >>> pdf_501_pages = create_pdf_with_pages(501)
    """
    return create_valid_pdf(pages=page_count)
