<script setup>
import { ref, onMounted, computed, watch } from 'vue'

const props = defineProps({
  width: { type: Number, required: true }, // CSS width
  height: { type: Number, required: true }, // CSS height
  scale: { type: Number, default: 1.0 }, // Used for line width calculation
  initialAnnotations: { type: Array, default: () => [] },
  enabled: { type: Boolean, default: true }
})

const emit = defineEmits(['annotation-created'])

const canvasRef = ref(null)
const isDrawing = ref(false)
const startPos = ref({ x: 0, y: 0 })
const currentRect = ref(null)

const dpr = window.devicePixelRatio || 1

// Dimensions in device pixels
const canvasWidth = computed(() => Math.round(props.width * dpr))
const canvasHeight = computed(() => Math.round(props.height * dpr))

const setupCanvas = () => {
    const canvas = canvasRef.value
    if (!canvas) return
    const ctx = canvas.getContext('2d')

    // Reset transform to identity before applying scale
    ctx.resetTransform()
    ctx.scale(dpr, dpr)
    
    // Line styles
    ctx.lineCap = 'round'
    ctx.lineJoin = 'round'
    
    redraw(ctx)
}

const redraw = (ctx) => {
    if (!canvasRef.value) return
    if (!ctx) ctx = canvasRef.value.getContext('2d')
    
    // Clear in logical CSS pixels
    ctx.clearRect(0, 0, props.width, props.height)

    // Draw existing annotations
    props.initialAnnotations.forEach(ann => {
        const rx = ann.x * props.width
        const ry = ann.y * props.height
        const rw = ann.w * props.width
        const rh = ann.h * props.height

        ctx.strokeStyle = '#007bff' // Blue
        ctx.lineWidth = 2 // Constant screen width
        ctx.setLineDash([])
        ctx.strokeRect(rx, ry, rw, rh)
        
        ctx.fillStyle = 'rgba(0, 123, 255, 0.1)'
        ctx.fillRect(rx, ry, rw, rh)
        
        if (ann.type) {
             ctx.fillStyle = '#007bff'
             ctx.font = 'bold 12px sans-serif'
             ctx.fillText(ann.type, rx, ry - 4)
        }
    })

    // Draw current drag rect
    if (currentRect.value) {
        ctx.strokeStyle = '#dc3545' // Red
        ctx.lineWidth = 2
        ctx.setLineDash([5, 3])
        ctx.strokeRect(currentRect.value.x, currentRect.value.y, currentRect.value.w, currentRect.value.h)
        ctx.setLineDash([])
    }
}

// Watchers
watch(
    [() => props.width, () => props.height, () => props.scale, () => props.initialAnnotations], 
    () =>  requestAnimationFrame(() => setupCanvas()),
    { deep: true }
)

onMounted(() => {
    setupCanvas()
})

const getCoords = (e) => {
  const rect = canvasRef.value.getBoundingClientRect()
  return {
    x: e.clientX - rect.left,
    y: e.clientY - rect.top
  }
}

const startDrawing = (e) => {
  if (!props.enabled) return
  isDrawing.value = true
  const coords = getCoords(e)
  startPos.value = coords
  currentRect.value = { x: coords.x, y: coords.y, w: 0, h: 0 }
  requestAnimationFrame(() => redraw())
}

const draw = (e) => {
  if (!isDrawing.value) return
  const coords = getCoords(e)
  
  const w = coords.x - startPos.value.x
  const h = coords.y - startPos.value.y
  
  currentRect.value = {
      x: startPos.value.x,
      y: startPos.value.y,
      w: w,
      h: h
  }
  requestAnimationFrame(() => redraw())
}

const stopDrawing = () => {
  if (!isDrawing.value) return
  isDrawing.value = false
  
  // Normalize and Emit
  if (currentRect.value && Math.abs(currentRect.value.w) > 5 && Math.abs(currentRect.value.h) > 5) {
      let x = currentRect.value.x
      let y = currentRect.value.y
      let w = currentRect.value.w
      let h = currentRect.value.h
      
      // Handle negative dims
      if (w < 0) { x += w; w = Math.abs(w); }
      if (h < 0) { y += h; h = Math.abs(h); }
      
      const normalized = {
          x: x / props.width,
          y: y / props.height,
          w: w / props.width,
          h: h / props.height
      }
      
      emit('annotation-created', normalized)
  }
  currentRect.value = null
  requestAnimationFrame(() => redraw())
}
</script>

<template>
  <canvas 
    ref="canvasRef"
    :width="canvasWidth"
    :height="canvasHeight"
    :style="{ 
      width: width + 'px', 
      height: height + 'px',
    }"
    :class="{ 'canvas-layer': true, 'disabled': !enabled }"
    data-testid="canvas-layer"
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
  pointer-events: auto;
}
.canvas-layer.disabled {
    cursor: not-allowed;
    pointer-events: none;
}
</style>
