import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import tailwindcss from '@tailwindcss/vite'

// Proxy target: use backend:8000 inside Docker, 127.0.0.1:8088 on host
const apiTarget = process.env.VITE_API_TARGET || 'http://127.0.0.1:8088'

export default defineConfig({
  plugins: [tailwindcss(), vue()],
  base: '/',
  server: {
    host: true,
    port: 5173,
    allowedHosts: ['korrigo.labomaths.tn', 'localhost', '127.0.0.1'],
    watch: {
      usePolling: true
    },
    proxy: {
      '/api': {
        target: apiTarget,
        changeOrigin: true,
      },
      '/media': {
        target: apiTarget,
        changeOrigin: true,
      },
      '/static': {
        target: apiTarget,
        changeOrigin: true,
      }
    }
  }
})
