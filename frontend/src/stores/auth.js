import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api from '../services/api' // Import Axios instance

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

    async function loginStudent(lastName, firstName, dateNaissance) {
        try {
            const res = await api.post('/students/login/', { 
                last_name: lastName,
                first_name: firstName,
                date_naissance: dateNaissance
            })
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
                    user.value = res.data
                    user.value.role = user.value.role || 'Admin'
                    return
                } catch {
                    // Ignore error and fallthrough to student check if not preferred but standard failed
                }
            }

            // If failed or preferStudent, try student endpoint
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
        clearMustChangePassword
    }
})
