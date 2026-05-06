import { beforeEach, describe, expect, it, vi } from 'vitest'

function createAuthStore(mockApi: { post: ReturnType<typeof vi.fn>; get: ReturnType<typeof vi.fn> }) {
  let user: any = null
  let lastError = ''
  let lastCheckedAt = 0
  const CHECK_DEBOUNCE_MS = 3000

  function isExpectedAuthFailure(status?: number) {
    return status === 401 || status === 403
  }

  return {
    get user() { return user },
    set user(v) { user = v },
    get lastError() { return lastError },

    async login(username: string, password: string) {
      try {
        lastError = ''
        await mockApi.post('/login/', { username, password })
        lastCheckedAt = Date.now() + CHECK_DEBOUNCE_MS
        return true
      } catch (e: any) {
        lastError = e.response?.data?.error || 'Identifiants incorrects.'
        if (!isExpectedAuthFailure(e?.response?.status)) {
          console.error(e)
        }
        return false
      }
    },

    async logout() {
      const endpoint = user?.role === 'Student' ? '/students/logout/' : '/logout/'
      user = null
      lastCheckedAt = 0
      try {
        await mockApi.post(endpoint)
      } catch (e: any) {
        if (!isExpectedAuthFailure(e?.response?.status)) {
          console.warn('Logout backend request failed (session will expire naturally):', e?.response?.status)
        }
      }
    },
  }
}

describe('auth store logging behavior', () => {
  const mockApi = {
    get: vi.fn(),
    post: vi.fn(),
  }

  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('does not log an error for expected 401 login failures', async () => {
    const store = createAuthStore(mockApi)
    const errorSpy = vi.spyOn(console, 'error').mockImplementation(() => {})

    mockApi.post.mockRejectedValue({
      response: {
        status: 401,
        data: { error: 'Identifiants incorrects.' },
      },
    })

    const ok = await store.login('prof', 'bad-password')

    expect(ok).toBe(false)
    expect(store.lastError).toBe('Identifiants incorrects.')
    expect(errorSpy).not.toHaveBeenCalled()
  })

  it('does not warn for expected 403 logout failures once local state is cleared', async () => {
    const store = createAuthStore(mockApi)
    const warnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {})

    store.user = { role: 'Teacher', username: 'prof' }
    mockApi.post.mockRejectedValue({
      response: {
        status: 403,
        data: { detail: 'CSRF Failed' },
      },
    })

    await store.logout()

    expect(store.user).toBeNull()
    expect(warnSpy).not.toHaveBeenCalled()
  })

  it('still logs unexpected login transport failures', async () => {
    const store = createAuthStore(mockApi)
    const errorSpy = vi.spyOn(console, 'error').mockImplementation(() => {})

    mockApi.post.mockRejectedValue(new Error('network down'))

    const ok = await store.login('prof', 'secret')

    expect(ok).toBe(false)
    expect(errorSpy).toHaveBeenCalledTimes(1)
  })
})
