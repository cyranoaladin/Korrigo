"""
PDF Fixture Generators for Upload Tests

Provides programmatic PDF generation utilities to avoid storing binary
fixtures in version control.
"""
import fitz  # PyMuPDF
from django.core.files.uploadedfile import SimpleUploadedFile
from io import BytesIO


def create_valid_pdf(pages=4, page_width=595, page_height=842):
    """
    Create a valid PDF with specified number of pages.
    
    Args:
        pages (int): Number of pages to create
        page_width (int): Page width in points (default: A4 width = 595)
        page_height (int): Page height in points (default: A4 height = 842)
    
    Returns:
        bytes: Valid PDF file as bytes
    
    Example:
        >>> pdf_bytes = create_valid_pdf(pages=4)
        >>> len(pdf_bytes) > 0
        True
    """
    doc = fitz.open()
    
    for i in range(pages):
        page = doc.new_page(width=page_width, height=page_height)
        # Add booklet header every 4 pages (simulates exam booklet structure)
        if i % 4 == 0:
            page.insert_text((50, 30), "EXAMEN - Copie d'examen", fontsize=14)
        # Add some text to make pages distinguishable
        text = f"Page {i + 1} of {pages}"
        page.insert_text((50, 50), text, fontsize=12)
    
    # Save to bytes
    pdf_bytes = doc.tobytes()
    doc.close()
    
    return pdf_bytes


def create_large_pdf(size_mb=51, min_pages=10):
    """
    Create a PDF larger than the specified size.
    
    Args:
        size_mb (int): Target size in megabytes (default: 51 MB)
        min_pages (int): Minimum number of pages to create
    
    Returns:
        bytes: Large PDF file as bytes
    
    Note:
        Uses random binary data embedded as a PDF stream object to reach
        target size quickly (~1s) instead of generating thousands of pages.
    """
    import os
    
    # Create a small valid PDF with min_pages
    doc = fitz.open()
    for i in range(min_pages):
        page = doc.new_page(width=595, height=842)
        page.insert_text((50, 50), f"Page {i + 1}", fontsize=12)
    base_pdf = doc.tobytes()
    doc.close()
    
    target_bytes = size_mb * 1024 * 1024
    if len(base_pdf) >= target_bytes:
        return base_pdf
    
    # Pad with random bytes wrapped in a valid PDF stream object.
    # We insert a dummy stream before %%EOF so the file size exceeds the limit.
    # The PDF header remains valid for size-based validators.
    padding_size = target_bytes - len(base_pdf) + 1024  # +1KB margin
    random_data = os.urandom(padding_size)
    
    # Build a raw PDF object with the random data as a stream
    # This keeps the file recognizable as PDF while being large
    padding_obj = (
        b"\n999 0 obj\n<< /Length " + str(padding_size).encode() +
        b" >>\nstream\n" + random_data + b"\nendstream\nendobj\n"
    )
    
    # Insert padding before the final %%EOF marker
    eof_marker = b"%%EOF"
    eof_pos = base_pdf.rfind(eof_marker)
    if eof_pos == -1:
        # Fallback: just append
        return base_pdf + padding_obj
    
    return base_pdf[:eof_pos] + padding_obj + base_pdf[eof_pos:]


def create_corrupted_pdf():
    """
    Create a corrupted PDF that fails integrity validation.
    
    Returns:
        bytes: Corrupted PDF bytes that will fail PyMuPDF parsing
    
    Note:
        Starts with PDF header but contains invalid structure.
    """
    # Start with PDF header but add garbage data
    corrupted = b'%PDF-1.4\n'
    corrupted += b'1 0 obj\n'
    corrupted += b'CORRUPTED_GARBAGE_DATA_INVALID_STRUCTURE\n'
    corrupted += b'endobj\n'
    corrupted += b'%%EOF\n'
    
    return corrupted


def create_fake_pdf():
    """
    Create a text file that pretends to be a PDF (for MIME type tests).
    
    Returns:
        bytes: Plain text content (not a real PDF)
    
    Note:
        Used to test MIME type validation - file will have .pdf extension
        but actual content is plain text.
    """
    fake_content = b"This is just a plain text file, not a PDF.\n"
    fake_content += b"It should fail MIME type validation.\n"
    fake_content += b"Even though it might have a .pdf extension.\n"
    
    return fake_content


def create_empty_pdf():
    """
    Create a 0-byte empty file.
    
    Returns:
        bytes: Empty bytes
    """
    return b''


def create_pdf_with_pages(page_count):
    """
    Create a PDF with exact page count (for testing page limits).
    
    Args:
        page_count (int): Exact number of pages to create
    
    Returns:
        bytes: PDF with specified page count
    
    Example:
        >>> pdf = create_pdf_with_pages(501)  # For testing max page limit
    """
    return create_valid_pdf(pages=page_count)


def create_uploadedfile(pdf_bytes, filename="test.pdf", content_type="application/pdf"):
    """
    Wrap PDF bytes in Django SimpleUploadedFile for testing.
    
    Args:
        pdf_bytes (bytes): PDF content as bytes
        filename (str): Filename for the uploaded file
        content_type (str): MIME type (default: application/pdf)
    
    Returns:
        SimpleUploadedFile: Django UploadedFile instance ready for testing
    
    Example:
        >>> pdf_bytes = create_valid_pdf(pages=4)
        >>> upload = create_uploadedfile(pdf_bytes, "exam.pdf")
        >>> upload.name
        'exam.pdf'
    """
    return SimpleUploadedFile(
        name=filename,
        content=pdf_bytes,
        content_type=content_type
    )


def get_valid_pdf_file(pages=4, filename="test.pdf"):
    """
    Create a valid PDF file ready for upload testing.
    
    Args:
        pages (int): Number of pages to create (default: 4)
        filename (str): Filename for the uploaded file (default: "test.pdf")
    
    Returns:
        SimpleUploadedFile: Django UploadedFile instance with valid PDF
    
    Example:
        >>> pdf_file = get_valid_pdf_file(pages=4, filename="exam.pdf")
        >>> pdf_file.name
        'exam.pdf'
    """
    pdf_bytes = create_valid_pdf(pages=pages)
    return create_uploadedfile(pdf_bytes, filename=filename)


# Convenience fixtures for common test cases
def fixture_valid_small():
    """Valid 4-page PDF (small)"""
    pdf_bytes = create_valid_pdf(pages=4)
    return create_uploadedfile(pdf_bytes, "valid_small.pdf")


def fixture_valid_large():
    """Valid 100-page PDF (large but within limits)"""
    pdf_bytes = create_valid_pdf(pages=100)
    return create_uploadedfile(pdf_bytes, "valid_large.pdf")


def fixture_valid_remainder():
    """Valid 13-page PDF (not divisible by 4 - tests remainder handling)"""
    pdf_bytes = create_valid_pdf(pages=13)
    return create_uploadedfile(pdf_bytes, "valid_remainder.pdf")


def fixture_invalid_empty():
    """Empty 0-byte file"""
    return create_uploadedfile(create_empty_pdf(), "empty.pdf")


def fixture_invalid_fake():
    """Text file with .pdf extension (MIME type test)"""
    return create_uploadedfile(
        create_fake_pdf(),
        "fake.pdf",
        content_type="application/pdf"  # Lie about content type
    )


def fixture_invalid_corrupted():
    """Corrupted PDF file"""
    return create_uploadedfile(create_corrupted_pdf(), "corrupted.pdf")


def fixture_invalid_too_large():
    """PDF file > 50 MB"""
    pdf_bytes = create_large_pdf(size_mb=51)
    return create_uploadedfile(pdf_bytes, "too_large.pdf")


def fixture_invalid_too_many_pages():
    """PDF with > 500 pages"""
    pdf_bytes = create_pdf_with_pages(501)
    return create_uploadedfile(pdf_bytes, "too_many_pages.pdf")


# Test the fixtures themselves
if __name__ == "__main__":
    print("Testing PDF fixture generators...")
    
    # Test valid PDF
    print("\n1. Valid PDF (4 pages):")
    valid_pdf = create_valid_pdf(pages=4)
    print(f"   Size: {len(valid_pdf)} bytes")
    try:
        doc = fitz.open(stream=valid_pdf, filetype="pdf")
        print(f"   Pages: {doc.page_count}")
        doc.close()
        print("   ✓ Valid PDF structure")
    except Exception as e:
        print(f"   ✗ Error: {e}")
    
    # Test large PDF
    print("\n2. Large PDF (> 50 MB):")
    large_pdf = create_large_pdf(size_mb=51)
    size_mb = len(large_pdf) / (1024 * 1024)
    print(f"   Size: {size_mb:.2f} MB")
    print(f"   ✓ Size > 50 MB: {size_mb > 50}")
    
    # Test corrupted PDF
    print("\n3. Corrupted PDF:")
    corrupted = create_corrupted_pdf()
    print(f"   Size: {len(corrupted)} bytes")
    try:
        doc = fitz.open(stream=corrupted, filetype="pdf")
        doc.close()
        print("   ✗ Should have failed but didn't")
    except Exception as e:
        print(f"   ✓ Correctly fails: {type(e).__name__}")
    
    # Test fake PDF
    print("\n4. Fake PDF (text file):")
    fake = create_fake_pdf()
    print(f"   Size: {len(fake)} bytes")
    print(f"   Content starts with: {fake[:50]}")
    print("   ✓ Not a real PDF")
    
    # Test empty
    print("\n5. Empty file:")
    empty = create_empty_pdf()
    print(f"   Size: {len(empty)} bytes")
    print(f"   ✓ Empty: {len(empty) == 0}")
    
    print("\n✓ All fixture generators tested successfully!")
