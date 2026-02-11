<script setup>
import { ref, onMounted } from 'vue'
import { useAuthStore } from '../../stores/auth'
import api from '../../services/api'
import { useRouter } from 'vue-router'

const auth = useAuthStore()
const router = useRouter()
const copies = ref([])
const selectedCopy = ref(null)
const loading = ref(true)

const fetchCopies = async () => {
    loading.value = true
    try {
        const res = await api.get('/students/copies/')
        copies.value = res.data
        if (copies.value.length > 0) {
            selectedCopy.value = copies.value[0]
        }
    } catch (e) {
        if (e.response?.status === 401) {
            router.push('/student/login')
        }
        console.error(e)
    } finally {
        loading.value = false
    }
}

const selectCopy = (copy) => {
    selectedCopy.value = copy
}

const logout = async () => {
    await auth.logout()
    router.push('/')
}

onMounted(() => {
    fetchCopies()
})
</script>

<template>
  <div
    class="result-view"
    data-testid="student-portal"
  >
    <header class="navbar">
      <div class="brand">
        Korrigo — Espace Élève <span
          v-if="auth.user"
          class="student-name"
        >| {{ auth.user.first_name }} {{ auth.user.last_name }}</span>
      </div>
      <button
        class="btn-logout"
        @click="logout"
      >
        Déconnexion
      </button>
    </header>
        
    <main class="content-split">
      <!-- Left: List -->
      <aside class="sidebar">
        <h3>Mes Copies</h3>
        <div
          v-if="loading"
          class="loading"
        >
          Chargement...
        </div>
        <div
          v-else-if="copies.length === 0"
          class="empty"
        >
          Aucune copie disponible.
        </div>
        <ul
          v-else
          class="copy-list"
        >
          <li 
            v-for="copy in copies" 
            :key="copy.id" 
            :class="{ active: selectedCopy?.id === copy.id }"
            @click="selectCopy(copy)"
          >
            <div class="copy-header">
              <span class="exam-name">{{ copy.exam_name }}</span>
              <span class="exam-date">{{ copy.date }}</span>
            </div>
            <div class="copy-score">
              Note: <span class="score-value">{{ copy.total_score.toFixed(2) }}</span> / 20
            </div>
          </li>
        </ul>
      </aside>
            
      <!-- Right: Details -->
      <section
        v-if="selectedCopy"
        class="details"
      >
        <div class="details-header">
          <h2>{{ selectedCopy.exam_name }}</h2>
          <a
            v-if="selectedCopy.final_pdf_url"
            :href="selectedCopy.final_pdf_url"
            download
            class="btn-download"
          >
            📥 Télécharger le PDF
          </a>
        </div>
                
        <div class="details-body">
          <!-- Tabs or Split vertical? Let's do TOP: Breakdown, BOTTOM: PDF -->
                    
          <div class="score-breakdown">
            <h4>Détail des notes</h4>
            <div class="tags">
              <span
                v-for="(val, key) in selectedCopy.scores_details"
                :key="key"
                class="tag"
              >
                {{ key }}: <b>{{ val }}</b>
              </span>
              <span
                v-if="Object.keys(selectedCopy.scores_details || {}).length === 0"
                class="no-scores"
              >
                Pas de détail disponible.
              </span>
            </div>
          </div>

          <!-- Remarks per question -->
          <div
            v-if="selectedCopy.remarks && Object.keys(selectedCopy.remarks).length > 0"
            class="remarks-section"
          >
            <h4>Remarques par question</h4>
            <div
              v-for="(remark, qid) in selectedCopy.remarks"
              :key="'remark-' + qid"
              class="remark-item"
            >
              <span class="remark-qid">{{ qid }}</span>
              <span class="remark-text">{{ remark }}</span>
            </div>
          </div>

          <!-- Global Appreciation -->
          <div
            v-if="selectedCopy.global_appreciation"
            class="appreciation-section"
          >
            <h4>Appréciation générale</h4>
            <p class="appreciation-text">
              {{ selectedCopy.global_appreciation }}
            </p>
          </div>
                    
          <div class="pdf-wrapper">
            <iframe 
              v-if="selectedCopy.final_pdf_url" 
              :src="selectedCopy.final_pdf_url" 
              width="100%" 
              height="100%"
            />
            <div
              v-else
              class="no-pdf"
            >
              PDF non disponible.
            </div>
          </div>
        </div>
      </section>
      <section
        v-else
        class="details empty-state"
      >
        <p>Sélectionnez une copie pour voir les détails.</p>
      </section>
    </main>
  </div>
</template>

<style scoped>
.result-view { height: 100vh; display: flex; flex-direction: column; font-family: 'Inter', sans-serif; background: #f3f4f6; }
.navbar { background: #667eea; color: white; padding: 1rem 2rem; display: flex; justify-content: space-between; align-items: center; }
.brand { font-weight: 700; font-size: 1.2rem; }
.student-name { font-weight: 400; font-size: 1rem; opacity: 0.9; }
.btn-logout { background: transparent; border: 1px solid white; color: white; padding: 0.5rem 1rem; border-radius: 4px; cursor: pointer; transition: all 0.2s; }
.btn-logout:hover { background: white; color: #667eea; }

.content-split { flex: 1; display: flex; overflow: hidden; }

.sidebar { width: 300px; background: white; border-right: 1px solid #e5e7eb; display: flex; flex-direction: column; overflow-y: auto; }
.sidebar h3 { padding: 1.5rem; margin: 0; border-bottom: 1px solid #e5e7eb; color: #374151; font-size: 1.1rem; }

.copy-list { list-style: none; padding: 0; margin: 0; }
.copy-list li { padding: 1.5rem; border-bottom: 1px solid #f3f4f6; cursor: pointer; transition: background 0.2s; }
.copy-list li:hover { background: #f9fafb; }
.copy-list li.active { background: #eef2ff; border-left: 4px solid #667eea; }

.copy-header { display: flex; justify-content: space-between; margin-bottom: 0.5rem; }
.exam-name { font-weight: 600; color: #1f2937; }
.exam-date { font-size: 0.8rem; color: #9ca3af; }
.copy-score { font-size: 0.9rem; color: #4b5563; }
.score-value { font-weight: 700; color: #667eea; }

.details { flex: 1; display: flex; flex-direction: column; padding: 1.5rem; overflow: hidden; }
.details-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.5rem; }
.details-header h2 { margin: 0; color: #111827; }

.btn-download { background: #10b981; color: white; padding: 0.75rem 1.5rem; border-radius: 6px; text-decoration: none; font-weight: 600; box-shadow: 0 4px 6px -1px rgba(16, 185, 129, 0.2); }
.btn-download:hover { background: #059669; }

.details-body { flex: 1; display: flex; flex-direction: column; gap: 1rem; overflow: hidden; }
.score-breakdown { background: white; padding: 1rem; border-radius: 8px; box-shadow: 0 1px 2px rgba(0,0,0,0.05); }
.score-breakdown h4 { margin: 0 0 0.5rem 0; font-size: 0.9rem; color: #6b7280; text-transform: uppercase; letter-spacing: 0.05em; }
.tags { display: flex; flex-wrap: wrap; gap: 0.5rem; }
.tag { background: #f3f4f6; padding: 0.25rem 0.5rem; border-radius: 4px; font-size: 0.85rem; color: #374151; border: 1px solid #e5e7eb; }

.no-scores { color: #9ca3af; font-style: italic; }

.remarks-section { background: white; padding: 1rem; border-radius: 8px; box-shadow: 0 1px 2px rgba(0,0,0,0.05); }
.remarks-section h4 { margin: 0 0 0.5rem 0; font-size: 0.9rem; color: #6b7280; text-transform: uppercase; letter-spacing: 0.05em; }
.remark-item { display: flex; gap: 0.5rem; padding: 0.4rem 0; border-bottom: 1px solid #f3f4f6; }
.remark-qid { font-weight: 600; color: #667eea; min-width: 60px; }
.remark-text { color: #374151; }

.appreciation-section { background: #fef3c7; padding: 1rem; border-radius: 8px; border: 1px solid #fde68a; }
.appreciation-section h4 { margin: 0 0 0.5rem 0; font-size: 0.9rem; color: #92400e; text-transform: uppercase; letter-spacing: 0.05em; }
.appreciation-text { color: #78350f; line-height: 1.6; margin: 0; }

.pdf-wrapper { flex: 1; background: #e5e7eb; border-radius: 8px; overflow: hidden; position: relative; }
.no-pdf { position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); color: #6b7280; font-weight: 500; }
.empty-state { align-items: center; justify-content: center; color: #9ca3af; font-size: 1.2rem; }
</style>
