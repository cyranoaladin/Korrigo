<script setup>
import { ref, onMounted, computed } from 'vue'

const props = defineProps({
  width: { type: Number, required: true },
  height: { type: Number, required: true },
  scale: { type: Number, required: true },
  initialAnnotations: { type: Array, default: () => [] }
})

const emit = defineEmits(['update-annotations'])

const canvasRef = ref(null)
const isDrawing = ref(false)
const currentPath = ref([])
const annotations = ref([...props.initialAnnotations])

// Drawing context
let ctx = null

onMounted(() => {
  const canvas = canvasRef.value
  ctx = canvas.getContext('2d')
  ctx.strokeStyle = 'red'
  ctx.lineWidth = 2 * props.scale
  ctx.lineCap = 'round'
  ctx.lineJoin = 'round'
  
  redraw()
})

const getCoords = (e) => {
  const rect = canvasRef.value.getBoundingClientRect()
  return {
    x: e.clientX - rect.left,
    y: e.clientY - rect.top
  }
}

const startDrawing = (e) => {
  isDrawing.value = true
  const coords = getCoords(e)
  currentPath.value = [coords]
  
  ctx.beginPath()
  ctx.moveTo(coords.x, coords.y)
}

const draw = (e) => {
  if (!isDrawing.value) return
  const coords = getCoords(e)
  currentPath.value.push(coords)
  
  ctx.lineTo(coords.x, coords.y)
  ctx.stroke()
}

const stopDrawing = () => {
  if (!isDrawing.value) return
  isDrawing.value = false
  ctx.closePath()
  
  // Save vector data relative to canvas dimensions (normalized 0-1?) 
  // OR absolute coords. Specification asks for {x,y}. 
  // Let's keep absolute for MVP simplicity, assume consistent resolution.
  
  if (currentPath.value.length > 1) {
    annotations.value.push({
      type: 'path',
      color: 'red',
      points: [...currentPath.value]
    })
    emit('update-annotations', annotations.value)
  }
}

const redraw = () => {
    // Logic to redraw existing annotations from props.initialAnnotations
    // Not implemented fully for MVP step, but critical for loading saved state.
}

</script>

<template>
  <canvas 
    ref="canvasRef"
    :width="width"
    :height="height"
    class="canvas-layer"
    @mousedown="startDrawing"
    @mousemove="draw"
    @mouseup="stopDrawing"
    @mouseleave="stopDrawing"
  ></canvas>
</template>

<style scoped>
.canvas-layer {
  position: absolute;
  top: 0;
  left: 0;
  /* Critical constraint: Transparent background */
  background: transparent; 
  cursor: crosshair;
  /* Ensure it matches strict dimensions of PDF underneath */
}
</style>
