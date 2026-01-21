# Règles Traitement PDF et Annotations - Viatique

## Statut : CRITIQUE

Ces règles garantissent l'intégrité du pipeline PDF et des annotations. Toute violation peut entraîner une perte de données.

---

## 1. Pipeline PDF Global

### 1.1 Workflow Complet

**Étapes Obligatoires** :
```
1. Upload PDF Source (Exam)
   ↓
2. Split PDF en Pages Images
   ↓
3. Détection Fascicules (Booklets) via OCR/Vision
   ↓
4. Validation Manuelle (Staging Area)
   ↓
5. Création Copies Finales (Merge Booklets si nécessaire)
   ↓
6. Correction avec Annotations Vectorielles
   ↓
7. Export PDF Final avec Annotations Aplaties
   ↓
8. Publication aux Élèves
```

**INTERDIT** :
- Court-circuiter des étapes
- Créer une Copy sans PDF final valide
- Perdre des annotations entre étapes
- Produire un PDF final sans traçabilité

### 1.2 Déterminisme

**OBLIGATOIRE** :
- Même input → même output (reproductibilité)
- Logs détaillés à chaque étape
- Traçabilité complète (timestamps, user, actions)
- Checksum/hash pour validation d'intégrité

---

## 2. Traitement PDF Source

### 2.1 Upload et Validation

**OBLIGATOIRE** :
```python
from django.core.validators import FileExtensionValidator
from django.core.exceptions import ValidationError

def validate_pdf_size(file):
    """
    Limite de taille: 50 MB pour éviter saturation mémoire.
    """
    max_size = 50 * 1024 * 1024  # 50 MB
    if file.size > max_size:
        raise ValidationError(f"File too large. Max size: {max_size / 1024 / 1024} MB")

class Exam(models.Model):
    pdf_source = models.FileField(
        upload_to='exams/source/',
        validators=[
            FileExtensionValidator(allowed_extensions=['pdf']),
            validate_pdf_size
        ]
    )
```

**Règles** :
- Extension .pdf uniquement
- Taille maximale 50 MB (configurable)
- MIME type validation
- Scan antivirus si possible (production)

### 2.2 Split PDF en Pages

**OBLIGATOIRE** :
```python
# processing/services/splitter.py
import fitz  # PyMuPDF
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class PDFSplitter:
    @staticmethod
    def split_to_images(pdf_path, output_dir, dpi=150):
        """
        Split PDF en images haute résolution.

        Args:
            pdf_path: Chemin vers PDF source
            output_dir: Répertoire de sortie
            dpi: Résolution (150 minimum pour OCR)

        Returns:
            List[Path]: Chemins des images générées
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        images = []
        try:
            doc = fitz.open(pdf_path)
            logger.info(f"Splitting PDF: {pdf_path} ({doc.page_count} pages)")

            for page_num in range(doc.page_count):
                page = doc[page_num]

                # Conversion en image haute résolution
                mat = fitz.Matrix(dpi / 72, dpi / 72)  # 72 DPI par défaut
                pix = page.get_pixmap(matrix=mat)

                # Sauvegarde
                image_path = output_dir / f"page_{page_num + 1:04d}.png"
                pix.save(str(image_path))

                images.append(image_path)
                logger.debug(f"Page {page_num + 1} saved: {image_path}")

            doc.close()
            logger.info(f"Split complete: {len(images)} images")
            return images

        except Exception as e:
            logger.error(f"Error splitting PDF {pdf_path}: {e}")
            raise
```

**Règles** :
- DPI minimum 150 (OCR lisible)
- Format PNG pour qualité
- Nommage séquentiel (`page_0001.png`, `page_0002.png`, ...)
- Logging de chaque page
- Gestion d'erreurs robuste

**INTERDIT** :
- DPI trop bas (<100) → OCR inefficace
- JPEG avec compression → perte de qualité
- Pas de logging → impossible de debug
- Charger tout le PDF en mémoire → OOM sur gros fichiers

---

## 3. Détection de Fascicules (Booklets)

### 3.1 Détection Automatique

**OBLIGATOIRE** :
```python
# processing/services/booklet_detector.py
class BookletDetector:
    @staticmethod
    def detect_booklets(exam, pages_images):
        """
        Détecte les fascicules via en-têtes.

        Logique:
        - Page avec en-tête nom/prénom = début de fascicule
        - Pages suivantes jusqu'au prochain en-tête = même fascicule
        - Nombre de pages attendu: configurable (ex: 4 pages par fascicule)
        """
        booklets = []
        current_start = 0

        for i, image_path in enumerate(pages_images):
            # OCR de la zone en-tête
            header_crop = crop_header_region(image_path)
            has_header = detect_name_field(header_crop)  # OCR/Vision

            if has_header and i > 0:
                # Créer booklet pour pages précédentes
                booklet = create_booklet(
                    exam=exam,
                    start_page=current_start,
                    end_page=i - 1,
                    pages_images=pages_images[current_start:i]
                )
                booklets.append(booklet)
                current_start = i

        # Dernier fascicule
        if current_start < len(pages_images):
            booklet = create_booklet(
                exam=exam,
                start_page=current_start,
                end_page=len(pages_images) - 1,
                pages_images=pages_images[current_start:]
            )
            booklets.append(booklet)

        return booklets
```

**Règles** :
- Détection basée sur en-têtes (nom/prénom)
- OCR de la zone en-tête uniquement (pas toute la page)
- Fallback : nombre de pages fixe (ex: 4)
- Création de Booklet en staging (status implicite)

### 3.2 OCR En-tête

**OBLIGATOIRE** :
```python
import pytesseract
from PIL import Image

def extract_student_name_guess(header_image_path):
    """
    OCR de l'en-tête pour deviner le nom.
    """
    try:
        img = Image.open(header_image_path)

        # Preprocessing pour améliorer OCR
        img = img.convert('L')  # Grayscale
        img = img.point(lambda x: 0 if x < 140 else 255)  # Binarization

        # OCR
        text = pytesseract.image_to_string(img, lang='fra')
        text = text.strip()

        logger.info(f"OCR result: {text[:50]}")
        return text

    except Exception as e:
        logger.error(f"OCR failed for {header_image_path}: {e}")
        return ""
```

**Règles** :
- Preprocessing image (grayscale, binarization)
- Langue française (`lang='fra'`)
- Gestion d'erreurs (OCR peut échouer)
- Résultat stocké en `student_name_guess` (indicatif, pas fiable à 100%)

---

## 4. Création de Copies

### 4.1 Validation Manuelle

**OBLIGATOIRE** :
- Interface de validation (Staging Area)
- Visualisation des booklets détectés
- Ajustement manuel possible (fusion, séparation)
- Validation explicite par utilisateur

**Workflow** :
```
1. Afficher tous les Booklets détectés
2. Utilisateur valide ou ajuste
3. Utilisateur crée des Copies en groupant Booklets
4. Génération PDF final pour chaque Copy
5. Statut Copy → READY
```

### 4.2 Génération PDF Final

**OBLIGATOIRE** :
```python
# processing/services/pdf_merger.py
import fitz

class PDFMerger:
    @staticmethod
    def merge_booklets_to_pdf(booklets, output_path):
        """
        Merge plusieurs booklets en un PDF final.

        Args:
            booklets: List[Booklet]
            output_path: Chemin du PDF de sortie

        Returns:
            Path: Chemin du PDF créé
        """
        try:
            output_doc = fitz.open()  # Nouveau PDF vide

            for booklet in booklets:
                # Récupérer pages images
                pages_images = booklet.pages_images  # JSON list

                for image_path in pages_images:
                    # Insérer image comme page PDF
                    img_doc = fitz.open(image_path)
                    output_doc.insert_pdf(img_doc)
                    img_doc.close()

            # Sauvegarder
            output_doc.save(output_path)
            output_doc.close()

            logger.info(f"Merged PDF created: {output_path}")
            return Path(output_path)

        except Exception as e:
            logger.error(f"Error merging booklets: {e}")
            raise
```

**Règles** :
- Un PDF final = toutes les pages de la Copy
- Pages dans l'ordre (booklet order + page order)
- PDF final anonymisé (pas de nom élève visible)
- PDF final assigné à `Copy.final_pdf` **OBLIGATOIREMENT**

**INTERDIT** :
- Créer une Copy sans PDF final
- PDF final corrompu ou illisible
- Ordre des pages incorrect

---

## 5. Annotations Vectorielles

### 5.1 Format d'Annotation

**OBLIGATOIRE** :
```json
{
  "type": "path",
  "tool": "pen",
  "color": "#FF0000",
  "width": 2,
  "points": [
    {"x": 100, "y": 200},
    {"x": 105, "y": 210},
    {"x": 110, "y": 220}
  ],
  "timestamp": "2026-01-21T14:30:00Z"
}
```

**Types d'Annotations** :
- `path` : Trait à main levée (stylo)
- `text` : Commentaire textuel
- `highlight` : Surligneur
- `shape` : Formes (cercle, rectangle)

**Champs Obligatoires** :
- `type` : Type d'annotation
- `tool` : Outil utilisé
- `color` : Couleur (hex)
- `width` : Épaisseur (si applicable)
- `points` : Coordonnées normalisées [0, 1]
- `timestamp` : Date de création

### 5.2 Coordonnées Normalisées

**OBLIGATOIRE** :
```javascript
// Frontend - Normalisation
function normalizeCoordinates(x, y, canvasWidth, canvasHeight) {
  return {
    x: x / canvasWidth,   // [0, 1]
    y: y / canvasHeight   // [0, 1]
  }
}

// Backend - Dénormalisation pour export
function denormalizeCoordinates(normalizedX, normalizedY, pdfWidth, pdfHeight) {
  return {
    x: normalizedX * pdfWidth,
    y: normalizedY * pdfHeight
  }
}
```

**Raisons** :
- Indépendance de la résolution d'affichage
- Export PDF correct quelle que soit la taille
- Zoom sans perte de précision

**INTERDIT** :
- Coordonnées en pixels absolus
- Coordonnées dépendantes du canvas size
- Annotations perdues lors du zoom

### 5.3 Stockage Annotations

**OBLIGATOIRE** :
```python
# grading/models.py
class Annotation(models.Model):
    copy = models.ForeignKey(Copy, on_delete=models.CASCADE, related_name='annotations')
    page_number = models.PositiveIntegerField()

    # JSON contenant TOUTES les annotations de cette page
    vector_data = models.JSONField()

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['copy', 'page_number']),
        ]
```

**Structure vector_data** :
```json
{
  "annotations": [
    {
      "id": "uuid-1",
      "type": "path",
      "tool": "pen",
      "color": "#FF0000",
      "width": 2,
      "points": [{"x": 0.1, "y": 0.2}, ...],
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

**Règles** :
- Une Annotation DB = une page
- `vector_data` contient array d'annotations
- IDs uniques par annotation (UUID)
- Timestamp pour traçabilité

---

## 6. Export PDF avec Annotations

### 6.1 Aplatissement (Flattening)

**OBLIGATOIRE** :
```python
# processing/services/pdf_flattener.py
import fitz
from pathlib import Path

class PDFAnnotationFlattener:
    @staticmethod
    def flatten_annotations(copy, output_path):
        """
        Applique les annotations sur le PDF final et génère un nouveau PDF.

        Args:
            copy: Instance de Copy
            output_path: Chemin du PDF de sortie

        Returns:
            Path: Chemin du PDF annoté
        """
        # Ouvrir PDF source
        doc = fitz.open(copy.final_pdf.path)

        # Récupérer toutes les annotations
        annotations = copy.annotations.all().order_by('page_number')

        for annotation in annotations:
            page_num = annotation.page_number - 1  # 0-indexed
            page = doc[page_num]

            # Appliquer chaque annotation vectorielle
            for annot_data in annotation.vector_data.get('annotations', []):
                apply_annotation_to_page(page, annot_data, page.rect)

        # Sauvegarder PDF final
        doc.save(output_path, deflate=True)
        doc.close()

        logger.info(f"Flattened PDF created: {output_path}")
        return Path(output_path)

    @staticmethod
    def apply_annotation_to_page(page, annot_data, page_rect):
        """
        Applique une annotation sur une page PDF.
        """
        annot_type = annot_data.get('type')

        if annot_type == 'path':
            draw_path_annotation(page, annot_data, page_rect)
        elif annot_type == 'text':
            draw_text_annotation(page, annot_data, page_rect)
        elif annot_type == 'highlight':
            draw_highlight_annotation(page, annot_data, page_rect)
        else:
            logger.warning(f"Unknown annotation type: {annot_type}")

def draw_path_annotation(page, annot_data, page_rect):
    """
    Dessine un trait sur la page PDF.
    """
    points = annot_data.get('points', [])
    color = hex_to_rgb(annot_data.get('color', '#000000'))
    width = annot_data.get('width', 2)

    # Dénormaliser coordonnées
    pdf_points = [
        (p['x'] * page_rect.width, p['y'] * page_rect.height)
        for p in points
    ]

    # Dessiner
    shape = page.new_shape()
    if len(pdf_points) > 1:
        shape.draw_polyline(pdf_points)
        shape.finish(color=color, width=width)
        shape.commit()
```

**Règles** :
- Dénormalisation des coordonnées selon taille page PDF
- Respect des couleurs, épaisseurs, styles
- Annotations aplaties (non modifiables dans PDF final)
- Qualité visuelle identique à l'interface de correction

**INTERDIT** :
- Annotations perdues lors de l'export
- Décalage de coordonnées
- Qualité dégradée
- PDF final non généré

### 6.2 Assignation PDF Final

**OBLIGATOIRE** :
```python
# exams/services.py
@transaction.atomic
def finalize_copy_grading(copy, scores_data, final_comment):
    """
    Finalise la correction d'une copie.
    """
    # Créer Score
    score = Score.objects.create(
        copy=copy,
        scores_data=scores_data,
        final_comment=final_comment
    )

    # ⚠️ CRITIQUE: Générer PDF final avec annotations
    output_path = f"/media/copies/graded/copy_{copy.id}_graded.pdf"
    final_pdf_path = PDFAnnotationFlattener.flatten_annotations(copy, output_path)

    # ⚠️ OBLIGATOIRE: Assigner à copy.final_pdf
    copy.final_pdf.name = str(final_pdf_path)
    copy.status = Copy.Status.GRADED
    copy.graded_at = timezone.now()
    copy.save(update_fields=['final_pdf', 'status', 'graded_at'])

    logger.info(f"Copy {copy.id} finalized with PDF: {final_pdf_path}")
    return score
```

**INTERDIT** :
- Finaliser une copie sans PDF final
- PDF final non accessible
- `copy.final_pdf` vide ou null

---

## 7. Gestion de la Mémoire

### 7.1 Streaming pour Gros Fichiers

**OBLIGATOIRE** :
```python
# Processing par chunks pour éviter OOM
def process_large_pdf_streaming(pdf_path):
    """
    Traite un gros PDF page par page.
    """
    doc = fitz.open(pdf_path)

    for page_num in range(doc.page_count):
        page = doc.load_page(page_num)  # Charge une page uniquement

        # Traiter la page
        process_page(page)

        # Libérer mémoire
        page = None  # Garbage collect

    doc.close()
```

**Règles** :
- Ne jamais charger tout le PDF en mémoire si >10 MB
- Traitement page par page
- Garbage collection explicite si nécessaire
- Monitoring mémoire

### 7.2 Celery pour Traitements Longs

**OBLIGATOIRE** :
```python
# processing/tasks.py
from celery import shared_task

@shared_task(bind=True, max_retries=3)
def process_exam_pdf_async(self, exam_id):
    """
    Traitement asynchrone du PDF d'examen.
    """
    try:
        exam = Exam.objects.get(id=exam_id)

        # Split en pages
        pages = PDFSplitter.split_to_images(exam.pdf_source.path, ...)

        # Détection booklets
        booklets = BookletDetector.detect_booklets(exam, pages)

        # Mise à jour
        exam.is_processed = True
        exam.save()

        return {'success': True, 'booklets_count': len(booklets)}

    except Exception as exc:
        logger.error(f"Error processing exam {exam_id}: {exc}")
        raise self.retry(exc=exc, countdown=60)
```

**Règles** :
- Celery pour PDF >5 MB ou >20 pages
- Retry policy configurée
- Progress updates si possible (Celery progress)
- Timeout raisonnable (30 min max)

---

## 8. Validation et Tests

### 8.1 Tests de Pipeline

**OBLIGATOIRE** :
```python
# processing/tests/test_pipeline.py
from django.test import TestCase
from exams.models import Exam
from processing.services import PDFSplitter

class PDFPipelineTest(TestCase):
    def test_split_pdf_produces_correct_number_of_pages(self):
        exam = create_test_exam_with_pdf(pages=4)

        pages = PDFSplitter.split_to_images(exam.pdf_source.path, "/tmp/test")

        self.assertEqual(len(pages), 4)

    def test_merged_pdf_has_all_pages(self):
        booklets = create_test_booklets(count=2, pages_per_booklet=4)

        merged_pdf = PDFMerger.merge_booklets_to_pdf(booklets, "/tmp/merged.pdf")

        doc = fitz.open(merged_pdf)
        self.assertEqual(doc.page_count, 8)
        doc.close()

    def test_annotations_preserved_after_flattening(self):
        copy = create_copy_with_annotations()

        flattened_pdf = PDFAnnotationFlattener.flatten_annotations(copy, "/tmp/flat.pdf")

        # Vérifier que le PDF contient les annotations visuellement
        # (Test manuel ou via image comparison)
        self.assertTrue(flattened_pdf.exists())
```

---

## 9. Checklist PDF Processing

Avant toute modification du pipeline PDF :
- [ ] Déterminisme garanti (même input → même output)
- [ ] Pas de perte de pages
- [ ] Pas de perte d'annotations
- [ ] Coordonnées normalisées utilisées
- [ ] PDF final toujours assigné à Copy
- [ ] Logging à chaque étape
- [ ] Gestion d'erreurs robuste
- [ ] Mémoire gérée (streaming si nécessaire)
- [ ] Tests passent

Avant export PDF final :
- [ ] Toutes les annotations chargées
- [ ] Coordonnées dénormalisées correctement
- [ ] Qualité visuelle vérifiée
- [ ] PDF final accessible et lisible
- [ ] `copy.final_pdf` non vide

---

**Version** : 1.0
**Date** : 2026-01-21
**Statut** : CRITIQUE - Aucune perte de données tolérée
