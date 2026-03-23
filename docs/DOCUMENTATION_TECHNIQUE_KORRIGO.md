# Korrigo — Documentation Technique Complète

**Plateforme de Correction Numérique Anonymisée d'Examens**
Version 2.0 — 23 Mars 2026

> Document à vocation **commerciale**, **pédagogique** et **technique**.
> Destiné aux décideurs, enseignants, équipes IT et partenaires institutionnels.

---

## Table des matières

1. [Présentation générale](#1-présentation-générale)
2. [Architecture technique](#2-architecture-technique)
3. [Stack technologique](#3-stack-technologique)
4. [Workflow des examens](#4-workflow-des-examens)
5. [Gestion des copies et PDFs](#5-gestion-des-copies-et-pdfs)
6. [Gestion du barème](#6-gestion-du-barème)
7. [Gestion des correcteurs](#7-gestion-des-correcteurs)
8. [Gestion des élèves](#8-gestion-des-élèves)
9. [Dashboard Correcteur](#9-dashboard-correcteur)
10. [Bureau de Correction (CorrectorDesk)](#10-bureau-de-correction-correctordesk)
11. [Portail Élève](#11-portail-élève)
12. [Dashboard Administrateur](#12-dashboard-administrateur)
13. [Intelligence Artificielle](#13-intelligence-artificielle)
14. [Sécurité](#14-sécurité)
15. [Conformité RGPD](#15-conformité-rgpd)
16. [Infrastructure réseau et serveur](#16-infrastructure-réseau-et-serveur)
17. [Base de données](#17-base-de-données)
18. [Observabilité et monitoring](#18-observabilité-et-monitoring)
19. [Atouts et différenciateurs](#19-atouts-et-différenciateurs)
20. [Arguments commerciaux](#20-arguments-commerciaux)

---

## 1. Présentation générale

### 1.1 Qu'est-ce que Korrigo ?

Korrigo est une plateforme web de **correction numérique anonymisée** d'examens sur papier, conçue pour les établissements scolaires du réseau AEFE et de l'Éducation Nationale. Elle digitalise intégralement le processus de correction tout en garantissant :

- **L'anonymat strict** des copies pendant toute la phase de correction
- **La traçabilité complète** de chaque action (audit trail RGPD)
- **L'équité** grâce à un barème structuré et partagé entre correcteurs
- **La restitution enrichie** aux élèves avec bilans pédagogiques personnalisés

### 1.2 Périmètre fonctionnel

| Acteur | Fonctionnalités principales |
|--------|---------------------------|
| **Administrateur** | Création d'examens, import de copies, gestion du barème, dispatch des correcteurs, publication des résultats, gestion des utilisateurs, rapports statistiques |
| **Correcteur (Enseignant)** | Correction copie par copie avec barème interactif, annotations visuelles (dont tampons V/X), remarques par question, appréciation globale, suivi de progression, mode split view (copie/corrigé côte à côte), réouverture de copies finalisées |
| **Élève** | Consultation de ses résultats, détail des notes par question, téléchargement du PDF corrigé, lecture du bilan pédagogique IA |

### 1.3 Contexte de déploiement

Korrigo est actuellement déployé en production pour le **Brevet Blanc de Mathématiques 2026** :
- **209 candidats** répartis sur 2 journées (BB_J1 : 106, BB_J2 : 103)
- **8 correcteurs** (4 par journée)
- **27 questions** par copie, barème sur 20 points
- Hébergé sur serveur dédié **Hetzner** (Allemagne — conformité RGPD UE)

---

## 2. Architecture technique

### 2.1 Architecture globale

```
┌─────────────────────────────────────────────────────────┐
│                    CLIENT (Navigateur)                    │
│              Vue.js 3 SPA + TailwindCSS                  │
└──────────────────────┬──────────────────────────────────┘
                       │ HTTPS (TLS 1.3)
┌──────────────────────▼──────────────────────────────────┐
│                   NGINX (Reverse Proxy)                   │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────────┐  │
│  │ Static SPA  │  │ /api/* proxy │  │ X-Accel-Redirect│  │
│  │ /korrigo/*  │  │  → Gunicorn  │  │ /internal-media │  │
│  └─────────────┘  └──────┬───────┘  └────────────────┘  │
└──────────────────────────┼──────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────┐
│              BACKEND (Django 4.2 + DRF)                   │
│  ┌─────────┐ ┌──────────┐ ┌─────────┐ ┌──────────────┐  │
│  │  Exams  │ │ Grading  │ │Students │ │Identification│  │
│  │  App    │ │  App     │ │  App    │ │    App       │  │
│  └────┬────┘ └────┬─────┘ └────┬────┘ └──────┬───────┘  │
│       │           │            │              │          │
│  ┌────▼───────────▼────────────▼──────────────▼───────┐  │
│  │            Services métier                         │  │
│  │  GradingService · AnnotationService · PDFFlattener │  │
│  │  LLMSummaryService · OCR · Validators              │  │
│  └────────────────────┬──────────────────────────────┘  │
└───────────────────────┼─────────────────────────────────┘
          ┌─────────────┼─────────────┐
          ▼             ▼             ▼
   ┌────────────┐ ┌──────────┐ ┌──────────┐
   │ PostgreSQL │ │  Redis   │ │  Ollama  │
   │   (BDD)    │ │ (Cache/  │ │  (LLM    │
   │            │ │  Celery) │ │  local)  │
   └────────────┘ └──────────┘ └──────────┘
```

### 2.2 Principes architecturaux

- **Séparation des responsabilités** : chaque app Django gère un domaine métier
- **Default Deny** : tous les endpoints requièrent authentification par défaut (`IsAuthenticated`)
- **Machine d'états stricte** : les copies suivent un cycle de vie formel (ADR-003)
- **Audit systématique** : chaque action critique génère un `GradingEvent` horodaté
- **Coordonnées normalisées** : les annotations utilisent des coordonnées `[0,1]` (ADR-002)
- **Verrouillage optimiste** : prévention des mises à jour concurrentes via versioning

---

## 3. Stack technologique

### 3.1 Backend

| Composant | Technologie | Version | Rôle |
|-----------|------------|---------|------|
| Framework | Django | 4.2 LTS | Framework web principal |
| API REST | Django REST Framework | latest | Endpoints API RESTful |
| Documentation API | drf-spectacular | 0.27.1 | OpenAPI 3.0 / Swagger |
| Base de données | PostgreSQL | 15+ | Stockage relationnel |
| Cache / Broker | Redis | 7+ | Cache, rate limiting, file Celery |
| Tâches async | Celery | latest | Traitements en arrière-plan |
| Serveur WSGI | Gunicorn | latest | Serveur d'application |
| Manipulation PDF | PyMuPDF | 1.23.26 | Rasterisation, annotations, export |
| OCR | Tesseract (pytesseract) | latest | Reconnaissance de texte |
| Vision | OpenCV | 4.8.1 | Traitement d'images |
| Validation MIME | python-magic | 0.4.27 | Vérification type de fichier |
| Rate limiting | django-ratelimit | 4.1.0 | Protection brute force |
| CSP | django-csp | 3.8 | Content Security Policy |
| Métriques | prometheus-client | 0.19.0 | Métriques Prometheus |
| Logs structurés | python-json-logger | 2.0.7 | Logs JSON en production |

### 3.2 Frontend

| Composant | Technologie | Version | Rôle |
|-----------|------------|---------|------|
| Framework | Vue.js | 3.4 | Framework réactif SPA |
| Routage | Vue Router | 4.2 | Navigation côté client |
| État global | Pinia | 2.1 | Store centralisé |
| HTTP | Axios | 1.13 | Client HTTP avec intercepteurs |
| Styles | TailwindCSS | 4.1 | Utility-first CSS |
| Icônes | Lucide | 0.563 | Bibliothèque d'icônes SVG |
| PDF Viewer | pdfjs-dist | 4.0 | Rendu PDF dans le navigateur |
| Build | Vite | 5.1 | Bundler ultra-rapide |
| Tests E2E | Playwright | 1.57 | Tests navigateur automatisés |
| Typage | TypeScript | 5.9 | Typage statique optionnel |

### 3.3 Infrastructure

| Composant | Technologie | Rôle |
|-----------|------------|------|
| Conteneurisation | Docker + Docker Compose | Orchestration des services |
| Reverse proxy | Nginx | TLS, routage, fichiers statiques |
| Serveur | Hetzner Dédié (Allemagne) | 12 cores, 62 GB RAM |
| LLM local | Ollama + Qwen 2.5:32b | Bilans pédagogiques IA |
| Certificats TLS | Let's Encrypt | HTTPS automatique |

---

## 4. Workflow des examens

### 4.1 Cycle de vie d'un examen

```
Création → Configuration → Import copies → Validation → Dispatch
    → Correction → Finalisation → Publication → Consultation élève
```

#### Étape 1 — Création de l'examen

L'administrateur crée un examen via le dashboard avec :
- **Nom** de l'examen (ex: `BB_J1`, `BB_J2`)
- **Date** de l'examen
- **Mode d'upload** :
  - `BATCH_A3` : scan par lots (un gros PDF, découpage automatique par nombre de pages par fascicule)
  - `INDIVIDUAL_A4` : fichiers individuels (un PDF par élève, déjà découpés)
- **Fichier CSV** des élèves (optionnel) : `Nom-Prenom,Date-naissance,Adresse-mail,Classe,Groupe`

**Endpoint** : `POST /api/exams/` — Crée l'examen
**Endpoint** : `PUT /api/exams/<id>/` — Modifie l'examen

#### Étape 2 — Import du barème (Grading Structure)

Le barème est défini en JSON hiérarchique dans le champ `grading_structure` de l'examen :

```json
[
  {
    "id": 1, "label": "Exercice 1 — QCM", "points": 5,
    "children": [
      { "id": "1.1", "label": "Q1", "points": 1 },
      { "id": "1.2", "label": "Q2", "points": 1 }
    ]
  },
  {
    "id": 2, "label": "Exercice 2 — Fonctions", "points": 5,
    "children": [...]
  }
]
```

**Endpoint** : `GET/PUT /api/exams/<id>/` — Lecture/modification du barème via `grading_structure`
**Vue admin** : `MarkingSchemeView.vue` — éditeur visuel du barème

#### Étape 3 — Upload des documents officiels

Trois types de documents PDF sont gérés par lot versionné (`ExamDocumentSet`) :

| Type | Description |
|------|------------|
| `sujet` | Énoncé de l'examen |
| `corrige` | Corrigé officiel |
| `bareme` | Barème détaillé |

Chaque document est :
- Validé (taille ≤ 50 MB, MIME `application/pdf`, intégrité PyMuPDF)
- Hashé en SHA-256 pour traçabilité et déduplication
- Extrait en texte (pipeline `DocumentTextExtraction` → `DocumentPage` → `DocumentChunk`)
- Découpé en segments par exercice/question pour les **suggestions contextuelles** aux correcteurs

**Endpoint** : `POST /api/exams/<exam_id>/document-sets/` — Upload d'un lot
**Endpoint** : `POST /api/exams/<exam_id>/document-sets/<set_id>/activate/` — Activer une version

#### Étape 4 — Import des copies

**Mode INDIVIDUAL_A4** (utilisé en production) :
1. L'administrateur uploade les PDFs individuels nommés `copie_NOM_PRENOM.pdf`
2. Chaque PDF crée une `Copy` en statut `STAGING`
3. Le PDF source est rastérisé en images PNG (144 DPI via PyMuPDF)
4. Un `Booklet` est créé avec la liste ordonnée des pages images
5. L'élève est associé automatiquement par matching nom de fichier → CSV → `Student`

**Endpoint** : `POST /api/exams/<exam_id>/upload-individual-pdfs/` — Upload multiple
**Endpoint** : `POST /api/exams/<exam_id>/copies/import/` — Import unitaire

#### Étape 5 — Validation des copies

Chaque copie passe de `STAGING` → `READY` après vérification :
- Les pages images existent sur disque
- Le fascicule est complet
- Validation individuelle ou en lot (`BulkCopyValidationView`)

**Endpoint** : `POST /api/exams/copies/<id>/validate/` — Validation unitaire
**Endpoint** : `POST /api/exams/<exam_id>/validate-all/` — Validation en lot

#### Étape 6 — Assignation des correcteurs (Dispatch)

L'administrateur assigne les correcteurs à l'examen puis lance le dispatch :
- Algorithme de répartition équitable des copies `READY` entre les correcteurs assignés
- Chaque copie reçoit un `assigned_corrector`, un `dispatch_run_id` (UUID traçable), et un `assigned_at`
- Protection : seules les copies `READY`/`STAGING` sont dispatchées

**Endpoint** : `POST /api/exams/<exam_id>/dispatch/` — Lance le dispatch

#### Étape 7 — Correction (détaillée en §10)

#### Étape 8 — Publication des résultats

L'administrateur publie les résultats en un clic :
- `results_released_at` est renseigné sur l'examen
- Les élèves peuvent alors voir leurs notes et télécharger leur PDF corrigé

**Endpoint** : `POST /api/grading/exams/<exam_id>/release-results/`
**Endpoint** : `POST /api/grading/exams/<exam_id>/unrelease-results/` — Retrait

---

## 5. Gestion des copies et PDFs

### 5.1 Machine d'états de la copie (ADR-003)

```
STAGING ──▶ READY ──▶ GRADING_IN_PROGRESS ──▶ GRADED
   │           │              │                    │
   │           │              ▼                    │
   │           │        GRADING_FAILED             │
   │           │              │                    │
   │           │              └──▶ (retry → GRADING_IN_PROGRESS)
   │           │                                   │
   │           └──▶ LOCKED (soft lock pour édition concurrente)
   │                                               │
   └──▶ PENDING_IDENTIFICATION (si OCR nécessaire) │
                                                   │
   GRADED ──▶ READY  (reopen : réouverture par admin/enseignant)
```

| Statut | Signification | Transitions possibles |
|--------|--------------|----------------------|
| `STAGING` | Copie importée, en attente de validation | → `READY` |
| `READY` | Prête à corriger | → `GRADING_IN_PROGRESS` |
| `GRADING_IN_PROGRESS` | Finalisation en cours (génération PDF) | → `GRADED` ou `GRADING_FAILED` |
| `GRADING_FAILED` | Échec de génération PDF | → `GRADING_IN_PROGRESS` (retry, max 3) |
| `GRADED` | Corrigée et finalisée | → `READY` (reopen) |

### 5.2 Modèle de données Copy

Chaque copie (`Copy`) possède :

| Champ | Type | Description |
|-------|------|------------|
| `id` | UUID | Identifiant unique |
| `anonymous_id` | CharField | Code d'anonymat (ex: `75FB-042`) |
| `exam` | FK → Exam | Examen parent (PROTECT) |
| `student` | FK → Student | Élève identifié (SET_NULL) |
| `assigned_corrector` | FK → User | Correcteur assigné |
| `status` | CharField | Statut machine d'états |
| `pdf_source` | FileField | PDF original scanné |
| `final_pdf` | FileField | PDF corrigé avec annotations |
| `subject_variant` | CharField | Sujet A ou B |
| `global_appreciation` | TextField | Appréciation du correcteur |
| `llm_summary` | TextField | Bilan pédagogique IA |
| `booklets` | M2M → Booklet | Fascicules composant la copie |

### 5.3 Pipeline PDF

```
PDF source → Rasterisation (PyMuPDF 144 DPI)
           → Images PNG par page (copies/pages/{uuid}/p000.png)
           → Booklet (liste ordonnée des pages)
           → Correction (annotations + scores)
           → PDFFlattener (génération PDF final)
           → PDF corrigé (copies/final/copy_{uuid}_corrected.pdf)
```

Le **PDFFlattener** génère le PDF final avec :
1. Pages de la copie avec annotations visuelles superposées (couleurs par type)
2. Page(s) de synthèse : note finale, détail par question, remarques, appréciation générale
3. Bilan pédagogique LLM (si généré)

### 5.4 Validation des PDFs

Quatre validateurs sont appliqués à chaque upload :

| Validateur | Vérification |
|-----------|-------------|
| `validate_pdf_size` | Taille ≤ 50 MB |
| `validate_pdf_not_empty` | Fichier non vide (> 0 bytes) |
| `validate_pdf_mime_type` | MIME type = `application/pdf` (python-magic) |
| `validate_pdf_integrity` | PDF non corrompu, ≤ 500 pages (PyMuPDF) |

---

## 6. Gestion du barème

### 6.1 Structure hiérarchique

Le barème est stocké en JSON dans `Exam.grading_structure`. Il supporte une arborescence à N niveaux :

```
Exercice 1 (5 pts)
  ├── Q1.1 (1 pt)
  ├── Q1.2 (1 pt)
  ├── Q1.3 (1 pt)
  ├── Q1.4 (1 pt)
  └── Q1.5 (1 pt)
Exercice 2 (5 pts)
  ├── Q2.1 (0.25 pt)
  ├── Q2.2 (0.50 pt)
  └── ... (10 sous-questions)
```

### 6.2 Notation par question

Les scores sont stockés dans le modèle `Score` :

```json
{
  "1.1": 1, "1.2": 0.5, "1.3": 1, "1.4": 0, "1.5": 1,
  "2.1": 0.25, "2.2": 0.50, ...
}
```

- **Un seul Score par copie** (contrainte unique en BDD)
- La note finale = somme de toutes les valeurs du `scores_data`
- Sauvegarde automatique en temps réel (autosave avec debounce)

### 6.3 Éditeur visuel (MarkingSchemeView)

L'administrateur dispose d'un éditeur visuel pour :
- Ajouter/supprimer des exercices et questions
- Définir les points par question avec précision au 0.25
- Visualiser le total et vérifier la cohérence

---

## 7. Gestion des correcteurs

### 7.1 Rôles et permissions

| Rôle | Groupe Django | Accès |
|------|-------------|-------|
| Admin | `admin` | Accès complet (CRUD examens, dispatch, publication, statistiques) |
| Teacher | `teacher` | Correction de ses copies assignées, annotations, scores, remarques |
| Student | `student` | Lecture seule de ses propres résultats |

Les permissions sont vérifiées à **3 niveaux** :
1. **DRF Permission Classes** : `IsAuthenticated`, `IsTeacherOrAdmin`, `IsAdminOnly`, `IsStudent`
2. **Router Guard Frontend** : `meta.requiresAuth` + `meta.role` sur chaque route
3. **Objet-level** : `IsOwnerOrAdmin`, `IsStudentForOwnData`

### 7.2 Assignation et dispatch

```
Admin sélectionne correcteurs → Exam.correctors (M2M)
Admin lance dispatch → Algorithme répartition équitable
  → Copy.assigned_corrector = correcteur
  → Copy.dispatch_run_id = UUID unique
  → Copy.assigned_at = timestamp
```

Exemple BB 2026 :
- BB_J1 : alaeddine (26), patrick (26), philippe (27), selima (27)
- BB_J2 : chawki (25), edouard (26), laroussi (26), sami (26)

### 7.3 Suivi de progression

Le `CorrectorDashboard` affiche pour chaque correcteur :
- Nombre total de copies / corrigées / restantes
- Statistiques détaillées (moyenne, médiane, écart-type, taux de réussite)
- Graphique de distribution comparé (lot personnel vs global)

---

## 8. Gestion des élèves

### 8.1 Import par CSV

Les élèves sont importés via fichier CSV :
```
Nom-Prenom,Date-naissance,Adresse-mail,Classe,Groupe
DUPONT Jean,15/03/2009,jean.dupont@eleve.school.tn,3ème A,Groupe 1
```

L'import crée :
1. Un objet `Student` (nom, prénom, date de naissance, email, classe, groupe)
2. Un `User` Django associé (username = email, mot de passe par défaut)
3. Association au groupe `student`

### 8.2 Authentification élève

- **Endpoint** : `POST /api/students/login/` — Login par email + mot de passe
- **Rate limiting** : 30 tentatives / 15 min par IP
- **Mot de passe initial** : `passe123` ou date de naissance (JJMMAAAA)
- **Changement obligatoire** : détecté automatiquement, redirection vers `/student/change-password`
- **Mode maintenance** : variable `STUDENT_ACCESS_BLOCKED` pour bloquer temporairement l'accès

### 8.3 Identification des copies

Le lien copie ↔ élève est établi par :
1. **Automatique** : matching nom de fichier PDF → email CSV → Student
2. **OCR** : reconnaissance du nom sur l'en-tête de copie (`OCRResult`)
3. **Manuel** : via l'interface `IdentificationDesk` (admin uniquement)

---

## 9. Dashboard Correcteur

### 9.1 Vue d'ensemble (`CorrectorDashboard.vue`)

Le correcteur voit immédiatement :
- **Compteurs** : Total copies | Corrigées | Restantes
- **Liste des copies** avec statut coloré (Prêt/Corrigé/Échec)
- **Statistiques personnelles** : moyenne, médiane, min, max, écart-type
- **Graphique SVG** : distribution des notes (lot personnel vs distribution globale)

### 9.2 Navigation

Le correcteur peut :
- Cliquer sur une copie → ouvre le `CorrectorDesk` (bureau de correction)
- Accéder à "Mes Élèves" → liste des élèves de son lot avec bilans
- Voir les statistiques de son examen

### 9.3 API utilisées

| Endpoint | Méthode | Description |
|----------|---------|------------|
| `/api/grading/copies/<copy_id>/annotations/` | GET/POST | Liste/crée des annotations |
| `/api/grading/copies/<copy_id>/scores/` | GET/PUT | Scores par question |
| `/api/grading/copies/<copy_id>/remarks/` | GET/POST | Remarques par question |
| `/api/grading/copies/<copy_id>/global-appreciation/` | GET/PUT | Appréciation globale |
| `/api/grading/copies/<copy_id>/finalize/` | POST | Finalise la copie |
| `/api/grading/exams/<exam_id>/stats/` | GET | Statistiques du correcteur |

---

## 10. Bureau de Correction (CorrectorDesk)

### 10.1 Interface

Le `CorrectorDesk` est l'interface centrale de correction, composée de :

```
┌──────────────────────────────────────────────────┐
│  Header : anonymat | statut | navigation pages   │
├──────────────┬───────────────────────────────────┤
│              │                                   │
│  Panneau     │     Visualisation de la copie     │
│  barème      │     (image PNG zoomable)          │
│  (scores     │                                   │
│   par Q)     │     + Annotations superposées     │
│              │       (CanvasLayer)               │
│  Remarques   │                                   │
│  par Q       │                                   │
│              │                                   │
├──────────────┴───────────────────────────────────┤
│  Footer : Appréciation globale | Finaliser       │
└──────────────────────────────────────────────────┘
```

### 10.2 Fonctionnalités détaillées

#### Notation par question
- Barème interactif dans le panneau latéral
- Chaque question affiche : label, points max, champ de saisie
- **Autosave** : les scores sont sauvegardés automatiquement avec debounce (2s)
- Indicateur visuel de sauvegarde (✓ vert / ⏳ en cours)

#### Annotations visuelles
- Click & drag sur l'image pour créer une annotation
- 6 types : **Commentaire** (bleu), **Surligné** (jaune), **Erreur** (rouge), **Bonus** (vert), **VRAI** (vert, tampon V), **FAUX** (rouge, tampon X)
- Coordonnées normalisées `[0,1]` (ADR-002) pour indépendance résolution
- CRUD complet avec **verrouillage optimiste** (champ `version` incrémenté atomiquement)

#### Remarques par question
- Texte libre associé à chaque question du barème
- Persistent (`QuestionRemark` — un par copie/question)
- Autosave avec debounce

#### Suggestions contextuelles
- **Banque d'annotations officielles** (`AnnotationTemplate`) générées depuis le barème/corrigé/sujet
- **Annotations personnelles** (`UserAnnotation`) avec compteur d'usage et auto-alimentation
- Panneau latéral de suggestions filtré par exercice/question

#### Appréciation globale
- Champ texte libre (`Copy.global_appreciation`)
- Autosave avec debounce

#### Tampon Vrai/Faux (V2)
- Boutons **V** (vert) et **X** (rouge) pour apposer rapidement un tampon sur la copie
- Mode **quick stamp** : un clic sur la copie dépose directement le tampon sélectionné
- Composant dédié : `TrueFalseTool.vue`

#### Mode Split View (V2)
- Affichage côte à côte : copie de l'élève à gauche, corrigé officiel à droite
- Synchronisation du zoom et de la navigation entre les deux panneaux
- Activation via bouton dans la barre d'outils du CorrectorDesk

#### Force Unlock (V2)
- Un administrateur ou l'enseignant propriétaire peut forcer le déverrouillage d'une copie bloquée
- Utile en cas de déconnexion ou de session expirée d'un autre correcteur

#### Réouverture de copie (V2)
- Transition `GRADED → READY` permettant de rouvrir une copie déjà finalisée
- Permet de corriger une erreur de notation après finalisation
- Accessible par l'enseignant ou l'administrateur

#### Indicateurs de progression (V2)
- Barre de progression dans le CorrectorDashboard montrant l'avancement de la correction
- Composant dédié : `ProgressDashboard.vue`

#### Finalisation
- Bouton "Finaliser" → `POST /api/grading/copies/<id>/finalize/`
- Génère le PDF final avec annotations aplaties + page de synthèse
- Transition atomique `READY → GRADING_IN_PROGRESS → GRADED`
- Retry automatique en cas d'échec (max 3 tentatives)

### 10.3 Protection des données

- **Anonymisation** : les pages d'en-tête (page 1, 5, 9...) et la dernière page (annexe) masquent l'identité
- **Lock système** : `CopyLock` empêche l'édition simultanée par deux correcteurs
  - TTL de 30 min, heartbeat keep-alive
  - Expiration automatique des locks obsolètes

### 10.4 Draft et récupération

- **Autosave serveur** : `DraftState` (un brouillon par copie/utilisateur)
  - Payload JSON complet de l'éditeur
  - Versioning + `client_id` anti-écrasement
- **Autosave local** : `localStorage` comme filet de sécurité
- **Restauration** : au chargement, propose de restaurer depuis le serveur ou le local

---

## 11. Portail Élève

### 11.1 Workflow élève

```
Login (email + mot de passe)
  → Changement mot de passe obligatoire (si défaut)
  → Portail résultats (/student-portal)
     → Sélection examen
     → Onglet Scores : détail par exercice et question
     → Onglet PDF : visualisation du PDF corrigé
     → Onglet Bilan : bilan pédagogique IA
```

### 11.2 Interface ResultView

L'élève voit :
- **Carte de note** : note finale `/20` avec jauge visuelle et mention
- **Détail par exercice** : dépliable, chaque question avec score / max et barre de progression
- **Remarques du correcteur** par question (si renseignées)
- **Appréciation générale** du correcteur
- **Bilan pédagogique IA** : texte personnalisé généré par LLM
- **PDF corrigé** : visualisation intégrée ou téléchargement

### 11.3 Classification des performances

| Score | Mention | Couleur |
|-------|---------|---------|
| ≥ 80% | Excellent | Émeraude |
| ≥ 65% | Bien | Bleu |
| ≥ 50% | Satisfaisant | Ambre |
| ≥ 35% | Insuffisant | Orange |
| < 35% | À renforcer | Rouge |

### 11.4 Sécurité d'accès

- Résultats visibles uniquement si `Exam.results_released_at` est renseigné
- Fichiers médias protégés : l'élève ne peut accéder qu'aux fichiers de **ses propres copies**
- Vérification en base : `Copy.student.user == request.user` ET `Copy.status == GRADED`

---

## 12. Dashboard Administrateur

### 12.1 Fonctionnalités

Le `AdminDashboard` centralise :

| Fonction | Description |
|----------|------------|
| **Liste des examens** | Affichage paginé avec statistiques par examen |
| **Créer un examen** | Modal de création (nom, date, mode upload) |
| **Upload de copies** | Modal d'upload avec barre de progression |
| **Dispatch** | Assignation des correcteurs et lancement |
| **Identification** | Desk de matching copie ↔ élève |
| **Barème** | Éditeur visuel de la grading_structure |
| **Agrafage** | StapleView pour gérer les fascicules |
| **Gestion utilisateurs** | Création, reset mot de passe, activation/désactivation |
| **Publication résultats** | Release / unrelease en un clic |
| **Export** | CSV des notes, export Pronote, export PDF global |
| **Statistiques** | Rapport statistique complet (StatsReport) |

### 12.2 Exports disponibles

| Format | Endpoint | Description |
|--------|----------|------------|
| CSV | `/api/exams/<id>/export-csv/` | Notes par élève |
| Pronote | `/api/exams/<id>/export-pronote/` | Format compatible Pronote |
| PDF | `/api/exams/<id>/export-pdf/` | PDF global de toutes les copies |

### 12.3 Rapport statistique (StatsReport)

Endpoint `GET /api/exams/stats-report/` calculé dynamiquement :

- **KPIs globaux** : moyenne, taux de réussite, taux TB, taux d'échec
- **Statistiques descriptives** : par journée (J1, J2) et global
- **Distribution des notes** : histogramme par tranches de 2 points
- **Mentions** : Très Bien / Bien / Assez Bien / Passable / Insuffisant
- **Par correcteur** : moyenne, médiane, min, max, écart-type, taux de réussite
- **Par groupe** : performance comparative des groupes de TD
- **Par classe** : comparaison inter-classes
- **Par sujet** : Sujet A vs Sujet B
- **Par question** : taux de réussite, zéro, difficulté
- **QCM** : distribution, élèves 5/5, corrélation QCM/note finale
- **Palmarès** : Top 15 et élèves en difficulté (< 5/20)
- **Qualité** : taux de remarques, annotations, appréciations, bilans LLM

---

## 13. Intelligence Artificielle

### 13.1 LLM local (Ollama)

Korrigo intègre un LLM local pour générer des **bilans pédagogiques personnalisés** :

| Paramètre | Valeur |
|-----------|--------|
| Moteur | Ollama |
| Modèle | Qwen 2.5:32b |
| Hébergement | Local (même serveur, réseau Docker) |
| Timeout | 300 secondes |
| Température | 0.7 |

### 13.2 Pipeline de génération

```
Copy GRADED → Collecte contexte
  → Score.scores_data (notes par question)
  → QuestionRemark (remarques du correcteur)
  → Annotation (toutes les annotations visuelles)
  → Copy.global_appreciation
  → Exam.grading_structure
→ Construction prompt (prompt engineering avancé)
→ Appel Ollama /api/generate
→ Persistance dans Copy.llm_summary
```

### 13.3 Structure du bilan

Le prompt impose une structure en 5 sections :
1. **Appréciation générale** (2-3 phrases situant le niveau)
2. **Points forts** (exercices/questions bien réussis)
3. **Points à améliorer** (lacunes, erreurs récurrentes)
4. **Conseils** (2-3 conseils concrets et actionnables)
5. **Encouragement final** (une phrase positive)

Règles du prompt :
- Tutoiement obligatoire (tu/ton/tes)
- Français uniquement
- 200 à 350 mots
- Basé uniquement sur les données fournies
- Pas de signature

### 13.4 Génération batch

**Endpoint** : `POST /api/grading/exams/<exam_id>/generate-summaries/`
- Génère les bilans pour toutes les copies GRADED d'un examen
- Option `force` pour régénérer les bilans existants
- Retourne un rapport : succès / ignorés / erreurs

### 13.5 OCR et identification

- **Tesseract** : reconnaissance du texte sur les en-têtes de copies
- **OpenCV** : traitement d'image (crop de la zone nom)
- **Matching** : texte OCR → liste CSV des élèves → suggestions classées par confiance

---

## 14. Sécurité

### 14.1 Authentification

| Mécanisme | Détail |
|-----------|--------|
| Sessions Django | `cached_db` engine, cookies HttpOnly + SameSite=Lax |
| Durée de session | 4 heures (14 400 s), expire à la fermeture du navigateur |
| CSRF | Token via cookie (CSRF_COOKIE_HTTPONLY=False pour SPA) |
| Mots de passe | Min 12 caractères, validateurs Django (similarity, common, numeric) |
| Rate limiting | Admin : 5/15 min par IP, Élèves : 30/15 min par IP |

### 14.2 Autorisation (RBAC)

```
                    IsAuthenticated (default deny)
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
          IsAdmin     IsTeacher     IsStudent
              │            │            │
              ▼            ▼            ▼
       Accès complet  Ses copies   Ses résultats
                       assignées    uniquement
```

Permissions spécifiques :
- `IsTeacherOrAdmin` : endpoints de correction et statistiques
- `IsAdminOnly` : création d'examens, dispatch, gestion utilisateurs
- `IsStudentForOwnData` : objet-level, l'élève ne voit que ses données
- `IsOwnerOrAdmin` : modification d'annotations par leur créateur uniquement

### 14.3 Protection des fichiers médias

**Avant** : Nginx servait `/media/` directement → tout fichier accessible par URL

**Après** (LOT 2) :
1. Le navigateur requête `/api/media/<path>`
2. Django vérifie l'authentification et les permissions
3. Si autorisé → header `X-Accel-Redirect: /internal-media/<path>`
4. Nginx sert le fichier depuis un `location` interne (pas d'accès direct)

Protection anti-traversée : `os.path.normpath()` + rejet de `..` et `/`

### 14.4 Headers de sécurité

| Header | Valeur (production) |
|--------|-------------------|
| X-Frame-Options | DENY |
| X-Content-Type-Options | nosniff |
| X-XSS-Protection | 1; mode=block |
| HSTS | max-age=31536000; includeSubDomains; preload |
| Content-Security-Policy | default-src 'self'; script-src 'self'; frame-ancestors 'none' |

### 14.5 Verrouillage concurrentiel

Deux mécanismes complémentaires :

1. **CopyLock** (soft lock)
   - Un seul correcteur peut éditer une copie à la fois
   - TTL 30 min, heartbeat keep-alive, expiration automatique
   - `select_for_update()` pour éviter les races conditions

2. **Verrouillage optimiste des annotations**
   - Champ `version` incrémenté atomiquement (`F('version') + 1`)
   - Le client envoie la version attendue → rejet si mismatch
   - Prévient les pertes de mise à jour en cas d'édition simultanée

### 14.6 Protection base de données

```python
# PostgreSQL timeouts (production)
lock_timeout = 5000ms        # Timeout d'attente de verrou
statement_timeout = 30000ms   # Timeout d'exécution requête
idle_in_transaction = 60000ms # Timeout transaction inactive
```

---

## 15. Conformité RGPD

### 15.1 Principes appliqués

| Principe RGPD | Implémentation |
|---------------|---------------|
| **Minimisation** | Seules les données nécessaires sont collectées (nom, prénom, date de naissance, email, classe) |
| **Pseudonymisation** | Copies identifiées par `anonymous_id` pendant la correction |
| **Traçabilité** | Audit trail complet via `GradingEvent` et `AuditLog` |
| **Droit d'accès** | Portail élève avec accès aux données personnelles |
| **Limitation** | Données conservées uniquement pour la durée de l'année scolaire |
| **Sécurité** | Chiffrement TLS, cookies HttpOnly, rate limiting, RBAC |

### 15.2 Audit Trail

Deux systèmes complémentaires :

1. **GradingEvent** (audit métier)
   - Actions : IMPORT, VALIDATE, LOCK, UNLOCK, CREATE_ANN, UPDATE_ANN, DELETE_ANN, FINALIZE, EXPORT
   - Champs : copy, action, actor, timestamp, metadata (JSON)
   - Indexé par (copy, timestamp) pour requêtes rapides

2. **AuditLog** (audit général)
   - Actions : login.success, login.failed, copy.download, copy.view...
   - Champs : user, student_id, action, resource_type, resource_id, ip_address, user_agent, metadata
   - Logging structuré vers fichier `audit.log` dédié

### 15.3 Hébergement

- **Serveur** : Hetzner (Falkenstein, Allemagne) — **UE, conforme RGPD**
- **Aucune donnée** n'est transférée hors UE
- **LLM local** : les bilans IA sont générés sur le même serveur (pas d'API cloud)
- **Pas de cookies tiers** : aucun tracker, analytics, ou service externe

---

## 16. Infrastructure réseau et serveur

### 16.1 Architecture serveur

```
Internet ──▶ DNS (korrigo.labomaths.tn)
           ──▶ Hetzner Dédié (88.99.254.59)
              ──▶ Docker Compose
                 ├── nginx (reverse proxy + TLS + SPA)
                 ├── backend (Django/Gunicorn)
                 ├── celery (worker async)
                 ├── redis (cache + broker)
                 ├── postgres (BDD)
                 └── ollama (LLM local)
```

### 16.2 Spécifications serveur

| Ressource | Valeur |
|-----------|--------|
| CPU | 12 cores |
| RAM | 62 GB |
| Stockage | SSD NVMe |
| OS | Linux |
| Localisation | Falkenstein, Allemagne |
| Bande passante | 1 Gbps |

### 16.3 Configuration Nginx

```nginx
# Frontend SPA
location /korrigo/ {
    root /usr/share/nginx/html;
    try_files $uri $uri/ /index.html;
}

# Backend API proxy
location /api/ {
    proxy_pass http://backend:8000;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}

# Fichiers médias protégés (internal only)
location /internal-media/ {
    internal;
    alias /app/media/;
}
```

### 16.4 TLS / HTTPS

- Certificats **Let's Encrypt** renouvelés automatiquement
- TLS 1.3 avec ciphers modernes
- HSTS activé avec preload
- Redirect HTTP → HTTPS

---

## 17. Base de données

### 17.1 Schéma relationnel

```
┌──────────┐      ┌──────────┐      ┌──────────┐
│   Exam   │──1:N─│   Copy   │──1:1─│  Score   │
│          │      │          │      │          │
│ name     │      │ anon_id  │      │scores_data│
│ date     │      │ status   │      │final_comment│
│ grading_ │      │ student  │      └──────────┘
│ structure│      │ corrector│
│ correctors│     │ booklets │──M:M─┌──────────┐
│ results_ │      └────┬─────┘      │ Booklet  │
│ released │           │            │ pages_   │
└──────────┘           │            │ images   │
                       │            └──────────┘
              ┌────────┼────────┐
              ▼        ▼        ▼
        ┌──────────┐ ┌─────┐ ┌────────────┐
        │Annotation│ │Lock │ │GradingEvent│
        │ x,y,w,h  │ │owner│ │ action     │
        │ content  │ │token│ │ actor      │
        │ type     │ │ TTL │ │ timestamp  │
        │ version  │ └─────┘ │ metadata   │
        └──────────┘         └────────────┘
```

### 17.2 Indexes de performance

```python
# Copy: recherche fréquente par statut et correcteur
Index(fields=['status'])
Index(fields=['exam', 'status'])
Index(fields=['assigned_corrector', 'status'])

# Annotation: recherche par copie et page
Index(fields=['copy', 'page_index'])

# GradingEvent: timeline par copie
Index(fields=['copy', 'timestamp'])

# CopyLock: nettoyage des locks expirés
Index(fields=['expires_at'])
```

### 17.3 Contraintes d'intégrité

| Contrainte | Table | Description |
|-----------|-------|------------|
| `PROTECT` | Copy → Exam | Empêche suppression d'un examen avec copies |
| `PROTECT` | Booklet → Exam | Empêche suppression d'un examen avec fascicules |
| `UniqueConstraint` | Score (copy) | Un seul score par copie |
| `UniqueConstraint` | CopyLock (copy) | Un seul lock par copie |
| `unique_together` | QuestionRemark (copy, question_id) | Une remarque par question/copie |
| `unique_together` | DraftState (copy, owner) | Un brouillon par copie/utilisateur |
| `SET_NULL` | Copy → Student | Suppression élève ne supprime pas la copie |

---

## 18. Observabilité et monitoring

### 18.1 Logging structuré

**Production** : logs JSON pour agrégation
```json
{
  "timestamp": "2026-03-10T18:30:00Z",
  "level": "INFO",
  "logger": "grading",
  "message": "Copy finalized",
  "request_id": "a1b2c3d4-...",
  "user_id": 42,
  "path": "/api/grading/copies/.../finalize/",
  "method": "POST"
}
```

**Fichiers de log** :
- `django.log` : logs applicatifs (rotation 10 MB × 10 fichiers)
- `audit.log` : audit trail dédié

### 18.2 Métriques Prometheus

| Métrique | Type | Description |
|----------|------|------------|
| `grading_import_duration_seconds` | Histogram | Durée d'import PDF |
| `grading_finalize_duration_seconds` | Histogram | Durée de finalisation |
| `grading_ocr_errors_total` | Counter | Erreurs OCR/rasterisation |
| `grading_lock_conflicts_total` | Counter | Conflits de verrouillage |
| `grading_copies_by_status` | Gauge | Copies par statut (backlog) |
| `http_requests_total` | Counter | Requêtes HTTP par path/status |
| `http_request_duration_seconds` | Histogram | Latence des requêtes |

**Endpoint** : `GET /metrics` (Prometheus format, authentification optionnelle via token)

### 18.3 Request ID

Chaque requête HTTP reçoit un UUID unique (`X-Request-ID`) :
- Généré automatiquement ou accepté du client (distributed tracing)
- Injecté dans tous les logs via `RequestContextLogFilter`
- Retourné dans le header de réponse

### 18.4 Health checks

| Endpoint | Rôle |
|----------|------|
| `/api/health/` | Health check général |
| `/api/health/live/` | Liveness probe (Docker) |
| `/api/health/ready/` | Readiness probe (BDD + Redis) |

---

## 19. Atouts et différenciateurs

### 19.1 Anonymat garanti

- Les copies sont **systématiquement anonymisées** pendant la correction
- Le correcteur ne voit que le code anonymat (`anonymous_id`)
- L'identification copie ↔ élève est gérée séparément par l'administrateur
- Les pages contenant le nom de l'élève sont masquées dans le CorrectorDesk

### 19.2 Traçabilité complète

- **Chaque action** (import, validation, annotation, modification, finalisation) est tracée
- Horodatage, acteur, métadonnées contextuelles
- Impossible de modifier une copie finalisée
- Journal d'audit consultable par l'administrateur

### 19.3 Équité de correction

- **Barème partagé** : tous les correcteurs utilisent exactement le même barème
- **Notation question par question** : impossible de « noter à la louche »
- **Statistiques comparatives** : l'administrateur peut détecter les écarts entre correcteurs
- **Variantes A/B** : prise en compte des sujets différents

### 19.4 IA locale et souveraine

- Le LLM tourne **sur le serveur** (pas de cloud, pas d'API externe)
- **Aucune donnée élève** ne quitte le serveur
- Bilans personnalisés pour chaque élève
- Ton bienveillant et pédagogique, structuré en 5 points

### 19.5 Zéro perte de données

- **Autosave** triple couche : serveur (DraftState) + localStorage + scores en temps réel
- **Verrouillage optimiste** : détection des conflits d'édition
- **Retry automatique** : finalisation avec max 3 tentatives
- **Protection PostgreSQL** : timeouts, PROTECT sur les FK critiques

### 19.6 UX moderne

- Interface réactive (Vue.js 3 + TailwindCSS)
- Responsive design (desktop + mobile)
- Icônes SVG (Lucide)
- Toasts de notification (pas d'alerts intrusifs)
- Barre de progression pour les uploads longs

---

## 20. Arguments commerciaux

### 20.1 Pour les établissements

| Argument | Détail |
|----------|--------|
| **Gain de temps** | Fini le transport de copies, la gestion papier, les calculs manuels |
| **Anonymat** | Conformité avec les recommandations de l'Éducation Nationale |
| **Traçabilité** | Preuve numérique de chaque étape de correction |
| **Statistiques** | Rapport de jury automatique avec 15+ indicateurs |
| **Export** | Compatible Pronote, CSV standard |

### 20.2 Pour les enseignants

| Argument | Détail |
|----------|--------|
| **Barème structuré** | Notation guidée question par question |
| **Annotations** | Banque d'annotations contextuelles + personnelles |
| **Suivi** | Dashboard personnel avec statistiques en temps réel |
| **Fiabilité** | Autosave permanent, jamais de perte de données |
| **Bilans IA** | Génération automatique de bilans pédagogiques |

### 20.3 Pour les élèves

| Argument | Détail |
|----------|--------|
| **Transparence** | Détail de chaque point gagné ou perdu |
| **Feedback enrichi** | Remarques par question + appréciation + bilan IA |
| **Accessibilité** | Résultats consultables depuis n'importe quel navigateur |
| **PDF corrigé** | Téléchargement de la copie corrigée annotée |

### 20.4 Pour les DSI / IT

| Argument | Détail |
|----------|--------|
| **Souveraineté** | Hébergement UE, IA locale, zéro service cloud tiers |
| **Sécurité** | RBAC, CSP, HSTS, rate limiting, audit trail |
| **RGPD** | Conforme par conception (Privacy by Design) |
| **API documentée** | OpenAPI 3.0 / Swagger |
| **Monitoring** | Prometheus + health checks + logs structurés |
| **Conteneurisé** | Docker Compose, déploiement reproductible |

### 20.5 Comparatif

| Critère | Korrigo | Solutions cloud (Pronote, etc.) |
|---------|---------|-------------------------------|
| Anonymat natif | ✅ Systématique | ❌ Rarement |
| IA pédagogique | ✅ LLM local | ❌ Non |
| Données en UE | ✅ Garanti | ⚠️ Variable |
| Annotation visuelle | ✅ Sur la copie | ❌ Non |
| Barème interactif | ✅ JSON hiérarchique | ⚠️ Limité |
| Autosave | ✅ Triple couche | ⚠️ Variable |
| Open API | ✅ OpenAPI 3.0 | ❌ Fermé |
| Coût récurrent | ✅ Serveur dédié | ❌ Licence/élève |

---

## Annexes

### A. Glossaire

| Terme | Définition |
|-------|-----------|
| **Copy** | Copie d'examen numérisée d'un élève |
| **Booklet** | Fascicule (groupe de pages) avant assemblage |
| **anonymous_id** | Code d'anonymat de la copie (ex: 75FB-042) |
| **GradingEvent** | Événement d'audit du workflow de correction |
| **CopyLock** | Verrou exclusif pour l'édition concurrente |
| **DraftState** | Brouillon autosavé de la correction en cours |
| **Score** | Objet contenant les notes détaillées par question |
| **AnnotationTemplate** | Suggestion d'annotation officielle issue du barème |
| **UserAnnotation** | Annotation personnelle du correcteur (mémoire) |
| **DocumentChunk** | Segment de texte extrait d'un document officiel |

### B. Endpoints API (résumé)

| Préfixe | Module | Endpoints |
|---------|--------|-----------|
| `/api/exams/` | Examens | 20 endpoints (CRUD, upload, dispatch, export, stats) |
| `/api/grading/` | Correction | 18 endpoints (annotations, scores, finalisation, LLM) |
| `/api/students/` | Élèves | 7 endpoints (login, profil, copies, changement MDP) |
| `/api/identification/` | OCR | Endpoints d'identification copie ↔ élève |
| `/api/` | Core | Login, logout, CSRF, users, settings, media, health, metrics |

### C. Documentation API interactive

Accessible à : `https://korrigo.labomaths.tn/api/docs/` (Swagger UI)
Schéma OpenAPI : `https://korrigo.labomaths.tn/api/schema/`

---

*Document généré le 10 mars 2026 — Korrigo v1.0*
*Contact : Alaeddine BEN RHOUMA — contact@nexusreussite.academy*
