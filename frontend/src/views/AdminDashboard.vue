<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import api from '../services/api'

const authStore = useAuthStore()
const router = useRouter()
const exams = ref([])
const loading = ref(true)

const fetchExams = async () => {
    loading.value = true
    try {
        const res = await api.get('/exams/')
        // Handle pagination (DRF default) or flat list
        exams.value = Array.isArray(res.data) ? res.data : (res.data.results || [])
    } catch (e) {
        console.error("Failed to fetch exams", e)
    } finally {
        loading.value = false
    }
}

const handleLogout = async () => {
    await authStore.logout()
    router.push('/login')
}

const goToIdentification = (id) => {
    if (!id) {
        console.error("Tentative de navigation sans ID d'examen");
        return;
    }
    router.push({ name: 'IdentificationDesk', params: { examId: id } })
}

const fileInput = ref(null)

const triggerUpload = () => {
    fileInput.value.click()
}

const uploadExam = async (event) => {
    const file = event.target.files[0]
    if (!file) return

    const examName = prompt("Nom de l'examen :", file.name.replace('.pdf', ''))
    if (!examName) return

    const formData = new FormData()
    formData.append('pdf_source', file)
    formData.append('name', examName)
    // Default date to today
    formData.append('date', new Date().toISOString().split('T')[0])

    try {
        await api.post('/exams/upload/', formData, {
            headers: { 'Content-Type': 'multipart/form-data' } // Axios auto-sets boundary but good to be explicit
        })
        
        alert('Examen importé avec succès !')
        await fetchExams()
    } catch (e) {
        const errMsg = e.response?.data?.error || 'Erreur technique'
        console.error("Upload failed", e)
        alert('Erreur: ' + errMsg)
    }
}

const showCreateModal = ref(false)
const newExam = ref({ name: '', date: new Date().toISOString().split('T')[0] })

const openCreateModal = () => {
    newExam.value = { name: '', date: new Date().toISOString().split('T')[0] }
    showCreateModal.value = true
}

const createExam = async () => {
    if (!newExam.value.name) return
    
    try {
        await api.post('/exams/', newExam.value)
        alert('Examen créé avec succès')
        showCreateModal.value = false
        fetchExams()
    } catch (e) {
        console.error("Create exam failed", e)
        alert("Erreur: " + (e.response?.data?.error || e.message))
    }
}

const teachersList = ref([])
const selectedCorrectors = ref([])
const showCorrectorModal = ref(false)
const selectedExamId = ref(null)
const selectedExamName = ref('')
const loadingTeachers = ref(false)

const loadTeachers = async () => {
    loadingTeachers.value = true
    try {
        const res = await api.get('/users/', { params: { role: 'Teacher' } })
        teachersList.value = res.data
    } catch (e) {
        console.error("Failed to load teachers", e)
    } finally {
        loadingTeachers.value = false
    }
}

const openCorrectorModal = async (exam) => {
    selectedExamId.value = exam.id
    selectedExamName.value = exam.name
    selectedCorrectors.value = exam.correctors || [] 
    
    showCorrectorModal.value = true
    if (teachersList.value.length === 0) {
        await loadTeachers()
    }
}

const saveCorrectors = async () => {
    try {
        await api.patch(`/exams/${selectedExamId.value}/`, {
            correctors: selectedCorrectors.value
        })
        alert("Correcteurs assignés avec succès")
        showCorrectorModal.value = false
        fetchExams() // Refresh list to update local state if needed
    } catch (e) {
        console.error("Save correctors failed", e)
        alert("Erreur lors de l'enregistrement")
    }
}

onMounted(() => {
    fetchExams()
})
</script>

<template>
  <div
    data-testid="admin-dashboard"
    class="admin-dashboard"
  >
    <nav class="sidebar">
      <div class="logo">
        <img
          src="/images/Korrigo.png"
          alt="Korrigo Logo"
          class="sidebar-logo-img"
        >
        <span>Korrigo</span>
      </div>
      <ul class="nav-links">
        <li class="active">
          Gestion Examens
        </li>
        <li 
          :class="{ active: $route.name === 'UserManagement' }"
          @click="router.push({ name: 'UserManagement' })"
        >
          Utilisateurs
        </li>
        <li 
          :class="{ active: $route.name === 'Settings' }"
          @click="router.push({ name: 'Settings' })"
        >
          Paramètres
        </li>
      </ul>
      <button
        data-testid="logout-button"
        class="logout-btn"
        @click="handleLogout"
      >
        Déconnexion
      </button>
      <div class="attribution">
        Concepteur : Aleddine BEN RHOUMA<br>Labo Maths ERT
      </div>
    </nav>
        
    <main class="content">
      <header>
        <h1 data-testid="admin-dashboard-title">
          Korrigo — Tableau de Bord Administrateur
        </h1>
        <div class="user-info">
          {{ authStore.user?.username }} (Admin)
        </div>
      </header>
            
      <section class="exam-management">
        <div class="actions-bar">
          <button
            data-testid="exams.new"
            class="btn btn-primary"
            @click="openCreateModal"
          >
            + Nouvel Examen
          </button>
          <button
            class="btn btn-outline"
            data-testid="exams.import"
            @click="triggerUpload"
          >
            Importer Scans
          </button>
          <input 
            ref="fileInput" 
            type="file" 
            style="display: none" 
            accept="application/pdf"
            data-testid="exams.fileInput"
            @change="uploadExam"
          >
        </div>
                
        <div
          v-if="loading"
          class="loading"
        >
          Chargement des examens...
        </div>
                
        <table
          v-else
          class="data-table"
          data-testid="exams.list"
        >
          <thead>
            <tr>
              <th>Nom</th>
              <th>Date</th>
              <th>État</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="exam in (exams || [])"
              :key="exam?.id"
              :data-testid="exam ? `exam.row.${exam.id}` : ''"
            >
              <td>{{ exam?.name }}</td>
              <td>{{ exam?.date }}</td>
              <td>
                <span
                  v-if="exam?.is_processed"
                  class="badge status-import"
                >Importé</span>
                <span
                  v-else
                  class="badge status-pending"
                >En création</span>
              </td>
              <td>
                <button
                  class="btn-sm"
                  @click="router.push({ name: 'StapleView', params: { examId: exam.id } })"
                >
                  Agrafer
                </button>
                <button
                  class="btn-sm"
                  @click="router.push({ name: 'MarkingSchemeView', params: { examId: exam.id } })"
                >
                  Barème
                </button>
                <button 
                  v-if="exam?.id"
                  class="btn-sm btn-action" 
                  @click="goToIdentification(exam.id)"
                >
                  Video-Coding
                </button>
                <button 
                  class="btn-sm" 
                  title="Assigner des correcteurs"
                  @click="openCorrectorModal(exam)"
                >
                  Correcteurs
                </button>
              </td>
            </tr>
            <tr v-if="exams.length === 0">
              <td
                colspan="4"
                class="empty-cell"
              >
                Aucun examen trouvé. Créez-en un ou importez des scans.
              </td>
            </tr>
          </tbody>
        </table>
      </section>
    </main>

    <!-- Create Exam Modal -->
    <div 
      v-if="showCreateModal" 
      class="modal-overlay"
    >
      <div class="modal-card">
        <h3>Nouvel Examen</h3>
        
        <div class="form-group">
          <label>Nom de l'examen</label>
          <input 
            v-model="newExam.name" 
            type="text" 
            placeholder="Ex: Bac Blanc Maths 2026" 
            class="form-input" 
            autofocus
          >
        </div>
        
        <div class="form-group">
          <label>Date</label>
          <input 
            v-model="newExam.date" 
            type="date" 
            class="form-input" 
          >
        </div>
        
        <div class="modal-actions">
          <button 
            class="btn btn-outline"
            @click="showCreateModal = false" 
          >
            Annuler
          </button>
          <button 
            class="btn btn-primary"
            @click="createExam" 
          >
            Créer
          </button>
        </div>
      </div>
    </div>

    <!-- Assign Correctors Modal -->
    <div 
      v-if="showCorrectorModal" 
      class="modal-overlay"
    >
      <div class="modal-card">
        <h3>Assigner Correcteurs</h3>
        <p class="modal-subtitle">
          Pour: {{ selectedExamName }}
        </p>
        
        <div class="form-group">
          <div v-if="loadingTeachers">
            Chargement...
          </div>
          <div 
            v-else 
            class="checkbox-list"
          >
            <label 
              v-for="teacher in teachersList" 
              :key="teacher.id" 
              class="checkbox-item"
            >
              <input 
                v-model="selectedCorrectors" 
                type="checkbox" 
                :value="teacher.id"
              >
              {{ teacher.username }} ({{ teacher.email }})
            </label>
            <div 
              v-if="teachersList.length === 0" 
              class="empty-list"
            >
              Aucun enseignant trouvé.
            </div>
          </div>
        </div>
        
        <div class="modal-actions">
          <button 
            class="btn btn-outline"
            @click="showCorrectorModal = false" 
          >
            Annuler
          </button>
          <button 
            class="btn btn-primary"
            @click="saveCorrectors" 
          >
            Enregistrer
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.btn-action { background: #8b5cf6; color: white; }
.btn-action:hover { background: #7c3aed; }
.loading { padding: 2rem; text-align: center; color: #6b7280; }
.empty-cell { padding: 3rem; text-align: center; color: #9ca3af; font-style: italic; }
.admin-dashboard { display: flex; height: 100vh; font-family: 'Inter', sans-serif; }
.sidebar { width: 250px; background: #1e293b; color: white; padding: 1.5rem; display: flex; flex-direction: column; }
.logo { font-size: 1.5rem; font-weight: 800; margin-bottom: 2.5rem; color: #60a5fa; display: flex; align-items: center; gap: 0.75rem; }
.sidebar-logo-img { height: 32px; width: auto; filter: drop-shadow(0 0 8px rgba(96, 165, 250, 0.3)); }
.nav-links { list-style: none; padding: 0; flex: 1; }
.nav-links li { padding: 0.75rem 1rem; cursor: pointer; border-radius: 6px; margin-bottom: 0.5rem; color: #94a3b8; transition: all 0.2s; }
.nav-links li.active, .nav-links li:hover { background: #334155; color: white; }
.logout-btn { margin-top: 1rem; background: none; border: 1px solid #ef4444; color: #ef4444; padding: 0.5rem; border-radius: 6px; cursor: pointer; transition: all 0.2s; }
.logout-btn:hover { background: #ef4444; color: white; }
.attribution { margin-top: 1.5rem; font-size: 0.7rem; color: #475569; text-align: center; line-height: 1.4; border-top: 1px solid #334155; padding-top: 1rem; }

.content { flex: 1; background: #f1f5f9; padding: 2rem; overflow-y: auto; }
header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 2rem; }
h1 { font-size: 1.5rem; color: #0f172a; margin: 0; }
.user-info { font-weight: 500; color: #64748b; }

.actions-bar { margin-bottom: 1.5rem; display: flex; gap: 1rem; }
.btn { padding: 0.6rem 1.2rem; border-radius: 6px; border: none; font-weight: 500; cursor: pointer; }
.btn-primary { background: #2563eb; color: white; }
.btn-outline { background: white; border: 1px solid #cbd5e1; color: #475569; }
.btn-sm { padding: 4px 8px; font-size: 0.8rem; margin-right: 5px; cursor: pointer; }

.data-table { width: 100%; background: white; border-radius: 8px; border-collapse: collapse; box-shadow: 0 1px 3px rgba(0,0,0,0.05); }
.data-table th, .data-table td { padding: 1rem; text-align: left; border-bottom: 1px solid #e2e8f0; }
.badge { padding: 4px 8px; border-radius: 999px; font-size: 0.75rem; background: #e0e7ff; color: #3730a3; }

/* Modal Styles */
.modal-overlay { position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.5); display: flex; justify-content: center; align-items: center; z-index: 1000; }
.modal-card { background: white; padding: 2rem; border-radius: 12px; width: 400px; box-shadow: 0 20px 25px -5px rgba(0,0,0,0.1); }
.modal-card h3 { margin-top: 0; margin-bottom: 1.5rem; color: #1e293b; }
.form-group { margin-bottom: 1rem; }
.form-group label { display: block; margin-bottom: 0.5rem; color: #475569; font-size: 0.9rem; }
.form-input { width: 100%; padding: 0.5rem; border: 1px solid #cbd5e1; border-radius: 4px; }
.modal-actions { display: flex; justify-content: flex-end; gap: 1rem; margin-top: 1.5rem; }

/* Checkbox List Styles */
.checkbox-list {
  max-height: 200px;
  overflow-y: auto;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  padding: 0.5rem;
}
.checkbox-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem;
  cursor: pointer;
  border-radius: 4px;
}
.checkbox-item:hover {
  background: #f1f5f9;
}
.modal-subtitle {
  color: #64748b;
  margin-top: -1rem;
  margin-bottom: 1.5rem;
  font-size: 0.9rem;
}
.empty-list {
  text-align: center;
  color: #94a3b8;
  padding: 1rem;
  font-style: italic;
}
</style>
