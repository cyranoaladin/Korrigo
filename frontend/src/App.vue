<script setup>
import { computed } from 'vue'
import { useAuthStore } from './stores/auth'
import ChangePasswordModal from './components/ChangePasswordModal.vue'

const authStore = useAuthStore()

const showPasswordModal = computed(() => {
  return authStore.isAuthenticated && authStore.mustChangePassword
})

const handlePasswordChanged = async () => {
  authStore.clearMustChangePassword()
  await authStore.fetchUser()
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
