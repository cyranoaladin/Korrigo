import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useAuthStore = defineStore('auth', () => {
    const user = ref(null)
    const isAuthenticated = computed(() => !!user.value)

    // Check if we are checking auth status
    const isChecking = ref(false)

    const API_URL = import.meta.env.VITE_API_URL || ''

    async function login(username, password) {
        try {
            const res = await fetch(`${API_URL}/api/login/`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username, password })
            })

            if (!res.ok) throw new Error("Login failed")

            await fetchUser() // Get User Data
            return true
        } catch (e) {
            console.error(e)
            return false
        }
    }

    async function loginStudent(ine, lastName) {
        try {
            const res = await fetch(`${API_URL}/api/students/login/`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ ine: ine, last_name: lastName })
            })

            if (res.ok) {
                const data = await res.json()
                // Fetch student info
                await fetchUser(true) // Pass flag to indicate student check preference
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
            await fetch(`${API_URL}/api/logout/`, { method: 'POST' })
            user.value = null
        } catch (e) {
            console.error(e)
            user.value = null
        }
    }

    async function logoutStudent() {
        try {
            await fetch(`${API_URL}/api/students/logout/`, { method: 'POST' })
            user.value = null
        } catch (e) {
            console.error(e)
            user.value = null
        }
    }

    async function fetchUser(preferStudent = false) {
        isChecking.value = true
        try {
            // Strategy: Try /api/me/ (Standard User) first, UNLESS preferStudent is true
            // Actually, simplest is to try /api/me/, if 401/403, try /api/students/me/
            // But 401 on /api/me/ might just mean not logged in at all.

            let res = null
            if (!preferStudent) {
                res = await fetch(`${API_URL}/api/me/`)
                if (res.ok) {
                    user.value = await res.json()
                    user.value.role = user.value.role || 'Admin' // Default fallback if field missing, but backend sends it?
                    // Backend User Detail view typically sends username, email, groups. 
                    // Assuming 'role' is derived or we add it. 
                    // For 'Admin' vs 'Teacher', we rely on 'is_staff' or Group. 
                    // Let's assume standard Django User for now.
                    return
                }
            }

            // If failed or preferStudent, try student endpoint
            res = await fetch(`${API_URL}/api/students/me/`)
            if (res.ok) {
                const student = await res.json()
                user.value = { ...student, role: 'Student' } // Tag as Student
            } else {
                user.value = null
            }
        } catch (e) {
            user.value = null
        } finally {
            isChecking.value = false
        }
    }

    // Helper for Headers if needed (cookies are HttpOnly, so mainly for CSRF if applicable, but we disabled Secure CSRF for localhost)
    const authHeaders = {
        'Content-Type': 'application/json'
    }

    return { user, isAuthenticated, isChecking, login, loginStudent, logout, logoutStudent, fetchUser, API_URL, authHeaders }
})
