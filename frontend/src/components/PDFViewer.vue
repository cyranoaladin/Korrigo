<script setup>
import { ref, watch } from 'vue'
import * as pdfjsLib from 'pdfjs-dist/build/pdf.mjs'

// Worker setup handled via CDN for simplicity in this MVP environment
// In prod, copy worker file to public or configure vite
pdfjsLib.GlobalWorkerOptions.workerSrc = `https://unpkg.com/pdfjs-dist@${pdfjsLib.version}/build/pdf.worker.min.mjs`

const props = defineProps({
  pdfUrl: {
    type: String,
    required: true
  },
  pageNumber: {
    type: Number,
    default: 1
  }
})

const emit = defineEmits(['page-rendered'])

const canvasRef = ref(null)
const pdfDoc = ref(null)

const renderPage = async (num) => {
  if (!pdfDoc.value) return

  try {
    const page = await pdfDoc.value.getPage(num)
    
    // Scale Logic: We want high res for crisp text
    const scale = 1.5
    const viewport = page.getViewport({ scale })

    const canvas = canvasRef.value
    const context = canvas.getContext('2d')
    canvas.height = viewport.height
    canvas.width = viewport.width

    const renderContext = {
      canvasContext: context,
      viewport: viewport
    }
    
    await page.render(renderContext).promise
    
    emit('page-rendered', { 
      width: viewport.width, 
      height: viewport.height,
      scale: scale 
    })
    
  } catch (err) {
    console.error('Error rendering page:', err)
  }
}

watch(() => props.pdfUrl, async (newUrl) => {
  if (newUrl) {
    pdfDoc.value = await pdfjsLib.getDocument(newUrl).promise
    renderPage(props.pageNumber)
  }
})

watch(() => props.pageNumber, (newVal) => {
  renderPage(newVal)
})
</script>

<template>
  <div class="pdf-container">
    <canvas ref="canvasRef" />
  </div>
</template>

<style scoped>
.pdf-container {
  display: flex;
  justify-content: center;
  /* Ensure container doesn't collapse */
  min-height: 800px; 
}
canvas {
  box-shadow: 0 0 10px rgba(0,0,0,0.1);
  direction: ltr;
}
</style>
