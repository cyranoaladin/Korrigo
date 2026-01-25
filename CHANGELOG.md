# Changelog

Tous les changements notables du projet Viatique seront documentés dans ce fichier.

Le format est basé sur [Keep a Changelog](https://keepachangelog.com/fr/1.0.0/),
et ce projet adhère au [Semantic Versioning](https://semver.org/lang/fr/).

---

## [1.2.0] - 2026-01-24

### 🚀 Ajouté

#### Phase 2 - Améliorations Production
- **Configuration CORS Production** : Configuration conditionnelle par environnement (development/production)
  - Origines explicites via variable `CORS_ALLOWED_ORIGINS`
  - Support same-origin et cross-origin
  - Headers CORS sécurisés (liste blanche)
- **Documentation API** : Intégration DRF Spectacular
  - Schéma OpenAPI 3.0 automatique (`/api/schema/`)
  - Interface Swagger UI interactive (`/api/docs/`)
  - Interface ReDoc documentation (`/api/redoc/`)
  - Métadonnées API complètes (titre, version, tags, contact)
- **Infrastructure Tests** : Configuration pytest avec coverage
  - Commandes standardisées pour tests et coverage
  - Objectif 70% coverage code critique

### 📝 Modifié
- `backend/core/settings.py` : Configuration CORS conditionnelle + DRF Spectacular
- `backend/core/urls.py` : Ajout URLs documentation API
- `backend/requirements.txt` : Ajout `drf-spectacular==0.27.1`
- `.env.example` : Documentation variable `CORS_ALLOWED_ORIGINS`

### 📚 Documentation
- `docs/PHASE2_PRODUCTION_IMPROVEMENTS.md` : Rapport complet Phase 2

---

## [1.1.0] - 2026-01-24

### 🔒 Sécurité (Phase 1 - Corrections Critiques)

#### Audit Trail - Conformité RGPD/CNIL
- **Modèle AuditLog** : Table centralisée pour traçabilité actions critiques
  - Traçabilité authentification (login/logout prof, admin, élève)
  - Traçabilité accès données (téléchargement PDF, liste copies)
  - Traçabilité workflow (lock, unlock, finalize)
  - Rétention 12 mois minimum (conformité légale)
- **Helpers Audit** : Fonctions utilitaires (`core/utils/audit.py`)
  - `log_audit()` : Helper générique
  - `log_authentication_attempt()` : Spécifique login/logout
  - `log_data_access()` : Spécifique accès données sensibles
  - `log_workflow_action()` : Spécifique workflow correction
  - `get_client_ip()` : Extraction IP avec support proxy

#### Rate Limiting - Protection Brute Force
- **django-ratelimit** : Protection endpoints login
  - Login professeur/admin : 5 tentatives / 15 minutes par IP
  - Login élève : 5 tentatives / 15 minutes par IP
  - Blocage automatique (HTTP 429 Too Many Requests)
  - Cache Redis via `CELERY_BROKER_URL`

#### Documentation Sécurité
- **Endpoint CopyFinalPdfView** : Documentation exhaustive `AllowAny`
  - Justification système dual authentication
  - Documentation 2 gates de sécurité (Status + Permissions)
  - Référence règles gouvernance

### 🚀 Ajouté
- `backend/core/models.py` : Modèle `AuditLog`
- `backend/core/utils/audit.py` : Helpers audit trail
- `backend/core/utils/__init__.py` : Package utils
- `backend/core/migrations/0001_add_auditlog_model.py` : Migration AuditLog

### 📝 Modifié
- `backend/requirements.txt` : Ajout `django-ratelimit==4.1.0`
- `backend/core/views.py` : Rate limiting + audit trail login
- `backend/students/views.py` : Rate limiting + audit trail login élève
- `backend/grading/views.py` : Audit trail download + documentation
- `backend/exams/views.py` : Audit trail liste copies élève

### 📚 Documentation
- `docs/PHASE1_SECURITY_CORRECTIONS.md` : Rapport complet Phase 1

---

## [1.0.0] - 2026-01-21

### 🚀 Version Initiale Production-Ready

#### Architecture
- **Backend** : Django 5.0 + Django REST Framework
- **Frontend** : Vue.js 3 (Composition API) + Pinia + Vite
- **Base de données** : PostgreSQL 15
- **Files de tâches** : Redis + Celery
- **Vision & PDF** : OpenCV + PyMuPDF

#### Fonctionnalités Principales

##### Gestion Examens
- Upload PDF examens scannés (A3)
- Split automatique en fascicules (4 pages)
- Détection header avec OCR (nom élève)
- Staging area pour validation manuelle
- Fusion fascicules en copies anonymes

##### Workflow Correction
- Machine d'états : STAGING → READY → LOCKED → GRADED
- Verrouillage copie pendant correction (soft lock)
- Annotations vectorielles (coordonnées normalisées [0,1])
- Éditeur de barème hiérarchique (Exercices → Questions → Points)
- Autosave brouillon (protection perte données)
- Export PDF final avec annotations aplaties

##### Gestion Élèves
- Authentification élève (INE + Nom)
- Session personnalisée (pas de User Django)
- Accès lecture seule copies GRADED
- Téléchargement PDF corrigé
- Consultation notes et relevé

##### Sécurité
- **P0 Baseline Security** : 100% conforme
  - `SECRET_KEY` validation production
  - `DEBUG=False` par défaut
  - `ALLOWED_HOSTS` validation production
  - SSL/HTTPS conditionnel
  - HSTS 1 an en production SSL
- **Permissions** : Default Deny (`IsAuthenticated`)
  - `IsTeacherOrAdmin` : Accès professeur/admin
  - `IsStudent` : Accès élève (session-based)
  - `IsOwnerStudent` : Vérification propriété copie
  - `IsLockedByOwnerOrReadOnly` : Workflow correction

##### Traçabilité
- **GradingEvent** : Journal audit workflow correction
  - Actions : IMPORT, VALIDATE, LOCK, UNLOCK, FINALIZE, EXPORT
  - Métadonnées JSON contextuelles
  - Timestamp + actor
- **Champs traçabilité** : Copy model
  - `validated_at`, `locked_at`, `locked_by`, `graded_at`

#### Tests
- Tests workflow correction (13 fichiers)
- Tests accès élève (gate4_flow)
- Tests concurrence et anti-perte
- Tests validation et serializers
- Configuration pytest + coverage

#### Déploiement
- Docker Compose (PostgreSQL, Redis, Backend, Frontend, Celery)
- Variables d'environnement (`.env.example`)
- Makefile pour commandes courantes
- Gunicorn pour production

### 📚 Documentation
- `README.md` : Guide utilisateur et installation
- `.antigravity/` : Système de gouvernance technique (v1.1.0)
  - 7 fichiers rules (sécurité, backend, frontend, database, PDF, deployment)
  - 6 workflows métier formalisés
  - 5 skills techniques
  - 3 checklists qualité
- `.claude/` : Système de gouvernance (v1.1.0, synchronisé)
- `docs/` : Documentation technique

---

## [Unreleased]

### 🔄 En Cours
- Tests complets audit trail (Phase 1)
- Tests rate limiting (Phase 1)
- Tests CORS (Phase 2)
- Atteindre 70% coverage code critique

### 🎯 Prévu (Phase 3)
- Monitoring production (Sentry, logs structurés)
- Optimisation performance (N+1 queries, cache Redis)
- CI/CD Pipeline (GitHub Actions, déploiement automatique)
- Tests sécurité frontend (XSS, localStorage)
- Validation fichiers PDF renforcée

---

## Types de Changements

- **Ajouté** : Nouvelles fonctionnalités
- **Modifié** : Changements de fonctionnalités existantes
- **Déprécié** : Fonctionnalités bientôt supprimées
- **Supprimé** : Fonctionnalités supprimées
- **Corrigé** : Corrections de bugs
- **Sécurité** : Corrections de vulnérabilités

---

## Références

- [Audit Complet Projet](docs/AUDIT_COMPLET_2026-01-24.md)
- [Phase 1 - Corrections Sécurité](docs/PHASE1_SECURITY_CORRECTIONS.md)
- [Phase 2 - Améliorations Production](docs/PHASE2_PRODUCTION_IMPROVEMENTS.md)
- [Règles de Gouvernance](.antigravity/README.md)

---

**Projet** : Viatique (Korrigo)  
**Contexte** : Production institutionnelle (AEFE / Éducation nationale)  
**Mainteneur** : Aleddine BEN RHOUMA
