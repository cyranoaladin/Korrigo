<script setup>
import { useToast } from '../composables/useToast'
import AppIcon from '../icons/AppIcon.vue'

const { toasts, remove } = useToast()

const typeStyles = {
  success: 'bg-emerald-50 border-emerald-300 text-emerald-800',
  error: 'bg-red-50 border-red-300 text-red-800',
  warning: 'bg-amber-50 border-amber-300 text-amber-800',
  info: 'bg-blue-50 border-blue-300 text-blue-800',
}

const iconMap = {
  success: 'check',
  error: 'x-mark',
  warning: 'warning',
  info: 'info',
}

const iconBg = {
  success: 'bg-emerald-500',
  error: 'bg-red-500',
  warning: 'bg-amber-500',
  info: 'bg-blue-500',
}
</script>

<template>
  <Teleport to="body">
    <div
      class="fixed top-4 right-4 z-[9999] flex flex-col gap-2 pointer-events-none"
      style="max-width: 380px;"
    >
      <TransitionGroup
        enter-active-class="transition-all duration-300 ease-out"
        enter-from-class="opacity-0 translate-x-8"
        enter-to-class="opacity-100 translate-x-0"
        leave-active-class="transition-all duration-200 ease-in"
        leave-from-class="opacity-100 translate-x-0"
        leave-to-class="opacity-0 translate-x-8"
      >
        <div
          v-for="toast in toasts"
          :key="toast.id"
          class="pointer-events-auto flex items-start gap-3 px-4 py-3 rounded-lg border shadow-lg backdrop-blur-sm"
          :class="typeStyles[toast.type] || typeStyles.info"
        >
          <span
            class="flex-shrink-0 w-5 h-5 rounded-full flex items-center justify-center text-white"
            :class="iconBg[toast.type] || iconBg.info"
          >
            <AppIcon
              :name="iconMap[toast.type] || 'info'"
              :size="12"
            />
          </span>
          <span class="text-sm font-medium flex-1">{{ toast.message }}</span>
          <button
            class="flex-shrink-0 p-0.5 rounded hover:bg-black/10 transition-colors"
            @click="remove(toast.id)"
          >
            <AppIcon
              name="close"
              :size="14"
            />
          </button>
        </div>
      </TransitionGroup>
    </div>
  </Teleport>
</template>
