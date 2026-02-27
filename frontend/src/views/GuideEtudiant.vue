<template>
  <SectionContainer title="Guide Élève">
    <div class="mb-8 p-4 bg-green-50 rounded-lg border border-green-200 flex items-start gap-3">
      <GraduationCap class="w-6 h-6 text-green-600 flex-shrink-0 mt-0.5" />
      <div>
        <h3 class="text-sm font-medium text-green-800">
          Bienvenue sur le portail élève Korrigo PMF
        </h3>
        <p class="mt-1 text-sm text-green-700">
          Ce portail vous permet de consulter vos copies d'examens corrigées, de comprendre les annotations
          de vos professeurs et de télécharger vos copies en PDF. Vos données sont protégées conformément au RGPD.
        </p>
      </div>
    </div>

    <CollapsibleSection title="1. Comment me connecter ?">
      <p class="mb-4">
        Vos identifiants de connexion sont fournis par le lycée :
      </p>
      <ul class="list-disc pl-5 space-y-2 mb-4">
        <li><strong>Email :</strong> Votre adresse email scolaire (ex : <code>prenom.nom@ert.tn</code>).</li>
        <li><strong>Mot de passe :</strong> Un mot de passe provisoire vous est fourni. À la première connexion, il peut vous être demandé de le modifier.</li>
      </ul>
      <h4 class="font-medium text-gray-900 mb-2">
        Étapes de connexion :
      </h4>
      <ol class="list-decimal pl-5 space-y-1.5 text-sm mb-4">
        <li>Ouvrez votre navigateur (Chrome, Firefox, Edge recommandés)</li>
        <li>Accédez à l'URL du portail élève (fournie par votre lycée)</li>
        <li>Saisissez votre email et votre mot de passe</li>
        <li>Cliquez sur <strong>« Se connecter »</strong></li>
      </ol>
      <div class="bg-yellow-50 border border-yellow-200 rounded p-3 text-sm text-yellow-800">
        <strong>Mot de passe oublié ?</strong> Contactez le secrétariat ou votre professeur principal.
        Il n'y a pas encore de lien automatique « Mot de passe oublié » sur le site.
      </div>
    </CollapsibleSection>

    <CollapsibleSection title="2. Mon tableau de bord">
      <p class="mb-4">
        Une fois connecté, votre tableau de bord affiche la liste de tous vos <strong>examens corrigés</strong>.
      </p>
      <p class="mb-3">
        Pour chaque examen, vous voyez :
      </p>
      <ul class="list-disc pl-5 space-y-1.5 text-sm mb-4">
        <li><strong>Nom de l'examen</strong> (ex : Bac Blanc Mathématiques TG)</li>
        <li><strong>Votre note</strong> (ex : 14.5/20)</li>
        <li><strong>Date de correction</strong></li>
        <li>Boutons <strong>« Voir la copie »</strong> et <strong>« Télécharger PDF »</strong></li>
      </ul>
      <div class="bg-blue-50 border border-blue-200 rounded p-3 text-sm text-blue-800">
        Les copies apparaissent <strong>uniquement après finalisation</strong> par le professeur. Si vous ne voyez pas encore de copies, c'est normal : la correction est probablement en cours.
      </div>
    </CollapsibleSection>

    <CollapsibleSection title="3. Comprendre les annotations et le Bilan IA">
      <p class="mb-4">
        Vos professeurs utilisent <strong>4 types d'annotations</strong> standardisées sur vos copies :
      </p>
      <div class="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-6">
        <div class="flex items-start gap-3 p-3 border rounded-lg bg-white shadow-sm">
          <span class="text-red-500 font-bold text-xl mt-0.5">💬</span>
          <div>
            <h4 class="font-semibold text-sm text-gray-900">
              Commentaire
            </h4>
            <p class="text-xs text-gray-600">
              Remarque, explication ou conseil du professeur. Peut contenir des points (+/-).
            </p>
          </div>
        </div>
        <div class="flex items-start gap-3 p-3 border rounded-lg bg-white shadow-sm">
          <span class="bg-yellow-200 w-6 h-6 rounded flex-shrink-0 mt-1" />
          <div>
            <h4 class="font-semibold text-sm text-gray-900">
              Surlignage
            </h4>
            <p class="text-xs text-gray-600">
              Passage mis en évidence par le professeur pour attirer votre attention.
            </p>
          </div>
        </div>
        <div class="flex items-start gap-3 p-3 border rounded-lg bg-white shadow-sm">
          <span class="text-red-500 font-bold text-xl mt-0.5">✗</span>
          <div>
            <h4 class="font-semibold text-sm text-gray-900">
              Erreur
            </h4>
            <p class="text-xs text-gray-600">
              Signale une erreur. Accompagné des points retirés (ex : -1.0).
            </p>
          </div>
        </div>
        <div class="flex items-start gap-3 p-3 border rounded-lg bg-white shadow-sm">
          <span class="text-green-500 font-bold text-xl mt-0.5">⭐</span>
          <div>
            <h4 class="font-semibold text-sm text-gray-900">
              Bonus
            </h4>
            <p class="text-xs text-gray-600">
              Récompense une initiative ou un raisonnement original (+ points).
            </p>
          </div>
        </div>
      </div>

      <div class="p-4 bg-primary-50 border border-primary-200 rounded-lg mb-4">
        <h4 class="font-bold text-primary-900 mb-2 flex items-center gap-2">
          <Sparkles class="w-5 h-5" /> Bilan Pédagogique IA (Nouveauté 2026)
        </h4>
        <p class="text-sm text-primary-800 leading-relaxed">
          En plus des annotations, vous trouverez souvent un <strong>bilan personnalisé</strong> généré par Korrigo AI. 
          Ce texte vous tutoie et résume vos points forts et vos axes de progrès en se basant sur les remarques de votre professeur. C'est un outil précieux pour vos révisions !
        </p>
      </div>

      <div class="bg-gray-50 border border-gray-200 rounded p-3 text-sm">
        <strong>Calcul de la note :</strong> Note = Somme des points par question + Bonus − Erreurs.
        Le total est calculé automatiquement sans erreur possible.
      </div>
    </CollapsibleSection>

    <CollapsibleSection title="4. Télécharger mes copies">
      <p class="mb-4">
        Vous pouvez télécharger vos copies en PDF pour les conserver, les partager avec vos parents ou les imprimer :
      </p>
      <ul class="list-disc pl-5 space-y-2 text-sm mb-4">
        <li><strong>Depuis le tableau de bord :</strong> Cliquez sur <strong>« Télécharger PDF »</strong> à côté de l'examen.</li>
        <li><strong>Depuis le visualiseur :</strong> Ouvrez la copie, puis cliquez sur le bouton de téléchargement.</li>
      </ul>
      <p class="text-sm text-gray-600 mb-3">
        Le PDF contient votre copie complète avec toutes les annotations intégrées, votre nom et votre note.
      </p>
      <p class="text-sm text-gray-500 italic">
        Vous pouvez télécharger vos copies autant de fois que vous le souhaitez.
      </p>
    </CollapsibleSection>

    <CollapsibleSection title="5. Vos droits et confidentialité (RGPD)">
      <p class="mb-4 text-sm">
        Korrigo PMF respecte le <strong>Règlement Général sur la Protection des Données</strong> (RGPD).
        Vos données personnelles sont protégées et votre vie privée est respectée.
      </p>

      <h4 class="font-medium text-gray-900 mb-2">
        Données stockées
      </h4>
      <ul class="list-disc pl-5 space-y-1 text-sm mb-4 text-gray-600">
        <li>Nom, prénom et classe</li>
        <li>Adresse email scolaire</li>
        <li>Copies d'examens et notes</li>
      </ul>

      <h4 class="font-medium text-gray-900 mb-2">
        Qui peut voir vos copies ?
      </h4>
      <div class="overflow-x-auto mb-4">
        <table class="w-full text-sm border-collapse">
          <tbody class="text-gray-600">
            <tr>
              <td class="px-3 py-1.5 border-b font-medium">
                Vous
              </td><td class="px-3 py-1.5 border-b">
                Uniquement vos propres copies
              </td>
            </tr>
            <tr>
              <td class="px-3 py-1.5 border-b font-medium">
                Vos professeurs
              </td><td class="px-3 py-1.5 border-b">
                Pour corriger (copie anonymisée)
              </td>
            </tr>
            <tr>
              <td class="px-3 py-1.5 border-b font-medium">
                Administrateurs
              </td><td class="px-3 py-1.5 border-b">
                Gestion technique de la plateforme
              </td>
            </tr>
            <tr>
              <td class="px-3 py-1.5 font-medium">
                Autres élèves
              </td><td class="px-3 py-1.5">
                Aucun accès à vos copies
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <h4 class="font-medium text-gray-900 mb-2">
        Vos droits
      </h4>
      <ul class="list-disc pl-5 space-y-1.5 text-sm text-gray-600 mb-4">
        <li><strong>Droit d'accès :</strong> Savoir quelles données sont stockées à votre sujet</li>
        <li><strong>Droit de rectification :</strong> Corriger une information inexacte (nom mal orthographié, etc.)</li>
        <li><strong>Droit à l'effacement :</strong> Suppression après la durée légale de conservation (1 an)</li>
        <li><strong>Droit de portabilité :</strong> Recevoir une copie de vos données en PDF</li>
      </ul>

      <h4 class="font-medium text-gray-900 mb-2">
        Durées de conservation
      </h4>
      <ul class="list-disc pl-5 space-y-1 text-sm text-gray-600 mb-4">
        <li>Copies d'examens : <strong>1 an</strong> après l'examen</li>
        <li>Notes : jusqu'à la fin de votre scolarité + 1 an</li>
        <li>Données personnelles : supprimées après votre départ du lycée</li>
      </ul>

      <div class="bg-green-50 border border-green-200 rounded p-3 text-sm text-green-800">
        <strong>Contact RGPD :</strong> Pour exercer vos droits, contactez le DPO de votre lycée ou écrivez à <code>dpo@korrigo.education</code>.
        En cas de non-respect de vos droits, vous pouvez contacter la <strong>CNIL</strong> (cnil.fr).
      </div>
    </CollapsibleSection>

    <CollapsibleSection title="6. Questions fréquentes">
      <div class="space-y-4">
        <div>
          <h4 class="font-medium text-gray-900">
            J'ai oublié mon mot de passe.
          </h4>
          <p class="text-sm text-gray-600">
            Contactez le secrétariat ou votre professeur principal pour une réinitialisation.
          </p>
        </div>
        <div>
          <h4 class="font-medium text-gray-900">
            Je n'ai pas encore de copies corrigées.
          </h4>
          <p class="text-sm text-gray-600">
            C'est normal si vos professeurs n'ont pas encore finalisé les corrections. Les copies apparaissent uniquement après finalisation.
          </p>
        </div>
        <div>
          <h4 class="font-medium text-gray-900">
            Le PDF ne s'affiche pas.
          </h4>
          <p class="text-sm text-gray-600">
            Actualisez la page (F5), videz le cache du navigateur, ou essayez Google Chrome. Vérifiez aussi votre connexion internet.
          </p>
        </div>
        <div>
          <h4 class="font-medium text-gray-900">
            Ma note est différente de celle sur Pronote.
          </h4>
          <p class="text-sm text-gray-600">
            C'est possible si la note a été arrondie ou si un coefficient a été appliqué dans Pronote. En cas de doute, demandez à votre professeur.
          </p>
        </div>
        <div>
          <h4 class="font-medium text-gray-900">
            Les autres élèves peuvent-ils voir mes notes ?
          </h4>
          <p class="text-sm text-gray-600">
            Non, absolument pas. Chaque élève ne voit que ses propres copies. La plateforme garantit cette confidentialité.
          </p>
        </div>
        <div>
          <h4 class="font-medium text-gray-900">
            Comment contester ma note ?
          </h4>
          <p class="text-sm text-gray-600">
            Parlez directement à votre professeur. Le support technique ne peut pas modifier les notes.
          </p>
        </div>
      </div>
    </CollapsibleSection>

    <CollapsibleSection title="7. Conseils d'utilisation">
      <div class="space-y-3 text-sm">
        <div>
          <h4 class="font-medium text-gray-900 mb-1">
            Consultez régulièrement
          </h4>
          <p class="text-gray-600">
            Connectez-vous régulièrement pour voir vos nouvelles copies corrigées.
          </p>
        </div>
        <div>
          <h4 class="font-medium text-gray-900 mb-1">
            Téléchargez vos copies
          </h4>
          <p class="text-gray-600">
            Téléchargez toutes vos copies importantes (Bac Blanc, contrôles). Organisez vos PDF par matière et trimestre.
          </p>
        </div>
        <div>
          <h4 class="font-medium text-gray-900 mb-1">
            Révisez avec vos copies
          </h4>
          <p class="text-gray-600">
            Relisez les commentaires de vos professeurs pour comprendre vos erreurs et noter les points à améliorer.
          </p>
        </div>
        <div>
          <h4 class="font-medium text-gray-900 mb-1">
            Sécurité
          </h4>
          <p class="text-gray-600">
            Ne partagez jamais vos identifiants. Déconnectez-vous après chaque session, surtout sur un ordinateur partagé.
          </p>
        </div>
      </div>
    </CollapsibleSection>
  </SectionContainer>
</template>

<script setup>
import SectionContainer from '../components/SectionContainer.vue'
import CollapsibleSection from '../components/CollapsibleSection.vue'
import { GraduationCap, Sparkles } from 'lucide-vue-next'
</script>
