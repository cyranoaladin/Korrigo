<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import api from '../../services/api'

const router = useRouter()

const name = ref('')
const date = ref(new Date().toISOString().split('T')[0])
const examType = ref('')
const examTypes = ref([])

const loading = ref(false)
const submitting = ref(false)
const error = ref(null)

const fetchExamTypes = async () => {
    loading.value = true
    error.value = null
    try {
        const response = await api.get('/exams/types/')
        examTypes.value = response.data
    } catch (err) {
        error.value = 'Impossible de charger les types d\'examen. Veuillez réessayer.'
        console.error('Erreur chargement types d\'examen:', err)
    } finally {
        loading.value = false
    }
}

const handleSubmit = async () => {
    if (!name.value.trim() || !examType.value) return

    submitting.value = true
    error.value = null
    try {
        const response = await api.post('/exams/', {
            name: name.value.trim(),
            date: date.value,
            exam_type: examType.value,
        })
        const newExamId = response.data.id
        router.push(`/admin/exams/${newExamId}/overview`)
    } catch (err) {
        const detail = err.response?.data?.detail
            || err.response?.data?.name?.[0]
            || err.response?.data?.non_field_errors?.[0]
            || 'Une erreur est survenue lors de la création de l\'examen.'
        error.value = detail
        console.error('Erreur création examen:', err)
    } finally {
        submitting.value = false
    }
}

onMounted(fetchExamTypes)
</script>

<template>
  <div class="min-h-screen bg-gray-50 flex flex-col">
    <!-- Header -->
    <header class="bg-white shadow z-10 p-4 flex justify-between items-center">
      <h1 class="text-xl font-bold text-gray-800 flex items-center gap-3">
        <img
          src="/images/logo_korrigo_pmf.svg"
          alt="Korrigo PMF"
          class="h-8 w-auto"
        >
        Korrigo — Nouvel examen
      </h1>
      <router-link
        to="/admin/exams"
        class="text-indigo-600 hover:text-indigo-800 text-sm"
      >
        ← Examens
      </router-link>
    </header>

    <!-- Main Content -->
    <main class="flex-1 flex items-start justify-center py-12 px-4">
      <div class="bg-white rounded-2xl shadow-md w-full max-w-lg p-8">
        <h2 class="text-2xl font-bold text-gray-800 mb-6">
          Créer un examen
        </h2>

        <!-- Error banner -->
        <div
          v-if="error"
          class="mb-6 rounded-lg bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700"
        >
          {{ error }}
        </div>

        <!-- Loading exam types -->
        <div
          v-if="loading"
          class="mb-6 text-sm text-gray-500"
        >
          Chargement des types d'examen…
        </div>

        <form
          v-else
          class="space-y-6"
          @submit.prevent="handleSubmit"
        >
          <!-- Nom de l'examen -->
          <div>
            <label
              for="exam-name"
              class="block text-sm font-medium text-gray-700 mb-1"
            >
              Nom de l'examen <span class="text-red-500">*</span>
            </label>
            <input
              id="exam-name"
              v-model="name"
              type="text"
              required
              placeholder="Ex. BAC BLANC MATHS 2026"
              class="w-full rounded-lg border border-gray-300 px-4 py-2.5 text-sm text-gray-800 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition"
            >
          </div>

          <!-- Date -->
          <div>
            <label
              for="exam-date"
              class="block text-sm font-medium text-gray-700 mb-1"
            >
              Date
            </label>
            <input
              id="exam-date"
              v-model="date"
              type="date"
              class="w-full rounded-lg border border-gray-300 px-4 py-2.5 text-sm text-gray-800 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition"
            >
          </div>

          <!-- Type d'examen -->
          <div>
            <label
              for="exam-type"
              class="block text-sm font-medium text-gray-700 mb-1"
            >
              Type d'examen <span class="text-red-500">*</span>
            </label>
            <select
              id="exam-type"
              v-model="examType"
              required
              class="w-full rounded-lg border border-gray-300 px-4 py-2.5 text-sm text-gray-800 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition bg-white"
            >
              <option
                value=""
                disabled
              >
                — Sélectionner un type —
              </option>
              <option
                v-for="type in examTypes"
                :key="type.id ?? type.value ?? type"
                :value="type.id ?? type.value ?? type"
              >
                {{ type.label ?? type.name ?? type }}
              </option>
            </select>
          </div>

          <!-- Actions -->
          <div class="flex gap-3 pt-2">
            <button
              type="submit"
              :disabled="submitting || !name.trim() || !examType"
              class="flex-1 rounded-lg bg-indigo-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2"
            >
              <span v-if="submitting">Création en cours…</span>
              <span v-else>Créer l'examen</span>
            </button>
            <button
              type="button"
              :disabled="submitting"
              class="rounded-lg border border-gray-300 px-5 py-2.5 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition focus:outline-none focus:ring-2 focus:ring-gray-400 focus:ring-offset-2"
              @click="router.back()"
            >
              Annuler
            </button>
          </div>
        </form>
      </div>
    </main>
  </div>
</template>
