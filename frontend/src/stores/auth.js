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

    function isExpectedAuthFailure(status) {
        return status === 401 || status === 403
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
            if (!isExpectedAuthFailure(e?.response?.status)) {
                console.error(e)
            }
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
            if (!isExpectedAuthFailure(e?.response?.status)) {
                console.error(e)
            }
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
            if (!isExpectedAuthFailure(e?.response?.status)) {
                // Erreur inattendue seulement : l'état local est déjà réinitialisé,
                // mais on garde une trace si le backend a réellement un problème.
                console.warn('Logout backend request failed (session will expire naturally):', e?.response?.status)
            }
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
            // Step 1: Single non-failing probe → /api/auth/status/
            // Returns 200 always with { authenticated, role, user }.
            // Avoids the noisy 403 spam on /me/ + /students/me/ at bootstrap.
            try {
                const statusRes = await api.get('/auth/status/')
                const s = statusRes.data || {}
                if (!s.authenticated) {
                    user.value = null
                    return
                }
                // Authenticated. For Admin/Teacher/Direction we still hit /me/
                // to get the full payload (assigned_codes, must_change_password, direction_scope, …).
                if ((s.role === 'Admin' || s.role === 'Teacher' || s.role === 'Direction') && !preferStudent) {
                    try {
                        const adminRes = await api.get('/me/')
                        user.value = adminRes.data
                        return
                    } catch (_) {
                        // Fallback to minimal payload from status
                        user.value = { ...(s.user || {}), role: s.role }
                        return
                    }
                }
                if (s.role === 'Student') {
                    try {
                        const studentRes = await api.get('/students/me/')
                        const studentData = studentRes.data
                        user.value = { ...studentData, role: 'Student' }
                        if (studentData.must_change_password !== undefined) {
                            user.value.must_change_password = studentData.must_change_password
                        }
                        return
                    } catch (_) {
                        user.value = { ...(s.user || {}), role: 'Student' }
                        return
                    }
                }
                // Unknown role: keep minimal payload
                user.value = { ...(s.user || {}), role: s.role || 'Unknown' }
            } catch (e) {
                // /auth/status/ itself failed (network, 5xx). Mark as unauthenticated.
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
