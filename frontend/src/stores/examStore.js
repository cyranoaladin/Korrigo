import { defineStore } from 'pinia'
import { ref } from 'vue'
import api, { UPLOAD_TIMEOUT } from '../services/api'

export const useExamStore = defineStore('exam', () => {
    const currentExam = ref(null)
    const booklets = ref([])
    const isLoading = ref(false)
    const error = ref(null)

    async function uploadExam(file) {
        isLoading.value = true
        error.value = null
        try {
            const formData = new FormData()
            formData.append('name', file.name)
            formData.append('date', new Date().toISOString().split('T')[0])
            formData.append('pdf_source', file)

            const response = await api.post('/exams/upload/', formData, {
                headers: { 'Content-Type': 'multipart/form-data' },
                timeout: UPLOAD_TIMEOUT
            })

            currentExam.value = response.data
            // Fetch booklets immediately after upload as per requirement
            if (currentExam.value?.id) {
                await fetchBooklets(currentExam.value.id)
            }
        } catch (e) {
            error.value = e.response?.data?.error || e.message
            console.error(e)
        } finally {
            isLoading.value = false
        }
    }

    async function fetchBooklets(examId) {
        isLoading.value = true
        try {
            const response = await api.get(`/exams/${examId}/booklets/`)
            booklets.value = response.data
        } catch (e) {
            error.value = e.response?.data?.error || e.message
        } finally {
            isLoading.value = false
        }
    }

    async function mergeBooklets(bookletIds) {
        if (!currentExam.value) return

        isLoading.value = true
        try {
            const response = await api.post(`/exams/${currentExam.value.id}/merge/`, {
                booklet_ids: bookletIds
            })

            // Refresh booklets list
            await fetchBooklets(currentExam.value.id)
            return response.data
        } catch (e) {
            error.value = e.response?.data?.error || e.message
            throw e
        } finally {
            isLoading.value = false
        }
    }

    return {
        currentExam,
        booklets,
        isLoading,
        error,
        uploadExam,
        fetchBooklets,
        mergeBooklets
    }
})
