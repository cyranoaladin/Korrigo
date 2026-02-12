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
            const res = await api.post('/students/login/', { 
                email,
                password
            })
            if (res.data) {
                // Fetch student info explicitly
                await fetchUser(true, true)
                // Propagate must_change_password from login response
                if (user.value && res.data.must_change_password) {
                    user.value.must_change_password = true
                }
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
        try {
            const endpoint = user.value?.role === 'Student' ? '/students/logout/' : '/logout/'
            await api.post(endpoint)
        } catch (e) {
            console.error(e)
        } finally {
            user.value = null
        }
    }

    async function fetchUser(preferStudent = false, force = false) {
        // Debounce: skip if checked recently and no user found
        const now = Date.now()
        if (!force && !user.value && (now - lastCheckedAt) < CHECK_DEBOUNCE_MS) {
            return
        }
        isChecking.value = true
        lastCheckedAt = now
        try {
            // Run both checks in parallel to avoid sequential 403 delays
            const [adminResult, studentResult] = await Promise.allSettled([
                preferStudent ? Promise.reject('skipped') : api.get('/me/'),
                api.get('/students/me/')
            ])

            // Prefer admin/teacher result unless preferStudent
            if (!preferStudent && adminResult.status === 'fulfilled') {
                user.value = adminResult.value.data
                user.value.role = user.value.role || 'Admin'
                return
            }

            // Fallback to student
            if (studentResult.status === 'fulfilled') {
                user.value = { ...studentResult.value.data, role: 'Student' }
                return
            }

            // Both failed — not authenticated
            user.value = null
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
