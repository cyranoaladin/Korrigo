<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../../stores/auth'
import api from '../../services/api'
import { QUESTIONNAIRE_SECTIONS } from '../../questionnaire/config'

const router = useRouter()
const authStore = useAuthStore()

const isLoading = ref(true)
const isSubmitting = ref(false)
const loadError = ref('')
const saveError = ref('')
const saveMessage = ref('')
const hasExistingResponse = ref(false)
const submittedAt = ref(null)
const answers = ref({})
const step = ref(0)
const questionnaireSummary = ref({ is_available: false, responses_count: 0, total_eligible: 0, remaining_count: 0, completion_rate: 0 })

const currentSection = computed(() => QUESTIONNAIRE_SECTIONS[step.value])
const totalSections = computed(() => QUESTIONNAIRE_SECTIONS.length)
const progressPercent = computed(() => Math.round((step.value / totalSections.value) * 100))

const fetchResponse = async () => {
  isLoading.value = true
  loadError.value = ''
  try {
    const response = await api.get('/grading/questionnaire/')
    hasExistingResponse.value = response.data.has_response
    submittedAt.value = response.data.submitted_at
    answers.value = response.data.response || {}
    questionnaireSummary.value = response.data.summary || questionnaireSummary.value
  } catch (error) {
    console.error('Failed to load questionnaire', error)
    loadError.value = error.response?.data?.detail || 'Erreur lors du chargement du questionnaire.'
  } finally {
    isLoading.value = false
  }
}

const goBack = () => {
  router.push('/corrector-dashboard')
}

const handleLogout = async () => {
  await authStore.logout()
  router.push('/')
}

const goToQuestionnaireBilan = () => {
  router.push({ name: 'QuestionnaireBilan' })
}

const formatDate = (value) => {
  if (!value) return ''
  return new Date(value).toLocaleString('fr-FR')
}

const isAnswered = (question) => {
  const value = answers.value[question.id]
  if (question.type === 'ck') return Array.isArray(value) && value.length > 0
  if (question.type === 'nps' || question.type === 'lk') return typeof value === 'number'
  return value !== undefined && value !== null && value !== ''
}

const validateCurrentSection = () => {
  saveError.value = ''
  for (const question of currentSection.value.questions) {
    if (question.req && !isAnswered(question)) {
      saveError.value = 'Veuillez répondre à toutes les questions obligatoires avant de continuer.'
      return false
    }
  }
  return true
}

const goNext = () => {
  if (!validateCurrentSection()) return
  if (step.value < totalSections.value - 1) {
    step.value += 1
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }
}

const goPrev = () => {
  if (step.value > 0) {
    saveError.value = ''
    step.value -= 1
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }
}

const setAnswer = (questionId, value) => {
  answers.value = {
    ...answers.value,
    [questionId]: value
  }
}

const toggleCheckboxAnswer = (questionId, option) => {
  const currentValues = Array.isArray(answers.value[questionId]) ? [...answers.value[questionId]] : []
  const index = currentValues.indexOf(option)
  if (index >= 0) currentValues.splice(index, 1)
  else currentValues.push(option)
  setAnswer(questionId, currentValues)
}

const submitQuestionnaire = async () => {
  if (!validateCurrentSection()) return
  isSubmitting.value = true
  saveError.value = ''
  saveMessage.value = ''
  try {
    const response = await api.post('/grading/questionnaire/', { answers: answers.value })
    hasExistingResponse.value = true
    submittedAt.value = response.data.submitted_at
    questionnaireSummary.value = response.data.summary || questionnaireSummary.value
    saveMessage.value = 'Votre réponse a bien été enregistrée.'
    window.scrollTo({ top: 0, behavior: 'smooth' })
  } catch (error) {
    console.error('Failed to submit questionnaire', error)
    saveError.value = error.response?.data?.detail || "Erreur lors de l'enregistrement du questionnaire."
  } finally {
    isSubmitting.value = false
  }
}

onMounted(fetchResponse)
</script>

<template>
  <div class="questionnaire-page" data-testid="corrector-questionnaire-page">
    <header class="top-nav">
      <div class="brand">
        <button class="btn-back" @click="goBack">
          ← Dashboard
        </button>
        <span>Questionnaire Correcteur</span>
      </div>
      <div class="user-menu">
        <span>{{ authStore.user?.username }}</span>
        <button class="btn-logout" @click="handleLogout">
          Déconnexion
        </button>
      </div>
    </header>

    <main class="container">
      <div class="page-header">
        <h1>Questionnaire Korrigo PMF</h1>
        <p>Retour d’expérience correcteur sur l’outil de correction.</p>
      </div>

      <div v-if="isLoading" class="state-card">
        Chargement du questionnaire...
      </div>

      <div v-else-if="loadError" class="state-card error-card">
        {{ loadError }}
      </div>

      <template v-else>
        <div v-if="hasExistingResponse" class="info-banner success-banner" data-testid="questionnaire-completed-state">
          <strong>Merci, votre questionnaire a bien été transmis.</strong>
          <span v-if="submittedAt">Réponse envoyée le {{ formatDate(submittedAt) }}</span>
          <span>
            Participation : {{ questionnaireSummary.responses_count }} / {{ questionnaireSummary.total_eligible }}
            correcteur(s)
          </span>
          <span v-if="!questionnaireSummary.is_available">
            Le bilan sera disponible quand les {{ questionnaireSummary.remaining_count }} correcteur(s) restant(s) auront répondu.
          </span>
          <div class="completed-actions">
            <button class="btn-secondary" @click="goBack">
              Retour au dashboard
            </button>
            <button
              v-if="questionnaireSummary.is_available"
              class="btn-primary"
              @click="goToQuestionnaireBilan"
            >
              Voir le bilan
            </button>
          </div>
        </div>

        <div v-else>
        <div v-if="saveMessage" class="info-banner success-banner">
          {{ saveMessage }}
        </div>

        <div class="progress-card" data-testid="questionnaire-progress-card">
          <div class="progress-top">
            <span>Section {{ step + 1 }} / {{ totalSections }}</span>
            <span>{{ progressPercent }} % complété</span>
          </div>
          <div class="progress-bar">
            <div
              class="progress-fill"
              :style="{ width: `${((step + 1) / totalSections) * 100}%` }"
            />
          </div>
          <div class="section-title-row">
            <h2>{{ currentSection.title }}</h2>
            <span>{{ currentSection.sub }}</span>
          </div>
        </div>

        <section class="section-card">
          <div
            v-for="question in currentSection.questions"
            :key="question.id"
            class="question-block"
            :data-testid="`question-${question.id}`"
          >
            <div class="question-label">
              {{ question.label }}
              <span v-if="question.req" class="required">*</span>
            </div>
            <div v-if="question.note" class="question-note">
              {{ question.note }}
            </div>

            <div v-if="question.type === 'lk'" class="likert-block">
              <div class="likert-row">
                <button
                  v-for="value in [1, 2, 3, 4, 5]"
                  :key="value"
                  type="button"
                  class="likert-btn"
                  :class="{ selected: answers[question.id] === value }"
                  @click="setAnswer(question.id, value)"
                >
                  {{ value }}
                </button>
              </div>
              <div class="range-labels">
                <span>{{ question.low }}</span>
                <span>{{ question.high }}</span>
              </div>
            </div>

            <div v-else-if="question.type === 'ro'" class="option-list">
              <button
                v-for="option in question.opts"
                :key="option"
                type="button"
                class="option-btn"
                :class="{ selected: answers[question.id] === option }"
                @click="setAnswer(question.id, option)"
              >
                {{ option }}
              </button>
            </div>

            <div v-else-if="question.type === 'ut'" class="utility-row">
              <button
                v-for="option in ['Inutile', 'Utile', 'Indispensable']"
                :key="option"
                type="button"
                class="utility-btn"
                :class="[
                  answers[question.id] === option ? 'selected' : '',
                  option === 'Inutile' ? 'utility-useless' : '',
                  option === 'Utile' ? 'utility-useful' : '',
                  option === 'Indispensable' ? 'utility-critical' : ''
                ]"
                @click="setAnswer(question.id, option)"
              >
                {{ option }}
              </button>
            </div>

            <div v-else-if="question.type === 'ck'" class="option-list">
              <button
                v-for="option in question.opts"
                :key="option"
                type="button"
                class="option-btn checkbox-btn"
                :class="{ selected: (answers[question.id] || []).includes(option) }"
                @click="toggleCheckboxAnswer(question.id, option)"
              >
                {{ option }}
              </button>
            </div>

            <div v-else-if="question.type === 'nps'" class="nps-block">
              <div class="nps-row">
                <button
                  v-for="value in [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10]"
                  :key="value"
                  type="button"
                  class="nps-btn"
                  :class="{
                    detractor: value <= 6,
                    passive: value >= 7 && value <= 8,
                    promoter: value >= 9,
                    selected: answers[question.id] === value
                  }"
                  @click="setAnswer(question.id, value)"
                >
                  {{ value }}
                </button>
              </div>
              <div class="range-labels">
                <span>Certainement pas</span>
                <span>Absolument</span>
              </div>
            </div>

            <div v-else-if="question.type === 'ta'">
              <textarea
                :value="answers[question.id] || ''"
                class="text-area"
                :data-testid="`textarea-${question.id}`"
                :placeholder="question.ph || ''"
                @input="setAnswer(question.id, $event.target.value)"
              />
            </div>
          </div>

          <div v-if="saveError" class="error-inline">
            {{ saveError }}
          </div>

          <div class="actions-row">
            <button
              v-if="step > 0"
              type="button"
              class="btn-secondary"
              @click="goPrev"
            >
              ← Précédent
            </button>
            <span v-else />

            <button
              v-if="step < totalSections - 1"
              type="button"
              class="btn-primary"
              @click="goNext"
            >
              Section suivante →
            </button>
            <button
              v-else
              type="button"
              class="btn-primary"
              data-testid="questionnaire-submit"
              :disabled="isSubmitting"
              @click="submitQuestionnaire"
            >
              {{ isSubmitting ? 'Enregistrement...' : 'Enregistrer le questionnaire' }}
            </button>
          </div>
        </section>
        </div>
      </template>
    </main>
  </div>
</template>

<style scoped>
.questionnaire-page {
  min-height: 100vh;
  background: #f8fafc;
  font-family: 'Inter', sans-serif;
}

.top-nav {
  background: white;
  padding: 1rem 2rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid #e2e8f0;
}

.brand {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  font-weight: 700;
  color: #0f172a;
}

.user-menu {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.btn-back,
.btn-secondary {
  border: 1px solid #cbd5e1;
  background: white;
  color: #475569;
  padding: 0.55rem 0.9rem;
  border-radius: 8px;
  cursor: pointer;
}

.btn-primary {
  border: none;
  background: #b45309;
  color: white;
  padding: 0.7rem 1.1rem;
  border-radius: 8px;
  cursor: pointer;
  font-weight: 600;
}

.btn-primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-logout {
  border: 1px solid #ef4444;
  background: white;
  color: #ef4444;
  padding: 0.5rem 0.8rem;
  border-radius: 8px;
  cursor: pointer;
}

.container {
  max-width: 960px;
  margin: 0 auto;
  padding: 2rem 1rem 3rem;
}

.page-header {
  margin-bottom: 1.5rem;
}

.page-header h1 {
  margin: 0 0 0.35rem;
  color: #0f172a;
}

.page-header p {
  margin: 0;
  color: #64748b;
}

.state-card,
.progress-card,
.section-card,
.info-banner {
  background: white;
  border: 1px solid #e2e8f0;
  border-radius: 14px;
  padding: 1.25rem;
}

.state-card,
.info-banner {
  margin-bottom: 1rem;
}

.error-card,
.error-inline {
  color: #b91c1c;
  background: #fef2f2;
  border-color: #fecaca;
}

.success-banner {
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
  color: #166534;
  background: #f0fdf4;
  border-color: #bbf7d0;
}

.progress-card {
  margin-bottom: 1rem;
}

.progress-top,
.section-title-row {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
  flex-wrap: wrap;
}

.progress-top {
  color: #64748b;
  font-size: 0.92rem;
  margin-bottom: 0.75rem;
}

.progress-bar {
  height: 8px;
  background: #e2e8f0;
  border-radius: 999px;
  overflow: hidden;
  margin-bottom: 1rem;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #d97706, #f59e0b);
}

.section-title-row h2 {
  margin: 0;
  color: #0f172a;
}

.section-title-row span {
  color: #64748b;
  max-width: 520px;
}

.question-block + .question-block {
  border-top: 1px solid #e2e8f0;
  margin-top: 1.5rem;
  padding-top: 1.5rem;
}

.question-label {
  font-weight: 600;
  color: #1e293b;
  margin-bottom: 0.4rem;
}

.required {
  color: #dc2626;
}

.question-note {
  font-size: 0.9rem;
  color: #64748b;
  margin-bottom: 0.8rem;
}

.likert-row,
.utility-row,
.nps-row {
  display: grid;
  gap: 0.5rem;
}

.likert-row {
  grid-template-columns: repeat(5, minmax(0, 1fr));
}

.utility-row {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.nps-row {
  grid-template-columns: repeat(11, minmax(0, 1fr));
}

.likert-btn,
.utility-btn,
.nps-btn,
.option-btn {
  border: 1px solid #dbe0e6;
  background: white;
  color: #334155;
  border-radius: 10px;
  padding: 0.75rem;
  cursor: pointer;
  text-align: left;
}

.likert-btn,
.utility-btn,
.nps-btn {
  text-align: center;
}

.likert-btn.selected,
.option-btn.selected {
  border-color: #d97706;
  background: #fff7ed;
  color: #9a3412;
}

.utility-btn.selected.utility-useless {
  background: #fef2f2;
  border-color: #ef4444;
}

.utility-btn.selected.utility-useful {
  background: #f0fdf4;
  border-color: #22c55e;
}

.utility-btn.selected.utility-critical {
  background: #fff7ed;
  border-color: #f59e0b;
}

.option-list {
  display: grid;
  gap: 0.65rem;
}

.checkbox-btn.selected {
  background: #eff6ff;
  border-color: #3b82f6;
  color: #1d4ed8;
}

.nps-btn.detractor.selected {
  background: #fee2e2;
  border-color: #ef4444;
}

.nps-btn.passive.selected {
  background: #fef3c7;
  border-color: #f59e0b;
}

.nps-btn.promoter.selected {
  background: #dcfce7;
  border-color: #22c55e;
}

.range-labels {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
  margin-top: 0.45rem;
  color: #64748b;
  font-size: 0.85rem;
}

.text-area {
  width: 100%;
  min-height: 110px;
  padding: 0.85rem 1rem;
  border-radius: 10px;
  border: 1px solid #dbe0e6;
  resize: vertical;
  font-family: inherit;
}

.error-inline {
  margin-top: 1rem;
  padding: 0.8rem 1rem;
  border: 1px solid #fecaca;
  border-radius: 10px;
}

.actions-row {
  margin-top: 1.5rem;
  display: flex;
  justify-content: space-between;
  gap: 1rem;
}

@media (max-width: 900px) {
  .nps-row {
    grid-template-columns: repeat(6, minmax(0, 1fr));
  }
}

@media (max-width: 720px) {
  .top-nav,
  .user-menu,
  .brand,
  .actions-row,
  .section-title-row,
  .progress-top {
    flex-direction: column;
    align-items: stretch;
  }

  .likert-row,
  .utility-row {
    grid-template-columns: 1fr;
  }
}
</style>
