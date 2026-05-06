<template>
  <div class="p-6">
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
          Bilan DNB 2026 — {{ formatDate(bilan?.generated_at) }}
        </h1>
      </div>

      <div class="flex flex-wrap items-center gap-3">
        <span
          :class="getStatusClass(bilan?.status)"
          class="px-3 py-1 text-sm font-medium rounded-full"
        >
          {{ getStatusText(bilan?.status) }}
        </span>

        <div class="text-sm text-gray-600">
          <span class="font-medium">Copies analysées :</span>
          {{ bilan?.s1_stats?.n_copies ?? bilan?.metadata?.n_copies ?? 'N/A' }}
        </div>

        <div class="text-sm text-gray-600">
          <span class="font-medium">Généré par :</span>
          {{ bilan?.generated_by || 'N/A' }}
        </div>

        <div v-if="bilan?.generated_at" class="text-sm text-gray-500">
          {{ formatDate(bilan.generated_at) }}
        </div>

        <button
          v-if="bilan?.pdf_available"
          @click="downloadPDF"
          class="inline-flex items-center gap-2 bg-green-600 text-white px-4 py-2 rounded-lg hover:bg-green-700 transition-colors font-medium"
        >
          <AppIcon name="download" :size="16" />
          Télécharger le PDF
        </button>
      </div>
    </div>

    <!-- Loading -->
    <div v-if="isLoading" class="text-center py-12">
      <div class="inline-flex items-center gap-2 text-gray-600">
        <div class="animate-spin rounded-full h-6 w-6 border-b-2 border-indigo-600"></div>
        Chargement du bilan...
      </div>
    </div>

    <!-- Error -->
    <div v-else-if="error" class="text-center py-12">
      <div class="inline-flex items-center justify-center w-16 h-16 bg-red-100 rounded-full mb-4">
        <AppIcon name="alert-triangle" :size="32" class="text-red-500" />
      </div>
      <h3 class="text-lg font-medium text-gray-900 mb-2">Erreur de chargement</h3>
      <p class="text-gray-600 mb-4">{{ error }}</p>
      <button
        @click="fetchBilan"
        class="inline-flex items-center gap-2 bg-indigo-600 text-white px-4 py-2 rounded-lg hover:bg-indigo-700 transition-colors font-medium"
      >
        <AppIcon name="refresh" :size="16" />
        Réessayer
      </button>
    </div>

    <!-- Bilan Content -->
    <div v-else-if="bilan && bilan.status === 'DONE'" class="space-y-8">

      <!-- ── SECTION 1 : Tableau de bord statistique ── -->
      <section class="bg-white border border-gray-200 rounded-lg p-6">
        <h2 class="text-xl font-semibold text-gray-900 mb-4 flex items-center gap-2">
          <AppIcon name="bar-chart" :size="20" class="text-indigo-600" />
          Tableau de bord statistique
        </h2>

        <!-- Signaux forts (métadonnées déterministes DB) -->
        <div v-if="bilan?.metadata?.strong_signals?.length" class="mb-6 space-y-2">
          <div
            v-for="(sig, i) in bilan.metadata.strong_signals"
            :key="i"
            :class="getSeverityClass(sig.severity)"
            class="border rounded-lg px-4 py-3 text-sm"
          >
            {{ sig.message }}
          </div>
        </div>

        <div class="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
          <div class="bg-blue-50 p-4 rounded-lg">
            <div class="text-2xl font-bold text-blue-900">
              {{ bilan.s1_stats?.mean?.toFixed(1) ?? 'N/A' }}/20
            </div>
            <div class="text-sm text-blue-700 mt-1">Moyenne générale</div>
          </div>

          <div class="bg-green-50 p-4 rounded-lg">
            <div class="text-2xl font-bold text-green-900">
              {{ bilan.s1_stats?.median?.toFixed(1) ?? 'N/A' }}/20
            </div>
            <div class="text-sm text-green-700 mt-1">Médiane</div>
          </div>

          <div class="bg-purple-50 p-4 rounded-lg">
            <div class="text-2xl font-bold text-purple-900">
              {{ bilan.s1_stats?.pct_above_10?.toFixed(1) ?? 'N/A' }}%
            </div>
            <div class="text-sm text-purple-700 mt-1">Taux de réussite ≥ 10</div>
          </div>

          <div class="bg-orange-50 p-4 rounded-lg">
            <div class="text-2xl font-bold text-orange-900">
              {{ bilan.s1_stats?.std?.toFixed(2) ?? 'N/A' }}
            </div>
            <div class="text-sm text-orange-700 mt-1">Écart-type</div>
          </div>
        </div>

        <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <!-- Distribution des notes -->
          <div>
            <h3 class="text-base font-medium text-gray-900 mb-3">Distribution des notes</h3>
            <div class="bg-gray-50 rounded-lg p-4 space-y-2">
              <div
                v-for="{ label, key, color } in distributionRows"
                :key="key"
                class="flex items-center gap-3"
              >
                <div class="w-40 text-sm text-gray-700">{{ label }}</div>
                <div class="flex-1 bg-gray-200 rounded-full h-5 overflow-hidden">
                  <div
                    :class="color"
                    class="h-5 rounded-full transition-all duration-500"
                    :style="{ width: distBarWidth(bilan.s1_stats?.distribution?.[key]) }"
                  ></div>
                </div>
                <div class="w-12 text-sm font-semibold text-right">
                  {{ bilan.s1_stats?.distribution?.[key] ?? 0 }}
                </div>
              </div>
            </div>
          </div>

          <!-- Indicateurs clés -->
          <div>
            <h3 class="text-base font-medium text-gray-900 mb-3">Indicateurs clés</h3>
            <div class="bg-gray-50 rounded-lg p-4 space-y-2">
              <div class="flex justify-between text-sm py-1 border-b border-gray-200">
                <span class="text-gray-600">Note minimale</span>
                <span class="font-semibold">{{ bilan.s1_stats?.min?.toFixed(1) ?? 'N/A' }}/20</span>
              </div>
              <div class="flex justify-between text-sm py-1 border-b border-gray-200">
                <span class="text-gray-600">Note maximale</span>
                <span class="font-semibold">{{ bilan.s1_stats?.max?.toFixed(1) ?? 'N/A' }}/20</span>
              </div>
              <div class="flex justify-between text-sm py-1 border-b border-gray-200">
                <span class="text-gray-600">Étendue</span>
                <span class="font-semibold">{{ bilan.s1_stats?.range?.toFixed(1) ?? 'N/A' }} pts</span>
              </div>
              <div class="flex justify-between text-sm py-1 border-b border-gray-200">
                <span class="text-gray-600">Nombre de copies</span>
                <span class="font-semibold">{{ bilan.s1_stats?.n_copies ?? 'N/A' }}</span>
              </div>
              <div class="flex justify-between text-sm py-1">
                <span class="text-gray-600">Modèle LLM</span>
                <span class="font-semibold text-xs text-gray-500">{{ bilan.llm_model ?? '—' }}</span>
              </div>

              <!-- Qualité données / traçabilité -->
              <div class="flex justify-between text-sm py-1 border-t border-gray-200 mt-2 pt-2">
                <span class="text-gray-600">DB</span>
                <span class="font-semibold text-xs text-gray-500">
                  {{ bilan?.metadata?.data_quality?.db_engine ?? '—' }}
                  <span v-if="bilan?.metadata?.data_quality?.db_name"> · {{ bilan.metadata.data_quality.db_name }}</span>
                </span>
              </div>
              <div class="flex justify-between text-sm py-1">
                <span class="text-gray-600">Copies avec scores</span>
                <span class="font-semibold">
                  {{ bilan?.metadata?.data_quality?.n_copies_with_scores ?? '—' }}
                  <span class="text-xs text-gray-500">/ {{ bilan?.metadata?.data_quality?.n_copies_included_in_bilan ?? '—' }}</span>
                </span>
              </div>
              <div class="flex justify-between text-sm py-1">
                <span class="text-gray-600">Copies sans élève</span>
                <span class="font-semibold text-red-700">
                  {{ bilan?.metadata?.data_quality?.n_scored_without_student ?? 0 }}
                </span>
              </div>
              <div class="flex justify-between text-sm py-1">
                <span class="text-gray-600">Copies sans correcteur</span>
                <span class="font-semibold text-orange-700">
                  {{ bilan?.metadata?.data_quality?.n_scored_without_corrector ?? 0 }}
                </span>
              </div>
              <div class="flex justify-between text-sm py-1">
                <span class="text-gray-600">RAG</span>
                <span class="font-semibold text-xs text-gray-500">
                  ok={{ bilan?.metadata?.rag_stats?.ok ?? 0 }} · empty={{ bilan?.metadata?.rag_stats?.empty ?? 0 }} · down={{ bilan?.metadata?.rag_stats?.unavailable ?? 0 }}
                </span>
              </div>
              <div class="flex justify-between text-sm py-1">
                <span class="text-gray-600">LLM</span>
                <span class="font-semibold text-xs text-gray-500">
                  calls={{ bilan?.metadata?.llm_stats?.calls ?? 0 }}
                </span>
              </div>
            </div>
          </div>
        </div>
      </section>

      <!-- ── SECTION 2 : Analyse par domaine ── -->
      <section class="bg-white border border-gray-200 rounded-lg p-6">
        <h2 class="text-xl font-semibold text-gray-900 mb-4 flex items-center gap-2">
          <AppIcon name="target" :size="20" class="text-indigo-600" />
          Analyse par domaine du programme
        </h2>

        <div class="overflow-x-auto">
          <table class="w-full text-sm">
            <thead class="bg-gray-50">
              <tr>
                <th class="px-4 py-2 text-left font-medium text-gray-900">Domaine</th>
                <th class="px-4 py-2 text-center font-medium text-gray-900">Taux de réussite</th>
                <th class="px-4 py-2 text-center font-medium text-gray-900">Signal</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="(rate, domain) in bilan.s2_domains?.data"
                :key="domain"
                class="border-t border-gray-200 hover:bg-gray-50"
              >
                <td class="px-4 py-2 font-medium">{{ domain }}</td>
                <td class="px-4 py-2 text-center">
                  <span :class="getRateClass(rate)">
                    {{ rate?.toFixed(1) ?? 'N/A' }}%
                  </span>
                </td>
                <td class="px-4 py-2 text-center">
                  <span :class="getSignalClass(rate)" class="px-2 py-1 text-xs font-bold rounded-full">
                    {{ getSignalText(rate) }}
                  </span>
                </td>
              </tr>
              <tr v-if="!bilan.s2_domains?.data || Object.keys(bilan.s2_domains.data).length === 0">
                <td colspan="3" class="px-4 py-6 text-center text-gray-500">Aucune donnée disponible</td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- Analyses LLM des domaines faibles -->
        <div v-if="bilan.s2_domains?.analyses && Object.keys(bilan.s2_domains.analyses).length > 0" class="mt-6 space-y-4">
          <h3 class="text-base font-medium text-gray-900">Analyse des domaines les plus faibles</h3>
          <div
            v-for="(analysis, domain) in bilan.s2_domains.analyses"
            :key="domain"
            class="bg-red-50 border border-red-200 rounded-lg p-5"
          >
            <h4 class="font-semibold text-red-900 mb-3 flex items-center gap-2">
              <span class="w-2 h-2 bg-red-500 rounded-full inline-block"></span>
              {{ domain }}
            </h4>
            <div class="prose prose-sm text-red-800 max-w-none" v-html="renderMarkdown(analysis)"></div>
          </div>
        </div>
      </section>

      <!-- ── SECTION 3 : Analyse question par question ── -->
      <section class="bg-white border border-gray-200 rounded-lg p-6">
        <h2 class="text-xl font-semibold text-gray-900 mb-4 flex items-center gap-2">
          <AppIcon name="list-checks" :size="20" class="text-indigo-600" />
          Analyse question par question
        </h2>

        <div v-if="bilan.s3_questions?.length > 0">
          <div class="overflow-x-auto">
            <table class="w-full text-sm">
              <thead class="bg-gray-50">
                <tr>
                  <th class="px-3 py-2 text-left font-medium text-gray-900">Q.</th>
                  <th class="px-3 py-2 text-left font-medium text-gray-900">Domaine</th>
                  <th class="px-3 py-2 text-left font-medium text-gray-900">Compétence</th>
                  <th class="px-3 py-2 text-center font-medium text-gray-900">Moy / Max</th>
                  <th class="px-3 py-2 text-center font-medium text-gray-900">Réussite</th>
                  <th class="px-3 py-2 text-center font-medium text-gray-900">Blancs</th>
                  <th class="px-3 py-2 text-center font-medium text-gray-900">Zéro</th>
                  <th class="px-3 py-2 text-center font-medium text-gray-900">Plein</th>
                </tr>
              </thead>
              <tbody>
                <tr
                  v-for="q in bilan.s3_questions"
                  :key="q.question?.number"
                  class="border-t border-gray-200 hover:bg-gray-50"
                >
                  <td class="px-3 py-2 font-semibold">Q{{ q.question?.number }}</td>
                  <td class="px-3 py-2 text-gray-600">{{ q.question?.domain || 'N/A' }}</td>
                  <td class="px-3 py-2">
                    <span class="text-xs px-2 py-0.5 bg-indigo-100 text-indigo-800 rounded-full">
                      {{ q.question?.competence || 'N/A' }}
                    </span>
                  </td>
                  <td class="px-3 py-2 text-center">
                    {{ q.mean_score?.toFixed(1) ?? 'N/A' }} / {{ q.question?.max_points ?? 'N/A' }}
                  </td>
                  <td class="px-3 py-2 text-center">
                    <span :class="getRateClass(q.success_rate)">
                      {{ q.success_rate?.toFixed(1) ?? 'N/A' }}%
                    </span>
                  </td>
                  <td class="px-3 py-2 text-center text-gray-600">{{ q.blank_rate?.toFixed(1) ?? 'N/A' }}%</td>
                  <td class="px-3 py-2 text-center text-red-600">{{ q.zero_rate?.toFixed(1) ?? 'N/A' }}%</td>
                  <td class="px-3 py-2 text-center text-green-600">{{ q.full_rate?.toFixed(1) ?? 'N/A' }}%</td>
                </tr>
              </tbody>
            </table>
          </div>

          <!-- Top / Flop questions -->
          <div class="grid grid-cols-1 lg:grid-cols-2 gap-6 mt-6">
            <div>
              <h3 class="text-base font-medium text-green-800 mb-3">Top 3 — Questions les mieux réussies</h3>
              <div class="space-y-2">
                <div
                  v-for="q in getTopQuestions(3)"
                  :key="q.question?.number"
                  class="bg-green-50 border border-green-200 p-3 rounded-lg flex justify-between items-center"
                >
                  <div>
                    <span class="font-semibold">Q{{ q.question?.number }}</span>
                    <span class="text-xs text-gray-500 ml-2">{{ q.question?.domain }}</span>
                  </div>
                  <span class="text-green-700 font-bold">{{ q.success_rate?.toFixed(1) }}%</span>
                </div>
              </div>
            </div>

            <div>
              <h3 class="text-base font-medium text-red-800 mb-3">Flop 3 — Questions les plus échouées</h3>
              <div class="space-y-2">
                <div
                  v-for="q in getFlopQuestions(3)"
                  :key="q.question?.number"
                  class="bg-red-50 border border-red-200 p-3 rounded-lg flex justify-between items-center"
                >
                  <div>
                    <span class="font-semibold">Q{{ q.question?.number }}</span>
                    <span class="text-xs text-gray-500 ml-2">{{ q.question?.domain }}</span>
                  </div>
                  <span class="text-red-700 font-bold">{{ q.success_rate?.toFixed(1) }}%</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div v-else class="py-8 text-center text-gray-500">
          <AppIcon name="info" :size="24" class="mx-auto mb-2 text-gray-400" />
          <p>Aucune donnée question disponible (les annotations n'ont pas encore été générées pour cet examen).</p>
        </div>
      </section>

      <!-- ── SECTION 4 : Maîtrise des 6 compétences DNB ── -->
      <section class="bg-white border border-gray-200 rounded-lg p-6">
        <h2 class="text-xl font-semibold text-gray-900 mb-4 flex items-center gap-2">
          <AppIcon name="award" :size="20" class="text-indigo-600" />
          Maîtrise des 6 compétences DNB
        </h2>

        <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div>
            <h3 class="text-base font-medium text-gray-900 mb-3">Taux de maîtrise par compétence</h3>
            <div class="space-y-3">
              <div
                v-for="(rate, comp) in bilan.s4_competences?.data"
                :key="comp"
                class="flex items-center gap-3"
              >
                <div class="w-28 text-sm font-medium capitalize text-gray-700">{{ comp }}</div>
                <div class="flex-1 bg-gray-200 rounded-full h-6 overflow-hidden">
                  <div
                    :class="getCompetenceBarClass(rate)"
                    class="h-6 rounded-full flex items-center justify-center text-xs font-semibold text-white transition-all duration-500"
                    :style="{ width: `${Math.min(Math.max(rate ?? 0, 8), 100)}%` }"
                  >
                    {{ rate?.toFixed(1) ?? 'N/A' }}%
                  </div>
                </div>
              </div>
              <div v-if="!bilan.s4_competences?.data" class="text-gray-500 text-sm">Aucune donnée</div>
            </div>
          </div>

          <div>
            <h3 class="text-base font-medium text-gray-900 mb-3">Analyse des compétences</h3>
            <div v-if="bilan.s4_competences?.analysis" class="bg-blue-50 border border-blue-200 rounded-lg p-5">
              <div class="prose prose-sm text-blue-800 max-w-none" v-html="renderMarkdown(bilan.s4_competences.analysis)"></div>
            </div>
            <div v-else class="text-gray-500 text-sm">Aucune analyse disponible</div>
          </div>
        </div>
      </section>

      <!-- ── SECTION 5 : Analyse inter-correcteurs (Admin uniquement) ── -->
      <section
        v-if="authStore.user?.role === 'Admin' && bilan.s5_correctors"
        class="bg-white border border-gray-200 rounded-lg p-6"
      >
        <h2 class="text-xl font-semibold text-gray-900 mb-1 flex items-center gap-2">
          <AppIcon name="users" :size="20" class="text-indigo-600" />
          Analyse inter-correcteurs
        </h2>
        <p class="text-xs text-gray-500 mb-4">Confidentiel — Réservé à l'administration</p>

        <div class="overflow-x-auto">
          <table class="w-full text-sm">
            <thead class="bg-gray-50">
              <tr>
                <th class="px-4 py-2 text-left font-medium text-gray-900">Correcteur</th>
                <th class="px-4 py-2 text-center font-medium text-gray-900">Copies</th>
                <th class="px-4 py-2 text-center font-medium text-gray-900">Moyenne</th>
                <th class="px-4 py-2 text-center font-medium text-gray-900">Δ vs moy.</th>
                <th class="px-4 py-2 text-center font-medium text-gray-900">Écart-type</th>
                <th class="px-4 py-2 text-center font-medium text-gray-900">Profil</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="c in bilan.s5_correctors?.data"
                :key="c.corrector__name"
                class="border-t border-gray-200 hover:bg-gray-50"
              >
                <td class="px-4 py-2 font-medium">{{ c.corrector__name }}</td>
                <td class="px-4 py-2 text-center">{{ c.n ?? 'N/A' }}</td>
                <td class="px-4 py-2 text-center">{{ c.mean?.toFixed(1) ?? 'N/A' }}/20</td>
                <td class="px-4 py-2 text-center">
                  <span :class="c.delta_from_mean > 1.5 ? 'text-orange-600 font-semibold' : c.delta_from_mean < -1.5 ? 'text-blue-600 font-semibold' : 'text-gray-600'">
                    {{ c.delta_from_mean != null ? (c.delta_from_mean > 0 ? '+' : '') + c.delta_from_mean.toFixed(1) : 'N/A' }}
                  </span>
                </td>
                <td class="px-4 py-2 text-center">{{ c.std?.toFixed(1) ?? 'N/A' }}</td>
                <td class="px-4 py-2 text-center">
                  <span :class="getCorrectorProfileClass(c.severity)" class="px-2 py-1 text-xs font-semibold rounded-full">
                    {{ c.severity ?? 'N/A' }}
                  </span>
                </td>
              </tr>
              <tr v-if="!bilan.s5_correctors?.data?.length">
                <td colspan="6" class="px-4 py-6 text-center text-gray-500">Aucune donnée</td>
              </tr>
            </tbody>
          </table>
        </div>

        <div v-if="bilan.s5_correctors?.analysis" class="mt-6">
          <h3 class="text-base font-medium text-gray-900 mb-3">Analyse de cohérence</h3>
          <div class="bg-orange-50 border border-orange-200 rounded-lg p-5">
            <div class="prose prose-sm text-orange-800 max-w-none" v-html="renderMarkdown(bilan.s5_correctors.analysis)"></div>
          </div>
        </div>
      </section>

      <!-- ── SECTION 6 : Profils de la promotion ── -->
      <section class="bg-white border border-gray-200 rounded-lg p-6">
        <h2 class="text-xl font-semibold text-gray-900 mb-4 flex items-center gap-2">
          <AppIcon name="users" :size="20" class="text-indigo-600" />
          Profils de la promotion
        </h2>

        <div class="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
          <!-- Répartition par mention -->
          <div>
            <h3 class="text-base font-medium text-gray-900 mb-3">Répartition par mention</h3>
            <div class="space-y-2">
              <div
                v-for="{ label, key, color, textColor } in distributionRows"
                :key="key"
                class="flex justify-between items-center p-2 bg-gray-50 rounded-lg"
              >
                <span class="text-sm font-medium">{{ label }}</span>
                <span :class="textColor" class="text-sm font-bold">
                  {{ bilan.s1_stats?.distribution?.[key] ?? 0 }} élèves
                </span>
              </div>
            </div>
          </div>

          <!-- Élèves à risque -->
          <div>
            <h3 class="text-base font-medium text-gray-900 mb-3">
              Élèves à risque
              <span v-if="bilan.s6_profiles?.at_risk?.length" class="ml-1 text-xs text-red-600 font-normal">
                ({{ bilan.s6_profiles.at_risk.length }} identifiés)
              </span>
            </h3>
            <div v-if="bilan.s6_profiles?.at_risk?.length > 0" class="space-y-2">
              <div
                v-for="(student, idx) in bilan.s6_profiles.at_risk.slice(0, 5)"
                :key="idx"
                class="bg-red-50 border border-red-100 p-3 rounded-lg"
              >
                <div class="flex justify-between items-start">
                  <div>
                    <div class="font-medium text-gray-900">
                      {{ student.name || student.anonymous_id || student.copy_id || '—' }}
                    </div>
                    <div class="text-xs text-gray-500">{{ student.class || '—' }}</div>
                  </div>
                  <div class="text-right text-sm">
                    <div class="text-gray-600">
                      Score total : <span class="font-semibold text-red-700">{{ student.total_score ?? formatScore(student.p1, student.p2) }}/20</span>
                    </div>
                    <div class="text-xs text-gray-500">
                      Partie 1 : {{ student.p1?.toFixed(1) ?? '—' }}/6 · Partie 2 : {{ student.p2?.toFixed(1) ?? '—' }}/14
                    </div>
                  </div>
                </div>
              </div>
              <div v-if="bilan.s6_profiles.at_risk.length > 5" class="text-sm text-gray-500 text-center py-1">
                … et {{ bilan.s6_profiles.at_risk.length - 5 }} autres élèves
              </div>
            </div>
            <div v-else class="bg-green-50 border border-green-200 p-4 rounded-lg text-green-800 text-center text-sm">
              Aucun élève à risque identifié
            </div>
          </div>
        </div>

        <!-- Statistiques par classe -->
        <div v-if="bilan.s6_profiles?.by_class?.length > 0">
          <h3 class="text-base font-medium text-gray-900 mb-3">Statistiques par classe</h3>
          <div class="overflow-x-auto">
            <table class="w-full text-sm">
              <thead class="bg-gray-50">
                <tr>
                  <th class="px-4 py-2 text-left font-medium text-gray-900">Classe</th>
                  <th class="px-4 py-2 text-center font-medium text-gray-900">Élèves</th>
                  <th class="px-4 py-2 text-center font-medium text-gray-900">Moyenne</th>
                  <th class="px-4 py-2 text-center font-medium text-gray-900">Écart-type</th>
                  <th class="px-4 py-2 text-center font-medium text-gray-900">Min</th>
                  <th class="px-4 py-2 text-center font-medium text-gray-900">Max</th>
                </tr>
              </thead>
              <tbody>
                <tr
                  v-for="cls in bilan.s6_profiles.by_class"
                  :key="cls.class_name"
                  class="border-t border-gray-200 hover:bg-gray-50"
                >
                  <td class="px-4 py-2 font-medium">{{ cls.class_name }}</td>
                  <td class="px-4 py-2 text-center">{{ cls.n_students }}</td>
                  <td class="px-4 py-2 text-center">
                    <span :class="getRateClass(cls.mean * 5)">{{ cls.mean?.toFixed(1) }}/20</span>
                  </td>
                  <td class="px-4 py-2 text-center">{{ cls.std?.toFixed(1) }}</td>
                  <td class="px-4 py-2 text-center">{{ cls.min?.toFixed(1) }}</td>
                  <td class="px-4 py-2 text-center">{{ cls.max?.toFixed(1) }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </section>

      <!-- ── SECTION 7 : Recommandations pédagogiques ── -->
      <section class="bg-white border border-gray-200 rounded-lg p-6">
        <h2 class="text-xl font-semibold text-gray-900 mb-4 flex items-center gap-2">
          <AppIcon name="lightbulb" :size="20" class="text-indigo-600" />
          Recommandations pédagogiques
        </h2>

        <div v-if="bilan.s7_recommendations" class="space-y-5">
          <div class="bg-blue-50 border border-blue-200 rounded-lg p-5">
            <h3 class="text-base font-semibold text-blue-900 mb-3">A — Pour le conseil de classe</h3>
            <div class="prose prose-sm text-blue-800 max-w-none" v-html="renderMarkdown(extractSection(bilan.s7_recommendations, 'A'))"></div>
          </div>

          <div class="bg-green-50 border border-green-200 rounded-lg p-5">
            <h3 class="text-base font-semibold text-green-900 mb-3">B — Pour les collègues de Seconde</h3>
            <div class="prose prose-sm text-green-800 max-w-none" v-html="renderMarkdown(extractSection(bilan.s7_recommendations, 'B'))"></div>
          </div>

          <div class="bg-purple-50 border border-purple-200 rounded-lg p-5">
            <h3 class="text-base font-semibold text-purple-900 mb-3">C — Pour l'équipe pédagogique</h3>
            <div class="prose prose-sm text-purple-800 max-w-none" v-html="renderMarkdown(extractSection(bilan.s7_recommendations, 'C'))"></div>
          </div>

          <!-- Fallback : si extractSection échoue, afficher le texte brut -->
          <details v-if="sectionsNotFound" class="mt-2">
            <summary class="text-xs text-gray-400 cursor-pointer">Afficher le texte complet des recommandations</summary>
            <div class="mt-2 bg-gray-50 rounded-lg p-4 prose prose-sm text-gray-700 max-w-none"
                 v-html="renderMarkdown(bilan.s7_recommendations)">
            </div>
          </details>
        </div>

        <div v-else class="text-gray-500 text-sm">Aucune recommandation disponible</div>
      </section>

    </div>

    <!-- No bilan or not DONE -->
    <div v-else-if="bilan && bilan.status !== 'DONE'" class="text-center py-12">
      <p class="text-gray-600">Le bilan est en cours de génération ou contient une erreur.</p>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useAuthStore } from '../../stores/auth'
import AppIcon from '../../icons/AppIcon.vue'
import { useToast } from '../../composables/useToast'
import { bilanService } from '../../services/bilan'

const route = useRoute()
const authStore = useAuthStore()
const toast = useToast()

const bilan = ref(null)
const isLoading = ref(false)
const error = ref(null)

// ── Helpers statut ────────────────────────────────────────────────

const getStatusClass = (status) => {
  switch (status) {
    case 'DONE': return 'bg-green-100 text-green-800'
    case 'GENERATING': return 'bg-blue-100 text-blue-800'
    case 'ERROR': return 'bg-red-100 text-red-800'
    default: return 'bg-gray-100 text-gray-800'
  }
}

const getStatusText = (status) => {
  switch (status) {
    case 'DONE': return 'Terminé'
    case 'GENERATING': return 'En cours de génération…'
    case 'ERROR': return 'Erreur'
    default: return status ?? 'Inconnu'
  }
}

const formatDate = (dateString) => {
  if (!dateString) return ''
  return new Date(dateString).toLocaleString('fr-FR', {
    day: '2-digit', month: '2-digit', year: 'numeric',
    hour: '2-digit', minute: '2-digit'
  })
}

// ── Distribution rows config ──────────────────────────────────────

const distributionRows = [
  { label: 'Très bien (≥16)', key: 'tb', color: 'bg-green-500', textColor: 'text-green-700' },
  { label: 'Bien (14–15)', key: 'b', color: 'bg-lime-500', textColor: 'text-lime-700' },
  { label: 'Assez bien (12–13)', key: 'ab', color: 'bg-yellow-400', textColor: 'text-yellow-700' },
  { label: 'Passable (10–11)', key: 'p', color: 'bg-orange-400', textColor: 'text-orange-700' },
  { label: 'Insuffisant (<10)', key: 'insuffisant', color: 'bg-red-500', textColor: 'text-red-700' },
]

const distBarWidth = (count) => {
  const total = bilan.value?.s1_stats?.n_copies || 1
  return `${Math.round((count ?? 0) / total * 100)}%`
}

// ── Coloration taux ───────────────────────────────────────────────

const getRateClass = (rate) => {
  if (rate >= 70) return 'text-green-600 font-semibold'
  if (rate >= 40) return 'text-orange-500 font-semibold'
  return 'text-red-600 font-semibold'
}

const getSignalClass = (rate) => {
  if (rate >= 70) return 'bg-green-100 text-green-800'
  if (rate >= 40) return 'bg-orange-100 text-orange-800'
  return 'bg-red-100 text-red-800'
}

const getSignalText = (rate) => {
  if (rate >= 70) return '✓ Bon'
  if (rate >= 40) return '⚠ Fragile'
  return '✗ Faible'
}

const getCompetenceBarClass = (rate) => {
  if (rate >= 70) return 'bg-green-600'
  if (rate >= 40) return 'bg-orange-500'
  return 'bg-red-500'
}

const getCorrectorProfileClass = (severity) => {
  switch (severity) {
    case 'calibré': return 'bg-green-100 text-green-800'
    case 'sévère': return 'bg-blue-100 text-blue-800'
    case 'indulgent': return 'bg-orange-100 text-orange-800'
    default: return 'bg-gray-100 text-gray-800'
  }
}

// ── Severity badges (metadata strong_signals) ─────────────────────

const getSeverityClass = (severity) => {
  switch (severity) {
    case 'high': return 'bg-red-50 border-red-200 text-red-800'
    case 'medium': return 'bg-orange-50 border-orange-200 text-orange-800'
    case 'low': return 'bg-blue-50 border-blue-200 text-blue-800'
    default: return 'bg-gray-50 border-gray-200 text-gray-800'
  }
}

// ── Questions Top / Flop ──────────────────────────────────────────

const getTopQuestions = (count) => {
  if (!bilan.value?.s3_questions?.length) return []
  return [...bilan.value.s3_questions]
    .sort((a, b) => (b.success_rate ?? 0) - (a.success_rate ?? 0))
    .slice(0, count)
}

const getFlopQuestions = (count) => {
  if (!bilan.value?.s3_questions?.length) return []
  return [...bilan.value.s3_questions]
    .sort((a, b) => (a.success_rate ?? 0) - (b.success_rate ?? 0))
    .slice(0, count)
}

// ── At-risk scores helper ─────────────────────────────────────────

const formatScore = (p1, p2) => {
  if (p1 == null && p2 == null) return 'N/A'
  return ((p1 ?? 0) + (p2 ?? 0)).toFixed(1)
}

// ── Markdown renderer (light, sans dépendance) ───────────────────

const renderMarkdown = (text) => {
  if (!text || typeof text !== 'string') return ''
  const html = text
    // Escape HTML first
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    // Headers ### ## #
    .replace(/^\s*#{3}\s+(.+)$/gm, '<h4 class="font-semibold mt-3 mb-1">$1</h4>')
    .replace(/^\s*#{2}\s+(.+)$/gm, '<h3 class="font-semibold text-base mt-4 mb-2">$1</h3>')
    .replace(/^\s*#{1}\s+(.+)$/gm, '<h2 class="font-bold text-lg mt-4 mb-2">$1</h2>')
    // Horizontal rules
    .replace(/^\s*---\s*$/gm, '<hr class="my-3 border-gray-200" />')
    // Bold **text** and *text*
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.+?)\*/g, '<em>$1</em>')
    // Bullet lists
    .replace(/^\s*[-•]\s+(.+)$/gm, '<li class="ml-4 list-disc">$1</li>')
    // Numbered lists
    .replace(/^\s*\d+\.\s+(.+)$/gm, '<li class="ml-4 list-decimal">$1</li>')
    // Paragraphs: double newline
    .replace(/\n{2,}/g, '</p><p class="mt-2">')
    // Single newline
    .replace(/\n/g, '<br>')
  return `<p>${html}</p>`
}

// ── Section extractor pour s7_recommendations ────────────────────

const extractSection = (text, section) => {
  if (!text || typeof text !== 'string') return ''

  // Preferred stable delimiters: [A] ... [/A]
  const startTag = `[${section}]`
  const endTag = `[/${section}]`
  const start = text.indexOf(startTag)
  if (start !== -1) {
    const end = text.indexOf(endTag, start + startTag.length)
    if (end !== -1) {
      return text.slice(start + startTag.length, end).trim()
    }
  }

  const lines = text.split('\n')
  // Match patterns: "**A —", "### A —", "A —", "A -", "A –", "A:", "A.", "A)"
  const startRe = new RegExp(`^\\s*(?:\\*{1,2})?(?:#{1,3}\\s*)?\\b${section}\\b\\s*[–—\\-:.)]`, 'i')
  // Next section header: any of A/B/C followed by a delimiter
  const nextRe = /^\s*(?:\*{1,2})?(?:#{1,3}\s*)?\b[A-C]\b\s*[–—\-:.)]/i

  const startIdx = lines.findIndex(l => startRe.test(l))
  if (startIdx === -1) {
    // Section not found — return empty (will show full text fallback)
    return ''
  }

  const endIdx = lines.findIndex((l, i) => i > startIdx && nextRe.test(l))
  // Include any content that might be on the same line as the header
  const headerLine = lines[startIdx] || ''
  const inline = headerLine.replace(startRe, '').trim()
  const bodyLines = lines.slice(startIdx + 1, endIdx === -1 ? undefined : endIdx)
  return [inline, ...bodyLines]
    .filter(Boolean)
    .join('\n')
    .trim()
}

// Détecter si les sections ne sont pas trouvées pour afficher le fallback
const sectionsNotFound = computed(() => {
  if (!bilan.value?.s7_recommendations) return false
  return (
    !extractSection(bilan.value.s7_recommendations, 'A') &&
    !extractSection(bilan.value.s7_recommendations, 'B') &&
    !extractSection(bilan.value.s7_recommendations, 'C')
  )
})

// ── Fetch ─────────────────────────────────────────────────────────

const fetchBilan = async () => {
  try {
    isLoading.value = true
    error.value = null

    const response = await bilanService.get(route.params.id)
    // L'API retourne { report: {...}, data: {...} }
    // On aplatit les deux niveaux pour un accès direct dans le template
    bilan.value = {
      ...(response.report || {}),
      ...(response.data  || {}),
    }
  } catch (err) {
    console.error('Error fetching bilan:', err)
    error.value = err.response?.status === 404
      ? 'Bilan non trouvé'
      : 'Erreur lors du chargement du bilan'
  } finally {
    isLoading.value = false
  }
}

const downloadPDF = async () => {
  try {
    const response = await bilanService.downloadPDF(route.params.id)
    const blob = new Blob([response.data], { type: 'application/pdf' })
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `bilan_dnb_${route.params.id}.pdf`
    document.body.appendChild(a)
    a.click()
    window.URL.revokeObjectURL(url)
    document.body.removeChild(a)
    toast.success('PDF téléchargé')
  } catch (err) {
    console.error('Error downloading PDF:', err)
    toast.error('Erreur lors du téléchargement du PDF')
  }
}

onMounted(() => {
  fetchBilan()
})
</script>
