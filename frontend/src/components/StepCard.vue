<template>
  <div class="flex flex-col items-center text-center group">
    <div class="relative mb-4">
      <div
        class="w-16 h-16 rounded-2xl flex items-center justify-center shadow-sm transition-all duration-300 group-hover:shadow-md group-hover:scale-105"
        :class="iconBgClass"
      >
        <component
          :is="icon"
          class="w-7 h-7"
          :class="iconColorClass"
        />
      </div>
      <span
        class="absolute -top-2 -right-2 w-7 h-7 rounded-full bg-primary-700 text-white text-xs font-bold flex items-center justify-center shadow"
      >
        {{ step }}
      </span>
    </div>
    <h3 class="font-semibold text-neutralDark mb-1">
      {{ title }}
    </h3>
    <p class="text-sm text-gray-500 leading-relaxed max-w-[200px]">
      {{ text }}
    </p>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  step: { type: [Number, String], required: true },
  title: { type: String, required: true },
  text: { type: String, default: '' },
  icon: { type: [Object, Function], required: true },
  accent: { type: String, default: 'primary' }
})

const colorMap = {
  primary: { bg: 'bg-primary-50', text: 'text-primary-600' },
  green: { bg: 'bg-green-50', text: 'text-green-600' },
  purple: { bg: 'bg-purple-50', text: 'text-purple-600' },
  orange: { bg: 'bg-orange-50', text: 'text-orange-600' },
  blue: { bg: 'bg-blue-50', text: 'text-blue-600' },
}

const iconBgClass = computed(() => colorMap[props.accent]?.bg || colorMap.primary.bg)
const iconColorClass = computed(() => colorMap[props.accent]?.text || colorMap.primary.text)
</script>
