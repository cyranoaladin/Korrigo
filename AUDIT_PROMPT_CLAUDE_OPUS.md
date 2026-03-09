# PROMPT D'AUDIT COMPLET — Projet Korrigo (Plateforme de Correction Numérique)

> **Destinataire** : Claude Opus 4.6
> **Date** : 6 mars 2026
> **Auteur** : Alaeddine BEN RHOUMA — Développeur principal & Administrateur système

---

## 0. PRÉAMBULE — CE QUE TU DOIS FAIRE

Tu es mandaté pour réaliser un **audit complet, exhaustif et sans complaisance** du projet **Korrigo**. Cet audit couvre :

1. **Sécurité** (authentification, autorisations, CSRF, CORS, CSP, injection, exposition de données)
2. **Architecture & Design** (cohérence des modèles, séparation des responsabilités, patterns Django/Vue)
3. **Qualité du code** (maintenabilité, dette technique, code mort, conventions, DRY)
4. **Performance** (requêtes N+1, index manquants, cache, pagination)
5. **Fiabilité** (gestion d'erreurs, race conditions, intégrité des données, transactions)
6. **Infrastructure** (Docker, Nginx, déploiement, overlay, monitoring)
7. **Frontend** (état réactif, gestion d'erreurs, UX, accessibilité)
8. **Tests** (couverture, qualité, cas limites)
9. **Conformité** (RGPD, données élèves, audit trail)

**Règle absolue** : ne suppose rien, vérifie tout. Si tu identifies un risque, classe-le par sévérité (🔴 CRITIQUE, 🟠 MAJEUR, 🟡 MINEUR, 🔵 INFO). Donne le fichier exact, la ligne exacte, et le correctif recommandé.

---

## 1. CONTEXTE FONCTIONNEL

### 1.1 Qu'est-ce que Korrigo ?

Korrigo est une **plateforme web de correction numérique d'examens** déployée au **Lycée Pierre Mendès France (AEFE) à Tunis**. Elle gère le cycle complet :

1. **Import** : L'admin uploade des scans PDF de copies d'examen (lots A3 ou fichiers A4 individuels)
2. **Découpage** : Les PDFs A3 sont découpés en fascicules individuels (booklets)
3. **Identification** : Chaque copie est associée à un élève (OCR assisté + validation manuelle)
4. **Dispatch** : Les copies sont assignées aux correcteurs
5. **Correction** : Les correcteurs annotent les copies (annotations vectorielles sur PDF), attribuent des scores par question, rédigent des appréciations
6. **Finalisation** : Les copies corrigées sont finalisées (GRADED), un PDF aplati est généré
7. **LLM Summary** : Un bilan personnalisé est généré par LLM (Ollama qwen2.5:32b) pour chaque élève
8. **Portail élève** : Les élèves accèdent à leurs résultats, copie annotée et bilan via un portail authentifié
9. **Statistiques** : Un rapport de jury dynamique agrège toutes les stats (StatsReport)

### 1.2 Données en production (au 6 mars 2026)

- **2 examens** : `BB_J1` (Bac Blanc Jour 1) et `BB_J2` (Bac Blanc Jour 2)
- **209 copies** : 106 pour BB_J1, 103 pour BB_J2
- **~110 élèves** (classes T.01 à T.10, groupes G1 à G6 + T.04, T.06)
- **8 correcteurs** (enseignants de mathématiques)
- **~4000 annotations**, **~4000 remarques de questions**, **209 scores finalisés**
- **Sujets A/B** : Chaque copie a une variante de sujet (A ou B)
- **Base PostgreSQL** en production, SQLite en dev

### 1.3 Rôles utilisateurs

| Rôle | Groupe Django | Accès |
|------|--------------|-------|
| Admin | `admin` | Tout : import, dispatch, correction, config, gestion users |
| Teacher | `teacher` | Correction des copies assignées, bilan élèves, stats |
| Student | `student` | Portail lecture seule : résultats, copie annotée, bilan LLM |

---

## 2. STACK TECHNIQUE COMPLET

### 2.1 Backend

- **Django 4.2+** avec **Django REST Framework**
- **PostgreSQL 15** (prod) / SQLite (dev)
- **Celery** + **Redis** (tâches asynchrones : PDF processing, LLM summaries)
- **Gunicorn** (serveur WSGI)
- **PyMuPDF 1.23.26** (manipulation PDF)
- **Pillow ≥ 12.1.1** (traitement images)
- **pytesseract** (OCR)
- **openai SDK** (interface Ollama pour LLM)
- **drf-spectacular** (documentation OpenAPI)
- **django-ratelimit** (limitation de requêtes)
- **django-csp** (Content Security Policy)
- **django-cors-headers** (CORS)
- **prometheus-client** (métriques)

### 2.2 Frontend

- **Vue 3.4** (Composition API, `<script setup>`)
- **Vue Router 4** (SPA avec historique HTML5)
- **Pinia** (state management)
- **Axios** (HTTP client avec retry, CSRF auto)
- **TailwindCSS 4** (styling)
- **Lucide Vue Next** (icons)
- **pdfjs-dist** (rendu PDF côté client)
- **Vite 5** (build tool)

### 2.3 Infrastructure

- **Serveur** : Hetzner dédié, IP `88.99.254.59`, domaine `korrigo.labomaths.tn`
- **Docker Compose** (6 services : db, redis, backend, celery, celery-beat, nginx)
- **Nginx** : reverse proxy, sert le frontend SPA, proxy API vers Gunicorn
- **Overlay system** : Les fichiers backend sont montés en read-only depuis `/var/www/labomaths/korrigo/overlay/` dans les containers Docker (59 fichiers overlayés pour backend + celery)
- **Ollama** : Réseau Docker externe `infra_rag_net` pour accéder au LLM local

---

## 3. ARCHITECTURE DU CODE SOURCE

### 3.1 Structure des répertoires

```
viatique__PMF/
├── backend/
│   ├── core/                    # App principale Django
│   │   ├── settings.py          # Config principale (515 lignes)
│   │   ├── settings_prod.py     # Overrides production
│   │   ├── urls.py              # URL racine (64 lignes)
│   │   ├── views.py             # Auth (Login, Logout, CSRF, UserDetail, ChangePassword, UserManage)
│   │   ├── auth.py              # RBAC (IsAdmin, IsTeacher, IsStudent, IsAdminOrTeacher)
│   │   ├── models.py            # GlobalSettings, AuditLog, UserProfile
│   │   ├── middleware/           # RequestID, Metrics
│   │   ├── views_health.py      # Health checks (liveness, readiness)
│   │   ├── views_prometheus.py  # Métriques Prometheus
│   │   └── management/commands/ # backup, restore, ensure_admin, init_pmf, cleanup
│   │
│   ├── exams/                   # App examens
│   │   ├── models.py            # Exam, Booklet, Copy, ExamPDF, ExamDocumentSet, ExamDocument, DocumentTextExtraction, DocumentPage, DocumentChunk (640 lignes)
│   │   ├── views.py             # 55700 bytes — Upload, Booklets, Copies, Merge, Export, Identification, Dispatch, Validation, SubjectVariant
│   │   ├── views_stats.py       # StatsReportView — Rapport de jury dynamique (27k)
│   │   ├── views_documents.py   # Gestion lots documentaires (sujet/corrigé/barème)
│   │   ├── views_analytics.py   # Analytiques uploads
│   │   ├── urls.py              # 75 routes d'examen
│   │   ├── serializers.py       # Sérialiseurs DRF
│   │   ├── permissions.py       # Permissions exam-level
│   │   ├── validators.py        # Validation PDF (taille, MIME, intégrité)
│   │   ├── validators_antivirus.py # Scan antivirus PDF
│   │   └── tasks.py             # Tâches Celery (OCR, PDF processing)
│   │
│   ├── grading/                 # App correction
│   │   ├── models.py            # Annotation, GradingEvent, CopyLock, DraftState, QuestionRemark, Score, AnnotationTemplate, UserAnnotation (495 lignes)
│   │   ├── views.py             # Annotations CRUD, Finalize, Ready, FinalPdf, Audit, Scores, Appreciation, LLM Summary (28k)
│   │   ├── views_lock.py        # Verrouillage optimiste des copies
│   │   ├── views_draft.py       # Auto-save brouillons
│   │   ├── views_annotation_bank.py # Banque d'annotations + suggestions contextuelles
│   │   ├── views_my_students.py # Liste élèves du correcteur + bilan individuel
│   │   ├── views_async.py       # Statut tâches Celery
│   │   ├── services.py          # Logique métier correction (16k)
│   │   ├── urls.py              # 88 lignes de routes
│   │   └── tasks.py             # Tâches Celery grading
│   │
│   ├── students/                # App élèves
│   │   ├── models.py            # Student (first_name, last_name, date_naissance, email, class_name, groupe, user FK)
│   │   ├── views.py             # Login/Logout élève, StudentMe, StudentCopyDetail, ChangePassword (16k)
│   │   └── urls.py              # Routes élèves
│   │
│   ├── identification/          # App OCR & identification
│   │   ├── models.py            # OCRResult
│   │   ├── services.py          # OCR processing (pytesseract)
│   │   └── views.py             # Endpoints identification
│   │
│   └── processing/              # Services de traitement
│       └── services/
│           ├── llm_summary.py   # Génération bilans LLM (Ollama qwen2.5:32b)
│           └── pdf_flattener.py # Aplatissement PDF (PyMuPDF)
│
├── frontend/src/
│   ├── main.js                  # Point d'entrée Vue
│   ├── App.vue                  # Composant racine
│   ├── router/index.js          # 290 lignes — Routes SPA avec guards RBAC
│   ├── stores/
│   │   ├── auth.js              # Pinia store — login, loginStudent, logout, fetchUser
│   │   └── examStore.js         # Pinia store — gestion examen courant
│   ├── services/
│   │   ├── api.js               # Axios instance — CSRF auto, retry avec backoff, gestion 401/403
│   │   └── gradingApi.js        # API spécialisée correction (annotations, scores, locks, drafts)
│   ├── views/
│   │   ├── Home.vue             # Portail d'accueil (cartes de connexion)
│   │   ├── HomeView.vue         # Landing page marketing
│   │   ├── Login.vue            # Login admin/teacher
│   │   ├── AdminDashboard.vue   # Dashboard admin (30k)
│   │   ├── CorrectorDashboard.vue # Dashboard correcteur (23k)
│   │   ├── StatsReport.vue      # Rapport de jury (63k) — consomme /api/exams/stats-report/
│   │   ├── admin/
│   │   │   ├── CorrectorDesk.vue    # Bureau de correction (annotations PDF, scores)
│   │   │   ├── IdentificationDesk.vue # Identification copies-élèves
│   │   │   ├── ImportCopies.vue     # Import de copies
│   │   │   ├── MarkingSchemeView.vue # Éditeur de barème
│   │   │   ├── ExamStudentList.vue  # Liste élèves d'un examen
│   │   │   ├── StapleView.vue      # Agrafage de fascicules
│   │   │   └── UserManagement.vue   # Gestion utilisateurs
│   │   ├── corrector/
│   │   │   ├── MyStudents.vue       # Mes élèves (correcteur)
│   │   │   └── StudentBilan.vue     # Bilan individuel élève
│   │   └── student/
│   │       ├── LoginStudent.vue     # Login élève
│   │       ├── ResultView.vue       # Portail résultats élève
│   │       └── ChangePasswordStudent.vue
│   └── components/              # 16 composants réutilisables
│       ├── Navbar.vue, Footer.vue
│       ├── CanvasLayer.vue      # Couche d'annotations sur PDF
│       ├── GradingSidebar.vue   # Sidebar de correction
│       ├── GradingScaleBuilder.vue # Constructeur de barème
│       ├── PDFViewer.vue        # Rendu PDF (pdfjs-dist)
│       ├── AnnotationSuggestionsPanel.vue # Suggestions d'annotations
│       └── ExamUploadModal.vue  # Modal d'upload
│
└── infra/
    ├── docker/
    │   ├── docker-compose.prod.yml  # 286 lignes — Production (6 services)
    │   ├── docker-compose.yml       # Développement
    │   └── ...                      # staging, e2e, local-prod variants
    └── nginx/
        └── nginx.conf               # 158 lignes — Reverse proxy + SPA + sécurité headers
```

---

## 4. MODÈLES DE DONNÉES — CE QUE TU DOIS VÉRIFIER

### 4.1 Modèles principaux

**`exams.Exam`** — L'examen
- `id` (UUID), `name`, `date`, `upload_mode` (BATCH_A3 | INDIVIDUAL_A4)
- `grading_structure` (JSONField — barème structuré)
- `correctors` (M2M → User)
- `results_released_at` (contrôle publication résultats)
- `pdf_source`, `students_csv`, `pages_per_booklet`

**`exams.Copy`** — La copie d'un élève
- `id` (UUID), `exam` (FK), `anonymous_id` (unique), `status` (STAGING → READY → LOCKED → GRADING_IN_PROGRESS → GRADED)
- `student` (FK → Student, nullable), `is_identified`
- `assigned_corrector` (FK → User), `dispatch_run_id`
- `subject_variant` (A | B)
- `global_appreciation`, `llm_summary`
- `final_pdf`, `pdf_source`
- `locked_by`, `locked_at`, `graded_at`, `validated_at`
- `grading_error_message`, `grading_retries`

**`grading.Score`** — Le score d'une copie
- `copy` (FK), `scores_data` (JSONField — scores par question)
- `final_comment` (appréciation générale)

**`grading.Annotation`** — Annotation vectorielle sur PDF
- `copy` (FK), `page_index`, `x/y/w/h` (coordonnées normalisées [0,1])
- `content`, `type` (COMMENT | HIGHLIGHT | ERROR | BONUS)
- `score_delta`, `created_by`, `version` (optimistic locking)

**`grading.QuestionRemark`** — Remarque par question
- `copy` (FK), `question_id`, `remark`, `created_by`
- `unique_together = ['copy', 'question_id']`

**`grading.CopyLock`** — Verrou d'édition
- `copy` (OneToOne), `owner`, `token`, `locked_at`, `expires_at`

**`grading.DraftState`** — Auto-save brouillon
- `copy`, `owner`, `payload` (JSON), `lock_token`, `version`

**`students.Student`** — L'élève
- `first_name`, `last_name`, `date_naissance`, `email`, `class_name`, `groupe`
- `user` (OneToOne → User, nullable)

**`core.AuditLog`** — Journal d'audit RGPD
- `timestamp`, `user`, `student_id`, `action`, `resource_type`, `resource_id`, `ip_address`, `user_agent`, `metadata`

### 4.2 Points à vérifier sur les modèles

- [ ] **Intégrité référentielle** : Les `on_delete` sont-ils corrects partout ? (PROTECT vs CASCADE vs SET_NULL)
- [ ] **Index** : Les requêtes fréquentes ont-elles des index appropriés ?
- [ ] **Contraintes d'unicité** : `unique_together` vs `UniqueConstraint` — cohérence ?
- [ ] **JSONField** : Les `scores_data` et `grading_structure` sont-ils validés à l'entrée ?
- [ ] **Champs nullable** : Les `null=True, blank=True` sont-ils justifiés ?
- [ ] **Timestamps** : `auto_now_add` vs `auto_now` correctement utilisés ?
- [ ] **Migration drift** : Les modèles locaux correspondent-ils bien au schéma en production ?

---

## 5. SÉCURITÉ — AUDIT APPROFONDI

### 5.1 Authentification

Le système utilise **SessionAuthentication** (Django sessions) + **BasicAuthentication** (DRF).

- **Admin/Teacher** : Login classique `POST /api/login/` avec username/password
- **Student** : Login séparé `POST /api/students/login/` avec email/password
- Sessions : `SESSION_ENGINE = 'cached_db'`, `SESSION_COOKIE_AGE = 14400` (4h), `SESSION_EXPIRE_AT_BROWSER_CLOSE = True`

**Vérifie** :
- [ ] BasicAuthentication est-il nécessaire en production ? (risque : credentials en clair dans chaque requête)
- [ ] Rate limiting sur `/api/login/` et `/api/students/login/` — combien de tentatives ?
- [ ] Le `SESSION_COOKIE_HTTPONLY = True` est bien appliqué ?
- [ ] `CSRF_COOKIE_HTTPONLY = False` — est-ce safe pour un SPA ?
- [ ] Mots de passe : `MinimumLengthValidator(min_length=12)` — les 4 validateurs sont-ils tous actifs ?
- [ ] Le `DEFAULT_PASSWORD = "passe123"` dans docker-compose est-il changé en prod ?

### 5.2 Autorisations (RBAC)

Les permissions sont définies dans `core/auth.py` :
- `IsAdmin`, `IsTeacher`, `IsStudent`, `IsAdminOrTeacher`, `IsAdminOnly`
- Basées sur l'appartenance aux groupes Django (`admin`, `teacher`, `student`)

**Vérifie** :
- [ ] Chaque endpoint a-t-il la bonne classe de permission ?
- [ ] Les vues de `students/views.py` vérifient-elles que l'élève ne voit que SES copies ?
- [ ] `StatsReportView` — qui peut y accéder ? Un teacher voit-il les stats de TOUS les correctors ?
- [ ] `ExamDispatchView` — seul un admin peut dispatcher ?
- [ ] `CopyFinalPdfView` — un teacher peut-il voir la copie d'un élève qui ne lui est pas assignée ?
- [ ] Y a-t-il des endpoints publics non intentionnels ?
- [ ] Les `IsStudent` fallback via `request.session.get('student_id')` — est-ce un vecteur d'escalade ?

### 5.3 CSRF

- Django CSRF middleware actif
- `CSRF_COOKIE_HTTPONLY = False` (nécessaire pour que le SPA lise le cookie)
- Frontend : intercepteur Axios lit `csrftoken` depuis `document.cookie` et l'envoie en header `X-CSRFToken`
- `CSRF_TRUSTED_ORIGINS` configuré via env var

**Vérifie** :
- [ ] Toutes les mutations (POST/PUT/DELETE) passent-elles par le CSRF check ?
- [ ] Les endpoints Celery task status sont-ils protégés ?
- [ ] Le `CSRF_COOKIE_SAMESITE = "Lax"` est-il suffisant ?

### 5.4 CORS

- Production : `CORS_ALLOWED_ORIGINS` via env var (explicite)
- Dev : localhost:5173, localhost:8088, etc.
- `CORS_ALLOW_CREDENTIALS = True`

**Vérifie** :
- [ ] La valeur réelle de `CORS_ALLOWED_ORIGINS` en prod — y a-t-il des origines trop larges ?
- [ ] `CORS_ALLOW_HEADERS` — la liste est-elle minimale ?

### 5.5 CSP (Content Security Policy)

- Nginx ajoute un header CSP
- Django-CSP ajoute aussi un header CSP
- **RISQUE DE DOUBLE HEADER** : Nginx `add_header` + Django CSP middleware

**Vérifie** :
- [ ] Y a-t-il un conflit/duplication de header CSP entre Nginx et Django ?
- [ ] La CSP production bloque-t-elle `unsafe-inline` / `unsafe-eval` ?
- [ ] `connect-src: 'self'` empêche-t-il les appels au LLM Ollama ?

### 5.6 Injection & Validation

- PDF uploads validés : extension, MIME type, taille, intégrité (PyMuPDF)
- `python-magic` pour validation MIME
- `validators_antivirus.py` existe

**Vérifie** :
- [ ] Les JSONField (`scores_data`, `grading_structure`, `metadata`) sont-ils validés côté serveur ?
- [ ] Les `CharField` avec `max_length` sont-ils tous bornés ?
- [ ] SQL injection via ORM — les `extra()`, `raw()`, `RawSQL()` existent-ils ?
- [ ] XSS : le frontend utilise-t-il `v-html` quelque part ? (dangereux si contenu user)
- [ ] Path traversal sur les uploads (`upload_to` paths sont-ils sûrs ?)

### 5.7 Exposition de données sensibles

**Vérifie** :
- [ ] Le `.env` est-il dans `.gitignore` ?
- [ ] Le `SECRET_KEY` est-il unique et non-default en production ?
- [ ] Les réponses API exposent-elles des champs sensibles (password hash, tokens) ?
- [ ] Les serializers excluent-ils les champs sensibles ?
- [ ] Le `/api/docs/` (Swagger) est-il accessible en production ?
- [ ] Le `/api/schema/` (OpenAPI) est-il accessible en production ?
- [ ] Les messages d'erreur en production exposent-ils des stack traces ?
- [ ] Le `DEBUG = False` est-il effectivement forcé en production ?

---

## 6. ARCHITECTURE & DESIGN — AUDIT

### 6.1 Backend

**Vérifie** :
- [ ] **Séparation des responsabilités** : Les views font-elles de la logique métier directement, ou délèguent-elles aux services ?
- [ ] `exams/views.py` fait 55700 bytes — doit-il être splitté ?
- [ ] `grading/views.py` fait 28k — même question
- [ ] Le `views_stats.py` (27k) — les calculs statistiques sont-ils dans la view ou dans un service dédié ?
- [ ] Les tâches Celery sont-elles idempotentes ?
- [ ] Les transactions DB sont-elles utilisées pour les opérations critiques (finalization, dispatch) ?
- [ ] Le workflow de statut des copies (STAGING → READY → LOCKED → GRADED) est-il protégé contre les transitions invalides ?

### 6.2 Frontend

**Vérifie** :
- [ ] Les composants sont-ils raisonnablement découpés ? (`StatsReport.vue` fait 63k — monstrueux)
- [ ] Le router guard RBAC (`router/index.js`) gère-t-il correctement les redirections infinies ?
- [ ] La gestion d'état Pinia est-elle cohérente ? (2 stores seulement : auth + exam)
- [ ] Les erreurs API sont-elles toujours affichées à l'utilisateur ?
- [ ] Le retry Axios est-il sûr pour les opérations non-idempotentes ?
- [ ] Les `v-show` dans `StatsReport.vue` — performance vs `v-if` ?

### 6.3 Système d'overlay

En production, les fichiers Python sont montés individuellement depuis l'overlay host dans les containers Docker. C'est un pattern non-standard.

**Vérifie** :
- [ ] Risque de désynchronisation overlay/image Docker — que se passe-t-il si l'overlay a un fichier plus ancien que l'image ?
- [ ] Les 59 fichiers overlayés sont-ils identiques entre backend et celery containers ?
- [ ] Un fichier Python ajouté au repo mais non ajouté à l'overlay serait silencieusement ignoré
- [ ] Les fichiers `__pycache__` dans le container peuvent masquer les changements d'overlay

---

## 7. PERFORMANCE — AUDIT

### 7.1 Requêtes N+1

**Vérifie** :
- [ ] `StatsReportView` fait-il des boucles Python sur des querysets sans `select_related` / `prefetch_related` ?
- [ ] `CopyListView` — les copies avec student, corrector, scores sont-elles prefetchées ?
- [ ] `MyStudentsListView` — idem
- [ ] Les templates d'annotation sont-ils chargés efficacement ?

### 7.2 Index base de données

**Vérifie** :
- [ ] Les champs utilisés dans les filtres (`exam`, `status`, `assigned_corrector`, `student`) ont-ils des index ?
- [ ] `Copy.anonymous_id` est `unique=True` (donc indexé) ✓
- [ ] `Annotation` a un index `['copy', 'page_index']` ✓
- [ ] `QuestionRemark` a un index `['copy', 'question_id']` ✓
- [ ] `Score` — a-t-il un index sur `copy` ?
- [ ] `GradingEvent` — index `['copy', 'timestamp']` ✓
- [ ] `AuditLog` — 3 index ✓

### 7.3 Cache

**Vérifie** :
- [ ] Le `StatsReportView` est-il mis en cache ? (calculs lourds sur 209 copies à chaque requête)
- [ ] Les réponses paginées utilisent-elles `PAGE_SIZE = 50` — est-ce approprié ?
- [ ] Le `SESSION_ENGINE = 'cached_db'` — le cache Redis est-il configuré en prod ?

### 7.4 Frontend

**Vérifie** :
- [ ] Le bundle `index.js` fait 342kB (gzip 105kB) — est-ce raisonnable ?
- [ ] Les routes lazy-loadées réduisent-elles effectivement le bundle initial ?
- [ ] Les images sont-elles optimisées ? (`Korrigo.png` fait 5549kB !)
- [ ] Le PDF viewer charge-t-il les pages à la demande ou tout le PDF d'un coup ?

---

## 8. FIABILITÉ — AUDIT

### 8.1 Race conditions

**Vérifie** :
- [ ] Le `CopyLock` protège-t-il réellement contre l'édition concurrente ?
- [ ] `Annotation.version` (optimistic locking) — est-il vérifié à chaque update ?
- [ ] Le dispatch de copies — que se passe-t-il si deux admins dispatche simultanément ?
- [ ] La finalisation — un double-click peut-il finaliser deux fois ?
- [ ] Le `DraftState.version` est-il incrémenté atomiquement ?

### 8.2 Intégrité des données

**Vérifie** :
- [ ] Un `Score` peut-il exister pour une copie qui n'est pas `GRADED` ?
- [ ] Peut-on supprimer un examen qui a des copies ? (`on_delete=PROTECT` sur `Copy.exam`)
- [ ] Peut-on supprimer un user qui a des annotations ? (`on_delete=PROTECT` sur `Annotation.created_by`)
- [ ] Le `unique_together = ['copy', 'question_id']` sur `QuestionRemark` — est-ce suffisant ?
- [ ] Les `JSONField` peuvent-ils contenir `null` vs `[]` vs `{}` de manière incohérente ?

### 8.3 Gestion d'erreurs

**Vérifie** :
- [ ] Les vues DRF renvoient-elles des codes HTTP cohérents (400, 403, 404, 409, 500) ?
- [ ] Les tâches Celery ont-elles des handlers d'erreur et des retry ?
- [ ] Le `CELERY_TASK_TIME_LIMIT = 300` et `SOFT_TIME_LIMIT = 270` — suffisants pour LLM summary ?
- [ ] Les erreurs Celery sont-elles loguées et visibles ?
- [ ] Le frontend affiche-t-il toujours un feedback en cas d'erreur réseau ?

---

## 9. INFRASTRUCTURE — AUDIT

### 9.1 Docker Compose

**Vérifie** :
- [ ] Les healthchecks sont-ils corrects pour chaque service ?
- [ ] Le `start_period: 120s` pour le backend — est-ce suffisant pour les migrations ?
- [ ] Les variables d'env `{?err}` forcent-elles bien des valeurs en prod ?
- [ ] Le `celery-beat` n'a PAS d'overlay volumes — est-ce intentionnel ?
- [ ] Les volumes `postgres_data`, `media_volume` sont-ils backupés ?
- [ ] Le réseau `ollama_net` (external) — que se passe-t-il s'il n'existe pas ?

### 9.2 Nginx

**Vérifie** :
- [ ] `client_max_body_size 1G` — est-ce trop permissif ?
- [ ] Les timeouts proxy de 1800s (30 min) — pourquoi si longs ?
- [ ] La règle `/admin/` — les routes frontend `/admin/login`, `/admin/users`, `/admin/settings` sont bien interceptées par le regex avant le proxy Django ?
- [ ] Le `proxy_hide_header X-Frame-Options` dans le bloc API — est-ce voulu ?
- [ ] Le CSP header Nginx vs Django CSP — y a-t-il un conflit ?
- [ ] `server_tokens off` ✓
- [ ] Les fichiers media (`/media/`) sont servis sans authentification — est-ce un problème ? (PDFs de copies)

### 9.3 Déploiement

Le processus de déploiement frontend est :
1. `npx vite build` localement
2. `scp dist/* root@88.99.254.59:/var/www/labomaths/korrigo/frontend/`
3. `docker cp ... docker-nginx-1:/usr/share/nginx/html/`

**Vérifie** :
- [ ] Ce processus est-il automatisable (CI/CD) ?
- [ ] Que se passe-t-il si l'étape 3 est oubliée ? (ancien build servi)
- [ ] Le backend est déployé via overlay, pas via rebuild d'image — est-ce durable ?
- [ ] Les backups DB sont-ils automatisés ?
- [ ] Y a-t-il un rollback possible ?

---

## 10. TESTS — AUDIT

### 10.1 Couverture

**Vérifie** :
- [ ] Quel pourcentage de couverture ? (Le fichier `.coverage` existe)
- [ ] Les tests critiques existent-ils :
  - Login/logout admin, teacher, student
  - RBAC (un teacher ne peut pas accéder aux endpoints admin)
  - Workflow copie (STAGING → GRADED)
  - Finalisation avec scores
  - Dispatch
  - Export PDF/CSV
  - StatsReportView
- [ ] Les tests d'intégration existent-ils (E2E) ?
- [ ] `@playwright/test` est dans les devDependencies — y a-t-il des tests Playwright ?
- [ ] Les tests utilisent-ils des fixtures réalistes ?

---

## 11. FRONTEND — AUDIT APPROFONDI

### 11.1 StatsReport.vue (63kB — le plus gros fichier)

Ce composant a été récemment refactoré pour consommer une API dynamique (`GET /api/exams/stats-report/`).

**Vérifie** :
- [ ] Toutes les données hardcodées ont-elles été remplacées par des computed properties ?
- [ ] Les `cheatDetected` et `nearCheat` arrays sont-ils encore hardcodés (contenu éditorial) ?
- [ ] Les `themes` sont-ils hardcodés ?
- [ ] Le loading state et error state sont-ils implémentés ?
- [ ] Les `v-show` tabs ne causent-ils pas un rendu inutile de toutes les sections ?
- [ ] Le composant devrait-il être splitté en sous-composants par tab ?

### 11.2 CorrectorDesk.vue (le bureau de correction)

C'est le composant le plus critique fonctionnellement.

**Vérifie** :
- [ ] Le canvas d'annotations gère-t-il correctement le zoom et le scroll ?
- [ ] L'auto-save draft fonctionne-t-il à intervalles réguliers ?
- [ ] Le lock est-il acquis avant toute modification ?
- [ ] Le lock est-il libéré proprement (onBeforeUnmount, visibilitychange) ?
- [ ] Les scores sont-ils validés côté client (pas de score > max) ?

### 11.3 Portail élève (ResultView.vue)

**Vérifie** :
- [ ] L'élève ne voit que SES copies
- [ ] L'élève ne peut pas modifier quoi que ce soit
- [ ] Le PDF annoté est affiché en lecture seule (iframe)
- [ ] Le `X-Frame-Options: SAMEORIGIN` est bien configuré pour le PDF viewer
- [ ] Le bilan LLM est affiché de manière sécurisée (pas de v-html non sanitisé)

---

## 12. CONFORMITÉ RGPD — AUDIT

### 12.1 Données personnelles traitées

- Nom, prénom, date de naissance, email, classe des élèves
- Copies d'examen (PDFs)
- Scores et appréciations
- Bilans LLM personnalisés
- Adresses IP et user agents (AuditLog)

**Vérifie** :
- [ ] Le `AuditLog` enregistre-t-il bien toutes les actions critiques ?
- [ ] Y a-t-il une politique de rétention des données ?
- [ ] Les données élèves peuvent-elles être exportées (droit d'accès) ?
- [ ] Les données élèves peuvent-elles être supprimées (droit à l'effacement) ?
- [ ] Les PDFs de copies sont-ils accessibles sans authentification via `/media/` ?
- [ ] Le LLM (Ollama local) — les données sont-elles envoyées à un service externe ?

---

## 13. FORMAT DE SORTIE ATTENDU

Structure ton audit ainsi :

```
# AUDIT KORRIGO — [Date]

## RÉSUMÉ EXÉCUTIF
- X findings 🔴 CRITIQUE
- X findings 🟠 MAJEUR
- X findings 🟡 MINEUR
- X findings 🔵 INFO
- Score de sécurité global : X/10
- Score de qualité global : X/10

## FINDINGS DÉTAILLÉS

### [ID] [Sévérité] [Catégorie] — Titre court
**Fichier** : `chemin/fichier.py:ligne`
**Description** : ...
**Impact** : ...
**Correctif recommandé** :
```code
...
```
**Effort** : Faible/Moyen/Élevé

## RECOMMANDATIONS PRIORITAIRES
1. ...
2. ...

## DETTE TECHNIQUE IDENTIFIÉE
...

## POINTS POSITIFS
...
```

---

## 14. FICHIERS À EXAMINER EN PRIORITÉ

Par ordre de criticité :

1. `backend/core/settings.py` (515 lignes) — Configuration de sécurité
2. `backend/core/views.py` (13k) — Authentification
3. `backend/core/auth.py` (75 lignes) — RBAC
4. `backend/exams/views.py` (55k) — Le plus gros fichier backend
5. `backend/grading/views.py` (28k) — Correction (le cœur métier)
6. `backend/grading/services.py` (16k) — Logique métier
7. `backend/grading/views_lock.py` (5k) — Concurrence
8. `backend/exams/models.py` (640 lignes) — Modèle de données
9. `backend/grading/models.py` (495 lignes) — Modèle de données
10. `backend/students/views.py` (16k) — Portail élève
11. `backend/exams/views_stats.py` (27k) — Stats report API
12. `frontend/src/services/api.js` (147 lignes) — Client HTTP
13. `frontend/src/stores/auth.js` (134 lignes) — Auth state
14. `frontend/src/router/index.js` (290 lignes) — Routing RBAC
15. `frontend/src/views/StatsReport.vue` (63k) — Report dynamique
16. `infra/docker/docker-compose.prod.yml` (286 lignes) — Infra prod
17. `infra/nginx/nginx.conf` (158 lignes) — Reverse proxy

---

## 15. QUESTIONS SPÉCIFIQUES À INVESTIGUER

1. **Le `BasicAuthentication` est-il activé en production ?** Si oui, c'est un risque car les credentials sont envoyés en clair (base64) à chaque requête, même en HTTP.

2. **Le endpoint `/media/` est-il accessible publiquement ?** Si oui, n'importe qui peut télécharger les PDFs de copies d'élèves.

3. **Le `IsStudent` fallback session** (`request.session.get('student_id')`) permet-il une élévation de privilège si on forge un session cookie ?

4. **Le `exams/views.py` de 55k** — contient-il de la logique métier mélangée avec la présentation ? Y a-t-il des calculs SQL ou des boucles O(n²) cachés ?

5. **Le `StatsReportView` est-il vulnérable à un DoS ?** — Il calcule des stats lourdes à chaque appel sans cache.

6. **Les copies GRADED sont-elles réellement immuables ?** — Peut-on modifier les annotations ou scores d'une copie finalisée ?

7. **Le déploiement overlay** — Y a-t-il des fichiers en production qui n'existent PAS dans le repo local (orphelins) ?

8. **Le `docker-compose.prod.yml`** duplique les 59 overlay mounts entre `backend` et `celery` — est-ce maintenu en sync ?

9. **Les `scores_data` JSONField** — quels sont les formats acceptés ? Y a-t-il une validation de schéma ?

10. **Le frontend fait-il du rendu HTML non échappé (`v-html`) avec du contenu user ?** (LLM summary, annotations, appreciations)

---

## 16. NOTE FINALE

Ce projet est en **production active** avec de vraies données d'élèves (mineurs). La rigueur de cet audit est donc cruciale. Ne minimise aucun finding. Si tu as un doute sur un point, signale-le comme un finding à investiguer plutôt que de le passer sous silence.

**Rappel** : Tu as accès à l'intégralité du code source. Lis chaque fichier mentionné en priorité. Ne te contente pas de lire les signatures — lis les implémentations, les boucles, les requêtes SQL, les validations manquantes.

Bon audit.
