<script setup>
import { ref, computed, onMounted } from 'vue'
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

// Toast notification system (P9 pattern)
const toast = ref({ show: false, message: '', type: 'success' })
let toastTimer = null
const showToast = (message, type = 'success') => {
    if (toastTimer) clearTimeout(toastTimer)
    toast.value = { show: true, message, type }
    toastTimer = setTimeout(() => { toast.value.show = false }, 4000)
}

// Recursive total points calculation (mirrors GradingScaleBuilder logic)
const getNodePoints = (node) => {
    if (node.children && node.children.length > 0) {
        return node.children.reduce((sum, child) => sum + getNodePoints(child), 0)
    }
    return parseFloat(node.points) || 0
}

const totalPoints = computed(() => {
    return gradingStructure.value.reduce((sum, node) => sum + getNodePoints(node), 0)
})

const isValidTotal = computed(() => totalPoints.value === 20)

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
        showToast("Erreur chargement examen", 'error')
    } finally {
        loading.value = false
    }
}

const saveScale = async () => {
    // Validate total = 20 before saving
    if (!isValidTotal.value) {
        showToast(`Le total du barème doit être exactement 20 points (actuellement ${totalPoints.value} pts)`, 'error')
        return
    }
    saving.value = true
    try {
        await api.patch(`/exams/${examId}/`, {
            grading_structure: gradingStructure.value
        })
        showToast("Barème sauvegardé avec succès")
        setTimeout(() => router.back(), 1000)
    } catch (e) {
        console.error("Failed to save", e)
        showToast(e.response?.data?.error || "Erreur lors de la sauvegarde", 'error')
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
        Définissez la structure de notation. Le total doit être exactement <strong>20 points</strong>.
      </div>

      <!-- Total validation indicator -->
      <div
        class="total-indicator"
        :class="{ 'total-valid': isValidTotal, 'total-invalid': !isValidTotal }"
      >
        Total : <strong>{{ totalPoints }}</strong> / 20 pts
        <span v-if="isValidTotal" class="check-icon">✓</span>
        <span v-else class="warning-icon">⚠ Le total doit être 20</span>
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
          :disabled="saving || !isValidTotal"
          @click="saveScale"
        >
          {{ saving ? 'Enregistrement...' : 'Valider le Barème' }}
        </button>
      </div>
    </div>

    <!-- Toast Notification -->
    <Transition name="toast">
      <div 
        v-if="toast.show" 
        class="toast-notification"
        :class="'toast-' + toast.type"
        @click="toast.show = false"
      >
        {{ toast.message }}
      </div>
    </Transition>
  </div>
</template>

<style scoped>
.marking-scheme-view { padding: 2rem; max-width: 900px; margin: 0 auto; font-family: 'Inter', sans-serif; background: #f8fafc; min-height: 100vh; }
.view-header { display: flex; align-items: center; gap: 2rem; margin-bottom: 2rem; }
.btn-back { background: none; border: none; color: #64748b; font-weight: 500; cursor: pointer; }
.editor-container { background: white; padding: 2rem; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }
.info-banner { background: #e0e7ff; color: #3730a3; padding: 1rem; border-radius: 6px; margin-bottom: 1rem; font-size: 0.9rem; }
.total-indicator { padding: 0.75rem 1rem; border-radius: 6px; font-size: 1rem; margin-bottom: 1.5rem; display: flex; align-items: center; gap: 0.5rem; font-weight: 500; }
.total-valid { background: #ecfdf5; color: #065f46; border: 1px solid #a7f3d0; }
.total-invalid { background: #fef2f2; color: #991b1b; border: 1px solid #fecaca; }
.check-icon { color: #059669; font-size: 1.2rem; }
.warning-icon { font-size: 0.85rem; font-weight: 400; }
.actions-footer { margin-top: 3rem; border-top: 1px solid #e2e8f0; padding-top: 2rem; display: flex; justify-content: flex-end; gap: 1rem; }
.btn { padding: 0.75rem 1.5rem; border-radius: 6px; font-weight: 600; cursor: pointer; border: none; transition: opacity 0.2s; }
.btn:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-primary { background: #3b82f6; color: white; }
.btn-secondary { background: #f1f5f9; color: #475569; }
.loading { text-align: center; padding: 4rem; color: #94a3b8; }

/* Toast Notification */
.toast-notification {
  position: fixed;
  top: 1.5rem;
  right: 1.5rem;
  padding: 1rem 1.5rem;
  border-radius: 8px;
  font-weight: 500;
  cursor: pointer;
  z-index: 9999;
  box-shadow: 0 4px 12px rgba(0,0,0,0.15);
  max-width: 400px;
}
.toast-success { background: #ecfdf5; color: #065f46; border: 1px solid #a7f3d0; }
.toast-error { background: #fef2f2; color: #991b1b; border: 1px solid #fecaca; }
.toast-enter-active { transition: all 0.3s ease; }
.toast-leave-active { transition: all 0.3s ease; }
.toast-enter-from { opacity: 0; transform: translateY(-20px); }
.toast-leave-to { opacity: 0; transform: translateX(20px); }
</style>
