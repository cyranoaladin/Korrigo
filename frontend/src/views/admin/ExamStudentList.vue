<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import api from '../../services/api'
import { ArrowLeft, Download, Users, Award, Clock, CheckCircle, AlertCircle, Search, ArrowUpDown } from 'lucide-vue-next'

const route = useRoute()
const router = useRouter()
const examId = route.params.examId
const loading = ref(true)
const error = ref(null)
const summary = ref(null)
const copies = ref([])
const searchQuery = ref('')
const sortField = ref('student_name')
const sortAsc = ref(true)
const filterStatus = ref('all')
const filterClasse = ref('all')
const filterGroupe = ref('all')

const fetchData = async () => {
  loading.value = true
  error.value = null
  try {
    const res = await api.get(`/exams/${examId}/student-list/`)
    summary.value = res.data.summary
    copies.value = res.data.copies
  } catch (e) {
    error.value = e.response?.data?.detail || 'Erreur lors du chargement.'
  } finally { loading.value = false }
}

const statusLabel = (s) => ({ GRADED:'Corrigée', READY:'Prête', STAGING:'En attente' }[s] || s)
const statusColor = (s) => ({ GRADED:'bg-emerald-100 text-emerald-700', READY:'bg-blue-100 text-blue-700', STAGING:'bg-amber-100 text-amber-700' }[s] || 'bg-gray-100 text-gray-600')
const scoreColor = (score) => {
  if (score === null) return 'text-gray-400'
  if (score >= 16) return 'text-emerald-600 font-bold'
  if (score >= 12) return 'text-blue-600 font-semibold'
  if (score >= 10) return 'text-amber-600 font-semibold'
  return 'text-red-600 font-bold'
}

const toggleSort = (field) => {
  if (sortField.value === field) { sortAsc.value = !sortAsc.value } else { sortField.value = field; sortAsc.value = true }
}

const uniqueClasses = computed(() => [...new Set(copies.value.map(c => c.student_class).filter(Boolean))].sort())
const uniqueGroupes = computed(() => [...new Set(copies.value.map(c => c.student_groupe).filter(Boolean))].sort())

const filteredCopies = computed(() => {
  let list = [...copies.value]
  if (filterStatus.value !== 'all') list = list.filter(c => c.status === filterStatus.value)
  if (filterClasse.value !== 'all') list = list.filter(c => c.student_class === filterClasse.value)
  if (filterGroupe.value !== 'all') list = list.filter(c => c.student_groupe === filterGroupe.value)
  if (searchQuery.value.trim()) {
    const q = searchQuery.value.toLowerCase()
    list = list.filter(c => (c.student_name||'').toLowerCase().includes(q) || (c.anonymous_id||'').toLowerCase().includes(q) || (c.corrector||'').toLowerCase().includes(q) || (c.student_class||'').toLowerCase().includes(q) || (c.student_groupe||'').toLowerCase().includes(q))
  }
  list.sort((a, b) => {
    let va = a[sortField.value], vb = b[sortField.value]
    if (va == null) va = sortAsc.value ? '\uffff' : ''
    if (vb == null) vb = sortAsc.value ? '\uffff' : ''
    if (typeof va === 'string') { va = va.toLowerCase(); vb = (vb+'').toLowerCase() }
    if (va < vb) return sortAsc.value ? -1 : 1
    if (va > vb) return sortAsc.value ? 1 : -1
    return 0
  })
  return list
})

const exportCSV = () => {
  const header = ['#','Anonymat','Élève','Classe','Groupe','Note','Statut','Correcteur','Appréciation']
  const rows = filteredCopies.value.map((c, i) => [i+1, c.anonymous_id, c.student_name||'—', c.student_class||'—', c.student_groupe||'—', c.total_score??'—', statusLabel(c.status), c.corrector||'—', c.has_appreciation?'Oui':'Non'])
  const csv = [header, ...rows].map(r => r.map(v => `"${v}"`).join(',')).join('\n')
  const blob = new Blob(['\uFEFF'+csv], {type:'text/csv;charset=utf-8;'})
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a'); a.href = url; a.download = `${summary.value?.exam_name||'exam'}_eleves.csv`
  document.body.appendChild(a); a.click(); document.body.removeChild(a); URL.revokeObjectURL(url)
}

onMounted(fetchData)
</script>

<template>
  <div class="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50/30 to-indigo-50/20 font-sans">
    <header class="bg-white/80 backdrop-blur-xl border-b border-slate-200/60 sticky top-0 z-50">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        <div class="flex items-center gap-3">
          <button @click="router.push({name:'AdminDashboard'})" class="p-2 rounded-lg hover:bg-slate-100"><ArrowLeft class="w-5 h-5 text-slate-600"/></button>
          <div>
            <h1 class="text-lg font-bold text-slate-800">Liste des élèves</h1>
            <p v-if="summary" class="text-xs text-slate-400">{{ summary.exam_name }}</p>
          </div>
        </div>
        <button @click="exportCSV" class="inline-flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-700"><Download class="w-4 h-4"/> Exporter CSV</button>
      </div>
    </header>

    <main class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
      <div v-if="loading" class="flex justify-center py-20"><div class="w-8 h-8 border-4 border-indigo-200 border-t-indigo-600 rounded-full animate-spin"></div></div>
      <div v-else-if="error" class="bg-red-50 rounded-2xl p-8 text-center"><AlertCircle class="w-10 h-10 text-red-300 mx-auto mb-3"/><p class="text-red-600">{{ error }}</p></div>

      <template v-else-if="summary">
        <div class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4">
          <div class="bg-white rounded-xl shadow-sm ring-1 ring-slate-100 px-4 py-3">
            <div class="flex items-center gap-2 mb-1"><Users class="w-4 h-4 text-slate-400"/><span class="text-xs text-slate-400 uppercase">Total</span></div>
            <p class="text-2xl font-bold text-slate-800">{{ summary.total_copies }}</p>
          </div>
          <div class="bg-white rounded-xl shadow-sm ring-1 ring-slate-100 px-4 py-3">
            <div class="flex items-center gap-2 mb-1"><CheckCircle class="w-4 h-4 text-emerald-400"/><span class="text-xs text-slate-400 uppercase">Corrigées</span></div>
            <p class="text-2xl font-bold text-emerald-600">{{ summary.graded }}</p>
          </div>
          <div class="bg-white rounded-xl shadow-sm ring-1 ring-slate-100 px-4 py-3">
            <div class="flex items-center gap-2 mb-1"><Clock class="w-4 h-4 text-blue-400"/><span class="text-xs text-slate-400 uppercase">Prêtes</span></div>
            <p class="text-2xl font-bold text-blue-600">{{ summary.ready }}</p>
          </div>
          <div class="bg-white rounded-xl shadow-sm ring-1 ring-slate-100 px-4 py-3">
            <div class="flex items-center gap-2 mb-1"><AlertCircle class="w-4 h-4 text-amber-400"/><span class="text-xs text-slate-400 uppercase">En attente</span></div>
            <p class="text-2xl font-bold text-amber-600">{{ summary.staging }}</p>
          </div>
          <div class="bg-white rounded-xl shadow-sm ring-1 ring-slate-100 px-4 py-3">
            <div class="flex items-center gap-2 mb-1"><Award class="w-4 h-4 text-indigo-400"/><span class="text-xs text-slate-400 uppercase">Moyenne</span></div>
            <p class="text-2xl font-bold text-indigo-600">{{ summary.average !== null ? summary.average.toFixed(2) : '—' }}</p>
          </div>
          <div class="bg-white rounded-xl shadow-sm ring-1 ring-slate-100 px-4 py-3">
            <div class="flex items-center gap-2 mb-1"><ArrowUpDown class="w-4 h-4 text-purple-400"/><span class="text-xs text-slate-400 uppercase">Min / Max</span></div>
            <p class="text-lg font-bold text-purple-600">{{ summary.min_score !== null ? summary.min_score.toFixed(2) : '—' }} / {{ summary.max_score !== null ? summary.max_score.toFixed(2) : '—' }}</p>
          </div>
        </div>

        <div class="flex flex-wrap gap-3 items-center">
          <div class="relative flex-1 min-w-[200px] max-w-md">
            <Search class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400"/>
            <input v-model="searchQuery" type="text" placeholder="Rechercher élève, anonymat, correcteur..." class="w-full pl-10 pr-4 py-2.5 bg-white rounded-xl ring-1 ring-slate-200 text-sm focus:ring-2 focus:ring-indigo-300 focus:outline-none"/>
          </div>
          <select v-model="filterClasse" class="px-4 py-2.5 bg-white rounded-xl ring-1 ring-slate-200 text-sm focus:ring-2 focus:ring-indigo-300 focus:outline-none">
            <option value="all">Toutes les classes</option>
            <option v-for="cl in uniqueClasses" :key="cl" :value="cl">{{ cl }}</option>
          </select>
          <select v-model="filterGroupe" class="px-4 py-2.5 bg-white rounded-xl ring-1 ring-slate-200 text-sm focus:ring-2 focus:ring-indigo-300 focus:outline-none">
            <option value="all">Tous les groupes</option>
            <option v-for="gr in uniqueGroupes" :key="gr" :value="gr">{{ gr }}</option>
          </select>
          <select v-model="filterStatus" class="px-4 py-2.5 bg-white rounded-xl ring-1 ring-slate-200 text-sm focus:ring-2 focus:ring-indigo-300 focus:outline-none">
            <option value="all">Tous les statuts</option>
            <option value="GRADED">Corrigées</option>
            <option value="READY">Prêtes</option>
            <option value="STAGING">En attente</option>
          </select>
          <span class="text-xs text-slate-400">{{ filteredCopies.length }} résultat(s)</span>
        </div>

        <div class="bg-white rounded-2xl shadow-sm ring-1 ring-slate-100 overflow-hidden">
          <div class="overflow-x-auto">
            <table class="w-full text-sm">
              <thead>
                <tr class="bg-slate-50/80 border-b border-slate-100">
                  <th class="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase">#</th>
                  <th class="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase cursor-pointer hover:text-indigo-600" @click="toggleSort('anonymous_id')">Anonymat <span v-if="sortField==='anonymous_id'">{{ sortAsc?'▲':'▼' }}</span></th>
                  <th class="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase cursor-pointer hover:text-indigo-600" @click="toggleSort('student_name')">Élève <span v-if="sortField==='student_name'">{{ sortAsc?'▲':'▼' }}</span></th>
                  <th class="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase cursor-pointer hover:text-indigo-600" @click="toggleSort('student_class')">Classe <span v-if="sortField==='student_class'">{{ sortAsc?'▲':'▼' }}</span></th>
                  <th class="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase cursor-pointer hover:text-indigo-600" @click="toggleSort('student_groupe')">Groupe <span v-if="sortField==='student_groupe'">{{ sortAsc?'▲':'▼' }}</span></th>
                  <th class="px-4 py-3 text-center text-xs font-semibold text-slate-500 uppercase cursor-pointer hover:text-indigo-600" @click="toggleSort('total_score')">Note /20 <span v-if="sortField==='total_score'">{{ sortAsc?'▲':'▼' }}</span></th>
                  <th class="px-4 py-3 text-center text-xs font-semibold text-slate-500 uppercase cursor-pointer hover:text-indigo-600" @click="toggleSort('status')">Statut <span v-if="sortField==='status'">{{ sortAsc?'▲':'▼' }}</span></th>
                  <th class="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase cursor-pointer hover:text-indigo-600" @click="toggleSort('corrector')">Correcteur <span v-if="sortField==='corrector'">{{ sortAsc?'▲':'▼' }}</span></th>
                  <th class="px-4 py-3 text-center text-xs font-semibold text-slate-500 uppercase">Appr.</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-slate-50">
                <tr v-for="(copy, idx) in filteredCopies" :key="copy.id" class="hover:bg-indigo-50/30 transition-colors">
                  <td class="px-4 py-3 text-slate-400 text-xs">{{ idx+1 }}</td>
                  <td class="px-4 py-3 font-mono text-xs text-slate-500">{{ copy.anonymous_id }}</td>
                  <td class="px-4 py-3 font-medium text-slate-800">{{ copy.student_name || '—' }}</td>
                  <td class="px-4 py-3 text-slate-500 text-xs">{{ copy.student_class || '—' }}</td>
                  <td class="px-4 py-3 text-slate-500 text-xs">{{ copy.student_groupe || '—' }}</td>
                  <td class="px-4 py-3 text-center"><span :class="scoreColor(copy.total_score)">{{ copy.total_score !== null ? copy.total_score.toFixed(2) : '—' }}</span></td>
                  <td class="px-4 py-3 text-center"><span :class="['px-2.5 py-1 rounded-full text-xs font-medium', statusColor(copy.status)]">{{ statusLabel(copy.status) }}</span></td>
                  <td class="px-4 py-3 text-slate-600 text-xs">{{ copy.corrector || '—' }}</td>
                  <td class="px-4 py-3 text-center"><span v-if="copy.has_appreciation" class="text-emerald-500">✓</span><span v-else class="text-slate-300">—</span></td>
                </tr>
                <tr v-if="filteredCopies.length===0"><td colspan="9" class="px-4 py-8 text-center text-slate-400">Aucun résultat.</td></tr>
              </tbody>
            </table>
          </div>
        </div>
      </template>
    </main>
  </div>
</template>
