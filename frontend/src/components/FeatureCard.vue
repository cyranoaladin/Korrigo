<template>
  <div class="group border border-borderSoft rounded-xl p-6 bg-white shadow-sm hover:shadow-lg hover:border-primary-200 transition-all duration-300">
    <div
      v-if="icon"
      class="w-12 h-12 rounded-lg flex items-center justify-center mb-4 transition-colors duration-300"
      :class="iconBgClass"
    >
      <component
        :is="icon"
        class="w-6 h-6"
        :class="iconColorClass"
      />
    </div>
    <h3 class="font-semibold text-lg mb-2 text-neutralDark group-hover:text-primary-700 transition-colors">
      {{ title }}
    </h3>
    <p class="text-gray-500 leading-relaxed text-sm">
      {{ text }}
    </p>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  title: {
    type: String,
    default: ''
  },
  text: {
    type: String,
    default: ''
  },
  icon: {
    type: [Object, Function],
    default: null
  },
  accent: {
    type: String,
    default: 'primary',
    validator: (v) => ['primary', 'green', 'purple', 'orange', 'blue', 'red'].includes(v)
  }
})

const colorMap = {
  primary: { bg: 'bg-primary-50 group-hover:bg-primary-100', text: 'text-primary-600' },
  green: { bg: 'bg-green-50 group-hover:bg-green-100', text: 'text-green-600' },
  purple: { bg: 'bg-purple-50 group-hover:bg-purple-100', text: 'text-purple-600' },
  orange: { bg: 'bg-orange-50 group-hover:bg-orange-100', text: 'text-orange-600' },
  blue: { bg: 'bg-blue-50 group-hover:bg-blue-100', text: 'text-blue-600' },
  red: { bg: 'bg-red-50 group-hover:bg-red-100', text: 'text-red-600' },
}

const iconBgClass = computed(() => colorMap[props.accent]?.bg || colorMap.primary.bg)
const iconColorClass = computed(() => colorMap[props.accent]?.text || colorMap.primary.text)
</script>
