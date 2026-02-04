import { test, expect } from '@playwright/test';
import { loginAsStudent } from './helpers/auth';

test.describe('Student Auth Flow E2E', () => {

    test.beforeEach(async ({ page }) => {
        await loginAsStudent(page);
        await page.waitForTimeout(500);
    });

    test('should login as student and access student portal', async ({ page }) => {
        await page.goto('/student-portal', { waitUntil: 'domcontentloaded' });
        await page.waitForLoadState('networkidle');

        await expect(page.getByTestId('student-portal')).toBeVisible({ timeout: 10000 });
        
        const brandElement = page.locator('.brand').first();
        await expect(brandElement).toContainText('Korrigo — Espace Élève');

        console.log('✓ Student can access student portal');
    });

    test('should be able to view list of graded copies', async ({ page }) => {
        await page.goto('/student-portal', { waitUntil: 'domcontentloaded' });
        await page.waitForLoadState('networkidle');

        const copyListContainer = page.locator('.copy-list');
        
        const hasCopies = await copyListContainer.isVisible().catch(() => false);
        const emptyState = page.locator('.empty');
        const hasEmptyState = await emptyState.isVisible().catch(() => false);

        if (hasCopies) {
            const copies = copyListContainer.locator('li');
            const copyCount = await copies.count();
            expect(copyCount).toBeGreaterThan(0);

            console.log(`✓ Student can view ${copyCount} graded copy/copies`);
        } else if (hasEmptyState) {
            await expect(emptyState).toContainText('Aucune copie disponible');
            console.log('⊘ No graded copies available for student');
        } else {
            throw new Error('Neither copy list nor empty state is visible');
        }
    });

    test('should be able to download PDF if available', async ({ page }) => {
        await page.goto('/student-portal', { waitUntil: 'domcontentloaded' });
        await page.waitForLoadState('networkidle');

        const downloadButton = page.locator('.btn-download');
        const hasDownloadButton = await downloadButton.isVisible().catch(() => false);

        if (hasDownloadButton) {
            const downloadLink = await downloadButton.getAttribute('href');
            expect(downloadLink).toBeTruthy();
            expect(downloadLink).toContain('/api/grading/copies/');

            console.log('✓ Student can download PDF (download link verified)');
        } else {
            console.log('⊘ No PDF available for download');
        }
    });

    test('should NOT be able to access admin dashboard', async ({ page }) => {
        await page.goto('/admin-dashboard', { waitUntil: 'domcontentloaded' });
        await page.waitForLoadState('networkidle');

        const currentUrl = page.url();
        expect(currentUrl).not.toContain('/admin-dashboard');
        
        const finalUrl = page.url();
        expect(finalUrl === '/' || finalUrl.includes('/student-portal') || finalUrl.includes('/')).toBeTruthy();

        console.log('✓ Student redirected from admin dashboard');
    });

    test('should NOT be able to access corrector dashboard', async ({ page }) => {
        await page.goto('/corrector-dashboard', { waitUntil: 'domcontentloaded' });
        await page.waitForLoadState('networkidle');

        const currentUrl = page.url();
        expect(currentUrl).not.toContain('/corrector-dashboard');

        const finalUrl = page.url();
        expect(finalUrl === '/' || finalUrl.includes('/student-portal') || finalUrl.includes('/')).toBeTruthy();

        console.log('✓ Student redirected from corrector dashboard');
    });

    test('should logout and cannot access protected route', async ({ page }) => {
        await page.goto('/student-portal', { waitUntil: 'domcontentloaded' });
        await page.waitForLoadState('networkidle');

        const logoutButton = page.locator('.btn-logout');
        await logoutButton.click();

        await page.waitForTimeout(1500);
        await page.waitForLoadState('networkidle');

        await page.goto('/student-portal', { waitUntil: 'domcontentloaded' });
        await page.waitForLoadState('networkidle');

        const currentUrl = page.url();
        const isProtected = !currentUrl.includes('/student-portal') ||
                           currentUrl.includes('/login') ||
                           currentUrl === 'http://localhost:8088/';
        
        expect(isProtected).toBeTruthy();

        console.log('✓ Student logout successful, cannot access protected route after logout');
    });
});
