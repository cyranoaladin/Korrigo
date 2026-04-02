<script setup>
import { ref } from 'vue'
import api from '../services/api'

const email = ref('')
const isSubmitting = ref(false)
const error = ref('')
const message = ref('')

const submit = async () => {
  isSubmitting.value = true
  error.value = ''
  message.value = ''
  try {
    const response = await api.post('/password-reset/', { email: email.value.trim().toLowerCase() })
    message.value = response.data?.message || "Si un compte existe pour cette adresse email, un lien de réinitialisation a été envoyé."
  } catch (e) {
    error.value = e.response?.data?.error || "Impossible d'envoyer la demande de réinitialisation."
  } finally {
    isSubmitting.value = false
  }
}
</script>

<template>
  <div class="min-h-screen bg-slate-50 flex items-center justify-center px-4">
    <div class="w-full max-w-md bg-white rounded-2xl shadow-sm border border-slate-200 p-8">
      <h1 class="text-2xl font-bold text-slate-900">Mot de passe oublié</h1>
      <p class="mt-2 text-sm text-slate-500">
        Entrez votre adresse email. Si un compte existe, vous recevrez un lien de réinitialisation.
      </p>

      <form class="mt-6 space-y-4" @submit.prevent="submit">
        <div>
          <label class="block text-sm font-medium text-slate-700 mb-1">Adresse email</label>
          <input
            v-model="email"
            type="email"
            required
            class="w-full rounded-xl border border-slate-300 px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
            placeholder="vous@exemple.com"
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
          {{ isSubmitting ? 'Envoi en cours...' : 'Envoyer le lien' }}
        </button>
      </form>

      <router-link to="/" class="mt-5 inline-flex text-sm text-indigo-600 hover:text-indigo-700">
        Retour à la connexion
      </router-link>
    </div>
  </div>
</template>
