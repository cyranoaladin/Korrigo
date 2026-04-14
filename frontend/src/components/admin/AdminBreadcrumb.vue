<script setup>
import { computed, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import AppIcon from '../../icons/AppIcon.vue'
import api from '../../services/api'

const route = useRoute()
const examCache = ref({}) // { examId: { name, exam_type_details } }

const fetchExam = async (examId) => {
  if (!examId || examCache.value[examId]) return
  try {
    const res = await api.get(`/exams/${examId}/`)
    examCache.value[examId] = res.data
  } catch { /* ignore */ }
}

const examId = computed(() => route.params.examId)

watch(examId, (id) => { if (id) fetchExam(id) }, { immediate: true })

const crumbs = computed(() => {
  const items = [{ label: 'Administration', to: '/admin/dashboard' }]
  const path = route.path

  if (path.includes('/admin/users')) {
    items.push({ label: 'Utilisateurs' })
  } else if (path.includes('/admin/settings')) {
    items.push({ label: 'Paramètres' })
  } else if (path.includes('/admin/questionnaire')) {
    items.push({ label: 'Questionnaire' })
  } else if (path === '/admin/exams/new') {
    items.push({ label: 'Nouvel Examen' })
  } else if (examId.value) {
    const exam = examCache.value[examId.value]
    if (exam?.exam_type_details?.name) {
      items.push({ label: exam.exam_type_details.name })
    }
    if (exam?.name) {
      items.push({ label: exam.name, to: `/admin/exams/${examId.value}/overview` })
    }
    // Sub-page
    if (path.endsWith('/copies')) items.push({ label: 'Copies' })
    else if (path.endsWith('/correctors')) items.push({ label: 'Correcteurs' })
    else if (path.endsWith('/scale')) items.push({ label: 'Barème' })
    else if (path.endsWith('/results')) items.push({ label: 'Résultats' })
    else if (path.endsWith('/identification')) items.push({ label: 'Identification' })
    else if (path.endsWith('/overview')) items.push({ label: 'Résumé' })
  }

  return items
})
</script>

<template>
  <nav
    v-if="crumbs.length > 1"
    class="flex items-center gap-1.5 text-sm text-slate-500 px-6 py-3 bg-white border-b border-slate-200"
  >
    <template
      v-for="(crumb, i) in crumbs"
      :key="i"
    >
      <AppIcon
        v-if="i > 0"
        name="chevron-right"
        :size="14"
        class="text-slate-300 flex-shrink-0"
      />
      <router-link
        v-if="crumb.to && i < crumbs.length - 1"
        :to="crumb.to"
        class="hover:text-indigo-600 transition-colors truncate max-w-[200px]"
      >
        {{ crumb.label }}
      </router-link>
      <span
        v-else
        class="font-medium text-slate-700 truncate max-w-[200px]"
      >
        {{ crumb.label }}
      </span>
    </template>
  </nav>
</template>
