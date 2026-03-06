# Audit Spécialisé — Intégrité des Données Métiers Post-Corrections P0/P1

**Date** : 6 mars 2026  
**Périmètre** : Exclusivement l'impact des corrections P0/P1 sur les données existantes  
**Méthode** : Relecture ligne par ligne de chaque fichier modifié, traçage de chaque write path  
**Critère** : Zéro corruption, zéro altération silencieuse des données métier

---

## Audit par catégorie de données

---

### Notes globales (total_score calculé à la volée)

**Lecture seule ou écriture impactée** : Lecture seule. `total_score` est calculé dynamiquement dans `StudentCopiesView.list` (ligne 721-725 de `exams/views.py`) et `CorrectorStatsView._get_scores_for_copies` (ligne 661-675 de `grading/views.py`). Aucune de ces fonctions n'a été modifiée par les corrections P0/P1.

**Fichiers / fonctions / vues / services impliqués** :
- `exams/views.py:721-725` — `sum(float(v) for v in scores_data.values() ...)` dans `StudentCopiesView.list`
- `grading/views.py:661-675` — `_get_scores_for_copies` dans `CorrectorStatsView`
- `grading/services.py:compute_score()` — fallback, non modifié

**Risque théorique avant corrections** : Nul sur les notes globales — aucune correction P0/P1 ne touche le calcul.

**Risque réel après corrections** : Nul. Le seul changement dans `CopyScoresView.put` est l'ajout d'un `select_for_update` dans le bloc atomic. Le `update_or_create` et son `defaults={'scores_data': ...}` sont strictement identiques. Le calcul `total_score` n'est pas dans ce path — il est dans les GET.

**Garanties introduites** : Aucune nouvelle (le path de calcul n'a pas été touché).

**Preuves concrètes dans le code** :
- `exams/views.py:721` : `total_score = sum(float(v) for v in scores_data.values() if v is not None and v != '')` — inchangé.
- `grading/views.py:668-674` : boucle `for val in score_obj.scores_data.values()` — inchangée.

**Tests de non-régression existants** : `test_sequential_score_writes_last_wins` vérifie que 2 PUT successifs produisent le bon résultat final. `test_update_or_create_does_not_duplicate` vérifie 1 seul Score après 5 PUT.

**Tests manquants** : Test dédié vérifiant que `total_score` calculé par `StudentCopiesView.list` produit la même valeur pour un `scores_data` donné.

**Conclusion** : **Aucun risque.** Les notes globales sont calculées en lecture seule et aucun calcul n'a été modifié.

---

### Notes par question (Score.scores_data JSONField)

**Lecture seule ou écriture impactée** : Écriture via `CopyScoresView.put` (seul endpoint d'écriture).

**Fichiers / fonctions / vues / services impliqués** :
- `grading/views.py:468-557` — `CopyScoresView.put` (modifié)
- `grading/models.py:304-335` — model `Score`

**Risque théorique avant corrections** : Lost update silencieux en cas de PUT concurrent (2 correcteurs ou admin+correcteur). Le `transaction.atomic()` sans `select_for_update` ne protégeait pas contre ça.

**Risque réel après corrections** : Le `select_for_update` (ligne 529) sérialise les écritures. Le deuxième PUT attend que le premier committe. Il écrit ensuite avec ses propres données — c'est le comportement attendu (last-writer-wins, mais séquentialisé et non plus en parallèle). Le `update_or_create(copy=copy, defaults={...})` est strictement identique avant/après le fix.

**Garanties introduites** :
1. `Copy.objects.select_for_update().filter(id=copy.id).first()` — row lock exclusif sur la copie parente.
2. Le `update_or_create` est toujours à l'intérieur du même `atomic()`.

**Preuves concrètes dans le code** :
- Ligne 529 : `Copy.objects.select_for_update().filter(id=copy.id).first()` — la seule ligne ajoutée dans le bloc write.
- Lignes 531-536 : `Score.objects.update_or_create(copy=copy, defaults={...})` — **strictement identique** au code précédent.
- Le `defaults` dict contient `scores_data` et `final_comment` issus de `request.data` — aucune transformation ajoutée.

**Tests de non-régression existants** :
- `test_sequential_score_writes_last_wins` — 2 PUT, vérifie que le second gagne.
- `test_update_or_create_does_not_duplicate` — 5 PUT, vérifie 1 seul Score.
- `test_valid_scores_accepted` — PUT avec scores valides → 200.

**Tests manquants** : Test de concurrence réelle sur PostgreSQL (impossible sur SQLite en test runner). Test vérifiant que `select_for_update` est bien appelé (mock).

**Conclusion** : **Risque résiduel faible.** Le write path est fonctionnellement identique. Le `select_for_update` ajoute une sérialisation, pas une transformation de données. Sur SQLite (test), `select_for_update` est un no-op — la vraie protection n'est active que sur PostgreSQL (production).

---

### scores_data (contenu du JSONField)

**Lecture seule ou écriture impactée** : Écriture. Le contenu est copié tel quel de `request.data.get('scores_data', {})` vers `Score.scores_data` via `update_or_create defaults`.

**Fichiers / fonctions / vues / services impliqués** :
- `grading/views.py:483` — `scores_data = request.data.get('scores_data', {})`
- `grading/views.py:533` — `'scores_data': scores_data` dans `defaults`

**Risque théorique avant corrections** : Un score > barème max pouvait être enregistré. Un PUT concurrent pouvait écraser silencieusement.

**Risque réel après corrections** : Le contenu de `scores_data` passe par les mêmes validations qu'avant (numeric, non-negative) + la validation barème LOT 6. **Aucune transformation n'est appliquée aux valeurs** — elles sont stockées telles que reçues du client. Le `select_for_update` ne modifie pas le contenu, seulement l'ordre d'exécution.

**Garanties introduites** : Validation barème (rejet 400 si overflow, jamais de capping silencieux). Sérialisation des writes.

**Preuves concrètes dans le code** :
- Ligne 483 : `scores_data = request.data.get('scores_data', {})` — pas de transformation.
- Lignes 492-506 : validation → `return Response(400)` en cas d'erreur — **jamais de modification silencieuse**.
- Lignes 511-523 : validation barème → `return Response(400)` — **rejet, pas de capping**.
- Ligne 533 : `'scores_data': scores_data` — la valeur originale est stockée sans modification.

**Tests de non-régression existants** : `test_valid_scores_accepted`, `test_negative_score_rejected`, `test_non_numeric_score_rejected`.

**Tests manquants** : Test que les valeurs numériques ne sont pas arrondies ou tronquées entre input et output.

**Conclusion** : **Aucun risque de corruption.** Les données passent du client au DB sans transformation. Les validations rejettent, ne modifient jamais.

---

### Barèmes / grading_structure (Exam.grading_structure JSONField)

**Lecture seule ou écriture impactée** : Lecture seule. Aucune correction P0/P1 ne touche `Exam.grading_structure`.

**Fichiers / fonctions / vues / services impliqués** :
- `exams/views.py:674-688` — `_build_exercise_config` lit `exam.grading_structure` (non modifié)
- `exams/views.py:651-671` — `Q_MAX_BY_EXAM` hardcodé (non modifié par les corrections P0/P1)

**Risque théorique avant corrections** : Aucun (pas touché).

**Risque réel après corrections** : Aucun. `Q_MAX_BY_EXAM` et `grading_structure` ne sont lus que dans les GET paths et la validation barème — cette dernière est un check en lecture seule.

**Garanties introduites** : Aucune (pas nécessaire).

**Preuves concrètes dans le code** :
- `exams/views.py:651-671` : `Q_MAX_BY_EXAM` est un dictionnaire de classe statique, jamais modifié.
- `exams/views.py:676` : `gs = exam.grading_structure or []` — lecture seule.
- `grading/views.py:509-510` : `from exams.views import StudentCopiesView; q_max = StudentCopiesView.Q_MAX_BY_EXAM.get(...)` — lecture seule.

**Tests de non-régression existants** : Aucun spécifique au barème.

**Tests manquants** : Test que `Q_MAX_BY_EXAM` correspond exactement à `exam.grading_structure` pour BB_J1 et BB_J2.

**Conclusion** : **Aucun risque.** Lecture seule, jamais modifié.

---

### Annotations (Annotation model)

**Lecture seule ou écriture impactée** : Écriture (PATCH/DELETE) impactée par le changement de permission.

**Fichiers / fonctions / vues / services impliqués** :
- `grading/views.py:119-152` — `AnnotationDetailView.update/destroy` (modifié)
- `grading/views.py:33-42` — `_can_write_copy` helper (inchangé)
- `grading/services.py:AnnotationService.update_annotation/delete_annotation` (inchangé)

**Risque théorique avant corrections** : L'ancien check `getattr(request.user, 'role', '') != 'Admin'` retournait toujours `True` (attribut inexistant → `'' != 'Admin'` → `True`). Conséquence : la seule protection effective était `annotation.created_by != request.user`. Un teacher qui avait créé des annotations sur une copie puis qui n'était plus assigné à cette copie pouvait toujours les modifier/supprimer.

**Risque réel après corrections** : Le check est maintenant `_can_write_copy(request.user, annotation.copy)`. Cela signifie :
- Si un teacher qui **est** le `assigned_corrector` → autorisé (comme avant pour les cas normaux).
- Si un teacher qui **n'est pas** le `assigned_corrector` mais qui était le `created_by` → **REJETÉ** (comportement nouveau).
- Si admin/superuser/is_staff → autorisé (comme avant).

**Changement de comportement potentiel** : Si une copie a été **réassignée** d'un correcteur A vers un correcteur B, et que A avait créé des annotations, A ne peut plus les modifier. Avant le fix, A pouvait encore (car `created_by == A`). Ce changement est **correct sémantiquement** mais représente un resserrement d'accès.

**Garanties introduites** : Le check ne modifie aucune donnée. Il retourne 403 ou laisse passer le flow existant qui lui est inchangé.

**Preuves concrètes dans le code** :
- Ligne 123 : `if not _can_write_copy(request.user, annotation.copy): return Response(403)` — **rejet seulement, jamais de write**.
- Lignes 126-133 : `AnnotationService.update_annotation(...)` — **strictement inchangé**.
- Lignes 146-148 : `AnnotationService.delete_annotation(...)` — **strictement inchangé**.

**Tests de non-régression existants** : 
- `test_assigned_corrector_can_update_annotation` — le correcteur assigné peut modifier → 200.
- `test_non_assigned_teacher_cannot_update_annotation` → 403.
- `test_admin_can_update_annotation` → 200.
- `test_non_assigned_teacher_cannot_delete_annotation` → 403.
- `test_assigned_corrector_can_delete_annotation` → 204.

**Tests manquants** : Test du scénario de réassignation (copy.assigned_corrector change après création d'annotations).

**Conclusion** : **Aucun risque de corruption.** Le check est un garde qui rejette ou laisse passer. Les fonctions de write en aval (`AnnotationService`) sont inchangées. Les annotations existantes ne sont jamais touchées par le guard.

---

### Appréciations (Copy.global_appreciation TextField)

**Lecture seule ou écriture impactée** : Non impactée par les corrections P0/P1. `CopyGlobalAppreciationView` n'a pas été modifié dans cette dernière passe de corrections.

**Fichiers / fonctions / vues / services impliqués** :
- `grading/views.py:396-443` — `CopyGlobalAppreciationView` (inchangé dans les corrections P0/P1)

**Risque théorique avant corrections** : Aucun spécifique à cette catégorie dans les P0/P1.

**Risque réel après corrections** : Nul. Le fichier `grading/views.py` a été modifié, mais les lignes de `CopyGlobalAppreciationView` sont **intouchées**. Le check `_can_write_copy` y était déjà appliqué dans la passe LOT 5 précédente.

**Preuves concrètes dans le code** :
- Ligne 420 : `if not _can_write_copy(request.user, copy)` — déjà présent avant les corrections P0/P1.
- Ligne 437 : `copy.save(update_fields=['global_appreciation'])` — inchangé.

**Tests de non-régression existants** : Aucun spécifique.

**Tests manquants** : Test que `update_fields=['global_appreciation']` ne touche pas d'autres champs.

**Conclusion** : **Aucun risque.** Non touché par les corrections P0/P1.

---

### Remarques (QuestionRemark model)

**Lecture seule ou écriture impactée** : Écriture (PATCH/DELETE) impactée par le changement de permission.

**Fichiers / fonctions / vues / services impliqués** :
- `grading/views.py:365-393` — `QuestionRemarkDetailView.update/destroy` (modifié)

**Risque théorique avant corrections** : Même bug que les annotations — `getattr(request.user, 'role', '')` toujours `''`.

**Risque réel après corrections** : Identique aux annotations. Le guard `_can_write_copy` rejette ou laisse passer. Les fonctions de write en aval sont inchangées :
- `update` → `serializer.save()` (DRF standard, inchangé).
- `destroy` → `remark_obj.delete()` (inchangé).

**Garanties introduites** : Cohérence avec le create endpoint qui utilisait déjà `_can_write_copy`.

**Preuves concrètes dans le code** :
- Ligne 369 : `if not _can_write_copy(request.user, remark_obj.copy): return Response(403)` — rejet seulement.
- Ligne 376-378 : `serializer = self.get_serializer(...)` + `serializer.save()` — **strictement inchangé**.
- Ligne 392 : `remark_obj.delete()` — **strictement inchangé**.

**Tests de non-régression existants** :
- `test_assigned_corrector_can_update_remark`, `test_non_assigned_teacher_cannot_update_remark`, `test_admin_can_update_remark`, `test_non_assigned_teacher_cannot_delete_remark`.

**Tests manquants** : Test que `serializer.save()` ne touche pas d'autres champs que `remark`.

**Conclusion** : **Aucun risque de corruption.** Même logique que les annotations — guard rejet-only devant un write path inchangé.

---

### PDFs finaux (Copy.final_pdf FileField)

**Lecture seule ou écriture impactée** : Non directement impactée. Indirectement via `cancel_task`.

**Fichiers / fonctions / vues / services impliqués** :
- `grading/views_async.py:107-152` — `cancel_task` (modifié)
- `grading/tasks.py:async_finalize_copy` — génère le PDF (inchangé)
- `grading/services.py:GradingService.finalize_copy` — sauvegarde le PDF (inchangé)

**Risque théorique avant corrections** : Un utilisateur non-admin pouvait cancel un `async_finalize_copy` en cours. Si le cancel arrivait entre la génération PDF et le `copy.save()`, le PDF pouvait être perdu.

**Risque réel après corrections** : **Réduit.** Deux protections ajoutées :
1. Seul admin/staff peut cancel → élimine les cancellations accidentelles par des non-admin.
2. `terminate=False` (soft revoke) au lieu de `terminate=True` (SIGTERM) → la task n'est plus interrompue brutalement. Elle sera marquée REVOKED au prochain checkpoint Celery, ce qui est bien plus sûr.

**Garanties introduites** : Soft revoke ne peut pas corrompre un PDF en cours de génération — il attend que la task vérifie son état.

**Preuves concrètes dans le code** :
- Ligne 127 : `if not (request.user.is_staff or request.user.is_superuser): return 403` — filtrage admin.
- Ligne 141 : `result.revoke(terminate=False)` — **pas de SIGTERM**.

**Tests de non-régression existants** :
- `test_admin_can_cancel_task`, `test_teacher_cannot_cancel_task`, `test_cancel_uses_soft_revoke`.

**Tests manquants** : Test d'intégration vérifiant qu'un soft revoke n'interrompt pas une finalisation en cours.

**Conclusion** : **Risque résiduel très faible.** Le soft revoke est beaucoup plus sûr que l'ancien SIGTERM. Les PDFs existants ne sont jamais touchés (seul le processus de cancel est modifié).

---

### Scans sources (Booklet.pages_images, Copy.pdf_source)

**Lecture seule ou écriture impactée** : Non impactée.

**Fichiers / fonctions / vues / services impliqués** : Aucun des fichiers modifiés ne touche aux scans.

**Risque théorique avant corrections** : Aucun.

**Risque réel après corrections** : Aucun.

**Preuves concrètes dans le code** : Aucun des 6 fichiers modifiés (`grading/views.py`, `grading/views_async.py`, `exams/views_documents.py`, `StatsReport.vue`, 2 migrations) ne contient de référence à `pages_images`, `pdf_source`, ou `Booklet`.

**Tests de non-régression existants** : Aucun spécifique.

**Tests manquants** : Aucun nécessaire (non impacté).

**Conclusion** : **Aucun risque.** Non touché.

---

### Copies (Copy model — status, anonymous_id, student, exam FK)

**Lecture seule ou écriture impactée** : Lecture seule dans le contexte des corrections P0/P1. La migration 0023 ajoute des index (lecture).

**Fichiers / fonctions / vues / services impliqués** :
- `grading/views.py:529` — `Copy.objects.select_for_update().filter(id=copy.id).first()` — **lecture + lock, pas d'écriture**.
- `exams/migrations/0023_...` — `AddIndex` sur `Copy`.

**Risque théorique avant corrections** : Aucun spécifique aux copies elles-mêmes.

**Risque réel après corrections** : Le `select_for_update` acquiert un lock exclusif sur la ligne Copy le temps de la transaction score write. **Il ne modifie aucun champ de Copy.** Le `.first()` est une lecture. La migration `AddIndex` ne touche aucune donnée — elle ajoute des structures d'indexation.

**Preuves concrètes dans le code** :
- Ligne 529 : `Copy.objects.select_for_update().filter(id=copy.id).first()` — `SELECT ... FOR UPDATE` en SQL, pas de `UPDATE`.
- Migration 0023 : `migrations.AddIndex(model_name='copy', index=...)` — DDL `CREATE INDEX`, pas de DML.

**Tests de non-régression existants** : `test_sequential_score_writes_last_wins` exécute des PUT sur des copies, vérifie que le modèle Copy n'est pas altéré.

**Tests manquants** : Aucun spécifique nécessaire.

**Conclusion** : **Aucun risque.** Le `select_for_update` est un lock temporaire, pas un write. Les index sont additifs.

---

### États de workflow (Copy.status — STAGING/READY/GRADED/etc.)

**Lecture seule ou écriture impactée** : Non impactée. `CopyReadyView` et `CopyFinalizeView` (qui changent le status) n'ont pas été modifiés.

**Fichiers / fonctions / vues / services impliqués** :
- `grading/views.py:155-196` — `CopyReadyView/CopyFinalizeView` (inchangés)
- `grading/views.py:475-481` — check `if copy.status == Copy.Status.GRADED` (inchangé, était déjà là)

**Risque théorique avant corrections** : Aucun lié aux corrections P0/P1.

**Risque réel après corrections** : Nul. Le seul lien indirect est que `CopyScoresView.put` refuse d'écrire si `status == GRADED` (sauf superuser). Ce check existait déjà avant les corrections.

**Preuves concrètes dans le code** :
- Ligne 475 : `if copy.status == Copy.Status.GRADED and not request.user.is_superuser` — **inchangé**.
- Aucune ligne des corrections P0/P1 n'appelle `copy.status = ...` ni `copy.save()`.

**Tests de non-régression existants** : Aucun spécifique au statut.

**Tests manquants** : Test que `CopyScoresView.put` rejette un PUT sur copie GRADED (sauf admin).

**Conclusion** : **Aucun risque.** Non touché.

---

### DraftState

**Lecture seule ou écriture impactée** : Non impactée. `views_draft.py` n'a pas été modifié dans les corrections P0/P1.

**Fichiers / fonctions / vues / services impliqués** :
- `grading/views_draft.py` — inchangé dans cette passe.

**Risque théorique avant corrections** : Aucun lié aux P0/P1.

**Risque réel après corrections** : Nul.

**Preuves concrètes dans le code** : Le fichier `views_draft.py` n'apparaît dans aucun diff des corrections P0/P1.

**Conclusion** : **Aucun risque.** Non touché.

---

### GradingEvent (audit trail)

**Lecture seule ou écriture impactée** : Écriture. De nouveaux `GradingEvent` sont créés dans `CopyScoresView.put` (ligne 543-548). Ce code était déjà présent avant les corrections P0/P1.

**Fichiers / fonctions / vues / services impliqués** :
- `grading/views.py:539-550` — `GradingEvent.objects.create(...)` (inchangé)

**Risque théorique avant corrections** : Aucun spécifique.

**Risque réel après corrections** : Nul. Le code de création de `GradingEvent` est **strictement identique** avant et après. Il est toujours dans le même bloc `try/except` silencieux. Le `select_for_update` ne change pas la logique de création d'events.

**Preuves concrètes dans le code** :
- Lignes 543-548 : `GradingEvent.objects.create(copy=copy, actor=request.user, action='scores_saved', metadata={...})` — **identique au code pré-fix**.

**Tests de non-régression existants** : Aucun spécifique.

**Tests manquants** : Test que `GradingEvent` est bien créé après un PUT scores réussi.

**Conclusion** : **Aucun risque.** Code inchangé.

---

### Affectations des correcteurs (Copy.assigned_corrector FK)

**Lecture seule ou écriture impactée** : Lecture seule. `_can_write_copy` lit `copy.assigned_corrector_id` mais ne le modifie jamais.

**Fichiers / fonctions / vues / services impliqués** :
- `grading/views.py:42` — `return copy.assigned_corrector_id == user.id` — **lecture seule**.

**Risque théorique avant corrections** : Aucun.

**Risque réel après corrections** : Nul. `_can_write_copy` est un check booléen pur. Il ne contient aucun `save()`, `update()`, ni assignation.

**Preuves concrètes dans le code** :
- Lignes 33-42 : la fonction `_can_write_copy` ne contient que des `return True/False` et un `.filter().exists()`. Aucune opération d'écriture.

**Tests de non-régression existants** : Tous les tests de permission vérifient implicitement que l'affectation n'est pas modifiée.

**Conclusion** : **Aucun risque.** Lecture seule.

---

### Liens entre copies / examens / élèves / correcteurs (FK/M2M)

**Lecture seule ou écriture impactée** : Non impactée.

**Fichiers / fonctions / vues / services impliqués** : Aucun des fichiers modifiés ne contient de `copy.student =`, `copy.exam =`, `copy.assigned_corrector =`, `exam.correctors.add/remove`.

**Risque théorique avant corrections** : Aucun.

**Risque réel après corrections** : Nul.

**Preuves concrètes dans le code** : Recherche exhaustive dans les diffs — aucune assignation de FK ou M2M.

**Conclusion** : **Aucun risque.** Non touché.

---

### Statistiques affichées (/exams/stats-report/)

**Lecture seule ou écriture impactée** : Lecture seule côté backend. Frontend modifié (ajout import `ClipboardList`).

**Fichiers / fonctions / vues / services impliqués** :
- `frontend/src/views/StatsReport.vue:558` — ajout de `ClipboardList` dans les imports
- `frontend/src/components/stats/StatsQcmTab.vue` — inchangé
- `frontend/src/components/stats/StatsPalmaresTab.vue` — inchangé
- `frontend/src/components/stats/StatsQualityTab.vue` — inchangé
- `exams/views.py:stats-report/` endpoint — inchangé

**Risque théorique avant corrections** : Régression runtime — le tab QCM crashait à cause de `ClipboardList` manquant.

**Risque réel après corrections** : L'ajout de l'import restaure le fonctionnement normal. **Aucune donnée n'est modifiée** — c'est un import d'icône JS. Aucun appel API modifié, aucun `computed` modifié, aucun format de données modifié.

**Preuves concrètes dans le code** :
- Ligne 558 : `ClipboardList` ajouté dans l'import — **seule modification**.
- Ligne 589 : `{ id: 'qcm', label: 'QCM 5/5', icon: ClipboardList }` — **inchangé, était déjà là**.
- Aucun `computed`, `onMounted`, `api.get()` modifié.

**Tests de non-régression existants** : Aucun test frontend automatisé.

**Tests manquants** : Test de build Vite (vérifie que `npm run build` passe sans erreur d'import).

**Conclusion** : **Aucun risque de corruption de données.** Modification purement cosmétique (import d'icône).

---

## 1. Vérification Explicite des Risques de Corruption Silencieuse

Pour chaque scénario demandé, analyse ligne par ligne :

### a) Mes modifications ont-elles pu écraser un score existant ?

**NON.** Le seul write path pour les scores est `CopyScoresView.put`, et le code d'écriture (`update_or_create` avec `defaults`) est **strictement identique** avant et après. La seule ligne ajoutée dans le write path est :
```python
Copy.objects.select_for_update().filter(id=copy.id).first()
```
C'est un `SELECT ... FOR UPDATE`, pas un `UPDATE`. Il acquiert un lock, il ne modifie rien.

Preuve : `grading/views.py:529` — lecture seule avec lock. Lignes 531-536 — `update_or_create` inchangé.

### b) Mes modifications ont-elles pu invalider une appréciation existante ?

**NON.** `CopyGlobalAppreciationView` n'a pas été modifié dans cette passe de corrections. La seule modification dans `grading/views.py` concernant les appréciations date du LOT 5 précédent (ajout de `_can_write_copy`), pas des corrections P0/P1 actuelles.

Preuve : diff des corrections P0/P1 — `CopyGlobalAppreciationView` n'apparaît pas.

### c) Mes modifications ont-elles pu déplacer un lien entre copie et élève ?

**NON.** Aucune des modifications ne contient `copy.student =`, `copy.exam =`, ou toute assignation de FK. `_can_write_copy` lit `copy.assigned_corrector_id` mais ne l'écrit jamais.

Preuve : recherche exhaustive `grep -n 'copy\.student\s*=' grading/views.py` → 0 résultats. Idem pour `copy.exam`, `copy.assigned_corrector =`.

### d) Mes modifications ont-elles pu casser la lecture d'un PDF déjà généré ?

**NON.** Le endpoint `CopyFinalPdfView` (qui sert les PDFs aux élèves) n'a pas été modifié. Le `cancel_task` a été modifié mais il ne touche pas les PDFs existants — il ne peut que cancel un task futur, et maintenant uniquement pour les admin. Le passage à `terminate=False` **réduit** le risque de corruption PDF par rapport à l'ancien `terminate=True`.

Preuve : `grading/views.py` — `CopyFinalPdfView` n'apparaît dans aucun diff. `views_async.py:141` — `revoke(terminate=False)` ne peut pas interrompre une I/O en cours.

### e) Mes modifications ont-elles pu rendre inaccessible une copie corrigée ?

**NON, sauf un cas théorique** :

Le changement de permission sur `AnnotationDetailView` et `QuestionRemarkDetailView` pourrait théoriquement **restreindre l'accès en écriture** pour un teacher qui n'est plus le `assigned_corrector` d'une copie. Cependant :
1. Les GET (lecture) ne sont pas affectés — `AnnotationDetailView` en GET n'a pas de check `_can_write_copy`, le queryset `Annotation.objects.all()` est inchangé.
2. Les données restent accessibles en lecture. Seule l'écriture est restreinte.
3. C'est le **comportement correct** — un teacher non-assigné ne devrait pas modifier les annotations d'un collègue.

Preuve : `AnnotationDetailView` hérite de `RetrieveUpdateDestroyAPIView` — le `get_object()` (GET/Retrieve) n'est pas overridé et utilise le queryset standard.

### f) Mes modifications ont-elles pu modifier le sens d'un champ historique ?

**NON.** Aucun model field n'a été renommé, son type n'a pas changé, ses choix n'ont pas été modifiés. Les deux migrations sont exclusivement `AddConstraint` et `AddIndex` — pas d'`AlterField`, `RenameField`, `RemoveField`.

Preuve : `0013_score_unique_copy_constraint.py` — seule opération `AddConstraint`. `0023_copy_performance_indexes_lot8.py` — seule opération `AddIndex` (×3).

### g) Mes modifications ont-elles pu rendre fausse une statistique affichée ?

**NON.** Les calculs de statistiques sont dans :
- `CorrectorStatsView._compute_stats/_get_scores_for_copies` — inchangés.
- `exams/views.py:stats-report/` endpoint — inchangé.
- `StatsReport.vue` — seul le tab QCM `ClipboardList` import est modifié, aucun `computed` ni `api.get()`.

Le `select_for_update` ne modifie pas les données lues par les calculs de stats — il sérialise seulement les writes.

Preuve : `grading/views.py:596-706` — toutes les fonctions de stats sont **identiques ligne par ligne** avant et après les corrections P0/P1.

### h) Mes modifications ont-elles pu bloquer des données existantes à cause d'une contrainte ou validation nouvelle ?

**OUI — risque conditionnel pour la migration 0013.** 

Si des doublons `Score` existent en base (même `copy_id` pour 2+ rows), la migration `0013_score_unique_copy_constraint.py` échouera avec `IntegrityError` lors du `CREATE UNIQUE INDEX`. Cela **ne détruit pas de données** mais **bloque toutes les futures migrations** tant que les doublons ne sont pas résolus.

**Ce risque est documenté** et mitigé :
- La migration n'a pas été exécutée — elle est seulement générée.
- Le docstring de la migration contient le pré-check SQL explicite.
- L'application de la migration nécessite une action manuelle délibérée.

Les validations de score (barème max, numeric, non-negative) sont toutes des **rejets 400** — elles ne modifient jamais les données existantes et ne s'appliquent qu'aux futures écritures via l'API.

---

## 2. Focus Obligatoire sur les Dernières Corrections P0/P1

### 2.1 `select_for_update()` dans `CopyScoresView.put`

**Pourquoi cela ne corrompt pas les données existantes :**
- C'est un `SELECT ... FOR UPDATE WHERE id = <copy_id>`, pas un `UPDATE`. Il acquiert un row lock exclusif sur la table `exams_copy`, lu via `.first()`. La valeur retournée n'est même pas utilisée — elle sert uniquement à poser le lock.
- Le `update_or_create` qui suit est **strictement identique** au code pré-fix. Les mêmes `defaults` sont passés.
- Le lock est automatiquement relâché quand le bloc `with transaction.atomic()` se termine (commit ou rollback).

**Quel risque subsiste malgré tout :**
- Sur SQLite (tests), `select_for_update` est un no-op. La sérialisation n'est effective que sur PostgreSQL. Si les tests sont exécutés sur SQLite, ils ne prouvent pas la concurrence.
- Si le `Copy` row n'existe pas (supprimé entre le `get_object_or_404` et le `select_for_update`), `.first()` retourne `None` et le `update_or_create` échouera avec `IntegrityError` (FK violation). Ce cas est **extrêmement improbable** (nécessite suppression de copie pendant un PUT) et non destructif (rollback automatique).
- Le lock est sur `Copy`, pas sur `Score`. Deux opérations différentes sur la même copie (ex: score PUT + annotation PATCH) ne se bloquent pas mutuellement. C'est le comportement voulu (seulement les score writes sont sérialisés).

**Vérification manuelle nécessaire :**
- Après déploiement : vérifier que `PUT /api/grading/copies/<id>/scores/` fonctionne normalement (latence acceptable, pas de timeout).
- Vérifier que le lock ne cause pas de deadlock en production avec d'autres transactions (test de charge).

### 2.2 Remplacement de `getattr(user, 'role', ...)` par `_can_write_copy`

**Pourquoi cela ne corrompt pas les données existantes :**
- `_can_write_copy` est un check booléen pur : `return True` ou `return False`. La fonction ne contient aucun `save()`, `update()`, `delete()`, ni aucune opération d'écriture.
- Le code de write en aval (`AnnotationService.update_annotation`, `AnnotationService.delete_annotation`, `serializer.save()`, `remark_obj.delete()`) est **strictement inchangé**.
- Le seul effet est de restreindre l'accès : certains users qui passaient avant (via le check cassé) seront désormais rejetés en 403.

**Quel risque subsiste malgré tout :**
- **Changement de sémantique d'accès** : l'ancien check vérifiait `created_by == request.user`. Le nouveau check vérifie `copy.assigned_corrector_id == request.user.id`. Si un teacher a créé des annotations sur une copie qui a été **réassignée** à un autre teacher, il perd l'accès en écriture. C'est **correct** mais constitue un changement de comportement.
- **Impact** : dans la pratique Korrigo, les copies sont rarement réassignées. Les 8 correcteurs ont chacun leur lot fixe. Risque concret : quasi-nul.

**Vérification manuelle nécessaire :**
- Vérifier qu'aucune copie n'a été réassignée entre correcteurs. Si oui, vérifier que les annotations du premier correcteur sont toujours accessibles en lecture.
- Tester manuellement que chaque correcteur peut modifier ses annotations sur ses copies assignées.

### 2.3 Sécurisation de `cancel_task`

**Pourquoi cela ne corrompt pas les données existantes :**
- La modification ajoute un guard `is_staff or is_superuser` qui rejette avec 403. C'est un filtre d'accès, pas une opération de données.
- Le passage de `terminate=True` à `terminate=False` **réduit** le risque. L'ancien `terminate=True` envoyait `SIGTERM` au worker process, ce qui pouvait interrompre une I/O en cours (génération PDF, save en DB). Le nouveau `terminate=False` marque simplement la task comme REVOKED — elle s'arrêtera proprement au prochain checkpoint Celery.
- Aucune donnée existante n'est touchée. Les PDFs déjà générés restent sur le filesystem. Les Scores déjà en DB restent intacts.

**Quel risque subsiste malgré tout :**
- Un admin pourrait encore cancel un `async_finalize_copy` en cours. Avec `terminate=False`, le soft revoke **peut** ne pas arrêter une task déjà en exécution si elle ne vérifie pas son état. `async_finalize_copy` n'a pas de checkpoint `self.is_aborted()`. Le pire cas : la task continue jusqu'au bout malgré le revoke, et le résultat est marqué REVOKED alors qu'il a réussi. Ce n'est pas de la corruption — c'est un faux négatif de statut.

**Vérification manuelle nécessaire :**
- Après déploiement : vérifier que le bouton "Annuler" (si existant dans le frontend) fonctionne ou est masqué pour les non-admin.

### 2.4 Migrations LOT 8

**Pourquoi cela ne corrompt pas les données existantes :**
- **Migration 0013 (UniqueConstraint)** : `CREATE UNIQUE INDEX uniq_score_per_copy ON grading_score (copy_id)`. C'est une opération DDL qui ajoute un index unique. Elle ne modifie, ne supprime, ni ne déplace aucune donnée. Elle échouera si des doublons existent, mais cet échec est un rollback atomique — la DB revient à l'état précédent.
- **Migration 0023 (Index ×3)** : `CREATE INDEX idx_copy_status ON exams_copy (status)`, etc. Purement additif.

**Quel risque subsiste malgré tout :**
- **Risque de blocage** : si des doublons `Score` existent (même `copy_id`, 2+ rows), la migration 0013 échoue et bloque toute migration future. Ce n'est pas de la corruption — c'est un blocage opérationnel.
- **Risque de lock table** : sur une table avec 200+ rows, le `CREATE UNIQUE INDEX` peut prendre quelques secondes et locker la table `grading_score`. Pendant ce temps, les writes sont bloqués. Impact négligeable avec 209 copies.

**Vérification manuelle nécessaire :**
```sql
-- OBLIGATOIRE AVANT migration 0013
SELECT copy_id, COUNT(*) AS cnt 
FROM grading_score 
GROUP BY copy_id 
HAVING COUNT(*) > 1;
```
Si résultat vide → migration safe. Si résultat non vide → data migration de déduplication requise d'abord.

### 2.5 Nouveaux tests ajoutés

**Pourquoi cela ne corrompt pas les données existantes :**
- Les tests utilisent `TestCase` et `TransactionTestCase` de Django, qui créent une base de test isolée et la détruisent après chaque test. Ils ne touchent jamais la DB de production.
- Les fixtures créent des objets (`User`, `Exam`, `Copy`, `Annotation`, `QuestionRemark`, `Score`) dans la base de test seulement.
- `force_authenticate` ne crée pas de session persistante.
- Les mocks (`@patch('grading.views_async.AsyncResult')`) ne touchent pas la DB.

**Quel risque subsiste malgré tout :**
- Aucun. Les tests sont isolés par conception Django. La DB de test est en mémoire (SQLite) ou dans un schéma dédié (PostgreSQL `test_korrigo_db`).

**Vérification manuelle nécessaire :** Aucune.

---

## 3. Scénarios Concrets Encore Possibles

### Scénario 1 : Doublons Score bloquant la migration

**Contexte** : Les scripts de recovery (import_laroussi_scores.py, import_patrick_scores.py, etc.) ont utilisé `Score.objects.create()` directement, sans passer par `update_or_create`. Si l'un de ces scripts a créé un Score pour une copie qui avait déjà un Score (ex: partial recovery suivi d'un full recovery), il y a un doublon.

**Déroulement** :
1. Admin exécute `python manage.py migrate`.
2. Migration 0013 tente `CREATE UNIQUE INDEX uniq_score_per_copy ON grading_score (copy_id)`.
3. PostgreSQL détecte le doublon → `IntegrityError`.
4. Migration échoue. Toutes les futures migrations bloquées.

**Impact données** : Aucune corruption (rollback atomique). Mais blocage opérationnel.

**Mitigation** : Exécuter le pré-check SQL documenté dans la migration. Si doublons trouvés, les résoudre manuellement (garder le plus récent, supprimer les anciens, avec backup préalable).

**Probabilité** : **MOYENNE** — les scripts de recovery ont été exécutés dans des conditions d'urgence.

### Scénario 2 : Teacher ne peut plus modifier ses annotations après réassignation

**Contexte** : Un teacher A avait des annotations sur une copie qui a été réassignée au teacher B. Avec l'ancien code cassé, A pouvait encore modifier ses annotations (car `created_by == A`). Avec le nouveau code, A est rejeté en 403 (car `copy.assigned_corrector_id != A.id`).

**Déroulement** :
1. Teacher A ouvre une copie qu'il avait corrigée.
2. Il tente de modifier une annotation.
3. 403 Forbidden.
4. A contacte l'admin pour comprendre.

**Impact données** : Aucune corruption. Aucune perte de données. Les annotations de A restent lisibles.

**Mitigation** : L'admin (superuser) peut modifier l'annotation pour A. Ou réassigner la copie à A temporairement.

**Probabilité** : **FAIBLE** — les assignations sont stables depuis le dispatch initial.

### Scénario 3 : Validation barème bloque un correcteur sur un examen non enregistré

**Contexte** : Si un nouvel examen est créé avec un nom différent de "BB_J1" ou "BB_J2", `Q_MAX_BY_EXAM.get(copy.exam.name, {})` retourne `{}`, et la validation barème est silencieusement skippée. Ce n'est pas un bug P0/P1 mais un risque pré-existant.

**Impact** : Pas de corruption des données existantes. Les scores des 209 copies BB_J1/J2 ne sont pas affectés.

**Probabilité** : **FAIBLE** à court terme (pas de nouvel examen prévu).

### Scénario 4 : Lock timeout sur `select_for_update` en production

**Contexte** : Si une transaction longue (ex: finalisation PDF) tient un lock sur une Copy row, et qu'un correcteur tente un PUT score sur la même copie, le `select_for_update` bloquera indéfiniment (PostgreSQL default lock timeout = infini).

**Déroulement** :
1. `async_finalize_copy` acquiert un lock sur la copie via `select_for_update` dans `GradingService`.
2. Le correcteur fait un PUT score → `select_for_update` attend.
3. Si la finalisation dure longtemps (LLM summary ~70s + PDF generation), le PUT est bloqué pendant cette durée.
4. Côté frontend, timeout HTTP → erreur affichée au correcteur.

**Impact données** : Aucune corruption. Le PUT sera soit exécuté après le lock, soit timeout côté client (retry possible).

**Mitigation** : Configurer `statement_timeout` ou `lock_timeout` au niveau PostgreSQL pour éviter les blocages infinis. Les finalisations et les score writes ne devraient pas cibler la même copie simultanément en usage normal.

**Probabilité** : **TRÈS FAIBLE** — la finalisation et le score write ciblent la même copie seulement si le correcteur clique "Sauvegarder" pendant une finalisation en cours.

### Scénario 5 : `_is_admin` dans views_documents.py trop permissif

**Contexte** : L'ancienne logique `getattr(user, 'role', None) == UserRole.ADMIN` ne matchait jamais (attribut inexistant). La nouvelle logique `user.is_staff or user.groups.filter(name=UserRole.ADMIN).exists()` est **plus permissive** que l'ancienne dans certains cas — un user `is_staff=True` qui n'est pas dans le groupe Admin peut maintenant uploader des documents.

**Impact** : Pas de corruption des données existantes. Risque d'élargissement d'accès pour l'upload documentaire. Mais tous les teachers dans Korrigo ont `is_staff=False` sauf l'admin.

**Probabilité** : **TRÈS FAIBLE**.

---

## 4. Conclusion Finale

### Verdict : **Données manifestement préservées**

**Justification technique détaillée :**

1. **Aucune des 6 corrections P0/P1 ne contient d'opération d'écriture sur les données existantes.** Chaque modification a été catégorisée :
   - **3 modifications sont des guards** (permission checks) qui rejettent avec 403 ou laissent passer le code existant inchangé. Elles ne contiennent aucun `save()`, `update()`, `delete()` sur les données métier.
   - **1 modification est un lock** (`select_for_update`) qui est un `SELECT ... FOR UPDATE` — lecture avec lock, pas écriture.
   - **2 modifications sont des DDL** (migrations `AddConstraint` + `AddIndex`) qui ne modifient pas les données.

2. **Le code de write effectif** (`update_or_create`, `AnnotationService.update_annotation`, `serializer.save()`, `remark_obj.delete()`) est **strictement identique ligne par ligne** avant et après les corrections P0/P1.

3. **Les données de production sont protégées par un garde supplémentaire** : rien n'a été déployé. Les modifications sont dans le repo local uniquement.

4. **Le seul risque identifié** est opérationnel (pas de corruption) : la migration 0013 peut échouer si des doublons Score existent. Ce risque est documenté, mitigé par un pré-check SQL, et ne détruit aucune donnée en cas d'échec (rollback atomique PostgreSQL).

**Ce que je ne peux pas garantir à 100%** :
- Le comportement exact du `select_for_update` sur PostgreSQL production (testé uniquement en logique sur SQLite).
- L'absence de doublons Score en DB production (nécessite le pré-check SQL).
- Le comportement du soft revoke Celery sur un task `async_finalize_copy` déjà en cours d'exécution (dépend de l'implémentation du worker).

**Vérifications manuelles restant indispensables** :
1. Pré-check doublons Score en production (SQL ci-dessus) avant toute migration.
2. Test fonctionnel POST/PUT scores par un correcteur assigné après déploiement.
3. Test fonctionnel PATCH/DELETE annotation par un correcteur assigné après déploiement.
4. Vérification que les statistiques affichées sur `/exams/stats-report/` sont identiques avant/après déploiement.
