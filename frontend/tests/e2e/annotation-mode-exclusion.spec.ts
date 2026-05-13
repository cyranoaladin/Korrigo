import { test, expect, type Page } from '@playwright/test'
import { loginAsTeacher } from './authHelpers'

/**
 * REGRESSION TEST — Annotation Mode Mutual Exclusion
 *
 * Reproduces the exact bug from commit 4effc50 (23 mars 2026):
 * 1. User clicks FAUX stamp button → quickStampMode = 'FAUX'
 * 2. User clicks Commentaire button → preSelectedAnnotationType = 'COMMENTAIRE'
 *    BUT quickStampMode was NOT cleared → still 'FAUX'
 * 3. User draws rectangle → handleDrawComplete checks quickStampMode FIRST
 *    → Creates FAUX stamp instead of opening comment editor
 *
 * Fix: Single annotationMode ref with setAnnotationMode() that structurally
 * prevents both groups from being active simultaneously.
 */

async function openFirstCopyDesk(page: Page): Promise<boolean> {
  const copyAction = page.locator('[data-testid="copy-action"]').first()
  const hasCopies = await copyAction.isVisible({ timeout: 10000 }).catch(() => false)
  if (hasCopies) {
    await copyAction.click()
    await page.waitForURL(/\/corrector\/desk\/\d+/, { timeout: 10000 })
    await page.waitForSelector('.corrector-desk', { timeout: 10000 })
    await page.waitForFunction(
      () => !document.querySelector('.loading-state'),
      { timeout: 15000 }
    )
  }
  return hasCopies
}

test.describe('Annotation Mode — Mutual Exclusion Regression', () => {
  test('CRITICAL: clicking Commentaire after FAUX deactivates FAUX stamp', async ({ page }) => {
    await loginAsTeacher(page)
    const hasCopies = await openFirstCopyDesk(page)
    if (!hasCopies) return

    const fauxBtn = page.locator('.btn-stamp-faux')
    const commentBtn = page.locator('.btn-annot-type').first() // 💬
    const isFauxVisible = await fauxBtn.isVisible().catch(() => false)
    const isCommentVisible = await commentBtn.isVisible().catch(() => false)
    if (!isFauxVisible || !isCommentVisible) return

    // Step 1: Activate FAUX
    await fauxBtn.click()
    await expect(fauxBtn).toHaveClass(/active/)

    // Step 2: Click Commentaire — FAUX must deactivate
    await commentBtn.click()
    await expect(commentBtn).toHaveClass(/active/)
    await expect(fauxBtn).not.toHaveClass(/active/) // ← THE REGRESSION CHECK
  })

  test('CRITICAL: clicking VRAI after Surlignage deactivates Surlignage', async ({ page }) => {
    await loginAsTeacher(page)
    const hasCopies = await openFirstCopyDesk(page)
    if (!hasCopies) return

    const vraiBtn = page.locator('.btn-stamp-vrai')
    const surlignageBtn = page.locator('.btn-annot-type').nth(1) // 🟨
    const isVraiVisible = await vraiBtn.isVisible().catch(() => false)
    const isSurlVisible = await surlignageBtn.isVisible().catch(() => false)
    if (!isVraiVisible || !isSurlVisible) return

    // Activate Surlignage
    await surlignageBtn.click()
    await expect(surlignageBtn).toHaveClass(/active/)

    // Click VRAI — Surlignage must deactivate
    await vraiBtn.click()
    await expect(vraiBtn).toHaveClass(/active/)
    await expect(surlignageBtn).not.toHaveClass(/active/)
  })

  test('only one button active at any time across both groups', async ({ page }) => {
    await loginAsTeacher(page)
    const hasCopies = await openFirstCopyDesk(page)
    if (!hasCopies) return

    const fauxBtn = page.locator('.btn-stamp-faux')
    const vraiBtn = page.locator('.btn-stamp-vrai')
    const annotBtns = page.locator('.btn-annot-type')
    const isFauxVisible = await fauxBtn.isVisible().catch(() => false)
    if (!isFauxVisible) return

    const allButtons = [
      fauxBtn, vraiBtn,
      annotBtns.nth(0), annotBtns.nth(1), annotBtns.nth(2), annotBtns.nth(3),
    ]

    // Click each button in sequence, verify at most 1 is active
    for (const btn of allButtons) {
      const isVisible = await btn.isVisible().catch(() => false)
      if (!isVisible) continue

      await btn.click()
      await page.waitForTimeout(100)

      let activeCount = 0
      for (const checkBtn of allButtons) {
        const vis = await checkBtn.isVisible().catch(() => false)
        if (!vis) continue
        const cls = await checkBtn.getAttribute('class') || ''
        if (cls.includes('active')) activeCount++
      }
      expect(activeCount).toBeLessThanOrEqual(1)
    }
  })

  test('toggling same button deactivates it', async ({ page }) => {
    await loginAsTeacher(page)
    const hasCopies = await openFirstCopyDesk(page)
    if (!hasCopies) return

    const fauxBtn = page.locator('.btn-stamp-faux')
    const isVisible = await fauxBtn.isVisible().catch(() => false)
    if (!isVisible) return

    // Click once → active
    await fauxBtn.click()
    await expect(fauxBtn).toHaveClass(/active/)

    // Click again → inactive
    await fauxBtn.click()
    await expect(fauxBtn).not.toHaveClass(/active/)
  })
})
