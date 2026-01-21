# Skill: PDF Processing Expert

## Quand Activer Ce Skill

Ce skill doit être activé pour :
- Modifications du pipeline PDF (split, merge, export)
- Gestion des annotations vectorielles
- Export PDF avec annotations aplaties
- Optimisation du traitement PDF
- Problèmes de qualité ou performance PDF
- Intégration OCR/Vision
- Canvas/PDF coordination

## Responsabilités

En tant que **PDF Processing Expert**, vous devez :

### 1. Pipeline PDF

- **Concevoir** un pipeline déterministe et traçable
- **Garantir** qu'aucune page/annotation n'est perdue
- **Optimiser** la performance (streaming, async)
- **Gérer** la mémoire pour gros fichiers
- **Tracer** chaque étape du pipeline

### 2. Traitement PDF

- **Split** PDF en pages images avec qualité appropriée (DPI)
- **Merge** booklets en PDF final cohérent
- **Flatten** annotations vectorielles sur PDF
- **Optimiser** taille fichiers sans perte de qualité
- **Valider** intégrité PDF à chaque étape

### 3. Annotations Vectorielles

- **Normaliser** les coordonnées (indépendantes de la résolution)
- **Stocker** annotations de manière structurée (JSON)
- **Appliquer** annotations sur PDF avec précision
- **Garantir** la fidélité visuelle (couleurs, épaisseurs)
- **Éviter** toute perte lors des transformations

### 4. OCR et Vision

- **Extraire** texte des en-têtes (noms élèves)
- **Détecter** zones d'intérêt (headers)
- **Prétraiter** images pour améliorer OCR
- **Gérer** les erreurs OCR (fallbacks)
- **Optimiser** performance OCR

### 5. Performance

- **Streaming** pour gros PDF
- **Traitement asynchrone** (Celery)
- **Caching** si approprié
- **Monitoring** mémoire et temps
- **Optimisation** images (compression, DPI)

## Pipeline PDF Complet

### Étape 1 : Upload et Validation

```python
# Validation
def validate_pdf(pdf_file):
    # Taille
    if pdf_file.size > 50 * 1024 * 1024:  # 50 MB
        raise ValidationError("File too large")

    # Type MIME
    if not pdf_file.content_type == 'application/pdf':
        raise ValidationError("Not a PDF")

    # Intégrité
    try:
        doc = fitz.open(stream=pdf_file.read(), filetype="pdf")
        doc.close()
    except Exception as e:
        raise ValidationError(f"Corrupt PDF: {e}")

    return True
```

### Étape 2 : Split en Pages Images

```python
import fitz
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class PDFSplitter:
    DPI = 150  # Résolution pour OCR

    @classmethod
    def split_to_images(cls, pdf_path, output_dir):
        """
        Split PDF en images PNG haute résolution.
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        images = []
        doc = fitz.open(pdf_path)

        logger.info(f"Splitting {pdf_path}: {doc.page_count} pages")

        for page_num in range(doc.page_count):
            page = doc.load_page(page_num)

            # Conversion haute résolution
            mat = fitz.Matrix(cls.DPI / 72, cls.DPI / 72)
            pix = page.get_pixmap(matrix=mat)

            # Sauvegarder
            image_path = output_dir / f"page_{page_num + 1:04d}.png"
            pix.save(str(image_path))

            images.append(str(image_path))
            logger.debug(f"Page {page_num + 1} → {image_path}")

        doc.close()

        logger.info(f"Split complete: {len(images)} images")
        return images
```

### Étape 3 : Détection Booklets via OCR

```python
import pytesseract
from PIL import Image

class BookletDetector:
    @staticmethod
    def crop_header(image_path, height_percent=0.2):
        """
        Rogne la zone d'en-tête (20% haut de page).
        """
        img = Image.open(image_path)
        width, height = img.size
        crop_height = int(height * height_percent)

        header = img.crop((0, 0, width, crop_height))
        return header

    @staticmethod
    def extract_text_from_header(header_img):
        """
        OCR de l'en-tête.
        """
        # Preprocessing
        gray = header_img.convert('L')
        bw = gray.point(lambda x: 0 if x < 140 else 255)

        # OCR
        text = pytesseract.image_to_string(bw, lang='fra')
        return text.strip()

    @classmethod
    def detect_booklets(cls, pages_images):
        """
        Détecte les fascicules via présence d'en-tête nom.
        """
        booklets = []
        current_start = 0

        for i, img_path in enumerate(pages_images):
            header = cls.crop_header(img_path)
            text = cls.extract_text_from_header(header)

            # Détection basique: si texte contient "Nom" ou "Prénom"
            has_header = any(kw in text.lower() for kw in ['nom', 'prénom', 'name'])

            if has_header and i > 0:
                # Nouveau fascicule détecté
                booklets.append({
                    'start': current_start,
                    'end': i - 1,
                    'pages': pages_images[current_start:i],
                    'header_text': text
                })
                current_start = i

        # Dernier fascicule
        if current_start < len(pages_images):
            booklets.append({
                'start': current_start,
                'end': len(pages_images) - 1,
                'pages': pages_images[current_start:],
                'header_text': ''
            })

        return booklets
```

### Étape 4 : Merge Booklets en PDF

```python
import fitz

class PDFMerger:
    @staticmethod
    def merge_images_to_pdf(images, output_path):
        """
        Crée un PDF à partir d'une liste d'images.
        """
        doc = fitz.open()  # Nouveau PDF

        for img_path in images:
            img_doc = fitz.open(img_path)
            pdf_bytes = img_doc.convert_to_pdf()
            img_pdf = fitz.open("pdf", pdf_bytes)

            doc.insert_pdf(img_pdf)

            img_pdf.close()
            img_doc.close()

        doc.save(output_path, deflate=True)
        doc.close()

        logger.info(f"Merged PDF: {output_path}")
        return output_path
```

### Étape 5 : Annotations Vectorielles

**Format JSON** :
```json
{
  "annotations": [
    {
      "id": "uuid-1",
      "type": "path",
      "tool": "pen",
      "color": "#FF0000",
      "width": 2,
      "points": [
        {"x": 0.1, "y": 0.2},
        {"x": 0.15, "y": 0.25}
      ],
      "timestamp": "2026-01-21T14:30:00Z"
    },
    {
      "id": "uuid-2",
      "type": "text",
      "text": "Bien !",
      "position": {"x": 0.5, "y": 0.3},
      "fontSize": 14,
      "color": "#00FF00",
      "timestamp": "2026-01-21T14:31:00Z"
    }
  ]
}
```

**Normalisation Coordonnées** :
```javascript
// Frontend - Normaliser lors de la capture
function captureAnnotation(event, canvas) {
  const rect = canvas.getBoundingClientRect()
  const x = event.clientX - rect.left
  const y = event.clientY - rect.top

  return {
    x: x / canvas.width,   // Normalisé [0, 1]
    y: y / canvas.height
  }
}
```

### Étape 6 : Export PDF avec Annotations

```python
import fitz

class PDFAnnotationFlattener:
    @staticmethod
    def flatten_annotations(copy, output_path):
        """
        Applique annotations vectorielles sur PDF et génère PDF final.
        """
        doc = fitz.open(copy.final_pdf.path)

        # Récupérer annotations par page
        annotations = copy.annotations.all().order_by('page_number')

        for annotation_obj in annotations:
            page_num = annotation_obj.page_number - 1
            page = doc[page_num]
            page_rect = page.rect

            # Appliquer chaque annotation
            for annot in annotation_obj.vector_data.get('annotations', []):
                PDFAnnotationFlattener.apply_annotation(page, annot, page_rect)

        # Sauvegarder
        doc.save(output_path, deflate=True, garbage=4)
        doc.close()

        logger.info(f"Flattened PDF: {output_path}")
        return output_path

    @staticmethod
    def apply_annotation(page, annot, page_rect):
        """
        Applique une annotation sur une page.
        """
        annot_type = annot.get('type')

        if annot_type == 'path':
            PDFAnnotationFlattener.draw_path(page, annot, page_rect)
        elif annot_type == 'text':
            PDFAnnotationFlattener.draw_text(page, annot, page_rect)
        elif annot_type == 'highlight':
            PDFAnnotationFlattener.draw_highlight(page, annot, page_rect)

    @staticmethod
    def draw_path(page, annot, page_rect):
        """
        Dessine un trait.
        """
        points = annot.get('points', [])
        color = hex_to_rgb(annot.get('color', '#FF0000'))
        width = annot.get('width', 2)

        # Dénormaliser coordonnées
        pdf_points = [
            (p['x'] * page_rect.width, p['y'] * page_rect.height)
            for p in points
        ]

        if len(pdf_points) > 1:
            shape = page.new_shape()
            shape.draw_polyline(pdf_points)
            shape.finish(color=color, width=width)
            shape.commit()

    @staticmethod
    def draw_text(page, annot, page_rect):
        """
        Ajoute un texte.
        """
        text = annot.get('text', '')
        pos = annot.get('position', {'x': 0, 'y': 0})
        font_size = annot.get('fontSize', 12)
        color = hex_to_rgb(annot.get('color', '#000000'))

        # Dénormaliser position
        x = pos['x'] * page_rect.width
        y = pos['y'] * page_rect.height

        # Insérer texte
        page.insert_text(
            (x, y),
            text,
            fontsize=font_size,
            color=color
        )

def hex_to_rgb(hex_color):
    """
    Convertit hex (#FF0000) en RGB normalisé (1.0, 0.0, 0.0).
    """
    hex_color = hex_color.lstrip('#')
    r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    return (r / 255, g / 255, b / 255)
```

## Gestion Mémoire

### Streaming pour Gros PDF

```python
def process_large_pdf_streaming(pdf_path):
    """
    Traite un gros PDF page par page sans tout charger en mémoire.
    """
    doc = fitz.open(pdf_path)

    for page_num in range(doc.page_count):
        # Charger une seule page
        page = doc.load_page(page_num)

        # Traiter
        process_page(page)

        # Libérer
        page = None

    doc.close()
```

### Celery pour Async

```python
from celery import shared_task

@shared_task(bind=True, max_retries=3)
def process_exam_pdf(self, exam_id):
    """
    Traitement asynchrone d'un PDF d'examen.
    """
    try:
        exam = Exam.objects.get(id=exam_id)

        # Split
        pages = PDFSplitter.split_to_images(exam.pdf_source.path, output_dir)

        # Détection booklets
        booklets_data = BookletDetector.detect_booklets(pages)

        # Créer Booklets en DB
        for data in booklets_data:
            Booklet.objects.create(
                exam=exam,
                start_page=data['start'],
                end_page=data['end'],
                pages_images=data['pages'],
                student_name_guess=data['header_text']
            )

        exam.is_processed = True
        exam.save()

        return {'success': True, 'booklets': len(booklets_data)}

    except Exception as exc:
        logger.error(f"Error processing exam {exam_id}: {exc}")
        raise self.retry(exc=exc, countdown=60)
```

## Checklist Pipeline PDF

Avant toute modification du pipeline :
- [ ] Déterminisme garanti (même input → même output)
- [ ] Pas de perte de pages
- [ ] Pas de perte d'annotations
- [ ] Coordonnées normalisées
- [ ] PDF final assigné à Copy
- [ ] Logging complet
- [ ] Gestion d'erreurs robuste
- [ ] Mémoire gérée (streaming)
- [ ] Tests passent

## Tests PDF

### Test Split

```python
def test_split_pdf_correct_page_count():
    # PDF de test avec 4 pages
    pdf_path = "test_data/exam_4pages.pdf"

    images = PDFSplitter.split_to_images(pdf_path, "/tmp/test_split")

    assert len(images) == 4
    for img in images:
        assert Path(img).exists()
```

### Test Merge

```python
def test_merge_images_to_pdf():
    images = ["page1.png", "page2.png", "page3.png"]

    pdf_path = PDFMerger.merge_images_to_pdf(images, "/tmp/merged.pdf")

    doc = fitz.open(pdf_path)
    assert doc.page_count == 3
    doc.close()
```

### Test Annotations

```python
def test_flatten_annotations_preserves_all():
    copy = create_test_copy_with_annotations(count=5)

    output = PDFAnnotationFlattener.flatten_annotations(copy, "/tmp/flat.pdf")

    assert Path(output).exists()
    # Vérification visuelle ou image comparison
```

## Optimisations

### Compression Images

```python
from PIL import Image

def optimize_image(image_path, quality=85):
    img = Image.open(image_path)
    img.save(image_path, optimize=True, quality=quality)
```

### DPI Adaptatif

```python
# DPI selon usage
DPI_OCR = 150      # OCR minimum
DPI_DISPLAY = 100  # Affichage écran
DPI_PRINT = 300    # Impression haute qualité
```

## Références

- PyMuPDF (fitz) : https://pymupdf.readthedocs.io/
- Tesseract OCR : https://github.com/tesseract-ocr/tesseract
- PIL/Pillow : https://pillow.readthedocs.io/
- PDF Specification : https://www.adobe.com/devnet/pdf/pdf_reference.html

---

**Activation** : Automatique pour code PDF/annotations
**Priorité** : CRITIQUE (perte de données inacceptable)
**Version** : 1.0
