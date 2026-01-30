import { test, expect } from '@playwright/test';
import { CREDS } from './helpers/auth';

// Base URL: http://127.0.0.1:8088
test.describe('Corrector Flow & Robustness', () => {

    test('Full Corrector Cycle: Login -> Lock -> Annotate -> Autosave -> Refresh -> Restore', async ({ page }) => {
        // Network Logging
        page.on('console', msg => console.log('[browser]', msg.type(), msg.text()));
        page.on('pageerror', err => console.log('[pageerror]', err.message));

        page.on('response', async (resp) => {
            const url = resp.url();
            if (url.includes('/api/copies')) {
                console.log('[api]', resp.status(), url);
                try {
                    const txt = await resp.text();
                    console.log('[api-body]', txt.slice(0, 800));
                } catch (e) {
                    console.log('[api-body] <unreadable>');
                }
            }
        });

        // 1. LOGIN
        await page.goto('/teacher/login');
        await page.fill('input[type="text"]', CREDS.teacher.username);
        await page.fill('input[type="password"]', CREDS.teacher.password);
        await page.click('button[type="submit"]');

        // Wait for Dashboard
        await expect(page).toHaveURL(/\/corrector-dashboard/);

        // 2. OPEN COPY
        // Verify Dashboard Loaded
        await expect(page.locator('h2')).toContainText('Vos Copies à Corriger');
        await expect(page.locator('.user-menu')).toContainText('prof1');

        // Wait for list
        await expect(page.getByTestId('copy-card').first()).toBeVisible();

        // 3. LOCK ACQUISITION
        // Find the E2E-READY copy specifically using data attribute (more robust than hasText)
        const e2eCopyCard = page.locator('[data-copy-anon="E2E-READY"]');
        await expect(e2eCopyCard).toBeVisible();

        // Click and wait for navigation
        await Promise.all([
            page.waitForURL(/\/corrector\/desk\/.+/),
            e2eCopyCard.getByTestId('copy-action').click()
        ]);

        // Debug URL
        console.log('[url-after-click]', page.url());

        // Assume navigation to Desk
        await expect(page).toHaveURL(/\/corrector\/desk\/.+/);

        // Check for "Lock" indicator or "Read Only" alert
        // If status was READY, we expect a "Verrouiller" action or auto-lock.
        // If UI implements Soft Lock auto-acquire:
        // Check for "Mode : Édition"

        // 4. ANNOTATE & AUTOSAVE
        // Click on canvas to add annotation
        // Perform drag to create annotation (min 5x5px required by CanvasLayer)
        const canvas = page.getByTestId('canvas-layer');
        const box = await canvas.boundingBox();
        if (box) {
            await page.mouse.move(box.x + 100, box.y + 100);
            await page.mouse.down();
            await page.mouse.move(box.x + 200, box.y + 200); // 100x100 rect
            await page.mouse.up();
        }

        // Check Editor opens
        await expect(page.getByTestId('editor-panel')).toBeVisible();

        // Fill content
        await page.fill('textarea', 'Test E2E Annotation');
        await page.fill('input[type="number"]', '2'); // Points

        // Save
        await page.click('.editor-actions .btn-primary'); // "Save" button

        // Wait for "Sauvegardé" indicator
        await expect(page.getByTestId('save-indicator')).toContainText('Sauvegardé');

        // 5. REFRESH & RESTORE
        await page.reload();

        // Verify annotation persists (Restore from Draft or Server)
        // List should show item
        // Wait for list item
        await expect(page.getByTestId('annotation-item').first()).toContainText('Test E2E Annotation');
    });

});
