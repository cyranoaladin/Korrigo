# Audit de Sûreté des Données — Korrigo

> **Statut documentaire**
> Audit historique daté. Il ne remplace pas la documentation technique normative courante.

> **LOT 1 — Audit préalable avant toute correction**
> Date : 2026-03-06
> Auteur : Principal Engineer / Security Engineer
> Statut : **COMPLET**

---

## 1. Modèles Critiques — Cartographie

| Modèle | App | Table | Données métier | Volume prod | Risque corruption |
|---|---|---|---|---|---|
| `Exam` | exams | `exams_exam` | Structure barème (`grading_structure` JSONField), PDF source, correcteurs M2M, `results_released_at` | ~2 | MOYEN |
| `Copy` | exams | `exams_copy` | Statut workflow, `anonymous_id`, `student` FK, `assigned_corrector` FK, `global_appreciation`, `llm_summary`, `final_pdf`, `subject_variant`, `grading_retries` | ~209 | **CRITIQUE** |
| `Booklet` | exams | `exams_booklet` | `pages_images` (JSONField = chemins fichiers PNG), `header_image`, M2M avec Copy | ~209 | **CRITIQUE** |
| `Score` | grading | `grading_score` | `scores_data` (JSONField `{question_id: value}`), `final_comment` | ~151 | **CRITIQUE** |
| `Annotation` | grading | `grading_annotation` | Coordonnées normalisées (x,y,w,h), `content`, `type`, `score_delta`, `page_index`, `version` (optimistic lock) | ~611 | **CRITIQUE** |
| `QuestionRemark` | grading | `grading_questionremark` | `question_id`, `remark` texte libre | ~1128 | ÉLEVÉ |
| `GradingEvent` | grading | `grading_gradingevent` | Journal d'audit workflow (action, actor, metadata JSON, timestamp) | Variable | ÉLEVÉ |
| `DraftState` | grading | `grading_draftstate` | Brouillon autosave (`content` JSON, `version`, `client_id`) | Variable | MOYEN |
| `CopyLock` | grading | `grading_copylock` | Verrouillage concurrentiel (`token`, `locked_by`, `expires_at`) | Transitoire | FAIBLE |
| `Student` | students | `students_student` | Identité (`first_name`, `last_name`, `date_naissance`, `email`, `classe`, `groupe`), FK `user` | ~209+ | ÉLEVÉ |
| `AuditLog` | core | `core_auditlog` | Traçabilité RGPD (action, user, IP, timestamp, metadata) | Variable | ÉLEVÉ |
| `AnnotationTemplate` | grading | `grading_annotationtemplate` | Templates officiels par examen | Faible | FAIBLE |
| `UserAnnotation` | grading | `grading_userannotation` | Banque perso correcteur (`text`, `usage_count`, `last_used`) | Variable | FAIBLE |
| `DocumentTextExtraction` | exams | `exams_documenttextextraction` | Extraction OCR documents (sujet/corrigé/barème) | Faible | FAIBLE |
| `DocumentPage` | exams | `exams_documentpage` | Texte extrait par page | Faible | FAIBLE |
| `DocumentChunk` | exams | `exams_documentchunk` | Chunks texte indexés par exercice/question | Faible | FAIBLE |

---

## 2. Chemins d'Écriture Critiques

### 2.1 Scores

| Chemin | Fichier | Méthode | Champs modifiés | Protection |
|---|---|---|---|---|
| Sauvegarde scores | `grading/views.py` | `CopyScoresView.post` | `Score.scores_data`, `Score.final_comment` | `IsTeacherOrAdmin` permission |
| Calcul score total | `grading/services.py` | `GradingService.compute_score()` | Lecture seule (compute) | — |
| Score dans finalize | `grading/services.py` | `_finalize_copy_inner()` | `Copy.status`, `Copy.final_pdf` (score calculé) | `select_for_update`, `@transaction.atomic` |

**LOT 4 — Corrections appliquées** :
- ✅ `CopyScoresView.put` désormais dans `transaction.atomic` (prévient les races sur `update_or_create`).
- ✅ Status check GRADED existe déjà (seul superuser peut override).
- ⚠️ Risque résiduel : pas de `select_for_update` sur le Score lui-même (faible risque en pratique — un seul correcteur par copie).

### 2.2 Annotations

| Chemin | Fichier | Méthode | Champs modifiés | Protection |
|---|---|---|---|---|
| Création | `grading/services.py` | `AnnotationService.add_annotation()` | `Annotation.*`, `GradingEvent` | `@transaction.atomic`, vérifie `READY` status |
| Mise à jour | `grading/services.py` | `AnnotationService.update_annotation()` | `Annotation.content/x/y/w/h/score_delta`, `version` | `@transaction.atomic`, optimistic lock `F('version')` |
| Suppression | `grading/services.py` | `AnnotationService.delete_annotation()` | Hard delete `Annotation` | `@transaction.atomic`, vérifie `READY` status |
| Auto-save perso | `grading/views_annotation_bank.py` | `AutoSaveAnnotationView.post` | `UserAnnotation.usage_count` (F() atomic) | `IsTeacherOrAdmin` |

**Risque identifié** : Suppression d'annotation est un **hard delete** — pas de soft delete ni d'historique. Si une annotation est supprimée par erreur, elle est perdue définitivement.

### 2.3 Appréciations & Remarques

| Chemin | Fichier | Méthode | Champs modifiés | Protection |
|---|---|---|---|---|
| Appréciation globale | `grading/views.py` | `CopyGlobalAppreciationView.post` | `Copy.global_appreciation` | `IsTeacherOrAdmin` |
| Remarque par question | `grading/views.py` | `QuestionRemarkListCreateView.create` | `QuestionRemark.remark` | `IsTeacherOrAdmin` |
| Remarque update/delete | `grading/views.py` | `QuestionRemarkDetailView` | `QuestionRemark.*` | `IsTeacherOrAdmin` |

**Risque identifié** : Aucune vérification de `Copy.status` avant écriture d'appréciation ou de remarque. Potentiellement modifiable après `GRADED`.

### 2.4 Workflow / Transitions d'État Copy

| Transition | Fichier | Méthode | Statut avant | Statut après | Protection |
|---|---|---|---|---|---|
| Import PDF | `grading/services.py` | `GradingService.import_pdf()` | — | `STAGING` | `@transaction.atomic` |
| Validation | `grading/services.py` | `GradingService.validate_copy()` | `STAGING` | `READY` | Vérifie status |
| Bulk validation | `exams/views.py` | `BulkCopyValidationView.post` | `STAGING` | `READY` | Itère copies STAGING |
| PDF re-upload | `exams/views.py` | `ExamSourceUploadView.post` | — | `READY`/`STAGING` | `@transaction.atomic`, bloque si non-STAGING exist |
| Ready (mark) | `grading/views.py` | `CopyReadyView.post` | `STAGING`/`READY` | `READY` | `IsTeacherOrAdmin` |
| Finalize | `grading/services.py` | `finalize_copy()` / `_finalize_copy_inner()` | `READY`/`GRADING_FAILED` | `GRADED` | `select_for_update`, `@transaction.atomic`, retry |
| Async finalize | `grading/tasks.py` | `async_finalize_copy` | `READY`/`GRADING_FAILED` | `GRADED` | Via `GradingService.finalize_copy()` |
| Release results | `grading/views.py` | `ExamReleaseResultsView.post` | — | Sets `Exam.results_released_at` | `IsTeacherOrAdmin` |
| Unrelease results | `grading/views.py` | `ExamUnreleaseResultsView.post` | — | Nullifies `Exam.results_released_at` | `IsTeacherOrAdmin` |

**Machine d'états Copy** :
```
STAGING → READY → GRADING_IN_PROGRESS → GRADED
                                       ↘ GRADING_FAILED → (retry) → GRADED
```

### 2.5 Fichiers Médias (Écriture)

| Opération | Fichier | Effet sur disque |
|---|---|---|
| Import PDF | `grading/services.py` `import_pdf()` | Crée `copies/pages/{uuid}/p000.png` etc. dans `MEDIA_ROOT` |
| PDF re-upload | `exams/views.py` `ExamSourceUploadView` | Écrase `exam.pdf_source`, supprime anciens booklets STAGING, re-rasterise |
| Finalize copy | `grading/services.py` `_finalize_copy_inner()` | Crée `copy_{id}_corrected.pdf` via `PDFFlattener` |
| LLM summary | `processing/services/llm_summary.py` | Écrit `Copy.llm_summary` (texte, pas fichier) |
| Cleanup orphans | `grading/tasks.py` `cleanup_orphaned_files` | **Supprime** fichiers orphelins dans `temp_uploads/` |

### 2.6 Identification & Dispatch

| Chemin | Fichier | Méthode | Champs modifiés | Protection |
|---|---|---|---|---|
| Identifier copie | `exams/views.py` | `CopyIdentificationView.post` | `Copy.student`, `Copy.is_identified` | `IsTeacherOrAdmin` |
| Dispatch copies | `exams/views.py` | `ExamDispatchView.post` | `Copy.assigned_corrector`, `Copy.dispatch_run_id`, `Copy.assigned_at` | `@transaction.atomic`, `bulk_update` |
| Subject variant | `exams/views.py` | `BulkSubjectVariantView.post` | `Copy.subject_variant` | `IsTeacherOrAdmin` |
| Auto-detect variant | `exams/views.py` | `AutoDetectSubjectVariantView.post` | `Copy.subject_variant` | `IsTeacherOrAdmin` |
| Merge booklets | `exams/views.py` | `MergeBookletsView.post` | Crée `Copy`, lie booklets M2M | `IsTeacherOrAdmin` |

### 2.7 Student / Auth

| Chemin | Fichier | Méthode | Champs modifiés |
|---|---|---|---|
| Import CSV | `students/views.py` | `StudentImportView.post` | `Student.*`, crée `User` si absent |
| Change password | `students/views.py` | `StudentChangePasswordView.post` | `User.password` |
| Login | `students/views.py` | `StudentLoginView.post` | Session Django |

---

## 3. Tâches Celery — Lecture/Écriture Données

| Tâche | Fichier | Type | Données affectées |
|---|---|---|---|
| `async_finalize_copy` | `grading/tasks.py` | **ÉCRITURE** | `Copy.status`, `Copy.final_pdf`, `Copy.graded_at`, `GradingEvent` |
| `async_import_pdf` | `grading/tasks.py` | **ÉCRITURE** | Crée `Copy`, `Booklet`, fichiers PNG |
| `cleanup_orphaned_files` | `grading/tasks.py` | **ÉCRITURE** | Supprime fichiers dans `temp_uploads/` |
| `update_copy_status_metrics` | `grading/tasks.py` | Lecture | Prometheus gauges (lecture DB) |
| `process_document_set` | `exams/tasks.py` | **ÉCRITURE** | `DocumentTextExtraction`, `DocumentPage`, `DocumentChunk` |
| `process_single_document` | `exams/tasks.py` | **ÉCRITURE** | Idem — extraction texte + chunking |

**LOT 4 — Corrections appliquées** :
- ✅ `async_finalize_copy` : utilise maintenant `self.retry(exc=exc)` pour les erreurs transientes (max 3 tentatives). Les erreurs business (`ValueError`, `LockConflictError`) restent non-retryables.
- ✅ Méthodes de verrou (`acquire_lock`, `release_lock`, `heartbeat_lock`, `get_lock_status`) implémentées dans `GradingService` — étaient référencées par `views_lock.py` mais manquantes.
- ✅ Toutes les opérations de verrou utilisent `select_for_update()` pour prévenir les races.

**Risques résiduels** :
- `cleanup_orphaned_files` : supprime des fichiers sans vérifier s'ils sont référencés par un Booklet actif (commentaire TODO dans le code).
- `process_single_document` : fait `DocumentPage.objects.filter(extraction=extraction).delete()` puis `DocumentChunk.objects.filter(extraction=extraction).delete()` — **suppression avant re-création** (non idempotent en cas d'échec partiel).

---

## 4. Endpoints Servant des Fichiers Médias

| Endpoint | Vue | Fichier servi | Protection |
|---|---|---|---|
| `/api/media/<path>` | `ProtectedMediaView` | Tout fichier dans MEDIA_ROOT | `IsAuthenticated` + rôle check + **X-Accel-Redirect** ✅ LOT 2 |
| `/api/grading/copies/<id>/final-pdf/` | `CopyFinalPdfView` | `copy.final_pdf` (PDF corrigé) | AllowAny + dual auth gates + **X-Accel-Redirect** ✅ LOT 2 |
| `/api/exams/booklets/<id>/header/` | `BookletHeaderView` | Image header (crop 25% première page) | `IsTeacherOrAdmin` + **X-Accel-Redirect** (Case 1) ✅ LOT 2 |
| `/api/exams/<id>/export-pronote/` | `PronoteExportView` | CSV export (généré dynamiquement) | `IsAuthenticated` + admin check |
| `/api/exams/<id>/csv-export/` | `CSVExportView` | CSV résultats (généré dynamiquement) | `IsTeacherOrAdmin` |

**LOT 2 — Corrections appliquées** :
- ✅ Nginx `/media/` et `/internal-media/` sont maintenant `internal` — accès direct bloqué.
- ✅ Nouveau endpoint `/api/media/<path>` vérifie auth + rôle avant de servir via X-Accel-Redirect.
- ✅ `CopyFinalPdfView` converti de `FileResponse` vers `X-Accel-Redirect` (zero-copy).
- ✅ `BookletHeaderView` Case 1 converti vers `X-Accel-Redirect`.
- ✅ Frontend `getMediaUrl()` redirigé vers `/api/media/` au lieu de `/media/`.
- ✅ Serializers `final_pdf_url` et `header_image_url` retournent `/api/media/...` au lieu de `/media/...`.
- ✅ Étudiants ne peuvent accéder qu'à leurs propres copies (vérification ownership dans `ProtectedMediaView`).

---

## 5. Vulnérabilités Auth & Permissions

### 5.1 BasicAuthentication ~~active~~ — ✅ CORRIGÉ LOT 3

- ✅ `BasicAuthentication` supprimée de `DEFAULT_AUTHENTICATION_CLASSES` dans `core/settings.py`.
- ✅ `views_async.py` : `task_status` et `cancel_task` utilisent désormais `SessionAuthentication` + `IsAuthenticated`.
- ✅ `cancel_task` avait **aucun check auth** — maintenant protégé par `@permission_classes([IsAuthenticated])`.

### 5.2 Endpoints AllowAny (restants légitimes)

| Endpoint | Fichier | Justification |
|---|---|---|
| `task_status` | `grading/views_async.py` | ~~AllowAny~~ → **IsAuthenticated** ✅ LOT 3 |
| `cancel_task` | `grading/views_async.py` | ~~AllowAny sans auth~~ → **IsAuthenticated** ✅ LOT 3 |
| `CopyFinalPdfView` | `grading/views.py` | `AllowAny` justifié — dual auth (teacher session + student session) |
| `StudentLoginView` | `students/views.py` | `AllowAny` — attendu (login public, rate limited) |
| `StudentLogoutView` | `students/views.py` | `AllowAny` — acceptable |
| `CSRFTokenView` | `core/views.py` | `AllowAny` — nécessaire pré-login |
| `LoginView` | `core/views.py` | `AllowAny` — login public, rate limited |
| Health check endpoints | `core/views_health.py` | `AllowAny` — attendu (probes Docker/K8s) |

### 5.3 Permissions manquantes / incohérentes — ✅ CORRIGÉ LOT 5

- ✅ `CopyScoresView.put` : vérifie désormais `_can_write_copy()` (assigned_corrector ou admin).
- ✅ `CopyGlobalAppreciationView._update` : idem.
- ✅ `QuestionRemarkListCreateView.create` : idem.
- ✅ `AnnotationListCreateView.create` : idem.
- ⚠️ `ExamStudentListView` : utilise `IsTeacherOrAdmin` — expose les noms d'élèves à tous les correcteurs (acceptable pour la collaboration inter-correcteurs, pas de changement).

---

## 6. Contraintes DB Implicites Non Protégées

| Contrainte manquante | Modèle | Risque | LOT cible |
|---|---|---|---|
| **Unicité Score par Copy** | `Score` | ✅ LOT 8: `UniqueConstraint(fields=['copy'], name='uniq_score_per_copy')` ajouté | Corrigé |
| **Unicité QuestionRemark par (copy, question_id)** | `QuestionRemark` | ✅ Déjà présent: `unique_together = ['copy', 'question_id']` | Résolu |
| Index sur `Copy.status` | `Copy` | ✅ LOT 8: `idx_copy_status` ajouté | Corrigé |
| Index sur `Copy.exam + status` | `Copy` | ✅ LOT 8: `idx_copy_exam_status` ajouté | Corrigé |
| Index sur `Copy.assigned_corrector + status` | `Copy` | ✅ LOT 8: `idx_copy_corrector_status` ajouté | Corrigé |
| Index sur `Annotation.copy + page_index` | `Annotation` | ✅ Déjà présent dans `Meta.indexes` | Résolu |
| Index sur `Score.copy` | `Score` | FK auto-indexé par Django | Résolu |

**LOT 7 — Corrections appliquées** :
- ✅ `CorrectorStatsView` : scores préchargés en bulk (1 query au lieu de N+1). Passés via `scores_by_copy` dict.
- ✅ `StudentCopiesView.list` : scores ET remarks préchargés en bulk (2 queries au lieu de 2N+1).
| **Pas de CHECK constraint** sur `Annotation.x/y/w/h` [0,1] | `Annotation` | Valeurs hors bornes possibles (validé au niveau Python seulement) | LOT 8 |
| **Pas de CHECK constraint** sur `Copy.status` transitions | `Copy` | Toute transition possible au niveau DB | LOT 8 |
| `Booklet.pages_images` JSONField | `Booklet` | Pas de validation de schéma — peut contenir n'importe quoi | LOT 8 |
| `Score.scores_data` JSONField | `Score` | Pas de validation de schéma — clés arbitraires | LOT 8 |

---

## 7. Code Mort / Références Cassées

| Problème | Fichier | Impact |
|---|---|---|
| `GradingService.acquire_lock`, `release_lock`, `heartbeat_lock`, `get_lock_status` **n'existent pas** dans `services.py` | `grading/views_lock.py` les référence | `views_lock.py` va crasher à l'exécution — lock endpoints non fonctionnels |
| `PDFProcessor.import_pdf()` ignore le paramètre `anonymous_id` | `grading/pdf_processor.py:35` | `async_import_pdf` task passe `anonymous_id` mais il est ignoré |
| `TEACHER_GROUPS` hardcodé | `grading/views_my_students.py:17-26` | Mapping correcteur→groupe en dur — pas maintenable |
| `Q_MAX_BY_EXAM` hardcodé | `exams/views.py:651-671` | Barèmes max par question en dur alors que `grading_structure` existe en DB |
| `OLLAMA_MODEL` default `llama3.2:latest` dans le code | `processing/services/llm_summary.py:21` | Production utilise `qwen2.5:32b` via settings — le default est trompeur |

---

## 8. Invariants Métier à Préserver

| # | Invariant | Implémentation actuelle | Risque si violé |
|---|---|---|---|
| INV-1 | Une copie `GRADED` ne doit plus être modifiable (scores, annotations, remarks) | ✅ LOT 5+6: `CopyScoresView.put` vérifie GRADED status (seul superuser override). Annotations check `READY`. | Corrigé |
| INV-2 | Le score total est la somme des `scores_data` values | Calculé dynamiquement par `GradingService.compute_score()` — pas stocké. ✅ LOT 6: validation barème max par question (rejet si > max). | Cohérent |
| INV-3 | Chaque Copy a au maximum 1 Score | **Non garanti** — pas de contrainte `unique` sur `Score.copy` | Doublons possibles |
| INV-4 | Les coordonnées d'annotation sont dans [0,1] | Validé par `AnnotationService.validate_coordinates()` (Python) | PDF mal rendu si hors bornes |
| INV-5 | `page_index` d'annotation est < nombre de pages du booklet | Validé par `AnnotationService.validate_page_index()` (Python) | Annotation orpheline si pages changent |
| INV-6 | Les fichiers dans `Booklet.pages_images` existent sur disque | **Non vérifié** — `PDFFlattener` fait un `continue` si fichier absent | PDF final avec pages manquantes |
| INV-7 | `Annotation.version` incrémenté atomiquement à chaque update | `F('version') + 1` dans `update_annotation()` | Conflits silencieux si non respecté |
| INV-8 | `DraftState` : un seul brouillon actif par (copy, owner) | `get_or_create` + `filter(version=expected)` | Conflit détecté → 409, mais pas de nettoyage |
| INV-9 | `Copy.student` + `Copy.is_identified` cohérents | `CopyIdentificationView` set les deux | Incohérence si `student` set mais `is_identified=False` |
| INV-10 | `Exam.results_released_at` contrôle la visibilité élève | `StudentCopiesView.get_queryset()` filtre `results_released_at__isnull=False` | Si null, copies invisibles aux élèves |
| INV-11 | Fichiers médias (PNG pages, PDF finaux) non supprimés tant que référencés | `cleanup_orphaned_files` ne vérifie que `temp_uploads/` | Sûr pour l'instant, mais fragile |
| INV-12 | `GradingEvent` trace toute action de workflow | Créé dans `add_annotation`, `update_annotation`, `delete_annotation`, `finalize_copy`, `validate_copy` | Audit trail incomplet si un chemin oublie de logger |

---

## 9. Migrations à Risque (futures)

| Migration envisagée | LOT | Risque | Mitigation |
|---|---|---|---|
| Ajouter `UNIQUE(copy_id)` sur `Score` | LOT 8 | Si doublons existent déjà → migration échoue | Audit doublons AVANT migration, fusionner manuellement |
| Ajouter `UNIQUE(copy_id, question_id)` sur `QuestionRemark` | LOT 8 | Idem | Audit doublons AVANT |
| Ajouter CHECK constraint `Annotation.x/y/w/h BETWEEN 0 AND 1` | LOT 8 | Si valeurs hors bornes existent → migration échoue | Audit données existantes AVANT |
| Supprimer `BasicAuthentication` des settings | LOT 3 | Casse `views_async.py` endpoints | Migrer vers `SessionAuthentication` d'abord |
| Modifier enum `Copy.Status` | LOT 4 | Si DB a des valeurs inconnues → incohérence | Vérifier toutes les valeurs en DB AVANT |
| Renommer/déplacer fichiers médias | LOT 2 | Casse les `pages_images` JSON dans `Booklet` | JAMAIS renommer sans mettre à jour la DB |
| Ajouter `X-Accel-Redirect` Nginx | LOT 2 | Casse l'accès aux images si mal configuré | Tester en staging, conserver fallback direct |

---

## 10. Données Production Connues

| Donnée | Valeur | Source |
|---|---|---|
| Examens | BB_J1, BB_J2 | Production DB |
| Copies BB_J1 | 106 | Dernière vérification |
| Copies BB_J2 | 103 | Dernière vérification |
| Total copies | 209 | — |
| Copies avec scores | 151 | Extraction Feb 27 |
| Annotations totales | 611 | Extraction Feb 27 |
| Remarques totales | 1128 | Extraction Feb 27 |
| Appréciations globales | 110 | Extraction Feb 27 |
| Bilans LLM | 42 | Extraction Feb 27 |
| Pages images (PNG) | 3345 fichiers (1.7 GB) | Extraction Feb 27 |
| Backup automatique | Toutes les 30 min, rétention 48 slots (24h) | Cron serveur |

### Copies modifiées manuellement (Feb 23)

5 copies de BB_J1 ont eu leur PDF source remplacé manuellement :
- GHORBAL_SOPHIE : 17→13 pages — **annotations potentiellement décalées**
- GRATI_MEHDI : 9→13 pages — **annotations potentiellement décalées**
- CHIHAOUI_INES, KAMMOUN_AYMAR, TRABELSI_ABDERRAHMANE : pages count inchangé ou mineur

**Action LOT 6** : Vérifier la cohérence `Annotation.page_index` vs nombre réel de pages pour ces 5 copies.

---

## 11. Résumé des Risques par Sévérité

### CRITIQUE (bloquant pour LOTs suivants)

1. ~~**INV-1 violable**~~ ✅ LOT 5+6: `CopyScoresView.put` vérifie GRADED + `_can_write_copy()`. Annotations check `READY`.
2. ~~**`cancel_task` sans auth**~~ ✅ LOT 3: Protégé par `SessionAuthentication` + `IsAuthenticated`.
3. ~~**Lock endpoints cassés**~~ ✅ LOT 4: `acquire_lock`, `release_lock`, `heartbeat_lock`, `get_lock_status` implémentés dans `GradingService`.
4. ~~**INV-3**~~ ✅ LOT 8: `UniqueConstraint(fields=['copy'], name='uniq_score_per_copy')` ajouté sur `Score`.

### ÉLEVÉ

5. ~~**BasicAuth en production**~~ ✅ LOT 3: Supprimée de `DEFAULT_AUTHENTICATION_CLASSES`.
6. ~~**Médias non protégés**~~ ✅ LOT 2: `ProtectedMediaView` + `X-Accel-Redirect` Nginx.
7. **Hard delete annotations** : Pas de soft delete ni historique (risque accepté — audit via `GradingEvent`).
8. **`cleanup_orphaned_files` fragile** : Pas de vérification des références DB.

### MOYEN

9. **TEACHER_GROUPS / Q_MAX_BY_EXAM hardcodés** : Maintenance manuelle, divergence possible.
10. ~~**Pas de validation JSONField**~~ ✅ LOT 6: Validation barème max par question dans `CopyScoresView.put`.
11. **`process_single_document` non idempotent** : Delete-then-create risque perte si crash entre les deux.
12. **Annotations décalées** sur 2 copies après remplacement PDF (GHORBAL, GRATI).

### FAIBLE

13. **`PDFProcessor.import_pdf` ignore `anonymous_id`** : Bug cosmétique.
14. **OLLAMA_MODEL default trompeur** : `llama3.2` en code vs `qwen2.5:32b` en prod.

### LOT 9 RGPD — Corrections appliquées

- ✅ Tâche Celery Beat `cleanup_expired_locks` : nettoyage des verrous expirés toutes les 5 min.
- ✅ Tâche Celery Beat `purge_old_audit_logs` : purge des `AuditLog` > 365 jours, quotidienne à 03h00.
- ✅ `AuditLog` modèle existant avec IP, user-agent, metadata — conforme RGPD/CNIL.

---

## 12. Checklist Pré-Correction

Avant de commencer LOT 2+, vérifier :

- [ ] Backup DB complète effectuée et testée (restore dry-run)
- [ ] Snapshot des 209 copies `scores_data` exporté en JSON
- [ ] Vérifier qu'aucun doublon `Score` n'existe (query : `SELECT copy_id, COUNT(*) FROM grading_score GROUP BY copy_id HAVING COUNT(*) > 1`)
- [ ] Vérifier qu'aucun doublon `QuestionRemark` n'existe (query : `SELECT copy_id, question_id, COUNT(*) FROM grading_questionremark GROUP BY copy_id, question_id HAVING COUNT(*) > 1`)
- [ ] Vérifier que toutes les `Annotation.page_index` sont dans les bornes du booklet associé
- [ ] Vérifier que tous les fichiers dans `Booklet.pages_images` existent sur disque
- [ ] Documenter le nombre exact de lignes par table critique avant toute migration

---

*Ce document est la référence pour tous les LOTs suivants. Aucune correction ne doit commencer sans avoir consulté les risques et invariants ci-dessus.*
