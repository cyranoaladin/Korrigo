<template>
  <section class="max-w-6xl mx-auto px-4 sm:px-6 py-10 md:py-14">
    <!-- Loading -->
    <div v-if="loading" class="flex items-center justify-center py-32">
      <div class="animate-spin rounded-full h-12 w-12 border-4 border-primary-200 border-t-primary-600"></div>
      <span class="ml-4 text-gray-500">Chargement des statistiques…</span>
    </div>

    <!-- Error -->
    <div v-else-if="error" class="bg-red-50 border border-red-200 rounded-xl p-6 text-center">
      <AlertTriangle class="w-8 h-8 text-red-500 mx-auto mb-2" />
      <p class="text-red-700 font-medium">Erreur de chargement</p>
      <p class="text-red-500 text-sm mt-1">{{ error }}</p>
    </div>

    <!-- Header -->
    <div v-else class="mb-10">
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
        <span class="bg-blue-100 text-blue-800 px-2.5 py-1 rounded-full font-medium">{{ header.n_candidates }} candidats</span>
        <span class="bg-green-100 text-green-800 px-2.5 py-1 rounded-full font-medium">BB_J1 : {{ header.n_j1 }} copies</span>
        <span class="bg-purple-100 text-purple-800 px-2.5 py-1 rounded-full font-medium">BB_J2 : {{ header.n_j2 }} copies</span>
        <span class="bg-gray-100 text-gray-700 px-2.5 py-1 rounded-full font-medium">{{ header.n_correctors }} correcteurs</span>
        <span class="bg-amber-100 text-amber-800 px-2.5 py-1 rounded-full font-medium">4 mars 2026</span>
      </div>
    </div>

    <!-- Navigation tabs -->
    <div v-if="data" class="sticky top-16 z-40 bg-gray-50/95 backdrop-blur-sm -mx-4 sm:-mx-6 px-4 sm:px-6 py-3 border-b border-gray-200 mb-8">
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
    <div v-if="activeTab === 'overview'">
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
                <th class="text-center px-4 py-2.5 font-medium text-green-700">BB_J1 ({{ header.n_j1 }})</th>
                <th class="text-center px-4 py-2.5 font-medium text-purple-700">BB_J2 ({{ header.n_j2 }})</th>
                <th class="text-center px-4 py-2.5 font-medium text-blue-700">Global ({{ header.n_candidates }})</th>
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
          <h2 class="text-lg font-semibold text-neutralDark">Distribution des Notes — Global ({{ header.n_candidates }} copies)</h2>
        </div>
        <div class="px-5 py-4 space-y-2">
          <div v-for="bin in globalDistribution" :key="bin.label" class="flex items-center gap-3">
            <span class="w-16 text-xs text-gray-500 font-mono text-right shrink-0">{{ bin.label }}</span>
            <div class="flex-1 bg-gray-100 rounded-full h-6 overflow-hidden relative">
              <div
                class="h-full rounded-full transition-all duration-500"
                :class="bin.count >= 30 ? 'bg-primary-600' : bin.count >= 20 ? 'bg-primary-500' : bin.count >= 10 ? 'bg-primary-400' : 'bg-primary-300'"
                :style="{ width: (bin.count / maxDistCount * 100) + '%' }"
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
    <div v-if="activeTab === 'correctors'">
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
    <div v-if="activeTab === 'groups'">
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

      <!-- Alert worst group -->
      <div v-if="groupsJ2.length" class="bg-red-50 border border-red-200 rounded-xl p-4 flex items-start gap-3">
        <AlertTriangle class="w-5 h-5 text-red-600 shrink-0 mt-0.5" />
        <div>
          <p class="text-sm font-semibold text-red-800">Groupe {{ groupsJ2[groupsJ2.length - 1]?.name }} en difficulté</p>
          <p class="text-sm text-red-700 mt-1">Moyenne {{ groupsJ2[groupsJ2.length - 1]?.mean }}/20, taux de réussite {{ groupsJ2[groupsJ2.length - 1]?.rate }} — nettement en-deçà des autres groupes. Remédiation ciblée recommandée.</p>
        </div>
      </div>
    </div>

    <!-- ============ TAB: CLASSES ============ -->
    <div v-if="activeTab === 'classes'">
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
    <div v-if="activeTab === 'subjects'">
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
                <td class="px-4 py-2 text-center">{{ subjects.j1_a?.n ?? '—' }}</td>
                <td class="px-4 py-2 text-center">{{ subjects.j1_b?.n ?? '—' }}</td>
                <td class="px-4 py-2 text-center">{{ subjects.j2_a?.n ?? '—' }}</td>
                <td class="px-4 py-2 text-center">{{ subjects.j2_b?.n ?? '—' }}</td>
              </tr>
              <tr class="border-t border-gray-100">
                <td class="px-4 py-2 font-medium text-gray-700">Moyenne</td>
                <td class="px-4 py-2 text-center">{{ subjects.j1_a?.mean ?? '—' }}</td>
                <td class="px-4 py-2 text-center font-bold text-green-700">{{ subjects.j1_b?.mean ?? '—' }}</td>
                <td class="px-4 py-2 text-center">{{ subjects.j2_a?.mean ?? '—' }}</td>
                <td class="px-4 py-2 text-center font-bold text-purple-700">{{ subjects.j2_b?.mean ?? '—' }}</td>
              </tr>
              <tr class="border-t border-gray-100">
                <td class="px-4 py-2 font-medium text-gray-700">Médiane</td>
                <td class="px-4 py-2 text-center">{{ subjects.j1_a?.median ?? '—' }}</td>
                <td class="px-4 py-2 text-center">{{ subjects.j1_b?.median ?? '—' }}</td>
                <td class="px-4 py-2 text-center">{{ subjects.j2_a?.median ?? '—' }}</td>
                <td class="px-4 py-2 text-center">{{ subjects.j2_b?.median ?? '—' }}</td>
              </tr>
              <tr class="border-t border-gray-100">
                <td class="px-4 py-2 font-medium text-gray-700">Écart-type</td>
                <td class="px-4 py-2 text-center">{{ subjects.j1_a?.std ?? '—' }}</td>
                <td class="px-4 py-2 text-center">{{ subjects.j1_b?.std ?? '—' }}</td>
                <td class="px-4 py-2 text-center">{{ subjects.j2_a?.std ?? '—' }}</td>
                <td class="px-4 py-2 text-center">{{ subjects.j2_b?.std ?? '—' }}</td>
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
    <div v-if="activeTab === 'questions'">
      <div class="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
        <div class="px-5 py-4 border-b border-gray-100">
          <h2 class="text-lg font-semibold text-neutralDark">Analyse par Question — BB_J2 ({{ questions.length }} questions, {{ header.n_j2 }} copies)</h2>
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
    <StatsPalmaresTab v-if="activeTab === 'palmares'" :data="data" />

    <!-- ============ TAB: CORRECTION ============ -->
    <StatsQualityTab v-if="activeTab === 'quality'" :data="data" />

    <!-- ============ TAB: QCM 5/5 ============ -->
    <StatsQcmTab v-if="activeTab === 'qcm'" :data="data" :header="header" />

    <!-- ============ TAB: RECOMMANDATIONS ============ -->
    <div v-if="activeTab === 'recommendations'">
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
              <li class="flex items-start gap-2"><span class="text-green-500 mt-1">●</span>209/209 copies finalisées ✓</li>
              <li class="flex items-start gap-2"><span class="text-green-500 mt-1">●</span>Générer bilans LLM (167 restantes)</li>
              <li class="flex items-start gap-2"><span class="text-green-500 mt-1">●</span>Portail élève déployé ✓</li>
            </ul>
          </div>
        </div>
      </div>
    </div>

    <!-- Footer -->
    <div class="mt-12 pt-6 border-t border-gray-200 text-center text-xs text-gray-400">
      <p>Rapport rédigé par la Commission de correction — Bac Blanc Mathématiques Spécialité 2026</p>
      <p class="mt-1">Données extraites de la plateforme Korrigo — korrigo.labomaths.tn · 5 mars 2026</p>
    </div>
  </section>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import api from '../services/api'
import {
  BarChart3, Users, GraduationCap, BookOpen, Award, PenTool,
  AlertTriangle, Trophy, CheckCircle2, TrendingUp, TrendingDown,
  MessageSquare, Target, Lightbulb, ClipboardList
} from 'lucide-vue-next'
import StatsQcmTab from '../components/stats/StatsQcmTab.vue'
import StatsPalmaresTab from '../components/stats/StatsPalmaresTab.vue'
import StatsQualityTab from '../components/stats/StatsQualityTab.vue'

const router = useRouter()
const authStore = useAuthStore()

const activeTab = ref('overview')
const loading = ref(true)
const error = ref(null)
const data = ref(null)

onMounted(async () => {
  // Defense-in-depth: redirect if not Teacher/Admin
  if (!authStore.user) {
    try { await authStore.fetchUser() } catch { /* ignore */ }
  }
  const role = authStore.user?.role
  if (role !== 'Teacher' && role !== 'Admin') {
    router.replace('/')
    return
  }

  try {
    const res = await api.get('/exams/stats-report/')
    data.value = res.data
  } catch (e) {
    if (e.response?.status === 403) {
      error.value = 'Accès réservé aux enseignants et à l\'administration.'
    } else {
      error.value = e.response?.data?.error || e.message || 'Erreur de chargement'
    }
  } finally {
    loading.value = false
  }
})

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

const header = computed(() => data.value?.header || {})

const kpis = computed(() => {
  if (!data.value) return []
  const k = data.value.kpis
  return [
    { label: 'Moyenne Globale', value: String(k.global_mean), sub: `/20 — ${k.total} copies`, icon: BarChart3, color: 'text-blue-600' },
    { label: 'Taux de Réussite', value: `${k.pass_rate}%`, sub: `${k.pass_count}/${k.total} ≥ 10`, icon: TrendingUp, color: 'text-green-600' },
    { label: 'Mention TB', value: `${k.tb_rate}%`, sub: `${k.tb_count} élèves ≥ 16`, icon: Award, color: 'text-amber-500' },
    { label: 'En Difficulté', value: `${k.difficulty_rate}%`, sub: `${k.difficulty_count} élèves < 10`, icon: TrendingDown, color: 'text-red-500' }
  ]
})

const descriptiveStats = computed(() => {
  if (!data.value) return []
  const j1 = data.value.descriptive_stats.j1
  const j2 = data.value.descriptive_stats.j2
  const g = data.value.descriptive_stats.global
  return [
    { label: 'Moyenne', j1: j1.mean, j2: j2.mean, global: g.mean },
    { label: 'Médiane', j1: j1.median, j2: j2.median, global: g.median },
    { label: 'Écart-type', j1: j1.std, j2: j2.std, global: g.std },
    { label: 'Minimum', j1: j1.min, j2: j2.min, global: g.min },
    { label: 'Maximum', j1: j1.max, j2: j2.max, global: g.max },
    { label: 'Q1 (25%)', j1: j1.q1, j2: j2.q1, global: g.q1 },
    { label: 'Q3 (75%)', j1: j1.q3, j2: j2.q3, global: g.q3 },
    { label: '≥ 10/20', j1: j1.ge10, j2: j2.ge10, global: g.ge10 },
    { label: '< 10/20', j1: j1.lt10, j2: j2.lt10, global: g.lt10 },
    { label: 'Taux réussite', j1: `${j1.rate}%`, j2: `${j2.rate}%`, global: `${g.rate}%` }
  ]
})

const globalDistribution = computed(() => data.value?.global_distribution || [])
const maxDistCount = computed(() => Math.max(...(globalDistribution.value.map(b => b.count)), 1))

const mentions = computed(() => data.value?.mentions || [])

const correctors = computed(() => data.value?.correctors || [])
const correctorsSorted = computed(() => [...correctors.value].sort((a, b) => (b.mean || 0) - (a.mean || 0)))

const groupsJ1 = computed(() => data.value?.groups_j1 || [])
const groupsJ2 = computed(() => data.value?.groups_j2 || [])

const classesJ1 = computed(() => data.value?.classes_j1 || [])
const classesJ2 = computed(() => data.value?.classes_j2 || [])

const subjects = computed(() => data.value?.subjects || {})

const questions = computed(() => data.value?.questions || [])

function difficultyClass(d) {
  if (d === 'Facile') return 'bg-green-100 text-green-800'
  if (d === 'Moyen') return 'bg-blue-100 text-blue-800'
  if (d === 'Difficile') return 'bg-red-100 text-red-800'
  return 'bg-gray-100 text-gray-800'
}

const constats = computed(() => {
  if (!data.value) return []
  const k = data.value.kpis
  const q = data.value.quality
  const allGroups = [...(data.value.groups_j1 || []), ...(data.value.groups_j2 || [])]
  const bestGroup = allGroups.length ? allGroups.reduce((a, b) => parseFloat(a.rate) > parseFloat(b.rate) ? a : b) : null
  const worstGroup = allGroups.length ? allGroups.reduce((a, b) => parseFloat(a.rate) < parseFloat(b.rate) ? a : b) : null
  const cJ1 = data.value.classes_j1 || []
  const bestClass = cJ1.length ? cJ1[0] : null
  const worstClass = cJ1.length ? cJ1[cJ1.length - 1] : null
  const remarksPerCopy = q.total_copies > 0 ? (q.remarks_count / q.total_copies).toFixed(1) : '0'
  const hardQs = (data.value.questions || []).filter(q => q.difficulty === 'Difficile').map(q => q.id).join(', ')
  const bot = data.value.bottom11 || []
  return [
    { text: `Taux de réussite global satisfaisant : ${k.pass_rate}% (${k.pass_count}/${k.total} ≥ 10/20)`, icon: CheckCircle2, color: 'text-green-600' },
    bestGroup && worstGroup ? { text: `Disparité entre groupes : de ${bestGroup.rate} (${bestGroup.name}) à ${worstGroup.rate} (${worstGroup.name})`, icon: AlertTriangle, color: 'text-amber-600' } : null,
    bestClass ? { text: `Classe ${bestClass.name} exceptionnelle : ${bestClass.rate} de réussite, moyenne ${bestClass.mean}`, icon: Trophy, color: 'text-green-600' } : null,
    worstClass ? { text: `Classe ${worstClass.name} en difficulté (BB_J1) : ${worstClass.rate} de réussite`, icon: TrendingDown, color: 'text-red-600' } : null,
    { text: `Qualité de correction : ${remarksPerCopy} remarques/copie, ${q.appreciation_rate} d'appréciations`, icon: CheckCircle2, color: 'text-green-600' },
    hardQs ? { text: `Questions discriminantes : ${hardQs}`, icon: Target, color: 'text-blue-600' } : null,
    { text: `${bot.length} élèves sous 5/20 : suivi individualisé urgent`, icon: AlertTriangle, color: 'text-red-600' }
  ].filter(Boolean)
})

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
