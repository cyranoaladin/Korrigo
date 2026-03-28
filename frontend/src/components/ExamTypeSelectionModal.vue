<script setup>
import { ref, onMounted } from 'vue'
import api from '../services/api'
import ExamTypeIcon from './ExamTypeIcon.vue'

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
        <div class="modal-logo">
          <span class="logo-mark">K</span>
        </div>
        <h2>Bienvenue sur Korrigo</h2>
        <p class="subtitle">Choisissez la matière pour démarrer votre session de correction.</p>
      </div>

      <div v-if="loading" class="loading-state">
        <div class="spinner" />
        Chargement des matières disponibles…
      </div>

      <div v-else-if="error" class="error-state">
        {{ error }}
      </div>

      <div v-else class="exam-types-grid">
        <button
          v-for="type in examTypes"
          :key="type.id"
          class="type-card"
          :style="{ '--accent': type.color || '#6366f1' }"
          @click="selectType(type)"
        >
          <div class="type-icon-wrap">
            <ExamTypeIcon :icon="type.icon" :size="26" />
          </div>
          <div class="type-info">
            <span class="type-name">{{ type.name }}</span>
            <span v-if="type.description" class="type-desc">{{ type.description }}</span>
          </div>
          <span class="type-arrow">›</span>
        </button>
      </div>

      <div v-if="!loading && examTypes.length === 0" class="empty-state">
        Aucune matière n'est encore configurée sur la plateforme.
      </div>
    </div>
  </div>
</template>

<style scoped>
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.8);
  backdrop-filter: blur(6px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 9999;
  padding: 1rem;
}

.modal-content {
  background: #fff;
  border-radius: 16px;
  width: 100%;
  max-width: 520px;
  padding: 2rem 2rem 2.5rem;
  box-shadow: 0 24px 40px rgba(0, 0, 0, 0.18);
}

/* Header */
.modal-header {
  text-align: center;
  margin-bottom: 2rem;
}

.modal-logo {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 52px;
  height: 52px;
  border-radius: 14px;
  background: linear-gradient(135deg, #6366f1, #4f46e5);
  margin-bottom: 1rem;
}

.logo-mark {
  font-size: 1.6rem;
  font-weight: 800;
  color: #fff;
  letter-spacing: -1px;
}

.modal-header h2 {
  font-size: 1.4rem;
  font-weight: 700;
  color: #0f172a;
  margin: 0 0 0.4rem;
}

.subtitle {
  color: #64748b;
  font-size: 0.95rem;
  margin: 0;
  line-height: 1.5;
}

/* Grid */
.exam-types-grid {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

/* Card */
.type-card {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 1rem 1.1rem;
  background: #f8fafc;
  border: 1.5px solid #e2e8f0;
  border-radius: 12px;
  cursor: pointer;
  text-align: left;
  transition: border-color 0.18s, box-shadow 0.18s, background 0.18s;
  width: 100%;
}

.type-card:hover {
  border-color: var(--accent, #6366f1);
  background: #fff;
  box-shadow: 0 4px 16px rgba(99, 102, 241, 0.1);
}

.type-icon-wrap {
  width: 44px;
  height: 44px;
  border-radius: 10px;
  background: color-mix(in srgb, var(--accent, #6366f1) 12%, transparent);
  color: var(--accent, #6366f1);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.type-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
}

.type-name {
  font-size: 1rem;
  font-weight: 600;
  color: #0f172a;
}

.type-desc {
  font-size: 0.82rem;
  color: #64748b;
  line-height: 1.4;
}

.type-arrow {
  font-size: 1.3rem;
  color: #cbd5e1;
  flex-shrink: 0;
  transition: color 0.18s;
}

.type-card:hover .type-arrow {
  color: var(--accent, #6366f1);
}

/* States */
.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.75rem;
  padding: 2rem;
  color: #64748b;
  font-size: 0.95rem;
}

.spinner {
  width: 28px;
  height: 28px;
  border: 3px solid #e2e8f0;
  border-top-color: #6366f1;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.error-state {
  text-align: center;
  padding: 1.25rem;
  color: #dc2626;
  background: #fef2f2;
  border-radius: 8px;
  font-size: 0.9rem;
}

.empty-state {
  text-align: center;
  padding: 2rem;
  color: #64748b;
  font-size: 0.9rem;
}
</style>
