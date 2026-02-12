<template>
  <header class="bg-white/95 backdrop-blur-sm border-b border-borderSoft sticky top-0 z-50">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
      <div class="flex justify-between h-16">
        <!-- Logo & Branding -->
        <div class="flex items-center">
          <router-link
            to="/"
            class="flex-shrink-0 flex items-center gap-3"
          >
            <div class="w-8 h-8 bg-primary-700 text-white flex items-center justify-center rounded-lg font-bold text-lg">
              K
            </div>
            <span class="font-bold text-xl text-primary-900 tracking-tight">KORRIGO <span class="text-primary-500 font-medium">PMF</span></span>
          </router-link>
        </div>

        <!-- Desktop Navigation -->
        <nav class="hidden md:flex items-center space-x-6">
          <router-link
            to="/"
            class="text-gray-600 hover:text-primary-700 font-medium transition"
          >
            Accueil
          </router-link>
          <router-link
            to="/guide-enseignant"
            class="text-gray-600 hover:text-primary-700 font-medium transition"
          >
            Guide Enseignant
          </router-link>
          <router-link
            to="/guide-eleve"
            class="text-gray-600 hover:text-primary-700 font-medium transition"
          >
            Guide Élève
          </router-link>
          <router-link
            to="/direction"
            class="text-gray-600 hover:text-primary-700 font-medium transition"
          >
            Conformité
          </router-link>
        </nav>

        <!-- CTA / Auth -->
        <div class="hidden md:flex items-center space-x-3 relative">
          <button
            class="inline-flex items-center gap-2 bg-primary-700 text-white px-5 py-2 rounded-lg hover:bg-primary-800 transition-colors font-medium text-sm shadow-sm"
            @click="isLoginDropdownOpen = !isLoginDropdownOpen"
            @blur="closeDropdown"
          >
            <LogIn class="w-4 h-4" />
            Connexion
            <ChevronDown class="w-3.5 h-3.5" :class="{ 'rotate-180': isLoginDropdownOpen }" />
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
                to="/teacher/login"
                class="flex items-center gap-3 px-4 py-2.5 text-sm text-gray-700 hover:bg-primary-50 hover:text-primary-700 transition-colors"
              >
                <PenTool class="w-4 h-4 text-primary-500" />
                Enseignant
              </router-link>
              <router-link
                to="/admin/login"
                class="flex items-center gap-3 px-4 py-2.5 text-sm text-gray-700 hover:bg-primary-50 hover:text-primary-700 transition-colors"
              >
                <Settings class="w-4 h-4 text-purple-500" />
                Administration
              </router-link>
              <div class="border-t border-gray-100 my-1" />
              <router-link
                to="/student/login"
                class="flex items-center gap-3 px-4 py-2.5 text-sm text-gray-700 hover:bg-primary-50 hover:text-primary-700 transition-colors"
              >
                <GraduationCap class="w-4 h-4 text-green-500" />
                Élève
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
            <svg
              class="h-6 w-6"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                v-if="!isMobileMenuOpen"
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M4 6h16M4 12h16M4 18h16"
              />
              <path
                v-else
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
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
          to="/"
          class="block px-3 py-2 rounded-md text-base font-medium text-gray-700 hover:text-primary-700 hover:bg-gray-50"
        >
          Accueil
        </router-link>
        <router-link
          to="/guide-enseignant"
          class="block px-3 py-2 rounded-md text-base font-medium text-gray-700 hover:text-primary-700 hover:bg-gray-50"
        >
          Guide Enseignant
        </router-link>
        <router-link
          to="/guide-eleve"
          class="block px-3 py-2 rounded-md text-base font-medium text-gray-700 hover:text-primary-700 hover:bg-gray-50"
        >
          Guide Élève
        </router-link>
        <router-link
          to="/direction"
          class="block px-3 py-2 rounded-md text-base font-medium text-gray-700 hover:text-primary-700 hover:bg-gray-50"
        >
          Conformité
        </router-link>
        <div class="border-t border-gray-100 pt-3 mt-3 space-y-1">
          <span class="block px-3 py-1 text-xs font-semibold text-gray-400 uppercase tracking-wider">Connexion</span>
          <router-link
            to="/teacher/login"
            class="flex items-center gap-2 px-3 py-2 rounded-md text-base font-medium text-gray-700 hover:text-primary-700 hover:bg-gray-50"
          >
            <PenTool class="w-4 h-4 text-primary-500" />
            Enseignant
          </router-link>
          <router-link
            to="/admin/login"
            class="flex items-center gap-2 px-3 py-2 rounded-md text-base font-medium text-gray-700 hover:text-primary-700 hover:bg-gray-50"
          >
            <Settings class="w-4 h-4 text-purple-500" />
            Administration
          </router-link>
          <router-link
            to="/student/login"
            class="flex items-center gap-2 px-3 py-2 rounded-md text-base font-medium text-gray-700 hover:text-primary-700 hover:bg-gray-50"
          >
            <GraduationCap class="w-4 h-4 text-green-500" />
            Élève
          </router-link>
        </div>
      </div>
    </div>
  </header>
</template>

<script setup>
import { ref } from 'vue'
import { LogIn, ChevronDown, PenTool, Settings, GraduationCap } from 'lucide-vue-next'

const isMobileMenuOpen = ref(false)
const isLoginDropdownOpen = ref(false)

function closeDropdown() {
  setTimeout(() => { isLoginDropdownOpen.value = false }, 150)
}
</script>
