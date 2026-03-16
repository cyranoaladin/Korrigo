<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../../stores/auth'
import api from '../../services/api'
import {
  BLOCK_OPTIONS,
  ERGONOMICS_QUESTION_IDS,
  QUESTIONNAIRE_SECTIONS,
  RECOMMENDATION_PREFIXES,
  SENTIMENT_PREFIXES,
  TOOL_LABELS,
  TOOL_QUESTION_IDS,
  UTILITY_LEVELS
} from '../../questionnaire/config'

const router = useRouter()
const authStore = useAuthStore()

const isLoading = ref(true)
const error = ref('')
const infoMessage = ref('')
const responses = ref([])
const summary = ref({ responses_count: 0, total_eligible: 0, remaining_count: 0, completion_rate: 0, is_available: false })

const getAnswer = (response, questionId) => response.answers?.[questionId]

const numericAverage = (questionIds) => {
  const values = responses.value.flatMap((response) => questionIds
    .map((questionId) => getAnswer(response, questionId))
    .filter((value) => typeof value === 'number'))

  if (!values.length) return null
  return Number((values.reduce((sum, value) => sum + value, 0) / values.length).toFixed(1))
}

const npsValues = computed(() => responses.value
  .map((response) => getAnswer(response, 'q53'))
  .filter((value) => typeof value === 'number'))

const npsAverage = computed(() => {
  if (!npsValues.value.length) return null
  return Number((npsValues.value.reduce((sum, value) => sum + value, 0) / npsValues.value.length).toFixed(1))
})

const npsIndex = computed(() => {
  if (!npsValues.value.length) return null
  const promoters = npsValues.value.filter((value) => value >= 9).length
  const detractors = npsValues.value.filter((value) => value <= 6).length
  return Math.round(((promoters - detractors) / npsValues.value.length) * 100)
})

const ergonomicsAverage = computed(() => numericAverage(ERGONOMICS_QUESTION_IDS))
const trustAverage = computed(() => numericAverage(['q33']))
const paperAverage = computed(() => numericAverage(['q41']))

const sentimentStats = computed(() => SENTIMENT_PREFIXES.map((prefix) => ({
  label: prefix,
  count: responses.value.filter((response) => (getAnswer(response, 'q61') || '').startsWith(prefix)).length
})))

const recommendationStats = computed(() => RECOMMENDATION_PREFIXES.map((prefix) => ({
  label: prefix === 'Oui, avec quelques' ? 'Oui, avec améliorations' : prefix,
  count: responses.value.filter((response) => (getAnswer(response, 'q51') || '').startsWith(prefix)).length
})))

const toolStats = computed(() => TOOL_QUESTION_IDS.map((questionId) => ({
  id: questionId,
  label: TOOL_LABELS[questionId],
  levels: UTILITY_LEVELS.map((level) => ({
    label: level,
    count: responses.value.filter((response) => getAnswer(response, questionId) === level).length
  }))
})))

const blockingStats = computed(() => BLOCK_OPTIONS.map((option) => ({
  label: option,
  count: responses.value.filter((response) => {
    const values = getAnswer(response, 'q25')
    return Array.isArray(values) && values.includes(option)
  }).length
})))

const respondentRows = computed(() => responses.value.map((response) => ({
  name: response.display_name,
  username: response.username,
  nps: getAnswer(response, 'q53'),
  sentiment: getAnswer(response, 'q61') || '—',
  recommendation: getAnswer(response, 'q51') || '—',
  submittedAt: response.submitted_at
})))

const collectVerbatims = (questionId) => responses.value
  .filter((response) => (getAnswer(response, questionId) || '').trim())
  .map((response) => ({
    text: getAnswer(response, questionId),
    author: response.display_name,
    submittedAt: response.submitted_at
  }))

const missingFeatures = computed(() => collectVerbatims('q54'))
const bugReports = computed(() => collectVerbatims('q55'))
const finalComments = computed(() => collectVerbatims('q62'))

const maxCount = (items) => Math.max(...items.map((item) => item.count), 1)

const formatDate = (value) => {
  if (!value) return '—'
  return new Date(value).toLocaleString('fr-FR')
}

const exportJson = () => {
  const blob = new Blob([JSON.stringify(responses.value, null, 2)], { type: 'application/json' })
  const link = document.createElement('a')
  link.href = URL.createObjectURL(blob)
  link.download = `korrigo_questionnaire_${new Date().toISOString().slice(0, 10)}.json`
  link.click()
  URL.revokeObjectURL(link.href)
}

const fetchBilan = async () => {
  isLoading.value = true
  error.value = ''
  try {
    const response = await api.get('/grading/questionnaire/bilan/')
    responses.value = response.data.responses || []
    summary.value = response.data.summary || summary.value
    infoMessage.value = response.data.detail || ''
  } catch (requestError) {
    console.error('Failed to load questionnaire bilan', requestError)
    error.value = requestError.response?.data?.detail || 'Erreur lors du chargement du bilan du questionnaire.'
  } finally {
    isLoading.value = false
  }
}

const goToDashboard = () => {
  if (authStore.user?.role === 'Teacher') {
    router.push('/corrector-dashboard')
    return
  }
  router.push('/admin-dashboard')
}

const handleLogout = async () => {
  await authStore.logout()
  router.push('/')
}

onMounted(fetchBilan)
</script>

<template>
  <div class="questionnaire-bilan-page" data-testid="questionnaire-bilan-page">
    <header class="top-nav">
      <div class="brand-row">
        <button class="btn-secondary" @click="goToDashboard">
          ← Dashboard
        </button>
        <div>
          <h1>Bilan Questionnaire Correcteurs</h1>
          <p>{{ summary.responses_count }} réponse(s) sur {{ summary.total_eligible }} correcteur(s)</p>
        </div>
      </div>
      <div class="user-menu">
        <span>{{ authStore.user?.username }}</span>
        <button class="btn-secondary" @click="exportJson">
          Exporter JSON
        </button>
        <button class="btn-logout" @click="handleLogout">
          Déconnexion
        </button>
      </div>
    </header>

    <main class="container">
      <div v-if="isLoading" class="panel">
        Chargement du bilan...
      </div>

      <div v-else-if="error" class="panel error-panel">
        {{ error }}
      </div>

      <template v-else>
        <div v-if="infoMessage" class="panel info-panel">
          {{ infoMessage }}
        </div>

        <section class="cards-grid" data-testid="questionnaire-bilan-summary">
          <div class="metric-card">
            <span class="metric-label">Participation</span>
            <strong class="metric-value">{{ summary.responses_count }} / {{ summary.total_eligible }}</strong>
            <span class="metric-sub">{{ summary.completion_rate }} % de complétion</span>
          </div>
          <div class="metric-card">
            <span class="metric-label">NPS moyen</span>
            <strong class="metric-value">{{ npsAverage ?? '—' }}</strong>
            <span class="metric-sub">sur 10</span>
          </div>
          <div class="metric-card">
            <span class="metric-label">Indice NPS</span>
            <strong class="metric-value">{{ npsIndex ?? '—' }}</strong>
            <span class="metric-sub">promoteurs - détracteurs</span>
          </div>
          <div class="metric-card">
            <span class="metric-label">Ergonomie</span>
            <strong class="metric-value">{{ ergonomicsAverage ?? '—' }}</strong>
            <span class="metric-sub">moyenne / 5</span>
          </div>
          <div class="metric-card">
            <span class="metric-label">Confiance</span>
            <strong class="metric-value">{{ trustAverage ?? '—' }}</strong>
            <span class="metric-sub">moyenne / 5</span>
          </div>
          <div class="metric-card">
            <span class="metric-label">Gain vs papier</span>
            <strong class="metric-value">{{ paperAverage ?? '—' }}</strong>
            <span class="metric-sub">moyenne / 5</span>
          </div>
        </section>

        <section class="panel progress-panel">
          <div class="section-head">
            <h2>Participation</h2>
            <span>{{ summary.completion_rate }} %</span>
          </div>
          <div class="progress-bar">
            <div class="progress-fill" :style="{ width: `${summary.completion_rate}%` }" />
          </div>
          <p v-if="!summary.is_available" class="waiting-text">
            Le bilan complet sera publié quand les {{ summary.remaining_count }} correcteur(s) restant(s) auront répondu.
          </p>
        </section>

        <div v-if="!summary.is_available" class="panel empty-panel">
          Le bilan détaillé n'est pas encore disponible.
        </div>

        <template v-else-if="responses.length">
          <section class="two-columns">
            <div class="panel">
              <div class="section-head">
                <h2>Sentiment global</h2>
                <span>{{ responses.length }} répondant(s)</span>
              </div>
              <div class="stat-list">
                <div v-for="item in sentimentStats" :key="item.label" class="stat-row">
                  <div class="stat-label-row">
                    <span>{{ item.label }}</span>
                    <strong>{{ item.count }}</strong>
                  </div>
                  <div class="mini-bar">
                    <div class="mini-fill" :style="{ width: `${(item.count / maxCount(sentimentStats)) * 100}%` }" />
                  </div>
                </div>
              </div>
            </div>

            <div class="panel">
              <div class="section-head">
                <h2>Recommandation prochain bac blanc</h2>
                <span>{{ responses.length }} répondant(s)</span>
              </div>
              <div class="stat-list">
                <div v-for="item in recommendationStats" :key="item.label" class="stat-row">
                  <div class="stat-label-row">
                    <span>{{ item.label }}</span>
                    <strong>{{ item.count }}</strong>
                  </div>
                  <div class="mini-bar">
                    <div class="mini-fill amber" :style="{ width: `${(item.count / maxCount(recommendationStats)) * 100}%` }" />
                  </div>
                </div>
              </div>
            </div>
          </section>

          <section class="panel">
            <div class="section-head">
              <h2>Utilité des outils de correction</h2>
              <span>{{ QUESTIONNAIRE_SECTIONS[1].questions.length - 2 }} items évalués</span>
            </div>
            <div class="tool-grid">
              <div v-for="tool in toolStats" :key="tool.id" class="tool-card">
                <h3>{{ tool.label }}</h3>
                <div v-for="level in tool.levels" :key="level.label" class="tool-level-row">
                  <span>{{ level.label }}</span>
                  <div class="mini-bar tool-bar">
                    <div
                      class="mini-fill"
                      :class="{
                        red: level.label === 'Inutile',
                        green: level.label === 'Utile',
                        amber: level.label === 'Indispensable'
                      }"
                      :style="{ width: `${responses.length ? (level.count / responses.length) * 100 : 0}%` }"
                    />
                  </div>
                  <strong>{{ level.count }}</strong>
                </div>
              </div>
            </div>
          </section>

          <section class="panel">
            <div class="section-head">
              <h2>Points de blocage signalés</h2>
              <span>Question multiple</span>
            </div>
            <div class="stat-list">
              <div v-for="item in blockingStats" :key="item.label" class="stat-row">
                <div class="stat-label-row">
                  <span>{{ item.label }}</span>
                  <strong>{{ item.count }}</strong>
                </div>
                <div class="mini-bar">
                  <div class="mini-fill blue" :style="{ width: `${(item.count / maxCount(blockingStats)) * 100}%` }" />
                </div>
              </div>
            </div>
          </section>

          <section class="panel">
            <div class="section-head">
              <h2>Détail par correcteur</h2>
              <span>{{ respondentRows.length }} ligne(s)</span>
            </div>
            <div class="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Correcteur</th>
                    <th>NPS</th>
                    <th>Sentiment</th>
                    <th>Recommande</th>
                    <th>Date</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="row in respondentRows" :key="`${row.username}-${row.submittedAt}`">
                    <td>
                      <div class="name-cell">
                        <strong>{{ row.name }}</strong>
                        <span>{{ row.username }}</span>
                      </div>
                    </td>
                    <td>{{ row.nps ?? '—' }}</td>
                    <td>{{ row.sentiment }}</td>
                    <td>{{ row.recommendation }}</td>
                    <td>{{ formatDate(row.submittedAt) }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </section>

          <section v-if="missingFeatures.length" class="panel">
            <div class="section-head">
              <h2>Fonctionnalités manquantes</h2>
              <span>{{ missingFeatures.length }} verbatim(s)</span>
            </div>
            <div class="verbatim-list">
              <div v-for="item in missingFeatures" :key="`${item.author}-${item.submittedAt}-q54`" class="verbatim-card">
                <p>{{ item.text }}</p>
                <span>{{ item.author }} — {{ formatDate(item.submittedAt) }}</span>
              </div>
            </div>
          </section>

          <section v-if="bugReports.length" class="panel">
            <div class="section-head">
              <h2>Bugs et problèmes signalés</h2>
              <span>{{ bugReports.length }} verbatim(s)</span>
            </div>
            <div class="verbatim-list">
              <div v-for="item in bugReports" :key="`${item.author}-${item.submittedAt}-q55`" class="verbatim-card">
                <p>{{ item.text }}</p>
                <span>{{ item.author }} — {{ formatDate(item.submittedAt) }}</span>
              </div>
            </div>
          </section>

          <section v-if="finalComments.length" class="panel">
            <div class="section-head">
              <h2>Commentaires libres</h2>
              <span>{{ finalComments.length }} verbatim(s)</span>
            </div>
            <div class="verbatim-list">
              <div v-for="item in finalComments" :key="`${item.author}-${item.submittedAt}-q62`" class="verbatim-card">
                <p>{{ item.text }}</p>
                <span>{{ item.author }} — {{ formatDate(item.submittedAt) }}</span>
              </div>
            </div>
          </section>
        </template>
      </template>
    </main>
  </div>
</template>

<style scoped>
.questionnaire-bilan-page {
  min-height: 100vh;
  background: #f8fafc;
  font-family: 'Inter', sans-serif;
}

.top-nav {
  padding: 1.2rem 2rem;
  background: white;
  border-bottom: 1px solid #e2e8f0;
  display: flex;
  justify-content: space-between;
  gap: 1rem;
  align-items: flex-start;
}

.brand-row {
  display: flex;
  gap: 1rem;
  align-items: flex-start;
}

.brand-row h1 {
  margin: 0 0 0.35rem;
  color: #0f172a;
  font-size: 1.5rem;
}

.brand-row p {
  margin: 0;
  color: #64748b;
}

.user-menu {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  flex-wrap: wrap;
}

.container {
  max-width: 1180px;
  margin: 0 auto;
  padding: 2rem 1rem 3rem;
}

.panel {
  background: white;
  border: 1px solid #e2e8f0;
  border-radius: 16px;
  padding: 1.25rem;
  margin-bottom: 1rem;
}

.error-panel {
  background: #fef2f2;
  border-color: #fecaca;
  color: #b91c1c;
}

.empty-panel {
  text-align: center;
  color: #64748b;
}

.cards-grid {
  display: grid;
  grid-template-columns: repeat(6, minmax(0, 1fr));
  gap: 1rem;
  margin-bottom: 1rem;
}

.metric-card {
  background: white;
  border: 1px solid #e2e8f0;
  border-radius: 16px;
  padding: 1rem;
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}

.metric-label {
  color: #64748b;
  font-size: 0.9rem;
}

.metric-value {
  color: #0f172a;
  font-size: 1.8rem;
}

.metric-sub {
  color: #94a3b8;
  font-size: 0.88rem;
}

.section-head {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
  align-items: center;
  margin-bottom: 1rem;
}

.section-head h2 {
  margin: 0;
  color: #0f172a;
  font-size: 1.1rem;
}

.section-head span {
  color: #64748b;
  font-size: 0.9rem;
}

.progress-bar,
.mini-bar {
  width: 100%;
  background: #e2e8f0;
  border-radius: 999px;
  overflow: hidden;
}

.progress-bar {
  height: 10px;
}

.mini-bar {
  height: 8px;
}

.progress-fill,
.mini-fill {
  height: 100%;
  background: #22c55e;
}

.mini-fill.amber {
  background: #f59e0b;
}

.mini-fill.red {
  background: #ef4444;
}

.mini-fill.blue {
  background: #3b82f6;
}

.mini-fill.green {
  background: #22c55e;
}

.two-columns {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 1rem;
}

.stat-list {
  display: grid;
  gap: 0.85rem;
}

.stat-row {
  display: grid;
  gap: 0.4rem;
}

.stat-label-row {
  display: flex;
  justify-content: space-between;
  gap: 0.75rem;
  color: #334155;
}

.tool-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 1rem;
}

.tool-card {
  border: 1px solid #e2e8f0;
  border-radius: 14px;
  padding: 1rem;
}

.tool-card h3 {
  margin: 0 0 0.85rem;
  color: #0f172a;
  font-size: 1rem;
}

.tool-level-row {
  display: grid;
  grid-template-columns: 110px 1fr 30px;
  gap: 0.75rem;
  align-items: center;
}

.tool-level-row + .tool-level-row {
  margin-top: 0.65rem;
}

.table-wrap {
  overflow-x: auto;
}

table {
  width: 100%;
  border-collapse: collapse;
}

th,
 td {
  border-bottom: 1px solid #e2e8f0;
  padding: 0.8rem;
  text-align: left;
  vertical-align: top;
}

th {
  color: #64748b;
  font-size: 0.8rem;
  text-transform: uppercase;
}

.name-cell {
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
}

.name-cell span {
  color: #94a3b8;
  font-size: 0.85rem;
}

.verbatim-list {
  display: grid;
  gap: 0.8rem;
}

.verbatim-card {
  border-left: 4px solid #f59e0b;
  background: #fffbeb;
  padding: 0.95rem 1rem;
  border-radius: 0 12px 12px 0;
}

.verbatim-card p {
  margin: 0 0 0.5rem;
  color: #1e293b;
  line-height: 1.5;
}

.verbatim-card span {
  color: #64748b;
  font-size: 0.85rem;
}

.btn-secondary {
  border: 1px solid #cbd5e1;
  background: white;
  color: #475569;
  padding: 0.55rem 0.85rem;
  border-radius: 8px;
  cursor: pointer;
}

.btn-logout {
  border: 1px solid #ef4444;
  background: white;
  color: #ef4444;
  padding: 0.55rem 0.85rem;
  border-radius: 8px;
  cursor: pointer;
}

@media (max-width: 1100px) {
  .cards-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}

@media (max-width: 900px) {
  .two-columns,
  .tool-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 720px) {
  .top-nav,
  .brand-row,
  .user-menu {
    flex-direction: column;
    align-items: stretch;
  }

  .cards-grid {
    grid-template-columns: 1fr;
  }

  .tool-level-row {
    grid-template-columns: 1fr;
  }
}
</style>
