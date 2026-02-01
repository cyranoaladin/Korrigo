<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../../stores/auth'

const email = ref('')
const password = ref('')
const showPassword = ref(false)
const error = ref('')
const loading = ref(false)
const authStore = useAuthStore()
const router = useRouter()

const handleLogin = async () => {
    error.value = ''
    loading.value = true

    try {
        const result = await authStore.loginStudent(email.value, password.value)

        if (result.success) {
            // Vérifier si changement de mot de passe requis
            if (result.must_change_password) {
                router.push('/student/change-password')
            } else {
                router.push('/student-portal')
            }
        } else {
            error.value = result.error || 'Identifiants invalides'
        }
    } catch (err) {
        console.error('Login error:', err)

        if (err.response?.status === 429) {
            const retryAfter = err.response.data.retry_after
            error.value = `Compte temporairement verrouillé. Réessayez dans ${retryAfter} secondes.`
        } else if (err.response?.status === 401) {
            error.value = 'Email ou mot de passe incorrect'
        } else {
            error.value = 'Erreur de connexion. Veuillez réessayer.'
        }
    } finally {
        loading.value = false
    }
}
</script>

<template>
  <div class="login-container">
    <div class="login-box">
      <h1>Espace Élève</h1>
      <p class="subtitle">
        Consultez vos copies corrigées
      </p>

      <form @submit.prevent="handleLogin">
        <div class="form-group">
          <label for="email">Adresse email</label>
          <input
            id="email"
            v-model="email"
            type="email"
            placeholder="votre.email@example.com"
            required
            autofocus
          >
        </div>

        <div class="form-group">
          <label for="password">Mot de passe</label>
          <div class="password-input">
            <input
              id="password"
              v-model="password"
              :type="showPassword ? 'text' : 'password'"
              placeholder="••••••••"
              required
            >
            <button
              type="button"
              class="toggle-password"
              @click="showPassword = !showPassword"
              tabindex="-1"
            >
              <span v-if="showPassword">👁️</span>
              <span v-else>👁️‍🗨️</span>
            </button>
          </div>
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
          class="btn-login"
        >
          {{ loading ? 'Connexion...' : 'Se connecter' }}
        </button>
      </form>

      <div class="footer-links">
        <router-link to="/">
          ← Retour à l'accueil
        </router-link>
      </div>
    </div>
  </div>
</template>

<style scoped>
.login-container {
    min-height: 100vh;
    display: flex;
    justify-content: center;
    align-items: center;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    font-family: 'Inter', sans-serif;
}

.login-box {
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
    font-size: 1.75rem;
    text-align: center;
}

.subtitle {
    color: #718096;
    text-align: center;
    margin: 0 0 2rem 0;
    font-size: 0.9rem;
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

input[type="email"],
input[type="password"],
input[type="text"] {
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

.password-input {
    position: relative;
    display: flex;
    align-items: center;
}

.password-input input {
    flex: 1;
    padding-right: 40px;
}

.toggle-password {
    position: absolute;
    right: 8px;
    background: none;
    border: none;
    cursor: pointer;
    padding: 8px;
    font-size: 1.125rem;
    opacity: 0.6;
    transition: opacity 0.2s;
}

.toggle-password:hover {
    opacity: 1;
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

.btn-login {
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

.btn-login:hover:not(:disabled) {
    background: #5568d3;
}

.btn-login:disabled {
    opacity: 0.6;
    cursor: not-allowed;
}

.footer-links {
    text-align: center;
    margin-top: 1.5rem;
    font-size: 0.875rem;
}

.footer-links a {
    color: #667eea;
    text-decoration: none;
}

.footer-links a:hover {
    text-decoration: underline;
}
</style>
