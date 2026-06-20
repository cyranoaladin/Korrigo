<script setup>
import AppIcon from '../../icons/AppIcon.vue'

defineProps({
  visible: { type: Boolean, default: false },
  targetLabel: { type: String, default: '' },
  targetDetail: { type: String, default: '' },
  mode: { type: String, default: 'user' },
  loading: { type: Boolean, default: false },
  successMessage: { type: String, default: '' },
  errorMessage: { type: String, default: '' },
})

const emit = defineEmits(['confirm', 'close'])
</script>

<template>
  <div
    v-if="visible"
    class="password-reset-overlay"
    data-testid="password-reset-dialog"
    role="dialog"
    aria-modal="true"
    aria-labelledby="password-reset-title"
    @click.self="!loading && emit('close')"
  >
    <section class="password-reset-card">
      <header class="password-reset-header">
        <div
          class="password-reset-icon"
          :class="{
            success: successMessage,
            error: errorMessage && !successMessage,
          }"
        >
          <AppIcon
            v-if="successMessage"
            name="success"
            :size="22"
          />
          <AppIcon
            v-else-if="errorMessage"
            name="alert"
            :size="22"
          />
          <AppIcon
            v-else
            name="key-round"
            :size="22"
          />
        </div>
        <div class="password-reset-title-block">
          <h2 id="password-reset-title">
            {{ successMessage ? 'Réinitialisation effectuée' : 'Réinitialiser le mot de passe' }}
          </h2>
          <p>
            {{ mode === 'student' ? 'Compte élève' : 'Compte utilisateur' }}
          </p>
        </div>
        <button
          class="password-reset-close"
          type="button"
          aria-label="Fermer"
          :disabled="loading"
          @click="emit('close')"
        >
          <AppIcon
            name="close"
            :size="18"
          />
        </button>
      </header>

      <div class="password-reset-body">
        <div class="target-box">
          <span class="target-label">Compte concerné</span>
          <strong>{{ targetLabel }}</strong>
          <small v-if="targetDetail">{{ targetDetail }}</small>
        </div>

        <div
          v-if="successMessage"
          class="status-box success"
          data-testid="password-reset-success"
        >
          <AppIcon
            name="success"
            :size="18"
          />
          <p>{{ successMessage }}</p>
        </div>

        <div
          v-else-if="errorMessage"
          class="status-box error"
          data-testid="password-reset-error"
        >
          <AppIcon
            name="alert"
            :size="18"
          />
          <p>{{ errorMessage }}</p>
        </div>

        <div
          v-else
          class="warning-copy"
        >
          <p>
            {{ mode === 'student'
              ? "Le mot de passe sera réinitialisé à la date de naissance enregistrée de l'élève."
              : 'Un mot de passe temporaire sera généré côté serveur.'
            }}
          </p>
          <p>
            L'utilisateur devra changer son mot de passe à sa prochaine connexion.
          </p>
          <p class="security-note">
            Aucun mot de passe ne sera affiché dans cette interface.
          </p>
        </div>
      </div>

      <footer class="password-reset-actions">
        <button
          class="btn-secondary"
          type="button"
          :disabled="loading"
          @click="emit('close')"
        >
          {{ successMessage ? 'Fermer' : 'Annuler' }}
        </button>
        <button
          v-if="!successMessage"
          class="btn-primary"
          type="button"
          :disabled="loading"
          data-testid="password-reset-confirm"
          @click="emit('confirm')"
        >
          <span
            v-if="loading"
            class="spinner"
            aria-hidden="true"
          />
          {{ loading ? 'Réinitialisation...' : 'Réinitialiser' }}
        </button>
      </footer>
    </section>
  </div>
</template>

<style scoped>
.password-reset-overlay {
  position: fixed;
  inset: 0;
  z-index: 10000;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 1rem;
  background: rgba(15, 23, 42, 0.62);
  backdrop-filter: blur(4px);
}

.password-reset-card {
  width: min(100%, 460px);
  max-height: calc(100vh - 2rem);
  overflow: auto;
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 24px 50px rgba(15, 23, 42, 0.24);
}

.password-reset-header {
  display: flex;
  align-items: flex-start;
  gap: 0.85rem;
  padding: 1.25rem 1.25rem 1rem;
  border-bottom: 1px solid #e2e8f0;
}

.password-reset-icon {
  display: inline-flex;
  width: 42px;
  height: 42px;
  align-items: center;
  justify-content: center;
  flex: 0 0 auto;
  border-radius: 8px;
  color: #b45309;
  background: #fffbeb;
  border: 1px solid #fde68a;
}

.password-reset-icon.success {
  color: #047857;
  background: #ecfdf5;
  border-color: #a7f3d0;
}

.password-reset-icon.error {
  color: #b91c1c;
  background: #fef2f2;
  border-color: #fecaca;
}

.password-reset-title-block {
  flex: 1;
  min-width: 0;
}

.password-reset-title-block h2 {
  margin: 0;
  color: #0f172a;
  font-size: 1.1rem;
  font-weight: 750;
  letter-spacing: 0;
}

.password-reset-title-block p {
  margin: 0.25rem 0 0;
  color: #64748b;
  font-size: 0.9rem;
}

.password-reset-close {
  display: inline-flex;
  min-width: 44px;
  min-height: 44px;
  align-items: center;
  justify-content: center;
  margin: -0.45rem -0.45rem 0 0;
  border: 0;
  border-radius: 8px;
  color: #64748b;
  background: transparent;
  cursor: pointer;
}

.password-reset-close:hover {
  color: #0f172a;
  background: #f1f5f9;
}

.password-reset-close:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.password-reset-body {
  padding: 1.25rem;
}

.target-box {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  padding: 0.9rem 1rem;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
}

.target-label {
  color: #64748b;
  font-size: 0.75rem;
  font-weight: 700;
  text-transform: uppercase;
}

.target-box strong {
  color: #0f172a;
  font-size: 1rem;
  overflow-wrap: anywhere;
}

.target-box small {
  color: #64748b;
  font-size: 0.85rem;
  line-height: 1.4;
}

.warning-copy {
  margin-top: 1rem;
  color: #334155;
  font-size: 0.95rem;
  line-height: 1.5;
}

.warning-copy p {
  margin: 0 0 0.75rem;
}

.security-note {
  padding: 0.75rem;
  color: #475569;
  background: #f8fafc;
  border-left: 3px solid #64748b;
  border-radius: 6px;
}

.status-box {
  display: flex;
  gap: 0.65rem;
  align-items: flex-start;
  margin-top: 1rem;
  padding: 0.85rem;
  border-radius: 8px;
  font-size: 0.95rem;
  line-height: 1.45;
}

.status-box p {
  margin: 0;
}

.status-box.success {
  color: #065f46;
  background: #ecfdf5;
  border: 1px solid #a7f3d0;
}

.status-box.error {
  color: #991b1b;
  background: #fef2f2;
  border: 1px solid #fecaca;
}

.password-reset-actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.75rem;
  padding: 1rem 1.25rem 1.25rem;
  border-top: 1px solid #e2e8f0;
}

.btn-primary,
.btn-secondary {
  min-height: 44px;
  padding: 0.65rem 1rem;
  border-radius: 8px;
  font-weight: 700;
  cursor: pointer;
}

.btn-primary {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  color: #fff;
  background: #2563eb;
  border: 1px solid #2563eb;
}

.btn-primary:hover {
  background: #1d4ed8;
}

.btn-secondary {
  color: #334155;
  background: #fff;
  border: 1px solid #cbd5e1;
}

.btn-secondary:hover {
  background: #f8fafc;
}

.btn-primary:disabled,
.btn-secondary:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.spinner {
  width: 16px;
  height: 16px;
  border: 2px solid rgba(255, 255, 255, 0.45);
  border-top-color: #fff;
  border-radius: 999px;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

@media (max-width: 520px) {
  .password-reset-overlay {
    align-items: flex-end;
    padding: 0.75rem;
  }

  .password-reset-card {
    width: 100%;
  }

  .password-reset-actions {
    flex-direction: column-reverse;
  }

  .btn-primary,
  .btn-secondary {
    width: 100%;
  }
}
</style>
