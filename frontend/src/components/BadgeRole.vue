<template>
  <span 
    class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium"
    :class="classes"
  >
    {{ label }}
  </span>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  role: {
    type: String,
    required: true,
    validator: (value) => ['admin', 'teacher', 'student'].includes(value)
  }
})

const classes = computed(() => {
  switch (props.role) {
    case 'admin':
      return 'bg-purple-100 text-purple-800'
    case 'teacher':
      return 'bg-primary-100 text-primary-800'
    case 'student':
      return 'bg-green-100 text-green-800'
    default:
      return 'bg-gray-100 text-gray-800'
  }
})

const label = computed(() => {
  switch (props.role) {
    case 'admin': return 'Administrateur'
    case 'teacher': return 'Enseignant'
    case 'student': return 'Élève'
    default: return 'Utilisateur'
  }
})
</script>
