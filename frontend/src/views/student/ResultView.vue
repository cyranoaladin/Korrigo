<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useAuthStore } from '../../stores/auth'
import api from '../../services/api'
import { useRouter } from 'vue-router'
import { LogOut, Download, ChevronDown, ChevronRight, BookOpen, Target, FileText, GraduationCap, MessageSquareText, ShieldCheck } from 'lucide-vue-next'

const auth = useAuthStore()
const router = useRouter()
const copies = ref([])
const selectedCopy = ref(null)
const loading = ref(true)
const expandedExercises = ref({})
const activeTab = ref('scores')
const pdfDirectUrl = ref(null)

const currentExerciseConfig = computed(() => {
  if (selectedCopy.value?.exercise_config && Object.keys(selectedCopy.value.exercise_config).length > 0) {
    const cfg = {}
    for (const [k, v] of Object.entries(selectedCopy.value.exercise_config)) cfg[parseInt(k)] = v
    return cfg
  }
  return { 1: { name: 'QCM — Géométrie', max: 5 }, 2: { name: 'Fonctions', max: 5 }, 3: { name: 'Probabilités', max: 4 }, 4: { name: 'Suites numériques', max: 6 } }
})
const currentQMax = computed(() => {
  if (selectedCopy.value?.q_max && Object.keys(selectedCopy.value.q_max).length > 0) return selectedCopy.value.q_max
  return {
    '1.1':1,'1.2':1,'1.3':1,'1.4':1,'1.5':1,
    '2.1':0.25,'2.2':0.50,'2.3':0.50,'2.4':0.75,'2.5':0.25,'2.6':0.75,'2.7':0.50,'2.8':0.25,'2.9':0.75,'2.10':0.50,
    '3.1':0.75,'3.2':0.50,'3.3':0.50,'3.4':1.00,'3.5':0.50,'3.6':0.75,
    '4.1':0.25,'4.2':0.25,'4.3':0.25,'4.4':0.75,'4.5':0.50,'4.6':0.75,'4.7':0.50,'4.8':1.00,'4.9':0.25,'4.10':0.25,'4.11':1.00,'4.12':0.25,
  }
})

const exerciseBreakdown = computed(() => {
  if (!selectedCopy.value) return {}
  const scores = selectedCopy.value.scores_details || {}
  const remarks = selectedCopy.value.remarks || {}
  const grouped = {}
  for (const [qid, score] of Object.entries(scores)) {
    const parts = qid.split('.')
    const exNum = parseInt(parts[0])
    if (!grouped[exNum]) {
      const c = currentExerciseConfig.value[exNum] || { name: `Exercice ${exNum}`, max: 0 }
      grouped[exNum] = { name: c.name, max: c.max, questions: [], total: 0 }
    }
    const n = parseFloat(score) || 0
    const qLabel = parts.length > 1 ? `Q${parts.slice(1).join('.')}` : 'QCM'
    grouped[exNum].questions.push({ qid, qLabel, score: n, maxScore: currentQMax.value[qid]||1, remark: (remarks[qid]&&remarks[qid].trim())?remarks[qid]:null })
    grouped[exNum].total += n
  }
  for (const k of Object.keys(grouped)) grouped[k].questions.sort((a,b) => { const ap=a.qid.split('.').map(Number), bp=b.qid.split('.').map(Number); return ap[0]-bp[0]||ap[1]-bp[1] })
  return grouped
})

const totalScore = computed(() => selectedCopy.value?.total_score ?? 0)
const scorePct = computed(() => (totalScore.value / 20) * 100)
const grade = computed(() => {
  const p = scorePct.value
  if (p>=80) return { label:'Excellent', color:'text-emerald-600', bg:'bg-emerald-50', bar:'bg-emerald-500', gradient:'from-emerald-500 to-teal-400' }
  if (p>=65) return { label:'Bien', color:'text-blue-600', bg:'bg-blue-50', bar:'bg-blue-500', gradient:'from-blue-500 to-indigo-400' }
  if (p>=50) return { label:'Satisfaisant', color:'text-amber-600', bg:'bg-amber-50', bar:'bg-amber-500', gradient:'from-amber-500 to-orange-400' }
  if (p>=35) return { label:'Insuffisant', color:'text-orange-600', bg:'bg-orange-50', bar:'bg-orange-500', gradient:'from-orange-500 to-red-400' }
  return { label:'À renforcer', color:'text-red-600', bg:'bg-red-50', bar:'bg-red-500', gradient:'from-red-500 to-rose-400' }
})
const toggleEx = (n) => { expandedExercises.value[n] = !expandedExercises.value[n] }
const qColor = (s,m) => { if(!m) return 'text-gray-400'; const p=(s/m)*100; if(p>=80) return 'text-emerald-600'; if(p>=50) return 'text-amber-600'; if(p>0) return 'text-orange-500'; return 'text-red-500' }
const exBarW = (t,m) => m?Math.min((t/m)*100,100)+'%':'0%'
const exBarC = (t,m) => { if(!m) return 'bg-gray-300'; const p=(t/m)*100; if(p>=80) return 'bg-emerald-500'; if(p>=50) return 'bg-amber-500'; if(p>0) return 'bg-orange-500'; return 'bg-red-500' }

const fetchCopies = async () => {
  loading.value = true
  try {
    const res = await api.get('/students/copies/')
    copies.value = res.data
    if (copies.value.length > 0) { selectedCopy.value = copies.value[0]; for (const qid of Object.keys(copies.value[0].scores_details||{})) expandedExercises.value[parseInt(qid.split('.')[0])]=true }
  } catch (e) { if(e.response?.status===401) router.push('/student/login'); console.error(e) }
  finally { loading.value = false }
}
const selectCopy = (copy) => { selectedCopy.value = copy; expandedExercises.value = {}; for (const qid of Object.keys(copy.scores_details||{})) expandedExercises.value[parseInt(qid.split('.')[0])]=true }
const loadPdf = () => {
  if (!selectedCopy.value?.final_pdf_url) return
  pdfDirectUrl.value = selectedCopy.value.final_pdf_url
}
watch(activeTab, (tab) => { if (tab === 'pdf' && !pdfDirectUrl.value) loadPdf() })
watch(selectedCopy, () => { pdfDirectUrl.value = null; if (activeTab.value === 'pdf') loadPdf() })
const downloadPdf = () => {
  if (!selectedCopy.value?.final_pdf_url) return
  const a = document.createElement('a')
  a.href = selectedCopy.value.final_pdf_url + '?download=1'
  a.download = `copie_corrigee_${selectedCopy.value.anonymous_id || 'copie'}.pdf`
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
}
const logout = async () => { await auth.logout(); router.push('/') }
onMounted(() => { fetchCopies() })
</script>

<template>
  <div class="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50/30 to-indigo-50/20 font-sans" data-testid="student-portal">
    <!-- NAVBAR -->
    <header class="bg-white/80 backdrop-blur-xl border-b border-slate-200/60 sticky top-0 z-50">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        <div class="flex items-center gap-3">
          <div class="w-8 h-8 rounded-lg bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center">
            <GraduationCap class="w-5 h-5 text-white" />
          </div>
          <span class="font-bold text-lg text-slate-800 tracking-tight">Korrigo</span>
          <span v-if="auth.user" class="hidden sm:inline text-sm text-slate-500 border-l border-slate-200 pl-3 ml-1">
            {{ auth.user.first_name }} {{ auth.user.last_name }}
          </span>
        </div>
        <button @click="logout" class="flex items-center gap-2 text-sm text-slate-500 hover:text-red-500 transition-colors px-3 py-2 rounded-lg hover:bg-red-50">
          <LogOut class="w-4 h-4" /> Déconnexion
        </button>
      </div>
    </header>

    <!-- LOADING -->
    <div v-if="loading" class="flex items-center justify-center h-[calc(100vh-4rem)]">
      <div class="text-center">
        <div class="w-10 h-10 border-4 border-indigo-200 border-t-indigo-600 rounded-full animate-spin mx-auto mb-4"></div>
        <p class="text-slate-500 text-sm">Chargement de vos résultats...</p>
      </div>
    </div>

    <!-- EMPTY -->
    <div v-else-if="copies.length === 0" class="flex items-center justify-center h-[calc(100vh-4rem)]">
      <div class="text-center">
        <FileText class="w-16 h-16 text-slate-300 mx-auto mb-4" />
        <h2 class="text-xl font-semibold text-slate-600 mb-2">Aucun résultat disponible</h2>
        <p class="text-slate-400">Vos résultats apparaîtront ici lorsqu'ils seront publiés.</p>
      </div>
    </div>

    <!-- MAIN -->
    <main v-else class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">

      <!-- TRANSPARENCY BANNER -->
      <div class="relative overflow-hidden rounded-2xl bg-white shadow-sm ring-1 ring-indigo-100">
        <div class="absolute inset-0 bg-gradient-to-br from-indigo-50/80 via-blue-50/40 to-transparent"></div>
        <div class="relative px-6 py-5 sm:px-8 sm:py-6">
          <div class="flex items-start gap-4">
            <div class="flex-shrink-0 w-10 h-10 rounded-xl bg-gradient-to-br from-indigo-500 to-blue-600 flex items-center justify-center shadow-md shadow-indigo-200">
              <ShieldCheck class="w-5 h-5 text-white" />
            </div>
            <div class="flex-1 min-w-0">
              <h3 class="text-sm font-bold text-indigo-900 tracking-tight mb-3">Garanties du processus de correction</h3>
              <ul class="space-y-2 text-xs sm:text-sm text-slate-600 leading-relaxed">
                <li class="flex items-start gap-2">
                  <span class="mt-1.5 w-1.5 h-1.5 rounded-full bg-indigo-400 flex-shrink-0"></span>
                  <span>Les copies ont été corrigées <strong class="text-slate-800">uniquement par les enseignants correcteurs</strong>.</span>
                </li>
                <li class="flex items-start gap-2">
                  <span class="mt-1.5 w-1.5 h-1.5 rounded-full bg-indigo-400 flex-shrink-0"></span>
                  <span><strong class="text-slate-800">Aucune intelligence artificielle</strong> n'a été utilisée pour corriger les copies.</span>
                </li>
                <li class="flex items-start gap-2">
                  <span class="mt-1.5 w-1.5 h-1.5 rounded-full bg-indigo-400 flex-shrink-0"></span>
                  <span>Les copies ont été <strong class="text-slate-800">anonymisées</strong> avant correction.</span>
                </li>
                <li class="flex items-start gap-2">
                  <span class="mt-1.5 w-1.5 h-1.5 rounded-full bg-indigo-400 flex-shrink-0"></span>
                  <span>Leur répartition entre les correcteurs a été effectuée de manière <strong class="text-slate-800">aléatoire</strong>.</span>
                </li>
                <li class="flex items-start gap-2">
                  <span class="mt-1.5 w-1.5 h-1.5 rounded-full bg-indigo-400 flex-shrink-0"></span>
                  <span>La correction a été réalisée à partir du <strong class="text-slate-800">sujet, du barème et des consignes</strong> de l'épreuve.</span>
                </li>
                <li class="flex items-start gap-2">
                  <span class="mt-1.5 w-1.5 h-1.5 rounded-full bg-indigo-400 flex-shrink-0"></span>
                  <span>Un <strong class="text-slate-800">contrôle complémentaire</strong> a été effectué après finalisation afin de vérifier que toutes les questions avaient bien été examinées.</span>
                </li>
              </ul>
              <p class="mt-3 text-xs font-medium text-indigo-700/80 italic">Ce dispositif vise à garantir l'équité, la rigueur et la transparence du processus de correction.</p>
            </div>
          </div>
        </div>
      </div>

      <!-- EXAM TITLE -->
      <div class="text-center">
        <h1 class="text-2xl sm:text-3xl font-extrabold text-slate-800 tracking-tight">Bac Blanc — Mathématiques</h1>
        <p class="text-sm text-slate-400 mt-1">Février 2026</p>
      </div>

      <!-- COPY SELECTOR (if multiple) -->
      <div v-if="copies.length > 1" class="flex gap-3 overflow-x-auto pb-2">
        <button v-for="copy in (copies || []).filter(c => !!c)" :key="copy.id" @click="selectCopy(copy)"
          :class="['px-4 py-2.5 rounded-xl text-sm font-medium transition-all whitespace-nowrap',
            selectedCopy?.id === copy.id
              ? 'bg-white text-indigo-700 shadow-md shadow-indigo-100 ring-1 ring-indigo-200'
              : 'bg-white/50 text-slate-500 hover:bg-white hover:shadow-sm']">
          {{ copy.exam_name }}
          <span class="ml-2 font-bold">{{ copy.total_score.toFixed(2) }}/20</span>
        </button>
      </div>

      <!-- ═══════════════ HERO SCORE CARD ═══════════════ -->
      <div v-if="selectedCopy" class="relative overflow-hidden rounded-2xl bg-white shadow-lg shadow-slate-200/50 ring-1 ring-slate-100">
        <div class="absolute inset-0 opacity-5">
          <div :class="['absolute -right-20 -top-20 w-80 h-80 rounded-full bg-gradient-to-br', grade.gradient]"></div>
          <div :class="['absolute -left-10 -bottom-10 w-60 h-60 rounded-full bg-gradient-to-tr', grade.gradient]"></div>
        </div>
        <div class="relative px-6 py-8 sm:px-10 sm:py-10">
          <div class="flex flex-col sm:flex-row items-center sm:items-start gap-6 sm:gap-10">
            <!-- Score circle -->
            <div class="relative flex-shrink-0">
              <svg class="w-32 h-32 sm:w-36 sm:h-36 -rotate-90" viewBox="0 0 120 120">
                <circle cx="60" cy="60" r="52" fill="none" stroke="#e2e8f0" stroke-width="8" />
                <circle cx="60" cy="60" r="52" fill="none" :stroke="scorePct >= 80 ? '#10b981' : scorePct >= 65 ? '#3b82f6' : scorePct >= 50 ? '#f59e0b' : scorePct >= 35 ? '#f97316' : '#ef4444'"
                  stroke-width="8" stroke-linecap="round"
                  :stroke-dasharray="`${scorePct * 3.267} 326.7`"
                  class="transition-all duration-1000 ease-out" />
              </svg>
              <div class="absolute inset-0 flex flex-col items-center justify-center">
                <span class="text-3xl sm:text-4xl font-black text-slate-800">{{ totalScore.toFixed(2) }}</span>
                <span class="text-sm text-slate-400 font-medium">/ 20</span>
              </div>
            </div>
            <!-- Info -->
            <div class="flex-1 text-center sm:text-left">
              <h1 class="text-2xl sm:text-3xl font-bold text-slate-800 mb-1">{{ selectedCopy.exam_name }}</h1>
              <p class="text-slate-400 text-sm mb-4">{{ selectedCopy.date }}</p>
              <span :class="['inline-flex items-center gap-1.5 px-4 py-1.5 rounded-full text-sm font-semibold', grade.bg, grade.color]">
                <Target class="w-4 h-4" /> {{ grade.label }}
              </span>
              <!-- Exercise mini bars -->
              <div class="mt-6 grid grid-cols-2 sm:grid-cols-4 gap-3">
                <div v-for="(ex, exNum) in exerciseBreakdown" :key="'mini-'+exNum">
                  <div v-if="ex" class="bg-slate-50/80 rounded-xl px-3 py-2.5">
                  <div class="flex justify-between items-baseline mb-1.5">
                    <span class="text-xs font-semibold text-slate-500">Ex. {{ exNum }}</span>
                    <span class="text-xs font-bold text-slate-700">{{ ex.total.toFixed(2) }}/{{ ex.max }}</span>
                  </div>
                  <div class="h-1.5 bg-slate-200 rounded-full overflow-hidden">
                    <div :class="['h-full rounded-full transition-all duration-700', exBarC(ex.total, ex.max)]" :style="{width: exBarW(ex.total, ex.max)}"></div>
                  </div>
                </div>
              </div>
            </div>
            <!-- Download -->
            <div class="flex-shrink-0">
              <button v-if="selectedCopy.final_pdf_url" @click="downloadPdf"
                class="inline-flex items-center gap-2 px-5 py-3 bg-gradient-to-r from-indigo-500 to-purple-600 text-white rounded-xl font-semibold text-sm shadow-lg shadow-indigo-200 hover:shadow-indigo-300 hover:scale-[1.02] transition-all">
                <Download class="w-4 h-4" /> Télécharger le PDF
              </button>
            </div>
          </div>
        </div>
      </div>
      </div>

      <!-- ═══════════════ TABS ═══════════════ -->
      <div v-if="selectedCopy" class="flex gap-1 bg-white/60 backdrop-blur rounded-xl p-1 shadow-sm ring-1 ring-slate-100 w-fit">
        <button @click="activeTab='scores'" :class="['px-5 py-2.5 rounded-lg text-sm font-medium transition-all flex items-center gap-2', activeTab==='scores' ? 'bg-white shadow-sm text-indigo-700' : 'text-slate-500 hover:text-slate-700']">
          <BookOpen class="w-4 h-4" /> Détail des notes
        </button>
        <button @click="activeTab='appreciation'" :class="['px-5 py-2.5 rounded-lg text-sm font-medium transition-all flex items-center gap-2', activeTab==='appreciation' ? 'bg-white shadow-sm text-indigo-700' : 'text-slate-500 hover:text-slate-700']">
          <MessageSquareText class="w-4 h-4" /> Appréciation
        </button>
        <button v-if="selectedCopy.final_pdf_url" @click="activeTab='pdf'" :class="['px-5 py-2.5 rounded-lg text-sm font-medium transition-all flex items-center gap-2', activeTab==='pdf' ? 'bg-white shadow-sm text-indigo-700' : 'text-slate-500 hover:text-slate-700']">
          <FileText class="w-4 h-4" /> Copie corrigée
        </button>
      </div>

      <!-- ═══════════════ TAB: SCORES ═══════════════ -->
      <div v-if="selectedCopy && activeTab==='scores'" class="space-y-4">
        <div v-for="(ex, exNum) in exerciseBreakdown" :key="'ex-'+exNum">
          <div v-if="ex"
            class="bg-white rounded-2xl shadow-sm ring-1 ring-slate-100 overflow-hidden transition-all">
          <!-- Exercise header -->
          <button @click="toggleEx(exNum)" class="w-full px-6 py-5 flex items-center justify-between hover:bg-slate-50/50 transition-colors">
            <div class="flex items-center gap-4">
              <div :class="['w-10 h-10 rounded-xl flex items-center justify-center font-bold text-sm',
                (ex.total/ex.max)>=0.8 ? 'bg-emerald-100 text-emerald-700' :
                (ex.total/ex.max)>=0.5 ? 'bg-amber-100 text-amber-700' :
                (ex.total/ex.max)>0 ? 'bg-orange-100 text-orange-700' : 'bg-red-100 text-red-700']">
                {{ exNum }}
              </div>
              <div class="text-left">
                <h3 class="font-semibold text-slate-800">Exercice {{ exNum }} — {{ ex.name }}</h3>
                <div class="flex items-center gap-3 mt-1">
                  <span class="text-sm font-bold" :class="(ex.total/ex.max)>=0.5?'text-slate-700':'text-red-600'">{{ ex.total.toFixed(2) }} / {{ ex.max }}</span>
                  <div class="w-24 h-1.5 bg-slate-200 rounded-full overflow-hidden">
                    <div :class="['h-full rounded-full', exBarC(ex.total, ex.max)]" :style="{width: exBarW(ex.total, ex.max)}"></div>
                  </div>
                </div>
              </div>
            </div>
            <ChevronDown v-if="expandedExercises[exNum]" class="w-5 h-5 text-slate-400" />
            <ChevronRight v-else class="w-5 h-5 text-slate-400" />
          </button>
          <!-- Questions -->
          <div v-if="expandedExercises[exNum]" class="border-t border-slate-100">
            <div v-for="(q, qi) in (ex.questions || []).filter(item => !!item)" :key="q.qid"
              :class="['px-6 py-4', qi < ex.questions.length-1 ? 'border-b border-slate-50' : '']">
              <div class="flex items-center justify-between">
                <div class="flex items-center gap-3">
                  <span class="text-sm font-mono font-semibold text-slate-400 w-10">{{ q.qid }}</span>
                  <span class="text-sm text-slate-600">{{ q.qLabel }}</span>
                </div>
                <div class="flex items-center gap-2">
                  <span :class="['text-sm font-bold', qColor(q.score, q.maxScore)]">{{ q.score.toFixed(2) }}</span>
                  <span class="text-xs text-slate-400">/ {{ q.maxScore.toFixed(2) }}</span>
                  <!-- mini dot -->
                  <div :class="['w-2 h-2 rounded-full', q.score >= q.maxScore*0.8 ? 'bg-emerald-400' : q.score >= q.maxScore*0.5 ? 'bg-amber-400' : q.score > 0 ? 'bg-orange-400' : 'bg-red-400']"></div>
                </div>
              </div>
              <!-- Remark -->
              <div v-if="q.remark" class="mt-2.5 ml-13 pl-4 border-l-2 border-indigo-200 bg-indigo-50/50 rounded-r-lg py-2.5 pr-4">
                <p class="text-xs text-indigo-800/80 leading-relaxed">{{ q.remark }}</p>
              </div>
            </div>
          </div>
        </div>
      </div>
      </div>

      <!-- ═══════════════ TAB: APPRECIATION ═══════════════ -->
      <div v-if="selectedCopy && activeTab==='appreciation'" class="space-y-4">
        <!-- Global appreciation -->
        <div v-if="selectedCopy.global_appreciation" class="bg-white rounded-2xl shadow-sm ring-1 ring-slate-100 overflow-hidden">
          <div class="px-6 py-4 border-b border-slate-100 flex items-center gap-3">
            <div class="w-8 h-8 rounded-lg bg-amber-100 flex items-center justify-center">
              <MessageSquareText class="w-4 h-4 text-amber-600" />
            </div>
            <h3 class="font-semibold text-slate-800">Appréciation générale</h3>
          </div>
          <div class="px-6 py-5">
            <p class="text-slate-700 leading-relaxed whitespace-pre-line text-sm">{{ selectedCopy.global_appreciation }}</p>
          </div>
        </div>
        <div v-else class="bg-white rounded-2xl shadow-sm ring-1 ring-slate-100 p-8 text-center">
          <MessageSquareText class="w-10 h-10 text-slate-300 mx-auto mb-3" />
          <p class="text-slate-400 text-sm">Aucune appréciation disponible.</p>
        </div>

      </div>

      <!-- ═══════════════ TAB: PDF ═══════════════ -->
      <div v-if="selectedCopy && activeTab==='pdf'" class="space-y-2">
        <div class="bg-white rounded-2xl shadow-sm ring-1 ring-slate-100 overflow-hidden" style="height: 75vh;">
          <iframe v-if="pdfDirectUrl" :src="pdfDirectUrl" class="w-full h-full border-0" />
          <div v-else class="flex items-center justify-center h-full">
            <p class="text-slate-400">PDF non disponible.</p>
          </div>
        </div>
        <p v-if="pdfDirectUrl" class="text-center text-xs text-slate-400">
          Le PDF ne s'affiche pas ?
          <a :href="selectedCopy.final_pdf_url + '?download=1'" class="text-indigo-600 hover:underline font-medium">Télécharger directement</a>
        </p>
      </div>

    </main>
  </div>
</template>
