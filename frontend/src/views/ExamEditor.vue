<script setup>
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { useExamStore } from '../stores/examStore'
import GradingScaleBuilder from '../components/GradingScaleBuilder.vue'

const route = useRoute()
const examId = route.params.examId
const exam = ref(null)
const isLoading = ref(false)
const error = ref(null)
const isSaving = ref(false)
const saveMessage = ref('')

// Should be extracted to store but for MVP keeping fetch here or reuse store.
// Let's assume we can fetch exam details via the ID from API. Need an endpoint for detail.
// We only created upload list endpoint and booklet list.
// We need GET /api/exams/{id}/ detail and PATCH /api/exams/{id}/
// Since we didn't explicitly create DetailView, we might need to add it or mock it.
// Assuming we add it to backend quickly or just use list and filters if available.
// Actually `ExamUploadView` is create-only.
// Let's add `ExamDetailView` in backend/exams/views.py first or assume we have it.
// Wait, we need to implement the View logic first if it's missing.
// I'll assume standard REST behavior and add the view quickly if needed, 
// but let's implement the frontend logic assuming it exists or verify it.
// In `backend/exams/urls.py` we have:
// path('upload/', ...), path('.../booklets/'), path('.../merge/')
// We MISS `path('<uuid:pk>/', ...)` for RetrieveUpdateDestroy.

const authStore = useAuthStore()

const fetchExam = async () => {
    isLoading.value = true
    try {
        const res = await fetch(`${authStore.API_URL}/api/exams/${examId}/`, {
            credentials: 'include'
        })
        if (!res.ok) throw new Error("Impossible de récupérer l'examen")
        exam.value = await res.json()
        if (!exam.value.grading_structure) {
            exam.value.grading_structure = []
        }
    } catch (e) {
        error.value = e.message
    } finally {
        isLoading.value = false
    }
}

const saveExam = async () => {
    isSaving.value = true
    saveMessage.value = ''
    try {
        const res = await fetch(`${authStore.API_URL}/api/exams/${examId}/`, {
            method: 'PATCH',
            credentials: 'include',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                grading_structure: exam.value.grading_structure
            })
        })
        if (!res.ok) {
            const errData = await res.json()
            throw new Error(JSON.stringify(errData))
        }
        saveMessage.value = 'Sauvegarde réussie !'
        setTimeout(() => saveMessage.value = '', 3000)
    } catch (e) {
        error.value = "Erreur sauvegarde: " + e.message
    } finally {
        isSaving.value = false
    }
}

onMounted(() => {
    if (examId) fetchExam()
})
</script>

<template>
  <div class="exam-editor">
    <div v-if="isLoading">
      Chargement...
    </div>
    <div
      v-else-if="error"
      class="error"
    >
      {{ error }}
    </div>
    <div v-else-if="exam">
      <div class="header">
        <h1>Korrigo — Éditeur: {{ exam.name }}</h1>
        <div class="controls">
          <span
            v-if="saveMessage"
            class="success"
          >{{ saveMessage }}</span>
          <button
            :disabled="isSaving"
            class="btn-save"
            @click="saveExam"
          >
            {{ isSaving ? 'Sauvegarde...' : 'Enregistrer le Barème' }}
          </button>
        </div>
      </div>
        
      <div class="editor-container">
        <h2>Structure du Barème</h2>
        <p class="help-text">
          Ajoutez des exercices et des questions. Les notes doivent être numériques.
        </p>
        <GradingScaleBuilder v-model="exam.grading_structure" />
      </div>
    </div>
  </div>
</template>

<style scoped>
.exam-editor {
    padding: 20px;
    max-width: 900px;
    margin: 0 auto;
    font-family: 'Inter', sans-serif;
}
.header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-bottom: 2px solid #eee;
    padding-bottom: 20px;
    margin-bottom: 20px;
}
.error { color: red; }
.success { color: green; margin-right: 15px; font-weight: bold; }
.btn-save {
    background: #007bff;
    color: white;
    border: none;
    padding: 10px 20px;
    font-size: 1rem;
    border-radius: 5px;
    cursor: pointer;
}
.btn-save:disabled {
    background: #ccc;
}
.help-text {
    color: #666;
    margin-bottom: 15px;
}
</style>
