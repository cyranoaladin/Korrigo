<script setup>
import { ref, computed, onMounted, nextTick } from 'vue'
import { useAuthStore } from '../stores/auth'
import { useRouter } from 'vue-router'
import gradingApi from '../services/gradingApi'
import api from '../services/api'

const authStore = useAuthStore()
const router = useRouter()

const statusLabels = {
  'STAGING': 'En attente',
  'READY': 'Prêt',
  'GRADED': 'Corrigé',
  'GRADING_IN_PROGRESS': 'Correction en cours',
  'GRADING_FAILED': 'Échec',
}
const getStatusLabel = (status) => statusLabels[status] || status

const copies = ref([])
const isLoading = ref(true)
const basicStats = ref({ total: 0, graded: 0, todo: 0 })
const examStats = ref(null)
const statsLoading = ref(false)
const showStats = ref(false)
const questionnaireSummary = ref({ has_response: false, summary: { is_available: false } })

const fetchCopies = async () => {
    isLoading.value = true
    try {
        const data = await gradingApi.listCopies()
        copies.value = data
        basicStats.value.total = data.length
        basicStats.value.graded = data.filter(c => c.status === 'GRADED').length
        basicStats.value.todo = data.filter(c => c.status === 'READY').length

        // Auto-fetch stats when at least 1 copy is graded
        if (basicStats.value.graded > 0) {
            showStats.value = true
            await fetchStats()
        }
    } catch (err) {
        console.error("Failed to fetch copies", err)
    } finally {
        isLoading.value = false
    }
}

const fetchQuestionnaireStatus = async () => {
    try {
        const res = await api.get('/grading/questionnaire/')
        questionnaireSummary.value = {
            has_response: !!res.data.has_response,
            summary: res.data.summary || { is_available: false }
        }
    } catch (err) {
        console.error("Failed to fetch questionnaire status", err)
    }
}

const fetchStats = async () => {
    if (!copies.value.length) return
    statsLoading.value = true
    try {
        // Get exam_id from first copy (exam is an object with .id or a direct UUID)
        const examRaw = copies.value[0]?.exam
        const examId = typeof examRaw === 'object' ? examRaw?.id : examRaw
        if (examId) {
            examStats.value = await gradingApi.fetchExamStats(examId)
        }
    } catch (err) {
        console.error("Failed to fetch stats", err)
    } finally {
        statsLoading.value = false
    }
}

// SVG chart dimensions
const chartW = 700
const chartH = 220
const padL = 35
const padR = 15
const padT = 20
const padB = 30
const plotW = chartW - padL - padR
const plotH = chartH - padT - padB

const mergedBins = computed(() => {
    const lot = examStats.value?.lot_distribution || []
    const global = examStats.value?.global_distribution || []
    const bins = []
    for (let n = 0; n <= 20; n++) {
        const lb = lot.find(b => b.start === n)
        const gb = global.find(b => b.start === n)
        bins.push({ note: n, lotCount: lb?.count || 0, globalCount: gb?.count || 0 })
    }
    return bins
})

const maxDistCount = computed(() => {
    if (!mergedBins.value.length) return 1
    return Math.max(...mergedBins.value.map(b => Math.max(b.lotCount, b.globalCount)), 1)
})

const yTicks = computed(() => {
    const m = maxDistCount.value
    if (m <= 5) return Array.from({ length: m + 1 }, (_, i) => i)
    const step = Math.ceil(m / 5)
    const ticks = []
    for (let v = 0; v <= m; v += step) ticks.push(v)
    if (ticks[ticks.length - 1] < m) ticks.push(m)
    return ticks
})

const toX = (note) => padL + (note / 20) * plotW
const toY = (count) => padT + plotH - (count / maxDistCount.value) * plotH

const buildPath = (series) => {
    const pts = mergedBins.value.map(b => ({ x: toX(b.note), y: toY(b[series]) }))
    if (!pts.length) return ''
    return 'M ' + pts.map(p => `${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(' L ')
}

const buildArea = (series) => {
    const pts = mergedBins.value.map(b => ({ x: toX(b.note), y: toY(b[series]) }))
    if (!pts.length) return ''
    const baseline = toY(0)
    return 'M ' + `${pts[0].x.toFixed(1)},${baseline.toFixed(1)} ` +
        pts.map(p => `L ${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(' ') +
        ` L ${pts[pts.length - 1].x.toFixed(1)},${baseline.toFixed(1)} Z`
}

const lotPath = computed(() => buildPath('lotCount'))
const globalPath = computed(() => buildPath('globalCount'))
const lotArea = computed(() => buildArea('lotCount'))
const globalArea = computed(() => buildArea('globalCount'))

const meanLineX = computed(() => {
    const m = examStats.value?.global_stats?.mean
    return m != null ? toX(m) : null
})
const medianLineX = computed(() => {
    const m = examStats.value?.global_stats?.median
    return m != null ? toX(m) : null
})

onMounted(async () => {
    await Promise.all([fetchCopies(), fetchQuestionnaireStatus()])
})

const handleLogout = async () => {
    await authStore.logout()
    router.push('/')
}

const handleChangePassword = async () => {
    const newPass = prompt("Nouveau mot de passe (min 6 caractères) :")
    if (!newPass) return
    if (newPass.length < 6) {
        alert("Le mot de passe doit faire au moins 6 caractères.")
        return
    }
    try {
        await api.post('/change-password/', { password: newPass })
        alert("Mot de passe mis à jour avec succès.")
    } catch (e) {
        alert("Erreur: " + (e.response?.data?.error || "Echec mise à jour"))
    }
}

const goToDesk = (copyId) => {
    router.push(`/corrector/desk/${copyId}`)
}

const toggleStats = async () => {
    showStats.value = !showStats.value
    if (showStats.value && !examStats.value) {
        await fetchStats()
    }
}

const scrollToStats = async () => {
    showStats.value = true
    if (!examStats.value) {
        await fetchStats()
    }
    nextTick(() => {
        const el = document.getElementById('stats-section')
        if (el) el.scrollIntoView({ behavior: 'smooth' })
    })
}

const goToMyStudents = () => {
    router.push('/corrector/my-students')
}

const goToQuestionnaire = () => {
    router.push('/corrector/questionnaire')
}

const goToQuestionnaireBilan = () => {
    router.push({ name: 'QuestionnaireBilan' })
}
</script>

<template>
  <div
    class="corrector-dashboard"
    data-testid="corrector-dashboard"
  >
    <header class="top-nav">
      <div class="brand">
        Korrigo — Correcteur
      </div>
      <div class="user-menu">
        <span>{{ authStore.user?.username }}</span>
        <button
          class="btn-text"
          @click="handleChangePassword"
        >
          Modifier mot de passe
        </button>
        <button
          v-if="basicStats.graded > 0"
          class="btn-nav-stats"
          @click="scrollToStats"
        >
          📊 Statistiques
        </button>
        <button
          class="btn-my-students"
          @click="goToMyStudents"
        >
          👥 Mes Élèves
        </button>
        <button
          v-if="!questionnaireSummary.has_response"
          class="btn-questionnaire"
          @click="goToQuestionnaire"
        >
          📝 Questionnaire
        </button>
        <button
          v-if="questionnaireSummary.summary?.is_available"
          class="btn-questionnaire-bilan"
          @click="goToQuestionnaireBilan"
        >
          📈 Bilan Questionnaire
        </button>
        <a
          href="https://korrigo.labomaths.tn/korrigo/stats-bb-maths-2026"
          target="_blank"
          class="btn-jury-report"
        >
          📋 Rapport du jury
        </a>
        <button
          class="btn-logout"
          @click="handleLogout"
        >
          Déconnexion
        </button>
      </div>
    </header>

    <main class="container">
      <div class="stats-overview">
        <div class="card stat">
          <h3>Copies Attribuées</h3>
          <div class="value">
            {{ basicStats.total }}
          </div>
        </div>
        <div class="card stat">
          <h3>Corrigées</h3>
          <div class="value success">
            {{ basicStats.graded }}
          </div>
        </div>
        <div class="card stat">
          <h3>Reste à faire</h3>
          <div class="value warning">
            {{ basicStats.todo }}
          </div>
        </div>
      </div>

      <!-- Stats Toggle -->
      <div
        v-if="basicStats.graded > 0"
        class="stats-toggle"
      >
        <button
          class="btn-stats"
          @click="toggleStats"
        >
          {{ showStats ? 'Masquer les statistiques' : 'Voir les statistiques' }}
        </button>
      </div>

      <!-- Charts Section -->
      <div
        v-if="showStats"
        id="stats-section"
        class="charts-section"
      >
        <div
          v-if="statsLoading"
          class="loading"
        >
          Chargement des statistiques...
        </div>

        <template v-else-if="examStats">
          <!-- Comparative Stats -->
          <div class="comparative-stats">
            <h3>Indicateurs Comparatifs</h3>
            <div
              v-if="!examStats.all_graded"
              class="partial-warning"
            >
              Statistiques globales partielles ({{ examStats.graded_copies }}/{{ examStats.total_copies }} copies corrigées)
            </div>
            <table class="stats-table">
              <thead>
                <tr>
                  <th>Indicateur</th>
                  <th>Mon Lot</th>
                  <th>Global</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td>Moyenne</td>
                  <td>{{ examStats.lot_stats?.mean ?? '-' }}</td>
                  <td>{{ examStats.global_stats?.mean ?? '-' }}</td>
                </tr>
                <tr>
                  <td>Médiane</td>
                  <td>{{ examStats.lot_stats?.median ?? '-' }}</td>
                  <td>{{ examStats.global_stats?.median ?? '-' }}</td>
                </tr>
                <tr>
                  <td>Écart-type</td>
                  <td>{{ examStats.lot_stats?.std_dev ?? '-' }}</td>
                  <td>{{ examStats.global_stats?.std_dev ?? '-' }}</td>
                </tr>
                <tr>
                  <td>Minimum</td>
                  <td>{{ examStats.lot_stats?.min ?? '-' }}</td>
                  <td>{{ examStats.global_stats?.min ?? '-' }}</td>
                </tr>
                <tr>
                  <td>Maximum</td>
                  <td>{{ examStats.lot_stats?.max ?? '-' }}</td>
                  <td>{{ examStats.global_stats?.max ?? '-' }}</td>
                </tr>
                <tr>
                  <td>Nombre de copies</td>
                  <td>{{ examStats.lot_stats?.count ?? '-' }}</td>
                  <td>{{ examStats.global_stats?.count ?? '-' }}</td>
                </tr>
              </tbody>
            </table>
          </div>

          <!-- Combined Distribution Chart (SVG Line) -->
          <div
            v-if="mergedBins.length"
            class="chart-container"
          >
            <div class="chart-header">
              <h3>
                Répartition des Notes (0–20){{ !examStats.all_graded ? ' — partiel' : '' }}
              </h3>
              <div class="chart-legend">
                <span class="legend-item"><span class="legend-dot lot-dot" /> Mon Lot</span>
                <span class="legend-item"><span class="legend-dot global-dot" /> Global</span>
                <span class="legend-item"><span class="legend-line mean-line" /> Moyenne</span>
                <span class="legend-item"><span class="legend-line median-line" /> Médiane</span>
              </div>
            </div>
            <svg :viewBox="`0 0 ${chartW} ${chartH}`" class="svg-chart" preserveAspectRatio="xMidYMid meet">
              <!-- Grid lines -->
              <line v-for="t in yTicks" :key="'gy'+t"
                :x1="padL" :x2="chartW - padR" :y1="toY(t)" :y2="toY(t)"
                stroke="#e2e8f0" stroke-width="0.5" />
              <line v-for="n in 21" :key="'gx'+n"
                :x1="toX(n-1)" :x2="toX(n-1)" :y1="padT" :y2="padT + plotH"
                stroke="#f1f5f9" stroke-width="0.5" />

              <!-- Area fills -->
              <path :d="globalArea" fill="#10b98120" />
              <path :d="lotArea" fill="#6366f120" />

              <!-- Curves -->
              <path :d="globalPath" fill="none" stroke="#10b981" stroke-width="2.5" stroke-linejoin="round" />
              <path :d="lotPath" fill="none" stroke="#6366f1" stroke-width="2.5" stroke-linejoin="round" />

              <!-- Data points -->
              <template v-for="b in mergedBins" :key="'dp'+b.note">
                <circle v-if="b.globalCount > 0" :cx="toX(b.note)" :cy="toY(b.globalCount)" r="3" fill="#10b981" />
                <circle v-if="b.lotCount > 0" :cx="toX(b.note)" :cy="toY(b.lotCount)" r="3" fill="#6366f1" />
              </template>

              <!-- Mean vertical line -->
              <line v-if="meanLineX != null"
                :x1="meanLineX" :x2="meanLineX" :y1="padT" :y2="padT + plotH"
                stroke="#ef4444" stroke-width="1.5" stroke-dasharray="6,3" opacity="0.7" />
              <text v-if="meanLineX != null"
                :x="meanLineX" :y="padT - 4" text-anchor="middle"
                fill="#ef4444" font-size="9" font-weight="600">
                μ={{ examStats.global_stats?.mean }}
              </text>

              <!-- Median vertical line -->
              <line v-if="medianLineX != null"
                :x1="medianLineX" :x2="medianLineX" :y1="padT" :y2="padT + plotH"
                stroke="#f59e0b" stroke-width="1.5" stroke-dasharray="3,3" opacity="0.7" />
              <text v-if="medianLineX != null"
                :x="medianLineX" :y="padT + plotH + 26" text-anchor="middle"
                fill="#f59e0b" font-size="9" font-weight="600">
                Méd={{ examStats.global_stats?.median }}
              </text>

              <!-- X axis labels -->
              <text v-for="n in 21" :key="'xl'+n"
                :x="toX(n-1)" :y="padT + plotH + 14"
                text-anchor="middle" fill="#64748b" font-size="9">
                {{ n - 1 }}
              </text>

              <!-- Y axis labels -->
              <text v-for="t in yTicks" :key="'yl'+t"
                :x="padL - 6" :y="toY(t) + 3"
                text-anchor="end" fill="#94a3b8" font-size="9">
                {{ t }}
              </text>

              <!-- Axes -->
              <line :x1="padL" :x2="chartW - padR" :y1="padT + plotH" :y2="padT + plotH" stroke="#cbd5e1" stroke-width="1" />
              <line :x1="padL" :x2="padL" :y1="padT" :y2="padT + plotH" stroke="#cbd5e1" stroke-width="1" />
            </svg>
          </div>

          <!-- Group Stats Table -->
          <div
            v-if="examStats.group_stats && examStats.group_stats.length"
            class="group-stats-section"
          >
            <h3>Statistiques par Groupe</h3>
            <div class="group-table-wrapper">
              <table class="group-stats-table">
                <thead>
                  <tr>
                    <th>Groupe</th>
                    <th>Copies</th>
                    <th>Moyenne</th>
                    <th>Médiane</th>
                    <th>Écart-type</th>
                    <th>Min</th>
                    <th>Max</th>
                    <th>≥ Moy. globale</th>
                    <th>&lt; Moy. globale</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="g in examStats.group_stats" :key="g.groupe">
                    <td class="group-name">{{ g.groupe }}</td>
                    <td>{{ g.count }}</td>
                    <td :class="{ 'above-global': g.mean >= examStats.global_stats?.mean, 'below-global': g.mean < examStats.global_stats?.mean }">
                      <strong>{{ g.mean ?? '-' }}</strong>
                    </td>
                    <td>{{ g.median ?? '-' }}</td>
                    <td>{{ g.std_dev ?? '-' }}</td>
                    <td>{{ g.min ?? '-' }}</td>
                    <td>{{ g.max ?? '-' }}</td>
                    <td class="count-above">{{ g.above_mean }}</td>
                    <td class="count-below">{{ g.below_mean }}</td>
                  </tr>
                </tbody>
                <tfoot>
                  <tr class="global-row">
                    <td class="group-name"><strong>Global</strong></td>
                    <td><strong>{{ examStats.global_stats?.count ?? '-' }}</strong></td>
                    <td><strong>{{ examStats.global_stats?.mean ?? '-' }}</strong></td>
                    <td><strong>{{ examStats.global_stats?.median ?? '-' }}</strong></td>
                    <td><strong>{{ examStats.global_stats?.std_dev ?? '-' }}</strong></td>
                    <td><strong>{{ examStats.global_stats?.min ?? '-' }}</strong></td>
                    <td><strong>{{ examStats.global_stats?.max ?? '-' }}</strong></td>
                    <td colspan="2" />
                  </tr>
                </tfoot>
              </table>
            </div>
          </div>
        </template>
      </div>

      <div class="task-list">
        <h2>Vos Copies à Corriger</h2>
        <div
          v-if="isLoading"
          class="loading"
        >
          Chargement...
        </div>
        <template v-else>
          <div
            v-for="copy in copies"
            :key="copy.id"
            class="copy-card"
            data-testid="copy-card"
            :data-copy-anon="copy.anonymous_id"
          >
            <div class="copy-info">
              <div class="exam-name">
                {{ copy.exam_name || 'Examen' }}
              </div>
              <div class="copy-id">
                Anonymat: {{ copy.anonymous_id }}
              </div>
            </div>
            <div :class="['copy-status', copy.status.toLowerCase()]">
              {{ getStatusLabel(copy.status) }}
            </div>
            <button
              class="btn-action"
              data-testid="copy-action"
              @click="goToDesk(copy.id)"
            >
              {{ copy.status === 'GRADED' ? 'Voir' : 'Corriger' }}
            </button>
          </div>
          <div
            v-if="copies.length === 0"
            class="empty-state"
          >
            Aucune copie disponible pour le moment.
          </div>
        </template>
      </div>
    </main>
  </div>
</template>

<style scoped>
.corrector-dashboard { background: #f8fafc; min-height: 100vh; font-family: 'Inter', sans-serif; }
.top-nav { background: white; padding: 1rem 2rem; display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #e2e8f0; }
.brand { font-weight: 700; color: #0f172a; font-size: 1.1rem; }
.user-menu { display: flex; gap: 1rem; align-items: center; font-size: 0.9rem; }
.btn-text { background: none; border: none; color: #64748b; cursor: pointer; text-decoration: underline; font-size: 0.85rem; }
.btn-nav-stats { background: #6366f1; color: white; border: none; cursor: pointer; font-weight: 500; padding: 4px 10px; border-radius: 4px; font-size: 0.85rem; }
.btn-nav-stats:hover { background: #4f46e5; }
.btn-my-students { background: #10b981; color: white; border: none; cursor: pointer; font-weight: 500; padding: 4px 10px; border-radius: 4px; font-size: 0.85rem; }
.btn-my-students:hover { background: #059669; }
.btn-questionnaire { background: #b45309; color: white; border: none; cursor: pointer; font-weight: 500; padding: 4px 10px; border-radius: 4px; font-size: 0.85rem; }
.btn-questionnaire:hover { background: #92400e; }
.btn-questionnaire-bilan { background: #7c3aed; color: white; border: none; cursor: pointer; font-weight: 500; padding: 4px 10px; border-radius: 4px; font-size: 0.85rem; }
.btn-questionnaire-bilan:hover { background: #6d28d9; }
.btn-jury-report { display: inline-block; background: #f59e0b; color: white; border: none; cursor: pointer; font-weight: 500; padding: 4px 10px; border-radius: 4px; font-size: 0.85rem; text-decoration: none; }
.btn-jury-report:hover { background: #d97706; }
.btn-logout { border: 1px solid #ef4444; background: white; color: #ef4444; cursor: pointer; font-weight: 500; padding: 4px 8px; border-radius: 4px; }
.btn-logout:hover { background: #ef4444; color: white; }

.container { max-width: 900px; margin: 2rem auto; padding: 0 1rem; }

.stats-overview { display: grid; grid-template-columns: repeat(3, 1fr); gap: 1rem; margin-bottom: 2rem; }
.card { background: white; padding: 1.5rem; border-radius: 8px; box-shadow: 0 1px 2px rgba(0,0,0,0.05); text-align: center; }
.stat h3 { margin: 0 0 0.5rem 0; font-size: 0.875rem; color: #64748b; font-weight: 500; }
.stat .value { font-size: 2rem; font-weight: 700; color: #0f172a; }
.value.success { color: #10b981; }
.value.warning { color: #f59e0b; }

.stats-toggle { text-align: center; margin-bottom: 1.5rem; }
.btn-stats { padding: 0.5rem 1.5rem; background: #6366f1; color: white; border: none; border-radius: 6px; cursor: pointer; font-weight: 500; font-size: 0.9rem; }
.btn-stats:hover { background: #4f46e5; }

.charts-section { margin-bottom: 2rem; }
.comparative-stats { background: white; padding: 1.5rem; border-radius: 8px; margin-bottom: 1rem; box-shadow: 0 1px 2px rgba(0,0,0,0.05); }
.comparative-stats h3 { margin: 0 0 1rem 0; font-size: 1rem; color: #1e293b; }
.partial-warning { background: #fef3c7; color: #92400e; padding: 0.5rem 1rem; border-radius: 4px; margin-bottom: 1rem; font-size: 0.85rem; }
.stats-table { width: 100%; border-collapse: collapse; }
.stats-table th, .stats-table td { padding: 0.5rem 1rem; text-align: center; border-bottom: 1px solid #e2e8f0; }
.stats-table th { background: #f8fafc; font-weight: 600; font-size: 0.85rem; color: #64748b; }
.stats-table td:first-child { text-align: left; font-weight: 500; }

.chart-container { background: white; padding: 1.5rem; border-radius: 8px; margin-bottom: 1rem; box-shadow: 0 1px 2px rgba(0,0,0,0.05); }
.chart-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem; flex-wrap: wrap; gap: 0.5rem; }
.chart-header h3 { margin: 0; font-size: 1rem; color: #1e293b; }
.chart-legend { display: flex; gap: 1rem; align-items: center; flex-wrap: wrap; }
.legend-item { display: flex; align-items: center; gap: 4px; font-size: 0.8rem; color: #475569; font-weight: 500; }
.legend-dot { width: 12px; height: 12px; border-radius: 3px; }
.lot-dot { background: #6366f1; }
.global-dot { background: #10b981; }
.legend-line { width: 18px; height: 0; border-top: 2px dashed; }
.mean-line { border-color: #ef4444; }
.median-line { border-color: #f59e0b; }
.svg-chart { width: 100%; height: auto; max-height: 260px; }

.group-stats-section { background: white; padding: 1.5rem; border-radius: 8px; margin-bottom: 1rem; box-shadow: 0 1px 2px rgba(0,0,0,0.05); }
.group-stats-section h3 { margin: 0 0 1rem 0; font-size: 1rem; color: #1e293b; }
.group-table-wrapper { overflow-x: auto; }
.group-stats-table { width: 100%; border-collapse: collapse; font-size: 0.85rem; }
.group-stats-table th, .group-stats-table td { padding: 0.5rem 0.6rem; text-align: center; border-bottom: 1px solid #e2e8f0; }
.group-stats-table th { background: #f8fafc; font-weight: 600; color: #64748b; font-size: 0.8rem; white-space: nowrap; }
.group-stats-table .group-name { text-align: left; font-weight: 600; color: #334155; }
.group-stats-table .above-global { color: #059669; }
.group-stats-table .below-global { color: #dc2626; }
.group-stats-table .count-above { color: #059669; font-weight: 600; }
.group-stats-table .count-below { color: #dc2626; font-weight: 600; }
.group-stats-table tfoot .global-row { background: #f1f5f9; }
.group-stats-table tfoot .global-row td { border-top: 2px solid #cbd5e1; font-size: 0.85rem; }

.task-list h2 { font-size: 1.25rem; color: #1e293b; margin-bottom: 1rem; }
.copy-card { background: white; padding: 1rem; border-radius: 8px; margin-bottom: 1rem; display: flex; justify-content: space-between; align-items: center; box-shadow: 0 1px 2px rgba(0,0,0,0.05); border: 1px solid #e2e8f0; }
.exam-name { font-weight: 600; color: #334155; }
.copy-id { font-size: 0.875rem; color: #64748b; }
.copy-status { font-size: 0.75rem; font-weight: 600; text-transform: uppercase; padding: 2px 6px; border-radius: 4px; }
.copy-status.ready { background: #dbeafe; color: #1d4ed8; }
.copy-status.locked { background: #fef3c7; color: #92400e; }
.copy-status.graded { background: #dcfce7; color: #166534; }
.copy-status.staging { background: #f1f5f9; color: #64748b; }

.btn-action { padding: 0.5rem 1rem; background: #2563eb; color: white; border: none; border-radius: 6px; cursor: pointer; font-weight: 500; }
.btn-action:hover { background: #1d4ed8; }

.loading { text-align: center; padding: 2rem; color: #64748b; }
.empty-state { text-align: center; padding: 2rem; color: #94a3b8; }
</style>
