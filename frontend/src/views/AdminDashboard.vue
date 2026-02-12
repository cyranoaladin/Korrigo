<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import api from '../services/api'
import ExamUploadModal from '../components/ExamUploadModal.vue'
import UploadAnalyticsDashboard from '../components/UploadAnalyticsDashboard.vue'

const authStore = useAuthStore()
const router = useRouter()
const exams = ref([])
const loading = ref(true)

// P9 FIX: Toast notification system (replaces native alert())
const toast = ref({ show: false, message: '', type: 'success' })
let toastTimer = null
const showToast = (message, type = 'success') => {
    if (toastTimer) clearTimeout(toastTimer)
    toast.value = { show: true, message, type }
    toastTimer = setTimeout(() => { toast.value.show = false }, 4000)
}

const fetchExams = async () => {
    loading.value = true
    try {
        const res = await api.get('/exams/')
        // Handle pagination (DRF default) or flat list
        exams.value = Array.isArray(res.data) ? res.data : (res.data.results || [])
    } catch (e) {
        console.error("Failed to fetch exams", e)
    } finally {
        loading.value = false
    }
}

const handleLogout = async () => {
    await authStore.logout()
    router.push('/login')
}

const goToIdentification = (id) => {
    if (!id) {
        console.error("Tentative de navigation sans ID d'examen");
        return;
    }
    router.push({ name: 'IdentificationDesk', params: { examId: id } })
}

// Upload modal
const showUploadModal = ref(false)
const showAnalytics = ref(false)

const openUploadModal = () => {
    showUploadModal.value = true
}

const handleExamUploaded = async (examData) => {
    console.log('Exam uploaded:', examData)
    await fetchExams()
}

const showCreateModal = ref(false)
const newExam = ref({ name: '', date: new Date().toISOString().split('T')[0] })

const openCreateModal = () => {
    newExam.value = { name: '', date: new Date().toISOString().split('T')[0] }
    showCreateModal.value = true
}

const createExam = async () => {
    if (!newExam.value.name) return
    
    try {
        await api.post('/exams/', newExam.value)
        showToast('Examen créé avec succès')
        showCreateModal.value = false
        fetchExams()
    } catch (e) {
        console.error("Create exam failed", e)
        showToast(e.response?.data?.error || e.message, 'error')
    }
}

const teachersList = ref([])
const selectedCorrectors = ref([])
const showCorrectorModal = ref(false)
const selectedExamId = ref(null)
const selectedExamName = ref('')
const loadingTeachers = ref(false)

const showDispatchModal = ref(false)
const showDispatchResultsModal = ref(false)
const dispatchResults = ref(null)
const dispatchingExam = ref(null)
const isDispatching = ref(false)

const loadTeachers = async () => {
    loadingTeachers.value = true
    try {
        const res = await api.get('/users/', { params: { role: 'Teacher' } })
        teachersList.value = res.data
    } catch (e) {
        console.error("Failed to load teachers", e)
    } finally {
        loadingTeachers.value = false
    }
}

const openCorrectorModal = async (exam) => {
    selectedExamId.value = exam.id
    selectedExamName.value = exam.name
    selectedCorrectors.value = exam.correctors || [] 
    
    showCorrectorModal.value = true
    if (teachersList.value.length === 0) {
        await loadTeachers()
    }
}

const saveCorrectors = async () => {
    try {
        await api.patch(`/exams/${selectedExamId.value}/`, {
            correctors: selectedCorrectors.value
        })
        showToast('Correcteurs assignés avec succès')
        showCorrectorModal.value = false
        fetchExams()
    } catch (e) {
        console.error("Save correctors failed", e)
        showToast("Erreur lors de l'enregistrement", 'error')
    }
}

const openDispatchModal = (exam) => {
    dispatchingExam.value = exam
    showDispatchModal.value = true
}

const confirmDispatch = async () => {
    if (!dispatchingExam.value) return
    
    isDispatching.value = true
    try {
        const res = await api.post(`/exams/${dispatchingExam.value.id}/dispatch/`)
        dispatchResults.value = res.data
        showDispatchModal.value = false
        showDispatchResultsModal.value = true
        await fetchExams()
    } catch (e) {
        console.error("Dispatch failed", e)
        const errMsg = e.response?.data?.error || e.response?.data?.detail || 'Erreur lors de la distribution'
        showToast(errMsg, 'error')
    } finally {
        isDispatching.value = false
    }
}

const canDispatch = (exam) => {
    return exam.correctors && exam.correctors.length > 0
}

// --- Subject Variant (Sujets A/B) ---
const showSubjectModal = ref(false)
const subjectExam = ref(null)
const subjectCopies = ref([])
const subjectLoading = ref(false)
const subjectSaving = ref(false)
const subjectDetecting = ref(false)

const openSubjectModal = async (exam) => {
    subjectExam.value = exam
    showSubjectModal.value = true
    subjectLoading.value = true
    try {
        const res = await api.get(`/exams/${exam.id}/bulk-subject-variant/`)
        subjectCopies.value = res.data
    } catch (e) {
        console.error('Failed to load copies for subject assignment', e)
        showToast('Erreur lors du chargement des copies', 'error')
    } finally {
        subjectLoading.value = false
    }
}

const setAllVariant = (variant) => {
    subjectCopies.value.forEach(c => { c.subject_variant = variant })
}

const clearAllVariants = () => {
    subjectCopies.value.forEach(c => { c.subject_variant = null })
}

const saveSubjectVariants = async () => {
    subjectSaving.value = true
    try {
        const assignments = {}
        subjectCopies.value.forEach(c => {
            assignments[c.id] = c.subject_variant || ''
        })
        const res = await api.post(`/exams/${subjectExam.value.id}/bulk-subject-variant/`, { assignments })
        showToast(`${res.data.updated} copie(s) mise(s) à jour`)
        showSubjectModal.value = false
    } catch (e) {
        console.error('Failed to save subject variants', e)
        showToast('Erreur lors de la sauvegarde', 'error')
    } finally {
        subjectSaving.value = false
    }
}

const autoDetectSubjects = async () => {
    subjectDetecting.value = true
    try {
        const res = await api.post(`/exams/${subjectExam.value.id}/auto-detect-subject/`, {}, { timeout: 120000 })
        const data = res.data
        // Refresh copies list with updated variants
        const refreshRes = await api.get(`/exams/${subjectExam.value.id}/bulk-subject-variant/`)
        subjectCopies.value = refreshRes.data
        showToast(`OCR termin\u00e9 : ${data.detected} d\u00e9tect\u00e9(s), ${data.failed} \u00e9chec(s)`)
    } catch (e) {
        console.error('Auto-detect failed', e)
        showToast('Erreur lors de la d\u00e9tection automatique', 'error')
    } finally {
        subjectDetecting.value = false
    }
}

const subjectStats = () => {
    const a = subjectCopies.value.filter(c => c.subject_variant === 'A').length
    const b = subjectCopies.value.filter(c => c.subject_variant === 'B').length
    const none = subjectCopies.value.length - a - b
    return { a, b, none, total: subjectCopies.value.length }
}

onMounted(() => {
    fetchExams()
})
</script>

<template>
  <div
    data-testid="admin-dashboard"
    class="admin-dashboard"
  >
    <nav class="sidebar">
      <div class="logo">
        <img
          src="/images/logo_korrigo_pmf.svg"
          alt="Korrigo PMF"
          class="sidebar-logo-img"
        >
      </div>
      <ul class="nav-links">
        <li class="active">
          Gestion Examens
        </li>
        <li 
          :class="{ active: $route.name === 'UserManagement' }"
          @click="router.push({ name: 'UserManagement' })"
        >
          Utilisateurs
        </li>
        <li 
          :class="{ active: $route.name === 'Settings' }"
          @click="router.push({ name: 'Settings' })"
        >
          Paramètres
        </li>
      </ul>
      <button
        data-testid="logout-button"
        class="logout-btn"
        @click="handleLogout"
      >
        Déconnexion
      </button>
      <div class="attribution">
        Concepteur : Aleddine BEN RHOUMA<br>Labo Maths ERT
      </div>
    </nav>
        
    <main class="content">
      <header>
        <h1 data-testid="admin-dashboard-title">
          Korrigo — Tableau de Bord Administrateur
        </h1>
        <div class="user-info">
          {{ authStore.user?.username }} (Admin)
        </div>
      </header>
            
      <section class="exam-management">
        <div class="actions-bar">
          <button
            data-testid="exams.new"
            class="btn btn-primary"
            @click="openCreateModal"
          >
            + Nouvel Examen
          </button>
          <button
            class="btn btn-outline"
            data-testid="exams.import"
            @click="openUploadModal"
          >
            Importer Examen
          </button>
        </div>
                
        <div
          v-if="loading"
          class="loading"
        >
          Chargement des examens...
        </div>
                
        <table
          v-else
          class="data-table"
          data-testid="exams.list"
        >
          <thead>
            <tr>
              <th>Nom</th>
              <th>Date</th>
              <th>État</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="exam in (exams || [])"
              :key="exam?.id"
              :data-testid="exam ? `exam.row.${exam.id}` : ''"
            >
              <td>{{ exam?.name }}</td>
              <td>{{ exam?.date }}</td>
              <td>
                <span
                  v-if="exam?.is_processed"
                  class="badge status-import"
                >Importé</span>
                <span
                  v-else
                  class="badge status-pending"
                >En création</span>
              </td>
              <td>
                <button
                  class="btn-sm"
                  @click="router.push({ name: 'StapleView', params: { examId: exam.id } })"
                >
                  Agrafer
                </button>
                <button
                  class="btn-sm"
                  @click="router.push({ name: 'MarkingSchemeView', params: { examId: exam.id } })"
                >
                  Barème
                </button>
                <button 
                  v-if="exam?.id"
                  class="btn-sm btn-action" 
                  @click="goToIdentification(exam.id)"
                >
                  Video-Coding
                </button>
                <button 
                  class="btn-sm" 
                  title="Assigner des correcteurs"
                  @click="openCorrectorModal(exam)"
                >
                  Correcteurs
                </button>
                <button 
                  class="btn-sm btn-subject"
                  title="Assigner Sujet A / Sujet B"
                  @click="openSubjectModal(exam)"
                >
                  Sujets A/B
                </button>
                <button 
                  class="btn-sm btn-dispatch"
                  :class="{ 'btn-disabled': !canDispatch(exam) }"
                  :disabled="!canDispatch(exam)"
                  :title="canDispatch(exam) ? 'Distribuer les copies' : 'Aucun correcteur assigné'"
                  @click="openDispatchModal(exam)"
                >
                  Dispatcher
                </button>
              </td>
            </tr>
            <tr v-if="exams.length === 0">
              <td
                colspan="4"
                class="empty-cell"
              >
                Aucun examen trouvé. Créez-en un ou importez des scans.
              </td>
            </tr>
          </tbody>
        </table>
      </section>
    </main>

    <!-- Create Exam Modal -->
    <div 
      v-if="showCreateModal" 
      class="modal-overlay"
    >
      <div class="modal-card">
        <h3>Nouvel Examen</h3>
        
        <div class="form-group">
          <label>Nom de l'examen</label>
          <input 
            v-model="newExam.name" 
            type="text" 
            placeholder="Ex: Bac Blanc Maths 2026" 
            class="form-input" 
            autofocus
          >
        </div>
        
        <div class="form-group">
          <label>Date</label>
          <input 
            v-model="newExam.date" 
            type="date" 
            class="form-input" 
          >
        </div>
        
        <div class="modal-actions">
          <button 
            class="btn btn-outline"
            @click="showCreateModal = false" 
          >
            Annuler
          </button>
          <button 
            class="btn btn-primary"
            @click="createExam" 
          >
            Créer
          </button>
        </div>
      </div>
    </div>

    <!-- Assign Correctors Modal -->
    <div 
      v-if="showCorrectorModal" 
      class="modal-overlay"
    >
      <div class="modal-card">
        <h3>Assigner Correcteurs</h3>
        <p class="modal-subtitle">
          Pour: {{ selectedExamName }}
        </p>
        
        <div class="form-group">
          <div v-if="loadingTeachers">
            Chargement...
          </div>
          <div 
            v-else 
            class="checkbox-list"
          >
            <label 
              v-for="teacher in teachersList" 
              :key="teacher.id" 
              class="checkbox-item"
            >
              <input 
                v-model="selectedCorrectors" 
                type="checkbox" 
                :value="teacher.id"
              >
              {{ teacher.username }} ({{ teacher.email }})
            </label>
            <div 
              v-if="teachersList.length === 0" 
              class="empty-list"
            >
              Aucun enseignant trouvé.
            </div>
          </div>
        </div>
        
        <div class="modal-actions">
          <button 
            class="btn btn-outline"
            @click="showCorrectorModal = false" 
          >
            Annuler
          </button>
          <button 
            class="btn btn-primary"
            @click="saveCorrectors" 
          >
            Enregistrer
          </button>
        </div>
      </div>
    </div>

    <!-- Dispatch Confirmation Modal -->
    <div 
      v-if="showDispatchModal" 
      class="modal-overlay"
    >
      <div class="modal-card">
        <h3>Dispatcher les Copies</h3>
        <p class="modal-subtitle">
          Pour: {{ dispatchingExam?.name }}
        </p>
        
        <div class="dispatch-info">
          <p>
            Voulez-vous distribuer les copies non assignées de cet examen aux correcteurs de manière aléatoire et équitable ?
          </p>
          <p class="warning-text">
            ⚠️ Les copies déjà assignées ne seront pas modifiées.
          </p>
        </div>
        
        <div class="modal-actions">
          <button 
            class="btn btn-outline"
            :disabled="isDispatching"
            @click="showDispatchModal = false" 
          >
            Annuler
          </button>
          <button 
            class="btn btn-primary"
            :disabled="isDispatching"
            @click="confirmDispatch" 
          >
            {{ isDispatching ? 'Distribution...' : 'Confirmer' }}
          </button>
        </div>
      </div>
    </div>

    <!-- Dispatch Results Modal -->
    <div 
      v-if="showDispatchResultsModal" 
      class="modal-overlay"
    >
      <div class="modal-card modal-card-wide">
        <h3>Distribution Terminée</h3>
        
        <div 
          v-if="dispatchResults" 
          class="dispatch-results"
        >
          <div class="result-summary">
            <div class="result-item">
              <span class="result-label">Copies assignées :</span>
              <span class="result-value">{{ dispatchResults.copies_assigned || 0 }}</span>
            </div>
            <div class="result-item">
              <span class="result-label">Nombre de correcteurs :</span>
              <span class="result-value">{{ dispatchResults.correctors_count || 0 }}</span>
            </div>
            <div 
              v-if="dispatchResults.dispatch_run_id" 
              class="result-item"
            >
              <span class="result-label">ID Distribution :</span>
              <span class="result-value result-id">{{ dispatchResults.dispatch_run_id }}</span>
            </div>
          </div>
          
          <div 
            v-if="dispatchResults.distribution" 
            class="distribution-table"
          >
            <h4>Répartition par correcteur</h4>
            <table class="mini-table">
              <thead>
                <tr>
                  <th>Correcteur</th>
                  <th>Copies assignées</th>
                </tr>
              </thead>
              <tbody>
                <tr 
                  v-for="(count, username) in dispatchResults.distribution" 
                  :key="username"
                >
                  <td>{{ username }}</td>
                  <td>{{ count }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
        
        <div class="modal-actions">
          <button 
            class="btn btn-primary"
            @click="showDispatchResultsModal = false" 
          >
            Fermer
          </button>
        </div>
      </div>
    </div>

    <!-- Subject Variant (Sujets A/B) Modal -->
    <div 
      v-if="showSubjectModal" 
      class="modal-overlay"
    >
      <div class="modal-card modal-card-wide">
        <h3>Assigner Sujets A / B</h3>
        <p class="modal-subtitle">
          Pour : {{ subjectExam?.name }}
        </p>

        <div v-if="subjectLoading" class="loading">
          Chargement des copies...
        </div>

        <template v-else>
          <!-- Bulk actions -->
          <div class="subject-bulk-actions">
            <button class="btn btn-sm btn-subject-a" @click="setAllVariant('A')">
              Tout → Sujet A
            </button>
            <button class="btn btn-sm btn-subject-b" @click="setAllVariant('B')">
              Tout → Sujet B
            </button>
            <button class="btn btn-sm btn-outline" @click="clearAllVariants">
              Réinitialiser
            </button>
            <button 
              class="btn btn-sm btn-ocr" 
              :disabled="subjectDetecting"
              @click="autoDetectSubjects"
            >
              {{ subjectDetecting ? 'Détection en cours...' : 'Auto-détecter (OCR)' }}
            </button>
            <span class="subject-stats">
              <span class="badge-a">A: {{ subjectStats().a }}</span>
              <span class="badge-b">B: {{ subjectStats().b }}</span>
              <span class="badge-none">Non assigné: {{ subjectStats().none }}</span>
            </span>
          </div>

          <!-- Copies table -->
          <div class="subject-table-wrapper">
            <table class="mini-table">
              <thead>
                <tr>
                  <th>Copie</th>
                  <th>Élève</th>
                  <th>Sujet</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="copy in subjectCopies" :key="copy.id">
                  <td>{{ copy.anonymous_id || '—' }}</td>
                  <td>{{ copy.student_name || 'Non identifié' }}</td>
                  <td>
                    <select
                      v-model="copy.subject_variant"
                      class="variant-select"
                      :class="{
                        'variant-a': copy.subject_variant === 'A',
                        'variant-b': copy.subject_variant === 'B'
                      }"
                    >
                      <option :value="null">—</option>
                      <option value="A">Sujet A</option>
                      <option value="B">Sujet B</option>
                    </select>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </template>

        <div class="modal-actions">
          <button 
            class="btn btn-outline"
            :disabled="subjectSaving"
            @click="showSubjectModal = false" 
          >
            Annuler
          </button>
          <button 
            class="btn btn-primary"
            :disabled="subjectSaving || subjectLoading"
            @click="saveSubjectVariants" 
          >
            {{ subjectSaving ? 'Sauvegarde...' : 'Sauvegarder' }}
          </button>
        </div>
      </div>
    </div>

    <!-- Exam Upload Modal -->
    <ExamUploadModal
      :show="showUploadModal"
      @close="showUploadModal = false"
      @uploaded="handleExamUploaded"
    />

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
.btn-action { background: #8b5cf6; color: white; }
.btn-action:hover { background: #7c3aed; }
.loading { padding: 2rem; text-align: center; color: #6b7280; }
.empty-cell { padding: 3rem; text-align: center; color: #9ca3af; font-style: italic; }
.admin-dashboard { display: flex; height: 100vh; font-family: 'Inter', sans-serif; }
.sidebar { width: 250px; background: #1e293b; color: white; padding: 1.5rem; display: flex; flex-direction: column; }
.logo { font-size: 1.5rem; font-weight: 800; margin-bottom: 2.5rem; color: #60a5fa; display: flex; align-items: center; gap: 0.75rem; }
.sidebar-logo-img { height: 32px; width: auto; filter: drop-shadow(0 0 8px rgba(96, 165, 250, 0.3)); }
.nav-links { list-style: none; padding: 0; flex: 1; }
.nav-links li { padding: 0.75rem 1rem; cursor: pointer; border-radius: 6px; margin-bottom: 0.5rem; color: #94a3b8; transition: all 0.2s; }
.nav-links li.active, .nav-links li:hover { background: #334155; color: white; }
.logout-btn { margin-top: 1rem; background: none; border: 1px solid #ef4444; color: #ef4444; padding: 0.5rem; border-radius: 6px; cursor: pointer; transition: all 0.2s; }
.logout-btn:hover { background: #ef4444; color: white; }
.attribution { margin-top: 1.5rem; font-size: 0.7rem; color: #475569; text-align: center; line-height: 1.4; border-top: 1px solid #334155; padding-top: 1rem; }

.content { flex: 1; background: #f1f5f9; padding: 2rem; overflow-y: auto; }
header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 2rem; }
h1 { font-size: 1.5rem; color: #0f172a; margin: 0; }
.user-info { font-weight: 500; color: #64748b; }

.actions-bar { margin-bottom: 1.5rem; display: flex; gap: 1rem; }
.btn { padding: 0.6rem 1.2rem; border-radius: 6px; border: none; font-weight: 500; cursor: pointer; }
.btn-primary { background: #2563eb; color: white; }
.btn-secondary {
  background: #6b7280;
  color: white;
  border: none;
  padding: 10px 20px;
  border-radius: 6px;
  cursor: pointer;
  font-weight: 500;
  margin-left: 12px;
}
.btn-outline { background: white; border: 1px solid #cbd5e1; color: #475569; }
.btn-sm { padding: 4px 8px; font-size: 0.8rem; margin-right: 5px; cursor: pointer; }

.data-table { width: 100%; background: white; border-radius: 8px; border-collapse: collapse; box-shadow: 0 1px 3px rgba(0,0,0,0.05); }
.data-table th, .data-table td { padding: 1rem; text-align: left; border-bottom: 1px solid #e2e8f0; }
.badge { padding: 4px 8px; border-radius: 999px; font-size: 0.75rem; background: #e0e7ff; color: #3730a3; }

/* Modal Styles */
.modal-overlay { position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.5); display: flex; justify-content: center; align-items: center; z-index: 1000; }
.modal-card { background: white; padding: 2rem; border-radius: 12px; width: 400px; box-shadow: 0 20px 25px -5px rgba(0,0,0,0.1); }
.modal-card h3 { margin-top: 0; margin-bottom: 1.5rem; color: #1e293b; }
.form-group { margin-bottom: 1rem; }
.form-group label { display: block; margin-bottom: 0.5rem; color: #475569; font-size: 0.9rem; }
.form-input { width: 100%; padding: 0.5rem; border: 1px solid #cbd5e1; border-radius: 4px; }
.modal-actions { display: flex; justify-content: flex-end; gap: 1rem; margin-top: 1.5rem; }

/* Checkbox List Styles */
.checkbox-list {
  max-height: 200px;
  overflow-y: auto;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  padding: 0.5rem;
}
.checkbox-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem;
  cursor: pointer;
  border-radius: 4px;
}
.checkbox-item:hover {
  background: #f1f5f9;
}
.modal-subtitle {
  color: #64748b;
  margin-top: -1rem;
  margin-bottom: 1.5rem;
  font-size: 0.9rem;
}
.empty-list {
  text-align: center;
  color: #94a3b8;
  padding: 1rem;
  font-style: italic;
}

/* Dispatch Styles */
.btn-dispatch {
  background: #10b981;
  color: white;
}
.btn-dispatch:hover:not(:disabled) {
  background: #059669;
}
.btn-disabled {
  background: #9ca3af;
  cursor: not-allowed;
  opacity: 0.6;
}

.dispatch-info {
  margin: 1rem 0;
  padding: 1rem;
  background: #f8fafc;
  border-radius: 6px;
}
.warning-text {
  color: #f59e0b;
  font-size: 0.9rem;
  margin-top: 0.5rem;
}

.dispatch-results {
  margin: 1rem 0;
}
.result-summary {
  background: #f0f9ff;
  border: 1px solid #bae6fd;
  border-radius: 6px;
  padding: 1rem;
  margin-bottom: 1.5rem;
}
.result-item {
  display: flex;
  justify-content: space-between;
  padding: 0.5rem 0;
  border-bottom: 1px solid #e0f2fe;
}
.result-item:last-child {
  border-bottom: none;
}
.result-label {
  font-weight: 500;
  color: #475569;
}
.result-value {
  font-weight: 600;
  color: #0f172a;
}
.result-id {
  font-family: monospace;
  font-size: 0.85rem;
  color: #64748b;
}

.distribution-table {
  margin-top: 1rem;
}
.distribution-table h4 {
  margin-bottom: 0.75rem;
  color: #334155;
  font-size: 1rem;
}
.mini-table {
  width: 100%;
  border-collapse: collapse;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  overflow: hidden;
}
.mini-table th {
  background: #f1f5f9;
  padding: 0.75rem;
  text-align: left;
  font-size: 0.9rem;
  color: #475569;
  border-bottom: 2px solid #cbd5e1;
}
.mini-table td {
  padding: 0.75rem;
  border-bottom: 1px solid #e2e8f0;
}
.mini-table tbody tr:last-child td {
  border-bottom: none;
}
.mini-table tbody tr:hover {
  background: #f8fafc;
}

.modal-card-wide {
  width: 600px;
  max-width: 90vw;
}

/* Toast Notification */
.toast-notification {
  position: fixed;
  top: 1.5rem;
  right: 1.5rem;
  padding: 0.75rem 1.5rem;
  border-radius: 8px;
  font-weight: 500;
  font-size: 0.9rem;
  z-index: 2000;
  cursor: pointer;
  box-shadow: 0 4px 12px rgba(0,0,0,0.15);
  max-width: 400px;
}
.toast-success {
  background: #ecfdf5;
  color: #065f46;
  border: 1px solid #a7f3d0;
}
.toast-error {
  background: #fef2f2;
  color: #991b1b;
  border: 1px solid #fecaca;
}
.toast-enter-active { transition: all 0.3s ease; }
.toast-leave-active { transition: all 0.3s ease; }
.toast-enter-from { opacity: 0; transform: translateY(-20px); }
.toast-leave-to { opacity: 0; transform: translateX(20px); }

/* Subject Variant Modal */
.btn-subject { background: #8b5cf6; color: white; }
.btn-subject:hover { background: #7c3aed; }
.subject-bulk-actions { display: flex; gap: 0.5rem; align-items: center; flex-wrap: wrap; margin-bottom: 1rem; }
.btn-subject-a { background: #3b82f6; color: white; border: none; padding: 4px 10px; border-radius: 4px; cursor: pointer; font-size: 0.8rem; }
.btn-subject-b { background: #10b981; color: white; border: none; padding: 4px 10px; border-radius: 4px; cursor: pointer; font-size: 0.8rem; }
.subject-stats { margin-left: auto; display: flex; gap: 0.75rem; font-size: 0.8rem; font-weight: 600; }
.badge-a { color: #3b82f6; }
.badge-b { color: #10b981; }
.badge-none { color: #9ca3af; }
.subject-table-wrapper { max-height: 400px; overflow-y: auto; border: 1px solid #e2e8f0; border-radius: 6px; }
.variant-select { padding: 4px 8px; border: 1px solid #cbd5e1; border-radius: 4px; font-size: 0.85rem; cursor: pointer; min-width: 100px; }
.variant-a { background: #eff6ff; border-color: #3b82f6; color: #1d4ed8; font-weight: 600; }
.variant-b { background: #ecfdf5; border-color: #10b981; color: #065f46; font-weight: 600; }
.btn-ocr { background: #f59e0b; color: white; border: none; padding: 4px 10px; border-radius: 4px; cursor: pointer; font-size: 0.8rem; }
.btn-ocr:hover:not(:disabled) { background: #d97706; }
.btn-ocr:disabled { opacity: 0.6; cursor: wait; }
</style>
