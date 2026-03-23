# Architecture Frontend Korrigo

> **Version**: 2.0
> **Date**: 23 Mars 2026
> **Public**: Développeurs Frontend, Architectes

Ce document décrit l'architecture complète du frontend de la plateforme Korrigo, une application Vue.js 3 moderne avec TypeScript.

---

## 📋 Table des Matières

1. [Vue d'Ensemble](#vue-densemble)
2. [Stack Technique](#stack-technique)
3. [Structure du Projet](#structure-du-projet)
4. [Routing et Navigation](#routing-et-navigation)
5. [State Management](#state-management)
6. [Services API](#services-api)
7. [Composants Principaux](#composants-principaux)
8. [Tests E2E](#tests-e2e)
9. [Build et Déploiement](#build-et-déploiement)

---

## Vue d'Ensemble

### Responsabilités

Le frontend Korrigo est une **Single Page Application (SPA)** qui gère:

- **Authentification** multi-rôles (Admin, Teacher, Student)
- **Interfaces spécifiques** par rôle avec navigation conditionnelle
- **Visualisation PDF** avec annotations vectorielles
- **Gestion d'état** centralisée (Pinia)
- **Communication API** REST avec le backend Django

### Principes de Design

- **Composition API**: Vue 3 avec `<script setup>` pour meilleure réutilisabilité
- **TypeScript**: Typage statique pour robustesse
- **Reactive State**: Pinia pour state management prévisible
- **Role-Based Access**: Guards de navigation basés sur les rôles
- **Responsive**: Interface adaptative (desktop prioritaire)

---

## Stack Technique

| Composant | Version | Rôle |
|-----------|---------|------|
| **Vue.js** | 3.4.15 | Framework UI (Composition API) |
| **TypeScript** | 5.9.3 | Typage statique |
| **Pinia** | 2.1.7 | State management |
| **Vue Router** | 4.2.5 | Routing SPA |
| **Axios** | 1.13.2 | Client HTTP |
| **PDF.js** | 4.0.0 | Visualisation PDF |
| **Vite** | 5.1.0 | Build tool, dev server |
| **Playwright** | 1.57.0 | Tests E2E |
| **ESLint** | 9.39.2 | Linting |

---

## Structure du Projet

```
frontend/
├── src/
│   ├── main.js                 # Point d'entrée application
│   ├── App.vue                 # Composant racine
│   │
│   ├── router/
│   │   └── index.js            # Configuration routing
│   │
│   ├── stores/
│   │   ├── auth.js             # Store authentification
│   │   └── examStore.js        # Store examens/copies
│   │
│   ├── services/
│   │   ├── api.js              # Client Axios configuré
│   │   └── pdfService.js       # Service manipulation PDF
│   │
│   ├── views/                  # Pages principales
│   │   ├── Home.vue            # Landing page (sélection rôle)
│   │   ├── Login.vue           # Login Admin/Teacher
│   │   ├── AdminDashboard.vue  # Tableau de bord Admin
│   │   ├── CorrectorDashboard.vue  # Tableau de bord Teacher
│   │   ├── Settings.vue        # Paramètres
│   │   │
│   │   ├── admin/              # Vues Admin
│   │   │   ├── ImportCopies.vue
│   │   │   ├── StapleView.vue
│   │   │   ├── IdentificationDesk.vue
│   │   │   ├── CorrectorDesk.vue
│   │   │   ├── MarkingSchemeView.vue
│   │   │   └── UserManagement.vue
│   │   │
│   │   └── student/            # Vues Student
│   │       ├── LoginStudent.vue
│   │       └── ResultView.vue
│   │
│   ├── components/             # Composants réutilisables
│   │   ├── PDFViewer.vue
│   │   ├── AnnotationLayer.vue
│   │   ├── GradingScaleBuilder.vue
│   │   ├── CopyCard.vue
│   │   ├── ExamCard.vue
│   │   ├── TrueFalseTool.vue     # V2 — Tampon V/X (VRAI/FAUX)
│   │   ├── ProgressDashboard.vue  # V2 — Indicateurs de progression
│   │   └── Navbar.vue
│   │
│   ├── utils/
│   │   └── helpers.js          # Fonctions utilitaires
│   │
│   └── types/
│       └── index.ts            # Types TypeScript
│
├── tests/
│   └── e2e/                    # Tests Playwright
│       ├── global-setup.ts
│       ├── auth_flow.spec.ts
│       ├── student_flow.spec.ts
│       └── dispatch_flow.spec.ts
│
├── public/                     # Assets statiques
├── index.html                  # Template HTML
├── vite.config.js              # Configuration Vite
├── playwright.config.ts        # Configuration Playwright
├── tsconfig.json               # Configuration TypeScript
└── package.json                # Dépendances npm
```

---

## Routing et Navigation

### Configuration Routes

Le routing est géré par **Vue Router 4** avec navigation basée sur les rôles.

```javascript
// src/router/index.js
const routes = [
  // Landing page
  { path: '/', name: 'Home', component: Home },
  
  // Authentification
  { path: '/admin/login', name: 'LoginAdmin', component: Login, props: { roleContext: 'Admin' } },
  { path: '/teacher/login', name: 'LoginTeacher', component: Login, props: { roleContext: 'Teacher' } },
  { path: '/student/login', name: 'StudentLogin', component: LoginStudent },
  
  // Admin routes
  { 
    path: '/admin-dashboard', 
    name: 'AdminDashboard', 
    component: AdminDashboard,
    meta: { requiresAuth: true, role: 'Admin' }
  },
  { 
    path: '/admin/users', 
    name: 'UserManagement', 
    component: UserManagement,
    meta: { requiresAuth: true, role: 'Admin' }
  },
  { 
    path: '/exam/:examId/staple', 
    name: 'StapleView', 
    component: StapleView,
    meta: { requiresAuth: true, role: 'Admin' }
  },
  { 
    path: '/exam/:examId/identification', 
    name: 'IdentificationDesk', 
    component: IdentificationDesk,
    meta: { requiresAuth: true, role: 'Admin' }
  },
  { 
    path: '/exam/:examId/grading-scale', 
    name: 'MarkingSchemeView', 
    component: MarkingSchemeView,
    meta: { requiresAuth: true, role: 'Admin' }
  },
  
  // Teacher routes
  { 
    path: '/corrector-dashboard', 
    name: 'CorrectorDashboard', 
    component: CorrectorDashboard,
    meta: { requiresAuth: true, role: 'Teacher' }
  },
  { 
    path: '/corrector/desk/:copyId', 
    name: 'CorrectorDesk', 
    component: CorrectorDesk,
    meta: { requiresAuth: true, role: 'Teacher' }
  },
  
  // Student routes
  { 
    path: '/student-portal', 
    name: 'StudentPortal', 
    component: ResultView,
    meta: { requiresAuth: true, role: 'Student' }
  },
  
  // 404
  { path: '/:pathMatch(.*)*', redirect: '/' }
]
```

### Navigation Guards

```javascript
router.beforeEach(async (to, from, next) => {
  const authStore = useAuthStore()
  
  // 1. Fetch user if not already loaded
  if (!authStore.user && !authStore.isChecking) {
    const preferStudent = to.path.startsWith('/student')
    await authStore.fetchUser(preferStudent)
  }
  
  const isAuthenticated = !!authStore.user
  const userRole = authStore.user?.role
  
  // 2. Protected routes
  if (to.meta.requiresAuth) {
    if (!isAuthenticated) {
      return next('/') // Redirect to landing page
    }
    
    // Role check
    const requiredRole = to.meta.role
    if (requiredRole) {
      const hasAccess = 
        userRole === requiredRole || 
        (userRole === 'Admin' && requiredRole === 'Teacher') // Admin can supervise
      
      if (!hasAccess) {
        // Redirect to correct dashboard
        if (userRole === 'Admin') return next('/admin-dashboard')
        if (userRole === 'Teacher') return next('/corrector-dashboard')
        if (userRole === 'Student') return next('/student-portal')
        return next('/')
      }
    }
  }
  
  // 3. Redirect authenticated users away from login pages
  const isLoginPage = ['LoginAdmin', 'LoginTeacher', 'StudentLogin', 'Home'].includes(to.name)
  if (isLoginPage && isAuthenticated) {
    if (userRole === 'Admin') return next('/admin-dashboard')
    if (userRole === 'Teacher') return next('/corrector-dashboard')
    if (userRole === 'Student') return next('/student-portal')
  }
  
  next()
})
```

### Flux de Navigation

```mermaid
graph TD
    Start[Utilisateur arrive sur /] --> Home[Home.vue]
    Home --> ChooseRole{Choisir Rôle}
    
    ChooseRole -->|Admin| AdminLogin[/admin/login]
    ChooseRole -->|Teacher| TeacherLogin[/teacher/login]
    ChooseRole -->|Student| StudentLogin[/student/login]
    
    AdminLogin --> AuthAdmin{Authentification}
    TeacherLogin --> AuthTeacher{Authentification}
    StudentLogin --> AuthStudent{Authentification}
    
    AuthAdmin -->|Success| AdminDash[AdminDashboard]
    AuthTeacher -->|Success| TeacherDash[CorrectorDashboard]
    AuthStudent -->|Success| StudentPortal[StudentPortal]
    
    AuthAdmin -->|Fail| AdminLogin
    AuthTeacher -->|Fail| TeacherLogin
    AuthStudent -->|Fail| StudentLogin
    
    AdminDash --> AdminActions[Gestion Examens<br/>Import Copies<br/>Identification<br/>Dispatch<br/>Gestion Utilisateurs]
    TeacherDash --> TeacherActions[Corriger Copies<br/>Consulter Assignations]
    StudentPortal --> StudentActions[Consulter Copies Corrigées]
```

---

## State Management

### Pinia Stores

Korrigo utilise **Pinia** pour la gestion d'état centralisée.

#### 1. Auth Store (`stores/auth.js`)

**Responsabilités**:
- Gestion de l'authentification
- Stockage des informations utilisateur
- Gestion des sessions

**État**:
```javascript
{
  user: null,          // { id, username, email, role, ... }
  isChecking: false,   // Loading state
  error: null          // Error message
}
```

**Actions**:
```javascript
// Récupérer l'utilisateur connecté
async fetchUser(preferStudent = false)

// Login Admin/Teacher
async login(username, password)

// Login Student
async loginStudent(lastName, dateOfBirth)

// Logout
async logout()

// Change password
async changePassword(oldPassword, newPassword)
```

**Getters**:
```javascript
isAuthenticated()  // Boolean
isAdmin()          // Boolean
isTeacher()        // Boolean
isStudent()        // Boolean
```

#### 2. Exam Store (`stores/examStore.js`)

**Responsabilités**:
- Gestion des examens
- Gestion des copies
- Cache des données

**État**:
```javascript
{
  exams: [],           // Liste examens
  currentExam: null,   // Examen sélectionné
  copies: [],          // Liste copies
  currentCopy: null,   // Copie en cours de correction
  loading: false,
  error: null
}
```

**Actions**:
```javascript
// Examens
async fetchExams()
async createExam(examData)
async updateExam(examId, examData)
async deleteExam(examId)

// Copies
async fetchCopies(examId)
async fetchCopy(copyId)
async updateCopy(copyId, copyData)

// Grading
async lockCopy(copyId)
async unlockCopy(copyId, lockToken)
async finalizeCopy(copyId, lockToken)
```

---

## Services API

### Client Axios Configuré

```javascript
// src/services/api.js
import axios from 'axios'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8088',
  withCredentials: true, // Important pour les cookies de session
  headers: {
    'Content-Type': 'application/json',
  },
})

// Intercepteur pour ajouter le token CSRF
api.interceptors.request.use(async (config) => {
  if (['post', 'put', 'patch', 'delete'].includes(config.method)) {
    const csrfToken = getCsrfToken() // Récupère depuis cookie
    if (csrfToken) {
      config.headers['X-CSRFToken'] = csrfToken
    }
  }
  return config
})

// Intercepteur pour gérer les erreurs
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Rediriger vers login
      router.push('/')
    }
    return Promise.reject(error)
  }
)

export default api
```

### Méthodes API par Domaine

```javascript
// Authentification
export const authAPI = {
  login: (username, password) => api.post('/api/login/', { username, password }),
  logout: () => api.post('/api/logout/'),
  me: () => api.get('/api/me/'),
  csrf: () => api.get('/api/csrf/'),
}

// Examens
export const examsAPI = {
  list: () => api.get('/api/exams/'),
  create: (data) => api.post('/api/exams/', data),
  get: (id) => api.get(`/api/exams/${id}/`),
  update: (id, data) => api.patch(`/api/exams/${id}/`, data),
  delete: (id) => api.delete(`/api/exams/${id}/`),
  uploadPDF: (id, file) => {
    const formData = new FormData()
    formData.append('pdf_source', file)
    return api.post(`/api/exams/${id}/upload/`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
  },
}

// Copies
export const copiesAPI = {
  list: (params) => api.get('/api/copies/', { params }),
  get: (id) => api.get(`/api/copies/${id}/`),
  update: (id, data) => api.patch(`/api/copies/${id}/`, data),
  validate: (id) => api.post(`/api/copies/${id}/validate/`),
}

// Grading
export const gradingAPI = {
  lock: (copyId) => api.post(`/api/grading/copies/${copyId}/lock/`),
  unlock: (copyId, lockToken) => api.post(`/api/grading/copies/${copyId}/unlock/`, { lock_token: lockToken }),
  finalize: (copyId, lockToken) => api.post(`/api/grading/copies/${copyId}/finalize/`, { lock_token: lockToken }),
  
  // Annotations
  listAnnotations: (copyId) => api.get(`/api/grading/copies/${copyId}/annotations/`),
  createAnnotation: (data) => api.post('/api/grading/annotations/', data),
  updateAnnotation: (id, data) => api.patch(`/api/grading/annotations/${id}/`, data),
  deleteAnnotation: (id) => api.delete(`/api/grading/annotations/${id}/`),
  
  // Scores
  saveScores: (copyId, scores) => api.post(`/api/grading/copies/${copyId}/scores/`, { scores }),
}

// Students
export const studentsAPI = {
  list: () => api.get('/api/students/'),
  myCopies: () => api.get('/api/students/me/copies/'),
}
```

---

## Composants Principaux

### 1. Home.vue - Landing Page

**Rôle**: Page d'accueil avec sélection du rôle

**Fonctionnalités**:
- 3 boutons: Admin, Enseignant, Élève
- Redirection automatique si déjà authentifié
- Design moderne et accueillant

### 2. AdminDashboard.vue - Tableau de Bord Admin

**Rôle**: Interface principale pour les administrateurs

**Fonctionnalités**:
- Liste des examens avec actions (Éditer, Supprimer, Agrafeuse, Identification, Barème)
- Création nouvel examen
- Import copies
- Dispatch copies aux correcteurs
- Export Pronote
- Gestion utilisateurs
- Statistiques

### 3. CorrectorDesk.vue - Interface de Correction

**Rôle**: Interface de correction pour enseignants

**Fonctionnalités**:
- Visualisation PDF (PDF.js)
- Annotations vectorielles (dessin à la souris)
- Barre latérale avec barème
- Notation par question
- Appréciation globale
- Autosave (draft)
- Lock/Unlock automatique
- Finalisation
- **V2** — Mode split view : copie de l'élève et corrigé officiel côte à côte
- **V2** — Quick stamp mode : boutons V (vert) et X (rouge) pour tampon rapide VRAI/FAUX
- **V2** — Force unlock : déverrouillage forcé d'une copie bloquée
- **V2** — Reopen : réouverture d'une copie finalisée (GRADED -> READY)

**Architecture**:
```vue
<template>
  <div class="corrector-desk">
    <!-- Header avec infos copie -->
    <header>
      <h1>Copie {{ copy.anonymous_id }}</h1>
      <button @click="finalize">Finaliser</button>
    </header>
    
    <!-- Zone principale -->
    <div class="main-area">
      <!-- PDF Viewer + Annotations -->
      <div class="pdf-container">
        <PDFViewer :pdf-url="copy.pdf_url" @page-change="onPageChange" />
        <AnnotationLayer 
          :annotations="annotations" 
          :current-page="currentPage"
          @add-annotation="addAnnotation"
          @update-annotation="updateAnnotation"
          @delete-annotation="deleteAnnotation"
        />
      </div>
      
      <!-- Sidebar avec barème -->
      <aside class="grading-sidebar">
        <GradingScale 
          :structure="exam.grading_structure"
          :scores="scores"
          @update-score="updateScore"
        />
        <textarea v-model="globalAppreciation" placeholder="Appréciation globale"></textarea>
      </aside>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue'
import { useRoute } from 'vue-router'
import { gradingAPI } from '@/services/api'

const route = useRoute()
const copyId = route.params.copyId

const copy = ref(null)
const annotations = ref([])
const scores = ref({})
const globalAppreciation = ref('')
const lockToken = ref(null)
const currentPage = ref(0)

// Lock copy on mount
onMounted(async () => {
  const { data } = await gradingAPI.lock(copyId)
  lockToken.value = data.lock_token
  
  // Fetch copy data
  // Fetch annotations
  // Setup autosave interval
})

// Unlock copy on unmount
onBeforeUnmount(async () => {
  if (lockToken.value) {
    await gradingAPI.unlock(copyId, lockToken.value)
  }
})

// Methods
const addAnnotation = async (annotationData) => {
  await gradingAPI.createAnnotation({
    ...annotationData,
    copy: copyId,
    lock_token: lockToken.value
  })
}

const finalize = async () => {
  await gradingAPI.finalize(copyId, lockToken.value)
  router.push('/corrector-dashboard')
}
</script>
```

### 4. StapleView.vue - Agrafeuse (Staging)

**Rôle**: Validation des fascicules détectés

**Fonctionnalités**:
- Affichage des fascicules détectés
- Prévisualisation images
- Fusion de fascicules
- Validation (STAGING → READY)

### 5. IdentificationDesk.vue - Identification

**Rôle**: Association copies ↔ élèves

**Fonctionnalités**:
- Liste copies non identifiées
- Affichage nom détecté par OCR
- Recherche élève
- Association manuelle
- Validation

---

## Tests E2E

### Configuration Playwright

```typescript
// playwright.config.ts
export default defineConfig({
  testDir: './tests/e2e',
  globalSetup: './tests/e2e/global-setup.ts',
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: 1,
  reporter: process.env.CI ? 'html' : 'list',
  use: {
    baseURL: process.env.E2E_BASE_URL || 'http://localhost:8088',
    trace: 'on-first-retry',
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
})
```

### Global Setup

```typescript
// tests/e2e/global-setup.ts
export default async function globalSetup() {
  console.log('==> E2E Global Setup: Validating environment...')
  
  // Verify E2E mode
  if (process.env.E2E_TEST_MODE !== 'true') {
    console.warn('⚠️  E2E_TEST_MODE is not set to "true"')
    console.warn('⚠️  Run tests via: bash tools/e2e.sh')
  }
  
  // Health check
  try {
    const response = await fetch('http://localhost:8088/api/health/')
    if (response.ok) {
      console.log('  ✓ Backend health check passed')
    } else {
      console.warn(`  ⚠️  Backend returned status ${response.status}`)
    }
  } catch (error) {
    console.warn('  ⚠️  Backend health check failed')
  }
  
  console.log('  ✓ Environment validation complete')
}
```

### Tests par Workflow

#### auth_flow.spec.ts

```typescript
test('Admin login flow', async ({ page }) => {
  await page.goto('/')
  await page.click('text=Admin')
  await page.fill('input[name="username"]', 'admin')
  await page.fill('input[name="password"]', 'admin123')
  await page.click('button[type="submit"]')
  await expect(page).toHaveURL('/admin-dashboard')
})
```

#### student_flow.spec.ts

```typescript
test('Student can view graded copy', async ({ page }) => {
  await page.goto('/student/login')
  await page.fill('input[name="lastName"]', 'DUPONT')
  await page.fill('input[name="dateOfBirth"]', '2005-03-15')
  await page.click('button[type="submit"]')
  await expect(page).toHaveURL('/student-portal')
  await expect(page.locator('.copy-card')).toBeVisible()
})
```

---

## Build et Déploiement

### Développement

```bash
npm run dev
# Vite dev server: http://localhost:5173
# Hot reload activé
```

### Build Production

```bash
npm run build
# Output: dist/
# Fichiers optimisés, minifiés, tree-shaken
```

### Preview Production Build

```bash
npm run preview
# Serveur local pour tester le build de production
```

### Linting

```bash
npm run lint
# ESLint + TypeScript checks
```

### Type Checking

```bash
npm run typecheck
# Vue-tsc sans émission de fichiers
```

---

## Références

- [Vue.js 3 Documentation](https://vuejs.org/)
- [Pinia Documentation](https://pinia.vuejs.org/)
- [Vue Router Documentation](https://router.vuejs.org/)
- [Playwright Documentation](https://playwright.dev/)
- [API Reference](API_REFERENCE.md)
- [Architecture Backend](ARCHITECTURE.md)

---

**Dernière mise à jour**: 23 mars 2026  
**Auteur**: Alaeddine BEN RHOUMA  
**Licence**: Propriétaire - AEFE/Éducation Nationale
