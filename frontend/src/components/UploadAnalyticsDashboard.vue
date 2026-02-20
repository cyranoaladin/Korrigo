<template>
  <div class="analytics-dashboard">
    <h2 class="dashboard-title">
      📊 Analytique des téléversements
    </h2>
    
    <!-- Période de sélection -->
    <div class="period-selector">
      <label>Période:</label>
      <select
        v-model="selectedPeriod"
        @change="loadAnalytics"
      >
        <option value="7">
          7 derniers jours
        </option>
        <option value="30">
          30 derniers jours
        </option>
        <option value="90">
          90 derniers jours
        </option>
        <option value="365">
          Année complète
        </option>
      </select>
    </div>

    <!-- Loading state -->
    <div
      v-if="loading"
      class="loading"
    >
      Chargement des analytics...
    </div>

    <!-- Error state -->
    <div
      v-if="error"
      class="error-message"
    >
      {{ error }}
    </div>

    <!-- Analytics content -->
    <div
      v-if="!loading && analytics"
      class="analytics-content"
    >
      <!-- Mode Distribution -->
      <div class="analytics-card">
        <h3>Distribution par Mode d'Upload</h3>
        <div class="mode-distribution">
          <div class="mode-stat">
            <span class="mode-badge badge-batch">BATCH_A3</span>
            <div class="stat-value">
              {{ analytics.upload_type_distribution.BATCH_A3.count }}
            </div>
            <div class="stat-label">
              {{ analytics.upload_type_distribution.BATCH_A3.percentage }}%
            </div>
          </div>
          <div class="mode-stat">
            <span class="mode-badge badge-individual">INDIVIDUAL_A4</span>
            <div class="stat-value">
              {{ analytics.upload_type_distribution.INDIVIDUAL_A4.count }}
            </div>
            <div class="stat-label">
              {{ analytics.upload_type_distribution.INDIVIDUAL_A4.percentage }}%
            </div>
          </div>
        </div>
      </div>

      <!-- Global Metrics -->
      <div class="analytics-card">
        <h3>Métriques Globales</h3>
        <div class="metrics-grid">
          <div class="metric-item">
            <div class="metric-label">
              Total téléversements
            </div>
            <div class="metric-value">
              {{ analytics.global_metrics.total_uploads || 0 }}
            </div>
          </div>
          <div class="metric-item">
            <div class="metric-label">
              Fichiers téléversés
            </div>
            <div class="metric-value">
              {{ analytics.global_metrics.total_files_uploaded || 0 }}
            </div>
          </div>
          <div class="metric-item">
            <div class="metric-label">
              Taux de Succès
            </div>
            <div class="metric-value success">
              {{ analytics.global_metrics.success_rate || 0 }}%
            </div>
          </div>
          <div class="metric-item">
            <div class="metric-label">
              Données téléversées
            </div>
            <div class="metric-value">
              {{ analytics.global_metrics.total_data_uploaded_gb || 0 }} GB
            </div>
          </div>
          <div class="metric-item">
            <div class="metric-label">
              Temps Moyen
            </div>
            <div class="metric-value">
              {{ (analytics.global_metrics.avg_upload_time || 0).toFixed(2) }}s
            </div>
          </div>
        </div>
      </div>

      <!-- Storage Analytics -->
      <div
        v-if="storageAnalytics"
        class="analytics-card"
      >
        <h3>Stockage et Optimisation</h3>
        <div class="storage-info">
          <div class="storage-item">
            <div class="storage-label">
              BATCH_A3
            </div>
            <div class="storage-value">
              {{ storageAnalytics.storage_by_mode.BATCH_A3.estimated_storage_gb }} GB
            </div>
            <div class="storage-copies">
              {{ storageAnalytics.storage_by_mode.BATCH_A3.copies_count }} copies
            </div>
          </div>
          <div class="storage-item">
            <div class="storage-label">
              INDIVIDUAL_A4
            </div>
            <div class="storage-value">
              {{ storageAnalytics.storage_by_mode.INDIVIDUAL_A4.estimated_storage_gb }} GB
            </div>
            <div class="storage-copies">
              {{ storageAnalytics.storage_by_mode.INDIVIDUAL_A4.copies_count }} copies
            </div>
          </div>
          <div class="storage-savings">
            <strong>✅ Économie de stockage:</strong> {{ storageAnalytics.total_storage_saved_percentage }}%
            <br>
            <small>({{ storageAnalytics.storage_by_mode.INDIVIDUAL_A4.deduplication.files_saved }} fichiers dupliqués évités)</small>
          </div>
        </div>
      </div>

      <!-- Top Users -->
      <div
        v-if="analytics.top_users && analytics.top_users.length > 0"
        class="analytics-card"
      >
        <h3>Top Utilisateurs</h3>
        <table class="top-users-table">
          <thead>
            <tr>
              <th>Utilisateur</th>
              <th>Téléversements</th>
              <th>Fichiers</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="user in analytics.top_users"
              :key="user.uploaded_by__username"
            >
              <td>{{ user.uploaded_by__username }}</td>
              <td>{{ user.uploads }}</td>
              <td>{{ user.total_files }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import api from '../services/api'

const selectedPeriod = ref(30)
const loading = ref(false)
const error = ref(null)
const analytics = ref(null)
const storageAnalytics = ref(null)

const loadAnalytics = async () => {
  loading.value = true
  error.value = null
  
  try {
    // Load upload analytics
    const uploadResponse = await api.get(`/exams/analytics/uploads/?days=${selectedPeriod.value}`)
    analytics.value = uploadResponse.data
    
    // Load storage analytics
    const storageResponse = await api.get('/exams/analytics/storage/')
    storageAnalytics.value = storageResponse.data
    
  } catch (err) {
    error.value = 'Erreur lors du chargement des analytics'
    console.error('Analytics error:', err)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadAnalytics()
})
</script>

<style scoped>
.analytics-dashboard {
  padding: 24px;
  max-width: 1200px;
  margin: 0 auto;
}

.dashboard-title {
  font-size: 28px;
  font-weight: 700;
  margin-bottom: 24px;
  color: #1f2937;
}

.period-selector {
  margin-bottom: 24px;
  display: flex;
  align-items: center;
  gap: 12px;
}

.period-selector label {
  font-weight: 600;
  color: #4b5563;
}

.period-selector select {
  padding: 8px 16px;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  background: white;
  font-size: 14px;
  cursor: pointer;
}

.analytics-card {
  background: white;
  border-radius: 12px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.1);
  padding: 24px;
  margin-bottom: 24px;
}

.analytics-card h3 {
  font-size: 18px;
  font-weight: 600;
  margin-bottom: 16px;
  color: #1f2937;
}

.mode-distribution {
  display: flex;
  gap: 32px;
  justify-content: center;
  flex-wrap: wrap;
}

.mode-stat {
  text-align: center;
  min-width: 200px;
}

.mode-badge {
  display: inline-block;
  padding: 6px 16px;
  border-radius: 20px;
  font-size: 14px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 12px;
}

.badge-batch {
  background-color: #dbeafe;
  color: #1e40af;
}

.badge-individual {
  background-color: #fef3c7;
  color: #92400e;
}

.stat-value {
  font-size: 36px;
  font-weight: 700;
  color: #1f2937;
  margin: 8px 0;
}

.stat-label {
  font-size: 14px;
  color: #6b7280;
}

.metrics-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 20px;
}

.metric-item {
  text-align: center;
  padding: 16px;
  background: #f9fafb;
  border-radius: 8px;
}

.metric-label {
  font-size: 13px;
  color: #6b7280;
  margin-bottom: 8px;
  font-weight: 500;
}

.metric-value {
  font-size: 24px;
  font-weight: 700;
  color: #1f2937;
}

.metric-value.success {
  color: #059669;
}

.storage-info {
  display: grid;
  gap: 16px;
}

.storage-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px;
  background: #f9fafb;
  border-radius: 8px;
}

.storage-label {
  font-weight: 600;
  color: #4b5563;
}

.storage-value {
  font-size: 20px;
  font-weight: 700;
  color: #1f2937;
}

.storage-copies {
  font-size: 14px;
  color: #6b7280;
}

.storage-savings {
  padding: 16px;
  background: #d1fae5;
  border-left: 4px solid #059669;
  border-radius: 8px;
  margin-top: 12px;
}

.top-users-table {
  width: 100%;
  border-collapse: collapse;
}

.top-users-table th,
.top-users-table td {
  padding: 12px;
  text-align: left;
  border-bottom: 1px solid #e5e7eb;
}

.top-users-table th {
  background: #f9fafb;
  font-weight: 600;
  color: #4b5563;
  font-size: 13px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.loading,
.error-message {
  padding: 24px;
  text-align: center;
  color: #6b7280;
}

.error-message {
  color: #dc2626;
  background: #fee2e2;
  border-radius: 8px;
}
</style>
