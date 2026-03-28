<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../../stores/auth'
import api from '../../services/api'

const authStore = useAuthStore()
const router = useRouter()

const exams = ref([])
const loading = ref(true)
const error = ref(null)

const fetchExams = async () => {
  loading.value = true
  error.value = null
  try {
    const res = await api.get('/exams/')
    exams.value = Array.isArray(res.data) ? res.data : (res.data.results || [])
  } catch (e) {
    console.error('AdminOverview: Failed to fetch exams', e)
    error.value = e.response?.data?.detail || e.message || 'Erreur lors du chargement des examens.'
  } finally {
    loading.value = false
  }
}

const totalExams = computed(() => exams.value.length)

const totalCopies = computed(() =>
  exams.value.reduce((sum, exam) => {
    const count = exam.copies_count ?? exam.total_copies ?? 0
    return sum + count
  }, 0)
)

const copiesByStatus = computed(() => {
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

const formatDate = (value) => {
  if (!value) return '—'
  return new Date(value).toLocaleDateString('fr-FR', { year: 'numeric', month: 'short', day: 'numeric' })
}

const getProgressPercent = (exam) => {
  const total = exam.copies_count ?? exam.total_copies ?? 0
  if (!total) return 0
  const finalized = exam.copies_by_status?.FINALIZED ?? exam.finalized_copies ?? 0
  return Math.round((finalized / total) * 100)
}

const getFinalizedCount = (exam) => {
  return exam.copies_by_status?.FINALIZED ?? exam.finalized_copies ?? 0
}

const getExamStatusLabel = (exam) => {
  const pct = getProgressPercent(exam)
  if (pct === 100) return { label: 'Finalisé', cls: 'bg-emerald-100 text-emerald-700' }
  if (pct > 0) return { label: 'En cours', cls: 'bg-amber-100 text-amber-700' }
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
        <svg class="w-4 h-4 shrink-0" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
          <circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>
        </svg>
        {{ error }}
        <button class="ml-auto text-red-500 hover:text-red-700 font-medium" @click="fetchExams">Réessayer</button>
      </div>

      <!-- Global stats cards -->
      <section>
        <h2 class="text-sm font-semibold text-slate-500 uppercase tracking-wider mb-4">Statistiques globales</h2>

        <div v-if="loading" class="grid grid-cols-2 gap-4 sm:grid-cols-4">
          <div v-for="i in 5" :key="i" class="bg-white rounded-xl border border-slate-200 p-5 animate-pulse">
            <div class="h-3 bg-slate-200 rounded w-2/3 mb-3"></div>
            <div class="h-7 bg-slate-200 rounded w-1/2"></div>
          </div>
        </div>

        <div v-else class="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-5">
          <!-- Total exams -->
          <div class="bg-white rounded-xl border border-slate-200 p-5 shadow-sm">
            <p class="text-xs font-medium text-slate-500 uppercase tracking-wide mb-2">Examens</p>
            <p class="text-3xl font-bold text-slate-800">{{ totalExams }}</p>
            <p class="text-xs text-slate-400 mt-1">au total</p>
          </div>

          <!-- Total copies -->
          <div class="bg-white rounded-xl border border-slate-200 p-5 shadow-sm">
            <p class="text-xs font-medium text-slate-500 uppercase tracking-wide mb-2">Copies</p>
            <p class="text-3xl font-bold text-slate-800">{{ totalCopies }}</p>
            <p class="text-xs text-slate-400 mt-1">au total</p>
          </div>

          <!-- READY -->
          <div class="bg-white rounded-xl border border-slate-200 p-5 shadow-sm">
            <p class="text-xs font-medium text-slate-500 uppercase tracking-wide mb-2">Prêtes</p>
            <p class="text-3xl font-bold text-blue-600">{{ copiesByStatus.READY }}</p>
            <p class="text-xs text-slate-400 mt-1">copies READY</p>
          </div>

          <!-- IN_PROGRESS -->
          <div class="bg-white rounded-xl border border-slate-200 p-5 shadow-sm">
            <p class="text-xs font-medium text-slate-500 uppercase tracking-wide mb-2">En cours</p>
            <p class="text-3xl font-bold text-amber-500">{{ copiesByStatus.IN_PROGRESS }}</p>
            <p class="text-xs text-slate-400 mt-1">copies IN_PROGRESS</p>
          </div>

          <!-- FINALIZED -->
          <div class="bg-white rounded-xl border border-slate-200 p-5 shadow-sm">
            <p class="text-xs font-medium text-slate-500 uppercase tracking-wide mb-2">Finalisées</p>
            <p class="text-3xl font-bold text-emerald-600">{{ copiesByStatus.FINALIZED }}</p>
            <p class="text-xs text-slate-400 mt-1">copies FINALIZED</p>
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
          <svg class="w-10 h-10 text-slate-300 mx-auto mb-3" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
          </svg>
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
                    <span class="font-medium">{{ getFinalizedCount(exam) }}</span>
                    <span class="text-slate-400"> / {{ exam.copies_count ?? exam.total_copies ?? 0 }}</span>
                  </td>
                  <td class="px-6 py-4">
                    <div class="flex items-center gap-2">
                      <div class="flex-1 bg-slate-200 rounded-full h-1.5 overflow-hidden">
                        <div
                          class="h-1.5 rounded-full transition-all duration-300"
                          :class="getProgressPercent(exam) === 100 ? 'bg-emerald-500' : getProgressPercent(exam) > 0 ? 'bg-amber-400' : 'bg-slate-300'"
                          :style="{ width: getProgressPercent(exam) + '%' }"
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
                      <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/>
                        <path stroke-linecap="round" stroke-linejoin="round" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"/>
                      </svg>
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
