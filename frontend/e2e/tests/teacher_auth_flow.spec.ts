import { test, expect } from '@playwright/test';
import { loginAsTeacher } from './helpers/auth';

test.describe('Teacher Auth Flow E2E', () => {

    test.beforeEach(async ({ page }) => {
        await loginAsTeacher(page);
        await page.waitForTimeout(500);
    });

    test('should login as teacher and access corrector dashboard', async ({ page }) => {
        await page.goto('/corrector-dashboard', { waitUntil: 'domcontentloaded' });
        await page.waitForLoadState('networkidle');

        await expect(page.getByTestId('corrector-dashboard')).toBeVisible({ timeout: 10000 });
        
        const brandElement = page.locator('.brand').first();
        await expect(brandElement).toContainText('Korrigo — Correcteur');

        console.log('✓ Teacher can access corrector dashboard');
    });

    test('should be able to access corrector desk if copy exists', async ({ page }) => {
        await page.goto('/corrector-dashboard', { waitUntil: 'domcontentloaded' });
        await page.waitForLoadState('networkidle');

        const copyCards = page.getByTestId('copy-card');
        const copyCount = await copyCards.count();

        if (copyCount > 0) {
            const firstCopyAction = copyCards.first().getByTestId('copy-action');
            
            await firstCopyAction.click();
            await page.waitForTimeout(2000);
            await page.waitForLoadState('networkidle');

            const currentUrl = page.url();
            expect(currentUrl).toContain('/corrector/desk/');

            console.log('✓ Teacher can access corrector desk');
        } else {
            console.log('⊘ No copies available to test desk access');
        }
    });

    test('should NOT be able to access admin pages', async ({ page }) => {
        await page.goto('/admin/users', { waitUntil: 'domcontentloaded' });
        await page.waitForLoadState('networkidle');

        const currentUrl = page.url();
        
        const isBlocked = currentUrl.includes('/admin/login') || 
                         currentUrl.includes('/corrector-dashboard') ||
                         (!currentUrl.includes('/admin/users'));
        
        expect(isBlocked).toBeTruthy();

        console.log('✓ Teacher blocked from admin pages (redirected to:', currentUrl, ')');
    });

    test('should logout and cannot access protected route', async ({ page }) => {
        await page.goto('/corrector-dashboard', { waitUntil: 'domcontentloaded' });
        await page.waitForLoadState('networkidle');

        const logoutButton = page.locator('.btn-logout');
        await logoutButton.click();
        
        await page.waitForTimeout(1500);
        await page.waitForLoadState('networkidle');

        await page.goto('/corrector-dashboard', { waitUntil: 'domcontentloaded' });
        await page.waitForLoadState('networkidle');

        const currentUrl = page.url();
        const isProtected = !currentUrl.includes('/corrector-dashboard') ||
                           currentUrl.includes('/login') ||
                           currentUrl === 'http://localhost:8088/';
        
        expect(isProtected).toBeTruthy();

        console.log('✓ Teacher logout successful, cannot access protected route after logout');
    });
});
