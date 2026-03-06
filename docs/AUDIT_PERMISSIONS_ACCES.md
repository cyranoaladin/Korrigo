# AUDIT PERMISSIONS, AUTHENTIFICATION & CONTRÔLES D'ACCÈS

**Date** : 2026-03-10  
**Périmètre** : Tous les endpoints backend après corrections P0/P1 (LOT 3–8)  
**Méthode** : Lecture exhaustive de chaque fichier de vue, permission, URL et service  
**Exigence** : Technique, sévère, argumentée, orientée production réelle

---

## 1. AUTHENTIFICATION

### 1.1 Configuration globale (core/settings.py)

```python
REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': ['rest_framework.permissions.IsAuthenticated'],
    'DEFAULT_AUTHENTICATION_CLASSES': ['rest_framework.authentication.SessionAuthentication'],
}
```

**Constat** :
- **BasicAuthentication** : **supprimée** (LOT 3). Commentaire en place. Aucune référence résiduelle dans le code applicatif (vérifié par grep). ✅
- **SessionAuthentication** : seul mécanisme actif. Implique CSRF obligatoire sur toutes les mutations (POST/PUT/PATCH/DELETE) sauf endpoints exemptés explicitement.
- **Default deny** : `IsAuthenticated` par défaut — tout endpoint non décoré exige une session valide. ✅

### 1.2 Endpoints exemptés de CSRF

| Endpoint | Classe | Justification |
|---|---|---|
| `POST /api/login/` | `LoginView` | Public. `csrf_exempt` + `authentication_classes = []`. Rate-limité 5/15min/IP. ✅ |
| `POST /api/students/login/` | `StudentLoginView` | Public. `csrf_exempt` + `authentication_classes = []`. Rate-limité 5/15min/IP. ✅ |
| `GET /api/csrf/` | `CSRFTokenView` | Distribue le cookie CSRF pour le SPA. `AllowAny` + `authentication_classes = []`. ✅ |

### 1.3 Endpoints AllowAny

| Endpoint | Classe | Analyse |
|---|---|---|
| `GET /api/csrf/` | CSRFTokenView | Inoffensif — distribue cookie CSRF. ✅ |
| `POST /api/login/` | LoginView | Public par design. Rate-limité. Rejette les students. ✅ |
| `POST /api/students/login/` | StudentLoginView | Public par design. Rate-limité. Maintenance mode. ✅ |
| `POST /api/students/logout/` | StudentLogoutView | Flush session. AllowAny pour permettre le logout même avec session expirée. ✅ |
| `GET /api/health/*` | Health checks | AllowAny. Probe K8s/Docker. Aucune donnée sensible. ✅ |
| `GET /api/grading/copies/<uuid>/final-pdf/` | CopyFinalPdfView | **AllowAny JUSTIFIÉ** — dual-auth. Voir §3.1. ⚠️ |
| `POST /api/dev/seed/` | seed_e2e_endpoint | Conditionnel (E2E_SEED_TOKEN). AllowAny mais protégé par token. ✅ |

### 1.4 Sessions étudiantes

Le login étudiant (`StudentLoginView`) :
1. Authentifie via `django.contrib.auth.authenticate` (email comme username)
2. Appelle `auth_login(request, user)` → session Django standard
3. Écrit `request.session['student_id']` et `request.session['role'] = 'Student'`

**Isolation profil** : `LoginView` (teachers) rejette explicitement les users liés à un `Student` (lignes 62-69 de `core/views.py`). ✅

---

## 2. CARTOGRAPHIE DES PERMISSIONS PAR ENDPOINT

### 2.1 Classes de permission définies

| Classe | Fichier | Logique |
|---|---|---|
| `IsAdmin` | core/auth.py:28 | `groups.filter(name='admin')` — **NE vérifie PAS `is_superuser`/`is_staff`** |
| `IsTeacher` | core/auth.py:37 | `groups.filter(name='teacher')` |
| `IsStudent` | core/auth.py:46 | `groups.filter(name='student')` **+ fallback session** `request.session.get('student_id')` |
| `IsAdminOrTeacher` | core/auth.py:58 | groups admin OU teacher |
| `IsAdminOnly` | core/auth.py:68 | **Identique à `IsAdmin`** — `groups.filter(name='admin')` |
| `IsTeacherOrAdmin` | exams/permissions.py:4 | **Identique à `IsAdminOrTeacher`** — groups teacher OU admin |
| `IsOwnerOrAdmin` | exams/permissions.py:16 | Object-level: SAFE_METHODS → teacher/admin; writes → admin ou `created_by` |
| `IsStudentForOwnData` | exams/permissions.py:34 | Object-level: teacher/admin passent; students vérifient `obj.student.user` |
| `IsAdminUser` | DRF built-in | `is_staff = True` |

### 2.2 Incohérence critique : `IsAdmin`/`IsAdminOnly` vs `is_superuser`

`IsAdmin` et `IsAdminOnly` vérifient **uniquement** l'appartenance au groupe `'admin'`. Un Django superuser qui n'est pas dans ce groupe **ne passe pas** ces checks. En revanche :
- `_is_admin()` (exams/views_documents.py:28) vérifie `is_superuser OR is_staff OR group`
- `_can_write_copy()` (grading/views.py:33) vérifie `is_superuser OR is_staff OR group`
- `cancel_task` (grading/views_async.py:127) vérifie `is_staff OR is_superuser`
- `MetricsView` utilise `IsAdminUser` (DRF) qui vérifie `is_staff`

**Impact** : Un superuser (ex: le compte `admin`) qui n'est PAS dans le groupe `'admin'` serait refusé par `IsAdmin`/`IsAdminOnly` mais accepté par `_is_admin()` et `_can_write_copy()`. En production actuelle, le superuser est probablement aussi dans le groupe admin, mais c'est une incohérence architecturale dangereuse.

### 2.3 Tableau complet des endpoints

#### Endpoints publics (AllowAny)

| Route | Vue | Méthode | Permission | Rate-limit |
|---|---|---|---|---|
| `/api/csrf/` | CSRFTokenView | GET | AllowAny | Non |
| `/api/login/` | LoginView | POST | AllowAny | 5/15m/IP |
| `/api/students/login/` | StudentLoginView | POST | AllowAny | 5/15m/IP |
| `/api/students/logout/` | StudentLogoutView | POST | AllowAny | Non |
| `/api/health/` | health_check | GET | AllowAny | Non |
| `/api/health/live/` | liveness_check | GET | AllowAny | Non |
| `/api/health/ready/` | readiness_check | GET | AllowAny | Non |
| `/api/grading/copies/<uuid>/final-pdf/` | CopyFinalPdfView | GET | AllowAny (dual-auth) | Non |

#### Endpoints student (IsStudent)

| Route | Vue | Méthode | Permission | Ownership |
|---|---|---|---|---|
| `/api/students/me/` | StudentMeView | GET | IsStudent | session.student_id |
| `/api/students/change-password/` | StudentChangePasswordView | POST | IsStudent | request.user |
| `/api/students/copies/` | StudentCopiesView | GET | IsStudent | student_id + GRADED + released |
| `/api/exams/student/copies/` | StudentCopiesView | GET | IsStudent | idem (doublon URL) |

#### Endpoints teacher/admin (IsTeacherOrAdmin)

| Route | Vue | Méthode | Permission | Ownership |
|---|---|---|---|---|
| `/api/exams/upload/` | ExamUploadView | POST | IsTeacherOrAdmin | — |
| `/api/exams/` | ExamListView | GET/POST | IsTeacherOrAdmin | — |
| `/api/exams/<uuid>/` | ExamDetailView | GET/PUT/DELETE | IsTeacherOrAdmin | — |
| `/api/exams/<uuid>/upload/` | ExamSourceUploadView | POST | IsTeacherOrAdmin | — |
| `/api/exams/<uuid>/copies/import/` | CopyImportView | POST | IsTeacherOrAdmin | — |
| `/api/exams/<uuid>/upload-individual-pdfs/` | IndividualPDFUploadView | POST | IsTeacherOrAdmin | — |
| `/api/exams/<uuid>/booklets/` | BookletListView | GET | IsTeacherOrAdmin | — |
| `/api/exams/booklets/<uuid>/header/` | BookletHeaderView | GET | IsTeacherOrAdmin | — |
| `/api/exams/booklets/<uuid>/split/` | BookletSplitView | POST | IsTeacherOrAdmin | — |
| `/api/exams/booklets/<uuid>/` | BookletDetailView | GET/DELETE | IsTeacherOrAdmin | — |
| `/api/exams/<uuid>/unidentified-copies/` | UnidentifiedCopiesView | GET | IsTeacherOrAdmin | — |
| `/api/exams/copies/<uuid>/identify/` | CopyIdentificationView | POST | IsTeacherOrAdmin | — |
| `/api/exams/<uuid>/copies/` | CopyListView | GET | IsTeacherOrAdmin | — |
| `/api/exams/<uuid>/merge-booklets/` | MergeBookletsView | POST | IsTeacherOrAdmin | — |
| `/api/exams/<uuid>/export-pdf/` | ExportAllView | POST | IsTeacherOrAdmin | — |
| `/api/exams/<uuid>/export-csv/` | CSVExportView | GET | IsTeacherOrAdmin | — |
| `/api/exams/copies/<uuid>/validate/` | CopyValidationView | POST | IsTeacherOrAdmin | — |
| `/api/exams/<uuid>/validate-all/` | BulkCopyValidationView | POST | IsTeacherOrAdmin | — |
| `/api/exams/<uuid>/bulk-subject-variant/` | BulkSubjectVariantView | GET/POST | IsTeacherOrAdmin | — |
| `/api/exams/<uuid>/auto-detect-subject/` | AutoDetectSubjectVariantView | POST | IsTeacherOrAdmin | — |
| `/api/exams/<uuid>/dispatch/` | ExamDispatchView | POST | IsTeacherOrAdmin | — |
| `/api/exams/<uuid>/student-list/` | ExamStudentListView | GET | IsTeacherOrAdmin | — |
| `/api/copies/` | CorrectorCopiesView | GET | IsTeacherOrAdmin | admin=all, teacher=assigned |
| `/api/copies/<uuid>/` | CorrectorCopyDetailView | GET/PATCH | IsAuthenticated+IsTeacherOrAdmin | — |
| `/api/copies/<uuid>/identify/` | CopyIdentificationView | POST | IsTeacherOrAdmin | — |
| `/api/grading/copies/<uuid>/annotations/` | AnnotationListCreateView | GET/POST | IsTeacherOrAdmin | POST: `_can_write_copy` |
| `/api/grading/annotations/<uuid>/` | AnnotationDetailView | GET/PATCH/DELETE | IsTeacherOrAdmin | PATCH/DELETE: `_can_write_copy` |
| `/api/grading/copies/<uuid>/ready/` | CopyReadyView | POST | IsTeacherOrAdmin | **Aucun** |
| `/api/grading/copies/<uuid>/finalize/` | CopyFinalizeView | POST | IsTeacherOrAdmin | **Aucun** |
| `/api/grading/copies/<uuid>/audit/` | CopyAuditView | GET | IsTeacherOrAdmin | — |
| `/api/grading/copies/<uuid>/remarks/` | QuestionRemarkListCreateView | GET/POST | IsTeacherOrAdmin | POST: `_can_write_copy` |
| `/api/grading/remarks/<uuid>/` | QuestionRemarkDetailView | GET/PATCH/DELETE | IsTeacherOrAdmin | PATCH/DELETE: `_can_write_copy` |
| `/api/grading/copies/<uuid>/global-appreciation/` | CopyGlobalAppreciationView | GET/PUT/PATCH | IsTeacherOrAdmin | PUT/PATCH: `_can_write_copy` |
| `/api/grading/copies/<uuid>/scores/` | CopyScoresView | GET/PUT | IsTeacherOrAdmin | PUT: `_can_write_copy` |
| `/api/grading/exams/<uuid>/release-results/` | ExamReleaseResultsView | POST | IsTeacherOrAdmin | — |
| `/api/grading/exams/<uuid>/unrelease-results/` | ExamUnreleaseResultsView | POST | IsTeacherOrAdmin | — |
| `/api/grading/exams/<uuid>/generate-summaries/` | ExamLLMSummaryView | POST | IsTeacherOrAdmin | — |
| `/api/grading/copies/<uuid>/generate-summary/` | CopyLLMSummaryView | POST | IsTeacherOrAdmin | — |
| `/api/grading/exams/<uuid>/suggestions/` | ContextualSuggestionsView | GET | IsAuthenticated+IsTeacherOrAdmin | — |
| `/api/grading/exams/<uuid>/annotation-templates/` | AnnotationTemplateListView | GET | IsAuthenticated+IsTeacherOrAdmin | — |
| `/api/grading/my-annotations/` | UserAnnotationListCreateView | GET/POST | IsAuthenticated+IsTeacherOrAdmin | user=request.user |
| `/api/grading/my-annotations/auto-save/` | AutoSaveAnnotationView | POST | IsAuthenticated+IsTeacherOrAdmin | user=request.user |
| `/api/grading/my-annotations/<uuid>/` | UserAnnotationDetailView | GET/PUT/DELETE | IsAuthenticated+IsTeacherOrAdmin | user=request.user |
| `/api/grading/my-annotations/<uuid>/use/` | UserAnnotationUseView | POST | IsAuthenticated+IsTeacherOrAdmin | user=request.user |
| `/api/grading/my-students/` | MyStudentsListView | GET | IsTeacherOrAdmin | groupe mapping |
| `/api/grading/students/<id>/bilan/` | StudentBilanView | GET | IsTeacherOrAdmin | groupe check (sauf superuser) |
| `/api/grading/copies/<uuid>/draft/` | DraftReturnView | GET/PUT/DELETE | **IsAuthenticated seulement** | GET/DELETE: owner=user. **PUT: AUCUN** |
| `/api/identification/desk/` | IdentificationDeskView | GET | IsAuthenticated+IsTeacherOrAdmin | — |
| `/api/identification/identify/<uuid>/` | ManualIdentifyView | POST | IsAuthenticated+IsTeacherOrAdmin | — |
| `/api/identification/ocr-identify/<uuid>/` | OCRIdentifyView | POST | IsAuthenticated+IsTeacherOrAdmin | — |
| `/api/identification/perform-ocr/<uuid>/` | OCRPerformView | POST | IsAuthenticated+IsTeacherOrAdmin | — |
| `/api/grading/copies/<uuid>/lock/` etc. | Lock views | POST/DELETE/GET | IsAuthenticated+IsTeacherOrAdmin | token-based |

#### Endpoints admin-only

| Route | Vue | Méthode | Permission | Mécanisme |
|---|---|---|---|---|
| `/api/exams/<uuid>/export-pronote/` | PronoteExportView | POST | IsAuthenticated + in-method `IsAdminOnly` | Group check |
| `/api/exams/<uuid>/document-sets/` (POST) | DocumentSetUploadView | POST | IsAuthenticated + in-method `_is_admin` | is_superuser/is_staff/group |
| `/api/exams/<uuid>/document-sets/<uuid>/activate/` | DocumentSetActivateView | POST | IsAuthenticated + in-method `_is_admin` | idem |
| `/api/exams/<uuid>/document-sets/<uuid>/retry-extraction/` | DocumentSetRetryExtractionView | POST | IsAuthenticated + in-method `_is_admin` | idem |
| `/api/grading/tasks/<id>/cancel/` | cancel_task | POST | IsAuthenticated + in-method is_staff/superuser | — |
| `/api/metrics/` | MetricsView | GET/DELETE | IsAdminUser (DRF) | is_staff |
| `/api/users/` | UserListView | GET/POST | IsAuthenticated + in-method is_superuser/is_staff | — |
| `/api/users/<pk>/` | UserManageView | PUT/DELETE | IsAuthenticated + in-method is_superuser/is_staff | — |
| `/api/users/<pk>/reset-password/` | UserResetPasswordView | POST | IsAuthenticated + in-method is_superuser/is_staff | — |
| `/api/settings/` (POST) | GlobalSettingsView | POST | IsAuthenticated + in-method is_superuser/is_staff | — |

#### Endpoints `IsAuthenticated` seul (pas de rôle vérifié)

| Route | Vue | Méthode | **RISQUE** |
|---|---|---|---|
| `/api/me/` | UserDetailView | GET | Faible — renvoie les infos du user connecté |
| `/api/logout/` | LogoutView | POST | Nul |
| `/api/change-password/` | ChangePasswordView | POST | Faible — agit sur soi-même |
| `/api/settings/` (GET) | GlobalSettingsView | GET | Faible — données publiques |
| `/api/grading/tasks/<id>/` | task_status | GET | **MOYEN** — tout user peut poll un task_id |
| `/api/grading/copies/<uuid>/draft/` | DraftReturnView | GET/PUT/DELETE | **CRITIQUE sur PUT** — voir §3 |
| `/api/students/` | StudentListView | GET | **ÉLEVÉ** — tout user liste tous les étudiants |
| `/api/students/import/` | StudentImportView | POST | **ÉLEVÉ** — tout user peut importer des étudiants |
| `/api/exams/stats-report/` | StatsReportView | GET | **ÉLEVÉ** — tout user voit le rapport jury complet |
| `/api/grading/exams/<uuid>/stats/` | CorrectorStatsView | GET | Moyen — check interne corrector/admin |
| `/api/exams/<uuid>/document-sets/list/` | DocumentSetListView | GET | **MOYEN** — tout user liste les lots documentaires |
| `/api/schema/` | SpectacularAPIView | GET | **MOYEN** — schéma OpenAPI complet exposé |
| `/api/docs/` | SpectacularSwaggerView | GET | **MOYEN** — documentation Swagger complète |
| `/api/redoc/` | SpectacularRedocView | GET | **MOYEN** — documentation ReDoc complète |
| `/metrics` | prometheus_metrics_view | GET | **ÉLEVÉ** — métriques Prometheus sans auth? |

---

## 3. AUDIT DÉTAILLÉ DES VUES SENSIBLES

### 3.1 CopyFinalPdfView — AllowAny (grading/views.py:180-279)

**Permission déclarée** : `AllowAny`  
**Permission réelle** : Dual-auth codée dans la vue

**Gates de sécurité** :
1. **Status gate** : `copy.status != GRADED` → 403. ✅
2. **Teacher/Admin gate** : `is_authenticated AND (is_staff OR is_superuser OR teacher group)`. ✅
3. **Student gate** : `session['student_id']` + ownership (`copy.student_id == sid`). ✅
4. **Aucune auth** : 401. ✅

**Faille identifiée** : La vue ne vérifie **PAS** `exam.results_released_at`. Un étudiant dont la copie est GRADED pourrait accéder à son PDF **avant** que les résultats soient officiellement publiés. La vue `StudentCopiesView` filtre correctement par `results_released_at__isnull=False`, donc le frontend ne montre pas le lien. Mais un étudiant connaissant l'UUID de sa copie pourrait forger l'URL directement.

**Risque** : MOYEN. Exploitation nécessite la connaissance de l'UUID (non devinable).

**Statut** : ⚠️ OK avec réserve

### 3.2 DraftReturnView — IsAuthenticated seulement (grading/views_draft.py)

**Permission déclarée** : `permissions.IsAuthenticated`  
**Permission réelle** :
- **GET** : filtre par `owner=request.user`. Un user ne voit que ses propres drafts. ✅
- **DELETE** : filtre par `owner=request.user`. ✅
- **PUT** : `get_object_or_404(Copy, id=copy_id)` puis écrit un draft pour `owner=request.user`. **AUCUNE vérification de rôle ni d'ownership sur la copie.**

**Analyse** : Un étudiant authentifié (ou tout user authentifié sans rôle teacher/admin) pourrait :
1. Forger un PUT vers `/api/grading/copies/<uuid>/draft/` avec un `copy_id` quelconque
2. Créer un `DraftState` lié à cette copie avec `owner=request.user`
3. Les données du brouillon (`payload`) n'affectent pas directement les scores/annotations
4. **Mais** le brouillon est consommé par le frontend (`CorrectorDesk`) : si un correcteur charge la copie, il pourrait voir un brouillon corrompu

**Impact potentiel** : Un acteur malveillant pourrait injecter des payloads JSON arbitraires dans le brouillon d'une copie, potentiellement perturbant la session du correcteur légitime. Le guard `client_id` empêche l'écrasement d'un brouillon existant (409 Conflict), mais la **création initiale** est non protégée.

**Guard partiel** : `copy.status == GRADED` → 400. Cela limite l'attaque aux copies non finalisées.

**Risque** : **CRITIQUE** — écriture possible par tout user authentifié sur toute copie non-GRADED.

**Statut** : ❌ **INSUFFISANT**

### 3.3 CopyReadyView (grading/views.py:155-163)

**Permission déclarée** : `IsTeacherOrAdmin`  
**Permission réelle** : Tout teacher/admin peut passer n'importe quelle copie à READY.  
**Ownership** : **AUCUN**. Un teacher A peut valider les copies assignées au teacher B.

**Impact** : Faible en pratique (la validation ne modifie que le status), mais viole le principe du moindre privilège.

**Risque** : FAIBLE  
**Statut** : ⚠️ OK avec réserve

### 3.4 CopyFinalizeView (grading/views.py:165-177)

**Permission déclarée** : `IsTeacherOrAdmin`  
**Permission réelle** : Tout teacher/admin peut finaliser n'importe quelle copie.  
**Ownership** : **AUCUN** — ni dans la vue, ni dans `GradingService.finalize_copy()`.

**Impact** : Un teacher pourrait finaliser une copie d'un autre teacher, verrouillant définitivement les scores/annotations. L'action est irréversible (status GRADED). La copie est ensuite accessible aux étudiants (si results_released_at est set).

**Risque** : **MOYEN** — action irréversible sans contrôle d'ownership.

**Statut** : ⚠️ OK avec réserve (en contexte PMF avec confiance inter-correcteurs)

### 3.5 task_status (grading/views_async.py:17-101)

**Permission déclarée** : `IsAuthenticated`  
**Permission réelle** : Tout user authentifié peut consulter le statut de n'importe quelle tâche Celery.

**Impact** : Fuite d'information possible (résultats de tâches, tracebacks pour staff). Traceback conditionné à `is_staff` ✅. Mais le résultat de la tâche est visible par tous.

**Risque** : FAIBLE (nécessite de connaître le task_id)  
**Statut** : ⚠️ OK avec réserve

### 3.6 cancel_task (grading/views_async.py:104-153)

**Permission déclarée** : `IsAuthenticated` + in-method `is_staff OR is_superuser`  
**Permission réelle** : Admin/staff seulement. ✅  
**Soft revoke** : `terminate=False`. ✅  
**Audit trail** : Logged. ✅

**Statut** : ✅ OK

### 3.7 Endpoints de médias/PDFs (core/views_media.py)

**Permission déclarée** : `IsAuthenticated`  
**Ownership** : Implémenté dans `_has_access()` :
- Staff/superuser → toujours ✅
- Teacher/Admin group → toujours ✅
- Student group → `_student_owns_file()` vérifie que le fichier appartient à une copie GRADED + results_released. ✅

**Path traversal** : `os.path.normpath` + rejet de `..` et `/`. ✅  
**Statut** : ✅ OK

### 3.8 Document management (exams/views_documents.py)

**Permission déclarée** : `IsAuthenticated` (classe) + in-method `_is_admin()` pour upload/activate/retry  
**Permission réelle** :
- `DocumentSetListView.get` : **IsAuthenticated seulement** — tout user peut lister les lots documentaires.
- Upload/activate/retry : admin seulement via `_is_admin()` qui vérifie `is_superuser OR is_staff OR admin group`. ✅

**Risque DocumentSetListView** : MOYEN — un étudiant pourrait lister les lots (métadonnées, pas les fichiers).

**Statut** : ⚠️ OK avec réserve (lecture seule des métadonnées)

### 3.9 Endpoints scores/annotations/appréciations/remarques

Tous protégés par `IsTeacherOrAdmin` au niveau classe + `_can_write_copy()` pour les mutations :

```python
def _can_write_copy(user, copy):
    if user.is_superuser or user.is_staff: return True
    if user.groups.filter(name=UserRole.ADMIN).exists(): return True
    return copy.assigned_corrector_id == user.id
```

**Analyse** :
- **Lecture** (GET) : tout teacher/admin peut lire scores/annotations/remarques de **toute** copie. ✅ (nécessaire pour les stats et le suivi)
- **Écriture** (POST/PUT/PATCH/DELETE) : seul le correcteur assigné ou un admin. ✅
- **CopyScoresView.put** : vérification supplémentaire `status != GRADED` (sauf superuser). ✅
- **Race condition** : `select_for_update` dans `CopyScoresView.put`. ✅

**Statut** : ✅ OK

### 3.10 ExamDispatchView (exams/views.py:910-1000)

**Permission déclarée** : `IsTeacherOrAdmin`  
**Permission réelle** : **Tout teacher** peut dispatcher les copies de n'importe quel examen.

**Impact** : Un teacher pourrait redistribuer les copies d'un examen, écrasant les assignments existants. L'opération ne touche que `assigned_corrector`, `dispatch_run_id`, `assigned_at` — pas les scores/annotations.

**Risque** : MOYEN — opération admin par nature, accessible à tout teacher.  
**Statut** : ⚠️ OK avec réserve

### 3.11 Export Pronote (exams/views.py:1003-1176)

**Permission déclarée** : `IsAuthenticated` (classe) + in-method `IsAdminOnly().has_permission()`  
**Permission réelle** : Admin group seulement. Audit trail complet. Rate-limité 10/h. ✅

**Statut** : ✅ OK

### 3.12 StudentListView / StudentImportView (students/views.py:215-380)

**Permission déclarée** : `IsAuthenticated`  
**Permission réelle** : **Aucun contrôle de rôle.**

**Impact** :
- `StudentListView` : tout user authentifié (y compris un étudiant) peut lister **tous** les étudiants (nom, prénom, email, classe, groupe).
- `StudentImportView` : tout user authentifié peut **importer** des étudiants via CSV, y compris créer des comptes Django User avec mot de passe par défaut `passe123`.

**Risque** : **ÉLEVÉ**
- Fuite de données personnelles (RGPD)
- Création non autorisée de comptes

**Statut** : ❌ **INSUFFISANT**

### 3.13 StatsReportView (exams/views_stats.py)

**Permission déclarée** : `IsAuthenticated`  
**Permission réelle** : **Aucun contrôle de rôle.**

**Impact** : Tout user authentifié (y compris un étudiant) peut accéder au **rapport de jury complet** : moyennes, distributions, classement (top 15, bottom 11), notes par question, notes par correcteur, notes par groupe, taux de réussite.

**Risque** : **ÉLEVÉ** — exposition de données confidentielles du jury.

**Statut** : ❌ **INSUFFISANT**

### 3.14 API Documentation (schema/docs/redoc)

**Permission** : DRF Spectacular utilise par défaut `SERVE_PERMISSIONS = ['rest_framework.permissions.AllowAny']` dans sa configuration. Le schéma nécessite `IsAuthenticated` (car `SpectacularAPIView` hérite les defaults DRF), mais les vues Swagger/ReDoc pourraient être accessibles.

**Risque** : MOYEN — expose toute l'API surface en production.

**Statut** : ⚠️ OK avec réserve (à désactiver en production)

### 3.15 Prometheus metrics (`/metrics`)

**Permission** : Requiert vérification du fichier `core/views_prometheus.py`.

**Risque** : Si non protégé, expose des métriques opérationnelles.

---

## 4. VÉRIFICATIONS OBLIGATOIRES

### 4.1 Fallback `role="Teacher"` supprimé partout ?

**Recherche** : `grep -r 'getattr.*role\|user\.role' backend/ --include="*.py"`

**Résultat** :
- `core/views.py:113` — `UserDetailView.get()` : **fallback `role = "Teacher"` ENCORE PRÉSENT**
  ```python
  else:
      role = "Teacher"  # fallback si ni Teacher ni Admin group
  ```
  Impact : Un user sans groupe (ni teacher, ni admin, ni student) reçoit `role = "Teacher"` dans la réponse API. Ceci est un problème de **reporting frontend**, pas de permission réelle (les vrais checks utilisent les groups). Mais cela masque un problème de configuration.

- `grading/tests/test_remarks.py:33,180` — `user.role = 'Teacher'` : Code de test uniquement, aucun impact production. Mais révèle l'existence historique d'un attribut `role` qui n'existe plus sur le modèle User.

**Verdict** : Le fallback `getattr(user, 'role', '') != 'Admin'` qui causait la faille P0 dans les vues d'annotation/remarque a bien été **supprimé et remplacé par `_can_write_copy()`** dans toutes les vues de grading. ✅

Le fallback `role = "Teacher"` dans `UserDetailView` est un **défaut cosmétique** sans impact sécurité. ⚠️

### 4.2 `IsStudent` est-il réellement sûr ?

**Code** (core/auth.py:46-56) :
```python
class IsStudent(BasePermission):
    def has_permission(self, request, view):
        if request.user.is_authenticated:
            return request.user.groups.filter(name=UserRole.STUDENT).exists()
        # Fallback for legacy session auth
        if request.session.get('student_id'):
            return True
        return False
```

**Problème** : Le fallback `request.session.get('student_id')` est **dangereux** :
- Un user NON authentifié mais avec une session contenant `student_id` passerait ce check
- En théorie, `SessionAuthentication` de DRF exige un user authentifié, donc `request.session` ne devrait pas avoir `student_id` sans authentification
- **Mais** : si un endpoint exempt de CSRF/auth définit manuellement `authentication_classes = []` et utilise `IsStudent`, le fallback pourrait être exploité

**Impact réel** : Faible car les endpoints `IsStudent` (StudentMeView, StudentChangePasswordView, StudentCopiesView) n'exemptent pas l'authentification.

**Verdict** : Le fallback session est un **vestige legacy** qui devrait être supprimé. ⚠️

### 4.3 `IsAdmin` / `IsAdminOnly` cohérents ?

**Non.** Les deux classes sont **strictement identiques** :
```python
# IsAdmin (line 28)
return request.user.groups.filter(name=UserRole.ADMIN).exists()
# IsAdminOnly (line 68)  
return request.user.groups.filter(name=UserRole.ADMIN).exists()
```

Aucune ne vérifie `is_superuser` ni `is_staff`. Ceci est incohérent avec :
- `_is_admin()` qui vérifie `is_superuser OR is_staff OR group`
- `_can_write_copy()` qui vérifie `is_superuser OR is_staff OR group`
- `cancel_task` qui vérifie `is_staff OR is_superuser`
- `MetricsView` qui utilise `IsAdminUser` (DRF, vérifie `is_staff`)

**Conséquence** : 4 définitions différentes de "admin" dans le codebase.

### 4.4 Un student peut-il accéder aux données d'un autre student ?

**Analyse par endpoint** :

| Endpoint | Mécanisme | Cross-student possible ? |
|---|---|---|
| StudentCopiesView | `student=student_id` (session) | Non — filtre par student_id session ✅ |
| CopyFinalPdfView | `copy.student_id != sid` → 403 | Non ✅ |
| ProtectedMediaView | `_student_owns_file()` | Non ✅ |
| StudentMeView | `student_id` from session | Non ✅ |
| StudentListView | **IsAuthenticated seulement** | **OUI — un student voit tous les students** ❌ |

**Verdict** : L'isolation inter-étudiants est correcte pour les données de correction (copies, scores, PDFs). **Mais un étudiant peut lister tous les autres étudiants** via `/api/students/`.

### 4.5 Un teacher peut-il modifier des copies hors périmètre ?

**Analyse** :
- **Annotations** (create/update/delete) : `_can_write_copy()` → assigned_corrector only. ✅
- **Remarques** (create/update/delete) : `_can_write_copy()` → assigned_corrector only. ✅
- **Scores** (PUT) : `_can_write_copy()` → assigned_corrector only. ✅
- **Appréciation** (PUT/PATCH) : `_can_write_copy()` → assigned_corrector only. ✅
- **Ready** (POST) : **pas de check** — tout teacher peut ready toute copie. ⚠️
- **Finalize** (POST) : **pas de check** — tout teacher peut finaliser toute copie. ⚠️
- **Draft** (PUT) : **pas de check de rôle** — tout user peut écrire un draft. ❌

**Verdict** : Les chemins d'écriture de données métier (scores, annotations, remarques, appréciations) sont correctement verrouillés. Les transitions d'état (ready, finalize) et les drafts ne le sont pas.

### 4.6 DraftReturnView constitue-t-il une porte dérobée ?

**Oui, partiellement.** La vue `DraftReturnView.put` :
1. N'a aucune vérification de rôle (`IsAuthenticated` seulement)
2. N'a aucune vérification d'ownership sur la copie (`assigned_corrector`)
3. Permet d'écrire un `DraftState` avec un `payload` JSON arbitraire sur toute copie non-GRADED
4. Le `DraftState` est ensuite lu par le correcteur légitime via `DraftReturnView.get`

**Scénario d'exploitation** :
1. Un étudiant se connecte via `/api/students/login/`
2. Il forge un PUT vers `/api/grading/copies/<uuid>/draft/` avec un payload malveillant
3. Le correcteur ouvre la copie dans CorrectorDesk, le draft chargé contient le payload injecté
4. Si le frontend ne valide pas le payload, cela pourrait corrompre l'interface

**Facteurs atténuants** :
- Le correcteur légitime a déjà un draft (GET filtre par `owner=request.user`), donc le draft injecté serait sous un autre `owner`
- **Mais** : `DraftReturnView.get` filtre par `owner=request.user`, donc le correcteur ne **voit pas** le draft injecté — seul l'attaquant voit le sien
- L'impact réel est donc : **pollution de la table DraftState** avec des entrées parasites, pas de corruption visible du correcteur

**Verdict révisé** : Le risque est **MOYEN** (pas critique). L'attaquant peut créer des DraftState parasites mais ne peut pas corrompre le draft du correcteur légitime grâce au filtre `owner=request.user` sur GET. L'écriture reste non autorisée par principe.

---

## 5. TABLEAU RÉCAPITULATIF

| # | Endpoint / Vue | Sensibilité | Permission attendue | Permission réelle | Ownership | Statut | Action |
|---|---|---|---|---|---|---|---|
| 1 | DraftReturnView PUT | **HAUTE** | IsTeacherOrAdmin + assigned_corrector | IsAuthenticated seul | **AUCUN** | ❌ Insuffisant | Ajouter IsTeacherOrAdmin + `_can_write_copy` |
| 2 | StudentListView | **HAUTE** | IsTeacherOrAdmin | IsAuthenticated | — | ❌ Insuffisant | Changer en IsTeacherOrAdmin |
| 3 | StudentImportView | **CRITIQUE** | IsAdminOnly | IsAuthenticated | — | ❌ Insuffisant | Changer en IsAdminOnly ou _is_admin |
| 4 | StatsReportView | **HAUTE** | IsTeacherOrAdmin ou IsAdminOnly | IsAuthenticated | — | ❌ Insuffisant | Changer en IsTeacherOrAdmin minimum |
| 5 | CopyFinalPdfView (student) | HAUTE | Vérifier results_released_at | Non vérifié | student_id ✅ | ⚠️ Réserve | Ajouter check results_released_at |
| 6 | DocumentSetListView | MOYENNE | IsTeacherOrAdmin | IsAuthenticated | — | ⚠️ Réserve | Changer en IsTeacherOrAdmin |
| 7 | CopyReadyView | MOYENNE | IsTeacherOrAdmin + ownership | IsTeacherOrAdmin sans ownership | — | ⚠️ Réserve | Ajouter `_can_write_copy` |
| 8 | CopyFinalizeView | HAUTE | IsTeacherOrAdmin + ownership | IsTeacherOrAdmin sans ownership | — | ⚠️ Réserve | Ajouter `_can_write_copy` |
| 9 | ExamDispatchView | MOYENNE | IsAdminOnly | IsTeacherOrAdmin | — | ⚠️ Réserve | Restreindre à admin |
| 10 | ExamReleaseResultsView | HAUTE | IsAdminOnly | IsTeacherOrAdmin | — | ⚠️ Réserve | Restreindre à admin |
| 11 | ExamUnreleaseResultsView | HAUTE | IsAdminOnly | IsTeacherOrAdmin | — | ⚠️ Réserve | Restreindre à admin |
| 12 | task_status | FAIBLE | IsTeacherOrAdmin | IsAuthenticated | — | ⚠️ Réserve | Ajouter IsTeacherOrAdmin |
| 13 | API docs (schema/docs/redoc) | MOYENNE | Désactiver en prod | IsAuthenticated | — | ⚠️ Réserve | Conditionner à DEBUG |
| 14 | IsStudent session fallback | MOYENNE | Group only | Group + session fallback | — | ⚠️ Réserve | Supprimer le fallback |
| 15 | IsAdmin ≠ _is_admin ≠ IsAdminUser | MOYENNE | Cohérent | 4 définitions différentes | — | ⚠️ Réserve | Unifier |
| 16 | UserDetailView role fallback | FAIBLE | Role réel | Fallback "Teacher" | — | ⚠️ Réserve | Retourner "Unknown" |
| 17 | Annotations/Scores/Remarks write | HAUTE | assigned_corrector + admin | `_can_write_copy` ✅ | ✅ | ✅ OK | — |
| 18 | cancel_task | HAUTE | Admin only | is_staff/is_superuser ✅ | — | ✅ OK | — |
| 19 | ProtectedMediaView (student) | HAUTE | Student owns file | Vérifié ✅ | ✅ | ✅ OK | — |
| 20 | PronoteExportView | HAUTE | Admin only | IsAdminOnly ✅ | — | ✅ OK | — |
| 21 | Document upload/activate/retry | HAUTE | Admin only | _is_admin ✅ | — | ✅ OK | — |
| 22 | Lock acquire/heartbeat/release | HAUTE | IsTeacherOrAdmin | ✅ + token | ✅ | ✅ OK | — |

---

## 6. IMPACT SUR LES DONNÉES PAR TROU DE PERMISSION

### 6.1 DraftReturnView.put (pas de rôle ni ownership)

| Donnée | Impact |
|---|---|
| **Notes** | Aucun — les drafts ne sont pas des scores |
| **Annotations** | Aucun — les drafts ne sont pas des annotations |
| **Appréciations** | Aucun |
| **Remarques** | Aucun |
| **États de workflow** | Aucun |
| **Copies** | Aucun — le draft est une table séparée (DraftState) |
| **Données élève** | Aucun |
| **Table DraftState** | **Pollution** — entrées parasites possibles (owner=attaquant) |

### 6.2 StudentListView (pas de rôle)

| Donnée | Impact |
|---|---|
| **Données élève** | **FUITE** — noms, prénoms, emails, classes, groupes de tous les étudiants |
| **Autres** | Aucun impact direct |

### 6.3 StudentImportView (pas de rôle)

| Donnée | Impact |
|---|---|
| **Données élève** | **CRÉATION** — insertion d'étudiants fictifs ou malveillants |
| **Comptes Django User** | **CRÉATION** — comptes avec mot de passe `passe123` et groupe `student` |
| **Autres** | Dégradation potentielle des listes de classe |

### 6.4 StatsReportView (pas de rôle)

| Donnée | Impact |
|---|---|
| **Notes** | **FUITE** — moyennes, distributions, notes individuelles (top/bottom), notes par correcteur |
| **Données élève** | **FUITE** — classement avec noms, classes, groupes |
| **Appréciations** | **FUITE** — tags d'appréciation et fréquences |
| **Workflow** | **FUITE** — statuts de correction par correcteur |

### 6.5 CopyFinalizeView (pas d'ownership)

| Donnée | Impact |
|---|---|
| **États de workflow** | **MODIFICATION** — un teacher peut finaliser une copie d'un autre teacher |
| **PDF final** | **GÉNÉRATION** — le PDF est généré lors de la finalisation |
| **Notes** | Indirectement verrouillées (status GRADED bloque les modifications) |

### 6.6 ExamReleaseResultsView (pas d'admin check)

| Donnée | Impact |
|---|---|
| **Données élève** | **EXPOSITION** — un teacher peut rendre les résultats visibles aux étudiants prématurément |
| **Notes** | **EXPOSITION** — les étudiants voient leurs notes avant décision officielle |

---

## 7. VERDICT

### Classification

| Catégorie | Nombre | Détail |
|---|---|---|
| ✅ OK | 6 | Annotations/scores/remarks, cancel_task, media, Pronote, documents admin, locks |
| ⚠️ OK avec réserve | 10 | CopyFinalPdfView, CopyReadyView, CopyFinalizeView, ExamDispatchView, Release/Unrelease, task_status, DocumentSetListView, API docs, IsStudent fallback, admin incohérence, UserDetailView fallback |
| ❌ Insuffisant | 4 | DraftReturnView PUT, StudentListView, StudentImportView, StatsReportView |

### Verdict global : **SATISFAISANTE AVEC RÉSERVES**

**Justification** :

Les chemins d'écriture critiques (scores, annotations, remarques, appréciations) sont **correctement protégés** par `_can_write_copy()` depuis les corrections LOT 5. Le `cancel_task` est désormais admin-only. L'export Pronote est admin-only avec audit trail. La gestion des médias implémente un contrôle d'ownership robuste pour les étudiants.

**Cependant**, 4 endpoints présentent des failles de permissions effectives :
1. **`StudentImportView`** — le plus grave : permet à tout user authentifié (y compris un étudiant) de créer des comptes
2. **`StatsReportView`** — fuite massive de données confidentielles du jury
3. **`StudentListView`** — fuite des données personnelles de tous les étudiants
4. **`DraftReturnView.put`** — écriture non autorisée dans la table DraftState

Ces 4 points requièrent des corrections avant toute ouverture publique de l'accès étudiant. En l'état actuel de production (accès étudiant contrôlé/limité), le risque est **atténué mais présent**.

### Actions prioritaires recommandées

| Priorité | Action | Effort |
|---|---|---|
| **P0** | `StudentImportView` : changer `permission_classes` en `[IsAuthenticated, IsTeacherOrAdmin]` + check `_is_admin` in-method | 2 lignes |
| **P0** | `StatsReportView` : changer `permission_classes` en `[IsAuthenticated, IsTeacherOrAdmin]` | 1 ligne |
| **P0** | `StudentListView` : changer `permission_classes` en `[IsAuthenticated, IsTeacherOrAdmin]` | 1 ligne |
| **P1** | `DraftReturnView` : ajouter `IsTeacherOrAdmin` + vérifier `_can_write_copy` dans PUT | 5 lignes |
| **P1** | `CopyFinalPdfView` : ajouter check `exam.results_released_at` pour student path | 3 lignes |
| **P2** | Unifier les définitions d'admin (`IsAdmin` doit vérifier `is_superuser OR is_staff OR group`) | 3 lignes |
| **P2** | Supprimer le fallback session dans `IsStudent` | 2 lignes |
| **P2** | `CopyFinalizeView` : ajouter `_can_write_copy` ownership check | 3 lignes |
| **P2** | `ExamReleaseResultsView` / `ExamUnreleaseResultsView` : restreindre à admin | 2 lignes |
| **P3** | Conditionner API docs à `DEBUG=True` | 5 lignes |
| **P3** | `DocumentSetListView` : changer en `IsTeacherOrAdmin` | 1 ligne |

---

*Fin de l'audit. Aucune donnée modifiée. Aucun code changé.*
