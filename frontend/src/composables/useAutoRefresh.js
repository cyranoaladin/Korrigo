import { onBeforeUnmount, onMounted } from 'vue'

const DEFAULT_AUTO_REFRESH_MS = Number.parseInt(
  import.meta.env.VITE_ADMIN_AUTO_REFRESH_MS || '',
  10,
)

export function useAutoRefresh(refreshFn, options = {}) {
  const intervalMs = options.intervalMs ?? (
    Number.isFinite(DEFAULT_AUTO_REFRESH_MS) && DEFAULT_AUTO_REFRESH_MS > 0
      ? DEFAULT_AUTO_REFRESH_MS
      : 60000
  )
  const immediate = options.immediate ?? true
  const refreshOnVisible = options.refreshOnVisible ?? true

  let timerId = null
  let inFlight = false
  let stopped = false

  const hasDocument = () => typeof document !== 'undefined'
  const isHidden = () => hasDocument() && document.visibilityState === 'hidden'

  const clearTimer = () => {
    if (timerId !== null) {
      clearTimeout(timerId)
      timerId = null
    }
  }

  const scheduleNext = () => {
    clearTimer()
    if (stopped || isHidden()) return
    timerId = window.setTimeout(async () => {
      timerId = null
      await run('timer')
    }, intervalMs)
  }

  async function run(reason = 'manual') {
    if (stopped || inFlight) return false
    inFlight = true
    try {
      await refreshFn(reason)
      return true
    } finally {
      inFlight = false
      if (!stopped && !isHidden()) {
        scheduleNext()
      }
    }
  }

  const handleVisibilityChange = async () => {
    if (stopped) return
    if (isHidden()) {
      clearTimer()
      return
    }

    if (refreshOnVisible) {
      await run('visible')
      return
    }

    scheduleNext()
  }

  const stop = () => {
    stopped = true
    clearTimer()
    if (hasDocument()) {
      document.removeEventListener('visibilitychange', handleVisibilityChange)
    }
  }

  onMounted(async () => {
    if (hasDocument()) {
      document.addEventListener('visibilitychange', handleVisibilityChange)
    }

    if (isHidden()) return

    if (immediate) {
      await run('mount')
      return
    }

    scheduleNext()
  })

  onBeforeUnmount(stop)

  return {
    refreshNow: run,
    stop,
  }
}
