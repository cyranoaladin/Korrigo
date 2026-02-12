<template>
  <section
    class="max-w-4xl mx-auto px-6 py-12 md:py-16"
  >
    <h1
      v-if="title"
      class="text-3xl font-semibold mb-8 text-neutralDark border-b pb-4 border-borderSoft"
    >
      {{ title }}
    </h1>
    <div class="space-y-4">
      <slot />
    </div>
  </section>
</template>

<script setup>
defineProps({ 
  title: {
    type: String,
    default: '' 
  }
})
</script>
