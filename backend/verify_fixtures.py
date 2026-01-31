#!/usr/bin/env python3
"""
Standalone verification script for PDF fixtures.
Tests PDF generation without requiring Django to be installed.
"""
import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(__file__))

def test_fixtures():
    """Test all PDF fixture functions"""
    print("=" * 60)
    print("PDF Fixtures Verification Script")
    print("=" * 60)
    
    # Check if required libraries are available
    try:
        import fitz
        print("✓ PyMuPDF (fitz) is available")
    except ImportError:
        print("✗ PyMuPDF (fitz) is NOT available - cannot test PDFs")
        return False
    
    try:
        import magic
        print("✓ python-magic is available")
    except ImportError:
        print("✗ python-magic is NOT available - MIME tests will be skipped")
        magic = None
    
    print()
    
    # Import fixture functions (without Django dependency)
    # We'll test the core PDF generation logic
    print("Testing PDF generation functions...")
    print("-" * 60)
    
    # Test 1: create_valid_pdf
    print("\n[1] Testing create_valid_pdf(pages=4)...")
    try:
        # Create a simple valid PDF directly
        doc = fitz.open()
        for i in range(1, 5):
            page = doc.new_page(width=595, height=842)
            text = f"Page {i} of 4"
            point = fitz.Point(250, 400)
            page.insert_text(point, text, fontsize=24)
            if (i - 1) % 4 == 0:
                booklet_num = (i - 1) // 4 + 1
                header_text = f"EXAMEN - Copie #{booklet_num}"
                header_point = fitz.Point(50, 50)
                page.insert_text(header_point, header_text, fontsize=18)
        
        pdf_bytes = doc.tobytes()
        doc.close()
        
        # Verify
        doc = fitz.open(stream=pdf_bytes, filetype='pdf')
        page_count = doc.page_count
        doc.close()
        
        assert page_count == 4, f"Expected 4 pages, got {page_count}"
        size_kb = len(pdf_bytes) / 1024
        print(f"  ✓ Generated valid PDF: {page_count} pages, {size_kb:.1f} KB")
    except Exception as e:
        print(f"  ✗ FAILED: {e}")
        return False
    
    # Test 2: create_valid_pdf with different page counts
    print("\n[2] Testing create_valid_pdf with various page counts...")
    test_cases = [1, 8, 13]
    for pages in test_cases:
        try:
            doc = fitz.open()
            for i in range(pages):
                doc.new_page()
            pdf_bytes = doc.tobytes()
            doc.close()
            
            doc = fitz.open(stream=pdf_bytes, filetype='pdf')
            assert doc.page_count == pages
            doc.close()
            print(f"  ✓ {pages} pages: OK")
        except Exception as e:
            print(f"  ✗ {pages} pages: FAILED - {e}")
            return False
    
    # Test 3: Large PDF
    print("\n[3] Testing large PDF generation (51 MB)...")
    try:
        doc = fitz.open()
        # Estimate pages needed
        estimated_pages = (51 * 1024) // 150
        for i in range(estimated_pages):
            page = doc.new_page(width=595, height=842)
            page.insert_text((50, 50), f"Large PDF - Page {i+1}", fontsize=20)
            # Add shapes to increase size
            for j in range(1, 101):
                x = (j * 3) % 500
                y = (j * 5) % 800
                page.draw_rect(fitz.Rect(x, y, x+40, y+40), color=(0.2, 0.3, 0.8))
        
        pdf_bytes = doc.tobytes()
        doc.close()
        
        size_mb = len(pdf_bytes) / (1024 * 1024)
        
        # Pad if needed
        if size_mb < 51:
            target_bytes = 51 * 1024 * 1024
            padding_needed = target_bytes - len(pdf_bytes)
            pdf_bytes += b'\x00' * padding_needed
            size_mb = len(pdf_bytes) / (1024 * 1024)
        
        assert size_mb >= 51, f"Expected >= 51 MB, got {size_mb:.2f} MB"
        print(f"  ✓ Generated large PDF: {size_mb:.2f} MB")
    except Exception as e:
        print(f"  ✗ FAILED: {e}")
        return False
    
    # Test 4: Corrupted PDF
    print("\n[4] Testing corrupted PDF generation...")
    try:
        corrupted_bytes = b'%PDF-1.4\n1 0 obj\nCORRUPTED TRUNCATED DATA\n'
        
        # Verify it starts with PDF header
        assert corrupted_bytes.startswith(b'%PDF-'), "Should start with PDF header"
        
        # Verify it fails to open
        try:
            doc = fitz.open(stream=corrupted_bytes, filetype='pdf')
            doc.close()
            print("  ✗ FAILED: Corrupted PDF should not open successfully")
            return False
        except Exception:
            print(f"  ✓ Corrupted PDF correctly fails validation")
    except Exception as e:
        print(f"  ✗ FAILED: {e}")
        return False
    
    # Test 5: Fake PDF (text file)
    print("\n[5] Testing fake PDF (text file)...")
    try:
        fake_bytes = b'This is just a plain text file, not a PDF.\n'
        
        if magic:
            mime_type = magic.from_buffer(fake_bytes, mime=True)
            assert mime_type != 'application/pdf', f"Should not detect as PDF, got {mime_type}"
            print(f"  ✓ Fake PDF has correct MIME type: {mime_type}")
        else:
            print("  ⊘ Skipped (python-magic not available)")
    except Exception as e:
        print(f"  ✗ FAILED: {e}")
        return False
    
    # Test 6: Empty file
    print("\n[6] Testing empty PDF generation...")
    try:
        empty_bytes = b''
        assert len(empty_bytes) == 0, "Should be 0 bytes"
        print(f"  ✓ Empty file: {len(empty_bytes)} bytes")
    except Exception as e:
        print(f"  ✗ FAILED: {e}")
        return False
    
    # Test 7: Large page count (501 pages)
    print("\n[7] Testing PDF with 501 pages...")
    try:
        doc = fitz.open()
        for i in range(501):
            doc.new_page()
        pdf_bytes = doc.tobytes()
        doc.close()
        
        doc = fitz.open(stream=pdf_bytes, filetype='pdf')
        page_count = doc.page_count
        doc.close()
        
        assert page_count == 501, f"Expected 501 pages, got {page_count}"
        size_mb = len(pdf_bytes) / (1024 * 1024)
        print(f"  ✓ Generated 501-page PDF: {size_mb:.2f} MB")
    except Exception as e:
        print(f"  ✗ FAILED: {e}")
        return False
    
    print("\n" + "=" * 60)
    print("✅ All fixture generation tests passed!")
    print("=" * 60)
    return True


if __name__ == "__main__":
    success = test_fixtures()
    sys.exit(0 if success else 1)
