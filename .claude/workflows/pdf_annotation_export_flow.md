# Workflow: Annotations et Export PDF

## Vue d'Ensemble

Workflow de capture, stockage et export des annotations vectorielles sur PDF.

---

## Workflow Annotations

```
1. Capture Annotations (Canvas Frontend)
   ├─ Normalisation Coordonnées [0, 1]
   └─ Stockage Local Temporaire
   ↓
2. Autosave Périodique (30s)
   ├─ Envoi Backend
   └─ Stockage DB (JSON)
   ↓
3. Finalisation Correction
   ├─ Save Final Annotations
   └─ Trigger Export PDF
   ↓
4. Export PDF avec Annotations (Celery)
   ├─ Load Annotations from DB
   ├─ Dénormalisation Coordonnées
   ├─ Application sur PDF (Flattening)
   └─ Génération PDF Final
   ↓
5. PDF Final Disponible pour Élève
```

---

## 1. Capture Annotations Frontend

**Canvas Event Handling** :
```javascript
// composables/useCanvas.js
export function useCanvas(canvasRef) {
  const currentPath = ref([])
  const isDrawing = ref(false)

  const startDrawing = (event) => {
    isDrawing.value = true
    const point = getCanvasPoint(event)
    currentPath.value = [point]
  }

  const draw = (event) => {
    if (!isDrawing.value) return

    const point = getCanvasPoint(event)
    currentPath.value.push(point)

    // Dessiner visuellement
    drawOnCanvas(point)
  }

  const stopDrawing = () => {
    if (currentPath.value.length > 0) {
      // Normaliser coordonnées
      const normalized = normalizeCoordinates(
        currentPath.value,
        canvasRef.value
      )

      // Créer annotation
      const annotation = {
        id: crypto.randomUUID(),
        type: 'path',
        tool: currentTool.value,
        color: currentColor.value,
        width: currentWidth.value,
        points: normalized,
        page_number: currentPage.value,
        timestamp: new Date().toISOString()
      }

      emit('annotation-added', annotation)
    }

    isDrawing.value = false
    currentPath.value = []
  }

  return { startDrawing, draw, stopDrawing }
}

function getCanvasPoint(event) {
  const rect = canvasRef.value.getBoundingClientRect()
  return {
    x: event.clientX - rect.left,
    y: event.clientY - rect.top
  }
}

function normalizeCoordinates(points, canvas) {
  return points.map(p => ({
    x: p.x / canvas.width,
    y: p.y / canvas.height
  }))
}
```

---

## 2. Stockage Backend

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

**Backend Save** :
```python
@api_view(['POST'])
@permission_classes([IsAuthenticated, IsProfessor])
def save_annotations(request, copy_id):
    copy = get_object_or_404(Copy, id=copy_id, locked_by=request.user)

    page_number = request.data.get('page_number')
    annotations = request.data.get('annotations', [])

    # Valider annotations
    for annot in annotations:
        validate_annotation(annot)

    # Sauvegarder
    Annotation.objects.update_or_create(
        copy=copy,
        page_number=page_number,
        defaults={
            'vector_data': {'annotations': annotations}
        }
    )

    return Response({'success': True})

def validate_annotation(annot):
    # Valider structure
    required_fields = ['id', 'type', 'timestamp']
    for field in required_fields:
        if field not in annot:
            raise ValidationError(f"Missing field: {field}")

    # Valider coordonnées normalisées
    if annot['type'] == 'path':
        for point in annot.get('points', []):
            if not (0 <= point['x'] <= 1 and 0 <= point['y'] <= 1):
                raise ValidationError("Coordinates must be normalized [0, 1]")
```

---

## 3. Export PDF avec Annotations

**Celery Task** :
```python
@shared_task
def generate_final_pdf(copy_id):
    copy = Copy.objects.get(id=copy_id)

    # Output path
    output_path = f"/media/copies/graded/copy_{copy.id}_graded.pdf"

    # Flatten annotations
    final_pdf = PDFAnnotationFlattener.flatten_annotations(copy, output_path)

    # Assigner à copy
    copy.final_pdf.name = str(final_pdf)
    copy.save(update_fields=['final_pdf'])

    logger.info(f"Final PDF generated: {copy.id}")
    return {'success': True, 'pdf': str(final_pdf)}
```

**Flattening Logic** :
```python
class PDFAnnotationFlattener:
    @staticmethod
    def flatten_annotations(copy, output_path):
        # Ouvrir PDF source
        doc = fitz.open(copy.final_pdf.path)

        # Récupérer annotations
        annotations = copy.annotations.all().order_by('page_number')

        for annotation_obj in annotations:
            page_num = annotation_obj.page_number - 1
            page = doc[page_num]
            page_rect = page.rect

            # Appliquer chaque annotation
            for annot in annotation_obj.vector_data.get('annotations', []):
                apply_annotation(page, annot, page_rect)

        # Sauvegarder
        doc.save(output_path, deflate=True, garbage=4)
        doc.close()

        return Path(output_path)

def apply_annotation(page, annot, page_rect):
    annot_type = annot.get('type')

    if annot_type == 'path':
        draw_path(page, annot, page_rect)
    elif annot_type == 'text':
        draw_text(page, annot, page_rect)
    elif annot_type == 'highlight':
        draw_highlight(page, annot, page_rect)

def draw_path(page, annot, page_rect):
    points = annot.get('points', [])
    color = hex_to_rgb(annot.get('color', '#FF0000'))
    width = annot.get('width', 2)

    # Dénormaliser
    pdf_points = [
        (p['x'] * page_rect.width, p['y'] * page_rect.height)
        for p in points
    ]

    # Dessiner
    if len(pdf_points) > 1:
        shape = page.new_shape()
        shape.draw_polyline(pdf_points)
        shape.finish(color=color, width=width)
        shape.commit()
```

---

## 4. Validation Export

**Checklist** :
- [ ] Toutes les annotations chargées
- [ ] Coordonnées dénormalisées correctement
- [ ] Couleurs/épaisseurs respectées
- [ ] Textes lisibles
- [ ] Pas d'annotations manquantes
- [ ] PDF final lisible et cohérent
- [ ] Qualité visuelle identique à l'interface

---

**Version** : 1.0
**Date** : 2026-01-21
