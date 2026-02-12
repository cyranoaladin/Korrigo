import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import MainLayout from '../layouts/MainLayout.vue'
import HomeView from '../views/HomeView.vue'
import GuideEnseignant from '../views/GuideEnseignant.vue'
import GuideEtudiant from '../views/GuideEtudiant.vue'
import DirectionConformite from '../views/DirectionConformite.vue'
import Login from '../views/Login.vue'
import AdminDashboard from '../views/AdminDashboard.vue'
import CorrectorDashboard from '../views/CorrectorDashboard.vue'
import ImportCopies from '../views/admin/ImportCopies.vue'
import LoginStudent from '../views/student/LoginStudent.vue'

function getDashboardForRole(role) {
    if (role === 'Admin') return '/admin-dashboard'
    if (role === 'Teacher') return '/corrector-dashboard'
    if (role === 'Student') return '/student-portal'
    return '/'
}

function isLoginPage(routeName) {
    return ['LoginAdmin', 'LoginTeacher', 'StudentLogin', 'Home'].includes(routeName)
}

const routes = [
    // ── Public landing pages (MainLayout with Navbar + Footer) ──
    {
        path: '/',
        component: MainLayout,
        children: [
            {
                path: '',
                name: 'Home',
                component: HomeView,
                meta: { title: 'Accueil - Korrigo PMF', public: true }
            },
            {
                path: 'guide-enseignant',
                name: 'GuideEnseignant',
                component: GuideEnseignant,
                meta: { title: 'Guide Enseignant', public: true }
            },
            {
                path: 'guide-eleve',
                name: 'GuideEleve',
                component: GuideEtudiant,
                meta: { title: 'Guide Élève', public: true }
            },
            {
                path: 'direction',
                name: 'Direction',
                component: DirectionConformite,
                meta: { title: 'Direction & Conformité', public: true }
            }
        ]
    },

    // ── Login routes ──
    {
        path: '/admin/login',
        name: 'LoginAdmin',
        component: Login,
        props: { roleContext: 'Admin' },
        meta: { public: true }
    },
    {
        path: '/teacher/login',
        name: 'LoginTeacher',
        component: Login,
        props: { roleContext: 'Teacher' },
        meta: { public: true }
    },
    {
        path: '/login',
        redirect: '/'
    },
    {
        path: '/student/login',
        name: 'StudentLogin',
        component: LoginStudent,
        meta: { public: true }
    },

    // ── Authenticated app routes ──
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
        meta: { requiresAuth: true, role: ['Teacher', 'Admin'] }
    },
    {
        path: '/exam/:examId/identification',
        name: 'IdentificationDesk',
        component: () => import('../views/admin/IdentificationDesk.vue'),
        meta: { requiresAuth: true, role: 'Admin' }
    },
    {
        path: '/student/change-password',
        name: 'StudentChangePassword',
        component: () => import('../views/student/ChangePasswordStudent.vue'),
        meta: { requiresAuth: true, role: 'Student' }
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

    // ── Catch-all ──
    {
        path: '/:pathMatch(.*)*',
        redirect: '/'
    }
]

const router = createRouter({
    history: createWebHistory(),
    routes,
    scrollBehavior(to, from, savedPosition) {
        if (savedPosition) {
            return savedPosition
        }
        if (to.hash) {
            return { el: to.hash, behavior: 'smooth' }
        }
        return { top: 0 }
    }
})

let redirectCount = 0
const MAX_REDIRECTS = 3

router.beforeEach(async (to, from, next) => {
    const authStore = useAuthStore()

    // Set page title
    document.title = to.meta.title ? to.meta.title : 'Korrigo PMF'

    if (from.name && to.name !== from.name) {
        redirectCount = 0
    }

    if (redirectCount >= MAX_REDIRECTS) {
        console.error('Max redirect limit reached. Allowing navigation to prevent loop.')
        redirectCount = 0
        return next()
    }

    // Skip auth check entirely for public pages — no API calls needed
    if (to.meta.public) {
        return next()
    }

    if (!authStore.user && !authStore.isChecking) {
        const preferStudent = to.path.startsWith('/student')
        try {
            await authStore.fetchUser(preferStudent)
        } catch (error) {
            console.error('Router guard: fetchUser failed', error)
            if (to.meta.requiresAuth) {
                redirectCount++
                return next({ path: '/', replace: true })
            }
        }
    }

    const isAuthenticated = !!authStore.user
    const userRole = authStore.user?.role

    if (to.meta.requiresAuth) {
        if (!isAuthenticated) {
            redirectCount++
            return next({ path: '/', replace: true })
        }

        const allowedRoles = Array.isArray(to.meta.role) ? to.meta.role : [to.meta.role]
        if (to.meta.role && !allowedRoles.includes(userRole) && userRole !== 'Admin') {
            const dashboardPath = getDashboardForRole(userRole)
            redirectCount++
            return next({ path: dashboardPath, replace: true })
        }
    }

    if (isLoginPage(to.name) && isAuthenticated) {
        const dashboardPath = getDashboardForRole(userRole)
        redirectCount++
        return next({ path: dashboardPath, replace: true })
    }

    next()
})

export default router
