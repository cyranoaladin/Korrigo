<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const authStore = useAuthStore()

const username = ref('')
const password = ref('')
const error = ref('')
const isLoading = ref(false)

const handleLogin = async () => {
    isLoading.value = true
    error.value = ''
    
    const success = await authStore.login(username.value, password.value)
    
    isLoading.value = false
    
    if (success) {
        // Redirect based on role
        if (authStore.user?.role === 'Admin') {
            router.push('/admin-dashboard')
        } else {
            router.push('/corrector-dashboard')
        }
    } else {
        error.value = "Identifiants incorrects."
    }
}
</script>

<template>
  <div class="login-container">
    <div class="login-card">
      <div class="brand">
        <img
          src="/images/Korrigo.png"
          alt="Korrigo Logo"
          class="logo-img"
        >
        <h1>Korrigo</h1>
        <p>Plateforme de Correction Numérique</p>
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
            placeholder="admin"
          >
        </div>
                
        <div class="form-group">
          <label>Mot de passe</label>
          <input
            v-model="password"
            data-testid="login.password"
            type="password"
            required
            placeholder="••••••••"
          >
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
}

.brand { text-align: center; margin-bottom: 2rem; display: flex; flex-direction: column; align-items: center; gap: 0.5rem; }
.logo-img { height: 64px; width: auto; margin-bottom: 0.5rem; }
.brand h1 { font-size: 2rem; font-weight: 800; color: #111827; margin: 0; letter-spacing: -0.025em; }
.brand p { color: #6b7280; font-size: 0.875rem; margin-top: 0; }
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
</style>
