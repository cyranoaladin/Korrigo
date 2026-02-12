import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import api from './services/api'
import './style.css'

import router from './router'

const app = createApp(App)

app.use(createPinia())
app.use(router)

// Obtain CSRF cookie before mounting (required for POST/PUT/DELETE requests)
api.get('/csrf/').catch(() => {}).finally(() => {
    app.mount('#app')
})
