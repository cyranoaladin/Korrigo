<template>
  <div>
    <!-- ============ HERO ============ -->
    <section class="bg-gradient-to-br from-primary-900 via-primary-800 to-primary-700 text-white pt-20 pb-28 relative overflow-hidden">
      <div class="absolute inset-0 overflow-hidden">
        <div class="absolute -top-1/2 -right-1/4 w-[800px] h-[800px] rounded-full bg-primary-600 opacity-10 blur-3xl" />
        <div class="absolute -bottom-1/3 -left-1/4 w-[600px] h-[600px] rounded-full bg-primary-500 opacity-[0.07] blur-3xl" />
      </div>

      <div class="max-w-7xl mx-auto px-6 relative z-10 text-center">
        <span class="inline-flex items-center gap-2 py-1.5 px-4 rounded-full bg-white/10 border border-white/20 text-primary-100 text-sm font-medium mb-8 backdrop-blur-sm">
          <ShieldCheck class="w-4 h-4" />
          Plateforme Académique Officielle
        </span>
        <h1 class="text-4xl md:text-5xl lg:text-6xl font-bold mb-6 tracking-tight leading-[1.1]">
          Correction numérique<br>
          <span class="text-primary-300">sécurisée</span> d'examens
        </h1>
        <p class="text-lg md:text-xl text-primary-200 mb-10 max-w-2xl mx-auto leading-relaxed">
          Anonymisation des copies · Barème structuré · Banque de suggestions ·&nbsp;Traçabilité complète<br class="hidden md:block">
          <span class="text-primary-300 font-medium">Lycée Pierre Mendès France de Tunis</span>
        </p>
        <div class="flex flex-col sm:flex-row justify-center gap-4">
          <router-link
            to="/teacher/login"
            class="inline-flex items-center justify-center gap-2 bg-white text-primary-900 px-8 py-3.5 rounded-lg font-semibold shadow-lg hover:bg-gray-50 hover:shadow-xl transition-all duration-200 hover:-translate-y-0.5"
          >
            <LogIn class="w-5 h-5" />
            Espace Enseignant
          </router-link>
          <router-link
            to="/student/login"
            class="inline-flex items-center justify-center gap-2 bg-primary-600/50 border border-primary-400/30 px-8 py-3.5 rounded-lg font-semibold text-white hover:bg-primary-500/50 transition-all duration-200 backdrop-blur-sm hover:-translate-y-0.5"
          >
            <GraduationCap class="w-5 h-5" />
            Espace Élève
          </router-link>
        </div>
      </div>
    </section>

    <!-- ============ STATS BAND ============ -->
    <section class="relative z-20 -mt-14">
      <div class="max-w-5xl mx-auto px-6">
        <div class="bg-white rounded-2xl shadow-xl border border-borderSoft grid grid-cols-2 md:grid-cols-4 divide-x divide-borderSoft">
          <div
            v-for="stat in stats"
            :key="stat.label"
            class="flex flex-col items-center py-8 px-4"
          >
            <span class="text-3xl font-bold text-primary-700">{{ stat.value }}</span>
            <span class="text-sm text-gray-500 mt-1">{{ stat.label }}</span>
          </div>
        </div>
      </div>
    </section>

    <!-- ============ COMMENT ÇA MARCHE ============ -->
    <section class="py-24 bg-white">
      <div class="max-w-7xl mx-auto px-6">
        <div class="text-center mb-16">
          <h2 class="text-3xl font-bold text-neutralDark mb-3">Comment ça marche</h2>
          <p class="text-gray-500 max-w-xl mx-auto">De l'upload du sujet à l'export des notes, un processus entièrement numérique et sécurisé.</p>
        </div>
        <div class="grid grid-cols-2 md:grid-cols-4 gap-8 md:gap-12">
          <StepCard
            :step="1"
            title="Upload & Split"
            text="Le coordinateur importe le PDF scanné. Le système découpe chaque copie automatiquement."
            :icon="Upload"
            accent="blue"
          />
          <StepCard
            :step="2"
            title="Anonymisation"
            text="Chaque copie reçoit un code anonyme (ex: 0F8E-042). L'en-tête est masquée."
            :icon="EyeOff"
            accent="purple"
          />
          <StepCard
            :step="3"
            title="Correction"
            text="Le correcteur annote, note par exercice et utilise la banque de suggestions officielle."
            :icon="PenTool"
            accent="primary"
          />
          <StepCard
            :step="4"
            title="Export & Restitution"
            text="Les notes sont exportées en CSV. Les copies annotées sont restituées aux élèves."
            :icon="Download"
            accent="green"
          />
        </div>
      </div>
    </section>

    <!-- ============ FONCTIONNALITÉS ============ -->
    <section
      id="fonctionnalites"
      class="py-24 bg-gray-50 border-t border-gray-100"
    >
      <div class="max-w-7xl mx-auto px-6">
        <div class="text-center mb-16">
          <h2 class="text-3xl font-bold text-neutralDark mb-3">Fonctionnalités</h2>
          <p class="text-gray-500 max-w-xl mx-auto">Des outils conçus pour les enseignants, validés par l'usage en conditions réelles.</p>
        </div>
        <div class="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
          <FeatureCard
            :icon="EyeOff"
            accent="purple"
            title="Anonymisation automatique"
            text="Code unique par copie (format XXXX-NNN). L'en-tête contenant l'identité est masquée pour le correcteur."
          />
          <FeatureCard
            :icon="PenTool"
            accent="blue"
            title="Annotation sur canvas"
            text="Outils de dessin vectoriel : texte, coche, croix, surlignage. Annotation directement sur la copie dans le navigateur."
          />
          <FeatureCard
            :icon="BarChart3"
            accent="primary"
            title="Barème structuré"
            text="Notation hiérarchique par exercice et sous-question. Calcul automatique des totaux avec le barème officiel."
          />
          <FeatureCard
            :icon="Lightbulb"
            accent="orange"
            title="Banque de suggestions"
            text="123 annotations officielles issues du barème et du corrigé. Banque personnelle auto-alimentée par l'usage."
          />
          <FeatureCard
            :icon="ScrollText"
            accent="green"
            title="Journal d'audit"
            text="Toutes les actions sont journalisées : accès, verrouillage, annotation, notation. Traçabilité complète."
          />
          <FeatureCard
            :icon="FileDown"
            accent="red"
            title="Export CSV"
            text="Génération automatique des fichiers de notes compatibles avec les logiciels de gestion de l'établissement."
          />
        </div>
      </div>
    </section>

    <!-- ============ SÉCURITÉ & CONFORMITÉ ============ -->
    <section class="py-24 bg-white border-t border-gray-100">
      <div class="max-w-4xl mx-auto px-6 text-center">
        <div class="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-green-50 text-green-700 text-sm font-medium mb-6 border border-green-200">
          <ShieldCheck class="w-4 h-4" />
          Privacy by Design
        </div>
        <h2 class="text-3xl font-bold text-neutralDark mb-4">
          Conformité & Protection des Données
        </h2>
        <p class="text-gray-500 text-lg leading-relaxed mb-12 max-w-2xl mx-auto">
          Korrigo PMF est conçu pour garantir la confidentialité des données académiques.
          Toutes les actions sont journalisées, les données sont hébergées localement et les accès sont contrôlés par rôle.
        </p>
        
        <div class="grid grid-cols-2 md:grid-cols-4 gap-8 mb-12">
          <div class="flex flex-col items-center">
            <div class="w-12 h-12 bg-green-50 text-green-600 rounded-xl flex items-center justify-center mb-3">
              <CheckCircle class="w-6 h-6" />
            </div>
            <span class="font-medium text-gray-900 text-sm">Conforme RGPD</span>
          </div>
          <div class="flex flex-col items-center">
            <div class="w-12 h-12 bg-blue-50 text-blue-600 rounded-xl flex items-center justify-center mb-3">
              <Lock class="w-6 h-6" />
            </div>
            <span class="font-medium text-gray-900 text-sm">Stockage chiffré</span>
          </div>
          <div class="flex flex-col items-center">
            <div class="w-12 h-12 bg-purple-50 text-purple-600 rounded-xl flex items-center justify-center mb-3">
              <ClipboardList class="w-6 h-6" />
            </div>
            <span class="font-medium text-gray-900 text-sm">Journal d'audit</span>
          </div>
          <div class="flex flex-col items-center">
            <div class="w-12 h-12 bg-orange-50 text-orange-600 rounded-xl flex items-center justify-center mb-3">
              <KeyRound class="w-6 h-6" />
            </div>
            <span class="font-medium text-gray-900 text-sm">Accès par rôle</span>
          </div>
        </div>

        <router-link
          to="/direction"
          class="inline-flex items-center gap-2 text-primary-700 font-semibold hover:text-primary-800 transition-colors"
        >
          Consulter le dossier complet
          <ArrowRight class="w-4 h-4" />
        </router-link>
      </div>
    </section>
  </div>
</template>

<script setup>
import FeatureCard from '../components/FeatureCard.vue'
import StepCard from '../components/StepCard.vue'
import {
  ShieldCheck, LogIn, GraduationCap,
  Upload, EyeOff, PenTool, Download,
  BarChart3, Lightbulb, ScrollText, FileDown,
  CheckCircle, Lock, ClipboardList, KeyRound, ArrowRight,
} from 'lucide-vue-next'

const stats = [
  { value: '209', label: 'Copies traitées' },
  { value: '8', label: 'Correcteurs' },
  { value: '123', label: 'Suggestions officielles' },
  { value: '100%', label: 'Anonymisées' },
]
</script>
