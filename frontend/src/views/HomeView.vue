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
          <AppIcon
            name="security"
            :size="16"
          />
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
            <AppIcon
              name="login"
              :size="20"
            />
            Connexion
          </router-link>
          <a
            href="#architecture"
            class="inline-flex items-center justify-center gap-2 bg-white/10 text-white border border-white/20 px-8 py-3.5 rounded-lg font-semibold hover:bg-white/20 transition-all duration-200 backdrop-blur-sm"
          >
            <AppIcon
              name="layers"
              :size="20"
            />
            Découvrir l'architecture
          </a>
        </div>
      </div>
    </section>

    <!-- ============ STATS BAND ============ -->
    <section class="relative z-20 -mt-14">
      <div class="max-w-6xl mx-auto px-6">
        <div class="bg-white rounded-2xl shadow-xl border border-borderSoft grid grid-cols-2 md:grid-cols-5 divide-x divide-borderSoft">
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

    <!-- ============ GARANTIES DE TRANSPARENCE ============ -->
    <section class="py-20 bg-gradient-to-b from-green-50 to-white border-t border-green-100">
      <div class="max-w-5xl mx-auto px-6">
        <div class="text-center mb-12">
          <div class="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-green-100 text-green-800 text-sm font-medium mb-4 border border-green-200">
            <AppIcon
              name="security"
              :size="16"
            />
            Garanties du processus de correction
          </div>
          <h2 class="text-3xl font-bold text-neutralDark mb-3">
            Transparence et intégrité
          </h2>
          <p class="text-gray-500 max-w-2xl mx-auto">
            Chaque élève voit ces garanties affichées sur son portail de consultation.
          </p>
        </div>
        <div class="grid md:grid-cols-2 lg:grid-cols-3 gap-5">
          <div
            v-for="guarantee in guarantees"
            :key="guarantee.title"
            class="bg-white border border-green-200 rounded-xl p-5 flex gap-4 items-start hover:shadow-md transition-shadow"
          >
            <div class="w-10 h-10 rounded-lg bg-green-100 flex items-center justify-center flex-shrink-0">
              <AppIcon
                :name="guarantee.icon"
                :size="20"
                class="text-green-700"
              />
            </div>
            <div>
              <h3 class="font-semibold text-neutralDark text-sm mb-1">
                {{ guarantee.title }}
              </h3>
              <p class="text-xs text-gray-500 leading-relaxed">
                {{ guarantee.desc }}
              </p>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- ============ WORKFLOW DIAGRAM ============ -->
    <section class="py-24 bg-gray-50 border-t border-gray-100">
      <div class="max-w-7xl mx-auto px-6">
        <div class="text-center mb-12">
          <h2 class="text-3xl font-bold text-neutralDark mb-3">
            Workflow complet en 9 étapes
          </h2>
          <p class="text-gray-500 max-w-2xl mx-auto">
            Du scan des copies papier à la consultation par les élèves, un processus entièrement numérique, sécurisé et assisté par IA.
          </p>
        </div>
        <WorkflowDiagram />
      </div>
    </section>

    <!-- ============ CYCLE DE VIE ============ -->
    <section class="py-24 bg-white border-t border-gray-100">
      <div class="max-w-7xl mx-auto px-6">
        <div class="text-center mb-12">
          <h2 class="text-3xl font-bold text-neutralDark mb-3">
            Machine d'états d'une copie
          </h2>
          <p class="text-gray-500 max-w-2xl mx-auto">
            Chaque copie passe par 5 statuts stricts avec verrouillage pessimiste, autosave et anonymisation automatique.
          </p>
        </div>
        <CopyLifecycleDiagram />
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
            Fonctionnalités avancées
          </h2>
          <p class="text-gray-500 max-w-2xl mx-auto">
            Des outils de pointe validés par les enseignants du Lycée Pierre Mendès France.
          </p>
        </div>
        <div class="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
          <FeatureCard
            icon="eye-off"
            accent="purple"
            title="Anonymisation stricte"
            text="Numéro d'anonymat séquentiel unique par copie. L'en-tête manuscrite est masquée dynamiquement pendant la phase de correction."
          />
          <FeatureCard
            icon="sparkles"
            accent="green"
            title="Korrigo AI (Bilans)"
            text="Génération de résumés pédagogiques personnalisés via LLM local Ollama (qwen2.5:32b). Analyse les points forts et axes de progrès."
          />
          <FeatureCard
            icon="bar-chart-3"
            accent="primary"
            title="Barème hiérarchique"
            text="Structure Exercice → Question → Sous-question. Saisie rapide au clavier, calcul automatique du total et export Pronote direct."
          />
          <FeatureCard
            icon="lightbulb"
            accent="orange"
            title="Banque de commentaires"
            text="123 suggestions officielles et banque personnelle auto-alimentée. Auto-complétion intelligente par fréquence."
          />
          <FeatureCard
            icon="identification"
            accent="blue"
            title="OCR Vision GPT-4o-mini"
            text="Reconnaissance ultra-précise de l'écriture manuscrite cursive pour l'identification automatique des copies scannées."
          />
          <FeatureCard
            icon="lock"
            accent="red"
            title="Verrouillage & Autosave"
            text="Verrouillage pessimiste avec heartbeat 30s et autosave dual-layer (localStorage 300ms + serveur 2s) : zéro perte de données."
          />
        </div>
      </div>
    </section>

    <!-- ============ ARCHITECTURE TECHNIQUE ============ -->
    <section
      id="architecture"
      class="py-24 bg-white border-t border-gray-100"
    >
      <div class="max-w-7xl mx-auto px-6">
        <div class="text-center mb-12">
          <div class="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-blue-50 text-blue-700 text-sm font-medium mb-4 border border-blue-200">
            <AppIcon
              name="server"
              :size="16"
            />
            Stack Technique
          </div>
          <h2 class="text-3xl font-bold text-neutralDark mb-3">
            Architecture technique
          </h2>
          <p class="text-gray-500 max-w-2xl mx-auto">
            Une architecture conteneurisée, souveraine et scalable, déployée sur un serveur dédié Hetzner.
          </p>
        </div>
        <ArchitectureDiagram />

        <!-- Tech Stack Pills -->
        <div class="mt-12 flex flex-wrap justify-center gap-3">
          <span
            v-for="tech in techStack"
            :key="tech.name"
            class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium border"
            :class="tech.class"
          >
            {{ tech.name }}
          </span>
        </div>
      </div>
    </section>

    <!-- ============ AVANTAGES ============ -->
    <section class="py-24 bg-gray-50 border-t border-gray-100">
      <div class="max-w-7xl mx-auto px-6">
        <div class="text-center mb-14">
          <h2 class="text-3xl font-bold text-neutralDark mb-3">
            Pourquoi Korrigo PMF ?
          </h2>
          <p class="text-gray-500 max-w-2xl mx-auto">
            Une solution souveraine, hébergée localement et conçue pour l'excellence pédagogique.
          </p>
        </div>
        <div class="grid md:grid-cols-3 gap-8">
          <div class="text-center">
            <div class="w-14 h-14 bg-blue-50 text-blue-600 rounded-2xl flex items-center justify-center mx-auto mb-4">
              <AppIcon
                name="book"
                :size="28"
              />
            </div>
            <h3 class="font-semibold text-neutralDark text-lg mb-2">
              Pédagogiques
            </h3>
            <ul class="text-sm text-gray-500 leading-relaxed space-y-1.5 text-left max-w-xs mx-auto">
              <li>Retour ultra-détaillé via Bilans IA personnalisés</li>
              <li>Analyse croisée des résultats par compétence</li>
              <li>Élèves absents consultent leurs copies en ligne</li>
              <li>Traçabilité complète de l'évolution des notes</li>
            </ul>
          </div>
          <div class="text-center">
            <div class="w-14 h-14 bg-green-50 text-green-600 rounded-2xl flex items-center justify-center mx-auto mb-4">
              <AppIcon
                name="clock"
                :size="28"
              />
            </div>
            <h3 class="font-semibold text-neutralDark text-lg mb-2">
              Organisationnels
            </h3>
            <ul class="text-sm text-gray-500 leading-relaxed space-y-1.5 text-left max-w-xs mx-auto">
              <li>Correction délocalisée (domicile, établissement)</li>
              <li>Zéro logistique papier (collecte, stockage, armoires)</li>
              <li>Import/Export Pronote en 2 clics</li>
              <li>Supervision temps-réel de l'avancement</li>
            </ul>
          </div>
          <div class="text-center">
            <div class="w-14 h-14 bg-purple-50 text-purple-600 rounded-2xl flex items-center justify-center mx-auto mb-4">
              <AppIcon
                name="security"
                :size="28"
              />
            </div>
            <h3 class="font-semibold text-neutralDark text-lg mb-2">
              Souveraineté
            </h3>
            <ul class="text-sm text-gray-500 leading-relaxed space-y-1.5 text-left max-w-xs mx-auto">
              <li>Hébergement dédié (Hetzner, Allemagne — UE)</li>
              <li>LLM Local (Ollama) : aucune donnée pédagogique sortante</li>
              <li>Conformité RGPD et référentiel CNIL Éducation</li>
              <li>Code source auditable et maîtrisé</li>
            </ul>
          </div>
        </div>
      </div>
    </section>

    <!-- ============ SÉCURITÉ & CONFORMITÉ ============ -->
    <section class="py-24 bg-white border-t border-gray-100">
      <div class="max-w-5xl mx-auto px-6 text-center">
        <div class="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-green-50 text-green-700 text-sm font-medium mb-6 border border-green-200">
          <AppIcon
            name="security"
            :size="16"
          />
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
              <AppIcon
                name="success"
                :size="24"
              />
            </div>
            <span class="font-medium text-gray-900 text-sm">RGPD conforme</span>
            <span class="text-xs text-gray-400 mt-0.5">Art. 6, 15–22, 28, 30</span>
          </div>
          <div class="flex flex-col items-center">
            <div class="w-12 h-12 bg-blue-50 text-blue-600 rounded-xl flex items-center justify-center mb-3">
              <AppIcon
                name="lock"
                :size="24"
              />
            </div>
            <span class="font-medium text-gray-900 text-sm">HTTPS + TLS 1.2+</span>
            <span class="text-xs text-gray-400 mt-0.5">HSTS, CSP, CSRF</span>
          </div>
          <div class="flex flex-col items-center">
            <div class="w-12 h-12 bg-purple-50 text-purple-600 rounded-xl flex items-center justify-center mb-3">
              <AppIcon
                name="list"
                :size="24"
              />
            </div>
            <span class="font-medium text-gray-900 text-sm">Audit complet</span>
            <span class="text-xs text-gray-400 mt-0.5">GradingEvent · AuditLog</span>
          </div>
          <div class="flex flex-col items-center">
            <div class="w-12 h-12 bg-orange-50 text-orange-600 rounded-xl flex items-center justify-center mb-3">
              <AppIcon
                name="key-round"
                :size="24"
              />
            </div>
            <span class="font-medium text-gray-900 text-sm">RBAC strict</span>
            <span class="text-xs text-gray-400 mt-0.5">Admin · Enseignant · Élève</span>
          </div>
        </div>

        <div class="bg-gray-50 rounded-xl border border-borderSoft p-6 text-left max-w-3xl mx-auto mb-10">
          <h3 class="font-semibold text-neutralDark mb-3">
            Conservation des données
          </h3>
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-3 text-sm">
            <div class="flex justify-between border-b border-gray-200 pb-2">
              <span class="text-gray-600">Copies numérisées</span>
              <span class="font-medium text-gray-800">1 an après examen</span>
            </div>
            <div class="flex justify-between border-b border-gray-200 pb-2">
              <span class="text-gray-600">Notes et annotations</span>
              <span class="font-medium text-gray-800">1 an après examen</span>
            </div>
            <div class="flex justify-between border-b border-gray-200 pb-2">
              <span class="text-gray-600">Données élèves</span>
              <span class="font-medium text-gray-800">Fin scolarité + 1 an</span>
            </div>
            <div class="flex justify-between border-b border-gray-200 pb-2">
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
          <AppIcon
            name="arrow-right"
            :size="16"
          />
        </router-link>
      </div>
    </section>

    <!-- ============ FOOTER ============ -->
    <section class="py-10 bg-gray-900 text-gray-400">
      <div class="max-w-5xl mx-auto px-6 text-center text-sm">
        <p class="mb-2">
          <strong class="text-white">Korrigo PMF</strong> — Plateforme de Correction Numérique
        </p>
        <p class="mb-1">
          Lycée Pierre Mendès France de Tunis · Labo Maths ERT
        </p>
        <p class="text-gray-500">
          Dernière activité : {{ lastActivityLabel }} · Développé par Alaeddine BEN RHOUMA
        </p>
      </div>
    </section>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import api from '../services/api'
import FeatureCard from '../components/FeatureCard.vue'
import ArchitectureDiagram from '../components/ArchitectureDiagram.vue'
import CopyLifecycleDiagram from '../components/CopyLifecycleDiagram.vue'
import WorkflowDiagram from '../components/WorkflowDiagram.vue'
import AppIcon from '../icons/AppIcon.vue'

const platformData = ref(null)
const statsLoading = ref(true)

const stats = ref([
  { value: '—', label: 'Copies finalisées' },
  { value: '—', label: 'Correcteurs' },
  { value: '—', label: 'Élèves' },
  { value: '—', label: 'Annotations posées' },
  { value: '—', label: 'Taux finalisation' },
])

onMounted(async () => {
  try {
    const { data } = await api.get('/platform-stats/')
    platformData.value = data
    stats.value = [
      { value: String(data.copies_finalized), label: 'Copies finalisées' },
      { value: String(data.correctors_count), label: 'Correcteurs' },
      { value: String(data.students_count), label: 'Élèves' },
      { value: String(data.annotations_count), label: 'Annotations posées' },
      { value: data.finalization_rate + '%', label: 'Taux finalisation' },
    ]
  } catch (e) {
    console.warn('Platform stats unavailable:', e.message)
  } finally {
    statsLoading.value = false
  }
})

const lastActivityLabel = computed(() => {
  if (!platformData.value?.last_activity) return '—'
  const d = new Date(platformData.value.last_activity)
  return d.toLocaleDateString('fr-FR', { day: 'numeric', month: 'long', year: 'numeric' })
})

const roles = [
  {
    icon: 'settings',
    bg: 'bg-red-50', color: 'text-red-600',
    title: 'Administration',
    desc: 'Création d\'examens, gestion des utilisateurs, import élèves CSV, dispatch correcteurs, exports Pronote et supervision globale.',
  },
  {
    icon: 'edit',
    bg: 'bg-primary-50', color: 'text-primary-600',
    title: 'Enseignants',
    desc: 'Correction numérique avec annotations vectorielles, notation par barème structuré, autosave dual-layer et finalisation des copies.',
  },
  {
    icon: 'briefcase',
    bg: 'bg-orange-50', color: 'text-orange-600',
    title: 'Secrétariat',
    desc: 'Identification des copies scannées : validation OCR GPT-4o-mini, association copie-élève et gestion des fascicules.',
  },
  {
    icon: 'student',
    bg: 'bg-green-50', color: 'text-green-600',
    title: 'Élèves',
    desc: 'Consultation sécurisée des copies corrigées avec bannière de transparence, téléchargement PDF et bilan IA personnalisé.',
  },
]

const guarantees = [
  {
    icon: 'user-check',
    title: 'Correction humaine uniquement',
    desc: 'Aucune intelligence artificielle n\'est utilisée pour noter les copies ou prendre des décisions pédagogiques.',
  },
  {
    icon: 'eye-off',
    title: 'Copies anonymisées',
    desc: 'Les copies sont anonymisées avant correction. Le correcteur ne voit jamais le nom de l\'élève.',
  },
  {
    icon: 'shuffle',
    title: 'Répartition aléatoire',
    desc: 'Les copies sont réparties aléatoirement entre les correcteurs par un algorithme round-robin équitable.',
  },
  {
    icon: 'file-check',
    title: 'Contrôle complémentaire',
    desc: 'Un contrôle complémentaire est effectué après finalisation pour garantir la cohérence des corrections.',
  },
  {
    icon: 'sparkles',
    title: 'IA uniquement pour l\'aide',
    desc: 'L\'IA n\'est utilisée que pour l\'OCR (identification) et les bilans pédagogiques personnalisés, jamais pour la notation.',
  },
  {
    icon: 'list',
    title: 'Traçabilité complète',
    desc: 'Chaque action (verrouillage, annotation, score, finalisation) est enregistrée dans un journal d\'audit horodaté.',
  },
]

const techStack = [
  { name: 'Vue.js 3', class: 'bg-green-50 text-green-700 border-green-200' },
  { name: 'Pinia', class: 'bg-yellow-50 text-yellow-700 border-yellow-200' },
  { name: 'TailwindCSS 4', class: 'bg-cyan-50 text-cyan-700 border-cyan-200' },
  { name: 'Vite 5', class: 'bg-purple-50 text-purple-700 border-purple-200' },
  { name: 'Django 4.2', class: 'bg-green-50 text-green-800 border-green-300' },
  { name: 'DRF', class: 'bg-red-50 text-red-700 border-red-200' },
  { name: 'Celery', class: 'bg-lime-50 text-lime-700 border-lime-200' },
  { name: 'PostgreSQL 15', class: 'bg-blue-50 text-blue-700 border-blue-200' },
  { name: 'Redis', class: 'bg-red-50 text-red-600 border-red-200' },
  { name: 'Ollama (qwen2.5:32b)', class: 'bg-violet-50 text-violet-700 border-violet-200' },
  { name: 'GPT-4o-mini (OCR)', class: 'bg-emerald-50 text-emerald-700 border-emerald-200' },
  { name: 'Docker Compose', class: 'bg-sky-50 text-sky-700 border-sky-200' },
  { name: 'Nginx + TLS', class: 'bg-gray-100 text-gray-700 border-gray-300' },
]
</script>
