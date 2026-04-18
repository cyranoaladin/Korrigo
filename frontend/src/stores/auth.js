import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api from '../services/api' // Import Axios instance

export const useAuthStore = defineStore('auth', () => {
    const user = ref(null)
    const lastError = ref('')
    const isAuthenticated = computed(() => !!user.value)
    const mustChangePassword = computed(() => user.value?.must_change_password || false)

    // Check if we are checking auth status
    const isChecking = ref(false)

    // Debounce: avoid redundant fetchUser calls within a short window
    let lastCheckedAt = 0
    const CHECK_DEBOUNCE_MS = 3000

    function clearError() {
        lastError.value = ''
    }

    // Note: api.defaults.baseURL handles the prefix now

    async function login(username, password) {
        try {
            lastError.value = ''
            await api.post('/login/', { username, password })
            await fetchUser(false, true) // Get User Data (force=true bypasses debounce)
            return true
        } catch (e) {
            lastError.value = e.response?.data?.error || 'Identifiants incorrects.'
            console.error(e)
            return false
        }
    }

    async function loginStudent(email, password) {
        try {
            lastError.value = ''
            const res = await api.post('/students/login/', { email, password })
            if (res.data) {
                // BUG-03 FIX: Définir user.value IMMÉDIATEMENT depuis la réponse login
                // (source de vérité) pour éviter toute race condition avec fetchUser.
                // La réponse login contient must_change_password issu de la session Django,
                // cohérent avec ce que /students/me/ retournerait.
                const mustChange = !!res.data.must_change_password
                const studentData = res.data.student || {}
                user.value = {
                    ...studentData,
                    role: 'Student',
                    must_change_password: mustChange
                }
                // Marquer comme vérifié pour éviter un re-fetch immédiat par le guard router
                lastCheckedAt = Date.now()
                
                // BUG-08/PATCH-02 FIX: Lancer fetchUser en background pour valider l'état complet
                // sans bloquer la transition d'UI.
                fetchUser(true, true).catch(() => {})
                return true
            }
            return false
        } catch (e) {
            lastError.value = e.response?.data?.error || 'Email ou mot de passe incorrect.'
            console.error(e)
            return false
        }
    }

    async function logout() {
        // BUG-18 FIX: réinitialiser l'état local AVANT la requête backend pour
        // éviter qu'un onglet concurrent utilise la session si le backend échoue.
        // La session Django sera expirée naturellement (SESSION_COOKIE_AGE).
        const endpoint = user.value?.role === 'Student' ? '/students/logout/' : '/logout/'
        user.value = null
        lastCheckedAt = 0
        try {
            await api.post(endpoint)
        } catch (e) {
            // Erreur ignorée : l'état local est déjà réinitialisé.
            // La session Django expirera via SESSION_COOKIE_AGE.
            console.warn('Logout backend request failed (session will expire naturally):', e?.response?.status)
        }
    }

    async function fetchUser(preferStudent = false, force = false) {
        // Debounce: skip if checked recently
        const now = Date.now()
        if (!force && (now - lastCheckedAt) < CHECK_DEBOUNCE_MS) {
            return // user déjà connu ou récemment vérifié, skip
        }
        isChecking.value = true
        lastCheckedAt = now
        try {
            // Step 1: Try Admin/Teacher endpoint first
            if (!preferStudent) {
                try {
                    const adminRes = await api.get('/me/')
                    const adminData = adminRes.data
                    // If role is a known staff role, stop here
                    if (adminData.role === 'Admin' || adminData.role === 'Teacher') {
                        user.value = adminData
                        return
                    }
                    // role=Unknown means the account exists but has no staff group
                    // → fall through to student check below
                } catch (e) {
                    // Admin check failed, continue to student
                }
            }

            // Step 2: Try Student endpoint
            try {
                const studentRes = await api.get('/students/me/')
                const studentData = studentRes.data
                user.value = { ...studentData, role: 'Student' }
                if (studentData.must_change_password !== undefined) {
                    user.value.must_change_password = studentData.must_change_password
                }
                return
            } catch (e) {
                // Silently handle discovery failure
                user.value = null
            }
        } catch (e) {
            user.value = null
        } finally {
            isChecking.value = false
        }
    }

    function clearMustChangePassword() {
        if (user.value) {
            user.value.must_change_password = false
        }
    }

    return { 
        user, 
        lastError,
        isAuthenticated, 
        mustChangePassword, 
        isChecking, 
        login, 
        loginStudent, 
        logout, 
        fetchUser,
        clearError,
        clearMustChangePassword
    }
})
