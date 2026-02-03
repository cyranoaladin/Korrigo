<template>
  <div class="h-screen flex flex-col bg-gray-50">
    <!-- Header -->
    <header class="bg-white shadow z-10 p-4 flex justify-between items-center">
      <h1 class="text-xl font-bold text-gray-800 flex items-center gap-3">
        <img
          src="/images/Korrigo.png"
          alt="Logo"
          class="h-8 w-auto"
        >
        Korrigo — Identification
      </h1>
      <router-link
        to="/admin-dashboard"
        class="text-indigo-600 hover:text-indigo-800"
      >
        Retour Dashboard
      </router-link>
    </header>

    <!-- Main Content -->
    <main class="flex-1 flex overflow-hidden">
      <!-- Left: Image Viewer -->
      <div class="w-2/3 bg-gray-200 relative flex items-center justify-center p-4">
        <div
          v-if="loading"
          class="text-gray-500"
        >
          Chargement...
        </div>
        <div
          v-else-if="!currentCopy"
          class="text-gray-500 text-lg"
        >
          Toutes les copies sont identifiées !
        </div>
        <div
          v-else
          class="relative w-full h-full flex items-center justify-center"
        >
          <!-- Image Display -->
          <img 
            v-if="currentCopy.header_image_url" 
            :src="currentCopy.header_image_url" 
            alt="Header Crop" 
            class="max-w-full max-h-full object-contain shadow-lg border-4 border-white"
          >
          <div
            v-else
            class="bg-white p-10 rounded shadow text-red-500"
          >
            Image non disponible pour cette copie.
          </div>
             
          <!-- Overlay Info -->
          <div class="absolute top-4 left-4 bg-black bg-opacity-50 text-white px-2 py-1 rounded">
            Copie ID: {{ currentCopy.anonymous_id }}
          </div>
        </div>
      </div>

      <!-- Right: Input Form -->
      <div class="w-1/3 bg-white border-l p-6 flex flex-col">
        <h2 class="text-lg font-semibold mb-4">
          Associer à un Étudiant
        </h2>

        <div v-if="currentCopy">
          <!-- Manual Search Section (hidden when OCR candidates are shown) -->
          <div
            v-if="ocrCandidates.length === 0"
            class="mb-4"
          >
            <label class="block text-sm font-medium text-gray-700 mb-1">Rechercher (Nom, Prénom, INE)</label>
            <input
              ref="searchInput"
              v-model="searchQuery"
              type="text"
              class="w-full border rounded px-3 py-2 focus:ring-2 focus:ring-indigo-500 outline-none"
              placeholder="Tapez pour chercher..."
              autofocus
              @input="searchStudents"
              @keydown.enter="selectFirstResult"
            >
          </div>

          <!-- Autocomplete Results (only in manual search mode) -->
          <div
            v-if="ocrCandidates.length === 0 && searchResults.length > 0"
            class="flex-1 overflow-y-auto border rounded mb-4 max-h-64"
          >
            <div
              v-for="(student, index) in searchResults"
              :key="student.id"
              :class="['p-3 border-b cursor-pointer hover:bg-indigo-50', {'bg-indigo-100': index === selectedIndex}]"
              @click="selectStudent(student)"
            >
              <div class="font-bold text-gray-900">
                {{ student.last_name }} {{ student.first_name }}
              </div>
              <div class="text-sm text-gray-500">
                {{ student.class_name }} - {{ student.ine }}
              </div>
            </div>
          </div>
          <div
            v-else-if="ocrCandidates.length === 0 && searchQuery.length > 2"
            class="text-gray-500 text-sm mb-4"
          >
            Aucun résultat.
          </div>

          <!-- Selected Student (only in manual search mode) -->
          <div
            v-if="ocrCandidates.length === 0 && selectedStudent"
            class="bg-green-50 border border-green-200 p-4 rounded mb-6"
          >
            <h3 class="text-green-800 font-bold mb-2">
              Sélectionné :
            </h3>
            <p class="text-lg">
              {{ selectedStudent.last_name }} {{ selectedStudent.first_name }}
            </p>
            <p class="text-gray-600">
              {{ selectedStudent.class_name }}
            </p>
          </div>

          <!-- PRD-19: Multi-layer OCR Candidates -->
          <div
            v-if="ocrCandidates.length > 0"
            class="flex-1 overflow-y-auto mb-4"
          >
            <div class="bg-gradient-to-r from-blue-50 to-indigo-50 border border-indigo-200 p-3 rounded-lg mb-3">
              <h3 class="text-indigo-800 font-bold text-sm flex items-center gap-2">
                <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                  <path d="M9 2a1 1 0 000 2h2a1 1 0 100-2H9z" />
                  <path fill-rule="evenodd" d="M4 5a2 2 0 012-2 3 3 0 003 3h2a3 3 0 003-3 2 2 0 012 2v11a2 2 0 01-2 2H6a2 2 0 01-2-2V5zm3 4a1 1 0 000 2h.01a1 1 0 100-2H7zm3 0a1 1 0 000 2h3a1 1 0 100-2h-3zm-3 4a1 1 0 100 2h.01a1 1 0 100-2H7zm3 0a1 1 0 100 2h3a1 1 0 100-2h-3z" clip-rule="evenodd" />
                </svg>
                Candidats OCR Multi-Moteur
              </h3>
              <p class="text-xs text-indigo-600 mt-1">
                Mode: {{ ocrMode }} | {{ totalEngines }} moteurs consultés
              </p>
            </div>

            <!-- Candidate Cards -->
            <div
              v-for="candidate in ocrCandidates"
              :key="candidate.rank"
              :class="[
                'mb-3 p-3 rounded-lg border-2 cursor-pointer transition-all duration-200',
                candidate.confidence > 0.6
                  ? 'border-green-300 bg-green-50 hover:bg-green-100 hover:border-green-400'
                  : 'border-gray-300 bg-white hover:bg-gray-50 hover:border-gray-400'
              ]"
              @click="selectOCRCandidate(candidate)"
            >
              <!-- Rank Badge -->
              <div class="flex items-start gap-3">
                <div
                  :class="[
                    'flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center text-white font-bold text-sm',
                    candidate.rank === 1 ? 'bg-gradient-to-br from-yellow-400 to-yellow-600' :
                    candidate.rank === 2 ? 'bg-gradient-to-br from-gray-300 to-gray-500' :
                    candidate.rank === 3 ? 'bg-gradient-to-br from-orange-400 to-orange-600' :
                    'bg-gradient-to-br from-blue-400 to-blue-600'
                  ]"
                >
                  {{ candidate.rank }}
                </div>

                <!-- Student Info -->
                <div class="flex-1 min-w-0">
                  <h4 class="font-bold text-gray-900 truncate">
                    {{ candidate.student.last_name }} {{ candidate.student.first_name }}
                  </h4>
                  <p class="text-xs text-gray-600 truncate">
                    {{ candidate.student.email }}
                  </p>
                  <p
                    v-if="candidate.student.date_of_birth"
                    class="text-xs text-gray-500"
                  >
                    Né(e) le {{ candidate.student.date_of_birth }}
                  </p>

                  <!-- Confidence Bar -->
                  <div class="mt-2">
                    <div class="flex items-center justify-between text-xs mb-1">
                      <span class="text-gray-600 font-medium">Confiance</span>
                      <span
                        :class="[
                          'font-bold',
                          candidate.confidence > 0.7 ? 'text-green-600' :
                          candidate.confidence > 0.5 ? 'text-yellow-600' :
                          'text-orange-600'
                        ]"
                      >
                        {{ Math.round(candidate.confidence * 100) }}%
                      </span>
                    </div>
                    <div class="h-2 bg-gray-200 rounded-full overflow-hidden">
                      <div
                        :class="[
                          'h-full transition-all duration-300 rounded-full',
                          candidate.confidence > 0.7 ? 'bg-gradient-to-r from-green-400 to-green-600' :
                          candidate.confidence > 0.5 ? 'bg-gradient-to-r from-yellow-400 to-yellow-600' :
                          'bg-gradient-to-r from-orange-400 to-orange-600'
                        ]"
                        :style="{ width: `${candidate.confidence * 100}%` }"
                      />
                    </div>
                  </div>

                  <!-- Vote Info -->
                  <div class="mt-2 flex items-center gap-2 text-xs text-gray-600">
                    <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 text-indigo-500" viewBox="0 0 20 20" fill="currentColor">
                      <path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd" />
                    </svg>
                    <span>{{ candidate.vote_count }} moteurs en accord</span>
                  </div>

                  <!-- Expandable OCR Sources -->
                  <details class="mt-2">
                    <summary class="text-xs text-indigo-600 cursor-pointer hover:text-indigo-800 select-none">
                      Voir détails OCR
                    </summary>
                    <ul class="mt-1 space-y-1 pl-2 border-l-2 border-indigo-200">
                      <li
                        v-for="(source, idx) in candidate.ocr_sources"
                        :key="idx"
                        class="text-xs text-gray-600"
                      >
                        <span class="font-semibold text-indigo-600">{{ source.engine }}</span>
                        <span class="text-gray-400"> (variant {{ source.variant }})</span>:
                        "{{ source.text }}"
                        <span class="text-gray-500">({{ (source.score * 100).toFixed(0) }}%)</span>
                      </li>
                    </ul>
                  </details>
                </div>
              </div>

              <!-- Select Button -->
              <button
                class="w-full mt-3 bg-indigo-600 text-white py-2 px-4 rounded-lg text-sm font-semibold hover:bg-indigo-700 transition"
                @click.stop="confirmOCRCandidate(candidate)"
              >
                Sélectionner cet étudiant
              </button>
            </div>

            <!-- Manual Override Button -->
            <button
              class="w-full mt-4 bg-gray-100 text-gray-700 py-2 px-4 rounded-lg text-sm font-medium hover:bg-gray-200 transition border border-gray-300"
              @click="showManualSearch"
            >
              Aucun de ces candidats ? Recherche manuelle
            </button>
          </div>

          <!-- OCR Button (legacy single-engine OCR) -->
          <button
            v-if="currentCopy && !ocrSuggestions.length && !ocrCandidates.length"
            :disabled="submitting"
            class="w-full bg-blue-600 text-white py-2 rounded-lg mb-2 hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition"
            @click="runOCR"
          >
            {{ submitting ? 'OCR en cours...' : 'OCR AUTOMATIQUE' }}
          </button>

          <!-- Legacy OCR Suggestions (for backward compatibility) -->
          <div
            v-if="ocrSuggestions.length > 0 && !ocrCandidates.length"
            class="bg-yellow-50 border border-yellow-200 p-4 rounded mb-4"
          >
            <h3 class="text-yellow-800 font-bold mb-2">
              Suggestions OCR:
            </h3>
            <div
              v-for="(suggestion, index) in ocrSuggestions"
              :key="suggestion.id"
              :class="['p-2 border-b cursor-pointer hover:bg-yellow-100', {'bg-yellow-100': index === ocrSelectedIndex}]"
              @click="selectOCRSuggestion(suggestion)"
            >
              {{ suggestion.full_name }} - {{ suggestion.class_name }}
            </div>
            <button
              class="mt-2 text-sm text-gray-600 hover:text-gray-800"
              @click="clearOCRSuggestions"
            >
              Effacer suggestions
            </button>
          </div>

          <!-- Actions (only in manual search mode) -->
          <button
            v-if="ocrCandidates.length === 0"
            :disabled="!selectedStudent || submitting"
            class="w-full bg-indigo-600 text-white py-3 rounded-lg text-lg font-bold hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition"
            @click="confirmIdentification"
          >
            {{ submitting ? 'Validation...' : 'VALIDER & SUIVANT (Entrée)' }}
          </button>

          <p
            v-if="ocrCandidates.length === 0"
            class="text-xs text-center text-gray-400 mt-2"
          >
            Raccourci: Touche Entrée pour valider
          </p>
        </div>
      </div>
    </main>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick } from 'vue'
import { useAuthStore } from '../../stores/auth'
import { ocrApi } from '../../services/api'

const auth = useAuthStore()
const unidentifiedCopies = ref([])
const currentCopy = ref(null)
const loading = ref(true)
const submitting = ref(false)

// Search Logic
const searchQuery = ref('')
const searchResults = ref([])
const selectedIndex = ref(0)
const selectedStudent = ref(null)
const searchInput = ref(null)

// OCR Logic (legacy)
const ocrSuggestions = ref([])
const ocrSelectedIndex = ref(-1)

// PRD-19: Multi-layer OCR Logic
const ocrCandidates = ref([])
const ocrMode = ref('')
const totalEngines = ref(0)
const showManualSearchMode = ref(false)

const fetchUnidentifiedCopies = async () => {
    loading.value = true
    try {
        const res = await fetch(`${auth.API_URL}/api/identification/desk/`, {
            credentials: 'include',
            headers: auth.authHeaders
        })
        if (res.ok) {
            unidentifiedCopies.value = await res.json()
            selectNextCopy()
        }
    } catch (e) {
        console.error("Fetch error", e)
    } finally {
        loading.value = false
    }
}

const selectNextCopy = async () => {
    if (unidentifiedCopies.value.length > 0) {
        currentCopy.value = unidentifiedCopies.value[0] // Always take first
        resetForm()

        // PRD-19: Try to fetch OCR candidates for this copy
        await fetchOCRCandidates()

        nextTick(() => searchInput.value?.focus())
    } else {
        currentCopy.value = null
    }
}

const resetForm = () => {
    searchQuery.value = ''
    searchResults.value = []
    selectedStudent.value = null
    selectedIndex.value = 0
    ocrCandidates.value = []
    ocrSuggestions.value = []
    ocrMode.value = ''
    totalEngines.value = 0
    showManualSearchMode.value = false
}

const searchStudents = async () => {
    selectedStudent.value = null
    if (searchQuery.value.length < 2) {
        searchResults.value = []
        return
    }
    
    try {
        const res = await fetch(`${auth.API_URL}/api/students/?search=${encodeURIComponent(searchQuery.value)}`, {
             credentials: 'include',
             headers: auth.authHeaders
        })
        if (res.ok) {
            searchResults.value = await res.json()
            selectedIndex.value = 0
        }
    } catch (e) {
        console.error(e)
    }
}

const selectStudent = (student) => {
    selectedStudent.value = student
    searchQuery.value = `${student.last_name} ${student.first_name}`
    searchResults.value = [] // Hide results
}

const selectFirstResult = () => {
    if (searchResults.value.length > 0) {
        selectStudent(searchResults.value[selectedIndex.value])
    } else if (selectedStudent.value) {
        // Assume intention to validate if already selected
        confirmIdentification()
    }
}

const runOCR = async () => {
    if (!currentCopy.value || submitting.value) return

    submitting.value = true
    try {
        const res = await fetch(`${auth.API_URL}/api/identification/perform-ocr/${currentCopy.value.id}/`, {
            method: 'POST',
            credentials: 'include',
            headers: new Headers({
                'Content-Type': 'application/json',
                ...auth.authHeaders
            })
        })

        if (res.ok) {
            const data = await res.json()
            ocrSuggestions.value = data.suggestions || []
            ocrSelectedIndex.value = 0
        } else {
            console.error("OCR failed")
        }
    } catch (e) {
        console.error("OCR error", e)
    } finally {
        submitting.value = false
    }
}

const selectOCRSuggestion = (suggestion) => {
    selectedStudent.value = suggestion
    searchQuery.value = `${suggestion.full_name}`
    ocrSuggestions.value = []
    ocrSelectedIndex.value = -1
}

const clearOCRSuggestions = () => {
    ocrSuggestions.value = []
    ocrSelectedIndex.value = -1
}

const confirmIdentification = async () => {
    if (!currentCopy.value || !selectedStudent.value || submitting.value) return

    submitting.value = true
    try {
        const res = await fetch(`${auth.API_URL}/api/identification/identify/${currentCopy.value.id}/`, {
            method: 'POST',
            credentials: 'include',
            headers: new Headers({
                'Content-Type': 'application/json',
                ...auth.authHeaders
            }),
            body: JSON.stringify({ student_id: selectedStudent.value.id })
        })

        if (res.ok) {
            // Remove identified copy from list
            unidentifiedCopies.value.shift()
            selectNextCopy()
        } else {
            console.error("Identification failed")
        }
    } catch (e) {
        console.error(e)
    } finally {
        submitting.value = false
    }
}

// PRD-19: Multi-layer OCR Functions

const fetchOCRCandidates = async () => {
    if (!currentCopy.value) return

    try {
        const response = await ocrApi.getCandidates(currentCopy.value.id)
        const data = response.data

        ocrCandidates.value = data.candidates || []
        ocrMode.value = data.ocr_mode || ''
        totalEngines.value = data.total_engines || 0

        // If we have candidates, hide manual search initially
        if (ocrCandidates.value.length > 0) {
            showManualSearchMode.value = false
        }
    } catch (error) {
        // No OCR result available yet, or error occurred
        if (error.response?.status === 404) {
            // No OCR result for this copy - normal case
            ocrCandidates.value = []
        } else {
            console.error('Error fetching OCR candidates:', error)
        }
    }
}

const selectOCRCandidate = (candidate) => {
    // Visual feedback - candidate is highlighted by click
    console.log('Selected candidate:', candidate)
}

const confirmOCRCandidate = async (candidate) => {
    if (!currentCopy.value || submitting.value) return

    submitting.value = true
    try {
        const response = await ocrApi.selectCandidate(currentCopy.value.id, candidate.rank)

        if (response.data.success) {
            // Remove identified copy from list
            unidentifiedCopies.value.shift()
            await selectNextCopy()
        } else {
            console.error('Candidate selection failed')
        }
    } catch (error) {
        console.error('Error selecting OCR candidate:', error)
        alert('Erreur lors de la sélection du candidat. Veuillez réessayer.')
    } finally {
        submitting.value = false
    }
}

const showManualSearch = () => {
    // Hide OCR candidates and show manual search interface
    ocrCandidates.value = []
    showManualSearchMode.value = true
    nextTick(() => searchInput.value?.focus())
}

onMounted(() => {
    fetchUnidentifiedCopies()
})
</script>
