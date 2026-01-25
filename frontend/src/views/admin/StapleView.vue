<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import api from '../../services/api'

const route = useRoute()
const router = useRouter()
const examId = route.params.examId
const examName = ref('')
const loading = ref(true)

const booklets = ref([])
const selectedBooklets = ref([])

const fetchBooklets = async () => {
    loading.value = true
    try {
        const [examRes, bookletRes] = await Promise.all([
            api.get(`/exams/${examId}/`),
            api.get(`/exams/${examId}/booklets/`)
        ])
        examName.value = examRes.data.name
        booklets.value = bookletRes.data
    } catch (e) {
        console.error("Failed to fetch data", e)
    } finally {
        loading.value = false
    }
}

const toggleSelection = (bookletId) => {
    if (selectedBooklets.value.includes(bookletId)) {
        selectedBooklets.value = selectedBooklets.value.filter(id => id !== bookletId)
    } else {
        selectedBooklets.value.push(bookletId)
    }
}

const mergeBooklets = async () => {
    if (selectedBooklets.value.length === 0) return
    
    // Sort logic requires at least 1, but usually 2 for a "merge"
    // But allowing 1 for "Promotion to Copy" is also valid workflow
    
    if (!confirm(`Fusionner ${selectedBooklets.value.length} fascicule(s) en une seule copie ?`)) return

    try {
        await api.post(`/exams/${examId}/merge-booklets/`, {
            booklet_ids: selectedBooklets.value
        })
        alert("Fascicules assemblés avec succès !")
        // Refresh
        selectedBooklets.value = []
        await fetchBooklets()
    } catch (e) {
        console.error("Failed to merge", e)
        alert("Erreur lors de l'assemblage: " + (e.response?.data?.error || 'Inconnue'))
    }
}

onMounted(() => {
    fetchBooklets()
})
</script>

<template>
  <div class="staple-view">
    <header class="view-header">
      <button
        class="btn-back"
        @click="router.back()"
      >
        ← Retour
      </button>
      <h2>Atelier d'Agrafe : {{ examName }}</h2>
    </header>

    <div
      v-if="loading"
      class="loading"
    >
      Chargement des fascicules...
    </div>

    <div v-else>
      <div class="actions-bar">
        <span>{{ selectedBooklets.length }} sélectionné(s)</span>
        <button
          class="btn btn-primary"
          :disabled="selectedBooklets.length === 0"
          @click="mergeBooklets"
        >
          Agrafer / Créer une Copie
        </button>
      </div>

      <div class="booklets-grid">
        <div
          v-for="booklet in booklets"
          :key="booklet.id"
          class="booklet-card"
          :class="{ selected: selectedBooklets.includes(booklet.id) }"
          @click="toggleSelection(booklet.id)"
        >
          <div class="card-header">
            Pages {{ booklet.start_page }} - {{ booklet.end_page }}
          </div>
          <div class="card-preview">
            <!-- If we had a thumbnail, display it here. Using header view for now -->
            <img 
              v-if="booklet.id"
              :src="`/api/booklets/${booklet.id}/header/`" 
              loading="lazy"
              alt="Aperçu"
            >
            <div v-else>
              Pas d'aperçu
            </div>
          </div>
          <div class="card-info">
            ID: {{ booklet.id.substring(0, 6) }}...
          </div>
        </div>
        
        <div v-if="booklets.length === 0" class="empty-state">
            Aucun fascicule trouvé.
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.staple-view { padding: 2rem; font-family: 'Inter', sans-serif; max-width: 1200px; margin: 0 auto; }
.view-header { display: flex; align-items: center; gap: 2rem; margin-bottom: 2rem; }
.btn-back { background: none; border: none; color: #64748b; cursor: pointer; font-size: 1rem; }
.actions-bar { background: white; padding: 1rem; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); display: flex; justify-content: space-between; align-items: center; margin-bottom: 2rem; position: sticky; top: 1rem; z-index: 10; }
.booklets-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 1.5rem; }
.booklet-card { background: white; border: 2px solid #e2e8f0; border-radius: 12px; overflow: hidden; cursor: pointer; transition: all 0.2s; }
.booklet-card:hover { transform: translateY(-3px); border-color: #94a3b8; }
.booklet-card.selected { border-color: #3b82f6; box-shadow: 0 0 0 4px rgba(59, 130, 246, 0.2); }
.card-header { padding: 0.5rem; background: #f8fafc; font-size: 0.8rem; border-bottom: 1px solid #e2e8f0; text-align: center; }
.card-preview { height: 100px; background: #cbd5e1; display: flex; align-items: center; justify-content: center; overflow: hidden; }
.card-preview img { width: 100%; height: auto; object-fit: cover; }
.card-info { padding: 0.5rem; font-size: 0.75rem; color: #64748b; text-align: center; }
.btn-primary { background: #3b82f6; color: white; border: none; padding: 0.75rem 1.5rem; border-radius: 8px; cursor: pointer; font-weight: 600; }
.btn-primary:disabled { background: #cbd5e1; cursor: not-allowed; }
.empty-state { grid-column: 1 / -1; text-align: center; padding: 3rem; color: #94a3b8; }
.loading { text-align: center; padding: 4rem; color: #94a3b8; }
</style>
