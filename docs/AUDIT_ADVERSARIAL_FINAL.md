# RELECTURE ADVERSARIALE FINALE — Korrigo

**Date** : 7 mars 2026  
**Posture** : Auditeur externe hostile — démontrer que le travail reste insuffisant  
**Périmètre** : Tous les correctifs appliqués, tous les audits produits, toutes les hypothèses formulées  
**Règle** : Aucune auto-indulgence. Chaque "✅ OK" des audits précédents est réexaminé.

---

## 1. LES 10 POINTS LES PLUS FRAGILES DE L'IMPLÉMENTATION ACTUELLE

### F-1. `scores_data` est un JSONField sans validation structurelle côté DB

**Point faible** : Le champ `Score.scores_data` est un `JSONField` libre. Aucune contrainte DB ne valide que les clés correspondent au `grading_structure` de l'examen, ni que les valeurs sont numériques et dans les bornes du barème. La validation `Q_MAX_BY_EXAM` existe uniquement dans `CopyScoresView.put` — un dictionnaire Python hardcodé pour 2 examens.

**Impact potentiel** : Un script ORM, un shell Django, un Celery task, ou un futur endpoint peut écrire n'importe quoi dans `scores_data` : clés fantômes (comme `4.1.3` lors de l'incident Laroussi), valeurs négatives, valeurs dépassant le barème, types non-numériques. La DB accepte tout.

**Pourquoi crédible** : L'incident Laroussi du 2 mars 2026 est la preuve vivante. Le script `import_laroussi_scores.py` a corrompu 21 copies avec une clé fantôme `4.1.3` et des valeurs décalées. La validation `Q_MAX_BY_EXAM` n'aurait **rien empêché** car le script écrivait via ORM direct (`Score.objects.create`), pas via l'API.

**Gravité** : **CRITIQUE**

**Correctif recommandé** : Implémenter une validation `scores_data` dans le `Score.clean()` ou un signal `pre_save` qui vérifie la structure contre `exam.grading_structure`. Alternativement, un `CHECK` constraint PostgreSQL avec `jsonb_typeof` et une fonction de validation.

---

### F-2. `_can_write_copy` traite `is_staff=True` comme admin universel

**Point faible** : La fonction `_can_write_copy` (`grading/views.py:38`) retourne `True` pour tout utilisateur avec `is_staff=True`, indépendamment de son groupe ou rôle réel.

**Impact potentiel** : Si un utilisateur est créé avec `is_staff=True` (nécessaire pour accéder à l'admin Django, souvent donné généreusement), il bypass TOUS les checks d'ownership : scores, annotations, remarques, appréciations, drafts, transitions d'état. Il peut modifier les données de n'importe quelle copie.

**Pourquoi crédible** : En production, 4 définitions différentes de "admin" coexistent : `IsAdmin` (groupe seul), `_is_admin` (is_superuser OR is_staff OR groupe), `_can_write_copy` (idem), `IsAdminUser` DRF (is_staff seul). Un admin système qui met `is_staff=True` pour déboguer un problème d'accès Django Admin ouvre involontairement toutes les portes d'écriture Korrigo.

**Gravité** : **HAUTE**

**Correctif recommandé** : `_can_write_copy` devrait vérifier `is_superuser` OU `groups.filter(name='admin')`, SANS `is_staff`. Unifier les 4 définitions d'admin.

---

### F-3. Aucune des protections LOT 3-11 n'est active en production

**Point faible** : Le serveur de production (`88.99.254.59`) tourne encore le code pré-corrections. Le pattern overlay (`/var/www/labomaths/korrigo/overlay/`) monte les fichiers modifiés dans le container Docker, mais **aucun déploiement des corrections LOT 3-11 n'a été effectué**.

**Impact potentiel** : TOUTES les protections documentées dans les 5 audits sont **inexistantes en production**. Le `_can_write_copy`, le `select_for_update`, la suppression de `BasicAuthentication`, le soft revoke de `cancel_task`, les lock service methods — tout ça n'existe que dans le repo local.

**Pourquoi crédible** : L'audit global le confirme explicitement : "0% est actif en production (rien déployé)". Les correcteurs travaillent actuellement avec le code vulnérable d'avant les corrections.

**Gravité** : **CRITIQUE**

**Correctif recommandé** : Déployer immédiatement via overlay les fichiers critiques. Ou exécuter le plan LOT 11 (migration Docker image).

---

### F-4. La migration `0013` (UniqueConstraint Score.copy) est une bombe potentielle

**Point faible** : La migration `0013_score_unique_copy_constraint` tente de créer un index unique sur `grading_score.copy_id`. Si des doublons existent en base, elle échoue et **bloque TOUTES les futures migrations de l'app `grading`**.

**Impact potentiel** : Blocage opérationnel complet de l'app grading. Impossible d'appliquer quelque migration future que ce soit jusqu'à résolution manuelle. Le risque est aggravé par le fait que les scripts de recovery (Patrick, Sami, Selima, Laroussi) ont utilisé un pattern `filter().first()` + `create()` non atomique qui rend les doublons **théoriquement possibles**.

**Pourquoi crédible** : 4 scripts de recovery ont été exécutés manuellement entre le 27 février et le 2 mars 2026. L'un d'eux (`import_laroussi_scores.py`) a déjà produit une corruption de données (incident `4.1.3`). La possibilité qu'un de ces scripts ait créé un doublon Score (par exécution double, par race avec l'API) n'est **pas exclue** — elle est simplement **non vérifiée**.

**Gravité** : **CRITIQUE** tant que le pré-check SQL n'est pas exécuté en production

**Correctif recommandé** : Exécuter immédiatement en production :
```sql
SELECT copy_id, COUNT(*) FROM grading_score GROUP BY copy_id HAVING COUNT(*) > 1;
```
Si résultat non vide : déduplication manuelle obligatoire AVANT toute migration.

---

### F-5. Le `CopyLock` est un verrou consultatif jamais enforced côté serveur

**Point faible** : Le mécanisme `CopyLock` (acquire/release/heartbeat) est correctement implémenté et sérialisé via `select_for_update`. Mais **aucun endpoint d'écriture ne vérifie si un lock existe avant d'écrire**. Les endpoints scores, annotations, remarques, appréciations ne consultent jamais la table `CopyLock`. Le champ `Copy.Status.LOCKED` n'est jamais écrit par aucun code.

**Impact potentiel** : Le lock est purement cosmétique — il informe le frontend, qui bloque l'UI. Mais tout appel direct à l'API (curl, script, autre onglet sans frontend) contourne entièrement le lock. Un correcteur B (s'il était le `assigned_corrector` après une réassignation) pourrait écrire sur une copie pendant que le correcteur A la tient verrouillée.

**Pourquoi crédible** : L'audit de concurrence (§6.4.1) l'identifie lui-même comme un "advisory lock". Mais les audits précédents (global, intégrité) ne mentionnent JAMAIS cette limitation. L'audit global dit "LOT 4c : 4 méthodes lock service ✅ Corrigé" — ce qui est techniquement vrai mais fonctionnellement trompeur.

**Gravité** : **HAUTE** (architecturale)

**Correctif recommandé** : Soit enforcer le lock dans `_can_write_copy` (vérifier `CopyLock.objects.filter(copy=copy).exclude(owner=user).exists()`), soit documenter explicitement que le lock est advisory-only et supprimer `Copy.Status.LOCKED`.

---

### F-6. Annotations : optimistic locking contournable si le frontend n'envoie pas `version`

**Point faible** : Dans `AnnotationService.update_annotation` (services.py:115-116), le check de version est conditionnel :
```python
expected_version = payload.get('version', None)
if expected_version is not None:  # ← OPTIONNEL
```
Si le frontend n'envoie pas le champ `version`, le check est entièrement skippé. Le mécanisme de protection contre les lost updates est inopérant.

**Impact potentiel** : Deux PATCH simultanés sur la même annotation → le second écrase le premier silencieusement, sans détection de conflit.

**Pourquoi crédible** : Aucun audit ne vérifie si le frontend Vue.js (`CorrectorDesk`) envoie le champ `version` lors des PATCH d'annotation. Si le frontend a été développé AVANT l'ajout du `version` field (P0-DI-008), il ne l'envoie probablement pas. Aucun test ne vérifie ce comportement.

**Gravité** : **MOYENNE**

**Correctif recommandé** : Rendre le `version` obligatoire sur PATCH : si `expected_version is None`, lever `ValueError("Le champ version est requis pour la modification")`.

---

### F-7. `validate_copy` sans `select_for_update` — doublon d'audit trail

**Point faible** : `GradingService.validate_copy` (services.py:294-313) est wrappé dans `@transaction.atomic` mais ne fait PAS de `select_for_update` sur la Copy. Deux appels simultanés lisent tous deux `status=STAGING`, passent le check, et tous deux écrivent `status=READY` avec chacun un `GradingEvent.VALIDATE`.

**Impact potentiel** : Doublon d'événement d'audit pour une seule validation. L'état final est correct (READY), mais l'audit trail est pollué et pourrait induire en erreur lors d'une investigation.

**Pourquoi crédible** : Le double-clic sur un bouton "Valider" dans le frontend envoie 2 POST en ~100ms. C'est un comportement utilisateur courant. Même avec un debounce frontend, le risque persiste si le backend ne se protège pas.

**Gravité** : **FAIBLE** (données correctes, audit pollué)

**Correctif recommandé** : Ajouter `copy = Copy.objects.select_for_update().get(id=copy.id)` comme première ligne de `validate_copy`.

---

### F-8. `ExamReleaseResultsView` et `ExamUnreleaseResultsView` : aucun audit trail

**Point faible** : Ces deux vues (views.py:742-786) modifient `Exam.results_released_at` sans créer de `GradingEvent`. Il n'y a aucune trace de qui a publié ou dépublié les résultats, ni quand, ni combien de fois.

**Impact potentiel** : En cas de litige ("les résultats ont été publiés prématurément"), il est impossible de retracer l'action. Le seul indice serait `Exam.results_released_at` (la dernière valeur) et le log Django (si conservé).

**Pourquoi crédible** : Dans un contexte éducatif (bac blanc), la publication des résultats est un acte administratif officiel. L'absence de traçabilité est un manquement fonctionnel.

**Gravité** : **MOYENNE**

**Correctif recommandé** : Ajouter un `GradingEvent.objects.create(copy=None, action='release_results', actor=request.user, metadata={'exam_id': str(exam.id)})`. Nécessite soit un event sans `copy` (champ nullable), soit un modèle d'audit séparé pour les actions exam-level.

---

### F-9. Aucun test de concurrence réel — `test_double_finalize_race` est un placeholder `pass`

**Point faible** : Le fichier `test_concurrency.py` contient 3 tests. L'un d'eux (`test_double_finalize_race`, ligne 76) a un body `pass` — c'est un placeholder jamais implémenté. Les deux autres sont séquentiels et tournent sur SQLite (où `select_for_update` est un no-op).

**Impact potentiel** : Aucune preuve que les mécanismes de concurrence fonctionnent réellement sous PostgreSQL. Le `select_for_update` dans `_finalize_copy_inner` pourrait avoir un bug subtil (mauvais queryset, mauvais timing) que seul un test multi-thread sur PostgreSQL détecterait.

**Pourquoi crédible** : L'audit de concurrence lui-même classe les tests comme "❌ Insuffisants". Pourtant les audits d'intégrité et le global utilisent l'existence de ces tests comme argument de sécurité ("test existant : `test_sequential_score_writes_last_wins`").

**Gravité** : **HAUTE** (faux sentiment de sécurité)

**Correctif recommandé** : Implémenter des tests multi-thread sur PostgreSQL avec `TransactionTestCase` + `threading.Thread`. Minimum : double finalize, double score PUT, double lock acquire.

---

### F-10. Les 5 copies PDF remplacées (23 fév 2026) avec changement de nombre de pages

**Point faible** : Le 23 février 2026, 5 copies BB_J1 ont eu leur PDF source remplacé. Deux d'entre elles ont changé de nombre de pages : GHORBAL (17→13 pages) et GRATI (9→13 pages). Les annotations existantes référencent des `page_index` qui peuvent être invalides après le changement de pages.

**Impact potentiel** : Une annotation avec `page_index=15` sur GHORBAL (anciennement 17 pages) pointe vers une page qui n'existe plus (maintenant 13 pages). Le frontend affichera l'annotation sur une page qui n'existe pas, ou crashera. Le PDF final généré par `flatten_copy` pourrait ignorer silencieusement les annotations hors-page ou crasher.

**Pourquoi crédible** : La mémoire système le confirme : "Warning: GHORBAL and GRATI page counts changed, annotations might reference shifted pages." Ce warning n'a jamais été suivi d'une vérification.

**Gravité** : **MOYENNE** (2 copies sur 209, mais corruption silencieuse possible)

**Correctif recommandé** : Exécuter une query de vérification en production :
```sql
SELECT a.id, a.page_index, a.copy_id, c.anonymous_id
FROM grading_annotation a
JOIN exams_copy c ON a.copy_id = c.id
WHERE c.id IN ('a5bd614d-...', 'de498607-...')
  AND a.page_index >= 13;
```
Si résultat non vide : les annotations sont orphelines et doivent être déplacées ou supprimées.

---

## 2. ZONES OÙ LES DONNÉES POURRAIENT ENCORE ÊTRE MENACÉES

### 2.1 Corruption silencieuse

| Zone | Menace | Mécanisme de détection actuel | Verdict |
|---|---|---|---|
| `scores_data` avec clés fantômes | Script ORM introduit des clés non conformes au barème | **AUCUN** — pas de validation DB ni service-layer | ❌ Non protégé |
| `scores_data` avec valeurs > barème | Script ORM bypass `Q_MAX_BY_EXAM` | **AUCUN** pour les écritures hors-API | ❌ Non protégé |
| Annotations hors page après remplacement PDF | `page_index` invalide après changement de nombre de pages | **AUCUN** — aucune vérification d'intégrité | ❌ Non protégé |
| `final_pdf` incohérent avec annotations DB | Annotation créée PENDANT la génération PDF de finalize | Le lock `select_for_update` sur Copy ne bloque PAS les annotations | ⚠️ Fenêtre de race |
| `total_score` calculé différemment selon le path | `GradingService.compute_score` vs `StudentCopiesView.list` vs `CorrectorStatsView` — 3 implémentations | **AUCUN test de cohérence** | ⚠️ Divergence possible |

### 2.2 Perte d'accès

| Zone | Menace | Verdict |
|---|---|---|
| Teacher réassigné perd ses annotations | `_can_write_copy` bloque l'ancien `assigned_corrector` | ⚠️ Changement de comportement voulu mais non communiqué |
| Copie stuck en GRADING_IN_PROGRESS | `cancel_task` revoke la task, aucun cleanup de status | ❌ Pas de mécanisme de recovery |
| Lock non libéré après crash navigateur | `cleanup_expired_locks` (5min) + TTL 30min = max 35min d'attente | ⚠️ OK mais 35min est long |

### 2.3 Mauvais ownership

| Zone | Menace | Verdict |
|---|---|---|
| `DraftState` créé par le mauvais user | Fixé (LOT 8 : `IsTeacherOrAdmin` + `_can_write_copy_draft`). Mais le draft existant d'un user non-assigné reste en DB. | ⚠️ Données orphelines possibles |
| `GradingEvent.actor` ne correspond pas au `assigned_corrector` | Un admin peut créer des events avec `actor=admin` sur une copie assignée à un teacher | ✅ Fonctionnellement correct (admin agit) |

### 2.4 Doublons

| Zone | Menace | Verdict |
|---|---|---|
| `Score` doublons | `UniqueConstraint` déclarée Python mais **non appliquée en DB** (migration non exécutée) | ❌ CRITIQUE |
| `GradingEvent` doublons | `validate_copy` peut créer des doublons VALIDATE. Seul `finalize_copy` utilise `get_or_create` | ⚠️ Doublons audit possibles |
| `Annotation` doublons | Pas de contrainte d'unicité. Deux POST rapides créent deux annotations identiques | ⚠️ Possible mais bénin (deux annotations distinctes) |

### 2.5 Cache faux / données stale

| Zone | Menace | Verdict |
|---|---|---|
| Frontend charge un draft stale | L'autosave écrit toutes les 5s. Si 2 onglets, le GET retourne le draft de l'onglet courant (filtre `owner=user`). Mais si l'onglet A a des données plus récentes que l'onglet B, B pourrait charger un draft partiel. | ⚠️ Le `client_id` protège, mais le GET ne vérifie pas le `client_id` |
| `Copy` lue hors transaction dans `CopyScoresView.put` | Le status est vérifié en ligne 475 HORS `transaction.atomic`. Le status pourrait changer entre le check et le write. | ⚠️ Fenêtre TOCTOU |

### 2.6 Régression médias

| Zone | Menace | Verdict |
|---|---|---|
| 5 PDFs remplacés le 23 fév avec changement de pages | Annotations potentiellement hors-page sur GHORBAL et GRATI | ❌ Non vérifié |
| `Booklet.pages_images` paths obsolètes après remplacement PDF | Si la re-rasterization a changé les paths des images, les anciens paths sont des fichiers orphelins | ⚠️ Non vérifié |

### 2.7 Divergence code/prod

| Zone | Menace | Verdict |
|---|---|---|
| **Backend** | 0% des corrections déployées | ❌ CRITIQUE |
| **Frontend** | 0% des corrections déployées | ❌ CRITIQUE |
| **Migrations** | 0 migration exécutée en prod | ❌ CRITIQUE |
| **Celery Beat** | 0 nouvelle tâche active en prod | ❌ Non déployé |
| Overlay 59 fichiers | Incertitude sur quels fichiers sont montés, lesquels sont à jour | ⚠️ Non vérifié |

### 2.8 Workflow concurrent imparfait

| Zone | Menace | Verdict |
|---|---|---|
| `finalize_copy` lock long (2-30s) pendant génération PDF | Bloque les PUT scores sur la même copie | ⚠️ Fonctionnel mais UX dégradée |
| `acquire_lock` IntegrityError non catchée | Deux users créent un lock simultanément → 500 au lieu de 409 | ❌ Bug non corrigé |
| Score LWW sans détection | Deux onglets écrasent mutuellement sans avertissement | ⚠️ Atténué par ownership |

### 2.9 Audit trail incomplet

| Zone | Menace | Verdict |
|---|---|---|
| `ExamReleaseResultsView` / `ExamUnreleaseResultsView` | Aucun event créé | ❌ Non tracé |
| `QuestionRemarkListCreateView.create` / `CopyGlobalAppreciationView._update` | Event dans `try/except` silencieux — perte possible | ⚠️ Fail-open |
| `DraftReturnView.put` | Aucun event créé pour les sauvegardes de brouillon | ⚠️ Choix assumé mais non documenté |
| Actions admin hors Korrigo (Django Admin, shell) | Aucune traçabilité | ❌ Angle mort |

---

## 3. HYPOTHÈSES NON PROUVÉES

### H-1. "La base de production ne contient pas de doublons Score"

**Statut : NON PROUVÉE.**

Les scripts de recovery utilisent `Score.objects.create()` avec un pattern check-then-act non atomique. L'hypothèse que ces scripts n'ont jamais créé de doublon repose sur le fait qu'ils ont été exécutés "manuellement et séquentiellement". Mais :
- Laroussi a été importé le 2 mars, après un incident de corruption le même jour
- Les scripts ont été exécutés dans des conditions d'urgence
- Aucun log ne confirme qu'ils n'ont pas été lancés deux fois (par erreur, debugging)

**Seule preuve acceptée** : le pré-check SQL exécuté en production.

### H-2. "PostgreSQL se comporte comme attendu avec `select_for_update`"

**Statut : NON PROUVÉE.**

Tous les tests tournent sur SQLite où `select_for_update` est un no-op. L'assertion que le lock fonctionne sous PostgreSQL repose sur la documentation PostgreSQL, pas sur un test réel. Les subtilités possibles :
- `READ COMMITTED` vs `REPEATABLE READ` — le comportement diffère
- Lock timeout non configuré → blocage potentiellement infini
- La version de PostgreSQL sur le serveur Docker n'est pas documentée dans les audits

### H-3. "Celery soft revoke arrête proprement une task en cours"

**Statut : NON PROUVÉE.**

`terminate=False` (soft revoke) marque la task comme REVOKED. Mais `async_finalize_copy` n'a **aucun checkpoint** `self.is_aborted()`. La task continue son exécution jusqu'au bout. Le soft revoke n'arrête PAS la task — il la marque comme revoked APRÈS son exécution. Le résultat est que :
- La task finit normalement
- Le statut Celery dit "REVOKED"
- La copie est GRADED mais le frontend pense que le task a été annulé

### H-4. "L'overlay en production est cohérent avec le repo local"

**Statut : NON PROUVÉE.**

Les 59 fichiers overlay sont montés dans le container Docker via `docker-compose.yml` volumes. Mais :
- Quels fichiers ont été mis à jour manuellement par SSH et ne sont pas dans le repo ?
- L'incident Laroussi a impliqué des scripts exécutés directement sur le serveur
- Le remplacement de PDFs du 23 février a été fait par script sur le serveur
- Des modifications pourraient avoir été faites dans le shell Django du serveur

**Il n'existe aucun mécanisme de diff overlay vs repo.**

### H-5. "Le frontend envoie le champ `version` lors des PATCH d'annotation"

**Statut : NON PROUVÉE.**

Le champ `Annotation.version` a été ajouté par P0-DI-008. Le service `update_annotation` accepte optionnellement `version` dans le payload. Mais :
- Aucun audit ne vérifie le code frontend (`CorrectorDesk.vue` ou équivalent)
- Le champ `version` est optionnel dans le service
- Si le frontend a été développé AVANT P0-DI-008, il ne l'envoie pas
- Aucun test frontend ne vérifie ce comportement

### H-6. "Les rôles utilisateurs en production sont correctement configurés"

**Statut : NON PROUVÉE.**

Les audits supposent que :
- Les 4 correcteurs sont dans le groupe `teacher`
- L'admin est dans le groupe `admin` ET est `is_superuser`
- Les étudiants sont dans le groupe `student`
- Aucun utilisateur n'a `is_staff=True` à tort

Mais aucune query de vérification n'a été exécutée sur la base de production.

### H-7. "Les 3 implémentations de calcul `total_score` produisent le même résultat"

**Statut : NON PROUVÉE.**

Le `total_score` est calculé dans 3 endroits :
1. `GradingService.compute_score` — `sum(float(v) for v in scores_data.values() if v is not None and v != '')`
2. `StudentCopiesView.list` — `sum(float(v) for v in scores_data.values() if v is not None and v != '')`  
3. `CorrectorStatsView._get_scores_for_copies` — boucle `for val in score_obj.scores_data.values()`

Les 3 implémentations ont des différences subtiles dans la gestion des valeurs `None`, `''`, `'null'`, `0`. Aucun test ne vérifie que les 3 produisent le même résultat pour un même `scores_data`.

### H-8. "Les copies GRADED ont toutes un `final_pdf` valide"

**Statut : NON PROUVÉE.**

Si une copie est passée à GRADED par un chemin qui a bypassé la génération PDF (shell Django, script recovery, ancien code), elle pourrait avoir `status=GRADED` et `final_pdf=''`. Le endpoint `CopyFinalPdfView` retournerait 404.

---

## 4. CE QUI RESTE POSSIBLEMENT TROP OPTIMISTE DANS LES AUDITS PRÉCÉDENTS

### 4.1 Audit Global (`AUDIT_GLOBAL_POST_EXECUTION.md`)

**Passage trop optimiste** : "Aucune donnée existante corrompue par les changements — CONFIANCE ÉLEVÉE"

**Pourquoi trop optimiste** : C'est vrai que les changements de code ne corrompent pas les données existantes. Mais l'audit passe sous silence le fait que **les changements ne sont pas déployés**. La confiance "ÉLEVÉE" porte sur un système qui n'existe qu'en local. La base de production, elle, reste exposée à toutes les vulnérabilités identifiées.

**Passage trop optimiste** : "LOT 4c: 4 méthodes lock service ✅ Corrigé"

**Pourquoi trop optimiste** : Les 4 méthodes existent et sont correctement implémentées. Mais le lock n'est **jamais enforced** sur les endpoints d'écriture. Dire "✅ Corrigé" laisse entendre que le verrouillage des copies fonctionne. Il ne fonctionne que côté frontend.

### 4.2 Audit Intégrité (`AUDIT_INTEGRITE_DONNEES_POST_P0P1.md`)

**Passage trop optimiste** : "Verdict : Données manifestement préservées"

**Pourquoi trop optimiste** : C'est techniquement correct — les corrections P0/P1 ne corrompent pas les données. Mais ce verdict pourrait être lu comme "les données sont en sécurité", ce qui est faux. Les données sont en sécurité **malgré** les corrections, pas **grâce** à elles. Les vulnérabilités pré-existantes (pas de validation structurelle scores_data, lock advisory, concurrence non testée) restent.

**Passage trop optimiste** : "Le seul risque identifié est opérationnel (pas de corruption)"

**Pourquoi trop optimiste** : L'incident Laroussi (corruption 4.1.3) est de la corruption de données, pas un risque opérationnel. Le même scénario peut se reproduire avec n'importe quel script ORM. L'audit sous-estime le risque des écritures hors-API.

### 4.3 Audit Permissions (`AUDIT_PERMISSIONS_ACCES.md`)

**Passage trop optimiste** : "Verdict global : SATISFAISANTE AVEC RÉSERVES"

**Pourquoi trop optimiste** : L'audit identifie 4 endpoints ❌ Insuffisant (StudentImportView, StatsReportView, StudentListView, DraftReturnView) et 10 ⚠️ avec réserve. Pourtant le verdict est "SATISFAISANTE". Un système avec 4 failles de permissions critiques dont une permet la création de comptes par tout utilisateur authentifié (StudentImportView) n'est PAS satisfaisant — il est **défaillant avec atténuations**.

**Passage trop optimiste** : "DraftReturnView — risque MOYEN (pas critique)" (révisé à la hausse dans le corps de l'audit, puis minimisé dans le verdict)

**Pourquoi trop optimiste** : Le risque DraftReturnView a été réévalué en §3.2 comme "❌ INSUFFISANT" puis en §4.6 comme "MOYEN". L'audit hésite entre les deux. En posture adversariale : un endpoint qui permet à **tout user authentifié** (y compris un étudiant) d'écrire dans une table métier (DraftState) sans vérification de rôle EST un problème critique, même si l'impact sur les données est limité.

### 4.4 Audit Migrations (`AUDIT_MIGRATIONS_LOT8.md`)

**Passage trop optimiste** : "Migration B : ✅ SÛRE EN L'ÉTAT"

**Pourquoi trop optimiste** : La migration B crée 3 index. L'audit affirme qu'elle ne peut pas échouer. C'est vrai pour les données. Mais si l'état des migrations en production est incohérent (0014/0015 appliquées mais pas 0016), les index seraient en doublon. L'audit le mentionne mais conclut "✅ SÛRE" quand même. Un audit adversarial dirait "⚠️ SÛRE SI ÉTAT MIGRATIONS VÉRIFIÉ".

### 4.5 Audit Concurrence (`AUDIT_CONCURRENCE_WORKFLOWS.md`)

**Passage trop optimiste** : "Ce qui sauve la situation en production : le modèle `assigned_corrector` ownership"

**Pourquoi trop optimiste** : L'ownership est vérifié uniquement sur les endpoints POST/PUT/PATCH/DELETE de données métier (scores, annotations, remarques, appréciations). Il n'est PAS vérifié sur :
- `CopyReadyView` (fixé dans le code actuel mais pas déployé)
- `CopyFinalizeView` (fixé dans le code actuel mais pas déployé)
- Les actions admin (un admin peut tout faire)
- Les scripts ORM directs

De plus, l'ownership repose sur `Copy.assigned_corrector_id`. Si ce champ est `NULL` (copie non-assignée), `_can_write_copy` retourne `False` pour tout teacher. Un admin doit intervenir. C'est le comportement correct mais c'est une dépendance sur la qualité du dispatch.

**Passage trop optimiste** : "Verdict DraftState / autosave : ✅ Sécurisé"

**Pourquoi trop optimiste** : Le mécanisme `client_id` + `conditional update` est robuste pour les conflits entre sessions. Mais le GET draft ne vérifie PAS le `client_id`. Si le correcteur ouvre un nouvel onglet (nouveau client_id), fait un PUT (rejeté en 409), puis un GET, il obtient le draft de l'ancien onglet. Le frontend pourrait charger des données obsolètes.

---

## 5. VÉRIFICATIONS MANUELLES INDISPENSABLES AVANT TOUTE MISE EN PRODUCTION

### 5.1 Permissions (sur le serveur de production)

```sql
-- V1: Vérifier les rôles utilisateurs
SELECT u.id, u.username, u.is_staff, u.is_superuser, 
       STRING_AGG(g.name, ', ') AS groups
FROM auth_user u
LEFT JOIN auth_user_groups ug ON u.id = ug.user_id
LEFT JOIN auth_group g ON ug.group_id = g.id
GROUP BY u.id, u.username, u.is_staff, u.is_superuser
ORDER BY u.username;
-- VÉRIFIER: aucun teacher n'a is_staff=True sauf si voulu
-- VÉRIFIER: l'admin est dans le groupe 'admin'
-- VÉRIFIER: les étudiants sont dans le groupe 'student'
```

### 5.2 Médias / PDFs

```bash
# V2: Vérifier que tous les pdf_source et final_pdf existent sur le filesystem
docker exec <container_backend> python manage.py shell -c "
from exams.models import Copy
import os
missing = []
for c in Copy.objects.all():
    if c.pdf_source and not os.path.exists(c.pdf_source.path):
        missing.append(('pdf_source', str(c.id), c.anonymous_id))
    if c.final_pdf and not os.path.exists(c.final_pdf.path):
        missing.append(('final_pdf', str(c.id), c.anonymous_id))
for m in missing:
    print(f'MISSING: {m[0]} for {m[2]} ({m[1]})')
print(f'Total missing: {len(missing)}')
"
# ATTENDU: 0 missing
```

### 5.3 Copies GRADED sans final_pdf

```sql
-- V3: Copies GRADED mais sans PDF final
SELECT id, anonymous_id, status, graded_at, final_pdf
FROM exams_copy
WHERE status = 'GRADED' AND (final_pdf IS NULL OR final_pdf = '');
-- ATTENDU: 0 rows
```

### 5.4 Annotations hors page (post-remplacement PDFs)

```sql
-- V4: Annotations avec page_index >= nombre de pages du booklet
SELECT a.id, a.page_index, a.copy_id, c.anonymous_id,
       (SELECT MAX(jsonb_array_length(b.pages_images::jsonb))
        FROM exams_copy_booklets cb
        JOIN exams_booklet b ON cb.booklet_id = b.id
        WHERE cb.copy_id = c.id) AS max_pages
FROM grading_annotation a
JOIN exams_copy c ON a.copy_id = c.id;
-- VÉRIFIER manuellement les rows où page_index >= max_pages
```

### 5.5 Doublons Score (BLOQUANT pour migration 0013)

```sql
-- V5: Doublons Score.copy (GO/NO-GO absolu)
SELECT copy_id, COUNT(*) AS nb
FROM grading_score
GROUP BY copy_id
HAVING COUNT(*) > 1;
-- ATTENDU: 0 rows → GO pour migration
-- Si ≥ 1: NO-GO, déduplication manuelle requise
```

### 5.6 Scores incohérents (clés fantômes, valeurs hors barème)

```sql
-- V6: Vérifier que tous les scores_data ont le bon nombre de questions
SELECT s.id, c.anonymous_id, e.name AS exam,
       (SELECT COUNT(*) FROM jsonb_object_keys(s.scores_data::jsonb)) AS nq
FROM grading_score s
JOIN exams_copy c ON s.copy_id = c.id
JOIN exams_exam e ON c.exam_id = e.id
ORDER BY e.name, nq;
-- ATTENDU: BB_J1 → 33 questions, BB_J2 → 27 questions (sauf copies partielles)
```

### 5.7 État des migrations en production

```sql
-- V7: Vérifier l'état exact des migrations
SELECT app, name, applied
FROM django_migrations
WHERE app IN ('grading', 'exams')
ORDER BY app, name;
-- VÉRIFIER: grading jusqu'à 0012, exams jusqu'à 0022
-- VÉRIFIER: migration 0016 (RemoveIndex) est bien appliquée
```

### 5.8 Index existants sur les tables cibles

```sql
-- V8: Index sur grading_score et exams_copy
SELECT tablename, indexname, indexdef
FROM pg_indexes
WHERE tablename IN ('grading_score', 'exams_copy')
ORDER BY tablename, indexname;
-- VÉRIFIER: pas d'anciens index 0014/0015, pas de uniq_score_per_copy déjà existant
```

### 5.9 Concurrence — test fonctionnel POST deploy

```bash
# V9: Après déploiement, tester manuellement :
# 1. PUT scores avec correcteur assigné → 200
# 2. PUT scores avec correcteur non-assigné → 403
# 3. PUT scores avec score > barème max → 400
# 4. BasicAuth → 401 (plus de BasicAuthentication)
# 5. Deux PUT scores rapides sur la même copie → le second attend, pas d'erreur
# 6. POST finalize sur copie GRADED → 400 ou 409
```

### 5.10 Celery tasks actives

```bash
# V10: Vérifier que le Beat scheduler a les nouvelles tâches
docker exec <container_celery_beat> celery -A core inspect scheduled
# VÉRIFIER: cleanup-expired-locks (every 300s) et purge-old-audit-logs (03:00 daily)
```

### 5.11 Overlay / Rollback

```bash
# V11: Avant déploiement, backup complet
docker exec <container_db> pg_dump -U korrigo_user -Fc korrigo_db > \
  /var/www/labomaths/korrigo/backups/pre_deploy_lot8_$(date +%Y%m%d_%H%M%S).dump

# V12: Diff overlay vs repo (optionnel mais recommandé)
# Pour chaque fichier dans overlay/:
#   diff <fichier_overlay> <fichier_repo>
# Chercher les modifications faites sur le serveur qui ne sont pas dans le repo
```

---

## 6. CE QUI DEVRAIT ENCORE ÊTRE CORRIGÉ

### P0 — Bloquant production

| # | Fichier(s) | Risque adressé | Impact potentiel | Justification |
|---|---|---|---|---|
| **P0-1** | *(déploiement)* | Aucune correction active en production | Toutes les vulnérabilités identifiées restent exploitables | 0% des corrections est déployé. C'est la faille la plus grave et la plus simple à corriger. |
| **P0-2** | *(production DB)* | Migration 0013 potentiellement bloquante | Blocage de toutes les futures migrations grading | Le pré-check doublons Score n'a jamais été exécuté. C'est un GO/NO-GO absolu. |
| **P0-3** | `students/views.py` | `StudentImportView` sans contrôle de rôle | Création de comptes par tout user authentifié (y compris étudiant) avec mot de passe `passe123` | Un étudiant peut créer des comptes utilisateurs Django. C'est une faille de sécurité critique. |
| **P0-4** | `exams/views_stats.py` | `StatsReportView` sans contrôle de rôle | Un étudiant voit le rapport de jury complet (moyennes, classement, notes par correcteur) | Fuite massive de données confidentielles. Violation de confidentialité du jury. |

### P1 — À corriger très vite

| # | Fichier(s) | Risque adressé | Impact potentiel | Justification |
|---|---|---|---|---|
| **P1-1** | `students/views.py` | `StudentListView` sans contrôle de rôle | Un étudiant liste tous les étudiants (noms, emails, classes) | Fuite de données personnelles (RGPD). |
| **P1-2** | `grading/services.py:294` | `validate_copy` sans `select_for_update` | Doublon d'audit trail sur double-clic | 2 lignes de fix. |
| **P1-3** | `grading/services.py:470` | `acquire_lock` : `IntegrityError` non catchée | 500 Internal Server Error au lieu de 409 Conflict | 5 lignes de fix. |
| **P1-4** | `grading/services.py:106` | Versioning annotations optionnel | Lost update silencieux si frontend n'envoie pas `version` | 3 lignes de fix (rendre `version` obligatoire sur PATCH). |
| **P1-5** | *(production)* | Annotations hors page après remplacement PDFs | Annotations pointant vers des pages inexistantes sur 2 copies | Query de vérification à exécuter. |

### P2 — Amélioration forte

| # | Fichier(s) | Risque adressé | Impact potentiel | Justification |
|---|---|---|---|---|
| **P2-1** | `grading/views.py:33-42` | `_can_write_copy` : unifier la définition d'admin | `is_staff=True` donne un accès total involontaire | 4 définitions différentes d'admin dans le codebase. |
| **P2-2** | `grading/views.py:742-786` | Release/Unrelease sans audit trail | Aucune traçabilité de qui publie les résultats | 10 lignes de fix. |
| **P2-3** | `grading/views.py`, `services.py` | Lock advisory non enforced côté serveur | Le lock ne protège pas réellement contre les écritures concurrentes | Décision architecturale à prendre : enforcer ou documenter. |
| **P2-4** | `grading/tests/test_concurrency.py` | Tests de concurrence réels inexistants | Faux sentiment de sécurité — `test_double_finalize_race` est un `pass` | 1 jour d'effort. PostgreSQL requis. |
| **P2-5** | `grading/models.py:304-332` | Pas de validation structurelle sur `scores_data` | Scripts ORM peuvent corrompre les données (incident Laroussi) | Signal `pre_save` ou `Score.clean()`. |
| **P2-6** | `core/auth.py:46-56` | `IsStudent` fallback session legacy | Potentiellement exploitable si un endpoint exempt d'auth utilise `IsStudent` | 2 lignes de fix. |
| **P2-7** | `exams/views.py:910` | `ExamDispatchView` accessible à tout teacher | Un teacher peut redistribuer les copies d'un autre examen | Restreindre à admin. |

### P3 — Dette technique acceptable temporairement

| # | Fichier(s) | Risque adressé | Impact potentiel | Justification |
|---|---|---|---|---|
| **P3-1** | `grading/views.py:544` | Pas de versioning sur `Score` | Lost update silencieux entre 2 onglets | Migration + 15 lignes. Atténué par ownership. |
| **P3-2** | `grading/services.py:338-419` | Long lock pendant `finalize_copy` (2-30s) | PUT scores bloqué pendant la génération PDF | Refactoring significatif (séparer PDF du lock). |
| **P3-3** | `core/settings.py` | API docs (schema/docs/redoc) exposées en production | Surface d'attaque réduite mais visible | Conditionner à `DEBUG=True`. |
| **P3-4** | `grading/tasks.py:231-248` | `purge_old_audit_logs` bulk delete sans pagination | Lock DB long si millions de rows (pas le cas à court terme) | Ajouter pagination `.delete()[:10000]` en boucle. |
| **P3-5** | Multiples | 3 implémentations de `total_score` potentiellement divergentes | Scores affichés différemment selon l'endpoint | Factoriser dans une méthode unique. |

---

## 7. VERDICT FINAL SANS COMPLAISANCE

### Choix : **NON PRÊT — AVEC RISQUE ACTIF SUR LES DONNÉES EXISTANTES**

### Justification technique détaillée

**1. Le code local est un brouillon non déployé.** Les 5 audits produits analysent un code qui n'existe qu'en local. Le serveur de production tourne l'ancien code vulnérable. Toutes les "protections" documentées (ownership, select_for_update, soft revoke, lock service) sont **inexistantes en production**. Produire 5 audits sur du code non déployé puis conclure "satisfaisant avec réserves" est une forme d'auto-illusion.

**2. Les failles de permissions les plus graves ne sont pas corrigées.** `StudentImportView` (création de comptes par tout user), `StatsReportView` (rapport de jury accessible aux étudiants), `StudentListView` (fuite de données personnelles) — ces 3 endpoints sont des failles P0 qui n'ont fait l'objet d'AUCUN correctif. Les audits les identifient, les documentent, les classifient — mais ne les corrigent pas.

**3. La migration critique est une bombe non désamorcée.** Le pré-check doublons Score n'a JAMAIS été exécuté en production. L'audit des migrations documente exhaustivement le risque, fournit les queries SQL, décrit le scénario d'échec — mais personne n'a encore exécuté la première query. Tant que c'est le cas, la migration est une bombe à retardement.

**4. L'audit trail est incomplet.** La publication des résultats (acte administratif majeur) n'est pas tracée. Les remarques et appréciations sont tracées en fail-open (try/except silencieux). Les actions via Django Admin ou shell ne sont jamais auditées.

**5. La concurrence n'est prouvée par aucun test réel.** Le fichier `test_concurrency.py` contient un placeholder `pass` comme test principal. Les 2 autres tests sont séquentiels sur SQLite. Affirmer que `select_for_update` protège la base sans jamais l'avoir testé sous PostgreSQL avec des threads parallèles est une extrapolation de la documentation, pas une preuve.

**6. Les données existantes portent des traces de fragilité passée.** L'incident Laroussi (corruption 4.1.3), le remplacement de PDFs avec changement de pages (annotations potentiellement orphelines), les scripts de recovery non atomiques — tout cela crée un terrain de données potentiellement incohérent que les audits présentent comme "stable" sans vérification.

### Ce qui est réellement solide

Pour être honnête, certaines parties du travail sont de qualité :
- L'implémentation de `_finalize_copy_inner` avec `select_for_update` + status check + `get_or_create` audit est correcte et robuste.
- Le mécanisme draft avec `client_id` + conditional update + `F('version')` est bien conçu.
- Les lock service methods (`acquire/release/heartbeat`) sont correctement sérialisées.
- La documentation des risques est exhaustive — les audits identifient presque tous les problèmes, même s'ils les sous-évaluent parfois.
- Les corrections P0/P1 sont non-destructives — elles ne corrompent aucune donnée existante.

### Pour passer à "Prêt avec réserves majeures", il faut :

1. **Déployer** les corrections backend en production (overlay ou Docker image)
2. **Exécuter** le pré-check doublons Score en production → résoudre si nécessaire → migrer
3. **Corriger** les 3 failles de permissions P0 (StudentImportView, StatsReportView, StudentListView) — 3 lignes chacune
4. **Vérifier** les annotations hors page sur les 2 copies PDF remplacées
5. **Vérifier** les rôles utilisateurs en production (query V1)
6. **Vérifier** les copies GRADED sans final_pdf (query V3)

### Pour passer à "Prêt", il faut en plus :

7. Implémenter les tests de concurrence réels sous PostgreSQL
8. Rendre le versioning annotations obligatoire
9. Ajouter l'audit trail sur release/unrelease results
10. Catch l'`IntegrityError` dans `acquire_lock`
11. Unifier les 4 définitions d'admin
12. Ajouter la validation structurelle sur `scores_data`

---

*Fin de l'audit adversarial. Ce rapport est volontairement sévère. Son objectif est de mettre en lumière tout ce qui reste fragile, non prouvé, ou insuffisamment protégé — pas de nier le travail accompli.*
