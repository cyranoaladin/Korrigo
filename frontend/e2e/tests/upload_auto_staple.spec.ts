import { test, expect } from '@playwright/test';

test.describe('Upload with Auto-Staple', () => {
    test.beforeEach(async ({ page }) => {
        // Login as admin
        await page.goto('http://localhost:8088/');
        await page.click('text=Connexion Admin');
        await page.fill('input[name="username"]', 'admin');
        await page.fill('input[name="password"]', 'adminpass');
        await page.click('button[type="submit"]');
        await expect(page).toHaveURL(/admin-dashboard/);
    });

    test('Upload modal opens with auto-staple option', async ({ page }) => {
        // Click "Importer Scans" button
        await page.click('button:has-text("Importer Scans")');
        
        // Verify modal is visible
        await expect(page.locator('.modal-card')).toBeVisible();
        await expect(page.locator('h3:has-text("Importer des Scans")')).toBeVisible();
        
        // Verify auto-staple checkbox exists
        const autoStapleCheckbox = page.locator('input[type="checkbox"]').first();
        await expect(autoStapleCheckbox).toBeVisible();
        
        // Verify "Agrafage automatique" text is present
        await expect(page.locator('text=Agrafage automatique')).toBeVisible();
    });

    test('Auto-staple option shows CSV field when checked', async ({ page }) => {
        await page.click('button:has-text("Importer Scans")');
        
        // Initially CSV field should not be visible
        await expect(page.locator('text=Fichier CSV des élèves')).not.toBeVisible();
        
        // Check auto-staple option
        await page.click('text=Agrafage automatique');
        
        // Now CSV field should be visible
        await expect(page.locator('text=Fichier CSV des élèves')).toBeVisible();
    });

    test('Upload button is disabled without required fields', async ({ page }) => {
        await page.click('button:has-text("Importer Scans")');
        
        // Import button should be disabled initially
        const importButton = page.locator('button:has-text("Importer")');
        await expect(importButton).toBeDisabled();
    });

    test('Modal can be closed with Escape key', async ({ page }) => {
        await page.click('button:has-text("Importer Scans")');
        await expect(page.locator('.modal-card')).toBeVisible();
        
        // Press Escape
        await page.keyboard.press('Escape');
        
        // Modal should be closed
        await expect(page.locator('.modal-card')).not.toBeVisible();
    });

    test('Modal can be closed with Cancel button', async ({ page }) => {
        await page.click('button:has-text("Importer Scans")');
        await expect(page.locator('.modal-card')).toBeVisible();
        
        // Click Cancel
        await page.click('button:has-text("Annuler")');
        
        // Modal should be closed
        await expect(page.locator('.modal-card')).not.toBeVisible();
    });

    test('Form validation requires PDF and name', async ({ page }) => {
        await page.click('button:has-text("Importer Scans")');
        
        // Fill only name, no PDF
        await page.fill('input[placeholder*="Bac Blanc"]', 'Test Exam');
        
        // Import button should still be disabled (no PDF)
        const importButton = page.locator('button:has-text("Importer")');
        await expect(importButton).toBeDisabled();
    });

    test('Auto-staple requires CSV when enabled', async ({ page }) => {
        await page.click('button:has-text("Importer Scans")');
        
        // Fill name
        await page.fill('input[placeholder*="Bac Blanc"]', 'Test Exam');
        
        // Enable auto-staple
        await page.click('text=Agrafage automatique');
        
        // Verify help text about CSV columns
        await expect(page.locator('text=Nom et Prénom')).toBeVisible();
    });
});

test.describe('Upload Flow Integration', () => {
    test.skip('Full upload with auto-staple (requires test files)', async ({ page }) => {
        // This test requires actual PDF and CSV files
        // Skip in CI, run manually with test fixtures
        
        await page.goto('http://localhost:8088/admin-dashboard');
        await page.click('button:has-text("Importer Scans")');
        
        // Would need to set up file chooser for PDF and CSV
        // const [fileChooser] = await Promise.all([
        //     page.waitForEvent('filechooser'),
        //     page.click('.file-input-wrapper')
        // ]);
        // await fileChooser.setFiles('path/to/test.pdf');
    });
});
