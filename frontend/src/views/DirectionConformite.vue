<template>
  <SectionContainer title="Direction & Conformité">
    <!-- TABLEAU DE BORD PLATEFORME (DYNAMIQUE) -->
    <div class="mb-12 bg-gradient-to-r from-primary-50 to-blue-50 rounded-xl border border-primary-200 p-6">
      <h2 class="text-lg font-semibold text-primary-800 mb-4 flex items-center gap-2">
        <AppIcon name="bar-chart-3" :size="20" />
        Tableau de bord plateforme
        <span v-if="statsLoading" class="text-xs font-normal text-gray-400 ml-2">Chargement…</span>
      </h2>
      <div class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
        <div class="bg-white rounded-lg p-3 border border-gray-200 text-center">
          <p class="text-2xl font-bold text-primary-700">{{ pd?.total_exams ?? '—' }}</p>
          <p class="text-xs text-gray-500 mt-1">Examens</p>
        </div>
        <div class="bg-white rounded-lg p-3 border border-gray-200 text-center">
          <p class="text-2xl font-bold text-primary-700">{{ pd?.total_copies ?? '—' }}</p>
          <p class="text-xs text-gray-500 mt-1">Copies</p>
        </div>
        <div class="bg-white rounded-lg p-3 border border-gray-200 text-center">
          <p class="text-2xl font-bold text-green-600">{{ pd?.copies_finalized ?? '—' }}</p>
          <p class="text-xs text-gray-500 mt-1">Finalisées</p>
        </div>
        <div class="bg-white rounded-lg p-3 border border-gray-200 text-center">
          <p class="text-2xl font-bold text-blue-600">{{ pd?.correctors_count ?? '—' }}</p>
          <p class="text-xs text-gray-500 mt-1">Correcteurs</p>
        </div>
        <div class="bg-white rounded-lg p-3 border border-gray-200 text-center">
          <p class="text-2xl font-bold text-orange-600">{{ pd?.students_count ?? '—' }}</p>
          <p class="text-xs text-gray-500 mt-1">Élèves</p>
        </div>
        <div class="bg-white rounded-lg p-3 border border-gray-200 text-center">
          <p class="text-2xl font-bold text-emerald-600">{{ pd?.finalization_rate ?? '—' }}%</p>
          <p class="text-xs text-gray-500 mt-1">Taux finalisation</p>
        </div>
      </div>
      <div v-if="pd?.exam_types?.length" class="mt-4 flex flex-wrap gap-2">
        <span
          v-for="et in pd.exam_types"
          :key="et.name"
          class="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium bg-white border border-gray-200 text-gray-700"
        >
          {{ et.name }} <span class="text-primary-600 font-bold">{{ et.count }}</span>
        </span>
      </div>
      <p v-if="pd?.last_activity" class="text-xs text-gray-400 mt-3">
        Dernière activité : {{ formatDate(pd.last_activity) }}
      </p>
    </div>

    <!-- CONTACTS -->
    <div class="grid md:grid-cols-2 lg:grid-cols-4 gap-6 mb-12">
      <div class="bg-white p-5 rounded-lg border border-borderSoft shadow-sm">
        <AppIcon name="building" :size="20" class="text-primary-600 mb-2" />
        <h3 class="font-semibold text-sm mb-1 text-neutralDark">
          Responsable de Traitement
        </h3>
        <p class="text-sm text-gray-600">
          Proviseur du Lycée Pierre Mendès France de Tunis
        </p>
      </div>
      <div class="bg-white p-5 rounded-lg border border-borderSoft shadow-sm">
        <AppIcon name="compliance" :size="20" class="text-green-600 mb-2" />
        <h3 class="font-semibold text-sm mb-1 text-neutralDark">
          DPO
        </h3>
        <p class="text-sm text-gray-600">
          DPO de l'établissement
        </p>
      </div>
      <div class="bg-white p-5 rounded-lg border border-borderSoft shadow-sm">
        <AppIcon name="code" :size="20" class="text-blue-600 mb-2" />
        <h3 class="font-semibold text-sm mb-1 text-neutralDark">
          Développement
        </h3>
        <p class="text-sm text-gray-600">
          Équipe Labo Maths<br><span class="text-xs text-gray-400">Contact institutionnel</span>
        </p>
      </div>
      <div class="bg-white p-5 rounded-lg border border-borderSoft shadow-sm">
        <AppIcon name="server" :size="20" class="text-orange-600 mb-2" />
        <h3 class="font-semibold text-sm mb-1 text-neutralDark">
          Hébergement
        </h3>
        <p class="text-sm text-gray-600">
          Serveur Local Sécurisé — aucun transfert hors France
        </p>
      </div>
    </div>

    <div class="space-y-10">
      <!-- 1. CADRE JURIDIQUE -->
      <div>
        <h2 class="text-xl font-semibold mb-4 text-primary-800 border-b border-gray-100 pb-2">
          1. Cadre Juridique
        </h2>
        <p class="text-gray-600 mb-4 leading-relaxed">
          Korrigo PMF traite des données personnelles d'élèves (dont des mineurs), conformément au RGPD et à la législation française.
        </p>
        <div class="overflow-x-auto mb-3">
          <table class="w-full text-sm border-collapse">
            <thead>
              <tr class="bg-gray-50">
                <th class="text-left px-3 py-2 border-b font-medium text-gray-700">
                  Texte
                </th><th class="text-left px-3 py-2 border-b font-medium text-gray-700">
                  Référence
                </th>
              </tr>
            </thead>
            <tbody class="text-gray-600">
              <tr>
                <td class="px-3 py-1.5 border-b font-medium">
                  RGPD
                </td><td class="px-3 py-1.5 border-b">
                  Règlement (UE) 2016/679
                </td>
              </tr>
              <tr>
                <td class="px-3 py-1.5 border-b font-medium">
                  Loi Informatique et Libertés
                </td><td class="px-3 py-1.5 border-b">
                  Loi n° 78-17 (modifiée 2018)
                </td>
              </tr>
              <tr>
                <td class="px-3 py-1.5 border-b font-medium">
                  Code de l'Éducation
                </td><td class="px-3 py-1.5 border-b">
                  Art. L. 111-1 et suivants
                </td>
              </tr>
              <tr>
                <td class="px-3 py-1.5 font-medium">
                  Référentiel CNIL Éducation
                </td><td class="px-3 py-1.5">
                  Juillet 2020
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <p class="text-sm text-gray-500">
          <strong>Base légale :</strong> Mission d'intérêt public (Art. 6.1.e RGPD). Aucune donnée sensible collectée (Art. 9).
        </p>
      </div>

      <!-- 2. DONNÉES COLLECTÉES -->
      <div>
        <h2 class="text-xl font-semibold mb-4 text-primary-800 border-b border-gray-100 pb-2">
          2. Données Personnelles Collectées
        </h2>
        <p class="text-gray-600 mb-4 leading-relaxed">
          Principe de minimisation (Art. 5.1.c) : seules les données strictement nécessaires sont collectées.
        </p>
        <div class="grid md:grid-cols-2 gap-4 mb-3">
          <div class="bg-gray-50 border border-gray-200 rounded-lg p-4">
            <h4 class="font-semibold text-gray-900 mb-2">
              Élèves
            </h4>
            <ul class="text-sm text-gray-600 space-y-1">
              <li>Nom, prénom, classe</li><li>Email scolaire</li><li>Copies d'examens, notes, annotations</li>
            </ul>
          </div>
          <div class="bg-gray-50 border border-gray-200 rounded-lg p-4">
            <h4 class="font-semibold text-gray-900 mb-2">
              Enseignants / Personnel
            </h4>
            <ul class="text-sm text-gray-600 space-y-1">
              <li>Nom, prénom, login / email</li><li>Actions de correction (traçabilité)</li>
            </ul>
          </div>
        </div>
        <div class="bg-red-50 border border-red-200 rounded p-3 text-sm text-red-800">
          <strong>NON collecté :</strong> photo, adresse, téléphone, données bancaires, santé, cookies publicitaires, localisation.
        </div>
      </div>

      <!-- 3. SÉCURITÉ -->
      <div>
        <h2 class="text-xl font-semibold mb-4 text-primary-800 border-b border-gray-100 pb-2">
          3. Architecture et Sécurité
        </h2>
        <p class="text-gray-600 mb-4 leading-relaxed">
          Approche défensive multicouche : moindre privilège, défense en profondeur, traçabilité totale.
        </p>
        <div class="overflow-x-auto">
          <table class="w-full text-sm border-collapse">
            <thead>
              <tr class="bg-gray-50">
                <th class="text-left px-3 py-2 border-b font-medium text-gray-700">
                  Catégorie
                </th><th class="text-left px-3 py-2 border-b font-medium text-gray-700">
                  Mesures
                </th>
              </tr>
            </thead>
            <tbody class="text-gray-600">
              <tr>
                <td class="px-3 py-2 border-b font-medium">
                  Authentification
                </td><td class="px-3 py-2 border-b">
                  Sessions sécurisées, rate limiting (5/15min admin, 30/15min élève par IP), cookies HttpOnly + SameSite
                </td>
              </tr>
              <tr>
                <td class="px-3 py-2 border-b font-medium">
                  Contrôle d'accès
                </td><td class="px-3 py-2 border-b">
                  RBAC (Admin/Enseignant/Élève), permission DRF, queryset filtering
                </td>
              </tr>
              <tr>
                <td class="px-3 py-2 border-b font-medium">
                  Chiffrement
                </td><td class="px-3 py-2 border-b">
                  HTTPS (TLS 1.2+), HSTS, CSP, CSRF tokens, mots de passe PBKDF2
                </td>
              </tr>
              <tr>
                <td class="px-3 py-2 border-b font-medium">
                  Anonymisation
                </td><td class="px-3 py-2 border-b">
                  Numéro séquentiel unique, masquage en-tête, séparation identité/copie
                </td>
              </tr>
              <tr>
                <td class="px-3 py-2 border-b font-medium">
                  Intelligence Artificielle
                </td><td class="px-3 py-2 border-b">
                  LLM Local (Ollama) : traitement interne sans sortie de données pédagogiques vers le cloud
                </td>
              </tr>
              <tr>
                <td class="px-3 py-2 font-medium">
                  Audit
                </td><td class="px-3 py-2">
                  AuditLog complet : connexions, annotations, exports, téléchargements
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- 4. DROITS RGPD -->
      <div>
        <h2 class="text-xl font-semibold mb-4 text-primary-800 border-b border-gray-100 pb-2">
          4. Droits des Personnes (Art. 15–22)
        </h2>
        <p class="text-gray-600 mb-4">
          Délai de réponse : <strong>1 mois maximum</strong>.
        </p>
        <ul class="list-disc pl-5 space-y-1.5 text-sm text-gray-600 mb-3">
          <li><strong>Accès</strong> (Art. 15) : savoir quelles données sont détenues</li>
          <li><strong>Rectification</strong> (Art. 16) : corriger une donnée inexacte</li>
          <li><strong>Effacement</strong> (Art. 17) : limité par obligations légales (Code de l'Éducation)</li>
          <li><strong>Portabilité</strong> (Art. 20) : export PDF / JSON des données</li>
          <li><strong>Opposition</strong> (Art. 21) : sauf mission d'intérêt public</li>
        </ul>
        <p class="text-xs text-gray-500">
          Aucune décision automatisée (Art. 22) : les notes sont attribuées par des enseignants.
        </p>
      </div>

      <!-- 5. CONSERVATION -->
      <div>
        <h2 class="text-xl font-semibold mb-4 text-primary-800 border-b border-gray-100 pb-2">
          5. Conservation des Données
        </h2>
        <div class="overflow-x-auto">
          <table class="w-full text-sm border-collapse">
            <thead>
              <tr class="bg-gray-50">
                <th class="text-left px-3 py-2 border-b font-medium text-gray-700">
                  Données
                </th><th class="text-left px-3 py-2 border-b font-medium text-gray-700">
                  Durée
                </th>
              </tr>
            </thead>
            <tbody class="text-gray-600">
              <tr>
                <td class="px-3 py-1.5 border-b">
                  Données élèves
                </td><td class="px-3 py-1.5 border-b font-medium">
                  Fin scolarité + 1 an
                </td>
              </tr>
              <tr>
                <td class="px-3 py-1.5 border-b">
                  Copies numérisées
                </td><td class="px-3 py-1.5 border-b font-medium">
                  1 an après examen
                </td>
              </tr>
              <tr>
                <td class="px-3 py-1.5 border-b">
                  Notes et annotations
                </td><td class="px-3 py-1.5 border-b font-medium">
                  1 an (export Pronote)
                </td>
              </tr>
              <tr>
                <td class="px-3 py-1.5 border-b">
                  Logs d'audit
                </td><td class="px-3 py-1.5 border-b font-medium">
                  6 mois (CNIL)
                </td>
              </tr>
              <tr>
                <td class="px-3 py-1.5">
                  Sessions
                </td><td class="px-3 py-1.5 font-medium">
                  2 semaines (inactivité)
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- 6. INCIDENTS -->
      <div>
        <h2 class="text-xl font-semibold mb-4 text-primary-800 border-b border-gray-100 pb-2">
          6. Gestion des Incidents
        </h2>
        <p class="text-gray-600 mb-4 leading-relaxed">
          En cas de violation de données (Art. 33-34 RGPD), notification CNIL sous <strong>72 heures</strong>.
        </p>
        <div class="grid md:grid-cols-3 gap-4 text-sm">
          <div class="bg-green-50 border border-green-200 rounded p-3">
            <h5 class="font-semibold text-green-800 mb-1">
              Mineur
            </h5>
            <p class="text-green-700">
              Log auto, revue mensuelle.
            </p>
          </div>
          <div class="bg-yellow-50 border border-yellow-200 rounded p-3">
            <h5 class="font-semibold text-yellow-800 mb-1">
              Modéré
            </h5>
            <p class="text-yellow-700">
              Investigation, mesures correctives.
            </p>
          </div>
          <div class="bg-red-50 border border-red-200 rounded p-3">
            <h5 class="font-semibold text-red-800 mb-1">
              Grave
            </h5>
            <p class="text-red-700">
              Cellule de crise, CNIL + personnes sous 72h.
            </p>
          </div>
        </div>
      </div>

      <!-- 7. CONFORMITÉ CNIL -->
      <div>
        <h2 class="text-xl font-semibold mb-4 text-primary-800 border-b border-gray-100 pb-2">
          7. Conformité CNIL Éducation
        </h2>
        <ul class="space-y-2 text-sm">
          <li class="flex items-center gap-2 text-gray-700">
            <AppIcon name="check-mark" :size="14" class="text-green-500 font-bold" /> Consentement éclairé mineur (portail élève)
          </li>
          <li class="flex items-center gap-2 text-gray-700">
            <AppIcon name="check-mark" :size="14" class="text-green-500 font-bold" /> Limitation accès données élèves (RBAC)
          </li>
          <li class="flex items-center gap-2 text-gray-700">
            <AppIcon name="check-mark" :size="14" class="text-green-500 font-bold" /> Sécurité réseau (HTTPS, HSTS, CSRF)
          </li>
          <li class="flex items-center gap-2 text-gray-700">
            <AppIcon name="check-mark" :size="14" class="text-green-500 font-bold" /> Conservation limitée + suppression automatique
          </li>
          <li class="flex items-center gap-2 text-gray-700">
            <AppIcon name="check-mark" :size="14" class="text-green-500 font-bold" /> Droit d'accès facilité (export données)
          </li>
          <li class="flex items-center gap-2 text-gray-700">
            <AppIcon name="check-mark" :size="14" class="text-green-500 font-bold" /> Information transparente (politique en français)
          </li>
          <li class="flex items-center gap-2 text-gray-700">
            <AppIcon name="check-mark" :size="14" class="text-green-500 font-bold" /> Pas de profilage ni décision automatisée
          </li>
        </ul>
      </div>

      <div class="pt-6 mt-6 border-t border-gray-200">
        <div class="flex items-start gap-3 bg-gray-50 border border-gray-200 rounded-lg p-4">
          <AppIcon name="file-down" :size="20" class="text-primary-600 flex-shrink-0 mt-0.5" />
          <div>
            <p class="text-sm font-medium text-gray-900">
              Registre des Activités de Traitement
            </p>
            <p class="text-sm text-gray-600 mt-1">
              Le registre complet (Art. 30 RGPD) est disponible sur demande auprès du DPO de l'établissement.
            </p>
          </div>
        </div>
      </div>
    </div>
  </SectionContainer>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import api from '../services/api'
import SectionContainer from '../components/SectionContainer.vue'
import AppIcon from '../icons/AppIcon.vue'

const pd = ref(null)
const statsLoading = ref(true)

function formatDate(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleDateString('fr-FR', { day: 'numeric', month: 'long', year: 'numeric', hour: '2-digit', minute: '2-digit' })
}

onMounted(async () => {
  try {
    const { data } = await api.get('/platform-stats/')
    pd.value = data
  } catch (e) {
    console.warn('Platform stats unavailable:', e.message)
  } finally {
    statsLoading.value = false
  }
})
</script>
