<script setup>
import { ref } from 'vue'
import { useExamStore } from '../stores/examStore'
import api from '../services/api'

const store = useExamStore()
const fileInput = ref(null)
const selectedBookletIds = ref([])
const splitMode = ref(null) // Booklet ID being split
const splitIndex = ref(1) // Where to split

const triggerUpload = () => {
  if (fileInput.value && fileInput.value.files.length > 0) {
    store.uploadExam(fileInput.value.files[0])
  }
}

const toggleSelection = (id) => {
  const index = selectedBookletIds.value.indexOf(id)
  if (index === -1) {
    selectedBookletIds.value.push(id)
    selectedBookletIds.value.sort() 
  } else {
    selectedBookletIds.value.splice(index, 1)
  }
}

const mergeSelection = async () => {
  if (selectedBookletIds.value.length < 1) return
  if (confirm(`Voulez-vous fusionner ${selectedBookletIds.value.length} fascicules en une copie ?`)) {
    await store.mergeBooklets(selectedBookletIds.value)
    selectedBookletIds.value = [] 
  }
}

const deleteBooklet = async (id, e) => {
    e.stopPropagation()
    if(!confirm("Supprimer ce fascicule définitivement ?")) return
    try {
        await api.delete(`/exams/booklets/${id}/`)
        store.fetchBooklets(store.currentExam.id)
    } catch {
        alert("Erreur suppression")
    }
}

const openSplit = (booklet, e) => {
    e.stopPropagation()
    splitMode.value = booklet
    splitIndex.value = Math.floor(booklet.pages_images.length / 2) // Default half
}

const performSplit = async () => {
    if (!splitMode.value) return
    try {
        await api.post(`/exams/booklets/${splitMode.value.id}/split/`, {
            split_at: splitIndex.value
        })
        splitMode.value = null
        store.fetchBooklets(store.currentExam.id)
    } catch {
        alert("Erreur split")
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
        <div class="controls">
          <button 
            :disabled="selectedBookletIds.length === 0" 
            class="btn-primary"
            @click="mergeSelection"
          >
            Agrafer sélection ({{ selectedBookletIds.length }})
          </button>
        </div>
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
            Pages {{ booklet.start_page }} - {{ booklet.end_page || '?' }} 
            <span class="badge">{{ booklet.pages_images ? booklet.pages_images.length : '?' }}p</span>
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
            <div class="mini-actions">
              <button 
                class="btn-xs" 
                title="Scinder"
                @click="openSplit(booklet, $event)"
              >
                ✂️
              </button>
              <button 
                class="btn-xs btn-danger" 
                title="Supprimer" 
                @click="deleteBooklet(booklet.id, $event)"
              >
                🗑️
              </button>
            </div>
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

    <!-- Split Modal -->
    <div
      v-if="splitMode"
      class="modal-overlay"
    >
      <div class="modal">
        <h3>Scinder le fascicule</h3>
        <p>Couper après la page :</p>
        <div class="split-controls">
          <input
            v-model.number="splitIndex"
            type="range"
            min="1"
            :max="(splitMode.pages_images.length - 1)"
          >
          <span>{{ splitIndex }} / {{ splitMode.pages_images.length }}</span>
        </div>
        <div class="preview-split">
          Garder pages 1 à {{ splitIndex }} <br>
          Nouveau fascicule : pages {{ splitIndex + 1 }} à {{ splitMode.pages_images.length }}
        </div>
        <div class="modal-actions">
          <button @click="splitMode = null">
            Annuler
          </button>
          <button
            class="btn-primary"
            @click="performSplit"
          >
            Confirmer Scission
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.staging-area { padding: 20px; font-family: sans-serif; }
.upload-section { border: 2px dashed #ccc; padding: 40px; text-align: center; }
.error { color: red; margin-top: 10px; }
.header-actions { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; background: #f5f5f5; padding: 10px; border-radius: 8px; }
.btn-primary { background-color: #007bff; color: white; border: none; padding: 10px 20px; border-radius: 4px; cursor: pointer; }
.btn-primary:disabled { background-color: #ccc; cursor: not-allowed; }
.grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 20px; }
.card { border: 1px solid #ddd; border-radius: 8px; overflow: hidden; cursor: pointer; transition: transform 0.2s; position: relative; background: white; }
.card:hover { transform: translateY(-2px); box-shadow: 0 4px 8px rgba(0,0,0,0.1); }
.card.selected { border-color: #007bff; box-shadow: 0 0 0 2px #007bff; }
.card-header { background: #eee; padding: 5px 10px; font-size: 0.8rem; color: #666; display: flex; justify-content: space-between; }
.badge { background: #ccc; padding: 1px 4px; border-radius: 4px; font-size: 0.7rem; }
.card-image { height: 100px; background: #fafafa; display: flex; align-items: center; justify-content: center; overflow: hidden; }
.card-image img { width: 100%; height: auto; }
.card-footer { padding: 10px; font-weight: bold; text-align: center; display: flex; flex-direction: column; gap: 5px; }
.checkbox-overlay { position: absolute; top: 5px; right: 5px; }
.mini-actions { display: flex; gap: 5px; justify-content: center; margin-top: 5px; }
.btn-xs { padding: 2px 6px; font-size: 0.8rem; border: 1px solid #ccc; background: white; border-radius: 3px; cursor: pointer; }
.btn-xs:hover { background: #eee; }
.btn-danger { color: red; border-color: #ffcccc; }
.btn-danger:hover { background: #ffe6e6; }

.modal-overlay { position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.5); display: flex; justify-content: center; align-items: center; z-index: 100; }
.modal { background: white; padding: 20px; border-radius: 8px; min-width: 300px; }
.split-controls { display: flex; align-items: center; gap: 10px; margin: 20px 0; }
.modal-actions { display: flex; justify-content: flex-end; gap: 10px; margin-top: 20px; }
</style>
