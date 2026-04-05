<script setup>
import { computed, ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import api from '../services/api'
import AppIcon from '../icons/AppIcon.vue'
import ExamUploadModal from '../components/ExamUploadModal.vue'
import { QUESTIONNAIRE_SECTIONS } from '../questionnaire/config'
// eslint-disable-next-line @typescript-eslint/no-unused-vars
import UploadAnalyticsDashboard from '../components/UploadAnalyticsDashboard.vue'
import JuryReportsModal from '../components/JuryReportsModal.vue'
import ExamTypeIcon from '../components/ExamTypeIcon.vue'

const authStore = useAuthStore()
const router = useRouter()
const exams = ref([])
const loading = ref(true)
const questionnaireSummary = ref({ is_available: false, responses_count: 0, total_eligible: 0 })
const questionnaireParticipants = ref({ responded: [], pending: [] })
const questionnaireResponses = ref([])
const questionnaireGeneratedBilan = ref({ status: 'missing', html: '', generated_at: null, error: '' })
const questionnaireLoading = ref(true)
const selectedQuestionnaireResponse = ref(null)

const questionnaireQuestionMeta = QUESTIONNAIRE_SECTIONS.flatMap(section =>
    (section?.questions || []).filter(q => !!q).map(question => ({
        id: question?.id,
        label: question?.label,
        sectionId: section?.id,
        sectionTitle: section?.title,
        type: question?.type
    }))
).reduce((acc, item) => {
    if (item && item.id) {
        acc[item.id] = item
    }
    return acc
}, {})

const formatAnswerValue = (value) => {
    if (Array.isArray(value)) return value.length ? value.join(', ') : '—'
    if (value === null || value === undefined || value === '') return '—'
    return value
}

const selectedResponseDetails = computed(() => {
    if (!selectedQuestionnaireResponse.value) {
        return []
    }
    return Object.entries(selectedQuestionnaireResponse.value.answers || {}).map(([key, value]) => ({
        key,
        label: questionnaireQuestionMeta[key]?.label || key,
        sectionId: questionnaireQuestionMeta[key]?.sectionId || 'other',
        sectionTitle: questionnaireQuestionMeta[key]?.sectionTitle || 'Autres réponses',
        type: questionnaireQuestionMeta[key]?.type || 'text',
        value: formatAnswerValue(value)
    }))
})

const selectedResponseSections = computed(() => {
    const grouped = selectedResponseDetails.value.reduce((acc, item) => {
        const existing = acc[item.sectionId] || {
            id: item.sectionId,
            title: item.sectionTitle,
            items: []
        }
        existing.items.push(item)
        acc[item.sectionId] = existing
        return acc
    }, {})

    const orderedSections = QUESTIONNAIRE_SECTIONS
        .map(section => grouped[section.id])
        .filter(Boolean)

    if (grouped.other) {
        orderedSections.push(grouped.other)
    }

    return orderedSections
})

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

const examsByType = computed(() => {
  const groups = {}
  const others = []
  
  ;(exams.value || []).forEach(exam => {
    if (!exam || typeof exam !== 'object') return // Robust filter
    
    const typeDetails = exam.exam_type_details
    if (typeDetails && (typeDetails.id || exam.exam_type)) {
      const typeId = typeDetails.id || exam.exam_type
      if (!groups[typeId]) {
         groups[typeId] = {
            details: {
                name: typeDetails?.name || 'Inconnu',
                icon: typeDetails?.icon || 'exam-folder',
                color: typeDetails?.color || '#64748b',
                id: typeId
            },
            exams: []
         }
      }
      groups[typeId].exams.push(exam)
    } else {
      others.push(exam)
    }
  })
  
  const result = Object.values(groups)
  if (others.length > 0) {
     result.push({
        details: { name: 'Autres Examens', icon: 'exam-folder', color: '#64748b' },
        exams: others
     })
  }
  return result
})

const fetchQuestionnaireBilanStatus = async () => {
    questionnaireLoading.value = true
    try {
        const res = await api.get('/grading/questionnaire/bilan/')
        questionnaireSummary.value = res.data.summary || questionnaireSummary.value
        questionnaireParticipants.value = res.data.participants || questionnaireParticipants.value
        questionnaireResponses.value = res.data.responses || []
        questionnaireGeneratedBilan.value = res.data.generated_bilan || questionnaireGeneratedBilan.value
        if (questionnaireResponses.value.length && !selectedQuestionnaireResponse.value) {
            selectedQuestionnaireResponse.value = questionnaireResponses.value[0]
        }
    } catch (e) {
        console.error("DEBUG [AdminDashboard]: Failed to fetch questionnaire bilan status", {
            error: e,
            status: e.response?.status,
            data: e.response?.data
        })
    } finally {
        questionnaireLoading.value = false
    }
}

const formatDate = (value) => {
    if (!value) return '—'
    return new Date(value).toLocaleString('fr-FR')
}

const openQuestionnaireBilan = () => {
    router.push({ name: 'QuestionnaireBilan' })
}

const handleLogout = async () => {
    await authStore.logout()
    router.push('/')
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
const showAnalytics = ref(false) // eslint-disable-line @typescript-eslint/no-unused-vars
const showJuryReportsModal = ref(false)

const openUploadModal = () => {
    showUploadModal.value = true
}

const openJuryReportsModal = () => {
    showJuryReportsModal.value = true
}

const handleExamUploaded = async (examData) => {
    console.log('Exam uploaded:', examData)
    await fetchExams()
}

const showCreateModal = ref(false)
const newExam = ref({ name: '', date: new Date().toISOString().split('T')[0], exam_type: '' })
const examTypes = ref([])

const fetchExamTypes = async () => {
    try {
        const response = await api.get('/exams/types/')
        examTypes.value = Array.isArray(response.data)
            ? response.data
            : (response.data.results || [])
    } catch (err) {
        console.error("DEBUG [AdminDashboard]: Failed to fetch exam types", {
            error: err,
            status: err.response?.status,
            data: err.response?.data
        })
        showToast('Erreur lors du chargement des rubriques', 'error')
    }
}

const openCreateModal = () => {
    newExam.value = { name: '', date: new Date().toISOString().split('T')[0], exam_type: '' }
    showCreateModal.value = true
}

const createExam = async () => {
    if (!newExam.value.name || !newExam.value.exam_type) return

    try {
        // Préparer les données: convertir les chaînes vides en null pour les champs optionnels
        const payload = {
            ...newExam.value,
            exam_type: newExam.value.exam_type || null,
        }
        await api.post('/exams/', payload)
        showToast('Examen créé avec succès')
        showCreateModal.value = false
        newExam.value = { name: '', date: new Date().toISOString().split('T')[0], exam_type: '' }
        await fetchExams()
    } catch (e) {
        console.error("Create exam failed", e, "Response data:", e.response?.data)
        // Afficher le détail de l'erreur de validation
        const errorData = e.response?.data
        let errorMsg = 'Erreur lors de la création'
        if (errorData) {
            if (typeof errorData === 'string') {
                errorMsg = errorData
            } else if (errorData.error) {
                errorMsg = errorData.error
            } else if (errorData.detail) {
                errorMsg = errorData.detail
            } else {
                // Extraire les erreurs de validation DRF
                const errors = Object.entries(errorData)
                    .map(([field, msgs]) => `${field}: ${Array.isArray(msgs) ? msgs.join(', ') : msgs}`)
                    .join(' | ')
                errorMsg = errors || JSON.stringify(errorData)
            }
        }
        showToast(errorMsg, 'error')
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


onMounted(() => {
    fetchExamTypes()
    fetchExams()
    fetchQuestionnaireBilanStatus()
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
        <li :class="{ active: $route.name === 'AdminDashboard' }" class="nav-item">
          <AppIcon name="dashboard" :size="18" />
          <span>Gestion Examens</span>
        </li>
        <li 
          :class="{ active: $route.name === 'UserManagement' }"
          class="nav-item"
          @click="router.push({ name: 'UserManagement' })"
        >
          <AppIcon name="users" :size="18" />
          <span>Utilisateurs</span>
        </li>
        <li 
          :class="{ active: $route.name === 'Settings' }"
          class="nav-item"
          @click="router.push({ name: 'Settings' })"
        >
          <AppIcon name="settings" :size="18" />
          <span>Paramètres</span>
        </li>
        <li 
          v-if="questionnaireSummary.is_available"
          :class="{ active: $route.name === 'QuestionnaireBilan' }"
          class="nav-item"
          @click="router.push({ name: 'QuestionnaireBilan' })"
        >
          <AppIcon name="chart" :size="18" />
          <span>Bilan Questionnaire</span>
        </li>
      </ul>
      <button
        data-testid="logout-button"
        class="logout-btn"
        @click="handleLogout"
      >
        <AppIcon name="logout" :size="18" />
        <span>Déconnexion</span>
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
            class="btn btn-primary btn-with-icon"
            @click="openCreateModal"
          >
            <AppIcon name="plus" :size="18" />
            <span>Nouvel Examen</span>
          </button>
          <button
            class="btn btn-outline btn-with-icon"
            data-testid="exams.import"
            @click="openUploadModal"
          >
            <AppIcon name="upload" :size="18" />
            <span>Importer Examen</span>
          </button>
          <button
            class="btn btn-outline btn-with-icon"
            @click="openJuryReportsModal"
          >
            <AppIcon name="book-check" :size="18" />
            <span>Rapports de Jury</span>
          </button>
          <button
            class="btn btn-outline btn-with-icon"
            @click="openQuestionnaireBilan"
          >
            <AppIcon name="questionnaire" :size="18" />
            <span>Questionnaire Correcteurs</span>
          </button>
        </div>

        <section class="questionnaire-panel">
          <div class="section-title-row">
            <div>
              <h2>Suivi Questionnaire Correcteurs</h2>
              <p>
                {{ questionnaireSummary.responses_count }} réponse(s) sur {{ questionnaireSummary.total_eligible }} correcteur(s)
              </p>
            </div>
            <div class="questionnaire-actions">
              <button
                class="btn btn-outline btn-with-icon"
                @click="fetchQuestionnaireBilanStatus"
              >
                <AppIcon name="refresh" :size="16" />
                <span>Actualiser</span>
              </button>
              <button
                class="btn btn-primary btn-with-icon"
                @click="openQuestionnaireBilan"
              >
                <AppIcon name="eye" :size="16" />
                <span>Ouvrir la vue bilan</span>
              </button>
            </div>
          </div>

          <div v-if="questionnaireLoading" class="loading">
            Chargement du questionnaire...
          </div>

          <template v-else>
            <div class="questionnaire-metrics">
              <div class="summary-card">
                <span class="summary-label">Participation</span>
                <strong>{{ questionnaireSummary.responses_count }} / {{ questionnaireSummary.total_eligible }}</strong>
                <span>{{ questionnaireSummary.completion_rate || 0 }} %</span>
              </div>
              <div class="summary-card">
                <span class="summary-label">Ont répondu</span>
                <strong>{{ questionnaireParticipants.responded?.length || 0 }}</strong>
                <span>correcteur(s)</span>
              </div>
              <div class="summary-card">
                <span class="summary-label">En attente</span>
                <strong>{{ questionnaireParticipants.pending?.length || 0 }}</strong>
                <span>correcteur(s)</span>
              </div>
              <div class="summary-card">
                <span class="summary-label">Bilan auto</span>
                <strong>{{ questionnaireGeneratedBilan.status || 'missing' }}</strong>
                <span>{{ formatDate(questionnaireGeneratedBilan.generated_at) }}</span>
              </div>
            </div>

            <div class="questionnaire-columns">
              <div class="questionnaire-card">
                <div class="card-title-row">
                  <h3>Correcteurs ayant répondu</h3>
                  <span>{{ questionnaireParticipants.responded?.length || 0 }}</span>
                </div>
                <div v-if="questionnaireParticipants.responded?.length" class="participant-list">
                  <div
                    v-for="item in (questionnaireParticipants.responded || []).filter(r => !!r)"
                    :key="`responded-${item?.user_id || Math.random()}`"
                    class="participant-item participant-answered"
                  >
                    <div>
                      <strong>{{ item.display_name }}</strong>
                      <span>{{ item.username }}</span>
                    </div>
                    <small>{{ formatDate(item.submitted_at) }}</small>
                  </div>
                </div>
                <div v-else class="empty-inline">
                  Aucune réponse enregistrée.
                </div>
              </div>

              <div class="questionnaire-card">
                <div class="card-title-row">
                  <h3>Correcteurs n’ayant pas répondu</h3>
                  <span>{{ questionnaireParticipants.pending?.length || 0 }}</span>
                </div>
                <div v-if="questionnaireParticipants.pending?.length" class="participant-list">
                  <div
                    v-for="item in (questionnaireParticipants.pending || []).filter(r => !!r)"
                    :key="`pending-${item?.user_id || Math.random()}`"
                    class="participant-item participant-pending"
                  >
                    <div>
                      <strong>{{ item.display_name }}</strong>
                      <span>{{ item.username }}</span>
                    </div>
                    <small>{{ item.email || '—' }}</small>
                  </div>
                </div>
                <div v-else class="empty-inline">
                  Tous les correcteurs ont répondu.
                </div>
              </div>
            </div>

            <div class="questionnaire-columns questionnaire-columns-stacked">
              <div class="questionnaire-card questionnaire-card-large">
                <div class="card-title-row">
                  <h3>Réponses déjà soumises</h3>
                  <span>{{ questionnaireResponses.length }}</span>
                </div>
                <div v-if="questionnaireResponses.length" class="response-master-detail">
                  <div class="response-list">
                    <button
                      v-for="item in questionnaireResponses"
                      :key="`${item.user_id}-${item.submitted_at}`"
                      class="response-list-item"
                      :class="{ active: selectedQuestionnaireResponse?.user_id === item.user_id }"
                      @click="selectedQuestionnaireResponse = item"
                    >
                      <strong>{{ item.display_name }}</strong>
                      <span>{{ item.username }}</span>
                      <small>{{ formatDate(item.submitted_at) }}</small>
                    </button>
                  </div>
                  <div class="response-detail" v-if="selectedQuestionnaireResponse">
                    <div class="card-title-row">
                      <h4>{{ selectedQuestionnaireResponse.display_name }}</h4>
                      <span>{{ formatDate(selectedQuestionnaireResponse.submitted_at) }}</span>
                    </div>
                    <div class="response-detail-sections">
                      <div
                        v-for="section in (selectedResponseSections || []).filter(s => !!s)"
                        :key="`${selectedQuestionnaireResponse?.user_id || 'no-user'}-${section?.id || Math.random()}`"
                        class="response-section-card"
                      >
                        <div class="response-section-header">
                          <h5>{{ section.title }}</h5>
                          <span>{{ section.items.length }} réponse(s)</span>
                        </div>
                        <div class="response-detail-grid">
                            <div
                              v-for="item in (section?.items || []).filter(i => !!i)"
                              :key="`${selectedQuestionnaireResponse?.user_id || 'no-user'}-${item?.key || Math.random()}`"
                              class="response-detail-item"
                            >
                            <span class="response-label">{{ item.label }}</span>
                            <strong class="response-value">{{ item.value }}</strong>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
                <div v-else class="empty-inline">
                  Aucune réponse détaillée disponible pour le moment.
                </div>
              </div>
            </div>

            <div class="questionnaire-card questionnaire-card-large">
              <div class="card-title-row">
                <h3>Bilan généré</h3>
                <span>{{ questionnaireGeneratedBilan.status || 'missing' }}</span>
              </div>
              <div v-if="questionnaireGeneratedBilan.status === 'ready'" class="generated-bilan-preview" v-html="questionnaireGeneratedBilan.html" />
              <div v-else-if="questionnaireGeneratedBilan.status === 'pending'" class="empty-inline">
                Le bilan automatique est en cours de génération.
              </div>
              <div v-else-if="questionnaireGeneratedBilan.status === 'error'" class="empty-inline error-inline">
                {{ questionnaireGeneratedBilan.error || 'Le bilan automatique n’a pas pu être généré pour le moment.' }}
              </div>
              <div v-else class="empty-inline">
                Le bilan automatique sera visible ici une fois généré.
              </div>
            </div>
          </template>
        </section>
                
        <div
          v-if="loading"
          class="loading"
        >
          Chargement des examens...
        </div>
                <div v-else>
          <div v-if="exams.length === 0" class="empty-state">
            Aucun examen trouvé. Créez-en un ou importez des scans.
          </div>
          
          <div v-for="group in examsByType" :key="group.details?.name || Math.random()" class="exam-group-section">
            <h3 class="exam-group-title" :style="{ borderLeftColor: group.details?.color || '#6366f1', color: group.details?.color || '#1e293b' }">
              <span class="exam-type-icon" :style="{ color: group.details?.color || '#6366f1' }">
                <ExamTypeIcon :icon="group.details?.icon" :size="18" />
              </span>
              {{ group.details?.name || 'Autres' }}
            </h3>
            
            <table class="data-table" data-testid="exams.list">
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
                  v-for="exam in (group.exams || []).filter(Boolean)"
                  :key="exam?.id"
                  :data-testid="exam ? `exam.row.${exam.id}` : ''"
                >
                  <td>{{ exam?.name }}</td>
                  <td>{{ exam?.date }}</td>
                  <td>
                    <span v-if="exam?.is_processed" class="badge status-import">Importé</span>
                    <span v-else class="badge status-pending">En création</span>
                  </td>
                  <td>
                    <button class="btn-sm" @click="exam?.id && router.push({ name: 'StapleView', params: { examId: exam.id } })">Agrafer</button>
                    <button class="btn-sm" @click="exam?.id && router.push({ name: 'MarkingSchemeView', params: { examId: exam.id } })">Barème</button>
                    <button v-if="exam?.id" class="btn-sm btn-action" @click="goToIdentification(exam.id)">Identification</button>
                    <button class="btn-sm" title="Assigner des correcteurs" @click="exam && openCorrectorModal(exam)">Correcteurs</button>
                    <button 
                      class="btn-sm btn-dispatch btn-with-icon"
                      :class="{ 'btn-disabled': !exam || !canDispatch(exam) }"
                      :disabled="!exam || !canDispatch(exam)"
                      :title="exam && canDispatch(exam) ? 'Distribuer les copies' : 'Configuration incomplète'"
                      @click="exam && openDispatchModal(exam)"
                    >
                      <AppIcon name="refresh" :size="14" />
                      <span>Distribuer</span>
                    </button>
                    <button class="btn-sm btn-students" title="Voir la liste des élèves et notes" @click="exam?.id && router.push({ name: 'ExamStudentList', params: { examId: exam.id } })">Élèves</button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
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
          <label>Nom de l'examen <span class="required">*</span></label>
          <input 
            v-model="newExam.name" 
            type="text" 
            placeholder="Ex: Bac Blanc Maths J1 2026" 
            class="form-input" 
            autofocus
          >
        </div>

        <div class="form-group">
          <label>Type d'examen (Rubrique) <span class="required">*</span></label>
          <select v-model="newExam.exam_type" class="form-input">
            <option disabled value="">-- Choisir un type --</option>
            <option v-for="t in (examTypes || []).filter(t => t && t.id)" :key="t.id" :value="t.id">
              {{ t.name }}
            </option>
          </select>
          <p v-if="!newExam.exam_type" class="field-hint">
            <AppIcon name="warning" :size="14" class="inline" />
            Sans type, l'examen sera invisible pour les correcteurs.
          </p>
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
            :disabled="!newExam.name || !newExam.exam_type"
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
          <label>Matière / Rubrique</label>
          <select v-model="newExam.exam_type" class="form-input">
            <option disabled value="">-- Choisir une matière --</option>
            <option v-for="e in (examTypes || []).filter(item => item && item.id)" :key="e.id" :value="e.id">{{ e.name }}</option>
          </select>
        </div>
        
        <div class="form-group">
          <div v-if="loadingTeachers">
            Chargement...
          </div>
          <div 
            v-else 
            class="checkbox-list"
          >
            <label 
              v-for="teacher in (teachersList || []).filter(item => !!item)" 
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
            <AppIcon name="warning" :size="14" class="inline" />
            Les copies déjà assignées ne seront pas modifiées.
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


    <!-- Exam Upload Modal -->
    <ExamUploadModal
      :show="showUploadModal"
      @close="showUploadModal = false"
      @uploaded="handleExamUploaded"
    />

    <!-- Jury Reports Modal -->
    <JuryReportsModal
      v-if="showJuryReportsModal"
      :visible="showJuryReportsModal"
      @close="showJuryReportsModal = false"
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
.nav-links li { padding: 0.75rem 1rem; cursor: pointer; border-radius: 6px; margin-bottom: 0.5rem; color: #94a3b8; transition: all 0.2s; display: flex; align-items: center; gap: 0.75rem; }
.nav-links li.active, .nav-links li:hover { background: #334155; color: white; }
.logout-btn { margin-top: 1rem; background: none; border: 1px solid #ef4444; color: #ef4444; padding: 0.5rem; border-radius: 6px; cursor: pointer; transition: all 0.2s; display: flex; align-items: center; gap: 0.75rem; justify-content: center; }
.logout-btn:hover { background: #ef4444; color: white; }
.attribution { margin-top: 1.5rem; font-size: 0.7rem; color: #475569; text-align: center; line-height: 1.4; border-top: 1px solid #334155; padding-top: 1rem; }

.content { flex: 1; background: #f1f5f9; padding: 2rem; overflow-y: auto; }
header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 2rem; }
h1 { font-size: 1.5rem; color: #0f172a; margin: 0; }
.user-info { font-weight: 500; color: #64748b; }

.questionnaire-panel {
  background: white;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 1.25rem;
  margin-bottom: 1.5rem;
}

.section-title-row {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
  align-items: flex-start;
  margin-bottom: 1rem;
}

.section-title-row h2 {
  margin: 0 0 0.25rem;
  color: #0f172a;
}

.section-title-row p {
  margin: 0;
  color: #64748b;
}

.questionnaire-actions {
  display: flex;
  gap: 0.75rem;
}

.questionnaire-metrics {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 1rem;
  margin-bottom: 1rem;
}

.summary-card {
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  padding: 1rem;
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
  background: #f8fafc;
}

.summary-card strong {
  color: #0f172a;
  font-size: 1.4rem;
}

.summary-label {
  color: #64748b;
  font-size: 0.9rem;
}

.questionnaire-columns {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 1rem;
  margin-bottom: 1rem;
}

.questionnaire-columns-stacked {
  grid-template-columns: 1fr;
}

.questionnaire-card {
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 1rem;
  background: #fff;
}

.questionnaire-card-large {
  padding: 1rem;
}

.card-title-row {
  display: flex;
  justify-content: space-between;
  gap: 0.75rem;
  align-items: center;
  margin-bottom: 0.85rem;
}

.card-title-row h3,
.card-title-row h4 {
  margin: 0;
  color: #0f172a;
}

.card-title-row span {
  color: #64748b;
  font-size: 0.9rem;
}

.participant-list {
  display: grid;
  gap: 0.75rem;
}

.participant-item {
  display: flex;
  justify-content: space-between;
  gap: 0.75rem;
  align-items: center;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  padding: 0.75rem;
}

.participant-item strong,
.response-list-item strong {
  display: block;
  color: #0f172a;
}

.participant-item span,
.response-list-item span {
  display: block;
  color: #64748b;
  font-size: 0.9rem;
}

.participant-item small,
.response-list-item small {
  color: #94a3b8;
}

.participant-answered {
  background: #f0fdf4;
}

.participant-pending {
  background: #fff7ed;
}

.empty-inline {
  color: #64748b;
  padding: 0.5rem 0;
}

.error-inline {
  color: #b91c1c;
}

.response-master-detail {
  display: grid;
  grid-template-columns: 280px 1fr;
  gap: 1rem;
}

.response-list {
  display: grid;
  gap: 0.75rem;
  max-height: 420px;
  overflow-y: auto;
}

.response-list-item {
  text-align: left;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  padding: 0.75rem;
  background: #f8fafc;
  cursor: pointer;
}

.response-list-item.active {
  border-color: #2563eb;
  background: #eff6ff;
}

.response-detail {
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  padding: 1rem;
  background: #f8fafc;
}

.response-detail-sections {
  display: grid;
  gap: 1rem;
}

.response-section-card {
  border: 1px solid #dbeafe;
  border-radius: 12px;
  background: #ffffff;
  padding: 0.9rem;
}

.response-section-header {
  display: flex;
  justify-content: space-between;
  gap: 0.75rem;
  align-items: center;
  margin-bottom: 0.75rem;
}

.response-section-header h5 {
  margin: 0;
  color: #1d4ed8;
  font-size: 1rem;
}

.response-section-header span {
  color: #64748b;
  font-size: 0.85rem;
}

.response-detail-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.75rem;
}

.response-detail-item {
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  background: white;
  padding: 0.75rem;
}

.response-label {
  display: block;
  color: #64748b;
  margin-bottom: 0.35rem;
  font-size: 0.9rem;
}

.response-value {
  color: #0f172a;
  white-space: pre-wrap;
  line-height: 1.55;
  font-weight: 600;
}

.generated-bilan-preview {
  line-height: 1.65;
}

.generated-bilan-preview :deep(h2),
.generated-bilan-preview :deep(h3) {
  color: #0f172a;
}

.generated-bilan-preview :deep(table) {
  width: 100%;
  border-collapse: collapse;
}

.generated-bilan-preview :deep(th),
.generated-bilan-preview :deep(td) {
  border: 1px solid #e2e8f0;
  padding: 0.65rem;
}

.actions-bar { margin-bottom: 1.5rem; display: flex; gap: 1rem; }
.btn { padding: 0.6rem 1.2rem; border-radius: 6px; border: none; font-weight: 500; cursor: pointer; }
.btn-with-icon { display: inline-flex; align-items: center; gap: 0.75rem; }
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

.exam-group-section {
  margin-bottom: 3rem;
  background: white;
  border-radius: 12px;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
  overflow: hidden;
}

.exam-group-title {
  margin: 0;
  padding: 1.25rem 1.5rem;
  background: #f8fafc;
  border-bottom: 1px solid #e2e8f0;
  border-left: 4px solid #6366f1;
  color: #1e293b;
  font-size: 1.1rem;
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.exam-type-icon {
  font-size: 1.25rem;
}

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
.required { color: #ef4444; margin-left: 2px; }
.field-hint { font-size: 0.8rem; color: #b45309; background: #fef3c7; padding: 4px 8px; border-radius: 4px; margin-top: 4px; margin-bottom: 0; }

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
.btn-students {
  background: #6366f1;
  color: white;
}
.btn-students:hover {
  background: #4f46e5;
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
.btn-ocr { background: #f59e0b; color: white; border: none; padding: 4px 10px; border-radius: 4px; cursor: pointer; font-size: 0.8rem; }
.btn-ocr:hover:not(:disabled) { background: #d97706; }
.btn-ocr:disabled { opacity: 0.6; cursor: wait; }

@media (max-width: 1100px) {
  .questionnaire-metrics,
  .questionnaire-columns,
  .response-master-detail,
  .response-detail-grid {
    grid-template-columns: 1fr;
  }
}
</style>
