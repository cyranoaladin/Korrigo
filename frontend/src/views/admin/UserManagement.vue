<script setup>
import { ref, onMounted, computed, watch } from 'vue'
import api from '../../services/api'

const activeTab = ref('students') // 'students', 'teachers', 'admins'
const items = ref([])
const loading = ref(true)
const searchQuery = ref('')

const fetchItems = async () => {
    loading.value = true
    items.value = []
    try {
        if (activeTab.value === 'students') {
            const res = await api.get('/students/')
            items.value = res.data
        } else if (activeTab.value === 'teachers') {
            const res = await api.get('/users/', { params: { role: 'Teacher' } })
            items.value = res.data
        } else if (activeTab.value === 'admins') {
            const res = await api.get('/users/', { params: { role: 'Admin' } })
            items.value = res.data
        }
    } catch (e) {
        console.error("Failed to fetch items", e)
    } finally {
        loading.value = false
    }
}

// Re-fetch when tab changes
watch(activeTab, () => {
    searchQuery.value = ''
    fetchItems()
})

const filteredItems = computed(() => {
    if (!searchQuery.value) return items.value
    const lower = searchQuery.value.toLowerCase()
    
    return items.value.filter(item => {
        if (activeTab.value === 'students') {
            return (item.last_name?.toLowerCase() || '').includes(lower) || 
                   (item.first_name?.toLowerCase() || '').includes(lower) || 
                   (item.ine?.toLowerCase() || '').includes(lower)
        } else {
            return (item.username?.toLowerCase() || '').includes(lower) || 
                   (item.email?.toLowerCase() || '').includes(lower) ||
                   (item.last_name?.toLowerCase() || '').includes(lower)
        }
    })
})

onMounted(() => {
    fetchItems()
})

const fileInput = ref(null)
const importing = ref(false)

const handleImport = async (event) => {
    const file = event.target.files[0]
    if (!file) return
    
    importing.value = true
    const formData = new FormData()
    formData.append('file', file)
    
    try {
        const res = await api.post('/students/import/', formData, {
            headers: { 'Content-Type': 'multipart/form-data' }
        })
        alert(`Import terminé ! Créés: ${res.data.created}`)
        if (activeTab.value === 'students') await fetchItems()
    } catch (e) {
        console.error("Import failed", e)
        alert("Erreur import: " + (e.response?.data?.error || e.message))
    } finally {
        importing.value = false
        if (event.target) event.target.value = ''
    }
}

// User Creation / Edit Logic
const showModal = ref(false)
const modalMode = ref('create') // 'create' | 'edit'
const selectedUserId = ref(null)
const newUser = ref({ username: '', email: '', password: '', role: 'Teacher', is_active: true })

const openCreateModal = () => {
    modalMode.value = 'create'
    selectedUserId.value = null
    newUser.value = { 
        username: '', 
        email: '', 
        password: '', 
        role: activeTab.value === 'admins' ? 'Admin' : 'Teacher',
        is_active: true
    }
    showModal.value = true
}

const openEditModal = (user) => {
    modalMode.value = 'edit'
    selectedUserId.value = user.id
    newUser.value = {
        username: user.username,
        email: user.email,
        password: '', // Leave empty to keep unchanged
        role: activeTab.value === 'admins' ? 'Admin' : 'Teacher',
        is_active: user.is_active
    }
    showModal.value = true
}

const saveUser = async () => {
    if (modalMode.value === 'create' && (!newUser.value.username || !newUser.value.password)) {
        alert("Nom d'utilisateur et mot de passe requis")
        return
    }
    
    try {
        if (modalMode.value === 'create') {
            await api.post('/users/', newUser.value)
            alert("Utilisateur créé avec succès")
        } else {
             await api.put(`/users/${selectedUserId.value}/`, newUser.value)
             alert("Utilisateur modifié avec succès")
        }
        showModal.value = false
        fetchItems()
    } catch (e) {
        console.error("Save failed", e)
        alert("Erreur: " + (e.response?.data?.error || e.message))
    }
}

const deleteUser = async (user) => {
    if (!confirm(`Voulez-vous vraiment supprimer ${user.username} ?`)) return
    
    try {
        await api.delete(`/users/${user.id}/`)
        alert("Utilisateur supprimé")
        fetchItems()
    } catch (e) {
        console.error("Delete failed", e)
        alert("Erreur suppression: " + (e.response?.data?.error || e.message))
    }
}

</script>

<template>
  <div class="user-management">
    <header class="page-header">
      <h2>Gestion des Utilisateurs</h2>
      <div class="actions">
        <input 
          v-model="searchQuery" 
          type="text" 
          :placeholder="activeTab === 'students' ? 'Rechercher un élève...' : 'Rechercher un utilisateur...'" 
          class="search-input"
        >
        
    <div v-if="activeTab === 'students'">
      <input 
        ref="fileInput"
        type="file"
        accept=".csv,.xml"
        style="display:none"
        @change="handleImport"
      >
      <button
        class="btn btn-primary"
        :disabled="importing"
        @click="$refs.fileInput.click()"
      >
        {{ importing ? 'Import...' : 'Import CSV/XML' }}
      </button>
    </div>
        
    <div v-else>
      <button
        class="btn btn-primary"
        @click="openCreateModal"
      >
        + Ajouter {{ activeTab === 'admins' ? 'Administrateur' : 'Enseignant' }}
      </button>
    </div>
  </div>
</header>

<div class="tabs">
  <button 
    class="tab" 
    :class="{ active: activeTab === 'students' }"
    @click="activeTab = 'students'"
  >
    Élèves
  </button>
  <button
    class="tab"
    :class="{ active: activeTab === 'teachers' }"
    @click="activeTab = 'teachers'"
  >
    Enseignants
  </button>
  <button
    class="tab"
    :class="{ active: activeTab === 'admins' }"
    @click="activeTab = 'admins'"
  >
    Administrateurs
  </button>
</div>

<div
  v-if="loading"
  class="loading"
>
  Chargement...
</div>

<table
  v-else
  class="data-table"
>
  <thead>
    <tr v-if="activeTab === 'students'">
      <th>INE</th>
      <th>Nom</th>
      <th>Prénom</th>
      <th>Classe</th>
      <th>Actions</th>
    </tr>
    <tr v-else>
      <th>Utilisateur</th>
      <th>Email</th>
      <th>Statut</th>
      <th>Dernière Connexion</th>
      <th>Actions</th>
    </tr>
  </thead>
  <tbody>
    <tr
      v-for="item in filteredItems"
      :key="item.id"
    >
      <!-- Student Row -->
      <template v-if="activeTab === 'students'">
        <td>{{ item.ine }}</td>
        <td class="font-bold">
          {{ item.last_name }}
        </td>
        <td>{{ item.first_name }}</td>
        <td>{{ item.class_name }}</td>
        <td>
          <button
            class="btn-sm btn-outline"
            @click="alert('Détails élève #' + item.id)"
          >
            Voir
          </button>
        </td>
      </template>

      <!-- User Row -->
      <template v-else>
        <td class="font-bold">
          {{ item.username }}
        </td>
        <td>{{ item.email || '-' }}</td>
        <td>
          <span :class="item.is_active ? 'status-active' : 'status-inactive'">
            {{ item.is_active ? 'Actif' : 'Inactif' }}
          </span>
        </td>
        <td>{{ item.last_login ? new Date(item.last_login).toLocaleDateString() : 'Jamais' }}</td>
        <td>
          <div class="btn-group">
            <button
              class="btn-sm btn-outline"
              @click="openEditModal(item)"
            >
              Éditer
            </button>
            <button
              class="btn-sm btn-danger"
              @click="deleteUser(item)"
            >
              Supprimer
            </button>
          </div>
        </td>
      </template>
    </tr>
    <tr v-if="filteredItems.length === 0">
      <td
        colspan="5"
        class="empty-cell"
      >
        Aucun résultat trouvé.
      </td>
    </tr>
  </tbody>
</table>

<!-- Generic Modal for User Creation / Edit -->
<div 
  v-if="showModal" 
  class="modal-overlay"
>
  <div class="modal-card">
    <h3>{{ modalMode === 'create' ? 'Ajouter' : 'Modifier' }} un {{ newUser.role === 'Admin' ? 'Administrateur' : 'Enseignant' }}</h3>
    
    <div 
      v-if="modalMode === 'create'" 
      class="form-group"
    >
      <label>Identifiant (Login)</label>
      <input 
        v-model="newUser.username" 
        type="text" 
        placeholder="ex: jdupont" 
        class="form-input" 
      >
    </div>
    
    <div class="form-group">
      <label>Email (Optionnel)</label>
      <input 
        v-model="newUser.email" 
        type="email" 
        placeholder="email@exemple.com" 
        class="form-input" 
      >
    </div>
    
      <div 
        v-if="modalMode === 'edit'" 
        class="form-group"
      >
      <label>Statut</label>
      <label class="checkbox-label">
        <input 
          v-model="newUser.is_active" 
          type="checkbox"
        > 
        Compte Actif
      </label>
    </div>
    
    <div class="form-group">
      <label>Mot de passe {{ modalMode === 'edit' ? '(Laisser vide pour ne pas changer)' : '' }}</label>
      <input 
        v-model="newUser.password" 
        type="password" 
        placeholder="********" 
        class="form-input" 
      >
    </div>
    
    <div class="modal-actions">
      <button 
        class="btn btn-outline"
        @click="showModal = false"
      >
        Annuler
      </button>
      <button 
        class="btn btn-primary"
        @click="saveUser"
      >
        {{ modalMode === 'create' ? 'Créer' : 'Sauvegarder' }}
      </button>
    </div>
  </div>
</div>
</div>
</template>

<style scoped>
.user-management { padding: 2rem; max-width: 1200px; margin: 0 auto; font-family: 'Inter', sans-serif; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 2rem; }
.search-input { padding: 8px 12px; border: 1px solid #cbd5e1; border-radius: 6px; width: 300px; }
.tabs { display: flex; gap: 1rem; margin-bottom: 1rem; border-bottom: 1px solid #e2e8f0; }
.tab { padding: 0.75rem 1.5rem; background: none; border: none; border-bottom: 2px solid transparent; cursor: pointer; color: #64748b; font-weight: 500; }
.tab.active { border-bottom-color: #3b82f6; color: #3b82f6; }
.tab:disabled { cursor: not-allowed; opacity: 0.5; }

.data-table { width: 100%; border-collapse: collapse; background: white; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
.data-table th, .data-table td { padding: 1rem; text-align: left; border-bottom: 1px solid #f1f5f9; }
.data-table th { background: #f8fafc; color: #475569; font-weight: 600; }
.data-table tr:hover { background: #f8fafc; }
.font-bold { font-weight: 600; color: #1e293b; }
.loading, .empty-cell { text-align: center; padding: 3rem; color: #94a3b8; }
.btn { padding: 0.5rem 1rem; border-radius: 6px; border: none; cursor: pointer; font-weight: 500; }
.btn-primary { background: #3b82f6; color: white; }
.btn-danger { background: #ef4444; color: white; margin-left: 0.5rem; }
.btn-sm { padding: 4px 8px; font-size: 0.8rem; }
.btn-outline { background: white; border: 1px solid #cbd5e1; color: #475569; }
.btn-group { display: flex; gap: 0.5rem; }

/* Modal Styles */
.modal-overlay { position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.5); display: flex; justify-content: center; align-items: center; z-index: 1000; }
.modal-card { background: white; padding: 2rem; border-radius: 12px; width: 400px; box-shadow: 0 20px 25px -5px rgba(0,0,0,0.1); }
.modal-card h3 { margin-top: 0; margin-bottom: 1.5rem; color: #1e293b; }
.form-group { margin-bottom: 1rem; }
.form-group label { display: block; margin-bottom: 0.5rem; color: #475569; font-size: 0.9rem; }
.form-input { width: 100%; padding: 0.5rem; border: 1px solid #cbd5e1; border-radius: 4px; }
.modal-actions { display: flex; justify-content: flex-end; gap: 1rem; margin-top: 1.5rem; }
.checkbox-label { display: flex; align-items: center; gap: 0.5rem; cursor: pointer; }
</style>
