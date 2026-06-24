import { describe, expect, it } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

const routerSource = readFileSync(
  resolve(__dirname, '../../src/router/index.js'),
  'utf-8',
)

describe('Route guard contracts (source analysis)', () => {
  describe('getLoginForRoute function exists and maps correctly', () => {
    it('getLoginForRoute is defined', () => {
      expect(routerSource).toContain('function getLoginForRoute(to)')
    })

    it('maps /student paths to /student/login', () => {
      expect(routerSource).toMatch(/to\.path\.startsWith\('\/student'\).*return '\/student\/login'/)
    })

    it('maps /corrector and /teacher paths to /teacher/login', () => {
      expect(routerSource).toMatch(/to\.path\.startsWith\('\/corrector'\).*return '\/teacher\/login'/)
    })

    it('maps /admin and /direction paths to /admin/login', () => {
      expect(routerSource).toMatch(/to\.path\.startsWith\('\/admin'\).*return '\/admin\/login'/)
    })
  })

  describe('Guard uses getLoginForRoute instead of generic /', () => {
    it('fetchUser error handler uses getLoginForRoute', () => {
      expect(routerSource).toContain('return safeRedirect(next, getLoginForRoute(to), to.path)')
    })

    it('does not redirect unauthenticated users to / for protected routes', () => {
      // The old pattern was safeRedirect(next, '/', to.path) in requiresAuth blocks
      // After fix, those should use getLoginForRoute(to) instead
      const requiresAuthBlock = routerSource.slice(
        routerSource.indexOf('if (to.meta.requiresAuth)'),
      )
      const guardBlock = requiresAuthBlock.slice(0, requiresAuthBlock.indexOf('if (isLoginPage'))

      // Count occurrences of the old generic redirect pattern
      const genericRedirectsInGuard = (guardBlock.match(/safeRedirect\(next, '\/'/g) || []).length
      expect(genericRedirectsInGuard, 'No generic / redirects should remain in auth guard').toBe(0)
    })
  })

  describe('Login routes are defined as public', () => {
    const loginRoutes = [
      { path: '/teacher/login', pattern: "path: '/teacher/login'" },
      { path: '/student/login', pattern: "path: '/student/login'" },
      { path: '/admin/login', pattern: "path: '/admin/login'" },
    ]

    for (const { path, pattern } of loginRoutes) {
      it(`${path} is defined`, () => {
        expect(routerSource).toContain(pattern)
      })

      it(`${path} is public`, () => {
        const idx = routerSource.indexOf(pattern)
        const block = routerSource.slice(idx, idx + 200)
        expect(block).toContain('public: true')
      })
    }
  })

  describe('Protected routes have requiresAuth', () => {
    const protectedPatterns = [
      '/corrector-dashboard',
      '/student/dashboard',
      '/direction/dashboard',
    ]

    for (const path of protectedPatterns) {
      it(`${path} has requiresAuth: true`, () => {
        const idx = routerSource.indexOf(`path: '${path}'`)
        expect(idx, `${path} not found`).toBeGreaterThan(-1)
        const block = routerSource.slice(idx, idx + 300)
        expect(block).toContain('requiresAuth: true')
      })
    }
  })

  describe('Legacy /direction redirects to /korrigo/direction', () => {
    it('/direction has a redirect', () => {
      const idx = routerSource.indexOf("path: '/direction'")
      expect(idx).toBeGreaterThan(-1)
      const block = routerSource.slice(idx, idx + 200)
      expect(block).toMatch(/redirect/)
    })
  })

  describe('Catch-all exists', () => {
    it('has a catch-all route', () => {
      expect(routerSource).toContain("path: '/:pathMatch(.*)*'")
    })
  })
})
