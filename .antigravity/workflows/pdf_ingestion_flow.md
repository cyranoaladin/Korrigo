# Workflow: Ingestion et Split PDF

## Vue d'Ensemble

Workflow d'ingestion d'un PDF d'examen source et création des copies individuelles.

---

## Workflow Complet

```
1. Upload PDF Source (Examen)
   ↓
2. Validation PDF (taille, intégrité)
   ↓
3. Traitement Asynchrone (Celery)
   ├─ 3a. Split PDF en Pages Images
   ├─ 3b. OCR En-têtes
   └─ 3c. Détection Fascicules (Booklets)
   ↓
4. Staging Area (Validation Manuelle)
   ├─ Affichage Booklets Détectés
   ├─ Ajustements Manuels (Fusion/Séparation)
   └─ Validation par Professeur
   ↓
5. Création Copies Finales
   ├─ Merge Booklets → PDF Final
   └─ Status Copy = READY
   ↓
6. Copies Prêtes pour Correction
```

---

## 1. Upload PDF Source

**Frontend** :
```vue
<input type="file" accept=".pdf" @change="handleFileUpload" />
```

**Backend** :
```python
class ExamViewSet(viewsets.ModelViewSet):
    @action(detail=False, methods=['post'])
    def upload_exam(self, request):
        pdf_file = request.FILES.get('pdf_source')
        name = request.data.get('name')
        date = request.data.get('date')

        # Validation
        if pdf_file.size > 50 * 1024 * 1024:
            return Response({'error': 'File too large'}, status=400)

        # Créer Exam
        exam = Exam.objects.create(
            name=name,
            date=date,
            pdf_source=pdf_file,
            is_processed=False
        )

        # Lancer traitement async
        from processing.tasks import process_exam_pdf
        process_exam_pdf.delay(exam.id)

        return Response({'exam_id': str(exam.id)}, status=201)
```

---

## 2. Traitement Asynchrone

**Celery Task** :
```python
@shared_task(bind=True, max_retries=3)
def process_exam_pdf(self, exam_id):
    exam = Exam.objects.get(id=exam_id)

    # 1. Split en pages images
    pages = PDFSplitter.split_to_images(
        exam.pdf_source.path,
        output_dir=f"/media/exams/{exam_id}/pages/"
    )

    # 2. Détection booklets via OCR
    booklets_data = BookletDetector.detect_booklets(pages)

    # 3. Créer Booklets en DB
    for data in booklets_data:
        header_img_path = save_header_image(data)

        Booklet.objects.create(
            exam=exam,
            start_page=data['start'],
            end_page=data['end'],
            pages_images=data['pages'],
            header_image=header_img_path,
            student_name_guess=data['ocr_text']
        )

    # 4. Marquer examen comme traité
    exam.is_processed = True
    exam.save()

    return {'success': True, 'booklets': len(booklets_data)}
```

---

## 3. Staging Area (Validation Manuelle)

**Frontend - StagingArea.vue** :
```vue
<template>
  <div class="staging-area">
    <h2>Validation Fascicules - {{ exam.name }}</h2>

    <div v-for="booklet in booklets" :key="booklet.id" class="booklet-card">
      <img :src="booklet.header_image" alt="En-tête" />
      <p>Pages {{ booklet.start_page }} - {{ booklet.end_page }}</p>
      <p>OCR: {{ booklet.student_name_guess }}</p>

      <button @click="previewBooklet(booklet)">Prévisualiser</button>
      <button @click="editBooklet(booklet)">Modifier</button>
    </div>

    <button @click="validateAndCreateCopies" class="btn-primary">
      Valider et Créer les Copies
    </button>
  </div>
</template>
```

**Actions Manuelles** :
- **Fusion** : Combiner 2+ booklets en une copie
- **Séparation** : Séparer un booklet en plusieurs
- **Ajustement pages** : Modifier start/end pages
- **Assignation manuelle** : Associer à un élève si OCR échoué

---

## 4. Création Copies Finales

**Backend** :
```python
@api_view(['POST'])
@permission_classes([IsAuthenticated, IsProfessor])
def create_copies_from_staging(request, exam_id):
    exam = get_object_or_404(Exam, id=exam_id)
    booklets_mapping = request.data.get('booklets_mapping')

    # booklets_mapping = {
    #   'ANON001': [booklet_id1, booklet_id2],  # Fusion
    #   'ANON002': [booklet_id3],
    # }

    copies = []
    with transaction.atomic():
        for anonymous_id, booklet_ids in booklets_mapping.items():
            booklets = Booklet.objects.filter(id__in=booklet_ids)

            # Merge booklets → PDF final
            pages = []
            for booklet in booklets:
                pages.extend(booklet.pages_images)

            final_pdf_path = PDFMerger.merge_images_to_pdf(
                pages,
                f"/media/copies/final/copy_{anonymous_id}.pdf"
            )

            # Créer Copy
            copy = Copy.objects.create(
                exam=exam,
                anonymous_id=anonymous_id,
                final_pdf=final_pdf_path,
                status=Copy.Status.READY
            )

            # Associer booklets
            copy.booklets.set(booklets)

            copies.append(copy)

    return Response({
        'success': True,
        'copies_created': len(copies)
    })
```

---

## 5. Validation Finale

**Checklist** :
- [ ] Toutes les pages du PDF source traitées
- [ ] Aucune page perdue
- [ ] Booklets validés manuellement
- [ ] PDFs finaux créés et accessibles
- [ ] Copies en status READY
- [ ] copy.final_pdf assigné pour toutes

---

**Version** : 1.0
**Date** : 2026-01-21
