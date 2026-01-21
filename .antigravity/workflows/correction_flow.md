# Workflow: Processus de Correction

## Vue d'Ensemble

Ce workflow décrit le processus complet de correction d'une copie, du verrouillage à la finalisation.

---

## Étapes du Workflow

```
1. Claim/Lock Copy (Verrouillage)
   ↓
2. Load PDF + Existing Annotations
   ↓
3. Annotate Pages (Dessins, Commentaires)
   ↓
4. Grade Questions (Barème)
   ↓
5. Write Final Comment
   ↓
6. Save Progress (Autosave périodique)
   ↓
7. Finalize Grading
   ↓
8. Generate Final PDF with Annotations
   ↓
9. Unlock Copy → Status GRADED
```

---

## 1. Claim/Lock Copy

### Objectif
Verrouiller une copie pour éviter corrections simultanées.

### État Initial
- Copy.status = READY

### Actions
```python
POST /api/copies/{id}/lock/

# Backend (service)
@transaction.atomic
def lock_copy(copy, professor):
    if copy.status != Copy.Status.READY:
        raise ValueError("Copy not ready for grading")

    copy.status = Copy.Status.LOCKED
    copy.locked_by = professor
    copy.locked_at = timezone.now()
    copy.save(update_fields=['status', 'locked_by', 'locked_at'])

    logger.info(f"Copy {copy.id} locked by {professor}")
    return copy
```

### État Final
- Copy.status = LOCKED
- Copy.locked_by = professor
- Copy.locked_at = timestamp

### Validation
- [ ] Copie en status READY
- [ ] Transaction atomique
- [ ] Logging effectué
- [ ] Permissions vérifiées

---

## 2. Load PDF + Annotations

### Objectif
Charger le PDF de la copie et les annotations existantes (si reprise).

### Actions
```javascript
// Frontend
const { copy, annotations } = await copyService.getCopyForCorrection(copyId)

// Charger PDF
const pdfUrl = copy.final_pdf

// Charger annotations existantes
const annotationsByPage = groupAnnotationsByPage(annotations)
```

### Validation
- [ ] PDF accessible
- [ ] Annotations chargées correctement
- [ ] Coordonnées normalisées

---

## 3. Annotate Pages

### Objectif
Ajouter annotations vectorielles sur les pages du PDF.

### Types d'Annotations
- **Path** : Traits à main levée (stylo, surligneur)
- **Text** : Commentaires textuels
- **Shape** : Formes (cercle pour souligner erreur, etc.)

### Actions
```javascript
// Frontend - Canvas
function handleDrawing(event) {
  const point = capturePoint(event, canvas)
  currentPath.push(point)

  // Normaliser
  const normalized = normalizeCoordinates(currentPath, canvas)

  // Ajouter annotation locale
  addAnnotation({
    id: crypto.randomUUID(),
    type: 'path',
    tool: 'pen',
    color: '#FF0000',
    width: 2,
    points: normalized,
    page_number: currentPage,
    timestamp: new Date().toISOString()
  })
}
```

### Autosave
```javascript
// Sauvegarde automatique toutes les 30 secondes
setInterval(async () => {
  if (hasUnsavedChanges) {
    await saveAnnotations()
  }
}, 30000)
```

### Validation
- [ ] Coordonnées normalisées [0, 1]
- [ ] Annotations sauvegardées périodiquement
- [ ] Pas de perte d'annotations
- [ ] UUIDs uniques

---

## 4. Grade Questions

### Objectif
Attribuer des notes selon le barème défini.

### Structure Barème
```json
{
  "exercices": [
    {
      "id": "ex1",
      "title": "Exercice 1",
      "total": 5,
      "questions": [
        {"id": "ex1q1", "points": 2},
        {"id": "ex1q2", "points": 3}
      ]
    }
  ]
}
```

### Actions
```javascript
// Frontend - GradingSidebar
function updateScore(questionId, points) {
  scores[questionId] = points

  // Calcul total
  const total = Object.values(scores).reduce((sum, p) => sum + p, 0)
  displayTotal(total)
}
```

### Validation
- [ ] Scores cohérents avec barème
- [ ] Total calculé correctement
- [ ] Validation côté backend également

---

## 5. Write Final Comment

### Objectif
Ajouter une appréciation générale pour l'élève.

### Actions
```javascript
// Frontend
<textarea
  v-model="finalComment"
  placeholder="Appréciation générale..."
  maxlength="1000"
/>
```

### Validation
- [ ] Longueur limitée (1000 caractères)
- [ ] Validation XSS (pas de HTML)

---

## 6. Finalize Grading

### Objectif
Finaliser la correction et générer le PDF final avec annotations.

### Actions

**Frontend** :
```javascript
async function finalizeGrading() {
  // Vérifications
  if (!allQuestionsGraded()) {
    alert("Toutes les questions doivent être notées")
    return
  }

  // Envoyer au backend
  await copyService.finalize(copyId, {
    scores_data: scores,
    final_comment: finalComment,
    annotations: annotations
  })

  // Redirect
  router.push('/dashboard')
}
```

**Backend** :
```python
@transaction.atomic
def finalize_grading(copy, scores_data, final_comment, annotations):
    if copy.status != Copy.Status.LOCKED:
        raise ValueError("Copy must be locked")

    # Créer Score
    score = Score.objects.create(
        copy=copy,
        scores_data=scores_data,
        final_comment=final_comment
    )

    # Sauvegarder annotations
    for page_num, annots in annotations.items():
        Annotation.objects.update_or_create(
            copy=copy,
            page_number=page_num,
            defaults={'vector_data': {'annotations': annots}}
        )

    # Générer PDF final avec annotations (async)
    from processing.tasks import generate_final_pdf
    generate_final_pdf.delay(copy.id)

    # Mettre à jour statut
    copy.status = Copy.Status.GRADED
    copy.graded_at = timezone.now()
    copy.save(update_fields=['status', 'graded_at'])

    return score
```

### Validation
- [ ] Toutes les questions notées
- [ ] Annotations sauvegardées
- [ ] Score créé
- [ ] PDF final généré
- [ ] Status → GRADED
- [ ] Transaction atomique

---

## 7. Generate Final PDF

### Objectif
Appliquer les annotations sur le PDF et générer le PDF final.

### Actions (Celery Task)
```python
@shared_task
def generate_final_pdf(copy_id):
    copy = Copy.objects.get(id=copy_id)

    # Générer PDF avec annotations aplaties
    output_path = f"/media/copies/graded/copy_{copy.id}_graded.pdf"
    final_pdf = PDFAnnotationFlattener.flatten_annotations(copy, output_path)

    # Assigner à copy.final_pdf
    copy.final_pdf.name = str(final_pdf)
    copy.save(update_fields=['final_pdf'])

    logger.info(f"Final PDF generated for copy {copy_id}")
```

### Validation
- [ ] Annotations appliquées visuellement
- [ ] PDF final accessible
- [ ] copy.final_pdf assigné
- [ ] Qualité visuelle identique à l'interface

---

## 8. Unlock (si nécessaire)

### Objectif
Déverrouiller une copie sans finaliser (si erreur ou changement de correcteur).

### Actions
```python
POST /api/copies/{id}/unlock/

@transaction.atomic
def unlock_copy(copy, professor):
    if copy.status != Copy.Status.LOCKED:
        raise ValueError("Copy not locked")

    if copy.locked_by != professor and not professor.is_superuser:
        raise PermissionError("Not authorized to unlock")

    copy.status = Copy.Status.READY
    copy.locked_by = None
    copy.locked_at = None
    copy.save(update_fields=['status', 'locked_by', 'locked_at'])

    logger.info(f"Copy {copy.id} unlocked by {professor}")
```

---

## Diagramme États

```
STAGING → READY → LOCKED → GRADED
    ↑               ↓
    └───── (unlock) ┘
```

**Transitions Autorisées** :
- STAGING → READY (validation manuelle)
- READY → LOCKED (claim)
- LOCKED → READY (unlock)
- LOCKED → GRADED (finalize)

**Interdit** :
- GRADED → * (immutable)
- Direct READY → GRADED (doit passer par LOCKED)

---

**Version** : 1.0
**Date** : 2026-01-21
**Statut** : Obligatoire
