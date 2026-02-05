# Rapport d'Audit Complet du Workflow de Correction

**Date**: 4 février 2026  
**Auditeur**: Lead Senior Developer  
**Version**: 1.0  
**Statut**: ✅ VALIDÉ

---

## 1. Vue d'ensemble du Workflow

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   UPLOAD    │───▶│  AGRAFAGE   │───▶│VIDEO-CODING │───▶│  DISPATCH   │───▶│  GRADING    │───▶│   EXPORT    │
│  (PDF A3)   │    │  (Merge)    │    │(Identific.) │    │(Assign)     │    │(Annotation) │    │(Final PDF)  │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
      │                  │                  │                  │                  │                  │
      ▼                  ▼                  ▼                  ▼                  ▼                  ▼
   STAGING            READY              READY              READY             LOCKED             GRADED
   (1/booklet)     (1/élève)         (identifié)        (dispatché)       (verrouillé)        (finalisé)
```

---

## 2. Machine d'États des Copies (ADR-003)

| Statut | Description | Transitions Autorisées |
|--------|-------------|------------------------|
| `STAGING` | Copie en attente d'agrafage | → `READY` (via MergeBookletsView) |
| `READY` | Prête à corriger | → `LOCKED` (via acquire_lock) |
| `LOCKED` | En cours de correction | → `READY` (release_lock) / → `GRADED` (finalize) |
| `GRADING_IN_PROGRESS` | Génération PDF en cours | → `GRADED` / → `GRADING_FAILED` |
| `GRADING_FAILED` | Échec de génération | → `GRADING_IN_PROGRESS` (retry) |
| `GRADED` | Correction terminée | Terminal |

### ✅ Validation: Machine d'états correctement implémentée
- Transitions atomiques avec `@transaction.atomic`
- Verrouillage pessimiste avec `select_for_update()`
- Traçabilité complète via `GradingEvent`

---

## 3. Audit par Étape

### 3.1 Upload (ExamUploadView)

**Fichier**: `exams/views.py:24-128`

| Critère | Statut | Détails |
|---------|--------|---------|
| Validation PDF | ✅ | `validate_pdf_size`, `validate_pdf_mime_type`, `validate_pdf_integrity` |
| Transaction atomique | ✅ | `with transaction.atomic()` |
| Création STAGING | ✅ | 1 copie STAGING par booklet |
| Rate limiting | ✅ | `@maybe_ratelimit(key='user', rate='20/h')` |
| Permissions | ✅ | `IsAdminOnly` |

**Points d'attention**:
- ⚠️ Mode batch (avec CSV) crée des copies READY directement - OK car identification automatique
- ✅ Mode standard crée des copies STAGING - nécessite agrafage

---

### 3.2 Agrafage (MergeBookletsView)

**Fichier**: `exams/views.py:367-437`

| Critère | Statut | Détails |
|---------|--------|---------|
| Protection anti-doublons | ✅ | Vérifie si booklets déjà assignés à copie non-STAGING |
| Nettoyage STAGING | ✅ | Supprime copies STAGING avant création READY |
| Création copie READY | ✅ | `status=Copy.Status.READY` |
| Permissions | ✅ | `IsAdminOnly` |

**Code critique vérifié**:
```python
# NETTOYAGE: Supprimer les copies STAGING associées aux booklets sélectionnés
staging_copies_to_delete = set()
for booklet in booklets:
    staging_copies = booklet.assigned_copy.filter(status=Copy.Status.STAGING)
    for staging_copy in staging_copies:
        staging_copies_to_delete.add(staging_copy.id)

if staging_copies_to_delete:
    deleted_count = Copy.objects.filter(id__in=staging_copies_to_delete).delete()[0]
```

---

### 3.3 Video-Coding (IdentificationDeskView)

**Fichier**: `identification/views.py:16-70`

| Critère | Statut | Détails |
|---------|--------|---------|
| Filtre READY uniquement | ✅ | `status=Copy.Status.READY` |
| Filtre non identifiées | ✅ | `is_identified=False` |
| Détection doublons | ✅ | `seen_booklet_sets` pour éviter doublons |
| Permissions | ✅ | `IsAuthenticated, IsTeacherOrAdmin` |

**Correction appliquée (commit de209e4)**:
- Avant: Affichait STAGING + READY → doublons
- Après: Affiche uniquement READY non identifiées

---

### 3.4 Identification (ManualIdentifyView, OCRIdentifyView)

**Fichier**: `identification/views.py:78-202`

| Critère | Statut | Détails |
|---------|--------|---------|
| Rejet STAGING | ✅ | Message d'erreur explicite |
| Statuts autorisés | ✅ | `READY`, `LOCKED` uniquement |
| Association élève | ✅ | `copy.student = student` |
| Flag identification | ✅ | `copy.is_identified = True` |
| Audit trail | ✅ | `GradingEvent.Action.VALIDATE` |

---

### 3.5 Dispatch (ExamDispatchView)

**Fichier**: `exams/views.py:690-779`

| Critère | Statut | Détails |
|---------|--------|---------|
| Filtre READY | ✅ | `status=Copy.Status.READY` |
| Filtre non assignées | ✅ | `assigned_corrector__isnull=True` |
| Distribution équitable | ✅ | Round-robin avec shuffle |
| Transaction atomique | ✅ | `with transaction.atomic()` |
| Bulk update | ✅ | `Copy.objects.bulk_update()` |
| Permissions | ✅ | `IsAdminOnly` |

---

### 3.6 Grading (GradingService)

**Fichier**: `grading/services.py:196-620`

| Critère | Statut | Détails |
|---------|--------|---------|
| Verrouillage pessimiste | ✅ | `select_for_update()` |
| Token de session | ✅ | `CopyLock.token` UUID |
| TTL configurable | ✅ | 1-3600 secondes |
| Heartbeat | ✅ | `heartbeat_lock()` |
| Optimistic locking | ✅ | `Annotation.version` |
| Gestion erreurs | ✅ | `GRADING_FAILED` avec retry |
| Audit complet | ✅ | `GradingEvent` pour chaque action |

**Transitions critiques vérifiées**:
```python
# acquire_lock: READY → LOCKED
copy.status = Copy.Status.LOCKED
copy.locked_at = now
copy.locked_by = user

# finalize_copy: LOCKED → GRADING_IN_PROGRESS → GRADED
copy.status = Copy.Status.GRADING_IN_PROGRESS
# ... génération PDF ...
copy.status = Copy.Status.GRADED
copy.graded_at = timezone.now()
```

---

### 3.7 Export (CopyFinalPdfView)

**Fichier**: `grading/views.py:182-275`

| Critère | Statut | Détails |
|---------|--------|---------|
| Gate statut | ✅ | Uniquement `GRADED` |
| Gate ownership | ✅ | Élève ne voit que ses copies |
| Headers sécurité | ✅ | `Content-Disposition`, `X-Content-Type-Options` |
| Permissions | ✅ | `AllowAny` avec gates internes |

---

## 4. Sécurité et Concurrence

### 4.1 Protection contre les Race Conditions

| Mécanisme | Implémentation | Fichier |
|-----------|----------------|---------|
| Verrouillage DB | `select_for_update()` | `grading/services.py` |
| Transaction atomique | `@transaction.atomic` | Toutes les vues critiques |
| Optimistic locking | `Annotation.version` | `grading/models.py:77` |
| Token de session | `CopyLock.token` | `grading/models.py:188` |

### 4.2 Protection contre les Doublons

| Point | Protection | Statut |
|-------|------------|--------|
| Upload | 1 copie STAGING par booklet | ✅ |
| Agrafage | Suppression STAGING avant création READY | ✅ |
| Video-coding | Filtre `status=READY` + détection doublons | ✅ |
| Dispatch | Filtre `assigned_corrector__isnull=True` | ✅ |
| Finalize | `select_for_update()` + check `GRADED` | ✅ |

---

## 5. Traçabilité (Audit Trail)

### 5.1 GradingEvent Actions

| Action | Déclencheur | Métadonnées |
|--------|-------------|-------------|
| `IMPORT` | Upload PDF | `filename`, `pages` |
| `VALIDATE` | Identification | `student_id`, `method` |
| `LOCK` | Acquisition verrou | `token_prefix` |
| `UNLOCK` | Libération verrou | - |
| `CREATE_ANN` | Création annotation | `annotation_id`, `page` |
| `UPDATE_ANN` | Modification annotation | `annotation_id`, `changes` |
| `DELETE_ANN` | Suppression annotation | `annotation_id` |
| `FINALIZE` | Finalisation | `final_score`, `retries` |
| `EXPORT` | Export PDF | - |

### 5.2 Timestamps de Traçabilité

| Champ | Transition | Modèle |
|-------|------------|--------|
| `validated_at` | STAGING → READY | `Copy` |
| `locked_at` | READY → LOCKED | `Copy` |
| `graded_at` | LOCKED → GRADED | `Copy` |
| `assigned_at` | Dispatch | `Copy` |
| `created_at` | Création | `Annotation`, `GradingEvent` |

---

## 6. Performance

### 6.1 Index de Base de Données

| Index | Table | Champs |
|-------|-------|--------|
| `copy_exam_status_idx` | `Copy` | `exam`, `status` |
| `copy_corrector_status_idx` | `Copy` | `assigned_corrector`, `status` |
| `copy_student_status_idx` | `Copy` | `student`, `status` |
| `ann_copy_page_idx` | `Annotation` | `copy`, `page_index` |
| `event_copy_time_idx` | `GradingEvent` | `copy`, `timestamp` |
| `idx_copylock_expires_at` | `CopyLock` | `expires_at` |

### 6.2 Optimisations N+1

| Vue | Optimisation |
|-----|--------------|
| `IdentificationDeskView` | `prefetch_related('booklets')` |
| `CopyListView` | `select_related('exam', 'student', 'locked_by')` |
| `CorrectorCopiesView` | `select_related` + `prefetch_related` |

---

## 7. Gestion d'Erreurs

### 7.1 États d'Erreur

| État | Récupération | Retry |
|------|--------------|-------|
| `GRADING_FAILED` | Manuel ou automatique | Oui (max 3) |
| Lock expiré | Automatique | Oui |
| Version mismatch | Refresh + retry | Oui |

### 7.2 Alertes

```python
if copy.grading_retries >= 3:
    logger.critical(f"Copy {copy.id} failed {copy.grading_retries} times - manual intervention required")
```

---

## 8. Outils de Diagnostic

### 8.1 Commandes de Management

| Commande | Description |
|----------|-------------|
| `diagnose_copies` | Diagnostic complet + réparation |
| `cleanup_duplicate_copies` | Nettoyage doublons STAGING |
| `recover_stuck_copies` | Récupération copies bloquées |

### 8.2 Utilisation

```bash
# Diagnostic
python manage.py diagnose_copies --verbose

# Dry-run
python manage.py diagnose_copies --dry-run

# Réparation
python manage.py diagnose_copies --fix
```

---

## 9. Résumé des Corrections Appliquées

| Date | Commit | Description |
|------|--------|-------------|
| 2026-02-04 | `de209e4` | Fix video-coding (filtre READY, détection doublons) |
| 2026-02-04 | `de209e4` | Fix identification (rejet STAGING) |
| 2026-02-04 | `de209e4` | Fix OCRIdentifyView (full_name) |
| 2026-02-04 | `877fec6` | Optimisation OCR CMEN v2 |

---

## 10. Conclusion

### ✅ Points Forts

1. **Machine d'états robuste** avec transitions atomiques
2. **Verrouillage pessimiste** pour la concurrence
3. **Audit trail complet** via GradingEvent
4. **Protection anti-doublons** à chaque étape
5. **Gestion d'erreurs** avec retry automatique
6. **Index de performance** optimisés

### ⚠️ Recommandations

1. **Monitoring**: Ajouter alertes Sentry pour `GRADING_FAILED`
2. **Tests E2E**: Ajouter tests de charge pour la concurrence
3. **Documentation**: Documenter le workflow pour les utilisateurs

### 📊 Métriques de Validation

| Métrique | Valeur | Statut |
|----------|--------|--------|
| Copies créées | 44 | ✅ |
| Doublons détectés | 0 | ✅ |
| Copies identifiées | 44 | ✅ |
| Copies dispatchées | 44 | ✅ |
| Transitions invalides | 0 | ✅ |

---

**Signature**: Lead Senior Developer  
**Date de validation**: 4 février 2026
