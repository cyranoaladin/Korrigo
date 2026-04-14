<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../../stores/auth'
import api from '../../services/api'
import AppIcon from '../../icons/AppIcon.vue'

const currentPassword = ref('')
const newPassword = ref('')
const confirmPassword = ref('')
const error = ref('')
const success = ref(false)
const loading = ref(false)
const showCurrent = ref(false)
const showNew = ref(false)

const authStore = useAuthStore()
const router = useRouter()

const handleChangePassword = async () => {
    error.value = ''
    success.value = false

    if (!currentPassword.value || !newPassword.value || !confirmPassword.value) {
        error.value = 'Tous les champs sont requis.'
        return
    }

    if (newPassword.value !== confirmPassword.value) {
        error.value = 'Les mots de passe ne correspondent pas.'
        return
    }

    if (newPassword.value.length < 12) {
        error.value = 'Le mot de passe doit contenir au moins 12 caractères.'
        return
    }

    if (newPassword.value === currentPassword.value) {
        error.value = 'Le nouveau mot de passe doit être différent du mot de passe actuel.'
        return
    }

    loading.value = true
    try {
        await api.post('/students/change-password/', {
            current_password: currentPassword.value,
            new_password: newPassword.value,
        })
        success.value = true
        authStore.clearMustChangePassword()

        setTimeout(() => {
            router.push('/student-portal')
        }, 2000)
    } catch (err) {
        const data = err.response?.data
        if (data?.error) {
            error.value = Array.isArray(data.error) ? data.error.join(' ') : data.error
        } else {
            error.value = 'Erreur lors du changement de mot de passe.'
        }
    } finally {
        loading.value = false
    }
}
</script>

<template>
  <div class="change-pw-container">
    <div class="change-pw-box">
      <h1>Changer votre mot de passe</h1>
      <p class="subtitle">
        Pour sécuriser votre compte, veuillez choisir un nouveau mot de passe.
      </p>

      <div
        v-if="success"
        class="success-msg"
      >
        Mot de passe modifié avec succès ! Redirection...
      </div>

      <form
        v-else
        @submit.prevent="handleChangePassword"
      >
        <div class="form-group">
          <label>Mot de passe actuel</label>
          <div class="password-field">
            <input
              v-model="currentPassword"
              :type="showCurrent ? 'text' : 'password'"
              placeholder="Votre mot de passe actuel"
              required
              autocomplete="current-password"
            >
            <button
              type="button"
              class="btn-toggle"
              @click="showCurrent = !showCurrent"
            >
              <AppIcon
                :name="showCurrent ? 'eye-off' : 'eye'"
                :size="18"
              />
            </button>
          </div>
        </div>

        <div class="form-group">
          <label>Nouveau mot de passe</label>
          <div class="password-field">
            <input
              v-model="newPassword"
              :type="showNew ? 'text' : 'password'"
              placeholder="Minimum 12 caractères"
              required
              autocomplete="new-password"
            >
            <button
              type="button"
              class="btn-toggle"
              @click="showNew = !showNew"
            >
              <AppIcon
                :name="showNew ? 'eye-off' : 'eye'"
                :size="18"
              />
            </button>
          </div>
        </div>

        <div class="password-rules">
          <p>Le mot de passe doit :</p>
          <ul>
            <li :class="{ 'rule-ok': newPassword.length >= 12 }">
              Contenir au moins 12 caractères
            </li>
            <li :class="{ 'rule-ok': !/^\d+$/.test(newPassword) && newPassword.length > 0 }">
              Ne pas être entièrement numérique
            </li>
            <li :class="{ 'rule-ok': newPassword.length > 0 && newPassword !== currentPassword }">
              Ne pas être identique au mot de passe initial
            </li>
          </ul>
        </div>

        <div class="form-group">
          <label>Confirmer le nouveau mot de passe</label>
          <input
            v-model="confirmPassword"
            type="password"
            placeholder="Retapez le nouveau mot de passe"
            required
            autocomplete="new-password"
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
          :disabled="loading"
          class="btn-submit"
        >
          {{ loading ? 'Enregistrement...' : 'Changer le mot de passe' }}
        </button>
      </form>

      <div class="footer-links">
        <router-link
          to="/student-portal"
          class="skip-link"
        >
          <span>Passer pour le moment</span>
          <AppIcon
            name="arrow-right"
            :size="16"
          />
        </router-link>
      </div>
    </div>
  </div>
</template>

<style scoped>
.change-pw-container {
    min-height: 100vh;
    display: flex;
    justify-content: center;
    align-items: center;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    font-family: 'Inter', sans-serif;
    padding: 1rem;
    box-sizing: border-box;
}

.change-pw-box {
    background: white;
    padding: 2.5rem;
    border-radius: 12px;
    box-shadow: 0 10px 25px rgba(0,0,0,0.2);
    width: 100%;
    max-width: 420px;
    box-sizing: border-box;
}

h1 { color: #2d3748; margin-bottom: 0.5rem; text-align: center; font-size: 1.4rem; }
.subtitle { color: #718096; text-align: center; margin-bottom: 2rem; font-size: 0.9rem; }

.form-group { margin-bottom: 1.25rem; }
label { display: block; margin-bottom: 0.5rem; color: #4a5568; font-weight: 500; font-size: 0.9rem; }
input {
    width: 100%;
    padding: 0.75rem;
    border: 1px solid #e2e8f0;
    border-radius: 6px;
    font-size: 16px;
    outline: none;
    transition: border-color 0.2s;
    box-sizing: border-box;
    -webkit-appearance: none;
}
input:focus { border-color: #667eea; box-shadow: 0 0 0 2px rgba(102,126,234,0.2); }

.password-field { position: relative; display: flex; align-items: center; }
.password-field input { padding-right: 3rem; }
.btn-toggle {
    position: absolute;
    right: 8px;
    background: none;
    border: none;
    cursor: pointer;
    font-size: 1.1rem;
    padding: 4px;
    line-height: 1;
}

.btn-submit {
    width: 100%;
    padding: 0.8rem;
    background: #667eea;
    color: white;
    border: none;
    border-radius: 6px;
    font-weight: 600;
    cursor: pointer;
    transition: background 0.2s;
    margin-top: 0.5rem;
}
.btn-submit:hover { background: #5a67d8; }
.btn-submit:disabled { opacity: 0.6; cursor: not-allowed; }

.error-msg { color: #e53e3e; text-align: center; margin-bottom: 1rem; font-size: 0.9rem; }
.success-msg {
    text-align: center;
    color: #38a169;
    font-weight: 600;
    padding: 1.5rem;
    background: #f0fff4;
    border-radius: 8px;
    border: 1px solid #c6f6d5;
}

.footer-links { text-align: center; margin-top: 1.5rem; font-size: 0.85rem; }
.skip-link { color: #a0aec0; text-decoration: none; display: inline-flex; align-items: center; gap: 0.5rem; justify-content: center; }
.skip-link:hover { text-decoration: underline; color: #718096; }
</style>
