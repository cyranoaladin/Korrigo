#!/usr/bin/env python
"""
Crée un PDF de test avec 8 pages (2 booklets de 4 pages chacun).
"""
import fitz  # PyMuPDF

def create_test_pdf(filename="test_exam.pdf", num_pages=8):
    """Crée un PDF avec num_pages pages."""
    doc = fitz.open()

    for i in range(1, num_pages + 1):
        page = doc.new_page(width=595, height=842)  # A4

        # Ajouter du texte
        text = f"Page {i}"
        point = fitz.Point(250, 400)
        page.insert_text(point, text, fontsize=48)

        # Si c'est une première page de booklet (1, 5, 9, etc.), ajouter un header
        if (i - 1) % 4 == 0:
            header_text = f"EXAMEN - Copie #{(i-1)//4 + 1}"
            header_point = fitz.Point(50, 50)
            page.insert_text(header_point, header_text, fontsize=24)

    doc.save(filename)
    doc.close()
    print(f"PDF créé : {filename} ({num_pages} pages)")

if __name__ == "__main__":
    create_test_pdf()
