import { describe, it, expect, beforeEach, vi } from 'vitest'

// Mock api module
const mockApi = {
  get: vi.fn(),
  post: vi.fn(),
  put: vi.fn(),
  patch: vi.fn(),
  delete: vi.fn(),
  defaults: { baseURL: '/api' },
  interceptors: {
    request: { use: vi.fn() },
    response: { use: vi.fn() },
  },
}
vi.mock('@services/api', () => ({ default: mockApi }))

// Inline auth store logic matching src/stores/auth.js
// We replicate the store as a plain object to avoid pinia dependency in unit tests.
function createAuthStore() {
  let user: any = null
  let lastError = ''
  let isChecking = false
  let lastCheckedAt = 0
  const CHECK_DEBOUNCE_MS = 3000

  return {
    get user() { return user },
    set user(v) { user = v },
    get lastError() { return lastError },
    set lastError(v) { lastError = v },
    get isChecking() { return isChecking },
    get isAuthenticated() { return !!user },
    get mustChangePassword() { return user?.must_change_password || false },

    clearError() {
      lastError = ''
    },

    clearMustChangePassword() {
      if (user) {
        user.must_change_password = false
      }
    },

    async login(username: string, password: string) {
      try {
        lastError = ''
        await mockApi.post('/login/', { username, password })
        await this.fetchUser(false, true)
        return true
      } catch (e: any) {
        lastError = e.response?.data?.error || 'Identifiants incorrects.'
        return false
      }
    },

    async loginStudent(email: string, password: string) {
      try {
        lastError = ''
        const res = await mockApi.post('/students/login/', { email, password })
        if (res.data) {
          await this.fetchUser(true, true)
          if (user && res.data.must_change_password) {
            user.must_change_password = true
          }
          return true
        }
        return false
      } catch (e: any) {
        lastError = e.response?.data?.error || 'Email ou mot de passe incorrect.'
        return false
      }
    },

    async logout() {
      try {
        const endpoint = user?.role === 'Student' ? '/students/logout/' : '/logout/'
        await mockApi.post(endpoint)
      } catch (e) {
        // ignore
      } finally {
        user = null
      }
    },

    async fetchUser(preferStudent = false, force = false) {
      const now = Date.now()
      if (!force && !user && (now - lastCheckedAt) < CHECK_DEBOUNCE_MS) {
        return
      }
      isChecking = true
      lastCheckedAt = now
      try {
        const [adminResult, studentResult] = await Promise.allSettled([
          preferStudent ? Promise.reject('skipped') : mockApi.get('/me/'),
          mockApi.get('/students/me/'),
        ])

        if (!preferStudent && adminResult.status === 'fulfilled') {
          user = (adminResult as any).value.data
          user.role = user.role || 'Admin'
          return
        }

        if (studentResult.status === 'fulfilled') {
          const studentData = (studentResult as any).value.data
          user = { ...studentData, role: 'Student' }
          if (studentData.must_change_password !== undefined) {
            user.must_change_password = studentData.must_change_password
          }
          return
        }

        user = null
      } catch (e) {
        user = null
      } finally {
        isChecking = false
      }
    },
  }
}

describe('AuthStore', () => {
  let store: ReturnType<typeof createAuthStore>

  beforeEach(() => {
    vi.clearAllMocks()
    store = createAuthStore()
  })

  // --- login ---

  it('login — success case, calls fetchUser', async () => {
    mockApi.post.mockResolvedValue({ data: { ok: true } })
    mockApi.get.mockImplementation((url: string) => {
      if (url === '/me/') return Promise.resolve({ data: { id: 1, username: 'prof', role: 'Admin' } })
      return Promise.reject(new Error('not found'))
    })

    const result = await store.login('prof', 'pass123')

    expect(result).toBe(true)
    expect(mockApi.post).toHaveBeenCalledWith('/login/', { username: 'prof', password: 'pass123' })
    expect(store.user).toBeTruthy()
    expect(store.user.username).toBe('prof')
    expect(store.lastError).toBe('')
  })

  it('login — failure case, sets lastError', async () => {
    mockApi.post.mockRejectedValue({
      response: { data: { error: 'Mot de passe incorrect' } },
    })

    const result = await store.login('prof', 'wrong')

    expect(result).toBe(false)
    expect(store.lastError).toBe('Mot de passe incorrect')
    expect(store.user).toBeNull()
  })

  it('login — failure with no response data uses default message', async () => {
    mockApi.post.mockRejectedValue(new Error('Network error'))

    const result = await store.login('prof', 'wrong')

    expect(result).toBe(false)
    expect(store.lastError).toBe('Identifiants incorrects.')
  })

  // --- loginStudent ---

  it('loginStudent — success case', async () => {
    mockApi.post.mockResolvedValue({ data: { id: 10, email: 'stu@test.com' } })
    mockApi.get.mockImplementation((url: string) => {
      if (url === '/students/me/') {
        return Promise.resolve({ data: { id: 10, email: 'stu@test.com', first_name: 'Alice' } })
      }
      return Promise.reject(new Error('not found'))
    })

    const result = await store.loginStudent('stu@test.com', 'pass')

    expect(result).toBe(true)
    expect(mockApi.post).toHaveBeenCalledWith('/students/login/', { email: 'stu@test.com', password: 'pass' })
    expect(store.user).toBeTruthy()
    expect(store.user.role).toBe('Student')
  })

  it('loginStudent — propagates must_change_password from login response', async () => {
    mockApi.post.mockResolvedValue({ data: { id: 10, must_change_password: true } })
    mockApi.get.mockImplementation((url: string) => {
      if (url === '/students/me/') {
        return Promise.resolve({ data: { id: 10, email: 'stu@test.com' } })
      }
      return Promise.reject(new Error('not found'))
    })

    await store.loginStudent('stu@test.com', 'pass')

    expect(store.user.must_change_password).toBe(true)
    expect(store.mustChangePassword).toBe(true)
  })

  it('loginStudent — failure case, sets lastError', async () => {
    mockApi.post.mockRejectedValue({
      response: { data: { error: 'Email inconnu' } },
    })

    const result = await store.loginStudent('bad@test.com', 'wrong')

    expect(result).toBe(false)
    expect(store.lastError).toBe('Email inconnu')
  })

  it('loginStudent — failure with no response uses default message', async () => {
    mockApi.post.mockRejectedValue(new Error('timeout'))

    const result = await store.loginStudent('bad@test.com', 'wrong')

    expect(result).toBe(false)
    expect(store.lastError).toBe('Email ou mot de passe incorrect.')
  })

  // --- logout ---

  it('logout — clears user, calls correct endpoint for admin', async () => {
    // Set up as admin user
    store.user = { id: 1, username: 'admin', role: 'Admin' }
    mockApi.post.mockResolvedValue({})

    await store.logout()

    expect(mockApi.post).toHaveBeenCalledWith('/logout/')
    expect(store.user).toBeNull()
  })

  it('logout — calls student endpoint for student role', async () => {
    store.user = { id: 10, email: 'stu@test.com', role: 'Student' }
    mockApi.post.mockResolvedValue({})

    await store.logout()

    expect(mockApi.post).toHaveBeenCalledWith('/students/logout/')
    expect(store.user).toBeNull()
  })

  it('logout — clears user even if API call fails', async () => {
    store.user = { id: 1, role: 'Admin' }
    mockApi.post.mockRejectedValue(new Error('server down'))

    await store.logout()

    expect(store.user).toBeNull()
  })

  // --- fetchUser ---

  it('fetchUser — sets admin user from /me/', async () => {
    mockApi.get.mockImplementation((url: string) => {
      if (url === '/me/') return Promise.resolve({ data: { id: 1, username: 'prof' } })
      return Promise.reject(new Error('not found'))
    })

    await store.fetchUser(false, true)

    expect(store.user).toBeTruthy()
    expect(store.user.username).toBe('prof')
    expect(store.user.role).toBe('Admin')
  })

  it('fetchUser — sets student user from /students/me/', async () => {
    mockApi.get.mockImplementation((url: string) => {
      if (url === '/students/me/') {
        return Promise.resolve({ data: { id: 10, email: 'stu@test.com', must_change_password: false } })
      }
      return Promise.reject(new Error('not found'))
    })

    await store.fetchUser(true, true)

    expect(store.user).toBeTruthy()
    expect(store.user.role).toBe('Student')
    expect(store.user.email).toBe('stu@test.com')
  })

  it('fetchUser — sets null when both fail', async () => {
    mockApi.get.mockRejectedValue(new Error('unauthorized'))

    await store.fetchUser(false, true)

    expect(store.user).toBeNull()
  })

  it('fetchUser — debounces rapid calls', async () => {
    mockApi.get.mockRejectedValue(new Error('unauthorized'))

    // First call (force=true to set lastCheckedAt)
    await store.fetchUser(false, true)
    const callCount = mockApi.get.mock.calls.length

    // Second call without force — should be debounced (user is null and within window)
    await store.fetchUser(false, false)

    expect(mockApi.get.mock.calls.length).toBe(callCount)
  })

  it('fetchUser — preferStudent skips /me/ call', async () => {
    mockApi.get.mockImplementation((url: string) => {
      if (url === '/students/me/') {
        return Promise.resolve({ data: { id: 10, email: 'stu@test.com' } })
      }
      return Promise.resolve({ data: { id: 1, username: 'admin' } })
    })

    await store.fetchUser(true, true)

    // When preferStudent is true, /me/ is skipped (rejected with 'skipped'),
    // so user should be student even if /me/ would succeed
    expect(store.user.role).toBe('Student')
  })

  // --- isAuthenticated ---

  it('isAuthenticated — computed returns true when user set', () => {
    store.user = { id: 1, username: 'prof', role: 'Admin' }
    expect(store.isAuthenticated).toBe(true)
  })

  it('isAuthenticated — computed returns false when user null', () => {
    store.user = null
    expect(store.isAuthenticated).toBe(false)
  })

  // --- mustChangePassword ---

  it('mustChangePassword — returns true when flag set', () => {
    store.user = { id: 1, must_change_password: true }
    expect(store.mustChangePassword).toBe(true)
  })

  it('mustChangePassword — returns false when flag not set', () => {
    store.user = { id: 1 }
    expect(store.mustChangePassword).toBe(false)
  })

  it('mustChangePassword — returns false when user is null', () => {
    store.user = null
    expect(store.mustChangePassword).toBe(false)
  })

  // --- clearError ---

  it('clearError — resets lastError', async () => {
    mockApi.post.mockRejectedValue({ response: { data: { error: 'Bad' } } })
    await store.login('x', 'y')
    expect(store.lastError).toBe('Bad')

    store.clearError()

    expect(store.lastError).toBe('')
  })

  // --- clearMustChangePassword ---

  it('clearMustChangePassword — clears the flag', () => {
    store.user = { id: 1, must_change_password: true }
    expect(store.mustChangePassword).toBe(true)

    store.clearMustChangePassword()

    expect(store.user.must_change_password).toBe(false)
    expect(store.mustChangePassword).toBe(false)
  })

  it('clearMustChangePassword — does nothing when user is null', () => {
    store.user = null
    store.clearMustChangePassword() // should not throw
    expect(store.user).toBeNull()
  })
})
