# Skill: Vue Frontend Expert

## Quand Activer Ce Skill

Ce skill doit être activé pour :
- Développement de composants Vue.js
- Architecture frontend (stores, services, routing)
- Intégration API backend
- Performance frontend
- Gestion d'état (Pinia)
- Interactions Canvas/PDF complexes
- UI/UX pour workflows métier

## Responsabilités

En tant que **Vue Frontend Expert**, vous devez :

### 1. Architecture Frontend

- **Structurer** l'application Vue en composants réutilisables
- **Organiser** les stores Pinia de manière cohérente
- **Gérer** les services API de manière centralisée
- **Implémenter** le routing avec guards
- **Séparer** la logique métier des composants UI

### 2. Composants Vue

- **Créer** des composants avec Composition API
- **Typer** les props et emits
- **Gérer** l'état local vs global approprié
- **Optimiser** le rendu (v-if vs v-show, keys, etc.)
- **Respecter** les bonnes pratiques Vue 3

### 3. Gestion d'État

- **Utiliser** Pinia pour état global
- **Structurer** les stores par domaine
- **Implémenter** actions asynchrones avec gestion d'erreurs
- **Éviter** la duplication de données entre stores
- **Synchroniser** avec backend de manière cohérente

### 4. Intégration API

- **Centraliser** les appels API dans services
- **Gérer** les erreurs et loading states
- **Implémenter** CSRF protection
- **Utiliser** interceptors Axios pour auth
- **Gérer** les timeouts et retry

### 5. Performance

- **Lazy load** des routes
- **Optimiser** les composants lourds
- **Debounce** les inputs
- **Virtualizer** les longues listes si nécessaire
- **Monitorer** les performances

## Patterns Vue

### Pattern 1 : Composable pour Logique Réutilisable

**Quand** : Logique commune entre plusieurs composants

**Implémentation** :
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
    annotations.value.forEach(a => {
      if (!byPage[a.page_number]) byPage[a.page_number] = []
      byPage[a.page_number].push(a)
    })
    return byPage
  })

  const loadAnnotations = async () => {
    isLoading.value = true
    try {
      annotations.value = await copyService.getAnnotations(copyId)
    } catch (err) {
      error.value = err.message
    } finally {
      isLoading.value = false
    }
  }

  const addAnnotation = (annotation) => {
    annotations.value.push({ id: crypto.randomUUID(), ...annotation })
  }

  return { annotations, annotationsByPage, isLoading, error, loadAnnotations, addAnnotation }
}

// Utilisation
const { annotations, addAnnotation } = useAnnotations(copyId.value)
```

### Pattern 2 : Service API

**Quand** : Toute communication avec backend

**Implémentation** :
```javascript
// services/api.js
import axios from 'axios'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '/api',
  withCredentials: true,
  timeout: 30000
})

api.interceptors.request.use(config => {
  const csrfToken = getCookie('csrftoken')
  if (csrfToken) {
    config.headers['X-CSRFToken'] = csrfToken
  }
  return config
})

api.interceptors.response.use(
  response => response,
  error => {
    if (error.response?.status === 401) {
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

export default api

// services/copyService.js
import api from './api'

export default {
  async getAll(filters = {}) {
    const response = await api.get('/copies/', { params: filters })
    return response.data
  },

  async getById(id) {
    const response = await api.get(`/copies/${id}/`)
    return response.data
  },

  async lock(id) {
    const response = await api.post(`/copies/${id}/lock/`)
    return response.data
  }
}
```

### Pattern 3 : Store Pinia

**Quand** : État partagé entre composants

**Implémentation** :
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

  // Getters
  const readyCopies = computed(() => copies.value.filter(c => c.status === 'READY'))
  const lockedCopies = computed(() => copies.value.filter(c => c.status === 'LOCKED'))

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
      const updated = await copyService.lock(copyId)
      const index = copies.value.findIndex(c => c.id === copyId)
      if (index !== -1) copies.value[index] = updated
      return updated
    } catch (err) {
      error.value = err.message
      throw err
    }
  }

  return { copies, currentCopy, isLoading, error, readyCopies, lockedCopies, fetchCopies, lockCopy }
})
```

## Composants Vue - Bonnes Pratiques

### Structure Composant

```vue
<template>
  <div class="copy-viewer">
    <LoadingSpinner v-if="isLoading" />
    <ErrorMessage v-else-if="error" :message="error" />
    <template v-else>
      <PDFViewer :pdf-url="pdfUrl" @page-change="handlePageChange" />
      <AnnotationLayer
        v-if="canAnnotate"
        :annotations="currentAnnotations"
        @annotation-added="handleAnnotationAdded"
      />
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useCopyStore } from '@/stores/copyStore'
import { useAnnotations } from '@/composables/useAnnotations'

// Props
const props = defineProps({
  copyId: { type: String, required: true },
  canAnnotate: { type: Boolean, default: false }
})

// Emits
const emit = defineEmits(['saved', 'error'])

// Store & Composables
const copyStore = useCopyStore()
const { annotations, addAnnotation } = useAnnotations(props.copyId)

// State
const pdfUrl = ref(null)
const currentPage = ref(1)
const isLoading = ref(false)
const error = ref(null)

// Computed
const currentAnnotations = computed(() =>
  annotations.value.filter(a => a.page_number === currentPage.value)
)

// Methods
const handlePageChange = (page) => {
  currentPage.value = page
}

const handleAnnotationAdded = async (annotation) => {
  try {
    addAnnotation(annotation)
    emit('saved')
  } catch (err) {
    emit('error', err)
  }
}

// Lifecycle
onMounted(async () => {
  isLoading.value = true
  try {
    pdfUrl.value = await copyStore.fetchCopyPdfUrl(props.copyId)
  } catch (err) {
    error.value = err.message
  } finally {
    isLoading.value = false
  }
})
</script>

<style scoped>
.copy-viewer {
  display: flex;
  height: 100vh;
  gap: 1rem;
}
</style>
```

### Props Validation

```javascript
const props = defineProps({
  copyId: {
    type: String,
    required: true,
    validator: (value) => /^[0-9a-f-]{36}$/.test(value) // UUID
  },
  status: {
    type: String,
    default: 'READY',
    validator: (value) => ['READY', 'LOCKED', 'GRADED'].includes(value)
  },
  annotations: {
    type: Array,
    default: () => []
  }
})
```

## Canvas et PDF - Patterns Spécifiques

### Annotation sur Canvas

```javascript
// composables/useCanvas.js
import { ref, onMounted, onUnmounted } from 'vue'

export function useCanvas(canvasRef) {
  const ctx = ref(null)
  const isDrawing = ref(false)
  const currentPath = ref([])

  const startDrawing = (event) => {
    isDrawing.value = true
    const rect = canvasRef.value.getBoundingClientRect()
    const x = event.clientX - rect.left
    const y = event.clientY - rect.top

    currentPath.value = [{ x, y }]
  }

  const draw = (event) => {
    if (!isDrawing.value) return

    const rect = canvasRef.value.getBoundingClientRect()
    const x = event.clientX - rect.left
    const y = event.clientY - rect.top

    currentPath.value.push({ x, y })

    // Dessiner
    if (ctx.value) {
      ctx.value.lineTo(x, y)
      ctx.value.stroke()
    }
  }

  const stopDrawing = () => {
    if (isDrawing.value && currentPath.value.length > 0) {
      // Normaliser coordonnées
      const normalized = normalizeCoordinates(currentPath.value, canvasRef.value)
      emit('annotation-added', { type: 'path', points: normalized })
    }
    isDrawing.value = false
    currentPath.value = []
  }

  onMounted(() => {
    ctx.value = canvasRef.value.getContext('2d')
    ctx.value.lineWidth = 2
    ctx.value.strokeStyle = '#FF0000'
  })

  return { startDrawing, draw, stopDrawing }
}
```

### Normalisation Coordonnées

```javascript
// utils/canvasUtils.js
export function normalizeCoordinates(points, canvas) {
  return points.map(p => ({
    x: p.x / canvas.width,
    y: p.y / canvas.height
  }))
}

export function denormalizeCoordinates(points, canvas) {
  return points.map(p => ({
    x: p.x * canvas.width,
    y: p.y * canvas.height
  }))
}
```

## Routing avec Permissions

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
    path: '/student/access',
    name: 'StudentAccess',
    component: () => import('@/views/StudentAccess.vue'),
    meta: { requiresAuth: true, role: 'student' }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach((to, from, next) => {
  const authStore = useAuthStore()

  if (to.meta.requiresAuth && !authStore.isAuthenticated) {
    next('/login')
  } else if (to.meta.role && authStore.role !== to.meta.role) {
    next('/')
  } else {
    next()
  }
})

export default router
```

## Performance Vue

### Lazy Loading

```javascript
// ✅ Lazy load routes
const routes = [
  {
    path: '/corrector-desk/:id',
    component: () => import('@/views/CorrectorDesk.vue')  // Chargé à la demande
  }
]

// ✅ Lazy load composants lourds
<script setup>
import { defineAsyncComponent } from 'vue'

const HeavyChart = defineAsyncComponent(() =>
  import('@/components/HeavyChart.vue')
)
</script>
```

### Debounce

```javascript
import { ref } from 'vue'
import { useDebounceFn } from '@vueuse/core'

const searchTerm = ref('')

const debouncedSearch = useDebounceFn(() => {
  performSearch(searchTerm.value)
}, 300)
```

### Virtual Scrolling

```vue
<template>
  <RecycleScroller
    :items="copies"
    :item-size="80"
    key-field="id"
    v-slot="{ item }"
  >
    <CopyCard :copy="item" />
  </RecycleScroller>
</template>
```

## Tests Vue

### Test Composable

```javascript
import { describe, it, expect } from 'vitest'
import { useAnnotations } from '@/composables/useAnnotations'

describe('useAnnotations', () => {
  it('should add annotation', () => {
    const { annotations, addAnnotation } = useAnnotations('copy-123')

    addAnnotation({ type: 'comment', text: 'Test' })

    expect(annotations.value).toHaveLength(1)
    expect(annotations.value[0].text).toBe('Test')
  })
})
```

### Test Composant

```javascript
import { mount } from '@vue/test-utils'
import CopyCard from '@/components/CopyCard.vue'

describe('CopyCard', () => {
  it('renders copy data', () => {
    const wrapper = mount(CopyCard, {
      props: {
        copy: { id: '123', anonymous_id: 'ANON001', status: 'READY' }
      }
    })

    expect(wrapper.text()).toContain('ANON001')
    expect(wrapper.text()).toContain('READY')
  })
})
```

## Références

- Vue 3 Documentation : https://vuejs.org/
- Pinia Documentation : https://pinia.vuejs.org/
- Vite Documentation : https://vitejs.dev/
- VueUse (composables) : https://vueuse.org/

---

**Activation** : Automatique pour code frontend Vue
**Priorité** : Haute
**Version** : 1.0
