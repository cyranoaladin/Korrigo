<script setup>
import { ref, onMounted, computed, watch } from 'vue'
import api from '../services/api'
import AppIcon from '../icons/AppIcon.vue'

const props = defineProps({
  visible: Boolean
})

const emit = defineEmits(['close', 'insert'])

const historyTexts = ref([])
const loading = ref(false)
const error = ref(null)
const searchQuery = ref('')
const isTouch = ref(matchMedia('(pointer: coarse)').matches)

// Filtrage et dé-duplication des commentaires
const filteredComments = computed(() => {
    // Dé-duplication (normalisation: trim + lowercase pour comparaison)
    const seen = new Set()
    const unique = historyTexts.value.filter(text => {
        const normalized = text.trim().toLowerCase()
        if (seen.has(normalized)) return false
        seen.add(normalized)
        return true
    })

    // Filtrage par recherche
    if (!searchQuery.value.trim()) return unique
    const query = searchQuery.value.trim().toLowerCase()
    return unique.filter(text => text.toLowerCase().includes(query))
})

const fetchHistory = async () => {
    loading.value = true
    error.value = null
    try {
        const response = await api.get('/grading/annotations/history/')
        // Response is [{content: "texte", type: "COMMENTAIRE"}], extract just the texts
        // Dé-duplication côté client au cas où le backend renvoie des doublons
        const texts = (response.data || []).map(item => item.content).filter(Boolean)
        historyTexts.value = [...new Set(texts)]
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
    // Feedback visuel
    e.target.classList.add('dragging')
}

const handleDragEnd = (e) => {
    e.target.classList.remove('dragging')
}

const handleTapInsert = (text) => {
    emit('insert', text)
}

const refresh = () => {
    fetchHistory()
}

onMounted(() => {
    if (props.visible) {
        fetchHistory()
    }
})

watch(() => props.visible, (newVal) => {
    if (newVal && historyTexts.value.length === 0) {
        fetchHistory()
    }
})
</script>

<template>
  <Transition name="slide">
    <div
      v-if="visible"
      class="comment-bank-panel"
    >
      <div class="panel-header">
        <h3>
          <AppIcon
            name="comment"
            :size="16"
            class="inline"
          /> Mes Commentaires
        </h3>
        <div class="header-actions">
          <button
            class="btn-refresh"
            title="Actualiser"
            @click="refresh"
          >
            <AppIcon
              name="search"
              :size="14"
              style="transform: rotate(-45deg)"
            />
          </button>
          <button
            class="btn-close"
            title="Fermer"
            @click="emit('close')"
          >
            ×
          </button>
        </div>
      </div>

      <div class="panel-body">
        <div class="search-bar">
          <input
            v-model="searchQuery"
            type="text"
            placeholder="Rechercher un commentaire..."
            class="search-input"
          >
        </div>

        <p class="help-text">
          <span v-if="isTouch">Cliquez sur un commentaire pour l'ajouter à la copie</span>
          <span v-else>Cliquez ou glissez un commentaire sur la copie pour l'ajouter</span>
        </p>

        <div
          v-if="loading"
          class="loading-state"
        >
          <span class="spinner" /> Chargement...
        </div>
        <div
          v-else-if="error"
          class="error-state"
        >
          {{ error }}
        </div>
        <div
          v-else-if="filteredComments.length === 0 && searchQuery"
          class="empty-state"
        >
          Aucun commentaire ne correspond à "{{ searchQuery }}"
        </div>
        <div
          v-else-if="historyTexts.length === 0"
          class="empty-state"
        >
          Vous n'avez pas encore saisi de commentaires.
          <br><small>Ils apparaîtront ici au fur et à mesure.</small>
        </div>

        <div
          v-else
          class="comments-list"
        >
          <div
            v-for="(text, index) in filteredComments"
            :key="text + index"
            class="comment-item"
            :draggable="!isTouch"
            title="Cliquer ou glisser-déposer sur la copie"
            @dragstart="handleDragStart(text, $event)"
            @dragend="handleDragEnd"
            @click="handleTapInsert(text)"
          >
            <span class="drag-icon">⋮⋮</span>
            <span class="comment-text">{{ text }}</span>
          </div>
        </div>

        <div
          v-if="filteredComments.length > 0"
          class="comments-count"
        >
          {{ filteredComments.length }} commentaire{{ filteredComments.length > 1 ? 's' : '' }}
        </div>
      </div>
    </div>
  </Transition>
</template>

<style scoped>
/* Panneau positionné à GAUCHE du viewer (pas sur le barème à droite) */
.comment-bank-panel {
  position: fixed;
  top: 120px;
  left: 20px;
  width: 300px;
  max-height: calc(100vh - 150px);
  max-height: calc(100dvh - 150px);
  background: white;
  border-radius: 12px;
  box-shadow: 0 10px 40px rgba(0,0,0,0.2), 0 0 0 1px rgba(0,0,0,0.05);
  display: flex;
  flex-direction: column;
  z-index: 150;
  border: 2px solid #3b82f6;
}

/* Animation slide-in depuis la gauche */
.slide-enter-active,
.slide-leave-active {
  transition: all 0.25s ease-out;
}
.slide-enter-from,
.slide-leave-to {
  opacity: 0;
  transform: translateX(-20px);
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.8rem 1rem;
  border-bottom: 1px solid #e2e8f0;
  background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
  border-radius: 10px 10px 0 0;
}

.panel-header h3 {
  margin: 0;
  font-size: 0.95rem;
  color: white;
  font-weight: 600;
}

.header-actions {
  display: flex;
  gap: 6px;
  align-items: center;
}

.btn-refresh {
  background: rgba(255,255,255,0.2);
  border: none;
  font-size: 0.85rem;
  cursor: pointer;
  color: white;
  padding: 4px 8px;
  border-radius: 4px;
  transition: background 0.15s;
}
.btn-refresh:hover { background: rgba(255,255,255,0.3); }

.btn-close {
  background: rgba(255,255,255,0.2);
  border: none;
  font-size: 1.2rem;
  cursor: pointer;
  color: white;
  line-height: 1;
  padding: 2px 8px;
  border-radius: 4px;
  transition: background 0.15s;
}
.btn-close:hover { background: rgba(239,68,68,0.8); }

.panel-body {
  padding: 0.8rem;
  overflow-y: auto;
  flex: 1;
}

.search-bar {
  margin-bottom: 0.75rem;
}

.search-input {
  width: 100%;
  padding: 8px 12px;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  font-size: 0.85rem;
  transition: border-color 0.15s, box-shadow 0.15s;
}
.search-input:focus {
  outline: none;
  border-color: #3b82f6;
  box-shadow: 0 0 0 3px rgba(59,130,246,0.15);
}

.help-text {
  font-size: 0.8rem;
  color: #64748b;
  margin-bottom: 0.75rem;
  text-align: center;
  padding: 6px 10px;
  background: #f0f9ff;
  border-radius: 6px;
  border: 1px dashed #93c5fd;
}

.drag-hint {
  color: #3b82f6;
  font-weight: 600;
}

.loading-state, .error-state, .empty-state {
  text-align: center;
  padding: 1.5rem 0.5rem;
  font-size: 0.85rem;
  color: #64748b;
}

.spinner {
  display: inline-block;
  width: 14px;
  height: 14px;
  border: 2px solid #e2e8f0;
  border-top-color: #3b82f6;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  margin-right: 6px;
}
@keyframes spin { to { transform: rotate(360deg); } }

.error-state { color: #dc2626; }

.empty-state small {
  display: block;
  margin-top: 6px;
  color: #94a3b8;
}

.comments-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  max-height: calc(100vh - 350px);
  overflow-y: auto;
}

.comment-item {
  display: flex;
  align-items: flex-start;
  gap: 0.5rem;
  padding: 0.65rem 0.75rem;
  background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  cursor: grab;
  transition: all 0.15s ease;
  position: relative;
}

@media (hover: hover) {
  .comment-item:hover {
    background: linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%);
    border-color: #93c5fd;
    transform: translateX(3px);
    box-shadow: 0 2px 8px rgba(59,130,246,0.15);
  }
}
.comment-item:active {
  background: linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%);
  border-color: #93c5fd;
}

.comment-item:active,
.comment-item.dragging {
  cursor: grabbing;
  transform: scale(0.98);
  opacity: 0.8;
  box-shadow: 0 4px 12px rgba(0,0,0,0.15);
}

.drag-icon {
  color: #94a3b8;
  font-weight: bold;
  font-size: 1rem;
  letter-spacing: -3px;
  flex-shrink: 0;
  user-select: none;
}

.comment-text {
  font-size: 0.85rem;
  color: #334155;
  word-break: break-word;
  line-height: 1.4;
  flex: 1;
}

.comments-count {
  text-align: center;
  font-size: 0.75rem;
  color: #94a3b8;
  margin-top: 0.75rem;
  padding-top: 0.5rem;
  border-top: 1px solid #e2e8f0;
}

/* Tablette paysage */
@media (max-width: 1180px) and (min-width: 768px) {
  .comment-bank-panel {
    width: 260px;
    top: 100px;
    left: 10px;
  }
}

/* Tablette portrait / mobile */
@media (max-width: 767px) {
  .comment-bank-panel {
    position: fixed;
    top: auto;
    bottom: 0;
    left: 0;
    right: 0;
    width: 100%;
    max-height: 50svh;
    border-radius: 16px 16px 0 0;
    border: none;
    border-top: 2px solid #3b82f6;
  }
}
</style>
