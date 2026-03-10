# État Actuel du Projet Korrigo — Mars 2026

> **Version** : 2.1  
> **Date** : 10 mars 2026  
> **Public** : Développeurs, Administrateurs, Product Owners

Ce document décrit l'état actuel de l'application Korrigo PMF tel qu'implémenté dans le code source.

---

## 📋 Table des Matières

1. [Architecture Frontend](#architecture-frontend)
2. [Routes et Navigation](#routes-et-navigation)
3. [Interfaces par Rôle](#interfaces-par-rôle)
4. [Fonctionnalités Clés](#fonctionnalités-clés)
5. [Workflows Métier](#workflows-métier)
6. [API Backend](#api-backend)

---

## Architecture Frontend

### Stack Technique

| Technologie | Version | Usage |
|-------------|---------|-------|
| **Vue.js** | 3.4+ | Framework UI (Composition API) |
| **Vue Router** | 4.2+ | Routing SPA |
| **Pinia** | 2.1+ | State management (auth, exam) |
| **Vite** | 5.x | Build tool |
| **TailwindCSS** | 4.x | Styling |
| **Axios** | - | Appels API |

### Structure des Fichiers

```
frontend/src/
├── App.vue                    # Root component
├── main.js                    # Entry point
├── router/index.js            # Configuration des routes
├── stores/
│   ├── auth.js                # Store authentification
│   └── examStore.js           # Store examens
├── services/
│   ├── api.js                 # Client API générique
│   └── gradingApi.js          # API correction
├── views/
│   ├── Home.vue               # Page d'accueil (portail login)
│   ├── HomeView.vue           # Landing page Korrigo
│   ├── Login.vue              # Login Admin/Teacher
│   ├── AdminDashboard.vue     # Dashboard administrateur
│   ├── CorrectorDashboard.vue # Dashboard correcteur
│   ├── GuideEnseignant.vue    # Guide enseignant
│   ├── GuideEtudiant.vue      # Guide élève
│   ├── DirectionConformite.vue # Page direction
│   ├── Settings.vue           # Paramètres
│   ├── admin/
│   │   ├── CorrectorDesk.vue      # Interface correction
│   │   ├── IdentificationDesk.vue # Video-coding
│   │   ├── UserManagement.vue     # Gestion utilisateurs
│   │   ├── StapleView.vue         # Agrafage fascicules
│   │   ├── MarkingSchemeView.vue  # Configuration barème
│   │   ├── ExamStudentList.vue    # Liste élèves/notes
│   │   └── ImportCopies.vue       # Import copies
│   ├── corrector/
│   │   ├── MyStudents.vue         # Mes élèves
│   │   └── StudentBilan.vue       # Bilan élève
│   └── student/
│       ├── LoginStudent.vue       # Login élève
│       ├── ResultView.vue         # Portail résultats
│       └── ChangePasswordStudent.vue
└── components/
    ├── CanvasLayer.vue            # Annotations sur PDF
    ├── AnnotationSuggestionsPanel.vue
    ├── ExamUploadModal.vue
    └── ...
```

---

## Routes et Navigation

### Routes Publiques

| Route | Composant | Description |
|-------|-----------|-------------|
| `/` | `Home.vue` | Portail d'accueil avec cartes de connexion |
| `/korrigo` | `HomeView.vue` | Landing page marketing |
| `/korrigo/guide-enseignant` | `GuideEnseignant.vue` | Documentation enseignants |
| `/korrigo/guide-eleve` | `GuideEtudiant.vue` | Documentation élèves |
| `/korrigo/direction` | `DirectionConformite.vue` | Informations direction |
| `/admin/login` | `Login.vue` | Connexion administrateur |
| `/teacher/login` | `Login.vue` | Connexion enseignant |
| `/student/login` | `LoginStudent.vue` | Connexion élève |

### Routes Admin

| Route | Composant | Description |
|-------|-----------|-------------|
| `/admin-dashboard` | `AdminDashboard.vue` | Tableau de bord admin |
| `/admin/users` | `UserManagement.vue` | Gestion utilisateurs |
| `/admin/settings` | `Settings.vue` | Paramètres système |
| `/exam/:examId/identification` | `IdentificationDesk.vue` | Video-coding OCR |
| `/exam/:examId/staple` | `StapleView.vue` | Agrafage fascicules |
| `/exam/:examId/grading-scale` | `MarkingSchemeView.vue` | Configuration barème |
| `/exam/:examId/students` | `ExamStudentList.vue` | Liste élèves et notes |

### Routes Correcteur (Teacher)

| Route | Composant | Description |
|-------|-----------|-------------|
| `/corrector-dashboard` | `CorrectorDashboard.vue` | Tableau de bord correcteur |
| `/corrector/desk/:copyId` | `CorrectorDesk.vue` | Interface de correction |
| `/corrector/my-students` | `MyStudents.vue` | Liste de mes élèves |
| `/corrector/student/:studentId/bilan` | `StudentBilan.vue` | Bilan pédagogique élève |

### Routes Élève (Student)

| Route | Composant | Description |
|-------|-----------|-------------|
| `/student-portal` | `ResultView.vue` | Consultation copies corrigées |
| `/student/change-password` | `ChangePasswordStudent.vue` | Changement mot de passe |

---

## Interfaces par Rôle

### 1. Administrateur

#### Dashboard Admin (`/admin-dashboard`)

**Sidebar Navigation :**
- Gestion Examens (actif par défaut)
- Utilisateurs → `/admin/users`
- Paramètres → `/admin/settings`
- Déconnexion

**Contenu Principal :**
- Boutons : `+ Nouvel Examen`, `Importer Examen`
- Table des examens avec colonnes : Nom, Date, État
- Actions par examen :
  - **Agrafer** → `/exam/:id/staple`
  - **Barème** → `/exam/:id/grading-scale`
  - **Video-Coding** → `/exam/:id/identification`
  - **Correcteurs** → Modal assignation
  - **Sujets A/B** → Modal attribution variante
  - **Dispatcher** → Modal distribution équitable
  - **Élèves** → `/exam/:id/students`

**Modals :**
1. **Créer Examen** : Nom + Date
2. **Assigner Correcteurs** : Checkboxes enseignants
3. **Dispatcher Copies** : Distribution round-robin
4. **Sujets A/B** : Attribution manuelle ou OCR auto-detect

---

### 2. Correcteur (Enseignant)

#### Dashboard Correcteur (`/corrector-dashboard`)

**Header Navigation :**
- Modifier mot de passe
- 📊 Statistiques (si copies corrigées)
- 👥 Mes Élèves → `/corrector/my-students`
- Déconnexion

**Stats Overview (3 cartes) :**
- Copies Attribuées (total)
- Corrigées (vert)
- Reste à faire (orange)

**Section Statistiques (si copies corrigées) :**
- Tableau comparatif : Mon Lot vs Global
  - Moyenne, Médiane, Écart-type, Min, Max
- Graphique SVG : Répartition des notes 0-20
  - Courbe Mon Lot (violet)
  - Courbe Global (vert)
  - Lignes verticales : Moyenne (rouge), Médiane (orange)
- Statistiques par Groupe (tableau)

**Liste des Copies :**
- Cards avec : Nom examen, Anonymat, Status
- Bouton : `Corriger` ou `Voir`

#### Interface Correction (`/corrector/desk/:copyId`)

**Layout 3 colonnes :**

1. **Colonne Gauche - Viewer PDF**
   - Navigation pages (◀ ▶)
   - Zoom (+/−)
   - Image de la copie
   - Overlay canvas pour annotations

2. **Colonne Centrale - Barème**
   - Exercices collapsibles
   - Pour chaque question :
     - Input score (0 à max)
     - Champ remarque avec autosave
   - Appréciation globale (textarea)
   - Indicateur sync : ✓ OK / ⚠ Pending / ❌ Error

3. **Colonne Droite - Outils**
   - Onglets : Editor, History, Grading
   - Types d'annotations : Comment, Highlight, Error, Bonus
   - Panel suggestions d'annotations

**Fonctionnalités :**
- Autosave dual-layer (localStorage + serveur)
- Récupération brouillon automatique
- Anonymisation header pages (masquage identité)
- Attribution Sujet A/B

---

### 3. Élève

#### Portail Élève (`/student-portal`)

**Bannière de Transparence :**
- Encart « Garanties du processus de correction » en haut du dashboard
- Icône `ShieldCheck` (Lucide)
- Garanties affichées : correction humaine, anonymisation, répartition aléatoire, contrôle complémentaire

**Contenu :**
- Liste des copies corrigées (status GRADED)
- Pour chaque copie :
  - Nom examen
  - Note finale
  - Bouton télécharger PDF

**Authentification :**
- Login par Email + Mot de passe (date de naissance JJMMAAAA par défaut)
- Changement mot de passe obligatoire première connexion
- Rate limit : 30 tentatives / 15 min par IP (HTTP 429 avec message français)

---

## Fonctionnalités Clés

### 1. Gestion des Examens

| Fonctionnalité | Description |
|----------------|-------------|
| **Création** | Nom + Date |
| **Import PDF** | Upload scans → Split A3→A4 → Booklets |
| **Barème** | Structure hiérarchique Exercice > Question |
| **Sujets A/B** | Attribution manuelle ou OCR auto-detect |
| **Dispatch** | Distribution équitable round-robin |

### 2. Identification (Video-Coding)

| Fonctionnalité | Description |
|----------------|-------------|
| **OCR GPT-4o-mini** | Lecture automatique en-têtes |
| **Suggestions** | Matching fuzzy élèves CSV |
| **Validation** | Liaison Copy ↔ Student |
| **Anonymisation** | Génération anonymous_id séquentiel |

### 3. Correction Numérique

| Fonctionnalité | Description |
|----------------|-------------|
| **Viewer PDF** | Navigation, zoom, canvas overlay |
| **Annotations** | Comment, Highlight, Error, Bonus |
| **Scores** | Input par question avec validation |
| **Remarques** | Champ texte par question, autosave |
| **Appréciation** | Textarea globale, autosave |
| **Autosave** | Dual-layer (localStorage 300ms + serveur 2s) |
| **Suggestions** | Banque d'annotations contextuelles |

### 4. Statistiques

| Fonctionnalité | Description |
|----------------|-------------|
| **Mon Lot** | Stats sur copies du correcteur |
| **Global** | Stats sur toutes copies GRADED |
| **Par Groupe** | Ventilation par classe/groupe |
| **Graphique** | Courbe de répartition 0-20 |

### 5. Export et Publication

| Fonctionnalité | Description |
|----------------|-------------|
| **PDF Final** | Aplatissement annotations + bilan LLM |
| **Export CSV** | Format Pronote |
| **Portail Élève** | Consultation copies GRADED |

---

## Workflows Métier

### Workflow Complet

```
1. CRÉATION EXAMEN
   Admin → Créer examen (nom, date)
   Admin → Configurer barème
   Admin → Assigner correcteurs

2. IMPORT COPIES
   Admin → Upload PDF scans
   Système → Split A3→A4, créer Booklets
   Admin → Attribution Sujets A/B (manuel ou OCR)

3. IDENTIFICATION
   Admin/Secrétariat → Video-Coding
   OCR → Lecture en-têtes
   Validation → Liaison élèves
   Système → Anonymisation (STAGING → READY)

4. DISPATCH
   Admin → Distribuer copies
   Système → Round-robin équitable
   Copies → Assignées aux correcteurs

5. CORRECTION
   Correcteur → Verrouiller copie
   Correcteur → Annoter + Noter + Remarques
   Correcteur → Appréciation globale
   Correcteur → Finaliser (READY → GRADED)

6. FINALISATION
   Système → Calculer score total
   Système → Générer PDF final
   LLM → Bilan pédagogique personnalisé

7. PUBLICATION
   Admin → Export CSV Pronote
   Élèves → Consultation portail
```

### États des Copies

```
STAGING ──validate──→ READY ──lock──→ LOCKED ──finalize──→ GRADED
    ↑                   ↑              │
    └─── reject ────────┘──── unlock ──┘
```

---

## API Backend

### Endpoints Principaux

#### Authentification
- `POST /api/login/` — Login admin/teacher
- `POST /api/logout/` — Déconnexion
- `POST /api/students/login/` — Login élève
- `POST /api/change-password/` — Changement mot de passe

#### Examens
- `GET /api/exams/` — Liste examens
- `POST /api/exams/` — Créer examen
- `PATCH /api/exams/:id/` — Modifier examen
- `POST /api/exams/:id/dispatch/` — Dispatcher copies
- `GET/POST /api/exams/:id/bulk-subject-variant/` — Sujets A/B
- `POST /api/exams/:id/auto-detect-subject/` — OCR sujets

#### Copies
- `GET /api/copies/` — Liste copies (filtré par correcteur)
- `GET /api/grading/copies/:id/` — Détails copie
- `POST /api/grading/copies/:id/lock/` — Verrouiller
- `POST /api/grading/copies/:id/finalize/` — Finaliser

#### Correction
- `GET /api/grading/copies/:id/scores/` — Scores
- `PUT /api/grading/copies/:id/scores/` — Sauvegarder scores
- `GET /api/grading/copies/:id/remarks/` — Remarques
- `POST /api/grading/copies/:id/remarks/` — Créer/modifier remarque
- `GET/PUT /api/grading/copies/:id/global-appreciation/` — Appréciation

#### Annotations
- `GET /api/grading/copies/:id/annotations/` — Liste annotations
- `POST /api/grading/copies/:id/annotations/` — Créer annotation
- `DELETE /api/grading/annotations/:id/` — Supprimer annotation

#### Statistiques
- `GET /api/grading/exams/:id/stats/` — Stats examen

#### Élèves
- `GET /api/students/my-copies/` — Copies de l'élève connecté

---

## Base de Données

### Modèles Principaux

| Modèle | Table | Description |
|--------|-------|-------------|
| `Exam` | `exams_exam` | Examen, barème, correcteurs |
| `Copy` | `exams_copy` | Copie élève, status, scores |
| `Booklet` | `exams_booklet` | Fascicule (pages images) |
| `Student` | `students_student` | Élève, classe, groupe |
| `Score` | `grading_score` | Notes par question (JSON) |
| `Annotation` | `grading_annotation` | Annotation sur copie |
| `QuestionRemark` | `grading_questionremark` | Remarque par question |

### Champs Clés Copy

| Champ | Type | Description |
|-------|------|-------------|
| `status` | enum | STAGING, READY, GRADED |
| `anonymous_id` | string | ID anonyme (ex: 0F8E-001) |
| `global_appreciation` | text | Appréciation correcteur |
| `llm_summary` | text | Bilan LLM généré |
| `subject_variant` | char | A, B ou null |
| `assigned_corrector_id` | FK | Correcteur assigné |

---

*Document généré le 4 mars 2026*
