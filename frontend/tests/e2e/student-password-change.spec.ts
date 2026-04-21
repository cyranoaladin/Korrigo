import { test, expect } from '@playwright/test'

const STUDENT_EMAIL = process.env.E2E_STUDENT_EMAIL || 'eleve.test-e@ert.tn'
const STUDENT_PASS = process.env.E2E_STUDENT_PASS || '15032005'

test.describe('Student forced password change', () => {
  test('student can log in, change password, and reach the dashboard', async ({ page }) => {
    const newPassword = `NouveauMdp-${Date.now()}!`

    await page.goto('/student/login')
    await page.waitForLoadState('networkidle')

    await page.locator('input[type="email"]').fill(STUDENT_EMAIL)
    await page.locator('input[autocomplete="current-password"]').first().fill(STUDENT_PASS)
    await page.locator('button[type="submit"]').click()

    await page.waitForURL('**/student/dashboard', { timeout: 10000 })
    await expect(page.locator('.modal-content')).toBeVisible()
    await expect(page.locator('.modal-content h2')).toContainText('Changement de mot de passe requis')

    const submitButton = page.locator('.modal-actions button[type="submit"]')
    await expect(submitButton).toBeDisabled()

    const passwordInputs = page.locator('.modal-content input[type="password"]')
    await passwordInputs.nth(0).fill(STUDENT_PASS)
    await passwordInputs.nth(1).fill(newPassword)
    await passwordInputs.nth(2).fill(newPassword)

    await expect(submitButton).toBeEnabled()
    await submitButton.click()

    await expect(page.locator('.modal-content')).toBeHidden({ timeout: 10000 })
    await expect(page.locator('[data-testid="student-portal"]')).toBeVisible()
    await expect(page.getByRole('heading', { name: /Espace Résultats/ })).toBeVisible()
  })
})
