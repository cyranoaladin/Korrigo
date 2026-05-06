<template>
  <div class="p-6">
    <div class="mb-6">
      <h1 class="text-2xl font-bold text-gray-900 mb-2">Bilans Pédagogiques DNB</h1>
      <p class="text-gray-600">Générez et consultez les bilans pédagogiques du DNB 2026</p>
    </div>

    <!-- Actions -->
    <div class="mb-6 flex flex-wrap gap-4">
      <button
        @click="showGenerateModal = true"
        :disabled="isGenerating"
        class="inline-flex items-center gap-2 bg-primary-700 text-white px-4 py-2 rounded-lg hover:bg-primary-800 transition-colors font-medium disabled:opacity-50 disabled:cursor-not-allowed"
      >
        <AppIcon name="plus" :size="16" />
        Générer un bilan
      </button>
      
      <button
        @click="refreshList"
        :disabled="isLoading"
        class="inline-flex items-center gap-2 bg-gray-100 text-gray-700 px-4 py-2 rounded-lg hover:bg-gray-200 transition-colors font-medium disabled:opacity-50"
      >
        <AppIcon name="refresh" :size="16" />
        Actualiser
      </button>
    </div>

    <!-- Loading -->
    <div v-if="isLoading" class="text-center py-8">
      <div class="inline-flex items-center gap-2 text-gray-600">
        <div class="animate-spin rounded-full h-5 w-5 border-b-2 border-primary-600"></div>
        Chargement des bilans...
      </div>
    </div>

    <!-- Bilans List -->
    <div v-else-if="bilans.length > 0" class="space-y-4">
      <div
        v-for="bilan in bilans"
        :key="bilan.id"
        class="bg-white border border-gray-200 rounded-lg p-6 hover:shadow-md transition-shadow"
      >
        <div class="flex items-start justify-between">
          <div class="flex-1">
            <div class="flex items-center gap-3 mb-2">
              <h3 class="text-lg font-semibold text-gray-900">
                Bilan DNB 2026
              </h3>
              <span
                :class="getStatusClass(bilan.status)"
                class="px-2 py-1 text-xs font-medium rounded-full"
              >
                {{ getStatusText(bilan.status) }}
              </span>
            </div>
            
            <div class="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm text-gray-600 mb-3">
              <div>
                <span class="font-medium">Généré le :</span>
                {{ formatDate(bilan.generated_at) }}
              </div>
              <div>
                <span class="font-medium">Copies analysées :</span>
                {{ bilan.n_copies ?? 'N/A' }}
              </div>
              <div>
                <span class="font-medium">Par :</span>
                {{ bilan.generated_by || 'N/A' }}
              </div>
            </div>

            <!-- Progress for generating bilans -->
            <div v-if="bilan.status === 'GENERATING'" class="mb-4">
              <div class="flex items-center gap-2 text-sm text-gray-600 mb-1">
                <AppIcon name="clock" :size="14" />
                Génération en cours...
              </div>
              <div class="w-full bg-gray-200 rounded-full h-2">
                <div class="bg-primary-600 h-2 rounded-full animate-pulse" style="width: 60%"></div>
              </div>
            </div>

            <!-- Error display -->
            <div v-else-if="bilan.status === 'ERROR'" class="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg">
              <div class="flex items-start gap-2">
                <AppIcon name="alert-triangle" :size="16" class="text-red-500 mt-0.5" />
                <div>
                  <p class="text-sm font-medium text-red-800">Erreur de génération</p>
                  <p class="text-xs text-red-600 mt-1">{{ bilan.error_message || 'Erreur inconnue' }}</p>
                </div>
              </div>
            </div>
          </div>

          <!-- Actions -->
          <div class="flex flex-col gap-2 ml-4">
            <button
              v-if="bilan.status === 'DONE'"
              @click="viewBilan(bilan)"
              class="inline-flex items-center gap-2 bg-blue-600 text-white px-3 py-1.5 rounded-lg hover:bg-blue-700 transition-colors text-sm font-medium"
            >
              <AppIcon name="eye" :size="14" />
              Consulter
            </button>
            
            <button
              v-if="bilan.status === 'DONE' && bilan.pdf_available"
              @click="downloadPDF(bilan)"
              class="inline-flex items-center gap-2 bg-green-600 text-white px-3 py-1.5 rounded-lg hover:bg-green-700 transition-colors text-sm font-medium"
            >
              <AppIcon name="download" :size="14" />
              PDF
            </button>
            
            <button
              v-if="canDelete(bilan)"
              @click="deleteBilan(bilan)"
              class="inline-flex items-center gap-2 bg-red-600 text-white px-3 py-1.5 rounded-lg hover:bg-red-700 transition-colors text-sm font-medium"
            >
              <AppIcon name="trash" :size="14" />
              Supprimer
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Empty state -->
    <div v-else class="text-center py-12">
      <div class="inline-flex items-center justify-center w-16 h-16 bg-gray-100 rounded-full mb-4">
        <AppIcon name="file-text" :size="32" class="text-gray-400" />
      </div>
      <h3 class="text-lg font-medium text-gray-900 mb-2">Aucun bilan disponible</h3>
      <p class="text-gray-600 mb-4">Générez votre premier bilan pédagogique DNB</p>
      <button
        @click="showGenerateModal = true"
        class="inline-flex items-center gap-2 bg-primary-700 text-white px-4 py-2 rounded-lg hover:bg-primary-800 transition-colors font-medium"
      >
        <AppIcon name="plus" :size="16" />
        Générer un bilan
      </button>
    </div>

    <!-- Generate Modal -->
    <div
      v-if="showGenerateModal"
      class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
      @click.self="showGenerateModal = false"
    >
      <div class="bg-white rounded-xl p-6 w-full max-w-md mx-4">
        <h3 class="text-lg font-semibold text-gray-900 mb-4">Générer un bilan DNB</h3>
        
        <div class="space-y-4">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">
              Type d'examen
            </label>
            <select
              v-model="generateForm.exam_type"
              class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
            >
              <option value="DNB_2026">DNB 2026 - Mathématiques</option>
            </select>
          </div>

          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">
              Périmètre
            </label>
            <select
              v-model="generateForm.scope"
              class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
            >
              <option value="ETABLISSEMENT">Établissement complet</option>
              <option value="CLASSE">Par classe</option>
            </select>
          </div>

          <div v-if="generateForm.scope === 'CLASSE'">
            <label class="block text-sm font-medium text-gray-700 mb-1">
              Classe
            </label>
            <select
              v-model="generateForm.class_id"
              class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
            >
              <option value="">Sélectionner une classe</option>
              <option value="3A">3ème A</option>
              <option value="3B">3ème B</option>
              <option value="3C">3ème C</option>
            </select>
          </div>
        </div>

        <div class="flex justify-end gap-3 mt-6">
          <button
            @click="showGenerateModal = false"
            class="px-4 py-2 text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors font-medium"
          >
            Annuler
          </button>
          <button
            @click="generateBilan"
            :disabled="!canGenerate || isGenerating"
            class="px-4 py-2 bg-primary-700 text-white rounded-lg hover:bg-primary-800 transition-colors font-medium disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <span v-if="isGenerating" class="flex items-center gap-2">
              <div class="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
              Génération...
            </span>
            <span v-else>Générer</span>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../../stores/auth'
import AppIcon from '../../icons/AppIcon.vue'
import { useToast } from '../../composables/useToast'
import { bilanService } from '../../services/bilan'

const router = useRouter()
const authStore = useAuthStore()
const toast = useToast()

const bilans = ref([])
const isLoading = ref(false)
const isGenerating = ref(false)
const showGenerateModal = ref(false)

const generateForm = ref({
  exam_type: 'DNB_2026',
  scope: 'ETABLISSEMENT',
  class_id: ''
})

const canGenerate = computed(() => {
  return generateForm.value.exam_type && 
         (generateForm.value.scope !== 'CLASSE' || generateForm.value.class_id)
})

const canDelete = (bilan) => {
  return authStore.user?.role === 'Admin'
}

const getStatusClass = (status) => {
  switch (status) {
    case 'DONE':
      return 'bg-green-100 text-green-800'
    case 'GENERATING':
      return 'bg-blue-100 text-blue-800'
    case 'ERROR':
      return 'bg-red-100 text-red-800'
    default:
      return 'bg-gray-100 text-gray-800'
  }
}

const getStatusText = (status) => {
  switch (status) {
    case 'DONE':
      return 'Terminé'
    case 'GENERATING':
      return 'En cours'
    case 'ERROR':
      return 'Erreur'
    default:
      return 'Inconnu'
  }
}

const formatDate = (dateString) => {
  if (!dateString) return 'N/A'
  return new Date(dateString).toLocaleString('fr-FR', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
}

const fetchBilans = async () => {
  try {
    isLoading.value = true
    const data = await bilanService.list()
    bilans.value = data.bilans || data.results || data
  } catch (error) {
    console.error('Error fetching bilans:', error)
    toast.error('Erreur lors du chargement des bilans')
  } finally {
    isLoading.value = false
  }
}

const generateBilan = async () => {
  if (!canGenerate.value) return
  
  try {
    isGenerating.value = true
    showGenerateModal.value = false
    
    const payload = {
      exam_slug: generateForm.value.exam_type,
      scope: generateForm.value.scope
    }
    
    if (generateForm.value.scope === 'CLASSE') {
      payload.class_id = generateForm.value.class_id
    }
    
    await bilanService.generate(payload)
    toast.success('Bilan généré avec succès')
    await fetchBilans()
  } catch (error) {
    console.error('Error generating bilan:', error)
    const errorMessage = error.response?.data?.error || error.message || 'Erreur lors de la génération'
    toast.error(errorMessage)
  } finally {
    isGenerating.value = false
  }
}

const viewBilan = (bilan) => {
  router.push(`/admin/bilan/${bilan.id}`)
}

const downloadPDF = async (bilan) => {
  try {
    const response = await bilanService.downloadPDF(bilan.id)
    const blob = new Blob([response.data], { type: 'application/pdf' })
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `bilan_dnb_${bilan.id}.pdf`
    document.body.appendChild(a)
    a.click()
    window.URL.revokeObjectURL(url)
    document.body.removeChild(a)
    toast.success('PDF téléchargé')
  } catch (error) {
    console.error('Error downloading PDF:', error)
    toast.error('Erreur lors du téléchargement du PDF')
  }
}

const deleteBilan = async (bilan) => {
  if (!confirm('Êtes-vous sûr de vouloir supprimer ce bilan ?')) return
  
  try {
    await bilanService.delete(bilan.id)
    toast.success('Bilan supprimé')
    await fetchBilans()
  } catch (error) {
    console.error('Error deleting bilan:', error)
    toast.error('Erreur lors de la suppression')
  }
}

const refreshList = () => {
  fetchBilans()
}

onMounted(() => {
  fetchBilans()
})
</script>
