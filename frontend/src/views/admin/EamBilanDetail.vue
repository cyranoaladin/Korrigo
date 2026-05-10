<template>
  <div class="p-6 max-w-6xl mx-auto">
    <!-- Header -->
    <div class="mb-6">
      <div class="flex items-center gap-4 mb-4">
        <button
          @click="$router.go(-1)"
          class="inline-flex items-center gap-2 text-gray-600 hover:text-gray-900 transition-colors"
        >
          <AppIcon name="arrow-left" :size="16" />
          Retour
        </button>
        <h1 class="text-2xl font-bold text-gray-900">
          Bilan EAM BLANCHE 2026 — {{ formatDate(report?.generated_at) }}
        </h1>
      </div>
      <div class="flex flex-wrap items-center gap-3">
        <span :class="getStatusClass(report?.status)" class="px-3 py-1 text-sm font-medium rounded-full">
          {{ getStatusText(report?.status) }}
        </span>
        <span class="text-sm text-gray-600">
          <span class="font-medium">Copies :</span> {{ meta?.n_copies ?? 'N/A' }}
        </span>
        <span class="text-sm text-gray-600">
          <span class="font-medium">Généré par :</span> {{ report?.generated_by || 'N/A' }}
        </span>
        <span class="text-sm text-gray-500">{{ report?.llm_model }}</span>
      </div>
    </div>

    <!-- Loading -->
    <div v-if="isLoading" class="text-center py-16">
      <div class="inline-flex items-center gap-3 text-gray-600">
        <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></div>
        <span class="text-lg">Chargement du bilan...</span>
      </div>
    </div>

    <!-- Error -->
    <div v-else-if="error" class="text-center py-12 bg-red-50 rounded-xl border border-red-200">
      <AppIcon name="alert-triangle" :size="40" class="text-red-500 mx-auto mb-3" />
      <h3 class="text-lg font-semibold text-red-800 mb-2">Erreur de chargement</h3>
      <p class="text-red-600 mb-4">{{ error }}</p>
      <button @click="fetchBilan" class="bg-indigo-600 text-white px-4 py-2 rounded-lg hover:bg-indigo-700">
        Réessayer
      </button>
    </div>

    <!-- Bilan Content -->
    <div v-else-if="report?.status === 'DONE'" class="space-y-8">

      <!-- ── S0 : Synthèse exécutive ── -->
      <section class="bg-white border border-gray-200 rounded-xl p-6 shadow-sm">
        <h2 class="text-xl font-semibold text-gray-900 mb-4 flex items-center gap-2">
          <AppIcon name="file-text" :size="20" class="text-indigo-600" />
          Synthèse exécutive
        </h2>
        <div class="prose max-w-none text-gray-700 leading-relaxed whitespace-pre-line">{{ s0?.content || 'N/A' }}</div>
      </section>

      <!-- ── S1 : Tableau de bord ── -->
      <section class="bg-white border border-gray-200 rounded-xl p-6 shadow-sm">
        <h2 class="text-xl font-semibold text-gray-900 mb-6 flex items-center gap-2">
          <AppIcon name="bar-chart" :size="20" class="text-indigo-600" />
          Tableau de bord statistique
        </h2>

        <!-- Indicateurs globaux -->
        <div class="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
          <div class="bg-blue-50 p-4 rounded-lg text-center">
            <div class="text-3xl font-bold text-blue-900">{{ meta?.mean?.toFixed(1) ?? 'N/A' }}/20</div>
            <div class="text-sm text-blue-700 mt-1">Moyenne générale</div>
          </div>
          <div class="bg-green-50 p-4 rounded-lg text-center">
            <div class="text-3xl font-bold text-green-900">{{ meta?.median?.toFixed(1) ?? 'N/A' }}/20</div>
            <div class="text-sm text-green-700 mt-1">Médiane</div>
          </div>
          <div class="bg-purple-50 p-4 rounded-lg text-center">
            <div class="text-3xl font-bold text-purple-900">{{ meta?.pct_above_10?.toFixed(1) ?? 'N/A' }}%</div>
            <div class="text-sm text-purple-700 mt-1">Taux ≥ 10/20</div>
          </div>
          <div class="bg-orange-50 p-4 rounded-lg text-center">
            <div class="text-3xl font-bold text-orange-900">{{ meta?.n_copies ?? 'N/A' }}</div>
            <div class="text-sm text-orange-700 mt-1">Copies analysées</div>
          </div>
        </div>

        <!-- Partie A vs Partie B -->
        <div class="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
          <div class="bg-indigo-50 rounded-xl p-5">
            <h3 class="font-semibold text-indigo-900 mb-3">Partie A — Automatismes (6 pts)</h3>
            <div class="space-y-2 text-sm">
              <div class="flex justify-between">
                <span class="text-gray-600">Moyenne</span>
                <span class="font-bold text-indigo-800">{{ autoStats?.mean?.toFixed(2) ?? 'N/A' }} / {{ autoStats?.max_points ?? 6 }} pts</span>
              </div>
              <div class="flex justify-between">
                <span class="text-gray-600">Taux de réussite</span>
                <span :class="getRateClass(autoStats?.mean_pct)" class="font-bold">{{ autoStats?.mean_pct?.toFixed(1) ?? 'N/A' }}%</span>
              </div>
              <div class="w-full bg-gray-200 rounded-full h-3 mt-2">
                <div class="bg-indigo-500 h-3 rounded-full transition-all" :style="{ width: (autoStats?.mean_pct ?? 0) + '%' }"></div>
              </div>
            </div>
          </div>
          <div class="bg-emerald-50 rounded-xl p-5">
            <h3 class="font-semibold text-emerald-900 mb-3">Partie B — Exercices (14 pts)</h3>
            <div class="space-y-2 text-sm">
              <div class="flex justify-between">
                <span class="text-gray-600">Moyenne</span>
                <span class="font-bold text-emerald-800">{{ exoStats?.mean?.toFixed(2) ?? 'N/A' }} / {{ exoStats?.max_points ?? 14 }} pts</span>
              </div>
              <div class="flex justify-between">
                <span class="text-gray-600">Taux de réussite</span>
                <span :class="getRateClass(exoStats?.mean_pct)" class="font-bold">{{ exoStats?.mean_pct?.toFixed(1) ?? 'N/A' }}%</span>
              </div>
              <div class="w-full bg-gray-200 rounded-full h-3 mt-2">
                <div class="bg-emerald-500 h-3 rounded-full transition-all" :style="{ width: (exoStats?.mean_pct ?? 0) + '%' }"></div>
              </div>
            </div>
          </div>
        </div>

        <!-- Comparaison A vs B -->
        <div v-if="s1?.comparison" class="bg-amber-50 border border-amber-200 rounded-lg px-5 py-3 mb-6 text-sm">
          <span class="font-semibold text-amber-800">Analyse comparative :</span>
          <span class="text-amber-700 ml-2">
            Partie {{ s1.comparison.stronger_part }} plus solide ({{ s1.comparison.diff_pct?.toFixed(1) }}pts d'écart).
            Partie {{ s1.comparison.weaker_part }} à renforcer.
          </span>
        </div>

        <!-- Distribution -->
        <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <h3 class="text-base font-medium text-gray-900 mb-3">Distribution des notes</h3>
            <div class="bg-gray-50 rounded-lg p-4 space-y-2">
              <div v-for="{ label, key, color } in distributionRows" :key="key" class="flex items-center gap-3">
                <div class="w-36 text-sm text-gray-700">{{ label }}</div>
                <div class="flex-1 bg-gray-200 rounded-full h-4 overflow-hidden">
                  <div :class="color" class="h-4 rounded-full transition-all" :style="{ width: distBarWidth(key) }"></div>
                </div>
                <div class="w-10 text-sm font-semibold text-right">{{ meta?.distribution?.[key] ?? 0 }}</div>
              </div>
            </div>
          </div>

          <!-- Stats par classe -->
          <div v-if="s1?.stats_by_class?.length">
            <h3 class="text-base font-medium text-gray-900 mb-3">Résultats par classe</h3>
            <div class="bg-gray-50 rounded-lg p-4 space-y-1 max-h-48 overflow-y-auto">
              <div v-for="cls in s1.stats_by_class" :key="cls.class_name" class="flex justify-between text-sm py-1 border-b border-gray-200 last:border-0">
                <span class="text-gray-700 font-medium">{{ cls.class_name }}</span>
                <span class="font-semibold">{{ cls.mean?.toFixed(1) }}/20</span>
                <span class="text-gray-500 text-xs">{{ cls.n_students }} élèves</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      <!-- ── S2A : Automatismes ── -->
      <section class="bg-white border border-gray-200 rounded-xl p-6 shadow-sm">
        <h2 class="text-xl font-semibold text-gray-900 mb-4 flex items-center gap-2">
          <AppIcon name="check-square" :size="20" class="text-indigo-600" />
          Partie A — Automatismes (12 questions QCM, 6 pts)
        </h2>

        <!-- Top réussites / Difficultés -->
        <div class="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
          <div v-if="s2a?.top_success?.length" class="bg-green-50 rounded-lg p-4">
            <h3 class="text-sm font-semibold text-green-800 mb-3">Top 3 réussites</h3>
            <div v-for="q in s2a.top_success" :key="q.question?.id" class="flex justify-between text-sm py-1">
              <span class="text-gray-700">{{ q.question?.label }}</span>
              <span class="font-semibold text-green-700">{{ q.success_rate?.toFixed(1) }}%</span>
            </div>
          </div>
          <div v-if="s2a?.top_failures?.length" class="bg-red-50 rounded-lg p-4">
            <h3 class="text-sm font-semibold text-red-800 mb-3">Top 3 difficultés</h3>
            <div v-for="q in s2a.top_failures" :key="q.question?.id" class="flex justify-between text-sm py-1">
              <span class="text-gray-700">{{ q.question?.label }}</span>
              <span class="font-semibold text-red-700">{{ q.success_rate?.toFixed(1) }}%</span>
            </div>
          </div>
        </div>

        <!-- Tableau questions -->
        <div class="overflow-x-auto">
          <table class="min-w-full text-sm">
            <thead class="bg-gray-100">
              <tr>
                <th class="px-4 py-2 text-left text-gray-700 font-medium">Question</th>
                <th class="px-4 py-2 text-right text-gray-700 font-medium">Max</th>
                <th class="px-4 py-2 text-right text-gray-700 font-medium">Moy.</th>
                <th class="px-4 py-2 text-right text-gray-700 font-medium">Taux</th>
                <th class="px-4 py-2 text-right text-gray-700 font-medium">Copies</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-gray-100">
              <tr v-for="q in s2a?.questions" :key="q.question?.id" class="hover:bg-gray-50">
                <td class="px-4 py-2 text-gray-900">{{ q.question?.label }}</td>
                <td class="px-4 py-2 text-right text-gray-600">{{ q.question?.max_points }}</td>
                <td class="px-4 py-2 text-right font-medium">{{ q.mean?.toFixed(2) }}</td>
                <td class="px-4 py-2 text-right" :class="getRateClass(q.success_rate)">
                  {{ q.success_rate?.toFixed(1) }}%
                </td>
                <td class="px-4 py-2 text-right text-gray-500">{{ q.n_attempts }}</td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- Analyse qualitative -->
        <div v-if="s2a?.content" class="mt-6 bg-indigo-50 rounded-lg p-5">
          <h3 class="text-sm font-semibold text-indigo-900 mb-3">Analyse pédagogique</h3>
          <p class="text-gray-700 leading-relaxed whitespace-pre-line text-sm">{{ s2a.content }}</p>
        </div>
      </section>

      <!-- ── S2B : Exercices ── -->
      <section class="bg-white border border-gray-200 rounded-xl p-6 shadow-sm">
        <h2 class="text-xl font-semibold text-gray-900 mb-6 flex items-center gap-2">
          <AppIcon name="edit" :size="20" class="text-emerald-600" />
          Partie B — Exercices (3 exercices, 14 pts)
        </h2>

        <div class="space-y-8">
          <div v-for="ex in s2b?.exercises" :key="ex.id" class="border border-gray-200 rounded-lg overflow-hidden">
            <!-- En-tête exercice -->
            <div class="bg-emerald-50 px-5 py-3 flex items-center justify-between">
              <h3 class="font-semibold text-emerald-900">{{ ex.name }}</h3>
              <div class="flex items-center gap-4 text-sm">
                <span class="text-gray-600">Max : <strong>{{ ex.max_points }} pts</strong></span>
                <span class="text-gray-600">Moy. : <strong>{{ ex.mean_score?.toFixed(2) }} pts</strong></span>
                <span :class="getRateClass(ex.mean_pct)" class="font-semibold">{{ ex.mean_pct?.toFixed(1) }}%</span>
              </div>
            </div>

            <!-- Sous-parties -->
            <div class="p-4">
              <table class="min-w-full text-sm mb-4">
                <thead class="bg-gray-50">
                  <tr>
                    <th class="px-3 py-2 text-left text-gray-700 font-medium">Sous-partie</th>
                    <th class="px-3 py-2 text-right text-gray-700 font-medium">Max</th>
                    <th class="px-3 py-2 text-right text-gray-700 font-medium">Moy.</th>
                    <th class="px-3 py-2 text-right text-gray-700 font-medium">Taux</th>
                  </tr>
                </thead>
                <tbody class="divide-y divide-gray-100">
                  <tr v-for="sp in ex.subparts" :key="sp.id" class="hover:bg-gray-50">
                    <td class="px-3 py-2 text-gray-900">{{ sp.label }}</td>
                    <td class="px-3 py-2 text-right text-gray-600">{{ sp.max_points }}</td>
                    <td class="px-3 py-2 text-right font-medium">{{ sp.mean_score?.toFixed(2) }}</td>
                    <td class="px-3 py-2 text-right" :class="getRateClass(sp.success_rate)">{{ sp.success_rate?.toFixed(1) }}%</td>
                  </tr>
                </tbody>
              </table>

              <!-- Analyse de l'exercice -->
              <div v-if="ex.analysis" class="bg-emerald-50 rounded-lg p-4">
                <p class="text-gray-700 leading-relaxed whitespace-pre-line text-sm">{{ ex.analysis }}</p>
              </div>
            </div>
          </div>
        </div>
      </section>

      <!-- ── S3 : Tableau complet questions ── -->
      <section class="bg-white border border-gray-200 rounded-xl p-6 shadow-sm">
        <h2 class="text-xl font-semibold text-gray-900 mb-4 flex items-center gap-2">
          <AppIcon name="list" :size="20" class="text-gray-600" />
          Analyse par question ({{ s3?.n_questions }} questions)
        </h2>
        <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <!-- Automatismes -->
          <div>
            <h3 class="text-sm font-semibold text-indigo-800 mb-3 uppercase tracking-wide">Automatismes (A)</h3>
            <div class="overflow-x-auto">
              <table class="min-w-full text-xs">
                <thead class="bg-indigo-50">
                  <tr>
                    <th class="px-3 py-2 text-left">Question</th>
                    <th class="px-3 py-2 text-right">Taux</th>
                    <th class="px-3 py-2 text-right">Moy.</th>
                  </tr>
                </thead>
                <tbody class="divide-y divide-gray-100">
                  <tr v-for="q in s3?.auto_questions" :key="q.question?.id" class="hover:bg-gray-50">
                    <td class="px-3 py-2 text-gray-800">{{ q.question?.label }}</td>
                    <td class="px-3 py-2 text-right" :class="getRateClass(q.success_rate)">{{ q.success_rate?.toFixed(1) }}%</td>
                    <td class="px-3 py-2 text-right text-gray-600">{{ q.mean?.toFixed(2) }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
          <!-- Exercices -->
          <div>
            <h3 class="text-sm font-semibold text-emerald-800 mb-3 uppercase tracking-wide">Exercices (B)</h3>
            <div class="overflow-x-auto">
              <table class="min-w-full text-xs">
                <thead class="bg-emerald-50">
                  <tr>
                    <th class="px-3 py-2 text-left">Question</th>
                    <th class="px-3 py-2 text-right">Taux</th>
                    <th class="px-3 py-2 text-right">Moy.</th>
                  </tr>
                </thead>
                <tbody class="divide-y divide-gray-100">
                  <tr v-for="q in s3?.exo_questions" :key="q.question?.id" class="hover:bg-gray-50">
                    <td class="px-3 py-2 text-gray-800">{{ q.question?.label }}</td>
                    <td class="px-3 py-2 text-right" :class="getRateClass(q.success_rate)">{{ q.success_rate?.toFixed(1) }}%</td>
                    <td class="px-3 py-2 text-right text-gray-600">{{ q.mean?.toFixed(2) }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </section>

      <!-- ── S4 : Recommandations ── -->
      <section class="bg-white border border-gray-200 rounded-xl p-6 shadow-sm">
        <h2 class="text-xl font-semibold text-gray-900 mb-6 flex items-center gap-2">
          <AppIcon name="trending-up" :size="20" class="text-amber-600" />
          Recommandations pédagogiques
        </h2>
        <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div v-for="(bloc, key) in s4?.blocks" :key="key" class="rounded-xl p-5" :class="blocClass(key)">
            <h3 class="font-semibold mb-3" :class="blocTitleClass(key)">{{ bloc.title }}</h3>
            <p class="text-sm text-gray-700 leading-relaxed whitespace-pre-line">{{ bloc.content }}</p>
          </div>
        </div>
      </section>

    </div>

    <!-- Bilan not done -->
    <div v-else-if="report" class="text-center py-12 bg-gray-50 rounded-xl">
      <AppIcon name="clock" :size="40" class="text-gray-400 mx-auto mb-3" />
      <p class="text-gray-600">Le bilan est en cours de génération ou contient une erreur.</p>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import AppIcon from '../../icons/AppIcon.vue'
import { bilanService } from '../../services/bilan'

const route = useRoute()

const report = ref(null)
const sections = ref({})
const isLoading = ref(false)
const error = ref(null)

// ── Computed sections ─────────────────────────────────────────────
const meta = computed(() => report.value?.metadata || {})
const s0 = computed(() => sections.value?.S0 || null)
const s1 = computed(() => sections.value?.S1 || null)
const s2a = computed(() => sections.value?.S2A || null)
const s2b = computed(() => sections.value?.S2B || null)
const s3 = computed(() => sections.value?.S3 || null)
const s4 = computed(() => sections.value?.S4 || null)
const autoStats = computed(() => s1.value?.automatismes_stats || null)
const exoStats = computed(() => s1.value?.exercices_stats || null)

// ── Distribution config ───────────────────────────────────────────
const distributionRows = [
  { label: 'Très bien (≥16)', key: 'tb', color: 'bg-green-500' },
  { label: 'Bien (14–15)', key: 'b', color: 'bg-lime-500' },
  { label: 'Assez bien (12–13)', key: 'ab', color: 'bg-yellow-400' },
  { label: 'Passable (10–11)', key: 'p', color: 'bg-orange-400' },
  { label: 'Insuffisant (<10)', key: 'insuffisant', color: 'bg-red-500' },
]

const distBarWidth = (key) => {
  const total = meta.value?.n_copies || 1
  const count = meta.value?.distribution?.[key] ?? 0
  return `${Math.round(count / total * 100)}%`
}

// ── Helpers ───────────────────────────────────────────────────────
const getStatusClass = (s) => ({
  DONE: 'bg-green-100 text-green-800',
  GENERATING: 'bg-blue-100 text-blue-800',
  ERROR: 'bg-red-100 text-red-800',
}[s] || 'bg-gray-100 text-gray-800')

const getStatusText = (s) => ({ DONE: 'Terminé', GENERATING: 'En cours…', ERROR: 'Erreur' }[s] || s)

const formatDate = (d) => d ? new Date(d).toLocaleString('fr-FR', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' }) : ''

const getRateClass = (rate) => {
  if (rate == null) return 'text-gray-500'
  if (rate >= 70) return 'text-green-600 font-semibold'
  if (rate >= 40) return 'text-orange-500 font-semibold'
  return 'text-red-600 font-semibold'
}

const blocClass = (key) => ({
  A: 'bg-indigo-50 border border-indigo-200',
  B: 'bg-emerald-50 border border-emerald-200',
  C: 'bg-amber-50 border border-amber-200',
}[key] || 'bg-gray-50 border border-gray-200')

const blocTitleClass = (key) => ({
  A: 'text-indigo-900',
  B: 'text-emerald-900',
  C: 'text-amber-900',
}[key] || 'text-gray-900')

// ── Fetch ─────────────────────────────────────────────────────────
const fetchBilan = async () => {
  try {
    isLoading.value = true
    error.value = null
    const response = await bilanService.get(route.params.id)
    report.value = response.report || {}
    // Merge report-level data fields
    const data = response.data || {}
    report.value = { ...report.value, ...data }
    sections.value = data.sections || {}
  } catch (err) {
    console.error('EAM bilan fetch error:', err)
    error.value = err.response?.status === 403
      ? "Vous n'avez pas la permission de consulter ce bilan."
      : err.response?.status === 404
        ? 'Bilan non trouvé.'
        : 'Erreur lors du chargement du bilan.'
  } finally {
    isLoading.value = false
  }
}

onMounted(fetchBilan)
</script>
