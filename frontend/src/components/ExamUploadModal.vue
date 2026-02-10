<script setup>
import { ref, computed } from 'vue'
import api from '../services/api'

const props = defineProps({
  show: Boolean
})

const emit = defineEmits(['close', 'uploaded'])

const uploadMode = ref('BATCH_A3')
const examName = ref('')
const examDate = ref(new Date().toISOString().split('T')[0])
const pagesPerBooklet = ref(4)
const csvFile = ref(null)
const pdfFiles = ref([])
const singlePdfFile = ref(null)
const isUploading = ref(false)
const uploadError = ref(null)
const uploadProgress = ref(null)

const fileInputSingle = ref(null)
const fileInputMultiple = ref(null)
const fileInputCsv = ref(null)

const modeLabel = computed(() => {
  return uploadMode.value === 'BATCH_A3' 
    ? 'Scan par lots (A3) - Découpage automatique' 
    : 'Fichiers individuels (A4) - Déjà découpés par élève'
})

const resetForm = () => {
  uploadMode.value = 'BATCH_A3'
  examName.value = ''
  examDate.value = new Date().toISOString().split('T')[0]
  pagesPerBooklet.value = 4
  csvFile.value = null
  pdfFiles.value = []
  singlePdfFile.value = null
  uploadError.value = null
  uploadProgress.value = null
}

const handleClose = () => {
  resetForm()
  emit('close')
}

const handleSingleFileSelect = (event) => {
  const file = event.target.files[0]
  if (file) {
    singlePdfFile.value = file
  }
}

const handleMultipleFilesSelect = (event) => {
  const files = Array.from(event.target.files)
  if (files.length > 100) {
    uploadError.value = 'Maximum 100 fichiers par upload'
    return
  }
  pdfFiles.value = files
  uploadError.value = null
}

const handleCsvFileSelect = (event) => {
  const file = event.target.files[0]
  if (file) {
    csvFile.value = file
  }
}

const removeFile = (index) => {
  pdfFiles.value = pdfFiles.value.filter((_, i) => i !== index)
}

const triggerFileInput = (inputRef) => {
  if (inputRef.value) {
    inputRef.value.click()
  }
}

const uploadExam = async () => {
  uploadError.value = null
  
  // Validation
  if (!examName.value.trim()) {
    uploadError.value = 'Le nom de l\'examen est obligatoire'
    return
  }
  
  if (uploadMode.value === 'BATCH_A3' && !singlePdfFile.value) {
    uploadError.value = 'Le fichier PDF est obligatoire en mode BATCH_A3'
    return
  }
  
  isUploading.value = true
  uploadProgress.value = 'Création de l\'examen...'
  
  try {
    // Step 1: Create exam
    const formData = new FormData()
    formData.append('name', examName.value)
    formData.append('date', examDate.value)
    formData.append('upload_mode', uploadMode.value)
    
    if (csvFile.value) {
      formData.append('students_csv', csvFile.value)
    }
    
    if (uploadMode.value === 'BATCH_A3') {
      formData.append('pdf_source', singlePdfFile.value)
      formData.append('pages_per_booklet', pagesPerBooklet.value)
    }
    
    const examResponse = await api.post('/exams/upload/', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
    
    const examId = examResponse.data.id
    
    // Step 2: If INDIVIDUAL_A4 mode, upload individual PDFs
    if (uploadMode.value === 'INDIVIDUAL_A4' && pdfFiles.value.length > 0) {
      uploadProgress.value = `Upload de ${pdfFiles.value.length} fichiers...`
      
      const individualFormData = new FormData()
      pdfFiles.value.forEach(file => {
        individualFormData.append('pdf_files', file)
      })
      
      await api.post(`/exams/${examId}/upload-individual-pdfs/`, individualFormData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      })
    }
    
    uploadProgress.value = 'Upload terminé !'
    
    setTimeout(() => {
      emit('uploaded', examResponse.data)
      handleClose()
    }, 1000)
    
  } catch (error) {
    console.error('Upload error:', error)
    const errorMsg = error.response?.data?.error 
      || error.response?.data?.detail
      || error.response?.data?.pdf_source?.[0]
      || 'Erreur lors de l\'upload'
    uploadError.value = errorMsg
  } finally {
    isUploading.value = false
  }
}
</script>

<template>
  <div 
    v-if="show" 
    class="modal-overlay"
    @click.self="handleClose"
  >
    <div class="modal-card upload-modal">
      <div class="modal-header">
        <h3>Importer un Examen</h3>
        <button 
          class="close-btn"
          @click="handleClose"
        >
          ×
        </button>
      </div>

      <div class="modal-body">
        <!-- Mode Selection -->
        <div class="form-group">
          <label class="form-label">Mode d'import</label>
          <div class="mode-selector">
            <label class="mode-option">
              <input 
                v-model="uploadMode" 
                type="radio" 
                value="BATCH_A3"
              >
              <div class="mode-card">
                <div class="mode-icon">📄</div>
                <div class="mode-title">Scan par lots (A3)</div>
                <div class="mode-desc">Un seul PDF multi-pages à découper automatiquement</div>
              </div>
            </label>
            
            <label class="mode-option">
              <input 
                v-model="uploadMode" 
                type="radio" 
                value="INDIVIDUAL_A4"
              >
              <div class="mode-card">
                <div class="mode-icon">📑</div>
                <div class="mode-title">Fichiers individuels (A4)</div>
                <div class="mode-desc">Plusieurs PDFs déjà découpés par élève</div>
              </div>
            </label>
          </div>
        </div>

        <!-- Exam Name -->
        <div class="form-group">
          <label class="form-label">Nom de l'examen *</label>
          <input 
            v-model="examName" 
            type="text" 
            class="form-input" 
            placeholder="Ex: Bac Blanc Maths 2026"
            :disabled="isUploading"
          >
        </div>

        <!-- Exam Date -->
        <div class="form-group">
          <label class="form-label">Date</label>
          <input 
            v-model="examDate" 
            type="date" 
            class="form-input"
            :disabled="isUploading"
          >
        </div>

        <!-- CSV Upload (Optional, both modes) -->
        <div class="form-group">
          <label class="form-label">Liste des élèves (CSV) - Optionnel</label>
          <div class="file-upload-zone">
            <button 
              class="btn-file-select"
              :disabled="isUploading"
              @click="triggerFileInput(fileInputCsv)"
            >
              {{ csvFile ? csvFile.name : 'Sélectionner un fichier CSV' }}
            </button>
            <input 
              ref="fileInputCsv"
              type="file" 
              accept=".csv"
              style="display: none"
              @change="handleCsvFileSelect"
            >
          </div>
        </div>

        <!-- BATCH_A3 Mode Fields -->
        <template v-if="uploadMode === 'BATCH_A3'">
          <div class="form-group">
            <label class="form-label">Fichier PDF source *</label>
            <div class="file-upload-zone">
              <button 
                class="btn-file-select"
                :disabled="isUploading"
                @click="triggerFileInput(fileInputSingle)"
              >
                {{ singlePdfFile ? singlePdfFile.name : 'Sélectionner un PDF' }}
              </button>
              <input 
                ref="fileInputSingle"
                type="file" 
                accept="application/pdf"
                style="display: none"
                @change="handleSingleFileSelect"
              >
            </div>
          </div>

          <div class="form-group">
            <label class="form-label">Pages par copie</label>
            <input 
              v-model.number="pagesPerBooklet" 
              type="number" 
              class="form-input" 
              min="1"
              :disabled="isUploading"
            >
          </div>
        </template>

        <!-- INDIVIDUAL_A4 Mode Fields -->
        <template v-if="uploadMode === 'INDIVIDUAL_A4'">
          <div class="form-group">
            <label class="form-label">Fichiers PDF individuels (max 100)</label>
            <div class="file-upload-zone">
              <button 
                class="btn-file-select"
                :disabled="isUploading"
                @click="triggerFileInput(fileInputMultiple)"
              >
                Sélectionner des PDFs
              </button>
              <input 
                ref="fileInputMultiple"
                type="file" 
                accept="application/pdf"
                multiple
                style="display: none"
                @change="handleMultipleFilesSelect"
              >
            </div>
            
            <div 
              v-if="pdfFiles.length > 0" 
              class="files-list"
            >
              <div class="files-count">
                {{ pdfFiles.length }} fichier(s) sélectionné(s)
              </div>
              <div class="files-preview">
                <div 
                  v-for="(file, index) in pdfFiles.slice(0, 5)" 
                  :key="index"
                  class="file-item"
                >
                  <span class="file-name">{{ file.name }}</span>
                  <button 
                    class="btn-remove"
                    @click="removeFile(index)"
                  >
                    ×
                  </button>
                </div>
                <div 
                  v-if="pdfFiles.length > 5"
                  class="more-files"
                >
                  + {{ pdfFiles.length - 5 }} autres fichiers...
                </div>
              </div>
            </div>
          </div>
        </template>

        <!-- Error Display -->
        <div 
          v-if="uploadError" 
          class="error-message"
        >
          {{ uploadError }}
        </div>

        <!-- Progress Display -->
        <div 
          v-if="uploadProgress" 
          class="progress-message"
        >
          {{ uploadProgress }}
        </div>
      </div>

      <div class="modal-footer">
        <button 
          class="btn btn-outline"
          :disabled="isUploading"
          @click="handleClose"
        >
          Annuler
        </button>
        <button 
          class="btn btn-primary"
          :disabled="isUploading"
          @click="uploadExam"
        >
          {{ isUploading ? 'Upload en cours...' : 'Importer' }}
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.upload-modal {
  width: 90%;
  max-width: 600px;
  max-height: 90vh;
  overflow-y: auto;
}

.modal-card {
  background: white;
  border-radius: 8px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.2);
}

.modal-header {
  padding: 20px 24px;
  border-bottom: 1px solid #eee;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.modal-header h3 {
  margin: 0;
  font-size: 1.5rem;
  color: #333;
}

.close-btn {
  background: none;
  border: none;
  font-size: 2rem;
  color: #999;
  cursor: pointer;
  padding: 0;
  width: 30px;
  height: 30px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.close-btn:hover {
  color: #333;
}

.modal-body {
  padding: 24px;
}

.form-group {
  margin-bottom: 20px;
}

.form-label {
  display: block;
  margin-bottom: 8px;
  font-weight: 600;
  color: #333;
}

.form-input {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 1rem;
}

.mode-selector {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  margin-top: 8px;
}

.mode-option {
  cursor: pointer;
}

.mode-option input[type="radio"] {
  display: none;
}

.mode-card {
  border: 2px solid #ddd;
  border-radius: 8px;
  padding: 16px;
  text-align: center;
  transition: all 0.2s;
}

.mode-option input:checked + .mode-card {
  border-color: #007bff;
  background: #f0f8ff;
}

.mode-card:hover {
  border-color: #999;
}

.mode-icon {
  font-size: 2rem;
  margin-bottom: 8px;
}

.mode-title {
  font-weight: 600;
  margin-bottom: 4px;
  color: #333;
}

.mode-desc {
  font-size: 0.85rem;
  color: #666;
}

.file-upload-zone {
  margin-top: 8px;
}

.btn-file-select {
  width: 100%;
  padding: 12px;
  border: 2px dashed #ddd;
  border-radius: 4px;
  background: #f9f9f9;
  cursor: pointer;
  color: #666;
  font-size: 1rem;
  transition: all 0.2s;
}

.btn-file-select:hover:not(:disabled) {
  border-color: #007bff;
  background: #f0f8ff;
  color: #007bff;
}

.btn-file-select:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.files-list {
  margin-top: 12px;
  padding: 12px;
  background: #f9f9f9;
  border-radius: 4px;
}

.files-count {
  font-weight: 600;
  margin-bottom: 8px;
  color: #333;
}

.files-preview {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.file-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 12px;
  background: white;
  border-radius: 4px;
  border: 1px solid #ddd;
}

.file-name {
  flex: 1;
  font-size: 0.9rem;
  color: #333;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.btn-remove {
  background: none;
  border: none;
  color: #999;
  font-size: 1.5rem;
  cursor: pointer;
  padding: 0 4px;
}

.btn-remove:hover {
  color: #ff4444;
}

.more-files {
  padding: 8px 12px;
  color: #666;
  font-size: 0.9rem;
  font-style: italic;
}

.error-message {
  padding: 12px;
  background: #fff3f3;
  border: 1px solid #ffcccc;
  border-radius: 4px;
  color: #cc0000;
  margin-top: 12px;
}

.progress-message {
  padding: 12px;
  background: #f0f8ff;
  border: 1px solid #cce7ff;
  border-radius: 4px;
  color: #0066cc;
  margin-top: 12px;
  text-align: center;
}

.modal-footer {
  padding: 16px 24px;
  border-top: 1px solid #eee;
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}

.btn {
  padding: 10px 20px;
  border-radius: 4px;
  font-size: 1rem;
  cursor: pointer;
  border: none;
  transition: all 0.2s;
}

.btn-outline {
  background: white;
  border: 1px solid #ddd;
  color: #666;
}

.btn-outline:hover:not(:disabled) {
  background: #f5f5f5;
}

.btn-primary {
  background: #007bff;
  color: white;
}

.btn-primary:hover:not(:disabled) {
  background: #0056b3;
}

.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
</style>
