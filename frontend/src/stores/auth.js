import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api from '../services/api'
import { getErrorMessage } from '../utils/errorMessages'

export const useAuthStore = defineStore('auth', () => {
    const user = ref(null)
    const isAuthenticated = computed(() => !!user.value)
    const mustChangePassword = computed(() => user.value?.must_change_password || false)

    const isChecking = ref(false)
    const lastError = ref(null)

    async function login(username, password) {
        lastError.value = null
        try {
            await api.post('/login/', { username, password })
            await fetchUser()
            return true
        } catch (e) {
            console.error(e)
            lastError.value = getErrorMessage(e)
            return false
        }
    }

    async function loginStudent(ine, lastName) {
        lastError.value = null
        try {
            const res = await api.post('/students/login/', { ine, last_name: lastName })
            if (res.data) {
                await fetchUser(true)
                return true
            }
            return false
        } catch (e) {
            console.error(e)
            lastError.value = getErrorMessage(e)
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
        lastError.value = null
        try {
            if (!preferStudent) {
                try {
                    const res = await api.get('/me/')
                    user.value = res.data
                    user.value.role = user.value.role || 'Admin'
                    return
                } catch {
                }
            }

            try {
                const res = await api.get('/students/me/')
                user.value = { ...res.data, role: 'Student' }
            } catch {
                user.value = null
            }
        } catch (e) {
            user.value = null
            lastError.value = getErrorMessage(e)
        } finally {
            isChecking.value = false
        }
    }

    function clearMustChangePassword() {
        if (user.value) {
            user.value.must_change_password = false
        }
    }

    function clearError() {
        lastError.value = null
    }

    return { 
        user, 
        isAuthenticated, 
        mustChangePassword, 
        isChecking,
        lastError,
        login, 
        loginStudent, 
        logout, 
        fetchUser,
        clearMustChangePassword,
        clearError
    }
})
