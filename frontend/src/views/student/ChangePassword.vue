<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import api from '@/services/api'

const newPassword = ref('')
const confirmPassword = ref('')
const error = ref('')
const loading = ref(false)

const router = useRouter()

const handleSubmit = async () => {
    error.value = ''

    // Validation
    if (newPassword.value !== confirmPassword.value) {
        error.value = 'Les mots de passe ne correspondent pas'
        return
    }

    if (newPassword.value.length < 8) {
        error.value = 'Le mot de passe doit contenir au moins 8 caractères'
        return
    }

    loading.value = true

    try {
        await api.post('/change-password/', {
            password: newPassword.value
        })

        // Succès - rediriger vers le portail
        router.push('/student-portal')
    } catch (err) {
        console.error('Password change error:', err)

        if (err.response?.data?.error) {
            error.value = Array.isArray(err.response.data.error)
                ? err.response.data.error.join(', ')
                : err.response.data.error
        } else {
            error.value = 'Erreur lors du changement de mot de passe'
        }
    } finally {
        loading.value = false
    }
}
</script>

<template>
  <div class="change-password-container">
    <div class="change-password-box">
      <h1>Changement de mot de passe requis</h1>
      <p class="subtitle">
        Pour des raisons de sécurité, veuillez choisir un nouveau mot de passe.
      </p>

      <form @submit.prevent="handleSubmit">
        <div class="form-group">
          <label for="new-password">Nouveau mot de passe</label>
          <input
            id="new-password"
            v-model="newPassword"
            type="password"
            placeholder="Minimum 8 caractères"
            required
            minlength="8"
            autofocus
          >
          <div class="help-text">
            Le mot de passe doit contenir au moins 8 caractères
          </div>
        </div>

        <div class="form-group">
          <label for="confirm-password">Confirmer le mot de passe</label>
          <input
            id="confirm-password"
            v-model="confirmPassword"
            type="password"
            placeholder="Retaper le mot de passe"
            required
          >
        </div>

        <div
          v-if="error"
          class="error-msg"
        >
          {{ error }}
        </div>

        <button
          type="submit"
          class="btn-submit"
          :disabled="loading"
        >
          {{ loading ? 'Modification...' : 'Modifier le mot de passe' }}
        </button>
      </form>
    </div>
  </div>
</template>

<style scoped>
.change-password-container {
    min-height: 100vh;
    display: flex;
    justify-content: center;
    align-items: center;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    font-family: 'Inter', sans-serif;
}

.change-password-box {
    background: white;
    padding: 2.5rem;
    border-radius: 12px;
    box-shadow: 0 10px 40px rgba(0, 0, 0, 0.2);
    width: 100%;
    max-width: 400px;
}

h1 {
    color: #2d3748;
    margin: 0 0 0.5rem 0;
    font-size: 1.5rem;
    text-align: center;
}

.subtitle {
    color: #718096;
    text-align: center;
    margin: 0 0 2rem 0;
    font-size: 0.875rem;
    line-height: 1.5;
}

.form-group {
    margin-bottom: 1.25rem;
}

label {
    display: block;
    margin-bottom: 0.5rem;
    color: #2d3748;
    font-weight: 500;
    font-size: 0.875rem;
}

input[type="password"] {
    width: 100%;
    padding: 0.75rem;
    border: 1px solid #cbd5e0;
    border-radius: 6px;
    font-size: 0.875rem;
    transition: border-color 0.2s;
}

input:focus {
    outline: none;
    border-color: #667eea;
    box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
}

.help-text {
    margin-top: 0.375rem;
    font-size: 0.75rem;
    color: #718096;
}

.error-msg {
    background: #fed7d7;
    color: #c53030;
    padding: 0.75rem;
    border-radius: 6px;
    margin-bottom: 1.25rem;
    font-size: 0.875rem;
    border: 1px solid #fc8181;
}

.btn-submit {
    width: 100%;
    padding: 0.8rem;
    background: #667eea;
    color: white;
    border: none;
    border-radius: 6px;
    font-size: 1rem;
    font-weight: 500;
    cursor: pointer;
    transition: background 0.2s;
}

.btn-submit:hover:not(:disabled) {
    background: #5568d3;
}

.btn-submit:disabled {
    opacity: 0.6;
    cursor: not-allowed;
}
</style>
