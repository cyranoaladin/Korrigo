<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '../../stores/auth'
import api from '../../services/api'
import gradingApi from '../../services/gradingApi'
import AppIcon from '../../icons/AppIcon.vue'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

const studentId = computed(() => route.params.studentId)
const student = ref(null)
const copies = ref([])
const isLoading = ref(true)
const error = ref(null)
const selectedCopyIndex = ref(0)
const showCorrectionModal = ref(false)
const correctionReason = ref('')
const correctionScores = ref({})
const isCorrecting = ref(false)
const correctionError = ref(null)

const fetchBilan = async () => {
    isLoading.value = true
    error.value = null
    try {
        const params = {}
        if (route.query.exam_id) {
            params.exam_id = route.query.exam_id
        } else if (route.query.exam_type_id) {
            params.exam_type_id = route.query.exam_type_id
        }
        const response = await api.get(`/grading/students/${studentId.value}/bilan/`, { params })
        student.value = response.data.student
        copies.value = response.data.copies || []
    } catch (err) {
        console.error('Failed to fetch bilan', err)
        error.value = err.response?.data?.error || 'Erreur lors du chargement du bilan.'
    } finally {
        isLoading.value = false
    }
}

const selectedCopy = computed(() => copies.value[selectedCopyIndex.value] || null)

const totalScore = computed(() => {
    if (!selectedCopy.value?.scores_data) return null
    return Object.values(selectedCopy.value.scores_data).reduce((sum, v) => sum + (v || 0), 0)
})

const questionLabels = computed(() => selectedCopy.value?.question_labels || {})

const qLabel = (qid) => questionLabels.value[qid] || qid

const sortedScores = computed(() => {
    if (!selectedCopy.value?.scores_data) return []
    const entries = Object.entries(selectedCopy.value.scores_data)
    // Sort by label order from grading_structure (key order preserved by backend)
    const labelKeys = Object.keys(questionLabels.value)
    return entries.sort((a, b) => {
        const idxA = labelKeys.indexOf(a[0])
        const idxB = labelKeys.indexOf(b[0])
        if (idxA !== -1 && idxB !== -1) return idxA - idxB
        if (idxA !== -1) return -1
        if (idxB !== -1) return 1
        return a[0].localeCompare(b[0])
    })
})

const goBack = () => {
    router.push({
        path: '/corrector/my-students',
        query: route.query,
    })
}

const goToDashboard = () => {
    router.push('/corrector-dashboard')
}

const handleLogout = async () => {
    await authStore.logout()
    router.push('/')
}

const openPdf = () => {
    // Priorité au pdf_source_url (nouveau PDF source remplacé)
    const pdfUrl = selectedCopy.value?.pdf_source_url || selectedCopy.value?.pdf_url
    if (pdfUrl) {
        window.open(gradingApi.resolveUrl(pdfUrl), '_blank')
    }
}

const getStatusClass = (status) => status?.toLowerCase() || 'unknown'

const getStatusLabel = (status) => {
    const labels = { 'READY': 'Prêt', 'IN_PROGRESS': 'En cours', 'FINALIZED': 'Finalisée' }
    return labels[status] || status
}

const openCorrectionModal = () => {
  if (!selectedCopy.value || selectedCopy.value.status !== 'FINALIZED') return
  correctionReason.value = ''
  correctionScores.value = { ...(selectedCopy.value.scores_data || {}) }
  correctionError.value = null
  showCorrectionModal.value = true
}

const closeCorrectionModal = () => {
  showCorrectionModal.value = false
  correctionReason.value = ''
  correctionScores.value = {}
  correctionError.value = null
}

const submitCorrection = async () => {
  if (!correctionReason.value.trim()) {
    correctionError.value = 'La justification est obligatoire.'
    return
  }

  isCorrecting.value = true
  correctionError.value = null
  try {
    await api.post(`/grading/copies/${selectedCopy.value.copy_id}/score-correction/`, {
      scores_data: correctionScores.value,
      final_comment: selectedCopy.value.final_comment || '',
      reason: correctionReason.value.trim(),
    })
    closeCorrectionModal()
    await fetchBilan() // Refresh data
  } catch (err) {
    console.error('Correction failed', err)
    correctionError.value = err.response?.data?.detail || 'Erreur lors de la correction.'
  } finally {
    isCorrecting.value = false
  }
}

const canCorrectCopy = computed(() => {
  if (!selectedCopy.value) return false
  if (selectedCopy.value.status !== 'FINALIZED') return false
  const user = authStore.user
  if (!user) return false
  // Admin can always correct
  if (user.is_superuser || user.groups?.some(g => g.name === 'ADMIN')) return true
  // Assigned corrector can correct
  if (selectedCopy.value.assigned_corrector_id === user.id) return true
  return false
})

onMounted(fetchBilan)
</script>

<template>
  <div class="student-bilan-page">
    <header class="top-nav">
      <div class="brand">
        <button class="btn-back" @click="goBack"><AppIcon name="arrow-left" :size="14" class="inline" /> Mes Élèves</button>
        <span class="separator">|</span>
        <button class="btn-back" @click="goToDashboard">Dashboard</button>
      </div>
      <div class="user-menu">
        <span>{{ authStore.user?.username }}</span>
        <button class="btn-logout" @click="handleLogout">Déconnexion</button>
      </div>
    </header>

    <main class="container">
      <div v-if="isLoading" class="loading">Chargement du bilan...</div>

      <div v-else-if="error" class="error-message">{{ error }}</div>

      <template v-else-if="student">
        <!-- Student Header -->
        <div class="student-header">
          <div class="student-identity">
            <h1>{{ student.last_name }} {{ student.first_name }}</h1>
            <div class="student-meta">
              <span class="class-badge">{{ student.class_name }}</span>
              <span class="groupe-badge">Groupe {{ student.groupe }}</span>
              <span class="email">{{ student.email }}</span>
            </div>
          </div>
          <div v-if="selectedCopy" class="score-display">
            <div class="score-value" :class="{ graded: selectedCopy.status === 'FINALIZED' }">
              {{ totalScore !== null ? totalScore.toFixed(2) : '—' }}
            </div>
            <div class="score-label">/ 20</div>
          </div>
        </div>

        <!-- Copy Selector (if multiple exams) -->
        <div v-if="copies.length > 1" class="copy-selector">
          <button
            v-for="(copy, idx) in copies"
            :key="copy.copy_id"
            :class="['tab-btn', { active: selectedCopyIndex === idx }]"
            @click="selectedCopyIndex = idx"
          >
            {{ copy.exam_name }}
          </button>
        </div>

        <!-- Copy Details -->
        <div v-if="selectedCopy" class="bilan-content">
          <!-- Status & Actions -->
          <div class="status-bar">
            <span :class="['status-badge', getStatusClass(selectedCopy.status)]">
              {{ getStatusLabel(selectedCopy.status) }}
            </span>
            <span class="anon-id">Anonymat: {{ selectedCopy.anonymous_id }}</span>
            <span v-if="selectedCopy.pdf_regeneration_pending" class="pdf-regenerating-badge">
              <AppIcon name="loader" :size="14" class="inline spin" /> PDF en régénération
            </span>
            <button
              v-if="selectedCopy.pdf_url && !selectedCopy.pdf_regeneration_pending"
              class="btn-pdf"
              @click="openPdf"
            >
              <AppIcon name="document" :size="16" class="inline" /> Voir le PDF corrigé
            </button>
            <button
              v-if="canCorrectCopy"
              class="btn-correct"
              @click="openCorrectionModal"
            >
              <AppIcon name="edit" :size="16" class="inline" /> Corriger la note
            </button>
          </div>

          <!-- Scores par question -->
          <section class="bilan-section">
            <h2><AppIcon name="stats" :size="18" class="inline" /> Notes par Question</h2>
            <div v-if="sortedScores.length" class="scores-grid">
              <div
                v-for="[qid, score] in sortedScores"
                :key="qid"
                class="score-item"
              >
                <span class="question-id">{{ qLabel(qid) }}</span>
                <span class="question-score">{{ typeof score === 'number' ? score.toFixed(2) : score }}</span>
              </div>
            </div>
            <div v-else class="empty-section">{{ selectedCopy.status === "FINALIZED" ? "Aucune note enregistrée." : "Données non disponibles — copie en cours de correction." }}</div>
          </section>

          <!-- Remarques par question -->
          <section class="bilan-section">
            <h2><AppIcon name="message" :size="18" class="inline" /> Remarques par Question</h2>
            <div v-if="Object.keys(selectedCopy.remarks || {}).length" class="remarks-list">
              <div
                v-for="(remark, qid) in selectedCopy.remarks"
                :key="qid"
                class="remark-item"
              >
                <span class="question-label">{{ qLabel(qid) }}:</span>
                <span class="remark-text">{{ remark }}</span>
              </div>
            </div>
            <div v-else class="empty-section">{{ selectedCopy.status === "FINALIZED" ? "Aucune remarque." : "Données non disponibles — copie en cours de correction." }}</div>
          </section>

          <!-- Annotations -->
          <section class="bilan-section">
            <h2><AppIcon name="teacher-pen" :size="18" class="inline" /> Annotations sur la Copie</h2>
            <div v-if="selectedCopy.annotations?.length" class="annotations-list">
              <div
                v-for="ann in selectedCopy.annotations"
                :key="ann.id"
                class="annotation-item"
              >
                <span class="ann-page">Page {{ ann.page_index + 1 }}</span>
                <span :class="['ann-type', ann.type?.toLowerCase()]">{{ ann.type }}</span>
                <span class="ann-content">{{ ann.content }}</span>
              </div>
            </div>
            <div v-else class="empty-section">{{ selectedCopy.status === "FINALIZED" ? "Aucune annotation." : "Données non disponibles — copie en cours de correction." }}</div>
          </section>

          <!-- Appréciation globale -->
          <section class="bilan-section">
            <h2><AppIcon name="comment" :size="18" class="inline" /> Appréciation Globale</h2>
            <div v-if="selectedCopy.global_appreciation" class="appreciation-box">
              {{ selectedCopy.global_appreciation }}
            </div>
            <div v-else class="empty-section">{{ selectedCopy.status === "FINALIZED" ? "Aucune appréciation." : "Données non disponibles — copie en cours de correction." }}</div>
          </section>

          <!-- Commentaire final -->
          <section v-if="selectedCopy.status === 'FINALIZED' && selectedCopy.final_comment" class="bilan-section">
            <h2><AppIcon name="questionnaire" :size="18" class="inline" /> Commentaire Final</h2>
            <div class="final-comment-box">
              {{ selectedCopy.final_comment }}
            </div>
          </section>
        </div>

        <div v-else class="empty-state">
          Aucune copie trouvée pour cet élève.
        </div>
      </template>

      <!-- Score Correction Modal -->
      <div v-if="showCorrectionModal" class="modal-overlay" @click.self="closeCorrectionModal">
        <div class="modal-content">
          <div class="modal-header">
            <h3>Corriger la note</h3>
            <button class="btn-close" @click="closeCorrectionModal">×</button>
          </div>
          <div class="modal-body">
            <div class="correction-info">
              <p><strong>Copie :</strong> {{ selectedCopy?.exam_name }}</p>
              <p><strong>Note actuelle :</strong> {{ totalScore !== null ? totalScore.toFixed(2) : '—' }} / 20</p>
            </div>
            <div class="form-group">
              <label>Justification (obligatoire) *</label>
              <textarea
                v-model="correctionReason"
                placeholder="Expliquez la raison de cette correction..."
                rows="3"
                class="form-textarea"
              ></textarea>
            </div>
            <div class="form-group">
              <label>Notes par question</label>
              <div class="scores-input-grid">
                <div
                  v-for="[qid, score] in sortedScores"
                  :key="qid"
                  class="score-input-item"
                >
                  <label>{{ qLabel(qid) }}</label>
                  <input
                    type="number"
                    v-model.number="correctionScores[qid]"
                    step="0.5"
                    min="0"
                    class="form-input"
                  />
                </div>
              </div>
            </div>
            <div v-if="correctionError" class="error-message">{{ correctionError }}</div>
          </div>
          <div class="modal-footer">
            <button class="btn-cancel" @click="closeCorrectionModal">Annuler</button>
            <button
              class="btn-submit"
              @click="submitCorrection"
              :disabled="isCorrecting || !correctionReason.trim()"
            >
              <AppIcon v-if="isCorrecting" name="loader" :size="16" class="inline spin" />
              {{ isCorrecting ? 'Correction...' : 'Corriger' }}
            </button>
          </div>
        </div>
      </div>
    </main>
  </div>
</template>

<style scoped>
.student-bilan-page { background: #f8fafc; min-height: 100vh; font-family: 'Inter', sans-serif; }

.top-nav { background: white; padding: 1rem 2rem; display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #e2e8f0; }
.brand { display: flex; align-items: center; gap: 0.5rem; }
.btn-back { background: none; border: none; color: #6366f1; cursor: pointer; font-size: 0.9rem; font-weight: 500; }
.btn-back:hover { text-decoration: underline; }
.separator { color: #cbd5e1; }
.user-menu { display: flex; gap: 1rem; align-items: center; font-size: 0.9rem; }
.btn-logout { border: 1px solid #ef4444; background: white; color: #ef4444; cursor: pointer; font-weight: 500; padding: 4px 8px; border-radius: 4px; }
.btn-logout:hover { background: #ef4444; color: white; }

.container { max-width: 900px; margin: 2rem auto; padding: 0 1rem; }

.loading, .error-message, .empty-state { text-align: center; padding: 3rem; color: #64748b; }
.error-message { color: #ef4444; background: #fef2f2; border-radius: 8px; }

.student-header { background: white; padding: 1.5rem; border-radius: 8px; margin-bottom: 1.5rem; display: flex; justify-content: space-between; align-items: center; box-shadow: 0 1px 3px rgba(0,0,0,0.08); }
.student-identity h1 { margin: 0 0 0.5rem 0; font-size: 1.5rem; color: #1e293b; }
.student-meta { display: flex; gap: 0.75rem; align-items: center; flex-wrap: wrap; }
.class-badge { background: #e0e7ff; color: #4338ca; padding: 2px 8px; border-radius: 4px; font-size: 0.8rem; font-weight: 600; }
.groupe-badge { background: #10b981; color: white; padding: 2px 8px; border-radius: 4px; font-size: 0.8rem; font-weight: 600; }
.email { color: #64748b; font-size: 0.85rem; }

.score-display { text-align: center; }
.score-value { font-size: 2.5rem; font-weight: 700; color: #94a3b8; }
.score-value.graded { color: #10b981; }
.score-label { font-size: 1rem; color: #64748b; }

.copy-selector { display: flex; gap: 0.5rem; margin-bottom: 1.5rem; }
.tab-btn { padding: 0.5rem 1rem; border: 1px solid #e2e8f0; background: white; border-radius: 6px; cursor: pointer; font-weight: 500; color: #64748b; }
.tab-btn.active { background: #6366f1; color: white; border-color: #6366f1; }

.status-bar { display: flex; align-items: center; gap: 1rem; margin-bottom: 1.5rem; padding: 0.75rem 1rem; background: white; border-radius: 6px; box-shadow: 0 1px 2px rgba(0,0,0,0.05); }
.status-badge { padding: 4px 10px; border-radius: 4px; font-size: 0.75rem; font-weight: 600; text-transform: uppercase; }
.status-badge.finalized { background: #dcfce7; color: #166534; }
.status-badge.ready { background: #dbeafe; color: #1d4ed8; }
.status-badge.in_progress { background: #FEF3C7; color: #92400e; }
.anon-id { color: #64748b; font-size: 0.85rem; }
.pdf-regenerating-badge { color: #f59e0b; font-size: 0.85rem; font-weight: 500; display: flex; align-items: center; gap: 0.25rem; }
.btn-pdf { margin-left: auto; background: #2563eb; color: white; border: none; padding: 6px 12px; border-radius: 6px; cursor: pointer; font-weight: 500; font-size: 0.85rem; }
.btn-pdf:hover { background: #1d4ed8; }
.btn-correct { background: #f59e0b; color: white; border: none; padding: 6px 12px; border-radius: 6px; cursor: pointer; font-weight: 500; font-size: 0.85rem; margin-left: 0.5rem; }
.btn-correct:hover { background: #d97706; }

.bilan-section { background: white; padding: 1.25rem; border-radius: 8px; margin-bottom: 1rem; box-shadow: 0 1px 2px rgba(0,0,0,0.05); }
.bilan-section h2 { margin: 0 0 1rem 0; font-size: 1rem; color: #1e293b; border-bottom: 1px solid #f1f5f9; padding-bottom: 0.5rem; }
.empty-section { color: #94a3b8; font-style: italic; font-size: 0.9rem; }

.scores-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(80px, 1fr)); gap: 0.5rem; }
.score-item { display: flex; flex-direction: column; align-items: center; padding: 0.5rem; background: #f8fafc; border-radius: 6px; border: 1px solid #e2e8f0; }
.question-id { font-size: 0.75rem; color: #64748b; font-weight: 500; }
.question-score { font-size: 1.1rem; font-weight: 700; color: #1e293b; }

.remarks-list { display: flex; flex-direction: column; gap: 0.5rem; }
.remark-item { display: flex; gap: 0.5rem; padding: 0.5rem; background: #f8fafc; border-radius: 4px; border-left: 3px solid #7F77DD; }
.question-label { font-weight: 600; color: #92400e; min-width: 50px; }
.remark-text { color: #78350f; }

.annotations-list { display: flex; flex-direction: column; gap: 0.5rem; }
.annotation-item { display: flex; gap: 0.75rem; align-items: center; padding: 0.5rem; background: #f1f5f9; border-radius: 4px; }
.ann-page { font-size: 0.75rem; color: #64748b; font-weight: 500; min-width: 60px; }
.ann-type { font-size: 0.7rem; padding: 2px 6px; border-radius: 3px; font-weight: 600; text-transform: uppercase; }
.ann-type.comment { background: #dbeafe; color: #1d4ed8; }
.ann-type.error { background: #fee2e2; color: #dc2626; }
.ann-type.highlight { background: #fef3c7; color: #d97706; }
.ann-type.bonus { background: #dcfce7; color: #16a34a; }
.ann-content { color: #334155; flex: 1; }

.appreciation-box, .final-comment-box { background: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 6px; padding: 1rem; color: #166534; line-height: 1.5; }

/* Score Correction Modal */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 1rem;
}

.modal-content {
  background: white;
  border-radius: 12px;
  width: 100%;
  max-width: 500px;
  max-height: 90vh;
  overflow-y: auto;
  box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1);
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1.25rem 1.5rem;
  border-bottom: 1px solid #e2e8f0;
}

.modal-header h3 {
  margin: 0;
  font-size: 1.25rem;
  color: #1e293b;
}

.btn-close {
  background: none;
  border: none;
  font-size: 2rem;
  color: #64748b;
  cursor: pointer;
  line-height: 1;
  padding: 0;
}

.btn-close:hover { color: #1e293b; }

.modal-body {
  padding: 1.5rem;
}

.correction-info {
  background: #f8fafc;
  padding: 1rem;
  border-radius: 8px;
  margin-bottom: 1.5rem;
}

.correction-info p {
  margin: 0.25rem 0;
  color: #334155;
  font-size: 0.9rem;
}

.form-group {
  margin-bottom: 1.5rem;
}

.form-group label {
  display: block;
  margin-bottom: 0.5rem;
  font-weight: 600;
  color: #1e293b;
  font-size: 0.9rem;
}

.form-textarea {
  width: 100%;
  padding: 0.75rem;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  font-family: 'Inter', sans-serif;
  font-size: 0.9rem;
  resize: vertical;
}

.form-textarea:focus {
  outline: none;
  border-color: #6366f1;
  box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.1);
}

.scores-input-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
  gap: 1rem;
}

.score-input-item {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.score-input-item label {
  font-size: 0.8rem;
  color: #64748b;
  font-weight: 500;
}

.form-input {
  padding: 0.5rem;
  border: 1px solid #e2e8f0;
  border-radius: 4px;
  font-size: 0.9rem;
}

.form-input:focus {
  outline: none;
  border-color: #6366f1;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 0.75rem;
  padding: 1rem 1.5rem;
  border-top: 1px solid #e2e8f0;
}

.btn-cancel {
  background: white;
  color: #64748b;
  border: 1px solid #e2e8f0;
  padding: 0.5rem 1rem;
  border-radius: 6px;
  cursor: pointer;
  font-weight: 500;
  font-size: 0.9rem;
}

.btn-cancel:hover {
  background: #f8fafc;
  color: #1e293b;
}

.btn-submit {
  background: #f59e0b;
  color: white;
  border: none;
  padding: 0.5rem 1rem;
  border-radius: 6px;
  cursor: pointer;
  font-weight: 600;
  font-size: 0.9rem;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.btn-submit:hover:not(:disabled) {
  background: #d97706;
}

.btn-submit:disabled {
  background: #cbd5e1;
  cursor: not-allowed;
}

.spin {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
</style>
