<script setup>
import { ref, computed, onMounted, nextTick } from 'vue'
import { useAuthStore } from '../stores/auth'
import { useExamStore } from '../stores/exam'
import { useRouter } from 'vue-router'
import gradingApi from '../services/gradingApi'
import api from '../services/api'
import JuryReportsModal from '../components/JuryReportsModal.vue'
import ExamTypeSelectionModal from '../components/ExamTypeSelectionModal.vue'
import ExamTypeIcon from '../components/ExamTypeIcon.vue'
import AppIcon from '../icons/AppIcon.vue'
import { normalizeCollectionResponse } from '../utils/normalizeCollection'

const authStore = useAuthStore()
const examStore = useExamStore()
const router = useRouter()

// ═══════════════════════════════════════════════════════════
// GUARD: Admins must not see the corrector dashboard at all
// ═══════════════════════════════════════════════════════════
if (authStore.user?.role === 'Admin' || authStore.user?.is_superuser) {
    router.replace('/admin/dashboard')
}

const statusLabels = {
  'READY': 'Prêt',
  'IN_PROGRESS': 'En cours',
  'LOCKED': 'Verrouillée',
  'GRADED': 'Corrigée',
  'FINALIZED': 'Finalisée',
}
const getStatusLabel = (status) => statusLabels[status] || status

const copies = ref([])
const isLoading = ref(true)
const basicStats = ref({ total: 0, graded: 0, todo: 0 })

// Stats : une entrée par examen { [examId]: statsObject }
const examStatsMap = ref({})
const statsLoadingMap = ref({})
// Quel examen est actuellement affiché dans la section stats (null = masqué)
const activeStatsExamId = ref(null)

// Computed rétro-compatibles avec le code des graphiques SVG
const examStats = computed(() =>
    activeStatsExamId.value ? (examStatsMap.value[activeStatsExamId.value] ?? null) : null
)
const statsLoading = computed(() =>
    activeStatsExamId.value ? (statsLoadingMap.value[activeStatsExamId.value] ?? false) : false
)

const myStudents = ref([])
const myStudentsLoading = ref(false)
const allExams = ref([])
const isExporting = ref(null) // ID or group_name being exported
const exportError = ref(null)

// --- Exam Type Selection ---
const selectedExamType = ref(null)

const storedType = localStorage.getItem('korrigo_selected_exam_type')
if (storedType) {
    try {
        selectedExamType.value = JSON.parse(storedType)
    } catch (e) { }
}

const showExamTypeModal = computed(() => !selectedExamType.value)

const handleExamTypeSelect = (type) => {
    selectedExamType.value = type
    localStorage.setItem('korrigo_selected_exam_type', JSON.stringify(type))
    examStore.setCurrentExamType(type.id, type.name)
    fetchCopies()
}

const handleChangeExamType = () => {
    selectedExamType.value = null
    localStorage.removeItem('korrigo_selected_exam_type')
    examStore.clearCurrentExamType()
    copies.value = []
    basicStats.value = { total: 0, graded: 0, todo: 0 }
    activeStatsExamId.value = null
    examStatsMap.value = {}
}
// ---------------------------

const questionnaireStatusLoaded = ref(false)
const questionnaireSummary = ref({ has_response: false, summary: { is_available: false } })

const showJuryReportsModal = ref(false)
const openJuryReportsModal = () => {
    showJuryReportsModal.value = true
}

// --- Per-copy scoring progress ---
const copyScores = ref({})
const scoresLoading = ref(false)

const flattenLeafQuestions = (structure, positionPrefix = '') => {
    const leaves = []
    if (!Array.isArray(structure)) return leaves
    for (let idx = 0; idx < structure.length; idx++) {
        const item = structure[idx]
        const pos = positionPrefix ? `${positionPrefix}.${idx + 1}` : String(idx + 1)
        const children = item.children || item.sub_questions || []
        if (children.length > 0) {
            leaves.push(...flattenLeafQuestions(children, item.id || pos))
        } else {
            const leafId = item.id || pos
            const pts = item.points || item.maxScore || item.max_score || 0
            leaves.push({ id: leafId, label: item.label || item.title || leafId, points: pts })
        }
    }
    return leaves
}

const getCopyProgress = (copy) => {
    const progress = copyScores.value[copy.id]
    if (progress) return progress

    const structure = copy.exam_details?.grading_structure || []
    const leaves = flattenLeafQuestions(structure)
    const total = leaves.length

    if (copy.status === 'FINALIZED' || copy.status === 'GRADED') {
        return { scored: total, total, percent: 100, questions: leaves.map(q => ({ ...q, scored: true })) }
    }
    return { scored: 0, total, percent: 0, questions: leaves.map(q => ({ ...q, scored: false })), pending: true }
}

const fetchAllCopyScores = async (copiesList) => {
    const relevantCopies = copiesList.filter(c =>
        (c.status === 'READY' || c.status === 'IN_PROGRESS' || c.status === 'FINALIZED' || c.status === 'GRADED') &&
        c.exam_details?.grading_structure && c.exam_details.grading_structure.length > 0
    )
    if (!relevantCopies.length) return

    scoresLoading.value = true
    const results = {}

    const batchSize = 6
    for (let i = 0; i < relevantCopies.length; i += batchSize) {
        const batch = relevantCopies.slice(i, i + batchSize)
        const promises = batch.map(async (copy) => {
            try {
                const data = await gradingApi.fetchScores(copy.id)
                const scoresData = data.scores_data || {}
                const structure = copy.exam_details?.grading_structure || []
                const leaves = flattenLeafQuestions(structure)
                const total = leaves.length

                const questions = leaves.map(q => ({
                    ...q,
                    scored: scoresData[q.id] !== undefined && scoresData[q.id] !== null && scoresData[q.id] !== ''
                }))
                const scored = questions.filter(q => q.scored).length
                const percent = total > 0 ? Math.round((scored / total) * 100) : 0

                results[copy.id] = { scored, total, percent, questions }
            } catch (err) {
                // Silently ignore 403/404
            }
        })
        await Promise.all(promises)
    }

    copyScores.value = { ...copyScores.value, ...results }
    scoresLoading.value = false
}

const fetchCopies = async () => {
    if (authStore.user?.role === 'Admin' || authStore.user?.is_superuser) {
        router.replace('/admin/dashboard')
        return
    }
    if (!selectedExamType.value) return;

    isLoading.value = true
    try {
        const data = await gradingApi.listCopies({ exam_type_id: selectedExamType.value.id })
        copies.value = Array.isArray(data) ? data : []

        const total = data.length
        const graded = data.filter(c => c.status === 'FINALIZED' || c.status === 'GRADED').length
        // "À faire" = READY + IN_PROGRESS
        const todo = data.filter(c => c.status === 'READY' || c.status === 'IN_PROGRESS').length
        basicStats.value = { total, graded, todo }

        // Fetch per-question scoring progress in background
        fetchAllCopyScores(data)

        // Fetch all exams of this type
        await fetchAllExams()

        // Auto-afficher les stats du premier examen qui a des copies corrigées
        const firstGradedGroup = copiesByExam.value.find(g =>
            g.copies.some(c => c.status === 'FINALIZED' || c.status === 'GRADED')
        )
        if (firstGradedGroup && !activeStatsExamId.value) {
            await fetchExamStats(firstGradedGroup.examId)
            activeStatsExamId.value = firstGradedGroup.examId
        }

        // Fetch teacher's own students' finalized copies
        fetchMyStudents()
    } catch (err) {
        console.error("Failed to fetch copies", err)
    } finally {
        isLoading.value = false
    }
}

const fetchAllExams = async () => {
    if (!selectedExamType.value) return
    try {
        const response = await api.get('/exams/', {
            params: { exam_type_id: selectedExamType.value.id }
        })
        allExams.value = normalizeCollectionResponse(response.data)
    } catch (err) {
        console.error("Failed to fetch all exams", err)
        allExams.value = []
    }
}

const fetchMyStudents = async () => {
    if (!selectedExamType.value) return
    myStudentsLoading.value = true
    try {
        const response = await api.get('/grading/my-students/', {
            params: { exam_type_id: selectedExamType.value.id }
        })
        myStudents.value = Array.isArray(response.data?.students) ? response.data.students : []
    } catch (err) {
        console.error("Failed to fetch my students copies", err)
    } finally {
        myStudentsLoading.value = false
    }
}

const fetchQuestionnaireStatus = async () => {
    questionnaireStatusLoaded.value = false
    try {
        const res = await api.get('/grading/questionnaire/')
        questionnaireSummary.value = {
            has_response: !!res.data.has_response,
            summary: res.data.summary || { is_available: false }
        }
    } catch (err) {
        console.error("Failed to fetch questionnaire status", err)
    } finally {
        questionnaireStatusLoaded.value = true
    }
}

// Fetch et stocke les stats d'un examen donné
const fetchExamStats = async (examId) => {
    if (!examId || examStatsMap.value[examId]) return
    statsLoadingMap.value = { ...statsLoadingMap.value, [examId]: true }
    try {
        const stats = await gradingApi.fetchExamStats(examId)
        examStatsMap.value = { ...examStatsMap.value, [examId]: stats }
    } catch (err) {
        console.error("Failed to fetch stats for exam", examId, err)
    } finally {
        statsLoadingMap.value = { ...statsLoadingMap.value, [examId]: false }
    }
}

// Grouper les copies par examen
const copiesByExam = computed(() => {
    const groups = {}
    for (const exam of (allExams.value || [])) {
        groups[exam.id] = {
            examId: exam.id,
            examName: exam.name,
            examDate: exam.date,
            examTypeDetails: exam.exam_type_details,
            copies: []
        }
    }

    for (const copy of (copies.value || [])) {
        const examId = copy.exam_details?.id || copy.exam || 'unknown'
        if (groups[examId]) {
            groups[examId].copies.push(copy)
        } else {
            const examName = copy.exam_details?.name || copy.exam_name || 'Examen'
            const examDate = copy.exam_details?.date || ''
            const examTypeDetails = copy.exam_details?.exam_type_details || null
            groups[examId] = { examId, examName, examDate, examTypeDetails, copies: [copy] }
        }
    }
    return Object.values(groups).sort((a, b) => a.examName.localeCompare(b.examName))
})

// Toggle stats pour un examen donné
const toggleExamStats = async (examId) => {
    if (activeStatsExamId.value === examId) {
        activeStatsExamId.value = null
        return
    }
    activeStatsExamId.value = examId
    await fetchExamStats(examId)
    nextTick(() => {
        const el = document.getElementById('stats-section')
        if (el) el.scrollIntoView({ behavior: 'smooth' })
    })
}

// SVG chart dimensions
const chartW = 700
const chartH = 220
const padL = 35
const padR = 15
const padT = 20
const padB = 30
const plotW = chartW - padL - padR
const plotH = chartH - padT - padB

const mergedBins = computed(() => {
    const lot = examStats.value?.lot_distribution || []
    const global = examStats.value?.global_distribution || []
    const bins = []
    for (let n = 0; n <= 20; n++) {
        const lb = lot.find(b => b.start === n)
        const gb = global.find(b => b.start === n)
        bins.push({ note: n, lotCount: lb?.count || 0, globalCount: gb?.count || 0 })
    }
    return bins
})

const maxDistCount = computed(() => {
    if (!mergedBins.value.length) return 1
    return Math.max(...mergedBins.value.map(b => Math.max(b.lotCount, b.globalCount)), 1)
})

const yTicks = computed(() => {
    const m = maxDistCount.value
    if (m <= 5) return Array.from({ length: m + 1 }, (_, i) => i)
    const step = Math.ceil(m / 5)
    const ticks = []
    for (let v = 0; v <= m; v += step) ticks.push(v)
    if (ticks[ticks.length - 1] < m) ticks.push(m)
    return ticks
})

const toX = (note) => padL + (note / 20) * plotW
const toY = (count) => padT + plotH - (count / maxDistCount.value) * plotH

const buildPath = (series) => {
    const pts = mergedBins.value.map(b => ({ x: toX(b.note), y: toY(b[series]) }))
    if (!pts.length) return ''
    return 'M ' + pts.map(p => `${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(' L ')
}

const buildArea = (series) => {
    const pts = mergedBins.value.map(b => ({ x: toX(b.note), y: toY(b[series]) }))
    if (!pts.length) return ''
    const baseline = toY(0)
    return 'M ' + `${pts[0].x.toFixed(1)},${baseline.toFixed(1)} ` +
        pts.map(p => `L ${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(' ') +
        ` L ${pts[pts.length - 1].x.toFixed(1)},${baseline.toFixed(1)} Z`
}

const lotPath = computed(() => buildPath('lotCount'))
const globalPath = computed(() => buildPath('globalCount'))
const lotArea = computed(() => buildArea('lotCount'))
const globalArea = computed(() => buildArea('globalCount'))

const meanLineX = computed(() => {
    const m = examStats.value?.global_stats?.mean
    return m != null ? toX(m) : null
})
const medianLineX = computed(() => {
    const m = examStats.value?.global_stats?.median
    return m != null ? toX(m) : null
})

onMounted(async () => {
    examStore.restoreFromStorage()

    const promises = [fetchQuestionnaireStatus()]
    if (selectedExamType.value) {
        promises.push(fetchCopies())
    }
    await Promise.all(promises)
})

const handleLogout = async () => {
    await authStore.logout()
    router.push('/')
}

const handleChangePassword = async () => {
    const newPass = prompt("Nouveau mot de passe (min 6 caractères) :")
    if (!newPass) return
    if (newPass.length < 6) {
        alert("Le mot de passe doit faire au moins 6 caractères.")
        return
    }
    try {
        await api.post('/change-password/', { password: newPass })
        alert("Mot de passe mis à jour avec succès.")
    } catch (e) {
        alert("Erreur: " + (e.response?.data?.error || "Echec mise à jour"))
    }
}

const goToDesk = (copyId) => {
    router.push(`/corrector/desk/${copyId}`)
}

const goToMyStudents = (exam = null) => {
    if (exam && exam.examId) {
        examStore.setCurrentExam(exam.examId, exam.examName)
    } else {
        examStore.clearCurrentExam()
    }
    router.push('/corrector/my-students')
}

const goToStudentBilan = (studentId) => {
    const query = {}
    if (examStore.currentExamId) {
        query.exam_id = examStore.currentExamId
    } else if (selectedExamType.value?.id) {
        query.exam_type_id = selectedExamType.value.id
    }
    router.push({
        path: `/corrector/student/${studentId}/bilan`,
        query,
    })
}

const goToQuestionnaire = () => {
    router.push('/corrector/questionnaire')
}

const goToQuestionnaireBilan = () => {
    router.push({ name: 'QuestionnaireBilanPublic' })
}

const bilanRoutesByExamTypeCode = {
    BAC_BLANC_MATHS_2026: { name: 'BilanBacBlanc' },
    DNB_BLANC_MATHS_2026: { name: 'DnbBilanList' },
    EAM_2026: { name: 'EamBilanDetail' },
}

const canSeeExamBilan = (examTypeCode) => !!bilanRoutesByExamTypeCode[examTypeCode]

const goToExamBilan = async (examTypeCode) => {
    const target = bilanRoutesByExamTypeCode[examTypeCode]
    if (!target) return

    // For EAM, fetch the bilan ID first then navigate to /bilan/eam/:id
    if (examTypeCode === 'EAM_2026') {
        try {
            const response = await api.get('/bilan/')
            const bilans = response.data.bilans || []
            const eamBilan = bilans.find(b => b.exam_type === 'EAM BLANCHE 2026' && b.status === 'DONE')
            if (eamBilan) {
                router.push(`/bilan/eam/${eamBilan.id}`)
            } else {
                alert('Aucun bilan EAM disponible pour le moment.')
            }
        } catch (err) {
            console.error('Failed to fetch EAM bilan:', err)
            alert('Erreur lors de la récupération du bilan EAM.')
        }
    } else {
        router.push(target)
    }
}

const downloadCsv = async (examId, groupName, examName, assignmentType = 'classe') => {
    isExporting.value = `${examId}_${groupName}`
    try {
        const params = {
            exam_id: examId,
            assignment_type: assignmentType
        }
        if (groupName) {
            params.group_name = groupName
        }

        if (groupName) {
            if (groupName.startsWith('T') || groupName.startsWith('Term')) params.level = 'terminale'
            else if (groupName.startsWith('1')) params.level = 'premiere'
            else if (groupName.startsWith('3')) params.level = 'troisieme'
        }

        const response = await api.get('/grading/my-students/export-csv/', {
            params,
            responseType: 'blob'
        })

        const url = window.URL.createObjectURL(new Blob([response.data]))
        const link = document.createElement('a')
        link.href = url
        link.setAttribute('download', `PRONOTE_${examName}_${groupName}.csv`)
        document.body.appendChild(link)
        link.click()
        document.body.removeChild(link)
    } catch (err) {
        console.error('CSV Export failed', err)
        alert('Erreur lors de l\'export CSV.')
    } finally {
        isExporting.value = null
    }
}

// --- Feature flags ---
const canSeeJuryReport = computed(() => {
    const codes = authStore.user?.features?.jury_report_exam_codes ?? []
    return codes.includes(selectedExamType.value?.code)
})
const canSeeQuestionnaire = computed(() =>
    authStore.user?.features?.show_questionnaire === true
)
</script>

<template>
  <div
    class="corrector-dashboard"
    data-testid="corrector-dashboard"
  >
    <header class="top-nav">
      <div class="brand">
        Korrigo — Correcteur
      </div>

      <div v-if="selectedExamType" class="exam-type-indicator">
        <span class="type-badge" :style="{ backgroundColor: selectedExamType.color + '20', color: selectedExamType.color }">
          {{ selectedExamType.name }}
        </span>
        <button class="btn-text btn-change-type" @click="handleChangeExamType">
          Changer d'examen
        </button>
      </div>

      <div class="user-menu">
        <span class="user-name">{{ authStore.user?.first_name || authStore.user?.username }}</span>
        <button
          class="btn-text"
          @click="handleChangePassword"
        >
          Modifier mot de passe
        </button>
        <button
          v-if="canSeeQuestionnaire && questionnaireStatusLoaded && !questionnaireSummary.has_response"
          class="btn-questionnaire"
          @click="goToQuestionnaire"
        >
          <AppIcon name="edit" :size="14" class="inline" /> Questionnaire
        </button>
        <button
          v-if="canSeeQuestionnaire && questionnaireStatusLoaded && questionnaireSummary.has_response"
          class="btn-questionnaire-bilan"
          @click="goToQuestionnaireBilan"
        >
          <AppIcon name="trending" :size="14" class="inline" /> Bilan du questionnaire
        </button>
        <button
          v-if="canSeeJuryReport"
          class="btn-jury-report"
          @click="openJuryReportsModal"
        >
          <AppIcon name="list" :size="14" class="inline" /> Rapport du Jury {{ selectedExamType?.name || '' }}
        </button>
        <button
          class="btn-logout"
          @click="handleLogout"
          data-testid="logout-button"
        >
          Déconnexion
        </button>
      </div>
    </header>

    <main class="container">
      <!-- KPIs globaux -->
      <div class="stats-overview">
        <div class="card stat">
          <h3>Copies Attribuées</h3>
          <div class="value">{{ basicStats.total }}</div>
        </div>
        <div class="card stat">
          <h3>Finalisées</h3>
          <div class="value success">{{ basicStats.graded }}</div>
        </div>
        <div class="card stat">
          <h3>Reste à faire</h3>
          <div class="value warning">{{ basicStats.todo }}</div>
        </div>
      </div>

      <!-- ════════════════════════════════════════════
           LISTE DES COPIES groupées par examen
           ════════════════════════════════════════════ -->
      <div class="task-list">
        <h2>Vos copies</h2>
        <div
          v-if="isLoading"
          class="loading"
        >
          Chargement des copies…
        </div>
        <template v-else>
          <div
            v-for="group in copiesByExam"
            :key="group.examId"
            class="exam-group"
          >
            <!-- En-tête de groupe d'examen -->
            <div class="exam-group-header">
              <div class="exam-group-title">
                <span v-if="group.examTypeDetails" class="exam-type-badge inline" :style="{ backgroundColor: group.examTypeDetails.color + '20', color: group.examTypeDetails.color }">
                  <ExamTypeIcon :icon="group.examTypeDetails.icon" :size="14" />
                </span>
                <strong>{{ group.examName }}</strong>
                <span v-if="group.examDate" class="exam-date-tag">{{ group.examDate }}</span>
              </div>
              <div class="exam-group-meta">
                <!-- Compteurs par état -->
                <span
                  v-if="group.copies.filter(c => c.status === 'READY').length > 0"
                  class="meta-chip ready"
                >
                  {{ group.copies.filter(c => c.status === 'READY').length }} à corriger
                </span>
                <span
                  v-if="group.copies.filter(c => c.status === 'IN_PROGRESS').length > 0"
                  class="meta-chip in-progress"
                >
                  {{ group.copies.filter(c => c.status === 'IN_PROGRESS').length }} en cours
                </span>
                <span
                  v-if="group.copies.filter(c => c.status === 'FINALIZED' || c.status === 'GRADED').length > 0"
                  class="meta-chip done"
                >
                  {{ group.copies.filter(c => c.status === 'FINALIZED' || c.status === 'GRADED').length }} finalisées
                </span>
                <!-- Bouton stats (visible dès qu'il y a des copies finalisées) -->
                <button
                  v-if="group.copies.some(c => c.status === 'FINALIZED' || c.status === 'GRADED')"
                  :class="['btn-stats-inline', { active: activeStatsExamId === group.examId }]"
                  @click="toggleExamStats(group.examId)"
                  :title="activeStatsExamId === group.examId ? 'Masquer les statistiques' : 'Voir les statistiques de cet examen'"
                >
                  <AppIcon name="bar-chart-3" :size="13" />
                  {{ activeStatsExamId === group.examId ? 'Masquer stats' : 'Statistiques' }}
                </button>
                <!-- Bouton Bilan (si disponible pour le type d'examen) -->
                <button
                  v-if="canSeeExamBilan(group.examTypeDetails?.code)"
                  class="btn-bilan-inline"
                  @click="goToExamBilan(group.examTypeDetails?.code)"
                  title="Consulter le bilan de cet examen"
                >
                  <AppIcon name="file-text" :size="14" class="inline" /> Bilan
                </button>
                <!-- Bouton Mes Élèves (strict par examen) -->
                <button
                  class="btn-my-students-inline"
                  data-testid="btn-my-students-inline"
                  :data-exam-id="group.examId"
                  @click="goToMyStudents(group)"
                  title="Voir mes élèves de cet examen (copies finalisées)"
                >
                  <AppIcon name="users" :size="14" class="inline" /> Mes Élèves
                </button>
                <!-- Export CSV -->
                <button
                  class="btn-export-inline"
                  @click="downloadCsv(group.examId, null, group.examName)"
                  :disabled="isExporting === `${group.examId}_null`"
                  title="Exporter toutes les notes de cet examen vers Pronote"
                >
                  <AppIcon :name="isExporting === `${group.examId}_null` ? 'loader' : 'download'" :size="14" class="inline" /> Export
                </button>
              </div>
            </div>

            <!-- Stats de cet examen (accordion : une seule section ouverte) -->
            <div
              v-if="activeStatsExamId === group.examId"
              id="stats-section"
              class="charts-section"
            >
              <div class="stats-section-title">
                <AppIcon name="bar-chart-3" :size="16" />
                Statistiques — <strong>{{ group.examName }}</strong>
                <button class="btn-close-stats" @click="activeStatsExamId = null" title="Fermer les statistiques">
                  <AppIcon name="x" :size="14" />
                </button>
              </div>

              <div v-if="statsLoading" class="loading">
                Chargement des statistiques...
              </div>

              <template v-else-if="examStats">
                <!-- Indicateurs comparatifs -->
                <div class="comparative-stats">
                  <h3>Indicateurs Comparatifs</h3>
                  <div
                    v-if="!examStats.all_graded"
                    class="partial-warning"
                  >
                    Statistiques partielles ({{ examStats.graded_copies }}/{{ examStats.total_copies }} copies corrigées)
                  </div>
                  <table class="stats-table">
                    <thead>
                      <tr>
                        <th>Indicateur</th>
                        <th>Mon Lot</th>
                        <th>Global</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr>
                        <td>Moyenne</td>
                        <td>{{ examStats.lot_stats?.mean ?? '-' }}</td>
                        <td>{{ examStats.global_stats?.mean ?? '-' }}</td>
                      </tr>
                      <tr>
                        <td>Médiane</td>
                        <td>{{ examStats.lot_stats?.median ?? '-' }}</td>
                        <td>{{ examStats.global_stats?.median ?? '-' }}</td>
                      </tr>
                      <tr>
                        <td>Écart-type</td>
                        <td>{{ examStats.lot_stats?.std_dev ?? '-' }}</td>
                        <td>{{ examStats.global_stats?.std_dev ?? '-' }}</td>
                      </tr>
                      <tr>
                        <td>Minimum</td>
                        <td>{{ examStats.lot_stats?.min ?? '-' }}</td>
                        <td>{{ examStats.global_stats?.min ?? '-' }}</td>
                      </tr>
                      <tr>
                        <td>Maximum</td>
                        <td>{{ examStats.lot_stats?.max ?? '-' }}</td>
                        <td>{{ examStats.global_stats?.max ?? '-' }}</td>
                      </tr>
                      <tr>
                        <td>Nombre de copies</td>
                        <td>{{ examStats.lot_stats?.count ?? '-' }}</td>
                        <td>{{ examStats.global_stats?.count ?? '-' }}</td>
                      </tr>
                    </tbody>
                  </table>
                </div>

                <!-- Courbe de répartition -->
                <div
                  v-if="mergedBins.length"
                  class="chart-container"
                >
                  <div class="chart-header">
                    <h3>
                      Répartition des Notes (0–20){{ !examStats.all_graded ? ' — partiel' : '' }}
                    </h3>
                    <div class="chart-legend">
                      <span class="legend-item"><span class="legend-dot lot-dot" /> Mon Lot</span>
                      <span class="legend-item"><span class="legend-dot global-dot" /> Global</span>
                      <span class="legend-item"><span class="legend-line mean-line" /> Moyenne</span>
                      <span class="legend-item"><span class="legend-line median-line" /> Médiane</span>
                    </div>
                  </div>
                  <svg :viewBox="`0 0 ${chartW} ${chartH}`" class="svg-chart" preserveAspectRatio="xMidYMid meet">
                    <line v-for="t in yTicks" :key="'gy'+t"
                      :x1="padL" :x2="chartW - padR" :y1="toY(t)" :y2="toY(t)"
                      stroke="#e2e8f0" stroke-width="0.5" />
                    <line v-for="n in 21" :key="'gx'+n"
                      :x1="toX(n-1)" :x2="toX(n-1)" :y1="padT" :y2="padT + plotH"
                      stroke="#f1f5f9" stroke-width="0.5" />

                    <path :d="globalArea" fill="#10b98120" />
                    <path :d="lotArea" fill="#6366f120" />

                    <path :d="globalPath" fill="none" stroke="#10b981" stroke-width="2.5" stroke-linejoin="round" />
                    <path :d="lotPath" fill="none" stroke="#6366f1" stroke-width="2.5" stroke-linejoin="round" />

                    <template v-for="b in mergedBins" :key="'dp'+b.note">
                      <circle v-if="b.globalCount > 0" :cx="toX(b.note)" :cy="toY(b.globalCount)" r="3" fill="#10b981" />
                      <circle v-if="b.lotCount > 0" :cx="toX(b.note)" :cy="toY(b.lotCount)" r="3" fill="#6366f1" />
                    </template>

                    <line v-if="meanLineX != null"
                      :x1="meanLineX" :x2="meanLineX" :y1="padT" :y2="padT + plotH"
                      stroke="#ef4444" stroke-width="1.5" stroke-dasharray="6,3" opacity="0.7" />
                    <text v-if="meanLineX != null"
                      :x="meanLineX" :y="padT - 4" text-anchor="middle"
                      fill="#ef4444" font-size="9" font-weight="600">
                      μ={{ examStats.global_stats?.mean }}
                    </text>

                    <line v-if="medianLineX != null"
                      :x1="medianLineX" :x2="medianLineX" :y1="padT" :y2="padT + plotH"
                      stroke="#f59e0b" stroke-width="1.5" stroke-dasharray="3,3" opacity="0.7" />
                    <text v-if="medianLineX != null"
                      :x="medianLineX" :y="padT + plotH + 26" text-anchor="middle"
                      fill="#f59e0b" font-size="9" font-weight="600">
                      Méd={{ examStats.global_stats?.median }}
                    </text>

                    <text v-for="n in 21" :key="'xl'+n"
                      :x="toX(n-1)" :y="padT + plotH + 14"
                      text-anchor="middle" fill="#64748b" font-size="9">
                      {{ n - 1 }}
                    </text>
                    <text v-for="t in yTicks" :key="'yl'+t"
                      :x="padL - 6" :y="toY(t) + 3"
                      text-anchor="end" fill="#94a3b8" font-size="9">
                      {{ t }}
                    </text>

                    <line :x1="padL" :x2="chartW - padR" :y1="padT + plotH" :y2="padT + plotH" stroke="#cbd5e1" stroke-width="1" />
                    <line :x1="padL" :x2="padL" :y1="padT" :y2="padT + plotH" stroke="#cbd5e1" stroke-width="1" />
                  </svg>
                </div>

                <!-- Stats par groupe -->
                <div
                  v-if="examStats.group_stats && examStats.group_stats.length"
                  class="group-stats-section"
                >
                  <h3>Statistiques par {{ examStats.group_stats[0]?.type === 'classe' ? 'Classe' : 'Groupe' }}</h3>
                  <div class="group-table-wrapper">
                    <table class="group-stats-table">
                      <thead>
                        <tr>
                          <th>{{ examStats.group_stats[0]?.type === 'classe' ? 'Classe' : 'Groupe' }}</th>
                          <th>Copies</th>
                          <th>Moyenne</th>
                          <th>Médiane</th>
                          <th>Écart-type</th>
                          <th>Min</th>
                          <th>Max</th>
                          <th>≥ Moy. globale</th>
                          <th>&lt; Moy. globale</th>
                          <th class="action-cell">Export</th>
                        </tr>
                      </thead>
                      <tbody>
                        <tr v-for="g in examStats.group_stats" :key="g.groupe">
                          <td class="group-name">{{ g.groupe }}</td>
                          <td>{{ g.count }}</td>
                          <td :class="{ 'above-global': g.mean >= examStats.global_stats?.mean, 'below-global': g.mean < examStats.global_stats?.mean }">
                            <strong>{{ g.mean ?? '-' }}</strong>
                          </td>
                          <td>{{ g.median ?? '-' }}</td>
                          <td>{{ g.std_dev ?? '-' }}</td>
                          <td>{{ g.min ?? '-' }}</td>
                          <td>{{ g.max ?? '-' }}</td>
                          <td class="count-above">{{ g.above_mean }}</td>
                          <td class="count-below">{{ g.below_mean }}</td>
                          <td class="action-cell">
                            <button
                              class="btn-export-table"
                              @click="downloadCsv(examStats.exam_id, g.groupe, examStats.exam_name, g.type || 'groupe')"
                              :disabled="isExporting === `${examStats.exam_id}_${g.groupe}`"
                              title="Exporter les notes de ce groupe vers Pronote"
                            >
                              <AppIcon :name="isExporting === `${examStats.exam_id}_${g.groupe}` ? 'loader' : 'download'" :size="12" />
                              CSV
                            </button>
                          </td>
                        </tr>
                      </tbody>
                      <tfoot>
                        <tr class="global-row">
                          <td class="group-name"><strong>Global</strong></td>
                          <td><strong>{{ examStats.global_stats?.count ?? '-' }}</strong></td>
                          <td><strong>{{ examStats.global_stats?.mean ?? '-' }}</strong></td>
                          <td><strong>{{ examStats.global_stats?.median ?? '-' }}</strong></td>
                          <td><strong>{{ examStats.global_stats?.std_dev ?? '-' }}</strong></td>
                          <td><strong>{{ examStats.global_stats?.min ?? '-' }}</strong></td>
                          <td><strong>{{ examStats.global_stats?.max ?? '-' }}</strong></td>
                          <td colspan="2" />
                        </tr>
                      </tfoot>
                    </table>
                  </div>
                </div>
              </template>
            </div>

            <!-- Copies de cet examen -->
            <div
              v-for="copy in group.copies"
              :key="copy.id"
              class="copy-card"
              data-testid="copy-card"
              :data-copy-anon="copy.anonymous_id"
            >
              <div class="copy-main-row">
                <div class="copy-info">
                  <div class="copy-id">
                    Anonymat : <strong>{{ copy.anonymous_id }}</strong>
                  </div>
                </div>
                <div :class="['copy-status', copy.status.toLowerCase()]">
                  {{ getStatusLabel(copy.status) }}
                </div>
                <button
                  class="btn-action"
                  data-testid="copy-action"
                  @click="goToDesk(copy.id)"
                >
                  {{ (copy.status === 'FINALIZED' || copy.status === 'GRADED') ? 'Consulter' : 'Corriger' }}
                </button>
              </div>
              <!-- Barre de progression par question -->
              <div
                v-if="getCopyProgress(copy).total > 0"
                class="copy-progress"
              >
                <div class="progress-label">
                  <span class="progress-text">
                    {{ getCopyProgress(copy).scored }}/{{ getCopyProgress(copy).total }} question{{ getCopyProgress(copy).total > 1 ? 's' : '' }} notée{{ getCopyProgress(copy).total > 1 ? 's' : '' }}
                  </span>
                  <span class="progress-percent">{{ getCopyProgress(copy).percent }}%</span>
                </div>
                <div class="progress-bar-track">
                  <div
                    v-for="(q, idx) in getCopyProgress(copy).questions"
                    :key="idx"
                    :class="['progress-segment', q.scored ? 'scored' : 'unscored']"
                    :style="{ width: (100 / getCopyProgress(copy).total) + '%' }"
                    :title="q.label + (q.scored ? ' (notée)' : ' (non notée)')"
                  />
                </div>
              </div>
            </div>

            <!-- État vide pour cet examen -->
            <div v-if="group.copies.length === 0" class="empty-exam-group">
              Aucune copie attribuée pour cet examen.
            </div>
          </div>

          <div
            v-if="copies.length === 0 && !isLoading"
            class="empty-state"
          >
            Aucune copie disponible pour le moment.
          </div>
        </template>
      </div>

      <!-- ════════════════════════════════════════════
           BILAN DES ÉLÈVES (enseignant)
           ════════════════════════════════════════════ -->
      <div v-if="selectedExamType && (myStudents.length > 0 || myStudentsLoading)" class="task-list my-students-section">
        <div class="section-header">
          <h2>Bilan de vos élèves — {{ selectedExamType.name }}</h2>
          <div class="section-actions">
            <button
              class="btn-my-students-global"
              data-testid="btn-my-students-global"
              @click="goToMyStudents()"
              title="Voir la page complète Mes Élèves"
            >
              <AppIcon name="users" :size="14" class="inline" /> Mes Élèves
            </button>
            <span v-if="!myStudentsLoading" class="count-badge">{{ myStudents.length }} élève(s)</span>
          </div>
        </div>

        <div v-if="myStudentsLoading" class="loading">
          Chargement du bilan des élèves...
        </div>

        <template v-else>
          <div class="students-results-grid">
            <div
              v-for="student in myStudents"
              :key="student.id"
              class="student-result-card"
              @click="goToStudentBilan(student.id)"
            >
              <div class="student-main">
                <div class="student-identity">
                  <div class="name">{{ student.last_name }} {{ student.first_name }}</div>
                  <div class="meta">{{ student.class_name }} <span v-if="student.groupe" class="bullet">•</span> {{ student.groupe }}</div>
                </div>

                <div class="student-copies-list">
                  <div v-for="copy in student.copies" :key="copy.copy_id" class="mini-copy-info">
                    <span class="exam-tag">{{ copy.exam_name }}</span>
                    <div class="score-display">
                      <span v-if="copy.total_score !== null" class="score-value">
                        {{ copy.total_score.toFixed(2) }}<span class="max">/20</span>
                      </span>
                      <span v-else class="score-pending">—</span>
                    </div>
                  </div>
                </div>
              </div>
              <div class="card-footer">
                <span class="btn-view-bilan">Voir le bilan détaillé <AppIcon name="chevron-right" :size="12" /></span>
              </div>
            </div>
          </div>
        </template>
      </div>
    </main>

    <JuryReportsModal
      :visible="showJuryReportsModal"
      :exam-type-code="selectedExamType?.code || ''"
      :exam-type-name="selectedExamType?.name || ''"
      @close="showJuryReportsModal = false"
    />
    <ExamTypeSelectionModal
      :visible="showExamTypeModal"
      @select="handleExamTypeSelect"
    />
  </div>
</template>

<style scoped>
.corrector-dashboard { background: #f8fafc; min-height: 100vh; font-family: 'Inter', sans-serif; }
.top-nav { background: white; padding: 1rem 2rem; display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #e2e8f0; }
.brand { font-weight: 700; color: #0f172a; font-size: 1.1rem; }
.user-menu { display: flex; gap: 1rem; align-items: center; font-size: 0.9rem; }
.btn-text { background: none; border: none; color: #64748b; cursor: pointer; text-decoration: underline; font-size: 0.85rem; }
.btn-questionnaire { background: #b45309; color: white; border: none; cursor: pointer; font-weight: 500; padding: 4px 10px; border-radius: 4px; font-size: 0.85rem; }
.btn-questionnaire:hover { background: #92400e; }
.btn-questionnaire-bilan { background: #7c3aed; color: white; border: none; cursor: pointer; font-weight: 500; padding: 4px 10px; border-radius: 4px; font-size: 0.85rem; }
.btn-questionnaire-bilan:hover { background: #6d28d9; }
.btn-jury-report { display: inline-block; background: #f59e0b; color: white; border: none; cursor: pointer; font-weight: 500; padding: 4px 10px; border-radius: 4px; font-size: 0.85rem; text-decoration: none; }
.btn-jury-report:hover { background: #d97706; }
.btn-logout { border: 1px solid #ef4444; background: white; color: #ef4444; cursor: pointer; font-weight: 500; padding: 4px 8px; border-radius: 4px; }
.btn-logout:hover { background: #ef4444; color: white; }

.section-header { display: flex; align-items: center; justify-content: space-between; gap: 1rem; }
.section-actions { display: flex; align-items: center; gap: 0.75rem; }
.btn-my-students-global { border: 1px solid #e2e8f0; background: white; color: #0f172a; cursor: pointer; font-weight: 600; padding: 6px 10px; border-radius: 8px; }
.btn-my-students-global:hover { background: #f1f5f9; }

.container { max-width: 900px; margin: 2rem auto; padding: 0 1rem; }

.stats-overview { display: grid; grid-template-columns: repeat(3, 1fr); gap: 1rem; margin-bottom: 2rem; }
.card { background: white; padding: 1.5rem; border-radius: 8px; box-shadow: 0 1px 2px rgba(0,0,0,0.05); text-align: center; }
.stat h3 { margin: 0 0 0.5rem 0; font-size: 0.875rem; color: #64748b; font-weight: 500; }
.stat .value { font-size: 2rem; font-weight: 700; color: #0f172a; }
.value.success { color: #10b981; }
.value.warning { color: #f59e0b; }

/* Section stats */
.charts-section { margin-bottom: 2rem; }
.stats-section-title {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 1rem;
  color: #1e293b;
  font-weight: 600;
  background: white;
  border: 1px solid #e2e8f0;
  border-bottom: none;
  border-radius: 8px 8px 0 0;
  padding: 0.75rem 1rem;
}
.btn-close-stats {
  margin-left: auto;
  background: none;
  border: none;
  color: #94a3b8;
  cursor: pointer;
  padding: 2px;
  display: flex;
  align-items: center;
}
.btn-close-stats:hover { color: #475569; }

.comparative-stats { background: white; padding: 1.5rem; margin-bottom: 1rem; box-shadow: 0 1px 2px rgba(0,0,0,0.05); border: 1px solid #e2e8f0; }
.comparative-stats h3 { margin: 0 0 1rem 0; font-size: 1rem; color: #1e293b; }
.partial-warning { background: #fef3c7; color: #92400e; padding: 0.5rem 1rem; border-radius: 4px; margin-bottom: 1rem; font-size: 0.85rem; }
.stats-table { width: 100%; border-collapse: collapse; }
.stats-table th, .stats-table td { padding: 0.5rem 1rem; text-align: center; border-bottom: 1px solid #e2e8f0; }
.stats-table th { background: #f8fafc; font-weight: 600; font-size: 0.85rem; color: #64748b; }
.stats-table td:first-child { text-align: left; font-weight: 500; }

.chart-container { background: white; padding: 1.5rem; border-radius: 0; margin-bottom: 1rem; box-shadow: 0 1px 2px rgba(0,0,0,0.05); border: 1px solid #e2e8f0; }
.chart-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem; flex-wrap: wrap; gap: 0.5rem; }
.chart-header h3 { margin: 0; font-size: 1rem; color: #1e293b; }
.chart-legend { display: flex; gap: 1rem; align-items: center; flex-wrap: wrap; }
.legend-item { display: flex; align-items: center; gap: 4px; font-size: 0.8rem; color: #475569; font-weight: 500; }
.legend-dot { width: 12px; height: 12px; border-radius: 3px; }
.lot-dot { background: #6366f1; }
.global-dot { background: #10b981; }
.legend-line { width: 18px; height: 0; border-top: 2px dashed; }
.mean-line { border-color: #ef4444; }
.median-line { border-color: #f59e0b; }
.svg-chart { width: 100%; height: auto; max-height: 260px; }

.group-stats-section { background: white; padding: 1.5rem; border-radius: 0 0 8px 8px; margin-bottom: 1rem; box-shadow: 0 1px 2px rgba(0,0,0,0.05); border: 1px solid #e2e8f0; }
.group-stats-section h3 { margin: 0 0 1rem 0; font-size: 1rem; color: #1e293b; }
.group-table-wrapper { overflow-x: auto; }
.group-stats-table { width: 100%; border-collapse: collapse; font-size: 0.85rem; }
.group-stats-table th, .group-stats-table td { padding: 0.5rem 0.6rem; text-align: center; border-bottom: 1px solid #e2e8f0; }
.group-stats-table th { background: #f8fafc; font-weight: 600; color: #64748b; font-size: 0.8rem; white-space: nowrap; }
.group-stats-table .group-name { text-align: left; font-weight: 600; color: #334155; }
.group-stats-table .above-global { color: #059669; }
.group-stats-table .below-global { color: #dc2626; }
.group-stats-table .count-above { color: #059669; font-weight: 600; }
.group-stats-table .count-below { color: #dc2626; font-weight: 600; }
.group-stats-table tfoot .global-row { background: #f1f5f9; }
.group-stats-table tfoot .global-row td { border-top: 2px solid #cbd5e1; font-size: 0.85rem; }

.task-list h2 { font-size: 1.25rem; color: #1e293b; margin-bottom: 1rem; }

/* Groupement par examen */
.exam-group { margin-bottom: 2rem; }
.exam-group-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: white;
  padding: 0.75rem 1rem;
  border-radius: 6px 6px 0 0;
  border: 1px solid #e2e8f0;
  border-bottom: none;
  flex-wrap: wrap;
  gap: 0.5rem;
}
.exam-group-title {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.95rem;
  color: #1e293b;
}
.exam-date-tag { font-size: 0.78rem; color: #64748b; background: #f1f5f9; padding: 2px 6px; border-radius: 4px; font-weight: 400; }
.exam-group-meta { display: flex; gap: 0.5rem; align-items: center; flex-wrap: wrap; }
.meta-chip { font-size: 0.75rem; font-weight: 600; padding: 2px 8px; border-radius: 10px; }
.meta-chip.ready { background: #dbeafe; color: #1d4ed8; }
.meta-chip.in-progress { background: #fef3c7; color: #92400e; }
.meta-chip.done { background: #dcfce7; color: #166534; }

/* Bouton stats inline dans le header d'examen */
.btn-stats-inline {
  display: inline-flex; align-items: center; gap: 5px;
  background: #f1f5f9; color: #475569; border: 1px solid #cbd5e1;
  padding: 4px 10px; border-radius: 14px; font-size: 0.78rem;
  font-weight: 600; cursor: pointer; transition: all 0.2s;
}
.btn-stats-inline:hover { background: #e2e8f0; color: #1e293b; }
.btn-stats-inline.active { background: #6366f1; color: white; border-color: #6366f1; }
.btn-stats-inline.active:hover { background: #4f46e5; }

.btn-bilan-inline {
  display: inline-flex; align-items: center; gap: 6px;
  background: #7c3aed; color: white; border: none;
  padding: 4px 10px; border-radius: 14px; font-size: 0.78rem;
  font-weight: 600; cursor: pointer; transition: background 0.2s;
}
.btn-bilan-inline:hover { background: #6d28d9; }

.btn-my-students-inline {
  display: inline-flex; align-items: center; gap: 6px;
  background: #6366f1; color: white; border: none;
  padding: 4px 10px; border-radius: 14px; font-size: 0.78rem;
  font-weight: 600; cursor: pointer; transition: background 0.2s;
}
.btn-my-students-inline:hover { background: #4f46e5; }

.exam-group .copy-card { border-top: none; border-radius: 0; border-color: #e2e8f0; }
.exam-group .copy-card:last-child { border-radius: 0 0 8px 8px; }

.exam-type-badge.inline {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: 6px;
  font-size: 0.9rem;
  flex-shrink: 0;
}

.copy-card { background: white; padding: 1rem; margin-bottom: 0; box-shadow: 0 1px 2px rgba(0,0,0,0.04); border: 1px solid #e2e8f0; }
.copy-main-row { display: flex; justify-content: space-between; align-items: center; }
.copy-id { font-size: 0.875rem; color: #64748b; }
.copy-status { font-size: 0.75rem; font-weight: 600; text-transform: uppercase; padding: 2px 6px; border-radius: 4px; }
.copy-status.ready { background: #dbeafe; color: #1d4ed8; }
.copy-status.in_progress { background: #fef3c7; color: #92400e; }
.copy-status.locked { background: #fee2e2; color: #991b1b; }
.copy-status.graded { background: #dcfce7; color: #166534; }
.copy-status.finalized { background: #dcfce7; color: #166534; }
.copy-status.staging { background: #f1f5f9; color: #64748b; }

/* ExamType Badge */
.exam-type-badge {
  display: inline-block;
  padding: 2px 6px;
  border-radius: 4px;
  color: white;
  font-size: 0.70rem;
  font-weight: 600;
  margin-right: 6px;
  vertical-align: middle;
  box-shadow: 0 1px 2px rgba(0,0,0,0.1);
}

/* Per-copy scoring progress */
.copy-progress { margin-top: 0.6rem; padding-top: 0.5rem; border-top: 1px solid #f1f5f9; }
.progress-label { display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px; }
.progress-text { font-size: 0.78rem; color: #64748b; font-weight: 500; }
.progress-percent { font-size: 0.75rem; color: #94a3b8; font-weight: 600; }
.progress-bar-track { display: flex; height: 8px; border-radius: 4px; overflow: hidden; background: #f1f5f9; gap: 1px; }
.progress-segment { height: 100%; transition: background-color 0.3s ease; }
.progress-segment.scored { background: #10b981; }
.progress-segment.unscored { background: #e2e8f0; }
.progress-segment:first-child { border-radius: 4px 0 0 4px; }
.progress-segment:last-child { border-radius: 0 4px 4px 0; }
.progress-segment:only-child { border-radius: 4px; }

.btn-action { padding: 0.5rem 1rem; background: #2563eb; color: white; border: none; border-radius: 6px; cursor: pointer; font-weight: 500; }
.btn-action:hover { background: #1d4ed8; }

.loading { text-align: center; padding: 2rem; color: #64748b; }
.empty-state { text-align: center; padding: 2rem; color: #94a3b8; }
.empty-exam-group { padding: 1rem; text-align: center; color: #94a3b8; font-size: 0.85rem; background: white; border: 1px solid #e2e8f0; border-radius: 0 0 8px 8px; }

/* Section: Bilan des élèves */
.my-students-section { margin-top: 3rem; }
.section-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.5rem; }
.section-header h2 { margin-bottom: 0; }
.count-badge { background: #eef2ff; color: #6366f1; padding: 2px 10px; border-radius: 12px; font-size: 0.8rem; font-weight: 600; }

.students-results-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 1rem; }
.student-result-card {
  background: white; border: 1px solid #e2e8f0; border-radius: 10px; padding: 1rem;
  cursor: pointer; transition: all 0.2s ease; display: flex; flex-direction: column; gap: 0.75rem;
}
.student-result-card:hover { border-color: #6366f1; box-shadow: 0 4px 12px rgba(99, 102, 241, 0.08); transform: translateY(-2px); }

.student-identity .name { font-weight: 700; color: #0f172a; font-size: 0.95rem; }
.student-identity .meta { font-size: 0.8rem; color: #64748b; margin-top: 2px; }
.bullet { color: #cbd5e1; margin: 0 4px; }

.student-copies-list { margin-top: 0.75rem; border-top: 1px solid #f1f5f9; padding-top: 0.75rem; }
.mini-copy-info { display: flex; justify-content: space-between; align-items: center; }
.exam-tag { font-size: 0.75rem; font-weight: 500; color: #475569; background: #f8fafc; padding: 2px 6px; border-radius: 4px; border: 1px solid #e2e8f0; }
.score-display { font-weight: 700; color: #0f172a; font-size: 1.1rem; }
.score-display .max { font-size: 0.7rem; color: #94a3b8; font-weight: 500; margin-left: 1px; }
.score-pending { color: #94a3b8; font-style: italic; font-size: 0.9rem; }

.card-footer { margin-top: auto; padding-top: 0.5rem; border-top: 1px solid #f8fafc; }
.btn-view-bilan { font-size: 0.75rem; font-weight: 600; color: #6366f1; display: flex; align-items: center; gap: 4px; }
.student-result-card:hover .btn-view-bilan { color: #4f46e5; text-decoration: underline; }

.btn-export-table {
  background: #6366f1;
  color: white;
  border: none;
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 0.7rem;
  font-weight: 600;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 4px;
  transition: all 0.2s;
}
.btn-export-table:hover:not(:disabled) { background: #4f46e5; transform: translateY(-1px); }
.btn-export-table:disabled { background: #94a3b8; cursor: not-allowed; }
.action-cell { padding-left: 1rem; }

.btn-export-inline {
  background: #10b981;
  color: white;
  border: none;
  padding: 4px 10px;
  border-radius: 14px;
  font-size: 0.78rem;
  font-weight: 600;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  transition: all 0.2s;
}
.btn-export-inline:hover:not(:disabled) { background: #059669; }
.btn-export-inline:disabled { background: #94a3b8; cursor: not-allowed; }
</style>
