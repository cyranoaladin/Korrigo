<script setup>
import { ref, onMounted } from 'vue'
import gradingApi from '../services/gradingApi'
import api from '../services/api'

const props = defineProps({
  visible: Boolean
})

const emit = defineEmits(['close'])

const historyTexts = ref([])
const loading = ref(false)
const error = ref(null)

const fetchHistory = async () => {
    loading.value = true
    error.value = null
    try {
        const response = await api.get('/grading/annotations/history/')
        historyTexts.value = response.data.history || []
    } catch (err) {
        error.value = "Erreur lors du chargement de l'historique de vos annotations."
        console.error(err)
    } finally {
        loading.value = false
    }
}

const handleDragStart = (text, e) => {
    e.dataTransfer.setData('text/plain', 'COMMENTBANK|' + text)
    e.dataTransfer.effectAllowed = 'copy'
}

onMounted(() => {
    if (props.visible) {
        fetchHistory()
    }
})

import { watch } from 'vue'
watch(() => props.visible, (newVal) => {
    if (newVal && historyTexts.value.length === 0) {
        fetchHistory()
    }
})
</script>

<template>
  <div v-if="visible" class="comment-bank-panel">
    <div class="panel-header">
      <h3>Banque de Commentaires</h3>
      <button class="btn-close" @click="emit('close')" title="Fermer">×</button>
    </div>
    
    <div class="panel-body">
      <p class="help-text">
        Ceci est votre historique de commentaires. Glissez-en un directement sur la copie pour l'ajouter.
      </p>
      
      <div v-if="loading" class="loading-state">Chargement...</div>
      <div v-else-if="error" class="error-state">{{ error }}</div>
      <div v-else-if="historyTexts.length === 0" class="empty-state">
        Vous n'avez pas encore saisi de commentaires.
      </div>
      
      <div class="comments-list" v-else>
        <div 
          v-for="(text, index) in historyTexts" 
          :key="index"
          class="comment-item"
          draggable="true"
          @dragstart="handleDragStart(text, $event)"
          title="Glisser-déposer sur la copie"
        >
          <span class="drag-icon">⋮⋮</span>
          <span class="comment-text">{{ text }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.comment-bank-panel {
  position: absolute;
  top: 70px;
  right: 20px;
  width: 320px;
  max-height: calc(100vh - 100px);
  background: white;
  border-radius: 8px;
  box-shadow: 0 10px 25px rgba(0,0,0,0.15);
  display: flex;
  flex-direction: column;
  z-index: 100;
  border: 1px solid #e2e8f0;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem 1.2rem;
  border-bottom: 1px solid #e2e8f0;
  background: #f8fafc;
  border-radius: 8px 8px 0 0;
}

.panel-header h3 {
  margin: 0;
  font-size: 1.05rem;
  color: #1e293b;
}

.btn-close {
  background: none;
  border: none;
  font-size: 1.5rem;
  cursor: pointer;
  color: #64748b;
  line-height: 1;
  padding: 0;
}
.btn-close:hover { color: #ef4444; }

.panel-body {
  padding: 1rem;
  overflow-y: auto;
  flex: 1;
}

.help-text {
  font-size: 0.85rem;
  color: #64748b;
  margin-bottom: 1rem;
}

.loading-state, .error-state, .empty-state {
  text-align: center;
  padding: 2rem 0;
  font-size: 0.9rem;
  color: #64748b;
}

.error-state { color: #dc2626; }

.comments-list {
  display: flex;
  flex-direction: column;
  gap: 0.6rem;
}

.comment-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem;
  background: #f1f5f9;
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  cursor: grab;
  transition: all 0.2s;
}

.comment-item:hover {
  background: #e2e8f0;
  border-color: #94a3b8;
  transform: translateY(-1px);
}

.comment-item:active {
  cursor: grabbing;
}

.drag-icon {
  color: #94a3b8;
  font-weight: bold;
  font-size: 1.1rem;
  letter-spacing: -2px;
}

.comment-text {
  font-size: 0.9rem;
  color: #334155;
  word-break: break-word;
  line-height: 1.4;
}
</style>
