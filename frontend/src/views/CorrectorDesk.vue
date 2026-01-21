<script setup>
import { ref } from 'vue'
import { useRoute } from 'vue-router'
import PDFViewer from '../components/PDFViewer.vue'
import CanvasLayer from '../components/CanvasLayer.vue'

// Mock Data for MVP - In real app, fetch from Store
const route = useRoute()
const copyId = route.params.copyId // Access from router path
const pdfUrl = '/sample-copy.pdf' // Placeholder URL (ensure backend serves this)
const scale = ref(1.5)

const pdfDimensions = ref({ width: 0, height: 0 })
const annotations = ref([])

// Sidebar Logic
const questions = ref([
  { id: 'ex1q1', label: 'Ex 1.a', score: 0, max: 2 },
  { id: 'ex1q2', label: 'Ex 1.b', score: 0, max: 3 },
  { id: 'ex2', label: 'Ex 2', score: 0, max: 5 },
])

const handlePageRendered = (dims) => {
  pdfDimensions.value = dims
}

const handleUpdateAnnotations = (newAnnotations) => {
  annotations.value = newAnnotations
  console.log('Annotations updated:', newAnnotations)
  // TODO: Auto-save to backend
}

const totalScore = ref(0) // Computed logic would go here
</script>

<template>
  <div class="corrector-desk">
    <div class="left-panel">
      <div class="canvas-wrapper" :style="{ width: pdfDimensions.width + 'px', height: pdfDimensions.height + 'px' }">
        <PDFViewer 
          :pdfUrl="pdfUrl" 
          :pageNumber="1"
          @page-rendered="handlePageRendered" 
        />
        <CanvasLayer
          v-if="pdfDimensions.width > 0"
          :width="pdfDimensions.width"
          :height="pdfDimensions.height"
          :scale="scale"
          @update-annotations="handleUpdateAnnotations"
        />
      </div>
    </div>
    
    <div class="right-sidebar">
      <h2>Barème</h2>
      <div v-for="q in questions" :key="q.id" class="grade-row">
        <label>{{ q.label }}</label>
        <input type="number" v-model.number="q.score" min="0" :max="q.max" step="0.5" />
        <span>/ {{ q.max }}</span>
      </div>
      <div class="total-row">
        <strong>Total: {{ questions.reduce((sum, q) => sum + q.score, 0) }} / 10</strong>
      </div>
      <div class="actions">
        <button class="btn-save">Enregistrer</button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.corrector-desk {
  display: flex;
  height: 100vh;
  overflow: hidden;
}
.left-panel {
  flex: 7;
  overflow: auto;
  background: #525659; /* Dark PDF viewer background */
  display: flex;
  justify-content: center;
  padding: 20px;
}
.canvas-wrapper {
  position: relative;
  /* Stack wrapper context */
}
.right-sidebar {
  flex: 3;
  background: #f8f9fa;
  box-shadow: -2px 0 5px rgba(0,0,0,0.1);
  padding: 20px;
  overflow-y: auto;
}
.grade-row {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 10px;
  border-bottom: 1px solid #eee;
  padding-bottom: 5px;
}
.grade-row label {
  flex: 1;
  font-weight: bold;
}
.grade-row input {
  width: 60px;
  padding: 5px;
}
.total-row {
  margin-top: 20px;
  font-size: 1.2rem;
  text-align: right;
  border-top: 2px solid #ccc;
  padding-top: 10px;
}
.btn-save {
  width: 100%;
  margin-top: 20px;
  padding: 10px;
  background: #28a745;
  color: white;
  border: none;
  font-size: 1rem;
  cursor: pointer;
}
</style>
