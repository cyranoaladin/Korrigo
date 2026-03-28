# Architecture Frontend Korrigo v2

> **Version** : 3.0
> **Date** : 28 Mars 2026
> **Public** : Développeurs Frontend, Architectes, Contributeurs

Ce document décrit l'architecture complète du frontend de la plateforme Korrigo — une Single Page Application Vue 3 moderne qui couvre l'ensemble du cycle de correction numérique d'examens.

---

## Table des matières

1. [Vue d'ensemble](#1-vue-densemble)
2. [Stack technique](#2-stack-technique)
3. [Structure du projet](#3-structure-du-projet)
4. [Routing et navigation](#4-routing-et-navigation)
5. [State management — Pinia](#5-state-management--pinia)
6. [Client HTTP — Axios](#6-client-http--axios)
7. [Vues principales](#7-vues-principales)
8. [Composants partagés](#8-composants-partagés)
9. [Tests](#9-tests)
10. [Build et déploiement](#10-build-et-déploiement)
11. [Variables d'environnement](#11-variables-denvironnement)

---

## 1. Vue d'ensemble

Le frontend Korrigo est une **Single Page Application (SPA)** qui prend en charge :

- **Authentification multi-rôles** : Admin, Enseignant (Teacher), Élève (Student)
- **Interface de correction annotée** : visualisation d'images de pages, dessin de rectangles d'annotation, notation par question, appréciation globale
- **Administration des examens** : import de copies PDF, dispatch aux correcteurs, identification OCR, publication des résultats
- **Espace élève** : consultation des copies corrigées et du bilan LLM

### Principes architecturaux

- **Composition API** : tous les composants utilisent `<script setup>` — pas d'Options API
- **Pas de TypeScript dans les fichiers Vue** : le typage statique est optionnel et limité aux utilitaires (le projet compile en JavaScript au runtime)
- **Pinia** pour un state management centré et prévisible
- **Contrôle d'accès par rôle** : navigation guards dans Vue Router
- **Desktop prioritaire** : l'interface de correction suppose un écran large

---

## 2. Stack technique

| Dépendance | Version | Rôle |
|------------|---------|------|
| **Vue.js** | 3.4.15 | Framework UI (Composition API, `<script setup>`) |
| **Vite** | 5.1.0 | Build tool, dev server, HMR |
| **Pinia** | 2.1.7 | State management global |
| **Vue Router** | 4.2.5 | Routing SPA, navigation guards |
| **Axios** | 1.13.2 | Client HTTP REST |
| **pdfjs-dist** | 4.0.0 | Rendu PDF côté navigateur (non utilisé directement — les pages sont servies comme images PNG par le backend) |
| **lucide-vue-next** | 0.563.0 | Bibliothèque d'icônes SVG |
| **TailwindCSS** | 4.1.18 | Framework CSS utilitaire (plugin Vite `@tailwindcss/vite`) |
| **TypeScript** | 5.9.3 | Typage statique (optionnel, `vue-tsc` pour vérification) |
| **ESLint** | 9.39.2 | Linting JavaScript/Vue |
| **Vitest** | 1.0.4 | Tests unitaires et d'intégration |
| **Playwright** | 1.57.0 | Tests End-to-End |
| **@vue/test-utils** | 2.4.3 | Utilitaires de test pour composants Vue |
| **msw** | 2.0.11 | Mock Service Worker pour tests d'intégration |

---

## 3. Structure du projet

```
frontend/
├── src/
│   ├── main.js                         # Point d'entrée : createApp + Pinia + Router
│   ├── App.vue                         # Composant racine (RouterView)
│   ├── style.css                       # Styles globaux + directives Tailwind
│   │
│   ├── router/
│   │   └── index.js                    # Configuration Vue Router (30+ routes)
│   │
│   ├── stores/
│   │   ├── auth.js                     # Store Pinia : authentification
│   │   └── examStore.js                # Store Pinia : examens / fascicules
│   │
│   ├── services/
│   │   ├── api.js                      # Instance Axios centrale
│   │   ├── gradingApi.js               # Appels REST spécifiques à la correction
│   │   └── pdfService.js               # Utilitaires PDF (PDF.js)
│   │
│   ├── layouts/
│   │   └── MainLayout.vue              # Layout avec Navbar + Footer (pages publiques)
│   │
│   ├── views/
│   │   ├── Home.vue                    # Portail d'accueil (sélection rôle)
│   │   ├── HomeView.vue                # Landing page marketing (/korrigo)
│   │   ├── Login.vue                   # Login Admin/Teacher (partagé, prop roleContext)
│   │   ├── AdminDashboard.vue          # Tableau de bord Admin
│   │   ├── CorrectorDashboard.vue      # Tableau de bord Correcteur
│   │   ├── Dashboard.vue               # Dashboard générique
│   │   ├── StatsReport.vue             # Rapport statistique BAC Blanc
│   │   ├── ExamEditor.vue              # Éditeur d'examen
│   │   ├── Settings.vue                # Paramètres admin
│   │   ├── StagingArea.vue             # Zone de staging
│   │   ├── GuideEnseignant.vue         # Guide utilisateur enseignant
│   │   ├── GuideEtudiant.vue           # Guide utilisateur élève
│   │   ├── DirectionConformite.vue     # Page direction/conformité
│   │   │
│   │   ├── admin/                      # Vues admin authentifiées
│   │   │   ├── CorrectorDesk.vue       # Interface de correction (VUE PRINCIPALE)
│   │   │   ├── ImportCopies.vue        # Import PDF copies
│   │   │   ├── IdentificationDesk.vue  # Identification copies ↔ élèves
│   │   │   ├── UserManagement.vue      # Gestion utilisateurs
│   │   │   ├── StapleView.vue          # Validation fascicules (staging)
│   │   │   ├── MarkingSchemeView.vue   # Éditeur barème
│   │   │   ├── ExamStudentList.vue     # Liste élèves d'un examen
│   │   │   └── QuestionnaireBilan.vue  # Bilan questionnaire correcteurs
│   │   │
│   │   ├── corrector/                  # Vues correcteur authentifiées
│   │   │   ├── MyStudents.vue          # Mes élèves
│   │   │   ├── QuestionnaireView.vue   # Questionnaire correcteur
│   │   │   └── StudentBilan.vue        # Bilan d'un élève
│   │   │
│   │   └── student/                    # Vues élève authentifiées
│   │       ├── LoginStudent.vue        # Connexion élève (email + mot de passe)
│   │       ├── ResultView.vue          # Résultats copies corrigées
│   │       └── ChangePasswordStudent.vue # Changement de mot de passe élève
│   │
│   ├── components/                     # 28 composants réutilisables
│   │   ├── AnnotationSuggestionsPanel.vue
│   │   ├── ArchitectureDiagram.vue
│   │   ├── BadgeRole.vue
│   │   ├── CanvasLayer.vue             # Dessin annotations sur canvas HTML5
│   │   ├── ChangePasswordModal.vue
│   │   ├── CollapsibleSection.vue
│   │   ├── CommentBank.vue             # Banque de commentaires prédéfinis
│   │   ├── CopyLifecycleDiagram.vue
│   │   ├── ExamTypeIcon.vue
│   │   ├── ExamTypeSelectionModal.vue
│   │   ├── ExamUploadModal.vue         # Modal upload copies PDF
│   │   ├── FeatureCard.vue
│   │   ├── Footer.vue
│   │   ├── GradingScaleBuilder.vue     # Constructeur de barème
│   │   ├── GradingSidebar.vue          # Panneau latéral de notation
│   │   ├── JuryReportsModal.vue        # Rapport de jury
│   │   ├── LoadingOverlay.vue
│   │   ├── Navbar.vue
│   │   ├── PDFViewer.vue               # Visualiseur pages copie
│   │   ├── ProgressDashboard.vue
│   │   ├── SectionContainer.vue
│   │   ├── stats/                      # Composants graphiques statistiques
│   │   ├── StepCard.vue
│   │   ├── TrueFalseTool.vue           # Tampons VRAI/FAUX
│   │   ├── UploadAnalyticsDashboard.vue
│   │   └── WorkflowDiagram.vue
│   │
│   ├── questionnaire/                  # Composants formulaire questionnaire
│   ├── utils/                          # Fonctions utilitaires partagées
│   └── assets/                         # Assets statiques (images, logos)
│
├── e2e/                                # Tests Playwright E2E
│   ├── global-setup.ts
│   ├── auth_flow.spec.ts
│   ├── student_flow.spec.ts
│   └── dispatch_flow.spec.ts
│
├── tests/                              # Tests Vitest (unitaires + intégration)
│
├── public/                             # Assets servis statiquement
├── index.html                          # Template HTML racine
├── vite.config.js                      # Configuration Vite + proxy dev
├── tailwind.config.js                  # Configuration TailwindCSS (v4)
├── playwright.config.ts                # Configuration Playwright E2E
├── playwright.workflow.config.ts       # Configuration Playwright workflows spécifiques
├── tsconfig.json                       # Configuration TypeScript
└── package.json                        # Dépendances npm
```

---

## 4. Routing et navigation

### 4.1 Configuration complète des routes

Le fichier `/src/router/index.js` définit toutes les routes avec `createWebHistory()`.

```javascript
// Routes publiques
{ path: '/',                   name: 'Portal',             component: Home }          // Portail sélection rôle
{ path: '/korrigo',            name: 'Landing',            component: HomeView }       // Landing marketing
{ path: '/korrigo/guide-enseignant', name: 'GuideEnseignant' }
{ path: '/korrigo/guide-eleve',      name: 'GuideEleve' }
{ path: '/korrigo/direction',        name: 'Direction' }

// Routes de connexion (publiques)
{ path: '/admin/login',        name: 'LoginAdmin',         props: { roleContext: 'Admin' } }
{ path: '/teacher/login',      name: 'LoginTeacher',       props: { roleContext: 'Teacher' } }
{ path: '/student/login',      name: 'StudentLogin',       component: LoginStudent }

// Redirections legacy
{ path: '/login',              redirect: '/' }
{ path: '/guide-enseignant',   redirect: '/korrigo/guide-enseignant' }
{ path: '/guide-eleve',        redirect: '/korrigo/guide-eleve' }

// Routes admin (requiresAuth: true, role: 'Admin')
{ path: '/admin-dashboard',             name: 'AdminDashboard' }
{ path: '/admin/users',                 name: 'UserManagement' }
{ path: '/admin/settings',              name: 'Settings' }
{ path: '/exam/:examId/identification', name: 'IdentificationDesk' }
{ path: '/exam/:examId/staple',         name: 'StapleView' }
{ path: '/exam/:examId/grading-scale',  name: 'MarkingSchemeView' }
{ path: '/exam/:examId/students',       name: 'ExamStudentList' }

// Routes correcteur (requiresAuth: true, role: ['Teacher', 'Admin'])
{ path: '/corrector-dashboard',         name: 'CorrectorDashboard',  role: 'Teacher' }
{ path: '/corrector/import',            name: 'ImportCopies',        role: 'Teacher' }
{ path: '/corrector/desk/:copyId',      name: 'CorrectorDesk',       role: ['Teacher', 'Admin'] }
{ path: '/corrector/my-students',       name: 'MyStudents',          role: ['Teacher', 'Admin'] }
{ path: '/corrector/questionnaire',     name: 'CorrectorQuestionnaire', role: 'Teacher' }
{ path: '/corrector/student/:studentId/bilan', name: 'StudentBilan', role: ['Teacher', 'Admin'] }

// Routes statistiques (partagées Teacher + Admin)
{ path: '/korrigo/stats-bb-maths-2026', name: 'StatsReport',         role: ['Teacher', 'Admin'] }
{ path: '/questionnaire/bilan',          name: 'QuestionnaireBilan',  role: ['Teacher', 'Admin'] }

// Routes élève (requiresAuth: true, role: 'Student')
{ path: '/student-portal',              name: 'StudentPortal' }
{ path: '/student/change-password',     name: 'StudentChangePassword' }

// Catch-all
{ path: '/:pathMatch(.*)*',             redirect: '/' }
```

Les vues lourdes sont chargées en lazy import : `component: () => import('../views/admin/CorrectorDesk.vue')`.

### 4.2 Navigation guards

Le guard `router.beforeEach` assure le contrôle d'accès :

1. **Pages publiques** (`meta.public: true`) : navigation directe, sauf si l'utilisateur est déjà authentifié — redirection vers son dashboard dans ce cas.
2. **Pages protégées** (`meta.requiresAuth: true`) : si `authStore.user` est absent, tentative de `fetchUser()` (appel `/me/`). Si non authentifié, redirection vers `/`.
3. **Contrôle de rôle** : `meta.role` accepte une chaîne ou un tableau. Le rôle `Admin` contourne toutes les restrictions de rôle (`userRole !== 'Admin'` est la condition de blocage).
4. **Anti-boucle** : compteur `redirectCount` plafonné à `MAX_REDIRECTS = 3`.
5. **Stale chunks** : `router.onError` gère les erreurs de chargement de modules (déploiement) en rechargeant la page une fois (`sessionStorage` flag).

### 4.3 Flux de navigation par rôle

```
/  (Home.vue)
├── /admin/login    → AdminDashboard (/admin-dashboard)
│     └── → ImportCopies, IdentificationDesk, StapleView, MarkingSchemeView,
│           UserManagement, Settings, ExamStudentList, QuestionnaireBilan
├── /teacher/login  → CorrectorDashboard (/corrector-dashboard)
│     └── → CorrectorDesk (/corrector/desk/:copyId)  ← interface principale
│           MyStudents, StudentBilan, QuestionnaireView
└── /student/login  → StudentPortal (/student-portal)
      └── → ChangePasswordStudent
```

---

## 5. State management — Pinia

### 5.1 Store Auth (`src/stores/auth.js`)

Ce store gère l'identité de l'utilisateur connecté, tous rôles confondus.

**État réactif :**
```javascript
const user = ref(null)
// Structure : { id, username, email, role, is_superuser, must_change_password, ... }
// role : 'Admin' | 'Teacher' | 'Student'

const lastError = ref('')
const isChecking = ref(false)
```

**Computed :**
```javascript
isAuthenticated     // computed(() => !!user.value)
mustChangePassword  // computed(() => user.value?.must_change_password || false)
```

**Actions exposées :**

| Action | Description |
|--------|-------------|
| `login(username, password)` | POST `/api/login/` puis `fetchUser(false, true)`. Retourne `true/false`. |
| `loginStudent(email, password)` | POST `/api/students/login/` avec email + mot de passe. Propage `must_change_password` depuis la réponse. |
| `logout()` | POST `/api/logout/` ou `/api/students/logout/` selon le rôle. Remet `user` à `null`. |
| `fetchUser(preferStudent, force)` | Tente d'abord GET `/api/me/` (admin/teacher), puis GET `/api/students/me/`. Debounce de 3 s sauf si `force=true`. |
| `clearError()` | Remet `lastError` à vide. |
| `clearMustChangePassword()` | Met `must_change_password = false` après changement réussi. |

**Détail du debounce de `fetchUser` :** pour éviter des appels redondants lors des navigations rapides, la fonction vérifie `(Date.now() - lastCheckedAt) < CHECK_DEBOUNCE_MS` (3 s). Le flag `force=true` contourne ce mécanisme.

**Utilisé par :** navigation guard (router), Login.vue, LoginStudent.vue, CorrectorDesk.vue (vérification rôle admin), tous les composants avec `useAuthStore()`.

### 5.2 Store Exam (`src/stores/examStore.js`)

Ce store gère l'upload d'examens et la récupération des fascicules associés.

**État réactif :**
```javascript
const currentExam = ref(null)   // { id, name, date, ... }
const booklets    = ref([])     // Liste des fascicules de l'examen courant
const isLoading   = ref(false)
const error       = ref(null)
```

**Actions exposées :**

| Action | Description |
|--------|-------------|
| `uploadExam(file)` | POST `/api/exams/upload/` avec `FormData`. Appelle `fetchBooklets()` automatiquement après succès. Utilise `UPLOAD_TIMEOUT` (120 s). |
| `fetchBooklets(examId)` | GET `/api/exams/{id}/booklets/`. Peuple `booklets`. |
| `mergeBooklets(bookletIds)` | POST `/api/exams/{id}/merge/` puis rafraîchit `booklets`. |

**Utilisé par :** ImportCopies.vue, StapleView.vue.

> Note : la gestion des copies, annotations et scores est effectuée directement via `gradingApi.js` dans `CorrectorDesk.vue` sans passer par un store dédié (state local au composant).

---

## 6. Client HTTP — Axios

### 6.1 Instance centrale (`src/services/api.js`)

```javascript
const api = axios.create({
    baseURL: import.meta.env.VITE_API_URL || '/api',
    withCredentials: true,   // Cookie de session Django
    headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
    },
    timeout: 30000,          // 30 s par défaut
})

export const UPLOAD_TIMEOUT = 120000   // 120 s pour les imports PDF
```

### 6.2 Intercepteur requête — CSRF

Pour toute requête (GET ou mutation), le token CSRF est lu depuis le cookie `csrftoken` et injecté dans l'en-tête `X-CSRFToken` :

```javascript
api.interceptors.request.use(config => {
    const csrftoken = getCookie('csrftoken')
    if (csrftoken) {
        config.headers['X-CSRFToken'] = csrftoken
    }
    return config
})
```

### 6.3 Intercepteur réponse — Gestion des erreurs et retry

| Situation | Comportement |
|-----------|-------------|
| HTTP 401 (hors endpoints `/login/` et `/me/`) | Réinitialise `authStore.user`, redirige vers `/` |
| HTTP 403 avec message CSRF | Rechargement de page (une seule fois, flag `__csrfRetried`) |
| Erreur réseau sur endpoint idempotent | Retry exponentiel (max 3 tentatives, délai 1 s × 2^n) |
| HTTP 5xx sur endpoint idempotent | Même comportement que ci-dessus |
| HTTP 408 ou 429 | Retry exponentiel |

**Endpoints idempotents autorisés au retry :**
- `PUT /scores/`
- `POST /remarks/`
- `PATCH /global-appreciation/`
- `PUT /draft/`

### 6.4 Proxy de développement (Vite)

```javascript
// vite.config.js
proxy: {
    '/api':    { target: process.env.VITE_API_TARGET || 'http://127.0.0.1:8000', changeOrigin: true },
    '/media':  { target: apiTarget, changeOrigin: true },
    '/static': { target: apiTarget, changeOrigin: true }
}
```

En production, Nginx route `/api/` → backend Gunicorn directement.

---

## 7. Vues principales

### 7.1 Home.vue — Portail d'accueil

**Route :** `/`

Écran de sélection du rôle : trois cartes cliquables (Admin, Enseignant, Élève) qui redirigent vers la page de connexion correspondante. Si l'utilisateur est déjà authentifié, le guard le redirige vers son dashboard avant même d'afficher cette page.

### 7.2 Login.vue — Connexion Admin/Teacher

**Routes :** `/admin/login` (prop `roleContext: 'Admin'`), `/teacher/login` (prop `roleContext: 'Teacher'`)

- Formulaire `username` + `password`
- Appelle `authStore.login(username, password)`
- Redirige vers `/admin-dashboard` ou `/corrector-dashboard` selon le rôle retourné par `/api/me/`

### 7.3 AdminDashboard.vue — Tableau de bord administrateur

**Route :** `/admin-dashboard` (Auth: Admin)

**Responsabilités :**
- Liste tous les examens avec statistiques (nombre de copies READY, IN_PROGRESS, FINALIZED)
- Actions par examen : upload copies, dispatch aux correcteurs, publication résultats, rapport de jury, statistiques
- Gestion des types d'examen (`ExamType`)
- Accès à : ImportCopies, IdentificationDesk, StapleView, MarkingSchemeView, UserManagement

**Appels API :**
- `GET /api/exams/`
- `POST /api/exams/{id}/dispatch/`
- `POST /api/exams/{id}/release-results/`
- `GET /api/exams/{id}/stats/`

### 7.4 CorrectorDesk.vue — Interface de correction

**Route :** `/corrector/desk/:copyId` (Auth: Teacher | Admin)

C'est la vue centrale de la plateforme. Son architecture interne est la plus complexe.

**Panneau gauche — Visualisation de la copie :**
- Affichage de la page courante sous forme d'image PNG (servie depuis `/media/`)
- Zoom : `scale` réf, modifié par molette (`wheel`) ou boutons +/−
- Navigation de page : boutons précédent/suivant, indicateur `page X / total`
- Préchargement des pages adjacentes (`preloadAdjacentPages`) pour navigation fluide
- Superposition `CanvasLayer.vue` pour le dessin d'annotations

**Panneau droit — Notation et outils :**
- Sélecteur de mode d'annotation (groupe `stamp` : VRAI/FAUX, groupe `type` : COMMENTAIRE/SURLIGNAGE/ERREUR/BONUS)
- Structure hiérarchique des exercices (accordéon, un seul exercice ouvert à la fois)
- Saisie de score par question + calcul du total automatique
- Remarques par question (debounce 800 ms → POST `/remarks/`)
- Appréciation globale (debounce → PATCH `/global-appreciation/`)

**Flux d'annotation :**
1. L'utilisateur sélectionne un type d'annotation dans la sidebar
2. `mousedown` sur le canvas → `startDrawing()`
3. `mousemove` → `draw()` — affichage du rectangle rouge en cours
4. `mouseup` → `stopDrawing()` — normalisation des coordonnées [0, 1] par division par `props.width/height`
5. Émission `annotation-created` avec `{ x, y, w, h }` normalisés
6. Affichage d'un overlay éditeur pour saisir le contenu textuel
7. POST vers `/api/grading/copies/{copyId}/annotations/`

**Anonymisation :**
- Les pages d'en-tête (pages 1, 5, 9, 13... selon `pages_per_booklet`) et la dernière page (annexe) contiennent l'identité de l'élève
- `isHeaderPage` computed masque le nom à l'affichage pour les correcteurs non-admin
- L'admin peut basculer l'affichage via le toggle `showIdentity`

**Autosave :**
- Scores : debounce → PUT `/api/grading/copies/{copyId}/scores/`
- Remarques par question : debounce individuel par question (Map de timers)
- Appréciation globale : debounce → PATCH `/api/grading/copies/{copyId}/global-appreciation/`
- Draft local : `sessionStorage` avec `clientId` UUID par copie (restauration possible après crash)
- Indicateurs de synchronisation : `hasPendingChanges`, `consecutiveFailures`, `syncStatusLevel` (ok/warning/critical/offline)

**Statut de la copie :**
- `READY` : correction possible, pas encore commencée
- `IN_PROGRESS` : au moins une annotation posée — la copie passe automatiquement à ce statut lors du premier POST annotation
- `FINALIZED` : correction terminée — lecture seule sauf pour l'admin et le correcteur assigné

**Finalisation :**
- Modal de confirmation → POST `/api/grading/copies/{copyId}/finalize/`
- Après succès : navigation vers `/corrector-dashboard`

### 7.5 CorrectorDashboard.vue — Tableau de bord correcteur

**Route :** `/corrector-dashboard` (Auth: Teacher)

- Liste les copies assignées au correcteur connecté
- Filtres rapides par statut : READY, IN_PROGRESS, FINALIZED
- Clic sur une copie → navigation vers `CorrectorDesk`

### 7.6 LoginStudent.vue — Connexion élève

**Route :** `/student/login`

- Formulaire : email + mot de passe
- Appelle `authStore.loginStudent(email, password)` → POST `/api/students/login/`
- Si `must_change_password: true` dans la réponse : redirection vers `/student/change-password`
- Sinon : redirection vers `/student-portal`

### 7.7 ResultView.vue — Espace élève

**Route :** `/student-portal` (Auth: Student)

- Affiche les copies finalisées de l'élève connecté
- Visualisation des pages corrigées avec annotations rendues
- Score total, appréciation globale
- Bilan LLM si généré

### 7.8 ChangePasswordStudent.vue — Changement de mot de passe

**Route :** `/student/change-password` (Auth: Student)

- Formulaire : mot de passe actuel + nouveau mot de passe (× 2)
- POST `/api/students/change-password/`
- Interdit la réutilisation du mot de passe par défaut (`passe123` ou date de naissance au format `JJMMAAAA`)
- Appelle `authStore.clearMustChangePassword()` après succès

---

## 8. Composants partagés

### 8.1 CanvasLayer.vue

**Rôle :** Superposition canvas HTML5 sur l'image de la page — capture le dessin de l'utilisateur et affiche les annotations existantes.

**Props :**
```javascript
width:               Number   // Largeur CSS de l'image (px)
height:              Number   // Hauteur CSS de l'image (px)
scale:               Number   // Facteur de zoom courant (pour épaisseur des traits)
initialAnnotations:  Array    // Annotations existantes à afficher
enabled:             Boolean  // Si false : lecture seule
```

**Émissions :** `annotation-created` avec `{ x, y, w, h }` en coordonnées normalisées [0, 1].

**Rendu des annotations :**
- Chaque annotation est un rectangle délimité par `(x * width, y * height, w * width, h * height)` en pixels CSS
- Couleur selon le type : COMMENTAIRE (bleu), SURLIGNAGE (orange/jaune), ERREUR (rouge), BONUS (vert), VRAI (vert), FAUX (rouge)
- Tampons VRAI/FAUX : symboles ✓ et ✗ centrés dans le rectangle
- BONUS : étoile ⭐ centrée
- Texte du contenu affiché avec word-wrap dans le rectangle
- DPR (Device Pixel Ratio) appliqué au canvas pour rendu net sur écrans Retina

**Normalisation des coordonnées (ADR-002) :**
```javascript
// Dans stopDrawing()
const normalized = {
    x: x / props.width,
    y: y / props.height,
    w: w / props.width,
    h: h / props.height
}
emit('annotation-created', normalized)
```

### 8.2 GradingSidebar.vue

**Rôle :** Panneau latéral affichant la structure hiérarchique du barème et permettant la saisie des scores.

**Props :**
```javascript
structure:  Array    // Arbre du barème : [{ id, label, points, children: [...] }]
scores:     Object   // { 'question_id': score_value, ... }
```

**Émissions :** `update-score(questionId, value)`

**Calcul du total :** récursif via `calculateNodeTotal(node)` — somme les feuilles depuis la racine.

### 8.3 PDFViewer.vue

Composant d'affichage d'image avec zoom et navigation de page. Dans la version actuelle, les pages de la copie sont des images PNG (pas des PDF bruts côté frontend). PDF.js (`pdfjs-dist`) est inclus dans les dépendances pour les cas où un PDF source serait rendu côté client.

### 8.4 CommentBank.vue

Bibliothèque de commentaires prédéfinis. Filtrable par catégorie. Un clic insère le template dans la saisie d'annotation active.

### 8.5 GradingScaleBuilder.vue

Outil admin pour définir la structure de notation d'un examen (exercices + sous-questions + barèmes). Sauvegarde dans `exam.grading_structure` (JSON).

### 8.6 ExamUploadModal.vue

Modal d'import de copies :
- Sélecteur de fichier PDF
- Sélection de l'examen cible
- Choix du mode : `BATCH_A3` (impression recto-verso A3 plié) ou `INDIVIDUAL_A4`
- Barre de progression pendant l'upload

### 8.7 JuryReportsModal.vue

Modal de rapport de jury :
- Téléchargement du rapport PDF final
- Statistiques : min, max, moyenne, médiane, distribution des notes (histogramme)

### 8.8 TrueFalseTool.vue

Sélecteur de tampons VRAI (✓ vert) / FAUX (✗ rouge). Utilisé dans CorrectorDesk pour le mode `quickStamp`.

### 8.9 AnnotationSuggestionsPanel.vue

Panneau de suggestions d'annotations alimenté par l'historique des corrections. Filtrable par exercice/question.

---

## 9. Tests

### 9.1 Tests unitaires — Vitest

```bash
npm run test:unit        # Vitest, fichiers tags "unit"
npm run test:integration # Vitest, fichiers tags "integration"
npm run test             # Vitest (tous)
npm run test:coverage    # Avec rapport de couverture
```

**Configuration :** `vitest.config.js` (ou section dans `vite.config.js`), environnement `jsdom`, `@vue/test-utils` pour le montage de composants, `msw` pour mocker les appels HTTP.

### 9.2 Tests E2E — Playwright

```bash
npm run test:e2e         # Playwright headless
npm run test:e2e:headed  # Avec navigateur visible
npm run test:e2e:ui      # Interface graphique Playwright
npm run test:workflow    # Config playwright.workflow.config.ts
```

**Configuration (`playwright.config.ts`) :**
```typescript
{
    testDir: './e2e',
    fullyParallel: false,
    workers: 1,
    use: {
        baseURL: process.env.E2E_BASE_URL || 'http://localhost:8088',
        trace: 'on-first-retry',
    },
    projects: [{ name: 'chromium', use: devices['Desktop Chrome'] }]
}
```

**Global setup (`e2e/global-setup.ts`) :** vérifie que le backend est accessible via `GET /api/health/` avant de lancer les tests.

**Contrat E2E (gate zéro-tolérance, 3 passages consécutifs requis) :**

| Test | Endpoint | Assertion |
|------|----------|-----------|
| Login admin | `POST /api/auth/login/` | HTTP 200 + session cookie |
| Créer annotation | `POST /api/grading/copies/{id}/annotations/` | HTTP 201 |
| Lire annotations | `GET /api/grading/copies/{id}/annotations/` | HTTP 200, annotation présente |
| Login élève | `POST /api/students/login/` | HTTP 200, `role: Student` |
| Consulter résultats | `GET /api/students/me/copies/` | HTTP 200, liste non vide |

### 9.3 Commandes de test complètes

```bash
npm run test:all     # unit + integration + e2e
npm run typecheck    # vue-tsc --noEmit
npm run lint         # ESLint
```

---

## 10. Build et déploiement

### 10.1 Développement local

```bash
npm run dev
# Vite dev server : http://localhost:5173
# HMR activé
# Proxy /api → http://127.0.0.1:8000 (ou VITE_API_TARGET)
```

### 10.2 Build production

```bash
npm run build
# Output : frontend/dist/
# Fichiers minifiés, tree-shaken, hash dans les noms de fichiers
# dist/index.html : point d'entrée servi par Nginx
```

### 10.3 Preview du build

```bash
npm run preview
# Serve dist/ localement pour vérification avant déploiement
```

### 10.4 Nginx — Serving en production

Nginx sert les fichiers statiques depuis `dist/` et fait proxy vers le backend pour `/api/` et `/media/`. La règle `try_files $uri $uri/ /index.html` assure le fonctionnement de la navigation SPA (retour à `index.html` pour toutes les routes non-fichiers).

---

## 11. Variables d'environnement

Fichier `.env` ou `.env.local` à la racine de `frontend/` :

```bash
VITE_API_URL=/api              # Préfixe URL API backend (proxied en dev, absolu en prod)
VITE_API_TARGET=http://127.0.0.1:8000   # Cible du proxy Vite en développement
VITE_APP_TITLE=Korrigo PMF     # Titre de l'application (meta og:title)
```

En production, `VITE_API_URL` est `/api` (Nginx route vers le backend). Aucune variable sensible ne doit figurer dans les variables `VITE_*` : elles sont inlinées dans le bundle JavaScript et visibles publiquement.

---

## Références

- [Vue.js 3 — Composition API](https://vuejs.org/guide/extras/composition-api-faq)
- [Pinia](https://pinia.vuejs.org/)
- [Vue Router 4](https://router.vuejs.org/)
- [Playwright](https://playwright.dev/)
- [Vitest](https://vitest.dev/)
- [ADR-002 — Normalisation coordonnées annotations](../decisions/ADR-002-pdf-coordinate-normalization.md)
- [ADR-001 — Authentification élève](../decisions/ADR-001-student-authentication-model.md)
- [Référence API Backend](API_REFERENCE.md)
- [Architecture Backend](ARCHITECTURE.md)

---

**Dernière mise à jour :** 28 mars 2026
**Auteur :** Alaeddine BEN RHOUMA
**Licence :** Propriétaire — AEFE / Éducation Nationale
