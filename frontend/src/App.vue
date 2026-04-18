<script setup>
import { computed, watch } from 'vue'
import { useAuthStore } from './stores/auth'
import { useTheme } from './composables/useTheme'
import api from './services/api'
import ChangePasswordModal from './components/ChangePasswordModal.vue'
import ToastContainer from './components/ToastContainer.vue'

useTheme() // Initialize theme (dark/light) from localStorage on app startup
const authStore = useAuthStore()

const showPasswordModal = computed(() => {
  return authStore.isAuthenticated && authStore.mustChangePassword
})

// BUG-04/PATCH-04 FIX: Fetch CSRF token if missing before showing the forced modal
watch(showPasswordModal, async (show) => {
  if (show && !document.cookie.includes('csrftoken')) {
    try {
      await api.get('/csrf/')
    } catch (e) {
      console.warn('Could not fetch CSRF token', e)
    }
  }
}, { immediate: true })

const handlePasswordChanged = async () => {
  // BUG-16 FIX: appeler clearMustChangePassword() immédiatement pour cacher le modal,
  // puis fetchUser(true, true) avec force=true pour bypasser le debounce 3s et
  // synchroniser l'état serveur (must_change_password=false confirmé par session).
  authStore.clearMustChangePassword()
  await authStore.fetchUser(true, true)
}
</script>

<template>
  <div id="app-root">
    <div
      v-if="authStore.isChecking"
      class="app-loading"
    >
      <div class="app-spinner" />
      <p>Chargement...</p>
    </div>
    <router-view v-else />
    <ChangePasswordModal
      v-if="showPasswordModal"
      :forced="true"
      @success="handlePasswordChanged"
    />
    <ToastContainer />
  </div>
</template>

<style>
body { margin: 0; padding: 0; font-family: 'Inter', sans-serif; }
#app-root { height: 100vh; }
.app-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100vh;
  color: #64748b;
  font-family: 'Inter', sans-serif;
}
.app-loading p { margin-top: 1rem; font-size: 1rem; }
.app-spinner {
  width: 40px;
  height: 40px;
  border: 4px solid #e2e8f0;
  border-top-color: #3b82f6;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }
</style>
