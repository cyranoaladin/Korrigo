# Audit Post-Exécution — LOTs 3 à 11

**Date** : 6 mars 2026  
**Auditeur** : Cascade (auto-audit sévère)  
**Périmètre** : Toutes les modifications appliquées dans les LOTs 3 à 11 du prompt de sécurisation.  
**Critère principal** : Préservation de l'intégrité des données existantes.

---

## Méthodologie

Relecture intégrale de chaque fichier modifié, comparaison avec l'intention déclarée, identification des trous de couverture, des hypothèses dangereuses, et des scénarios de corruption possibles.

---

## LOT 3 — Authentification

### Ce qui a été fait
- `core/settings.py:159-162` : `BasicAuthentication` retiré de `DEFAULT_AUTHENTICATION_CLASSES`. Seul `SessionAuthentication` reste.
- `grading/views_async.py:5-17` : `task_status` et `cancel_task` protégés par `@authentication_classes([SessionAuthentication])` + `@permission_classes([IsAuthenticated])`.

### Verdict : ✅ Corrigé

### Risques résiduels

| # | Risque | Sévérité | Détail |
|---|--------|----------|--------|
| R3-1 | **Aucun contrôle d'autorisation sur `task_status` et `cancel_task`** | **ÉLEVÉ** | N'importe quel utilisateur authentifié (y compris un élève avec session) peut interroger ou **annuler** n'importe quel task Celery via son `task_id`. Un élève qui intercepterait un `task_id` (prévisible si UUIDs séquentiels Celery) pourrait annuler la finalisation d'une copie en cours. Le fix LOT 3 a fermé l'accès anonyme mais **n'a pas ajouté de vérification que l'utilisateur est le propriétaire de la task ou un admin**. |
| R3-2 | **`cancel_task` utilise `terminate=True, signal='SIGTERM'`** | MOYEN | Ceci kill le worker process, pas seulement la task. Si le worker traite d'autres tasks en parallèle (prefork pool), le SIGTERM peut interrompre des tasks tierces. Il faudrait `terminate=False` (soft revoke) ou vérifier que le pool est configuré en `solo`. |
| R3-3 | **AllowAny sur `CopyFinalPdfView`** | FAIBLE (justifié) | L'AllowAny est justifié par le dual-auth (teacher Django auth + student session). Les security gates sont correctement implémentées (status check, ownership check). Pas de risque de corruption. Cependant, le commentaire docstring référence des numéros de lignes (`line 179`, `lines 186-215`) qui ne correspondent plus au code actuel — documentation périmée. |
| R3-4 | **AllowAny sur endpoints publics** | FAIBLE (légitime) | `StudentLoginView`, `StudentLogoutView`, `CSRFCookieView`, `LoginView`, health checks — tous légitimes. Rate-limités. |

### Ce qui n'a PAS été fait
- **Pas de test unitaire** pour vérifier que `task_status`/`cancel_task` rejettent les requêtes non-authentifiées. Le fichier `test_async_views.py` existe mais n'a pas été mis à jour pour tester le nouveau comportement auth.

---

## LOT 4 — Verrouillage, Concurrence, Atomicité

### Ce qui a été fait
1. **`grading/views.py:527-536`** : `CopyScoresView.put` wrappé dans `transaction.atomic()` autour du `Score.objects.update_or_create`.
2. **`grading/tasks.py:92-100`** : `async_finalize_copy` — les erreurs transientes déclenchent maintenant `self.retry(exc=exc)` au lieu d'être avalées dans un error dict.
3. **`grading/services.py:421-572`** : 4 méthodes de lock service ajoutées (`acquire_lock`, `release_lock`, `heartbeat_lock`, `get_lock_status`).

### Verdict : ⚠️ Partiellement corrigé

### Problèmes identifiés

| # | Problème | Sévérité | Détail |
|---|----------|----------|--------|
| R4-1 | **`CopyScoresView.put` : `transaction.atomic` sans `select_for_update`** | **ÉLEVÉ** | Le `update_or_create` dans le bloc `atomic` n'utilise PAS `select_for_update`. Deux requêtes PUT simultanées sur la même copie peuvent passer la validation barème en parallèle, puis l'une écrase l'autre au moment du `update_or_create`. Le `transaction.atomic` protège uniquement contre les partial writes (GradingEvent sans Score), **pas contre les race conditions de lecture-écriture**. Pour corriger : `Score.objects.select_for_update().filter(copy=copy)` avant le `update_or_create`, ou utiliser un `F()` update. |
| R4-2 | **`CopyGlobalAppreciationView._update` : aucun `transaction.atomic`** | MOYEN | Le `copy.save(update_fields=['global_appreciation'])` suivi du `GradingEvent.objects.create` n'est pas atomique. Si le GradingEvent échoue, l'appréciation est sauvegardée sans trace d'audit. Le `except Exception: logger.warning(...)` avale silencieusement cette incohérence. |
| R4-3 | **`QuestionRemarkListCreateView.create` : aucun `transaction.atomic`** | MOYEN | Même problème : `update_or_create` + `GradingEvent.objects.create` sans transaction. Le GradingEvent peut échouer silencieusement. |
| R4-4 | **`DraftReturnView.put` : race condition sur `get_or_create` → `filter().update()`** | MOYEN | Le check `existing_draft.client_id != client_id` puis le `get_or_create` ne sont pas dans une transaction. Deux requêtes simultanées du même correcteur avec des `client_id` différents pourraient passer le check et créer deux DraftState (si l'unique_together n'est pas en place). En pratique, le modèle a probablement un unique_together (copy, owner) qui protège, mais c'est une défense accidentelle, pas intentionnelle. |
| R4-5 | **`async_import_pdf` : ne retry PAS, retourne un error dict** | FAIBLE | Contrairement à `async_finalize_copy` qui a été corrigé pour utiliser `self.retry()`, `async_import_pdf` (lignes 158-171) catch toutes les exceptions et retourne un error dict. Incohérence. Mais l'import PDF n'est pas un chemin critique pour la corruption de données. |

### Impact sur l'intégrité des données
- **R4-1 est le plus critique** : deux correcteurs (ou un script batch + un correcteur) sauvegardant simultanément des scores sur la même copie → perte silencieuse de données du premier writer. Probabilité faible en pratique (un seul correcteur par copie), mais pas nulle si un admin intervient en parallèle.

---

## LOT 5 — Permissions Écriture (assigned_corrector)

### Ce qui a été fait
- `grading/views.py:33-42` : Fonction `_can_write_copy(user, copy)` créée.
- Appliquée à : `AnnotationListCreateView.create`, `QuestionRemarkListCreateView.create`, `CopyGlobalAppreciationView._update`, `CopyScoresView.put`.

### Verdict : ⚠️ Partiellement corrigé — **trous de couverture significatifs**

### Problèmes identifiés

| # | Problème | Sévérité | Détail |
|---|----------|----------|--------|
| R5-1 | **`AnnotationDetailView.update` et `.destroy` : N'UTILISE PAS `_can_write_copy`** | **ÉLEVÉ** | Ces méthodes (lignes 119-152) utilisent `getattr(request.user, 'role', '')` qui est **un attribut qui n'existe PAS** sur le modèle User de Django. Le check `request.user.role != 'Admin'` sera **TOUJOURS True** (car `role` vaudra toujours `''`). En conséquence, seul `is_superuser` bypass, et sinon le check `annotation.created_by != request.user` s'applique. **Un correcteur A peut modifier l'annotation d'un correcteur B sur SA PROPRE copie** (si l'annotation a été créée par un script ou un admin). Inversement, **un correcteur ne peut PAS modifier ses propres annotations sur une copie réassignée**. La logique est incohérente avec le reste du LOT 5. |
| R5-2 | **`QuestionRemarkDetailView.update` et `.destroy` : même problème** | **ÉLEVÉ** | Lignes 365-395 : même pattern `getattr(request.user, 'role', '') != 'Admin'`. Même bug. De plus, **pas de check `_can_write_copy`** — un correcteur peut modifier/supprimer des remarques de n'importe quelle copie via l'endpoint `/api/remarks/<id>/` s'il est le `created_by`. |
| R5-3 | **`DraftReturnView` : aucun check `_can_write_copy`** | MOYEN | `views_draft.py:34` utilise seulement `IsAuthenticated`. Un correcteur authentifié peut sauvegarder un draft sur une copie qui ne lui est pas assignée. En pratique, le front ne le fait pas, mais l'API est ouverte. |
| R5-4 | **`CopyReadyView` et `CopyFinalizeView` : pas de check `_can_write_copy`** | MOYEN | Lignes 155-177 : n'importe quel teacher/admin peut passer une copie en READY ou la finaliser, même si elle est assignée à un autre correcteur. Problème si un correcteur finalise accidentellement la copie d'un collègue avant qu'il ait fini. |
| R5-5 | **`_can_write_copy` : `is_staff` trop permissif** | FAIBLE | La fonction accorde l'accès en écriture à tout `is_staff=True`. Si un utilisateur est `is_staff` mais n'est pas dans le groupe `admin`, il bypass quand même le check. En pratique tous les `is_staff` sont probablement admins, mais c'est une hypothèse non vérifiée. |
| R5-6 | **`_can_write_copy` utilise `copy.assigned_corrector_id == user.id`** | INFO | Ceci compare un FK integer avec `user.id`. C'est correct. Mais si `assigned_corrector` est NULL, le check retourne False (correcteur non assigné = personne ne peut écrire sauf admin). Comportement correct. |

### Impact sur l'intégrité des données
- **R5-1 et R5-2** sont les plus graves : les endpoints `PATCH/DELETE /api/annotations/<id>/` et `PATCH/DELETE /api/remarks/<id>/` ne vérifient pas si l'utilisateur a le droit d'écrire sur la copie parente. Un correcteur malveillant pourrait modifier les annotations d'un autre correcteur s'il connaît les UUIDs.

---

## LOT 6 — Validation Barème Max

### Ce qui a été fait
- `grading/views.py:510-525` : Validation des scores individuels contre `Q_MAX_BY_EXAM` dans `CopyScoresView.put`.

### Verdict : ⚠️ Partiellement corrigé — **hypothèse dangereuse**

### Problèmes identifiés

| # | Problème | Sévérité | Détail |
|---|----------|----------|--------|
| R6-1 | **`Q_MAX_BY_EXAM` est HARDCODÉ, pas dynamique** | **ÉLEVÉ** | Le dictionnaire `Q_MAX_BY_EXAM` dans `exams/views.py:651-671` est une constante statique. Il n'est PAS dérivé de `exam.grading_structure` en DB. Si le barème change en DB (via `ExamSerializer.validate_grading_structure`), la validation frontend reste sur l'ancien barème. **Pour tout nouvel examen**, la validation sera silencieusement ignorée (ligne 513 : `if q_max:` — si l'exam n'est pas dans le dict, aucune validation). |
| R6-2 | **Validation côté API uniquement, pas côté service** | MOYEN | La validation barème est dans la vue (`CopyScoresView.put`), pas dans le service layer (`GradingService`). Tout code qui écrit des scores directement via ORM (scripts d'import, shell Django, recovery scripts) **bypass complètement cette validation**. L'incident Laroussi (phantom `4.1.3`, overflow `4.1.2` à 0.50 vs max 0.25) se serait produit même avec le LOT 6 en place, car l'import a utilisé l'ORM directement. |
| R6-3 | **Pas de validation de la somme totale** | MOYEN | On vérifie que chaque note individuelle ≤ max question, mais on ne vérifie PAS que `sum(scores) <= 20`. Un correcteur pourrait entrer des scores valides individuellement mais dont la somme dépasse 20 (improbable mais possible avec des erreurs d'arrondi ou de saisie). |
| R6-4 | **Import circulaire fragile** | FAIBLE | Ligne 511 : `from exams.views import StudentCopiesView` — import d'une vue dans une vue d'un autre module. Si `exams.views` importe quelque chose de `grading.views`, on a un import circulaire. Actuellement pas le cas, mais c'est fragile. Le `Q_MAX_BY_EXAM` devrait être dans un module partagé (ex: `exams/constants.py` ou dérivé de `exam.grading_structure`). |

### Impact sur l'intégrité des données
- **R6-1** est le problème structurel : la validation est incomplète pour tout examen futur et découplée de la source de vérité DB. Cependant, pour les 2 examens existants (BB_J1, BB_J2), les valeurs sont correctes et vérifiées post-Laroussi.

---

## LOT 7 — Performance (N+1)

### Ce qui a été fait
1. `grading/views.py:584-588` : `CorrectorStatsView` — prefetch de tous les `Score` en un seul query, passé via `scores_by_copy` dict.
2. `exams/views.py:702-714` : `StudentCopiesView.list` — prefetch des `Score` et `QuestionRemark` en bulk.

### Verdict : ✅ Corrigé

### Risques résiduels

| # | Risque | Sévérité | Détail |
|---|--------|----------|--------|
| R7-1 | **`CorrectorStatsView._get_scores_for_copies` : fallback au N+1** | FAIBLE | Ligne 665 : `scores_by_copy.get(copy.id) if scores_by_copy else Score.objects.filter(copy=copy).first()`. Le fallback garde l'ancien comportement N+1 si `scores_by_copy` est None. En pratique, les 3 appels à cette méthode dans `get()` passent toujours le dict, donc le fallback ne se déclenche pas. Mais c'est du dead code dangereux — un futur développeur pourrait appeler la méthode sans le dict. |
| R7-2 | **Pas de `.select_related('exam')` sur `StudentCopiesView.list`** | FAIBLE | Ligne 730 : `copy.exam.name` et `copy.exam.date` accèdent au FK exam sans prefetch. Si `get_queryset()` ne fait pas de `select_related('exam')`, c'est un N+1 résiduel (1 query par copie pour l'exam). Il faudrait vérifier le queryset de base. |

### Impact sur l'intégrité des données
- **Aucun risque d'intégrité.** Les optimisations sont en lecture seule.

---

## LOT 8 — Contraintes DB

### Ce qui a été fait
1. `grading/models.py:329-332` : `UniqueConstraint(fields=['copy'], name='uniq_score_per_copy')` sur `Score`.
2. `exams/models.py:327-331` : 3 index sur `Copy` (status, exam+status, corrector+status).

### Verdict : ⚠️ NON APPLIQUÉ EN PRODUCTION

### Problèmes identifiés

| # | Problème | Sévérité | Détail |
|---|----------|----------|--------|
| R8-1 | **Aucune migration générée** | **CRITIQUE** | Les changements de modèle sont dans le code Python, mais **aucun fichier de migration n'existe** dans le repo local. `makemigrations` doit être exécuté (sur le serveur ou localement avec un env Django fonctionnel) pour générer les migrations, puis `migrate` pour les appliquer. **Jusqu'à ce que ce soit fait, la contrainte d'unicité n'existe qu'en Python, pas en DB.** |
| R8-2 | **Risque de migration destructive** | **ÉLEVÉ** | Si des doublons de `Score` existent en DB (plusieurs Score pour la même Copy), la migration `UniqueConstraint` échouera avec `django.db.utils.IntegrityError`. Il FAUT vérifier l'absence de doublons AVANT de migrer : `SELECT copy_id, COUNT(*) FROM grading_score GROUP BY copy_id HAVING COUNT(*) > 1`. |
| R8-3 | **Pas de données de migration** | MOYEN | Si des doublons existent, il faut une data migration pour les fusionner/supprimer AVANT d'appliquer la contrainte. Aucune data migration n'a été prévue. |

### Impact sur l'intégrité des données
- **R8-1 est le plus critique** : la protection promise par le LOT 8 est **inexistante en production** tant que la migration n'est pas appliquée. Le `update_or_create` dans `CopyScoresView.put` fonctionne uniquement grâce au fait qu'il filtre sur `copy=copy`, mais un script externe pourrait créer des doublons.

---

## LOT 9 — RGPD, AuditLog, Rétention

### Ce qui a été fait
1. `grading/tasks.py:212-228` : `cleanup_expired_locks` — purge des `CopyLock` expirés.
2. `grading/tasks.py:231-248` : `purge_old_audit_logs` — purge des `AuditLog` > 365 jours.
3. `core/celery.py:25-34` : Enregistrement dans Celery Beat (5min pour locks, 03:00 daily pour audit logs).

### Verdict : ✅ Corrigé

### Risques résiduels

| # | Risque | Sévérité | Détail |
|---|--------|----------|--------|
| R9-1 | **`purge_old_audit_logs` : suppression en bulk sans batch** | MOYEN | Ligne 245 : `old_entries.delete()` peut supprimer des millions de rows en une seule transaction, causant un lock long sur la table et potentiellement un timeout. Il faudrait paginer : `old_entries[:10000].delete()` en boucle. |
| R9-2 | **Pas d'anonymisation, suppression pure** | FAIBLE | La RGPD autorise la suppression pure ou l'anonymisation. La suppression est plus simple et plus sûre. Mais si des AuditLog contiennent des références à des données encore nécessaires (ex: `student_id` dans un AuditLog lié à une copie encore active), la suppression pourrait perdre de la traçabilité. En pratique, 365 jours est largement suffisant pour le cycle de vie d'un bac blanc. |
| R9-3 | **`cleanup_orphaned_files` n'est PAS enregistré dans Celery Beat** | FAIBLE | La task existe (ligne 174-209) mais n'est PAS dans `app.conf.beat_schedule`. Le nettoyage des fichiers temp orphelins ne se fait jamais automatiquement. |

### Impact sur l'intégrité des données
- **Aucun risque de corruption.** Les tâches sont purement de nettoyage.

---

## LOT 10 — Frontend Stats Refactoring

### Ce qui a été fait
1. `StatsReport.vue` : 1076 → 685 lignes. 3 sub-components extraits.
2. `StatsQcmTab.vue`, `StatsPalmaresTab.vue`, `StatsQualityTab.vue` créés.
3. `v-show` → `v-if` sur tous les tabs (lazy rendering).
4. Dead code supprimé (computed properties migrées dans les sub-components).
5. Unused icon imports nettoyés.

### Verdict : ✅ Corrigé

### Risques résiduels

| # | Risque | Sévérité | Détail |
|---|--------|----------|--------|
| R10-1 | **Données hardcodées dans `StatsQcmTab.vue`** | INFO | Les tableaux `cheatDetected` et `nearCheat` sont des constantes statiques dans le composant, pas des données venant de l'API. C'est un choix de design (données d'analyse manuelle), mais ça signifie que ces données ne seront jamais mises à jour automatiquement. |
| R10-2 | **Pas de test frontend** | FAIBLE | Aucun test unitaire Vue pour vérifier que les sub-components reçoivent les bonnes props et s'affichent correctement. Risque de régression si la structure de l'API change. |
| R10-3 | **`MessageSquare` importé dans `StatsReport.vue` mais peut-être inutilisé** | FAIBLE | L'icône `MessageSquare` reste importée dans le parent. Il faudrait vérifier qu'elle est encore utilisée dans les tabs restants (non extraits). Si non, c'est du dead code. |

### Impact sur l'intégrité des données
- **Aucun risque.** Le refactoring est purement frontend, lecture seule.

---

## LOT 11 — Overlay Exit

### Ce qui a été fait
- `docs/LOT11-overlay-exit.md` : Guide de migration en 5 phases.

### Verdict : ✅ Documentation uniquement (pas d'action technique)

### Risques
- **Le pattern overlay est toujours actif en production.** Tant que la migration n'est pas exécutée, le risque de divergence local/serveur persiste.

---

## Synthèse Globale

### Classement des risques par sévérité

| # | Risque | LOT | Sévérité | Données impactées | Action requise |
|---|--------|-----|----------|-------------------|----------------|
| **R8-1** | Migration DB non générée/appliquée | 8 | **CRITIQUE** | Score, Copy indexes | Générer et appliquer les migrations |
| **R4-1** | Race condition sur `CopyScoresView.put` (pas de `select_for_update`) | 4 | ÉLEVÉ | `scores_data` | Ajouter `select_for_update` dans le bloc atomic |
| **R5-1** | `AnnotationDetailView` n'utilise pas `_can_write_copy` | 5 | ÉLEVÉ | Annotations | Remplacer le check `role` par `_can_write_copy` |
| **R5-2** | `QuestionRemarkDetailView` n'utilise pas `_can_write_copy` | 5 | ÉLEVÉ | Remarques | Idem |
| **R6-1** | `Q_MAX_BY_EXAM` hardcodé, pas dynamique | 6 | ÉLEVÉ | Validation scores | Dériver de `exam.grading_structure` |
| **R3-1** | `task_status`/`cancel_task` : pas de check owner | 3 | ÉLEVÉ | Workflow async | Ajouter vérification task ownership |
| **R8-2** | Risque doublons Score bloquant migration | 8 | ÉLEVÉ | Migration | Vérifier doublons avant migrate |
| R4-2 | `CopyGlobalAppreciationView` sans `atomic` | 4 | MOYEN | Audit trail | Wrapper dans transaction |
| R4-3 | `QuestionRemarkListCreateView` sans `atomic` | 4 | MOYEN | Audit trail | Wrapper dans transaction |
| R5-3 | `DraftReturnView` sans `_can_write_copy` | 5 | MOYEN | DraftState | Ajouter le check |
| R5-4 | `CopyReadyView`/`CopyFinalizeView` sans check assignation | 5 | MOYEN | Status copie | Ajouter le check ou documenter |
| R6-2 | Validation barème côté vue, pas service | 6 | MOYEN | Scripts d'import | Déplacer dans le service layer |
| R9-1 | Purge audit logs sans batch | 9 | MOYEN | Performance DB | Paginer la suppression |

### Données effectivement protégées (améliorations réelles)

1. **BasicAuthentication supprimé** — plus de credentials en clair sur le réseau.
2. **Endpoints async fermés** — plus d'accès anonyme aux tasks Celery.
3. **4 endpoints d'écriture protégés** par `_can_write_copy` : annotations (create), remarques (create), appréciation, scores.
4. **Retry Celery fonctionnel** sur `async_finalize_copy` — plus de perte silencieuse de finalisation.
5. **Lock service complet** — acquire, heartbeat, release, status opérationnels.
6. **Validation barème** opérationnelle pour BB_J1 et BB_J2 (mais hardcodée).
7. **N+1 résolus** sur `CorrectorStatsView` et `StudentCopiesView.list`.
8. **Nettoyage automatique** des locks expirés et des audit logs anciens.

### Données NON protégées (trous de couverture)

1. **Annotations existantes** : `PATCH/DELETE /api/annotations/<id>/` — vérification de permission cassée (attribut `role` inexistant).
2. **Remarques existantes** : `PATCH/DELETE /api/remarks/<id>/` — même problème.
3. **Drafts** : aucun check d'assignation correcteur.
4. **Scores via ORM** : aucune validation barème hors de la vue API.
5. **Contrainte d'unicité Score** : inexistante en DB tant que la migration n'est pas appliquée.
6. **Task Celery** : annulable par n'importe quel utilisateur authentifié.

### Hypothèses dangereuses identifiées

1. **"Un seul correcteur par copie" comme protection contre les races** — vrai dans le workflow normal, faux quand un admin intervient.
2. **"`Q_MAX_BY_EXAM` ne changera pas"** — vrai pour BB_J1/BB_J2, faux pour tout futur examen.
3. **"Le frontend empêche les appels non autorisés"** — vrai pour les utilisateurs normaux, faux pour un attaquant avec curl.
4. **"Les scripts d'import passent par l'API"** — faux, tous les recovery scripts (Laroussi, Patrick, Selima) utilisent l'ORM directement.
5. **"La migration sera appliquée bientôt"** — tant qu'elle n'est pas faite, la contrainte d'unicité est du papier.

### Aucun test n'a été ajouté ou modifié

**C'est le constat le plus sévère.** Aucun des 51 fichiers de test existants n'a été mis à jour pour couvrir les changements des LOTs 3-11. Cela signifie :
- Aucune vérification automatisée que les fixes fonctionnent.
- Aucune protection contre les régressions.
- Aucun moyen de détecter si un futur déploiement casse les protections.

---

## Recommandations Prioritaires

### Immédiat (avant prochain déploiement)
1. **Générer et appliquer les migrations** LOT 8 (après vérification doublons).
2. **Corriger `AnnotationDetailView` et `QuestionRemarkDetailView`** pour utiliser `_can_write_copy` au lieu de `getattr(request.user, 'role', '')`.
3. **Ajouter `select_for_update`** dans `CopyScoresView.put` pour éliminer la race condition.

### Court terme
4. Ajouter un check d'autorisation sur `cancel_task` (vérifier que l'utilisateur a lancé la task).
5. Dériver `Q_MAX_BY_EXAM` de `exam.grading_structure` au lieu du hardcode.
6. Ajouter `_can_write_copy` à `DraftReturnView`.
7. Écrire des tests de régression pour les fixes critiques.

### Moyen terme
8. Déplacer la validation barème dans le service layer.
9. Paginer `purge_old_audit_logs`.
10. Documenter les endpoints AllowAny avec leurs justifications actualisées.
