import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useExamStore = defineStore('exam', () => {
    // Store the current exam type ID for filtering "My Students" view
    const currentExamTypeId = ref(null)
    const currentExamTypeName = ref(null)

    function setCurrentExamType(id, name = null) {
        currentExamTypeId.value = id
        currentExamTypeName.value = name
        // Persist to localStorage for page refreshes
        if (id) {
            localStorage.setItem('currentExamTypeId', id)
            if (name) localStorage.setItem('currentExamTypeName', name)
        }
    }

    function clearCurrentExamType() {
        currentExamTypeId.value = null
        currentExamTypeName.value = null
        localStorage.removeItem('currentExamTypeId')
        localStorage.removeItem('currentExamTypeName')
    }

    function restoreFromStorage() {
        const storedId = localStorage.getItem('currentExamTypeId')
        const storedName = localStorage.getItem('currentExamTypeName')
        if (storedId) {
            currentExamTypeId.value = storedId
            currentExamTypeName.value = storedName
        }
    }

    return {
        currentExamTypeId,
        currentExamTypeName,
        setCurrentExamType,
        clearCurrentExamType,
        restoreFromStorage
    }
})
