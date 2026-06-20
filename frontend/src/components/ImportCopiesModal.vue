<script setup>
import { ref, computed } from 'vue'
import api, { UPLOAD_TIMEOUT } from '../services/api'

const props = defineProps({
  examId: { type: String, required: true }
})

const emit = defineEmits(['close', 'success'])

const mode = ref('batch') // 'batch' | 'individual'
const pdfFile = ref(null)
const pagesPerBooklet = ref(4)
const individualFiles = ref([])
const isUploading = ref(false)
const uploadError = ref(null)
const uploadProgress = ref(null)
const uploadPercent = ref(0)
const fileInputBatch = ref(null)
const fileInputIndividual = ref(null)

const canSubmit = computed(() => {
  if (mode.value === 'batch') return !!pdfFile.value
  return individualFiles.value.length > 0
})

const handleBatchFileSelect = (event) => {
  const file = event.target.files[0]
  if (file) {
    pdfFile.value = file
    uploadError.value = null
  }
}

const handleIndividualFilesSelect = (event) => {
  const files = Array.from(event.target.files)
  if (files.length > 100) {
    uploadError.value = 'Maximum 100 fichiers par upload.'
    return
  }
  individualFiles.value = files
  uploadError.value = null
}

const removeFile = (index) => {
  individualFiles.value = individualFiles.value.filter((_, i) => i !== index)
}

const uploadCopies = async () => {
  uploadError.value = null
  isUploading.value = true
  uploadProgress.value = 'Upload en cours...'
  uploadPercent.value = 0

  try {
    if (mode.value === 'batch') {
      const formData = new FormData()
      formData.append('pdf_source', pdfFile.value)
      formData.append('pages_per_booklet', pagesPerBooklet.value)

      await api.post(`/exams/${props.examId}/upload/`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
        timeout: UPLOAD_TIMEOUT,
        onUploadProgress: (progressEvent) => {
          if (progressEvent.total) {
            uploadPercent.value = Math.round((progressEvent.loaded * 100) / progressEvent.total)
            uploadProgress.value = uploadPercent.value >= 100
              ? 'Découpage du PDF en cours...'
              : `Upload : ${uploadPercent.value}%`
          }
        }
      })
    } else {
      const formData = new FormData()
      individualFiles.value.forEach(file => {
        formData.append('pdf_files', file)
      })

      await api.post(`/exams/${props.examId}/upload-individual-pdfs/`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
        timeout: UPLOAD_TIMEOUT,
        onUploadProgress: (progressEvent) => {
          if (progressEvent.total) {
            uploadPercent.value = Math.round((progressEvent.loaded * 100) / progressEvent.total)
            uploadProgress.value = uploadPercent.value >= 100
              ? 'Traitement des fichiers...'
              : `Upload : ${uploadPercent.value}%`
          }
        }
      })
    }

    uploadProgress.value = 'Import terminé !'
    setTimeout(() => {
      emit('success')
      emit('close')
    }, 800)
  } catch (error) {
    const msg = error.response?.data?.error
      || error.response?.data?.detail
      || error.response?.data?.pdf_source?.[0]
      || "Erreur lors de l'import des copies."
    uploadError.value = msg
  } finally {
    isUploading.value = false
  }
}
</script>

<template>
  <div
    class="fixed inset-0 z-[100] bg-slate-900/50 backdrop-blur-sm flex items-center justify-center px-4"
    @click.self="$emit('close')"
  >
    <div class="w-full max-w-lg bg-white rounded-2xl shadow-2xl ring-1 ring-slate-200 overflow-hidden">
      <!-- Header -->
      <div class="px-6 py-4 border-b border-slate-100 flex items-center justify-between">
        <div>
          <h2 class="text-lg font-bold text-slate-800">Importer des copies</h2>
          <p class="text-xs text-slate-500">Ajoutez des copies PDF dans cet examen.</p>
        </div>
        <button class="p-2 rounded-lg hover:bg-slate-100" @click="$emit('close')">
          <svg xmlns="http://www.w3.org/2000/svg" class="w-5 h-5 text-slate-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      <!-- Body -->
      <div class="p-6 space-y-5">
        <!-- Mode selector -->
        <div class="grid grid-cols-2 gap-3">
          <button
            class="flex flex-col items-center gap-2 px-4 py-4 border-2 rounded-xl text-sm font-medium transition-all"
            :class="mode === 'batch'
              ? 'border-indigo-500 bg-indigo-50 text-indigo-700'
              : 'border-slate-200 text-slate-500 hover:border-slate-300'"
            :disabled="isUploading"
            @click="mode = 'batch'"
          >
            <svg xmlns="http://www.w3.org/2000/svg" class="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
              <path stroke-linecap="round" stroke-linejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
            </svg>
            <span>Scan par lots (A3)</span>
            <span class="text-xs font-normal opacity-70">1 PDF multi-pages</span>
          </button>
          <button
            class="flex flex-col items-center gap-2 px-4 py-4 border-2 rounded-xl text-sm font-medium transition-all"
            :class="mode === 'individual'
              ? 'border-indigo-500 bg-indigo-50 text-indigo-700'
              : 'border-slate-200 text-slate-500 hover:border-slate-300'"
            :disabled="isUploading"
            @click="mode = 'individual'"
          >
            <svg xmlns="http://www.w3.org/2000/svg" class="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
              <path stroke-linecap="round" stroke-linejoin="round" d="M15.75 17.25v3.375c0 .621-.504 1.125-1.125 1.125h-9.75a1.125 1.125 0 01-1.125-1.125V7.875c0-.621.504-1.125 1.125-1.125H6.75a9.06 9.06 0 011.5.124m7.5 10.376h3.375c.621 0 1.125-.504 1.125-1.125V11.25c0-4.46-3.243-8.161-7.5-8.876a9.06 9.06 0 00-1.5-.124H9.375c-.621 0-1.125.504-1.125 1.125v3.5m7.5 10.375H9.375a1.125 1.125 0 01-1.125-1.125v-9.25m12 6.625v-1.875a3.375 3.375 0 00-3.375-3.375h-1.5a1.125 1.125 0 01-1.125-1.125v-1.5a3.375 3.375 0 00-3.375-3.375H9.75" />
            </svg>
            <span>Par copie (A4)</span>
            <span class="text-xs font-normal opacity-70">1 PDF par élève</span>
          </button>
        </div>

        <!-- BATCH mode fields -->
        <template v-if="mode === 'batch'">
          <div>
            <label class="block text-sm font-semibold text-slate-700 mb-2">Fichier PDF source *</label>
            <button
              class="w-full px-4 py-4 border-2 border-dashed rounded-xl text-sm transition-colors"
              :class="pdfFile
                ? 'border-indigo-300 bg-indigo-50 text-indigo-700'
                : 'border-slate-200 bg-slate-50 text-slate-500 hover:border-indigo-300 hover:bg-indigo-50/50'"
              :disabled="isUploading"
              @click="fileInputBatch?.click()"
            >
              {{ pdfFile ? pdfFile.name : 'Cliquez pour sélectionner un PDF' }}
            </button>
            <input
              ref="fileInputBatch"
              type="file"
              accept="application/pdf"
              class="hidden"
              @change="handleBatchFileSelect"
            >
          </div>
          <div>
            <label class="block text-sm font-semibold text-slate-700 mb-2">Pages par copie</label>
            <input
              v-model.number="pagesPerBooklet"
              type="number"
              min="1"
              class="w-full px-4 py-2.5 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
              :disabled="isUploading"
            >
          </div>
        </template>

        <!-- INDIVIDUAL mode fields -->
        <template v-if="mode === 'individual'">
          <div>
            <label class="block text-sm font-semibold text-slate-700 mb-2">Fichiers PDF individuels (max 100)</label>
            <button
              class="w-full px-4 py-4 border-2 border-dashed rounded-xl text-sm transition-colors"
              :class="individualFiles.length > 0
                ? 'border-indigo-300 bg-indigo-50 text-indigo-700'
                : 'border-slate-200 bg-slate-50 text-slate-500 hover:border-indigo-300 hover:bg-indigo-50/50'"
              :disabled="isUploading"
              @click="fileInputIndividual?.click()"
            >
              {{ individualFiles.length > 0
                ? `${individualFiles.length} fichier(s) sélectionné(s)`
                : 'Cliquez pour sélectionner les PDFs' }}
            </button>
            <input
              ref="fileInputIndividual"
              type="file"
              accept="application/pdf"
              multiple
              class="hidden"
              @change="handleIndividualFilesSelect"
            >
          </div>

          <!-- Files list -->
          <div v-if="individualFiles.length > 0" class="bg-slate-50 rounded-xl p-3 space-y-1.5 max-h-48 overflow-y-auto">
            <div
              v-for="(file, index) in individualFiles.slice(0, 10)"
              :key="index"
              class="flex items-center justify-between px-3 py-1.5 bg-white rounded-lg ring-1 ring-slate-100 text-xs"
            >
              <span class="text-slate-700 truncate mr-2">{{ file.name }}</span>
              <button
                class="text-slate-400 hover:text-red-500 flex-shrink-0"
                @click="removeFile(index)"
              >
                <svg xmlns="http://www.w3.org/2000/svg" class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
            <p v-if="individualFiles.length > 10" class="text-xs text-slate-400 text-center pt-1">
              + {{ individualFiles.length - 10 }} autres fichiers...
            </p>
          </div>
        </template>

        <!-- Error -->
        <div v-if="uploadError" class="px-4 py-3 bg-red-50 border border-red-200 rounded-xl text-sm text-red-700">
          {{ uploadError }}
        </div>

        <!-- Progress -->
        <div v-if="uploadProgress" class="space-y-2">
          <p class="text-sm text-indigo-600 font-medium text-center">{{ uploadProgress }}</p>
          <div v-if="uploadPercent > 0" class="w-full h-2 bg-indigo-100 rounded-full overflow-hidden">
            <div
              class="h-full bg-indigo-600 rounded-full transition-all duration-300"
              :style="{ width: uploadPercent + '%' }"
            />
          </div>
        </div>
      </div>

      <!-- Footer -->
      <div class="px-6 py-4 border-t border-slate-100 flex items-center justify-end gap-3 bg-slate-50/60">
        <button
          class="px-4 py-2 rounded-lg text-sm font-medium text-slate-600 hover:bg-slate-100"
          :disabled="isUploading"
          @click="$emit('close')"
        >
          Annuler
        </button>
        <button
          class="inline-flex items-center gap-2 px-5 py-2 rounded-lg text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 disabled:opacity-60 disabled:cursor-not-allowed"
          :disabled="isUploading || !canSubmit"
          @click="uploadCopies"
        >
          {{ isUploading ? 'Import en cours...' : 'Importer' }}
        </button>
      </div>
    </div>
  </div>
</template>
