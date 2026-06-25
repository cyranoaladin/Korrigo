<template>
  <header class="bg-white/95 backdrop-blur-sm border-b border-borderSoft sticky top-0 z-50">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
      <div class="flex justify-between h-16">
        <!-- Logo & Branding -->
        <div class="flex items-center">
          <router-link
            to="/korrigo"
            class="flex-shrink-0 flex items-center gap-3"
          >
            <img
              src="/images/logo_korrigo_pmf.svg"
              alt="Korrigo PMF"
              class="h-9 w-auto"
            >
          </router-link>
        </div>

        <!-- Desktop Navigation -->
        <nav class="hidden md:flex items-center space-x-6">
          <router-link
            v-for="route in KORRIGO_PUBLIC_ROUTES"
            :key="route.key"
            :to="route.path"
            class="text-gray-600 hover:text-primary-700 font-medium transition"
          >
            {{ route.label }}
          </router-link>
          <router-link
            v-for="code in juryReportCodes"
            :key="code"
            :to="`/korrigo/stats/${code}`"
            class="text-gray-600 hover:text-primary-700 font-medium transition"
          >
            Stats {{ code }}
          </router-link>
        </nav>

        <!-- CTA / Auth -->
        <div class="hidden md:flex items-center space-x-3 relative">
          <button
            class="inline-flex items-center gap-2 bg-primary-700 text-white px-5 py-2 rounded-lg hover:bg-primary-800 transition-colors font-medium text-sm shadow-sm"
            @click.stop="isLoginDropdownOpen = !isLoginDropdownOpen"
          >
            <AppIcon name="login" :size="16" />
            Connexion
            <AppIcon
              name="chevron-down"
              :size="14"
              class="transition-transform duration-200"
              :class="{ 'rotate-180': isLoginDropdownOpen }"
            />
          </button>
          <transition
            enter-active-class="transition duration-150 ease-out"
            enter-from-class="opacity-0 -translate-y-1"
            enter-to-class="opacity-100 translate-y-0"
            leave-active-class="transition duration-100 ease-in"
            leave-from-class="opacity-100 translate-y-0"
            leave-to-class="opacity-0 -translate-y-1"
          >
            <div
              v-if="isLoginDropdownOpen"
              class="absolute right-0 top-full mt-2 w-52 bg-white border border-borderSoft rounded-xl shadow-xl py-2 z-50"
            >
              <router-link
                v-for="link in KORRIGO_LOGIN_LINKS"
                :key="link.to"
                :to="link.to"
                class="flex items-center gap-3 px-4 py-2.5 text-sm text-gray-700 hover:bg-primary-50 hover:text-primary-700 transition-colors"
              >
                <AppIcon :name="link.icon" :size="16" class="text-primary-500" />
                {{ link.label }}
              </router-link>
            </div>
          </transition>
        </div>

        <!-- Mobile menu button -->
        <div class="flex items-center md:hidden">
          <button
            class="text-gray-500 hover:text-gray-700 p-2"
            @click="isMobileMenuOpen = !isMobileMenuOpen"
          >
            <AppIcon
              v-if="!isMobileMenuOpen"
              name="menu"
              :size="24"
            />
            <AppIcon
              v-else
              name="close"
              :size="24"
            />
          </button>
        </div>
      </div>
    </div>

    <!-- Mobile Menu -->
    <div
      v-show="isMobileMenuOpen"
      class="md:hidden border-t border-borderSoft bg-white"
    >
      <div class="px-2 pt-2 pb-3 space-y-1 sm:px-3">
        <router-link
          v-for="route in KORRIGO_PUBLIC_ROUTES"
          :key="route.key"
          :to="route.path"
          class="block px-3 py-2 rounded-md text-base font-medium text-gray-700 hover:text-primary-700 hover:bg-gray-50"
        >
          {{ route.label }}
        </router-link>
        <router-link
          v-for="code in juryReportCodes"
          :key="code"
          :to="`/korrigo/stats/${code}`"
          class="block px-3 py-2 rounded-md text-base font-medium text-gray-700 hover:text-primary-700 hover:bg-gray-50"
        >
          Stats {{ code }}
        </router-link>
        <div class="border-t border-gray-100 pt-3 mt-3 space-y-1">
          <span class="block px-3 py-1 text-xs font-semibold text-gray-400 uppercase tracking-wider">Connexion</span>
          <router-link
            v-for="link in KORRIGO_LOGIN_LINKS"
            :key="link.to"
            :to="link.to"
            class="flex items-center gap-2 px-3 py-2 rounded-md text-base font-medium text-gray-700 hover:text-primary-700 hover:bg-gray-50"
          >
            <AppIcon :name="link.icon" :size="16" class="text-primary-500" />
            {{ link.label }}
          </router-link>
        </div>
      </div>
    </div>
  </header>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useAuthStore } from '../stores/auth'
import AppIcon from '../icons/AppIcon.vue'
import {
  KORRIGO_LOGIN_LINKS,
  KORRIGO_PUBLIC_ROUTES,
} from '../features/korrigo/content/korrigoPublicContent'

const authStore = useAuthStore()
const juryReportCodes = computed(() =>
  authStore.user?.features?.jury_report_exam_codes ?? []
)

const isMobileMenuOpen = ref(false)
const isLoginDropdownOpen = ref(false)

const handleGlobalClick = () => {
  if (isLoginDropdownOpen.value) {
    isLoginDropdownOpen.value = false
  }
}

onMounted(() => {
  window.addEventListener('click', handleGlobalClick)
})

onUnmounted(() => {
  window.removeEventListener('click', handleGlobalClick)
})
</script>
