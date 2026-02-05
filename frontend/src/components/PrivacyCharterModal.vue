<script setup>
import { ref } from 'vue'

const props = defineProps({
  show: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['accept', 'close'])

const handleAccept = () => {
  emit('accept')
}

const handleDecline = () => {
  emit('close')
}
</script>

<template>
  <div
    v-if="show"
    class="modal-overlay"
    @click.self="handleDecline"
  >
    <div class="modal-content">
      <div class="modal-header">
        <h2>📑 Charte de Confidentialité & Protection des Données</h2>
        <p class="text-xs text-gray-600 mb-4">
          Dernière mise à jour : Février 2026
        </p>
      </div>

      <div class="modal-body">
        <section>
          <h3>1. Responsabilité du Traitement</h3>
          <p>Le traitement des données est placé sous la responsabilité du <strong>Chef d'Établissement du Lycée PMF</strong>, avec le support technique du <strong>Labo Maths ERT</strong>. Korrigo est une solution développée en interne, garantissant une souveraineté totale sur les données scolaires.</p>
        </section>

        <section>
          <h3>2. Nature des Données Collectées</h3>
          <p>Dans le cadre strict de l'évaluation pédagogique, Korrigo traite les données suivantes :</p>
          <ul>
            <li><strong>Identité :</strong> Nom, prénom, classe et date de naissance (pour authentification)</li>
            <li><strong>Contenu :</strong> Copies d'examens scannées, annotations des correcteurs, notes et appréciations</li>
            <li><strong>Audit :</strong> Logs de connexion et d'accès aux copies (pour des raisons de sécurité)</li>
          </ul>
        </section>

        <section>
          <h3>3. Finalités du Traitement</h3>
          <p>Vos données sont utilisées exclusivement pour :</p>
          <ol>
            <li>La numérisation et l'indexation sécurisée des copies d'examen</li>
            <li>La correction anonymisée par les enseignants titulaires</li>
            <li>La mise à disposition des copies corrigées pour consultation par l'élève et ses responsables légaux</li>
            <li>L'exportation sécurisée des résultats vers les outils de gestion scolaire (Pronote)</li>
          </ol>
        </section>

        <section>
          <h3>4. Confidentialité et Accès</h3>
          <ul>
            <li><strong>Anonymat :</strong> L'identité de l'élève est masquée durant la phase de correction</li>
            <li><strong>Accès Restreint :</strong> Seuls l'élève concerné, ses enseignants et l'administration autorisée peuvent accéder aux copies. Aucune donnée n'est cédée à des tiers ou utilisée à des fins commerciales</li>
            <li><strong>Sécurité :</strong> Les données transitent via des protocoles chiffrés (SSL/TLS) et sont stockées sur des serveurs sécurisés au sein de l'établissement</li>
          </ul>
        </section>

        <section>
          <h3>5. Conservation et Droits (RGPD & INPDP)</h3>
          <p><strong>Durée :</strong> Les données sont conservées pour la durée de l'année scolaire en cours. Une purge automatique est effectuée à la fin de chaque cycle annuel.</p>
          <p class="mt-2">
            <strong>Vos Droits :</strong> Conformément au <strong>RGPD</strong> et à la loi tunisienne (<strong>INPDP</strong>), vous disposez d'un droit d'accès, de rectification et d'effacement de vos données.
          </p>
          <p class="mt-2">
            Pour toute demande, contactez le DPO à l'adresse : <a
              href="mailto:labo.maths@ert.tn"
              class="text-blue-600 hover:underline"
            >labo.maths@ert.tn</a>
          </p>
        </section>

        <section class="consent-box">
          <p>
            <strong>Consentement :</strong> Le fait de se connecter à la plateforme vaut acceptation de la présente charte pour la durée du traitement des examens.
          </p>
        </section>

        <div class="footer-info">
          <p>Développé avec ❤️ par le Labo Maths ERT</p>
          <p>Propriété du Lycée Pierre Mendès France</p>
        </div>
      </div>

      <div class="modal-footer">
        <button
          class="btn-decline"
          @click="handleDecline"
        >
          Refuser
        </button>
        <button
          class="btn-accept"
          @click="handleAccept"
        >
          J'accepte la charte
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 9999;
  padding: 1rem;
}

.modal-content {
  background: white;
  border-radius: 8px;
  max-width: 700px;
  width: 100%;
  max-height: 90vh;
  display: flex;
  flex-direction: column;
  box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
}

.modal-header {
  padding: 1.5rem;
  border-bottom: 1px solid #e5e7eb;
}

.modal-header h2 {
  font-size: 1.25rem;
  font-weight: 600;
  margin: 0 0 0.5rem 0;
  color: #111827;
}

.modal-body {
  padding: 1.5rem;
  overflow-y: auto;
  flex: 1;
}

.modal-body section {
  margin-bottom: 1.5rem;
}

.modal-body h3 {
  font-size: 1rem;
  font-weight: 600;
  color: #1f2937;
  margin-bottom: 0.5rem;
}

.modal-body p {
  font-size: 0.875rem;
  line-height: 1.5;
  color: #374151;
  margin-bottom: 0.5rem;
}

.modal-body ul,
.modal-body ol {
  font-size: 0.875rem;
  line-height: 1.5;
  color: #374151;
  margin-left: 1.5rem;
  margin-top: 0.5rem;
}

.modal-body ul {
  list-style-type: disc;
}

.modal-body ol {
  list-style-type: decimal;
}

.modal-body li {
  margin-bottom: 0.25rem;
}

.consent-box {
  background-color: #f9fafb;
  padding: 1rem;
  border-radius: 6px;
  border: 1px solid #e5e7eb;
}

.consent-box p {
  font-size: 0.875rem;
  color: #374151;
  margin: 0;
}

.footer-info {
  margin-top: 1rem;
  padding-top: 1rem;
  border-top: 1px solid #e5e7eb;
  font-size: 0.75rem;
  color: #6b7280;
}

.footer-info p {
  margin: 0.25rem 0;
}

.modal-footer {
  padding: 1rem 1.5rem;
  border-top: 1px solid #e5e7eb;
  display: flex;
  justify-content: flex-end;
  gap: 1rem;
}

.btn-decline,
.btn-accept {
  padding: 0.625rem 1.25rem;
  border-radius: 6px;
  font-weight: 600;
  font-size: 0.875rem;
  cursor: pointer;
  transition: all 0.2s;
  border: none;
}

.btn-decline {
  background-color: #f3f4f6;
  color: #374151;
}

.btn-decline:hover {
  background-color: #e5e7eb;
}

.btn-accept {
  background-color: #2563eb;
  color: white;
}

.btn-accept:hover {
  background-color: #1d4ed8;
}

.mt-2 {
  margin-top: 0.5rem;
}
</style>
