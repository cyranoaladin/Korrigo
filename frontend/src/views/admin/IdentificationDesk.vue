<template>
  <div class="h-screen flex flex-col bg-gray-50">
    <!-- Header -->
    <header class="bg-white shadow z-10 p-4 flex justify-between items-center">
      <h1 class="text-xl font-bold text-gray-800">Identification Desk (Video-Coding)</h1>
      <router-link to="/admin-dashboard" class="text-indigo-600 hover:text-indigo-800">Retour Dashboard</router-link>
    </header>

    <!-- Main Content -->
    <main class="flex-1 flex overflow-hidden">
      <!-- Left: Image Viewer -->
      <div class="w-2/3 bg-gray-200 relative flex items-center justify-center p-4">
        <div v-if="loading" class="text-gray-500">Chargement...</div>
        <div v-else-if="!currentCopy" class="text-gray-500 text-lg">Toutes les copies sont identifiées !</div>
        <div v-else class="relative w-full h-full flex items-center justify-center">
             <!-- Image Display -->
             <img 
                v-if="currentCopy.header_image_url" 
                :src="currentCopy.header_image_url" 
                alt="Header Crop" 
                class="max-w-full max-h-full object-contain shadow-lg border-4 border-white"
             />
             <div v-else class="bg-white p-10 rounded shadow text-red-500">
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
        <h2 class="text-lg font-semibold mb-4">Associer à un Étudiant</h2>
        
        <div v-if="currentCopy">
            <div class="mb-4">
                <label class="block text-sm font-medium text-gray-700 mb-1">Rechercher (Nom, Prénom, INE)</label>
                <input 
                    ref="searchInput"
                    type="text" 
                    v-model="searchQuery" 
                    @input="searchStudents"
                    @keydown.enter="selectFirstResult"
                    class="w-full border rounded px-3 py-2 focus:ring-2 focus:ring-indigo-500 outline-none"
                    placeholder="Tapez pour chercher..."
                    autofocus
                />
            </div>

            <!-- Autocomplete Results -->
            <div class="flex-1 overflow-y-auto border rounded mb-4 max-h-64" v-if="searchResults.length > 0">
                <div 
                    v-for="(student, index) in searchResults" 
                    :key="student.id"
                    :class="['p-3 border-b cursor-pointer hover:bg-indigo-50', {'bg-indigo-100': index === selectedIndex}]"
                    @click="selectStudent(student)"
                >
                    <div class="font-bold text-gray-900">{{ student.last_name }} {{ student.first_name }}</div>
                    <div class="text-sm text-gray-500">{{ student.class_name }} - {{ student.ine }}</div>
                </div>
            </div>
            <div v-else-if="searchQuery.length > 2" class="text-gray-500 text-sm mb-4">
                Aucun résultat.
            </div>

            <!-- Selected Student -->
            <div v-if="selectedStudent" class="bg-green-50 border border-green-200 p-4 rounded mb-6">
                <h3 class="text-green-800 font-bold mb-2">Sélectionné :</h3>
                <p class="text-lg">{{ selectedStudent.last_name }} {{ selectedStudent.first_name }}</p>
                <p class="text-gray-600">{{ selectedStudent.class_name }}</p>
            </div>

            <!-- Actions -->
            <button 
                @click="confirmIdentification" 
                :disabled="!selectedStudent || submitting"
                class="w-full bg-indigo-600 text-white py-3 rounded-lg text-lg font-bold hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition"
            >
                {{ submitting ? 'Validation...' : 'VALIDER & SUIVANT (Entrée)' }}
            </button>
            
            <p class="text-xs text-center text-gray-400 mt-2">Raccourci: Touche Entrée pour valider</p>
        </div>
      </div>
    </main>
  </div>
</template>

<script setup>
import { ref, onMounted, watch, nextTick } from 'vue'
import { useRoute } from 'vue-router'
import { useAuthStore } from '../../stores/auth'

const route = useRoute()
const auth = useAuthStore()

const examId = route.params.examId
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

const fetchUnidentifiedCopies = async () => {
    loading.value = true
    try {
        const res = await fetch(`${auth.API_URL}/api/exams/${examId}/unidentified_copies/`, {
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

const selectNextCopy = () => {
    if (unidentifiedCopies.value.length > 0) {
        currentCopy.value = unidentifiedCopies.value[0] // Always take first
        resetForm()
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
}

const searchStudents = async () => {
    selectedStudent.value = null
    if (searchQuery.value.length < 2) {
        searchResults.value = []
        return
    }
    
    try {
        const res = await fetch(`${auth.API_URL}/api/students/?search=${encodeURIComponent(searchQuery.value)}`, {
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

const confirmIdentification = async () => {
    if (!currentCopy.value || !selectedStudent.value || submitting.value) return
    
    submitting.value = true
    try {
        const res = await fetch(`${auth.API_URL}/api/copies/${currentCopy.value.id}/identify/`, {
            method: 'POST',
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

onMounted(() => {
    fetchUnidentifiedCopies()
})
</script>
