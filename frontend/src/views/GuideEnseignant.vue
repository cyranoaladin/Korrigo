<template>
  <SectionContainer title="Guide Enseignant">
    <div class="mb-8 p-4 bg-primary-50 rounded-lg border border-primary-100 flex items-start gap-3">
      <Info class="w-6 h-6 text-primary-600 flex-shrink-0 mt-0.5" />
      <div>
        <h3 class="text-sm font-medium text-primary-800">Bienvenue sur Korrigo PMF</h3>
        <p class="mt-1 text-sm text-primary-700">
          Ce guide vous accompagne dans la correction numérique de vos copies.
          Korrigo vous permet de corriger sans impression, d'annoter directement sur les PDF,
          de noter selon un barème préétabli et de générer automatiquement les PDF finaux pour les élèves.
        </p>
        <div class="mt-3 flex flex-wrap gap-2">
          <span class="inline-flex items-center gap-1 text-xs bg-white px-2.5 py-1 rounded-full border border-primary-200 text-primary-700">
            <CheckCircle class="w-3 h-3" /> Gain de temps
          </span>
          <span class="inline-flex items-center gap-1 text-xs bg-white px-2.5 py-1 rounded-full border border-primary-200 text-primary-700">
            <CheckCircle class="w-3 h-3" /> Correction flexible
          </span>
          <span class="inline-flex items-center gap-1 text-xs bg-white px-2.5 py-1 rounded-full border border-primary-200 text-primary-700">
            <CheckCircle class="w-3 h-3" /> Sauvegarde auto
          </span>
          <span class="inline-flex items-center gap-1 text-xs bg-white px-2.5 py-1 rounded-full border border-primary-200 text-primary-700">
            <CheckCircle class="w-3 h-3" /> Annotations professionnelles
          </span>
        </div>
      </div>
    </div>

    <CollapsibleSection title="1. Connexion et Tableau de Bord">
      <p class="mb-4">
        Accédez à la plateforme depuis l'URL fournie par votre lycée et connectez-vous avec vos identifiants académiques.
      </p>
      <ul class="list-disc pl-5 space-y-2 mb-4">
        <li><strong>Identifiant :</strong> Généralement sous la forme <code>prenom.nom</code> ou votre email <code>@ert.tn</code>.</li>
        <li><strong>Mot de passe :</strong> Votre mot de passe sécurisé (fourni par l'administration).</li>
      </ul>
      <p class="mb-4">Une fois connecté, votre <strong>tableau de bord</strong> affiche :</p>
      <ul class="list-disc pl-5 space-y-1 text-sm mb-4">
        <li>La liste de vos examens avec le nombre de copies à corriger / finalisées</li>
        <li>Un bouton <strong>« Accéder aux copies »</strong> pour chaque examen</li>
      </ul>
      <div class="bg-yellow-50 border border-yellow-200 rounded p-3 text-sm text-yellow-800">
        <strong>Navigateurs recommandés :</strong> Google Chrome (optimal), Mozilla Firefox, Microsoft Edge.
        Safari fonctionne partiellement. Internet Explorer n'est pas supporté.
      </div>
    </CollapsibleSection>

    <CollapsibleSection title="2. Sélection des Copies et Verrouillage">
      <p class="mb-4">
        Depuis le tableau de bord, cliquez sur <strong>« Accéder aux copies »</strong> pour voir la liste des copies (anonymisées).
      </p>
      <div class="bg-gray-50 p-4 rounded mb-4">
        <h4 class="font-medium mb-2">Statuts des copies :</h4>
        <ul class="space-y-2 text-sm">
          <li><span class="inline-block w-3 h-3 rounded-full bg-green-500 mr-2"></span><strong>PRÊT :</strong> Copie identifiée, prête à corriger. Cliquez pour verrouiller et commencer.</li>
          <li><span class="inline-block w-3 h-3 rounded-full bg-yellow-500 mr-2"></span><strong>VERROUILLÉE (par vous) :</strong> Vous êtes en train de corriger. Cliquez pour continuer.</li>
          <li><span class="inline-block w-3 h-3 rounded-full bg-red-500 mr-2"></span><strong>VERROUILLÉE (autre) :</strong> Un collègue corrige cette copie. Attendez la libération.</li>
          <li><span class="inline-block w-3 h-3 rounded-full bg-blue-500 mr-2"></span><strong>CORRIGÉE :</strong> Correction finalisée. Consultation uniquement.</li>
        </ul>
      </div>
      <p class="mb-3">
        Lorsque vous ouvrez une copie, elle est automatiquement <strong>verrouillée</strong> pour vous, empêchant toute modification concurrente.
      </p>
      <div class="bg-blue-50 border border-blue-200 rounded p-3 text-sm text-blue-800">
        <strong>Heartbeat :</strong> Le verrouillage est maintenu tant que vous travaillez (mécanisme automatique).
        Il expire après <strong>30 minutes d'inactivité</strong>. Si vous fermez votre navigateur, vos annotations sont sauvegardées et restaurées à la reprise.
      </div>
    </CollapsibleSection>

    <CollapsibleSection title="3. Interface de Correction">
      <p class="mb-4">L'interface est divisée en <strong>deux zones principales</strong> :</p>
      <div class="grid md:grid-cols-2 gap-4 mb-6">
        <div class="bg-white border border-gray-200 rounded-lg p-4">
          <h4 class="font-semibold text-gray-900 mb-2">Zone gauche : Visualiseur PDF</h4>
          <ul class="text-sm text-gray-600 space-y-1.5">
            <li>Affichage de la copie scannée page par page</li>
            <li>Barre d'outils d'annotation en bas</li>
            <li>Navigation entre pages (flèches clavier <code>← →</code>)</li>
            <li>Zoom (<code>Ctrl +</code> / <code>Ctrl -</code>)</li>
          </ul>
        </div>
        <div class="bg-white border border-gray-200 rounded-lg p-4">
          <h4 class="font-semibold text-gray-900 mb-2">Zone droite : Barème & Notation</h4>
          <ul class="text-sm text-gray-600 space-y-1.5">
            <li>Barème hiérarchique : Exercice → Question → Sous-question</li>
            <li>Cases à cocher (tout ou rien) ou saisie manuelle de points</li>
            <li>Calcul automatique du total (aucune erreur possible)</li>
            <li>Boutons <strong>Sauvegarder</strong> et <strong>Finaliser</strong></li>
          </ul>
        </div>
      </div>
      <p class="text-sm text-gray-600">
        <strong>Sauvegarde automatique :</strong> Vos annotations sont sauvegardées toutes les 30 secondes.
        Indicateur <code>☁️</code> en haut à droite. Sauvegarde manuelle possible avec <code>Ctrl + S</code>.
      </p>
    </CollapsibleSection>

    <CollapsibleSection title="4. Les 4 Types d'Annotations">
      <p class="mb-4">Korrigo propose quatre outils d'annotation complémentaires :</p>
      <div class="space-y-4">
        <div class="flex items-start gap-3 p-3 bg-white border border-gray-200 rounded-lg">
          <span class="text-red-500 text-xl font-bold mt-0.5">💬</span>
          <div>
            <h4 class="font-semibold text-gray-900">Commentaire</h4>
            <p class="text-sm text-gray-600">Remarque pédagogique, explication, conseil. Peut porter des points positifs ou négatifs.
              Exemples : « Erreur de signe ligne 3 » (-0.5), « Excellent raisonnement ! » (+0.5).</p>
          </div>
        </div>
        <div class="flex items-start gap-3 p-3 bg-white border border-gray-200 rounded-lg">
          <span class="bg-yellow-200 w-6 h-6 rounded flex-shrink-0 mt-1"></span>
          <div>
            <h4 class="font-semibold text-gray-900">Surlignage</h4>
            <p class="text-sm text-gray-600">Cliquez-glissez pour mettre en évidence un passage. N'affecte pas le score (0 points par défaut).</p>
          </div>
        </div>
        <div class="flex items-start gap-3 p-3 bg-white border border-gray-200 rounded-lg">
          <span class="text-red-500 text-xl font-bold mt-0.5">✗</span>
          <div>
            <h4 class="font-semibold text-gray-900">Erreur</h4>
            <p class="text-sm text-gray-600">Signale une erreur factuelle. Points retirés (nombre négatif). Exemple : « Erreur de méthode » (-1.0).</p>
          </div>
        </div>
        <div class="flex items-start gap-3 p-3 bg-white border border-gray-200 rounded-lg">
          <span class="text-green-500 text-xl font-bold mt-0.5">⭐</span>
          <div>
            <h4 class="font-semibold text-gray-900">Bonus</h4>
            <p class="text-sm text-gray-600">Récompense une initiative ou une réponse exceptionnelle. Points bonus (nombre positif). À utiliser avec parcimonie.</p>
          </div>
        </div>
      </div>
    </CollapsibleSection>

    <CollapsibleSection title="5. Banque de Commentaires">
      <p class="mb-4">
        Pour gagner du temps, Korrigo enregistre automatiquement vos commentaires fréquents dans une <strong>banque personnelle</strong>.
      </p>
      <ul class="list-disc pl-5 space-y-2 text-sm mb-4">
        <li>Chaque commentaire saisi est ajouté à votre banque.</li>
        <li>Lors de la création d'un nouveau commentaire, l'<strong>auto-complétion</strong> propose vos textes existants.</li>
        <li>Les commentaires sont classés par <strong>fréquence d'utilisation</strong>.</li>
        <li>Le texte et la note associée sont remplis automatiquement.</li>
      </ul>
      <p class="text-sm text-gray-500">
        En plus de votre banque personnelle, <strong>123 suggestions officielles</strong> issues du barème et du corrigé sont disponibles.
      </p>
    </CollapsibleSection>

    <CollapsibleSection title="6. Finalisation et Export">
      <p class="mb-4">La finalisation d'une copie :</p>
      <ul class="list-disc pl-5 space-y-2 mb-4 text-sm">
        <li><strong>Verrouille définitivement</strong> la correction (modification par admin uniquement)</li>
        <li><strong>Génère le PDF final</strong> avec annotations aplaties et nom de l'élève réaffiché</li>
        <li><strong>Rend la copie accessible</strong> aux élèves sur le portail</li>
        <li><strong>Libère le verrouillage</strong> pour corriger la copie suivante</li>
      </ul>
      <h4 class="font-medium text-gray-900 mb-2">Avant de finaliser, vérifiez :</h4>
      <ol class="list-decimal pl-5 space-y-1 text-sm mb-4">
        <li>Toutes les questions du barème sont notées</li>
        <li>Les annotations sont claires et professionnelles</li>
        <li>Le score total est cohérent</li>
      </ol>
      <p class="text-sm text-gray-600">
        Après finalisation de toutes les copies, les notes sont exportables en <strong>CSV compatible Pronote</strong> depuis le tableau de bord de l'examen.
      </p>
    </CollapsibleSection>

    <CollapsibleSection title="7. Raccourcis Clavier">
      <div class="overflow-x-auto">
        <table class="w-full text-sm border-collapse">
          <thead>
            <tr class="bg-gray-50">
              <th class="text-left px-3 py-2 border-b font-medium text-gray-700">Raccourci</th>
              <th class="text-left px-3 py-2 border-b font-medium text-gray-700">Action</th>
            </tr>
          </thead>
          <tbody class="text-gray-600">
            <tr><td class="px-3 py-1.5 border-b"><code>Ctrl + S</code></td><td class="px-3 py-1.5 border-b">Sauvegarde manuelle</td></tr>
            <tr><td class="px-3 py-1.5 border-b"><code>←</code> / <code>→</code></td><td class="px-3 py-1.5 border-b">Page précédente / suivante</td></tr>
            <tr><td class="px-3 py-1.5 border-b"><code>Ctrl +</code> / <code>Ctrl -</code></td><td class="px-3 py-1.5 border-b">Zoom avant / arrière</td></tr>
            <tr><td class="px-3 py-1.5 border-b"><code>Ctrl 0</code></td><td class="px-3 py-1.5 border-b">Réinitialiser le zoom</td></tr>
            <tr><td class="px-3 py-1.5"><code>Échap</code></td><td class="px-3 py-1.5">Annuler l'annotation en cours</td></tr>
          </tbody>
        </table>
      </div>
    </CollapsibleSection>

    <CollapsibleSection title="8. Bonnes Pratiques">
      <div class="space-y-4 text-sm">
        <div>
          <h4 class="font-medium text-gray-900 mb-1">Organisation</h4>
          <ul class="list-disc pl-5 space-y-1 text-gray-600">
            <li>Corrigez par blocs : terminez toutes les copies d'un même exercice avant de passer au suivant</li>
            <li>Estimez 15–20 minutes par copie</li>
            <li>Faites des pauses toutes les 5–10 copies</li>
          </ul>
        </div>
        <div>
          <h4 class="font-medium text-gray-900 mb-1">Qualité des annotations</h4>
          <ul class="list-disc pl-5 space-y-1 text-gray-600">
            <li>Soyez précis : « Erreur de signe à la ligne 3 » plutôt que « Erreur »</li>
            <li>Soyez constructif : « Méthode correcte, attention aux calculs »</li>
            <li>Valorisez les initiatives : « Bien ! », « Excellent raisonnement »</li>
          </ul>
        </div>
        <div>
          <h4 class="font-medium text-gray-900 mb-1">Sécurité</h4>
          <ul class="list-disc pl-5 space-y-1 text-gray-600">
            <li>Vérifiez votre connexion avant une longue session</li>
            <li>Déconnectez-vous après utilisation sur un poste partagé</li>
            <li>Ne partagez jamais vos identifiants</li>
          </ul>
        </div>
      </div>
    </CollapsibleSection>

    <CollapsibleSection title="9. FAQ et Problèmes Courants">
      <div class="space-y-4">
        <div>
          <h4 class="font-medium text-gray-900">Je ne vois pas mes copies assignées.</h4>
          <p class="text-sm text-gray-600">Vérifiez que vous êtes connecté avec le bon compte. Si le problème persiste, contactez le coordinateur de discipline ou l'administrateur.</p>
        </div>
        <div>
          <h4 class="font-medium text-gray-900">Une copie est bloquée « Verrouillée ».</h4>
          <p class="text-sm text-gray-600">Le verrouillage expire automatiquement après 30 minutes d'inactivité. Si le collègue est parti sans finaliser, le verrou se libérera. Sinon, contactez l'administrateur.</p>
        </div>
        <div>
          <h4 class="font-medium text-gray-900">« Votre verrouillage a expiré »</h4>
          <p class="text-sm text-gray-600">Inactivité de plus de 30 min. Cliquez sur « Reverrouiller la copie ». Vos annotations sont conservées et seront restaurées automatiquement.</p>
        </div>
        <div>
          <h4 class="font-medium text-gray-900">Le PDF ne s'affiche pas.</h4>
          <p class="text-sm text-gray-600">Actualisez la page (F5), videz le cache du navigateur, ou essayez Google Chrome. Si le problème persiste, contactez le support.</p>
        </div>
        <div>
          <h4 class="font-medium text-gray-900">J'ai finalisé une copie par erreur.</h4>
          <p class="text-sm text-gray-600">Contactez l'administrateur, qui peut remettre la copie en statut brouillon et vous permettre de la modifier.</p>
        </div>
      </div>
    </CollapsibleSection>

  </SectionContainer>
</template>

<script setup>
import SectionContainer from '../components/SectionContainer.vue'
import CollapsibleSection from '../components/CollapsibleSection.vue'
import { Info, CheckCircle } from 'lucide-vue-next'
</script>
