<template>
  <div class="border-b border-borderSoft last:border-b-0">
    <button
      class="w-full flex justify-between items-center py-4 text-left focus:outline-none focus:text-primary-600 hover:text-primary-600 transition"
      :aria-expanded="isOpen"
      @click="isOpen = !isOpen"
    >
      <span class="font-medium text-lg">{{ title }}</span>
      <span
        class="transform transition-transform duration-200 text-gray-400"
        :class="{ 'rotate-180': isOpen }"
      >
        <svg
          xmlns="http://www.w3.org/2000/svg"
          class="h-5 w-5"
          viewBox="0 0 20 20"
          fill="currentColor"
        >
          <path
            fill-rule="evenodd"
            d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z"
            clip-rule="evenodd"
          />
        </svg>
      </span>
    </button>
    <transition
      enter-active-class="transition duration-200 ease-out"
      enter-from-class="transform scale-95 opacity-0"
      enter-to-class="transform scale-100 opacity-100"
      leave-active-class="transition duration-75 ease-in"
      leave-from-class="transform scale-100 opacity-100"
      leave-to-class="transform scale-95 opacity-0"
    >
      <div
        v-if="isOpen"
        class="pb-6 text-gray-600 leading-relaxed"
      >
        <slot />
      </div>
    </transition>
  </div>
</template>

<script setup>
import { ref } from 'vue'

defineProps({ 
  title: {
    type: String,
    required: true
  }
})

const isOpen = ref(false)
</script>
