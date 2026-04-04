<script setup>
import { resolveIcon } from '../icons/iconRegistry'

const props = defineProps({
  icon: { type: String, default: '' },
  size: { type: [Number, String], default: 24 },
  strokeWidth: { type: [Number, String], default: 2 },
})
</script>

<template>
  <component
    :is="resolveIcon(icon)"
    :size="Number(size)"
    :stroke-width="Number(strokeWidth)"
    aria-hidden="true"
  />
</template>
