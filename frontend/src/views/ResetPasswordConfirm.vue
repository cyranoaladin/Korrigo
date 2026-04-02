<script setup>
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import api from '../services/api'

const route = useRoute()
const router = useRouter()

const newPassword = ref('')
const confirmPassword = ref('')
const isSubmitting = ref(false)
const error = ref('')
const message = ref('')

const uid = computed(() => route.query.uid || '')
const token = computed(() => route.query.token || '')

const submit = async () => {
  error.value = ''
  message.value = ''
  if (!uid.value || !token.value) {
    error.value = 'Lien de réinitialisation invalide.'
    return
  }
  if (newPassword.value.length < 12) {
    error.value = 'Le nouveau mot de passe doit contenir au moins 12 caractères.'
    return
  }
  if (newPassword.value !== confirmPassword.value) {
    error.value = 'Les mots de passe ne correspondent pas.'
    return
  }

  isSubmitting.value = true
  try {
    const response = await api.post('/password-reset/confirm/', {
      uid: uid.value,
      token: token.value,
      new_password: newPassword.value,
    })
    message.value = response.data?.message || 'Mot de passe réinitialisé avec succès.'
    setTimeout(() => router.push('/teacher/login'), 1200)
  } catch (e) {
    error.value = e.response?.data?.error || 'Impossible de réinitialiser le mot de passe.'
  } finally {
    isSubmitting.value = false
  }
}
</script>

<template>
  <div class="min-h-screen bg-slate-50 flex items-center justify-center px-4">
    <div class="w-full max-w-md bg-white rounded-2xl shadow-sm border border-slate-200 p-8">
      <h1 class="text-2xl font-bold text-slate-900">Réinitialiser le mot de passe</h1>
      <p class="mt-2 text-sm text-slate-500">
        Choisissez un nouveau mot de passe d'au moins 12 caractères.
      </p>

      <form class="mt-6 space-y-4" @submit.prevent="submit">
        <div>
          <label class="block text-sm font-medium text-slate-700 mb-1">Nouveau mot de passe</label>
          <input
            v-model="newPassword"
            type="password"
            required
            minlength="12"
            class="w-full rounded-xl border border-slate-300 px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
          >
        </div>

        <div>
          <label class="block text-sm font-medium text-slate-700 mb-1">Confirmer le mot de passe</label>
          <input
            v-model="confirmPassword"
            type="password"
            required
            minlength="12"
            class="w-full rounded-xl border border-slate-300 px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
          >
        </div>

        <p v-if="message" class="rounded-xl bg-emerald-50 border border-emerald-200 px-4 py-3 text-sm text-emerald-700">
          {{ message }}
        </p>
        <p v-if="error" class="rounded-xl bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700">
          {{ error }}
        </p>

        <button
          type="submit"
          :disabled="isSubmitting"
          class="w-full rounded-xl bg-indigo-600 px-4 py-3 text-sm font-semibold text-white hover:bg-indigo-700 disabled:opacity-50"
        >
          {{ isSubmitting ? 'Validation...' : 'Réinitialiser le mot de passe' }}
        </button>
      </form>
    </div>
  </div>
</template>
