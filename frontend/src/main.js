import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'

import router from './router'

// Initialize CSRF cookie before mounting app
fetch('/api/csrf/', { credentials: 'include' })
    .catch(() => console.warn('CSRF init failed'))

const app = createApp(App)

app.use(createPinia())
app.use(router)
app.mount('#app')
