import { test, expect } from '@playwright/test';
import { loginAsAdmin } from './helpers/auth';

test.describe('Upload Scans Modal', () => {
    test.beforeEach(async ({ page }) => {
        await loginAsAdmin(page);
        await page.waitForTimeout(500);
    });

    test('Upload modal opens with correct structure', async ({ page }) => {
        // Click "Importer Scans" button
        await page.getByTestId('exams.import').click();
        
        // Verify modal is visible with correct title
        await expect(page.locator('h3:has-text("Importer des Scans")')).toBeVisible();
        
        // Verify required fields are present
        await expect(page.locator('text=Nom de l\'examen')).toBeVisible();
        await expect(page.locator('text=Fichiers PDF des scans')).toBeVisible();
        
        // Verify optional fields are present
        await expect(page.locator('text=Fichier CSV des élèves')).toBeVisible();
        await expect(page.locator('text=Fichier PDF des annexes')).toBeVisible();
    });

    test('CSV field shows helper text about columns', async ({ page }) => {
        await page.getByTestId('exams.import').click();
        
        // CSV helper text should be visible
        await expect(page.locator('text=Nom et Prénom')).toBeVisible();
        await expect(page.locator('text=Date de naissance')).toBeVisible();
    });

    test('Upload button is disabled without required fields', async ({ page }) => {
        await page.getByTestId('exams.import').click();
        
        // The submit button inside the modal (exact match "Importer", not "Importer Scans")
        const submitButton = page.getByRole('button', { name: 'Importer', exact: true });
        await expect(submitButton).toBeDisabled();
    });

    test('Modal can be closed with Escape key', async ({ page }) => {
        await page.getByTestId('exams.import').click();
        await expect(page.locator('h3:has-text("Importer des Scans")')).toBeVisible();
        
        // Press Escape
        await page.keyboard.press('Escape');
        
        // Modal should be closed
        await expect(page.locator('h3:has-text("Importer des Scans")')).not.toBeVisible();
    });

    test('Modal can be closed with Cancel button', async ({ page }) => {
        await page.getByTestId('exams.import').click();
        await expect(page.locator('h3:has-text("Importer des Scans")')).toBeVisible();
        
        // Click Cancel
        await page.click('button:has-text("Annuler")');
        
        // Modal should be closed
        await expect(page.locator('h3:has-text("Importer des Scans")')).not.toBeVisible();
    });

    test('Form validation requires PDF and name', async ({ page }) => {
        await page.getByTestId('exams.import').click();
        
        // Fill only name, no PDF
        await page.fill('input[placeholder*="Bac Blanc"]', 'Test Exam');
        
        // Import button should still be disabled (no PDF)
        const submitButton = page.getByRole('button', { name: 'Importer', exact: true });
        await expect(submitButton).toBeDisabled();
    });
});

test.describe('Upload Flow Integration', () => {
    test.skip('Full upload with auto-staple (requires test files)', async ({ page }) => {
        // This test requires actual PDF and CSV files
        // Skip in CI, run manually with test fixtures
        
        await page.goto('/admin-dashboard');
        await page.getByTestId('exams.import').click();
        
        // Would need to set up file chooser for PDF and CSV
        // const [fileChooser] = await Promise.all([
        //     page.waitForEvent('filechooser'),
        //     page.click('.file-input-wrapper')
        // ]);
        // await fileChooser.setFiles('path/to/test.pdf');
    });
});
