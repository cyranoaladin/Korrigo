import { ref, watch, onMounted } from 'vue'

const currentTheme = ref(localStorage.getItem('korrigo_theme') || 'light')

function applyTheme(theme) {
  const root = document.documentElement
  let effective = theme
  if (theme === 'auto') {
    effective = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
  }
  root.classList.toggle('dark', effective === 'dark')
  root.setAttribute('data-theme', effective)
}

// Listen for OS theme changes when in auto mode
if (typeof window !== 'undefined') {
  window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => {
    if (currentTheme.value === 'auto') applyTheme('auto')
  })
}

export function useTheme() {
  const setTheme = (theme) => {
    currentTheme.value = theme
    localStorage.setItem('korrigo_theme', theme)
    applyTheme(theme)
  }

  // Apply on first use
  applyTheme(currentTheme.value)

  return {
    currentTheme,
    setTheme,
  }
}
