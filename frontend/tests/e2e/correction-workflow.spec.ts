import { test, expect } from '@playwright/test'

test.describe('Correction Workflow E2E Tests', () => {
  test.beforeEach(async ({ page }) => {
    // Mock authentication
    await page.goto('/login')
    await page.fill('[data-testid=username]', 'test-corrector')
    await page.fill('[data-testid=password]', 'test-password')
    await page.click('[data-testid=login-button]')
    
    // Wait for dashboard to load
    await page.waitForURL('/dashboard')
  })

  test('complete correction workflow', async ({ page }) => {
    // Navigate to exam list
    await page.click('[data-testid=exam-list-button]')
    await page.waitForURL('/exams')
    
    // Select an exam
    await page.click('[data-testid=exam-item-1]')
    await page.waitForURL('/exams/1/copies')
    
    // Select first copy
    await page.click('[data-testid=copy-item-1]')
    await page.waitForURL('/exams/1/copies/1/correct')
    
    // Verify PDF viewer is loaded
    await expect(page.locator('[data-testid=pdf-viewer]')).toBeVisible()
    
    // Test TrueFalseTool component
    await page.click('[data-testid=true-false-tool-true]')
    await expect(page.locator('[data-testid=true-false-tool]')).toHaveAttribute('data-value', 'true')
    
    // Test EnhancedGradingPanel
    await page.fill('[data-testid=score-input-1]', '8')
    await page.fill('[data-testid=remark-input-1]', 'Good work on this exercise')
    
    // Navigate to next page
    await page.click('[data-testid=next-page-button]')
    await page.waitForTimeout(1000)
    
    // Add annotation
    await page.click('[data-testid=annotation-tool]')
    await page.click('[data-testid=pdf-canvas]', { position: { x: 100, y: 100 } })
    await page.fill('[data-testid=annotation-text]', 'Check calculation here')
    await page.click('[data-testid=annotation-save]')
    
    // Navigate to next copy
    await page.click('[data-testid=next-copy-button]')
    await page.waitForURL('/exams/1/copies/2/correct')
    
    // Verify navigation worked
    await expect(page.locator('[data-testid=copy-header]')).toContainText('Copy 2')
    
    // Save progress
    await page.click('[data-testid=save-progress-button]')
    await expect(page.locator('[data-testid=save-success-message]')).toBeVisible()
  })

  test('keyboard navigation workflow', async ({ page }) => {
    // Navigate to correction page
    await page.goto('/exams/1/copies/1/correct')
    await page.waitForLoadState('networkidle')
    
    // Test keyboard shortcuts
    await page.keyboard.press('ArrowRight') // Next page
    await page.waitForTimeout(500)
    
    await page.keyboard.press('ArrowDown') // Next question
    await page.waitForTimeout(500)
    
    await page.keyboard.press('v') // True in TrueFalseTool
    await page.waitForTimeout(500)
    
    await page.keyboard.press('Ctrl+S') // Save
    await page.waitForTimeout(500)
    
    // Verify save indicator
    await expect(page.locator('[data-testid=save-indicator]')).toBeVisible()
  })

  test('bulk grading workflow', async ({ page }) => {
    // Navigate to bulk grading view
    await page.goto('/exams/1/bulk-grading')
    await page.waitForLoadState('networkidle')
    
    // Select multiple copies
    await page.check('[data-testid=copy-checkbox-1]')
    await page.check('[data-testid=copy-checkbox-2]')
    await page.check('[data-testid=copy-checkbox-3]')
    
    // Apply bulk score
    await page.click('[data-testid=bulk-score-button]')
    await page.fill('[data-testid=bulk-score-input]', '5')
    await page.click('[data-testid=apply-bulk-score]')
    
    // Verify scores applied
    await expect(page.locator('[data-testid=bulk-success-message]')).toBeVisible()
    
    // Apply bulk remark
    await page.click('[data-testid=bulk-remark-button]')
    await page.fill('[data-testid=bulk-remark-input]', 'Good performance overall')
    await page.click('[data-testid=apply-bulk-remark]')
    
    // Verify remarks applied
    await expect(page.locator('[data-testid=remark-success-message]')).toBeVisible()
  })

  test('annotation workflow', async ({ page }) => {
    // Navigate to correction page
    await page.goto('/exams/1/copies/1/correct')
    await page.waitForLoadState('networkidle')
    
    // Activate annotation tool
    await page.click('[data-testid=annotation-mode-toggle]')
    await expect(page.locator('[data-testid=annotation-toolbar]')).toBeVisible()
    
    // Add error annotation
    await page.click('[data-testid=error-annotation-button]')
    await page.click('[data-testid=pdf-canvas]', { position: { x: 200, y: 150 } })
    await page.fill('[data-testid=annotation-text]', 'Incorrect formula')
    await page.click('[data-testid=annotation-save]')
    
    // Add success annotation
    await page.click('[data-testid=success-annotation-button]')
    await page.click('[data-testid=pdf-canvas]', { position: { x: 300, y: 250 } })
    await page.fill('[data-testid=annotation-text]', 'Perfect solution!')
    await page.click('[data-testid=annotation-save]')
    
    // Verify annotations are visible
    await expect(page.locator('[data-testid=annotation-error]')).toBeVisible()
    await expect(page.locator('[data-testid=annotation-success]')).toBeVisible()
    
    // Edit annotation
    await page.click('[data-testid=annotation-error]')
    await page.fill('[data-testid=annotation-text]', 'Incorrect formula - check steps')
    await page.click('[data-testid=annotation-save]')
    
    // Delete annotation
    await page.click('[data-testid=annotation-success]')
    await page.click('[data-testid=annotation-delete]')
    await expect(page.locator('[data-testid=annotation-success]')).not.toBeVisible()
  })

  test('template and quick actions workflow', async ({ page }) => {
    // Navigate to correction page
    await page.goto('/exams/1/copies/1/correct')
    await page.waitForLoadState('networkidle')
    
    // Use quick score buttons
    await page.click('[data-testid=quick-max-button-1]')
    await expect(page.locator('[data-testid=score-input-1]')).toHaveValue('10')
    
    await page.click('[data-testid=quick-half-button-1]')
    await expect(page.locator('[data-testid=score-input-1]')).toHaveValue('5')
    
    await page.click('[data-testid=quick-zero-button-1]')
    await expect(page.locator('[data-testid=score-input-1]')).toHaveValue('0')
    
    // Use remark templates
    await page.click('[data-testid=template-dropdown-1]')
    await page.click('[data-testid=template-good-work]')
    await expect(page.locator('[data-testid=remark-input-1]')).toHaveValue('Good work overall')
    
    // Create custom template
    await page.click('[data-testid=save-template-button]')
    await page.fill('[data-testid=template-name]', 'Excellent solution')
    await page.fill('[data-testid=template-content]', 'Excellent solution with clear steps')
    await page.click('[data-testid=create-template]')
    
    // Verify template is available
    await page.click('[data-testid=template-dropdown-1]')
    await expect(page.locator('[data-testid=template-excellent-solution]')).toBeVisible()
  })

  test('validation and error handling workflow', async ({ page }) => {
    // Navigate to correction page
    await page.goto('/exams/1/copies/1/correct')
    await page.waitForLoadState('networkidle')
    
    // Try to submit with invalid scores
    await page.fill('[data-testid=score-input-1]', '15') // Exceeds max points
    await page.click('[data-testid=validate-button]')
    
    // Verify error message
    await expect(page.locator('[data-testid=validation-error]')).toBeVisible()
    await expect(page.locator('[data-testid=validation-error]')).toContainText('Score cannot exceed')
    
    // Fix the error
    await page.fill('[data-testid=score-input-1]', '8')
    await page.click('[data-testid=validate-button]')
    
    // Verify success
    await expect(page.locator('[data-testid=validation-success]')).toBeVisible()
    
    // Test auto-save
    await page.fill('[data-testid=score-input-2]', '7')
    await page.waitForTimeout(2000) // Wait for auto-save
    
    // Refresh page to verify auto-save worked
    await page.reload()
    await page.waitForLoadState('networkidle')
    await expect(page.locator('[data-testid=score-input-2]')).toHaveValue('7')
  })

  test('responsive design workflow', async ({ page }) => {
    // Test desktop view
    await page.setViewportSize({ width: 1200, height: 800 })
    await page.goto('/exams/1/copies/1/correct')
    await page.waitForLoadState('networkidle')
    
    // Verify desktop layout
    await expect(page.locator('[data-testid=sidebar]')).toBeVisible()
    await expect(page.locator('[data-testid=main-content]')).toBeVisible()
    await expect(page.locator('[data-testid=pdf-viewer]')).toBeVisible()
    
    // Test tablet view
    await page.setViewportSize({ width: 768, height: 1024 })
    await expect(page.locator('[data-testid=sidebar]')).toBeVisible()
    await expect(page.locator('[data-testid=mobile-menu-toggle]')).toBeVisible()
    
    // Test mobile view
    await page.setViewportSize({ width: 375, height: 667 })
    await expect(page.locator('[data-testid=sidebar]')).not.toBeVisible()
    await expect(page.locator('[data-testid=mobile-menu-toggle]')).toBeVisible()
    
    // Test mobile menu
    await page.click('[data-testid=mobile-menu-toggle]')
    await expect(page.locator('[data-testid=mobile-menu]')).toBeVisible()
    
    // Close mobile menu
    await page.click('[data-testid=mobile-menu-toggle]')
    await expect(page.locator('[data-testid=mobile-menu]')).not.toBeVisible()
  })
})
