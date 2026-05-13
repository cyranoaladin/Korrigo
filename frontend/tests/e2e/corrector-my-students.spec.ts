import { test, expect, type Page } from '@playwright/test'
import { loginAsTeacher } from './authHelpers'

const EXAM_TYPE_NAME = 'E2E Mathématiques'
const STUDENT_FULL_NAME = 'E2E_STUDENT Jean'

async function selectExamType(page: Page) {
  if (await page.getByText(EXAM_TYPE_NAME).first().isVisible().catch(() => false)) {
    await expect(page.locator('[data-testid="corrector-dashboard"]')).toBeVisible({ timeout: 10000 })
    return
  }

  const modal = page.getByTestId('exam-type-selection-modal')
  const modalVisible = await modal.isVisible().catch(() => false)

  if (modalVisible) {
    const typeCard = modal.locator('.type-card').filter({ hasText: EXAM_TYPE_NAME }).first()
    if (await typeCard.isVisible({ timeout: 1000 }).catch(() => false)) {
      await typeCard.click()
    }
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

    const exportButton = page.locator('.btn-global-export')
    await expect(exportButton).toBeVisible()
    const downloadPromise = page.waitForEvent('download', { timeout: 5000 }).catch(() => null)
    await exportButton.click()
    const download = await downloadPromise
    if (download) {
      expect(download.suggestedFilename()).toMatch(/^PRONOTE_/)
    }

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
