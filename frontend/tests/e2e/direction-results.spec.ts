/**
 * E2E tests — Direction "Résultats" tab
 *
 * Tests that Direction users can navigate to the read-only student results view
 * for each exam, and that admin-only actions (Pronote export, password reset)
 * are hidden in read-only mode.
 *
 * Requires an e2e seed with at least one Direction user and one exam with copies.
 */
import { test, expect } from '@playwright/test'
import { loginAsAdmin, loginAsDirection } from './authHelpers'

function normalizeExamList(payload: any) {
  return Array.isArray(payload) ? payload : (payload?.results || [])
}

test.describe('Direction — Résultats tab (read-only)', () => {

  test('Direction dashboard shows "Résultats" buttons', async ({ page }) => {
    await loginAsDirection(page)
    // At least one "Résultats" button should be visible in the dashboard
    const resultsBtns = page.locator('button', { hasText: 'Résultats' })
    await expect(resultsBtns.first()).toBeVisible({ timeout: 10000 })
  })

  test('Navigating to /direction/exams/:id/results loads the student list', async ({ page }) => {
    await loginAsDirection(page)

    // Get first exam id from the API
    const res = await page.request.get('/api/exams/direction/exams/')
    expect(res.ok()).toBeTruthy()
    const exams = await res.json()
    expect(exams.length).toBeGreaterThan(0)
    const examId = exams[0].id

    await page.goto(`/direction/exams/${examId}/results`)
    await page.waitForLoadState('networkidle')

    // Should show the student list header
    await expect(page.locator('h1', { hasText: 'Liste des élèves' })).toBeVisible({ timeout: 10000 })
  })

  test('Read-only view hides "Export Pronote" button', async ({ page }) => {
    await loginAsDirection(page)

    const res = await page.request.get('/api/exams/direction/exams/')
    const exams = await res.json()
    const examId = exams[0].id

    await page.goto(`/direction/exams/${examId}/results`)
    await page.waitForLoadState('networkidle')

    // Pronote export button must NOT be visible
    await expect(page.locator('button', { hasText: 'Export Pronote' })).not.toBeVisible()
  })

  test('Read-only view hides password-reset buttons', async ({ page }) => {
    await loginAsDirection(page)

    const res = await page.request.get('/api/exams/direction/exams/')
    const exams = await res.json()
    const examId = exams[0].id

    await page.goto(`/direction/exams/${examId}/results`)
    await page.waitForLoadState('networkidle')

    // No password-reset icon buttons should be visible
    // They carry title="Réinitialiser le mot de passe..."
    const resetBtns = page.locator('button[title*="Réinitialiser"]')
    await expect(resetBtns).toHaveCount(0)
  })

  test('Back button from read-only view navigates to Direction Dashboard', async ({ page }) => {
    await loginAsDirection(page)

    const res = await page.request.get('/api/exams/direction/exams/')
    const exams = await res.json()
    const examId = exams[0].id

    await page.goto(`/direction/exams/${examId}/results`)
    await page.waitForLoadState('networkidle')

    // Click the back arrow button
    await page.locator('button').filter({ has: page.locator('svg') }).first().click()
    await page.waitForURL('**/direction/dashboard', { timeout: 8000 })
  })

  test('Admin results page still shows Export Pronote (not read-only)', async ({ page }) => {
    await loginAsAdmin(page)

    const res = await page.request.get('/api/exams/')
    expect(res.ok()).toBeTruthy()
    const exams = normalizeExamList(await res.json())
    expect(exams.length).toBeGreaterThan(0)
    const examId = exams[0].id

    await page.goto(`/admin/exams/${examId}/results`)
    await page.waitForLoadState('networkidle')

    // Pronote export button MUST be visible for admin
    await expect(page.locator('button', { hasText: 'Export Pronote' })).toBeVisible({ timeout: 10000 })
  })

  test('Unauthenticated access to /direction/exams/:id/results redirects to portal', async ({ page }) => {
    await page.context().clearCookies()
    await page.goto('/direction/exams/00000000-0000-0000-0000-000000000001/results')
    await page.waitForURL('**/', { timeout: 8000 })
  })
})
