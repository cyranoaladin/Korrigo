# Changelog

Tous les changements notables du projet Korrigo seront documentés dans ce fichier.

Le format est basé sur [Keep a Changelog](https://keepachangelog.com/fr/1.0.0/),
et ce projet adhère au [Semantic Versioning](https://semver.org/lang/fr/).

---

## [2.0.0] - 2026-03-23

### Améliorations V2 — Réponse au bilan correcteurs (NPS -29 → objectif NPS > 0)

Suite au bilan du premier déploiement (Bac Blanc Mathématiques Mars 2026, 7/8 correcteurs, NPS -29), cette version majeure adresse les 7 recommandations prioritaires identifiées.

#### Correction & Annotations

- **Correction du reset de position du barème** : Le panneau barème conserve désormais sa position de scroll lors des allers-retours entre onglets (Annotations ↔ Barème). Les onglets utilisent `v-show` au lieu de `v-if` pour préserver le DOM.
- **Outil tampon Vrai/Faux (V/✗)** : Nouveau type d'annotation rapide permettant d'apposer un checkmark vert (✓) ou une croix rouge (✗) en un clic, reproduisant le geste papier le plus fréquent. Rendu canvas + PDF final. Demandé par Philippe Carr et Patrick Dupont.
- **Mode tampon rapide** : Boutons V/X dans la barre d'outils du viewer. Un clic active le mode, puis chaque rectangle dessiné crée instantanément un tampon sans ouvrir l'éditeur d'annotation.
- **Mémorisation automatique des remarques** : Les remarques substantielles (>5 caractères) sont automatiquement sauvegardées dans la banque personnelle d'annotations pour réutilisation entre copies. Contexte exercice/question préservé.

#### Interface de Correction (CorrectorDesk)

- **Vue scindée (Split View)** : Nouveau bouton "Split" permettant d'afficher le barème en permanence à côté de la copie PDF, éliminant les allers-retours constants entre panneaux. Panneau redimensionnable (320px). Demandé par Chawki Saadi.
- **Types d'annotation étendus** : L'éditeur d'annotation propose désormais 6 types : Commentaire, Surlignage, Erreur, Bonus, Vrai (✓), Faux (✗).

#### Administration

- **Déverrouillage admin (Force Unlock)** : Nouvel endpoint `POST /grading/copies/{id}/force-unlock/` et bouton "Déverrouiller" dans la toolbar admin. Résout le bug bloquant des copies en mode "locked" signalé par Patrick Dupont et Philippe Carr.
- **Réouverture de copie finalisée (GRADED → READY)** : Nouvel endpoint `POST /grading/copies/{id}/reopen/` et bouton "Rouvrir" (superuser uniquement). Permet de corriger une erreur après finalisation, avec invalidation du PDF final. Demandé par Edouard Rousseau.
- **Nouvel événement d'audit REOPEN** : Traçabilité complète des réouvertures dans le journal d'événements.

#### Tableau de Bord Correcteur

- **Indicateur de progression par question** : Chaque copie affiche une barre de progression segmentée montrant les questions notées vs non notées (ex: "5/8 questions notées — 63%"). Demandé par Sami Ben Tiba.

#### Backend & Base de Données

- **Migration 0015** : Ajout des types d'annotation VRAI/FAUX et de l'action GradingEvent REOPEN.
- **PDF Flattener** : Support du rendu des tampons V/✗ dans le PDF final généré (symboles vectoriels).

#### Documentation

- Mise à jour complète de toute la documentation (guides utilisateurs, référence API, schéma BDD, workflows, ADR).

---

## [1.4.0] - 2026-03-10

### 🎓 Portail Élève — Améliorations

- **Bannière de transparence** : Ajout d'un encart "Garanties du processus de correction" en haut du dashboard élève (`ResultView.vue`)
  - Correction humaine uniquement (pas d'IA)
  - Anonymisation des copies avant correction
  - Répartition aléatoire entre correcteurs
  - Contrôle complémentaire post-finalisation
- **Import Lucide** : Ajout de l'icône `ShieldCheck` pour la bannière

### 🐛 Corrigé — Connexion Mobile Élèves

- **Root cause** : Rate limiter trop agressif (`5/15m` par IP) bloquait les classes entières derrière un NAT partagé (opérateur mobile / WiFi école). Le 403 générique DRF causait une boucle de retry côté frontend.
- **Backend** (`students/views.py`) :
  - Rate limit porté de `5/15m` à `30/15m` (30 tentatives / 15 min par IP)
  - Passage de `block=True` à `block=False` avec vérification manuelle `request.limited`
  - Retour **HTTP 429** (au lieu de 403) avec message français clair : *"Trop de tentatives de connexion. Veuillez réessayer dans quelques minutes."*
  - Champ `rate_limited: true` dans la réponse JSON pour identification côté frontend
- **Frontend** (`errorMessages.js`) :
  - Ajout case explicite `429` dans `getErrorMessage()` affichant le message serveur

### 📚 Documentation — Mise à jour complète

- **README.md** : Date actualisée, rate limiting mis à jour
- **CHANGELOG.md** : Entrée v1.4.0
- **docs/INDEX.md** : Version 1.5, date 10 mars 2026
- **docs/README.md** : Version et date actualisées
- **docs/security/MANUEL_SECURITE.md** : Rate limit 30/15m, HTTP 429, version mise à jour
- **docs/security/SECURITY_PERMISSIONS_INVENTORY.md** : Valeurs rate limit corrigées
- **docs/technical/API_REFERENCE.md** : Rate limit 30/15m, message 429 actualisé
- **docs/users/GUIDE_ETUDIANT.md** : Bannière transparence, mot de passe par défaut (date de naissance), version
- **docs/QUICKSTART.md** : Login élève email+mot de passe, date mise à jour
- **docs/technical/CURRENT_STATE_MARCH_2026.md** : Bannière, rate limit, date

---

## [1.3.0] - 2026-02-14

### 📚 Documentation — Mise à jour complète

- **README.md** : Réécriture complète — architecture illustrée, stack technique détaillée, modèle de données, API REST (~60 endpoints), rôles/permissions, workflow de correction, OCR/IA, installation dev/prod
- **docs/INDEX.md** : Liens corrigés (chemins `technical/`, `deployment/`, `development/`), métadonnées actualisées, historique des versions
- **docs/README.md** : Réécrit comme index rapide avec tables par public
- **docs/technical/ARCHITECTURE.md** : Python 3.11, OCR dual (GPT-4o-mini + Tesseract), machine d'états 6 statuts, production Docker Compose server.yml, évolutions réalisées depuis v1.0
- **docs/technical/DATABASE_SCHEMA.md** : 5 apps (~20 modèles), modèles core (AuditLog, GlobalSettings, UserProfile), champ `version` sur Annotation, statuts GRADING_IN_PROGRESS/GRADING_FAILED, Student.groupe, CopyLock TTL/heartbeat
- **Archivage** : 38 fichiers .md obsolètes déplacés de la racine vers `docs/archive/root_reports/`
- **Liens** : Tous les liens internes corrigés (INDEX.md, README.md principal, docs/README.md)

### 🔧 Maintenance
- Racine nettoyée : seuls README.md, CHANGELOG.md et BILAN_AFFECTATIONS.md conservés
- Correction des chemins cassés vers `technical/`, `deployment/`, `development/` dans toute la documentation

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
- `docs/` : Documentation technique complète

---

## [Unreleased]

### 🔄 En Cours
- Atteindre 70% coverage code critique
- Tests sécurité frontend (XSS, localStorage)

### 🎯 Prévu
- CI/CD Pipeline (GitHub Actions, déploiement automatique)
- Optimisation performance (N+1 queries, cache Redis)
- Validation fichiers PDF renforcée
- Notifications email élèves (copies disponibles)

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
- [Documentation](docs/INDEX.md)

---

**Projet** : Korrigo (Korrigo)  
**Contexte** : Production institutionnelle (AEFE / Éducation nationale)  
**Mainteneur** : Alaeddine BEN RHOUMA
