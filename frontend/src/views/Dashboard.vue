<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRoute } from 'vue-router'
import { API_URL, csrfHeader } from '../services/http'

const route = useRoute()
const examId = route.params.examId
const copies = ref([])
const exam = ref(null)
const isLoading = ref(false)
const message = ref('')

// Computed Stats
const totalCopies = computed(() => copies.value.length)
const gradedCopies = computed(() => copies.value.filter(c => c.status === 'GRADED').length)
const averageScore = computed(() => {
    if (gradedCopies.value === 0) return 0
    const total = copies.value
        .filter(c => c.status === 'GRADED')
        .reduce((sum, c) => sum + (c.total_score || 0), 0)
    return (total / gradedCopies.value).toFixed(2)
})

const fetchCopies = async () => {
  isLoading.value = true
  try {
      const res = await fetch(`${API_URL}/api/exams/${examId}/`, {
          credentials: 'include'
      })
      if (!res.ok) throw new Error("Failed to fetch exam")
      exam.value = await res.json()
      
      // Mock data until Copy Listing endpoint is ready
      // This allows UI validation without backend changes yet
      copies.value = [
          { id: '1', anonymous_id: 'A7F93', status: 'GRADED', total_score: 14.5, updated_at: '2026-06-02' },
          { id: '2', anonymous_id: 'B2X41', status: 'READY', total_score: 0, updated_at: '2026-06-02' },
          { id: '3', anonymous_id: 'C8L99', status: 'GRADED', total_score: 18.0, updated_at: '2026-06-02' },
          { id: '4', anonymous_id: 'D4K22', status: 'PROCESSING', total_score: 0, updated_at: '2026-06-02' },
          { id: '5', anonymous_id: 'E1M77', status: 'GRADED', total_score: 10.0, updated_at: '2026-06-02' },
      ]
      
  } catch (e) {
      console.error(e)
      message.value = "Erreur lors du chargement des données."
  } finally {
      isLoading.value = false
  }
}

const triggerExport = async () => {
    isLoading.value = true
    message.value = "Génération des PDF en cours..."
    try {
        const res = await fetch(`${API_URL}/api/exams/${examId}/export_all/`, {
            method: 'POST',
            credentials: 'include',
            headers: { ...csrfHeader() }
        })
        if (res.ok) {
            const data = await res.json()
            message.value = `Succès: ${data.message}`
        } else {
            message.value = "Erreur lors de l'export."
        }
    } catch (e) {
        console.error(e)
        message.value = "Erreur réseau."
    } finally {
        isLoading.value = false
    }
}

const downloadCSV = () => {
    window.open(`${API_URL}/api/exams/${examId}/csv/`, '_blank')
}

onMounted(() => {
    if (examId) fetchCopies()
})
</script>

<template>
  <div class="dashboard-container">
    <!-- Navbar Placeholder -->
    <nav class="navbar">
      <div class="brand">
        Korrigo — PMF
      </div>
      <div class="user-profile">
        <span>Admin User</span>
        <div class="avatar">
          A
        </div>
      </div>
    </nav>

    <div
      v-if="exam"
      class="main-content"
    >
      <!-- Header Section -->
      <header class="page-header">
        <div class="header-left">
          <h1>{{ exam.name }}</h1>
          <p class="subtitle">
            Tableau de bord de correction - Session {{ exam.date }}
          </p>
        </div>
        <div class="header-actions">
          <button
            class="btn btn-secondary"
            @click="downloadCSV"
          >
            <span class="icon">📊</span> Export CSV
          </button>
          <button
            class="btn btn-primary"
            @click="triggerExport"
          >
            <span class="icon">📑</span> Générer PDF Finaux
          </button>
        </div>
      </header>

      <!-- Notification Area -->
      <div
        v-if="message"
        class="notification"
        :class="{ error: message.includes('Erreur') }"
      >
        {{ message }}
      </div>

      <!-- Stats Cards -->
      <div class="stats-grid">
        <div class="stat-card">
          <div class="stat-value">
            {{ totalCopies }}
          </div>
          <div class="stat-label">
            Copies Totales
          </div>
        </div>
        <div class="stat-card">
          <div class="stat-value highlight">
            {{ gradedCopies }}
          </div>
          <div class="stat-label">
            Copies Corrigées
          </div>
        </div>
        <div class="stat-card">
          <div class="stat-value">
            {{ averageScore }} <span class="unit">/ 20</span>
          </div>
          <div class="stat-label">
            Moyenne Générale
          </div>
        </div>
      </div>

      <!-- Data Table -->
      <div class="table-container shadow-sm">
        <table class="premium-table">
          <thead>
            <tr>
              <th>ID Anonyme</th>
              <th>Date Maj</th>
              <th>Statut</th>
              <th>Note</th>
              <th class="text-right">
                Actions
              </th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="copy in copies"
              :key="copy.id"
            >
              <td class="font-medium">
                {{ copy.anonymous_id }}
              </td>
              <td class="text-muted">
                {{ copy.updated_at }}
              </td>
              <td>
                <span :class="['status-badge', copy.status.toLowerCase()]">
                  {{ copy.status }}
                </span>
              </td>
              <td class="font-bold">
                <span v-if="copy.status === 'GRADED'">{{ copy.total_score }}</span>
                <span
                  v-else
                  class="text-muted"
                >-</span>
              </td>
              <td class="text-right">
                <button
                  class="btn-icon"
                  title="Voir Détails"
                >
                  👁️
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
    <div
      v-else
      class="loading-state"
    >
      Chargement...
    </div>
  </div>
</template>

<style scoped>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

.dashboard-container {
    font-family: 'Inter', sans-serif;
    background-color: #f8f9fa;
    min-height: 100vh;
    color: #1a1a1a;
}

/* Navbar */
.navbar {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 1rem 2rem;
    background: white;
    border-bottom: 1px solid #eef2f6;
}
.brand { font-weight: 700; font-size: 1.25rem; color: #2d3748; }
.badge-beta { background: #ebf8ff; color: #3182ce; font-size: 0.75rem; padding: 2px 6px; border-radius: 4px; vertical-align: middle; }
.user-profile { display: flex; align-items: center; gap: 0.75rem; font-size: 0.9rem; }
.avatar { width: 32px; height: 32px; background: #4a5568; color: white; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: 600; }

/* Main Content */
.main-content { max-width: 1200px; margin: 0 auto; padding: 2rem; }

/* Header */
.page-header { display: flex; justify-content: space-between; align-items: flex-end; margin-bottom: 2rem; }
.page-header h1 { font-size: 1.75rem; font-weight: 700; margin: 0; color: #1a202c; }
.subtitle { color: #718096; margin: 0.25rem 0 0 0; }
.header-actions { display: flex; gap: 1rem; }

/* Buttons */
.btn { padding: 0.6rem 1.2rem; border-radius: 6px; font-weight: 500; cursor: pointer; border: none; transition: all 0.2s; display: flex; align-items: center; gap: 0.5rem; }
.btn-primary { background: #3182ce; color: white; box-shadow: 0 4px 6px -1px rgba(49, 130, 206, 0.2); }
.btn-primary:hover { background: #2c5282; }
.btn-secondary { background: white; border: 1px solid #e2e8f0; color: #4a5568; }
.btn-secondary:hover { background: #f7fafc; }

/* Stats Grid */
.stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1.5rem; margin-bottom: 2rem; }
.stat-card { background: white; padding: 1.5rem; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.05); border: 1px solid #e2e8f0; }
.stat-value { font-size: 2rem; font-weight: 700; color: #2d3748; line-height: 1.2; }
.stat-value.highlight { color: #3182ce; }
.unit { font-size: 1rem; color: #a0aec0; margin-left: 4px; }
.stat-label { color: #718096; font-size: 0.875rem; margin-top: 0.25rem; }

/* Table */
.table-container { background: white; border-radius: 8px; overflow: hidden; border: 1px solid #e2e8f0; }
.premium-table { width: 100%; border-collapse: collapse; }
.premium-table th { background: #f7fafc; padding: 1rem; text-align: left; font-weight: 600; color: #4a5568; font-size: 0.875rem; border-bottom: 1px solid #e2e8f0; }
.premium-table td { padding: 1rem; border-bottom: 1px solid #eef2f6; font-size: 0.95rem; }
.premium-table tr:hover { background: #fcfcfc; }
.premium-table tr:last-child td { border-bottom: none; }

/* Badges & Text Utilities */
.status-badge { padding: 4px 10px; border-radius: 9999px; font-size: 0.75rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.025em; }
.status-badge.graded { background: #def7ec; color: #03543f; }
.status-badge.ready { background: #feecdc; color: #9c4221; }
.status-badge.processing { background: #ebf8ff; color: #2c5282; }

.font-medium { font-weight: 500; }
.font-bold { font-weight: 600; }
.text-muted { color: #a0aec0; }
.text-right { text-align: right; }

.btn-icon { background: none; border: none; cursor: pointer; font-size: 1.2rem; opacity: 0.6; transition: opacity 0.2s; }
.btn-icon:hover { opacity: 1; }

.notification { background: #def7ec; color: #03543f; padding: 1rem; border-radius: 6px; margin-bottom: 1.5rem; }
.notification.error { background: #fed7d7; color: #9b2c2c; }

.shadow-sm { box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.05); }
</style>
