# Korrigo

**Korrigo** est une plateforme de correction numérique d'examens scannés, conçue pour le Lycée Pierre Mendès France (Tunis, AEFE). Elle couvre le cycle complet : ingestion des scans PDF, anonymisation, dispatch aux correcteurs, annotation vectorielle, notation par barème, export PDF/CSV, et consultation des résultats par les élèves.

**Production** : [https://korrigo.labomaths.tn](https://korrigo.labomaths.tn)

---

## 🏗 Architecture Technique

```
┌───────────────────────────────────────────────────────┐
│                 NGINX (reverse proxy)                  │
│           korrigo.labomaths.tn:443 (TLS)              │
├────────────────────┬──────────────────────────────────┤
│  Frontend (SPA)    │       Backend (API REST)          │
│  Vue 3 + Vite      │  Django 4.2 + DRF + Python 3.11  │
│  Pinia + Router    │  Gunicorn · Session Auth · CSRF   │
│  TailwindCSS 4     │  PyMuPDF · OpenCV · Tesseract     │
│  PDF.js · Lucide   │  GPT-4o-mini Vision (OCR)         │
├────────────────────┼──────────────────────────────────┤
│                    │  Celery + Beat │ Redis (broker)   │
│                    │  PostgreSQL 15  (port 5432)       │
└────────────────────┴──────────────────────────────────┘
```

| Couche | Technologie | Version |
|--------|-------------|---------|
| **Frontend** | Vue.js 3 (Composition API) + Vite | 3.4 / 5.1 |
| **UI** | TailwindCSS + Lucide Icons | 4.x |
| **State / Routing** | Pinia + Vue Router | 2.1 / 4.2 |
| **PDF Viewer** | PDF.js | 4.0 |
| **Backend** | Django + Django REST Framework | 4.2 |
| **Runtime** | Python 3.11 + Gunicorn | |
| **Base de données** | PostgreSQL | 15 |
| **Cache / Broker** | Redis | |
| **Tâches async** | Celery + Celery Beat | |
| **PDF Processing** | PyMuPDF (fitz) | 1.23.26 |
| **Vision** | OpenCV (headless) | 4.8 |
| **OCR** | GPT-4o-mini Vision (principal) + Tesseract (fallback) | |
| **Monitoring** | Prometheus metrics + JSON structured logging | |
| **API Docs** | DRF Spectacular (OpenAPI 3.0) | 0.27.1 |
| **Sécurité** | django-ratelimit, django-csp, python-magic | |
| **Container** | Docker + Docker Compose | |

---

## 🎯 Fonctionnalités Principales

### Gestion des Examens
- **Deux modes d'upload** : `BATCH_A3` (scan par lots, découpage automatique) et `INDIVIDUAL_A4` (1 PDF = 1 copie)
- **Import CSV** des listes d'élèves avec liaison automatique copie ↔ élève
- **Anonymisation** : IDs séquentiels collision-free (ex: `0F8E-001`)
- **Dispatch automatique** : répartition équitable des copies entre correcteurs (round-robin)
- **Gestion documentaire versionnée** : sujet, corrigé, barème (avec extraction de texte)

### Correction et Annotation
- **Annotations vectorielles** : coordonnées normalisées [0,1] (ADR-002)
- **Verrouillage pessimiste** (CopyLock) : un seul correcteur par copie, TTL 10 min + heartbeat
- **Autosave** : brouillon persistant (DraftState) contre la perte de données
- **Barème hiérarchique** : Exercices → Questions → Sous-questions → Points
- **Variante de sujet** : support Sujet A / Sujet B
- **Banque d'annotations** : templates officiels + annotations personnelles + suggestions contextuelles
- **Versionnement optimiste** : champ `version` sur les annotations (détection conflits)

### Export et Résultats
- **PDF final** : copie avec annotations aplaties (PDFFlattener via PyMuPDF)
- **CSV** : notes formatées pour Pronote
- **Publication contrôlée** : release/unrelease par l'admin
- **Portail élève** : consultation copies corrigées + notes

### OCR et Intelligence Artificielle
- **GPT-4o-mini Vision** (principal) : lecture écriture manuscrite française sur en-tête de copie
- **Tesseract OCR** (fallback) : si OpenAI non configuré
- **Pipeline** : rasterise → crop header 25% → OCR → matching fuzzy vs liste élèves → suggestions

### Sécurité et Conformité
- **RGPD/CNIL** : AuditLog centralisé, politique de rétention, droits d'accès
- **Rate limiting** : protection brute force (5 tentatives / 15 min)
- **CSP** + CSRF + HSTS + Secure Cookies en production
- **Validation PDF** : taille (100 MB max), type MIME, intégrité

---

## 🗄 Modèle de Données (Résumé)

### Machine d'États des Copies (ADR-003)

```
STAGING ──validate──→ READY ──lock──→ LOCKED ──finalize──→ GRADING_IN_PROGRESS ──→ GRADED
                        ↑              │                           │
                        └──unlock──────┘                    GRADING_FAILED
                                                                │
                                                                └──retry──→ GRADING_IN_PROGRESS
```

### Modèles Principaux

| App | Modèle | Rôle |
|-----|--------|------|
| **exams** | `Exam` | Examen avec structure, mode d'upload, correcteurs (M2M) |
| **exams** | `Copy` | Copie d'un élève, machine d'états, liens PDF source/final |
| **exams** | `Booklet` | Fascicule (pages rasterisées en PNG) |
| **exams** | `ExamPDF` | PDF individuel uploadé (mode INDIVIDUAL_A4) |
| **exams** | `ExamDocumentSet` / `ExamDocument` | Lots documentaires versionnés (sujet, corrigé, barème) |
| **grading** | `Annotation` | Annotation vectorielle [0,1] avec score_delta et version |
| **grading** | `Score` | Scores par question (JSON) + commentaire final |
| **grading** | `GradingEvent` | Journal d'audit : IMPORT, VALIDATE, LOCK, UNLOCK, FINALIZE |
| **grading** | `CopyLock` | Verrou pessimiste avec token UUID et TTL |
| **grading** | `DraftState` | Brouillon autosave (protection perte données) |
| **grading** | `AnnotationTemplate` / `UserAnnotation` | Banque d'annotations |
| **grading** | `QuestionRemark` | Remarque par question |
| **students** | `Student` | Élève (OneToOne → User), nom, email, classe, groupe |
| **identification** | `OCRResult` | Résultat OCR avec confiance et suggestions |
| **core** | `AuditLog` | Traçabilité RGPD (action, IP, user-agent, metadata) |
| **core** | `GlobalSettings` | Paramètres singleton (ex: résultats publiés) |
| **core** | `UserProfile` | Profil étendu (must_change_password) |

---

## 🔌 API REST (Résumé)

**Base** : `/api/` · **Swagger** : `/api/docs/` · **ReDoc** : `/api/redoc/` · **Schéma** : `/api/schema/`

### Authentification
`POST /api/login/` · `POST /api/logout/` · `GET /api/me/` · `GET /api/csrf/`

### Élèves
`POST /api/students/login/` · `GET /api/students/me/` · `GET /api/students/copies/` · `POST /api/students/import/`

### Examens
`GET /api/exams/` · `POST /api/exams/upload/` · `GET /api/exams/{id}/` · `POST /api/exams/{id}/upload-individual-pdfs/` · `POST /api/exams/{id}/dispatch/` · `POST /api/exams/{id}/validate-all/` · `GET /api/exams/{id}/export-csv/` · `GET /api/exams/{id}/export-pronote/`

### Correction
`POST /api/grading/copies/{id}/lock/` · `POST /api/grading/copies/{id}/lock/heartbeat/` · `DELETE /api/grading/copies/{id}/lock/release/` · `GET|POST /api/grading/copies/{id}/annotations/` · `POST /api/grading/copies/{id}/finalize/` · `GET /api/grading/copies/{id}/final-pdf/` · `GET|PUT /api/grading/copies/{id}/scores/` · `GET|PUT /api/grading/copies/{id}/draft/`

### OCR / Identification
`GET /api/identification/desk/` · `POST /api/identification/perform-ocr/{id}/` · `POST /api/identification/identify/{id}/`

### Monitoring
`GET /api/health/` · `GET /api/health/live/` · `GET /api/health/ready/` · `GET /metrics`

> Pour la référence API complète, voir [docs/technical/API_REFERENCE.md](docs/technical/API_REFERENCE.md)

---

## 👥 Rôles et Permissions

| Rôle | Accès |
|------|-------|
| **Admin** (`is_staff`) | Tout : examens, copies, dispatch, utilisateurs, paramètres, export |
| **Teacher** (groupe) | Copies assignées uniquement : annotation, notation, finalisation |
| **Student** (modèle) | Lecture seule : copies GRADED si résultats publiés |

### Routes Frontend

| Route | Rôle | Description |
|-------|------|-------------|
| `/` | Public | Portail d'accueil (3 portes de connexion) |
| `/korrigo` | Public | Landing page, guides |
| `/admin-dashboard` | Admin | Tableau de bord admin |
| `/corrector-dashboard` | Teacher | Liste des copies assignées |
| `/corrector/desk/:copyId` | Teacher/Admin | Interface de correction |
| `/exam/:examId/identification` | Admin | Bureau d'identification OCR |
| `/exam/:examId/staple` | Admin | Agrafeuse (staging) |
| `/exam/:examId/grading-scale` | Admin | Éditeur de barème |
| `/admin/users` | Admin | Gestion utilisateurs |
| `/student-portal` | Student | Consultation résultats |

---

## 📋 Workflow de Correction

### 1. Préparation (Admin)
Créer examen → Choisir mode (`BATCH_A3` ou `INDIVIDUAL_A4`) → Upload scans → Import élèves (CSV) → Upload documents (sujet, corrigé, barème)

### 2. Traitement
- **BATCH_A3** : Split automatique → OCR en-têtes → Staging (agrafeuse) → Fusion → Validation
- **INDIVIDUAL_A4** : 1 PDF = 1 Copie → Rasterisation @144 DPI → Booklet auto → READY

### 3. Identification & Dispatch
OCR ou identification manuelle → Liaison copie ↔ élève → Dispatch round-robin aux correcteurs

### 4. Correction (Enseignant)
Acquérir verrou → Naviguer les pages → Annoter (canvas vectoriel) → Noter par question → Heartbeat auto → Autosave brouillon → Finaliser → PDF final généré

### 5. Export (Admin)
Exporter CSV (Pronote) → Exporter PDFs corrigés → Publier résultats → Élèves consultent

---

## 🛠 Installation

### Prérequis
- Docker & Docker Compose v2
- 4 GB RAM minimum (8 GB recommandé)

### Développement Local

```bash
# Cloner le repo
git clone <repo-url> && cd korrigo

# Lancer tous les services
make up
# Ou manuellement :
docker-compose up --build -d

# Créer le super-utilisateur
make superuser
```

**Accès** :
- Frontend : [http://localhost:5173](http://localhost:5173)
- Backend API : [http://localhost:8000/api/](http://localhost:8000/api/)
- Admin Django : [http://localhost:8000/django-admin/](http://localhost:8000/django-admin/)
- Swagger : [http://localhost:8000/api/docs/](http://localhost:8000/api/docs/)

### Production (korrigo.labomaths.tn)

```bash
cd infra/docker
docker compose -f docker-compose.yml -f docker-compose.server.yml up -d
```

Variables d'environnement requises dans `infra/docker/.env` :
- `SECRET_KEY` — Clé secrète Django (obligatoire)
- `DATABASE_URL` — URL PostgreSQL
- `DJANGO_ENV=production`
- `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`, `CORS_ALLOWED_ORIGINS`
- `OPENAI_API_KEY` — Pour l'OCR GPT-4o-mini (optionnel, fallback Tesseract)
- `OPENAI_MODEL` — Modèle OCR (défaut : `gpt-4.1-mini-2025-04-14`)
- `METRICS_TOKEN` — Authentification endpoint Prometheus (recommandé)

---

## 🧪 Tests

```bash
# Tests unitaires et intégration
make test

# Avec couverture
cd backend && pytest --cov=. --cov-report=html

# Tests E2E (Playwright)
cd frontend && npx playwright test
```

Tests principaux :
- `backend/exams/tests/` — Upload, validation, dispatch, import
- `backend/grading/tests/` — Annotations, locking, finalization, scores
- `backend/exams/tests/test_audit_fixes.py` — 15 correctifs audités (P1-P15)

## � Structure du Projet

```
korrigo/
├── backend/                          # Django REST API (Python 3.11)
│   ├── core/                         # Auth, settings, health, metrics, audit
│   ├── exams/                        # Examens, copies, booklets, documents
│   ├── grading/                      # Annotations, scores, locks, drafts, events
│   ├── students/                     # Modèle élève, auth élève, import CSV
│   ├── identification/               # OCR (GPT-4o-mini + Tesseract)
│   ├── processing/services/          # PDF splitter, flattener, vision OpenCV
│   ├── Dockerfile                    # Python 3.11-slim + Tesseract + OpenCV
│   └── requirements.txt
├── frontend/                         # Vue.js 3 SPA
│   ├── src/
│   │   ├── views/                    # Pages (Admin, Corrector, Student)
│   │   ├── views/admin/              # CorrectorDesk, StapleView, Identification...
│   │   ├── components/               # CanvasLayer, PDFViewer, GradingSidebar...
│   │   ├── stores/                   # auth.js, examStore.js (Pinia)
│   │   ├── services/                 # api.js (Axios), gradingApi.js
│   │   └── router/index.js          # Routes avec guards RBAC
│   └── Dockerfile                    # Multi-stage (Node 20 → Nginx Alpine)
├── infra/
│   ├── docker/                       # docker-compose.yml + .server.yml + .env
│   └── nginx/                        # Config reverse proxy
├── docs/                             # Documentation complète
│   ├── INDEX.md                      # Index principal
│   ├── admin/                        # Guides direction et administration
│   ├── users/                        # Guides enseignant, secrétariat, élève
│   ├── security/                     # RGPD, sécurité, données, audit
│   ├── legal/                        # Confidentialité, CGU, DPA, consentement
│   ├── support/                      # FAQ, dépannage, support
│   ├── technical/                    # Architecture, API, DB, workflows
│   ├── deployment/                   # Guides déploiement, runbooks
│   └── decisions/                    # ADRs (Architecture Decision Records)
├── CHANGELOG.md                      # Historique des versions
└── Makefile                          # Commandes courantes
```

---

## 📚 Documentation

**👉 [INDEX PRINCIPAL](docs/INDEX.md)** — Point d'entrée unique pour toute la documentation.

| Public | Documents |
|--------|-----------|
| **Direction** | [Guide Administrateur Lycée](docs/admin/GUIDE_ADMINISTRATEUR_LYCEE.md) · [Procédures](docs/admin/PROCEDURES_OPERATIONNELLES.md) |
| **Admin technique** | [Guide Admin](docs/admin/GUIDE_UTILISATEUR_ADMIN.md) · [Gestion Utilisateurs](docs/admin/GESTION_UTILISATEURS.md) |
| **Enseignant** | [Guide Enseignant](docs/users/GUIDE_ENSEIGNANT.md) · [Navigation UI](docs/users/NAVIGATION_UI.md) |
| **Secrétariat** | [Guide Secrétariat](docs/users/GUIDE_SECRETARIAT.md) |
| **Élève** | [Guide Étudiant](docs/users/GUIDE_ETUDIANT.md) |
| **Sécurité** | [RGPD](docs/security/POLITIQUE_RGPD.md) · [Sécurité](docs/security/MANUEL_SECURITE.md) · [Données](docs/security/GESTION_DONNEES.md) · [Audit](docs/security/AUDIT_CONFORMITE.md) |
| **Légal** | [Confidentialité](docs/legal/POLITIQUE_CONFIDENTIALITE.md) · [CGU](docs/legal/CONDITIONS_UTILISATION.md) · [DPA](docs/legal/ACCORD_TRAITEMENT_DONNEES.md) |
| **Support** | [FAQ](docs/support/FAQ.md) · [Dépannage](docs/support/DEPANNAGE.md) · [Support](docs/support/SUPPORT.md) |
| **Technique** | [Architecture](docs/technical/ARCHITECTURE.md) · [API](docs/technical/API_REFERENCE.md) · [DB Schema](docs/technical/DATABASE_SCHEMA.md) · [Workflows](docs/technical/BUSINESS_WORKFLOWS.md) |
| **DevOps** | [Développement](docs/development/DEVELOPMENT_GUIDE.md) · [Déploiement](docs/deployment/DEPLOYMENT_GUIDE.md) |
| **ADRs** | [ADR-001](docs/decisions/ADR-001-student-authentication-model.md) · [ADR-002](docs/decisions/ADR-002-pdf-coordinate-normalization.md) · [ADR-003](docs/decisions/ADR-003-copy-status-state-machine.md) |

---

## 📜 Crédits & Attribution

**Concepteur** : Alaeddine BEN RHOUMA — Labo Maths ERT  
**Contexte** : Lycée Pierre Mendès France, Tunis (AEFE)  
**Licence** : Propriétaire — Usage institutionnel
