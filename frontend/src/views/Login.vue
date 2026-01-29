<script setup>
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const props = defineProps({
  roleContext: {
    type: String,
    default: ''
  }
})

const router = useRouter()
const authStore = useAuthStore()

const username = ref('')
const password = ref('')
const error = ref('')
const isLoading = ref(false)
const passwordVisible = ref(false)

const title = computed(() => {
    if (props.roleContext === 'Admin') return 'Administration'
    if (props.roleContext === 'Teacher') return 'Espace Enseignant'
    return 'Connexion'
})

const handleLogin = async () => {
    isLoading.value = true
    error.value = ''
    
    const success = await authStore.login(username.value, password.value)
    
    isLoading.value = false
    
    if (success) {
        // Redirect based on ACTUAL role from backend
        if (authStore.user?.role === 'Admin') {
            router.push('/admin-dashboard')
        } else if (authStore.user?.role === 'Teacher') {
            router.push('/corrector-dashboard')
        } else {
             // Fallback
             router.push('/')
        }
    } else {
        error.value = "Identifiants incorrects."
    }
}
</script>

<template>
  <div class="login-container">
    <div 
      class="login-card"
      :class="{
        'role-admin': props.roleContext === 'Admin',
        'role-teacher': props.roleContext === 'Teacher'
      }"
    >
      <div class="brand">
        <img
          src="/images/Korrigo.png"
          alt="Korrigo Logo"
          class="logo-img"
        >
        <h1>Korrigo</h1>
        <p>{{ title }}</p>
      </div>
            
      <form
        class="login-form"
        @submit.prevent="handleLogin"
      >
        <div class="form-group">
          <label>Identifiant / Email</label>
          <input
            v-model="username"
            data-testid="login.username"
            type="text"
            required
            :placeholder="props.roleContext === 'Admin' ? 'admin' : 'enseignant'"
          >
        </div>
                
        <div class="form-group">
          <label>Mot de passe</label>
          <div class="password-input-wrapper">
            <input
              v-model="password"
              data-testid="login.password"
              :type="passwordVisible ? 'text' : 'password'"
              required
              placeholder="••••••••"
            >
            <button
              type="button"
              class="password-toggle"
              :aria-label="passwordVisible ? 'Masquer le mot de passe' : 'Afficher le mot de passe'"
              :title="passwordVisible ? 'Masquer le mot de passe' : 'Afficher le mot de passe'"
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
                stroke-linecap="round"
                stroke-linejoin="round"
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
                stroke-linecap="round"
                stroke-linejoin="round"
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
                
        <div
          v-if="error"
          class="error-message"
          data-testid="login.error"
        >
          {{ error }}
        </div>
                
        <button
          data-testid="login.submit"
          type="submit"
          class="btn-primary"
          :disabled="isLoading"
        >
          {{ isLoading ? 'Connexion en cours...' : 'Se connecter' }}
        </button>
      </form>

      <div class="footer-links">
        <router-link to="/">
          ← Retour à l'accueil
        </router-link>
      </div>

      <footer class="attribution">
        Concepteur : Aleddine BEN RHOUMA – Labo Maths ERT
      </footer>
    </div>
  </div>
</template>

<style scoped>
.login-container {
    height: 100vh;
    display: flex;
    justify-content: center;
    align-items: center;
    background-color: #f3f4f6;
    font-family: 'Inter', sans-serif;
}

.login-card {
    background: white;
    padding: 2.5rem;
    border-radius: 8px;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
    width: 100%;
    max-width: 400px;
    border-top: 4px solid #cbd5e1; /* Default */
}
.login-card.role-admin { border-top-color: #ef4444; }
.login-card.role-teacher { border-top-color: #3b82f6; }

.brand { text-align: center; margin-bottom: 2rem; display: flex; flex-direction: column; align-items: center; gap: 0.5rem; }
.logo-img { height: 64px; width: auto; margin-bottom: 0.5rem; }
.brand h1 { font-size: 2rem; font-weight: 800; color: #111827; margin: 0; letter-spacing: -0.025em; }
.brand p { color: #6b7280; font-size: 1rem; font-weight: 500; margin-top: 0; }
.attribution { margin-top: 2rem; padding-top: 1rem; border-top: 1px solid #f3f4f6; text-align: center; font-size: 0.75rem; color: #9ca3af; }

.login-form { display: flex; flex-direction: column; gap: 1.25rem; }

.form-group { display: flex; flex-direction: column; gap: 0.5rem; }
.form-group label { font-size: 0.875rem; font-weight: 500; color: #374151; }
.form-group input {
    padding: 0.625rem;
    border: 1px solid #d1d5db;
    border-radius: 6px;
    font-size: 0.95rem;
    transition: border-color 0.15s;
}
.form-group input:focus { outline: none; border-color: #2563eb; box-shadow: 0 0 0 2px #dbeafe; }

.password-input-wrapper {
    position: relative;
    display: flex;
    align-items: center;
}
.password-input-wrapper input {
    flex: 1;
    padding-right: 2.5rem;
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
.password-toggle:focus {
    outline: 2px solid #2563eb;
    outline-offset: 2px;
    border-radius: 4px;
}

.btn-primary {
    background-color: #2563eb;
    color: white;
    padding: 0.75rem;
    border: none;
    border-radius: 6px;
    font-weight: 600;
    cursor: pointer;
    transition: background-color 0.2s;
}
.btn-primary:hover:not(:disabled) { background-color: #1d4ed8; }
.btn-primary:disabled { opacity: 0.7; cursor: not-allowed; }

.error-message {
    color: #dc2626;
    font-size: 0.875rem;
    text-align: center;
    background: #fee2e2;
    padding: 0.5rem;
    border-radius: 4px;
}

.footer-links {
    margin-top: 1.5rem;
    text-align: center;
}
.footer-links a {
    color: #6b7280;
    text-decoration: none;
    font-size: 0.9rem;
}
.footer-links a:hover {
    color: #1f2937;
    text-decoration: underline;
}
</style>
