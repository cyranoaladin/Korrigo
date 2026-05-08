import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import MainLayout from '../layouts/MainLayout.vue'
import AdminLayout from '../layouts/AdminLayout.vue'
import HomeView from '../views/HomeView.vue'
import Home from '../views/Home.vue'
import GuideEnseignant from '../views/GuideEnseignant.vue'
import GuideEtudiant from '../views/GuideEtudiant.vue'
import DirectionConformite from '../views/DirectionConformite.vue'
import StatsReport from '../views/StatsReport.vue'
import Login from '../views/Login.vue'
import CorrectorDashboard from '../views/CorrectorDashboard.vue'
import ImportCopies from '../views/admin/ImportCopies.vue'
import LoginStudent from '../views/student/LoginStudent.vue'
import ForgotPassword from '../views/ForgotPassword.vue'
import ResetPasswordConfirm from '../views/ResetPasswordConfirm.vue'

function getDashboardForRole(role) {
    if (role === 'Admin') return '/admin/dashboard'
    if (role === 'Teacher') return '/corrector-dashboard'
    if (role === 'Student') return '/student/dashboard'
    if (role === 'Direction') return '/bilan/bac-blanc-2026'
    return '/'
}

function isLoginPage(routeName) {
    return ['LoginAdmin', 'LoginTeacher', 'StudentLogin', 'Portal'].includes(routeName)
}

const routes = [
    // ── Main portal (login cards) ──
    {
        path: '/',
        name: 'Portal',
        component: Home,
        meta: { title: 'Korrigo PMF', public: true }
    },

    // ── Landing / documentation pages (MainLayout with Navbar + Footer) ──
    {
        path: '/korrigo',
        component: MainLayout,
        children: [
            {
                path: '',
                name: 'Landing',
                component: HomeView,
                meta: { title: 'Korrigo PMF - Correction Numérique', public: true }
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
            },
            {
                path: 'stats/:examTypeCode',
                name: 'StatsReport',
                component: StatsReport,
                meta: { title: 'Rapport Statistique', requiresAuth: true, role: ['Teacher', 'Admin'] }
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
    // Legacy landing redirects
    {
        path: '/guide-enseignant',
        redirect: '/korrigo/guide-enseignant'
    },
    {
        path: '/guide-eleve',
        redirect: '/korrigo/guide-eleve'
    },
    {
        path: '/direction',
        redirect: '/korrigo/direction'
    },
    {
        path: '/student/login',
        name: 'StudentLogin',
        component: LoginStudent,
        meta: { public: true }
    },
    {
        path: '/forgot-password',
        name: 'ForgotPassword',
        component: ForgotPassword,
        meta: { public: true }
    },
    {
        path: '/reset-password',
        name: 'ResetPasswordConfirm',
        component: ResetPasswordConfirm,
        meta: { public: true }
    },

    // ── Admin app (with persistent sidebar) ──
    {
        path: '/admin',
        component: AdminLayout,
        meta: { requiresAuth: true, role: 'Admin' },
        children: [
            { path: '', redirect: 'dashboard' },
            {
                path: 'dashboard',
                name: 'AdminDashboard',
                component: () => import('../views/admin/AdminOverview.vue'),
                meta: { title: 'Vue d\'ensemble — Admin' }
            },
            {
                path: 'exams',
                name: 'ExamsList',
                component: () => import('../views/admin/ExamsList.vue'),
                meta: { title: 'Examens' }
            },
            {
                path: 'exams/new',
                name: 'CreateExam',
                component: () => import('../views/admin/CreateExam.vue'),
                meta: { title: 'Nouvel Examen' }
            },
            {
                path: 'exams/:examId',
                redirect: to => `/admin/exams/${to.params.examId}/overview`
            },
            {
                path: 'exams/:examId/overview',
                name: 'ExamOverview',
                component: () => import('../views/admin/ExamOverview.vue'),
                meta: { title: 'Résumé Examen' }
            },
            {
                path: 'exams/:examId/copies',
                name: 'ExamCopies',
                component: () => import('../views/admin/ExamCopies.vue'),
                meta: { title: 'Copies' }
            },
            {
                path: 'exams/:examId/correctors',
                name: 'ExamCorrectors',
                component: () => import('../views/admin/ExamCorrectors.vue'),
                meta: { title: 'Correcteurs' }
            },
            {
                path: 'exams/:examId/scale',
                name: 'MarkingSchemeView',
                component: () => import('../views/admin/MarkingSchemeView.vue'),
                meta: { title: 'Barème' }
            },
            {
                path: 'exams/:examId/results',
                name: 'ExamStudentList',
                component: () => import('../views/admin/ExamStudentList.vue'),
                meta: { title: 'Résultats' }
            },
            {
                path: 'users',
                name: 'UserManagement',
                component: () => import('../views/admin/UserManagement.vue'),
                meta: { title: 'Utilisateurs' }
            },
            {
                path: 'settings',
                name: 'Settings',
                component: () => import('../views/Settings.vue'),
                meta: { title: 'Paramètres' }
            },
            {
                path: 'questionnaire',
                name: 'QuestionnaireBilan',
                component: () => import('../views/admin/QuestionnaireBilan.vue'),
                meta: { title: 'Bilan Questionnaire Correcteurs' }
            },
            {
                path: 'bilan',
                name: 'BilanList',
                component: () => import('../views/admin/BilanList.vue'),
                meta: { title: 'Bilans Pédagogiques DNB' }
            },
            {
                path: 'bilan/:id',
                name: 'BilanDetail',
                component: () => import('../views/admin/BilanDetail.vue'),
                meta: { title: 'Détail du Bilan DNB' }
            }
        ]
    },

    // ── Admin (standalone — full-screen, no sidebar) ──
    {
        path: '/admin/exams/:examId/identification',
        name: 'IdentificationDesk',
        component: () => import('../views/admin/IdentificationDesk.vue'),
        meta: { requiresAuth: true, role: 'Admin' }
    },
    {
        path: '/admin/exams/:examId/staple',
        name: 'StapleView',
        component: () => import('../views/admin/StapleView.vue'),
        meta: { requiresAuth: true, role: 'Admin' }
    },

    // ── Bilan Bac Blanc ──
    {
        path: '/bilan/bac-blanc-2026',
        name: 'BilanBacBlanc',
        component: () => import('../views/BilanBacBlanc.vue'),
        meta: { requiresAuth: true, role: ['Teacher', 'Admin', 'Direction'], title: 'Bilan Bac Blanc Maths 2026' }
    },

    // ── Teacher / corrector routes ──
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
        path: '/corrector/my-students',
        name: 'MyStudents',
        component: () => import('../views/corrector/MyStudents.vue'),
        meta: { requiresAuth: true, role: ['Teacher', 'Admin'] }
    },
    {
        path: '/corrector/questionnaire',
        name: 'CorrectorQuestionnaire',
        component: () => import('../views/corrector/QuestionnaireView.vue'),
        meta: { requiresAuth: true, role: 'Teacher', title: 'Questionnaire Correcteur' }
    },
    {
        path: '/corrector/student/:studentId/bilan',
        name: 'StudentBilan',
        component: () => import('../views/corrector/StudentBilan.vue'),
        meta: { requiresAuth: true, role: ['Teacher', 'Admin'] }
    },

    // ── Student routes ──
    {
        path: '/student/change-password',
        redirect: '/student/dashboard'
    },
    {
        path: '/student/dashboard',
        name: 'StudentDashboard',
        component: () => import('../views/student/ResultView.vue'),
        meta: { requiresAuth: true, role: 'Student', title: 'Mon Espace Élève' }
    },
    // Legacy redirect
    {
        path: '/student-portal',
        redirect: '/student/dashboard'
    },

    // ── Legacy redirects (backward compatibility) ──
    { path: '/admin-dashboard', redirect: '/admin/dashboard' },
    { path: '/exam/:examId/identification', redirect: to => `/admin/exams/${to.params.examId}/identification` },
    { path: '/exam/:examId/staple', redirect: to => `/admin/exams/${to.params.examId}/staple` },
    { path: '/exam/:examId/grading-scale', redirect: to => `/admin/exams/${to.params.examId}/scale` },
    { path: '/exam/:examId/students', redirect: to => `/admin/exams/${to.params.examId}/results` },
    { path: '/questionnaire/bilan', redirect: '/admin/questionnaire' },

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

    // Public pages: skip heavy auth fetch, but still redirect authenticated
    // users away from login pages to their dashboard
    if (to.meta.public) {
        if (isLoginPage(to.name) && authStore.user) {
            const dashboardPath = getDashboardForRole(authStore.user.role)
            redirectCount++
            return next({ path: dashboardPath, replace: true })
        }
        return next()
    }

    // Attendre la fin d'un fetchUser en cours avant de décider
    if (authStore.isChecking) {
        await new Promise(resolve => {
            const interval = setInterval(() => {
                if (!authStore.isChecking) { clearInterval(interval); resolve() }
            }, 50)
        })
    }

    if (!authStore.user) {
        const preferStudent = to.path.startsWith('/student')
            || to.meta.role === 'Student'
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
        if (!isAuthenticated || userRole === 'Unknown') {
            redirectCount++
            return next({ path: '/', replace: true })
        }

        const allowedRoles = Array.isArray(to.meta.role) ? to.meta.role : [to.meta.role]
        if (to.meta.role && !allowedRoles.includes(userRole)) {
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

// Handle stale chunk errors after deploy (old hash no longer exists).
// Reload once to pick up the fresh index.html with updated asset hashes.
router.onError((error, to) => {
    if (
        error.message?.includes('Failed to fetch dynamically imported module') ||
        error.message?.includes('Importing a module script failed') ||
        error.message?.includes('Loading chunk') ||
        error.message?.includes('Loading CSS chunk')
    ) {
        const reloadKey = `chunk-reload:${to.fullPath}`
        if (!sessionStorage.getItem(reloadKey)) {
            sessionStorage.setItem(reloadKey, '1')
            console.warn('[Router] Stale chunk detected, reloading page…', error.message)
            window.location.assign(to.fullPath)
        } else {
            sessionStorage.removeItem(reloadKey)
            console.error('[Router] Chunk reload already attempted, not retrying.', error)
        }
    }
})

export default router
