<template>
  <div class="bg-gradient-to-br from-indigo-50 to-purple-50 border border-indigo-200 rounded-xl p-6 shadow-sm">
    <div class="flex items-center justify-between mb-4">
      <div class="flex items-center gap-3">
        <div class="w-12 h-12 bg-indigo-600 rounded-lg flex items-center justify-center">
          <AppIcon name="file-text" :size="20" class="text-white" />
        </div>
        <div>
          <h3 class="text-lg font-semibold text-gray-900">Bilan Pédagogique {{ examName === 'DNB_2026' ? 'DNB' : examName === 'EAM BLANCHE 2026' ? 'EAM' : examName }}</h3>
          <p class="text-sm text-gray-600">Analyse complète des résultats</p>
        </div>
      </div>
      <div class="flex items-center gap-2">
        <span
          v-if="bilan"
          :class="getStatusClass(bilan.status)"
          class="px-3 py-1 text-xs font-medium rounded-full"
        >
          {{ getStatusText(bilan.status) }}
        </span>
      </div>
    </div>

    <!-- Loading state -->
    <div v-if="loading" class="space-y-3">
      <div class="h-4 bg-gray-200 rounded animate-pulse"></div>
      <div class="h-4 bg-gray-200 rounded w-3/4 animate-pulse"></div>
      <div class="h-8 bg-gray-200 rounded animate-pulse"></div>
    </div>

    <!-- Bilan available -->
    <div v-else-if="bilan" class="space-y-4">
      <div class="grid grid-cols-2 gap-4">
        <div class="bg-white rounded-lg p-3">
          <div class="text-2xl font-bold text-indigo-600">
            {{ bilan.n_copies ?? 'N/A' }}
          </div>
          <div class="text-xs text-gray-600">Copies analysées</div>
        </div>
        <div class="bg-white rounded-lg p-3">
          <div class="text-2xl font-bold text-green-600">
            {{ formatDate(bilan.generated_at) }}
          </div>
          <div class="text-xs text-gray-600">Dernière génération</div>
        </div>
      </div>

      <div class="flex items-center justify-between">
        <div class="text-sm text-gray-600">
          <span class="font-medium">Généré par :</span>
          {{ bilan.generated_by }}
        </div>
        <div class="flex items-center gap-2">
          <button
            @click="viewBilan"
            class="inline-flex items-center gap-2 bg-indigo-600 text-white px-4 py-2 rounded-lg hover:bg-indigo-700 transition-colors text-sm font-medium"
          >
            <AppIcon name="eye" :size="14" />
            Consulter
          </button>
          <button
            v-if="bilan.pdf_available"
            @click="downloadPDF"
            class="inline-flex items-center gap-2 bg-green-600 text-white px-4 py-2 rounded-lg hover:bg-green-700 transition-colors text-sm font-medium"
          >
            <AppIcon name="download" :size="14" />
            PDF
          </button>
        </div>
      </div>
    </div>

    <!-- No bilan available -->
    <div v-else class="text-center py-4">
      <div class="inline-flex items-center justify-center w-12 h-12 bg-gray-100 rounded-full mb-3">
        <AppIcon name="file-text" :size="20" class="text-gray-400" />
      </div>
      <p class="text-gray-600 font-medium mb-4">Aucun bilan disponible</p>
      <button
        @click="generateBilan"
        :disabled="isGenerating"
        class="inline-flex items-center gap-2 bg-indigo-600 text-white px-4 py-2 rounded-lg hover:bg-indigo-700 transition-colors text-sm font-medium disabled:opacity-50"
      >
        <div v-if="isGenerating" class="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
        <AppIcon v-else name="plus" :size="14" />
        {{ isGenerating ? 'Génération...' : 'Générer le bilan' }}
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useToast } from '../../composables/useToast'
import { bilanService } from '../../services/bilan'
import AppIcon from '../../icons/AppIcon.vue'

const props = defineProps({
  examId: {
    type: String,
    required: true
  },
  examName: {
    type: String,
    default: 'DNB_2026'
  }
})

const router = useRouter()
const toast = useToast()

const bilan = ref(null)
const loading = ref(false)
const isGenerating = ref(false)

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
    console.error('Error fetching bilan:', error)
  } finally {
    loading.value = false
  }
}

const generateBilan = async () => {
  try {
    isGenerating.value = true
    await bilanService.generate({
      exam_slug: props.examName,
      scope: 'ETABLISSEMENT'
    })
    toast.success('Bilan généré avec succès')
    await fetchBilan()
  } catch (error) {
    console.error('Error generating bilan:', error)
    const errorMessage = error.response?.data?.error || error.message || 'Erreur lors de la génération'
    toast.error(errorMessage)
  } finally {
    isGenerating.value = false
  }
}

const viewBilan = () => {
  if (!bilan.value) return
  if (props.examName === 'EAM BLANCHE 2026') {
    router.push(`/bilan/eam/${bilan.value.id}`)
  } else {
    router.push(`/admin/bilan/${bilan.value.id}`)
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
