<script setup>
import { ref, onMounted, computed } from 'vue'
import api from '../services/api'
import { useAuthStore } from '../stores/auth'

const props = defineProps({
  visible: Boolean
})

const emit = defineEmits(['close'])
const authStore = useAuthStore()

const reports = ref([])
const examTypes = ref([])
const loading = ref(false)
const saving = ref(false)
const error = ref(null)

const showForm = ref(false)
const formData = ref({
  id: null,
  exam_type: '',
  title: '',
  content: '',
  is_published: false
})

const isAdmin = computed(() => authStore.user?.role === 'Admin' || authStore.user?.is_superuser)

const fetchExamTypes = async () => {
    try {
        const response = await api.get('/exams/types/')
        examTypes.value = response.data
    } catch (err) {
        console.error('Failed to fetch exam types', err)
    }
}

const fetchReports = async () => {
  loading.value = true
  error.value = null
  try {
    const response = await api.get('/exams/reports/')
    reports.value = response.data
  } catch (err) {
    error.value = 'Erreur lors du chargement des rapports.'
    console.error(err)
  } finally {
    loading.value = false
  }
}

const openCreate = () => {
  formData.value = { id: null, exam_type: '', title: '', content: '', is_published: false }
  showForm.value = true
}

const editReport = (report) => {
  formData.value = { ...report }
  showForm.value = true
}

const saveReport = async () => {
  if (!formData.value.exam_type || !formData.value.title) {
    error.value = "La matière et le titre sont obligatoires."
    return
  }
  saving.value = true
  try {
    if (formData.value.id) {
      await api.put(`/exams/reports/${formData.value.id}/`, formData.value)
    } else {
      await api.post('/exams/reports/', formData.value)
    }
    showForm.value = false
    await fetchReports()
  } catch (err) {
    error.value = 'Erreur lors de la sauvegarde.'
    console.error(err)
  } finally {
    saving.value = false
  }
}

const deleteReport = async (id) => {
  if (!confirm('Voulez-vous vraiment supprimer ce rapport ?')) return
  try {
    await api.delete(`/exams/reports/${id}/`)
    await fetchReports()
  } catch (err) {
    error.value = 'Erreur lors de la suppression.'
  }
}

onMounted(() => {
  fetchReports()
  fetchExamTypes()
})
</script>

<template>
  <div v-if="visible" class="modal-overlay">
    <div class="modal-card modal-card-large jury-modal">
      <div class="modal-header-nav">
        <h3>Gérer les Rapports de Jury</h3>
        <button class="btn-close" @click="emit('close')">×</button>
      </div>
      
      <div v-if="error" class="error-banner">
        {{ error }}
        <button class="btn-close" @click="error = null">×</button>
      </div>

      <div class="jury-reports-container" v-if="!showForm">
        <div class="toolbar">
          <button v-if="isAdmin" class="btn-primary" @click="openCreate">Nouveau Rapport</button>
        </div>
        
        <div v-if="loading" class="loading">Chargement...</div>
        <table v-else-if="reports && reports.length > 0" class="data-table">
          <thead>
            <tr>
              <th>Matière/Rubrique</th>
              <th>Titre</th>
              <th>Auteur</th>
              <th>Statut</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="r in reports" :key="r.id">
              <td>{{ r.exam_type_name || 'Rubrique ' + r.exam_type }}</td>
              <td>{{ r.title }}</td>
              <td>{{ r.created_by_username }}</td>
              <td>
                <span :class="['badge', r.is_published ? 'status-published' : 'status-draft']">
                  {{ r.is_published ? 'Publié' : 'Brouillon' }}
                </span>
              </td>
              <td class="actions-cell">
                <button class="btn-sm" @click="editReport(r)">Lire / Éditer</button>
                <button v-if="isAdmin" class="btn-sm btn-danger" @click="deleteReport(r.id)">Supprimer</button>
              </td>
            </tr>
          </tbody>
        </table>
        <div v-else class="empty-state">
          Aucun rapport de jury n'a été trouvé.
        </div>
      </div>

      <div class="report-form" v-else>
        <div class="form-group">
          <label>Matière / Rubrique</label>
          <select v-model="formData.exam_type" class="form-input" :disabled="!isAdmin">
            <option disabled value="">-- Choisir une matière --</option>
            <option v-for="e in examTypes" :key="e?.id" :value="e?.id">{{ e?.name }}</option>
          </select>
        </div>
        <div class="form-group">
          <label>Titre du Rapport</label>
          <input type="text" v-model="formData.title" class="form-input" placeholder="Ex: Rapport de jury BB Maths..." :disabled="!isAdmin">
        </div>
        <div class="form-group">
          <label>Contenu / Bilan</label>
          <textarea v-model="formData.content" class="form-input" rows="10" placeholder="Rédigez le bilan global..." :disabled="!isAdmin"></textarea>
        </div>
        <div class="form-group checkbox-group" v-if="isAdmin">
          <label>
            <input type="checkbox" v-model="formData.is_published">
            Rapport Publié (visible par les correcteurs)
          </label>
        </div>
        
        <div class="modal-actions">
          <button class="btn-outline" @click="showForm = false" :disabled="saving">Annuler</button>
          <button v-if="isAdmin" class="btn-primary" @click="saveReport" :disabled="saving">
            {{ saving ? 'Enregistrement...' : 'Enregistrer le rapport' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.modal-overlay { position: fixed; top: 0; left: 0; width: 100vw; height: 100vh; background: rgba(15,23,42,0.6); display: flex; justify-content: center; align-items: center; z-index: 50; }
.modal-card { background: white; padding: 2rem; border-radius: 8px; width: 400px; max-width: 90%; box-shadow: 0 10px 15px -3px rgba(0,0,0,0.1); }
.modal-card-large { width: 800px; max-width: 95vw; max-height: 90vh; overflow-y: auto; }
.modal-header-nav { display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #e2e8f0; padding-bottom: 1rem; margin-bottom: 1.5rem; }
.modal-header-nav h3 { margin: 0; }
.btn-close { background: none; border: none; font-size: 1.5rem; cursor: pointer; color: #64748b; padding: 0; line-height: 1; }
.btn-close:hover { color: #ef4444; }

.toolbar { margin-bottom: 1rem; display: flex; justify-content: flex-end; }
.data-table { width: 100%; border-collapse: collapse; }
.data-table th, .data-table td { padding: 1rem; text-align: left; border-bottom: 1px solid #e2e8f0; }
.data-table th { background: #f8fafc; font-weight: 600; color: #64748b; font-size: 0.85rem; text-transform: uppercase; }
.actions-cell { display: flex; gap: 0.5rem; }

.error-banner { background: #fee2e2; color: #b91c1c; padding: 1rem; border-radius: 6px; margin-bottom: 1rem; display: flex; justify-content: space-between; }
.badge { padding: 0.25rem 0.5rem; border-radius: 12px; font-size: 0.75rem; font-weight: 600; }
.status-published { background: #dcfce7; color: #166534; }
.status-draft { background: #f1f5f9; color: #475569; }

.form-group { margin-bottom: 1.5rem; }
.form-group label { display: block; margin-bottom: 0.5rem; font-weight: 500; color: #475569; font-size: 0.9rem; }
.form-input { width: 100%; padding: 0.6rem; border: 1px solid #cbd5e1; border-radius: 4px; font-size: 0.95rem; font-family: inherit; }
.checkbox-group label { display: flex; align-items: center; gap: 0.5rem; cursor: pointer; }
.modal-actions { display: flex; justify-content: flex-end; gap: 1rem; margin-top: 2rem; }

.btn-primary { background: #38bdf8; color: white; border: none; padding: 0.6rem 1.2rem; border-radius: 6px; cursor: pointer; font-weight: 500; }
.btn-primary:hover { background: #0284c7; }
.btn-outline { background: white; border: 1px solid #cbd5e1; color: #475569; padding: 0.6rem 1.2rem; border-radius: 6px; cursor: pointer; font-weight: 500; }
.btn-sm { padding: 0.4rem 0.8rem; font-size: 0.8rem; border-radius: 4px; border: 1px solid #cbd5e1; background: white; cursor: pointer; }
.btn-danger { color: #ef4444; border-color: #fca5a5; }
.btn-danger:hover { background: #fef2f2; }
.empty-state { padding: 3rem; text-align: center; color: #64748b; background: #f8fafc; border-radius: 8px; border: 1px dashed #cbd5e1; }
</style>
