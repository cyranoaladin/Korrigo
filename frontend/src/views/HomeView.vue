<template>
  <div>
    <!-- ============ HERO ============ -->
    <section class="bg-gradient-to-br from-primary-900 via-primary-800 to-primary-700 text-white pt-20 pb-28 relative overflow-hidden">
      <div class="absolute inset-0 overflow-hidden">
        <div class="absolute -top-1/2 -right-1/4 w-[800px] h-[800px] rounded-full bg-primary-600 opacity-10 blur-3xl" />
        <div class="absolute -bottom-1/3 -left-1/4 w-[600px] h-[600px] rounded-full bg-primary-500 opacity-[0.07] blur-3xl" />
      </div>

      <div class="max-w-7xl mx-auto px-6 relative z-10 text-center">
        <img
          src="/images/logo_korrigo_pmf.svg"
          alt="Korrigo PMF"
          class="h-20 md:h-24 mx-auto mb-8 drop-shadow-lg"
        >
        <span class="inline-flex items-center gap-2 py-1.5 px-4 rounded-full bg-white/10 border border-white/20 text-primary-100 text-sm font-medium mb-8 backdrop-blur-sm">
          <ShieldCheck class="w-4 h-4" />
          Plateforme de Correction Numérique — Conforme RGPD
        </span>
        <h1 class="text-4xl md:text-5xl lg:text-6xl font-bold mb-6 tracking-tight leading-[1.1]">
          Correction numérique<br>
          <span class="text-primary-300">anonymisée</span> et sécurisée
        </h1>
        <p class="text-lg md:text-xl text-primary-200 mb-4 max-w-3xl mx-auto leading-relaxed">
          De la numérisation des copies scannées à l'export vers Pronote, Korrigo PMF transforme
          le processus de correction papier en un workflow numérique moderne, traçable et&nbsp;conforme&nbsp;RGPD.
        </p>
        <p class="text-primary-300 font-medium mb-10">
          Lycée Pierre Mendès France de Tunis · Labo Maths ERT
        </p>
        <div class="flex flex-col sm:flex-row justify-center gap-4">
          <router-link
            to="/"
            class="inline-flex items-center justify-center gap-2 bg-white text-primary-900 px-8 py-3.5 rounded-lg font-semibold shadow-lg hover:bg-gray-50 hover:shadow-xl transition-all duration-200 hover:-translate-y-0.5"
          >
            <LogIn class="w-5 h-5" />
            Connexion
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

    <!-- ============ POUR QUI ? ============ -->
    <section class="py-20 bg-white">
      <div class="max-w-7xl mx-auto px-6">
        <div class="text-center mb-14">
          <h2 class="text-3xl font-bold text-neutralDark mb-3">
            Conçu pour tout l'établissement
          </h2>
          <p class="text-gray-500 max-w-2xl mx-auto">
            Chaque profil dispose d'un espace dédié adapté à son rôle dans le processus de correction.
          </p>
        </div>
        <div class="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
          <div
            v-for="role in roles"
            :key="role.title"
            class="bg-white border border-borderSoft rounded-xl p-6 hover:shadow-lg transition-shadow"
          >
            <div
              class="w-11 h-11 rounded-lg flex items-center justify-center mb-4"
              :class="role.bg"
            >
              <component
                :is="role.icon"
                class="w-5 h-5"
                :class="role.color"
              />
            </div>
            <h3 class="font-semibold text-neutralDark mb-2">
              {{ role.title }}
            </h3>
            <p class="text-sm text-gray-500 leading-relaxed">
              {{ role.desc }}
            </p>
          </div>
        </div>
      </div>
    </section>

    <!-- ============ COMMENT ÇA MARCHE ============ -->
    <section class="py-24 bg-gray-50 border-t border-gray-100">
      <div class="max-w-7xl mx-auto px-6">
        <div class="text-center mb-16">
          <h2 class="text-3xl font-bold text-neutralDark mb-3">
            Le workflow complet
          </h2>
          <p class="text-gray-500 max-w-2xl mx-auto">
            Du scan des copies papier à la consultation par les élèves, un processus en 5 étapes entièrement numérique et sécurisé.
          </p>
        </div>
        <div class="grid grid-cols-2 md:grid-cols-5 gap-6 md:gap-8">
          <StepCard
            :step="1"
            title="Numérisation"
            text="L'admin importe le PDF scanné (batch A3 ou copies individuelles). Le système découpe et rasterise chaque fascicule."
            :icon="Upload"
            accent="blue"
          />
          <StepCard
            :step="2"
            title="Identification"
            text="L'OCR détecte les noms manuscrits. Le secrétariat valide ou corrige, puis associe chaque copie à un élève."
            :icon="ScanSearch"
            accent="orange"
          />
          <StepCard
            :step="3"
            title="Anonymisation"
            text="Un numéro d'anonymat unique est généré. L'en-tête est masquée : le correcteur ne voit jamais le nom de l'élève."
            :icon="EyeOff"
            accent="purple"
          />
          <StepCard
            :step="4"
            title="Correction"
            text="L'enseignant annote sur le PDF, note par question selon le barème structuré et utilise la banque de suggestions."
            :icon="PenTool"
            accent="primary"
          />
          <StepCard
            :step="5"
            title="Export & Restitution"
            text="Les PDF finaux sont générés, les notes exportées en CSV pour Pronote, et les élèves consultent leurs copies en ligne."
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
          <h2 class="text-3xl font-bold text-neutralDark mb-3">
            Fonctionnalités clés
          </h2>
          <p class="text-gray-500 max-w-2xl mx-auto">
            Des outils pensés pour l'enseignement, validés en conditions réelles sur des examens blancs et contrôles continus.
          </p>
        </div>
        <div class="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
          <FeatureCard
            :icon="EyeOff"
            accent="purple"
            title="Anonymisation stricte"
            text="Numéro d'anonymat séquentiel unique par copie. L'en-tête manuscrite est masquée : l'enseignant ne voit jamais le nom de l'élève pendant la correction."
          />
          <FeatureCard
            :icon="PenTool"
            accent="blue"
            title="4 types d'annotations"
            text="Commentaire pédagogique, surlignage, signalement d'erreur et bonus. Chaque annotation peut porter des points positifs ou négatifs."
          />
          <FeatureCard
            :icon="BarChart3"
            accent="primary"
            title="Barème hiérarchique"
            text="Structure Exercice → Question → Sous-question avec points. Cases à cocher ou saisie libre. Calcul automatique du total sans erreur."
          />
          <FeatureCard
            :icon="Lightbulb"
            accent="orange"
            title="Banque de commentaires"
            text="Banque officielle de 123 suggestions issues du barème. Banque personnelle auto-alimentée : auto-complétion par fréquence d'usage."
          />
          <FeatureCard
            :icon="ScanSearch"
            accent="green"
            title="OCR et identification"
            text="Reconnaissance optique des noms manuscrits sur les en-têtes. Validation humaine par le secrétariat avant liaison copie-élève."
          />
          <FeatureCard
            :icon="FileDown"
            accent="red"
            title="Export Pronote & PDF"
            text="Export CSV des notes compatible Pronote. Génération de PDF finaux annotés avec nom de l'élève réaffiché pour consultation."
          />
        </div>
      </div>
    </section>

    <!-- ============ AVANTAGES ============ -->
    <section class="py-24 bg-white border-t border-gray-100">
      <div class="max-w-7xl mx-auto px-6">
        <div class="text-center mb-14">
          <h2 class="text-3xl font-bold text-neutralDark mb-3">
            Pourquoi Korrigo PMF ?
          </h2>
          <p class="text-gray-500 max-w-2xl mx-auto">
            Des bénéfices concrets pour l'ensemble de la communauté éducative.
          </p>
        </div>
        <div class="grid md:grid-cols-3 gap-8">
          <div class="text-center">
            <div class="w-14 h-14 bg-blue-50 text-blue-600 rounded-2xl flex items-center justify-center mx-auto mb-4">
              <BookOpen class="w-7 h-7" />
            </div>
            <h3 class="font-semibold text-neutralDark text-lg mb-2">
              Pédagogiques
            </h3>
            <ul class="text-sm text-gray-500 leading-relaxed space-y-1.5 text-left max-w-xs mx-auto">
              <li>Retour détaillé : annotations claires et pérennes</li>
              <li>Traçabilité complète de chaque action</li>
              <li>Élèves absents consultent leurs copies en ligne</li>
              <li>Historique de correction consultable à tout moment</li>
            </ul>
          </div>
          <div class="text-center">
            <div class="w-14 h-14 bg-green-50 text-green-600 rounded-2xl flex items-center justify-center mx-auto mb-4">
              <Clock class="w-7 h-7" />
            </div>
            <h3 class="font-semibold text-neutralDark text-lg mb-2">
              Organisationnels
            </h3>
            <ul class="text-sm text-gray-500 leading-relaxed space-y-1.5 text-left max-w-xs mx-auto">
              <li>Correction depuis n'importe où (domicile, salle des profs)</li>
              <li>Réduction du temps de distribution et collecte</li>
              <li>Fin des armoires de copies papier</li>
              <li>Export direct vers Pronote en un clic</li>
            </ul>
          </div>
          <div class="text-center">
            <div class="w-14 h-14 bg-purple-50 text-purple-600 rounded-2xl flex items-center justify-center mx-auto mb-4">
              <ShieldCheck class="w-7 h-7" />
            </div>
            <h3 class="font-semibold text-neutralDark text-lg mb-2">
              Sécuritaires
            </h3>
            <ul class="text-sm text-gray-500 leading-relaxed space-y-1.5 text-left max-w-xs mx-auto">
              <li>Conformité RGPD et référentiel CNIL Éducation</li>
              <li>Anonymisation garantie pendant la correction</li>
              <li>Journal d'audit immuable de chaque action</li>
              <li>Données hébergées localement en France</li>
            </ul>
          </div>
        </div>
      </div>
    </section>

    <!-- ============ SÉCURITÉ & CONFORMITÉ ============ -->
    <section class="py-24 bg-gray-50 border-t border-gray-100">
      <div class="max-w-5xl mx-auto px-6 text-center">
        <div class="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-green-50 text-green-700 text-sm font-medium mb-6 border border-green-200">
          <ShieldCheck class="w-4 h-4" />
          Privacy by Design · Référentiel CNIL Éducation 2020
        </div>
        <h2 class="text-3xl font-bold text-neutralDark mb-4">
          Conformité & Protection des Données
        </h2>
        <p class="text-gray-500 text-lg leading-relaxed mb-12 max-w-3xl mx-auto">
          Le traitement des données repose sur la <strong class="text-gray-700">mission d'intérêt public</strong> (Art.&nbsp;6.1.e RGPD, Code de l'Éducation).
          Aucune donnée sensible n'est collectée, aucun transfert hors UE, aucun cookie publicitaire.
        </p>
        
        <div class="grid grid-cols-2 md:grid-cols-4 gap-8 mb-14">
          <div class="flex flex-col items-center">
            <div class="w-12 h-12 bg-green-50 text-green-600 rounded-xl flex items-center justify-center mb-3">
              <CheckCircle class="w-6 h-6" />
            </div>
            <span class="font-medium text-gray-900 text-sm">RGPD conforme</span>
            <span class="text-xs text-gray-400 mt-0.5">Art. 6, 15–22, 28, 30</span>
          </div>
          <div class="flex flex-col items-center">
            <div class="w-12 h-12 bg-blue-50 text-blue-600 rounded-xl flex items-center justify-center mb-3">
              <Lock class="w-6 h-6" />
            </div>
            <span class="font-medium text-gray-900 text-sm">HTTPS + TLS 1.2+</span>
            <span class="text-xs text-gray-400 mt-0.5">HSTS, CSP, CSRF</span>
          </div>
          <div class="flex flex-col items-center">
            <div class="w-12 h-12 bg-purple-50 text-purple-600 rounded-xl flex items-center justify-center mb-3">
              <ClipboardList class="w-6 h-6" />
            </div>
            <span class="font-medium text-gray-900 text-sm">Audit complet</span>
            <span class="text-xs text-gray-400 mt-0.5">Connexions, annotations, exports</span>
          </div>
          <div class="flex flex-col items-center">
            <div class="w-12 h-12 bg-orange-50 text-orange-600 rounded-xl flex items-center justify-center mb-3">
              <KeyRound class="w-6 h-6" />
            </div>
            <span class="font-medium text-gray-900 text-sm">RBAC strict</span>
            <span class="text-xs text-gray-400 mt-0.5">Admin · Enseignant · Élève</span>
          </div>
        </div>

        <div class="bg-white rounded-xl border border-borderSoft p-6 text-left max-w-3xl mx-auto mb-10">
          <h3 class="font-semibold text-neutralDark mb-3">
            Conservation des données
          </h3>
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-3 text-sm">
            <div class="flex justify-between border-b border-gray-100 pb-2">
              <span class="text-gray-600">Copies numérisées</span>
              <span class="font-medium text-gray-800">1 an après examen</span>
            </div>
            <div class="flex justify-between border-b border-gray-100 pb-2">
              <span class="text-gray-600">Notes et annotations</span>
              <span class="font-medium text-gray-800">1 an après examen</span>
            </div>
            <div class="flex justify-between border-b border-gray-100 pb-2">
              <span class="text-gray-600">Données élèves</span>
              <span class="font-medium text-gray-800">Fin scolarité + 1 an</span>
            </div>
            <div class="flex justify-between border-b border-gray-100 pb-2">
              <span class="text-gray-600">Logs d'audit</span>
              <span class="font-medium text-gray-800">6 mois (CNIL)</span>
            </div>
          </div>
        </div>

        <router-link
          to="/korrigo/direction"
          class="inline-flex items-center gap-2 text-primary-700 font-semibold hover:text-primary-800 transition-colors"
        >
          Consulter le dossier complet Direction & Conformité
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
  Upload, EyeOff, PenTool, Download, ScanSearch,
  BarChart3, Lightbulb, FileDown,
  CheckCircle, Lock, ClipboardList, KeyRound, ArrowRight,
  BookOpen, Clock, Settings, Briefcase,
} from 'lucide-vue-next'

const stats = [
  { value: '209', label: 'Copies traitées' },
  { value: '8', label: 'Correcteurs' },
  { value: '123', label: 'Suggestions officielles' },
  { value: '100%', label: 'Anonymisées' },
]

const roles = [
  {
    icon: Settings,
    bg: 'bg-red-50', color: 'text-red-600',
    title: 'Administration',
    desc: 'Création d\'examens, gestion des utilisateurs, import élèves depuis Pronote, exports CSV et supervision globale.',
  },
  {
    icon: PenTool,
    bg: 'bg-primary-50', color: 'text-primary-600',
    title: 'Enseignants',
    desc: 'Correction numérique avec annotations vectorielles, notation par barème structuré et finalisation des copies.',
  },
  {
    icon: Briefcase,
    bg: 'bg-orange-50', color: 'text-orange-600',
    title: 'Secrétariat',
    desc: 'Identification des copies scannées : validation OCR, association copie-élève et gestion des fascicules.',
  },
  {
    icon: GraduationCap,
    bg: 'bg-green-50', color: 'text-green-600',
    title: 'Élèves',
    desc: 'Consultation sécurisée des copies corrigées, téléchargement PDF et accès aux annotations des professeurs.',
  },
]
</script>
