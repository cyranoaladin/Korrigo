<script setup>
import { computed } from 'vue'
import { resolveIcon } from './iconRegistry'

const props = defineProps({
  /** Semantic icon name (e.g. 'student', 'logout', 'chevron-down') */
  name: {
    type: String,
    default: '',
  },
  /** Icon size in pixels */
  size: {
    type: [Number, String],
    default: 24,
  },
  /** Stroke width */
  strokeWidth: {
    type: [Number, String],
    default: 2,
  },
})

const iconComponent = computed(() => resolveIcon(props.name))
</script>

<template>
  <component
    :is="iconComponent"
    :size="Number(size)"
    :stroke-width="Number(strokeWidth)"
    aria-hidden="true"
  />
</template>
