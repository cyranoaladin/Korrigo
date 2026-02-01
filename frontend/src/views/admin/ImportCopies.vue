<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import api from '../../services/api'

const router = useRouter()
const exams = ref([])
const selectedExam = ref(null)
const selectedFile = ref(null)
const isUploading = ref(false)
const error = ref(null)
const successMessage = ref(null)

const fetchExams = async () => {
    try {
        const res = await api.get('/exams/')
        exams.value = res.data
        if (exams.value.length > 0) selectedExam.value = exams.value[0].id
    } catch {
        error.value = "Failed to load exams"
    }
}

const handleFileChange = (e) => {
    selectedFile.value = e.target.files[0]
}

const handleUpload = async () => {
    if (!selectedExam.value || !selectedFile.value) return;
    
    isUploading.value = true;
    error.value = null;
    successMessage.value = null;
    
    const formData = new FormData();
    formData.append('pdf_file', selectedFile.value);
    
    try {
        const res = await api.post(`/exams/${selectedExam.value}/copies/import/`, formData, {
            headers: { 'Content-Type': 'multipart/form-data' }
        });
        
        successMessage.value = "Import successful! Rasterizing..."
        // Since we are sync for P0, we have the copy ID
        if (res.data.id) {
             setTimeout(() => {
                 router.push(`/corrector/desk/${res.data.id}`)
             }, 1000)
        }
    } catch {
        console.error(err)
        error.value = err.response?.data?.error || "Import failed"
    } finally {
        isUploading.value = false;
    }
}

onMounted(fetchExams)
</script>

<template>
  <div class="import-copies">
    <h1>Import Copies (Real PDF)</h1>
    
    <div class="card">
      <div class="form-group">
        <label>Select Exam</label>
        <select v-model="selectedExam">
          <option
            v-for="ex in exams"
            :key="ex.id"
            :value="ex.id"
          >
            {{ ex.name }} ({{ ex.date }})
          </option>
        </select>
      </div>
        
      <div class="form-group">
        <label>Upload PDF Copy</label>
        <input
          type="file"
          accept="application/pdf"
          @change="handleFileChange"
        >
        <small>Upload a single PDF file representing one copy (pages will be rasterized).</small>
      </div>
        
      <div
        v-if="error"
        class="alert alert-danger"
      >
        {{ error }}
      </div>
      <div
        v-if="successMessage"
        class="alert alert-success"
      >
        {{ successMessage }}
      </div>
        
      <button
        :disabled="isUploading || !selectedFile"
        class="btn-primary"
        @click="handleUpload"
      >
        {{ isUploading ? 'Processing...' : 'Import & Process' }}
      </button>
    </div>
  </div>
</template>

<style scoped>
.import-copies { padding: 20px; max-width: 600px; margin: 0 auto; }
.card { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
.form-group { margin-bottom: 20px; display: flex; flex-direction: column; }
.form-group label { font-weight: bold; margin-bottom: 5px; }
.btn-primary { background: #007bff; color: white; padding: 10px 20px; border: none; border-radius: 4px; cursor: pointer; font-size: 1rem; }
.btn-primary:disabled { opacity: 0.6; cursor: not-allowed; }
.alert { padding: 10px; margin-bottom: 15px; border-radius: 4px; }
.alert-danger { background: #f8d7da; color: #721c24; }
.alert-success { background: #d4edda; color: #155724; }
</style>
