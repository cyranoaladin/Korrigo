<template>
  <div class="min-h-screen bg-slate-50">

    <!-- HERO HEADER -->
    <div class="bg-gradient-to-br from-indigo-700 via-indigo-600 to-violet-700 text-white print:bg-indigo-700">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 py-8">

        <div class="flex items-center gap-2 text-indigo-200 text-sm mb-6">
          <button @click="$router.go(-1)" class="hover:text-white flex items-center gap-1 transition-colors">
            <AppIcon name="arrow-left" :size="14" />
            Retour
          </button>
          <span class="text-indigo-300">›</span>
          <span class="text-white font-medium">Bilan Bac Blanc Maths 2026</span>
        </div>

        <div class="flex flex-col lg:flex-row lg:items-start lg:justify-between gap-6 mb-8">
          <div>
            <div class="flex items-center gap-3 mb-3">
              <div class="w-12 h-12 bg-white/15 rounded-2xl flex items-center justify-center border border-white/20">
                <AppIcon name="book-open" :size="22" class="text-white" />
              </div>
              <div>
                <div class="text-indigo-200 text-xs font-semibold uppercase tracking-widest">Rapport du Jury · 4 mars 2026</div>
                <div class="text-indigo-300 text-xs">Lycée Pierre Mendès France — Tunis (AEFE)</div>
              </div>
            </div>
            <h1 class="text-3xl lg:text-4xl font-bold tracking-tight mb-2">Bac Blanc Mathématiques 2026</h1>
            <p class="text-indigo-200 text-sm">Session Terminale Spécialité · BB_J1 &amp; BB_J2 · 8 correcteurs · Données Korrigo prod.</p>
          </div>
          <div class="flex items-center gap-3 shrink-0">
            <span class="inline-flex items-center gap-1.5 bg-emerald-500/20 border border-emerald-400/40 text-emerald-300 text-xs font-semibold px-3 py-1.5 rounded-full">
              <span class="w-1.5 h-1.5 bg-emerald-400 rounded-full"></span>
              Rapport finalisé
            </span>
            <button @click="printPage" class="inline-flex items-center gap-2 bg-white/10 hover:bg-white/20 border border-white/20 text-white px-4 py-2 rounded-xl text-sm font-medium transition-colors">
              <AppIcon name="printer" :size="15" />
              Imprimer
            </button>
          </div>
        </div>

        <!-- KPI cards -->
        <div class="grid grid-cols-2 lg:grid-cols-4 gap-3">
          <div v-for="kpi in kpis" :key="kpi.label" class="bg-white/10 backdrop-blur-sm rounded-2xl p-4 border border-white/15 hover:bg-white/15 transition-colors">
            <div class="text-indigo-200 text-xs font-medium uppercase tracking-wide mb-1">{{ kpi.label }}</div>
            <div class="text-3xl font-bold">{{ kpi.value }}<span class="text-lg text-indigo-300">{{ kpi.unit }}</span></div>
            <div class="text-indigo-300 text-xs mt-1.5 leading-snug">{{ kpi.sub }}</div>
          </div>
        </div>
      </div>
    </div>

    <!-- TABS NAVIGATION -->
    <div class="bg-white border-b border-gray-200 sticky top-0 z-20 shadow-sm print:hidden">
      <div class="max-w-7xl mx-auto px-4 sm:px-6">
        <nav class="flex gap-0.5 overflow-x-auto py-1">
          <button
            v-for="tab in visibleTabs" :key="tab.id" @click="activeTab = tab.id"
            :class="['flex items-center gap-2 px-4 py-2.5 text-sm font-medium rounded-lg whitespace-nowrap transition-all',
              activeTab === tab.id ? 'bg-indigo-50 text-indigo-700 shadow-sm ring-1 ring-indigo-100' : 'text-gray-500 hover:text-gray-800 hover:bg-gray-50']"
          >
            <AppIcon :name="tab.icon" :size="14" />
            {{ tab.label }}
          </button>
        </nav>
      </div>
    </div>

    <!-- CONTENT -->
    <div class="max-w-7xl mx-auto px-4 sm:px-6 py-8">

      <!-- TAB: Vue d'ensemble -->
      <div v-if="activeTab === 'overview'" class="space-y-6">

        <div class="grid sm:grid-cols-3 gap-4">
          <div v-for="sig in signals" :key="sig.key" :class="sig.bg" class="rounded-2xl p-4 border">
            <div class="flex items-start gap-3">
              <div :class="sig.iconBg" class="w-9 h-9 rounded-xl flex items-center justify-center shrink-0 mt-0.5">
                <AppIcon :name="sig.icon" :size="16" :class="sig.iconColor" />
              </div>
              <div>
                <div :class="sig.titleColor" class="text-sm font-semibold mb-0.5">{{ sig.title }}</div>
                <div :class="sig.textColor" class="text-xs leading-relaxed">{{ sig.message }}</div>
              </div>
            </div>
          </div>
        </div>

        <div class="grid lg:grid-cols-2 gap-6">
          <div class="bg-white rounded-2xl border border-gray-200 overflow-hidden shadow-sm">
            <div class="px-5 py-4 border-b border-gray-100">
              <h2 class="text-base font-semibold text-gray-900 flex items-center gap-2">
                <AppIcon name="bar-chart-2" :size="16" class="text-indigo-500" />
                Statistiques descriptives
              </h2>
            </div>
            <div class="overflow-x-auto">
              <table class="w-full text-sm">
                <thead class="bg-gray-50 border-b border-gray-100">
                  <tr>
                    <th class="px-4 py-3 text-left font-medium text-gray-600">Indicateur</th>
                    <th class="px-4 py-3 text-center font-medium text-indigo-600">BB_J1 (106)</th>
                    <th class="px-4 py-3 text-center font-medium text-violet-600">BB_J2 (103)</th>
                    <th class="px-4 py-3 text-center font-medium text-gray-900">Global (209)</th>
                  </tr>
                </thead>
                <tbody class="divide-y divide-gray-50">
                  <tr v-for="row in descStats" :key="row.label" class="hover:bg-gray-50">
                    <td class="px-4 py-2.5 text-gray-600 font-medium">{{ row.label }}</td>
                    <td class="px-4 py-2.5 text-center text-indigo-700 font-semibold">{{ row.j1 }}</td>
                    <td class="px-4 py-2.5 text-center text-violet-700 font-semibold">{{ row.j2 }}</td>
                    <td class="px-4 py-2.5 text-center font-bold text-gray-900">{{ row.global }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>

          <div class="bg-white rounded-2xl border border-gray-200 p-5 shadow-sm">
            <h2 class="text-base font-semibold text-gray-900 mb-4 flex items-center gap-2">
              <AppIcon name="award" :size="16" class="text-indigo-500" />
              Répartition par mention
            </h2>
            <div class="space-y-3">
              <div v-for="m in MENTIONS" :key="m.key">
                <div class="flex items-center justify-between mb-1">
                  <span class="text-sm font-medium text-gray-700">{{ m.label }}</span>
                  <div class="flex items-center gap-3">
                    <span class="text-xs text-gray-500 font-semibold text-gray-800">{{ m.global }} élèves</span>
                    <span :class="m.pctClass" class="font-bold text-sm">{{ m.pct_g }}%</span>
                  </div>
                </div>
                <div class="flex gap-1 h-5 rounded-lg overflow-hidden bg-gray-100">
                  <div :class="m.colorJ1" class="h-full transition-all duration-700 rounded-l-lg" :style="{ width: `${(m.j1 / 209) * 100}%` }" :title="`BB_J1 : ${m.j1}`"></div>
                  <div :class="m.colorJ2" class="h-full transition-all duration-700 rounded-r-lg opacity-70" :style="{ width: `${(m.j2 / 209) * 100}%` }" :title="`BB_J2 : ${m.j2}`"></div>
                </div>
                <div class="flex justify-between text-xs text-gray-400 mt-0.5">
                  <span>J1 : {{ m.j1 }}</span><span>J2 : {{ m.j2 }}</span>
                </div>
              </div>
              <div class="flex items-center gap-4 pt-2 text-xs text-gray-400">
                <span class="flex items-center gap-1.5"><span class="w-3 h-3 rounded bg-indigo-400 inline-block"></span>BB_J1</span>
                <span class="flex items-center gap-1.5"><span class="w-3 h-3 rounded bg-violet-400 inline-block"></span>BB_J2</span>
              </div>
            </div>
          </div>
        </div>

        <div class="bg-white rounded-2xl border border-gray-200 p-5 shadow-sm">
          <h2 class="text-base font-semibold text-gray-900 mb-4 flex items-center gap-2">
            <AppIcon name="check-circle" :size="16" class="text-emerald-500" />
            Qualité de la correction
          </h2>
          <div class="grid grid-cols-2 sm:grid-cols-4 gap-4">
            <div v-for="q in qualiteMetrics" :key="q.label" :class="q.bg" class="rounded-xl p-4 text-center border">
              <div :class="q.valueColor" class="text-2xl font-bold mb-0.5">{{ q.value }}</div>
              <div class="text-xs font-medium text-gray-600">{{ q.label }}</div>
              <div class="text-xs text-gray-400 mt-0.5">{{ q.sub }}</div>
            </div>
          </div>
        </div>
      </div>

      <!-- TAB: Distribution -->
      <div v-if="activeTab === 'distribution'" class="space-y-6">
        <div class="grid lg:grid-cols-2 gap-6">
          <div class="bg-white rounded-2xl border border-gray-200 p-5 shadow-sm">
            <h2 class="text-base font-semibold text-gray-900 mb-1 flex items-center gap-2">
              <AppIcon name="bar-chart" :size="16" class="text-indigo-500" />
              Distribution des notes — Global (209 copies)
            </h2>
            <p class="text-xs text-gray-400 mb-5">Effectifs par tranche de 2 points</p>
            <svg viewBox="0 0 440 220" class="w-full" style="max-height:220px">
              <line v-for="y in [40,80,120,160,200]" :key="y" x1="44" :y1="y" x2="436" :y2="y" stroke="#f1f5f9" stroke-width="1"/>
              <text v-for="(n, i) in [40,30,20,10,0]" :key="i" x="36" :y="i*40+44" text-anchor="end" font-size="10" fill="#94a3b8">{{ n }}</text>
              <g v-for="(b, i) in HISTOGRAM" :key="i">
                <rect :x="48 + i * 39" :y="200 - b.count * 4" width="36" :height="b.count * 4" :fill="barColorHex(i)" rx="3" opacity="0.85"/>
                <text :x="66 + i * 39" :y="200 - b.count * 4 - 4" text-anchor="middle" font-size="9" font-weight="600" fill="#475569">{{ b.count }}</text>
                <text :x="66 + i * 39" y="213" text-anchor="middle" font-size="8" fill="#94a3b8" :transform="`rotate(-35, ${66 + i * 39}, 213)`">{{ b.range }}</text>
              </g>
              <line x1="44" y1="200" x2="436" y2="200" stroke="#e2e8f0" stroke-width="1.5"/>
            </svg>
          </div>

          <div class="bg-white rounded-2xl border border-gray-200 p-5 shadow-sm">
            <h2 class="text-base font-semibold text-gray-900 mb-4 flex items-center gap-2">
              <AppIcon name="layers" :size="16" class="text-indigo-500" />
              BB_J1 vs BB_J2 — Indicateurs comparatifs
            </h2>
            <div class="space-y-4">
              <div v-for="comp in comparaisons" :key="comp.label">
                <div class="flex justify-between text-xs text-gray-500 mb-1">
                  <span class="font-medium text-gray-700">{{ comp.label }}</span>
                </div>
                <div class="grid grid-cols-2 gap-2">
                  <div class="bg-indigo-50 rounded-lg px-3 py-2 text-center">
                    <div class="text-lg font-bold text-indigo-700">{{ comp.j1 }}</div>
                    <div class="text-xs text-indigo-400">BB_J1</div>
                  </div>
                  <div class="bg-violet-50 rounded-lg px-3 py-2 text-center">
                    <div class="text-lg font-bold text-violet-700">{{ comp.j2 }}</div>
                    <div class="text-xs text-violet-400">BB_J2</div>
                  </div>
                </div>
              </div>
            </div>
            <div class="mt-5 pt-5 border-t border-gray-100">
              <h3 class="text-sm font-semibold text-amber-700 mb-3 flex items-center gap-2">
                <AppIcon name="alert-triangle" :size="14" class="text-amber-500" />
                Biais Sujet A vs Sujet B
              </h3>
              <div class="grid grid-cols-2 gap-3 text-xs">
                <div class="bg-amber-50 rounded-xl p-3 border border-amber-100">
                  <div class="font-semibold text-amber-800 mb-2">BB_J1</div>
                  <div class="space-y-1 text-amber-700">
                    <div class="flex justify-between"><span>Sujet A</span><span class="font-bold">12.98/20</span></div>
                    <div class="flex justify-between"><span>Sujet B</span><span class="font-bold text-amber-900">14.60/20</span></div>
                    <div class="flex justify-between border-t border-amber-200 pt-1 mt-1"><span>Écart</span><span class="font-bold text-red-600">+1.62 pts</span></div>
                  </div>
                </div>
                <div class="bg-amber-50 rounded-xl p-3 border border-amber-100">
                  <div class="font-semibold text-amber-800 mb-2">BB_J2</div>
                  <div class="space-y-1 text-amber-700">
                    <div class="flex justify-between"><span>Sujet A</span><span class="font-bold">12.16/20</span></div>
                    <div class="flex justify-between"><span>Sujet B</span><span class="font-bold text-amber-900">13.23/20</span></div>
                    <div class="flex justify-between border-t border-amber-200 pt-1 mt-1"><span>Écart</span><span class="font-bold text-red-600">+1.07 pts</span></div>
                  </div>
                </div>
              </div>
              <p class="text-xs text-amber-600 mt-2 italic">Sujet B systématiquement supérieur. À investiguer.</p>
            </div>
          </div>
        </div>

        <div class="bg-white rounded-2xl border border-gray-200 overflow-hidden shadow-sm">
          <div class="px-5 py-4 border-b border-gray-100">
            <h2 class="text-base font-semibold text-gray-900 flex items-center gap-2">
              <AppIcon name="table" :size="16" class="text-indigo-500" />
              Distribution détaillée par tranche
            </h2>
          </div>
          <div class="overflow-x-auto">
            <table class="w-full text-sm">
              <thead class="bg-gray-50 border-b border-gray-100">
                <tr>
                  <th class="px-4 py-3 text-left font-medium text-gray-600">Tranche</th>
                  <th class="px-4 py-3 text-center font-medium text-gray-600">Global</th>
                  <th class="px-4 py-3 text-center font-medium text-indigo-600">BB_J1</th>
                  <th class="px-4 py-3 text-center font-medium text-violet-600">BB_J2</th>
                  <th class="px-4 py-3 text-left font-medium text-gray-600">Proportion</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-gray-50">
                <tr v-for="(b, i) in HISTOGRAM" :key="b.range" class="hover:bg-gray-50">
                  <td class="px-4 py-2.5 font-mono text-gray-700">{{ b.range }}</td>
                  <td class="px-4 py-2.5 text-center font-bold text-gray-900">{{ b.count }}</td>
                  <td class="px-4 py-2.5 text-center text-indigo-600">{{ b.j1 }}</td>
                  <td class="px-4 py-2.5 text-center text-violet-600">{{ b.j2 }}</td>
                  <td class="px-4 py-2.5">
                    <div class="flex items-center gap-2">
                      <div class="flex-1 bg-gray-100 rounded-full h-3 overflow-hidden">
                        <div class="h-3 rounded-full" :style="{ width: `${(b.count / 42) * 100}%`, background: barColorHex(i) }"></div>
                      </div>
                      <span class="text-xs text-gray-400 w-10 text-right">{{ ((b.count / 209) * 100).toFixed(1) }}%</span>
                    </div>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>

      <!-- TAB: Classes et groupes -->
      <div v-if="activeTab === 'classes'" class="space-y-6">
        <div class="grid sm:grid-cols-2 gap-4">
          <div class="bg-red-50 border border-red-200 rounded-2xl p-4 flex items-start gap-3">
            <div class="w-9 h-9 bg-red-100 rounded-xl flex items-center justify-center shrink-0">
              <AppIcon name="alert-triangle" :size="16" class="text-red-600" />
            </div>
            <div>
              <div class="text-sm font-semibold text-red-800">T.01 (BB_J1) — Classe en difficulté</div>
              <div class="text-xs text-red-600 mt-0.5">43.8% de réussite · Médiane : 9.82/20</div>
            </div>
          </div>
          <div class="bg-emerald-50 border border-emerald-200 rounded-2xl p-4 flex items-start gap-3">
            <div class="w-9 h-9 bg-emerald-100 rounded-xl flex items-center justify-center shrink-0">
              <AppIcon name="star" :size="16" class="text-emerald-600" />
            </div>
            <div>
              <div class="text-sm font-semibold text-emerald-800">T.02 (BB_J1) — Classe d'excellence</div>
              <div class="text-xs text-emerald-600 mt-0.5">100% réussite · Moyenne 16.24/20 · É.-T. 2.09</div>
            </div>
          </div>
        </div>

        <div class="grid lg:grid-cols-2 gap-6">
          <div class="bg-white rounded-2xl border border-gray-200 overflow-hidden shadow-sm">
            <div class="px-5 py-4 border-b border-indigo-100 bg-indigo-50">
              <h2 class="text-base font-semibold text-indigo-800 flex items-center gap-2">
                <AppIcon name="clipboard-list" :size="15" class="text-indigo-600" />
                BB_J1 — Par classe (106 copies)
              </h2>
            </div>
            <div class="overflow-x-auto">
              <table class="w-full text-sm">
                <thead class="bg-gray-50 border-b border-gray-100">
                  <tr>
                    <th class="px-3 py-2.5 text-left font-medium text-gray-600">Classe</th>
                    <th class="px-3 py-2.5 text-center font-medium text-gray-600">n</th>
                    <th class="px-3 py-2.5 text-center font-medium text-gray-600">Moy.</th>
                    <th class="px-3 py-2.5 text-center font-medium text-gray-600">É.-T.</th>
                    <th class="px-3 py-2.5 text-center font-medium text-gray-600">Réussite</th>
                  </tr>
                </thead>
                <tbody class="divide-y divide-gray-50">
                  <tr v-for="c in CLASSES_J1" :key="c.cls" :class="classRowBg(c.pct)" class="hover:bg-indigo-50/50 transition-colors">
                    <td class="px-3 py-2.5 font-semibold text-gray-800">{{ c.cls }}</td>
                    <td class="px-3 py-2.5 text-center text-gray-600">{{ c.n }}</td>
                    <td class="px-3 py-2.5 text-center"><span :class="meanColor(c.mean)" class="font-bold">{{ c.mean.toFixed(2) }}/20</span></td>
                    <td class="px-3 py-2.5 text-center text-gray-500">{{ c.std.toFixed(2) }}</td>
                    <td class="px-3 py-2.5 text-center"><span :class="pctBadge(c.pct)" class="px-2 py-0.5 rounded-full text-xs font-bold">{{ c.pct }}%</span></td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>

          <div class="bg-white rounded-2xl border border-gray-200 overflow-hidden shadow-sm">
            <div class="px-5 py-4 border-b border-violet-100 bg-violet-50">
              <h2 class="text-base font-semibold text-violet-800 flex items-center gap-2">
                <AppIcon name="clipboard-list" :size="15" class="text-violet-600" />
                BB_J2 — Par classe (103 copies)
              </h2>
            </div>
            <div class="overflow-x-auto">
              <table class="w-full text-sm">
                <thead class="bg-gray-50 border-b border-gray-100">
                  <tr>
                    <th class="px-3 py-2.5 text-left font-medium text-gray-600">Classe</th>
                    <th class="px-3 py-2.5 text-center font-medium text-gray-600">n</th>
                    <th class="px-3 py-2.5 text-center font-medium text-gray-600">Moy.</th>
                    <th class="px-3 py-2.5 text-center font-medium text-gray-600">É.-T.</th>
                    <th class="px-3 py-2.5 text-center font-medium text-gray-600">Réussite</th>
                  </tr>
                </thead>
                <tbody class="divide-y divide-gray-50">
                  <tr v-for="c in CLASSES_J2" :key="c.cls" :class="classRowBg(c.pct)" class="hover:bg-violet-50/50 transition-colors">
                    <td class="px-3 py-2.5 font-semibold text-gray-800">{{ c.cls }}</td>
                    <td class="px-3 py-2.5 text-center text-gray-600">{{ c.n }}</td>
                    <td class="px-3 py-2.5 text-center"><span :class="meanColor(c.mean)" class="font-bold">{{ c.mean.toFixed(2) }}/20</span></td>
                    <td class="px-3 py-2.5 text-center text-gray-500">{{ c.std.toFixed(2) }}</td>
                    <td class="px-3 py-2.5 text-center"><span :class="pctBadge(c.pct)" class="px-2 py-0.5 rounded-full text-xs font-bold">{{ c.pct }}%</span></td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>

        <div class="bg-white rounded-2xl border border-gray-200 overflow-hidden shadow-sm">
          <div class="px-5 py-4 border-b border-gray-100">
            <h2 class="text-base font-semibold text-gray-900 flex items-center gap-2">
              <AppIcon name="users" :size="16" class="text-indigo-500" />
              Groupes de TD — classement global
            </h2>
          </div>
          <div class="overflow-x-auto">
            <table class="w-full text-sm">
              <thead class="bg-gray-50 border-b border-gray-100">
                <tr>
                  <th class="px-4 py-3 text-center font-medium text-gray-600">Rang</th>
                  <th class="px-4 py-3 text-left font-medium text-gray-600">Groupe</th>
                  <th class="px-4 py-3 text-left font-medium text-gray-600">Professeur</th>
                  <th class="px-4 py-3 text-center font-medium text-gray-600">Examen</th>
                  <th class="px-4 py-3 text-center font-medium text-gray-600">n</th>
                  <th class="px-4 py-3 text-center font-medium text-gray-600">Moyenne</th>
                  <th class="px-4 py-3 text-center font-medium text-gray-600">Réussite</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-gray-50">
                <tr v-for="(g, i) in GROUPES_CLASSEMENT" :key="g.groupe"
                  :class="[i < 3 ? 'bg-emerald-50/30' : '', g.alerte ? 'bg-red-50/40' : '']"
                  class="hover:bg-gray-50 transition-colors">
                  <td class="px-4 py-2.5 text-center">
                    <span :class="rankBadge(i+1)" class="w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold mx-auto">{{ i + 1 }}</span>
                  </td>
                  <td class="px-4 py-2.5 font-bold text-gray-800">{{ g.groupe }}</td>
                  <td class="px-4 py-2.5 text-gray-600">{{ g.prof }}</td>
                  <td class="px-4 py-2.5 text-center">
                    <span :class="g.exam === 'BB_J1' ? 'bg-indigo-100 text-indigo-700' : 'bg-violet-100 text-violet-700'" class="px-2 py-0.5 rounded-full text-xs font-medium">{{ g.exam }}</span>
                  </td>
                  <td class="px-4 py-2.5 text-center text-gray-600">{{ g.n }}</td>
                  <td class="px-4 py-2.5 text-center"><span :class="meanColor(g.mean)" class="font-bold">{{ g.mean.toFixed(2) }}/20</span></td>
                  <td class="px-4 py-2.5 text-center"><span :class="pctBadge(g.pct)" class="px-2 py-0.5 rounded-full text-xs font-bold">{{ g.pct }}%</span></td>
                </tr>
              </tbody>
            </table>
          </div>
          <div class="px-5 py-3 bg-amber-50 border-t border-amber-100 text-xs text-amber-700 flex items-center gap-2">
            <AppIcon name="alert-circle" :size="13" class="text-amber-500 shrink-0" />
            <strong>Alerte G5</strong> : Moyenne 9.70/20, réussite 58.3% — Remédiation ciblée recommandée.
          </div>
        </div>
      </div>

      <!-- TAB: Élèves -->
      <div v-if="activeTab === 'eleves'" class="space-y-6">
        <div class="grid lg:grid-cols-2 gap-6">
          <div class="bg-white rounded-2xl border border-gray-200 shadow-sm overflow-hidden">
            <div class="px-5 py-4 border-b border-amber-100 bg-gradient-to-r from-amber-50 to-yellow-50">
              <h2 class="text-base font-semibold text-amber-800 flex items-center gap-2">
                <AppIcon name="medal" :size="16" class="text-amber-600" />
                Félicitations du jury — ≥ 18/20 (24 élèves)
              </h2>
            </div>
            <div class="overflow-x-auto">
              <table class="w-full text-sm">
                <thead class="bg-gray-50 border-b border-gray-100">
                  <tr>
                    <th class="px-3 py-2 text-left font-medium text-gray-600">Élève</th>
                    <th class="px-3 py-2 text-center font-medium text-gray-600">Classe</th>
                    <th class="px-3 py-2 text-center font-medium text-gray-600">Exam</th>
                    <th class="px-3 py-2 text-center font-medium text-gray-600">Note</th>
                  </tr>
                </thead>
                <tbody class="divide-y divide-gray-50">
                  <tr v-for="e in PALMARES_TOP" :key="e.nom" class="hover:bg-amber-50/30">
                    <td class="px-3 py-2 font-medium text-gray-800">{{ e.nom }}</td>
                    <td class="px-3 py-2 text-center text-gray-500">{{ e.classe }}</td>
                    <td class="px-3 py-2 text-center">
                      <span :class="e.exam === 'BB_J1' ? 'bg-indigo-100 text-indigo-700' : 'bg-violet-100 text-violet-700'" class="px-1.5 py-0.5 rounded text-xs font-medium">{{ e.exam }}</span>
                    </td>
                    <td class="px-3 py-2 text-center font-bold text-amber-700">{{ e.note }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>

          <div class="bg-white rounded-2xl border border-gray-200 shadow-sm overflow-hidden">
            <div class="px-5 py-4 border-b border-red-100 bg-red-50">
              <h2 class="text-base font-semibold text-red-800 flex items-center gap-2">
                <AppIcon name="alert-triangle" :size="16" class="text-red-600" />
                Grande difficulté — &lt; 5/20 (11 élèves)
              </h2>
            </div>
            <div class="overflow-x-auto">
              <table class="w-full text-sm">
                <thead class="bg-gray-50 border-b border-gray-100">
                  <tr>
                    <th class="px-3 py-2 text-left font-medium text-gray-600">Élève</th>
                    <th class="px-3 py-2 text-center font-medium text-gray-600">Classe</th>
                    <th class="px-3 py-2 text-center font-medium text-gray-600">Groupe</th>
                    <th class="px-3 py-2 text-center font-medium text-gray-600">Note</th>
                  </tr>
                </thead>
                <tbody class="divide-y divide-gray-50">
                  <tr v-for="e in DIFFICULTE" :key="e.nom" class="hover:bg-red-50/30">
                    <td class="px-3 py-2 font-medium text-gray-800">{{ e.nom }}<span v-if="e.alerte" class="ml-1 text-xs text-red-500">⚠</span></td>
                    <td class="px-3 py-2 text-center text-gray-500">{{ e.classe }}</td>
                    <td class="px-3 py-2 text-center text-gray-500">{{ e.groupe }}</td>
                    <td class="px-3 py-2 text-center font-bold text-red-700">{{ e.note }}/20</td>
                  </tr>
                </tbody>
              </table>
            </div>
            <div class="px-4 py-2.5 bg-red-50 border-t border-red-100 text-xs text-red-600">8/11 élèves sous 5 sont en BB_J2. 4 élèves du groupe G5.</div>
          </div>
        </div>

        <div class="bg-amber-50 border border-amber-200 rounded-2xl p-5">
          <h2 class="text-base font-semibold text-amber-800 mb-3 flex items-center gap-2">
            <AppIcon name="zap" :size="16" class="text-amber-600" />
            Investigation QCM — Exercice 1
          </h2>
          <div class="grid sm:grid-cols-3 gap-4 text-sm">
            <div class="bg-white rounded-xl p-4 border border-amber-100">
              <div class="text-2xl font-bold text-amber-700">54</div>
              <div class="text-xs text-amber-600 mt-0.5">élèves BB_J1 avec 5/5 au QCM (50.9%)</div>
              <div class="text-xs text-gray-400 mt-1">QCM très peu discriminant en J1</div>
            </div>
            <div class="bg-white rounded-xl p-4 border border-amber-100">
              <div class="text-2xl font-bold text-violet-700">16</div>
              <div class="text-xs text-violet-600 mt-0.5">élèves BB_J2 avec 5/5 au QCM (15.5%)</div>
              <div class="text-xs text-gray-400 mt-1">QCM nettement plus discriminant en J2</div>
            </div>
            <div class="bg-white rounded-xl p-4 border border-red-100">
              <div class="text-2xl font-bold text-red-700">6</div>
              <div class="text-xs text-red-600 mt-0.5">élèves 5/5 QCM mais note &lt; 10</div>
              <div class="text-xs text-gray-400 mt-1">QCM = 50-80% de leur note totale</div>
            </div>
          </div>
        </div>
      </div>

      <!-- TAB: Recommandations -->
      <div v-if="activeTab === 'recommandations'" class="space-y-6">
        <div class="grid lg:grid-cols-3 gap-6">
          <div class="bg-white rounded-2xl border border-red-200 shadow-sm overflow-hidden">
            <div class="bg-gradient-to-br from-red-500 to-red-600 px-5 py-4 text-white">
              <div class="flex items-center gap-3">
                <div class="w-10 h-10 bg-white/20 rounded-xl flex items-center justify-center"><AppIcon name="zap" :size="18" class="text-white" /></div>
                <div>
                  <div class="text-xs font-medium text-red-200 uppercase tracking-wide">Actions</div>
                  <div class="text-base font-bold">Court terme</div>
                </div>
              </div>
            </div>
            <div class="p-5">
              <ul class="space-y-3">
                <li v-for="(action, i) in RECO.court_terme" :key="i" class="flex items-start gap-2.5 text-sm text-gray-700">
                  <span class="w-5 h-5 bg-red-100 text-red-700 rounded-full flex items-center justify-center text-xs font-bold shrink-0 mt-0.5">{{ i + 1 }}</span>
                  {{ action }}
                </li>
              </ul>
            </div>
          </div>
          <div class="bg-white rounded-2xl border border-amber-200 shadow-sm overflow-hidden">
            <div class="bg-gradient-to-br from-amber-500 to-orange-500 px-5 py-4 text-white">
              <div class="flex items-center gap-3">
                <div class="w-10 h-10 bg-white/20 rounded-xl flex items-center justify-center"><AppIcon name="calendar" :size="18" class="text-white" /></div>
                <div>
                  <div class="text-xs font-medium text-amber-200 uppercase tracking-wide">Actions</div>
                  <div class="text-base font-bold">Moyen terme</div>
                </div>
              </div>
            </div>
            <div class="p-5">
              <ul class="space-y-3">
                <li v-for="(action, i) in RECO.moyen_terme" :key="i" class="flex items-start gap-2.5 text-sm text-gray-700">
                  <span class="w-5 h-5 bg-amber-100 text-amber-700 rounded-full flex items-center justify-center text-xs font-bold shrink-0 mt-0.5">{{ i + 1 }}</span>
                  {{ action }}
                </li>
              </ul>
            </div>
          </div>
          <div class="bg-white rounded-2xl border border-indigo-200 shadow-sm overflow-hidden">
            <div class="bg-gradient-to-br from-indigo-500 to-violet-600 px-5 py-4 text-white">
              <div class="flex items-center gap-3">
                <div class="w-10 h-10 bg-white/20 rounded-xl flex items-center justify-center"><AppIcon name="settings" :size="18" class="text-white" /></div>
                <div>
                  <div class="text-xs font-medium text-indigo-200 uppercase tracking-wide">Processus</div>
                  <div class="text-base font-bold">Korrigo</div>
                </div>
              </div>
            </div>
            <div class="p-5">
              <ul class="space-y-3">
                <li v-for="(action, i) in RECO.processus" :key="i" class="flex items-start gap-2.5 text-sm text-gray-700">
                  <span class="w-5 h-5 bg-indigo-100 text-indigo-700 rounded-full flex items-center justify-center text-xs font-bold shrink-0 mt-0.5">{{ i + 1 }}</span>
                  {{ action }}
                </li>
              </ul>
            </div>
          </div>
        </div>

        <div class="bg-white rounded-2xl border border-gray-200 p-5 shadow-sm">
          <h2 class="text-base font-semibold text-gray-900 mb-4 flex items-center gap-2">
            <AppIcon name="lightbulb" :size="16" class="text-amber-500" />
            Constats principaux du jury
          </h2>
          <div class="grid sm:grid-cols-2 gap-3">
            <div v-for="(constat, i) in CONSTATS" :key="i"
              :class="constat.ok ? 'bg-emerald-50 border-emerald-200' : 'bg-red-50 border-red-200'"
              class="rounded-xl p-3 border flex items-start gap-2.5 text-sm">
              <AppIcon :name="constat.ok ? 'check-circle' : 'x-circle'" :size="15" :class="constat.ok ? 'text-emerald-500' : 'text-red-500'" class="shrink-0 mt-0.5" />
              <span :class="constat.ok ? 'text-emerald-800' : 'text-red-800'">{{ constat.text }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- TAB: Correcteurs (Admin seulement) -->
      <div v-if="activeTab === 'correcteurs'" class="space-y-6">
        <div class="flex items-center gap-3 bg-slate-800 text-white px-5 py-3 rounded-2xl">
          <AppIcon name="shield" :size="18" class="text-slate-300" />
          <div>
            <span class="font-semibold text-sm">Section confidentielle</span>
            <span class="text-slate-400 text-xs ml-2">Réservée à l'administration</span>
          </div>
        </div>

        <div class="bg-white rounded-2xl border border-gray-200 shadow-sm overflow-hidden">
          <div class="px-5 py-4 border-b border-gray-100">
            <h2 class="text-base font-semibold text-gray-900 flex items-center gap-2">
              <AppIcon name="users" :size="16" class="text-indigo-500" />
              Analyse inter-correcteurs
            </h2>
            <p class="text-xs text-gray-400 mt-0.5">Les écarts dépendent du lot assigné, pas uniquement de la sévérité.</p>
          </div>
          <div class="overflow-x-auto">
            <table class="w-full text-sm">
              <thead class="bg-gray-50 border-b border-gray-100">
                <tr>
                  <th class="px-4 py-3 text-left font-medium text-gray-600">Correcteur</th>
                  <th class="px-4 py-3 text-center font-medium text-gray-600">Examen</th>
                  <th class="px-4 py-3 text-center font-medium text-gray-600">Copies</th>
                  <th class="px-4 py-3 text-center font-medium text-gray-600">Moyenne</th>
                  <th class="px-4 py-3 text-center font-medium text-gray-600">É.-T.</th>
                  <th class="px-4 py-3 text-center font-medium text-gray-600">Réussite</th>
                  <th class="px-4 py-3 text-center font-medium text-gray-600">Profil</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-gray-50">
                <tr v-for="c in CORRECTEURS" :key="c.name" class="hover:bg-gray-50 transition-colors">
                  <td class="px-4 py-3 font-semibold text-gray-800">{{ c.name }}</td>
                  <td class="px-4 py-3 text-center">
                    <span :class="c.exam === 'BB_J1' ? 'bg-indigo-100 text-indigo-700' : 'bg-violet-100 text-violet-700'" class="px-2 py-0.5 rounded-full text-xs font-medium">{{ c.exam }}</span>
                  </td>
                  <td class="px-4 py-3 text-center text-gray-600">{{ c.n }}</td>
                  <td class="px-4 py-3 text-center font-bold" :class="meanColor(c.mean)">{{ c.mean.toFixed(2) }}/20</td>
                  <td class="px-4 py-3 text-center text-gray-500">{{ c.std.toFixed(2) }}</td>
                  <td class="px-4 py-3 text-center"><span :class="pctBadge(c.pct)" class="px-2 py-0.5 rounded-full text-xs font-bold">{{ c.pct }}%</span></td>
                  <td class="px-4 py-3 text-center"><span :class="profilBadge(c.severity)" class="px-2 py-0.5 rounded-full text-xs font-semibold">{{ c.severity }}</span></td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <div class="bg-white rounded-2xl border border-gray-200 p-5 shadow-sm">
          <h2 class="text-base font-semibold text-gray-900 mb-5 flex items-center gap-2">
            <AppIcon name="bar-chart-2" :size="16" class="text-indigo-500" />
            Comparaison des moyennes par correcteur
          </h2>
          <div class="space-y-3">
            <div v-for="c in CORRECTEURS" :key="c.name + '-bar'" class="flex items-center gap-3">
              <div class="w-44 text-xs text-gray-600 truncate shrink-0">{{ c.name }}</div>
              <div class="flex-1 bg-gray-100 rounded-full h-6 overflow-hidden relative">
                <div :class="c.exam === 'BB_J1' ? 'bg-indigo-400' : 'bg-violet-400'"
                  class="h-6 rounded-full flex items-center justify-end pr-2 transition-all duration-700"
                  :style="{ width: `${(c.mean / 20) * 100}%` }">
                  <span class="text-white text-xs font-bold">{{ c.mean.toFixed(2) }}</span>
                </div>
              </div>
              <div class="text-xs text-gray-400 shrink-0 w-12 text-right">{{ c.pct }}%</div>
            </div>
          </div>
        </div>
      </div>

    </div>

    <div class="max-w-7xl mx-auto px-4 sm:px-6 pb-8">
      <div class="bg-gray-100 rounded-2xl px-5 py-4 text-xs text-gray-500 flex items-center gap-3">
        <AppIcon name="database" :size="14" class="text-gray-400 shrink-0" />
        <span>Source : Plateforme Korrigo · Extraction directe base de données production · 4 mars 2026</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useAuthStore } from '../stores/auth'
import AppIcon from '../icons/AppIcon.vue'

const authStore = useAuthStore()
const isAdmin = computed(() => authStore.user?.role === 'Admin' || authStore.user?.is_superuser)

const HISTOGRAM = [
  { range: '[0;2[',   count: 2,  j1: 1,  j2: 1  },
  { range: '[2;4[',   count: 5,  j1: 0,  j2: 5  },
  { range: '[4;6[',   count: 8,  j1: 4,  j2: 4  },
  { range: '[6;8[',   count: 14, j1: 9,  j2: 5  },
  { range: '[8;10[',  count: 18, j1: 9,  j2: 9  },
  { range: '[10;12[', count: 22, j1: 9,  j2: 13 },
  { range: '[12;14[', count: 31, j1: 12, j2: 19 },
  { range: '[14;16[', count: 42, j1: 23, j2: 19 },
  { range: '[16;18[', count: 35, j1: 19, j2: 16 },
  { range: '[18;20]', count: 32, j1: 20, j2: 12 },
]

const MENTIONS = [
  { label: 'Très Bien (≥16)',    key: 'tb', global: 67, pct_g: 32.1, j1: 39, j2: 28, colorJ1: 'bg-emerald-500', colorJ2: 'bg-emerald-400', pctClass: 'text-emerald-700' },
  { label: 'Bien [14;16[',       key: 'b',  global: 42, pct_g: 20.1, j1: 23, j2: 19, colorJ1: 'bg-lime-500',    colorJ2: 'bg-lime-400',    pctClass: 'text-lime-700'    },
  { label: 'Assez Bien [12;14[', key: 'ab', global: 31, pct_g: 14.8, j1: 12, j2: 19, colorJ1: 'bg-yellow-400',  colorJ2: 'bg-yellow-300',  pctClass: 'text-yellow-700'  },
  { label: 'Passable [10;12[',   key: 'p',  global: 22, pct_g: 10.5, j1:  9, j2: 13, colorJ1: 'bg-orange-400',  colorJ2: 'bg-orange-300',  pctClass: 'text-orange-700'  },
  { label: 'Insuffisant (<10)',  key: 'i',  global: 47, pct_g: 22.5, j1: 23, j2: 24, colorJ1: 'bg-red-500',     colorJ2: 'bg-red-400',     pctClass: 'text-red-700'     },
]

const CORRECTEURS = [
  { name: 'Alaeddine BEN RHOUMA', exam: 'BB_J1', n: 26, mean: 14.84, std: 3.60, pct: 92.3, severity: 'calibré'   },
  { name: 'Selima KLIBI',         exam: 'BB_J1', n: 27, mean: 13.84, std: 4.42, pct: 81.5, severity: 'calibré'   },
  { name: 'Patrick DUPONT',       exam: 'BB_J1', n: 26, mean: 13.34, std: 4.50, pct: 69.2, severity: 'calibré'   },
  { name: 'Philippe CARR',        exam: 'BB_J1', n: 27, mean: 13.17, std: 4.35, pct: 70.4, severity: 'calibré'   },
  { name: 'Chawki SAADI',         exam: 'BB_J2', n: 25, mean: 13.47, std: 4.17, pct: 80.0, severity: 'calibré'   },
  { name: 'Edouard ROUSSEAU',     exam: 'BB_J2', n: 26, mean: 12.80, std: 5.04, pct: 76.9, severity: 'indulgent' },
  { name: 'Sami BEN TIBA',        exam: 'BB_J2', n: 26, mean: 12.69, std: 4.74, pct: 73.1, severity: 'calibré'   },
  { name: 'Laroussi LAROUSSI',    exam: 'BB_J2', n: 26, mean: 11.80, std: 3.70, pct: 76.9, severity: 'sévère'    },
]

const CLASSES_J1 = [
  { cls: 'T.02', n: 17, mean: 16.24, std: 2.09, pct: 100.0 },
  { cls: 'T.06', n: 25, mean: 14.51, std: 3.69, pct: 92.0  },
  { cls: 'T.07', n: 14, mean: 14.19, std: 5.68, pct: 71.4  },
  { cls: 'T.08', n: 11, mean: 14.12, std: 4.18, pct: 81.8  },
  { cls: 'T.03', n:  5, mean: 13.42, std: 4.76, pct: 80.0  },
  { cls: 'T.09', n:  8, mean: 12.24, std: 4.03, pct: 75.0  },
  { cls: 'T.05', n:  6, mean: 12.03, std: 3.75, pct: 66.7  },
  { cls: 'T.10', n:  4, mean: 11.76, std: 2.60, pct: 75.0  },
  { cls: 'T.01', n: 16, mean: 11.56, std: 4.20, pct: 43.8  },
]

const CLASSES_J2 = [
  { cls: 'T.04', n: 27, mean: 14.39, std: 3.59, pct: 88.9 },
  { cls: 'T.01', n:  5, mean: 14.30, std: 3.96, pct: 80.0 },
  { cls: 'T.10', n: 16, mean: 13.03, std: 3.76, pct: 81.2 },
  { cls: 'T.03', n: 19, mean: 12.36, std: 5.32, pct: 73.7 },
  { cls: 'T.09', n: 12, mean: 11.29, std: 4.66, pct: 66.7 },
  { cls: 'T.05', n: 13, mean: 11.25, std: 4.32, pct: 69.2 },
  { cls: 'T.07', n:  6, mean: 11.08, std: 2.90, pct: 66.7 },
  { cls: 'T.08', n:  3, mean: 11.00, std: 6.75, pct: 66.7 },
  { cls: 'T.02', n:  2, mean: 10.88, std: 2.62, pct: 50.0 },
]

const GROUPES_CLASSEMENT = [
  { groupe: 'G2',   prof: 'Patrick DUPONT',      exam: 'BB_J1', n: 26, mean: 15.38, pct: 92.3, alerte: false },
  { groupe: 'T.06', prof: 'Selima KLIBI',         exam: 'BB_J1', n: 25, mean: 14.51, pct: 92.0, alerte: false },
  { groupe: 'T.04', prof: 'Edouard ROUSSEAU',     exam: 'BB_J2', n: 27, mean: 14.39, pct: 88.9, alerte: false },
  { groupe: 'G6',   prof: 'Sami BEN TIBA',        exam: 'BB_J2', n: 25, mean: 13.53, pct: 84.0, alerte: false },
  { groupe: 'G1',   prof: 'Philippe CARR',        exam: 'BB_J1', n: 27, mean: 12.90, pct: 70.4, alerte: false },
  { groupe: 'G4',   prof: 'Chawki SAADI',         exam: 'BB_J2', n: 27, mean: 12.84, pct: 74.1, alerte: false },
  { groupe: 'G3',   prof: 'Alaeddine BEN RHOUMA', exam: 'BB_J1', n: 28, mean: 12.54, pct: 60.7, alerte: false },
  { groupe: 'G5',   prof: 'Laroussi LAROUSSI',    exam: 'BB_J2', n: 24, mean:  9.70, pct: 58.3, alerte: true  },
]

const PALMARES_TOP = [
  { nom: 'HACHICH Selim',       classe: 'T.01', exam: 'BB_J1', note: 20.00 },
  { nom: 'BEN REGUIGA Nour',    classe: 'T.04', exam: 'BB_J2', note: 20.00 },
  { nom: 'BEN RAYANA Mohamed',  classe: 'T.07', exam: 'BB_J1', note: 19.95 },
  { nom: 'DRISS Yacine',        classe: 'T.02', exam: 'BB_J1', note: 19.95 },
  { nom: 'DOGGAZ Enis',         classe: 'T.09', exam: 'BB_J2', note: 19.75 },
  { nom: 'BEN BRAHIM Jawad',    classe: 'T.08', exam: 'BB_J1', note: 19.50 },
  { nom: 'ISSA Mourad',         classe: 'T.06', exam: 'BB_J1', note: 19.50 },
  { nom: 'BLOUZA Emna',         classe: 'T.04', exam: 'BB_J2', note: 19.50 },
  { nom: 'AMARA Fares',         classe: 'T.06', exam: 'BB_J1', note: 19.45 },
  { nom: 'AMMAR Amal',          classe: 'T.04', exam: 'BB_J2', note: 19.00 },
  { nom: 'BENNANI Lilya',       classe: 'T.05', exam: 'BB_J2', note: 19.00 },
  { nom: 'AMEUR Selim',         classe: 'T.02', exam: 'BB_J1', note: 18.95 },
  { nom: 'BELCADHI Yoldez',     classe: 'T.02', exam: 'BB_J1', note: 18.95 },
  { nom: 'BOUKER Fares',        classe: 'T.07', exam: 'BB_J1', note: 18.95 },
  { nom: 'SFIA Iyad Alex',      classe: 'T.06', exam: 'BB_J1', note: 18.90 },
  { nom: 'JOMAA Emine',         classe: 'T.06', exam: 'BB_J1', note: 18.80 },
  { nom: 'ZAIER Khalil',        classe: 'T.01', exam: 'BB_J2', note: 18.75 },
  { nom: 'AKROUT Mehdi',        classe: 'T.04', exam: 'BB_J2', note: 18.25 },
  { nom: 'BEN AYED Salma',      classe: 'T.07', exam: 'BB_J1', note: 18.10 },
  { nom: 'MEHERZI Ines',        classe: 'T.07', exam: 'BB_J1', note: 18.05 },
]

const DIFFICULTE = [
  { nom: 'SNOUSSI Yasmine',           classe: 'T.03', groupe: 'G5', note: 1.00  },
  { nom: 'SATOURI Adem',              classe: 'T.07', groupe: 'G1', note: 1.45, alerte: true },
  { nom: 'CHANNOUFI Mohamed Yassine', classe: 'T.08', groupe: 'G5', note: 2.00  },
  { nom: 'MEZIOU Ines Celia',         classe: 'T.03', groupe: 'G4', note: 2.25  },
  { nom: 'BEN MEZIANE Maya',          classe: 'T.09', groupe: 'G5', note: 2.50  },
  { nom: 'IDANI Mariem',              classe: 'T.05', groupe: 'G5', note: 2.75  },
  { nom: 'DEKHIL Mohamed Selim',      classe: 'T.03', groupe: 'G5', note: 3.25  },
  { nom: 'EBEYE Yahya',               classe: 'T.09', groupe: 'G4', note: 4.25  },
  { nom: 'JARRAYA Abdelhamid',        classe: 'T.10', groupe: 'G6', note: 4.50  },
  { nom: 'MAATOUG Safa',              classe: 'T.08', groupe: 'G3', note: 4.50  },
  { nom: 'BOUGHABA Sirine',           classe: 'T.03', groupe: 'G1', note: 4.60  },
]

const RECO = {
  court_terme: [
    'Remédiation ciblée pour le groupe G5 (moy. 9.70/20) et la classe T.01 (réussite 43.8%)',
    'Entretiens individuels pour les 11 élèves sous 5/20',
    'Révision des méthodes de calcul de limites et études de signe',
    'Travail collectif sur la rédaction et la justification',
  ],
  moyen_terme: [
    "Enquête sur le biais Sujet A/B (~1.5 pts d'écart) — harmonisation si confirmé",
    'Suivi de la suspicion de fraude QCM signalée (1 cas)',
    'Partage de bonnes pratiques entre G2/T.06 (meilleurs) et G5/G3 (en difficulté)',
    'Bac blanc supplémentaire ciblé pour les groupes G5 et G3',
  ],
  processus: [
    'Finaliser les 182 copies en statut READY (passage GRADED)',
    'Générer les bilans LLM pour les 167 copies manquantes',
    'Déployer les résultats sur le portail élève Korrigo',
  ],
}

const CONSTATS = [
  { ok: true,  text: 'Taux de réussite global satisfaisant : 77.5% (162/209 ≥ 10/20)' },
  { ok: false, text: 'Disparité entre groupes : de 92.3% (G2) à 58.3% (G5) de réussite' },
  { ok: true,  text: 'Classe T.02 exceptionnelle : 100% de réussite, moyenne 16.24/20' },
  { ok: false, text: 'Classe T.01 en difficulté (BB_J1) : seulement 43.8% de réussite' },
  { ok: false, text: 'Écart Sujet A/B systématique : ~1.5 pts en faveur du Sujet B' },
  { ok: true,  text: 'Correction de qualité : 19.4 remarques/copie, 100% avec appréciation' },
  { ok: false, text: 'Questions Q2.2.4, Q3.7, Q4.2.6-7 très peu réussies' },
  { ok: false, text: '11 élèves sous 5/20 — suivi individualisé urgent requis' },
]

const kpis = [
  { label: 'Candidats',        value: '209',   unit: '',    sub: 'J1 : 106 · J2 : 103' },
  { label: 'Moyenne globale',  value: '13.25', unit: '/20', sub: 'J1 : 13.79 · J2 : 12.68' },
  { label: 'Taux de réussite', value: '77.5',  unit: '%',   sub: '162 / 209 ≥ 10/20' },
  { label: 'Très bien (≥16)',  value: '32.1',  unit: '%',   sub: '67 élèves · Médiane : 14.00/20' },
]

const signals = [
  { key: 'difficulte', icon: 'alert-triangle', title: '47 élèves insuffisants', message: '22.5% sous 10/20 · Groupe G5 en alerte (58.3% réussite)', bg: 'bg-red-50 border-red-200', iconBg: 'bg-red-100', iconColor: 'text-red-600', titleColor: 'text-red-800', textColor: 'text-red-700' },
  { key: 'excellence', icon: 'star',            title: '32.1% Très Bien',        message: 'T.02 à 100% réussite · 24 félicitations du jury (≥18/20)', bg: 'bg-emerald-50 border-emerald-200', iconBg: 'bg-emerald-100', iconColor: 'text-emerald-600', titleColor: 'text-emerald-800', textColor: 'text-emerald-700' },
  { key: 'qualite',    icon: 'check-circle',    title: 'Correction de qualité',  message: '4 054 remarques · 100% des copies avec appréciation', bg: 'bg-blue-50 border-blue-200', iconBg: 'bg-blue-100', iconColor: 'text-blue-600', titleColor: 'text-blue-800', textColor: 'text-blue-700' },
]

const descStats = [
  { label: 'Moyenne (/20)',    j1: '13.79', j2: '12.68', global: '13.25' },
  { label: 'Médiane (/20)',    j1: '14.48', j2: '13.25', global: '14.00' },
  { label: 'Écart-type',       j1: '4.29',  j2: '4.48',  global: '4.42'  },
  { label: 'Minimum (/20)',    j1: '1.45',  j2: '1.00',  global: '1.00'  },
  { label: 'Maximum (/20)',    j1: '20.00', j2: '20.00', global: '20.00' },
  { label: 'Q1 (25%)',         j1: '10.90', j2: '10.25', global: '10.75' },
  { label: 'Q3 (75%)',         j1: '17.60', j2: '16.00', global: '16.70' },
  { label: 'Taux réussite',    j1: '78.3%', j2: '76.7%', global: '77.5%' },
]

const qualiteMetrics = [
  { label: 'Remarques péda.', value: '4 054', sub: '19.4 / copie',    bg: 'bg-indigo-50 border-indigo-100', valueColor: 'text-indigo-700' },
  { label: 'Copies annotées', value: '88%',   sub: '184 / 209',        bg: 'bg-blue-50 border-blue-100',    valueColor: 'text-blue-700'   },
  { label: 'Annot. graphiq.',  value: '706',   sub: '39.7% des copies', bg: 'bg-violet-50 border-violet-100', valueColor: 'text-violet-700' },
  { label: 'Avec appréciat.', value: '100%',  sub: '209 / 209',        bg: 'bg-emerald-50 border-emerald-100', valueColor: 'text-emerald-700' },
]

const comparaisons = [
  { label: 'Moyenne',            j1: '13.79/20', j2: '12.68/20' },
  { label: 'Médiane',            j1: '14.48/20', j2: '13.25/20' },
  { label: 'Taux réussite',      j1: '78.3%',    j2: '76.7%'    },
  { label: 'Très bien (≥16)',    j1: '36.8%',    j2: '27.2%'    },
  { label: 'Insuffisant (<10)',  j1: '21.7%',    j2: '23.3%'    },
]

const HIST_COLORS_HEX = ['#ef4444','#ef4444','#f97316','#fb923c','#facc15','#a3e635','#4ade80','#22c55e','#10b981','#059669']
const barColorHex = (i) => HIST_COLORS_HEX[i] || '#94a3b8'

const meanColor  = (m) => m >= 15 ? 'text-emerald-700' : m >= 12 ? 'text-green-600' : m >= 10 ? 'text-orange-600' : 'text-red-600'
const pctBadge   = (p) => p >= 85 ? 'bg-emerald-100 text-emerald-800' : p >= 70 ? 'bg-green-100 text-green-800' : p >= 60 ? 'bg-yellow-100 text-yellow-800' : 'bg-red-100 text-red-800'
const classRowBg = (p) => p >= 90 ? 'bg-emerald-50/40' : p < 50 ? 'bg-red-50/40' : ''
const rankBadge  = (r) => r === 1 ? 'bg-amber-400 text-white' : r === 2 ? 'bg-slate-300 text-slate-800' : r === 3 ? 'bg-amber-600/80 text-white' : 'bg-gray-100 text-gray-600'
const profilBadge = (s) => s === 'calibré' ? 'bg-emerald-100 text-emerald-800' : s === 'sévère' ? 'bg-blue-100 text-blue-800' : 'bg-orange-100 text-orange-800'

const ALL_TABS = [
  { id: 'overview',         label: "Vue d'ensemble",  icon: 'layout-dashboard' },
  { id: 'distribution',    label: 'Distribution',     icon: 'bar-chart'        },
  { id: 'classes',         label: 'Classes & TD',     icon: 'grid'             },
  { id: 'eleves',          label: 'Élèves',           icon: 'users'            },
  { id: 'recommandations', label: 'Recommandations',  icon: 'lightbulb'        },
  { id: 'correcteurs',     label: 'Correcteurs',      icon: 'shield', adminOnly: true },
]

const visibleTabs = computed(() => ALL_TABS.filter(t => !t.adminOnly || isAdmin.value))
const activeTab = ref('overview')
const printPage = () => window.print()
</script>
