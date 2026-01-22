
import fitz
import os
import random

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "pdfs")
os.makedirs(OUTPUT_DIR, exist_ok=True)

def create_scan_like_10p(filename):
    doc = fitz.open()
    for i in range(10):
        # Rotate page slightly to simulate scan skew
        # PyMuPDF page.set_rotation is in 90 deg increments usually, 
        # but we can set a rotation matrix on content or keep it simple.
        # Actually proper scan skew is hard to fake in PDF structure without raster image.
        # We will use simple rotation attribute if possible or just noise.
        # For valid PDF, rotation is usually 0, 90, 180, 270.
        # So we will focus on "Noise" content.
        page = doc.new_page()
        
        # Add random "dirt"
        for _ in range(50):
            x, y = random.randint(0, 595), random.randint(0, 842)
            page.draw_circle((x, y), random.uniform(0.5, 2), color=(0.2, 0.2, 0.2), fill=(0.2, 0.2, 0.2))
            
        page.insert_text((50, 50), f"Scan-Like Page {i+1}", fontsize=20, color=(0.1, 0.1, 0.1))
        
        # Skewed content simulation (using morph)
        # Not strictly necessary if we just check processing. 
    
    path = os.path.join(OUTPUT_DIR, filename)
    doc.save(path)
    doc.close()
    print(f"Created {path}")

def create_multi_booklet_20p(filename):
    # Just 20 pages
    doc = fitz.open()
    for i in range(20):
        page = doc.new_page()
        page.insert_text((50, 50), f"Page {i+1} of 20", fontsize=20)
        # Add unique marker for booklet splitting verification if needed
        page.insert_text((50, 500), f"Marker {i}", fontsize=10)
        
    path = os.path.join(OUTPUT_DIR, filename)
    doc.save(path)
    doc.close()
    print(f"Created {path}")

def create_heavy_60p(filename):
    doc = fitz.open()
    for i in range(60):
        page = doc.new_page()
        page.insert_text((50, 50), f"Heavy Page {i+1}", fontsize=20)
        # Moderate complexity per page, but high volume
        for j in range(50):
            page.draw_rect(fitz.Rect(j*10, j*5, j*10+50, j*5+50), color=(0, 0, 1))
            
    path = os.path.join(OUTPUT_DIR, filename)
    doc.save(path)
    doc.close()
    print(f"Created {path}")

def create_weird_metadata_pdf(filename):
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 50), "Weird Metadata", fontsize=20)
    
    # Set weird metadata
    doc.set_metadata({
        "title": "Weird \x00 Title",
        "author": "Ghost 👻",
        "keywords": "test, chaos, " * 100
    })
    
    path = os.path.join(OUTPUT_DIR, filename)
    doc.save(path)
    doc.close()
    print(f"Created {path}")

def create_mixed_orientation_pdf(filename):
    doc = fitz.open()
    for i in range(4):
        # Alternate orientation
        if i % 2 == 0:
            page = doc.new_page(width=595, height=842) # A4 Portrait
            page.insert_text((50, 50), f"Portrait {i+1}", fontsize=20)
        else:
             page = doc.new_page(width=842, height=595) # A4 Landscape
             page.insert_text((50, 50), f"Landscape {i+1}", fontsize=20)
             
    path = os.path.join(OUTPUT_DIR, filename)
    doc.save(path)
    doc.close()
    print(f"Created {path}")

def create_corrupted_truncated(filename):
    # Valid header, valid partial obj, cut off.
    path = os.path.join(OUTPUT_DIR, filename)
    
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 50), "Content to be cut", fontsize=20)
    temp_path = path + ".tmp"
    doc.save(temp_path)
    doc.close()
    
    # Read and truncate
    with open(temp_path, "rb") as f:
        data = f.read()
    
    # Keep 50%
    truncated = data[:len(data)//2]
    
    with open(path, "wb") as f:
        f.write(truncated)
        
    os.remove(temp_path)
    print(f"Created {path}")

if __name__ == "__main__":
    create_scan_like_10p("scan_like_10p.pdf")
    create_multi_booklet_20p("multi_booklets_20p.pdf")
    create_heavy_60p("heavy_60p.pdf")
    create_weird_metadata_pdf("weird_metadata.pdf")
    create_mixed_orientation_pdf("mixed_orientation.pdf")
    create_corrupted_truncated("corrupted_truncated.pdf")
