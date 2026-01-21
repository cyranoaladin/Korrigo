import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import Login from '../views/Login.vue'
import AdminDashboard from '../views/AdminDashboard.vue'
import CorrectorDashboard from '../views/CorrectorDashboard.vue'
import ImportCopies from '../views/admin/ImportCopies.vue'
// Import existing views if needed, e.g. StagingArea, etc., or route via dashboards

const routes = [
    {
        path: '/login',
        name: 'Login',
        component: Login
    },
    {
        path: '/admin-dashboard',
        name: 'AdminDashboard',
        component: AdminDashboard,
        meta: { requiresAuth: true, role: 'Admin' }
    },
    {
        path: '/corrector-dashboard',
        name: 'CorrectorDashboard',
        component: CorrectorDashboard,
        meta: { requiresAuth: true, role: 'Teacher' }
    },
    {
        path: '/corrector/import',
        name: 'ImportCopies',
        component: ImportCopies,
        meta: { requiresAuth: true, role: 'Teacher' }
    },
    {
        path: '/corrector/desk/:copyId',
        name: 'CorrectorDesk',
        component: () => import('../views/admin/CorrectorDesk.vue'),
        meta: { requiresAuth: true, role: 'Teacher' }
    },
    {
        path: '/exam/:examId/identification',
        name: 'IdentificationDesk',
        component: () => import('../views/admin/IdentificationDesk.vue'),
        meta: { requiresAuth: true, role: 'Admin' }
    },
    {
        path: '/student/login',
        name: 'StudentLogin',
        component: () => import('../views/student/LoginStudent.vue')
    },
    {
        path: '/student-portal',
        name: 'StudentPortal',
        component: () => import('../views/student/ResultView.vue'),
        meta: { requiresAuth: true, role: 'Student' }
    },
    {
        path: '/',
        redirect: '/login'
    }
]

const router = createRouter({
    history: createWebHistory(),
    routes
})

router.beforeEach(async (to, from, next) => {
    const authStore = useAuthStore()

    // Attempt to fetch user if not loaded and accessing protected route
    // Note: We avoid infinite loop if fetchUser fails -> it stays null
    if (to.meta.requiresAuth && !authStore.user && !authStore.isChecking) {
        await authStore.fetchUser()
    }

    if (to.meta.requiresAuth) {
        if (!authStore.user) {
            return next('/login')
        }

        // Role based access control
        if (to.meta.role && authStore.user.role !== to.meta.role && authStore.user.role !== 'Admin') {
            // Allow Admin to access everything or just specific? 
            // Simplified: If role mismatch, redirect to their home
            if (authStore.user.role === 'Admin') return next('/admin-dashboard')
            if (authStore.user.role === 'Teacher') return next('/corrector-dashboard')
            return next('/login')
        }
    }

    // Prevent logged in users from visiting login
    if (to.path === '/login' && authStore.user) {
        if (authStore.user.role === 'Admin') return next('/admin-dashboard')
        return next('/corrector-dashboard')
    }

    next()
})

export default router
