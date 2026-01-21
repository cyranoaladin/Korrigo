# Workflow: Accès Élève (Lecture Copies)

## Vue d'Ensemble

Workflow d'accès en **lecture seule** pour les élèves à leurs copies corrigées.

---

## Workflow Complet

```
1. Élève Login (INE + code d'accès)
   ↓
2. Session Élève Créée (student_id, timeout 4h)
   ↓
3. Liste Copies Élève (status=GRADED uniquement)
   ↓
4. Sélection d'une Copie
   ↓
5. Visualisation PDF Final avec Annotations
   ↓
6. Consultation Note et Appréciation
   ↓
7. Logout (ou timeout auto)
```

---

## Étapes Détaillées

### 1. Login Élève
Voir [authentication_flow.md](./authentication_flow.md#3-authentification-élève)

### 2. Liste Copies

**Backend** :
```python
class StudentCopyViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsStudent, IsOwnerStudent]

    def get_queryset(self):
        student_id = self.request.session.get('student_id')
        return Copy.objects.filter(
            student_id=student_id,
            status=Copy.Status.GRADED,
            is_identified=True
        ).select_related('exam').prefetch_related('scores')
```

**Restrictions** :
- [ ] Status = GRADED uniquement
- [ ] Student = élève connecté uniquement
- [ ] is_identified = True (levée anonymat)
- [ ] Lecture seule (ReadOnlyModelViewSet)

### 3. Visualisation Copie

**Frontend** :
```vue
<template>
  <div class="student-copy-view">
    <PDFViewer :pdf-url="copy.final_pdf" :readonly="true" />

    <div class="score-panel">
      <h3>Note : {{ totalScore }} / {{ exam.total }}</h3>
      <p>{{ copy.score.final_comment }}</p>
    </div>
  </div>
</template>
```

**Backend** :
```python
@api_view(['GET'])
@permission_classes([IsStudent, IsOwnerStudent])
def download_copy_pdf(request, copy_id):
    copy = get_object_or_404(
        Copy,
        id=copy_id,
        student_id=request.session.get('student_id'),
        status=Copy.Status.GRADED
    )

    # Servir PDF de manière sécurisée
    response = FileResponse(copy.final_pdf.open('rb'))
    response['Content-Disposition'] = f'inline; filename="{copy.anonymous_id}.pdf"'
    return response
```

### 4. Restrictions Sécurité

**INTERDIT pour Élève** :
- [ ] Modifier quoi que ce soit
- [ ] Accéder aux copies d'autres élèves
- [ ] Accéder aux copies non corrigées (status != GRADED)
- [ ] Accéder aux endpoints API autres que consultation
- [ ] Énumérer les copies (pas de liste globale)
- [ ] Accéder au Django Admin

**OBLIGATOIRE** :
- [ ] Permissions strictes (IsStudent + IsOwnerStudent)
- [ ] Filtrage par student_id en session
- [ ] Timeout session court (4h)
- [ ] Logging accès

---

## Diagramme Sécurité

```
Élève Login
    ↓
Session avec student_id uniquement (PAS Django User)
    ↓
Accès filtré copies:
  - student_id = session.student_id
  - status = GRADED
  - is_identified = True
    ↓
PDF Final READONLY
```

---

**Version** : 1.0
**Date** : 2026-01-21
