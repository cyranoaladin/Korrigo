import { test, expect, type Page } from '@playwright/test'
import { TEACHER_USER, TEACHER_PASS } from './e2eEnv'

const EXAM_TYPE_NAME = 'E2E Mathématiques'
const STUDENT_FULL_NAME = 'E2E_STUDENT Jean'

async function loginAsTeacher(page: Page) {
  await page.goto('/login', { waitUntil: 'domcontentloaded' })

  const loginResult = await page.evaluate(async ({ username: user, password: pass }) => {
    const response = await fetch('/api/login/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({ username: user, password: pass }),
    })

    return {
      ok: response.ok,
      status: response.status,
      body: await response.text(),
    }
  }, { username: TEACHER_USER, password: TEACHER_PASS })

  expect(loginResult.ok, `Teacher login failed: HTTP ${loginResult.status}\n${loginResult.body}`).toBeTruthy()

  await page.goto('/corrector-dashboard', { waitUntil: 'networkidle' })
  await expect(page.getByTestId('corrector-dashboard')).toBeVisible({ timeout: 10000 })
}

async function selectExamType(page: Page) {
  const modal = page.getByTestId('exam-type-selection-modal')
  const modalVisible = await modal.isVisible().catch(() => false)

  if (modalVisible) {
    const typeCard = modal.locator('.type-card').filter({ hasText: EXAM_TYPE_NAME }).first()
    await expect(typeCard).toBeVisible({ timeout: 10000 })
    await typeCard.click()
  }

  await expect(page.locator('[data-testid="corrector-dashboard"]')).toBeVisible({ timeout: 10000 })
  await expect(page.locator('.type-badge')).toContainText(EXAM_TYPE_NAME)
}

test.describe('Corrector Dashboard / Mes Eleves', () => {
  test.beforeEach(async ({ page }) => {
    await loginAsTeacher(page)
    await selectExamType(page)
  })

  test('dashboard exposes the seeded copies, stats and my-students entrypoints', async ({ page }) => {
    await expect(page.locator('.stats-overview')).toBeVisible()
    await expect(page.locator('[data-testid="copy-card"]').first()).toBeVisible()
    await expect(page.locator('.btn-export-inline').first()).toBeVisible()
    await expect(page.getByTestId('btn-my-students-global')).toBeVisible()
    await expect(page.locator('.my-students-section')).toContainText(STUDENT_FULL_NAME)
  })

  test('my-students supports export and detailed bilan navigation', async ({ page }) => {
    await page.getByTestId('btn-my-students-global').click()
    await page.waitForURL('**/corrector/my-students', { timeout: 10000 })

    await expect(page.locator('h1')).toContainText('Mes Élèves')
    await expect(page.locator('.student-card').filter({ hasText: STUDENT_FULL_NAME }).first()).toBeVisible()

    const downloadPromise = page.waitForEvent('download')
    await page.locator('.btn-global-export').click()
    const download = await downloadPromise
    expect(download.suggestedFilename()).toMatch(/^PRONOTE_/)

    await page.locator('.student-card').filter({ hasText: STUDENT_FULL_NAME }).first().click()
    await page.waitForURL(/\/corrector\/student\/.+\/bilan/, { timeout: 10000 })

    await expect(page.locator('.student-header h1')).toContainText(STUDENT_FULL_NAME)
    await expect(page.locator('.score-value')).toContainText('15.00')
    await expect(page.locator('.scores-grid .score-item')).toHaveCount(2)
    await expect(page.locator('.remarks-list')).toContainText('Méthode correcte')
    await expect(page.locator('.annotations-list')).toContainText('Bon raisonnement')

    await page.getByRole('button', { name: /Mes Élèves/i }).click()
    await page.waitForURL('**/corrector/my-students**', { timeout: 10000 })
    await expect(page.locator('h1')).toContainText('Mes Élèves')
  })
})
