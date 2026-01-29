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
    <router-view />
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
</style>
