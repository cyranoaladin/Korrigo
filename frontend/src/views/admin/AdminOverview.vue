<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../../stores/auth'
import api from '../../services/api'
import AppIcon from '../../icons/AppIcon.vue'

const authStore = useAuthStore()
const router = useRouter()

const exams = ref([])
const globalStats = ref(null)
const loading = ref(true)
const error = ref(null)

const fetchExams = async () => {
  loading.value = true
  error.value = null
  try {
    const [examsResult, statsResult] = await Promise.allSettled([
      api.get('/exams/'),
      api.get('/exams/global-stats/'),
    ])

    // Exams are required — if this fails, show the error
    if (examsResult.status === 'fulfilled') {
      exams.value = Array.isArray(examsResult.value.data)
        ? examsResult.value.data
        : (examsResult.value.data.results || [])
    } else {
      const e = examsResult.reason
      console.error('AdminOverview: Failed to fetch exams', e)
      error.value = e.response?.data?.detail || e.message || 'Erreur lors du chargement des examens.'
    }

    // Global stats are optional — graceful degradation if endpoint is missing
    if (statsResult.status === 'fulfilled') {
      globalStats.value = statsResult.value.data
    }
  } catch (e) {
    console.error('AdminOverview: Unexpected error', e)
    error.value = e.message || 'Erreur inattendue.'
  } finally {
    loading.value = false
  }
}

const totalExams = computed(() => globalStats.value?.total_exams ?? exams.value.length)

const totalCopies = computed(() =>
  globalStats.value?.total_copies ?? exams.value.reduce((sum, exam) => {
    const count = exam.copies_count ?? exam.total_copies ?? 0
    return sum + count
  }, 0)
)

const copiesByStatus = computed(() => {
  if (globalStats.value?.copies_by_status) {
    return {
      READY: globalStats.value.copies_by_status.READY ?? 0,
      IN_PROGRESS: globalStats.value.copies_by_status.IN_PROGRESS ?? 0,
      FINALIZED: globalStats.value.copies_by_status.FINALIZED ?? 0,
    }
  }
  const counts = { READY: 0, IN_PROGRESS: 0, FINALIZED: 0 }
  exams.value.forEach(exam => {
    if (exam.copies_by_status) {
      counts.READY += exam.copies_by_status.READY ?? 0
      counts.IN_PROGRESS += exam.copies_by_status.IN_PROGRESS ?? 0
      counts.FINALIZED += exam.copies_by_status.FINALIZED ?? 0
    }
  })
  return counts
})

const studentsCount = computed(() => globalStats.value?.students_count ?? 0)
const releasedExamsCount = computed(() => globalStats.value?.exams_with_results_released ?? 0)
const correctorsCount = computed(() => globalStats.value?.correctors_count ?? 0)

const formatDate = (value) => {
  if (!value) return '—'
  return new Date(value).toLocaleDateString('fr-FR', { year: 'numeric', month: 'short', day: 'numeric' })
}

const getExamCounts = (exam) => {
  const total = exam.copies_count ?? exam.total_copies ?? 0
  const finalized = exam.copies_by_status?.FINALIZED ?? 0
  const inProgress = exam.copies_by_status?.IN_PROGRESS ?? 0
  const ready = exam.copies_by_status?.READY ?? 0
  return { total, finalized, inProgress, ready }
}

const getProgressPercent = (exam) => {
  const { total, finalized } = getExamCounts(exam)
  if (!total) return 0
  return Math.round((finalized / total) * 100)
}

const getInProgressPercent = (exam) => {
  const { total, inProgress } = getExamCounts(exam)
  if (!total) return 0
  return Math.round((inProgress / total) * 100)
}

const getFinalizedCount = (exam) => {
  return getExamCounts(exam).finalized
}

const getExamStatusLabel = (exam) => {
  const { total, finalized, inProgress } = getExamCounts(exam)
  if (!total) return { label: 'Vide', cls: 'bg-slate-100 text-slate-600' }
  if (finalized === total) return { label: 'Finalisé', cls: 'bg-emerald-100 text-emerald-700' }
  if (finalized > 0 || inProgress > 0) return { label: 'En cours', cls: 'bg-amber-100 text-amber-700' }
  return { label: 'Non démarré', cls: 'bg-slate-100 text-slate-600' }
}

const goToExam = (examId) => {
  router.push(`/admin/exams/${examId}/overview`)
}

onMounted(fetchExams)
</script>

<template>
  <div data-testid="admin-dashboard" class="min-h-screen bg-slate-50">
    <!-- Header -->
    <header class="bg-white border-b border-slate-200 px-6 py-4">
      <div class="max-w-7xl mx-auto flex items-center justify-between">
        <div>
          <h1 data-testid="admin-dashboard-title" class="text-2xl font-bold text-slate-800 tracking-tight">Vue d'ensemble</h1>
          <p class="text-sm text-slate-500 mt-0.5">Tableau de bord administrateur</p>
        </div>
        <div class="flex items-center gap-3">
          <span class="text-sm text-slate-600 font-medium">{{ authStore.user?.username }}</span>
          <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-indigo-100 text-indigo-700 tracking-wide uppercase">
            Admin
          </span>
        </div>
      </div>
    </header>

    <main class="max-w-7xl mx-auto px-6 py-8 space-y-8">

      <!-- Error banner -->
      <div
        v-if="error"
        class="flex items-center gap-3 bg-red-50 border border-red-200 text-red-700 rounded-lg px-4 py-3 text-sm"
      >
        <AppIcon name="alert" :size="16" class="shrink-0" />
        {{ error }}
        <button class="ml-auto text-red-500 hover:text-red-700 font-medium" @click="fetchExams">Réessayer</button>
      </div>

      <!-- Global stats cards -->
      <section>
        <h2 class="text-sm font-semibold text-slate-500 uppercase tracking-wider mb-4">Statistiques globales</h2>

        <div v-if="loading" class="grid grid-cols-2 gap-4 sm:grid-cols-4 xl:grid-cols-7">
          <div v-for="i in 7" :key="i" class="bg-white rounded-xl border border-slate-200 p-5 animate-pulse">
            <div class="h-3 bg-slate-200 rounded w-2/3 mb-3"></div>
            <div class="h-7 bg-slate-200 rounded w-1/2"></div>
          </div>
        </div>

        <div v-else class="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-7">
          <!-- Total exams -->
          <div class="bg-white rounded-xl border border-slate-200 p-5 shadow-sm">
            <div class="flex items-center gap-2 mb-2">
              <AppIcon name="exam" :size="14" class="text-slate-400" />
              <p class="text-xs font-medium text-slate-500 uppercase tracking-wide">Examens</p>
            </div>
            <p class="text-3xl font-bold text-slate-800">{{ totalExams }}</p>
            <p class="text-xs text-slate-400 mt-1">au total</p>
          </div>

          <!-- Total copies -->
          <div class="bg-white rounded-xl border border-slate-200 p-5 shadow-sm">
            <div class="flex items-center gap-2 mb-2">
              <AppIcon name="document" :size="14" class="text-slate-400" />
              <p class="text-xs font-medium text-slate-500 uppercase tracking-wide">Copies</p>
            </div>
            <p class="text-3xl font-bold text-slate-800">{{ totalCopies }}</p>
            <p class="text-xs text-slate-400 mt-1">au total</p>
          </div>

          <!-- READY -->
          <div class="bg-white rounded-xl border border-slate-200 p-5 shadow-sm">
            <div class="flex items-center gap-2 mb-2">
              <AppIcon name="success" :size="14" class="text-blue-400" />
              <p class="text-xs font-medium text-slate-500 uppercase tracking-wide">Prêtes</p>
            </div>
            <p class="text-3xl font-bold text-blue-600">{{ copiesByStatus.READY }}</p>
            <p class="text-xs text-slate-400 mt-1">copies READY</p>
          </div>

          <!-- IN_PROGRESS -->
          <div class="bg-white rounded-xl border border-slate-200 p-5 shadow-sm">
            <div class="flex items-center gap-2 mb-2">
              <AppIcon name="trending" :size="14" class="text-amber-400" />
              <p class="text-xs font-medium text-slate-500 uppercase tracking-wide">En cours</p>
            </div>
            <p class="text-3xl font-bold text-amber-500">{{ copiesByStatus.IN_PROGRESS }}</p>
            <p class="text-xs text-slate-400 mt-1">copies IN_PROGRESS</p>
          </div>

          <!-- FINALIZED -->
          <div class="bg-white rounded-xl border border-slate-200 p-5 shadow-sm">
            <div class="flex items-center gap-2 mb-2">
              <AppIcon name="success" :size="14" class="text-emerald-400" />
              <p class="text-xs font-medium text-slate-500 uppercase tracking-wide">Finalisées</p>
            </div>
            <p class="text-3xl font-bold text-emerald-600">{{ copiesByStatus.FINALIZED }}</p>
            <p class="text-xs text-slate-400 mt-1">copies FINALIZED</p>
          </div>

          <div class="bg-white rounded-xl border border-slate-200 p-5 shadow-sm">
            <div class="flex items-center gap-2 mb-2">
              <AppIcon name="student" :size="14" class="text-slate-400" />
              <p class="text-xs font-medium text-slate-500 uppercase tracking-wide">Élèves</p>
            </div>
            <p class="text-3xl font-bold text-slate-800">{{ studentsCount }}</p>
            <p class="text-xs text-slate-400 mt-1">profils élèves</p>
          </div>

          <div class="bg-white rounded-xl border border-slate-200 p-5 shadow-sm">
            <div class="flex items-center gap-2 mb-2">
              <AppIcon name="result" :size="14" class="text-indigo-400" />
              <p class="text-xs font-medium text-slate-500 uppercase tracking-wide">Résultats publiés</p>
            </div>
            <p class="text-3xl font-bold text-indigo-600">{{ releasedExamsCount }}</p>
            <p class="text-xs text-slate-400 mt-1">examens publiés</p>
          </div>

          <div class="bg-white rounded-xl border border-slate-200 p-5 shadow-sm">
            <div class="flex items-center gap-2 mb-2">
              <AppIcon name="teacher" :size="14" class="text-slate-400" />
              <p class="text-xs font-medium text-slate-500 uppercase tracking-wide">Correcteurs</p>
            </div>
            <p class="text-3xl font-bold text-slate-800">{{ correctorsCount }}</p>
            <p class="text-xs text-slate-400 mt-1">enseignants actifs</p>
          </div>
        </div>
      </section>

      <!-- Exams table -->
      <section>
        <h2 class="text-sm font-semibold text-slate-500 uppercase tracking-wider mb-4">Liste des examens</h2>

        <!-- Loading skeleton -->
        <div v-if="loading" class="bg-white rounded-xl border border-slate-200 overflow-hidden shadow-sm">
          <div v-for="i in 4" :key="i" class="flex items-center gap-4 px-6 py-4 border-b border-slate-100 last:border-0 animate-pulse">
            <div class="h-4 bg-slate-200 rounded w-1/4"></div>
            <div class="h-4 bg-slate-200 rounded w-1/6"></div>
            <div class="h-4 bg-slate-200 rounded w-1/6"></div>
            <div class="h-4 bg-slate-200 rounded w-1/5 ml-auto"></div>
          </div>
        </div>

        <!-- Empty state -->
        <div
          v-else-if="!error && exams.length === 0"
          class="bg-white rounded-xl border border-slate-200 p-12 text-center shadow-sm"
        >
          <AppIcon name="empty" :size="40" class="text-slate-300 mx-auto mb-3" />
          <p class="text-slate-500 font-medium">Aucun examen disponible</p>
          <p class="text-slate-400 text-sm mt-1">Les examens créés apparaîtront ici.</p>
        </div>

        <!-- Table -->
        <div v-else-if="!loading" class="bg-white rounded-xl border border-slate-200 overflow-hidden shadow-sm">
          <div class="overflow-x-auto">
            <table class="w-full text-sm">
              <thead>
                <tr class="border-b border-slate-200 bg-slate-50">
                  <th class="px-6 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Nom</th>
                  <th class="px-6 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Type</th>
                  <th class="px-6 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Date</th>
                  <th class="px-6 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Copies</th>
                  <th class="px-6 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider w-48">Progression</th>
                  <th class="px-6 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Statut</th>
                  <th class="px-6 py-3 text-right text-xs font-semibold text-slate-500 uppercase tracking-wider">Actions</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-slate-100">
                <tr
                  v-for="exam in exams"
                  :key="exam.id"
                  class="hover:bg-slate-50 transition-colors"
                >
                  <td class="px-6 py-4 font-medium text-slate-800 max-w-xs truncate">
                    {{ exam.name || '—' }}
                  </td>
                  <td class="px-6 py-4 text-slate-600">
                    {{ exam.exam_type_details?.name || '—' }}
                  </td>
                  <td class="px-6 py-4 text-slate-500 whitespace-nowrap">
                    {{ formatDate(exam.date) }}
                  </td>
                  <td class="px-6 py-4 text-slate-600 whitespace-nowrap">
                    <span class="font-medium text-emerald-600">{{ getExamCounts(exam).finalized }}</span>
                    <span v-if="getExamCounts(exam).inProgress > 0" class="text-amber-500 text-xs ml-1">(+{{ getExamCounts(exam).inProgress }} en cours)</span>
                    <span class="text-slate-400"> / {{ getExamCounts(exam).total }}</span>
                  </td>
                  <td class="px-6 py-4">
                    <div class="flex items-center gap-2">
                      <div class="flex-1 bg-slate-200 rounded-full h-1.5 overflow-hidden flex">
                        <div
                          class="h-1.5 bg-emerald-500 transition-all duration-300"
                          :style="{ width: getProgressPercent(exam) + '%' }"
                        ></div>
                        <div
                          class="h-1.5 bg-amber-400 transition-all duration-300"
                          :style="{ width: getInProgressPercent(exam) + '%' }"
                        ></div>
                      </div>
                      <span class="text-xs text-slate-500 w-8 text-right">{{ getProgressPercent(exam) }}%</span>
                    </div>
                  </td>
                  <td class="px-6 py-4">
                    <span
                      class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium"
                      :class="getExamStatusLabel(exam).cls"
                    >
                      {{ getExamStatusLabel(exam).label }}
                    </span>
                  </td>
                  <td class="px-6 py-4 text-right">
                    <button
                      class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-indigo-600 text-white text-xs font-medium hover:bg-indigo-700 active:bg-indigo-800 transition-colors"
                      @click="goToExam(exam.id)"
                    >
                      <AppIcon name="view" :size="14" />
                      Voir
                    </button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </section>
    </main>
  </div>
</template>
