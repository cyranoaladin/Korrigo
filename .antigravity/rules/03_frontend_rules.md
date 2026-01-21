# Règles Frontend - Vue.js - Viatique

## Statut : OBLIGATOIRE

Ces règles définissent l'architecture frontend Vue.js et les pratiques obligatoires.

---

## 1. Architecture Vue.js

### 1.1 Structure du Projet

**Structure Obligatoire** :
```
frontend/
├── src/
│   ├── main.js              # Entry point
│   ├── App.vue              # Root component
│   ├── router/              # Vue Router
│   │   └── index.js
│   ├── stores/              # Pinia stores
│   │   ├── authStore.js
│   │   ├── examStore.js
│   │   └── correctionStore.js
│   ├── views/               # Pages/Views
│   │   ├── Dashboard.vue
│   │   ├── CorrectorDesk.vue
│   │   ├── ExamEditor.vue
│   │   └── StudentAccess.vue
│   ├── components/          # Composants réutilisables
│   │   ├── PDFViewer.vue
│   │   ├── CanvasLayer.vue
│   │   └── GradingSidebar.vue
│   ├── composables/         # Composition API utilities
│   │   ├── useAnnotations.js
│   │   ├── usePDF.js
│   │   └── useAuth.js
│   ├── services/            # API calls
│   │   ├── api.js           # Axios instance
│   │   ├── examService.js
│   │   └── copyService.js
│   └── utils/               # Utilitaires
│       ├── pdfUtils.js
│       └── canvasUtils.js
├── public/
└── package.json
```

**Règles** :
- Séparation claire views / components / composables
- Services pour toutes les API calls
- Stores Pinia pour état global
- Pas de logique métier dans les composants

---

## 2. Composants Vue

### 2.1 Structure de Composant

**OBLIGATOIRE** :
```vue
<!-- ✅ Bon exemple -->
<template>
  <div class="copy-viewer">
    <PDFViewer :pdf-url="pdfUrl" @page-change="handlePageChange" />
    <CanvasLayer
      v-if="isEditing"
      :annotations="currentAnnotations"
      @annotation-added="handleAnnotationAdded"
    />
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useCopyStore } from '@/stores/copyStore'
import { useAnnotations } from '@/composables/useAnnotations'
import PDFViewer from '@/components/PDFViewer.vue'
import CanvasLayer from '@/components/CanvasLayer.vue'

// Props
const props = defineProps({
  copyId: {
    type: String,
    required: true
  },
  isEditing: {
    type: Boolean,
    default: false
  }
})

// Emits
const emit = defineEmits(['annotationSaved', 'error'])

// Store
const copyStore = useCopyStore()

// Composables
const { annotations, addAnnotation, saveAnnotations } = useAnnotations(props.copyId)

// State
const pdfUrl = ref(null)
const currentPage = ref(1)

// Computed
const currentAnnotations = computed(() => {
  return annotations.value.filter(a => a.page_number === currentPage.value)
})

// Methods
const handlePageChange = (page) => {
  currentPage.value = page
}

const handleAnnotationAdded = async (annotation) => {
  try {
    await addAnnotation(annotation)
    emit('annotationSaved')
  } catch (error) {
    emit('error', error)
  }
}

// Lifecycle
onMounted(async () => {
  pdfUrl.value = await copyStore.fetchCopyPdfUrl(props.copyId)
})
</script>

<style scoped>
.copy-viewer {
  display: flex;
  gap: 1rem;
  height: 100vh;
}
</style>
```

**Règles** :
- Composition API (`<script setup>`) obligatoire pour nouveaux composants
- Props typées avec validation
- Emits déclarés explicitement
- État réactif via `ref`/`reactive`
- Computed pour valeurs dérivées
- Lifecycle hooks explicites
- Styles scoped

**INTERDIT** :
```vue
<!-- ❌ Mauvais exemple -->
<script>
export default {
  data() {  // Options API déprécié pour nouveaux composants
    return { ... }
  },
  methods: {
    async handleClick() {
      // Logique métier complexe dans composant ❌
      const response = await fetch('/api/copies/...')
      const data = await response.json()
      // Transformation complexe...
    }
  }
}
</script>
```

### 2.2 Props et Events

**OBLIGATOIRE** :
```javascript
// ✅ Props bien typées
const props = defineProps({
  copyId: {
    type: String,
    required: true,
    validator: (value) => /^[0-9a-f-]{36}$/.test(value)  // UUID
  },
  status: {
    type: String,
    default: 'READY',
    validator: (value) => ['READY', 'LOCKED', 'GRADED'].includes(value)
  },
  annotations: {
    type: Array,
    default: () => []  // Default factory
  }
})

// ✅ Emits typés
const emit = defineEmits({
  save: (data) => {
    // Validation payload
    return data && typeof data.score === 'number'
  },
  cancel: null
})
```

**INTERDIT** :
```javascript
// ❌ Props non typées
const props = defineProps(['copyId', 'status'])

// ❌ Modification directe des props
props.status = 'LOCKED'  // JAMAIS

// ❌ Mutation d'objets/arrays props
props.annotations.push(newAnnotation)  // JAMAIS
```

---

## 3. Pinia Stores

### 3.1 Structure de Store

**OBLIGATOIRE** :
```javascript
// stores/copyStore.js
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import copyService from '@/services/copyService'

export const useCopyStore = defineStore('copy', () => {
  // State
  const copies = ref([])
  const currentCopy = ref(null)
  const isLoading = ref(false)
  const error = ref(null)

  // Getters (computed)
  const lockedCopies = computed(() => {
    return copies.value.filter(c => c.status === 'LOCKED')
  })

  const currentCopyAnnotations = computed(() => {
    return currentCopy.value?.annotations || []
  })

  // Actions
  const fetchCopies = async () => {
    isLoading.value = true
    error.value = null
    try {
      copies.value = await copyService.getAll()
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      isLoading.value = false
    }
  }

  const lockCopy = async (copyId) => {
    try {
      const updatedCopy = await copyService.lock(copyId)
      // Mettre à jour le store
      const index = copies.value.findIndex(c => c.id === copyId)
      if (index !== -1) {
        copies.value[index] = updatedCopy
      }
      if (currentCopy.value?.id === copyId) {
        currentCopy.value = updatedCopy
      }
      return updatedCopy
    } catch (err) {
      error.value = err.message
      throw err
    }
  }

  const reset = () => {
    copies.value = []
    currentCopy.value = null
    isLoading.value = false
    error.value = null
  }

  return {
    // State
    copies,
    currentCopy,
    isLoading,
    error,
    // Getters
    lockedCopies,
    currentCopyAnnotations,
    // Actions
    fetchCopies,
    lockCopy,
    reset
  }
})
```

**Règles** :
- Setup syntax pour stores
- État séparé des getters et actions
- Actions asynchrones avec gestion d'erreurs
- Mise à jour cohérente du state
- Reset function pour cleanup

**INTERDIT** :
```javascript
// ❌ Mutation directe dans composant
copyStore.copies.push(newCopy)  // Utiliser action

// ❌ Logique métier complexe dans store
const processComplexData = () => {
  // 100 lignes de code... → service
}
```

---

## 4. Services API

### 4.1 Configuration Axios

**OBLIGATOIRE** :
```javascript
// services/api.js
import axios from 'axios'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '/api',
  timeout: 30000,
  withCredentials: true,  // Pour cookies (CSRF, session)
  headers: {
    'Content-Type': 'application/json'
  }
})

// Request interceptor - CSRF token
api.interceptors.request.use(
  (config) => {
    // Récupérer CSRF token depuis cookie
    const csrfToken = getCookie('csrftoken')
    if (csrfToken) {
      config.headers['X-CSRFToken'] = csrfToken
    }
    return config
  },
  (error) => Promise.reject(error)
)

// Response interceptor - Error handling
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Redirect to login
      window.location.href = '/login'
    } else if (error.response?.status === 403) {
      // Permission denied
      console.error('Permission denied')
    }
    return Promise.reject(error)
  }
)

export default api
```

**Règles** :
- Instance Axios centralisée
- CSRF token dans headers
- withCredentials pour cookies
- Interceptors pour erreurs globales
- Timeout configuré

### 4.2 Services API

**OBLIGATOIRE** :
```javascript
// services/copyService.js
import api from './api'

export default {
  async getAll(filters = {}) {
    const params = new URLSearchParams(filters)
    const response = await api.get(`/copies/?${params}`)
    return response.data
  },

  async getById(id) {
    const response = await api.get(`/copies/${id}/`)
    return response.data
  },

  async lock(id) {
    const response = await api.post(`/copies/${id}/lock/`)
    return response.data
  },

  async unlock(id) {
    const response = await api.post(`/copies/${id}/unlock/`)
    return response.data
  },

  async saveAnnotations(copyId, annotations) {
    const response = await api.post(`/copies/${copyId}/annotations/`, {
      annotations
    })
    return response.data
  },

  async finalize(copyId, data) {
    const response = await api.post(`/copies/${copyId}/finalize/`, data)
    return response.data
  }
}
```

**Règles** :
- Un service par ressource API
- Méthodes async/await
- Retour de response.data
- Gestion d'erreurs dans store/composant (pas dans service)

---

## 5. Composables (Composition API)

### 5.1 Structure Composable

**OBLIGATOIRE** :
```javascript
// composables/useAnnotations.js
import { ref, computed } from 'vue'
import copyService from '@/services/copyService'

export function useAnnotations(copyId) {
  const annotations = ref([])
  const isLoading = ref(false)
  const error = ref(null)

  const annotationsByPage = computed(() => {
    const byPage = {}
    annotations.value.forEach(annotation => {
      const page = annotation.page_number
      if (!byPage[page]) byPage[page] = []
      byPage[page].push(annotation)
    })
    return byPage
  })

  const loadAnnotations = async () => {
    isLoading.value = true
    error.value = null
    try {
      const data = await copyService.getAnnotations(copyId)
      annotations.value = data
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      isLoading.value = false
    }
  }

  const addAnnotation = (annotation) => {
    annotations.value.push({
      id: crypto.randomUUID(),
      ...annotation,
      created_at: new Date().toISOString()
    })
  }

  const removeAnnotation = (annotationId) => {
    const index = annotations.value.findIndex(a => a.id === annotationId)
    if (index !== -1) {
      annotations.value.splice(index, 1)
    }
  }

  const saveAnnotations = async () => {
    isLoading.value = true
    try {
      await copyService.saveAnnotations(copyId, annotations.value)
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      isLoading.value = false
    }
  }

  return {
    annotations,
    annotationsByPage,
    isLoading,
    error,
    loadAnnotations,
    addAnnotation,
    removeAnnotation,
    saveAnnotations
  }
}
```

**Règles** :
- Logique réutilisable
- État réactif encapsulé
- Return explicite des propriétés/méthodes
- Paramètres pour configuration

**INTERDIT** :
- Accès direct au DOM (sauf cas exceptionnel)
- Dépendances hard-codées
- Side effects non contrôlés

---

## 6. Routing

### 6.1 Configuration Router

**OBLIGATOIRE** :
```javascript
// router/index.js
import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/authStore'

const routes = [
  {
    path: '/',
    name: 'Dashboard',
    component: () => import('@/views/Dashboard.vue'),
    meta: { requiresAuth: true, role: 'professor' }
  },
  {
    path: '/corrector-desk/:copyId',
    name: 'CorrectorDesk',
    component: () => import('@/views/CorrectorDesk.vue'),
    meta: { requiresAuth: true, role: 'professor' },
    props: true  // Pass route params as props
  },
  {
    path: '/student/access',
    name: 'StudentAccess',
    component: () => import('@/views/StudentAccess.vue'),
    meta: { requiresAuth: true, role: 'student' }
  },
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/Login.vue')
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// Navigation guard
router.beforeEach((to, from, next) => {
  const authStore = useAuthStore()

  if (to.meta.requiresAuth && !authStore.isAuthenticated) {
    next('/login')
  } else if (to.meta.role && authStore.role !== to.meta.role) {
    next('/')  // Ou page 403
  } else {
    next()
  }
})

export default router
```

**Règles** :
- Meta fields pour permissions
- Navigation guards pour auth
- Lazy loading des views
- Props via route params

---

## 7. Gestion d'État

### 7.1 État Local vs Global

**État Local (ref/reactive)** :
- UI state (modals, dropdowns)
- Form state
- Temporary data

**État Global (Pinia)** :
- User authentication
- Shared data (copies, exams)
- Data nécessitant persistance

**INTERDIT** :
```javascript
// ❌ Tout dans Pinia
const uiStore = useUIStore()
uiStore.isModalOpen = true  // Non, état local suffit

// ❌ Props drilling excessif
<GrandChild :data="data" />  // 5 niveaux... utiliser store
```

---

## 8. Sécurité Frontend

### 8.1 XSS Prevention

**OBLIGATOIRE** :
```vue
<!-- ✅ Bon - Binding safe par défaut -->
<div>{{ userInput }}</div>

<!-- ❌ DANGER - v-html avec input utilisateur -->
<div v-html="userInput"></div>

<!-- ✅ OK seulement si sanitized -->
<div v-html="sanitizedHtml"></div>
```

**Règles** :
- Jamais `v-html` avec input utilisateur non sanitisé
- Utiliser DOMPurify si HTML nécessaire
- Validation côté client ET serveur

### 8.2 CSRF Protection

**OBLIGATOIRE** :
```javascript
// Inclure CSRF token dans headers (voir api.js)
const getCookie = (name) => {
  const value = `; ${document.cookie}`
  const parts = value.split(`; ${name}=`)
  if (parts.length === 2) return parts.pop().split(';').shift()
}
```

---

## 9. Performance

### 9.1 Optimisations

**OBLIGATOIRE** :
- Lazy loading des routes
- V-if vs v-show (v-if pour rare, v-show pour fréquent)
- Keys uniques sur v-for
- Debounce sur inputs (search, etc.)

**Code de Référence** :
```vue
<template>
  <!-- ✅ Keys uniques -->
  <div v-for="copy in copies" :key="copy.id">

  <!-- ✅ Debounced search -->
  <input v-model="searchTerm" @input="debouncedSearch" />
</template>

<script setup>
import { ref } from 'vue'
import { useDebounceFn } from '@vueuse/core'

const searchTerm = ref('')
const debouncedSearch = useDebounceFn(() => {
  performSearch(searchTerm.value)
}, 300)
</script>
```

**INTERDIT** :
```vue
<!-- ❌ Key non unique -->
<div v-for="(copy, index) in copies" :key="index">

<!-- ❌ Computed avec side effects -->
const total = computed(() => {
  saveToLocalStorage()  // ❌ Side effect
  return sum(values)
})
```

---

## 10. Tests Frontend

### 10.1 Tests Obligatoires

**OBLIGATOIRE** :
- Tests unitaires pour composables
- Tests de composants critiques (PDF viewer, Canvas)
- Tests d'intégration pour workflows

**Exemple Vitest** :
```javascript
// composables/__tests__/useAnnotations.test.js
import { describe, it, expect, vi } from 'vitest'
import { useAnnotations } from '../useAnnotations'
import copyService from '@/services/copyService'

vi.mock('@/services/copyService')

describe('useAnnotations', () => {
  it('should add annotation locally', () => {
    const { annotations, addAnnotation } = useAnnotations('copy-123')

    addAnnotation({ type: 'comment', text: 'Test' })

    expect(annotations.value).toHaveLength(1)
    expect(annotations.value[0].text).toBe('Test')
  })

  it('should save annotations to API', async () => {
    copyService.saveAnnotations.mockResolvedValue({ success: true })

    const { addAnnotation, saveAnnotations } = useAnnotations('copy-123')
    addAnnotation({ type: 'comment', text: 'Test' })

    await saveAnnotations()

    expect(copyService.saveAnnotations).toHaveBeenCalledWith(
      'copy-123',
      expect.arrayContaining([
        expect.objectContaining({ text: 'Test' })
      ])
    )
  })
})
```

---

## 11. Checklist Frontend

Avant tout commit frontend :
- [ ] Composition API utilisée
- [ ] Props/emits typés
- [ ] Pas de logique métier dans composants
- [ ] Services API pour toutes les calls
- [ ] CSRF token configuré
- [ ] Pas de v-html avec input utilisateur
- [ ] Keys uniques sur v-for
- [ ] Lazy loading des routes
- [ ] Tests passent

---

**Version** : 1.0
**Date** : 2026-01-21
**Statut** : Obligatoire
