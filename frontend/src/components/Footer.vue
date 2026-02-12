<template>
  <footer class="bg-gray-50 border-t border-borderSoft pt-12 pb-8">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
      <div class="grid grid-cols-1 md:grid-cols-4 gap-8">
        <!-- Brand / Identity -->
        <div class="col-span-1 md:col-span-1">
          <div class="flex items-center gap-2 mb-4">
            <div class="w-7 h-7 bg-primary-800 text-white flex items-center justify-center rounded-lg text-xs font-bold">
              K
            </div>
            <span class="font-bold text-primary-900 tracking-tight">KORRIGO PMF</span>
          </div>
          <p class="text-sm text-gray-500 leading-relaxed">
            Plateforme institutionnelle de correction numérique des examens.
            Sécurisée, traçable et conforme aux standards académiques.
          </p>
        </div>

        <!-- Links Columns -->
        <div>
          <h4 class="font-semibold text-neutralDark mb-4 text-sm uppercase tracking-wider">
            Plateforme
          </h4>
          <ul class="space-y-2.5 text-sm text-gray-600">
            <li>
              <router-link
                to="/"
                class="hover:text-primary-600 transition"
                @click="scrollToFeatures"
              >
                Fonctionnalités
              </router-link>
            </li>
            <li>
              <router-link
                to="/guide-enseignant"
                class="hover:text-primary-600 transition"
              >
                Guide enseignant
              </router-link>
            </li>
            <li>
              <router-link
                to="/guide-eleve"
                class="hover:text-primary-600 transition"
              >
                Guide élève
              </router-link>
            </li>
          </ul>
        </div>
        
        <div>
          <h4 class="font-semibold text-neutralDark mb-4 text-sm uppercase tracking-wider">
            Conformité
          </h4>
          <ul class="space-y-2.5 text-sm text-gray-600">
            <li>
              <router-link
                to="/direction"
                class="hover:text-primary-600 transition"
              >
                RGPD & Protection des données
              </router-link>
            </li>
            <li>
              <router-link
                to="/direction"
                class="hover:text-primary-600 transition"
              >
                Architecture & Sécurité
              </router-link>
            </li>
          </ul>
        </div>

        <div>
          <h4 class="font-semibold text-neutralDark mb-4 text-sm uppercase tracking-wider">
            Contact
          </h4>
          <ul class="space-y-2.5 text-sm text-gray-600">
            <li class="flex items-center gap-2">
              <Mail class="w-3.5 h-3.5 text-gray-400 flex-shrink-0" />
              <a
                href="mailto:labo.maths@ert.tn"
                class="hover:text-primary-600 transition"
              >
                labo.maths@ert.tn
              </a>
            </li>
            <li class="flex items-center gap-2">
              <Mail class="w-3.5 h-3.5 text-gray-400 flex-shrink-0" />
              <a
                href="mailto:alaeddine.benrhouma@ert.tn"
                class="hover:text-primary-600 transition"
              >
                alaeddine.benrhouma@ert.tn
              </a>
            </li>
          </ul>
        </div>
      </div>

      <div class="mt-10 pt-6 border-t border-borderSoft flex flex-col md:flex-row justify-between items-center text-xs text-gray-400 gap-2">
        <p>&copy; 2026 Korrigo PMF — Lycée Pierre Mendès France de Tunis. Usage interne.</p>
        <div class="flex items-center gap-4">
          <span class="flex items-center gap-1">
            <Server class="w-3 h-3" />
            Hébergement local sécurisé
          </span>
        </div>
      </div>
    </div>
  </footer>
</template>

<script setup>
import { Mail, Server } from 'lucide-vue-next'
import { nextTick } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()

function scrollToFeatures() {
  nextTick(() => {
    const el = document.getElementById('fonctionnalites')
    if (el) el.scrollIntoView({ behavior: 'smooth' })
  })
}
</script>
