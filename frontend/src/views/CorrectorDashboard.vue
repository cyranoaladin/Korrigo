<script setup>
import { ref, onMounted } from 'vue'
import { useAuthStore } from '../stores/auth'
import { useRouter } from 'vue-router'
import gradingApi from '../services/gradingApi'

const authStore = useAuthStore()
const router = useRouter()

const copies = ref([])
const isLoading = ref(true)
const stats = ref({ total: 0, graded: 0, todo: 0 })

const fetchCopies = async () => {
    isLoading.value = true
    try {
        const data = await gradingApi.listCopies()
        copies.value = data
        stats.value.total = data.length
        stats.value.graded = data.filter(c => c.status === 'GRADED').length
        stats.value.todo = data.filter(c => ['READY', 'LOCKED'].includes(c.status)).length
    } catch (err) {
        console.error("Failed to fetch copies", err)
    } finally {
        isLoading.value = false
    }
}

onMounted(fetchCopies)

const handleLogout = async () => {
    await authStore.logout()
    router.push('/login')
}

const handleChangePassword = () => {
    alert("Fonctionnalité bientôt disponible. Veuillez contacter l'administrateur.")
}
const goToDesk = (copyId) => {
    router.push(`/corrector/desk/${copyId}`)
}
</script>

<template>
  <div class="corrector-dashboard">
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
            {{ stats.total }}
          </div>
        </div>
        <div class="card stat">
          <h3>Corrigées</h3>
          <div class="value success">
            {{ stats.graded }}
          </div>
        </div>
        <div class="card stat">
          <h3>Reste à faire</h3>
          <div class="value warning">
            {{ stats.todo }}
          </div>
        </div>
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
              {{ copy.status }}
            </div>
            <button 
              class="btn-action"
              data-testid="copy-action"
              @click="goToDesk(copy.id)"
            >
              {{ copy.status === 'GRADED' ? 'Voir' : (copy.status === 'LOCKED' ? 'Continuer' : 'Corriger') }}
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
.btn-logout { border: 1px solid #ef4444; background: white; color: #ef4444; cursor: pointer; font-weight: 500; padding: 4px 8px; border-radius: 4px; }
.btn-logout:hover { background: #ef4444; color: white; }

.container { max-width: 800px; margin: 2rem auto; padding: 0 1rem; }

.stats-overview { display: grid; grid-template-columns: repeat(3, 1fr); gap: 1rem; margin-bottom: 2rem; }
.card { background: white; padding: 1.5rem; border-radius: 8px; box-shadow: 0 1px 2px rgba(0,0,0,0.05); text-align: center; }
.stat h3 { margin: 0 0 0.5rem 0; font-size: 0.875rem; color: #64748b; font-weight: 500; }
.stat .value { font-size: 2rem; font-weight: 700; color: #0f172a; }
.value.success { color: #10b981; }
.value.warning { color: #f59e0b; }

.task-list h2 { font-size: 1.25rem; color: #1e293b; margin-bottom: 1rem; }
.copy-card { background: white; padding: 1rem; border-radius: 8px; margin-bottom: 1rem; display: flex; justify-content: space-between; align-items: center; box-shadow: 0 1px 2px rgba(0,0,0,0.05); border: 1px solid #e2e8f0; }
.exam-name { font-weight: 600; color: #334155; }
.copy-id { font-size: 0.875rem; color: #64748b; }
.copy-status { font-size: 0.75rem; font-weight: 600; text-transform: uppercase; padding: 2px 6px; border-radius: 4px; }
.copy-status.pending { background: #fee2e2; color: #ef4444; }
.copy-status.done { background: #dcfce7; color: #166534; }

.btn-action { padding: 0.5rem 1rem; background: #2563eb; color: white; border: none; border-radius: 6px; cursor: pointer; font-weight: 500; }
.btn-action.secondary { background: #f1f5f9; color: #475569; }
</style>
