import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useExamStore = defineStore('exam', () => {
    // ExamType (groupe d'examens, ex: BAC_BLANC_MATHS_2026 → BB_J1, BB_J2, ...)
    const currentExamTypeId = ref(null)
    const currentExamTypeName = ref(null)

    // Examen précis (ex: BB_J1 vs BB_J2). Utilisé pour filtrer "Mes Élèves"
    // de manière STRICTE à cet examen (et copies finalisées uniquement).
    const currentExamId = ref(null)
    const currentExamName = ref(null)

    function setCurrentExamType(id, name = null) {
        currentExamTypeId.value = id
        currentExamTypeName.value = name
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
        // Le clear du type éefface aussi l'exam sélectionné (cohérence)
        clearCurrentExam()
    }

    function setCurrentExam(id, name = null) {
        currentExamId.value = id
        currentExamName.value = name
        if (id) {
            localStorage.setItem('currentExamId', id)
            if (name) localStorage.setItem('currentExamName', name)
        }
    }

    function clearCurrentExam() {
        currentExamId.value = null
        currentExamName.value = null
        localStorage.removeItem('currentExamId')
        localStorage.removeItem('currentExamName')
    }

    function restoreFromStorage() {
        const storedTypeId = localStorage.getItem('currentExamTypeId')
        const storedTypeName = localStorage.getItem('currentExamTypeName')
        if (storedTypeId) {
            currentExamTypeId.value = storedTypeId
            currentExamTypeName.value = storedTypeName
        }
        const storedExamId = localStorage.getItem('currentExamId')
        const storedExamName = localStorage.getItem('currentExamName')
        if (storedExamId) {
            currentExamId.value = storedExamId
            currentExamName.value = storedExamName
        }
    }

    return {
        currentExamTypeId,
        currentExamTypeName,
        currentExamId,
        currentExamName,
        setCurrentExamType,
        clearCurrentExamType,
        setCurrentExam,
        clearCurrentExam,
        restoreFromStorage
    }
})
