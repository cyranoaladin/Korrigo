<template>
  <SectionContainer title="Direction & Conformité">
    <!-- CONTACTS -->
    <div class="grid md:grid-cols-2 lg:grid-cols-4 gap-6 mb-12">
      <div class="bg-white p-5 rounded-lg border border-borderSoft shadow-sm">
        <Building class="w-5 h-5 text-primary-600 mb-2" />
        <h3 class="font-semibold text-sm mb-1 text-neutralDark">
          Responsable de Traitement
        </h3>
        <p class="text-sm text-gray-600">
          Proviseur du Lycée Pierre Mendès France de Tunis
        </p>
      </div>
      <div class="bg-white p-5 rounded-lg border border-borderSoft shadow-sm">
        <ShieldCheck class="w-5 h-5 text-green-600 mb-2" />
        <h3 class="font-semibold text-sm mb-1 text-neutralDark">
          DPO
        </h3>
        <p class="text-sm text-gray-600">
          labo.maths@ert.tn
        </p>
      </div>
      <div class="bg-white p-5 rounded-lg border border-borderSoft shadow-sm">
        <Code class="w-5 h-5 text-blue-600 mb-2" />
        <h3 class="font-semibold text-sm mb-1 text-neutralDark">
          Développement
        </h3>
        <p class="text-sm text-gray-600">
          Alaeddine BEN RHOUMA<br><span class="text-xs text-gray-400">alaeddine.benrhouma@ert.tn</span>
        </p>
      </div>
      <div class="bg-white p-5 rounded-lg border border-borderSoft shadow-sm">
        <Server class="w-5 h-5 text-orange-600 mb-2" />
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
                  Sessions sécurisées, rate limiting (5/15 min), cookies HttpOnly + SameSite
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
                <td class="px-3 py-2 font-medium">
                  Audit
                </td><td class="px-3 py-2">
                  GradingEvent : connexions, annotations, exports, téléchargements
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
            <span class="text-green-500 font-bold">✓</span> Consentement éclairé mineur (portail élève)
          </li>
          <li class="flex items-center gap-2 text-gray-700">
            <span class="text-green-500 font-bold">✓</span> Limitation accès données élèves (RBAC)
          </li>
          <li class="flex items-center gap-2 text-gray-700">
            <span class="text-green-500 font-bold">✓</span> Sécurité réseau (HTTPS, HSTS, CSRF)
          </li>
          <li class="flex items-center gap-2 text-gray-700">
            <span class="text-green-500 font-bold">✓</span> Conservation limitée + suppression automatique
          </li>
          <li class="flex items-center gap-2 text-gray-700">
            <span class="text-green-500 font-bold">✓</span> Droit d'accès facilité (export données)
          </li>
          <li class="flex items-center gap-2 text-gray-700">
            <span class="text-green-500 font-bold">✓</span> Information transparente (politique en français)
          </li>
          <li class="flex items-center gap-2 text-gray-700">
            <span class="text-green-500 font-bold">✓</span> Pas de profilage ni décision automatisée
          </li>
        </ul>
      </div>

      <div class="pt-6 mt-6 border-t border-gray-200">
        <div class="flex items-start gap-3 bg-gray-50 border border-gray-200 rounded-lg p-4">
          <FileDown class="w-5 h-5 text-primary-600 flex-shrink-0 mt-0.5" />
          <div>
            <p class="text-sm font-medium text-gray-900">
              Registre des Activités de Traitement
            </p>
            <p class="text-sm text-gray-600 mt-1">
              Le registre complet (Art. 30 RGPD) est disponible sur demande auprès du DPO :
              <a
                href="mailto:labo.maths@ert.tn"
                class="text-primary-600 hover:text-primary-800 font-medium"
              >labo.maths@ert.tn</a>
            </p>
          </div>
        </div>
      </div>
    </div>
  </SectionContainer>
</template>

<script setup>
import SectionContainer from '../components/SectionContainer.vue'
import { Building, ShieldCheck, Code, Server, FileDown } from 'lucide-vue-next'
</script>
