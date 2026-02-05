<script setup>
import { ref, computed } from 'vue'
import api from '../services/api'

const props = defineProps({
  forced: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['close', 'success'])

const currentPassword = ref('')
const newPassword = ref('')
const confirmPassword = ref('')
const error = ref('')
const isLoading = ref(false)
const currentPasswordVisible = ref(false)
const passwordVisible = ref(false)
const confirmVisible = ref(false)

const passwordsMatch = computed(() => {
  return newPassword.value === confirmPassword.value
})

const canSubmit = computed(() => {
  return currentPassword.value && newPassword.value.length >= 8 && passwordsMatch.value && !isLoading.value
})

const handleSubmit = async () => {
  error.value = ''

  if (!currentPassword.value) {
    error.value = 'Le mot de passe actuel est requis.'
    return
  }

  if (!passwordsMatch.value) {
    error.value = 'Les mots de passe ne correspondent pas.'
    return
  }

  if (newPassword.value.length < 8) {
    error.value = 'Le mot de passe doit contenir au moins 8 caractères.'
    return
  }

  isLoading.value = true

  try {
    await api.post('/change-password/', { 
      current_password: currentPassword.value,
      new_password: newPassword.value 
    })
    emit('success')
  } catch (e) {
    if (e.response?.data?.error) {
      error.value = Array.isArray(e.response.data.error) 
        ? e.response.data.error.join(' ')
        : e.response.data.error
    } else {
      error.value = 'Erreur lors du changement de mot de passe.'
    }
  } finally {
    isLoading.value = false
  }
}

const handleClose = () => {
  if (!props.forced) {
    emit('close')
  }
}
</script>

<template>
  <div 
    class="modal-overlay"
    @click.self="handleClose"
  >
    <div class="modal-content">
      <div class="modal-header">
        <h2>{{ forced ? 'Changement de mot de passe requis' : 'Changer le mot de passe' }}</h2>
        <button
          v-if="!forced"
          class="close-btn"
          aria-label="Fermer"
          @click="handleClose"
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            width="24"
            height="24"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
          >
            <line
              x1="18"
              y1="6"
              x2="6"
              y2="18"
            />
            <line
              x1="6"
              y1="6"
              x2="18"
              y2="18"
            />
          </svg>
        </button>
      </div>

      <div class="modal-body">
        <p
          v-if="forced"
          class="warning-message"
        >
          Vous devez changer votre mot de passe pour continuer.
        </p>

        <form @submit.prevent="handleSubmit">
          <div class="form-group">
            <label for="current-password">Mot de passe actuel</label>
            <div class="password-input-wrapper">
              <input
                id="current-password"
                v-model="currentPassword"
                :type="currentPasswordVisible ? 'text' : 'password'"
                required
                placeholder="Votre mot de passe actuel"
              >
              <button
                type="button"
                class="password-toggle"
                :aria-label="currentPasswordVisible ? 'Masquer' : 'Afficher'"
                @click="currentPasswordVisible = !currentPasswordVisible"
              >
                <svg
                  v-if="!currentPasswordVisible"
                  xmlns="http://www.w3.org/2000/svg"
                  width="20"
                  height="20"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="2"
                >
                  <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
                  <circle
                    cx="12"
                    cy="12"
                    r="3"
                  />
                </svg>
                <svg
                  v-else
                  xmlns="http://www.w3.org/2000/svg"
                  width="20"
                  height="20"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="2"
                >
                  <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24" />
                  <line
                    x1="1"
                    y1="1"
                    x2="23"
                    y2="23"
                  />
                </svg>
              </button>
            </div>
          </div>

          <div class="form-group">
            <label for="new-password">Nouveau mot de passe</label>
            <div class="password-input-wrapper">
              <input
                id="new-password"
                v-model="newPassword"
                :type="passwordVisible ? 'text' : 'password'"
                required
                minlength="8"
                placeholder="Minimum 8 caractères"
              >
              <button
                type="button"
                class="password-toggle"
                :aria-label="passwordVisible ? 'Masquer' : 'Afficher'"
                @click="passwordVisible = !passwordVisible"
              >
                <svg
                  v-if="!passwordVisible"
                  xmlns="http://www.w3.org/2000/svg"
                  width="20"
                  height="20"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="2"
                >
                  <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
                  <circle
                    cx="12"
                    cy="12"
                    r="3"
                  />
                </svg>
                <svg
                  v-else
                  xmlns="http://www.w3.org/2000/svg"
                  width="20"
                  height="20"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="2"
                >
                  <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24" />
                  <line
                    x1="1"
                    y1="1"
                    x2="23"
                    y2="23"
                  />
                </svg>
              </button>
            </div>
          </div>

          <div class="form-group">
            <label for="confirm-password">Confirmer le mot de passe</label>
            <div class="password-input-wrapper">
              <input
                id="confirm-password"
                v-model="confirmPassword"
                :type="confirmVisible ? 'text' : 'password'"
                required
                minlength="8"
                placeholder="Retapez le mot de passe"
              >
              <button
                type="button"
                class="password-toggle"
                :aria-label="confirmVisible ? 'Masquer' : 'Afficher'"
                @click="confirmVisible = !confirmVisible"
              >
                <svg
                  v-if="!confirmVisible"
                  xmlns="http://www.w3.org/2000/svg"
                  width="20"
                  height="20"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="2"
                >
                  <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
                  <circle
                    cx="12"
                    cy="12"
                    r="3"
                  />
                </svg>
                <svg
                  v-else
                  xmlns="http://www.w3.org/2000/svg"
                  width="20"
                  height="20"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="2"
                >
                  <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24" />
                  <line
                    x1="1"
                    y1="1"
                    x2="23"
                    y2="23"
                  />
                </svg>
              </button>
            </div>
            <span
              v-if="confirmPassword && !passwordsMatch"
              class="error-hint"
            >
              Les mots de passe ne correspondent pas
            </span>
          </div>

          <div
            v-if="error"
            class="error-message"
          >
            {{ error }}
          </div>

          <div class="modal-actions">
            <button
              v-if="!forced"
              type="button"
              class="btn-secondary"
              @click="handleClose"
            >
              Annuler
            </button>
            <button
              type="submit"
              class="btn-primary"
              :disabled="!canSubmit"
            >
              {{ isLoading ? 'Enregistrement...' : 'Changer le mot de passe' }}
            </button>
          </div>
        </form>
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
  justify-content: center;
  align-items: center;
  z-index: 9999;
}

.modal-content {
  background: white;
  border-radius: 8px;
  box-shadow: 0 10px 25px rgba(0, 0, 0, 0.2);
  width: 90%;
  max-width: 500px;
  max-height: 90vh;
  overflow-y: auto;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1.5rem;
  border-bottom: 1px solid #e5e7eb;
}

.modal-header h2 {
  margin: 0;
  font-size: 1.25rem;
  font-weight: 600;
  color: #111827;
}

.close-btn {
  background: none;
  border: none;
  cursor: pointer;
  padding: 0.25rem;
  color: #6b7280;
  transition: color 0.15s;
  display: flex;
  align-items: center;
}

.close-btn:hover {
  color: #374151;
}

.modal-body {
  padding: 1.5rem;
}

.warning-message {
  background: #fef3c7;
  border-left: 4px solid #f59e0b;
  padding: 0.75rem 1rem;
  margin-bottom: 1.5rem;
  color: #92400e;
  font-size: 0.875rem;
  border-radius: 4px;
}

.form-group {
  margin-bottom: 1.25rem;
}

.form-group label {
  display: block;
  font-size: 0.875rem;
  font-weight: 500;
  color: #374151;
  margin-bottom: 0.5rem;
}

.password-input-wrapper {
  position: relative;
  display: flex;
  align-items: center;
}

.password-input-wrapper input {
  flex: 1;
  padding: 0.625rem;
  padding-right: 2.5rem;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  font-size: 0.95rem;
  transition: border-color 0.15s;
}

.password-input-wrapper input:focus {
  outline: none;
  border-color: #2563eb;
  box-shadow: 0 0 0 2px #dbeafe;
}

.password-toggle {
  position: absolute;
  right: 0.5rem;
  background: none;
  border: none;
  cursor: pointer;
  padding: 0.25rem;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #6b7280;
  transition: color 0.15s;
}

.password-toggle:hover {
  color: #374151;
}

.error-hint {
  display: block;
  margin-top: 0.25rem;
  font-size: 0.75rem;
  color: #dc2626;
}

.error-message {
  color: #dc2626;
  font-size: 0.875rem;
  background: #fee2e2;
  padding: 0.75rem;
  border-radius: 4px;
  margin-bottom: 1rem;
}

.modal-actions {
  display: flex;
  gap: 0.75rem;
  justify-content: flex-end;
  margin-top: 1.5rem;
}

.btn-primary,
.btn-secondary {
  padding: 0.625rem 1.25rem;
  border-radius: 6px;
  font-weight: 600;
  font-size: 0.875rem;
  cursor: pointer;
  transition: all 0.2s;
  border: none;
}

.btn-primary {
  background-color: #2563eb;
  color: white;
}

.btn-primary:hover:not(:disabled) {
  background-color: #1d4ed8;
}

.btn-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-secondary {
  background-color: #f3f4f6;
  color: #374151;
}

.btn-secondary:hover {
  background-color: #e5e7eb;
}
</style>
