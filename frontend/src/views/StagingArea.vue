<script setup>
import { ref, computed } from 'vue'
import { useExamStore } from '../stores/examStore'

const store = useExamStore()
const fileInput = ref(null)
const selectedBookletIds = ref([])

const triggerUpload = () => {
  if (fileInput.value && fileInput.value.files.length > 0) {
    store.uploadExam(fileInput.value.files[0])
  }
}

const toggleSelection = (id) => {
  const index = selectedBookletIds.value.indexOf(id)
  if (index === -1) {
    selectedBookletIds.value.push(id)
    // Sort to ensure adjacent check if needed later
    selectedBookletIds.value.sort() 
  } else {
    selectedBookletIds.value.splice(index, 1)
  }
}

const mergeSelection = async () => {
  if (selectedBookletIds.value.length < 1) return
  if (confirm(`Voulez-vous fusionner ${selectedBookletIds.value.length} fascicules en une copie ?`)) {
    await store.mergeBooklets(selectedBookletIds.value)
    selectedBookletIds.value = [] // Reset selection
  }
}

</script>

<template>
  <div class="staging-area">
    <h1>Zone d'Agrafage Virtuel</h1>

    <!-- Upload Section -->
    <div
      v-if="!store.currentExam"
      class="upload-section"
    >
      <p>Veuillez téléverser le PDF "Vrac" des copies.</p>
      <input
        ref="fileInput"
        type="file"
        accept="application/pdf"
        @change="triggerUpload"
      >
      <div v-if="store.isLoading">
        Traitement en cours (Vision)...
      </div>
      <div
        v-if="store.error"
        class="error"
      >
        {{ store.error }}
      </div>
    </div>

    <!-- Stapler Interface -->
    <div
      v-else
      class="workspace"
    >
      <div class="header-actions">
        <h2>Examen: {{ store.currentExam.name }}</h2>
        <button 
          :disabled="selectedBookletIds.length === 0" 
          class="btn-primary"
          @click="mergeSelection"
        >
          Valider / Créer Copie ({{ selectedBookletIds.length }})
        </button>
      </div>

      <div class="grid">
        <div 
          v-for="booklet in store.booklets" 
          :key="booklet.id" 
          class="card"
          :class="{ selected: selectedBookletIds.includes(booklet.id) }"
          @click="toggleSelection(booklet.id)"
        >
          <div class="card-header">
            Page {{ booklet.start_page }}
          </div>
          <div class="card-image">
            <img 
              v-if="booklet.header_image_url" 
              :src="booklet.header_image_url" 
              alt="En-tête" 
            >
            <div
              v-else
              class="placeholder"
            >
              Pas d'image
            </div>
          </div>
          <div class="card-footer">
            <span v-if="booklet.student_name_guess">{{ booklet.student_name_guess }}</span>
            <span v-else>Nom inconnu</span>
          </div>
          
          <div class="checkbox-overlay">
            <input
              type="checkbox"
              :checked="selectedBookletIds.includes(booklet.id)"
            >
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.staging-area {
  padding: 20px;
  font-family: sans-serif;
}
.upload-section {
  border: 2px dashed #ccc;
  padding: 40px;
  text-align: center;
}
.error {
  color: red;
  margin-top: 10px;
}
.header-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  background: #f5f5f5;
  padding: 10px;
  border-radius: 8px;
}
.btn-primary {
  background-color: #007bff;
  color: white;
  border: none;
  padding: 10px 20px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 1rem;
}
.btn-primary:disabled {
  background-color: #ccc;
  cursor: not-allowed;
}
.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 20px;
}
.card {
  border: 1px solid #ddd;
  border-radius: 8px;
  overflow: hidden;
  cursor: pointer;
  transition: transform 0.2s, box-shadow 0.2s;
  position: relative;
}
.card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 8px rgba(0,0,0,0.1);
}
.card.selected {
  border-color: #007bff;
  box-shadow: 0 0 0 2px #007bff;
}
.card-header {
  background: #eee;
  padding: 5px 10px;
  font-size: 0.8rem;
  color: #666;
}
.card-image {
  height: 100px;
  background: #fafafa;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}
.card-image img {
  width: 100%;
  height: auto;
}
.card-footer {
  padding: 10px;
  font-weight: bold;
  text-align: center;
}
.checkbox-overlay {
  position: absolute;
  top: 5px;
  right: 5px;
}
</style>
