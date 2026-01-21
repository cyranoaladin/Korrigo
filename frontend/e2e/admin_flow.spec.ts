import { test, expect } from '@playwright/test';

test('Admin Login and Dashboard Navigation', async ({ page }) => {
    // 1. Login Page
    await page.goto('http://localhost:8088/login');
    await expect(page.locator('.login-form')).toBeVisible();

    // 2. Perform Login
    await page.fill('input[type="email"]', 'alaeddine.benrhouma@ert.tn');
    await page.fill('input[type="password"]', 'adminpass');
    await page.click('button[type="submit"]');

    // 3. Verify Redirection to Dashboard
    await expect(page).toHaveURL('http://localhost:8088/admin-dashboard');
    await expect(page.locator('h1')).toContainText('Tableau de Bord Administrateur');

    // 4. Check Elements
    await expect(page.locator('.actions-bar')).toBeVisible();
    await expect(page.locator('button:has-text("Importer Scans")')).toBeVisible();

    // 5. Check if Table is present
    // Wait for loading to finish
    await expect(page.locator('.loading')).not.toBeVisible({ timeout: 10000 });

    // Either table or empty message
    const emptyCell = page.locator('.empty-cell');
    const table = page.locator('.data-table');

    if (await emptyCell.isVisible()) {
        console.log('Dashboard is empty, test passed.');
    } else {
        await expect(table).toBeVisible();
        console.log('Dashboard has exams, test passed.');

        // If exams exist, check Video-Coding button
        const videoBtn = page.locator('.btn-action').first();
        await expect(videoBtn).toBeVisible();
    }
});
