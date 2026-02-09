<script setup>
import { ref, onMounted } from 'vue'
import api from '../services/api'
import AdminLayout from '../components/AdminLayout.vue'

const loading = ref(true)
const saving = ref(false)

const settings = ref({
    theme: 'light',
    notifications: true,
    defaultDuration: 60,
    gradingScaleType: '20',
    institutionName: 'Lycée Pierre Mendès France'
})

const fetchSettings = async () => {
    loading.value = true
    try {
        const res = await api.get('/settings/')
        // Merge with defaults in case some keys missing
        settings.value = { ...settings.value, ...res.data }
    } catch (e) {
        console.error("Failed to load settings", e)
    } finally {
        loading.value = false
    }
}

const saveSettings = async () => {
    saving.value = true
    try {
        await api.post('/settings/', settings.value)
        alert('Paramètres enregistrés sur le serveur')
    } catch (e) {
        console.error("Save failed", e)
        alert('Erreur lors de la sauvegarde: ' + (e.response?.data?.error || 'Erreur technique'))
    } finally {
        saving.value = false
    }
}

onMounted(() => {
    fetchSettings()
})
</script>


<template>
  <AdminLayout>
    <div class="settings-view">
      <header class="page-header">
        <h2>Paramètres Système</h2>
      </header>

    <div class="settings-card">
      <div class="setting-group">
        <label>Nom de l'établissement</label>
        <input
          v-model="settings.institutionName"
          type="text"
          class="form-input"
        >
      </div>

      <div class="setting-group">
        <label>Thème par défaut</label>
        <select
          v-model="settings.theme"
          class="form-select"
        >
          <option value="light">
            Clair
          </option>
          <option value="dark">
            Sombre
          </option>
          <option value="auto">
            Système
          </option>
        </select>
      </div>

      <div class="setting-group">
        <label>Durée d'examen par défaut (min)</label>
        <input
          v-model="settings.defaultDuration"
          type="number"
          class="form-input"
        >
      </div>

      <div class="setting-group">
        <label class="checkbox-label">
          <input
            v-model="settings.notifications"
            type="checkbox"
          >
          Activer les notifications email
        </label>
      </div>

      <div class="actions">
        <button
          class="btn btn-primary"
          @click="saveSettings"
        >
          Enregistrer
        </button>
      </div>
    </div>
    </div>
  </AdminLayout>
</template>

<style scoped>
.settings-view { padding: 2rem; max-width: 800px; margin: 0 auto; font-family: 'Inter', sans-serif; }
.page-header { margin-bottom: 2rem; border-bottom: 1px solid #e2e8f0; padding-bottom: 1rem; }
.settings-card { background: white; padding: 2rem; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); border: 1px solid #e2e8f0; }
.setting-group { margin-bottom: 1.5rem; }
.setting-group label { display: block; margin-bottom: 0.5rem; font-weight: 500; color: #334155; }
.form-input, .form-select { width: 100%; padding: 0.75rem; border: 1px solid #cbd5e1; border-radius: 6px; font-size: 1rem; }
.checkbox-label { display: flex; align-items: center; gap: 0.75rem; cursor: pointer; }
.btn-primary { background: #3b82f6; color: white; padding: 0.75rem 1.5rem; border: none; border-radius: 6px; font-weight: 600; cursor: pointer; }
.btn-primary:hover { background: #2563eb; }
</style>
