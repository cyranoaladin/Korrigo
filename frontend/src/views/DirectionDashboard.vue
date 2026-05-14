<template>
  <div class="min-h-screen bg-[#f5f7fa] font-sans">

    <!-- ── Hero Header ──────────────────────────────────────────────────── -->
    <header class="bg-slate-900 text-white">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <!-- Top bar -->
        <div class="flex items-center justify-between py-4 border-b border-white/10">
          <div class="flex items-center gap-3">
            <div class="w-8 h-8 bg-white/10 rounded-lg flex items-center justify-center ring-1 ring-white/15">
              <AppIcon name="school" :size="16" class="text-slate-300" />
            </div>
            <span class="text-slate-400 text-xs uppercase tracking-widest font-medium">Lycée Pierre Mendès France de Tunis</span>
          </div>
          <div class="flex items-center gap-3">
            <div v-if="scopeLabel" class="px-3 py-1 bg-white/10 rounded-full border border-white/15 text-xs text-slate-300 font-medium">
              {{ scopeLabel }}
            </div>
            <button @click="logout"
              class="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium text-slate-400 hover:text-white hover:bg-white/10 transition-colors">
              <AppIcon name="logout" :size="13" />
              Déconnexion
            </button>
          </div>
        </div>

        <!-- Main header content -->
        <div class="py-6 flex flex-col sm:flex-row sm:items-end justify-between gap-6">
          <div>
            <h1 class="text-2xl sm:text-3xl font-bold tracking-tight text-white">
              Bonjour, {{ firstName }}
            </h1>
            <p class="mt-1 text-slate-400 text-sm">Tableau de bord · Année scolaire 2025-2026</p>
          </div>

          <!-- KPIs -->
          <div v-if="!loading && !error" class="flex items-stretch gap-3">
            <div class="text-center bg-white/8 rounded-xl px-5 py-3 border border-white/10 min-w-[72px]">
              <div class="text-2xl font-bold text-white">{{ visibleExams.length }}</div>
              <div class="text-slate-400 text-xs mt-0.5">Examens</div>
            </div>
            <div class="text-center bg-white/8 rounded-xl px-5 py-3 border border-white/10 min-w-[72px]">
              <div class="text-2xl font-bold text-white">{{ totalCopies }}</div>
              <div class="text-slate-400 text-xs mt-0.5">Copies</div>
            </div>
            <div class="text-center bg-white/8 rounded-xl px-5 py-3 border border-white/10 min-w-[72px]">
              <div class="text-2xl font-bold text-white">{{ totalFinalized }}</div>
              <div class="text-slate-400 text-xs mt-0.5">Corrigées</div>
            </div>
            <div class="text-center bg-white/8 rounded-xl px-5 py-3 border border-white/10 min-w-[72px]">
              <div class="text-2xl font-bold text-white">{{ bilansCount }}</div>
              <div class="text-slate-400 text-xs mt-0.5">Bilans</div>
            </div>
          </div>
        </div>
      </div>
    </header>

    <!-- ── Content ───────────────────────────────────────────────────────── -->
    <main class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">

      <!-- Loading -->
      <div v-if="loading" class="flex flex-col items-center justify-center py-28 gap-4">
        <div class="w-10 h-10 border-[3px] border-indigo-200 border-t-indigo-600 rounded-full animate-spin"></div>
        <p class="text-slate-400 text-sm">Chargement en cours…</p>
      </div>

      <!-- Error -->
      <div v-else-if="error" class="bg-white rounded-2xl shadow-sm ring-1 ring-red-100 p-10 text-center">
        <div class="w-12 h-12 bg-red-50 rounded-xl flex items-center justify-center mx-auto mb-4">
          <AppIcon name="alert" :size="22" class="text-red-400" />
        </div>
        <p class="text-slate-700 font-medium mb-1">Erreur de chargement</p>
        <p class="text-slate-400 text-sm mb-5">{{ error }}</p>
        <button @click="fetchExams" class="px-5 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium rounded-xl transition-colors shadow-sm">
          Réessayer
        </button>
      </div>

      <template v-else>

        <!-- ── Bac Blanc ───────────────────────────────────────────────── -->
        <section v-if="canViewBacBlanc && bacBlancExams.length > 0">
          <ExamSection
            accent="indigo"
            icon="award"
            title="Bac Blanc Mathématiques 2026"
            level="Terminale"
            :exams="bacBlancExamsSorted"
            :show-bilan-btn="true"
            @bilan="$router.push('/bilan/bac-blanc-2026')"
            @results="(id) => $router.push(`/direction/exams/${id}/results`)"
          />
        </section>

        <!-- ── EAM ────────────────────────────────────────────────────── -->
        <section v-if="canViewEAM && eamExams.length > 0">
          <ExamSection
            accent="emerald"
            icon="book-open-check"
            title="EAM Blanche 2026"
            level="Première"
            :exams="eamExams"
            @bilan="(id) => $router.push(`/bilan/eam/${id}`)"
            @results="(id) => $router.push(`/direction/exams/${id}/results`)"
          />
        </section>

        <!-- ── DNB ────────────────────────────────────────────────────── -->
        <section v-if="canViewDNB && dnbExams.length > 0">
          <ExamSection
            accent="amber"
            icon="graduation-cap"
            title="Diplôme National du Brevet 2026"
            level="Troisième"
            :exams="dnbExams"
            @bilan="(id) => $router.push(`/bilan/dnb/${id}`)"
            @results="(id) => $router.push(`/direction/exams/${id}/results`)"
          />
        </section>

        <!-- ── Other exams table ──────────────────────────────────────── -->
        <section v-if="otherExams.length > 0">
          <div class="bg-white rounded-2xl shadow-sm ring-1 ring-slate-100 overflow-hidden">
            <div class="px-6 py-4 border-b border-slate-100 flex items-center gap-3">
              <div class="w-8 h-8 bg-slate-50 rounded-lg flex items-center justify-center ring-1 ring-slate-100">
                <AppIcon name="layers" :size="15" class="text-slate-500" />
              </div>
              <h2 class="text-sm font-semibold text-slate-700 uppercase tracking-wide">Autres examens</h2>
            </div>
            <div class="overflow-x-auto">
              <table class="min-w-full text-sm">
                <thead>
                  <tr class="border-b border-slate-50">
                    <th class="px-6 py-3 text-left text-xs font-semibold text-slate-400 uppercase tracking-wide">Examen</th>
                    <th class="px-6 py-3 text-left text-xs font-semibold text-slate-400 uppercase tracking-wide">Date</th>
                    <th class="px-6 py-3 text-center text-xs font-semibold text-slate-400 uppercase tracking-wide">Copies</th>
                    <th class="px-6 py-3 text-center text-xs font-semibold text-slate-400 uppercase tracking-wide">Statut</th>
                    <th class="px-6 py-3 text-right text-xs font-semibold text-slate-400 uppercase tracking-wide">Actions</th>
                  </tr>
                </thead>
                <tbody class="divide-y divide-slate-50">
                  <tr v-for="exam in otherExams" :key="exam.id" class="hover:bg-slate-50/60 transition-colors">
                    <td class="px-6 py-4 font-medium text-slate-800">{{ formatExamName(exam.name) }}</td>
                    <td class="px-6 py-4 text-slate-500 text-xs">{{ formatDate(exam.date) }}</td>
                    <td class="px-6 py-4 text-center font-semibold text-slate-700">{{ exam.copies_count || 0 }}</td>
                    <td class="px-6 py-4 text-center">
                      <StatusBadge :status="exam.status" />
                    </td>
                    <td class="px-6 py-4 text-right">
                      <div class="flex items-center justify-end gap-2">
                        <button v-if="exam.has_bilan" @click="goToBilan(exam)"
                          class="inline-flex items-center gap-1 text-xs font-medium text-indigo-600 hover:text-white hover:bg-indigo-600 bg-indigo-50 px-2.5 py-1.5 rounded-lg transition-all">
                          <AppIcon name="file-text" :size="12" /> Bilan
                        </button>
                        <button @click="$router.push(`/direction/exams/${exam.id}/results`)"
                          class="inline-flex items-center gap-1 text-xs font-medium text-slate-600 hover:text-white hover:bg-slate-600 bg-slate-100 px-2.5 py-1.5 rounded-lg transition-all">
                          <AppIcon name="users" :size="12" /> Résultats
                        </button>
                      </div>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </section>

      </template>
    </main>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, h } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import api from '../services/api'
import AppIcon from '../icons/AppIcon.vue'

const router    = useRouter()
const authStore = useAuthStore()

// ── Access control via backend direction_scope (no hardcoded emails) ────
const directionScope = computed(() => authStore.user?.direction_scope)
const scopeLabel = computed(() => {
  const s = directionScope.value
  if (s === 'all') return 'Accès complet'
  if (Array.isArray(s)) {
    const map = { 'bac-blanc': 'Bac Blanc', 'eam': 'EAM', 'dnb': 'DNB' }
    return s.map(k => map[k] || k).join(' · ')
  }
  return null
})
const firstName = computed(() => {
  const u = authStore.user
  if (!u) return ''
  if (u.first_name) return u.first_name
  const email = u.email || ''
  return email.split('.')[0]?.replace(/^./, c => c.toUpperCase()) || email
})

const canViewBacBlanc = computed(() => {
  const s = directionScope.value
  return !s || s === 'all' || (Array.isArray(s) && s.includes('bac-blanc'))
})
const canViewEAM = computed(() => {
  const s = directionScope.value
  return !s || s === 'all' || (Array.isArray(s) && s.includes('eam'))
})
const canViewDNB = computed(() => {
  const s = directionScope.value
  return !s || s === 'all' || (Array.isArray(s) && s.includes('dnb'))
})

// ── Data ─────────────────────────────────────────────────────────────────
const loading = ref(true)
const error   = ref(null)
const exams   = ref([])

const fetchExams = async () => {
  loading.value = true
  error.value   = null
  try {
    const res = await api.get('/exams/direction/exams/')
    exams.value = Array.isArray(res.data) ? res.data : (res.data.results || [])
  } catch (e) {
    error.value = 'Erreur lors du chargement des examens.'
  } finally {
    loading.value = false
  }
}

// ── Filters ──────────────────────────────────────────────────────────────
const isBacBlanc = (e) => {
  const n = e.name?.toLowerCase() || '', t = e.exam_type?.toLowerCase() || ''
  const match = n.includes('bac blanc') || n.includes('bb_') || n.includes('bb ') || t.includes('bac blanc')
  const test  = n.includes('validation') || n.includes('test') || n.includes('prod')
  return match && !test
}
const isEAM = (e) => e.name?.toLowerCase().includes('eam') || e.exam_type?.toLowerCase().includes('eam')
const isDNB = (e) => e.name?.toLowerCase().includes('dnb') || e.exam_type?.toLowerCase().includes('dnb')

const bacBlancExams       = computed(() => exams.value.filter(isBacBlanc))
const bacBlancExamsSorted = computed(() => [...bacBlancExams.value].sort((a, b) => {
  const j = (e) => e.name?.toLowerCase().includes('j2') ? 2 : e.name?.toLowerCase().includes('j1') ? 1 : 0
  return j(a) - j(b)
}))
const eamExams  = computed(() => exams.value.filter(isEAM))
const dnbExams  = computed(() => exams.value.filter(isDNB))
const otherExams = computed(() => exams.value.filter(e => !isBacBlanc(e) && !isEAM(e) && !isDNB(e)))
const visibleExams = computed(() => exams.value.filter(e =>
  (canViewBacBlanc.value && isBacBlanc(e)) ||
  (canViewEAM.value      && isEAM(e)) ||
  (canViewDNB.value      && isDNB(e)) ||
  otherExams.value.includes(e)
))

// ── Header KPIs ──────────────────────────────────────────────────────────
const totalCopies    = computed(() => visibleExams.value.reduce((s, e) => s + (e.copies_count    || 0), 0))
const totalFinalized = computed(() => visibleExams.value.reduce((s, e) => s + (e.finalized_count || 0), 0))
const bilansCount    = computed(() => {
  let count = 0
  // Bac Blanc a un rapport de jury consolidé à /bilan/bac-blanc-2026 (JuryReport, pas BilanReport)
  if (canViewBacBlanc.value && bacBlancExams.value.length > 0) count += 1
  // EAM et DNB utilisent BilanReport (has_bilan vient de l'API)
  if (canViewEAM.value && eamExams.value.some(e => e.has_bilan)) count += 1
  if (canViewDNB.value && dnbExams.value.some(e => e.has_bilan)) count += 1
  return count
})

// ── Helpers ──────────────────────────────────────────────────────────────
const formatDate = (v) => {
  if (!v) return '—'
  return new Date(v).toLocaleDateString('fr-FR', { year: 'numeric', month: 'long', day: 'numeric' })
}

const formatExamName = (name) => {
  if (!name) return '—'
  // Known transformations
  const rules = [
    [/^BB_J1$/i,   'Bac Blanc 2026 — Jour 1'],
    [/^BB_J2$/i,   'Bac Blanc 2026 — Jour 2'],
    [/^DNB_2026$/i,'DNB Blanc 2026'],
    [/^EAM BLANCHE 2026$/i, 'EAM Blanche 2026'],
  ]
  for (const [re, label] of rules) {
    if (re.test(name.trim())) return label
  }
  // Generic: underscores → spaces, title case
  return name
    .replace(/_/g, ' ')
    .replace(/\b(\w)/g, c => c.toUpperCase())
}

const goToBilan = (exam) => {
  if (isEAM(exam)) router.push(`/bilan/eam/${exam.id}`)
  else if (isDNB(exam)) router.push(`/bilan/dnb/${exam.id}`)
}

const logout = async () => {
  await authStore.logout()
  router.push('/')
}

onMounted(fetchExams)

const ACCENT_CONFIG = {
  indigo: {
    section:  'from-indigo-600 to-violet-600',
    iconBg:   'bg-indigo-100',
    iconText: 'text-indigo-600',
    badge:    'bg-indigo-50 text-indigo-600 ring-indigo-100',
    btnSolid: 'bg-indigo-600 hover:bg-indigo-700 text-white shadow-indigo-100',
    btnOutline:'bg-white hover:bg-indigo-50 text-indigo-700 ring-1 ring-indigo-200 hover:ring-indigo-300',
    progress: 'from-indigo-400 to-violet-500',
    cardHover:'hover:ring-indigo-200',
  },
  emerald: {
    section:  'from-emerald-600 to-teal-600',
    iconBg:   'bg-emerald-100',
    iconText: 'text-emerald-600',
    badge:    'bg-emerald-50 text-emerald-700 ring-emerald-100',
    btnSolid: 'bg-emerald-600 hover:bg-emerald-700 text-white shadow-emerald-100',
    btnOutline:'bg-white hover:bg-emerald-50 text-emerald-700 ring-1 ring-emerald-200 hover:ring-emerald-300',
    progress: 'from-emerald-400 to-teal-500',
    cardHover:'hover:ring-emerald-200',
  },
  amber: {
    section:  'from-amber-500 to-orange-500',
    iconBg:   'bg-amber-100',
    iconText: 'text-amber-600',
    badge:    'bg-amber-50 text-amber-700 ring-amber-100',
    btnSolid: 'bg-amber-600 hover:bg-amber-700 text-white shadow-amber-100',
    btnOutline:'bg-white hover:bg-amber-50 text-amber-700 ring-1 ring-amber-200 hover:ring-amber-300',
    progress: 'from-amber-400 to-orange-400',
    cardHover:'hover:ring-amber-200',
  },
}

const STATUS_MAP = {
  draft:       { label: 'Brouillon',  cls: 'bg-slate-100 text-slate-500' },
  published:   { label: 'Publié',     cls: 'bg-blue-100 text-blue-700' },
  in_progress: { label: 'En cours',   cls: 'bg-amber-100 text-amber-700' },
  grading:     { label: 'Correction', cls: 'bg-purple-100 text-purple-700' },
  completed:   { label: 'Terminé',    cls: 'bg-emerald-100 text-emerald-700' },
  archived:    { label: 'Archivé',    cls: 'bg-slate-100 text-slate-500' },
}

// ── StatusBadge ────────────────────────────────────────────────────────────
const StatusBadge = {
  name: 'StatusBadge',
  props: { status: String },
  setup(props) {
    return () => {
      const s = STATUS_MAP[props.status] || { label: props.status || '—', cls: 'bg-gray-100 text-gray-500' }
      return h('span', { class: `inline-flex items-center px-2.5 py-1 rounded-lg text-xs font-medium ${s.cls}` }, s.label)
    }
  }
}

// ── ExamCard ───────────────────────────────────────────────────────────────
const ExamCard = {
  name: 'ExamCard',
  props: {
    exam:   { type: Object, required: true },
    accent: { type: String, default: 'indigo' },
    dayLabel: { type: String, default: '' },
  },
  emits: ['bilan', 'results'],
  setup(props, { emit }) {
    const formatDate = (v) => {
      if (!v) return '—'
      return new Date(v).toLocaleDateString('fr-FR', { year: 'numeric', month: 'long', day: 'numeric' })
    }
    const pct = (e) => {
      const total = e.copies_count || 0
      if (!total) return 0
      return Math.round(((e.finalized_count || 0) / total) * 100)
    }
    const progressColor = (p, accent) => {
      if (p === 100) return 'from-emerald-400 to-emerald-500'
      if (p >= 50)   return 'from-amber-400 to-orange-400'
      return ACCENT_CONFIG[accent]?.progress || 'from-slate-300 to-slate-400'
    }
    const formatName = (name) => {
      if (!name) return '—'
      const rules = [
        [/^BB_J1$/i, 'Bac Blanc — Jour 1'],
        [/^BB_J2$/i, 'Bac Blanc — Jour 2'],
        [/^DNB_2026$/i, 'DNB Blanc 2026'],
        [/^EAM BLANCHE 2026$/i, 'EAM Blanche 2026'],
      ]
      for (const [re, lbl] of rules) if (re.test(name.trim())) return lbl
      return name.replace(/_/g, ' ').replace(/\b(\w)/g, c => c.toUpperCase())
    }

    return () => {
      const e   = props.exam
      const a   = ACCENT_CONFIG[props.accent] || ACCENT_CONFIG.indigo
      const p   = pct(e)
      const st  = STATUS_MAP[e.status] || { label: e.status || '—', cls: 'bg-gray-100 text-gray-500' }
      // AppIcon importé en haut du <script setup> — référence directe, pas resolveComponent

      return h('div', {
        class: `bg-white rounded-2xl ring-1 ring-slate-100 ${a.cardHover} hover:shadow-md transition-all p-5`
      }, [
        // Header row
        h('div', { class: 'flex items-start justify-between gap-3 mb-4' }, [
          h('div', { class: 'flex-1 min-w-0' }, [
            h('div', { class: 'flex items-center gap-2 flex-wrap' }, [
              h('h3', { class: 'font-semibold text-slate-800 text-base' }, formatName(e.name)),
              props.dayLabel
                ? h('span', { class: `text-xs font-medium px-2 py-0.5 rounded-md ${a.badge} ring-1` }, props.dayLabel)
                : null,
            ]),
            h('div', { class: 'flex items-center flex-wrap gap-x-3 gap-y-1 mt-1.5' }, [
              h('span', { class: 'text-xs text-slate-400 flex items-center gap-1' }, [
                h(AppIcon, { name: 'calendar', size: 11 }),
                formatDate(e.date),
              ]),
              h('span', { class: 'text-slate-400 text-xs' }, '·'),
              h('span', { class: 'text-xs text-slate-400' }, `${e.copies_count || 0} copies`),
              e.finalized_count != null
                ? h('span', { class: 'text-xs text-slate-400' }, `· ${e.finalized_count} corrigées`)
                : null,
            ]),
          ]),
          h('span', { class: `shrink-0 inline-flex items-center px-2.5 py-1 rounded-lg text-xs font-medium ${st.cls}` }, st.label),
        ]),

        // Progress bar
        e.copies_count > 0
          ? h('div', { class: 'mb-4' }, [
              h('div', { class: 'flex items-center justify-between mb-1.5' }, [
                h('span', { class: 'text-xs text-slate-400' }, 'Progression correction'),
                h('span', { class: `text-xs font-semibold ${p === 100 ? 'text-emerald-600' : p >= 50 ? 'text-amber-600' : 'text-slate-500'}` }, `${p} %`),
              ]),
              h('div', { class: 'h-1.5 bg-slate-100 rounded-full overflow-hidden' }, [
                h('div', {
                  class: `h-full rounded-full bg-gradient-to-r transition-all duration-700 ${progressColor(p, props.accent)}`,
                  style: `width:${p}%`
                })
              ])
            ])
          : null,

        // Divider
        h('div', { class: 'border-t border-slate-50 my-3' }),

        // Actions
        h('div', { class: 'flex flex-wrap gap-2' }, [
          e.has_bilan
            ? h('button', {
                class: `inline-flex items-center gap-1.5 px-4 py-2 rounded-xl text-sm font-medium transition-all shadow-sm ${a.btnSolid}`,
                onClick: () => emit('bilan', e.id)
              }, [h(AppIcon, { name: 'file-text', size: 14 }), 'Rapport de jury'])
            : h('button', {
                disabled: true,
                class: 'inline-flex items-center gap-1.5 px-4 py-2 rounded-xl text-sm font-medium bg-slate-50 text-slate-400 ring-1 ring-slate-100 cursor-not-allowed'
              }, [h(AppIcon, { name: 'clock', size: 14 }), 'Bilan en préparation']),

          h('button', {
            class: `inline-flex items-center gap-1.5 px-4 py-2 rounded-xl text-sm font-medium transition-all ${a.btnOutline}`,
            onClick: () => emit('results', e.id)
          }, [h(AppIcon, { name: 'users', size: 14 }), 'Résultats élèves']),
        ]),
      ])
    }
  }
}

// ── ExamSection ────────────────────────────────────────────────────────────
const ExamSection = {
  name: 'ExamSection',
  props: {
    accent:       { type: String, default: 'indigo' },
    icon:         { type: String, default: 'layers' },
    title:        { type: String, required: true },
    level:        { type: String, default: '' },
    exams:        { type: Array,  default: () => [] },
    showBilanBtn: { type: Boolean, default: false },
  },
  emits: ['bilan', 'results'],
  setup(props, { emit }) {
    const dayLabel = (exam) => {
      const n = exam.name?.toLowerCase() || ''
      if (n.includes('j1') || n.includes('jour 1') || n.includes('jour1')) return 'Jour 1'
      if (n.includes('j2') || n.includes('jour 2') || n.includes('jour2')) return 'Jour 2'
      return ''
    }

    return () => {
      const a = ACCENT_CONFIG[props.accent] || ACCENT_CONFIG.indigo
      // Références directes — AppIcon importé en haut, ExamCard défini dans le même scope

      // Section-level stats
      const totalCopies    = props.exams.reduce((s, e) => s + (e.copies_count    || 0), 0)
      const totalFinalized = props.exams.reduce((s, e) => s + (e.finalized_count || 0), 0)
      const globalPct      = totalCopies > 0 ? Math.round((totalFinalized / totalCopies) * 100) : 0

      return h('div', { class: 'bg-white rounded-2xl shadow-sm ring-1 ring-slate-100 overflow-hidden' }, [

        // ── Section header ──
        h('div', { class: 'px-6 py-5 border-b border-slate-100 flex items-center justify-between' }, [
          h('div', { class: 'flex items-center gap-3' }, [
            h('div', { class: `w-9 h-9 ${a.iconBg} rounded-xl flex items-center justify-center` }, [
              h(AppIcon, { name: props.icon, size: 17, class: a.iconText })
            ]),
            h('div', null, [
              h('h2', { class: 'text-slate-800 font-bold text-base leading-tight' }, props.title),
              props.level
                ? h('p', { class: 'text-slate-500 text-xs mt-0.5' }, props.level)
                : null,
            ]),
          ]),
          // Global progress pill
          totalCopies > 0
            ? h('div', { class: 'hidden sm:flex items-center gap-2 bg-slate-50 rounded-full px-4 py-1.5 ring-1 ring-slate-100' }, [
                h('div', { class: 'w-16 h-1.5 bg-slate-200 rounded-full overflow-hidden' }, [
                  h('div', { class: `h-full rounded-full transition-all bg-gradient-to-r ${a.progress}`, style: `width:${globalPct}%` })
                ]),
                h('span', { class: 'text-slate-600 text-xs font-semibold' }, `${globalPct}%`),
              ])
            : null,
        ]),

        // ── Section body ──
        h('div', { class: 'p-5 space-y-4' }, [
          // Optional top-level bilan CTA (Bac Blanc)
          props.showBilanBtn
            ? h('div', { class: 'flex items-center justify-between px-4 py-3 bg-indigo-50 rounded-xl ring-1 ring-indigo-100 mb-2' }, [
                h('div', { class: 'flex items-center gap-2 text-sm text-indigo-700' }, [
                  h(AppIcon, { name: 'report', size: 15 }),
                  h('span', { class: 'font-medium' }, 'Rapport de jury consolidé (J1 + J2)'),
                ]),
                h('button', {
                  class: 'inline-flex items-center gap-1.5 px-3.5 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium rounded-lg transition-colors shadow-sm',
                  onClick: () => emit('bilan')
                }, [h(AppIcon, { name: 'file-text', size: 13 }), 'Voir le rapport'])
              ])
            : null,

          // Exam cards
          ...props.exams.map(exam =>
            h(ExamCard, {
              key:       exam.id,
              exam,
              accent:    props.accent,
              dayLabel:  dayLabel(exam),
              onBilan:   (id) => emit('bilan', id),
              onResults: (id) => emit('results', id),
            })
          ),
        ]),
      ])
    }
  }
}
</script>
