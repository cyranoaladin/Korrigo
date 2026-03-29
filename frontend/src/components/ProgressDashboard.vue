<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import gradingApi from '../services/gradingApi'

const props = defineProps({
  examId: {
    type: String,
    required: true
  }
})

const emit = defineEmits(['copy-selected'])

// State
const copies = ref([])
const isLoading = ref(true)
const error = ref(null)
const selectedCopyId = ref(null)
const refreshInterval = ref(null)

// Computed
const stats = computed(() => {
  const total = copies.value.length
  const graded = copies.value.filter(c => c.status === 'FINALIZED').length
  const inProgress = copies.value.filter(c => c.status === 'IN_PROGRESS').length
  const ready = copies.value.filter(c => c.status === 'READY').length
  
  return {
    total,
    graded,
    inProgress,
    ready,
    completionRate: total > 0 ? Math.round((graded / total) * 100) : 0
  }
})

// Group by corrector
const byCorrector = computed(() => {
  const grouped = {}
  copies.value.forEach(copy => {
    const corrector = copy.assigned_corrector 
      ? `${copy.assigned_corrector.first_name} ${copy.assigned_corrector.last_name}`.trim()
      : 'Non assigné'
    
    if (!grouped[corrector]) {
      grouped[corrector] = {
        total: 0,
        graded: 0,
        inProgress: 0,
        ready: 0,
        copies: []
      }
    }
    
    grouped[corrector].total++
    grouped[corrector][copy.status.toLowerCase()]++
    grouped[corrector].copies.push(copy)
  })
  
  return grouped
})

// Group by question progress
const questionProgress = computed(() => {
  const questions = {}
  
  copies.value.forEach(copy => {
    if (copy.scores_data) {
      Object.entries(copy.scores_data).forEach(([questionId, score]) => {
        if (!questions[questionId]) {
          questions[questionId] = {
            total: 0,
            graded: 0,
            avgScore: 0,
            scores: []
          }
        }
        
        questions[questionId].total++
        if (score !== null && score !== undefined && score !== '') {
          questions[questionId].graded++
          questions[questionId].scores.push(parseFloat(score))
        }
      })
    }
  })
  
  // Calculate averages
  Object.values(questions).forEach(question => {
    if (question.scores.length > 0) {
      question.avgScore = question.scores.reduce((a, b) => a + b, 0) / question.scores.length
    }
  })
  
  return questions
})

const loadCopies = async () => {
  try {
    isLoading.value = true
    const response = await gradingApi.getCopies(props.examId)
    copies.value = response.data
    error.value = null
  } catch (e) {
    error.value = e.message
    console.error('Failed to load copies:', e)
  } finally {
    isLoading.value = false
  }
}

const selectCopy = (copy) => {
  selectedCopyId.value = copy.id
  emit('copy-selected', copy)
}

const getStatusColor = (status) => {
  const colors = {
    'FINALIZED': '#4caf50',
    'IN_PROGRESS': '#ff9800',
    'READY': '#2196f3',
  }
  return colors[status] || '#9e9e9e'
}

const getStatusLabel = (status) => {
  const labels = {
    'FINALIZED': 'Finalisée',
    'IN_PROGRESS': 'En cours',
    'READY': 'Prêt',
  }
  return labels[status] || status
}

const getProgressColor = (percentage) => {
  if (percentage >= 80) return '#4caf50'
  if (percentage >= 60) return '#ff9800'
  if (percentage >= 40) return '#ff5722'
  return '#f44336'
}

// Auto-refresh every 30 seconds
const setupAutoRefresh = () => {
  refreshInterval.value = setInterval(() => {
    loadCopies()
  }, 30000)
}

onMounted(() => {
  loadCopies()
  setupAutoRefresh()
})

onUnmounted(() => {
  if (refreshInterval.value) {
    clearInterval(refreshInterval.value)
  }
})
</script>

<template>
  <div class="progress-dashboard">
    <!-- Header -->
    <header class="dashboard-header">
      <h2>Tableau de Bord de Progression</h2>
      <div class="refresh-info">
        Auto-rafraîchissement toutes les 30s
      </div>
    </header>

    <!-- Error State -->
    <div v-if="error" class="error-state">
      <p>❌ Erreur de chargement: {{ error }}</p>
      <button @click="loadCopies" class="retry-button">Réessayer</button>
    </div>

    <!-- Loading State -->
    <div v-else-if="isLoading" class="loading-state">
      <p>Chargement des données...</p>
    </div>

    <!-- Dashboard Content -->
    <div v-else class="dashboard-content">
      <!-- Global Stats -->
      <section class="stats-section">
        <h3>Vue d'ensemble</h3>
        <div class="stats-grid">
          <div class="stat-card">
            <div class="stat-number">{{ stats.total }}</div>
            <div class="stat-label">Total copies</div>
          </div>
          <div class="stat-card">
            <div class="stat-number" style="color: #4caf50">{{ stats.graded }}</div>
            <div class="stat-label">Corrigées</div>
          </div>
          <div class="stat-card">
            <div class="stat-number" style="color: #ff9800">{{ stats.inProgress }}</div>
            <div class="stat-label">En cours</div>
          </div>
          <div class="stat-card">
            <div class="stat-number" style="color: #2196f3">{{ stats.ready }}</div>
            <div class="stat-label">Prêtes</div>
          </div>
          <div class="stat-card progress-card">
            <div class="progress-bar">
              <div 
                class="progress-fill" 
                :style="{ 
                  width: `${stats.completionRate}%`,
                  backgroundColor: getProgressColor(stats.completionRate)
                }"
              ></div>
            </div>
            <div class="stat-number">{{ stats.completionRate }}%</div>
            <div class="stat-label">Taux de complétion</div>
          </div>
        </div>
      </section>

      <!-- Progress by Corrector -->
      <section class="corrector-section">
        <h3>Progression par correcteur</h3>
        <div class="corrector-grid">
          <div 
            v-for="(corrector, name) in byCorrector" 
            :key="name"
            class="corrector-card"
          >
            <h4>{{ name }}</h4>
            <div class="corrector-stats">
              <div class="mini-stat">
                <span class="mini-number">{{ corrector.total }}</span>
                <span class="mini-label">Total</span>
              </div>
              <div class="mini-stat">
                <span class="mini-number" style="color: #4caf50">{{ corrector.graded }}</span>
                <span class="mini-label">Corrigées</span>
              </div>
              <div class="mini-stat">
                <span class="mini-number" style="color: #ff9800">{{ corrector.inProgress }}</span>
                <span class="mini-label">En cours</span>
              </div>
            </div>
            <div class="corrector-progress">
              <div class="progress-bar small">
                <div 
                  class="progress-fill" 
                  :style="{ 
                    width: `${Math.round((corrector.graded / corrector.total) * 100)}%`,
                    backgroundColor: getProgressColor(Math.round((corrector.graded / corrector.total) * 100))
                  }"
                ></div>
              </div>
              <span class="progress-text">
                {{ Math.round((corrector.graded / corrector.total) * 100) }}%
              </span>
            </div>
            <!-- Copy list for this corrector -->
            <div class="copy-list">
              <div 
                v-for="copy in corrector.copies.slice(0, 3)" 
                :key="copy.id"
                class="copy-item"
                :class="{ active: selectedCopyId === copy.id }"
                @click="selectCopy(copy)"
              >
                <span class="copy-id">{{ copy.anonymous_id }}</span>
                <span 
                  class="copy-status"
                  :style="{ color: getStatusColor(copy.status) }"
                >
                  {{ getStatusLabel(copy.status) }}
                </span>
              </div>
              <div v-if="corrector.copies.length > 3" class="more-copies">
                +{{ corrector.copies.length - 3 }} autres
              </div>
            </div>
          </div>
        </div>
      </section>

      <!-- Question Progress -->
      <section class="question-section">
        <h3>Progression par question</h3>
        <div class="question-grid">
          <div 
            v-for="(question, questionId) in questionProgress" 
            :key="questionId"
            class="question-card"
          >
            <h4>Question {{ questionId }}</h4>
            <div class="question-stats">
              <div class="mini-stat">
                <span class="mini-number">{{ question.graded }}</span>
                <span class="mini-label">Notées</span>
              </div>
              <div class="mini-stat">
                <span class="mini-number">{{ question.total }}</span>
                <span class="mini-label">Total</span>
              </div>
              <div class="mini-stat" v-if="question.avgScore">
                <span class="mini-number">{{ question.avgScore.toFixed(1) }}</span>
                <span class="mini-label">Moyenne</span>
              </div>
            </div>
            <div class="question-progress">
              <div class="progress-bar small">
                <div 
                  class="progress-fill" 
                  :style="{ 
                    width: `${Math.round((question.graded / question.total) * 100)}%`,
                    backgroundColor: getProgressColor(Math.round((question.graded / question.total) * 100))
                  }"
                ></div>
              </div>
              <span class="progress-text">
                {{ Math.round((question.graded / question.total) * 100) }}%
              </span>
            </div>
          </div>
        </div>
      </section>

      <!-- Recent Activity -->
      <section class="activity-section">
        <h3>Activité récente</h3>
        <div class="activity-list">
          <div 
            v-for="copy in copies.slice().reverse().slice(0, 10)" 
            :key="copy.id"
            class="activity-item"
            @click="selectCopy(copy)"
          >
            <div class="activity-info">
              <span class="copy-id">{{ copy.anonymous_id }}</span>
              <span class="copy-corrector" v-if="copy.assigned_corrector">
                {{ copy.assigned_corrector.first_name }} {{ copy.assigned_corrector.last_name }}
              </span>
            </div>
            <div class="activity-status">
              <span 
                class="status-badge"
                :style="{ backgroundColor: getStatusColor(copy.status) }"
              >
                {{ getStatusLabel(copy.status) }}
              </span>
              <span class="activity-time">
                {{ copy.graded_at ? new Date(copy.graded_at).toLocaleTimeString() : '—' }}
              </span>
            </div>
          </div>
        </div>
      </section>
    </div>
  </div>
</template>

<style scoped>
.progress-dashboard {
  padding: 1rem;
  background: #f8f9fa;
  min-height: 100vh;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
}

.dashboard-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 2rem;
}

.dashboard-header h2 {
  margin: 0;
  color: #333;
}

.refresh-info {
  font-size: 0.9rem;
  color: #666;
  font-style: italic;
}

.error-state, .loading-state {
  text-align: center;
  padding: 2rem;
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.retry-button {
  margin-top: 1rem;
  padding: 0.5rem 1rem;
  background: #1976d2;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.dashboard-content {
  display: flex;
  flex-direction: column;
  gap: 2rem;
}

.stats-section, .corrector-section, .question-section, .activity-section {
  background: white;
  padding: 1.5rem;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.stats-section h3, .corrector-section h3, .question-section h3, .activity-section h3 {
  margin: 0 0 1rem 0;
  color: #333;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
  gap: 1rem;
}

.stat-card {
  text-align: center;
  padding: 1rem;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  background: white;
}

.stat-card.progress-card {
  grid-column: span 2;
  display: flex;
  flex-direction: column;
  justify-content: center;
}

.stat-number {
  font-size: 2rem;
  font-weight: bold;
  color: #333;
  line-height: 1;
}

.stat-label {
  font-size: 0.9rem;
  color: #666;
  margin-top: 0.5rem;
}

.progress-bar {
  width: 100%;
  height: 8px;
  background: #e0e0e0;
  border-radius: 4px;
  overflow: hidden;
  margin: 0.5rem 0;
}

.progress-bar.small {
  height: 6px;
}

.progress-fill {
  height: 100%;
  transition: width 0.3s ease;
  border-radius: 4px;
}

.progress-text {
  font-size: 0.9rem;
  font-weight: 500;
  color: #333;
}

.corrector-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 1rem;
}

.corrector-card {
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  padding: 1rem;
  background: #fafafa;
}

.corrector-card h4 {
  margin: 0 0 1rem 0;
  color: #333;
  font-size: 1.1rem;
}

.corrector-stats {
  display: flex;
  gap: 1rem;
  margin-bottom: 1rem;
}

.mini-stat {
  text-align: center;
}

.mini-number {
  display: block;
  font-size: 1.2rem;
  font-weight: bold;
  color: #333;
}

.mini-label {
  font-size: 0.8rem;
  color: #666;
}

.corrector-progress {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 1rem;
}

.corrector-progress .progress-bar {
  flex: 1;
}

.copy-list {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.copy-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  cursor: pointer;
  transition: background 0.2s ease;
}

.copy-item:hover {
  background: #e3f2fd;
}

.copy-item.active {
  background: #1976d2;
  color: white;
}

.copy-id {
  font-weight: 500;
  font-size: 0.9rem;
}

.copy-status {
  font-size: 0.8rem;
  font-weight: 500;
}

.more-copies {
  font-size: 0.8rem;
  color: #666;
  text-align: center;
  padding: 0.25rem;
  font-style: italic;
}

.question-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1rem;
}

.question-card {
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  padding: 1rem;
  background: #fafafa;
}

.question-card h4 {
  margin: 0 0 1rem 0;
  color: #333;
}

.question-stats {
  display: flex;
  gap: 1rem;
  margin-bottom: 1rem;
}

.question-progress {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.question-progress .progress-bar {
  flex: 1;
}

.activity-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.activity-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.75rem;
  border: 1px solid #e0e0e0;
  border-radius: 4px;
  cursor: pointer;
  transition: background 0.2s ease;
}

.activity-item:hover {
  background: #f5f5f5;
}

.activity-info {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.copy-id {
  font-weight: 500;
  color: #333;
}

.copy-corrector {
  font-size: 0.8rem;
  color: #666;
}

.activity-status {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 0.25rem;
}

.status-badge {
  color: white;
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  font-size: 0.8rem;
  font-weight: 500;
}

.activity-time {
  font-size: 0.8rem;
  color: #666;
}

/* Responsive Design */
@media (max-width: 768px) {
  .stats-grid {
    grid-template-columns: repeat(2, 1fr);
  }
  
  .stat-card.progress-card {
    grid-column: span 2;
  }
  
  .corrector-grid, .question-grid {
    grid-template-columns: 1fr;
  }
  
  .corrector-stats, .question-stats {
    flex-wrap: wrap;
    gap: 0.5rem;
  }
  
  .mini-stat {
    min-width: 60px;
  }
}

@media (max-width: 480px) {
  .progress-dashboard {
    padding: 0.5rem;
  }
  
  .stats-section, .corrector-section, .question-section, .activity-section {
    padding: 1rem;
  }
  
  .dashboard-header {
    flex-direction: column;
    gap: 0.5rem;
    text-align: center;
  }
}
</style>
