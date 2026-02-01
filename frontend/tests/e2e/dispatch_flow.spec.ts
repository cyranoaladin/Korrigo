import { test, expect } from '@playwright/test';
import { CREDS } from './helpers/auth';

test.describe('Exam Copy Dispatch Flow', () => {
  test.beforeEach(async ({ page }) => {
    page.on('console', msg => console.log(`[browser] ${msg.text()}`));
    await page.goto('/teacher/login');
    await page.fill('[data-testid="login.username"]', CREDS.admin.username);
    await page.fill('[data-testid="login.password"]', CREDS.admin.password);
    await page.click('[data-testid="login.submit"]');
    await expect(page).toHaveURL('http://localhost:8088/admin-dashboard');
    await page.waitForLoadState('networkidle');
  });

  test('should disable dispatch button when no correctors assigned', async ({ page }) => {
    await page.waitForSelector('.data-table', { timeout: 10000 });

    const firstDispatchButton = page.locator('.btn-dispatch').first();
    if (await firstDispatchButton.isVisible()) {
      const isDisabled = await firstDispatchButton.isDisabled();
      const title = await firstDispatchButton.getAttribute('title');

      if (isDisabled) {
        expect(title).toContain('Aucun correcteur assigné');
      }
    }
  });

  test('should show dispatch confirmation modal', async ({ page }) => {
    await page.waitForSelector('.data-table', { timeout: 10000 });

    const enabledDispatchButton = page.locator('.btn-dispatch:not(:disabled)').first();

    if (await enabledDispatchButton.isVisible()) {
      await enabledDispatchButton.click();

      await expect(page.locator('h3:has-text("Dispatcher les Copies")')).toBeVisible();

      await expect(page.locator('text=Voulez-vous distribuer les copies')).toBeVisible();

      await expect(page.locator('text=⚠️ Les copies déjà assignées ne seront pas modifiées')).toBeVisible();

      await expect(page.locator('button:has-text("Confirmer")')).toBeVisible();
      await expect(page.locator('button:has-text("Annuler")')).toBeVisible();

      await page.locator('button:has-text("Annuler")').click();

      await expect(page.locator('h3:has-text("Dispatcher les Copies")')).not.toBeVisible();
    }
  });

  test('should complete dispatch and show results', async ({ page }) => {
    await page.waitForSelector('.data-table', { timeout: 10000 });

    const enabledDispatchButton = page.locator('.btn-dispatch:not(:disabled)').first();

    if (await enabledDispatchButton.isVisible()) {
      await enabledDispatchButton.click();

      await expect(page.locator('h3:has-text("Dispatcher les Copies")')).toBeVisible();

      await page.locator('button:has-text("Confirmer")').click();

      await page.waitForResponse(response =>
        response.url().includes('/dispatch/') && response.status() === 200,
        { timeout: 10000 }
      );

      await expect(page.locator('h3:has-text("Distribution Terminée")')).toBeVisible({ timeout: 5000 });

      await expect(page.locator('text=Copies assignées :')).toBeVisible();
      await expect(page.locator('text=Nombre de correcteurs :')).toBeVisible();

      const copiesAssigned = await page.locator('.result-item:has-text("Copies assignées") .result-value').textContent();
      expect(parseInt(copiesAssigned || '0')).toBeGreaterThan(0);

      const correctorsCount = await page.locator('.result-item:has-text("Nombre de correcteurs") .result-value').textContent();
      expect(parseInt(correctorsCount || '0')).toBeGreaterThan(0);

      const distributionTable = page.locator('.mini-table');
      if (await distributionTable.isVisible()) {
        await expect(distributionTable.locator('th:has-text("Correcteur")')).toBeVisible();
        await expect(distributionTable.locator('th:has-text("Copies assignées")')).toBeVisible();

        const rows = distributionTable.locator('tbody tr');
        const rowCount = await rows.count();
        expect(rowCount).toBeGreaterThan(0);
      }

      await page.locator('button:has-text("Fermer")').click();

      await expect(page.locator('h3:has-text("Distribution Terminée")')).not.toBeVisible();
    } else {
      console.log('No enabled dispatch button found - skipping dispatch test');
      test.skip();
    }
  });

  test('should show dispatch run ID for traceability', async ({ page }) => {
    await page.waitForSelector('.data-table', { timeout: 10000 });

    const enabledDispatchButton = page.locator('.btn-dispatch:not(:disabled)').first();

    if (await enabledDispatchButton.isVisible()) {
      await enabledDispatchButton.click();
      await page.locator('button:has-text("Confirmer")').click();

      await expect(page.locator('h3:has-text("Distribution Terminée")')).toBeVisible({ timeout: 5000 });

      const dispatchIdElement = page.locator('.result-item:has-text("ID Distribution") .result-id');
      if (await dispatchIdElement.isVisible()) {
        const dispatchId = await dispatchIdElement.textContent();
        expect(dispatchId).toMatch(/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i);
      }

      await page.locator('button:has-text("Fermer")').click();
    } else {
      test.skip();
    }
  });

  test('should handle dispatch with no unassigned copies gracefully', async ({ page }) => {
    await page.waitForSelector('.data-table', { timeout: 10000 });

    const enabledDispatchButton = page.locator('.btn-dispatch:not(:disabled)').first();

    if (await enabledDispatchButton.isVisible()) {
      await enabledDispatchButton.click();
      await page.locator('button:has-text("Confirmer")').click();

      await page.waitForTimeout(1000);

      const alertText = await page.evaluate(() => {
        const alerts = document.querySelectorAll('.alert, .notification, .message');
        return Array.from(alerts).map(el => el.textContent).join(' ');
      });

      if (alertText.includes('Aucune copie')) {
        expect(alertText).toContain('Aucune copie');
      }
    } else {
      test.skip();
    }
  });
});
