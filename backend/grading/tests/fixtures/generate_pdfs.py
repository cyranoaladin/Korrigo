
import fitz
import os

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "pdfs")
os.makedirs(OUTPUT_DIR, exist_ok=True)

def create_simple_pdf(filename, pages=2):
    doc = fitz.open()
    for i in range(pages):
        page = doc.new_page()
        page.insert_text((50, 50), f"Page {i+1} of {pages}", fontsize=20)
        page.insert_text((50, 100), "Simple Content", fontsize=12)
    
    path = os.path.join(OUTPUT_DIR, filename)
    doc.save(path)
    doc.close()
    print(f"Created {path}")

def create_heavy_pdf(filename, pages=12):
    doc = fitz.open()
    for i in range(pages):
        page = doc.new_page()
        page.insert_text((50, 50), f"Heavy Page {i+1}", fontsize=20)
        # Draw many shapes to increase complexity
        for j in range(1, 101):
            page.draw_rect(fitz.Rect(j*5, j*5, j*5+50, j*5+50), color=(0, 0, 1))
            page.draw_circle((300, 300), j*2, color=(1, 0, 0))
    
    path = os.path.join(OUTPUT_DIR, filename)
    doc.save(path)
    doc.close()
    print(f"Created {path}")

def create_scanned_like_pdf(filename, pages=2):
    doc = fitz.open()
    for i in range(pages):
        page = doc.new_page()
        # Simulate rotation/skew effectively by drawing text then rotating page? 
        # For now, just simulated text and noise.
        page.insert_text((100, 100), f"Scanned Page {i+1}", fontsize=20) 
        for k in range(10):
             page.draw_line((0, k*50), (595, k*60), color=(0.5, 0.5, 0.5)) # Noise lines
    
    path = os.path.join(OUTPUT_DIR, filename)
    doc.save(path)
    doc.close()
    print(f"Created {path}")

def create_corrupted_pdf(filename):
    path = os.path.join(OUTPUT_DIR, filename)
    with open(path, "wb") as f:
        f.write(b"%PDF-1.4\nTRUNCATED CONTENT...")
    print(f"Created {path}")

if __name__ == "__main__":
    create_simple_pdf("copy_2p_simple.pdf", 2)
    create_simple_pdf("copy_6p_multibooklet.pdf", 6)
    create_heavy_pdf("copy_12p_heavy.pdf", 12)
    create_scanned_like_pdf("copy_scanned_like.pdf", 2)
    create_corrupted_pdf("copy_corrupted.pdf")
