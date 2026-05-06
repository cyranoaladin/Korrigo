<template>
  <div class="bg-gradient-to-r from-indigo-500 to-purple-600 rounded-xl p-6 text-white shadow-lg">
    <div class="flex items-center justify-between">
      <div class="flex items-center gap-4">
        <div class="w-12 h-12 bg-white/20 rounded-lg flex items-center justify-center">
          <AppIcon name="file-text" :size="20" class="text-white" />
        </div>
        <div>
          <h3 class="text-lg font-semibold">Bilan Pédagogique DNB</h3>
          <p class="text-sm text-white/90">Consultez l'analyse complète des résultats</p>
        </div>
      </div>
      
      <div class="flex items-center gap-3">
        <span
          v-if="bilan"
          :class="getStatusClass(bilan.status)"
          class="px-3 py-1 text-xs font-medium rounded-full"
        >
          {{ getStatusText(bilan.status) }}
        </span>
        
        <button
          @click="viewBilan"
          class="inline-flex items-center gap-2 bg-white text-indigo-600 px-4 py-2 rounded-lg hover:bg-gray-100 transition-colors text-sm font-medium"
        >
          <AppIcon name="eye" :size="14" />
          {{ bilan ? 'Consulter' : 'Voir les bilans' }}
        </button>
      </div>
    </div>

    <!-- Loading state -->
    <div v-if="loading" class="mt-4">
      <div class="h-2 bg-white/20 rounded animate-pulse"></div>
    </div>

    <!-- Bilan info -->
    <div v-else-if="bilan" class="mt-4 pt-4 border-t border-white/20">
      <div class="grid grid-cols-3 gap-4 text-sm">
        <div>
          <div class="text-white/70">Copies analysées</div>
          <div class="font-semibold">{{ bilan.n_copies ?? 'N/A' }}</div>
        </div>
        <div>
          <div class="text-white/70">Généré le</div>
          <div class="font-semibold">{{ formatDate(bilan.generated_at) }}</div>
        </div>
        <div>
          <div class="text-white/70">Statut</div>
          <div class="font-semibold">{{ getStatusText(bilan.status) }}</div>
        </div>
      </div>
      
      <div v-if="bilan.pdf_available" class="mt-3">
        <button
          @click="downloadPDF"
          class="inline-flex items-center gap-2 bg-white/20 text-white px-3 py-1.5 rounded-lg hover:bg-white/30 transition-colors text-sm"
        >
          <AppIcon name="download" :size="14" />
          Télécharger le PDF
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useToast } from '../composables/useToast'
import { bilanService } from '../services/bilan'
import AppIcon from '../icons/AppIcon.vue'

const props = defineProps({
  examName: {
    type: String,
    default: 'DNB_2026'
  }
})

const router = useRouter()
const toast = useToast()

const bilan = ref(null)
const loading = ref(false)

const getStatusClass = (status) => {
  switch (status) {
    case 'DONE':
      return 'bg-green-500 text-white'
    case 'GENERATING':
      return 'bg-blue-500 text-white'
    case 'ERROR':
      return 'bg-red-500 text-white'
    default:
      return 'bg-white/30 text-white'
  }
}

const getStatusText = (status) => {
  switch (status) {
    case 'DONE':
      return 'Disponible'
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
  return new Date(dateString).toLocaleDateString('fr-FR', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric'
  })
}

const fetchBilan = async () => {
  try {
    loading.value = true
    const response = await bilanService.list()
    // La réponse est { bilans: [...], count: N }
    const list = Array.isArray(response.bilans) ? response.bilans : []
    bilan.value = list.find(b => b.exam_type === props.examName) || null
  } catch (error) {
    // 403 silencieux : l'utilisateur n'a pas accès au bilan (normal pour certains rôles)
    if (error?.response?.status !== 403) {
      console.error('Error fetching bilan:', error)
    }
  } finally {
    loading.value = false
  }
}

const viewBilan = () => {
  if (bilan.value) {
    router.push(`/admin/bilan/${bilan.value.id}`)
  } else {
    router.push('/admin/bilan')
  }
}

const downloadPDF = async () => {
  if (!bilan.value) return
  
  try {
    const response = await bilanService.downloadPDF(bilan.value.id)
    const blob = new Blob([response.data], { type: 'application/pdf' })
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `bilan_dnb_${bilan.value.id}.pdf`
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

onMounted(() => {
  fetchBilan()
})
</script>
