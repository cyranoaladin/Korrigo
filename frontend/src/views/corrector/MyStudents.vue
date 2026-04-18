<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../../stores/auth'
import { useExamStore } from '../../stores/exam'
import api from '../../services/api'
import AppIcon from '../../icons/AppIcon.vue'

const router = useRouter()
const authStore = useAuthStore()
const examStore = useExamStore()

const students = ref([])
const groupe = ref('')
const isLoading = ref(true)
const error = ref(null)
const examName = ref('')

// Restore exam selection from storage on mount
examStore.restoreFromStorage()

const currentExamId = computed(() => examStore.currentExamId)
const currentExamTypeId = computed(() => examStore.currentExamTypeId)

const fetchStudents = async () => {
    isLoading.value = true
    error.value = null
    try {
        // Priorité au filtrage strict par exam_id (sélection depuis un
        // exam-group). Fallback sur exam_type_id (sélection globale du type).
        const params = {}
        if (currentExamId.value) {
            params.exam_id = currentExamId.value
        } else if (currentExamTypeId.value) {
            params.exam_type_id = currentExamTypeId.value
        }

        const response = await api.get('/grading/my-students/', { params })

        // Si filtrage par examen actif → format avec exam_name + students filtrés FINALIZED
        if (response.data.filter === 'finalized_only') {
            students.value = response.data.students || []
            examName.value = response.data.exam_name || ''
            groupe.value = ''
        } else {
            // Mode legacy : tous les élèves, toutes copies
            students.value = response.data.students || []
            groupe.value = response.data.groupe || ''
            examName.value = ''
        }
    } catch (err) {
        console.error('Failed to fetch students', err)
        error.value = err.response?.data?.error || err.response?.data?.detail || 'Erreur lors du chargement des élèves.'
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
    router.push('/')
}

const getStatusClass = (status) => {
    return status?.toLowerCase() || 'unknown'
}

const getStatusLabel = (status) => {
    const labels = {
        'READY': 'Prêt',
        'IN_PROGRESS': 'En cours',
        'FINALIZED': 'Finalisée',
    }
    return labels[status] || status
}

onMounted(fetchStudents)
</script>

<template>
  <div class="my-students-page">
    <header class="top-nav">
      <div class="brand">
        <button class="btn-back" @click="goBack"><AppIcon name="arrow-left" :size="14" class="inline" /> Retour</button>
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
        <h1><AppIcon name="users" :size="24" class="inline" /> Mes Élèves</h1>
        <p v-if="examName">
          <strong>{{ examName }}</strong> — {{ students.length }} élève(s) avec copie finalisée
        </p>
        <p v-else-if="groupe">Groupe <strong>{{ groupe }}</strong> — {{ students.length }} élève(s)</p>
      </div>

      <div v-if="isLoading" class="loading">
        Chargement des élèves...
      </div>

      <div v-else-if="error" class="error-message">
        {{ error }}
      </div>

      <div v-else-if="students.length === 0" class="empty-state">
        <template v-if="examName">
          <div style="font-size: 1.1rem; margin-bottom: 8px;">
            <strong>Aucune copie finalisée dans {{ examName }}</strong>
          </div>
          <div style="color: #64748b;">
            La liste de vos élèves apparaîtra ici au fur et à mesure que vous finaliserez leurs copies.
          </div>
        </template>
        <template v-else>
          Aucun élève trouvé dans votre groupe.
        </template>
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
            <div class="student-meta">
              <span class="class-tag">{{ student.class_name }}</span>
              <span v-if="student.groupe" class="dot-separator">•</span>
              <span v-if="student.groupe" class="groupe-tag">{{ student.groupe }}</span>
            </div>
            <div v-if="student.email" class="student-email">
              <AppIcon name="mail" :size="12" class="inline" /> {{ student.email }}
            </div>
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
              <div class="score">
                <template v-if="copy.total_score !== null">
                  {{ copy.total_score.toFixed(2) }}<span class="max">/20</span>
                </template>
                <span v-else class="score pending">—</span>
              </div>
              <span v-if="copy.corrector_name" class="corrector-info" :title="'Corrigé par ' + copy.corrector_name">
                <AppIcon name="user" :size="12" />
              </span>
            </div>
          </div>
          <div class="action-arrow">
            <AppIcon name="chevron-right" :size="20" />
          </div>
        </div>
      </div>
    </main>
  </div>
</template>

<style scoped>
.my-students-page { background: #f8fafc; min-height: 100vh; font-family: 'Inter', sans-serif; }

.top-nav { background: white; padding: 1rem 2rem; display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #e2e8f0; position: sticky; top: 0; z-index: 100; }
.brand { font-weight: 700; color: #0f172a; font-size: 1.1rem; display: flex; align-items: center; gap: 1rem; }
.btn-back { background: none; border: none; color: #6366f1; cursor: pointer; font-size: 0.9rem; font-weight: 600; display: flex; align-items: center; gap: 6px; padding: 6px 12px; border-radius: 6px; transition: background 0.2s; }
.btn-back:hover { background: #eef2ff; }
.user-menu { display: flex; gap: 1rem; align-items: center; font-size: 0.9rem; }
.groupe-badge { background: #10b981; color: white; padding: 2px 10px; border-radius: 12px; font-size: 0.8rem; font-weight: 600; }
.btn-logout { border: 1px solid #ef4444; background: white; color: #ef4444; cursor: pointer; font-weight: 500; padding: 4px 12px; border-radius: 6px; transition: all 0.2s; }
.btn-logout:hover { background: #ef4444; color: white; }

.container { max-width: 1000px; margin: 2rem auto; padding: 0 1.5rem; }

.page-header { margin-bottom: 2.5rem; }
.page-header h1 { margin: 0 0 0.5rem 0; font-size: 2rem; color: #0f172a; font-weight: 800; letter-spacing: -0.025em; }
.page-header p { margin: 0; color: #64748b; font-size: 1.1rem; }
.highlight { color: #6366f1; font-weight: 600; }

.loading, .error-message, .empty-state { text-align: center; padding: 5rem 2rem; color: #64748b; background: white; border-radius: 12px; border: 1px solid #e2e8f0; }
.error-message { color: #ef4444; background: #fef2f2; border-color: #fee2e2; }

.students-grid { display: flex; flex-direction: column; gap: 1.25rem; }

.student-card {
    background: white;
    padding: 1.5rem;
    border-radius: 12px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    border: 1px solid #e2e8f0;
    display: grid;
    grid-template-columns: 1fr auto auto;
    gap: 2rem;
    align-items: center;
    cursor: pointer;
    transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
}
.student-card:hover {
    border-color: #6366f1;
    box-shadow: 0 10px 25px rgba(99, 102, 241, 0.1);
    transform: translateY(-2px);
}

.student-info { display: flex; flex-direction: column; gap: 4px; }
.student-name { font-weight: 700; color: #0f172a; font-size: 1.15rem; }
.student-meta { display: flex; align-items: center; gap: 8px; color: #64748b; font-size: 0.9rem; }
.dot-separator { color: #cbd5e1; }

.student-copies { display: flex; flex-direction: column; gap: 8px; min-width: 250px; }
.copy-summary { 
    display: flex; align-items: center; gap: 0.75rem; font-size: 0.9rem; 
    background: #f8fafc; padding: 6px 12px; border-radius: 8px; border: 1px solid #f1f5f9;
}
.exam-name { color: #334155; font-weight: 600; flex: 1; }
.status-badge { padding: 2px 8px; border-radius: 6px; font-size: 0.7rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.025em; }
.status-badge.finalized { background: #dcfce7; color: #166534; }
.status-badge.ready { background: #dbeafe; color: #1d4ed8; }
.status-badge.in_progress { background: #fef3c7; color: #92400e; }

.score { font-weight: 800; color: #0f172a; font-size: 1.1rem; min-width: 60px; text-align: right; }
.score .max { font-size: 0.75rem; color: #94a3b8; font-weight: 500; }
.score.pending { color: #cbd5e1; font-weight: 500; }

.corrector-info { 
    display: flex; align-items: center; gap: 4px; color: #6366f1; 
    font-size: 0.75rem; font-weight: 600; background: #eef2ff; 
    padding: 2px 8px; border-radius: 6px; white-space: nowrap;
}

.action-arrow { 
    color: #cbd5e1; width: 32px; height: 32px; display: flex; 
    align-items: center; justify-content: center; border-radius: 50%; 
    background: #f8fafc; transition: all 0.2s;
}
.student-card:hover .action-arrow { color: #6366f1; background: #eef2ff; transform: translateX(4px); }
</style>
