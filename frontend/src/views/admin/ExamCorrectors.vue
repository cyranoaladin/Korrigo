<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import api from '../../services/api'

const route = useRoute()
const router = useRouter()
const examId = route.params.examId

const loading = ref(true)
const error = ref(null)
const exam = ref(null)
const allTeachers = ref([])
const selectedCorrectors = ref(new Set())
const saving = ref(false)

// Dispatch state
const dispatching = ref(false)
const dispatchConfirmed = ref(false)
const dispatchResults = ref(null)
const undispatchedCount = ref(null) // copies READY sans correcteur

// Toast
const toast = ref({ show: false, message: '', type: 'success' })
let toastTimer = null

const showToast = (message, type = 'success') => {
  if (toastTimer) clearTimeout(toastTimer)
  toast.value = { show: true, message, type }
  toastTimer = setTimeout(() => { toast.value.show = false }, 4000)
}

const loadData = async () => {
  loading.value = true
  error.value = null
  try {
    const [examRes, teachersRes] = await Promise.all([
      api.get(`/exams/${examId}/`),
      api.get('/users/', { params: { role: 'Teacher' } }),
    ])
    exam.value = examRes.data
    allTeachers.value = Array.isArray(teachersRes.data)
      ? teachersRes.data
      : (teachersRes.data.results || [])

    // Initialise selection from current correctors
    const correctors = exam.value.correctors || []
    selectedCorrectors.value = new Set(
      correctors.map(c => (typeof c === 'object' ? c.id : c))
    )

    // Check how many copies still need dispatching (no assigned corrector)
    try {
      const copiesRes = await api.get(`/exams/${examId}/copies/`, { params: { page_size: 999 } })
      const allCopies = copiesRes.data.results || copiesRes.data || []
      undispatchedCount.value = allCopies.filter(c => !c.assigned_corrector).length
    } catch { undispatchedCount.value = null }
  } catch (e) {
    error.value = e.response?.data?.detail || 'Erreur lors du chargement.'
  } finally {
    loading.value = false
  }
}

const toggleCorrector = (teacherId) => {
  if (selectedCorrectors.value.has(teacherId)) {
    selectedCorrectors.value.delete(teacherId)
  } else {
    selectedCorrectors.value.add(teacherId)
  }
  // Trigger reactivity — Set mutations are not auto-tracked in Vue 3
  selectedCorrectors.value = new Set(selectedCorrectors.value)
}

const saveCorrecteurs = async () => {
  saving.value = true
  try {
    await api.patch(`/exams/${examId}/`, { correctors: [...selectedCorrectors.value] })
    showToast('Correcteurs enregistrés avec succès.', 'success')
    // Refresh exam data
    const res = await api.get(`/exams/${examId}/`)
    exam.value = res.data
  } catch (e) {
    showToast(e.response?.data?.detail || 'Erreur lors de la sauvegarde.', 'error')
  } finally {
    saving.value = false
  }
}

const dispatchCopies = async () => {
  if (!dispatchConfirmed.value) {
    dispatchConfirmed.value = true
    return
  }
  dispatching.value = true
  dispatchResults.value = null
  try {
    const res = await api.post(`/exams/${examId}/dispatch/`)
    dispatchResults.value = res.data
    undispatchedCount.value = 0
    showToast('Copies dispatchées avec succès.', 'success')
    dispatchConfirmed.value = false
  } catch (e) {
    showToast(e.response?.data?.detail || 'Erreur lors du dispatch.', 'error')
    dispatchConfirmed.value = false
  } finally {
    dispatching.value = false
  }
}

const cancelDispatch = () => {
  dispatchConfirmed.value = false
}

const selectedCount = computed(() => selectedCorrectors.value.size)
const allDispatched = computed(() => undispatchedCount.value === 0)

const dispatchSummary = computed(() => {
  if (!dispatchResults.value) return []
  // Handle both { assignments: { teacherName: count } } and array formats
  const data = dispatchResults.value
  if (Array.isArray(data)) return data
  if (data.assignments && typeof data.assignments === 'object') {
    return Object.entries(data.assignments).map(([name, count]) => ({ name, count }))
  }
  if (data.results && typeof data.results === 'object') {
    return Object.entries(data.results).map(([name, count]) => ({ name, count }))
  }
  return []
})

onMounted(loadData)
</script>

<template>
  <div class="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50/30 to-indigo-50/20 font-sans">
    <!-- Header -->
    <header class="bg-white/80 backdrop-blur-xl border-b border-slate-200/60 sticky top-0 z-50">
      <div class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
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
            <h1 class="text-lg font-bold text-slate-800">Correcteurs</h1>
            <p
              v-if="exam"
              class="text-xs text-slate-400"
            >
              {{ exam.name }}
            </p>
          </div>
        </div>
        <button
          :disabled="saving || loading"
          class="inline-flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          @click="saveCorrecteurs"
        >
          <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7" />
          </svg>
          {{ saving ? 'Enregistrement…' : 'Enregistrer' }}
        </button>
      </div>
    </header>

    <main class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
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

      <template v-else>
        <!-- Correctors selection -->
        <div class="bg-white rounded-2xl shadow-sm ring-1 ring-slate-100 p-6">
          <div class="flex items-center justify-between mb-4">
            <h3 class="text-base font-semibold text-slate-700">
              Assigner des correcteurs
            </h3>
            <span class="text-xs text-slate-400">
              {{ selectedCount }} sélectionné{{ selectedCount !== 1 ? 's' : '' }}
            </span>
          </div>

          <div
            v-if="allTeachers.length === 0"
            class="text-center py-8 text-slate-400 text-sm"
          >
            Aucun enseignant disponible.
          </div>

          <div
            v-else
            class="grid grid-cols-1 sm:grid-cols-2 gap-2"
          >
            <label
              v-for="teacher in allTeachers"
              :key="teacher.id"
              class="flex items-center gap-3 p-3 rounded-xl cursor-pointer transition-colors"
              :class="selectedCorrectors.has(teacher.id)
                ? 'bg-indigo-50 ring-1 ring-indigo-200'
                : 'bg-slate-50 hover:bg-slate-100 ring-1 ring-slate-100'"
            >
              <input
                type="checkbox"
                class="w-4 h-4 accent-indigo-600 flex-shrink-0"
                :checked="selectedCorrectors.has(teacher.id)"
                @change="toggleCorrector(teacher.id)"
              >
              <div class="min-w-0">
                <p class="text-sm font-medium text-slate-800 truncate">
                  {{ teacher.username }}
                </p>
                <p
                  v-if="teacher.email"
                  class="text-xs text-slate-400 truncate"
                >
                  {{ teacher.email }}
                </p>
              </div>
              <span
                v-if="selectedCorrectors.has(teacher.id)"
                class="ml-auto flex-shrink-0 w-5 h-5 bg-indigo-600 rounded-full flex items-center justify-center"
              >
                <svg xmlns="http://www.w3.org/2000/svg" class="w-3 h-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="3">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7" />
                </svg>
              </span>
            </label>
          </div>
        </div>

        <!-- Dispatch section -->
        <div class="bg-white rounded-2xl shadow-sm ring-1 ring-slate-100 p-6">
          <h3 class="text-base font-semibold text-slate-700 mb-2">
            Dispatcher les copies
          </h3>

          <!-- All dispatched -->
          <div v-if="allDispatched && !dispatchResults" class="bg-emerald-50 ring-1 ring-emerald-100 rounded-xl p-4 text-sm text-emerald-700 flex items-center gap-2">
            <svg xmlns="http://www.w3.org/2000/svg" class="w-5 h-5 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            Toutes les copies sont déjà dispatchées aux correcteurs.
          </div>

          <template v-else>
          <p class="text-sm text-slate-500 mb-4">
            Distribue les copies prêtes (statut READY) entre les correcteurs assignés à cet examen.
          </p>

          <!-- Warning & confirmation step -->
          <div
            v-if="!dispatchConfirmed"
            class="flex flex-wrap items-center gap-3"
          >
            <div class="bg-amber-50 ring-1 ring-amber-100 rounded-xl p-4 flex-1 min-w-0">
              <div class="flex items-start gap-2">
                <svg xmlns="http://www.w3.org/2000/svg" class="w-5 h-5 text-amber-500 flex-shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M12 9v2m0 4h.01M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z" />
                </svg>
                <div>
                  <p class="text-sm font-medium text-amber-800">
                    Attention
                  </p>
                  <p class="text-xs text-amber-700 mt-0.5">
                    Le dispatch réassignera toutes les copies au statut READY. Assurez-vous que les correcteurs sont bien configurés avant de continuer.
                  </p>
                </div>
              </div>
            </div>
            <button
              :disabled="selectedCount === 0 || dispatching"
              class="inline-flex items-center gap-2 px-5 py-2.5 bg-amber-500 text-white rounded-xl text-sm font-medium hover:bg-amber-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex-shrink-0"
              @click="dispatchCopies"
            >
              <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                <path stroke-linecap="round" stroke-linejoin="round" d="M8 9l3 3-3 3m5 0h3M5 20h14a2 2 0 002-2V6a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
              </svg>
              Dispatcher les copies
            </button>
          </div>

          <!-- Confirm step -->
          <div
            v-else
            class="bg-red-50 ring-1 ring-red-100 rounded-xl p-4"
          >
            <p class="text-sm font-semibold text-red-800 mb-3">
              Confirmer le dispatch ?
            </p>
            <p class="text-xs text-red-700 mb-4">
              Cette action va distribuer toutes les copies READY entre {{ selectedCount }} correcteur{{ selectedCount !== 1 ? 's' : '' }}.
              Cette opération ne peut pas être annulée facilement.
            </p>
            <div class="flex items-center gap-3">
              <button
                class="px-4 py-2 bg-white ring-1 ring-slate-200 text-slate-700 rounded-lg text-sm font-medium hover:bg-slate-50 transition-colors"
                @click="cancelDispatch"
              >
                Annuler
              </button>
              <button
                :disabled="dispatching"
                class="inline-flex items-center gap-2 px-4 py-2 bg-red-600 text-white rounded-lg text-sm font-medium hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                @click="dispatchCopies"
              >
                <svg
                  v-if="dispatching"
                  class="w-4 h-4 animate-spin"
                  xmlns="http://www.w3.org/2000/svg"
                  fill="none"
                  viewBox="0 0 24 24"
                >
                  <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
                  <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                </svg>
                {{ dispatching ? 'Dispatch en cours…' : 'Confirmer le dispatch' }}
              </button>
            </div>
          </div>

          <!-- Dispatch results -->
          <div
            v-if="dispatchResults"
            class="mt-6"
          >
            <h4 class="text-sm font-semibold text-slate-700 mb-3">
              Résultats du dispatch
            </h4>

            <!-- Generic message if no breakdown available -->
            <div
              v-if="dispatchSummary.length === 0"
              class="bg-emerald-50 ring-1 ring-emerald-100 rounded-xl p-4 text-sm text-emerald-700"
            >
              <svg xmlns="http://www.w3.org/2000/svg" class="w-5 h-5 inline-block mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                <path stroke-linecap="round" stroke-linejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              Dispatch effectué avec succès.
              <template v-if="dispatchResults.dispatched_count !== undefined">
                {{ dispatchResults.dispatched_count }} copies assignées.
              </template>
            </div>

            <!-- Per-corrector breakdown -->
            <div
              v-else
              class="grid grid-cols-1 sm:grid-cols-2 gap-2"
            >
              <div
                v-for="entry in dispatchSummary"
                :key="entry.name"
                class="flex items-center justify-between px-4 py-2.5 bg-emerald-50 rounded-xl ring-1 ring-emerald-100"
              >
                <span class="text-sm font-medium text-slate-700">{{ entry.name }}</span>
                <span class="text-sm font-bold text-emerald-700">
                  {{ entry.count }} copie{{ entry.count !== 1 ? 's' : '' }}
                </span>
              </div>
            </div>
          </div>
          </template>
        </div>
      </template>
    </main>

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
