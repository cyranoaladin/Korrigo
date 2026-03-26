<script setup>
import { ref, onMounted } from 'vue'
import api from '../services/api'

const props = defineProps({
  visible: Boolean
})

const emit = defineEmits(['select'])

const examTypes = ref([])
const loading = ref(true)
const error = ref('')

onMounted(async () => {
    try {
        const res = await api.get('/exams/types/')
        // L'API renvoie { results: [...] } si paginé, ou un array
        examTypes.value = Array.isArray(res.data) ? res.data : (res.data.results || [])
    } catch (e) {
        console.error("Erreur chargement des types d'examens", e)
        error.value = "Impossible de charger les types d'examens."
    } finally {
        loading.value = false
    }
})

const selectType = (examType) => {
    emit('select', examType)
}
</script>

<template>
  <div v-if="visible" class="modal-overlay" data-testid="exam-type-selection-modal">
    <div class="modal-content">
      <div class="modal-header">
        <h2>Bienvenue sur Korrigo PMF</h2>
        <p class="subtitle">Sélectionnez votre type d'examen (matière) pour cette session de correction.</p>
      </div>

      <div v-if="loading" class="loading-state">
        Chargement des matières disponibles...
      </div>

      <div v-else-if="error" class="error-state">
        {{ error }}
      </div>

      <div v-else class="exam-types-grid">
        <button
          v-for="type in examTypes"
          :key="type.id"
          class="type-card"
          :style="{ borderColor: type.color + '40' }"
          @click="selectType(type)"
        >
          <div class="type-icon" :style="{ backgroundColor: type.color + '20', color: type.color }">
            <span v-if="type.icon" class="material-icons">{{ type.icon }}</span>
            <span v-else class="material-icons">folder</span>
          </div>
          <div class="type-info">
            <h3 :style="{ color: type.color }">{{ type.name }}</h3>
            <p v-if="type.description">{{ type.description }}</p>
          </div>
        </button>
      </div>
      
      <div v-if="!loading && examTypes.length === 0" class="empty-state">
        Aucun type d'examen n'est configuré sur la plateforme.
      </div>
    </div>
  </div>
</template>

<style scoped>
.modal-overlay {
  position: fixed;
  top: 0; left: 0; right: 0; bottom: 0;
  background: rgba(15, 23, 42, 0.85); /* Fond plus sombre pour focaliser l'attention */
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 9999;
}

.modal-content {
  background: white;
  border-radius: 12px;
  width: 90%;
  max-width: 600px;
  padding: 2.5rem;
  box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
}

.modal-header {
  text-align: center;
  margin-bottom: 2rem;
}

.modal-header h2 {
  font-size: 1.5rem;
  color: #0f172a;
  margin: 0 0 0.5rem 0;
}

.subtitle {
  color: #64748b;
  font-size: 1rem;
  margin: 0;
}

.exam-types-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
  gap: 1.25rem;
}

.type-card {
  display: flex;
  align-items: flex-start;
  gap: 1rem;
  padding: 1.25rem;
  background: white;
  border: 2px solid #e2e8f0;
  border-radius: 10px;
  cursor: pointer;
  text-align: left;
  transition: all 0.2s ease;
}

.type-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
  border-color: currentColor;
}

.type-icon {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.type-icon .material-icons {
  font-size: 24px;
}

.type-info {
  flex: 1;
}

.type-info h3 {
  margin: 0 0 0.25rem 0;
  font-size: 1.1rem;
  font-weight: 600;
}

.type-info p {
  margin: 0;
  font-size: 0.85rem;
  color: #64748b;
  line-height: 1.4;
}

.loading-state, .error-state, .empty-state {
  text-align: center;
  padding: 2rem;
  color: #64748b;
}

.error-state {
  color: #ef4444;
  background: #fef2f2;
  border-radius: 8px;
}
</style>
