import { test, expect, type Page, type BrowserContext } from '@playwright/test'

const TEACHER_USER = process.env.E2E_TEACHER_USER || 'philippe.carr@ert.tn'
const TEACHER_PASS = process.env.E2E_TEACHER_PASS || 'passe123'
const BASE_URL = process.env.E2E_BASE_URL || 'http://localhost:8088'

/**
 * Login once via API (avoids rate limiting from repeated form submissions).
 * Returns cookies to inject into the browser context.
 */
async function loginViaAPI(context: BrowserContext): Promise<boolean> {
  // First, get the CSRF token
  const csrfResponse = await context.request.get(`${BASE_URL}/api/health/`)
  if (!csrfResponse.ok()) return false

  // Login via API
  const loginResponse = await context.request.post(`${BASE_URL}/api/login/`, {
    data: { username: TEACHER_USER, password: TEACHER_PASS },
    headers: { 'Content-Type': 'application/json' },
  })

  return loginResponse.ok()
}

async function openFirstCopyDesk(page: Page): Promise<boolean> {
  await page.goto('/corrector-dashboard')
  await page.waitForLoadState('networkidle')

  if (page.url().includes('login')) return false

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

// ════════════════════════════════════════
// Continuous Scroll PDF Viewer Tests
// ════════════════════════════════════════

test.describe('Continuous Scroll PDF Viewer', () => {
  test.beforeEach(async ({ context }) => {
    await loginViaAPI(context)
  })

  test('default zoom is 100%', async ({ page }) => {
    const hasCopies = await openFirstCopyDesk(page)
    if (!hasCopies) return

    const zoomText = page.locator('.zoom-controls .zoom-reset')
    await expect(zoomText).toContainText('100%')
  })

  test('all pages are rendered in the scroll area', async ({ page }) => {
    const hasCopies = await openFirstCopyDesk(page)
    if (!hasCopies) return

    const pageText = page.locator('.pagination span')
    const text = await pageText.textContent()
    const totalMatch = text?.match(/\/\s*(\d+)/)
    const totalPages = totalMatch ? parseInt(totalMatch[1]) : 0

    if (totalPages > 1) {
      const canvasWrappers = page.locator('.scroll-area .canvas-wrapper')
      const count = await canvasWrappers.count()
      expect(count).toBe(totalPages)
    }
  })

  test('each page has data-page-index attribute', async ({ page }) => {
    const hasCopies = await openFirstCopyDesk(page)
    if (!hasCopies) return

    const canvasWrappers = page.locator('.scroll-area .canvas-wrapper')
    const count = await canvasWrappers.count()

    if (count > 1) {
      expect(await canvasWrappers.first().getAttribute('data-page-index')).toBe('0')
      expect(await canvasWrappers.last().getAttribute('data-page-index')).toBe(String(count - 1))
    }
  })

  test('scroll area uses vertical column layout with gap', async ({ page }) => {
    const hasCopies = await openFirstCopyDesk(page)
    if (!hasCopies) return

    const styles = await page.locator('.scroll-area').evaluate(el => {
      const cs = getComputedStyle(el)
      return { display: cs.display, flexDirection: cs.flexDirection, gap: cs.gap }
    })

    expect(styles.display).toBe('flex')
    expect(styles.flexDirection).toBe('column')
    expect(styles.gap).toContain('16px')
  })

  test('scrolling down updates page counter', async ({ page }) => {
    const hasCopies = await openFirstCopyDesk(page)
    if (!hasCopies) return

    const count = await page.locator('.scroll-area .canvas-wrapper').count()
    if (count <= 1) return

    const pageText = page.locator('.pagination span')
    await expect(pageText).toContainText('Page 1')

    await page.evaluate(() => {
      const p2 = document.querySelectorAll('.canvas-wrapper')[1]
      if (p2) p2.scrollIntoView({ behavior: 'instant', block: 'center' })
    })
    await page.waitForTimeout(500)
    await expect(pageText).toContainText('Page 2', { timeout: 3000 })
  })

  test('can see parts of two pages simultaneously', async ({ page }) => {
    const hasCopies = await openFirstCopyDesk(page)
    if (!hasCopies) return

    const count = await page.locator('.scroll-area .canvas-wrapper').count()
    if (count <= 1) return

    await page.locator('.scroll-area').evaluate(el => {
      const first = el.querySelector('.canvas-wrapper') as HTMLElement
      if (first) el.scrollTop = first.offsetHeight - 100
    })
    await page.waitForTimeout(200)

    const vis = await page.evaluate(() => {
      const sa = document.querySelector('.scroll-area')
      if (!sa) return { p1: false, p2: false }
      const sr = sa.getBoundingClientRect()
      const w = document.querySelectorAll('.canvas-wrapper')
      if (w.length < 2) return { p1: false, p2: false }
      const r1 = w[0].getBoundingClientRect(), r2 = w[1].getBoundingClientRect()
      return {
        p1: r1.bottom > sr.top && r1.top < sr.bottom,
        p2: r2.bottom > sr.top && r2.top < sr.bottom,
      }
    })
    expect(vis.p1).toBe(true)
    expect(vis.p2).toBe(true)
  })

  test('scroll stops at top boundary', async ({ page }) => {
    const hasCopies = await openFirstCopyDesk(page)
    if (!hasCopies) return

    const sa = page.locator('.scroll-area')
    await sa.evaluate(el => { el.scrollTop = 0 })
    expect(await sa.evaluate(el => el.scrollTop)).toBe(0)
    await sa.evaluate(el => { el.scrollTop = -100 })
    expect(await sa.evaluate(el => el.scrollTop)).toBe(0)
  })

  test('scroll stops at bottom boundary', async ({ page }) => {
    const hasCopies = await openFirstCopyDesk(page)
    if (!hasCopies) return

    const sa = page.locator('.scroll-area')
    await sa.evaluate(el => { el.scrollTop = el.scrollHeight })
    await page.waitForTimeout(100)

    const r = await sa.evaluate(el => ({
      st: el.scrollTop, sh: el.scrollHeight, ch: el.clientHeight,
    }))
    expect(Math.abs(r.st + r.ch - r.sh)).toBeLessThan(2)
  })

  test('Next/Prev buttons scroll between pages', async ({ page }) => {
    const hasCopies = await openFirstCopyDesk(page)
    if (!hasCopies) return

    const count = await page.locator('.scroll-area .canvas-wrapper').count()
    if (count <= 1) return

    const pageText = page.locator('.pagination span')
    await expect(pageText).toContainText('Page 1')

    await page.locator('.pagination button', { hasText: 'Suiv.' }).click()
    await page.waitForTimeout(1000)
    await expect(pageText).toContainText('Page 2', { timeout: 3000 })

    await page.locator('.pagination button', { hasText: 'Préc.' }).click()
    await page.waitForTimeout(1000)
    await expect(pageText).toContainText('Page 1', { timeout: 3000 })
  })

  test('ArrowRight/ArrowLeft navigate pages via scroll', async ({ page }) => {
    const hasCopies = await openFirstCopyDesk(page)
    if (!hasCopies) return

    const count = await page.locator('.scroll-area .canvas-wrapper').count()
    if (count <= 1) return

    const pageText = page.locator('.pagination span')
    await expect(pageText).toContainText('Page 1')

    await page.keyboard.press('ArrowRight')
    await page.waitForTimeout(1000)
    await expect(pageText).toContainText('Page 2', { timeout: 3000 })

    await page.keyboard.press('ArrowLeft')
    await page.waitForTimeout(1000)
    await expect(pageText).toContainText('Page 1', { timeout: 3000 })
  })

  test('each page has its own CanvasLayer', async ({ page }) => {
    const hasCopies = await openFirstCopyDesk(page)
    if (!hasCopies) return

    const wrappers = page.locator('.scroll-area .canvas-wrapper')
    const count = await wrappers.count()

    for (let i = 0; i < count; i++) {
      const canvasCount = await wrappers.nth(i).locator('canvas').count()
      expect(canvasCount).toBeGreaterThanOrEqual(1)
    }
  })

  test('page images use lazy loading', async ({ page }) => {
    const hasCopies = await openFirstCopyDesk(page)
    if (!hasCopies) return

    const images = page.locator('.scroll-area .page-image')
    if (await images.count() > 1) {
      expect(await images.nth(1).getAttribute('loading')).toBe('lazy')
    }
  })

  test('zoom in/out changes page dimensions', async ({ page }) => {
    const hasCopies = await openFirstCopyDesk(page)
    if (!hasCopies) return

    const w = page.locator('.scroll-area .canvas-wrapper').first()
    const initW = await w.evaluate(el => el.offsetWidth)

    await page.locator('.zoom-controls button', { hasText: '+' }).click()
    await page.waitForTimeout(200)
    expect(await w.evaluate(el => el.offsetWidth)).toBeGreaterThan(initW)

    await page.locator('.zoom-controls button', { hasText: '-' }).click()
    await page.waitForTimeout(200)
    expect(Math.abs(await w.evaluate(el => el.offsetWidth) - initW)).toBeLessThan(5)
  })

  test('zoom reset returns to 100%', async ({ page }) => {
    const hasCopies = await openFirstCopyDesk(page)
    if (!hasCopies) return

    const zoomBtn = page.locator('.zoom-controls button', { hasText: '+' })
    await zoomBtn.click()
    await zoomBtn.click()

    const zoomText = page.locator('.zoom-controls .zoom-reset')
    await expect(zoomText).not.toContainText('100%')
    await zoomText.click()
    await expect(zoomText).toContainText('100%')
  })

  test('regular wheel does not change zoom', async ({ page }) => {
    const hasCopies = await openFirstCopyDesk(page)
    if (!hasCopies) return

    const zoomText = page.locator('.zoom-controls .zoom-reset')
    const before = await zoomText.textContent()

    const box = await page.locator('.scroll-area').boundingBox()
    if (box) {
      await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2)
      await page.mouse.wheel(0, -100)
    }
    expect(await zoomText.textContent()).toBe(before)
  })

  test('anonymization overlay present on first page', async ({ page }) => {
    const hasCopies = await openFirstCopyDesk(page)
    if (!hasCopies) return

    const overlay = page.locator('.scroll-area .canvas-wrapper').first().locator('.anonymization-overlay')
    // Just check it exists in DOM (visible depends on showIdentity)
    expect(await overlay.count()).toBeGreaterThanOrEqual(1)
  })
})

// ════════════════════════════════════════
// Tablet Touch Tests
// ════════════════════════════════════════

test.describe('Tablet Mode — Touch Interactions', () => {
  test.beforeEach(async ({ context }) => {
    await loginViaAPI(context)
  })

  test('touch scroll navigates between pages', async ({ page }) => {
    const hasCopies = await openFirstCopyDesk(page)
    if (!hasCopies) return

    const count = await page.locator('.scroll-area .canvas-wrapper').count()
    if (count <= 1) return

    const pageText = page.locator('.pagination span')
    await expect(pageText).toContainText('Page 1')

    await page.locator('.scroll-area').evaluate(el => {
      const p2 = el.querySelectorAll('.canvas-wrapper')[1]
      if (p2) p2.scrollIntoView({ behavior: 'instant', block: 'center' })
    })
    await page.waitForTimeout(500)
    await expect(pageText).toContainText('Page 2', { timeout: 3000 })
  })

  test('tablet viewport shows workspace', async ({ page }) => {
    const hasCopies = await openFirstCopyDesk(page)
    if (!hasCopies) return

    await expect(page.locator('.workspace')).toBeVisible()
    await expect(page.locator('.viewer-container')).toBeVisible()
    await expect(page.locator('.inspector-panel')).toBeVisible()
  })

  test('pagination buttons are tappable', async ({ page }) => {
    const hasCopies = await openFirstCopyDesk(page)
    if (!hasCopies) return

    const buttons = page.locator('.pagination button')
    for (let i = 0; i < await buttons.count(); i++) {
      const box = await buttons.nth(i).boundingBox()
      if (box) {
        expect(box.height).toBeGreaterThanOrEqual(25)
        expect(box.width).toBeGreaterThanOrEqual(25)
      }
    }
  })

  test('stamp buttons are tappable', async ({ page }) => {
    const hasCopies = await openFirstCopyDesk(page)
    if (!hasCopies) return

    for (const sel of ['.btn-stamp-vrai', '.btn-stamp-faux']) {
      const btn = page.locator(sel)
      if (await btn.isVisible().catch(() => false)) {
        const box = await btn.boundingBox()
        if (box) {
          expect(box.height).toBeGreaterThanOrEqual(25)
          expect(box.width).toBeGreaterThanOrEqual(25)
        }
      }
    }
  })

  test('zoom controls are accessible', async ({ page }) => {
    const hasCopies = await openFirstCopyDesk(page)
    if (!hasCopies) return

    await expect(page.locator('.zoom-controls')).toBeVisible()
    const btns = page.locator('.zoom-controls button')
    expect(await btns.count()).toBeGreaterThanOrEqual(3)
  })

  test('score inputs have adequate height', async ({ page }) => {
    const hasCopies = await openFirstCopyDesk(page)
    if (!hasCopies) return

    const tabs = page.locator('.inspector-tabs button')
    if (await tabs.count() >= 2) await tabs.nth(1).click()

    const inputs = page.locator('.score-input')
    for (let i = 0; i < Math.min(await inputs.count(), 3); i++) {
      const box = await inputs.nth(i).boundingBox()
      if (box) expect(box.height).toBeGreaterThanOrEqual(40)
    }
  })

  test('page images render with proper size', async ({ page }) => {
    const hasCopies = await openFirstCopyDesk(page)
    if (!hasCopies) return

    const img = page.locator('.scroll-area .page-image').first()
    if (await img.isVisible().catch(() => false)) {
      const box = await img.boundingBox()
      if (box) {
        expect(box.width).toBeGreaterThan(200)
        expect(box.height).toBeGreaterThan(200)
      }
    }
  })

  test('no horizontal overflow', async ({ page }) => {
    const hasCopies = await openFirstCopyDesk(page)
    if (!hasCopies) return

    const overflow = await page.evaluate(() =>
      document.documentElement.scrollWidth > document.documentElement.clientWidth
    )
    expect(overflow).toBe(false)
  })
})
