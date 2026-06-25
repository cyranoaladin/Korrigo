import { expect, test } from '@playwright/test'

import {
  KORRIGO_PUBLIC_ROUTE_PATHS,
  KORRIGO_PUBLIC_ROUTES,
} from '../../src/features/korrigo/content/korrigoPublicContent'

const forbiddenText = [
  /guide-enseignanthttps/i,
  /Lorem/i,
  /TODO/i,
  /à compléter/i,
  /fake/i,
  /dummy/i,
  /anonymous_id/i,
]

const emailPattern = /[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}/

test.describe('Korrigo public pages', () => {
  for (const route of KORRIGO_PUBLIC_ROUTES) {
    test(`${route.path} renders public content without broken internal links`, async ({ page, request }) => {
      const consoleErrors: string[] = []
      const failedRequests: string[] = []

      page.on('console', (message) => {
        if (message.type() === 'error') consoleErrors.push(message.text())
      })
      page.on('requestfailed', (requestFailure) => {
        failedRequests.push(`${requestFailure.method()} ${requestFailure.url()}`)
      })

      const response = await page.goto(route.path, { waitUntil: 'networkidle' })
      expect(response?.status()).toBeLessThan(500)
      await expect(page.getByRole('heading', { level: 1 })).toBeVisible()

      const visibleText = await page.locator('body').innerText()
      expect(visibleText.length).toBeGreaterThan(200)
      expect(visibleText).not.toMatch(emailPattern)

      for (const pattern of forbiddenText) {
        expect(visibleText).not.toMatch(pattern)
      }

      const internalLinks = await page.locator('a[href^="/"]').evaluateAll((links) =>
        Array.from(new Set(links.map((link) => link.getAttribute('href')).filter(Boolean)))
      )

      for (const href of internalLinks) {
        const cleanPath = String(href).split('#')[0]
        const linkResponse = await request.get(cleanPath)
        expect(linkResponse.status(), `${route.path} links to ${cleanPath}`).toBeLessThan(500)
      }

      expect(failedRequests).toEqual([])
      expect(consoleErrors).toEqual([])
    })
  }

  test('public page routes stay canonical and typo-free', () => {
    expect(KORRIGO_PUBLIC_ROUTE_PATHS).toEqual([
      '/korrigo',
      '/korrigo/guide-enseignant',
      '/korrigo/guide-eleve',
      '/korrigo/direction',
    ])
    expect(KORRIGO_PUBLIC_ROUTE_PATHS.join('\n')).not.toMatch(/guide-enseignanthttps/i)
  })
})
