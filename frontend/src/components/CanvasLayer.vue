<script setup>
import { ref, onMounted, watch } from 'vue'

const props = defineProps({
  width: { type: Number, required: true }, // CSS width
  height: { type: Number, required: true }, // CSS height
  scale: { type: Number, default: 1.0 }, // Used for line width calculation
  initialAnnotations: { type: Array, default: () => [] },
  enabled: { type: Boolean, default: true },
})

const emit = defineEmits(['annotation-created'])

const canvasRef = ref(null)
const isDrawing = ref(false)
const startPos = ref({ x: 0, y: 0 })
const currentRect = ref(null)

// Palm rejection: track active pen pointer IDs; when a pen is down, ignore touch events
const activePenPointers = new Set()
// Multi-touch guard: track active touch pointers to detect pinch (2+ fingers)
const activeTouchPointers = new Set()

const dpr = window.devicePixelRatio || 1

const setupCanvas = () => {
    const canvas = canvasRef.value
    if (!canvas) return
    if (!props.width || !props.height || props.width < 1 || props.height < 1) return

    // Manually update canvas physical dimensions — this clears the canvas and
    // resets the 2D context state atomically, BEFORE we redraw. This avoids
    // the race condition that happens when Vue updates :width/:height attributes
    // asynchronously (which also clears the canvas, potentially after redraw).
    const physW = Math.round(props.width * dpr)
    const physH = Math.round(props.height * dpr)
    if (canvas.width !== physW) canvas.width = physW
    if (canvas.height !== physH) canvas.height = physH

    // Set CSS display size
    canvas.style.width = props.width + 'px'
    canvas.style.height = props.height + 'px'

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

    // Type-based color map (French — canonical types)
    const typeColors = {
        'COMMENTAIRE': { stroke: '#2563eb', fill: 'rgba(37, 99, 235, 0.12)', text: '#1e40af' },
        'SURLIGNAGE':  { stroke: '#d97706', fill: 'rgba(251, 191, 36, 0.18)', text: '#92400e' },
        'ERREUR':      { stroke: '#dc2626', fill: 'rgba(220, 38, 38, 0.12)', text: '#991b1b' },
        'BONUS':       { stroke: '#16a34a', fill: 'rgba(22, 163, 74, 0.12)', text: '#166534' },
        'VRAI':        { stroke: '#16a34a', fill: 'rgba(22, 163, 74, 0.10)', text: '#16a34a' },
        'FAUX':        { stroke: '#dc2626', fill: 'rgba(220, 38, 38, 0.10)', text: '#dc2626' },
    }
    const defaultColor = { stroke: '#2563eb', fill: 'rgba(37, 99, 235, 0.12)', text: '#1e40af' }

    // Word-wrap helper: splits text into lines that fit within maxWidth
    const wrapText = (text, maxWidth, font) => {
        ctx.font = font
        const words = text.split(/\s+/)
        const lines = []
        let currentLine = ''
        for (const word of words) {
            const testLine = currentLine ? currentLine + ' ' + word : word
            if (ctx.measureText(testLine).width > maxWidth && currentLine) {
                lines.push(currentLine)
                currentLine = word
            } else {
                currentLine = testLine
            }
        }
        if (currentLine) lines.push(currentLine)
        return lines
    }

    // Draw existing annotations
    props.initialAnnotations.forEach(ann => {
        const rx = ann.x * props.width
        const ry = ann.y * props.height
        const rw = ann.w * props.width
        const rh = ann.h * props.height
        const colors = typeColors[ann.type] || defaultColor

        // Stamp types: symbol only, no text
        const isStamp = ann.type === 'VRAI' || ann.type === 'FAUX' || ann.type === 'BONUS'
        // Surlignage: no label above, just fill + optional text
        const isSurlignage = ann.type === 'SURLIGNAGE' || ann.type === 'HIGHLIGHT'

        // Rectangle fill + stroke
        ctx.fillStyle = colors.fill
        ctx.fillRect(rx, ry, rw, rh)
        ctx.strokeStyle = colors.stroke
        ctx.lineWidth = isSurlignage ? 1 : 2
        ctx.setLineDash([])
        ctx.strokeRect(rx, ry, rw, rh)

        if (isStamp) {
            // Draw stamp symbol centered (no label, no text)
            const cx = rx + rw / 2
            const cy = ry + rh / 2
            const size = Math.min(rw, rh) * 0.35

            ctx.save()
            ctx.lineCap = 'round'
            ctx.lineJoin = 'round'
            ctx.lineWidth = 3.5

            if (ann.type === 'VRAI') {
                ctx.strokeStyle = '#16a34a'
                ctx.beginPath()
                ctx.moveTo(cx - size, cy)
                ctx.lineTo(cx - size * 0.3, cy + size * 0.7)
                ctx.lineTo(cx + size, cy - size * 0.6)
                ctx.stroke()
            } else if (ann.type === 'FAUX') {
                ctx.strokeStyle = '#dc2626'
                ctx.beginPath()
                ctx.moveTo(cx - size * 0.7, cy - size * 0.7)
                ctx.lineTo(cx + size * 0.7, cy + size * 0.7)
                ctx.stroke()
                ctx.beginPath()
                ctx.moveTo(cx + size * 0.7, cy - size * 0.7)
                ctx.lineTo(cx - size * 0.7, cy + size * 0.7)
                ctx.stroke()
            } else {
                // BONUS: star symbol
                ctx.fillStyle = '#16a34a'
                ctx.font = `${Math.min(rw, rh) * 0.6}px sans-serif`
                ctx.textAlign = 'center'
                ctx.textBaseline = 'middle'
                ctx.fillText('⭐', cx, cy)
                ctx.textAlign = 'start'
                ctx.textBaseline = 'alphabetic'
            }
            ctx.restore()
        } else {
            // Label above rectangle (skip for surlignage)
            if (ann.type && !isSurlignage) {
                ctx.fillStyle = colors.text
                ctx.font = 'bold 11px sans-serif'
                const labelY = ry >= 14 ? ry - 4 : ry + 14
                ctx.fillText(ann.type, rx + 2, labelY)
            }

            // Content text inside rectangle
            if (ann.content) {
                ctx.save()
                ctx.beginPath()
                ctx.rect(rx + 4, ry + 2, rw - 8, rh - 4)
                ctx.clip()

                const fontSize = Math.max(10, Math.min(13, rh * 0.25))
                const font = `600 ${fontSize}px sans-serif`
                const lines = wrapText(ann.content, rw - 10, font)
                const lineHeight = fontSize * 1.3

                ctx.font = font
                ctx.fillStyle = colors.text
                ctx.textBaseline = 'top'
                const startY = ry + 4
                for (let i = 0; i < lines.length; i++) {
                    const ly = startY + i * lineHeight
                    if (ly + lineHeight > ry + rh) break
                    ctx.fillText(lines[i], rx + 5, ly)
                }
                ctx.restore()
            }
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

// Watcher — any prop change triggers setupCanvas() which atomically resizes
// and redraws the canvas. No flush:'post' needed because Vue no longer controls
// the canvas width/height attributes (managed manually inside setupCanvas).
watch(
    [() => props.width, () => props.height, () => props.scale, () => props.initialAnnotations],
    () => setupCanvas(),
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
  // Palm rejection: ignore touch when a pen/stylus pointer is active
  if (e.pointerType === 'touch' && activePenPointers.size > 0) return
  // Track pen pointers for palm rejection
  if (e.pointerType === 'pen') activePenPointers.add(e.pointerId)
  // Multi-touch guard: ignore 2nd+ finger (pinch zoom) — don't interfere with scroll-area zoom
  if (e.pointerType === 'touch') {
    activeTouchPointers.add(e.pointerId)
    if (activeTouchPointers.size > 1) return
  }
  // Capture pointer so move/up events fire even if cursor leaves the canvas
  e.currentTarget.setPointerCapture(e.pointerId)

  isDrawing.value = true
  const coords = getCoords(e)
  startPos.value = coords
  currentRect.value = { x: coords.x, y: coords.y, w: 0, h: 0 }
  requestAnimationFrame(() => setupCanvas())
}

const draw = (e) => {
  if (!isDrawing.value) return
  const coords = getCoords(e)
  currentRect.value = {
      x: startPos.value.x,
      y: startPos.value.y,
      w: coords.x - startPos.value.x,
      h: coords.y - startPos.value.y,
  }
  requestAnimationFrame(() => setupCanvas())
}

const stopDrawing = (e) => {
  if (e?.pointerType === 'touch') activeTouchPointers.delete(e.pointerId)
  if (!isDrawing.value) return
  isDrawing.value = false
  if (e?.pointerType === 'pen') activePenPointers.delete(e.pointerId)

  // Quick stamp on tap: tiny movement → emit a small fixed-size annotation rect
  if (currentRect.value && Math.abs(currentRect.value.w) <= 5 && Math.abs(currentRect.value.h) <= 5) {
      const STAMP_PX = 30
      const normalized = {
          x: Math.max(0, (startPos.value.x - STAMP_PX / 2) / props.width),
          y: Math.max(0, (startPos.value.y - STAMP_PX / 2) / props.height),
          w: STAMP_PX / props.width,
          h: STAMP_PX / props.height,
      }
      emit('annotation-created', normalized)
      currentRect.value = null
      requestAnimationFrame(() => setupCanvas())
      return
  }

  // Normalize and emit regular drag rect
  if (currentRect.value && Math.abs(currentRect.value.w) > 5 && Math.abs(currentRect.value.h) > 5) {
      let x = currentRect.value.x
      let y = currentRect.value.y
      let w = currentRect.value.w
      let h = currentRect.value.h
      if (w < 0) { x += w; w = Math.abs(w); }
      if (h < 0) { y += h; h = Math.abs(h); }
      emit('annotation-created', {
          x: x / props.width,
          y: y / props.height,
          w: w / props.width,
          h: h / props.height,
      })
  }
  currentRect.value = null
  requestAnimationFrame(() => setupCanvas())
}
</script>

<template>
  <canvas
    ref="canvasRef"
    :class="{ 'canvas-layer': true, 'disabled': !enabled }"
    data-testid="canvas-layer"
    @pointerdown="startDrawing"
    @pointermove="draw"
    @pointerup="stopDrawing"
    @pointercancel="stopDrawing"
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
.canvas-layer.disabled {
    touch-action: auto;
    cursor: default;
    pointer-events: none;
}
</style>
