<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const authStore = useAuthStore()
const router = useRouter()
const exams = ref([])
const loading = ref(true)

const fetchExams = async () => {
    loading.value = true
    try {
        const res = await fetch(`${authStore.API_URL}/api/exams/`, {
            headers: authStore.authHeaders
        })
        if (res.ok) {
            exams.value = await res.json()
        }
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
        const res = await fetch(`${authStore.API_URL}/api/exams/upload/`, {
            method: 'POST',
            headers: {
                // Determine Authorization header but do NOT set Content-Type (browser does it for FormData)
                'Authorization': authStore.authHeaders.Authorization
            },
            body: formData
        })
        
        if (res.ok) {
            alert('Examen importé avec succès !')
            await fetchExams()
        } else {
            const err = await res.json()
            alert('Erreur: ' + JSON.stringify(err))
        }
    } catch (e) {
        console.error("Upload failed", e)
        alert('Erreur technique')
    }
}

onMounted(() => {
    fetchExams()
})
</script>

<template>
    <div class="admin-dashboard">
        <nav class="sidebar">
            <div class="logo">OpenViatique Admin</div>
            <ul class="nav-links">
                <li class="active">Gestion Examens</li>
                <li>Utilisateurs</li>
                <li>Paramètres</li>
            </ul>
            <button @click="handleLogout" class="logout-btn">Déconnexion</button>
        </nav>
        
        <main class="content">
            <header>
                <h1>Tableau de Bord Administrateur</h1>
                <div class="user-info">{{ authStore.user?.username }} (Admin)</div>
            </header>
            
            <section class="exam-management">
                <div class="actions-bar">
                    <button class="btn btn-primary">+ Nouvel Examen</button>
                    <button class="btn btn-outline" @click="triggerUpload">Importer Scans</button>
                    <input 
                        type="file" 
                        ref="fileInput" 
                        style="display: none" 
                        accept="application/pdf"
                        @change="uploadExam"
                    >
                </div>
                
                <div v-if="loading" class="loading">Chargement des examens...</div>
                
                <table v-else class="data-table">
                    <thead>
                        <tr>
                            <th>Nom</th>
                            <th>Date</th>
                            <th>État</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr v-for="exam in exams" :key="exam.id">
                            <td>{{ exam.name }}</td>
                            <td>{{ exam.date }}</td>
                            <td>
                                <span v-if="exam.is_processed" class="badge status-import">Importé</span>
                                <span v-else class="badge status-pending">En création</span>
                            </td>
                            <td>
                                <button class="btn-sm" @click="alert('Fonctionnalité Agrafer en cours de développement')">Agrafer</button>
                                <button class="btn-sm" @click="alert('Éditeur de Barème bientôt disponible')">Barème</button>
                                <button 
                                    class="btn-sm btn-action" 
                                    @click="goToIdentification(exam.id)"
                                >
                                    Video-Coding
                                </button>
                            </td>
                        </tr>
                        <tr v-if="exams.length === 0">
                            <td colspan="4" class="empty-cell">Aucun examen trouvé. Créez-en un ou importez des scans.</td>
                        </tr>
                    </tbody>
                </table>
            </section>
        </main>
    </div>
</template>

<style scoped>
.btn-action { background: #8b5cf6; color: white; }
.btn-action:hover { background: #7c3aed; }
.loading { padding: 2rem; text-align: center; color: #6b7280; }
.empty-cell { padding: 3rem; text-align: center; color: #9ca3af; font-style: italic; }
.admin-dashboard { display: flex; height: 100vh; font-family: 'Inter', sans-serif; }
.sidebar { width: 250px; background: #1e293b; color: white; padding: 1.5rem; display: flex; flex-direction: column; }
.logo { font-size: 1.25rem; font-weight: 700; margin-bottom: 2rem; color: #60a5fa; }
.nav-links { list-style: none; padding: 0; flex: 1; }
.nav-links li { padding: 0.75rem 1rem; cursor: pointer; border-radius: 6px; margin-bottom: 0.5rem; color: #94a3b8; }
.nav-links li.active, .nav-links li:hover { background: #334155; color: white; }
.logout-btn { margin-top: auto; background: none; border: 1px solid #ef4444; color: #ef4444; padding: 0.5rem; border-radius: 6px; cursor: pointer; }
.logout-btn:hover { background: #ef4444; color: white; }

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
</style>
