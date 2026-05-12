<template>
  <div class="p-4 md:p-6 max-w-6xl mx-auto">
    <!-- Navigation -->
    <div class="mb-4">
      <button @click="$router.go(-1)" class="inline-flex items-center gap-2 text-gray-500 hover:text-indigo-700 transition-colors text-sm font-medium">
        <AppIcon name="arrow-left" :size="14" />
        Retour
      </button>
    </div>

    <!-- Bannière officielle -->
    <div class="bg-gradient-to-br from-indigo-950 via-indigo-800 to-indigo-700 rounded-2xl p-6 md:p-8 mb-8 shadow-xl text-white">
      <div class="flex flex-col md:flex-row md:items-start justify-between gap-3 mb-6">
        <div>
          <p class="text-indigo-300 text-xs font-semibold uppercase tracking-widest mb-2">Épreuve Anticipée de Mathématiques · Première Générale</p>
          <h1 class="text-2xl md:text-3xl font-bold leading-tight">Bilan de correction — EAM Blanche 2026</h1>
          <p class="text-indigo-200 text-sm mt-2">
            {{ meta?.etablissement || 'Analyse Korrigo' }} · Produit le {{ formatDate(report?.generated_at) }}
          </p>
        </div>
        <span :class="getStatusClass(report?.status)" class="px-4 py-1.5 text-sm font-semibold rounded-full whitespace-nowrap self-start">
          {{ getStatusText(report?.status) }}
        </span>
      </div>
      <div class="grid grid-cols-2 md:grid-cols-4 gap-3 pt-5 border-t border-indigo-600/60">
        <div class="bg-white/10 backdrop-blur rounded-xl p-3 text-center">
          <div class="text-2xl font-bold">{{ meta?.n_copies ?? '—' }}</div>
          <div class="text-indigo-200 text-xs mt-0.5">copies analysées</div>
        </div>
        <div class="bg-white/10 backdrop-blur rounded-xl p-3 text-center">
          <div class="text-2xl font-bold">{{ meta?.mean?.toFixed(1) ?? '—' }}<span class="text-base text-indigo-300">/20</span></div>
          <div class="text-indigo-200 text-xs mt-0.5">moyenne générale</div>
        </div>
        <div class="bg-white/10 backdrop-blur rounded-xl p-3 text-center">
          <div class="text-2xl font-bold">{{ meta?.pct_above_10?.toFixed(0) ?? '—' }}<span class="text-base text-indigo-300">%</span></div>
          <div class="text-indigo-200 text-xs mt-0.5">taux ≥ 10/20</div>
        </div>
        <div class="bg-white/10 backdrop-blur rounded-xl p-3 text-center">
          <div class="text-lg font-bold">8 juin 2026</div>
          <div class="text-indigo-200 text-xs mt-0.5">épreuve officielle</div>
        </div>
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
      <section class="bg-white border border-gray-200 rounded-xl p-6 md:p-8 shadow-sm">
        <h2 class="text-lg font-bold text-indigo-900 mb-5 flex items-center gap-2 uppercase tracking-wide">
          <span class="w-1 h-5 bg-indigo-600 rounded-full inline-block"></span>
          Synthèse exécutive
        </h2>
        <!-- Paragraphe introductif -->
        <div v-if="s0Parsed.intro" class="border-l-4 border-indigo-400 pl-5 py-1 mb-6 bg-indigo-50/50 rounded-r-lg">
          <p class="text-gray-800 leading-relaxed">{{ s0Parsed.intro }}</p>
        </div>
        <!-- Leviers prioritaires -->
        <div v-if="s0Parsed.levers.length">
          <h3 class="text-xs font-bold text-gray-400 uppercase tracking-widest mb-3">Leviers prioritaires</h3>
          <div class="space-y-3">
            <div v-for="(lev, i) in s0Parsed.levers" :key="i"
              class="flex gap-4 items-start bg-gradient-to-r from-indigo-50 to-white border border-indigo-100 rounded-xl p-4 hover:border-indigo-300 transition-colors">
              <span class="flex-shrink-0 w-8 h-8 rounded-full bg-indigo-600 text-white text-sm font-bold flex items-center justify-center shadow">{{ i + 1 }}</span>
              <p class="text-sm text-gray-700 leading-relaxed pt-1">{{ lev }}</p>
            </div>
          </div>
        </div>
        <div v-else-if="s0?.content" class="text-gray-700 leading-relaxed whitespace-pre-line">{{ cleanContent(s0.content) }}</div>
      </section>

      <!-- ── S1 : Tableau de bord ── -->
      <section class="bg-white border border-gray-200 rounded-xl p-6 shadow-sm">
        <h2 class="text-lg font-bold text-indigo-900 mb-6 flex items-center gap-2 uppercase tracking-wide">
          <span class="w-1 h-5 bg-indigo-600 rounded-full inline-block"></span>
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
            <div class="bg-gray-50 rounded-lg p-4 space-y-2.5 max-h-52 overflow-y-auto">
              <div v-for="cls in s1.stats_by_class" :key="cls.class_name" class="pb-2 border-b border-gray-100 last:border-0">
                <div class="flex justify-between items-center mb-1">
                  <span class="text-sm font-semibold text-gray-800">{{ cls.class_name }}</span>
                  <span :class="getMeanTextClass(cls.mean)" class="text-sm">{{ cls.mean?.toFixed(1) }}/20</span>
                  <span class="text-xs text-gray-400">{{ cls.n_students }} élèves</span>
                </div>
                <div class="w-full bg-gray-200 rounded-full h-2">
                  <div class="h-2 rounded-full transition-all" :class="getMeanBarClass(cls.mean)" :style="{ width: (cls.mean / 20 * 100) + '%' }"></div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <!-- ── S2A : Automatismes ── -->
      <section class="bg-white border border-gray-200 rounded-xl p-6 shadow-sm">
        <h2 class="text-lg font-bold text-indigo-900 mb-4 flex items-center gap-2 uppercase tracking-wide">
          <span class="w-1 h-5 bg-indigo-600 rounded-full inline-block"></span>
          Partie A — Automatismes
          <span class="text-xs font-normal text-indigo-400 normal-case tracking-normal">12 questions QCM · 6 pts</span>
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
              <tr v-for="q in s2a?.questions" :key="q.question?.id"
                :class="q.success_rate < 35 ? 'bg-red-50 hover:bg-red-100' : q.success_rate < 50 ? 'bg-amber-50/60 hover:bg-amber-100/50' : 'hover:bg-gray-50'">
                <td class="px-4 py-2 text-gray-900">{{ q.question?.label }}</td>
                <td class="px-4 py-2 text-right text-gray-600">{{ q.question?.max_points }}</td>
                <td class="px-4 py-2 text-right font-medium text-gray-600">{{ q.mean != null ? q.mean.toFixed(2) : '—' }}</td>
                <td class="px-4 py-2 text-right" :class="getRateClass(q.success_rate)">
                  {{ q.success_rate?.toFixed(1) }}%
                </td>
                <td class="px-4 py-2 text-right text-gray-500">{{ q.n_attempts }}</td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- Analyse pédagogique : sous-sections parsées -->
        <div v-if="s2a?.content" class="mt-6 space-y-3">
          <template v-for="(sec, i) in parseAnalysis(s2a.content)" :key="i">
            <div :class="`border rounded-xl p-4 ${subStyle(sec.heading).wrap}`">
              <div v-if="sec.heading" class="flex items-center gap-2 mb-2">
                <span class="w-2.5 h-2.5 rounded-full flex-shrink-0" :class="subStyle(sec.heading).dot"></span>
                <p :class="`text-xs font-bold uppercase tracking-wide ${subStyle(sec.heading).title}`">{{ sec.heading }}</p>
              </div>
              <p class="text-sm text-gray-700 leading-relaxed whitespace-pre-line">{{ sec.body }}</p>
            </div>
          </template>
        </div>
      </section>

      <!-- ── S5 : Table de correspondance Questions → Programme BO ── -->
      <section v-if="s5?.items?.length" class="bg-white border border-gray-200 rounded-xl p-6 shadow-sm">
        <h2 class="text-lg font-bold text-gray-700 mb-4 flex items-center gap-2 uppercase tracking-wide">
          <span class="w-1 h-5 bg-gray-400 rounded-full inline-block"></span>
          Correspondance Questions → Programme officiel (BO)
        </h2>
        <div class="overflow-x-auto">
          <table class="min-w-full text-xs">
            <thead class="bg-gray-100">
              <tr>
                <th class="px-3 py-2 text-left text-gray-700 font-medium">Question</th>
                <th class="px-3 py-2 text-left text-gray-700 font-medium">Capacité BO</th>
                <th class="px-3 py-2 text-left text-gray-700 font-medium">Notion</th>
                <th class="px-3 py-2 text-right text-gray-700 font-medium">Taux</th>
                <th class="px-3 py-2 text-right text-gray-700 font-medium">Max</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-gray-100">
              <tr v-for="item in s5.items" :key="item.id_question" class="hover:bg-gray-50">
                <td class="px-3 py-2 font-medium text-gray-800">{{ item.id_question }}</td>
                <td class="px-3 py-2 text-gray-700">{{ item.capacite_bo }}</td>
                <td class="px-3 py-2 text-gray-500">{{ item.notion }}</td>
                <td class="px-3 py-2 text-right" :class="getRateClass(item.success_rate)">{{ item.success_rate?.toFixed(1) }}%</td>
                <td class="px-3 py-2 text-right text-gray-500">{{ item.max_points }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <!-- ── S2B : Exercices ── -->
      <section class="bg-white border border-gray-200 rounded-xl p-6 shadow-sm">
        <h2 class="text-lg font-bold text-emerald-900 mb-6 flex items-center gap-2 uppercase tracking-wide">
          <span class="w-1 h-5 bg-emerald-600 rounded-full inline-block"></span>
          Partie B — Exercices
          <span class="text-xs font-normal text-emerald-400 normal-case tracking-normal">3 exercices · 14 pts</span>
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
                  <tr v-for="sp in ex.subparts" :key="sp.id"
                    :class="sp.success_rate < 35 ? 'bg-red-50 hover:bg-red-100' : sp.success_rate < 50 ? 'bg-amber-50/60' : 'hover:bg-gray-50'">
                    <td class="px-3 py-2 text-gray-900">{{ sp.label }}</td>
                    <td class="px-3 py-2 text-right text-gray-600">{{ sp.max_points }}</td>
                    <td class="px-3 py-2 text-right font-medium">{{ sp.mean_score?.toFixed(2) }}</td>
                    <td class="px-3 py-2 text-right" :class="getRateClass(sp.success_rate)">{{ sp.success_rate?.toFixed(1) }}%</td>
                  </tr>
                </tbody>
              </table>

              <!-- Analyse de l'exercice : sous-sections parsées -->
              <div v-if="ex.analysis" class="space-y-2.5 mt-2">
                <template v-for="(sec, i) in parseAnalysis(ex.analysis)" :key="i">
                  <div :class="`border rounded-xl p-4 ${subStyle(sec.heading).wrap}`">
                    <div v-if="sec.heading" class="flex items-center gap-2 mb-2">
                      <span class="w-2.5 h-2.5 rounded-full flex-shrink-0" :class="subStyle(sec.heading).dot"></span>
                      <p :class="`text-xs font-bold uppercase tracking-wide ${subStyle(sec.heading).title}`">{{ sec.heading }}</p>
                    </div>
                    <p class="text-sm text-gray-700 leading-relaxed whitespace-pre-line">{{ sec.body }}</p>
                  </div>
                </template>
              </div>
            </div>
          </div>
        </div>
      </section>

      <!-- ── S3 : Tableau complet questions ── -->
      <section class="bg-white border border-gray-200 rounded-xl p-6 shadow-sm">
        <div class="flex flex-wrap items-center justify-between gap-3 mb-4">
          <h2 class="text-lg font-bold text-gray-700 flex items-center gap-2 uppercase tracking-wide">
            <span class="w-1 h-5 bg-gray-400 rounded-full inline-block"></span>
            Analyse par question
            <span class="text-xs font-normal text-gray-400 normal-case tracking-normal">{{ s3?.n_questions }} questions</span>
          </h2>
          <div class="flex items-center gap-3 text-xs text-gray-500">
            <span class="flex items-center gap-1.5"><span class="w-3 h-3 rounded bg-red-100 border border-red-300 inline-block"></span>&lt; 35 %</span>
            <span class="flex items-center gap-1.5"><span class="w-3 h-3 rounded bg-amber-50 border border-amber-200 inline-block"></span>35–55 %</span>
            <span class="flex items-center gap-1.5"><span class="w-3 h-3 rounded bg-white border border-gray-200 inline-block"></span>≥ 55 %</span>
          </div>
        </div>
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
                  </tr>
                </thead>
                <tbody class="divide-y divide-gray-100">
                  <tr v-for="q in s3?.auto_questions" :key="q.question?.id"
                    :class="q.success_rate < 35 ? 'bg-red-50' : q.success_rate < 55 ? 'bg-amber-50/50' : ''">
                    <td class="px-3 py-2 text-gray-800">{{ q.question?.label }}</td>
                    <td class="px-3 py-2 text-right">
                      <div class="flex items-center justify-end gap-1.5">
                        <div class="w-10 bg-gray-200 rounded-full h-1.5 hidden sm:block">
                          <div class="h-1.5 rounded-full" :class="getMeanBarClass(q.success_rate / 5)" :style="{width: Math.min(q.success_rate,100)+'%'}"></div>
                        </div>
                        <span :class="getRateClass(q.success_rate)">{{ q.success_rate?.toFixed(1) }}%</span>
                      </div>
                    </td>
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
                  </tr>
                </thead>
                <tbody class="divide-y divide-gray-100">
                  <tr v-for="q in s3?.exo_questions" :key="q.question?.id"
                    :class="q.success_rate < 35 ? 'bg-red-50' : q.success_rate < 55 ? 'bg-amber-50/50' : ''">
                    <td class="px-3 py-2 text-gray-800">{{ q.question?.label }}</td>
                    <td class="px-3 py-2 text-right">
                      <div class="flex items-center justify-end gap-1.5">
                        <div class="w-10 bg-gray-200 rounded-full h-1.5 hidden sm:block">
                          <div class="h-1.5 rounded-full" :class="getMeanBarClass(q.success_rate / 5)" :style="{width: Math.min(q.success_rate,100)+'%'}"></div>
                        </div>
                        <span :class="getRateClass(q.success_rate)">{{ q.success_rate?.toFixed(1) }}%</span>
                      </div>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </section>

      <!-- ── S4 : Recommandations ── -->
      <section class="bg-white border border-gray-200 rounded-xl p-6 shadow-sm">
        <h2 class="text-lg font-bold text-amber-900 mb-6 flex items-center gap-2 uppercase tracking-wide">
          <span class="w-1 h-5 bg-amber-500 rounded-full inline-block"></span>
          Recommandations pédagogiques
        </h2>
        <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div v-for="(bloc, key) in s4?.blocks" :key="key" class="rounded-xl p-5" :class="blocClass(key)">
            <h3 class="font-bold text-sm uppercase tracking-wide mb-4" :class="blocTitleClass(key)">{{ bloc.title }}</h3>
            <!-- Texte narratif + items parsés pour Blocs A/B -->
            <div v-if="bloc.content" class="space-y-2.5">
              <template v-for="(sec, i) in parseAnalysis(bloc.content)" :key="i">
                <div :class="`border rounded-lg p-3 ${subStyle(sec.heading).wrap}`">
                  <div v-if="sec.heading" class="flex items-center gap-2 mb-2">
                    <span class="w-2 h-2 rounded-full flex-shrink-0" :class="subStyle(sec.heading).dot"></span>
                    <p :class="`text-xs font-bold uppercase tracking-wide ${subStyle(sec.heading).title}`">{{ sec.heading }}</p>
                  </div>
                  <!-- Champs structurés (Action / Modalité / Indicateur) -->
                  <template v-if="parseItemFields(sec.body)">
                    <div v-for="(f, fi) in parseItemFields(sec.body)" :key="fi" class="mt-1 text-xs leading-relaxed">
                      <template v-if="f.label">
                        <span :class="`font-bold uppercase tracking-wide mr-1 ${fieldLabelColor(f.label)}`">{{ f.label }} :</span>
                        <span class="text-gray-700">{{ f.text }}</span>
                      </template>
                      <p v-else class="text-gray-600 italic">{{ f.text }}</p>
                    </div>
                  </template>
                  <p v-else class="text-xs text-gray-700 leading-relaxed whitespace-pre-line">{{ sec.body }}</p>
                </div>
              </template>
              <p v-if="!parseAnalysis(bloc.content).length" class="text-sm text-gray-700 leading-relaxed whitespace-pre-line">{{ bloc.content }}</p>
            </div>
            <!-- Recommandations structurées (Bloc C : affiché même quand content est présent) -->
            <div v-if="bloc.recommandations?.length" class="space-y-3 mt-3">
              <div v-if="bloc.volume" class="text-xs text-amber-700 font-semibold mb-1">{{ bloc.volume }}</div>
              <div v-for="rec in bloc.recommandations" :key="rec.id" class="bg-white rounded-lg p-3 border border-amber-200 space-y-1">
                <div class="font-bold text-sm text-amber-900">[{{ rec.id }}] {{ rec.titre }}</div>
                <p class="text-xs text-gray-700 leading-relaxed">{{ rec.action }}</p>
                <p v-if="rec.modalite" class="text-xs text-gray-500 italic border-l-2 border-gray-300 pl-2">{{ rec.modalite }}</p>
                <p v-if="rec.observable" class="text-xs text-emerald-700 font-medium">↳ {{ rec.observable }}</p>
              </div>
              <div v-if="bloc.observable" class="text-xs text-gray-500 italic border-t border-gray-200 pt-2">Observable global : {{ bloc.observable }}</div>
            </div>
          </div>
        </div>
      </section>

      <!-- ── S4 : Plan de phases ── -->
      <section v-if="s4?.plan_phases" class="bg-white border border-gray-200 rounded-xl p-6 shadow-sm">
        <h2 class="text-lg font-bold text-indigo-900 mb-6 flex items-center gap-2 uppercase tracking-wide">
          <span class="w-1 h-5 bg-indigo-600 rounded-full inline-block"></span>
          Plan d'action par phases
        </h2>
        <div class="space-y-6">
          <div v-for="(phase, key) in s4.plan_phases" :key="key" class="border border-gray-200 rounded-xl overflow-hidden">
            <div class="bg-indigo-50 px-5 py-3 flex items-center justify-between">
              <h3 class="font-semibold text-indigo-900">{{ phase.titre }}</h3>
              <span class="text-sm text-indigo-700 font-medium">{{ phase.periode }}</span>
            </div>
            <div class="p-4">
              <!-- Semaines détaillées (phase 1) -->
              <div v-if="phase.semaines?.length" class="space-y-2 mb-3">
                <div v-for="sem in phase.semaines" :key="sem.label"
                  class="flex flex-col sm:flex-row sm:items-start gap-2 py-2 border-b border-gray-100 last:border-0">
                  <span class="text-sm font-medium text-gray-700 w-44 shrink-0">{{ sem.label }}</span>
                  <div class="flex-1">
                    <p class="text-sm text-gray-700">{{ sem.focus }}</p>
                    <p v-if="sem.modalite" class="text-xs text-gray-500 mt-0.5">{{ sem.modalite }}</p>
                    <p v-if="sem.livrable" class="text-xs text-emerald-700 mt-0.5">↳ {{ sem.livrable }}</p>
                  </div>
                </div>
              </div>
              <!-- Phase 2 : pack contenu -->
              <div v-if="phase.pack_contenu?.length" class="space-y-1">
                <p class="text-sm font-medium text-gray-700 mb-2">Contenu du pack :</p>
                <ul class="list-disc list-inside space-y-1">
                  <li v-for="item in phase.pack_contenu" :key="item" class="text-sm text-gray-600">{{ item }}</li>
                </ul>
                <p v-if="phase.pack_livraison" class="text-xs text-indigo-700 mt-2">Livraison : {{ phase.pack_livraison }}</p>
                <p v-if="phase.recommandation_eleves" class="text-xs text-gray-500 italic mt-1">{{ phase.recommandation_eleves }}</p>
              </div>
              <!-- Phase 3 : note -->
              <p v-if="phase.note" class="text-sm text-gray-500 italic">{{ phase.note }}</p>
              <p v-if="phase.action" class="text-sm text-gray-700">{{ phase.action }}</p>
              <p v-if="phase.tampon" class="text-xs text-amber-700 mt-2">⚠ {{ phase.tampon }}</p>
            </div>
          </div>
        </div>
      </section>

      <!-- ── S11 : Anticipation Terminale ── -->
      <section v-if="s11?.domaines?.length" class="bg-white border border-gray-200 rounded-xl p-6 shadow-sm">
        <h2 class="text-lg font-bold text-purple-900 mb-2 flex items-center gap-2 uppercase tracking-wide">
          <span class="w-1 h-5 bg-purple-600 rounded-full inline-block"></span>
          Anticipation Terminale
        </h2>
        <p v-if="s11.note_interne" class="text-xs text-gray-400 italic mb-6 ml-3">{{ s11.note_interne }}</p>
        <div class="space-y-5">
          <div v-for="dom in s11.domaines" :key="dom.key"
            :class="`border rounded-xl overflow-hidden ${domainColors(dom.titre).border}`">
            <!-- En-tête domaine -->
            <div :class="`px-5 py-3 flex items-center gap-3 ${domainColors(dom.titre).header}`">
              <AppIcon name="book-open" :size="16" :class="domainColors(dom.titre).icon" />
              <h3 :class="`font-bold text-sm uppercase tracking-wide ${domainColors(dom.titre).ht}`">
                {{ dom.titre?.charAt(0).toUpperCase() + dom.titre?.slice(1).toLowerCase() }}
              </h3>
            </div>
            <div class="p-4 grid grid-cols-1 md:grid-cols-3 gap-3">
              <!-- Prérequis observés -->
              <div v-if="dom.prereqs_obs" :class="`rounded-lg p-3 ${domainColors(dom.titre).p1}`">
                <p :class="`text-xs font-bold uppercase tracking-wide mb-2 ${domainColors(dom.titre).icon}`">📋 Prérequis EAM</p>
                <p class="text-xs text-gray-700 leading-relaxed">{{ dom.prereqs_obs }}</p>
              </div>
              <!-- Compétences Terminale -->
              <div v-if="dom.competences_terminale" :class="`rounded-lg p-3 ${domainColors(dom.titre).p2}`">
                <p :class="`text-xs font-bold uppercase tracking-wide mb-2 ${domainColors(dom.titre).icon}`">🎓 Programme Terminale</p>
                <p class="text-xs text-gray-700 leading-relaxed">{{ dom.competences_terminale }}</p>
              </div>
              <!-- Recommandation passerelle -->
              <div v-if="dom.recommandation" class="rounded-lg p-3 bg-emerald-50 border border-emerald-200">
                <p class="text-xs font-bold uppercase tracking-wide mb-2 text-emerald-700">📍 Recommandation</p>
                <p class="text-xs text-gray-700 leading-relaxed">{{ dom.recommandation }}</p>
              </div>
            </div>
          </div>
        </div>
      </section>

      <!-- ── S12 : Note de transmission ── -->
      <section v-if="s12" class="bg-white border border-gray-200 rounded-xl p-6 shadow-sm">
        <h2 class="text-lg font-bold text-gray-500 mb-4 flex items-center gap-2 uppercase tracking-wide">
          <span class="w-1 h-5 bg-gray-400 rounded-full inline-block"></span>
          Note de Transmission
        </h2>
        <div class="border border-gray-200 rounded-xl overflow-hidden">
          <div class="bg-gray-50 px-5 py-3 flex flex-wrap items-center justify-between gap-2 border-b border-gray-200">
            <span class="text-xs font-semibold text-gray-600 uppercase tracking-wide">{{ s12.auteur }}</span>
            <span class="text-xs text-gray-400 italic">{{ s12.date_production }}</span>
          </div>
          <div class="p-5 bg-white">
            <p class="text-sm text-gray-700 leading-relaxed whitespace-pre-line">{{ s12.content }}</p>
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
const s5 = computed(() => {
  const raw = sections.value?.S5 || null
  if (!raw) return null
  if (Array.isArray(raw)) return { items: raw }
  if (raw.items) return raw
  return null
})
const s11 = computed(() => sections.value?.S11 || null)
const s12 = computed(() => sections.value?.S12 || null)
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

// ── S0 : intro + leviers ─────────────────────────────────────────
const s0Parsed = computed(() => {
  const text = cleanContent(s0.value?.content)
  if (!text) return { intro: '', levers: [] }
  const idx = text.indexOf('Leviers prioritaires')
  if (idx === -1) return { intro: text, levers: [] }
  const intro = text.slice(0, idx).trim()
  const rest = text.slice(idx + 'Leviers prioritaires'.length).trim()
  const levers = []
  for (const p of rest.split(/\n(?=\d+\.)/)) {
    const c = p.trim()
    if (c) levers.push(c.replace(/^\d+\.\s*/, ''))
  }
  return { intro, levers }
})

// ── Parser sous-sections analyse LLM ─────────────────────────────
const ANALYSIS_HEADS = [
  'Analyse des réussites', 'Analyse des difficultés',
  'Micro-rituels de remédiation différenciée',
  'Analyse des résultats par sous-partie',
  'Hypothèse diagnostique principale',
  "Hypothèse principale sur l'erreur la plus fréquente",
  'Leviers méthodologiques', 'Prolongement en révision autonome',
  'Grille formative commune',
]
const isAnalHead = (line) =>
  ANALYSIS_HEADS.some(h => line.trim().startsWith(h)) ||
  /^Item\s+Q\d+/.test(line.trim()) ||
  /^Recommandation\s+B\d+/.test(line.trim())

const parseAnalysis = (text) => {
  if (!text) return []
  const lines = cleanContent(text).split('\n')
  const out = []
  let cur = { heading: null, lines: [] }
  for (const line of lines) {
    if (isAnalHead(line) && line.trim().length < 120) {
      if (cur.lines.some(l => l.trim())) out.push({ heading: cur.heading, body: cur.lines.join('\n').trim() })
      cur = { heading: line.trim(), lines: [] }
    } else {
      cur.lines.push(line)
    }
  }
  if (cur.lines.some(l => l.trim())) out.push({ heading: cur.heading, body: cur.lines.join('\n').trim() })
  return out.filter(s => s.body)
}

const subStyle = (heading) => {
  const h = (heading || '').toLowerCase()
  if (h.includes('réussite'))  return { wrap: 'bg-emerald-50 border-emerald-200', dot: 'bg-emerald-500', title: 'text-emerald-800' }
  if (h.includes('difficult')) return { wrap: 'bg-red-50 border-red-200',         dot: 'bg-red-500',     title: 'text-red-800' }
  if (h.includes('rituel') || h.includes('micro')) return { wrap: 'bg-indigo-50 border-indigo-200', dot: 'bg-indigo-500', title: 'text-indigo-800' }
  if (h.includes('hypothèse') || h.includes('diagnostiq')) return { wrap: 'bg-amber-50 border-amber-200', dot: 'bg-amber-500', title: 'text-amber-800' }
  if (h.includes('levier') || h.includes('méthodolog')) return { wrap: 'bg-sky-50 border-sky-200', dot: 'bg-sky-500', title: 'text-sky-800' }
  if (h.includes('révision') || h.includes('prolongement')) return { wrap: 'bg-purple-50 border-purple-200', dot: 'bg-purple-500', title: 'text-purple-800' }
  if (h.includes('grille')) return { wrap: 'bg-gray-50 border-gray-200', dot: 'bg-gray-400', title: 'text-gray-700' }
  if (/^item\s+q/i.test(h))    return { wrap: 'bg-amber-50 border-amber-200', dot: 'bg-amber-500', title: 'text-amber-800' }
  if (/^recommandation\s+b/i.test(h)) return { wrap: 'bg-emerald-50 border-emerald-200', dot: 'bg-emerald-600', title: 'text-emerald-900' }
  return { wrap: 'bg-gray-50 border-gray-100', dot: 'bg-gray-400', title: 'text-gray-700' }
}

const domainColors = (titre) => {
  const t = (titre || '').toLowerCase()
  if (t.includes('suite'))                         return { border:'border-blue-200',   header:'bg-blue-50',   ht:'text-blue-900',   icon:'text-blue-500',   p1:'bg-blue-50',    p2:'bg-blue-100/60'  }
  if (t.includes('probab'))                        return { border:'border-violet-200', header:'bg-violet-50', ht:'text-violet-900', icon:'text-violet-500', p1:'bg-violet-50',  p2:'bg-violet-100/60' }
  if (t.includes('deriv') || t.includes('fonction')) return { border:'border-emerald-200',header:'bg-emerald-50',ht:'text-emerald-900',icon:'text-emerald-500',p1:'bg-emerald-50',p2:'bg-emerald-100/60' }
  if (t.includes('trigo'))                         return { border:'border-amber-200',  header:'bg-amber-50',  ht:'text-amber-900',  icon:'text-amber-500',  p1:'bg-amber-50',   p2:'bg-amber-100/60' }
  if (t.includes('algo') || t.includes('python'))  return { border:'border-slate-200',  header:'bg-slate-50',  ht:'text-slate-900',  icon:'text-slate-500',  p1:'bg-slate-50',   p2:'bg-slate-100/60' }
  return { border:'border-gray-200', header:'bg-gray-50', ht:'text-gray-900', icon:'text-gray-500', p1:'bg-gray-50', p2:'bg-gray-100/60' }
}

const getMeanBarClass = (m) => {
  if (m == null) return 'bg-gray-300'
  if (m >= 14) return 'bg-green-500'
  if (m >= 10) return 'bg-indigo-400'
  return 'bg-red-400'
}
const getMeanTextClass = (m) => {
  if (m == null) return 'text-gray-500'
  if (m >= 14) return 'text-green-700 font-bold'
  if (m >= 10) return 'text-indigo-700 font-semibold'
  return 'text-red-600 font-semibold'
}

// ── Parser Action / Modalité / Indicateur dans les items S4 ───────
const ITEM_FIELD_LABELS = ['Action', 'Modalité', 'Indicateur observable', 'Observable', 'Grille formative']
const parseItemFields = (body) => {
  if (!body) return null
  const lines = body.split('\n')
  const result = []
  let cur = null
  for (const line of lines) {
    const t = line.trim()
    if (!t) continue
    const fl = ITEM_FIELD_LABELS.find(f => t.startsWith(f + ' :') || t.startsWith(f + ':'))
    if (fl) {
      if (cur) result.push(cur)
      cur = { label: fl, text: t.slice(t.indexOf(':') + 1).trim() }
    } else if (cur) {
      cur.text += ' ' + t
    } else {
      result.push({ label: null, text: t })
    }
  }
  if (cur) result.push(cur)
  return result.some(r => r.label) ? result : null
}
const fieldLabelColor = (label) => {
  const l = (label || '').toLowerCase()
  if (l === 'action')              return 'text-indigo-700'
  if (l === 'modalité')            return 'text-slate-600'
  if (l.includes('indicateur') || l === 'observable') return 'text-emerald-700'
  return 'text-gray-500'
}

const cleanContent = (text) => {
  if (!text) return ''
  const lines = text.split('\n')
  const firstLine = lines[0]?.trim()
  if (firstLine && firstLine.length < 80 && !firstLine.includes('.') && lines[1]?.trim() === '' && lines.length > 2) {
    return lines.slice(2).join('\n').trim()
  }
  return text.trim()
}

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
    const status = err.response?.status
    const detail = (err.response?.data?.detail || '').toLowerCase()
    error.value = status === 403 && detail.includes('not provided')
      ? 'Session expirée. Veuillez vous reconnecter.'
      : status === 403
        ? "Vous n'avez pas la permission de consulter ce bilan."
        : status === 404
          ? 'Bilan non trouvé pour cet examen.'
          : 'Erreur lors du chargement du bilan.'
  } finally {
    isLoading.value = false
  }
}

onMounted(fetchBilan)
</script>
