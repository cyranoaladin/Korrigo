<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import api from '../../services/api'
import ExamTypeIcon from '../../components/ExamTypeIcon.vue'
import JuryReportsModal from '../../components/JuryReportsModal.vue'

const route = useRoute()
const router = useRouter()
const examId = route.params.examId

const loading = ref(true)
const error = ref(null)
const exam = ref(null)
const copiesStats = ref({ total: 0, READY: 0, IN_PROGRESS: 0, FINALIZED: 0 })

// Toast notification
const toast = ref({ show: false, message: '', type: 'success' })
let toastTimer = null

const showToast = (message, type = 'success') => {
  if (toastTimer) clearTimeout(toastTimer)
  toast.value = { show: true, message, type }
  toastTimer = setTimeout(() => { toast.value.show = false }, 4000)
}

// Jury reports modal
const showJuryModal = ref(false)

// Publish loading
const publishing = ref(false)

const fetchExam = async () => {
  const res = await api.get(`/exams/${examId}/`)
  exam.value = res.data
}

const fetchCopies = async () => {
  // Fetch first page to get count and status breakdown
  const res = await api.get(`/exams/${examId}/copies/`)
  const data = res.data

  // Support both paginated ({ count, results }) and plain array responses
  const results = Array.isArray(data) ? data : (data.results || [])
  const total = Array.isArray(data) ? data.length : (data.count ?? results.length)

  const breakdown = { READY: 0, IN_PROGRESS: 0, FINALIZED: 0 }
  results.forEach(c => {
    if (c.status in breakdown) breakdown[c.status]++
  })

  // If paginated and there are more pages, fetch them all to get full breakdown
  if (!Array.isArray(data) && data.next) {
    let nextUrl = data.next.replace(/^https?:\/\/[^/]+\/api/, '')
    while (nextUrl) {
      const pageRes = await api.get(nextUrl)
      const pageData = pageRes.data
      const pageResults = pageData.results || []
      pageResults.forEach(c => {
        if (c.status in breakdown) breakdown[c.status]++
      })
      nextUrl = pageData.next ? pageData.next.replace(/^https?:\/\/[^/]+\/api/, '') : null
    }
  }

  copiesStats.value = { total, ...breakdown }
}

const loadData = async () => {
  loading.value = true
  error.value = null
  try {
    await Promise.all([fetchExam(), fetchCopies()])
  } catch (e) {
    error.value = e.response?.data?.detail || 'Erreur lors du chargement.'
  } finally {
    loading.value = false
  }
}

const publishResults = async () => {
  if (!confirm('Publier les résultats ? Les élèves pourront accéder à leurs copies corrigées.')) return
  publishing.value = true
  try {
    await api.post(`/exams/${examId}/publish/`)
    showToast('Résultats publiés avec succès.', 'success')
  } catch (e) {
    showToast(e.response?.data?.detail || 'Erreur lors de la publication.', 'error')
  } finally {
    publishing.value = false
  }
}

const progressPercent = computed(() => {
  const total = copiesStats.value.total
  if (!total) return 0
  return Math.round((copiesStats.value.FINALIZED / total) * 100)
})

const formatDate = (d) => {
  if (!d) return '—'
  return new Date(d).toLocaleDateString('fr-FR', { day: '2-digit', month: 'long', year: 'numeric' })
}

const quickActions = [
  { label: 'Copies', icon: '📄', path: (id) => `/admin/exams/${id}/copies` },
  { label: 'Identification', icon: '🔍', path: (id) => `/admin/exams/${id}/identification` },
  { label: 'Correcteurs', icon: '👥', path: (id) => `/admin/exams/${id}/correctors` },
  { label: 'Barème', icon: '📏', path: (id) => `/admin/exams/${id}/scale` },
  { label: 'Résultats', icon: '📊', path: (id) => `/admin/exams/${id}/results` },
]

onMounted(loadData)
</script>

<template>
  <div class="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50/30 to-indigo-50/20 font-sans">
    <!-- Header -->
    <header class="bg-white/80 backdrop-blur-xl border-b border-slate-200/60 sticky top-0 z-50">
      <div class="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        <div class="flex items-center gap-3">
          <button
            class="p-2 rounded-lg hover:bg-slate-100 transition-colors"
            @click="router.push({ name: 'AdminDashboard' })"
          >
            <svg xmlns="http://www.w3.org/2000/svg" class="w-5 h-5 text-slate-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M15 19l-7-7 7-7" />
            </svg>
          </button>
          <div>
            <h1 class="text-lg font-bold text-slate-800">Vue d'ensemble de l'examen</h1>
            <p
              v-if="exam"
              class="text-xs text-slate-400"
            >
              {{ exam.name }}
            </p>
          </div>
        </div>
        <div class="flex items-center gap-2">
          <button
            class="inline-flex items-center gap-2 px-4 py-2 bg-white border border-slate-200 text-slate-700 rounded-lg text-sm font-medium hover:bg-slate-50 transition-colors"
            @click="showJuryModal = true"
          >
            <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            Rapports de Jury
          </button>
          <button
            :disabled="publishing"
            class="inline-flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            @click="publishResults"
          >
            <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
              <path stroke-linecap="round" stroke-linejoin="round" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
            </svg>
            {{ publishing ? 'Publication…' : 'Publier les résultats' }}
          </button>
        </div>
      </div>
    </header>

    <main class="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
      <!-- Loading -->
      <div
        v-if="loading"
        class="flex justify-center py-20"
      >
        <div class="w-8 h-8 border-4 border-indigo-200 border-t-indigo-600 rounded-full animate-spin" />
      </div>

      <!-- Error -->
      <div
        v-else-if="error"
        class="bg-red-50 rounded-2xl p-8 text-center ring-1 ring-red-100"
      >
        <p class="text-red-600 font-medium">
          {{ error }}
        </p>
        <button
          class="mt-4 px-4 py-2 bg-red-600 text-white rounded-lg text-sm hover:bg-red-700"
          @click="loadData"
        >
          Réessayer
        </button>
      </div>

      <template v-else-if="exam">
        <!-- Exam Info Card -->
        <div class="bg-white rounded-2xl shadow-sm ring-1 ring-slate-100 p-6">
          <div class="flex items-start gap-4">
            <div
              class="w-14 h-14 rounded-xl flex items-center justify-center text-white flex-shrink-0"
              :style="exam.exam_type_details?.color ? `background-color: ${exam.exam_type_details.color}` : 'background-color: #6366f1'"
            >
              <ExamTypeIcon
                :icon="exam.exam_type_details?.icon || 'graduation-cap'"
                :size="28"
              />
            </div>
            <div class="flex-1 min-w-0">
              <div class="flex items-center gap-2 flex-wrap">
                <h2 class="text-xl font-bold text-slate-800">
                  {{ exam.name }}
                </h2>
                <span
                  v-if="exam.exam_type_details?.name"
                  class="px-2 py-0.5 rounded-full text-xs font-medium bg-indigo-50 text-indigo-700 ring-1 ring-indigo-100"
                >
                  {{ exam.exam_type_details.name }}
                </span>
              </div>
              <div class="mt-2 flex flex-wrap gap-4 text-sm text-slate-500">
                <span
                  v-if="exam.date"
                  class="flex items-center gap-1"
                >
                  <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                    <rect x="3" y="4" width="18" height="18" rx="2" ry="2" /><line x1="16" y1="2" x2="16" y2="6" /><line x1="8" y1="2" x2="8" y2="6" /><line x1="3" y1="10" x2="21" y2="10" />
                  </svg>
                  {{ formatDate(exam.date) }}
                </span>
                <span
                  v-if="exam.exam_type"
                  class="flex items-center gap-1"
                >
                  <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.994 1.994 0 013 12V7a4 4 0 014-4z" />
                  </svg>
                  Type : {{ exam.exam_type_details?.name || exam.exam_type }}
                </span>
              </div>
            </div>
          </div>
        </div>

        <!-- Quick Actions -->
        <div class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
          <button
            v-for="action in quickActions"
            :key="action.label"
            class="bg-white rounded-xl shadow-sm ring-1 ring-slate-100 p-4 flex flex-col items-center gap-2 hover:bg-indigo-50/60 hover:ring-indigo-200 transition-all group"
            @click="router.push(action.path(examId))"
          >
            <span class="text-2xl">{{ action.icon }}</span>
            <span class="text-sm font-medium text-slate-700 group-hover:text-indigo-700">{{ action.label }}</span>
          </button>
        </div>

        <!-- Copies Statistics -->
        <div class="bg-white rounded-2xl shadow-sm ring-1 ring-slate-100 p-6">
          <h3 class="text-base font-semibold text-slate-700 mb-4">
            Statistiques des copies
          </h3>
          <div class="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-6">
            <div class="bg-slate-50 rounded-xl p-4">
              <p class="text-xs text-slate-400 uppercase font-semibold mb-1">
                Total
              </p>
              <p class="text-3xl font-bold text-slate-800">
                {{ copiesStats.total }}
              </p>
            </div>
            <div class="bg-blue-50 rounded-xl p-4">
              <p class="text-xs text-blue-400 uppercase font-semibold mb-1">
                Prêtes
              </p>
              <p class="text-3xl font-bold text-blue-700">
                {{ copiesStats.READY }}
              </p>
            </div>
            <div class="bg-amber-50 rounded-xl p-4">
              <p class="text-xs text-amber-400 uppercase font-semibold mb-1">
                En cours
              </p>
              <p class="text-3xl font-bold text-amber-700">
                {{ copiesStats.IN_PROGRESS }}
              </p>
            </div>
            <div class="bg-emerald-50 rounded-xl p-4">
              <p class="text-xs text-emerald-400 uppercase font-semibold mb-1">
                Finalisées
              </p>
              <p class="text-3xl font-bold text-emerald-700">
                {{ copiesStats.FINALIZED }}
              </p>
            </div>
          </div>

          <!-- Progress bar -->
          <div>
            <div class="flex items-center justify-between mb-1">
              <span class="text-xs text-slate-500">Progression</span>
              <span class="text-xs font-semibold text-slate-700">{{ progressPercent }}%</span>
            </div>
            <div class="w-full h-3 bg-slate-100 rounded-full overflow-hidden">
              <div
                class="h-3 bg-gradient-to-r from-emerald-400 to-emerald-600 rounded-full transition-all duration-500"
                :style="{ width: progressPercent + '%' }"
              />
            </div>
            <p class="text-xs text-slate-400 mt-1">
              {{ copiesStats.FINALIZED }} / {{ copiesStats.total }} copies finalisées
            </p>
          </div>
        </div>

        <!-- Correctors List -->
        <div class="bg-white rounded-2xl shadow-sm ring-1 ring-slate-100 p-6">
          <div class="flex items-center justify-between mb-4">
            <h3 class="text-base font-semibold text-slate-700">
              Correcteurs assignés
            </h3>
            <button
              class="text-sm text-indigo-600 hover:text-indigo-800 font-medium"
              @click="router.push(`/admin/exams/${examId}/correctors`)"
            >
              Gérer →
            </button>
          </div>

          <div
            v-if="!exam.correctors || exam.correctors.length === 0"
            class="text-center py-6 text-slate-400 text-sm"
          >
            Aucun correcteur assigné pour l'instant.
          </div>

          <div
            v-else
            class="flex flex-wrap gap-2"
          >
            <span
              v-for="corrector in exam.correctors"
              :key="typeof corrector === 'object' ? corrector.id : corrector"
              class="inline-flex items-center gap-1.5 px-3 py-1.5 bg-indigo-50 text-indigo-700 rounded-full text-sm font-medium ring-1 ring-indigo-100"
            >
              <svg xmlns="http://www.w3.org/2000/svg" class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                <path stroke-linecap="round" stroke-linejoin="round" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
              </svg>
              {{ typeof corrector === 'object' ? (corrector.username || corrector.id) : corrector }}
            </span>
          </div>
        </div>
      </template>
    </main>

    <!-- Jury Reports Modal -->
    <JuryReportsModal
      v-if="showJuryModal"
      :exam-id="examId"
      @close="showJuryModal = false"
    />

    <!-- Toast -->
    <transition name="toast">
      <div
        v-if="toast.show"
        class="fixed bottom-6 right-6 z-[100] flex items-center gap-3 px-5 py-3.5 rounded-xl shadow-lg text-white text-sm font-medium"
        :class="toast.type === 'success' ? 'bg-emerald-600' : 'bg-red-600'"
      >
        <svg
          v-if="toast.type === 'success'"
          xmlns="http://www.w3.org/2000/svg"
          class="w-4 h-4"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          stroke-width="2"
        >
          <path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7" />
        </svg>
        <svg
          v-else
          xmlns="http://www.w3.org/2000/svg"
          class="w-4 h-4"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          stroke-width="2"
        >
          <path stroke-linecap="round" stroke-linejoin="round" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        {{ toast.message }}
      </div>
    </transition>
  </div>
</template>

<style scoped>
.toast-enter-active,
.toast-leave-active {
  transition: all 0.3s ease;
}
.toast-enter-from,
.toast-leave-to {
  opacity: 0;
  transform: translateY(12px);
}
</style>
