<script setup>
import { ref, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import api from '../../services/api'
import ExamUploadModal from '../../components/ExamUploadModal.vue'
import { useAutoRefresh } from '../../composables/useAutoRefresh'

const route = useRoute()
const router = useRouter()
const examId = route.params.examId

const loading = ref(true)
const error = ref(null)
const copies = ref([])
const totalCount = ref(0)
const filterStatus = ref('all')
const showUploadModal = ref(false)
const showRotateModal = ref(false)
const rotationInput = ref('')
const rotationLoading = ref(false)

// Toast
const toast = ref({ show: false, message: '', type: 'success' })
let toastTimer = null

const showToast = (message, type = 'success') => {
  if (toastTimer) clearTimeout(toastTimer)
  toast.value = { show: true, message, type }
  toastTimer = setTimeout(() => { toast.value.show = false }, 4000)
}

const exportAnnotations = async () => {
  try {
    const response = await api.get(`/grading/exams/${examId}/export-all-annotations/`, {
      params: { format: 'json' },
    })
    const blob = new Blob([JSON.stringify(response.data, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `exam_${examId}_annotations_${new Date().toISOString().slice(0, 10)}.json`
    link.click()
    URL.revokeObjectURL(url)
    showToast('Export des annotations prêt.', 'success')
  } catch (e) {
    showToast(e.response?.data?.detail || "Échec de l'export des annotations.", 'error')
  }
}

const exportPronote = async () => {
  try {
    const response = await api.get('/grading/my-students/export-csv/', {
      params: { exam_id: examId },
      responseType: 'blob'
    })
    const url = window.URL.createObjectURL(new Blob([response.data]))
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', `PRONOTE_Examen_${examId}.csv`)
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    showToast('Export Pronote réussi.', 'success')
  } catch (e) {
    showToast('Échec de l\'export Pronote.', 'error')
  }
}

const statusLabel = (s) => ({
  READY: 'Prête',
  IN_PROGRESS: 'En cours',
  FINALIZED: 'Finalisée',
  STAGING: 'En attente',
  NO_COPY: 'Sans copie',
}[s] || s)

const statusClass = (s) => ({
  READY: 'bg-blue-50 text-blue-700 ring-1 ring-blue-100',
  IN_PROGRESS: 'bg-amber-50 text-amber-700 ring-1 ring-amber-100',
  FINALIZED: 'bg-emerald-50 text-emerald-700 ring-1 ring-emerald-100',
  STAGING: 'bg-slate-100 text-slate-500 ring-1 ring-slate-200',
  NO_COPY: 'bg-slate-100 text-slate-500 ring-1 ring-slate-200',
}[s] || 'bg-gray-100 text-gray-600')

const fetchCopies = async () => {
  loading.value = true
  error.value = null
  try {
    const res = await api.get(`/exams/${examId}/student-list/`)
    const data = res.data
    if (Array.isArray(data)) {
      copies.value = data
      totalCount.value = data.length
    } else {
      copies.value = data.copies || []
      totalCount.value = data.summary?.total_students ?? copies.value.length
    }
  } catch (e) {
    error.value = e.response?.data?.detail || 'Erreur lors du chargement des copies.'
  } finally {
    loading.value = false
  }
}

const onUploadSuccess = () => {
  showUploadModal.value = false
  showToast('Copies importées avec succès.', 'success')
  fetchCopies()
}

const parseAnonymousIds = (value) => {
  const raw = value
    .split(/[\n,;]+/g)
    .flatMap((chunk) => chunk.split(/\s+/g))
    .map((chunk) => chunk.trim())
    .filter(Boolean)
  return [...new Set(raw)]
}

const rotateLastPages = async () => {
  const anonymousIds = parseAnonymousIds(rotationInput.value)
  if (anonymousIds.length === 0) {
    showToast('Saisissez au moins un anonymat.', 'error')
    return
  }

  rotationLoading.value = true
  try {
    const response = await api.post(`/exams/${examId}/copies/rotate-last-pages/`, {
      anonymous_ids: anonymousIds,
    })
    const rotatedCount = response.data?.rotated_count ?? 0
    const errorCount = response.data?.error_count ?? 0
    showToast(
      errorCount > 0
        ? `${rotatedCount} copie(s) tournée(s), ${errorCount} erreur(s).`
        : `${rotatedCount} copie(s) tournée(s) avec succès.`,
      errorCount > 0 ? 'error' : 'success'
    )
    showRotateModal.value = false
    rotationInput.value = ''
    await fetchCopies()
  } catch (e) {
    showToast(e.response?.data?.detail || 'Échec de la rotation des dernières pages.', 'error')
  } finally {
    rotationLoading.value = false
  }
}

const filteredCopies = computed(() => {
  if (filterStatus.value === 'all') return copies.value
  return copies.value.filter(copy => copy.status === filterStatus.value)
})

useAutoRefresh(fetchCopies)
</script>

<template>
  <div class="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50/30 to-indigo-50/20 font-sans">
    <!-- Header -->
    <header class="bg-white/80 backdrop-blur-xl border-b border-slate-200/60 sticky top-0 z-50">
      <div class="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        <div class="flex items-center gap-3">
          <button
            class="p-2 rounded-lg hover:bg-slate-100 transition-colors"
            @click="router.push(`/admin/exams/${examId}/overview`)"
          >
            <svg xmlns="http://www.w3.org/2000/svg" class="w-5 h-5 text-slate-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M15 19l-7-7 7-7" />
            </svg>
          </button>
          <div>
            <h1 class="text-lg font-bold text-slate-800">Copies</h1>
            <p class="text-xs text-slate-400">
              Examen #{{ examId }}
            </p>
          </div>
        </div>
        <div class="flex items-center gap-2">
          <button
            class="inline-flex items-center gap-2 px-4 py-2 bg-white border border-slate-200 text-slate-700 rounded-lg text-sm font-medium hover:bg-slate-50 transition-colors"
            @click="router.push({ name: 'StapleView', params: { examId } })"
          >
            <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101" />
              <path stroke-linecap="round" stroke-linejoin="round" d="M14.828 14.828a4 4 0 015.656 0l4 4a4 4 0 01-5.656 5.656l-1.101-1.102" />
            </svg>
            Agrafer les copies
          </button>
          <button
            class="inline-flex items-center gap-2 px-4 py-2 bg-white border border-slate-200 text-slate-700 rounded-lg text-sm font-medium hover:bg-slate-50 transition-colors"
            @click="exportAnnotations"
          >
            <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M12 16V4m0 12l-4-4m4 4l4-4M4 20h16" />
            </svg>
            Annotations JSON
          </button>
          <button
            class="inline-flex items-center gap-2 px-4 py-2 bg-white border border-slate-200 text-emerald-700 rounded-lg text-sm font-medium hover:bg-emerald-50 transition-colors"
            @click="exportPronote"
          >
            <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
            </svg>
            Export Pronote
          </button>
          <button
            class="inline-flex items-center gap-2 px-4 py-2 bg-white border border-slate-200 text-slate-700 rounded-lg text-sm font-medium hover:bg-slate-50 transition-colors"
            @click="showRotateModal = true"
          >
            <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0A8.003 8.003 0 019.582 15m10.417 0H15" />
            </svg>
            Rotation dernière page
          </button>
          <button
            class="inline-flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-700 transition-colors"
            @click="showUploadModal = true"
          >
            <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
            </svg>
            Importer des copies
          </button>
        </div>
      </div>
    </header>

    <main class="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
      <!-- Filters & count -->
      <div class="flex flex-wrap items-center gap-3">
        <div class="flex items-center gap-2 bg-white rounded-xl ring-1 ring-slate-200 p-1">
          <button
            v-for="opt in [
            { value: 'all', label: 'Toutes' },
            { value: 'READY', label: 'Prêtes' },
            { value: 'IN_PROGRESS', label: 'En cours' },
            { value: 'FINALIZED', label: 'Finalisées' },
            { value: 'NO_COPY', label: 'Sans copie' },
            ]"
            :key="opt.value"
            class="px-3 py-1.5 rounded-lg text-sm font-medium transition-colors"
            :class="filterStatus === opt.value
              ? 'bg-indigo-600 text-white shadow-sm'
              : 'text-slate-600 hover:bg-slate-100'"
            @click="filterStatus = opt.value"
          >
            {{ opt.label }}
          </button>
        </div>
        <span class="text-sm text-slate-400 ml-auto">
          {{ filteredCopies.length }} élève{{ filteredCopies.length !== 1 ? 's' : '' }}
        </span>
      </div>

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
          @click="fetchCopies"
        >
          Réessayer
        </button>
      </div>

      <!-- Table -->
      <div
        v-else
        class="bg-white rounded-2xl shadow-sm ring-1 ring-slate-100 overflow-hidden"
      >
        <div class="overflow-x-auto">
          <table class="w-full text-sm">
            <thead>
              <tr class="bg-slate-50/80 border-b border-slate-100">
                <th class="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase">
                  Anonymat
                </th>
                <th class="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase">
                  Élève
                </th>
                <th class="px-4 py-3 text-center text-xs font-semibold text-slate-500 uppercase">
                  Statut
                </th>
                <th class="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase">
                  Correcteur
                </th>
                <th class="px-4 py-3 text-center text-xs font-semibold text-slate-500 uppercase">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-50">
                <tr
                v-for="copy in filteredCopies"
                  :key="copy.copy_id || copy.student_id || copy.student_name || copy.anonymous_id || copy.id"
                  class="hover:bg-indigo-50/30 transition-colors"
                >
                <td class="px-4 py-3 font-mono text-xs text-slate-500">
                  {{ copy.anonymous_id || '—' }}
                </td>
                <td class="px-4 py-3 font-medium text-slate-800">
                  {{ copy.student_name || copy.student || '—' }}
                </td>
                <td class="px-4 py-3 text-center">
                  <span
                    class="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium"
                    :class="statusClass(copy.status)"
                  >
                    {{ statusLabel(copy.status) }}
                  </span>
                </td>
                <td class="px-4 py-3 text-slate-500 text-xs">
                  {{ copy.corrector || '—' }}
                </td>
                <td class="px-4 py-3 text-center">
                  <button
                    :disabled="!copy.has_copy"
                    class="inline-flex items-center gap-1 px-3 py-1.5 bg-slate-50 text-slate-700 rounded-lg text-xs font-medium hover:bg-indigo-50 hover:text-indigo-700 ring-1 ring-slate-200 transition-colors"
                    :class="!copy.has_copy ? 'opacity-50 cursor-not-allowed hover:bg-slate-50 hover:text-slate-700' : ''"
                    @click="copy.has_copy && router.push({ name: 'CorrectorDesk', params: { copyId: copy.copy_id || copy.id } })"
                  >
                    <svg xmlns="http://www.w3.org/2000/svg" class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                      <path stroke-linecap="round" stroke-linejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                      <path stroke-linecap="round" stroke-linejoin="round" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                    </svg>
                    {{ copy.has_copy ? 'Voir copie' : 'Pas de copie' }}
                  </button>
                </td>
              </tr>
              <tr v-if="filteredCopies.length === 0">
                <td
                  colspan="5"
                  class="px-4 py-10 text-center text-slate-400"
                >
                  Aucun élève trouvé pour ce filtre.
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

    </main>

    <!-- Upload Modal -->
    <ExamUploadModal
      v-if="showUploadModal"
      :exam-id="examId"
      @close="showUploadModal = false"
      @success="onUploadSuccess"
    />

    <transition name="toast">
      <div
        v-if="showRotateModal"
        class="fixed inset-0 z-[90] bg-slate-900/50 backdrop-blur-sm flex items-center justify-center px-4"
      >
        <div class="w-full max-w-xl bg-white rounded-2xl shadow-2xl ring-1 ring-slate-200 overflow-hidden">
          <div class="px-6 py-4 border-b border-slate-100 flex items-center justify-between">
            <div>
              <h2 class="text-lg font-bold text-slate-800">Rotation dernière page</h2>
              <p class="text-xs text-slate-500">Collez les anonymats à traiter, séparés par des virgules ou des retours ligne.</p>
            </div>
            <button class="p-2 rounded-lg hover:bg-slate-100" @click="showRotateModal = false">
              <svg xmlns="http://www.w3.org/2000/svg" class="w-5 h-5 text-slate-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
          <div class="p-6 space-y-4">
            <textarea
              v-model="rotationInput"
              rows="7"
              class="w-full rounded-xl border border-slate-200 px-4 py-3 text-sm text-slate-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
              placeholder="69CB-010&#10;69CB-074&#10;69CB-094"
            />
            <p class="text-xs text-slate-500">
              Seule la dernière page de chaque copie sera tournée de 180°. Les autres pages restent intactes.
            </p>
          </div>
          <div class="px-6 py-4 border-t border-slate-100 flex items-center justify-end gap-3 bg-slate-50/60">
            <button
              class="px-4 py-2 rounded-lg text-sm font-medium text-slate-600 hover:bg-slate-100"
              @click="showRotateModal = false"
            >
              Annuler
            </button>
            <button
              class="inline-flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 disabled:opacity-60 disabled:cursor-not-allowed"
              :disabled="rotationLoading"
              @click="rotateLastPages"
            >
              <svg v-if="rotationLoading" xmlns="http://www.w3.org/2000/svg" class="w-4 h-4 animate-spin" viewBox="0 0 24 24" fill="none">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z"></path>
              </svg>
              Lancer la rotation
            </button>
          </div>
        </div>
      </div>
    </transition>

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
