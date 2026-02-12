import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import api from './services/api'
import './style.css'

import router from './router'

const app = createApp(App)

app.use(createPinia())
app.use(router)

// Mount immediately — fetch CSRF cookie in background (needed for POST/PUT/DELETE)
app.mount('#app')
api.get('/csrf/').catch(() => {})
