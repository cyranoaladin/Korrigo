<template>
  <section class="max-w-6xl mx-auto px-4 sm:px-6 py-10 md:py-14">
    <!-- Header -->
    <div class="mb-10">
      <div class="flex items-center gap-3 mb-4">
        <div class="bg-primary-100 rounded-xl p-3">
          <BarChart3 class="w-7 h-7 text-primary-700" />
        </div>
        <div>
          <h1 class="text-2xl sm:text-3xl font-bold text-neutralDark">
            Rapport du Jury — Bac Blanc Mathématiques 2026
          </h1>
          <p class="text-sm text-gray-500 mt-1">
            Lycée Pierre Mendès France — Tunis (AEFE) · Session Janvier-Février 2026
          </p>
        </div>
      </div>
      <div class="flex flex-wrap gap-2 text-xs">
        <span class="bg-blue-100 text-blue-800 px-2.5 py-1 rounded-full font-medium">209 candidats</span>
        <span class="bg-green-100 text-green-800 px-2.5 py-1 rounded-full font-medium">BB_J1 : 106 copies</span>
        <span class="bg-purple-100 text-purple-800 px-2.5 py-1 rounded-full font-medium">BB_J2 : 103 copies</span>
        <span class="bg-gray-100 text-gray-700 px-2.5 py-1 rounded-full font-medium">8 correcteurs</span>
        <span class="bg-amber-100 text-amber-800 px-2.5 py-1 rounded-full font-medium">4 mars 2026</span>
      </div>
    </div>

    <!-- Navigation tabs -->
    <div class="sticky top-16 z-40 bg-gray-50/95 backdrop-blur-sm -mx-4 sm:-mx-6 px-4 sm:px-6 py-3 border-b border-gray-200 mb-8">
      <div class="flex gap-1 overflow-x-auto no-scrollbar">
        <button
          v-for="tab in tabs"
          :key="tab.id"
          class="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium whitespace-nowrap transition-colors"
          :class="activeTab === tab.id
            ? 'bg-primary-700 text-white shadow-sm'
            : 'text-gray-600 hover:bg-gray-200/70'"
          @click="activeTab = tab.id"
        >
          <component :is="tab.icon" class="w-3.5 h-3.5" />
          {{ tab.label }}
        </button>
      </div>
    </div>

    <!-- ============ TAB: VUE D'ENSEMBLE ============ -->
    <div v-show="activeTab === 'overview'">
      <!-- KPI Cards -->
      <div class="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <div v-for="kpi in kpis" :key="kpi.label" class="bg-white rounded-xl border border-gray-200 p-4 shadow-sm">
          <div class="flex items-center gap-2 mb-2">
            <component :is="kpi.icon" class="w-4 h-4" :class="kpi.color" />
            <span class="text-xs text-gray-500 font-medium uppercase tracking-wide">{{ kpi.label }}</span>
          </div>
          <p class="text-2xl font-bold text-neutralDark">{{ kpi.value }}</p>
          <p class="text-xs text-gray-400 mt-0.5">{{ kpi.sub }}</p>
        </div>
      </div>

      <!-- Statistiques descriptives -->
      <div class="bg-white rounded-xl border border-gray-200 shadow-sm mb-8 overflow-hidden">
        <div class="px-5 py-4 border-b border-gray-100">
          <h2 class="text-lg font-semibold text-neutralDark">Statistiques Descriptives</h2>
        </div>
        <div class="overflow-x-auto">
          <table class="w-full text-sm">
            <thead>
              <tr class="bg-gray-50">
                <th class="text-left px-4 py-2.5 font-medium text-gray-600">Statistique</th>
                <th class="text-center px-4 py-2.5 font-medium text-green-700">BB_J1 (106)</th>
                <th class="text-center px-4 py-2.5 font-medium text-purple-700">BB_J2 (103)</th>
                <th class="text-center px-4 py-2.5 font-medium text-blue-700">Global (209)</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in descriptiveStats" :key="row.label" class="border-t border-gray-100">
                <td class="px-4 py-2 font-medium text-gray-700">{{ row.label }}</td>
                <td class="px-4 py-2 text-center text-gray-800">{{ row.j1 }}</td>
                <td class="px-4 py-2 text-center text-gray-800">{{ row.j2 }}</td>
                <td class="px-4 py-2 text-center font-semibold text-blue-800">{{ row.global }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- Distribution globale (barres horizontales) -->
      <div class="bg-white rounded-xl border border-gray-200 shadow-sm mb-8 overflow-hidden">
        <div class="px-5 py-4 border-b border-gray-100">
          <h2 class="text-lg font-semibold text-neutralDark">Distribution des Notes — Global (209 copies)</h2>
        </div>
        <div class="px-5 py-4 space-y-2">
          <div v-for="bin in globalDistribution" :key="bin.label" class="flex items-center gap-3">
            <span class="w-16 text-xs text-gray-500 font-mono text-right shrink-0">{{ bin.label }}</span>
            <div class="flex-1 bg-gray-100 rounded-full h-6 overflow-hidden relative">
              <div
                class="h-full rounded-full transition-all duration-500"
                :class="bin.count >= 30 ? 'bg-primary-600' : bin.count >= 20 ? 'bg-primary-500' : bin.count >= 10 ? 'bg-primary-400' : 'bg-primary-300'"
                :style="{ width: (bin.count / 42 * 100) + '%' }"
              />
              <span class="absolute inset-0 flex items-center justify-center text-xs font-semibold" :class="bin.count >= 20 ? 'text-white' : 'text-gray-700'">
                {{ bin.count }} ({{ bin.pct }})
              </span>
            </div>
          </div>
        </div>
      </div>

      <!-- Mentions -->
      <div class="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
        <div class="px-5 py-4 border-b border-gray-100">
          <h2 class="text-lg font-semibold text-neutralDark">Répartition par Mention</h2>
        </div>
        <div class="overflow-x-auto">
          <table class="w-full text-sm">
            <thead>
              <tr class="bg-gray-50">
                <th class="text-left px-4 py-2.5 font-medium text-gray-600">Mention</th>
                <th class="text-center px-4 py-2.5 font-medium text-gray-600">Seuil</th>
                <th class="text-center px-4 py-2.5 font-medium text-green-700">BB_J1</th>
                <th class="text-center px-4 py-2.5 font-medium text-purple-700">BB_J2</th>
                <th class="text-center px-4 py-2.5 font-medium text-blue-700">Global</th>
                <th class="text-center px-4 py-2.5 font-medium text-blue-700">%</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="m in mentions" :key="m.label" class="border-t border-gray-100">
                <td class="px-4 py-2 font-medium" :class="m.labelColor">
                  <span class="inline-flex items-center gap-1.5">
                    <span class="w-2.5 h-2.5 rounded-full" :class="m.dotColor" />
                    {{ m.label }}
                  </span>
                </td>
                <td class="px-4 py-2 text-center text-gray-500 text-xs">{{ m.seuil }}</td>
                <td class="px-4 py-2 text-center">{{ m.j1 }}</td>
                <td class="px-4 py-2 text-center">{{ m.j2 }}</td>
                <td class="px-4 py-2 text-center font-semibold">{{ m.global }}</td>
                <td class="px-4 py-2 text-center font-semibold">{{ m.pct }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- ============ TAB: CORRECTEURS ============ -->
    <div v-show="activeTab === 'correctors'">
      <div class="bg-white rounded-xl border border-gray-200 shadow-sm mb-8 overflow-hidden">
        <div class="px-5 py-4 border-b border-gray-100">
          <h2 class="text-lg font-semibold text-neutralDark">Synthèse par Correcteur</h2>
        </div>
        <div class="overflow-x-auto">
          <table class="w-full text-sm">
            <thead>
              <tr class="bg-gray-50">
                <th class="text-left px-4 py-2.5 font-medium text-gray-600">Correcteur</th>
                <th class="text-center px-3 py-2.5 font-medium text-gray-600">Exam</th>
                <th class="text-center px-3 py-2.5 font-medium text-gray-600">n</th>
                <th class="text-center px-3 py-2.5 font-medium text-gray-600">Final.</th>
                <th class="text-center px-3 py-2.5 font-medium text-gray-600">Moy</th>
                <th class="text-center px-3 py-2.5 font-medium text-gray-600">Méd</th>
                <th class="text-center px-3 py-2.5 font-medium text-gray-600">É.-T.</th>
                <th class="text-center px-3 py-2.5 font-medium text-gray-600">Min</th>
                <th class="text-center px-3 py-2.5 font-medium text-gray-600">Max</th>
                <th class="text-center px-3 py-2.5 font-medium text-gray-600">Réussite</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="c in correctors" :key="c.name" class="border-t border-gray-100 hover:bg-gray-50/50">
                <td class="px-4 py-2.5 font-medium text-gray-800">
                  <div class="flex items-center gap-2">
                    <div class="w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold text-white" :class="c.exam === 'BB_J1' ? 'bg-green-600' : 'bg-purple-600'">
                      {{ c.initials }}
                    </div>
                    {{ c.name }}
                  </div>
                </td>
                <td class="px-3 py-2.5 text-center">
                  <span class="text-xs px-2 py-0.5 rounded-full font-medium" :class="c.exam === 'BB_J1' ? 'bg-green-100 text-green-800' : 'bg-purple-100 text-purple-800'">{{ c.exam }}</span>
                </td>
                <td class="px-3 py-2.5 text-center">{{ c.n }}</td>
                <td class="px-3 py-2.5 text-center">
                  <span v-if="c.finalized > 0" class="text-green-600 font-semibold">{{ c.finalized }} ✓</span>
                  <span v-else class="text-gray-400">0</span>
                </td>
                <td class="px-3 py-2.5 text-center font-semibold">{{ c.mean }}</td>
                <td class="px-3 py-2.5 text-center">{{ c.median }}</td>
                <td class="px-3 py-2.5 text-center">{{ c.std }}</td>
                <td class="px-3 py-2.5 text-center text-red-600">{{ c.min }}</td>
                <td class="px-3 py-2.5 text-center text-green-600">{{ c.max }}</td>
                <td class="px-3 py-2.5 text-center">
                  <span class="font-semibold" :class="parseFloat(c.rate) >= 80 ? 'text-green-700' : parseFloat(c.rate) >= 70 ? 'text-amber-700' : 'text-red-700'">{{ c.rate }}</span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- Barre visuelle des moyennes -->
      <div class="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
        <div class="px-5 py-4 border-b border-gray-100">
          <h2 class="text-lg font-semibold text-neutralDark">Comparaison des Moyennes</h2>
          <p class="text-xs text-gray-400 mt-1">Les moyennes dépendent du lot assigné, pas de la sévérité du correcteur</p>
        </div>
        <div class="px-5 py-4 space-y-3">
          <div v-for="c in correctorsSorted" :key="c.name" class="flex items-center gap-3">
            <span class="w-44 text-sm text-gray-700 font-medium truncate shrink-0">{{ c.name }}</span>
            <div class="flex-1 bg-gray-100 rounded-full h-7 overflow-hidden relative">
              <div
                class="h-full rounded-full"
                :class="c.exam === 'BB_J1' ? 'bg-green-500' : 'bg-purple-500'"
                :style="{ width: (c.mean / 20 * 100) + '%' }"
              />
              <span class="absolute inset-0 flex items-center pl-2 text-xs font-bold" :class="c.mean >= 13 ? 'text-white' : 'text-gray-700'" :style="{ paddingLeft: Math.max(c.mean / 20 * 100 - 12, 2) + '%' }">
                {{ c.mean }}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- ============ TAB: GROUPES ============ -->
    <div v-show="activeTab === 'groups'">
      <div class="grid lg:grid-cols-2 gap-6 mb-8">
        <!-- BB_J1 groups -->
        <div class="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
          <div class="px-5 py-4 border-b border-gray-100 bg-green-50">
            <h2 class="text-base font-semibold text-green-800">BB_J1 — Groupes de TD</h2>
          </div>
          <div class="overflow-x-auto">
            <table class="w-full text-sm">
              <thead>
                <tr class="bg-gray-50">
                  <th class="text-left px-3 py-2 font-medium text-gray-600">Groupe</th>
                  <th class="text-left px-3 py-2 font-medium text-gray-600">Enseignant</th>
                  <th class="text-center px-2 py-2 font-medium text-gray-600">n</th>
                  <th class="text-center px-2 py-2 font-medium text-gray-600">Moy</th>
                  <th class="text-center px-2 py-2 font-medium text-gray-600">Réus.</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="g in groupsJ1" :key="g.name" class="border-t border-gray-100">
                  <td class="px-3 py-2 font-semibold text-gray-800">{{ g.name }}</td>
                  <td class="px-3 py-2 text-gray-600">{{ g.teacher }}</td>
                  <td class="px-2 py-2 text-center">{{ g.n }}</td>
                  <td class="px-2 py-2 text-center font-semibold">{{ g.mean }}</td>
                  <td class="px-2 py-2 text-center">
                    <span class="font-semibold" :class="parseFloat(g.rate) >= 80 ? 'text-green-700' : parseFloat(g.rate) >= 70 ? 'text-amber-700' : 'text-red-700'">{{ g.rate }}</span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <!-- BB_J2 groups -->
        <div class="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
          <div class="px-5 py-4 border-b border-gray-100 bg-purple-50">
            <h2 class="text-base font-semibold text-purple-800">BB_J2 — Groupes de TD</h2>
          </div>
          <div class="overflow-x-auto">
            <table class="w-full text-sm">
              <thead>
                <tr class="bg-gray-50">
                  <th class="text-left px-3 py-2 font-medium text-gray-600">Groupe</th>
                  <th class="text-left px-3 py-2 font-medium text-gray-600">Enseignant</th>
                  <th class="text-center px-2 py-2 font-medium text-gray-600">n</th>
                  <th class="text-center px-2 py-2 font-medium text-gray-600">Moy</th>
                  <th class="text-center px-2 py-2 font-medium text-gray-600">Réus.</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="g in groupsJ2" :key="g.name" class="border-t border-gray-100">
                  <td class="px-3 py-2 font-semibold text-gray-800">{{ g.name }}</td>
                  <td class="px-3 py-2 text-gray-600">{{ g.teacher }}</td>
                  <td class="px-2 py-2 text-center">{{ g.n }}</td>
                  <td class="px-2 py-2 text-center font-semibold">{{ g.mean }}</td>
                  <td class="px-2 py-2 text-center">
                    <span class="font-semibold" :class="parseFloat(g.rate) >= 80 ? 'text-green-700' : parseFloat(g.rate) >= 70 ? 'text-amber-700' : 'text-red-700'">{{ g.rate }}</span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>

      <!-- Alert G5 -->
      <div class="bg-red-50 border border-red-200 rounded-xl p-4 flex items-start gap-3">
        <AlertTriangle class="w-5 h-5 text-red-600 shrink-0 mt-0.5" />
        <div>
          <p class="text-sm font-semibold text-red-800">Groupe G5 en difficulté</p>
          <p class="text-sm text-red-700 mt-1">Moyenne 9.70/20, taux de réussite 58.3% — nettement en-deçà des autres groupes. Remédiation ciblée recommandée.</p>
        </div>
      </div>
    </div>

    <!-- ============ TAB: CLASSES ============ -->
    <div v-show="activeTab === 'classes'">
      <div class="grid lg:grid-cols-2 gap-6 mb-8">
        <div class="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
          <div class="px-5 py-4 border-b border-gray-100 bg-green-50">
            <h2 class="text-base font-semibold text-green-800">BB_J1 — Par Classe</h2>
          </div>
          <div class="overflow-x-auto">
            <table class="w-full text-sm">
              <thead>
                <tr class="bg-gray-50">
                  <th class="text-left px-3 py-2 font-medium text-gray-600">Classe</th>
                  <th class="text-center px-2 py-2 font-medium text-gray-600">n</th>
                  <th class="text-center px-2 py-2 font-medium text-gray-600">Moy</th>
                  <th class="text-center px-2 py-2 font-medium text-gray-600">É.-T.</th>
                  <th class="text-center px-2 py-2 font-medium text-gray-600">Réussite</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="cl in classesJ1" :key="cl.name" class="border-t border-gray-100" :class="cl.highlight ? 'bg-yellow-50' : ''">
                  <td class="px-3 py-2 font-semibold text-gray-800">
                    {{ cl.name }}
                    <span v-if="cl.badge" class="ml-1 text-xs px-1.5 py-0.5 rounded-full" :class="cl.badgeClass">{{ cl.badge }}</span>
                  </td>
                  <td class="px-2 py-2 text-center">{{ cl.n }}</td>
                  <td class="px-2 py-2 text-center font-semibold">{{ cl.mean }}</td>
                  <td class="px-2 py-2 text-center text-gray-500">{{ cl.std }}</td>
                  <td class="px-2 py-2 text-center">
                    <span class="font-semibold" :class="cl.rateNum >= 80 ? 'text-green-700' : cl.rateNum >= 60 ? 'text-amber-700' : 'text-red-700'">{{ cl.rate }}</span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <div class="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
          <div class="px-5 py-4 border-b border-gray-100 bg-purple-50">
            <h2 class="text-base font-semibold text-purple-800">BB_J2 — Par Classe</h2>
          </div>
          <div class="overflow-x-auto">
            <table class="w-full text-sm">
              <thead>
                <tr class="bg-gray-50">
                  <th class="text-left px-3 py-2 font-medium text-gray-600">Classe</th>
                  <th class="text-center px-2 py-2 font-medium text-gray-600">n</th>
                  <th class="text-center px-2 py-2 font-medium text-gray-600">Moy</th>
                  <th class="text-center px-2 py-2 font-medium text-gray-600">É.-T.</th>
                  <th class="text-center px-2 py-2 font-medium text-gray-600">Réussite</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="cl in classesJ2" :key="cl.name" class="border-t border-gray-100">
                  <td class="px-3 py-2 font-semibold text-gray-800">{{ cl.name }}</td>
                  <td class="px-2 py-2 text-center">{{ cl.n }}</td>
                  <td class="px-2 py-2 text-center font-semibold">{{ cl.mean }}</td>
                  <td class="px-2 py-2 text-center text-gray-500">{{ cl.std }}</td>
                  <td class="px-2 py-2 text-center">
                    <span class="font-semibold" :class="cl.rateNum >= 80 ? 'text-green-700' : cl.rateNum >= 60 ? 'text-amber-700' : 'text-red-700'">{{ cl.rate }}</span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>

    <!-- ============ TAB: SUJETS ============ -->
    <div v-show="activeTab === 'subjects'">
      <div class="bg-white rounded-xl border border-gray-200 shadow-sm mb-8 overflow-hidden">
        <div class="px-5 py-4 border-b border-gray-100">
          <h2 class="text-lg font-semibold text-neutralDark">Comparaison Sujet A / Sujet B</h2>
        </div>
        <div class="overflow-x-auto">
          <table class="w-full text-sm">
            <thead>
              <tr class="bg-gray-50">
                <th class="text-left px-4 py-2.5 font-medium text-gray-600" />
                <th class="text-center px-4 py-2.5 font-medium text-green-700">BB_J1 Sujet A</th>
                <th class="text-center px-4 py-2.5 font-medium text-green-700">BB_J1 Sujet B</th>
                <th class="text-center px-4 py-2.5 font-medium text-purple-700">BB_J2 Sujet A</th>
                <th class="text-center px-4 py-2.5 font-medium text-purple-700">BB_J2 Sujet B</th>
              </tr>
            </thead>
            <tbody>
              <tr class="border-t border-gray-100">
                <td class="px-4 py-2 font-medium text-gray-700">Effectif</td>
                <td class="px-4 py-2 text-center">53</td>
                <td class="px-4 py-2 text-center">53</td>
                <td class="px-4 py-2 text-center">53</td>
                <td class="px-4 py-2 text-center">50</td>
              </tr>
              <tr class="border-t border-gray-100">
                <td class="px-4 py-2 font-medium text-gray-700">Moyenne</td>
                <td class="px-4 py-2 text-center">12.98</td>
                <td class="px-4 py-2 text-center font-bold text-green-700">14.60</td>
                <td class="px-4 py-2 text-center">12.16</td>
                <td class="px-4 py-2 text-center font-bold text-purple-700">13.23</td>
              </tr>
              <tr class="border-t border-gray-100">
                <td class="px-4 py-2 font-medium text-gray-700">Médiane</td>
                <td class="px-4 py-2 text-center">14.10</td>
                <td class="px-4 py-2 text-center">15.15</td>
                <td class="px-4 py-2 text-center">12.75</td>
                <td class="px-4 py-2 text-center">14.00</td>
              </tr>
              <tr class="border-t border-gray-100">
                <td class="px-4 py-2 font-medium text-gray-700">Écart-type</td>
                <td class="px-4 py-2 text-center">4.66</td>
                <td class="px-4 py-2 text-center">3.70</td>
                <td class="px-4 py-2 text-center">4.65</td>
                <td class="px-4 py-2 text-center">4.24</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <div class="bg-amber-50 border border-amber-200 rounded-xl p-4 flex items-start gap-3">
        <AlertTriangle class="w-5 h-5 text-amber-600 shrink-0 mt-0.5" />
        <div>
          <p class="text-sm font-semibold text-amber-800">Écart systématique Sujet A / B</p>
          <p class="text-sm text-amber-700 mt-1">Sur les deux épreuves, le Sujet B donne systématiquement une moyenne supérieure (~1.5 pts BB_J1, ~1 pt BB_J2). Vérifier si l'attribution A/B était strictement aléatoire.</p>
        </div>
      </div>
    </div>

    <!-- ============ TAB: QUESTIONS ============ -->
    <div v-show="activeTab === 'questions'">
      <div class="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
        <div class="px-5 py-4 border-b border-gray-100">
          <h2 class="text-lg font-semibold text-neutralDark">Analyse par Question — BB_J2 (27 questions, 103 copies)</h2>
        </div>
        <div class="overflow-x-auto">
          <table class="w-full text-sm">
            <thead>
              <tr class="bg-gray-50">
                <th class="text-left px-3 py-2.5 font-medium text-gray-600">Question</th>
                <th class="text-center px-3 py-2.5 font-medium text-gray-600">Max</th>
                <th class="text-center px-3 py-2.5 font-medium text-gray-600">Moy</th>
                <th class="text-center px-3 py-2.5 font-medium text-gray-600">% Zéros</th>
                <th class="text-center px-3 py-2.5 font-medium text-gray-600">% Max</th>
                <th class="text-left px-3 py-2.5 font-medium text-gray-600">Difficulté</th>
                <th class="text-left px-3 py-2.5 font-medium text-gray-600">Barre</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="q in questions" :key="q.id" class="border-t border-gray-100" :class="q.hard ? 'bg-red-50/40' : ''">
                <td class="px-3 py-2 font-medium text-gray-800">{{ q.id }}</td>
                <td class="px-3 py-2 text-center text-gray-600">{{ q.max }}</td>
                <td class="px-3 py-2 text-center font-semibold">{{ q.mean }}</td>
                <td class="px-3 py-2 text-center" :class="q.zeros >= 30 ? 'text-red-700 font-semibold' : 'text-gray-600'">{{ q.zeros }}%</td>
                <td class="px-3 py-2 text-center" :class="q.maxPct >= 60 ? 'text-green-700' : 'text-gray-600'">{{ q.maxPct }}%</td>
                <td class="px-3 py-2">
                  <span class="text-xs px-2 py-0.5 rounded-full font-medium" :class="difficultyClass(q.difficulty)">{{ q.difficulty }}</span>
                </td>
                <td class="px-3 py-2 w-32">
                  <div class="bg-gray-100 rounded-full h-3 overflow-hidden">
                    <div class="h-full rounded-full" :class="q.difficulty === 'Difficile' ? 'bg-red-400' : q.difficulty === 'Facile' ? 'bg-green-400' : 'bg-blue-400'" :style="{ width: (q.mean / q.max * 100) + '%' }" />
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- ============ TAB: PALMARES ============ -->
    <div v-show="activeTab === 'palmares'">
      <!-- Top 15 -->
      <div class="bg-white rounded-xl border border-gray-200 shadow-sm mb-8 overflow-hidden">
        <div class="px-5 py-4 border-b border-gray-100">
          <h2 class="text-lg font-semibold text-neutralDark flex items-center gap-2">
            <Trophy class="w-5 h-5 text-amber-500" />
            Top 15 Global
          </h2>
        </div>
        <div class="overflow-x-auto">
          <table class="w-full text-sm">
            <thead>
              <tr class="bg-gray-50">
                <th class="text-center px-3 py-2.5 font-medium text-gray-600 w-12">#</th>
                <th class="text-left px-3 py-2.5 font-medium text-gray-600">Élève</th>
                <th class="text-center px-3 py-2.5 font-medium text-gray-600">Classe</th>
                <th class="text-center px-3 py-2.5 font-medium text-gray-600">Groupe</th>
                <th class="text-center px-3 py-2.5 font-medium text-gray-600">Exam</th>
                <th class="text-center px-3 py-2.5 font-medium text-gray-600">Note</th>
                <th class="text-left px-3 py-2.5 font-medium text-gray-600">Correcteur</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="s in top15" :key="s.rank + s.name" class="border-t border-gray-100 hover:bg-amber-50/30">
                <td class="px-3 py-2.5 text-center">
                  <span v-if="s.rank <= 2" class="text-lg">{{ s.rank === 1 ? '🥇' : '🥈' }}</span>
                  <span v-else class="text-gray-500 font-medium">{{ s.rank }}</span>
                </td>
                <td class="px-3 py-2.5 font-semibold text-gray-800">{{ s.name }}</td>
                <td class="px-3 py-2.5 text-center text-gray-600">{{ s.classe }}</td>
                <td class="px-3 py-2.5 text-center text-gray-600">{{ s.groupe }}</td>
                <td class="px-3 py-2.5 text-center">
                  <span class="text-xs px-2 py-0.5 rounded-full font-medium" :class="s.exam === 'BB_J1' ? 'bg-green-100 text-green-800' : 'bg-purple-100 text-purple-800'">{{ s.exam }}</span>
                </td>
                <td class="px-3 py-2.5 text-center font-bold text-lg" :class="s.note >= 20 ? 'text-amber-600' : 'text-green-700'">{{ s.note }}</td>
                <td class="px-3 py-2.5 text-gray-600 text-xs">{{ s.corrector }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- Bottom 11 -->
      <div class="bg-white rounded-xl border border-red-200 shadow-sm overflow-hidden">
        <div class="px-5 py-4 border-b border-red-100 bg-red-50">
          <h2 class="text-lg font-semibold text-red-800 flex items-center gap-2">
            <AlertTriangle class="w-5 h-5" />
            Élèves en Grande Difficulté (&lt; 5/20)
          </h2>
        </div>
        <div class="overflow-x-auto">
          <table class="w-full text-sm">
            <thead>
              <tr class="bg-red-50/50">
                <th class="text-center px-3 py-2.5 font-medium text-red-700 w-12">#</th>
                <th class="text-left px-3 py-2.5 font-medium text-red-700">Élève</th>
                <th class="text-center px-3 py-2.5 font-medium text-red-700">Classe</th>
                <th class="text-center px-3 py-2.5 font-medium text-red-700">Groupe</th>
                <th class="text-center px-3 py-2.5 font-medium text-red-700">Exam</th>
                <th class="text-center px-3 py-2.5 font-medium text-red-700">Note</th>
                <th class="text-left px-3 py-2.5 font-medium text-red-700">Correcteur</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="s in bottom11" :key="s.rank + s.name" class="border-t border-red-100 hover:bg-red-50/30">
                <td class="px-3 py-2.5 text-center text-gray-500">{{ s.rank }}</td>
                <td class="px-3 py-2.5 font-semibold text-gray-800">{{ s.name }}</td>
                <td class="px-3 py-2.5 text-center text-gray-600">{{ s.classe }}</td>
                <td class="px-3 py-2.5 text-center text-gray-600">{{ s.groupe }}</td>
                <td class="px-3 py-2.5 text-center">
                  <span class="text-xs px-2 py-0.5 rounded-full font-medium" :class="s.exam === 'BB_J1' ? 'bg-green-100 text-green-800' : 'bg-purple-100 text-purple-800'">{{ s.exam }}</span>
                </td>
                <td class="px-3 py-2.5 text-center font-bold text-red-700">{{ s.note }}</td>
                <td class="px-3 py-2.5 text-gray-600 text-xs">{{ s.corrector }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- ============ TAB: CORRECTION ============ -->
    <div v-show="activeTab === 'quality'">
      <!-- Quality KPIs -->
      <div class="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <div v-for="q in qualityKpis" :key="q.label" class="bg-white rounded-xl border border-gray-200 p-4 shadow-sm">
          <component :is="q.icon" class="w-5 h-5 mb-2" :class="q.color" />
          <p class="text-2xl font-bold text-neutralDark">{{ q.value }}</p>
          <p class="text-xs text-gray-500 mt-1">{{ q.label }}</p>
          <p class="text-xs text-gray-400">{{ q.sub }}</p>
        </div>
      </div>

      <!-- Appreciations -->
      <div class="bg-white rounded-xl border border-gray-200 shadow-sm mb-8 overflow-hidden">
        <div class="px-5 py-4 border-b border-gray-100">
          <h2 class="text-lg font-semibold text-neutralDark">Appréciations Globales — Fréquence</h2>
        </div>
        <div class="px-5 py-4">
          <div class="flex flex-wrap gap-2 mb-4">
            <span v-for="a in appreciationTags" :key="a.text" class="inline-flex items-center gap-1 px-3 py-1.5 rounded-full text-xs font-medium border" :class="a.class">
              {{ a.text }}
              <span class="bg-white/50 px-1.5 py-0.5 rounded-full text-xs">{{ a.count }}</span>
            </span>
          </div>
          <p class="text-sm text-gray-500 mt-2">Les correcteurs BB_J1 (notamment Philippe CARR) ont rédigé des appréciations détaillées et personnalisées. Les correcteurs BB_J2 ont privilégié des appréciations courtes standardisées.</p>
        </div>
      </div>

      <!-- Thèmes récurrents -->
      <div class="bg-white rounded-xl border border-gray-200 shadow-sm mb-8 overflow-hidden">
        <div class="px-5 py-4 border-b border-gray-100">
          <h2 class="text-lg font-semibold text-neutralDark">Thèmes Récurrents des Appréciations</h2>
        </div>
        <div class="px-5 py-4 space-y-3">
          <div v-for="th in themes" :key="th.label" class="flex items-center gap-3">
            <span class="w-3 h-3 rounded-full shrink-0" :class="th.dotColor" />
            <span class="text-sm text-gray-700 flex-1">{{ th.label }}</span>
            <span class="text-xs font-medium px-2 py-0.5 rounded-full" :class="th.tagClass">{{ th.freq }}</span>
          </div>
        </div>
      </div>

      <!-- Fraud alert -->
      <div class="bg-red-50 border border-red-300 rounded-xl p-4 flex items-start gap-3">
        <AlertTriangle class="w-5 h-5 text-red-600 shrink-0 mt-0.5" />
        <div>
          <p class="text-sm font-semibold text-red-800">Suspicion de fraude signalée</p>
          <p class="text-sm text-red-700 mt-1 italic">"Une anomalie grave et inacceptable est à souligner à l'Exercice 1 : vos réponses au QCM correspondent exactement à la grille de correction d'un autre sujet."</p>
        </div>
      </div>
    </div>

    <!-- ============ TAB: QCM 5/5 ============ -->
    <div v-show="activeTab === 'qcm'">
      <!-- KPIs QCM -->
      <div class="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <div class="bg-white rounded-xl border border-gray-200 p-4 shadow-sm">
          <ClipboardList class="w-5 h-5 text-blue-600 mb-2" />
          <p class="text-2xl font-bold text-neutralDark">70</p>
          <p class="text-xs text-gray-500 mt-1">Élèves avec 5/5</p>
          <p class="text-xs text-gray-400">33.5% des 209 copies</p>
        </div>
        <div class="bg-white rounded-xl border border-gray-200 p-4 shadow-sm">
          <BarChart3 class="w-5 h-5 text-green-600 mb-2" />
          <p class="text-2xl font-bold text-neutralDark">54</p>
          <p class="text-xs text-gray-500 mt-1">BB_J1 — 50.9%</p>
          <p class="text-xs text-gray-400">QCM très accessible</p>
        </div>
        <div class="bg-white rounded-xl border border-gray-200 p-4 shadow-sm">
          <BarChart3 class="w-5 h-5 text-purple-600 mb-2" />
          <p class="text-2xl font-bold text-neutralDark">16</p>
          <p class="text-xs text-gray-500 mt-1">BB_J2 — 15.5%</p>
          <p class="text-xs text-gray-400">QCM discriminant</p>
        </div>
        <div class="bg-white rounded-xl border border-gray-200 p-4 shadow-sm">
          <AlertTriangle class="w-5 h-5 text-red-500 mb-2" />
          <p class="text-2xl font-bold text-neutralDark">6</p>
          <p class="text-xs text-gray-500 mt-1">5/5 mais &lt; 10/20</p>
          <p class="text-xs text-gray-400">QCM > 50% de la note</p>
        </div>
      </div>

      <!-- Distribution Ex1 -->
      <div class="grid lg:grid-cols-2 gap-6 mb-8">
        <div class="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
          <div class="px-5 py-4 border-b border-gray-100 bg-green-50">
            <h2 class="text-base font-semibold text-green-800">BB_J1 — Distribution Ex1 (moy 4.12/5)</h2>
          </div>
          <div class="px-5 py-4 space-y-2">
            <div v-for="d in distJ1" :key="d.label" class="flex items-center gap-3">
              <span class="w-10 text-xs text-gray-500 font-mono text-right shrink-0">{{ d.label }}</span>
              <div class="flex-1 bg-gray-100 rounded-full h-5 overflow-hidden relative">
                <div class="h-full rounded-full bg-green-500" :style="{ width: (d.count / 54 * 100) + '%' }" />
                <span class="absolute inset-0 flex items-center justify-center text-xs font-semibold" :class="d.count >= 30 ? 'text-white' : 'text-gray-700'">{{ d.count }} ({{ d.pct }})</span>
              </div>
            </div>
          </div>
        </div>
        <div class="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
          <div class="px-5 py-4 border-b border-gray-100 bg-purple-50">
            <h2 class="text-base font-semibold text-purple-800">BB_J2 — Distribution Ex1 (moy 2.93/5)</h2>
          </div>
          <div class="px-5 py-4 space-y-1.5">
            <div v-for="d in distJ2" :key="d.label" class="flex items-center gap-3">
              <span class="w-10 text-xs text-gray-500 font-mono text-right shrink-0">{{ d.label }}</span>
              <div class="flex-1 bg-gray-100 rounded-full h-5 overflow-hidden relative">
                <div class="h-full rounded-full bg-purple-500" :style="{ width: (d.count / 20 * 100) + '%' }" />
                <span class="absolute inset-0 flex items-center justify-center text-xs font-semibold" :class="d.count >= 15 ? 'text-white' : 'text-gray-700'">{{ d.count }} ({{ d.pct }})</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Table 70 élèves -->
      <div class="bg-white rounded-xl border border-gray-200 shadow-sm mb-8 overflow-hidden">
        <div class="px-5 py-4 border-b border-gray-100">
          <h2 class="text-lg font-semibold text-neutralDark">70 Élèves avec 5/5 à l'Exercice 1 (QCM)</h2>
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
                <th class="text-center px-2 py-2.5 font-medium text-gray-600">Grp</th>
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
                <td class="px-2 py-2 text-center text-gray-600">{{ s.groupe }}</td>
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
        <AlertTriangle class="w-5 h-5 text-amber-600 shrink-0 mt-0.5" />
        <div>
          <p class="text-sm font-semibold text-amber-800">24 élèves BB_J1 avec %Ex1 supérieur au seuil BB_J2 (31.2%)</p>
          <p class="text-sm text-amber-700 mt-1">Les 16 élèves BB_J2 ayant eu 5/5 ont un %Ex1 moyen de 31.2%. <strong>24 élèves BB_J1 sur 54</strong> (44.4%) dépassent ce seuil, indiquant un poids disproportionné du QCM dans leur note. Les écarts les plus extrêmes atteignent +49 points (CHAMAM, KHALSI).</p>
        </div>
      </div>
      <div class="bg-red-50 border border-red-200 rounded-xl p-4 flex items-start gap-3 mb-4">
        <AlertTriangle class="w-5 h-5 text-red-600 shrink-0 mt-0.5" />
        <div>
          <p class="text-sm font-semibold text-red-800">6 élèves avec 5/5 au QCM mais note globale &lt; 10/20</p>
          <p class="text-sm text-red-700 mt-1">Pour ces élèves, le QCM représente entre 50% et 80% de leur note totale. Sans le QCM, leur note effective serait entre 1.2 et 5.0 sur 15 points — <strong>fragilité extrême sur les exercices de rédaction</strong>.</p>
          <p class="text-sm text-red-700 mt-1"><strong>4 des 6 sont en T.01</strong> — confirmation de la difficulté structurelle de cette classe (taux réussite BB_J1 : 43.8%).</p>
        </div>
      </div>
      <div class="bg-amber-50 border border-amber-200 rounded-xl p-4 flex items-start gap-3 mb-8">
        <AlertTriangle class="w-5 h-5 text-amber-600 shrink-0 mt-0.5" />
        <div>
          <p class="text-sm font-semibold text-amber-800">Le QCM BB_J1 est très peu discriminant</p>
          <p class="text-sm text-amber-700 mt-1">50.9% des candidats obtiennent 5/5 à BB_J1 contre seulement 15.5% à BB_J2. Le QCM BB_J2 différencie nettement mieux les niveaux (moyenne 2.93/5 vs 4.12/5).</p>
        </div>
      </div>

      <!-- ===== DÉTECTION DE TRICHE ===== -->
      <div class="bg-white rounded-xl border-2 border-red-300 shadow-sm mb-8 overflow-hidden">
        <div class="px-5 py-4 border-b border-red-200 bg-red-50">
          <h2 class="text-lg font-semibold text-red-800 flex items-center gap-2">
            <AlertTriangle class="w-5 h-5 text-red-600" />
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
                <td class="px-3 py-2 font-medium text-red-800">{{ c.name }}</td>
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
              <span class="text-amber-500">●</span>
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

    <!-- ============ TAB: RECOMMANDATIONS ============ -->
    <div v-show="activeTab === 'recommendations'">
      <div class="space-y-6">
        <!-- Constats -->
        <div class="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
          <div class="px-5 py-4 border-b border-gray-100">
            <h2 class="text-lg font-semibold text-neutralDark">Constats Principaux</h2>
          </div>
          <div class="px-5 py-4 space-y-3">
            <div v-for="c in constats" :key="c.text" class="flex items-start gap-3">
              <component :is="c.icon" class="w-4 h-4 mt-0.5 shrink-0" :class="c.color" />
              <p class="text-sm text-gray-700">{{ c.text }}</p>
            </div>
          </div>
        </div>

        <!-- Actions -->
        <div class="grid lg:grid-cols-3 gap-4">
          <div class="bg-white rounded-xl border border-blue-200 shadow-sm overflow-hidden">
            <div class="px-4 py-3 bg-blue-50 border-b border-blue-100">
              <h3 class="text-sm font-semibold text-blue-800">Court Terme</h3>
            </div>
            <ul class="px-4 py-3 space-y-2 text-sm text-gray-700">
              <li class="flex items-start gap-2"><span class="text-blue-500 mt-1">●</span>Remédiation ciblée G5 et T.01</li>
              <li class="flex items-start gap-2"><span class="text-blue-500 mt-1">●</span>Entretiens individuels pour les 11 élèves &lt; 5/20</li>
              <li class="flex items-start gap-2"><span class="text-blue-500 mt-1">●</span>Révision calcul de limites et études de signe</li>
              <li class="flex items-start gap-2"><span class="text-blue-500 mt-1">●</span>Travail rédaction et justification</li>
            </ul>
          </div>
          <div class="bg-white rounded-xl border border-amber-200 shadow-sm overflow-hidden">
            <div class="px-4 py-3 bg-amber-50 border-b border-amber-100">
              <h3 class="text-sm font-semibold text-amber-800">Moyen Terme</h3>
            </div>
            <ul class="px-4 py-3 space-y-2 text-sm text-gray-700">
              <li class="flex items-start gap-2"><span class="text-amber-500 mt-1">●</span>Enquête biais Sujet A/B</li>
              <li class="flex items-start gap-2"><span class="text-amber-500 mt-1">●</span>Suivi suspicion fraude QCM</li>
              <li class="flex items-start gap-2"><span class="text-amber-500 mt-1">●</span>Partage bonnes pratiques G2/T.06 → G5/G3</li>
              <li class="flex items-start gap-2"><span class="text-amber-500 mt-1">●</span>Bac blanc supplémentaire G5 et G3</li>
            </ul>
          </div>
          <div class="bg-white rounded-xl border border-green-200 shadow-sm overflow-hidden">
            <div class="px-4 py-3 bg-green-50 border-b border-green-100">
              <h3 class="text-sm font-semibold text-green-800">Processus de Correction</h3>
            </div>
            <ul class="px-4 py-3 space-y-2 text-sm text-gray-700">
              <li class="flex items-start gap-2"><span class="text-green-500 mt-1">●</span>Finaliser 182 copies en READY</li>
              <li class="flex items-start gap-2"><span class="text-green-500 mt-1">●</span>Générer bilans LLM (167 restantes)</li>
              <li class="flex items-start gap-2"><span class="text-green-500 mt-1">●</span>Déployer résultats portail élève</li>
            </ul>
          </div>
        </div>
      </div>
    </div>

    <!-- Footer -->
    <div class="mt-12 pt-6 border-t border-gray-200 text-center text-xs text-gray-400">
      <p>Rapport rédigé par la Commission de correction — Bac Blanc Mathématiques Spécialité 2026</p>
      <p class="mt-1">Données extraites de la plateforme Korrigo — korrigo.labomaths.tn · 4 mars 2026</p>
    </div>
  </section>
</template>

<script setup>
import { ref, computed } from 'vue'
import {
  BarChart3, Users, GraduationCap, BookOpen, Award, PenTool,
  AlertTriangle, Trophy, CheckCircle2, TrendingUp, TrendingDown,
  MessageSquare, FileText, Brain, ClipboardList,
  Target, Lightbulb
} from 'lucide-vue-next'

const activeTab = ref('overview')

const tabs = [
  { id: 'overview', label: 'Vue d\'ensemble', icon: BarChart3 },
  { id: 'correctors', label: 'Correcteurs', icon: PenTool },
  { id: 'groups', label: 'Groupes', icon: Users },
  { id: 'classes', label: 'Classes', icon: GraduationCap },
  { id: 'subjects', label: 'Sujets A/B', icon: BookOpen },
  { id: 'questions', label: 'Questions', icon: Target },
  { id: 'palmares', label: 'Palmarès', icon: Trophy },
  { id: 'quality', label: 'Correction', icon: MessageSquare },
  { id: 'qcm', label: 'QCM 5/5', icon: ClipboardList },
  { id: 'recommendations', label: 'Recommandations', icon: Lightbulb }
]

const kpis = [
  { label: 'Moyenne Globale', value: '13.25', sub: '/20 — 209 copies', icon: BarChart3, color: 'text-blue-600' },
  { label: 'Taux de Réussite', value: '77.5%', sub: '162/209 ≥ 10', icon: TrendingUp, color: 'text-green-600' },
  { label: 'Mention TB', value: '32.1%', sub: '67 élèves ≥ 16', icon: Award, color: 'text-amber-500' },
  { label: 'En Difficulté', value: '22.5%', sub: '47 élèves < 10', icon: TrendingDown, color: 'text-red-500' }
]

const descriptiveStats = [
  { label: 'Moyenne', j1: '13.79', j2: '12.68', global: '13.25' },
  { label: 'Médiane', j1: '14.48', j2: '13.25', global: '14.00' },
  { label: 'Écart-type', j1: '4.29', j2: '4.48', global: '4.42' },
  { label: 'Minimum', j1: '1.45', j2: '1.00', global: '1.00' },
  { label: 'Maximum', j1: '20.00', j2: '20.00', global: '20.00' },
  { label: 'Q1 (25%)', j1: '10.90', j2: '10.25', global: '10.75' },
  { label: 'Q3 (75%)', j1: '17.60', j2: '16.00', global: '16.70' },
  { label: '≥ 10/20', j1: '83', j2: '79', global: '162' },
  { label: '< 10/20', j1: '23', j2: '24', global: '47' },
  { label: 'Taux réussite', j1: '78.3%', j2: '76.7%', global: '77.5%' }
]

const globalDistribution = [
  { label: '[0;2[', count: 2, pct: '1.0%' },
  { label: '[2;4[', count: 5, pct: '2.4%' },
  { label: '[4;6[', count: 8, pct: '3.8%' },
  { label: '[6;8[', count: 14, pct: '6.7%' },
  { label: '[8;10[', count: 18, pct: '8.6%' },
  { label: '[10;12[', count: 22, pct: '10.5%' },
  { label: '[12;14[', count: 31, pct: '14.8%' },
  { label: '[14;16[', count: 42, pct: '20.1%' },
  { label: '[16;18[', count: 35, pct: '16.7%' },
  { label: '[18;20]', count: 32, pct: '15.3%' }
]

const mentions = [
  { label: 'Très Bien', seuil: '≥ 16', j1: 39, j2: 28, global: 67, pct: '32.1%', labelColor: 'text-green-800', dotColor: 'bg-green-500' },
  { label: 'Bien', seuil: '[14;16[', j1: 23, j2: 19, global: 42, pct: '20.1%', labelColor: 'text-blue-800', dotColor: 'bg-blue-500' },
  { label: 'Assez Bien', seuil: '[12;14[', j1: 12, j2: 19, global: 31, pct: '14.8%', labelColor: 'text-cyan-800', dotColor: 'bg-cyan-500' },
  { label: 'Passable', seuil: '[10;12[', j1: 9, j2: 13, global: 22, pct: '10.5%', labelColor: 'text-amber-800', dotColor: 'bg-amber-500' },
  { label: 'Insuffisant', seuil: '< 10', j1: 23, j2: 24, global: 47, pct: '22.5%', labelColor: 'text-red-800', dotColor: 'bg-red-500' }
]

const correctors = [
  { name: 'Alaeddine BEN RHOUMA', initials: 'AB', exam: 'BB_J1', n: 26, finalized: 26, mean: 14.84, median: '14.85', std: '3.60', min: '5.65', max: '19.50', rate: '92.3%' },
  { name: 'Selima KLIBI', initials: 'SK', exam: 'BB_J1', n: 27, finalized: 0, mean: 13.84, median: '15.35', std: '4.42', min: '1.45', max: '18.90', rate: '81.5%' },
  { name: 'Patrick DUPONT', initials: 'PD', exam: 'BB_J1', n: 26, finalized: 0, mean: 13.34, median: '14.48', std: '4.50', min: '4.60', max: '19.95', rate: '69.2%' },
  { name: 'Philippe CARR', initials: 'PC', exam: 'BB_J1', n: 27, finalized: 0, mean: 13.17, median: '14.00', std: '4.35', min: '4.50', max: '20.00', rate: '70.4%' },
  { name: 'Chawki SAADI', initials: 'CS', exam: 'BB_J2', n: 25, finalized: 1, mean: 13.47, median: '14.00', std: '4.17', min: '2.50', max: '19.00', rate: '80.0%' },
  { name: 'Edouard ROUSSEAU', initials: 'ER', exam: 'BB_J2', n: 26, finalized: 0, mean: 12.80, median: '14.25', std: '5.04', min: '2.00', max: '20.00', rate: '76.9%' },
  { name: 'Sami BEN TIBA', initials: 'SB', exam: 'BB_J2', n: 26, finalized: 0, mean: 12.69, median: '13.00', std: '4.74', min: '1.00', max: '18.75', rate: '73.1%' },
  { name: 'Laroussi LAROUSSI', initials: 'LL', exam: 'BB_J2', n: 26, finalized: 0, mean: 11.80, median: '12.38', std: '3.70', min: '2.75', max: '17.00', rate: '76.9%' }
]

const correctorsSorted = computed(() => [...correctors].sort((a, b) => b.mean - a.mean))

const groupsJ1 = [
  { name: 'G2', teacher: 'Patrick DUPONT', n: 26, mean: '15.38', rate: '92.3%' },
  { name: 'T.06', teacher: 'Selima KLIBI', n: 25, mean: '14.51', rate: '92.0%' },
  { name: 'G1', teacher: 'Philippe CARR', n: 27, mean: '12.90', rate: '70.4%' },
  { name: 'G3', teacher: 'Alaeddine BEN RHOUMA', n: 28, mean: '12.54', rate: '60.7%' }
]
const groupsJ2 = [
  { name: 'T.04', teacher: 'Edouard ROUSSEAU', n: 27, mean: '14.39', rate: '88.9%' },
  { name: 'G6', teacher: 'Sami BEN TIBA', n: 25, mean: '13.53', rate: '84.0%' },
  { name: 'G4', teacher: 'Chawki SAADI', n: 27, mean: '12.84', rate: '74.1%' },
  { name: 'G5', teacher: 'Laroussi LAROUSSI', n: 24, mean: '9.70', rate: '58.3%' }
]

const classesJ1 = [
  { name: 'T.02', n: 17, mean: '16.24', std: '2.09', rate: '100.0%', rateNum: 100, highlight: true, badge: '★', badgeClass: 'bg-green-100 text-green-800' },
  { name: 'T.06', n: 25, mean: '14.51', std: '3.69', rate: '92.0%', rateNum: 92 },
  { name: 'T.07', n: 14, mean: '14.19', std: '5.68', rate: '71.4%', rateNum: 71.4 },
  { name: 'T.08', n: 11, mean: '14.12', std: '4.18', rate: '81.8%', rateNum: 81.8 },
  { name: 'T.03', n: 5, mean: '13.42', std: '4.76', rate: '80.0%', rateNum: 80 },
  { name: 'T.09', n: 8, mean: '12.24', std: '4.03', rate: '75.0%', rateNum: 75 },
  { name: 'T.05', n: 6, mean: '12.03', std: '3.75', rate: '66.7%', rateNum: 66.7 },
  { name: 'T.10', n: 4, mean: '11.76', std: '2.60', rate: '75.0%', rateNum: 75 },
  { name: 'T.01', n: 16, mean: '11.56', std: '4.20', rate: '43.8%', rateNum: 43.8, highlight: true, badge: '⚠', badgeClass: 'bg-red-100 text-red-800' }
]
const classesJ2 = [
  { name: 'T.04', n: 27, mean: '14.39', std: '3.59', rate: '88.9%', rateNum: 88.9 },
  { name: 'T.01', n: 5, mean: '14.30', std: '3.96', rate: '80.0%', rateNum: 80 },
  { name: 'T.10', n: 16, mean: '13.03', std: '3.76', rate: '81.2%', rateNum: 81.2 },
  { name: 'T.03', n: 19, mean: '12.36', std: '5.32', rate: '73.7%', rateNum: 73.7 },
  { name: 'T.09', n: 12, mean: '11.29', std: '4.66', rate: '66.7%', rateNum: 66.7 },
  { name: 'T.05', n: 13, mean: '11.25', std: '4.32', rate: '69.2%', rateNum: 69.2 },
  { name: 'T.07', n: 6, mean: '11.08', std: '2.90', rate: '66.7%', rateNum: 66.7 },
  { name: 'T.08', n: 3, mean: '11.00', std: '6.75', rate: '66.7%', rateNum: 66.7 },
  { name: 'T.02', n: 2, mean: '10.88', std: '2.62', rate: '50.0%', rateNum: 50 }
]

const questions = [
  { id: 'Q1 (QCM)', max: 5.00, mean: 2.93, zeros: 1.0, maxPct: 15.5, difficulty: 'Moyen', hard: false },
  { id: 'Q3.1', max: 0.50, mean: 0.37, zeros: 21.4, maxPct: 70.9, difficulty: 'Facile', hard: false },
  { id: 'Q3.2', max: 0.50, mean: 0.39, zeros: 11.7, maxPct: 68.0, difficulty: 'Facile', hard: false },
  { id: 'Q3.3', max: 1.00, mean: 0.47, zeros: 34.0, maxPct: 33.0, difficulty: 'Moyen', hard: false },
  { id: 'Q3.4', max: 0.75, mean: 0.60, zeros: 10.7, maxPct: 63.1, difficulty: 'Facile', hard: false },
  { id: 'Q3.5', max: 0.50, mean: 0.36, zeros: 15.5, maxPct: 58.3, difficulty: 'Moyen', hard: false },
  { id: 'Q3.6', max: 0.75, mean: 0.52, zeros: 18.4, maxPct: 55.3, difficulty: 'Moyen', hard: false },
  { id: 'Q3.7', max: 1.00, mean: 0.39, zeros: 31.1, maxPct: 15.5, difficulty: 'Difficile', hard: true },
  { id: 'Q2.1.1', max: 0.25, mean: 0.18, zeros: 27.2, maxPct: 72.8, difficulty: 'Moyen', hard: false },
  { id: 'Q2.1.2', max: 0.50, mean: 0.36, zeros: 15.5, maxPct: 61.2, difficulty: 'Moyen', hard: false },
  { id: 'Q2.1.3', max: 1.00, mean: 0.71, zeros: 8.7, maxPct: 39.8, difficulty: 'Facile', hard: false },
  { id: 'Q2.1.4', max: 0.50, mean: 0.32, zeros: 15.5, maxPct: 43.7, difficulty: 'Moyen', hard: false },
  { id: 'Q2.1.5', max: 0.25, mean: 0.17, zeros: 33.0, maxPct: 67.0, difficulty: 'Difficile', hard: true },
  { id: 'Q2.2.1', max: 0.50, mean: 0.34, zeros: 23.3, maxPct: 59.2, difficulty: 'Moyen', hard: false },
  { id: 'Q2.2.2', max: 0.50, mean: 0.41, zeros: 13.6, maxPct: 78.6, difficulty: 'Facile', hard: false },
  { id: 'Q2.2.3', max: 0.50, mean: 0.35, zeros: 22.3, maxPct: 62.1, difficulty: 'Moyen', hard: false },
  { id: 'Q2.2.4', max: 0.50, mean: 0.22, zeros: 45.6, maxPct: 32.0, difficulty: 'Difficile', hard: true },
  { id: 'Q2.2.5', max: 0.50, mean: 0.29, zeros: 26.2, maxPct: 40.8, difficulty: 'Moyen', hard: false },
  { id: 'Q4.1.1', max: 0.50, mean: 0.29, zeros: 31.1, maxPct: 48.5, difficulty: 'Moyen', hard: false },
  { id: 'Q4.1.2', max: 0.50, mean: 0.21, zeros: 31.1, maxPct: 14.6, difficulty: 'Difficile', hard: true },
  { id: 'Q4.2.1', max: 0.75, mean: 0.43, zeros: 22.3, maxPct: 42.7, difficulty: 'Moyen', hard: false },
  { id: 'Q4.2.2', max: 0.50, mean: 0.39, zeros: 13.6, maxPct: 68.9, difficulty: 'Facile', hard: false },
  { id: 'Q4.2.3', max: 0.50, mean: 0.35, zeros: 21.4, maxPct: 59.2, difficulty: 'Moyen', hard: false },
  { id: 'Q4.2.4', max: 1.00, mean: 0.64, zeros: 13.6, maxPct: 39.8, difficulty: 'Moyen', hard: false },
  { id: 'Q4.2.5', max: 0.50, mean: 0.36, zeros: 17.5, maxPct: 62.1, difficulty: 'Moyen', hard: false },
  { id: 'Q4.2.6', max: 0.50, mean: 0.28, zeros: 26.2, maxPct: 36.9, difficulty: 'Difficile', hard: true },
  { id: 'Q4.2.7', max: 0.50, mean: 0.28, zeros: 19.4, maxPct: 32.0, difficulty: 'Difficile', hard: true }
]

function difficultyClass(d) {
  if (d === 'Facile') return 'bg-green-100 text-green-800'
  if (d === 'Moyen') return 'bg-blue-100 text-blue-800'
  if (d === 'Difficile') return 'bg-red-100 text-red-800'
  return 'bg-gray-100 text-gray-800'
}

const top15 = [
  { rank: 1, name: 'HACHICH Selim', classe: 'T.01', groupe: 'G3', exam: 'BB_J1', note: '20.00', corrector: 'Philippe CARR' },
  { rank: 1, name: 'BEN REGUIGA Nour', classe: 'T.04', groupe: 'T.04', exam: 'BB_J2', note: '20.00', corrector: 'Edouard ROUSSEAU' },
  { rank: 3, name: 'BEN RAYANA Mohamed', classe: 'T.07', groupe: 'G1', exam: 'BB_J1', note: '19.95', corrector: 'Patrick DUPONT' },
  { rank: 3, name: 'DRISS Yacine', classe: 'T.02', groupe: 'G2', exam: 'BB_J1', note: '19.95', corrector: 'Patrick DUPONT' },
  { rank: 5, name: 'DOGGAZ Enis', classe: 'T.09', groupe: 'G4', exam: 'BB_J2', note: '19.75', corrector: 'Edouard ROUSSEAU' },
  { rank: 6, name: 'BEN BRAHIM Jawad', classe: 'T.08', groupe: 'G3', exam: 'BB_J1', note: '19.50', corrector: 'Alaeddine BEN RHOUMA' },
  { rank: 6, name: 'ISSA Mourad', classe: 'T.06', groupe: 'T.06', exam: 'BB_J1', note: '19.50', corrector: 'Philippe CARR' },
  { rank: 6, name: 'BLOUZA Emna', classe: 'T.04', groupe: 'T.04', exam: 'BB_J2', note: '19.50', corrector: 'Edouard ROUSSEAU' },
  { rank: 9, name: 'AMARA Fares', classe: 'T.06', groupe: 'T.06', exam: 'BB_J1', note: '19.45', corrector: 'Alaeddine BEN RHOUMA' },
  { rank: 10, name: 'AMMAR Amal', classe: 'T.04', groupe: 'T.04', exam: 'BB_J2', note: '19.00', corrector: 'Chawki SAADI' },
  { rank: 10, name: 'BENNANI Lilya', classe: 'T.05', groupe: 'G6', exam: 'BB_J2', note: '19.00', corrector: 'Chawki SAADI' },
  { rank: 12, name: 'AMEUR Selim', classe: 'T.02', groupe: 'G2', exam: 'BB_J1', note: '18.95', corrector: 'Alaeddine BEN RHOUMA' },
  { rank: 12, name: 'BELCADHI Yoldez', classe: 'T.02', groupe: 'G2', exam: 'BB_J1', note: '18.95', corrector: 'Alaeddine BEN RHOUMA' },
  { rank: 12, name: 'BOUKER Fares', classe: 'T.07', groupe: 'G1', exam: 'BB_J1', note: '18.95', corrector: 'Patrick DUPONT' },
  { rank: 15, name: 'SFIA Iyad Alex', classe: 'T.06', groupe: 'T.06', exam: 'BB_J1', note: '18.90', corrector: 'Selima KLIBI' }
]

const bottom11 = [
  { rank: 209, name: 'SNOUSSI Yasmine', classe: 'T.03', groupe: 'G5', exam: 'BB_J2', note: '1.00', corrector: 'Sami BEN TIBA' },
  { rank: 208, name: 'SATOURI Adem', classe: 'T.07', groupe: 'G1', exam: 'BB_J1', note: '1.45', corrector: 'Selima KLIBI' },
  { rank: 207, name: 'CHANNOUFI Mohamed Yassine', classe: 'T.08', groupe: 'G5', exam: 'BB_J2', note: '2.00', corrector: 'Edouard ROUSSEAU' },
  { rank: 206, name: 'MEZIOU Ines Celia', classe: 'T.03', groupe: 'G4', exam: 'BB_J2', note: '2.25', corrector: 'Sami BEN TIBA' },
  { rank: 205, name: 'BEN MEZIANE Maya', classe: 'T.09', groupe: 'G5', exam: 'BB_J2', note: '2.50', corrector: 'Chawki SAADI' },
  { rank: 204, name: 'IDANI Mariem', classe: 'T.05', groupe: 'G5', exam: 'BB_J2', note: '2.75', corrector: 'Laroussi LAROUSSI' },
  { rank: 203, name: 'DEKHIL Mohamed Selim', classe: 'T.03', groupe: 'G5', exam: 'BB_J2', note: '3.25', corrector: 'Edouard ROUSSEAU' },
  { rank: 202, name: 'EBEYE Yahya', classe: 'T.09', groupe: 'G4', exam: 'BB_J2', note: '4.25', corrector: 'Edouard ROUSSEAU' },
  { rank: 201, name: 'JARRAYA Abdelhamid', classe: 'T.10', groupe: 'G6', exam: 'BB_J2', note: '4.50', corrector: 'Laroussi LAROUSSI' },
  { rank: 200, name: 'MAATOUG Safa', classe: 'T.08', groupe: 'G3', exam: 'BB_J1', note: '4.50', corrector: 'Philippe CARR' },
  { rank: 199, name: 'BOUGHABA Sirine', classe: 'T.03', groupe: 'G1', exam: 'BB_J1', note: '4.60', corrector: 'Patrick DUPONT' }
]

const qualityKpis = [
  { label: 'Remarques pédagogiques', value: '4 054', sub: '184/209 copies', icon: MessageSquare, color: 'text-blue-600' },
  { label: 'Annotations graphiques', value: '706', sub: '83/209 copies', icon: PenTool, color: 'text-purple-600' },
  { label: 'Appréciations globales', value: '100%', sub: '209/209 copies', icon: FileText, color: 'text-green-600' },
  { label: 'Bilans LLM générés', value: '42', sub: '20.1% des copies', icon: Brain, color: 'text-amber-600' }
]

const appreciationTags = [
  { text: 'Très Bien', count: 14, class: 'bg-green-50 border-green-200 text-green-800' },
  { text: 'Bien', count: 7, class: 'bg-blue-50 border-blue-200 text-blue-800' },
  { text: 'Excellent', count: 6, class: 'bg-amber-50 border-amber-200 text-amber-800' },
  { text: 'Ensemble Moyen', count: 4, class: 'bg-gray-50 border-gray-200 text-gray-700' },
  { text: 'Assez Bien', count: 4, class: 'bg-cyan-50 border-cyan-200 text-cyan-800' },
  { text: 'Ensemble Juste', count: 4, class: 'bg-yellow-50 border-yellow-200 text-yellow-800' },
  { text: 'Insuffisant', count: 3, class: 'bg-red-50 border-red-200 text-red-800' },
  { text: 'Bien juste', count: 3, class: 'bg-orange-50 border-orange-200 text-orange-800' },
  { text: 'Ensemble Correct', count: 2, class: 'bg-teal-50 border-teal-200 text-teal-800' }
]

const themes = [
  { label: 'Manque de justification / rédaction', freq: 'Très fréquent', dotColor: 'bg-red-500', tagClass: 'bg-red-100 text-red-800' },
  { label: 'Erreurs de calcul évitables', freq: 'Fréquent', dotColor: 'bg-orange-500', tagClass: 'bg-orange-100 text-orange-800' },
  { label: 'Méthodes classiques non maîtrisées', freq: 'Fréquent', dotColor: 'bg-orange-500', tagClass: 'bg-orange-100 text-orange-800' },
  { label: 'Trop rapide, saute des étapes', freq: 'Occasionnel', dotColor: 'bg-yellow-500', tagClass: 'bg-yellow-100 text-yellow-800' },
  { label: 'Copie vide ou quasi-vide', freq: 'Rare', dotColor: 'bg-gray-400', tagClass: 'bg-gray-100 text-gray-700' },
  { label: 'Suspicion de fraude (QCM)', freq: '1 cas', dotColor: 'bg-red-600', tagClass: 'bg-red-100 text-red-800' }
]

const constats = [
  { text: 'Taux de réussite global satisfaisant : 77.5% (162/209 ≥ 10/20)', icon: CheckCircle2, color: 'text-green-600' },
  { text: 'Disparité entre groupes : de 92.3% (G2) à 58.3% (G5)', icon: AlertTriangle, color: 'text-amber-600' },
  { text: 'Classe T.02 exceptionnelle : 100% de réussite, moyenne 16.24', icon: Trophy, color: 'text-green-600' },
  { text: 'Classe T.01 en difficulté (BB_J1) : 43.8% de réussite seulement', icon: TrendingDown, color: 'text-red-600' },
  { text: 'Écart Sujet A / Sujet B : ~1.5 pts en faveur du Sujet B', icon: AlertTriangle, color: 'text-amber-600' },
  { text: 'Qualité de correction : 19.4 remarques/copie, 100% d\'appréciations', icon: CheckCircle2, color: 'text-green-600' },
  { text: 'Questions discriminantes : Q2.2.4, Q3.7, Q4.2.6-7 très peu réussies', icon: Target, color: 'text-blue-600' },
  { text: '11 élèves sous 5/20 : suivi individualisé urgent', icon: AlertTriangle, color: 'text-red-600' }
]

const distJ1 = [
  { label: '1/5', count: 2, pct: '1.9%' },
  { label: '2/5', count: 14, pct: '13.2%' },
  { label: '3/5', count: 7, pct: '6.6%' },
  { label: '4/5', count: 29, pct: '27.4%' },
  { label: '5/5', count: 54, pct: '50.9%' }
]

const distJ2 = [
  { label: '0/5', count: 1, pct: '1.0%' },
  { label: '0.5', count: 3, pct: '2.9%' },
  { label: '1/5', count: 6, pct: '5.8%' },
  { label: '1.5', count: 13, pct: '12.6%' },
  { label: '2/5', count: 8, pct: '7.8%' },
  { label: '2.5', count: 20, pct: '19.4%' },
  { label: '3/5', count: 12, pct: '11.7%' },
  { label: '3.5', count: 8, pct: '7.8%' },
  { label: '4/5', count: 14, pct: '13.6%' },
  { label: '4.5', count: 2, pct: '1.9%' },
  { label: '5/5', count: 16, pct: '15.5%' }
]

const qcmPerfect = [
  { name: 'BEN REGUIGA Nour', exam: 'BB_J2', classe: 'T.04', groupe: 'T.04', total: 20.00, pct: 25.0, corrector: 'Edouard ROUSSEAU' },
  { name: 'HACHICH Selim', exam: 'BB_J1', classe: 'T.01', groupe: 'G3', total: 20.00, pct: 25.0, corrector: 'Philippe CARR' },
  { name: 'BEN RAYANA Mohamed', exam: 'BB_J1', classe: 'T.07', groupe: 'G1', total: 19.95, pct: 25.1, corrector: 'Patrick DUPONT' },
  { name: 'DRISS Yacine', exam: 'BB_J1', classe: 'T.02', groupe: 'G2', total: 19.95, pct: 25.1, corrector: 'Patrick DUPONT' },
  { name: 'DOGGAZ Enis', exam: 'BB_J2', classe: 'T.09', groupe: 'G4', total: 19.75, pct: 25.3, corrector: 'Edouard ROUSSEAU' },
  { name: 'BEN BRAHIM Jawad', exam: 'BB_J1', classe: 'T.08', groupe: 'G3', total: 19.50, pct: 25.6, corrector: 'Alaeddine BEN RHOUMA' },
  { name: 'BLOUZA Emna', exam: 'BB_J2', classe: 'T.04', groupe: 'T.04', total: 19.50, pct: 25.6, corrector: 'Edouard ROUSSEAU' },
  { name: 'ISSA Mourad', exam: 'BB_J1', classe: 'T.06', groupe: 'T.06', total: 19.50, pct: 25.6, corrector: 'Philippe CARR' },
  { name: 'AMARA Fares', exam: 'BB_J1', classe: 'T.06', groupe: 'T.06', total: 19.45, pct: 25.7, corrector: 'Alaeddine BEN RHOUMA' },
  { name: 'AMMAR Amal', exam: 'BB_J2', classe: 'T.04', groupe: 'T.04', total: 19.00, pct: 26.3, corrector: 'Chawki SAADI' },
  { name: 'BENNANI Lilya', exam: 'BB_J2', classe: 'T.05', groupe: 'G6', total: 19.00, pct: 26.3, corrector: 'Chawki SAADI' },
  { name: 'AMEUR Selim', exam: 'BB_J1', classe: 'T.02', groupe: 'G2', total: 18.95, pct: 26.4, corrector: 'Alaeddine BEN RHOUMA' },
  { name: 'BELCADHI Yoldez', exam: 'BB_J1', classe: 'T.02', groupe: 'G2', total: 18.95, pct: 26.4, corrector: 'Alaeddine BEN RHOUMA' },
  { name: 'SFIA Iyad Alex', exam: 'BB_J1', classe: 'T.06', groupe: 'T.06', total: 18.90, pct: 26.5, corrector: 'Selima KLIBI' },
  { name: 'ALLANI Meriem', exam: 'BB_J1', classe: 'T.08', groupe: 'G3', total: 18.80, pct: 26.6, corrector: 'Alaeddine BEN RHOUMA' },
  { name: 'BEN AYED Salma', exam: 'BB_J1', classe: 'T.07', groupe: 'G1', total: 18.80, pct: 26.6, corrector: 'Alaeddine BEN RHOUMA' },
  { name: 'HAMAIED Emna', exam: 'BB_J1', classe: 'T.02', groupe: 'G2', total: 18.75, pct: 26.7, corrector: 'Philippe CARR' },
  { name: 'JOMAA Emine', exam: 'BB_J1', classe: 'T.06', groupe: 'T.06', total: 18.60, pct: 26.9, corrector: 'Philippe CARR' },
  { name: 'OUEDERNI Rafif', exam: 'BB_J1', classe: 'T.01', groupe: 'G3', total: 18.45, pct: 27.1, corrector: 'Selima KLIBI' },
  { name: 'MEJRI Haroun', exam: 'BB_J1', classe: 'T.05', groupe: 'G2', total: 18.40, pct: 27.2, corrector: 'Selima KLIBI' },
  { name: 'ALBOUCHI Adam', exam: 'BB_J2', classe: 'T.04', groupe: 'T.04', total: 18.25, pct: 27.4, corrector: 'Chawki SAADI' },
  { name: 'AYADI Lina', exam: 'BB_J1', classe: 'T.06', groupe: 'T.06', total: 18.25, pct: 27.4, corrector: 'Alaeddine BEN RHOUMA' },
  { name: 'BCHATNIA Ikram', exam: 'BB_J2', classe: 'T.03', groupe: 'G4', total: 18.25, pct: 27.4, corrector: 'Chawki SAADI' },
  { name: 'BELHAJ Sirine', exam: 'BB_J2', classe: 'T.01', groupe: 'G6', total: 18.25, pct: 27.4, corrector: 'Chawki SAADI' },
  { name: 'BARCHICHE Ines Amelie', exam: 'BB_J1', classe: 'T.07', groupe: 'G1', total: 17.90, pct: 27.9, corrector: 'Alaeddine BEN RHOUMA' },
  { name: 'JALLOULI Amine', exam: 'BB_J1', classe: 'T.02', groupe: 'G2', total: 17.85, pct: 28.0, corrector: 'Philippe CARR' },
  { name: 'BENOTHMAN Malek', exam: 'BB_J2', classe: 'T.04', groupe: 'T.04', total: 17.75, pct: 28.2, corrector: 'Chawki SAADI' },
  { name: 'MRAD Mohamed-Aziz', exam: 'BB_J1', classe: 'T.09', groupe: 'G1', total: 17.70, pct: 28.2, corrector: 'Selima KLIBI' },
  { name: 'SANTOS Sarra Christiane', exam: 'BB_J1', classe: 'T.06', groupe: 'T.06', total: 17.70, pct: 28.2, corrector: 'Selima KLIBI' },
  { name: 'MECHICHI Mehdi', exam: 'BB_J1', classe: 'T.03', groupe: 'G2', total: 17.60, pct: 28.4, corrector: 'Philippe CARR' },
  { name: 'MESTIRI Mahmoud', exam: 'BB_J1', classe: 'T.06', groupe: 'T.06', total: 17.60, pct: 28.4, corrector: 'Selima KLIBI' },
  { name: 'DABOUSSI Iheb', exam: 'BB_J1', classe: 'T.02', groupe: 'G2', total: 17.55, pct: 28.5, corrector: 'Patrick DUPONT' },
  { name: 'BEN GHORBAL Feryel', exam: 'BB_J2', classe: 'T.10', groupe: 'G6', total: 17.50, pct: 28.6, corrector: 'Chawki SAADI' },
  { name: 'MESSEDI Khadija', exam: 'BB_J2', classe: 'T.03', groupe: 'G4', total: 17.50, pct: 28.6, corrector: 'Sami BEN TIBA' },
  { name: 'RAHMOUNI Nesrine Sabrina', exam: 'BB_J1', classe: 'T.07', groupe: 'G1', total: 17.50, pct: 28.6, corrector: 'Selima KLIBI' },
  { name: 'BEL HADJ KHALIFA Mohamed', exam: 'BB_J1', classe: 'T.07', groupe: 'G1', total: 17.45, pct: 28.7, corrector: 'Alaeddine BEN RHOUMA' },
  { name: 'KAMMOUN Aymar', exam: 'BB_J1', classe: 'T.09', groupe: 'G1', total: 16.65, pct: 30.0, corrector: 'Philippe CARR' },
  { name: "M'HIRSI Rayene", exam: 'BB_J1', classe: 'T.03', groupe: 'G2', total: 16.40, pct: 30.5, corrector: 'Selima KLIBI' },
  { name: 'ALOULOU Malek Loula', exam: 'BB_J1', classe: 'T.03', groupe: 'G2', total: 16.25, pct: 30.8, corrector: 'Alaeddine BEN RHOUMA' },
  { name: 'TRABELSI Skander-Aziz', exam: 'BB_J1', classe: 'T.02', groupe: 'G2', total: 16.25, pct: 30.8, corrector: 'Selima KLIBI' },
  { name: 'GHORBAL Sophie', exam: 'BB_J1', classe: 'T.02', groupe: 'G2', total: 16.15, pct: 31.0, corrector: 'Patrick DUPONT' },
  { name: 'SOUISSI Yomna', exam: 'BB_J1', classe: 'T.08', groupe: 'G3', total: 15.90, pct: 31.4, corrector: 'Selima KLIBI' },
  { name: 'LANGAR Mohamed-Amine', exam: 'BB_J2', classe: 'T.04', groupe: 'T.04', total: 15.75, pct: 31.7, corrector: 'Laroussi LAROUSSI' },
  { name: 'KHOUADJA Lina', exam: 'BB_J1', classe: 'T.05', groupe: 'G2', total: 15.50, pct: 32.3, corrector: 'Philippe CARR' },
  { name: 'MARRAKCHI Ahmed', exam: 'BB_J1', classe: 'T.02', groupe: 'G2', total: 15.45, pct: 32.4, corrector: 'Philippe CARR' },
  { name: 'SOUISSI Yosr', exam: 'BB_J1', classe: 'T.02', groupe: 'G2', total: 15.35, pct: 32.6, corrector: 'Selima KLIBI' },
  { name: 'DABOUSSI Yasmine', exam: 'BB_J1', classe: 'T.02', groupe: 'G2', total: 15.15, pct: 33.0, corrector: 'Patrick DUPONT' },
  { name: 'KAABI Omar-Mokhtar', exam: 'BB_J1', classe: 'T.02', groupe: 'G2', total: 15.00, pct: 33.3, corrector: 'Philippe CARR' },
  { name: 'PERON Rayan', exam: 'BB_J1', classe: 'T.09', groupe: 'G1', total: 14.80, pct: 33.8, corrector: 'Selima KLIBI' },
  { name: 'CHOUAYA Youssef', exam: 'BB_J1', classe: 'T.07', groupe: 'G1', total: 14.65, pct: 34.1, corrector: 'Patrick DUPONT' },
  { name: 'AOUADI Ahmed', exam: 'BB_J2', classe: 'T.04', groupe: 'T.04', total: 14.50, pct: 34.5, corrector: 'Chawki SAADI' },
  { name: 'KOUNDI Hedi', exam: 'BB_J2', classe: 'T.04', groupe: 'T.04', total: 14.50, pct: 34.5, corrector: 'Laroussi LAROUSSI' },
  { name: 'TURKI Sami', exam: 'BB_J1', classe: 'T.06', groupe: 'T.06', total: 14.30, pct: 35.0, corrector: 'Selima KLIBI' },
  { name: 'BEN AYED Hafedh', exam: 'BB_J1', classe: 'T.06', groupe: 'T.06', total: 14.10, pct: 35.5, corrector: 'Alaeddine BEN RHOUMA' },
  { name: 'BEN ALI Zeineb', exam: 'BB_J1', classe: 'T.02', groupe: 'G2', total: 14.00, pct: 35.7, corrector: 'Alaeddine BEN RHOUMA' },
  { name: 'BEN JEMAA Sadri', exam: 'BB_J1', classe: 'T.01', groupe: 'G3', total: 14.00, pct: 35.7, corrector: 'Alaeddine BEN RHOUMA' },
  { name: 'BEN JERAD Yassine', exam: 'BB_J1', classe: 'T.01', groupe: 'G3', total: 14.00, pct: 35.7, corrector: 'Alaeddine BEN RHOUMA' },
  { name: 'CHAOUCH Rima', exam: 'BB_J1', classe: 'T.09', groupe: 'G1', total: 12.95, pct: 38.6, corrector: 'Patrick DUPONT' },
  { name: 'ALBANESE Alexandre', exam: 'BB_J1', classe: 'T.06', groupe: 'T.06', total: 12.00, pct: 41.7, corrector: 'Alaeddine BEN RHOUMA' },
  { name: 'GRATI Mohamed-Mehdi', exam: 'BB_J1', classe: 'T.10', groupe: 'G1', total: 11.75, pct: 42.6, corrector: 'Philippe CARR' },
  { name: 'NAJI Ines', exam: 'BB_J1', classe: 'T.01', groupe: 'G3', total: 11.75, pct: 42.6, corrector: 'Selima KLIBI' },
  { name: 'BEN HTIRA Adonis', exam: 'BB_J2', classe: 'T.07', groupe: 'G6', total: 10.75, pct: 46.5, corrector: 'Chawki SAADI' },
  { name: 'SGHAIER Lilia', exam: 'BB_J1', classe: 'T.06', groupe: 'T.06', total: 10.75, pct: 46.5, corrector: 'Selima KLIBI' },
  { name: 'SOUISSI Mohamed Ali', exam: 'BB_J1', classe: 'T.06', groupe: 'T.06', total: 10.35, pct: 48.3, corrector: 'Selima KLIBI' },
  { name: 'CHIHAOUI Ines', exam: 'BB_J1', classe: 'T.01', groupe: 'G3', total: 9.95, pct: 50.3, corrector: 'Patrick DUPONT' },
  { name: 'MONTACER Rayen', exam: 'BB_J1', classe: 'T.01', groupe: 'G3', total: 9.70, pct: 51.5, corrector: 'Selima KLIBI' },
  { name: 'HADROUG Mohamed-Aziz', exam: 'BB_J2', classe: 'T.09', groupe: 'G4', total: 9.00, pct: 55.6, corrector: 'Laroussi LAROUSSI' },
  { name: 'GRAF Alia', exam: 'BB_J1', classe: 'T.01', groupe: 'G3', total: 7.25, pct: 69.0, corrector: 'Philippe CARR' },
  { name: 'KHALSI Safe', exam: 'BB_J1', classe: 'T.01', groupe: 'G3', total: 6.25, pct: 80.0, corrector: 'Philippe CARR' },
  { name: 'CHAMAM Jasim-Brahim', exam: 'BB_J1', classe: 'T.09', groupe: 'G1', total: 6.20, pct: 80.6, corrector: 'Patrick DUPONT' }
]

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

<style scoped>
.no-scrollbar::-webkit-scrollbar {
  display: none;
}
.no-scrollbar {
  -ms-overflow-style: none;
  scrollbar-width: none;
}
</style>
