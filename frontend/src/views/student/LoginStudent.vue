<script setup>
import { ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../../stores/auth'
import { getErrorMessage } from '../../utils/errorMessages'

const email = ref('')
const password = ref('')
const passwordVisible = ref(false)
const error = ref('')
const loading = ref(false)
const authStore = useAuthStore()
const router = useRouter()

watch(() => authStore.lastError, (newError) => {
    if (newError) {
        error.value = newError
    }
})

const handleLogin = async () => {
    error.value = ''
    loading.value = true
    authStore.clearError()
    
    try {
        const success = await authStore.loginStudent(email.value, password.value)
        if (success) {
            if (authStore.mustChangePassword) {
                router.push('/student/change-password')
            } else {
                router.push('/student-portal')
            }
        } else {
            error.value = authStore.lastError || "Email ou mot de passe incorrect."
        }
    } catch (err) {
        error.value = getErrorMessage(err)
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
          <label>Adresse email</label>
          <input
            v-model="email"
            type="email"
            placeholder="prenom.nom-e@ert.tn"
            required
            autocomplete="email"
          >
        </div>
        
        <div class="form-group">
          <label>Mot de passe</label>
          <div class="password-field">
            <input
              v-model="password"
              :type="passwordVisible ? 'text' : 'password'"
              placeholder="Entrez votre mot de passe"
              required
              autocomplete="current-password"
            >
            <button
              type="button"
              class="btn-toggle-password"
              @click="passwordVisible = !passwordVisible"
            >
              {{ passwordVisible ? '🙈' : '👁️' }}
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
          {{ loading ? 'Connexion...' : 'Accéder à mes copies' }}
        </button>
      </form>

      <p class="hint-text">
        Mot de passe par défaut : <strong>passe123</strong><br>
        Vous serez invité à le changer à la première connexion.
      </p>
            
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
    height: 100vh;
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
    box-shadow: 0 10px 25px rgba(0,0,0,0.2);
    width: 100%;
    max-width: 400px;
}

h1 { color: #2d3748; margin-bottom: 0.5rem; text-align: center; }
.subtitle { color: #718096; text-align: center; margin-bottom: 2rem; }

.form-group { margin-bottom: 1.5rem; }
label { display: block; margin-bottom: 0.5rem; color: #4a5568; font-weight: 500; font-size: 0.9rem; }
input {
    width: 100%;
    padding: 0.75rem;
    border: 1px solid #e2e8f0;
    border-radius: 6px;
    font-size: 1rem;
    outline: none;
    transition: border-color 0.2s;
}
input:focus { border-color: #667eea; box-shadow: 0 0 0 2px #667eea; outline: none; }

.btn-login {
    width: 100%;
    padding: 0.8rem;
    background: #667eea;
    color: white;
    border: none;
    border-radius: 6px;
    font-weight: 600;
    cursor: pointer;
    transition: background 0.2s;
}
.btn-login:hover { background: #5a67d8; }
.btn-login:disabled { opacity: 0.6; cursor: not-allowed; }
.error-msg { color: #e53e3e; text-align: center; margin-bottom: 1rem; font-size: 0.9rem; }

.password-field { position: relative; display: flex; align-items: center; }
.password-field input { padding-right: 3rem; }
.btn-toggle-password {
    position: absolute;
    right: 8px;
    background: none;
    border: none;
    cursor: pointer;
    font-size: 1.1rem;
    padding: 4px;
    line-height: 1;
}

.hint-text {
    text-align: center;
    font-size: 0.8rem;
    color: #a0aec0;
    margin-top: 1rem;
    line-height: 1.5;
}
.hint-text strong { color: #718096; }

.footer-links { text-align: center; margin-top: 1.5rem; font-size: 0.9rem; }
.footer-links a { color: #718096; text-decoration: none; }
.footer-links a:hover { text-decoration: underline; }
</style>
