<template>
  <div class="identification-desk">
    <!-- Header -->
    <header class="desk-header">
      <h1 class="header-title">
        <img src="/images/Korrigo.png" alt="Logo" class="header-logo">
        Korrigo — Video-Coding (Identification)
      </h1>
      <div class="header-actions">
        <span class="stat-badge">{{ unidentifiedCopies.length }} copies à identifier</span>
        <button 
          v-if="unidentifiedCopies.length > 0 && currentExamId"
          class="btn btn-auto-identify"
          :disabled="batchProcessing"
          @click="runBatchAutoIdentify"
        >
          {{ batchProcessing ? 'Traitement...' : '⚡ Auto-identifier tout' }}
        </button>
      </div>
      <router-link to="/admin-dashboard" class="back-link">
        ← Retour Dashboard
      </router-link>
    </header>

    <!-- Batch Results Modal -->
    <div v-if="batchResults" class="modal-overlay" @click.self="batchResults = null">
      <div class="modal-content">
        <h3>Résultats de l'auto-identification</h3>
        <div class="batch-stats">
          <div class="stat-item success">
            <span class="stat-value">{{ batchResults.results.auto_identified }}</span>
            <span class="stat-label">Identifiées</span>
          </div>
          <div class="stat-item warning">
            <span class="stat-value">{{ batchResults.results.needs_review }}</span>
            <span class="stat-label">À vérifier</span>
          </div>
          <div class="stat-item error">
            <span class="stat-value">{{ batchResults.results.failed }}</span>
            <span class="stat-label">Échouées</span>
          </div>
        </div>
        <div class="batch-details">
          <details v-for="(detail, idx) in batchResults.results.details" :key="idx">
            <summary :class="detail.status">
              {{ detail.anonymous_id }} - {{ detail.status }}
            </summary>
            <pre>{{ JSON.stringify(detail, null, 2) }}</pre>
          </details>
        </div>
        <button class="btn btn-primary" @click="closeBatchResults">Fermer</button>
      </div>
    </div>

    <!-- Main Content -->
    <main class="desk-main">
      <!-- Left: Header Image Viewer -->
      <div class="viewer-panel">
        <div v-if="loading" class="loading-state">Chargement...</div>
        <div v-else-if="!currentCopy" class="empty-state success">
          <span class="success-icon">✓</span>
          <p>Toutes les copies sont identifiées !</p>
        </div>
        <div v-else class="image-container">
          <div class="copy-info-overlay">
            <span class="anonymous-id">Anonymat: {{ currentCopy.anonymous_id }}</span>
          </div>
          <img 
            v-if="headerImageUrl" 
            :src="headerImageUrl" 
            alt="En-tête de la copie" 
            class="header-image"
            @error="handleImageError"
          >
          <div v-else class="no-image">
            <p>⚠️ Image d'en-tête non disponible</p>
            <small>Vérifiez que le fascicule a été correctement traité</small>
          </div>
        </div>
      </div>

      <!-- Right: Identification Form -->
      <div class="form-panel">
        <h2 class="panel-title">Identifier l'élève</h2>

        <div v-if="currentCopy" class="form-content">
          <!-- OCR CMEN Button -->
          <div class="ocr-section">
            <button
              v-if="!cmenOcrResult && !cmenOcrLoading"
              class="btn btn-primary btn-large"
              :disabled="submitting"
              @click="runCMENOCR"
            >
              🔍 Lancer OCR (NOM / PRÉNOM / DATE)
            </button>
            <div v-if="cmenOcrLoading" class="loading-indicator">
              <span class="spinner"></span> Analyse OCR en cours...
            </div>
          </div>

          <!-- CMEN OCR Results -->
          <div v-if="cmenOcrResult" class="ocr-results">
            <h3 class="results-title">Résultat OCR</h3>
            <div class="ocr-fields">
              <div class="ocr-field">
                <label>NOM:</label>
                <span class="field-value">{{ cmenOcrResult.ocr_result?.last_name || '-' }}</span>
              </div>
              <div class="ocr-field">
                <label>PRÉNOM:</label>
                <span class="field-value">{{ cmenOcrResult.ocr_result?.first_name || '-' }}</span>
              </div>
              <div class="ocr-field">
                <label>DATE NAISSANCE:</label>
                <span class="field-value">{{ cmenOcrResult.ocr_result?.date_of_birth || '-' }}</span>
              </div>
              <div class="ocr-field">
                <label>Confiance:</label>
                <span class="confidence-badge" :class="confidenceClass">
                  {{ Math.round((cmenOcrResult.ocr_result?.confidence || 0) * 100) }}%
                </span>
              </div>
            </div>

            <!-- Suggestions from CSV -->
            <div v-if="cmenOcrResult.suggestions?.length > 0" class="suggestions-list">
              <h4>Correspondances trouvées:</h4>
              <div
                v-for="(suggestion, idx) in cmenOcrResult.suggestions.slice(0, 5)"
                :key="idx"
                class="suggestion-item"
                :class="{ 'high-confidence': suggestion.score > 0.6 }"
                @click="selectCMENSuggestion(suggestion)"
              >
                <div class="suggestion-name">{{ suggestion.last_name }} {{ suggestion.first_name }}</div>
                <div class="suggestion-details">
                  <span>Né(e) le {{ suggestion.date_of_birth || 'N/A' }}</span>
                  <span class="score-badge">{{ Math.round(suggestion.score * 100) }}%</span>
                </div>
              </div>
            </div>

            <button class="btn btn-secondary btn-small" @click="clearCMENOCR">
              Effacer et rechercher manuellement
            </button>
          </div>

          <!-- Manual Search -->
          <div class="manual-search">
            <label class="search-label">Recherche manuelle (Nom, Prénom, Date naissance)</label>
            <input
              ref="searchInput"
              v-model="searchQuery"
              type="text"
              class="search-input"
              placeholder="Tapez pour chercher..."
              @input="searchStudents"
              @keydown.enter="selectFirstResult"
            >
          </div>

          <!-- Search Results -->
          <div v-if="searchResults.length > 0" class="search-results">
            <div
              v-for="(student, index) in searchResults"
              :key="student.id"
              class="result-item"
              :class="{ 'selected': index === selectedIndex }"
              @click="selectStudent(student)"
            >
              <div class="student-name">{{ student.last_name }} {{ student.first_name }}</div>
              <div class="student-details">
                {{ student.class_name }} | {{ student.date_of_birth || 'Date N/A' }}
              </div>
            </div>
          </div>
          <div v-else-if="searchQuery.length > 2" class="no-results">
            Aucun résultat trouvé.
          </div>

          <!-- Selected Student -->
          <div v-if="selectedStudent" class="selected-student">
            <h4>✓ Élève sélectionné:</h4>
            <p class="selected-name">{{ selectedStudent.last_name }} {{ selectedStudent.first_name }}</p>
            <p class="selected-details">{{ selectedStudent.class_name }}</p>
          </div>

          <!-- Validate Button -->
          <button
            class="btn btn-success btn-large validate-btn"
            :disabled="!selectedStudent || submitting"
            @click="confirmIdentification"
          >
            {{ submitting ? 'Validation...' : '✓ VALIDER & SUIVANT' }}
          </button>
          <p class="shortcut-hint">Raccourci: Touche Entrée pour valider</p>
        </div>
      </div>
    </main>
  </div>
</template>


<script setup>
import { ref, computed, onMounted, nextTick } from 'vue'
import { useAuthStore } from '../../stores/auth'
import api, { ocrApi } from '../../services/api'

// Computed property for header image URL with /api prefix
const headerImageUrl = computed(() => {
    if (!currentCopy.value?.header_image_url) return null
    const url = currentCopy.value.header_image_url
    // Ensure URL starts with /api
    if (url.startsWith('/api')) return url
    if (url.startsWith('/')) return '/api' + url
    return '/api/' + url
})

// Confidence class for styling
const confidenceClass = computed(() => {
    const conf = cmenOcrResult.value?.ocr_result?.confidence || 0
    if (conf > 0.7) return 'high'
    if (conf > 0.5) return 'medium'
    return 'low'
})

const handleImageError = (e) => {
    console.error('Image load error:', e.target.src)
}

const auth = useAuthStore()
const unidentifiedCopies = ref([])
const currentCopy = ref(null)
const loading = ref(true)
const submitting = ref(false)

// Batch auto-identify
const batchProcessing = ref(false)
const batchResults = ref(null)
const currentExamId = computed(() => {
    // Get exam ID from the first unidentified copy
    if (currentCopy.value?.exam_id) return currentCopy.value.exam_id
    if (unidentifiedCopies.value.length > 0 && unidentifiedCopies.value[0].exam_id) {
        return unidentifiedCopies.value[0].exam_id
    }
    return null
})

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

// CMEN OCR Logic
const cmenOcrResult = ref(null)
const cmenOcrLoading = ref(false)

const fetchUnidentifiedCopies = async () => {
    loading.value = true
    try {
        const res = await api.get('/identification/desk/')
        const data = res.data
        // Handle paginated response
        unidentifiedCopies.value = Array.isArray(data) ? data : (data.results || [])
        selectNextCopy()
    } catch (e) {
        if (e.response?.status === 401 || e.response?.status === 403) {
            console.error("Authentication required")
            window.location.href = '/login'
        } else {
            console.error("Fetch error", e)
        }
    } finally {
        loading.value = false
    }
}

const selectNextCopy = async () => {
    if (unidentifiedCopies.value.length > 0) {
        currentCopy.value = unidentifiedCopies.value[0] // Always take first
        resetForm()

        // Note: OCR candidates endpoint removed - use CMEN OCR button instead

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
    cmenOcrResult.value = null
    cmenOcrLoading.value = false
}

const searchStudents = async () => {
    selectedStudent.value = null
    if (searchQuery.value.length < 2) {
        searchResults.value = []
        return
    }
    
    try {
        const res = await api.get(`/students/?search=${encodeURIComponent(searchQuery.value)}`)
        const data = res.data
        // Handle paginated response
        searchResults.value = Array.isArray(data) ? data : (data.results || [])
        selectedIndex.value = 0
    } catch (e) {
        console.error(e)
    }
}

const selectStudent = (student) => {
    selectedStudent.value = student
    searchQuery.value = student.full_name || `${student.last_name || ''} ${student.first_name || ''}`.trim()
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
        const res = await api.post(`/identification/perform-ocr/${currentCopy.value.id}/`)
        ocrSuggestions.value = res.data.suggestions || []
        ocrSelectedIndex.value = 0
    } catch (e) {
        console.error("OCR error", e)
    } finally {
        submitting.value = false
    }
}

const selectOCRSuggestion = (suggestion) => {
    selectedStudent.value = suggestion
    searchQuery.value = suggestion.full_name || `${suggestion.last_name || ''} ${suggestion.first_name || ''}`.trim()
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
        await api.post(`/identification/identify/${currentCopy.value.id}/`, {
            student_id: selectedStudent.value.id
        })
        // Remove identified copy from list
        unidentifiedCopies.value.shift()
        selectNextCopy()
    } catch (e) {
        console.error("Identification failed", e)
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

// CMEN OCR Functions
const runCMENOCR = async () => {
    if (!currentCopy.value || cmenOcrLoading.value) return

    cmenOcrLoading.value = true
    cmenOcrResult.value = null

    try {
        const res = await api.post(`/identification/cmen-ocr/${currentCopy.value.id}/`)
        cmenOcrResult.value = res.data
        
        // Si on a un best_match avec haute confiance, le pré-sélectionner
        if (res.data.best_match && res.data.best_match.confidence > 0.7) {
            // Chercher l'élève dans la base de données
            const searchRes = await api.get(`/students/?search=${encodeURIComponent(res.data.best_match.last_name + ' ' + res.data.best_match.first_name)}`)
            const students = Array.isArray(searchRes.data) ? searchRes.data : (searchRes.data.results || [])
            if (students.length > 0) {
                selectedStudent.value = students[0]
            }
        }
    } catch (e) {
        console.error("CMEN OCR error", e)
        alert("Erreur OCR CMEN: " + (e.response?.data?.error || e.message))
    } finally {
        cmenOcrLoading.value = false
    }
}

const selectCMENSuggestion = async (suggestion) => {
    // Si on a déjà le db_id, l'utiliser directement
    if (suggestion.db_id) {
        try {
            const res = await api.get(`/students/${suggestion.db_id}/`)
            selectedStudent.value = res.data
            searchQuery.value = res.data.full_name
            return
        } catch (e) {
            console.error("Error fetching student by ID", e)
        }
    }
    
    // Sinon chercher l'élève dans la base de données par nom/prénom
    try {
        const searchName = `${suggestion.last_name || ''} ${suggestion.first_name || ''}`.trim()
        const searchRes = await api.get(`/students/?search=${encodeURIComponent(searchName)}`)
        const students = Array.isArray(searchRes.data) ? searchRes.data : (searchRes.data.results || [])
        
        if (students.length > 0) {
            selectedStudent.value = students[0]
            searchQuery.value = students[0].full_name
        } else {
            alert(`Élève "${searchName}" non trouvé dans la base de données. Veuillez l'ajouter d'abord.`)
        }
    } catch (e) {
        console.error("Error selecting CMEN suggestion", e)
    }
}

const clearCMENOCR = () => {
    cmenOcrResult.value = null
    selectedStudent.value = null
    searchQuery.value = ''
    nextTick(() => searchInput.value?.focus())
}

// Batch auto-identify functions
const runBatchAutoIdentify = async () => {
    if (!currentExamId.value || batchProcessing.value) return
    
    if (!confirm(`Lancer l'auto-identification sur ${unidentifiedCopies.value.length} copies ?\n\nCette opération va analyser chaque copie avec l'OCR et identifier automatiquement celles avec une confiance suffisante.`)) {
        return
    }
    
    batchProcessing.value = true
    batchResults.value = null
    
    try {
        const response = await api.post(`/identification/batch-auto-identify/${currentExamId.value}/`, {
            confidence_threshold: 0.6,
            dry_run: false
        })
        
        batchResults.value = response.data
        
        // Refresh the list
        await fetchUnidentifiedCopies()
        
    } catch (e) {
        console.error('Batch auto-identify error:', e)
        alert('Erreur lors de l\'auto-identification: ' + (e.response?.data?.error || e.message))
    } finally {
        batchProcessing.value = false
    }
}

const closeBatchResults = () => {
    batchResults.value = null
}

onMounted(() => {
    fetchUnidentifiedCopies()
})
</script>

<style scoped>
/* Layout */
.identification-desk {
    display: flex;
    flex-direction: column;
    height: 100vh;
    background: #f5f5f5;
}

/* Header */
.desk-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 15px 25px;
    background: white;
    border-bottom: 1px solid #ddd;
    box-shadow: 0 2px 4px rgba(0,0,0,0.05);
}

.header-actions {
    display: flex;
    align-items: center;
    gap: 15px;
}

.btn-auto-identify {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    border: none;
    padding: 10px 20px;
    border-radius: 6px;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.2s;
}
.btn-auto-identify:hover:not(:disabled) {
    transform: translateY(-1px);
    box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
}
.btn-auto-identify:disabled {
    opacity: 0.6;
    cursor: not-allowed;
}

/* Modal */
.modal-overlay {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: rgba(0,0,0,0.5);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 1000;
}

.modal-content {
    background: white;
    border-radius: 12px;
    padding: 25px;
    max-width: 600px;
    width: 90%;
    max-height: 80vh;
    overflow-y: auto;
}

.modal-content h3 {
    margin: 0 0 20px 0;
    color: #333;
}

.batch-stats {
    display: flex;
    gap: 20px;
    margin-bottom: 20px;
}

.stat-item {
    flex: 1;
    text-align: center;
    padding: 15px;
    border-radius: 8px;
}
.stat-item.success { background: #e8f5e9; }
.stat-item.warning { background: #fff3e0; }
.stat-item.error { background: #ffebee; }

.stat-value {
    display: block;
    font-size: 2rem;
    font-weight: bold;
}
.stat-item.success .stat-value { color: #2e7d32; }
.stat-item.warning .stat-value { color: #f57c00; }
.stat-item.error .stat-value { color: #c62828; }

.stat-label {
    font-size: 0.85rem;
    color: #666;
}

.batch-details {
    max-height: 300px;
    overflow-y: auto;
    margin-bottom: 20px;
}

.batch-details details {
    margin-bottom: 5px;
    border: 1px solid #ddd;
    border-radius: 4px;
}

.batch-details summary {
    padding: 10px;
    cursor: pointer;
    font-weight: 500;
}
.batch-details summary.auto_identified { color: #2e7d32; background: #e8f5e9; }
.batch-details summary.would_identify { color: #1976d2; background: #e3f2fd; }
.batch-details summary.needs_review { color: #f57c00; background: #fff3e0; }
.batch-details summary.failed { color: #c62828; background: #ffebee; }

.batch-details pre {
    padding: 10px;
    background: #f5f5f5;
    font-size: 0.8rem;
    overflow-x: auto;
    margin: 0;
}

.header-title {
    display: flex;
    align-items: center;
    gap: 12px;
    font-size: 1.3rem;
    font-weight: bold;
    color: #333;
    margin: 0;
}

.header-logo {
    height: 32px;
    width: auto;
}

.header-stats {
    display: flex;
    gap: 10px;
}

.stat-badge {
    background: #e3f2fd;
    color: #1976d2;
    padding: 6px 12px;
    border-radius: 20px;
    font-size: 0.85rem;
    font-weight: 600;
}

.back-link {
    color: #666;
    text-decoration: none;
    font-size: 0.9rem;
}
.back-link:hover {
    color: #333;
    text-decoration: underline;
}

/* Main Layout */
.desk-main {
    display: flex;
    flex: 1;
    overflow: hidden;
}

/* Viewer Panel (Left) */
.viewer-panel {
    flex: 2;
    background: #2c3e50;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 20px;
    position: relative;
}

.loading-state {
    color: #aaa;
    font-size: 1.2rem;
}

.empty-state {
    text-align: center;
    color: #aaa;
}
.empty-state.success {
    color: #4caf50;
}
.success-icon {
    font-size: 4rem;
    display: block;
    margin-bottom: 15px;
}

.image-container {
    position: relative;
    max-width: 100%;
    max-height: 100%;
}

.copy-info-overlay {
    position: absolute;
    top: 10px;
    left: 10px;
    background: rgba(0,0,0,0.7);
    color: white;
    padding: 8px 15px;
    border-radius: 5px;
    font-size: 0.9rem;
    z-index: 10;
}

.anonymous-id {
    font-weight: bold;
}

.header-image {
    max-width: 100%;
    max-height: 80vh;
    border: 4px solid white;
    border-radius: 8px;
    box-shadow: 0 4px 20px rgba(0,0,0,0.3);
}

.no-image {
    background: white;
    padding: 40px;
    border-radius: 8px;
    text-align: center;
    color: #e74c3c;
}
.no-image small {
    display: block;
    margin-top: 10px;
    color: #999;
}

/* Form Panel (Right) */
.form-panel {
    flex: 1;
    background: white;
    border-left: 1px solid #ddd;
    padding: 25px;
    overflow-y: auto;
    display: flex;
    flex-direction: column;
}

.panel-title {
    font-size: 1.2rem;
    font-weight: bold;
    color: #333;
    margin: 0 0 20px 0;
    padding-bottom: 10px;
    border-bottom: 2px solid #3498db;
}

.form-content {
    flex: 1;
    display: flex;
    flex-direction: column;
    gap: 20px;
}

/* OCR Section */
.ocr-section {
    margin-bottom: 10px;
}

.loading-indicator {
    display: flex;
    align-items: center;
    gap: 10px;
    color: #666;
    padding: 15px;
    background: #f9f9f9;
    border-radius: 6px;
}

.spinner {
    width: 20px;
    height: 20px;
    border: 3px solid #ddd;
    border-top-color: #3498db;
    border-radius: 50%;
    animation: spin 1s linear infinite;
}

@keyframes spin {
    to { transform: rotate(360deg); }
}

/* OCR Results */
.ocr-results {
    background: #e8f5e9;
    border: 1px solid #a5d6a7;
    border-radius: 8px;
    padding: 15px;
}

.results-title {
    font-size: 1rem;
    font-weight: bold;
    color: #2e7d32;
    margin: 0 0 15px 0;
}

.ocr-fields {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 10px;
    margin-bottom: 15px;
}

.ocr-field {
    background: white;
    padding: 10px;
    border-radius: 4px;
}

.ocr-field label {
    display: block;
    font-size: 0.75rem;
    color: #666;
    margin-bottom: 3px;
}

.field-value {
    font-weight: bold;
    color: #333;
}

.confidence-badge {
    display: inline-block;
    padding: 3px 8px;
    border-radius: 4px;
    font-weight: bold;
    font-size: 0.85rem;
}
.confidence-badge.high { background: #c8e6c9; color: #2e7d32; }
.confidence-badge.medium { background: #fff9c4; color: #f57f17; }
.confidence-badge.low { background: #ffcdd2; color: #c62828; }

/* Suggestions */
.suggestions-list {
    margin-top: 15px;
}

.suggestions-list h4 {
    font-size: 0.9rem;
    color: #555;
    margin: 0 0 10px 0;
}

.suggestion-item {
    background: white;
    border: 1px solid #ddd;
    border-radius: 6px;
    padding: 12px;
    margin-bottom: 8px;
    cursor: pointer;
    transition: all 0.2s;
}
.suggestion-item:hover {
    border-color: #3498db;
    background: #f0f7ff;
}
.suggestion-item.high-confidence {
    border-color: #4caf50;
    background: #f1f8e9;
}

.suggestion-name {
    font-weight: bold;
    color: #333;
}

.suggestion-details {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-top: 5px;
    font-size: 0.85rem;
    color: #666;
}

.score-badge {
    background: #e3f2fd;
    color: #1976d2;
    padding: 2px 8px;
    border-radius: 10px;
    font-weight: bold;
    font-size: 0.8rem;
}

/* Manual Search */
.manual-search {
    margin-top: 10px;
}

.search-label {
    display: block;
    font-size: 0.85rem;
    color: #666;
    margin-bottom: 8px;
}

.search-input {
    width: 100%;
    padding: 12px 15px;
    border: 2px solid #ddd;
    border-radius: 6px;
    font-size: 1rem;
    box-sizing: border-box;
}
.search-input:focus {
    outline: none;
    border-color: #3498db;
}

/* Search Results */
.search-results {
    max-height: 200px;
    overflow-y: auto;
    border: 1px solid #ddd;
    border-radius: 6px;
    margin-top: 10px;
}

.result-item {
    padding: 12px 15px;
    border-bottom: 1px solid #eee;
    cursor: pointer;
}
.result-item:hover {
    background: #f5f5f5;
}
.result-item.selected {
    background: #e3f2fd;
}
.result-item:last-child {
    border-bottom: none;
}

.student-name {
    font-weight: bold;
    color: #333;
}

.student-details {
    font-size: 0.85rem;
    color: #666;
    margin-top: 3px;
}

.no-results {
    color: #999;
    font-size: 0.9rem;
    padding: 10px 0;
}

/* Selected Student */
.selected-student {
    background: #e8f5e9;
    border: 2px solid #4caf50;
    border-radius: 8px;
    padding: 15px;
}

.selected-student h4 {
    color: #2e7d32;
    margin: 0 0 8px 0;
    font-size: 0.9rem;
}

.selected-name {
    font-size: 1.1rem;
    font-weight: bold;
    color: #333;
    margin: 0;
}

.selected-details {
    color: #666;
    margin: 5px 0 0 0;
}

/* Buttons */
.btn {
    border: none;
    border-radius: 6px;
    cursor: pointer;
    font-weight: 600;
    transition: all 0.2s;
}

.btn:disabled {
    opacity: 0.5;
    cursor: not-allowed;
}

.btn-large {
    width: 100%;
    padding: 15px 20px;
    font-size: 1rem;
}

.btn-small {
    padding: 8px 15px;
    font-size: 0.85rem;
}

.btn-primary {
    background: #3498db;
    color: white;
}
.btn-primary:hover:not(:disabled) {
    background: #2980b9;
}

.btn-secondary {
    background: #ecf0f1;
    color: #666;
}
.btn-secondary:hover:not(:disabled) {
    background: #ddd;
}

.btn-success {
    background: #27ae60;
    color: white;
}
.btn-success:hover:not(:disabled) {
    background: #219a52;
}

.validate-btn {
    margin-top: auto;
}

.shortcut-hint {
    text-align: center;
    font-size: 0.8rem;
    color: #999;
    margin-top: 10px;
}
</style>
