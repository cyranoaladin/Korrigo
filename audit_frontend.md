Suite à l'analyse du code source (notamment `frontend/src/services`, `frontend/src/components/CanvasLayer.vue` et `frontend/src/views/admin/CorrectorDesk.vue`), voici le rapport de vérification et les suggestions d'optimisation.

### 1. Vérification du Typage TypeScript

**Constat :**
Le projet n'utilise **pas** correctement le typage TypeScript pour les données provenant de l'API. Bien que l'environnement soit configuré pour TypeScript (`tsconfig.json` présent, `strict: true`), l'implémentation actuelle est majoritairement en JavaScript standard :
*   **Services API :** Les fichiers `api.js` et `gradingApi.js` sont en JavaScript pur. Ils retournent `response.data` sans aucune définition de type.
*   **Composants :** `CorrectorDesk.vue` et `CanvasLayer.vue` n'utilisent pas `<script setup lang="ts">`. Les données sont stockées dans des `ref(null)` sans typage générique (ex: `const copy = ref(null)` au lieu de `const copy = ref<Copy | null>(null)`).
*   **Absence de définitions :** Il n'existe pas de dossier `types/` ou d'interfaces partagées pour les objets métiers (Copie, Annotation, Examen).

**Recommandation (Action immédiate) :**
Créer un fichier de définitions et migrer les composants clés.

**Fichier suggéré : `frontend/src/types/grading.ts`**
```typescript
export interface Annotation {
  x: number;
  y: number;
  w: number;
  h: number;
  type?: string;
  content?: string;
  page_index?: number;
}

export interface Exam {
  id: string;
  name: string;
  grading_structure: any[]; // À préciser selon la structure JSON
}

export interface Copy {
  id: string;
  status: 'STAGING' | 'READY' | 'LOCKED' | 'GRADED';
  exam: Exam;
  booklets: Array<{
    id: string;
    pages_images: string[];
  }>;
}
```

### 2. Optimisation du Rendu Canvas (`CanvasLayer.vue`)

**Problèmes de performance identifiés :**
1.  **Redessin complet à chaque frame :** La fonction `redraw` efface (`clearRect`) et redessine *toutes* les annotations existantes à chaque mouvement de souris (`mousemove`) lors de la création d'une nouvelle annotation.
2.  **Calculs répétitifs :** La boucle `forEach` sur `initialAnnotations` est exécutée inutilement alors que ces annotations ne changent pas pendant le drag & drop.

**Solution proposée : Double Buffering (Mise en cache)**
Utiliser un canvas hors-écran (en mémoire) pour dessiner les annotations statiques une seule fois. Le canvas principal ne fait que copier cette image et dessiner le rectangle de sélection par-dessus.

Voici le code refactorisé (migré en TypeScript + Optimisé) :

```vue
<script setup lang="ts">
import { ref, onMounted, computed, watch } from 'vue'
import type { Annotation } from '@/types/grading' // Supposant que vous avez créé le fichier

const props = defineProps<{
  width: number
  height: number
  scale?: number
  initialAnnotations: Annotation[]
  enabled?: boolean
}>()

const emit = defineEmits<{
  (e: 'annotation-created', payload: Annotation): void
}>()

const canvasRef = ref<HTMLCanvasElement | null>(null)
// Optimisation: Canvas hors-écran pour mettre en cache les annotations existantes
const offscreenCanvas = document.createElement('canvas')
const offscreenCtx = offscreenCanvas.getContext('2d')

const isDrawing = ref(false)
const startPos = ref({ x: 0, y: 0 })
const currentRect = ref<{ x: number, y: number, w: number, h: number } | null>(null)

const dpr = window.devicePixelRatio || 1

// Dimensions en pixels physiques
const canvasWidth = computed(() => Math.round(props.width * dpr))
const canvasHeight = computed(() => Math.round(props.height * dpr))

// 1. Dessine la couche statique (annotations existantes) dans le buffer
const updateStaticLayer = () => {
  if (!offscreenCtx) return
  
  // Redimensionnement du buffer
  offscreenCanvas.width = canvasWidth.value
  offscreenCanvas.height = canvasHeight.value
  
  // Reset transform
  offscreenCtx.resetTransform()
  offscreenCtx.scale(dpr, dpr)
  
  offscreenCtx.clearRect(0, 0, props.width, props.height)
  
  // Dessin des annotations statiques
  props.initialAnnotations.forEach(ann => {
    const rx = ann.x * props.width
    const ry = ann.y * props.height
    const rw = ann.w * props.width
    const rh = ann.h * props.height

    offscreenCtx.strokeStyle = '#007bff'
    offscreenCtx.lineWidth = 2
    offscreenCtx.setLineDash([])
    offscreenCtx.strokeRect(rx, ry, rw, rh)
    
    offscreenCtx.fillStyle = 'rgba(0, 123, 255, 0.1)'
    offscreenCtx.fillRect(rx, ry, rw, rh)
    
    if (ann.type) {
         offscreenCtx.fillStyle = '#007bff'
         offscreenCtx.font = 'bold 12px sans-serif'
         offscreenCtx.fillText(ann.type, rx, ry - 4)
    }
  })
  
  // Une fois le static layer à jour, on demande un rendu final
  requestAnimationFrame(renderMain)
}

// 2. Rendu principal : Copie le buffer + Dessine le rectangle en cours
const renderMain = () => {
  const canvas = canvasRef.value
  if (!canvas) return
  const ctx = canvas.getContext('2d')
  if (!ctx) return

  ctx.resetTransform()
  ctx.clearRect(0, 0, canvas.width, canvas.height) // Nettoyage en pixels physiques
  
  // Copie instantanée du buffer (très rapide)
  ctx.drawImage(offscreenCanvas, 0, 0)

  // Dessin de l'interaction dynamique (Drag & Drop)
  if (currentRect.value) {
      ctx.scale(dpr, dpr) // On réapplique l'échelle pour le dessin vectoriel
      ctx.strokeStyle = '#dc3545'
      ctx.lineWidth = 2
      ctx.setLineDash([5, 3])
      ctx.strokeRect(currentRect.value.x, currentRect.value.y, currentRect.value.w, currentRect.value.h)
      ctx.setLineDash([])
  }
}

// Watchers intelligents
watch(
    [() => props.width, () => props.height, () => props.scale, () => props.initialAnnotations], 
    () =>  requestAnimationFrame(updateStaticLayer),
    { deep: true } // Important pour détecter les changements dans le tableau d'annotations
)

onMounted(() => {
    updateStaticLayer()
})

// --- Gestion Souris (Inchangée mais typée) ---
const getCoords = (e: MouseEvent) => {
  if (!canvasRef.value) return { x: 0, y: 0 }
  const rect = canvasRef.value.getBoundingClientRect()
  return {
    x: e.clientX - rect.left,
    y: e.clientY - rect.top
  }
}

const startDrawing = (e: MouseEvent) => {
  if (!props.enabled) return
  isDrawing.value = true
  const coords = getCoords(e)
  startPos.value = coords
  currentRect.value = { x: coords.x, y: coords.y, w: 0, h: 0 }
  requestAnimationFrame(renderMain)
}

const draw = (e: MouseEvent) => {
  if (!isDrawing.value) return
  const coords = getCoords(e)
  
  currentRect.value = {
      x: startPos.value.x,
      y: startPos.value.y,
      w: coords.x - startPos.value.x,
      h: coords.y - startPos.value.y
  }
  requestAnimationFrame(renderMain)
}

const stopDrawing = () => {
  if (!isDrawing.value) return
  isDrawing.value = false
  
  if (currentRect.value && Math.abs(currentRect.value.w) > 5 && Math.abs(currentRect.value.h) > 5) {
      let { x, y, w, h } = currentRect.value
      if (w < 0) { x += w; w = Math.abs(w); }
      if (h < 0) { y += h; h = Math.abs(h); }
      
      emit('annotation-created', {
          x: x / props.width,
          y: y / props.height,
          w: w / props.width,
          h: h / props.height
      })
  }
  currentRect.value = null
  requestAnimationFrame(renderMain)
}
</script>

<template>
  <canvas 
    ref="canvasRef"
    :width="canvasWidth"
    :height="canvasHeight"
    :style="{ width: width + 'px', height: height + 'px' }"
    class="canvas-layer"
    :class="{ 'disabled': !enabled }"
    @mousedown="startDrawing"
    @mousemove="draw"
    @mouseup="stopDrawing"
    @mouseleave="stopDrawing"
  />
</template>

<style scoped>
.canvas-layer {
  position: absolute;
  top: 0;
  left: 0;
  z-index: 10;
  touch-action: none;
  cursor: crosshair;
}
.disabled {
    pointer-events: none;
}
</style>
```
