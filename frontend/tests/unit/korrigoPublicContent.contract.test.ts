import { describe, expect, it } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

import {
  KORRIGO_COPY_STATUSES,
  KORRIGO_LOGIN_LINKS,
  KORRIGO_PUBLIC_PAGE_KEYS,
  KORRIGO_PUBLIC_PAGES,
  KORRIGO_PUBLIC_ROUTE_PATHS,
  KORRIGO_PUBLIC_ROUTES,
} from '../../src/features/korrigo/content/korrigoPublicContent'
import { hasIcon } from '../../src/icons/iconRegistry'

const repoRoot = resolve(__dirname, '../..')

const publicPageFiles = [
  'src/views/HomeView.vue',
  'src/views/GuideEnseignant.vue',
  'src/views/GuideEtudiant.vue',
  'src/views/DirectionConformite.vue',
]

const sharedShellFiles = [
  'src/components/Navbar.vue',
  'src/components/Footer.vue',
]

const routeSourceFiles = [
  'src/router/index.js',
  ...publicPageFiles,
  ...sharedShellFiles,
]

const forbiddenText = [
  /guide-enseignanthttps/i,
  /Lorem/i,
  /TODO/i,
  /à compléter/i,
  /fake/i,
  /dummy/i,
]

const allowedInternalTargets = new Set([
  '/teacher/login',
  '/student/login',
  '/admin/login',
  ...KORRIGO_PUBLIC_ROUTE_PATHS,
])

function readRepoFile(relativePath: string): string {
  return readFileSync(resolve(repoRoot, relativePath), 'utf8')
}

function walkText(value: unknown): string[] {
  if (typeof value === 'string') return [value]
  if (Array.isArray(value)) return value.flatMap(walkText)
  if (value && typeof value === 'object') {
    return Object.values(value as Record<string, unknown>).flatMap(walkText)
  }
  return []
}

function walkObjects(value: unknown): Record<string, unknown>[] {
  if (Array.isArray(value)) return value.flatMap(walkObjects)
  if (value && typeof value === 'object') {
    return [
      value as Record<string, unknown>,
      ...Object.values(value as Record<string, unknown>).flatMap(walkObjects),
    ]
  }
  return []
}

function extractBackendCopyStatusCodes(): string[] {
  const models = readRepoFile('../backend/exams/models.py')
  const statusStart = models.indexOf('class Status(models.TextChoices):')
  const nextNestedClass = models.indexOf('\n    class ', statusStart + 1)

  expect(statusStart).toBeGreaterThanOrEqual(0)
  expect(nextNestedClass).toBeGreaterThan(statusStart)

  const statusClass = models.slice(statusStart, nextNestedClass)

  return [...statusClass.matchAll(/^\s{8}[A-Z_]+\s*=\s*['"]([A-Z_]+)['"]/gm)]
    .map((match) => match[1])
}

describe('Korrigo public page content contract', () => {
  it('declares exactly the four public Korrigo routes once', () => {
    expect(KORRIGO_PUBLIC_ROUTE_PATHS).toEqual([
      '/korrigo',
      '/korrigo/guide-enseignant',
      '/korrigo/guide-eleve',
      '/korrigo/direction',
    ])
    expect(new Set(KORRIGO_PUBLIC_ROUTE_PATHS).size).toBe(KORRIGO_PUBLIC_ROUTE_PATHS.length)
    expect(KORRIGO_PUBLIC_ROUTES.map((route) => route.key)).toEqual(KORRIGO_PUBLIC_PAGE_KEYS)
  })

  it('keeps all editorial page content in the central source', () => {
    expect(KORRIGO_PUBLIC_PAGE_KEYS).toEqual(['home', 'teacherGuide', 'studentGuide', 'direction'])

    for (const key of KORRIGO_PUBLIC_PAGE_KEYS) {
      const page = KORRIGO_PUBLIC_PAGES[key]
      expect(page.title).toBeTruthy()
      expect(page.subtitle).toBeTruthy()
      expect(page.sections.length).toBeGreaterThan(0)
    }
  })

  it('does not contain placeholders, typo routes, emails, or real-person markers in public content', () => {
    const allText = walkText({ KORRIGO_PUBLIC_ROUTES, KORRIGO_PUBLIC_PAGES }).join('\\n')

    for (const pattern of forbiddenText) {
      expect(allText).not.toMatch(pattern)
    }
    expect(allText).not.toMatch(/[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}/)
    expect(allText).not.toMatch(/anonymous_id/i)
  })

  it('keeps public CTAs on known internal routes', () => {
    for (const page of Object.values(KORRIGO_PUBLIC_PAGES)) {
      for (const cta of page.ctas ?? []) {
        expect(allowedInternalTargets.has(cta.to)).toBe(true)
      }
    }
  })

  it('keeps displayed copy status codes aligned with backend Copy.Status choices', () => {
    const backendStatuses = extractBackendCopyStatusCodes()
    const publicStatuses = KORRIGO_COPY_STATUSES.map((status) => status.code)

    expect(backendStatuses).toEqual(['READY', 'IN_PROGRESS', 'FINALIZED'])
    expect(publicStatuses).toEqual(backendStatuses)
  })

  it('uses only registered icons in public page content and login links', () => {
    const iconNames = walkObjects({ KORRIGO_PUBLIC_PAGES, KORRIGO_LOGIN_LINKS })
      .map((item) => item.icon)
      .filter((icon): icon is string => typeof icon === 'string')

    expect(iconNames.length).toBeGreaterThan(0)
    for (const icon of iconNames) {
      expect(hasIcon(icon), `Missing icon registry entry for ${icon}`).toBe(true)
    }
  })

  it('uses the real authenticated entrypoint for Direction instead of the generic portal', () => {
    const directionPage = KORRIGO_PUBLIC_PAGES.direction
    const directionLogin = directionPage.ctas?.find((cta) => /direction|authentifié/i.test(cta.label))

    expect(directionLogin).toBeTruthy()
    expect(directionLogin?.to).toBe('/admin/login')
    expect(directionLogin?.label).not.toBe('Connexion direction')
  })

  it('public page components consume the centralized content renderer', () => {
    for (const file of publicPageFiles) {
      const text = readRepoFile(file)

      expect(text).toContain('KorrigoPublicPage')
      expect(text).toContain('page-key')
      expect(text).not.toContain("api.get('/platform-stats/')")
      expect(text).not.toContain('platform-stats')
    }
  })

  it('router uses central public route constants and keeps the teacher guide typo absent', () => {
    const router = readRepoFile('src/router/index.js')

    expect(router).toContain('KORRIGO_PUBLIC_ROUTE_SEGMENTS')
    expect(router).not.toMatch(/guide-enseignanthttps/i)
  })

  it('shared shell navigation consumes the centralized route definitions', () => {
    for (const file of sharedShellFiles) {
      const text = readRepoFile(file)

      expect(text).toMatch(/KORRIGO_PUBLIC_ROUTE/)
      expect(text).not.toMatch(/guide-enseignanthttps/i)
      expect(text).not.toContain('to="/korrigo/guide-enseignant"')
      expect(text).not.toContain('to="/korrigo/guide-eleve"')
      expect(text).not.toContain('to="/korrigo/direction"')
    }
  })

  it('does not hardcode public route paths outside the central route source', () => {
    const central = readRepoFile('src/features/korrigo/content/korrigoPublicContent.js')

    for (const routePath of KORRIGO_PUBLIC_ROUTE_PATHS) {
      expect(central).toContain(routePath)
    }

    for (const file of routeSourceFiles) {
      const text = readRepoFile(file)
      if (file.endsWith('korrigoPublicContent.js')) continue

      for (const routePath of KORRIGO_PUBLIC_ROUTE_PATHS.filter((path) => path !== '/korrigo')) {
        expect(text, `${file} must use central route constants for ${routePath}`).not.toContain(`"${routePath}"`)
        expect(text, `${file} must use central route constants for ${routePath}`).not.toContain(`'${routePath}'`)
      }
    }
  })
})
