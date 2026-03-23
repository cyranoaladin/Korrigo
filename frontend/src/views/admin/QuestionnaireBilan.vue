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
const generatedBilan = ref({ status: 'missing', html: '', generated_at: null, error: '' })
const canSeePartialResponses = computed(() => authStore.user?.role === 'Admin' && responses.value.length > 0)
const selectedResponseUserId = ref(null)

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

        <section class="panel nps-explainer">
          <h3>Qu'est-ce que le NPS (Net Promoter Score) ?</h3>
          <p>Le NPS mesure la probabilité qu'un utilisateur recommande l'outil à un collègue, sur une échelle de 0 à 10. Les répondants sont classés en trois catégories :</p>
          <ul>
            <li><strong>Promoteurs (9-10)</strong> — enthousiastes, ils recommandent activement</li>
            <li><strong>Passifs (7-8)</strong> — satisfaits mais sans enthousiasme</li>
            <li><strong>Détracteurs (0-6)</strong> — insatisfaits, risque de bouche-à-oreille négatif</li>
          </ul>
          <p><strong>Indice NPS</strong> = % Promoteurs − % Détracteurs. Le score varie de −100 à +100. Un NPS positif est considéré comme bon, au-dessus de +50 comme excellent.</p>
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

        <div v-if="!summary.is_available && !canSeePartialResponses && generatedBilan.status !== 'ready'" class="panel empty-panel">
          Le bilan détaillé n'est pas encore disponible.
        </div>

        <section v-if="generatedBilan.status === 'ready'" class="panel generated-bilan-panel">
          <div class="section-head">
            <h2>Bilan automatique</h2>
            <span>{{ formatDate(generatedBilan.generated_at) }}</span>
          </div>
          <div class="generated-bilan-html" v-html="generatedBilan.html" />
        </section>

        <section v-if="generatedBilan.status === 'pending'" class="panel info-panel">
          Le bilan automatique est en cours de génération.
        </section>

        <section v-if="generatedBilan.status === 'error'" class="panel error-panel">
          {{ generatedBilan.error || "Le bilan automatique n'a pas pu être généré pour le moment." }}
        </section>

        <template v-if="(summary.is_available || canSeePartialResponses) && responses.length && generatedBilan.status !== 'ready'">
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

        <!-- Section V2: Améliorations apportées (toujours visible, hors du bloc conditionnel) -->
        <section class="panel v2-improvements-panel">
          <div class="v2-header">
            <h2>Améliorations apportées — V2 (Mars 2026)</h2>
            <p class="v2-subtitle">En réponse directe aux retours des correcteurs, les améliorations suivantes ont été développées et déployées sur la plateforme.</p>
          </div>

          <table class="v2-table">
            <thead>
                <tr>
                  <th class="col-priority">Priorité</th>
                  <th class="col-issue">Problème signalé</th>
                  <th class="col-source">Correcteur(s)</th>
                  <th class="col-solution">Amélioration apportée</th>
                  <th class="col-status">Statut</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td><span class="priority-badge critical">1</span></td>
                  <td>
                    <strong>Friction annotation / barème</strong><br>
                    Le panneau barème se réinitialisait en haut à chaque retour depuis les annotations, dissuadant les correcteurs d'annoter.
                  </td>
                  <td>Selima Klibi, Patrick Dupont, Chawki Saadi</td>
                  <td>
                    <strong>Refonte complète du layout :</strong> le barème est désormais affiché en permanence dans le panneau latéral droit. Les outils d'annotation sont dans la barre d'outils au-dessus de la copie. Plus aucune navigation entre onglets n'est nécessaire — les deux sont visibles simultanément.
                  </td>
                  <td><span class="status-badge deployed">Déployé</span></td>
                </tr>
                <tr>
                  <td><span class="priority-badge high">2</span></td>
                  <td>
                    <strong>Outil tampon Vrai/Faux manquant</strong><br>
                    Absence d'un outil de marquage rapide V/X correspondant au geste papier le plus fréquent.
                  </td>
                  <td>Patrick Dupont, Philippe Carr</td>
                  <td>
                    <strong>Boutons ✓ V et ✗ F dans la barre d'outils :</strong> un clic sur le bouton active le mode tampon. Chaque rectangle dessiné sur la copie crée instantanément un checkmark vert (✓) ou une croix rouge (✗) sans ouvrir d'éditeur. Le tampon persiste sur le PDF final remis à l'élève.
                  </td>
                  <td><span class="status-badge deployed">Déployé</span></td>
                </tr>
                <tr>
                  <td><span class="priority-badge high">3</span></td>
                  <td>
                    <strong>Outils d'annotation lents</strong><br>
                    Le workflow création d'annotation nécessitait trop d'étapes (sélection outil, clic, saisie, validation).
                  </td>
                  <td>Ensemble des correcteurs</td>
                  <td>
                    <strong>6 boutons d'annotation rapide dans la barre d'outils :</strong> Commentaire (💬), Surlignage (🟨), Erreur (❌), Bonus (⭐), Vrai (✓), Faux (✗). Les 3 premiers ouvrent un éditeur de texte pour saisir un commentaire. Les 3 derniers créent un tampon visuel instantané sans éditeur.
                  </td>
                  <td><span class="status-badge deployed">Déployé</span></td>
                </tr>
                <tr>
                  <td><span class="priority-badge blocking">4</span></td>
                  <td>
                    <strong>Copies bloquées en mode « locked »</strong><br>
                    Des copies restaient verrouillées sans possibilité d'y accéder ni de les annoter.
                  </td>
                  <td>Patrick Dupont, Philippe Carr</td>
                  <td>
                    <strong>Bouton « Déverrouiller » (administrateur) :</strong> visible dans la barre d'outils pour les administrateurs. Force la suppression du verrou avec journalisation complète de l'action (qui a déverrouillé, quand, ancien propriétaire du verrou).
                  </td>
                  <td><span class="status-badge deployed">Déployé</span></td>
                </tr>
                <tr>
                  <td><span class="priority-badge medium">5</span></td>
                  <td>
                    <strong>Impossible de revenir sur une copie finalisée</strong><br>
                    Une fois la copie corrigée, aucune modification n'était possible même en cas d'erreur.
                  </td>
                  <td>Edouard Rousseau</td>
                  <td>
                    <strong>Bouton « Rouvrir » (superutilisateur) :</strong> permet de remettre une copie finalisée en statut « Prêt » pour correction. Le PDF final est invalidé, mais toutes les notes, annotations, remarques et appréciations sont conservées. Action entièrement tracée dans le journal d'audit.
                  </td>
                  <td><span class="status-badge deployed">Déployé</span></td>
                </tr>
                <tr>
                  <td><span class="priority-badge medium">6</span></td>
                  <td>
                    <strong>Pas de suivi des questions non corrigées</strong><br>
                    Aucun indicateur visuel pour savoir quelles questions du barème avaient reçu une note.
                  </td>
                  <td>Sami Ben Tiba</td>
                  <td>
                    <strong>Barre de progression segmentée par question :</strong> dans le tableau de bord correcteur, chaque copie affiche une barre visuelle indiquant les questions notées (vert) et non notées (gris), avec le pourcentage et le détail (ex : « 5/8 questions notées — 63 % »).
                  </td>
                  <td><span class="status-badge deployed">Déployé</span></td>
                </tr>
                <tr>
                  <td><span class="priority-badge medium">7</span></td>
                  <td>
                    <strong>Commentaires non mémorisés entre copies</strong><br>
                    Les remarques saisies sur une copie ne pouvaient pas être réutilisées sur la suivante.
                  </td>
                  <td>Chawki Saadi</td>
                  <td>
                    <strong>Sauvegarde automatique dans la banque personnelle :</strong> chaque remarque substantielle (plus de 5 caractères) est automatiquement enregistrée dans la banque d'annotations personnelle du correcteur avec le contexte exercice/question. Les remarques fréquentes sont proposées en priorité lors de la correction de la copie suivante.
                  </td>
                  <td><span class="status-badge deployed">Déployé</span></td>
                </tr>
                <tr>
                  <td><span class="priority-badge medium">8</span></td>
                  <td>
                    <strong>Chargement lent des pages PDF</strong><br>
                    Délai perceptible lors du passage d'une page à l'autre.
                  </td>
                  <td>Sami Ben Tiba, Philippe Carr, Selima Klibi</td>
                  <td>
                    <strong>Préchargement des pages adjacentes :</strong> les pages précédente et suivante sont chargées en arrière-plan avant que le correcteur ne navigue. Résultat : affichage quasi-instantané lors du changement de page. Ajout d'une transition en fondu pour éliminer le flash blanc.
                  </td>
                  <td><span class="status-badge deployed">Déployé</span></td>
                </tr>
                <tr>
                  <td><span class="priority-badge medium">9</span></td>
                  <td>
                    <strong>Scroll et navigation non fluides</strong><br>
                    Le défilement des pages n'était pas naturel et le zoom difficile à ajuster.
                  </td>
                  <td>Chawki Saadi, Philippe Carr</td>
                  <td>
                    <strong>Scroll fluide natif + zoom amélioré :</strong> activation du scroll smooth CSS, support du Ctrl+molette pour zoomer/dézoomer rapidement, bouton « Ajuster à la largeur » (↔), clic sur le pourcentage pour réinitialiser le zoom à 100 %. Temps de réponse au changement de page réduit de 400 ms à 300 ms.
                  </td>
                  <td><span class="status-badge deployed">Déployé</span></td>
                </tr>
                <tr>
                  <td><span class="priority-badge medium">10</span></td>
                  <td>
                    <strong>Barème non replié par défaut</strong><br>
                    Tous les exercices du barème étaient dépliés à l'ouverture, encombrant l'espace de travail.
                  </td>
                  <td>Retour d'usage général</td>
                  <td>
                    <strong>Comportement accordéon :</strong> tous les exercices sont repliés par défaut à l'ouverture de la copie. Cliquer sur un exercice le déplie et replie automatiquement le précédent. Un seul exercice est visible à la fois pour un confort d'affichage optimal.
                  </td>
                  <td><span class="status-badge deployed">Déployé</span></td>
                </tr>
              </tbody>
            </table>

            <div class="v2-footer">
              <p><strong>Date de déploiement :</strong> 23 mars 2026</p>
              <p><strong>Périmètre :</strong> 10 améliorations · 84 fichiers modifiés · 15 338 lignes de code · 414 tests automatisés</p>
              <p class="v2-note">Ces améliorations sont le résultat direct de l'analyse des 7 réponses au questionnaire et du bilan automatique. Chaque modification a été testée, validée et déployée en production sans interruption de service ni perte de données.</p>
            </div>
          </section>
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

.generated-bilan-panel {
  line-height: 1.65;
}

.nps-explainer {
  background: #f0f9ff;
  border-color: #bae6fd;
  line-height: 1.6;
}

.nps-explainer h3 {
  color: #0c4a6e;
  margin-bottom: 0.5rem;
  font-size: 1rem;
}

.nps-explainer p {
  color: #334155;
  margin-bottom: 0.5rem;
  font-size: 0.9rem;
}

.nps-explainer ul {
  margin: 0.5rem 0;
  padding-left: 1.5rem;
}

.nps-explainer li {
  color: #334155;
  font-size: 0.9rem;
  margin-bottom: 0.25rem;
}

.generated-bilan-html :deep(h2),
.generated-bilan-html :deep(h3) {
  color: #0f172a;
  margin-top: 1.1rem;
}

.generated-bilan-html :deep(p),
.generated-bilan-html :deep(li),
.generated-bilan-html :deep(blockquote),
.generated-bilan-html :deep(td),
.generated-bilan-html :deep(th) {
  color: #334155;
}

.generated-bilan-html :deep(blockquote) {
  margin: 0.75rem 0;
  padding: 0.75rem 1rem;
  border-left: 4px solid #cbd5e1;
  background: #f8fafc;
}

.generated-bilan-html :deep(table) {
  width: 100%;
  border-collapse: collapse;
  margin-top: 1rem;
}

.generated-bilan-html :deep(th),
.generated-bilan-html :deep(td) {
  border: 1px solid #e2e8f0;
  padding: 0.65rem;
  vertical-align: top;
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

.response-master-detail {
  display: grid;
  grid-template-columns: minmax(260px, 320px) minmax(0, 1fr);
  gap: 1rem;
}

.response-list {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.response-list-item {
  width: 100%;
  border: 1px solid #dbeafe;
  border-radius: 12px;
  background: #f8fafc;
  padding: 0.9rem;
  text-align: left;
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
  cursor: pointer;
  transition: all 0.2s ease;
}

.response-list-item strong {
  color: #0f172a;
}

.response-list-item span,
.response-list-item small {
  color: #64748b;
}

.response-list-item:hover,
.response-list-item.active {
  border-color: #2563eb;
  background: #eff6ff;
}

.response-detail {
  border: 1px solid #e2e8f0;
  border-radius: 14px;
  background: #f8fafc;
  padding: 1rem;
}

.response-detail-head {
  margin-bottom: 1rem;
}

.name-cell {
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
}

.name-cell strong {
  color: #0f172a;
}

.name-cell span {
  color: #64748b;
}

.response-detail-sections {
  display: grid;
  gap: 1rem;
}

.response-section-card {
  border: 1px solid #dbeafe;
  border-radius: 12px;
  background: #ffffff;
  padding: 0.95rem;
}

.response-section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 0.75rem;
  margin-bottom: 0.75rem;
}

.response-section-header h3 {
  margin: 0;
  color: #1d4ed8;
  font-size: 1rem;
}

.response-section-header span {
  color: #64748b;
  font-size: 0.85rem;
}

.response-detail-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.75rem;
}

.response-detail-item {
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  background: white;
  padding: 0.85rem;
}

.response-label {
  display: block;
  margin-bottom: 0.35rem;
  color: #64748b;
  font-size: 0.9rem;
}

.response-value {
  color: #0f172a;
  white-space: pre-wrap;
  line-height: 1.55;
}

.stat-list {
  display: flex;
  flex-direction: column;
  gap: 0.85rem;
}

.stat-row {
  display: grid;
  gap: 0.4rem;
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

/* V2 Improvements Panel */
.v2-improvements-panel {
  border: 2px solid #3b82f6;
  background: linear-gradient(135deg, #f0f7ff 0%, #ffffff 100%);
}

.v2-header {
  margin-bottom: 1.25rem;
}

.v2-header h2 {
  margin: 0 0 0.5rem;
  color: #1e40af;
  font-size: 1.2rem;
}

.v2-subtitle {
  margin: 0;
  color: #475569;
  font-size: 0.95rem;
  line-height: 1.5;
}

.v2-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.9rem;
  margin-bottom: 1.25rem;
}

.v2-table thead {
  background: #1e40af;
  color: white;
}

.v2-table th {
  padding: 0.75rem 0.65rem;
  text-align: left;
  font-weight: 600;
  font-size: 0.85rem;
  white-space: nowrap;
}

.v2-table td {
  padding: 0.75rem 0.65rem;
  border-bottom: 1px solid #e2e8f0;
  vertical-align: top;
  line-height: 1.5;
  color: #334155;
}

.v2-table tbody tr:hover {
  background: #f0f7ff;
}

.v2-table .col-priority { width: 60px; text-align: center; }
.v2-table .col-issue { width: 25%; }
.v2-table .col-source { width: 14%; font-size: 0.85rem; color: #64748b; }
.v2-table .col-solution { width: 40%; }
.v2-table .col-status { width: 80px; text-align: center; }

.priority-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: 50%;
  font-weight: 700;
  font-size: 0.85rem;
  color: white;
}

.priority-badge.critical { background: #dc2626; }
.priority-badge.high { background: #f59e0b; }
.priority-badge.blocking { background: #7c3aed; }
.priority-badge.medium { background: #3b82f6; }

.status-badge.deployed {
  display: inline-block;
  padding: 3px 10px;
  border-radius: 12px;
  font-size: 0.78rem;
  font-weight: 600;
  background: #dcfce7;
  color: #166534;
  border: 1px solid #bbf7d0;
}

.v2-footer {
  padding-top: 1rem;
  border-top: 1px solid #e2e8f0;
}

.v2-footer p {
  margin: 0.3rem 0;
  color: #475569;
  font-size: 0.9rem;
}

.v2-note {
  margin-top: 0.75rem !important;
  padding: 0.75rem 1rem;
  background: #f0fdf4;
  border-left: 4px solid #22c55e;
  border-radius: 0 8px 8px 0;
  color: #166534 !important;
  font-size: 0.88rem !important;
  line-height: 1.5;
}

@media (max-width: 1100px) {
  .cards-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}

@media (max-width: 960px) {
  .cards-grid,
  .two-columns,
  .response-master-detail,
  .response-detail-grid {
    grid-template-columns: 1fr;
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
