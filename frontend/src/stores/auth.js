import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api from '../services/api' // Import Axios instance
import { API_URL } from '../services/http'

export const useAuthStore = defineStore('auth', () => {
    const user = ref(null)
    const isAuthenticated = computed(() => !!user.value)
    const mustChangePassword = computed(() => user.value?.must_change_password || false)

    // Check if we are checking auth status
    const isChecking = ref(false)

    // Note: api.defaults.baseURL handles the prefix now

    async function login(username, password) {
        try {
            await api.post('/login/', { username, password })
            await fetchUser() // Get User Data
            return true
        } catch (e) {
            console.error(e)
            return false
        }
    }

    async function loginStudent(email, lastName) {
        try {
            const res = await api.post('/students/login/', { email, last_name: lastName })
            if (res.data) {
                // Fetch student info explicitly
                await fetchUser(true)
                return true
            }
            return false
        } catch (e) {
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

    async function fetchUser(preferStudent = false) {
        isChecking.value = true
        try {
            // Strategy: Try /me/ (Standard User) first, UNLESS preferStudent is true
            // Axios automatically uses baseURL (e.g. /api) and sends credentials

            if (!preferStudent) {
                try {
                    const res = await api.get('/me/')
                    if (res.data && res.data.role) {
                        user.value = res.data
                        return // SUCCESS - don't try student endpoint
                    }
                } catch (err) {
                    // Only try student endpoint if /me/ returns 403 or 401
                    if (err.response && (err.response.status === 403 || err.response.status === 401)) {
                        // Fallthrough to student check
                    } else {
                        // Other error - don't try student endpoint
                        user.value = null
                        return
                    }
                }
            }

            // If preferStudent or /me/ returned 403/401, try student endpoint
            try {
                const res = await api.get('/students/me/')
                user.value = { ...res.data, role: 'Student' }
            } catch {
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
        isAuthenticated, 
        mustChangePassword, 
        isChecking, 
        login, 
        loginStudent, 
        logout, 
        fetchUser,
        clearMustChangePassword,
        API_URL
    }
})
