import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import Home from '../views/Home.vue'
import Login from '../views/Login.vue'
import AdminDashboard from '../views/AdminDashboard.vue'
import CorrectorDashboard from '../views/CorrectorDashboard.vue'
import ImportCopies from '../views/admin/ImportCopies.vue'

const routes = [
    {
        path: '/',
        name: 'Home',
        component: Home
    },
    {
        path: '/admin/login',
        name: 'LoginAdmin',
        component: Login,
        props: { roleContext: 'Admin' }
    },
    {
        path: '/teacher/login',
        name: 'LoginTeacher',
        component: Login,
        props: { roleContext: 'Teacher' }
    },
    // Backwards compatibility or redirect
    {
        path: '/login',
        redirect: '/'
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
        path: '/admin/users',
        name: 'UserManagement',
        component: () => import('../views/admin/UserManagement.vue'),
        meta: { requiresAuth: true, role: 'Admin' }
    },
    {
        path: '/admin/settings',
        name: 'Settings',
        component: () => import('../views/Settings.vue'),
        meta: { requiresAuth: true, role: 'Admin' }
    },
    {
        path: '/exam/:examId/staple',
        name: 'StapleView',
        component: () => import('../views/admin/StapleView.vue'),
        meta: { requiresAuth: true, role: 'Admin' }
    },
    {
        path: '/exam/:examId/grading-scale',
        name: 'MarkingSchemeView',
        component: () => import('../views/admin/MarkingSchemeView.vue'),
        meta: { requiresAuth: true, role: 'Admin' }
    },
    {
        path: '/:pathMatch(.*)*',
        redirect: '/'
    }
]

const router = createRouter({
    history: createWebHistory(),
    routes
})

router.beforeEach(async (to, from, next) => {
    const authStore = useAuthStore()

    // 1. Fetch user if needed (prevent infinite loop)
    // Only try to fetch if we don't have user and we aren't already checking
    if (!authStore.user && !authStore.isChecking) {
        // Optimization: Pass preference based on URL to avoid 401s on wrong endpoints
        const preferStudent = to.path.startsWith('/student')
        await authStore.fetchUser(preferStudent)
    }

    const isAuthenticated = !!authStore.user
    const userRole = authStore.user?.role

    // 2. Route Guard for Protected Routes
    if (to.meta.requiresAuth) {
        if (!isAuthenticated) {
            // Not authenticated -> Redirect to Home (Landing Page)
            return next('/')
        }

        // Role Check
        if (to.meta.role && userRole !== to.meta.role && userRole !== 'Admin') {
            // Wrong role -> Redirect to correct dashboard
            if (userRole === 'Admin') return next('/admin-dashboard')
            if (userRole === 'Teacher') return next('/corrector-dashboard')
            if (userRole === 'Student') return next('/student-portal')
            return next('/')
        }
    }

    // 3. Redirect Logged-In Users away from Login Pages
    const isLoginPage = ['LoginAdmin', 'LoginTeacher', 'StudentLogin', 'Home'].includes(to.name)
    if (isLoginPage && isAuthenticated) {
        if (userRole === 'Admin') return next('/admin-dashboard')
        if (userRole === 'Teacher') return next('/corrector-dashboard')
        if (userRole === 'Student') return next('/student-portal')
    }

    next()
})

export default router
