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
  'LOCKED': 'En cours',
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

const fetchCopies = async () => {
    isLoading.value = true
    try {
        const data = await gradingApi.listCopies()
        copies.value = data
        basicStats.value.total = data.length
        basicStats.value.graded = data.filter(c => c.status === 'GRADED').length
        basicStats.value.todo = data.filter(c => ['READY', 'LOCKED'].includes(c.status)).length

        // If all copies graded, auto-fetch stats
        if (basicStats.value.graded === basicStats.value.total && basicStats.value.total > 0) {
            showStats.value = true
            await fetchStats()
        }
    } catch (err) {
        console.error("Failed to fetch copies", err)
    } finally {
        isLoading.value = false
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

// Merge lot + global distributions into aligned bins for the combined chart
const mergedBins = computed(() => {
    const lot = examStats.value?.lot_distribution || []
    const global = examStats.value?.global_distribution || []
    const rangeMap = new Map()
    for (const b of global) {
        rangeMap.set(b.range, { range: b.range, start: b.start, lotCount: 0, globalCount: b.count })
    }
    for (const b of lot) {
        if (rangeMap.has(b.range)) {
            rangeMap.get(b.range).lotCount = b.count
        } else {
            rangeMap.set(b.range, { range: b.range, start: b.start, lotCount: b.count, globalCount: 0 })
        }
    }
    return [...rangeMap.values()].sort((a, b) => a.start - b.start)
})

// Compute max bar height for chart (across both series)
const maxDistCount = computed(() => {
    if (!mergedBins.value.length) return 1
    return Math.max(...mergedBins.value.map(b => Math.max(b.lotCount, b.globalCount)), 1)
})

onMounted(fetchCopies)

const handleLogout = async () => {
    await authStore.logout()
    router.push('/login')
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

          <!-- Combined Distribution Chart -->
          <div
            v-if="mergedBins.length"
            class="chart-container"
          >
            <div class="chart-header">
              <h3>
                Répartition des Notes{{ !examStats.all_graded ? ' (global partiel)' : '' }}
              </h3>
              <div class="chart-legend">
                <span class="legend-item">
                  <span class="legend-dot lot-dot" />
                  Mon Lot
                </span>
                <span class="legend-item">
                  <span class="legend-dot global-dot" />
                  Global
                </span>
              </div>
            </div>
            <div class="bar-chart">
              <div
                v-for="bin in mergedBins"
                :key="bin.range"
                class="bar-group"
              >
                <div class="bar-pair">
                  <div
                    class="bar lot-bar"
                    :style="{ height: (bin.lotCount / maxDistCount * 140) + 'px' }"
                    :title="`Mon lot ${bin.range}: ${bin.lotCount} copies`"
                  >
                    <span
                      v-if="bin.lotCount > 0"
                      class="bar-label lot-label"
                    >
                      {{ bin.lotCount }}
                    </span>
                  </div>
                  <div
                    class="bar global-bar"
                    :style="{ height: (bin.globalCount / maxDistCount * 140) + 'px' }"
                    :title="`Global ${bin.range}: ${bin.globalCount} copies`"
                  >
                    <span
                      v-if="bin.globalCount > 0"
                      class="bar-label global-label"
                    >
                      {{ bin.globalCount }}
                    </span>
                  </div>
                </div>
                <span class="bar-range">
                  {{ bin.range }}
                </span>
              </div>
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
.chart-legend { display: flex; gap: 1rem; align-items: center; }
.legend-item { display: flex; align-items: center; gap: 4px; font-size: 0.8rem; color: #475569; font-weight: 500; }
.legend-dot { width: 12px; height: 12px; border-radius: 3px; }
.lot-dot { background: #6366f1; }
.global-dot { background: #10b981; }
.bar-chart { display: flex; align-items: flex-end; gap: 6px; padding: 10px 0; min-height: 180px; border-bottom: 2px solid #e2e8f0; }
.bar-group { display: flex; flex-direction: column; align-items: center; flex: 1; }
.bar-pair { display: flex; align-items: flex-end; gap: 2px; }
.bar { min-width: 16px; border-radius: 3px 3px 0 0; position: relative; transition: height 0.3s ease; min-height: 2px; }
.lot-bar { background: #6366f1; }
.global-bar { background: #10b981; }
.bar-label { position: absolute; top: -18px; left: 50%; transform: translateX(-50%); font-size: 0.65rem; font-weight: 600; white-space: nowrap; }
.lot-label { color: #6366f1; }
.global-label { color: #059669; }
.bar-range { font-size: 0.65rem; color: #64748b; margin-top: 4px; white-space: nowrap; }

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
