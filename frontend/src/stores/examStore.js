import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useExamStore = defineStore('exam', () => {
    const currentExam = ref(null)
    const booklets = ref([])
    const isLoading = ref(false)
    const error = ref(null)

    // API Base URL from env or default
    const API_URL = import.meta.env.VITE_API_URL || ''

    async function uploadExam(file) {
        isLoading.value = true
        error.value = null
        try {
            const formData = new FormData()
            formData.append('name', file.name)
            formData.append('date', new Date().toISOString().split('T')[0])
            formData.append('pdf_source', file)

            const response = await fetch(`${API_URL}/api/exams/upload/`, {
                method: 'POST',
                credentials: 'include',
                body: formData,
            })

            if (!response.ok) throw new Error('Erreur lors de l\'upload')

            currentExam.value = await response.json()
            // Fetch booklets immediately after upload as per requirement
            if (currentExam.value?.id) {
                await fetchBooklets(currentExam.value.id)
            }
        } catch (e) {
            error.value = e.message
            console.error(e)
        } finally {
            isLoading.value = false
        }
    }

    async function fetchBooklets(examId) {
        isLoading.value = true
        try {
            const response = await fetch(`${API_URL}/api/exams/${examId}/booklets/`, {
                credentials: 'include'
            })
            if (!response.ok) throw new Error('Erreur lors de la récupération des fascicules')
            booklets.value = await response.json()
        } catch (e) {
            error.value = e.message
        } finally {
            isLoading.value = false
        }
    }

    async function mergeBooklets(bookletIds) {
        if (!currentExam.value) return

        isLoading.value = true
        try {
            const response = await fetch(`${API_URL}/api/exams/${currentExam.value.id}/merge/`, {
                method: 'POST',
                credentials: 'include',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ booklet_ids: bookletIds }),
            })

            if (!response.ok) throw new Error('Erreur lors de la fusion')

            const result = await response.json()
            // Refresh booklets list (merged ones should disappear or be marked - logic depends on backend)
            // For MVP, we just reload
            await fetchBooklets(currentExam.value.id)
            return result
        } catch (e) {
            error.value = e.message
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
