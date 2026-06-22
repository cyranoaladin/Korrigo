<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../../stores/auth'
import api from '../../services/api'
import DOMPurify from 'dompurify'
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
const generatedBilan = ref({ status: 'missing', html: '', generated_at: null, error: '' })
const sanitizedBilanHtml = computed(() => DOMPurify.sanitize(generatedBilan.value.html || ''))
const canSeePartialResponses = computed(() => authStore.user?.role === 'Admin' && responses.value.length > 0)
const selectedResponseUserId = ref(null)
const activeTab = ref('synthese')

const questionnaireQuestionMeta = QUESTIONNAIRE_SECTIONS.flatMap((section) => section.questions.map((question) => ({
  id: question.id,
  label: question.label,
  sectionId: section.id,
  sectionTitle: section.title
}))).reduce((acc, item) => {
  acc[item.id] = item
  return acc
}, {})

const formatAnswerValue = (value) => {
  if (Array.isArray(value)) return value.length ? value.join(', ') : '—'
  if (value === null || value === undefined || value === '') return '—'
  return value
}

const selectedDetailedResponse = computed(() => responses.value.find((response) => response.user_id === selectedResponseUserId.value) || responses.value[0] || null)

const selectedDetailedSections = computed(() => {
  if (!selectedDetailedResponse.value) return []
  const grouped = Object.entries(selectedDetailedResponse.value.answers || {}).reduce((acc, [key, value]) => {
    const meta = questionnaireQuestionMeta[key] || { sectionId: 'other', sectionTitle: 'Autres réponses', label: key }
    const existing = acc[meta.sectionId] || { id: meta.sectionId, title: meta.sectionTitle, items: [] }
    existing.items.push({
      key,
      label: meta.label,
      value: formatAnswerValue(value)
    })
    acc[meta.sectionId] = existing
    return acc
  }, {})

  const ordered = QUESTIONNAIRE_SECTIONS.map((section) => grouped[section.id]).filter(Boolean)
  if (grouped.other) ordered.push(grouped.other)
  return ordered
})

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
    generatedBilan.value = response.data.generated_bilan || generatedBilan.value
    infoMessage.value = response.data.detail || ''
    if (responses.value.length && !selectedResponseUserId.value) {
      selectedResponseUserId.value = responses.value[0].user_id
    }
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
  router.push('/admin/dashboard')
}

const handleLogout = async () => {
  await authStore.logout()
  router.push('/')
}

onMounted(fetchBilan)
</script>

<template>
  <div class="bilan-page" data-testid="questionnaire-bilan-page">
    <!-- Premium Header -->
    <header class="bilan-header">
      <div class="header-content">
        <button class="header-btn" @click="goToDashboard">
          <span class="btn-icon">&#8592;</span> Dashboard
        </button>
        <div class="header-title">
          <h1>Bilan Questionnaire Correcteurs</h1>
          <p class="header-subtitle">{{ summary.responses_count }} réponse(s) sur {{ summary.total_eligible }} correcteur(s)</p>
        </div>
        <div class="header-actions">
          <span class="header-user">{{ authStore.user?.username }}</span>
          <button class="header-btn logout" @click="handleLogout">Déconnexion</button>
        </div>
      </div>
    </header>

    <!-- Tab Navigation -->
    <nav class="tab-bar" v-if="!isLoading && !error">
      <div class="tab-bar-inner">
        <button :class="['tab', { active: activeTab === 'synthese' }]" @click="activeTab = 'synthese'">
          <span class="tab-icon">&#x1F4CA;</span> Synthèse
        </button>
        <button :class="['tab', { active: activeTab === 'bilan' }]" @click="activeTab = 'bilan'">
          <span class="tab-icon">&#x1F4C4;</span> Bilan complet
        </button>
        <button :class="['tab', { active: activeTab === 'donnees' }]" @click="activeTab = 'donnees'">
          <span class="tab-icon">&#x1F4C8;</span> Données détaillées
        </button>
        <button :class="['tab', { active: activeTab === 'retours' }]" @click="activeTab = 'retours'">
          <span class="tab-icon">&#x1F4AC;</span> Retours libres
        </button>
        <button :class="['tab', { active: activeTab === 'v2' }]" @click="activeTab = 'v2'">
          <span class="tab-icon">&#x1F680;</span> Améliorations V2
        </button>
      </div>
    </nav>

    <!-- Content -->
    <main class="bilan-content">
      <!-- Loading state -->
      <div v-if="isLoading" class="glass-card loading-card">
        <div class="loading-spinner"></div>
        <p>Chargement du bilan...</p>
      </div>

      <!-- Error state -->
      <div v-else-if="error" class="glass-card error-card">
        <div class="error-icon">!</div>
        <p>{{ error }}</p>
      </div>

      <template v-else>
        <!-- Tab: Synthèse -->
        <div v-show="activeTab === 'synthese'" class="tab-panel">
          <section class="kpi-grid" data-testid="questionnaire-bilan-summary">
            <div class="kpi-card kpi-participation">
              <div class="kpi-accent"></div>
              <span class="kpi-label">Participation</span>
              <strong class="kpi-value">{{ summary.responses_count }} / {{ summary.total_eligible }}</strong>
              <span class="kpi-sub">{{ summary.completion_rate }} % de complétion</span>
            </div>
            <div class="kpi-card kpi-nps">
              <div class="kpi-accent"></div>
              <span class="kpi-label">NPS moyen</span>
              <strong class="kpi-value">{{ npsAverage ?? '—' }}</strong>
              <span class="kpi-sub">sur 10</span>
            </div>
            <div class="kpi-card kpi-index">
              <div class="kpi-accent"></div>
              <span class="kpi-label">Indice NPS</span>
              <strong class="kpi-value">{{ npsIndex ?? '—' }}</strong>
              <span class="kpi-sub">promoteurs - détracteurs</span>
            </div>
            <div class="kpi-card kpi-ergo">
              <div class="kpi-accent"></div>
              <span class="kpi-label">Ergonomie</span>
              <strong class="kpi-value">{{ ergonomicsAverage ?? '—' }}</strong>
              <span class="kpi-sub">moyenne / 5</span>
            </div>
            <div class="kpi-card kpi-trust">
              <div class="kpi-accent"></div>
              <span class="kpi-label">Confiance</span>
              <strong class="kpi-value">{{ trustAverage ?? '—' }}</strong>
              <span class="kpi-sub">moyenne / 5</span>
            </div>
            <div class="kpi-card kpi-paper">
              <div class="kpi-accent"></div>
              <span class="kpi-label">Gain vs papier</span>
              <strong class="kpi-value">{{ paperAverage ?? '—' }}</strong>
              <span class="kpi-sub">moyenne / 5</span>
            </div>
          </section>

          <section class="glass-card nps-explainer">
            <h3>Qu'est-ce que le NPS (Net Promoter Score) ?</h3>
            <p>Le NPS mesure la probabilité qu'un utilisateur recommande l'outil à un collègue, sur une échelle de 0 à 10. Les répondants sont classés en trois catégories :</p>
            <ul>
              <li><strong class="promoter">Promoteurs (9-10)</strong> — enthousiastes, ils recommandent activement</li>
              <li><strong class="passive">Passifs (7-8)</strong> — satisfaits mais sans enthousiasme</li>
              <li><strong class="detractor">Détracteurs (0-6)</strong> — insatisfaits, risque de bouche-à-oreille négatif</li>
            </ul>
            <p><strong>Indice NPS</strong> = % Promoteurs − % Détracteurs. Le score varie de −100 à +100. Un NPS positif est considéré comme bon, au-dessus de +50 comme excellent.</p>
          </section>

          <section class="glass-card progress-section">
            <div class="section-head">
              <h2>Participation</h2>
              <span class="section-badge">{{ summary.completion_rate }} %</span>
            </div>
            <div class="progress-track">
              <div class="progress-fill" :style="{ width: `${summary.completion_rate}%` }"></div>
            </div>
          </section>
        </div>

        <!-- Tab: Bilan complet -->
        <div v-show="activeTab === 'bilan'" class="tab-panel">
          <div v-if="!summary.is_available && !canSeePartialResponses && generatedBilan.status !== 'ready'" class="glass-card empty-card">
            <div class="empty-icon">&#x1F4CB;</div>
            <p>Le bilan détaillé n'est pas encore disponible.</p>
          </div>

          <section v-if="generatedBilan.status === 'ready'" class="glass-card generated-bilan-section">
            <div class="section-head">
              <h2>Bilan automatique</h2>
              <span class="section-badge">{{ formatDate(generatedBilan.generated_at) }}</span>
            </div>
            <div class="generated-bilan-html" v-html="sanitizedBilanHtml" />
          </section>

          <section v-if="generatedBilan.status === 'pending'" class="glass-card info-card">
            <div class="loading-spinner small"></div>
            <p>Le bilan automatique est en cours de génération.</p>
          </section>

          <section v-if="generatedBilan.status === 'failed'" class="glass-card error-card">
            <p>{{ generatedBilan.error || "Le bilan automatique n'a pas pu être généré pour le moment." }}</p>
          </section>
        </div>

        <!-- Tab: Données détaillées -->
        <div v-show="activeTab === 'donnees'" class="tab-panel">
          <template v-if="responses.length">
            <section class="two-columns">
              <div class="glass-card">
                <div class="section-head">
                  <h2>Sentiment global</h2>
                  <span class="section-badge">{{ responses.length }} répondant(s)</span>
                </div>
                <div class="stat-list">
                  <div v-for="item in (sentimentStats || []).filter(i => !!i)" :key="item.label" class="stat-row">
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

              <div class="glass-card">
                <div class="section-head">
                  <h2>Recommandation prochain bac blanc</h2>
                  <span class="section-badge">{{ responses.length }} répondant(s)</span>
                </div>
                <div class="stat-list">
                  <div v-for="item in (recommendationStats || []).filter(i => !!i)" :key="item.label" class="stat-row">
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

            <section class="glass-card">
              <div class="section-head">
                <h2>Utilité des outils de correction</h2>
                <span class="section-badge">{{ QUESTIONNAIRE_SECTIONS[1].questions.length - 2 }} items évalués</span>
              </div>
              <div class="tool-grid">
                <div v-for="tool in (toolStats || []).filter(i => !!i)" :key="tool.id" class="tool-card">
                  <h3>{{ tool.label }}</h3>
                  <div v-for="level in (tool.levels || []).filter(i => !!i)" :key="level.label" class="tool-level-row">
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

            <section class="glass-card">
              <div class="section-head">
                <h2>Points de blocage signalés</h2>
                <span class="section-badge">Question multiple</span>
              </div>
              <div class="stat-list">
                <div v-for="item in (blockingStats || []).filter(i => !!i)" :key="item.label" class="stat-row">
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
          </template>

          <div v-else class="glass-card empty-card">
            <p>Les données détaillées seront affichées dès réception des premières réponses.</p>
          </div>
        </div>

        <!-- Tab: Retours libres -->
        <div v-show="activeTab === 'retours'" class="tab-panel">
          <template v-if="responses.length">
            <section v-if="missingFeatures.length" class="glass-card">
              <div class="section-head">
                <h2>Fonctionnalités manquantes</h2>
                <span class="section-badge">{{ missingFeatures.length }} verbatim(s)</span>
              </div>
              <div class="verbatim-list">
                <div v-for="item in (missingFeatures || []).filter(i => !!i)" :key="`${item.author}-${item.submittedAt}-q54`" class="verbatim-card">
                  <p>{{ item.text }}</p>
                  <span class="verbatim-meta">{{ item.author }} — {{ formatDate(item.submittedAt) }}</span>
                </div>
              </div>
            </section>

            <section v-if="bugReports.length" class="glass-card">
              <div class="section-head">
                <h2>Bugs et problèmes signalés</h2>
                <span class="section-badge">{{ bugReports.length }} verbatim(s)</span>
              </div>
              <div class="verbatim-list">
                <div v-for="item in (bugReports || []).filter(i => !!i)" :key="`${item.author}-${item.submittedAt}-q55`" class="verbatim-card bug">
                  <p>{{ item.text }}</p>
                  <span class="verbatim-meta">{{ item.author }} — {{ formatDate(item.submittedAt) }}</span>
                </div>
              </div>
            </section>

            <section v-if="finalComments.length" class="glass-card">
              <div class="section-head">
                <h2>Commentaires libres</h2>
                <span class="section-badge">{{ finalComments.length }} verbatim(s)</span>
              </div>
              <div class="verbatim-list">
                <div v-for="item in (finalComments || []).filter(i => !!i)" :key="`${item.author}-${item.submittedAt}-q62`" class="verbatim-card comment">
                  <p>{{ item.text }}</p>
                  <span class="verbatim-meta">{{ item.author }} — {{ formatDate(item.submittedAt) }}</span>
                </div>
              </div>
            </section>

            <div v-if="!missingFeatures.length && !bugReports.length && !finalComments.length" class="glass-card empty-card">
              <p>Aucun retour libre pour le moment.</p>
            </div>
          </template>

          <div v-else class="glass-card empty-card">
            <p>Les retours libres seront affichés dès réception des premières réponses.</p>
          </div>
        </div>

        <!-- Tab: Améliorations V2 -->
        <div v-show="activeTab === 'v2'" class="tab-panel">
          <div class="v2-intro glass-card">
            <h2>Améliorations apportées — V2 (Mars 2026)</h2>
            <p class="v2-subtitle">En réponse directe aux retours des correcteurs, les améliorations suivantes ont été développées et déployées sur la plateforme.</p>
          </div>

          <div class="v2-cards-grid">
            <div class="v2-card">
              <div class="v2-card-header">
                <span class="priority-badge critical">1</span>
                <span class="status-badge deployed">Déployé</span>
              </div>
              <h3>Friction annotation / barème</h3>
              <p class="v2-problem">Le panneau barème se réinitialisait en haut à chaque retour depuis les annotations, dissuadant les correcteurs d'annoter.</p>
              <p class="v2-source">Retours correcteurs anonymisés</p>
              <div class="v2-solution">
                <strong>Refonte complète du layout :</strong> le barème est désormais affiché en permanence dans le panneau lateral droit. Les outils d'annotation sont dans la barre d'outils au-dessus de la copie. Plus aucune navigation entre onglets n'est nécessaire — les deux sont visibles simultanément.
              </div>
            </div>

            <div class="v2-card">
              <div class="v2-card-header">
                <span class="priority-badge high">2</span>
                <span class="status-badge deployed">Déployé</span>
              </div>
              <h3>Outil tampon Vrai/Faux manquant</h3>
              <p class="v2-problem">Absence d'un outil de marquage rapide V/X correspondant au geste papier le plus fréquent.</p>
              <p class="v2-source">Retours correcteurs anonymisés</p>
              <div class="v2-solution">
                <strong>Boutons V et F dans la barre d'outils :</strong> un clic sur le bouton active le mode tampon. Chaque rectangle dessiné sur la copie crée instantanément un checkmark vert ou une croix rouge sans ouvrir d'éditeur. Le tampon persiste sur le PDF final remis à l'élève.
              </div>
            </div>

            <div class="v2-card">
              <div class="v2-card-header">
                <span class="priority-badge high">3</span>
                <span class="status-badge deployed">Déployé</span>
              </div>
              <h3>Outils d'annotation lents</h3>
              <p class="v2-problem">Le workflow de création d'annotation nécessitait trop d'étapes (sélection outil, clic, saisie, validation).</p>
              <p class="v2-source">Ensemble des correcteurs</p>
              <div class="v2-solution">
                <strong>6 boutons d'annotation rapide dans la barre d'outils :</strong> Commentaire, Surlignage, Erreur, Bonus, Vrai, Faux. Les 3 premiers ouvrent un éditeur de texte pour saisir un commentaire. Les 3 derniers créent un tampon visuel instantané sans éditeur.
              </div>
            </div>

            <div class="v2-card">
              <div class="v2-card-header">
                <span class="priority-badge blocking">4</span>
                <span class="status-badge deployed">Déployé</span>
              </div>
              <h3>Copies bloquées en mode "locked"</h3>
              <p class="v2-problem">Des copies restaient verrouillées sans possibilité d'y accéder ni de les annoter.</p>
              <p class="v2-source">Retours correcteurs anonymisés</p>
              <div class="v2-solution">
                <strong>Bouton "Déverrouiller" (administrateur) :</strong> visible dans la barre d'outils pour les administrateurs. Force la suppression du verrou avec journalisation complète de l'action (qui a déverrouillé, quand, ancien propriétaire du verrou).
              </div>
            </div>

            <div class="v2-card">
              <div class="v2-card-header">
                <span class="priority-badge medium">5</span>
                <span class="status-badge deployed">Déployé</span>
              </div>
              <h3>Impossible de revenir sur une copie finalisée</h3>
              <p class="v2-problem">Une fois la copie corrigée, aucune modification n'était possible même en cas d'erreur.</p>
              <p class="v2-source">Retour correcteur anonymisé</p>
              <div class="v2-solution">
                <strong>Bouton "Rouvrir" (superutilisateur) :</strong> permet de remettre une copie finalisée en statut "Pret" pour correction. Le PDF final est invalidé, mais toutes les notes, annotations, remarques et appréciations sont conservées. Action entièrement tracée dans le journal d'audit.
              </div>
            </div>

            <div class="v2-card">
              <div class="v2-card-header">
                <span class="priority-badge medium">6</span>
                <span class="status-badge deployed">Déployé</span>
              </div>
              <h3>Pas de suivi des questions non corrigées</h3>
              <p class="v2-problem">Aucun indicateur visuel pour savoir quelles questions du barème avaient reçu une note.</p>
              <p class="v2-source">Retour correcteur anonymisé</p>
              <div class="v2-solution">
                <strong>Barre de progression segmentée par question :</strong> dans le tableau de bord correcteur, chaque copie affiche une barre visuelle indiquant les questions notées (vert) et non notées (gris), avec le pourcentage et le détail (ex : "5/8 questions notées — 63 %").
              </div>
            </div>

            <div class="v2-card">
              <div class="v2-card-header">
                <span class="priority-badge medium">7</span>
                <span class="status-badge deployed">Déployé</span>
              </div>
              <h3>Commentaires non mémorisés entre copies</h3>
              <p class="v2-problem">Les remarques saisies sur une copie ne pouvaient pas être réutilisées sur la suivante.</p>
              <p class="v2-source">Retour correcteur anonymisé</p>
              <div class="v2-solution">
                <strong>Sauvegarde automatique dans la banque personnelle :</strong> chaque remarque substantielle (plus de 5 caractères) est automatiquement enregistrée dans la banque d'annotations personnelle du correcteur avec le contexte exercice/question. Les remarques fréquentes sont proposées en priorité lors de la correction de la copie suivante.
              </div>
            </div>

            <div class="v2-card">
              <div class="v2-card-header">
                <span class="priority-badge medium">8</span>
                <span class="status-badge deployed">Déployé</span>
              </div>
              <h3>Chargement lent des pages PDF</h3>
              <p class="v2-problem">Délai perceptible lors du passage d'une page à l'autre.</p>
              <p class="v2-source">Retours correcteurs anonymisés</p>
              <div class="v2-solution">
                <strong>Préchargement des pages adjacentes :</strong> les pages précédente et suivante sont chargées en arrière-plan avant que le correcteur ne navigue. Résultat : affichage quasi-instantané lors du changement de page. Ajout d'une transition en fondu pour éliminer le flash blanc.
              </div>
            </div>

            <div class="v2-card">
              <div class="v2-card-header">
                <span class="priority-badge medium">9</span>
                <span class="status-badge deployed">Déployé</span>
              </div>
              <h3>Scroll et navigation non fluides</h3>
              <p class="v2-problem">Le défilement des pages n'était pas naturel et le zoom difficile à ajuster.</p>
              <p class="v2-source">Retours correcteurs anonymisés</p>
              <div class="v2-solution">
                <strong>Scroll fluide natif + zoom amélioré :</strong> activation du scroll smooth CSS, support du Ctrl+molette pour zoomer/dézoomer rapidement, bouton « Ajuster à la largeur », clic sur le pourcentage pour réinitialiser le zoom à 100 %. Temps de réponse au changement de page réduit de 400 ms à 300 ms.
              </div>
            </div>

            <div class="v2-card">
              <div class="v2-card-header">
                <span class="priority-badge medium">10</span>
                <span class="status-badge deployed">Déployé</span>
              </div>
              <h3>Barème non replié par défaut</h3>
              <p class="v2-problem">Tous les exercices du barème étaient dépliés à l'ouverture, encombrant l'espace de travail.</p>
              <p class="v2-source">Retour d'usage général</p>
              <div class="v2-solution">
                <strong>Comportement accordéon :</strong> tous les exercices sont repliés par défaut à l'ouverture de la copie. Cliquer sur un exercice le déplie et replie automatiquement le précédent. Un seul exercice est visible à la fois pour un confort d'affichage optimal.
              </div>
            </div>
          </div>

          <div class="glass-card v2-footer-card">
            <p><strong>Date de déploiement :</strong> 23 mars 2026</p>
            <p><strong>Périmètre :</strong> 10 améliorations · 84 fichiers modifiés · 15 338 lignes de code · 414 tests automatisés</p>
            <div class="v2-note">
              Ces améliorations sont le résultat direct de l'analyse des 7 réponses au questionnaire et du bilan automatique. Chaque modification a été testée, validée et déployée en production sans interruption de service ni perte de données.
            </div>
          </div>
        </div>
      </template>
    </main>
  </div>
</template>

<style scoped>
/* ============================================
   PREMIUM BILAN PAGE — GLASSMORPHISM DESIGN
   ============================================ */

/* Base page */
.bilan-page {
  min-height: 100vh;
  background: linear-gradient(135deg, #f5f3ff 0%, #ede9fe 30%, #e0f2fe 70%, #f0fdf4 100%);
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  color: #1e293b;
}

/* ---- HEADER ---- */
.bilan-header {
  background: linear-gradient(135deg, #312e81 0%, #4338ca 50%, #3730a3 100%);
  padding: 0;
  position: sticky;
  top: 0;
  z-index: 100;
  box-shadow: 0 4px 30px rgba(49, 46, 129, 0.25);
}

.header-content {
  max-width: 1280px;
  margin: 0 auto;
  padding: 1rem 2rem;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1.5rem;
}

.header-title {
  flex: 1;
  text-align: center;
}

.header-title h1 {
  margin: 0;
  color: #ffffff;
  font-size: 1.5rem;
  font-weight: 700;
  letter-spacing: -0.02em;
}

.header-subtitle {
  margin: 0.25rem 0 0;
  color: rgba(255, 255, 255, 0.7);
  font-size: 0.9rem;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 0.6rem;
}

.header-user {
  color: rgba(255, 255, 255, 0.85);
  font-size: 0.9rem;
  font-weight: 500;
  padding-right: 0.5rem;
  border-right: 1px solid rgba(255, 255, 255, 0.2);
}

.header-btn {
  background: rgba(255, 255, 255, 0.12);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(255, 255, 255, 0.2);
  color: #ffffff;
  padding: 0.5rem 1rem;
  border-radius: 10px;
  font-size: 0.88rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
  white-space: nowrap;
}

.header-btn:hover {
  background: rgba(255, 255, 255, 0.22);
  border-color: rgba(255, 255, 255, 0.35);
  transform: translateY(-1px);
}

.header-btn.logout {
  background: rgba(239, 68, 68, 0.2);
  border-color: rgba(239, 68, 68, 0.4);
}

.header-btn.logout:hover {
  background: rgba(239, 68, 68, 0.35);
  border-color: rgba(239, 68, 68, 0.6);
}

.btn-icon {
  font-size: 1.1rem;
}

/* ---- TAB BAR ---- */
.tab-bar {
  background: rgba(255, 255, 255, 0.92);
  backdrop-filter: blur(20px);
  border-bottom: 1px solid rgba(0, 0, 0, 0.06);
  box-shadow: 0 2px 16px rgba(0, 0, 0, 0.04);
  position: sticky;
  top: 68px;
  z-index: 90;
}

.tab-bar-inner {
  max-width: 1280px;
  margin: 0 auto;
  padding: 0 2rem;
  display: flex;
  gap: 0;
  overflow-x: auto;
}

.tab {
  position: relative;
  background: none;
  border: none;
  padding: 0.85rem 1.25rem;
  font-size: 0.92rem;
  font-weight: 500;
  color: #64748b;
  cursor: pointer;
  transition: all 0.25s ease;
  white-space: nowrap;
  border-bottom: 3px solid transparent;
}

.tab:hover {
  color: #4f46e5;
  background: rgba(79, 70, 229, 0.04);
}

.tab.active {
  color: #4f46e5;
  border-bottom-color: #4f46e5;
  background: rgba(79, 70, 229, 0.06);
}

.tab-icon {
  margin-right: 0.4rem;
  font-size: 1rem;
}

/* ---- MAIN CONTENT ---- */
.bilan-content {
  max-width: 1280px;
  margin: 0 auto;
  padding: 2rem 2rem 4rem;
}

.tab-panel {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

/* ---- GLASS CARD BASE ---- */
.glass-card {
  background: rgba(255, 255, 255, 0.85);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(255, 255, 255, 0.6);
  border-radius: 16px;
  padding: 1.5rem;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.06);
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.glass-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 30px rgba(0, 0, 0, 0.08);
}

/* ---- LOADING ---- */
.loading-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 3rem;
  gap: 1rem;
  color: #64748b;
}

.loading-spinner {
  width: 40px;
  height: 40px;
  border: 3px solid #e2e8f0;
  border-top-color: #4f46e5;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

.loading-spinner.small {
  width: 24px;
  height: 24px;
  border-width: 2px;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* ---- ERROR / INFO / EMPTY ---- */
.error-card {
  background: rgba(254, 242, 242, 0.9);
  border-color: #fecaca;
  color: #b91c1c;
  display: flex;
  align-items: center;
  gap: 1rem;
}

.error-icon {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: #ef4444;
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: 1.2rem;
  flex-shrink: 0;
}

.info-card {
  background: rgba(240, 249, 255, 0.9);
  border-color: #bae6fd;
  color: #0c4a6e;
  display: flex;
  align-items: center;
  gap: 1rem;
}

.info-card p,
.error-card p {
  margin: 0;
}

.empty-card {
  text-align: center;
  color: #64748b;
  padding: 3rem;
}

.empty-icon {
  font-size: 2.5rem;
  margin-bottom: 0.75rem;
  opacity: 0.5;
}

/* ---- KPI GRID ---- */
.kpi-grid {
  display: grid;
  grid-template-columns: repeat(6, minmax(0, 1fr));
  gap: 1rem;
}

.kpi-card {
  background: rgba(255, 255, 255, 0.9);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(255, 255, 255, 0.6);
  border-radius: 16px;
  padding: 1.25rem;
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
  position: relative;
  overflow: hidden;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.06);
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.kpi-card:hover {
  transform: translateY(-3px);
  box-shadow: 0 8px 30px rgba(0, 0, 0, 0.1);
}

.kpi-accent {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 4px;
  border-radius: 16px 16px 0 0;
}

.kpi-participation .kpi-accent { background: linear-gradient(90deg, #4f46e5, #7c3aed); }
.kpi-nps .kpi-accent { background: linear-gradient(90deg, #059669, #10b981); }
.kpi-index .kpi-accent { background: linear-gradient(90deg, #0891b2, #06b6d4); }
.kpi-ergo .kpi-accent { background: linear-gradient(90deg, #d97706, #f59e0b); }
.kpi-trust .kpi-accent { background: linear-gradient(90deg, #7c3aed, #a78bfa); }
.kpi-paper .kpi-accent { background: linear-gradient(90deg, #059669, #34d399); }

.kpi-label {
  color: #64748b;
  font-size: 0.85rem;
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.kpi-value {
  color: #1e293b;
  font-size: 2rem;
  font-weight: 800;
  letter-spacing: -0.03em;
  line-height: 1.1;
}

.kpi-sub {
  color: #94a3b8;
  font-size: 0.82rem;
}

/* ---- NPS EXPLAINER ---- */
.nps-explainer {
  background: rgba(240, 249, 255, 0.85);
  border-color: rgba(186, 230, 253, 0.6);
  line-height: 1.7;
}

.nps-explainer h3 {
  color: #0c4a6e;
  margin: 0 0 0.75rem;
  font-size: 1.05rem;
}

.nps-explainer p {
  color: #334155;
  margin: 0 0 0.5rem;
  font-size: 0.92rem;
}

.nps-explainer ul {
  margin: 0.75rem 0;
  padding-left: 1.5rem;
}

.nps-explainer li {
  color: #334155;
  font-size: 0.92rem;
  margin-bottom: 0.35rem;
  line-height: 1.6;
}

.nps-explainer .promoter { color: #059669; }
.nps-explainer .passive { color: #d97706; }
.nps-explainer .detractor { color: #dc2626; }

/* ---- SECTION HEAD ---- */
.section-head {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
  align-items: center;
  margin-bottom: 1.25rem;
}

.section-head h2 {
  margin: 0;
  color: #1e293b;
  font-size: 1.15rem;
  font-weight: 700;
}

.section-badge {
  color: #4f46e5;
  font-size: 0.85rem;
  font-weight: 600;
  background: rgba(79, 70, 229, 0.08);
  padding: 0.3rem 0.75rem;
  border-radius: 20px;
  white-space: nowrap;
}

/* ---- PROGRESS ---- */
.progress-section {
  /* inherits glass-card */
}

.progress-track {
  width: 100%;
  height: 12px;
  background: #e2e8f0;
  border-radius: 999px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #4f46e5, #059669);
  border-radius: 999px;
  transition: width 0.6s ease;
}

.waiting-text {
  color: #64748b;
  font-size: 0.9rem;
  margin: 0.75rem 0 0;
}

/* ---- GENERATED BILAN ---- */
.generated-bilan-section {
  line-height: 1.75;
}

.generated-bilan-html :deep(h1),
.generated-bilan-html :deep(h2),
.generated-bilan-html :deep(h3) {
  color: #1e293b;
  margin-top: 1.5rem;
  margin-bottom: 0.75rem;
  font-weight: 700;
}

.generated-bilan-html :deep(h2) {
  font-size: 1.25rem;
  padding-bottom: 0.5rem;
  border-bottom: 2px solid;
  border-image: linear-gradient(90deg, #4f46e5, transparent) 1;
}

.generated-bilan-html :deep(h3) {
  font-size: 1.1rem;
  color: #4338ca;
}

.generated-bilan-html :deep(p),
.generated-bilan-html :deep(li),
.generated-bilan-html :deep(td),
.generated-bilan-html :deep(th) {
  color: #334155;
  font-size: 0.95rem;
  line-height: 1.7;
}

.generated-bilan-html :deep(blockquote) {
  margin: 1rem 0;
  padding: 0.85rem 1.25rem;
  border-left: 4px solid #4f46e5;
  background: rgba(79, 70, 229, 0.04);
  border-radius: 0 12px 12px 0;
  font-style: italic;
  color: #475569;
}

.generated-bilan-html :deep(table) {
  width: 100%;
  border-collapse: collapse;
  margin: 1rem 0;
  border-radius: 12px;
  overflow: hidden;
}

.generated-bilan-html :deep(th) {
  background: rgba(79, 70, 229, 0.06);
  font-weight: 600;
  text-align: left;
}

.generated-bilan-html :deep(th),
.generated-bilan-html :deep(td) {
  border: 1px solid #e2e8f0;
  padding: 0.7rem 0.85rem;
  vertical-align: top;
}

.generated-bilan-html :deep(strong) {
  color: #1e293b;
}

.generated-bilan-html :deep(ul),
.generated-bilan-html :deep(ol) {
  padding-left: 1.5rem;
  margin: 0.5rem 0;
}

.generated-bilan-html :deep(li) {
  margin-bottom: 0.3rem;
}

.generated-bilan-html :deep(hr) {
  border: none;
  height: 2px;
  background: linear-gradient(90deg, #4f46e5, #059669, transparent);
  margin: 2rem 0;
}

/* ---- TWO COLUMNS ---- */
.two-columns {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 1.25rem;
}

/* ---- STAT LIST ---- */
.stat-list {
  display: flex;
  flex-direction: column;
  gap: 0.9rem;
}

.stat-row {
  display: grid;
  gap: 0.45rem;
}

.stat-label-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.stat-label-row span {
  color: #475569;
  font-size: 0.9rem;
}

.stat-label-row strong {
  color: #1e293b;
  font-size: 0.95rem;
}

.mini-bar {
  width: 100%;
  height: 8px;
  background: #e2e8f0;
  border-radius: 999px;
  overflow: hidden;
}

.mini-fill {
  height: 100%;
  background: linear-gradient(90deg, #4f46e5, #7c3aed);
  border-radius: 999px;
  transition: width 0.4s ease;
}

.mini-fill.amber { background: linear-gradient(90deg, #d97706, #f59e0b); }
.mini-fill.red { background: linear-gradient(90deg, #dc2626, #ef4444); }
.mini-fill.blue { background: linear-gradient(90deg, #2563eb, #3b82f6); }
.mini-fill.green { background: linear-gradient(90deg, #059669, #10b981); }

/* ---- TOOL GRID ---- */
.tool-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 1rem;
}

.tool-card {
  border: 1px solid rgba(79, 70, 229, 0.1);
  border-radius: 14px;
  padding: 1.15rem;
  background: rgba(255, 255, 255, 0.6);
  transition: all 0.2s ease;
}

.tool-card:hover {
  border-color: rgba(79, 70, 229, 0.25);
  background: rgba(255, 255, 255, 0.85);
}

.tool-card h3 {
  margin: 0 0 0.9rem;
  color: #1e293b;
  font-size: 0.98rem;
  font-weight: 600;
}

.tool-level-row {
  display: grid;
  grid-template-columns: 110px 1fr 30px;
  gap: 0.75rem;
  align-items: center;
}

.tool-level-row span {
  font-size: 0.85rem;
  color: #64748b;
}

.tool-level-row strong {
  font-size: 0.88rem;
  color: #1e293b;
  text-align: right;
}

.tool-level-row + .tool-level-row {
  margin-top: 0.65rem;
}

.tool-bar {
  height: 6px;
}

/* ---- VERBATIM ---- */
.verbatim-list {
  display: grid;
  gap: 0.85rem;
}

.verbatim-card {
  border-left: 4px solid #f59e0b;
  background: rgba(255, 251, 235, 0.8);
  padding: 1rem 1.25rem;
  border-radius: 0 14px 14px 0;
  transition: all 0.2s ease;
}

.verbatim-card:hover {
  transform: translateX(4px);
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.05);
}

.verbatim-card.bug {
  border-left-color: #ef4444;
  background: rgba(254, 242, 242, 0.6);
}

.verbatim-card.comment {
  border-left-color: #4f46e5;
  background: rgba(245, 243, 255, 0.6);
}

.verbatim-card p {
  margin: 0 0 0.5rem;
  color: #1e293b;
  line-height: 1.6;
  font-size: 0.95rem;
}

.verbatim-meta {
  color: #64748b;
  font-size: 0.82rem;
}

/* ---- V2 IMPROVEMENTS — CARD LAYOUT ---- */
.v2-intro {
  text-align: center;
  background: linear-gradient(135deg, rgba(79, 70, 229, 0.06), rgba(5, 150, 105, 0.06));
}

.v2-intro h2 {
  margin: 0 0 0.5rem;
  color: #312e81;
  font-size: 1.35rem;
  font-weight: 800;
}

.v2-subtitle {
  margin: 0;
  color: #475569;
  font-size: 0.95rem;
  line-height: 1.6;
}

.v2-cards-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 1.25rem;
  margin-top: 1.25rem;
}

.v2-card {
  background: rgba(255, 255, 255, 0.9);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(255, 255, 255, 0.6);
  border-radius: 16px;
  padding: 1.5rem;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.06);
  transition: all 0.25s ease;
  display: flex;
  flex-direction: column;
  gap: 0.6rem;
}

.v2-card:hover {
  transform: translateY(-3px);
  box-shadow: 0 12px 36px rgba(0, 0, 0, 0.1);
}

.v2-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.v2-card h3 {
  margin: 0;
  color: #1e293b;
  font-size: 1.02rem;
  font-weight: 700;
}

.v2-problem {
  margin: 0;
  color: #64748b;
  font-size: 0.88rem;
  line-height: 1.5;
}

.v2-source {
  margin: 0;
  color: #94a3b8;
  font-size: 0.8rem;
  font-style: italic;
}

.v2-solution {
  margin: 0;
  padding: 0.85rem 1rem;
  background: rgba(79, 70, 229, 0.04);
  border-radius: 10px;
  border-left: 3px solid #4f46e5;
  color: #334155;
  font-size: 0.88rem;
  line-height: 1.55;
}

.v2-solution strong {
  color: #4338ca;
}

/* Priority badges */
.priority-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border-radius: 10px;
  font-weight: 800;
  font-size: 0.85rem;
  color: white;
  flex-shrink: 0;
}

.priority-badge.critical { background: linear-gradient(135deg, #dc2626, #b91c1c); }
.priority-badge.high { background: linear-gradient(135deg, #f59e0b, #d97706); }
.priority-badge.blocking { background: linear-gradient(135deg, #7c3aed, #6d28d9); }
.priority-badge.medium { background: linear-gradient(135deg, #3b82f6, #2563eb); }

/* Status badges */
.status-badge.deployed {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  padding: 0.3rem 0.75rem;
  border-radius: 20px;
  font-size: 0.78rem;
  font-weight: 600;
  background: linear-gradient(135deg, #dcfce7, #bbf7d0);
  color: #166534;
  border: 1px solid #86efac;
  position: relative;
}

.status-badge.deployed::before {
  content: '';
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #22c55e;
  animation: pulse-dot 2s ease-in-out infinite;
}

@keyframes pulse-dot {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.5; transform: scale(1.4); }
}

/* V2 Footer */
.v2-footer-card {
  margin-top: 1.25rem;
}

.v2-footer-card p {
  margin: 0.3rem 0;
  color: #475569;
  font-size: 0.92rem;
}

.v2-note {
  margin-top: 1rem;
  padding: 0.85rem 1.15rem;
  background: linear-gradient(135deg, rgba(5, 150, 105, 0.06), rgba(16, 185, 129, 0.08));
  border-left: 4px solid #059669;
  border-radius: 0 12px 12px 0;
  color: #166534;
  font-size: 0.9rem;
  line-height: 1.6;
}

/* ---- RESPONSIVE ---- */
@media (max-width: 1100px) {
  .kpi-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }

  .v2-cards-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 960px) {
  .kpi-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .two-columns,
  .tool-grid {
    grid-template-columns: 1fr;
  }

  .v2-cards-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 720px) {
  .header-content {
    flex-direction: column;
    align-items: stretch;
    text-align: center;
    padding: 0.85rem 1rem;
  }

  .header-title {
    order: -1;
  }

  .header-title h1 {
    font-size: 1.2rem;
  }

  .header-actions {
    justify-content: center;
    flex-wrap: wrap;
  }

  .tab-bar-inner {
    padding: 0 0.5rem;
  }

  .tab {
    padding: 0.7rem 0.85rem;
    font-size: 0.82rem;
  }

  .bilan-content {
    padding: 1.25rem 0.75rem 3rem;
  }

  .kpi-grid {
    grid-template-columns: 1fr;
  }

  .kpi-value {
    font-size: 1.6rem;
  }

  .tool-level-row {
    grid-template-columns: 1fr;
    gap: 0.3rem;
  }

  .glass-card {
    padding: 1rem;
    border-radius: 12px;
  }
}

@media (max-width: 480px) {
  .tab-icon {
    display: none;
  }

  .tab {
    padding: 0.65rem 0.6rem;
    font-size: 0.78rem;
  }
}
</style>
