<template>
  <div>
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
</template>

<script setup>
import { computed } from 'vue'
import { MessageSquare, PenTool, FileText, Brain, AlertTriangle } from 'lucide-vue-next'

const props = defineProps({
  data: { type: Object, required: true }
})

const qualityKpis = computed(() => {
  if (!props.data) return []
  const q = props.data.quality
  return [
    { label: 'Remarques pédagogiques', value: q.remarks_count.toLocaleString('fr-FR'), sub: `${q.copies_with_remarks}/${q.total_copies} copies`, icon: MessageSquare, color: 'text-blue-600' },
    { label: 'Annotations graphiques', value: q.annotations_count.toLocaleString('fr-FR'), sub: `${q.copies_with_annotations}/${q.total_copies} copies`, icon: PenTool, color: 'text-purple-600' },
    { label: 'Appréciations globales', value: q.appreciation_rate, sub: `${q.copies_with_appreciation}/${q.total_copies} copies`, icon: FileText, color: 'text-green-600' },
    { label: 'Bilans LLM générés', value: String(q.llm_count), sub: `${q.llm_pct}% des copies`, icon: Brain, color: 'text-amber-600' }
  ]
})

const appreciationTags = computed(() => props.data?.quality?.appreciation_tags || [])

const themes = [
  { label: 'Manque de justification / rédaction', freq: 'Très fréquent', dotColor: 'bg-red-500', tagClass: 'bg-red-100 text-red-800' },
  { label: 'Erreurs de calcul évitables', freq: 'Fréquent', dotColor: 'bg-orange-500', tagClass: 'bg-orange-100 text-orange-800' },
  { label: 'Méthodes classiques non maîtrisées', freq: 'Fréquent', dotColor: 'bg-orange-500', tagClass: 'bg-orange-100 text-orange-800' },
  { label: 'Trop rapide, saute des étapes', freq: 'Occasionnel', dotColor: 'bg-yellow-500', tagClass: 'bg-yellow-100 text-yellow-800' },
  { label: 'Copie vide ou quasi-vide', freq: 'Rare', dotColor: 'bg-gray-400', tagClass: 'bg-gray-100 text-gray-700' },
  { label: 'Suspicion de fraude (QCM)', freq: '1 cas', dotColor: 'bg-red-600', tagClass: 'bg-red-100 text-red-800' }
]
</script>
