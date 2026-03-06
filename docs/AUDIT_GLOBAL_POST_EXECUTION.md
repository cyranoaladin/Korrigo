# Audit Global Post-Exécution — Korrigo LOTs 3-11

**Date** : 6 mars 2026  
**Auditeur** : Cascade (auto-audit sévère)  
**Critère principal** : Préservation de l'intégrité des données existantes  
**Niveau d'exigence** : Maximal — aucune complaisance

---

## 1. Résumé Exécutif

### Ce qui a été réellement corrigé
- **BasicAuthentication supprimé** de la config DRF globale (`core/settings.py`).
- **Endpoints async `task_status`/`cancel_task`** fermés aux anonymes (SessionAuth + IsAuthenticated).
- **4 endpoints d'écriture** protégés par `_can_write_copy` : `AnnotationListCreateView.create`, `QuestionRemarkListCreateView.create`, `CopyGlobalAppreciationView._update`, `CopyScoresView.put`.
- **Retry Celery** restauré sur `async_finalize_copy` (les transient errors déclenchent `self.retry(exc=exc)` au lieu d'être avalées).
- **4 méthodes lock service** implémentées dans `GradingService` (`acquire_lock`, `release_lock`, `heartbeat_lock`, `get_lock_status`).
- **`CopyScoresView.put`** wrappé dans `transaction.atomic`.
- **Validation barème** sur `CopyScoresView.put` — rejet si score > max par question (pour BB_J1 et BB_J2 uniquement).
- **N+1 corrigés** dans `CorrectorStatsView` et `StudentCopiesView.list`.
- **Celery Beat** enrichi : `cleanup_expired_locks` (5min), `purge_old_audit_logs` (daily 03:00).
- **`UniqueConstraint`** déclarée sur `Score.copy` et **3 index** déclarés sur `Copy` dans les modèles.
- **Frontend** : `StatsReport.vue` découpé en 3 sub-components, `v-show` → `v-if`, dead code nettoyé.
- **Documentation** : guide de sortie overlay (`docs/LOT11-overlay-exit.md`).

### Ce qui est partiellement corrigé
- **Permissions écriture LOT 5** : 4 endpoints protégés sur 8 concernés. `AnnotationDetailView.update/destroy`, `QuestionRemarkDetailView.update/destroy`, `DraftReturnView`, `CopyReadyView/CopyFinalizeView` ne sont PAS protégés par `_can_write_copy`.
- **Atomicité LOT 4** : `CopyScoresView.put` est dans un `atomic`, mais sans `select_for_update` → race condition toujours possible. `CopyGlobalAppreciationView._update` et `QuestionRemarkListCreateView.create` n'ont aucun `atomic`.
- **Validation barème LOT 6** : fonctionne pour BB_J1 et BB_J2 (hardcodés), mais tout futur examen est silencieusement ignoré. Validation dans la vue, pas dans le service layer.

### Ce qui n'a PAS été corrigé
- **Aucune migration DB générée** — la `UniqueConstraint` sur `Score.copy` et les 3 index sur `Copy` n'existent qu'en Python. **La DB de production n'est pas protégée.**
- **Aucun test ajouté ou modifié** pour couvrir les changements LOT 3-11.
- **`AnnotationDetailView` et `QuestionRemarkDetailView`** utilisent un attribut `role` inexistant sur le modèle User → logique de permission cassée.

### Ce qui reste risqué
- **Race condition** sur l'écriture de scores (2 PUT simultanés → lost update).
- **Migration LOT 8** potentiellement destructive si des doublons Score existent en DB.
- **`cancel_task`** accessible à tout utilisateur authentifié (y compris élèves) pour annuler n'importe quel task Celery.
- **Régression frontend LOT 10** : `ClipboardList` utilisé dans `StatsReport.vue:589` mais absent des imports (supprimé lors du cleanup).
- **Pattern overlay toujours actif** en production — divergence local/serveur inévitable.

---

## 2. Tableau « Exigence Initiale → État Réel »

| # | Exigence | Statut | Fichiers touchés | Justification technique |
|---|----------|--------|------------------|------------------------|
| **LOT 3a** | Supprimer BasicAuthentication de la config globale | ✅ Corrigé | `core/settings.py:159-162` | `BasicAuthentication` retiré de `DEFAULT_AUTHENTICATION_CLASSES`. Seul `SessionAuthentication` reste. Vérifié : aucune autre occurrence de `BasicAuthentication` dans le code applicatif (hors venv). |
| **LOT 3b** | Fermer `task_status` et `cancel_task` | ⚠️ Partiel | `grading/views_async.py:5-17,101-103` | Auth fermée (SessionAuth + IsAuthenticated). **Mais** : aucun contrôle d'**autorisation** (ownership de la task). Un élève authentifié peut annuler le task d'un correcteur si le task_id est connu. `terminate=True` kill le worker, pas seulement la task. |
| **LOT 4a** | Atomicité `CopyScoresView.put` | ⚠️ Partiel | `grading/views.py:527-536` | `transaction.atomic()` wrapping le `update_or_create` + `GradingEvent`. **Mais** : pas de `select_for_update` → race condition sur lecture-écriture. Le `atomic` empêche les partial writes, pas les lost updates. |
| **LOT 4b** | Retry Celery sur `async_finalize_copy` | ✅ Corrigé | `grading/tasks.py:92-100` | `ValueError`/`LockConflictError` → error dict (non-retryable). Toute autre exception → `self.retry(exc=exc)` avec `max_retries=3, default_retry_delay=60`. |
| **LOT 4c** | Implémenter les méthodes lock manquantes | ✅ Corrigé | `grading/services.py:421-572` | 4 méthodes statiques avec `@transaction.atomic` et `select_for_update`. Gèrent: création, renouvellement, takeover de lock expiré, release avec vérification token, heartbeat, status avec cleanup expired. Cohérent avec `views_lock.py`. |
| **LOT 5a** | Vérifier `assigned_corrector` sur les endpoints d'écriture | ⚠️ Partiel | `grading/views.py:33-42,90,315,422,474` | `_can_write_copy` créée et appliquée à 4 endpoints. **Manquant** : `AnnotationDetailView.update/destroy` (lignes 119-152), `QuestionRemarkDetailView.update/destroy` (lignes 365-395), `DraftReturnView` (tout le fichier), `CopyReadyView`, `CopyFinalizeView`. |
| **LOT 5b** | Bug `getattr(user, 'role', '')` | ❌ Non corrigé | `grading/views.py:122,142,369,387` | L'attribut `role` n'existe PAS sur le modèle User Django. `getattr(request.user, 'role', '')` retourne toujours `''`, donc `!= 'Admin'` est toujours True. Le check est cassé depuis le début et n'a pas été corrigé par le LOT 5. |
| **LOT 6** | Validation barème max par question | ⚠️ Partiel | `grading/views.py:510-525`, `exams/views.py:651-671` | Fonctionne pour BB_J1 (33 questions) et BB_J2 (27 questions). **Problèmes** : (1) `Q_MAX_BY_EXAM` est un dictionnaire hardcodé, pas dérivé de `exam.grading_structure` en DB ; (2) tout examen absent du dict → aucune validation ; (3) validation dans la vue, pas dans `GradingService` → les scripts ORM bypass ; (4) import circulaire fragile (`from exams.views import StudentCopiesView`). |
| **LOT 7a** | Fix N+1 dans `CorrectorStatsView` | ✅ Corrigé | `grading/views.py:584-588,629-665` | Prefetch de tous les `Score` via un seul query, stockés dans `scores_by_copy` dict, passé à `_get_scores_for_copies` et `_compute_group_stats`. Fallback N+1 conservé si dict est None (dead code path). |
| **LOT 7b** | Fix N+1 dans `StudentCopiesView.list` | ✅ Corrigé | `exams/views.py:702-714` | Bulk prefetch `Score.objects.filter(copy_id__in=copy_ids)` et `QuestionRemark.objects.filter(copy_id__in=copy_ids)`. N+1 résiduel possible sur `copy.exam.name/date` (pas de `select_related('exam')` vérifié). |
| **LOT 8a** | UniqueConstraint sur `Score.copy` | ❌ Non appliqué | `grading/models.py:329-332` | Déclaré dans le modèle Python (`UniqueConstraint(fields=['copy'], name='uniq_score_per_copy')`). **Aucune migration générée.** Dernière migration : `0012_annotation_bank_and_documents.py`. La contrainte **n'existe pas en DB**. |
| **LOT 8b** | Index sur `Copy` (status, exam+status, corrector+status) | ❌ Non appliqué | `exams/models.py:327-331` | 3 index déclarés dans le modèle Python. **Aucune migration générée.** Dernière migration : `0022_copy_llm_summary.py`. Les index **n'existent pas en DB**. |
| **LOT 9a** | Tâche Celery nettoyage locks | ✅ Corrigé | `grading/tasks.py:212-228`, `core/celery.py:25-28` | `cleanup_expired_locks` : supprime les `CopyLock` avec `expires_at <= now`. Enregistré dans Beat : every 300s. |
| **LOT 9b** | Tâche Celery purge audit logs | ✅ Corrigé | `grading/tasks.py:231-248`, `core/celery.py:30-34` | `purge_old_audit_logs` : supprime les `AuditLog` avec `timestamp < now - 365 jours`. Enregistré dans Beat : `crontab(hour=3, minute=0)`. **Risque** : suppression bulk sans pagination → lock DB long si millions de rows. |
| **LOT 10** | Frontend stats refactoring | ⚠️ Partiel (régression) | `StatsReport.vue`, 3 sub-components | 3 sub-components extraits, `v-show` → `v-if`, dead code nettoyé. **Régression** : `ClipboardList` supprimé des imports mais encore utilisé ligne 589 → crash runtime sur onglet QCM. |
| **LOT 11** | Documentation overlay exit | ✅ Corrigé | `docs/LOT11-overlay-exit.md` | Guide de migration 5 phases, checklist validation, rollback. Documentation uniquement. |

---

## 3. Impacts Potentiels sur les Données Existantes

### 3.1 Notes globales (total_score calculé)
- **Touché** : NON directement. Le calcul `total_score = sum(scores_data.values())` n'a pas été modifié.
- **Risque** : AUCUN. Les notes sont calculées à la volée dans `StudentCopiesView.list` et `CorrectorStatsView`, pas stockées.
- **Garanties** : Code de calcul inchangé.
- **Test existant** : Aucun test dédié.
- **Test manquant** : Test vérifiant que `sum(scores_data.values())` produit le même résultat avant/après.
- **Risque résiduel** : Nul.

### 3.2 Notes par question (scores_data JSONField)
- **Touché** : OUI — `CopyScoresView.put` modifié (validation ajoutée + atomic wrapper).
- **Risque** : FAIBLE. Les modifications n'impactent que l'écriture de nouvelles données, pas la lecture. La validation barème rejette les scores invalides mais n'altère pas les existants.
- **Garanties** : (1) `update_or_create` inchangé ; (2) validation rejet-seulement (jamais de modification silencieuse) ; (3) les données passent par `float()` conversion comme avant.
- **Test existant** : Aucun test spécifique à la validation barème.
- **Test manquant** : Test que des `scores_data` valides sont acceptés, que des overflow sont rejetés, que des scores existants ne sont pas altérés.
- **Risque résiduel** : **MOYEN** — race condition (R4-1) : deux PUT simultanés → le dernier écrase le premier sans avertissement.

### 3.3 scores_data (Score model, JSONField)
- **Touché** : OUI — contrainte d'unicité déclarée mais non appliquée.
- **Risque** : **ÉLEVÉ si migration appliquée avec doublons existants** → `IntegrityError` qui bloque toute migration future.
- **Garanties** : Le `update_or_create(copy=copy)` dans `CopyScoresView.put` empêche la création de doublons via API. Mais les scripts ORM (recovery Laroussi, etc.) pourraient avoir créé des doublons.
- **Test existant** : Aucun.
- **Test manquant** : Query de vérification pré-migration : `SELECT copy_id, COUNT(*) FROM grading_score GROUP BY copy_id HAVING COUNT(*) > 1`.
- **Risque résiduel** : **CRITIQUE tant que la migration n'est pas vérifiée et appliquée.**

### 3.4 grading_structure (Exam.grading_structure JSONField)
- **Touché** : NON. Aucune modification de `ExamSerializer` ni du modèle `Exam`.
- **Risque** : AUCUN direct. **Mais** : `Q_MAX_BY_EXAM` hardcodé est découplé de `grading_structure` → risque de dérive si `grading_structure` est modifié sans mise à jour du dict.
- **Test manquant** : Test que `Q_MAX_BY_EXAM` correspond exactement à `grading_structure` en DB.
- **Risque résiduel** : FAIBLE (les 2 examens existants sont stables).

### 3.5 Annotations
- **Touché** : OUI — `AnnotationListCreateView.create` protégé par `_can_write_copy`.
- **Risque** : FAIBLE pour les données existantes (lecture non modifiée).
- **Garanties** : Le check `_can_write_copy` est rejet-seulement, jamais de modification.
- **Test existant** : Aucun test pour le check `_can_write_copy`.
- **Test manquant** : Test qu'un correcteur non-assigné est rejeté en 403, qu'un admin passe, que le correcteur assigné passe.
- **Risque résiduel** : **ÉLEVÉ** — `AnnotationDetailView.update/destroy` (PATCH/DELETE) ne vérifie PAS `_can_write_copy`. Le check `getattr(user, 'role', '')` est cassé (attribut inexistant). Un correcteur avec `IsTeacherOrAdmin` peut modifier/supprimer n'importe quelle annotation s'il est le `created_by`.

### 3.6 Appréciations (Copy.global_appreciation TextField)
- **Touché** : OUI — `CopyGlobalAppreciationView._update` protégé par `_can_write_copy`.
- **Risque** : FAIBLE. Le `save(update_fields=['global_appreciation'])` est ciblé.
- **Garanties** : Seul le champ `global_appreciation` est modifié, jamais d'autres champs.
- **Test existant** : Aucun.
- **Test manquant** : Test de permission + test que seul `global_appreciation` est modifié.
- **Risque résiduel** : FAIBLE — pas d'`atomic`, le `GradingEvent` peut échouer silencieusement (perte d'audit trail, pas de perte de données).

### 3.7 Remarques (QuestionRemark)
- **Touché** : OUI — `QuestionRemarkListCreateView.create` protégé par `_can_write_copy`.
- **Risque** : FAIBLE pour les données existantes.
- **Garanties** : `update_or_create` avec `unique_together = ['copy', 'question_id']` empêche les doublons.
- **Test existant** : Aucun.
- **Risque résiduel** : **ÉLEVÉ** — `QuestionRemarkDetailView.update/destroy` a le même bug `role` que `AnnotationDetailView`.

### 3.8 PDFs finaux (Copy.final_pdf FileField)
- **Touché** : NON directement par les LOTs 3-11. Aucune modification de `GradingService.finalize_copy`, `pdf_flattener.py`, ou `llm_summary.py`.
- **Risque** : AUCUN direct.
- **Risque résiduel** : FAIBLE — `cancel_task` peut annuler un `async_finalize_copy` en cours, potentiellement laissant une copie en état `GRADING_IN_PROGRESS` sans PDF final. Le retry Celery relancera, mais si le cancel arrive après la génération PDF mais avant le save → état incohérent.

### 3.9 Scans sources (Booklet.pages_images, Copy.pdf_source)
- **Touché** : NON. Aucune modification des modèles de scan ou d'import.
- **Risque** : AUCUN.
- **Risque résiduel** : Nul.

### 3.10 Copies (Copy model)
- **Touché** : OUI — 3 index déclarés sur `Copy.Meta.indexes` (non appliqués en DB).
- **Risque** : AUCUN pour les données existantes (les index sont additifs, jamais destructifs).
- **Risque résiduel** : FAIBLE — les index n'existent pas en DB, donc aucun gain de performance effectif.

### 3.11 Exam (Exam model)
- **Touché** : NON. Aucune modification du modèle `Exam`.
- **Risque** : AUCUN.
- **Risque résiduel** : Nul.

### 3.12 Score (Score model)
- **Touché** : OUI — `UniqueConstraint` déclarée sur `copy`, non appliquée en DB.
- **Risque** : Aucun pour les données existantes (la contrainte est additive). **MAIS** : si des doublons existent et qu'on tente `makemigrations` + `migrate`, l'`IntegrityError` bloquera.
- **Risque résiduel** : **CRITIQUE** — nécessite vérification pré-migration.

### 3.13 DraftState
- **Touché** : NON directement. `DraftReturnView` n'a pas été modifié par les LOTs.
- **Risque** : AUCUN pour les données existantes.
- **Risque résiduel** : MOYEN — pas de check `_can_write_copy`, un correcteur peut sauvegarder un draft sur une copie non-assignée.

### 3.14 GradingEvent
- **Touché** : OUI — de nouveaux `GradingEvent` sont créés par le lock service (`LOCK`, `UNLOCK`). Les events existants ne sont pas modifiés.
- **Risque** : AUCUN pour les données existantes (ajout seulement).
- **Risque résiduel** : FAIBLE — les `try: GradingEvent.objects.create() except: logger.warning()` dans les vues avalent silencieusement les erreurs de création d'events → perte de traçabilité sans erreur visible.

### 3.15 AuditLog
- **Touché** : OUI — `purge_old_audit_logs` supprime les entrées > 365 jours.
- **Risque** : AUCUN pour les données récentes (la plateforme a ~2 mois).
- **Risque résiduel** : MOYEN à long terme — suppression bulk sans pagination → potential lock DB.

### 3.16 Liens élève / copie / examen / correcteur
- **Touché** : NON. Aucune modification des FK `Copy.student`, `Copy.exam`, `Copy.assigned_corrector`, `Exam.correctors` M2M.
- **Risque** : AUCUN.
- **Risque résiduel** : Nul.

---

## 4. Liste Exhaustive des Fichiers Modifiés

### Backend

| Fichier | LOT | Modifications |
|---------|-----|---------------|
| `backend/core/settings.py` | 3 | Suppression `BasicAuthentication` de `DEFAULT_AUTHENTICATION_CLASSES` |
| `backend/core/celery.py` | 9 | Ajout 2 tâches Beat : `cleanup-expired-locks`, `purge-old-audit-logs` |
| `backend/grading/views_async.py` | 3 | `SessionAuthentication` + `IsAuthenticated` sur `task_status` et `cancel_task` |
| `backend/grading/views.py` | 4,5,6,7 | `_can_write_copy()` helper, permission checks sur 4 endpoints, `transaction.atomic` sur scores, validation barème, prefetch N+1 `CorrectorStatsView` |
| `backend/grading/services.py` | 4 | 4 méthodes lock service : `acquire_lock`, `release_lock`, `heartbeat_lock`, `get_lock_status` |
| `backend/grading/tasks.py` | 4,9 | `self.retry(exc=exc)` sur `async_finalize_copy`, 2 nouvelles tâches (`cleanup_expired_locks`, `purge_old_audit_logs`) |
| `backend/grading/models.py` | 8 | `UniqueConstraint(fields=['copy'], name='uniq_score_per_copy')` sur `Score.Meta` |
| `backend/exams/models.py` | 8 | 3 index dans `Copy.Meta.indexes` |
| `backend/exams/views.py` | 7 | Prefetch bulk `Score` + `QuestionRemark` dans `StudentCopiesView.list` |

### Frontend

| Fichier | LOT | Modifications |
|---------|-----|---------------|
| `frontend/src/views/StatsReport.vue` | 10 | 3 tabs extraits en components, `v-show` → `v-if`, dead code supprimé, imports nettoyés. **BUG** : `ClipboardList` supprimé des imports mais utilisé ligne 589. |
| `frontend/src/components/stats/StatsQcmTab.vue` | 10 | Nouveau fichier — tab QCM 5/5 extrait |
| `frontend/src/components/stats/StatsPalmaresTab.vue` | 10 | Nouveau fichier — tab Palmarès extrait |
| `frontend/src/components/stats/StatsQualityTab.vue` | 10 | Nouveau fichier — tab Correction/Qualité extrait |

### Infra

| Fichier | LOT | Modifications |
|---------|-----|---------------|
| *(aucun)* | — | Aucune modification infra (docker-compose, nginx, Dockerfile) |

### Tests

| Fichier | LOT | Modifications |
|---------|-----|---------------|
| *(aucun)* | — | **Aucun test ajouté ou modifié** |

### Docs

| Fichier | LOT | Modifications |
|---------|-----|---------------|
| `docs/data-integrity-audit.md` | 3-9 | Mises à jour des sections reflétant les fixes appliqués |
| `docs/LOT11-overlay-exit.md` | 11 | Nouveau — guide migration overlay → image Docker |
| `docs/audit-post-execution-LOT3-11.md` | — | Nouveau — premier rapport d'audit post-exécution |

### Migrations

| Fichier | LOT | Modifications |
|---------|-----|---------------|
| *(aucun)* | — | **Aucune migration générée** |

---

## 5. Migrations Introduites

**AUCUNE MIGRATION N'A ÉTÉ GÉNÉRÉE.**

Deux changements de modèle requièrent des migrations :

| Changement | App | Table | Type | Risque | Destructif | Réversible | Prérequis |
|------------|-----|-------|------|--------|------------|------------|-----------|
| `UniqueConstraint(fields=['copy'], name='uniq_score_per_copy')` | grading | `grading_score` | Contrainte d'unicité | **ÉLEVÉ** | **OUI si doublons** — la migration échouera avec `IntegrityError` | OUI — `RemoveConstraint` | Vérifier absence de doublons : `SELECT copy_id, COUNT(*) FROM grading_score GROUP BY copy_id HAVING COUNT(*) > 1` |
| 3 index sur `Copy` | exams | `exams_copy` | Index additifs | FAIBLE | NON | OUI — `RemoveIndex` | Aucun |

**Conséquence** : les protections promises par le LOT 8 sont **inexistantes en production**. La DB accepte toujours des doublons de Score par Copy et n'a pas les index de performance.

**Dernières migrations existantes** :
- `grading/migrations/0012_annotation_bank_and_documents.py`
- `exams/migrations/0022_copy_llm_summary.py`

**Action requise** : `python manage.py makemigrations grading exams --name lot8_constraints_indexes` puis vérification doublons puis `python manage.py migrate`.

---

## 6. Tests Ajoutés ou Modifiés

**AUCUN.**

C'est le constat le plus critique de cet audit. Les 51 fichiers de test existants dans le repository n'ont pas été modifiés. Aucun test de régression ne couvre les changements des LOTs 3-11.

### Tests qui auraient dû être ajoutés

| Test manquant | Objectif | Ce qu'il prouverait | Priorité |
|---------------|----------|---------------------|----------|
| `test_basicauth_removed` | Vérifier qu'un appel avec BasicAuth est rejeté | Que LOT 3 fonctionne | HAUTE |
| `test_task_status_requires_auth` | Vérifier que `/api/grading/tasks/<id>/` retourne 401 sans auth | Que LOT 3 fonctionne | HAUTE |
| `test_cancel_task_requires_auth` | Idem pour POST cancel | Idem | HAUTE |
| `test_score_put_requires_assigned_corrector` | Vérifier qu'un correcteur non-assigné est rejeté en 403 | Que LOT 5 fonctionne | HAUTE |
| `test_annotation_create_requires_assigned_corrector` | Idem pour POST annotation | Idem | HAUTE |
| `test_score_overflow_rejected` | Vérifier qu'un score > barème max est rejeté en 400 | Que LOT 6 fonctionne | HAUTE |
| `test_score_unique_constraint` | Vérifier qu'on ne peut pas créer 2 Score pour 1 Copy | Que LOT 8 fonctionne | HAUTE (après migration) |
| `test_cleanup_expired_locks` | Vérifier que les locks expirés sont supprimés | Que LOT 9 fonctionne | MOYENNE |
| `test_purge_old_audit_logs` | Vérifier la purge RGPD | Que LOT 9 fonctionne | MOYENNE |
| `test_lock_acquire_release_heartbeat` | Vérifier le cycle de vie du lock | Que LOT 4 lock service fonctionne | HAUTE |

---

## 7. Risques Résiduels

### 7.1 Risques de Sécurité

| # | Risque | Sévérité | Détail |
|---|--------|----------|--------|
| SEC-1 | `cancel_task` sans vérification ownership | **ÉLEVÉ** | N'importe quel user authentifié (y compris un élève via session) peut annuler n'importe quel task Celery. `terminate=True` + `SIGTERM` tue le worker process, potentiellement affectant d'autres tasks. |
| SEC-2 | `AnnotationDetailView` check permission cassé | **ÉLEVÉ** | `getattr(request.user, 'role', '')` retourne toujours `''` → le check `!= 'Admin'` est toujours True → seul `is_superuser` bypass. Un correcteur Teacher peut modifier les annotations d'un autre correcteur s'il est le `created_by`. Mais il ne peut pas modifier des annotations créées par autrui (check `created_by != request.user`). |
| SEC-3 | `QuestionRemarkDetailView` check permission cassé | **ÉLEVÉ** | Même pattern cassé que SEC-2. |
| SEC-4 | `DraftReturnView` sans check d'assignation | MOYEN | `IsAuthenticated` seul → un correcteur peut lire/écrire le draft d'une copie non-assignée. |

### 7.2 Risques de Permissions

| # | Risque | Sévérité | Détail |
|---|--------|----------|--------|
| PERM-1 | `_can_write_copy` : `is_staff` trop large | FAIBLE | Tout `is_staff=True` est traité comme admin. Si un utilisateur est `is_staff` sans être dans le groupe `admin`, il bypass les checks. |
| PERM-2 | `CopyReadyView/CopyFinalizeView` sans check assignation | MOYEN | N'importe quel Teacher peut finaliser la copie d'un collègue. |
| PERM-3 | Pas de `_can_write_copy` sur `AnnotationDetailView.update/destroy` | **ÉLEVÉ** | Un Teacher peut PATCH/DELETE n'importe quelle annotation dont il est le `created_by`, même si la copie a été réassignée. |

### 7.3 Risques de Performance

| # | Risque | Sévérité | Détail |
|---|--------|----------|--------|
| PERF-1 | `purge_old_audit_logs` bulk delete | MOYEN | Pas de pagination. Si des millions d'AuditLog accumulent, le DELETE verrouillera la table. |
| PERF-2 | Index Copy non appliqués | FAIBLE | Les 3 index déclarés dans le modèle ne sont pas en DB. Queries `Copy.objects.filter(status=X)` restent non-indexées. Impact faible avec 209 copies. |
| PERF-3 | N+1 résiduel `copy.exam` dans `StudentCopiesView.list` | FAIBLE | `copy.exam.name` et `copy.exam.date` sans `select_related('exam')` vérifié sur le queryset de base. |

### 7.4 Risques de Corruption de Données

| # | Risque | Sévérité | Détail |
|---|--------|----------|--------|
| DATA-1 | Race condition `CopyScoresView.put` | **ÉLEVÉ** | Deux PUT simultanés : les deux passent la validation, le dernier `update_or_create` écrase le premier. L'`atomic` ne protège PAS contre ça — il faut `select_for_update`. Scénario : admin modifie en même temps que le correcteur assigné. |
| DATA-2 | `cancel_task` pendant finalisation | MOYEN | Si un task est cancelled entre la génération PDF et le `copy.save()` → copie en état `GRADING_IN_PROGRESS` sans PDF, bloquée. |
| DATA-3 | Migration LOT 8 avec doublons | **CRITIQUE** | Si des doublons Score existent, `migrate` crash et bloque toute migration future jusqu'à résolution manuelle. |
| DATA-4 | Scripts ORM bypass validation barème | MOYEN | `Q_MAX_BY_EXAM` n'est vérifié que dans `CopyScoresView.put`. Tout script utilisant `Score.objects.create()` ou `update()` directement peut écrire des scores > barème max. L'incident Laroussi se serait produit même avec LOT 6. |

### 7.5 Risques Infra / Déploiement

| # | Risque | Sévérité | Détail |
|---|--------|----------|--------|
| INFRA-1 | Pattern overlay toujours actif | **ÉLEVÉ** | Les 59 fichiers sont montés via volumes. Les modifications LOT 3-11 ne sont dans le repo local que. **Rien n'a été déployé sur le serveur.** Il faut soit déployer via overlay, soit exécuter le plan LOT 11. |
| INFRA-2 | Celery Beat schedule modifié mais pas déployé | MOYEN | Les 2 nouvelles tâches Beat (locks cleanup, audit purge) ne s'exécuteront que quand le `core/celery.py` modifié sera déployé et le Beat worker redémarré. |
| INFRA-3 | `cleanup_orphaned_files` non enregistré dans Beat | FAIBLE | La tâche `cleanup_orphaned_files` (lignes 174-209 de `tasks.py`) existe mais n'est PAS dans `beat_schedule`. Le nettoyage des fichiers temp ne se fait jamais automatiquement. |

### 7.6 Risques de Divergence Code / Production

| # | Risque | Sévérité | Détail |
|---|--------|----------|--------|
| DIV-1 | LOTs 3-11 non déployés | **CRITIQUE** | Toutes les modifications sont dans le repo local uniquement. Le serveur de production tourne encore le code pré-LOT. Aucune des protections n'est active en production. |
| DIV-2 | Migrations non générées | **ÉLEVÉ** | Même si le code est déployé, la DB ne reflète pas les changements de modèle LOT 8. |
| DIV-3 | Frontend non buildé/déployé | MOYEN | Les modifications Vue.js ne sont pas buildées (`npx vite build`) ni déployées sur nginx. La régression `ClipboardList` n'est pas visible en prod (l'ancien code y tourne). |

---

## 8. Verdict Final

### État global

Les LOTs 3-11 constituent un **travail de code correct dans son intention mais incomplet dans son exécution**. Sur les 11 exigences principales :
- **6 sont correctement implémentées** dans le code local (BasicAuth, retry Celery, lock service, N+1 fixes, Celery Beat tasks, documentation).
- **4 sont partiellement implémentées** (permissions écriture, atomicité, validation barème, frontend refactoring).
- **1 est déclarée mais non appliquée** (contraintes DB LOT 8 — aucune migration).

**Aucune des modifications n'est déployée en production.** Le serveur tourne l'ancien code.

### Niveau de confiance

| Aspect | Confiance | Justification |
|--------|-----------|---------------|
| Aucune donnée existante corrompue par les changements | **ÉLEVÉE** | Tous les changements sont additifs (ajout de checks, de validations, de contraintes). Aucun changement ne modifie, supprime ou déplace des données existantes. |
| Les nouvelles protections fonctionnent correctement | **FAIBLE** | Aucun test automatisé. Logique `role` cassée dans 2 vues critiques. Race condition non résolue. |
| Le déploiement sera sans risque | **FAIBLE** | Migration LOT 8 potentiellement bloquante. Régression frontend ClipboardList. 59 fichiers overlay à synchroniser. |

### Vérifications manuelles encore indispensables

1. **AVANT toute migration** : Exécuter sur le serveur :
   ```sql
   SELECT copy_id, COUNT(*) FROM grading_score GROUP BY copy_id HAVING COUNT(*) > 1;
   ```
   Si résultat non vide → data migration de déduplication AVANT la contrainte d'unicité.

2. **AVANT déploiement frontend** : Corriger le bug `ClipboardList` (ajouter l'import manquant dans `StatsReport.vue`).

3. **APRÈS déploiement backend** :
   - Vérifier que `GET /api/exams/stats-report/` retourne les mêmes données qu'avant.
   - Vérifier que chaque correcteur voit toujours ses copies assignées.
   - Vérifier que les élèves voient toujours leurs bulletins.
   - Tester manuellement : sauvegarder un score, une annotation, une remarque, une appréciation.
   - Vérifier les logs Celery Beat pour les 2 nouvelles tâches.

4. **Tests de non-régression critiques** à exécuter manuellement :
   - `curl -u admin:admin https://korrigo.labomaths.tn/api/copies/` → doit retourner 401 (BasicAuth supprimé).
   - Login normal via session → doit fonctionner.
   - PUT scores avec valeur > barème max → doit retourner 400.
   - PUT scores par correcteur non-assigné → doit retourner 403.

### Conclusion sévère

Le travail effectué améliore la posture de sécurité et la robustesse du code **en théorie**. En pratique :
- **0% est actif en production** (rien déployé).
- **0 test** ne prouve que les protections fonctionnent.
- **2 régressions** introduites (ClipboardList, check `role` non corrigé).
- **1 bombe à retardement** (migration LOT 8 sans vérification doublons).
- **La protection la plus critique** (unicité Score par Copy) **n'existe qu'en Python, pas en DB**.

Le code est dans un état déployable **sous réserve** de : corriger le bug ClipboardList, vérifier les doublons Score, générer les migrations, et déployer l'ensemble (overlay ou image Docker selon LOT 11).
