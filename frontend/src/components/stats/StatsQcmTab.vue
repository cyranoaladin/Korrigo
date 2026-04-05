<!-- ⚠️ RAPPORT ARCHIVÉ — BAC BLANC MATHS 2026 (BB_J1/BB_J2)
     Données hardcodées. Voir StatsReport.vue pour le contexte complet. -->
<template>
  <!-- ============ TAB: QCM 5/5 ============ -->
  <div>
    <!-- KPIs QCM -->
    <div class="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
      <div class="bg-white rounded-xl border border-gray-200 p-4 shadow-sm">
        <AppIcon name="list" :size="20" class="text-blue-600 mb-2" />
        <p class="text-2xl font-bold text-neutralDark">{{ qcmData.total_perfect }}</p>
        <p class="text-xs text-gray-500 mt-1">Élèves avec 5/5</p>
        <p class="text-xs text-gray-400">{{ qcmData.total_perfect_pct }}% des {{ header.n_candidates }} copies</p>
      </div>
      <div class="bg-white rounded-xl border border-gray-200 p-4 shadow-sm">
        <AppIcon name="bar-chart-3" :size="20" class="text-green-600 mb-2" />
        <p class="text-2xl font-bold text-neutralDark">{{ qcmData.j1_perfect_count }}</p>
        <p class="text-xs text-gray-500 mt-1">BB_J1 — {{ qcmData.j1_perfect_pct }}%</p>
        <p class="text-xs text-gray-400">QCM très accessible</p>
      </div>
      <div class="bg-white rounded-xl border border-gray-200 p-4 shadow-sm">
        <AppIcon name="bar-chart-3" :size="20" class="text-purple-600 mb-2" />
        <p class="text-2xl font-bold text-neutralDark">{{ qcmData.j2_perfect_count }}</p>
        <p class="text-xs text-gray-500 mt-1">BB_J2 — {{ qcmData.j2_perfect_pct }}%</p>
        <p class="text-xs text-gray-400">QCM discriminant</p>
      </div>
      <div class="bg-white rounded-xl border border-gray-200 p-4 shadow-sm">
        <AppIcon name="alert" :size="20" class="text-red-500 mb-2" />
        <p class="text-2xl font-bold text-neutralDark">{{ qcmData.below10_with_perfect }}</p>
        <p class="text-xs text-gray-500 mt-1">5/5 mais &lt; 10/20</p>
        <p class="text-xs text-gray-400">QCM > 50% de la note</p>
      </div>
    </div>

    <!-- Distribution Ex1 -->
    <div class="grid lg:grid-cols-2 gap-6 mb-8">
      <div class="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
        <div class="px-5 py-4 border-b border-gray-100 bg-green-50">
          <h2 class="text-base font-semibold text-green-800">BB_J1 — Distribution Ex1 (moy {{ qcmData.j1_mean_ex1 }}/5)</h2>
        </div>
        <div class="px-5 py-4 space-y-2">
          <div v-for="d in distJ1" :key="d.label" class="flex items-center gap-3">
            <span class="w-10 text-xs text-gray-500 font-mono text-right shrink-0">{{ d.label }}</span>
            <div class="flex-1 bg-gray-100 rounded-full h-5 overflow-hidden relative">
              <div class="h-full rounded-full bg-green-500" :style="{ width: (d.count / maxDistJ1 * 100) + '%' }" />
              <span class="absolute inset-0 flex items-center justify-center text-xs font-semibold" :class="d.count >= 30 ? 'text-white' : 'text-gray-700'">{{ d.count }} ({{ d.pct }})</span>
            </div>
          </div>
        </div>
      </div>
      <div class="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
        <div class="px-5 py-4 border-b border-gray-100 bg-purple-50">
          <h2 class="text-base font-semibold text-purple-800">BB_J2 — Distribution Ex1 (moy {{ qcmData.j2_mean_ex1 }}/5)</h2>
        </div>
        <div class="px-5 py-4 space-y-1.5">
          <div v-for="d in distJ2" :key="d.label" class="flex items-center gap-3">
            <span class="w-10 text-xs text-gray-500 font-mono text-right shrink-0">{{ d.label }}</span>
            <div class="flex-1 bg-gray-100 rounded-full h-5 overflow-hidden relative">
              <div class="h-full rounded-full bg-purple-500" :style="{ width: (d.count / maxDistJ2 * 100) + '%' }" />
              <span class="absolute inset-0 flex items-center justify-center text-xs font-semibold" :class="d.count >= 15 ? 'text-white' : 'text-gray-700'">{{ d.count }} ({{ d.pct }})</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Table élèves 5/5 -->
    <div class="bg-white rounded-xl border border-gray-200 shadow-sm mb-8 overflow-hidden">
      <div class="px-5 py-4 border-b border-gray-100">
        <h2 class="text-lg font-semibold text-neutralDark">{{ qcmData.total_perfect }} Élèves avec 5/5 à l'Exercice 1 (QCM)</h2>
        <p class="text-xs text-gray-400 mt-1">Classement par note globale décroissante · <span class="text-amber-600">Jaune</span> = %Ex1 &gt; 31.2% (seuil J2) · <span class="text-red-600">Rouge</span> = %Ex1 ≥ 50%</p>
      </div>
      <div class="overflow-x-auto">
        <table class="w-full text-sm">
          <thead>
            <tr class="bg-gray-50">
              <th class="text-center px-2 py-2.5 font-medium text-gray-600 w-10">#</th>
              <th class="text-left px-3 py-2.5 font-medium text-gray-600">Élève</th>
              <th class="text-center px-2 py-2.5 font-medium text-gray-600">Exam</th>
              <th class="text-center px-2 py-2.5 font-medium text-gray-600">Classe</th>
              <th v-if="hasGroups" class="text-center px-2 py-2.5 font-medium text-gray-600">Grp</th>
              <th class="text-center px-2 py-2.5 font-medium text-gray-600">Note</th>
              <th class="text-center px-2 py-2.5 font-medium text-gray-600">%Ex1</th>
              <th class="text-left px-3 py-2.5 font-medium text-gray-600">Correcteur</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(s, i) in qcmPerfect" :key="i" class="border-t border-gray-100" :class="s.pct >= 50 ? 'bg-red-50' : s.pct > 31.2 && s.exam === 'BB_J1' ? 'bg-amber-50' : ''">
              <td class="px-2 py-2 text-center text-gray-500 text-xs">{{ i + 1 }}</td>
              <td class="px-3 py-2 font-medium text-gray-800" :class="s.pct >= 50 ? 'text-red-800' : ''">{{ s.name }}</td>
              <td class="px-2 py-2 text-center">
                <span class="text-xs px-1.5 py-0.5 rounded-full font-medium" :class="s.exam === 'BB_J1' ? 'bg-green-100 text-green-800' : 'bg-purple-100 text-purple-800'">{{ s.exam }}</span>
              </td>
              <td class="px-2 py-2 text-center text-gray-600">{{ s.classe }}</td>
              <td v-if="hasGroups" class="px-2 py-2 text-center text-gray-600">{{ s.groupe }}</td>
              <td class="px-2 py-2 text-center font-bold" :class="s.total < 10 ? 'text-red-700' : 'text-gray-800'">{{ s.total }}</td>
              <td class="px-2 py-2 text-center font-semibold" :class="s.pct >= 50 ? 'text-red-700' : s.pct >= 40 ? 'text-amber-700' : 'text-gray-600'">{{ s.pct }}%</td>
              <td class="px-3 py-2 text-gray-500 text-xs">{{ s.corrector }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Alerts -->
    <div class="bg-amber-50 border border-amber-200 rounded-xl p-4 flex items-start gap-3 mb-4">
      <AppIcon name="alert" :size="20" class="text-amber-600 shrink-0 mt-0.5" />
      <div>
        <p class="text-sm font-semibold text-amber-800">24 élèves BB_J1 avec %Ex1 supérieur au seuil BB_J2 (31.2%)</p>
        <p class="text-sm text-amber-700 mt-1">Les 16 élèves BB_J2 ayant eu 5/5 ont un %Ex1 moyen de 31.2%. <strong>24 élèves BB_J1 sur 54</strong> (44.4%) dépassent ce seuil, indiquant un poids disproportionné du QCM dans leur note. Les écarts les plus extrêmes atteignent +49 points (CHAMAM, KHALSI).</p>
      </div>
    </div>
    <div class="bg-red-50 border border-red-200 rounded-xl p-4 flex items-start gap-3 mb-4">
      <AppIcon name="alert" :size="20" class="text-red-600 shrink-0 mt-0.5" />
      <div>
        <p class="text-sm font-semibold text-red-800">6 élèves avec 5/5 au QCM mais note globale &lt; 10/20</p>
        <p class="text-sm text-red-700 mt-1">Pour ces élèves, le QCM représente entre 50% et 80% de leur note totale. Sans le QCM, leur note effective serait entre 1.2 et 5.0 sur 15 points — <strong>fragilité extrême sur les exercices de rédaction</strong>.</p>
        <p class="text-sm text-red-700 mt-1"><strong>4 des 6 sont en T.01</strong> — confirmation de la difficulté structurelle de cette classe (taux réussite BB_J1 : 43.8%).</p>
      </div>
    </div>
    <div class="bg-amber-50 border border-amber-200 rounded-xl p-4 flex items-start gap-3 mb-8">
      <AppIcon name="alert" :size="20" class="text-amber-600 shrink-0 mt-0.5" />
      <div>
        <p class="text-sm font-semibold text-amber-800">Le QCM BB_J1 est très peu discriminant</p>
        <p class="text-sm text-amber-700 mt-1">50.9% des candidats obtiennent 5/5 à BB_J1 contre seulement 15.5% à BB_J2. Le QCM BB_J2 différencie nettement mieux les niveaux (moyenne 2.93/5 vs 4.12/5).</p>
      </div>
    </div>

    <!-- ===== DÉTECTION DE TRICHE ===== -->
    <div class="bg-white rounded-xl border-2 border-red-300 shadow-sm mb-8 overflow-hidden">
      <div class="px-5 py-4 border-b border-red-200 bg-red-50">
        <h2 class="text-lg font-semibold text-red-800 flex items-center gap-2">
          <AppIcon name="alert" :size="20" class="text-red-600" />
          Détection de Triche au QCM — BB_J1
        </h2>
        <p class="text-xs text-red-600 mt-1">Pattern caractéristique : [0, 1, 0, 1, 0] → 2/5 — réponses du mauvais sujet</p>
      </div>

      <div class="px-5 py-4 border-b border-gray-100">
        <div class="grid grid-cols-3 gap-4 text-center">
          <div>
            <p class="text-2xl font-bold text-red-700">10</p>
            <p class="text-xs text-gray-500">élèves détectés</p>
          </div>
          <div>
            <p class="text-2xl font-bold text-red-600">9 Sujet A</p>
            <p class="text-xs text-gray-500">réponses du Sujet B copiées</p>
          </div>
          <div>
            <p class="text-2xl font-bold text-red-600">1 Sujet B</p>
            <p class="text-xs text-gray-500">réponses du Sujet A copiées</p>
          </div>
        </div>
      </div>

      <div class="overflow-x-auto">
        <table class="w-full text-sm">
          <thead>
            <tr class="bg-red-50/50">
              <th class="text-center px-2 py-2.5 font-medium text-gray-600 w-10">#</th>
              <th class="text-left px-3 py-2.5 font-medium text-gray-600">Élève</th>
              <th class="text-center px-2 py-2.5 font-medium text-gray-600">Sujet</th>
              <th class="text-center px-2 py-2.5 font-medium text-gray-600">Classe</th>
              <th class="text-center px-1 py-2.5 font-medium text-gray-600">Q1.1</th>
              <th class="text-center px-1 py-2.5 font-medium text-gray-600">Q1.2</th>
              <th class="text-center px-1 py-2.5 font-medium text-gray-600">Q1.3</th>
              <th class="text-center px-1 py-2.5 font-medium text-gray-600">Q1.4</th>
              <th class="text-center px-1 py-2.5 font-medium text-gray-600">Q1.5</th>
              <th class="text-center px-2 py-2.5 font-medium text-gray-600">QCM</th>
              <th class="text-center px-2 py-2.5 font-medium text-gray-600">Note</th>
              <th class="text-left px-3 py-2.5 font-medium text-gray-600">Correcteur</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(c, i) in cheatDetected" :key="i" class="border-t border-gray-100 bg-red-50/30 hover:bg-red-50">
              <td class="px-2 py-2 text-center text-gray-500 text-xs">{{ i + 1 }}</td>
              <td class="px-3 py-2 font-medium text-red-800 flex items-center gap-1">
                <AppIcon name="alert" :size="14" class="text-red-600" />
                {{ c.name }}
              </td>
              <td class="px-2 py-2 text-center">
                <span class="text-xs px-1.5 py-0.5 rounded-full font-bold" :class="c.subject === 'B' ? 'bg-red-200 text-red-900' : 'bg-orange-100 text-orange-800'">{{ c.subject }}</span>
              </td>
              <td class="px-2 py-2 text-center text-gray-600">{{ c.classe }}</td>
              <td class="px-1 py-2 text-center" :class="c.q[0] === 0 ? 'text-red-600 font-bold' : 'text-green-600 font-bold'">{{ c.q[0] }}</td>
              <td class="px-1 py-2 text-center" :class="c.q[1] === 0 ? 'text-red-600 font-bold' : 'text-green-600 font-bold'">{{ c.q[1] }}</td>
              <td class="px-1 py-2 text-center" :class="c.q[2] === 0 ? 'text-red-600 font-bold' : 'text-green-600 font-bold'">{{ c.q[2] }}</td>
              <td class="px-1 py-2 text-center" :class="c.q[3] === 0 ? 'text-red-600 font-bold' : 'text-green-600 font-bold'">{{ c.q[3] }}</td>
              <td class="px-1 py-2 text-center" :class="c.q[4] === 0 ? 'text-red-600 font-bold' : 'text-green-600 font-bold'">{{ c.q[4] }}</td>
              <td class="px-2 py-2 text-center font-bold text-red-700">2/5</td>
              <td class="px-2 py-2 text-center font-bold" :class="c.total < 10 ? 'text-red-700' : 'text-gray-800'">{{ c.total }}</td>
              <td class="px-3 py-2 text-gray-500 text-xs">{{ c.corrector }}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <div class="px-5 py-4 border-t border-gray-100 bg-gray-50">
        <p class="text-sm font-semibold text-gray-700 mb-2">Élèves proches du pattern triche (4/5 positions matchent)</p>
        <div class="space-y-1">
          <div v-for="nc in nearCheat" :key="nc.name" class="flex items-center gap-2 text-sm">
            <AppIcon name="circle" :size="8" class="text-amber-500" />
            <span class="font-medium text-gray-700">{{ nc.name }}</span>
            <span class="text-xs px-1.5 py-0.5 rounded-full bg-gray-200 text-gray-700">Sujet {{ nc.subject }}</span>
            <span class="text-gray-500">{{ nc.classe }}</span>
            <span class="font-mono text-xs text-gray-600">[{{ nc.q.join(',') }}]</span>
            <span class="text-gray-500">→ {{ nc.qcm }}/5</span>
          </div>
        </div>
      </div>

      <div class="px-5 py-4 border-t border-red-200 bg-red-50">
        <p class="text-sm text-red-800"><strong>Asymétrie 9A vs 1B</strong> : les 9 élèves du Sujet A ont probablement recopié les réponses d'un voisin Sujet B. HAMZAOUI (Sujet B) a recopié les réponses d'un voisin Sujet A.</p>
        <p class="text-sm text-red-700 mt-1">Taux de triche potentielle : <strong>9.4%</strong> des candidats BB_J1. Note moyenne des tricheurs : <strong>10.09/20</strong>.</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import AppIcon from '../../icons/AppIcon.vue'

const props = defineProps({
  data: { type: Object, required: true },
  header: { type: Object, required: true },
  hasGroups: { type: Boolean, default: true }
})

const distJ1 = computed(() => props.data?.qcm?.dist_j1 || [])
const distJ2 = computed(() => props.data?.qcm?.dist_j2 || [])
const maxDistJ1 = computed(() => Math.max(...(distJ1.value.map(d => d.count)), 1))
const maxDistJ2 = computed(() => Math.max(...(distJ2.value.map(d => d.count)), 1))

const qcmPerfect = computed(() => props.data?.qcm?.perfect || [])
const qcmData = computed(() => props.data?.qcm || {})

const cheatDetected = [
  { name: 'ABID Youcef', subject: 'A', classe: 'T.01', q: [0,1,0,1,0], total: 13.85, corrector: 'Alaeddine BEN RHOUMA' },
  { name: 'ZARAA Lina', subject: 'A', classe: 'T.02', q: [0,1,0,1,0], total: 13.15, corrector: 'Selima KLIBI' },
  { name: 'CHAHED Seddik', subject: 'A', classe: 'T.09', q: [0,1,0,1,0], total: 12.10, corrector: 'Patrick DUPONT' },
  { name: 'HAMZAOUI Ismaël Satyavan', subject: 'B', classe: 'T.06', q: [0,1,0,1,0], total: 11.15, corrector: 'Philippe CARR' },
  { name: 'AOUAOUI Chaima', subject: 'A', classe: 'T.05', q: [0,1,0,1,0], total: 11.10, corrector: 'Alaeddine BEN RHOUMA' },
  { name: 'BACCOUCHE Selima', subject: 'A', classe: 'T.05', q: [0,1,0,1,0], total: 10.75, corrector: 'Alaeddine BEN RHOUMA' },
  { name: 'JAAFAR Youssef', subject: 'A', classe: 'T.01', q: [0,1,0,1,0], total: 8.75, corrector: 'Philippe CARR' },
  { name: 'JAIDANE Mohamed-Seyf', subject: 'A', classe: 'T.07', q: [0,1,0,1,0], total: 8.25, corrector: 'Philippe CARR' },
  { name: 'BEN TURKIA Leith', subject: 'A', classe: 'T.06', q: [0,1,0,1,0], total: 7.15, corrector: 'Patrick DUPONT' },
  { name: 'BOUGHABA Sirine', subject: 'A', classe: 'T.03', q: [0,1,0,1,0], total: 4.60, corrector: 'Patrick DUPONT' }
]

const nearCheat = [
  { name: 'BOUASSIDA Ilyes', subject: 'B', classe: 'T.06', q: [1,1,0,1,0], qcm: 3 },
  { name: 'AYADI Sarra', subject: 'B', classe: 'T.03', q: [1,1,0,1,0], qcm: 3 },
  { name: 'DEBBECH Mohamed-Anas', subject: 'A', classe: 'T.05', q: [0,1,0,1,1], qcm: 3 },
  { name: 'SATOURI Adem', subject: 'A', classe: 'T.07', q: [0,1,0,0,0], qcm: 1 }
]
</script>
