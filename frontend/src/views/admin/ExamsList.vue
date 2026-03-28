<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import api from '../../services/api'
import ExamUploadModal from '../../components/ExamUploadModal.vue'
import ExamTypeIcon from '../../components/ExamTypeIcon.vue'

const router = useRouter()

const exams = ref([])
const examTypes = ref([])
const loading = ref(true)
const error = ref(null)
const showUploadModal = ref(false)
const deletingId = ref(null)

const fetchExams = async () => {
  loading.value = true
  error.value = null
  try {
    const [examsRes, typesRes] = await Promise.all([
      api.get('/exams/'),
      api.get('/exams/types/').catch(() => ({ data: [] }))
    ])
    exams.value = Array.isArray(examsRes.data) ? examsRes.data : (examsRes.data.results || [])
    examTypes.value = Array.isArray(typesRes.data) ? typesRes.data : (typesRes.data.results || [])
  } catch (e) {
    console.error('ExamsList: Failed to fetch exams', e)
    error.value = e.response?.data?.detail || e.message || 'Erreur lors du chargement des examens.'
  } finally {
    loading.value = false
  }
}

const examsByType = computed(() => {
  const groups = {}
  const others = []

  ;(exams.value || []).forEach(exam => {
    if (!exam || typeof exam !== 'object') return

    const typeDetails = exam.exam_type_details
    if (typeDetails && (typeDetails.id || exam.exam_type)) {
      const typeId = typeDetails.id || exam.exam_type
      if (!groups[typeId]) {
        groups[typeId] = {
          details: {
            id: typeId,
            name: typeDetails?.name || 'Inconnu',
            icon: typeDetails?.icon || '',
            color: typeDetails?.color || '#64748b',
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
      details: { id: null, name: 'Autres Examens', icon: '', color: '#64748b' },
      exams: others
    })
  }
  return result
})

const formatDate = (value) => {
  if (!value) return '—'
  return new Date(value).toLocaleDateString('fr-FR', { year: 'numeric', month: 'short', day: 'numeric' })
}

const getCopiesCount = (exam) => exam.copies_count ?? exam.total_copies ?? 0

const getDispatchLabel = (exam) => {
  if (exam.is_dispatched) return { label: 'Dispatché', cls: 'bg-emerald-100 text-emerald-700' }
  if (getCopiesCount(exam) > 0) return { label: 'Non dispatché', cls: 'bg-amber-100 text-amber-700' }
  return { label: 'Vide', cls: 'bg-slate-100 text-slate-500' }
}

const openExam = (examId) => {
  router.push(`/admin/exams/${examId}/overview`)
}

const goToNewExam = () => {
  router.push('/admin/exams/new')
}

const deleteExam = async (exam) => {
  const confirmed = window.confirm(`Supprimer l'examen « ${exam.name} » ? Cette action est irréversible.`)
  if (!confirmed) return

  deletingId.value = exam.id
  try {
    await api.delete(`/exams/${exam.id}/`)
    exams.value = exams.value.filter(e => e.id !== exam.id)
  } catch (e) {
    console.error('ExamsList: Failed to delete exam', e)
    alert(e.response?.data?.detail || 'Erreur lors de la suppression.')
  } finally {
    deletingId.value = null
  }
}

const handleExamUploaded = async () => {
  showUploadModal.value = false
  await fetchExams()
}

onMounted(fetchExams)
</script>

<template>
  <div class="min-h-screen bg-slate-50">
    <!-- Header -->
    <header class="bg-white border-b border-slate-200 px-6 py-4">
      <div class="max-w-7xl mx-auto flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 class="text-2xl font-bold text-slate-800 tracking-tight">Examens</h1>
          <p class="text-sm text-slate-500 mt-0.5">Gestion de tous les examens</p>
        </div>
        <div class="flex items-center gap-2">
          <button
            class="inline-flex items-center gap-2 px-4 py-2 rounded-lg border border-slate-300 bg-white text-slate-700 text-sm font-medium hover:bg-slate-50 active:bg-slate-100 transition-colors"
            @click="showUploadModal = true"
          >
            <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12"/>
            </svg>
            Importer Examen
          </button>
          <button
            class="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-indigo-600 text-white text-sm font-medium hover:bg-indigo-700 active:bg-indigo-800 transition-colors shadow-sm"
            @click="goToNewExam"
          >
            <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4"/>
            </svg>
            Nouvel Examen
          </button>
        </div>
      </div>
    </header>

    <main class="max-w-7xl mx-auto px-6 py-8 space-y-8">

      <!-- Error banner -->
      <div
        v-if="error"
        class="flex items-center gap-3 bg-red-50 border border-red-200 text-red-700 rounded-lg px-4 py-3 text-sm"
      >
        <svg class="w-4 h-4 shrink-0" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
          <circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>
        </svg>
        {{ error }}
        <button class="ml-auto text-red-500 hover:text-red-700 font-medium" @click="fetchExams">Réessayer</button>
      </div>

      <!-- Loading skeleton -->
      <div v-if="loading" class="space-y-6">
        <div v-for="g in 2" :key="g" class="space-y-3">
          <div class="h-4 bg-slate-200 rounded w-40 animate-pulse"></div>
          <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            <div v-for="i in 3" :key="i" class="bg-white rounded-xl border border-slate-200 p-5 animate-pulse">
              <div class="h-4 bg-slate-200 rounded w-3/4 mb-3"></div>
              <div class="h-3 bg-slate-100 rounded w-1/2 mb-2"></div>
              <div class="h-3 bg-slate-100 rounded w-1/3"></div>
            </div>
          </div>
        </div>
      </div>

      <!-- Empty state -->
      <div
        v-else-if="!loading && !error && exams.length === 0"
        class="bg-white rounded-xl border border-slate-200 p-16 text-center shadow-sm"
      >
        <svg class="w-12 h-12 text-slate-300 mx-auto mb-4" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
        </svg>
        <p class="text-slate-600 font-medium text-lg">Aucun examen</p>
        <p class="text-slate-400 text-sm mt-1 mb-6">Commencez par créer ou importer un examen.</p>
        <button
          class="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-indigo-600 text-white text-sm font-medium hover:bg-indigo-700 transition-colors"
          @click="goToNewExam"
        >
          <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4"/>
          </svg>
          Nouvel Examen
        </button>
      </div>

      <!-- Grouped by type -->
      <div v-else-if="!loading" class="space-y-8">
        <section v-for="group in examsByType" :key="group.details.id ?? 'others'">
          <!-- Group header -->
          <div class="flex items-center gap-2 mb-4">
            <span
              class="inline-flex items-center justify-center w-7 h-7 rounded-lg text-white text-sm shrink-0"
              :style="{ backgroundColor: group.details.color }"
            >
              <ExamTypeIcon :icon="group.details.icon" :size="14" />
            </span>
            <h2 class="text-base font-semibold text-slate-700">{{ group.details.name }}</h2>
            <span class="text-xs text-slate-400 font-medium bg-slate-100 px-2 py-0.5 rounded-full">
              {{ group.exams.length }} examen{{ group.exams.length > 1 ? 's' : '' }}
            </span>
          </div>

          <!-- Exam cards -->
          <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            <div
              v-for="exam in group.exams"
              :key="exam.id"
              class="bg-white rounded-xl border border-slate-200 p-5 shadow-sm hover:shadow-md hover:border-indigo-200 transition-all duration-150 group"
            >
              <!-- Card header -->
              <div class="flex items-start justify-between gap-2 mb-3">
                <h3 class="font-semibold text-slate-800 text-sm leading-snug line-clamp-2">
                  {{ exam.name || 'Examen sans nom' }}
                </h3>
                <span
                  class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium shrink-0"
                  :class="getDispatchLabel(exam).cls"
                >
                  {{ getDispatchLabel(exam).label }}
                </span>
              </div>

              <!-- Meta -->
              <div class="space-y-1.5 mb-4">
                <div class="flex items-center gap-1.5 text-xs text-slate-500">
                  <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
                    <rect x="3" y="4" width="18" height="18" rx="2" ry="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/>
                  </svg>
                  {{ formatDate(exam.date) }}
                </div>
                <div class="flex items-center gap-1.5 text-xs text-slate-500">
                  <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M9 12h6m-6 4h6M7 2h10a2 2 0 012 2v16a2 2 0 01-2 2H7a2 2 0 01-2-2V4a2 2 0 012-2z"/>
                  </svg>
                  <span>{{ getCopiesCount(exam) }} copie{{ getCopiesCount(exam) > 1 ? 's' : '' }}</span>
                </div>
              </div>

              <!-- Actions -->
              <div class="flex items-center gap-2 pt-3 border-t border-slate-100">
                <button
                  class="flex-1 inline-flex items-center justify-center gap-1.5 px-3 py-2 rounded-lg bg-indigo-600 text-white text-xs font-medium hover:bg-indigo-700 active:bg-indigo-800 transition-colors"
                  @click="openExam(exam.id)"
                >
                  <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"/>
                  </svg>
                  Ouvrir
                </button>
                <button
                  class="inline-flex items-center justify-center p-2 rounded-lg text-slate-400 hover:text-red-600 hover:bg-red-50 transition-colors"
                  :class="{ 'opacity-50 cursor-not-allowed': deletingId === exam.id }"
                  :disabled="deletingId === exam.id"
                  :title="`Supprimer ${exam.name}`"
                  @click="deleteExam(exam)"
                >
                  <svg v-if="deletingId !== exam.id" class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/>
                  </svg>
                  <svg v-else class="w-4 h-4 animate-spin" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/>
                  </svg>
                </button>
              </div>
            </div>
          </div>
        </section>
      </div>
    </main>

    <!-- Import Modal -->
    <ExamUploadModal
      :show="showUploadModal"
      @close="showUploadModal = false"
      @uploaded="handleExamUploaded"
    />
  </div>
</template>
