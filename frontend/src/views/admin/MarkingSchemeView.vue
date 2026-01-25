<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import api from '../../services/api'
import GradingScaleBuilder from '../../components/GradingScaleBuilder.vue'

const route = useRoute()
const router = useRouter()
const examId = route.params.examId

const loading = ref(true)
const saving = ref(false)
const exam = ref(null)
const gradingStructure = ref([])

const fetchExam = async () => {
    try {
        const res = await api.get(`/exams/${examId}/`)
        exam.value = res.data
        // Initialize structure from DB or default
        gradingStructure.value = res.data.grading_structure && res.data.grading_structure.length > 0
            ? res.data.grading_structure
            : [
                {
                    id: '1',
                    label: 'Exercice 1',
                    points: 5,
                    points_backup: 5,
                    children: []
                }
            ]
    } catch (e) {
        console.error("Failed to fetch exam", e)
        alert("Erreur chargement examen")
    } finally {
        loading.value = false
    }
}

const saveScale = async () => {
    saving.value = true
    try {
        await api.patch(`/exams/${examId}/`, {
            grading_structure: gradingStructure.value
        })
        alert("Barème sauvegardé avec succès")
        router.back() // Go back to dashboard
    } catch (e) {
        console.error("Failed to save", e)
        alert("Erreur lors de la sauvegarde")
    } finally {
        saving.value = false
    }
}

onMounted(() => {
    fetchExam()
})
</script>

<template>
  <div class="marking-scheme-view">
    <header class="view-header">
      <button
        class="btn-back"
        @click="router.back()"
      >
        ← Retour
      </button>
      <h2>Éditeur de Barème : {{ exam?.name }}</h2>
    </header>

    <div
      v-if="loading"
      class="loading"
    >
      Chargement...
    </div>

    <div
      v-else
      class="editor-container"
    >
      <div class="info-banner">
        Définissez la structure de notation. Les sous-questions divisent automatiquement les points des parents.
      </div>
      
      <GradingScaleBuilder v-model="gradingStructure" />

      <div class="actions-footer">
        <button
          class="btn btn-secondary"
          @click="router.back()"
        >
          Annuler
        </button>
        <button
          class="btn btn-primary"
          :disabled="saving"
          @click="saveScale"
        >
          {{ saving ? 'Enregistrement...' : 'Valider le Barème' }}
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.marking-scheme-view { padding: 2rem; max-width: 900px; margin: 0 auto; font-family: 'Inter', sans-serif; background: #f8fafc; min-height: 100vh; }
.view-header { display: flex; align-items: center; gap: 2rem; margin-bottom: 2rem; }
.btn-back { background: none; border: none; color: #64748b; font-weight: 500; cursor: pointer; }
.editor-container { background: white; padding: 2rem; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }
.info-banner { background: #e0e7ff; color: #3730a3; padding: 1rem; border-radius: 6px; margin-bottom: 2rem; font-size: 0.9rem; }
.actions-footer { margin-top: 3rem; border-top: 1px solid #e2e8f0; padding-top: 2rem; display: flex; justify-content: flex-end; gap: 1rem; }
.btn { padding: 0.75rem 1.5rem; border-radius: 6px; font-weight: 600; cursor: pointer; border: none; }
.btn-primary { background: #3b82f6; color: white; }
.btn-secondary { background: #f1f5f9; color: #475569; }
.loading { text-align: center; padding: 4rem; color: #94a3b8; }
</style>
