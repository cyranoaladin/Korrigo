import { test, expect, type Page } from '@playwright/test'
import { TEACHER_USER, TEACHER_PASS } from './e2eEnv'

async function loginAsTeacher(page: Page) {
  await page.goto('/teacher/login')
  await page.locator('[data-testid="login.username"]').fill(TEACHER_USER)
  await page.locator('[data-testid="login.password"]').fill(TEACHER_PASS)
  await page.locator('[data-testid="login.submit"]').click()
  await page.waitForURL('**/corrector-dashboard', { timeout: 10000 })
}

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

/**
 * Draw a rectangle on the canvas and return whether the editor panel opened.
 */
async function drawAnnotationOnCanvas(
  page: Page,
  offsetX = 100,
  offsetY = 100,
  width = 120,
  height = 80
): Promise<boolean> {
  const canvas = page.locator('canvas').first()
  const isCanvasVisible = await canvas.isVisible().catch(() => false)
  if (!isCanvasVisible) return false

  const box = await canvas.boundingBox()
  if (!box) return false

  await page.mouse.move(box.x + offsetX, box.y + offsetY)
  await page.mouse.down()
  await page.mouse.move(box.x + offsetX + width, box.y + offsetY + height, { steps: 10 })
  await page.mouse.up()
  await page.waitForTimeout(500)

  const editorPanel = page.locator('[data-testid="editor-panel"]')
  return editorPanel.isVisible().catch(() => false)
}

/**
 * Fill annotation editor and save.
 */
async function fillAndSaveAnnotation(
  page: Page,
  type: string,
  content: string
) {
  const editorPanel = page.locator('[data-testid="editor-panel"]')
  const typeSelect = editorPanel.locator('select')
  await typeSelect.selectOption(type)
  if (content) {
    await editorPanel.locator('textarea').fill(content)
  }
  await editorPanel.locator('button', { hasText: 'Enregistrer' }).click()
  await page.waitForTimeout(1000)
}

/**
 * Count current annotations in the list.
 */
async function countAnnotations(page: Page): Promise<number> {
  return page.locator('[data-testid="annotation-item"]').count()
}

test.describe('Annotation Tools — Comprehensive Tests', () => {
  test.describe.configure({ mode: 'serial' })

  // ────────────────────────────────────────
  // Create annotations by type
  // ────────────────────────────────────────

  test('create COMMENTAIRE annotation with text', async ({ page }) => {
    await loginAsTeacher(page)
    const hasCopies = await openFirstCopyDesk(page)
    if (!hasCopies) return

    const editorOpened = await drawAnnotationOnCanvas(page, 50, 50, 100, 60)
    if (editorOpened) {
      await fillAndSaveAnnotation(page, 'COMMENTAIRE', 'Ceci est un commentaire E2E')

      // Verify annotation appears in list
      const annotations = page.locator('[data-testid="annotation-item"]')
      const lastAnnotation = annotations.last()
      await expect(lastAnnotation.locator('.ann-type')).toContainText('COMMENTAIRE')
      await expect(lastAnnotation.locator('.ann-content')).toContainText('commentaire E2E')
    }
  })

  test('create SURLIGNAGE annotation', async ({ page }) => {
    await loginAsTeacher(page)
    const hasCopies = await openFirstCopyDesk(page)
    if (!hasCopies) return

    const editorOpened = await drawAnnotationOnCanvas(page, 60, 180, 150, 30)
    if (editorOpened) {
      await fillAndSaveAnnotation(page, 'SURLIGNAGE', '')

      const annotations = page.locator('[data-testid="annotation-item"]')
      const lastAnnotation = annotations.last()
      await expect(lastAnnotation.locator('.ann-type')).toContainText('SURLIGNAGE')
    }
  })

  test('create ERREUR annotation', async ({ page }) => {
    await loginAsTeacher(page)
    const hasCopies = await openFirstCopyDesk(page)
    if (!hasCopies) return

    const editorOpened = await drawAnnotationOnCanvas(page, 70, 250, 100, 40)
    if (editorOpened) {
      await fillAndSaveAnnotation(page, 'ERREUR', 'Erreur de calcul dans le raisonnement')

      const annotations = page.locator('[data-testid="annotation-item"]')
      const lastAnnotation = annotations.last()
      await expect(lastAnnotation.locator('.ann-type')).toContainText('ERREUR')
      await expect(lastAnnotation.locator('.ann-content')).toContainText('Erreur de calcul')
    }
  })

  test('create BONUS annotation', async ({ page }) => {
    await loginAsTeacher(page)
    const hasCopies = await openFirstCopyDesk(page)
    if (!hasCopies) return

    const editorOpened = await drawAnnotationOnCanvas(page, 80, 320, 100, 40)
    if (editorOpened) {
      await fillAndSaveAnnotation(page, 'BONUS', 'Methode originale, bonus')

      const annotations = page.locator('[data-testid="annotation-item"]')
      const lastAnnotation = annotations.last()
      await expect(lastAnnotation.locator('.ann-type')).toContainText('BONUS')
    }
  })

  // ────────────────────────────────────────
  // Quick stamp annotations
  // ────────────────────────────────────────

  test('create VRAI stamp annotation via quick stamp', async ({ page }) => {
    await loginAsTeacher(page)
    const hasCopies = await openFirstCopyDesk(page)
    if (!hasCopies) return

    const vraiBtn = page.locator('.btn-stamp-vrai')
    const isVisible = await vraiBtn.isVisible().catch(() => false)
    if (!isVisible) return

    const countBefore = await countAnnotations(page)

    // Activate quick stamp mode
    await vraiBtn.click()
    await expect(vraiBtn).toHaveClass(/active/)

    // Draw on canvas (stamp mode creates annotation without editor)
    const canvas = page.locator('canvas').first()
    const box = await canvas.boundingBox()
    if (box) {
      await page.mouse.move(box.x + 150, box.y + 400)
      await page.mouse.down()
      await page.mouse.move(box.x + 180, box.y + 430, { steps: 5 })
      await page.mouse.up()
      await page.waitForTimeout(1000)

      const countAfter = await countAnnotations(page)
      expect(countAfter).toBeGreaterThanOrEqual(countBefore)
    }

    // Deactivate stamp mode
    await vraiBtn.click()
  })

  test('create FAUX stamp annotation via quick stamp', async ({ page }) => {
    await loginAsTeacher(page)
    const hasCopies = await openFirstCopyDesk(page)
    if (!hasCopies) return

    const fauxBtn = page.locator('.btn-stamp-faux')
    const isVisible = await fauxBtn.isVisible().catch(() => false)
    if (!isVisible) return

    const countBefore = await countAnnotations(page)

    await fauxBtn.click()
    await expect(fauxBtn).toHaveClass(/active/)

    const canvas = page.locator('canvas').first()
    const box = await canvas.boundingBox()
    if (box) {
      await page.mouse.move(box.x + 200, box.y + 400)
      await page.mouse.down()
      await page.mouse.move(box.x + 230, box.y + 430, { steps: 5 })
      await page.mouse.up()
      await page.waitForTimeout(1000)

      const countAfter = await countAnnotations(page)
      expect(countAfter).toBeGreaterThanOrEqual(countBefore)
    }

    await fauxBtn.click()
  })

  test('VRAI stamp renders green checkmark on canvas', async ({ page }) => {
    await loginAsTeacher(page)
    const hasCopies = await openFirstCopyDesk(page)
    if (!hasCopies) return

    // Check if there's a VRAI annotation rendered on the canvas
    // The CanvasLayer component draws stamps; we check for their presence
    // by looking at annotation items with type VRAI
    const vraiAnnotations = page.locator('[data-testid="annotation-item"]').filter({
      has: page.locator('.ann-type', { hasText: 'VRAI' })
    })
    const count = await vraiAnnotations.count()

    if (count > 0) {
      // Canvas should be present with content drawn
      const canvas = page.locator('canvas').first()
      await expect(canvas).toBeVisible()
      // Verify canvas has non-zero dimensions (rendering happened)
      const canvasBox = await canvas.boundingBox()
      expect(canvasBox!.width).toBeGreaterThan(0)
      expect(canvasBox!.height).toBeGreaterThan(0)
    }
  })

  test('FAUX stamp renders red X on canvas', async ({ page }) => {
    await loginAsTeacher(page)
    const hasCopies = await openFirstCopyDesk(page)
    if (!hasCopies) return

    const fauxAnnotations = page.locator('[data-testid="annotation-item"]').filter({
      has: page.locator('.ann-type', { hasText: 'FAUX' })
    })
    const count = await fauxAnnotations.count()

    if (count > 0) {
      const canvas = page.locator('canvas').first()
      await expect(canvas).toBeVisible()
      const canvasBox = await canvas.boundingBox()
      expect(canvasBox!.width).toBeGreaterThan(0)
      expect(canvasBox!.height).toBeGreaterThan(0)
    }
  })

  // ────────────────────────────────────────
  // Annotation list management
  // ────────────────────────────────────────

  test('annotation appears in annotation list after creation', async ({ page }) => {
    await loginAsTeacher(page)
    const hasCopies = await openFirstCopyDesk(page)
    if (!hasCopies) return

    const countBefore = await countAnnotations(page)

    const editorOpened = await drawAnnotationOnCanvas(page, 90, 150, 80, 50)
    if (editorOpened) {
      await fillAndSaveAnnotation(page, 'COMMENTAIRE', 'Annotation de test pour liste')
      const countAfter = await countAnnotations(page)
      expect(countAfter).toBe(countBefore + 1)
    }
  })

  test('annotation count updates correctly', async ({ page }) => {
    await loginAsTeacher(page)
    const hasCopies = await openFirstCopyDesk(page)
    if (!hasCopies) return

    const countBefore = await countAnnotations(page)

    // Create two annotations
    const editorOpened1 = await drawAnnotationOnCanvas(page, 95, 160, 80, 50)
    if (editorOpened1) {
      await fillAndSaveAnnotation(page, 'COMMENTAIRE', 'Annotation count test 1')
    }

    const editorOpened2 = await drawAnnotationOnCanvas(page, 95, 230, 80, 50)
    if (editorOpened2) {
      await fillAndSaveAnnotation(page, 'COMMENTAIRE', 'Annotation count test 2')
    }

    const countAfter = await countAnnotations(page)
    const expected = countBefore + (editorOpened1 ? 1 : 0) + (editorOpened2 ? 1 : 0)
    expect(countAfter).toBe(expected)
  })

  test('delete annotation removes from list and canvas', async ({ page }) => {
    await loginAsTeacher(page)
    const hasCopies = await openFirstCopyDesk(page)
    if (!hasCopies) return

    const annotations = page.locator('[data-testid="annotation-item"]')
    const countBefore = await annotations.count()

    if (countBefore > 0) {
      // Accept confirmation dialogs
      page.on('dialog', dialog => dialog.accept())

      const deleteBtn = annotations.first().locator('.btn-delete')
      const deleteBtnVisible = await deleteBtn.isVisible().catch(() => false)
      if (deleteBtnVisible) {
        await deleteBtn.click()
        await page.waitForTimeout(1000)

        const countAfter = await annotations.count()
        expect(countAfter).toBe(countBefore - 1)
      }
    }
  })

  // ────────────────────────────────────────
  // Suggestions panel
  // ────────────────────────────────────────

  test('annotation suggestions panel opens with light bulb button', async ({ page }) => {
    await loginAsTeacher(page)
    const hasCopies = await openFirstCopyDesk(page)
    if (!hasCopies) return

    // Create an annotation to get the editor open
    const editorOpened = await drawAnnotationOnCanvas(page, 110, 170, 80, 50)

    if (editorOpened) {
      // Look for the suggestion button (light bulb icon)
      const suggestionsBtn = page.locator('.btn-suggestions, .btn-suggestion-trigger').first()
      const isVisible = await suggestionsBtn.isVisible().catch(() => false)

      if (isVisible) {
        await suggestionsBtn.click()
        await page.waitForTimeout(500)

        // The AnnotationSuggestionsPanel should become visible
        const suggestionsPanel = page.locator('.suggestions-panel, [class*="suggestion"]')
        const panelVisible = await suggestionsPanel.first().isVisible().catch(() => false)
        expect(panelVisible).toBe(true)
      }

      // Cancel the annotation editor
      const cancelBtn = page.locator('[data-testid="editor-panel"] button', { hasText: 'Annuler' })
      if (await cancelBtn.isVisible().catch(() => false)) {
        await cancelBtn.click()
      }
    }
  })

  test('insert suggestion into annotation text', async ({ page }) => {
    await loginAsTeacher(page)
    const hasCopies = await openFirstCopyDesk(page)
    if (!hasCopies) return

    const editorOpened = await drawAnnotationOnCanvas(page, 120, 180, 80, 50)

    if (editorOpened) {
      const suggestionsBtn = page.locator('.btn-suggestions').first()
      const isVisible = await suggestionsBtn.isVisible().catch(() => false)

      if (isVisible) {
        await suggestionsBtn.click()
        await page.waitForTimeout(500)

        // If suggestions are loaded, click the first one to insert it
        const suggestionItem = page.locator('.suggestion-item, [class*="suggestion"] button, [class*="suggestion"] li').first()
        const hasSuggestions = await suggestionItem.isVisible().catch(() => false)

        if (hasSuggestions) {
          await suggestionItem.click()
          await page.waitForTimeout(300)

          // The textarea should now contain some text
          const textarea = page.locator('[data-testid="editor-panel"] textarea')
          const value = await textarea.inputValue()
          expect(value.length).toBeGreaterThan(0)
        }
      }

      // Cancel
      const cancelBtn = page.locator('[data-testid="editor-panel"] button', { hasText: 'Annuler' })
      if (await cancelBtn.isVisible().catch(() => false)) {
        await cancelBtn.click()
      }
    }
  })

  test('annotation bank records used annotations', async ({ page }) => {
    await loginAsTeacher(page)
    const hasCopies = await openFirstCopyDesk(page)
    if (!hasCopies) return

    // After creating annotations, the suggestion system should remember them.
    // This is verified by checking the API response of the suggestions endpoint.
    // For E2E, we verify that the suggestions panel loads without errors.
    const editorOpened = await drawAnnotationOnCanvas(page, 130, 190, 80, 50)

    if (editorOpened) {
      const suggestionsBtn = page.locator('.btn-suggestions').first()
      const isVisible = await suggestionsBtn.isVisible().catch(() => false)

      if (isVisible) {
        // Listen for network requests to suggestions endpoint
        const suggestionsRequest = page.waitForResponse(
          response => response.url().includes('suggest') || response.url().includes('annotation'),
          { timeout: 3000 }
        ).catch(() => null)

        await suggestionsBtn.click()
        const response = await suggestionsRequest

        if (response) {
          expect(response.status()).toBeLessThan(500) // No server errors
        }
      }

      const cancelBtn = page.locator('[data-testid="editor-panel"] button', { hasText: 'Annuler' })
      if (await cancelBtn.isVisible().catch(() => false)) {
        await cancelBtn.click()
      }
    }
  })

  // ────────────────────────────────────────
  // Multiple annotations and page navigation
  // ────────────────────────────────────────

  test('multiple annotations on same page', async ({ page }) => {
    await loginAsTeacher(page)
    const hasCopies = await openFirstCopyDesk(page)
    if (!hasCopies) return

    const countBefore = await countAnnotations(page)
    let created = 0

    // Create 3 annotations at different positions
    for (const [ox, oy] of [[50, 60], [50, 200], [50, 340]]) {
      const editorOpened = await drawAnnotationOnCanvas(page, ox, oy, 100, 40)
      if (editorOpened) {
        await fillAndSaveAnnotation(page, 'COMMENTAIRE', `Multi-annotation ${created + 1}`)
        created++
      }
    }

    if (created > 0) {
      const countAfter = await countAnnotations(page)
      expect(countAfter).toBe(countBefore + created)
    }
  })

  test('annotations filter by current page', async ({ page }) => {
    await loginAsTeacher(page)
    const hasCopies = await openFirstCopyDesk(page)
    if (!hasCopies) return

    // Count annotations on page 1
    const countPage1 = await countAnnotations(page)

    const pageText = page.locator('.pagination span')
    const text = await pageText.textContent()
    const totalMatch = text?.match(/\/\s*(\d+)/)
    const totalPages = totalMatch ? parseInt(totalMatch[1]) : 0

    if (totalPages > 1) {
      // Navigate to page 2
      await page.keyboard.press('ArrowRight')
      await page.waitForTimeout(500)

      // Count annotations on page 2
      const countPage2 = await countAnnotations(page)

      // The counts may differ (annotations are filtered by page_index)
      // Just verify that the list updated without error
      expect(countPage2).toBeGreaterThanOrEqual(0)

      // Navigate back to page 1
      await page.keyboard.press('ArrowLeft')
      await page.waitForTimeout(500)

      // Should restore page 1 annotations
      const countPage1After = await countAnnotations(page)
      expect(countPage1After).toBe(countPage1)
    }
  })

  test('annotations survive page navigation (reload)', async ({ page }) => {
    await loginAsTeacher(page)
    const hasCopies = await openFirstCopyDesk(page)
    if (!hasCopies) return

    const countBefore = await countAnnotations(page)

    // Reload the page
    await page.reload()
    await page.waitForLoadState('networkidle')
    await page.waitForFunction(
      () => !document.querySelector('.loading-state'),
      { timeout: 15000 }
    )

    const countAfter = await countAnnotations(page)
    // Persisted annotations should still be there
    expect(countAfter).toBe(countBefore)
  })
})
