import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  base: '/',
  server: {
    host: true,
    port: 5173,
    watch: {
      usePolling: true
    },
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8088',
        changeOrigin: true,
      },
      '/media': {
        target: 'http://127.0.0.1:8088',
        changeOrigin: true,
      },
      '/static': {
        target: 'http://127.0.0.1:8088',
        changeOrigin: true,
      }
    }
  }
})
