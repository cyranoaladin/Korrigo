<!-- ⚠️ RAPPORT ARCHIVÉ — BAC BLANC MATHS 2026 (BB_J1/BB_J2)
     Données hardcodées. Voir StatsReport.vue pour le contexte complet. -->
<template>
  <div>
    <!-- Top 15 -->
    <div class="bg-white rounded-xl border border-gray-200 shadow-sm mb-8 overflow-hidden">
      <div class="px-5 py-4 border-b border-gray-100">
        <h2 class="text-lg font-semibold text-neutralDark flex items-center gap-2">
          <AppIcon
            name="trophy"
            :size="20"
            class="text-amber-500"
          />
          Top 15 Global
        </h2>
      </div>
      <div class="overflow-x-auto">
        <table class="w-full text-sm">
          <thead>
            <tr class="bg-gray-50">
              <th class="text-center px-3 py-2.5 font-medium text-gray-600 w-12">
                #
              </th>
              <th class="text-left px-3 py-2.5 font-medium text-gray-600">
                Élève
              </th>
              <th class="text-center px-3 py-2.5 font-medium text-gray-600">
                Classe
              </th>
              <th
                v-if="hasGroups"
                class="text-center px-3 py-2.5 font-medium text-gray-600"
              >
                Groupe
              </th>
              <th class="text-center px-3 py-2.5 font-medium text-gray-600">
                Exam
              </th>
              <th class="text-center px-3 py-2.5 font-medium text-gray-600">
                Note
              </th>
              <th class="text-left px-3 py-2.5 font-medium text-gray-600">
                Correcteur
              </th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="s in top15"
              :key="s.rank + s.name"
              class="border-t border-gray-100 hover:bg-amber-50/30"
            >
              <td class="px-3 py-2.5 text-center">
                <AppIcon
                  v-if="s.rank === 1"
                  name="trophy"
                  :size="18"
                  class="text-amber-500"
                />
                <AppIcon
                  v-else-if="s.rank === 2"
                  name="award"
                  :size="18"
                  class="text-gray-400"
                />
                <span
                  v-else
                  class="text-gray-500 font-medium"
                >{{ s.rank }}</span>
              </td>
              <td class="px-3 py-2.5 font-semibold text-gray-800">
                {{ s.name }}
              </td>
              <td class="px-3 py-2.5 text-center text-gray-600">
                {{ s.classe }}
              </td>
              <td
                v-if="hasGroups"
                class="px-3 py-2.5 text-center text-gray-600"
              >
                {{ s.groupe }}
              </td>
              <td class="px-3 py-2.5 text-center">
                <span
                  class="text-xs px-2 py-0.5 rounded-full font-medium"
                  :class="s.exam === 'BB_J1' ? 'bg-green-100 text-green-800' : 'bg-purple-100 text-purple-800'"
                >{{ s.exam }}</span>
              </td>
              <td
                class="px-3 py-2.5 text-center font-bold text-lg"
                :class="s.note >= 20 ? 'text-amber-600' : 'text-green-700'"
              >
                {{ s.note }}
              </td>
              <td class="px-3 py-2.5 text-gray-600 text-xs">
                {{ s.corrector }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Bottom 11 -->
    <div class="bg-white rounded-xl border border-red-200 shadow-sm overflow-hidden">
      <div class="px-5 py-4 border-b border-red-100 bg-red-50">
        <h2 class="text-lg font-semibold text-red-800 flex items-center gap-2">
          <AppIcon
            name="alert"
            :size="20"
            class="text-red-600"
          />
          Élèves en Grande Difficulté (&lt; 5/20)
        </h2>
      </div>
      <div class="overflow-x-auto">
        <table class="w-full text-sm">
          <thead>
            <tr class="bg-red-50/50">
              <th class="text-center px-3 py-2.5 font-medium text-red-700 w-12">
                #
              </th>
              <th class="text-left px-3 py-2.5 font-medium text-red-700">
                Élève
              </th>
              <th class="text-center px-3 py-2.5 font-medium text-red-700">
                Classe
              </th>
              <th
                v-if="hasGroups"
                class="text-center px-3 py-2.5 font-medium text-red-700"
              >
                Groupe
              </th>
              <th class="text-center px-3 py-2.5 font-medium text-red-700">
                Exam
              </th>
              <th class="text-center px-3 py-2.5 font-medium text-red-700">
                Note
              </th>
              <th class="text-left px-3 py-2.5 font-medium text-red-700">
                Correcteur
              </th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="s in bottom11"
              :key="s.rank + s.name"
              class="border-t border-red-100 hover:bg-red-50/30"
            >
              <td class="px-3 py-2.5 text-center text-gray-500">
                {{ s.rank }}
              </td>
              <td class="px-3 py-2.5 font-semibold text-gray-800">
                <span
                  v-if="s.cheatFlag === 'exact'"
                  class="inline-flex items-center mr-1"
                  title="Suspicion de triche QCM (pattern exact)"
                >
                  <AppIcon
                    name="alert"
                    :size="14"
                    class="text-red-600"
                  />
                </span>
                <span
                  v-else-if="s.cheatFlag === 'near'"
                  class="inline-flex items-center mr-1"
                  title="Pattern QCM proche de la triche (4/5)"
                >
                  <AppIcon
                    name="alert"
                    :size="14"
                    class="text-amber-500"
                  />
                </span>
                {{ s.name }}
              </td>
              <td class="px-3 py-2.5 text-center text-gray-600">
                {{ s.classe }}
              </td>
              <td
                v-if="hasGroups"
                class="px-3 py-2.5 text-center text-gray-600"
              >
                {{ s.groupe }}
              </td>
              <td class="px-3 py-2.5 text-center">
                <span
                  class="text-xs px-2 py-0.5 rounded-full font-medium"
                  :class="s.exam === 'BB_J1' ? 'bg-green-100 text-green-800' : 'bg-purple-100 text-purple-800'"
                >{{ s.exam }}</span>
              </td>
              <td class="px-3 py-2.5 text-center font-bold text-red-700">
                {{ s.note }}
              </td>
              <td class="px-3 py-2.5 text-gray-600 text-xs">
                {{ s.corrector }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import AppIcon from '../../icons/AppIcon.vue'

const props = defineProps({
  data: { type: Object, required: true },
  hasGroups: { type: Boolean, default: true }
})

const top15 = computed(() => props.data?.top15 || [])
const bottom11 = computed(() => props.data?.bottom11 || [])
</script>
