<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../../stores/auth'
import api from '../../services/api'

const router = useRouter()
const authStore = useAuthStore()

const students = ref([])
const groupe = ref('')
const isLoading = ref(true)
const error = ref(null)

const fetchStudents = async () => {
    isLoading.value = true
    error.value = null
    try {
        const response = await api.get('/grading/my-students/')
        students.value = response.data.students || []
        groupe.value = response.data.groupe || ''
    } catch (err) {
        console.error('Failed to fetch students', err)
        error.value = err.response?.data?.error || 'Erreur lors du chargement des élèves.'
    } finally {
        isLoading.value = false
    }
}

const goToStudentBilan = (studentId) => {
    router.push(`/corrector/student/${studentId}/bilan`)
}

const goBack = () => {
    router.push('/corrector-dashboard')
}

const handleLogout = async () => {
    await authStore.logout()
    router.push('/login')
}

const getStatusClass = (status) => {
    return status?.toLowerCase() || 'unknown'
}

const getStatusLabel = (status) => {
    const labels = {
        'STAGING': 'En attente',
        'READY': 'Prêt',
        'GRADED': 'Corrigé',
    }
    return labels[status] || status
}

onMounted(fetchStudents)
</script>

<template>
  <div class="my-students-page">
    <header class="top-nav">
      <div class="brand">
        <button class="btn-back" @click="goBack">← Retour</button>
        Korrigo — Mes Élèves
      </div>
      <div class="user-menu">
        <span>{{ authStore.user?.username }}</span>
        <span v-if="groupe" class="groupe-badge">Groupe {{ groupe }}</span>
        <button class="btn-logout" @click="handleLogout">Déconnexion</button>
      </div>
    </header>

    <main class="container">
      <div class="page-header">
        <h1>👥 Mes Élèves</h1>
        <p v-if="groupe">Groupe <strong>{{ groupe }}</strong> — {{ students.length }} élève(s)</p>
      </div>

      <div v-if="isLoading" class="loading">
        Chargement des élèves...
      </div>

      <div v-else-if="error" class="error-message">
        {{ error }}
      </div>

      <div v-else-if="students.length === 0" class="empty-state">
        Aucun élève trouvé dans votre groupe.
      </div>

      <div v-else class="students-grid">
        <div
          v-for="student in students"
          :key="student.id"
          class="student-card"
          @click="goToStudentBilan(student.id)"
        >
          <div class="student-info">
            <div class="student-name">{{ student.last_name }} {{ student.first_name }}</div>
            <div class="student-class">{{ student.class_name }}</div>
            <div class="student-email">{{ student.email }}</div>
          </div>
          <div class="student-copies">
            <div
              v-for="copy in student.copies"
              :key="copy.copy_id"
              class="copy-summary"
            >
              <span class="exam-name">{{ copy.exam_name }}</span>
              <span :class="['status-badge', getStatusClass(copy.status)]">
                {{ getStatusLabel(copy.status) }}
              </span>
              <span v-if="copy.total_score !== null" class="score">
                {{ copy.total_score.toFixed(2) }}/20
              </span>
              <span v-else class="score pending">—</span>
            </div>
          </div>
          <div class="action-arrow">→</div>
        </div>
      </div>
    </main>
  </div>
</template>

<style scoped>
.my-students-page { background: #f8fafc; min-height: 100vh; font-family: 'Inter', sans-serif; }

.top-nav { background: white; padding: 1rem 2rem; display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #e2e8f0; }
.brand { font-weight: 700; color: #0f172a; font-size: 1.1rem; display: flex; align-items: center; gap: 1rem; }
.btn-back { background: none; border: none; color: #6366f1; cursor: pointer; font-size: 0.9rem; font-weight: 500; }
.btn-back:hover { text-decoration: underline; }
.user-menu { display: flex; gap: 1rem; align-items: center; font-size: 0.9rem; }
.groupe-badge { background: #10b981; color: white; padding: 2px 8px; border-radius: 4px; font-size: 0.8rem; font-weight: 600; }
.btn-logout { border: 1px solid #ef4444; background: white; color: #ef4444; cursor: pointer; font-weight: 500; padding: 4px 8px; border-radius: 4px; }
.btn-logout:hover { background: #ef4444; color: white; }

.container { max-width: 1000px; margin: 2rem auto; padding: 0 1rem; }

.page-header { margin-bottom: 2rem; }
.page-header h1 { margin: 0 0 0.5rem 0; font-size: 1.5rem; color: #1e293b; }
.page-header p { margin: 0; color: #64748b; }

.loading, .error-message, .empty-state { text-align: center; padding: 3rem; color: #64748b; }
.error-message { color: #ef4444; background: #fef2f2; border-radius: 8px; }

.students-grid { display: flex; flex-direction: column; gap: 1rem; }

.student-card {
    background: white;
    padding: 1.25rem;
    border-radius: 8px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.08);
    border: 1px solid #e2e8f0;
    display: grid;
    grid-template-columns: 1fr auto auto;
    gap: 1rem;
    align-items: center;
    cursor: pointer;
    transition: all 0.15s ease;
}
.student-card:hover {
    border-color: #6366f1;
    box-shadow: 0 4px 12px rgba(99, 102, 241, 0.15);
}

.student-info { }
.student-name { font-weight: 600; color: #1e293b; font-size: 1rem; margin-bottom: 2px; }
.student-class { color: #64748b; font-size: 0.85rem; }
.student-email { color: #94a3b8; font-size: 0.8rem; }

.student-copies { display: flex; flex-direction: column; gap: 4px; }
.copy-summary { display: flex; align-items: center; gap: 0.5rem; font-size: 0.85rem; }
.exam-name { color: #475569; font-weight: 500; min-width: 60px; }
.status-badge { padding: 2px 6px; border-radius: 4px; font-size: 0.7rem; font-weight: 600; text-transform: uppercase; }
.status-badge.graded { background: #dcfce7; color: #166534; }
.status-badge.ready { background: #dbeafe; color: #1d4ed8; }
.status-badge.staging { background: #f1f5f9; color: #64748b; }
.score { font-weight: 700; color: #0f172a; min-width: 50px; text-align: right; }
.score.pending { color: #94a3b8; }

.action-arrow { color: #94a3b8; font-size: 1.2rem; }
.student-card:hover .action-arrow { color: #6366f1; }
</style>
