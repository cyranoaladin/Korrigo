<template>
  <aside class="w-64 h-screen bg-gray-900 text-white flex flex-col overflow-y-auto">
    <div class="p-4 border-b border-gray-700">
      <img src="/images/logo_korrigo_pmf.svg" alt="Korrigo" class="h-10 w-auto" />
    </div>

    <nav class="flex-1 px-3 py-4 space-y-1">
      <router-link
        to="/admin/dashboard"
        class="flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium transition-colors"
        :class="route.path === '/admin/dashboard'
          ? 'bg-blue-600 text-white'
          : 'text-gray-300 hover:bg-gray-800 hover:text-white'"
      >
        <BarChart3 :size="16" />
        <span>Vue d'ensemble</span>
      </router-link>

      <div class="pt-4">
        <p class="px-3 pb-1 text-xs font-semibold uppercase tracking-wider text-gray-500">Examens</p>

        <div v-for="group in examsByType" :key="group.details.id || group.details.name" class="mt-1">
          <p class="px-3 py-1 text-xs font-semibold text-gray-400 truncate">
            {{ group.details.name }}
          </p>

          <div v-for="exam in group.exams" :key="exam.id" class="mt-0.5">
            <button
              type="button"
              class="w-full flex items-center justify-between px-3 py-2 rounded-lg text-sm transition-colors"
              :class="expandedExamId === exam.id
                ? 'bg-gray-700 text-white'
                : 'text-gray-300 hover:bg-gray-800 hover:text-white'"
              @click="toggleExam(exam.id)"
            >
              <span class="truncate text-left">{{ exam.name }}</span>
              <span class="ml-2 flex-shrink-0 text-xs text-gray-400">
                {{ expandedExamId === exam.id ? '▲' : '▼' }}
              </span>
            </button>

            <div v-if="expandedExamId === exam.id" class="ml-3 mt-0.5 space-y-0.5">
              <router-link
                v-for="item in subItems(exam.id)"
                :key="item.to"
                :to="item.to"
                class="flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm transition-colors"
                :class="route.path === item.to
                  ? 'bg-blue-600 text-white'
                  : 'text-gray-400 hover:bg-gray-800 hover:text-white'"
              >
                {{ item.label }}
              </router-link>
            </div>
          </div>
        </div>

        <router-link
          to="/admin/exams/new"
          class="mt-2 flex items-center gap-2 px-3 py-2 rounded-lg text-sm text-blue-400 hover:bg-gray-800 hover:text-blue-300 transition-colors"
        >
          <span>+</span>
          <span>Nouvel Examen</span>
        </router-link>
      </div>
    </nav>

    <div class="px-3 pb-2 border-t border-gray-700 pt-3 space-y-1">
      <router-link
        to="/admin/users"
        class="flex items-center gap-2 px-3 py-2 rounded-lg text-sm transition-colors"
        :class="route.path === '/admin/users'
          ? 'bg-blue-600 text-white'
          : 'text-gray-300 hover:bg-gray-800 hover:text-white'"
      >
        <Users :size="16" />
        <span>Utilisateurs</span>
      </router-link>

      <router-link
        v-if="questionnaireSummary.is_available"
        to="/admin/questionnaire"
        class="flex items-center gap-2 px-3 py-2 rounded-lg text-sm transition-colors"
        :class="route.path === '/admin/questionnaire'
          ? 'bg-blue-600 text-white'
          : 'text-gray-300 hover:bg-gray-800 hover:text-white'"
      >
        <MessageSquare :size="16" />
        <span>Questionnaire</span>
      </router-link>

      <router-link
        to="/admin/settings"
        class="flex items-center gap-2 px-3 py-2 rounded-lg text-sm transition-colors"
        :class="route.path === '/admin/settings'
          ? 'bg-blue-600 text-white'
          : 'text-gray-300 hover:bg-gray-800 hover:text-white'"
      >
        <Settings :size="16" />
        <span>Paramètres</span>
      </router-link>

      <hr class="border-gray-700 my-2" />

      <button
        type="button"
        class="w-full flex items-center gap-2 px-3 py-2 rounded-lg text-sm text-red-400 hover:bg-gray-800 hover:text-red-300 transition-colors"
        @click="handleLogout"
      >
        <LogOut :size="16" />
        <span>Déconnexion</span>
      </button>
    </div>

    <div class="px-4 py-3 border-t border-gray-800">
      <p class="text-xs text-gray-600 leading-tight">
        Concepteur : Aleddine BEN RHOUMA — Labo Maths ERT
      </p>
    </div>
  </aside>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../../stores/auth'
import api from '../../services/api'
import { BarChart3, Users, MessageSquare, Settings, LogOut } from 'lucide-vue-next'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

const exams = ref([])
const questionnaireSummary = ref({ is_available: false })
const expandedExamId = ref(null)

const examsByType = computed(() => {
  const groups = {}
  const others = []

  ;(exams.value || []).forEach(exam => {
    if (!exam || typeof exam !== 'object') return

    const typeDetails = exam.exam_type_details
    if (typeDetails && (typeDetails.id || exam.exam_type)) {
      const typeId = typeDetails.id || exam.exam_type
      if (!groups[typeId]) {
        groups[typeId] = {
          details: {
            name: typeDetails?.name || 'Inconnu',
            icon: typeDetails?.icon || '📁',
            color: typeDetails?.color || '#64748b',
            id: typeId
          },
          exams: []
        }
      }
      groups[typeId].exams.push(exam)
    } else {
      others.push(exam)
    }
  })

  const result = Object.values(groups)
  if (others.length > 0) {
    result.push({
      details: { name: 'Autres Examens', icon: '📁', color: '#64748b' },
      exams: others
    })
  }
  return result
})

function subItems(examId) {
  return [
    { label: 'Résumé', to: `/admin/exams/${examId}/overview` },
    { label: 'Copies', to: `/admin/exams/${examId}/copies` },
    { label: 'Identification', to: `/admin/exams/${examId}/identification` },
    { label: 'Correcteurs', to: `/admin/exams/${examId}/correctors` },
    { label: 'Barème', to: `/admin/exams/${examId}/scale` },
    { label: 'Résultats', to: `/admin/exams/${examId}/results` },
  ]
}

function toggleExam(id) {
  expandedExamId.value = expandedExamId.value === id ? null : id
}

function syncExpandedFromRoute() {
  const paramId = route.params.examId
  if (paramId) {
    const idAsNumber = Number(paramId)
    expandedExamId.value = isNaN(idAsNumber) ? paramId : idAsNumber
  }
}

watch(() => route.params.examId, syncExpandedFromRoute)

async function handleLogout() {
  await authStore.logout()
  router.push('/')
}

onMounted(async () => {
  syncExpandedFromRoute()

  try {
    const res = await api.get('/exams/')
    exams.value = Array.isArray(res.data) ? res.data : (res.data.results || [])
  } catch (e) {
    console.error('AdminSidebar: failed to fetch exams', e)
  }

  try {
    const res = await api.get('/grading/questionnaire/bilan/')
    questionnaireSummary.value = res.data.summary || { is_available: false }
  } catch (e) {
    // questionnaire endpoint may not be available — silently ignore
  }
})
</script>
