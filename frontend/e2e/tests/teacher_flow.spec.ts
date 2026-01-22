import { test, expect } from '@playwright/test';
import { loginAsAdmin } from './helpers/auth';

// Using direct API login with store hydration
// The router guard calls fetchUser() which we simulate in loginAsAdmin

test.describe('Admin Dashboard E2E', () => {

    test.beforeEach(async ({ page }) => {
        // Login via direct API calls and hydrate store
        await loginAsAdmin(page);

        // Small delay to ensure cookies are set
        await page.waitForTimeout(500);
    });

    test('should access dashboard with authenticated session', async ({ page }) => {
        // Navigate to admin dashboard
        // The router guard should see the cookies and allow access
        await page.goto('/admin-dashboard', { waitUntil: 'domcontentloaded' });

        // Wait for the fetchUser() call in router guard to complete
        await page.waitForResponse((r) => r.url().includes('/api/me/') || r.url().includes('/api/exams/'), { timeout: 10000 });

        // Wait for network to be idle
        await page.waitForLoadState('networkidle');

        // Verify dashboard loaded
        await expect(page.getByTestId('admin-dashboard')).toBeVisible({ timeout: 10000 });
        await expect(page.getByTestId('admin-dashboard-title')).toBeVisible();

        console.log('✓ Dashboard accessible with authenticated session');
    });

    test('should display admin interface elements', async ({ page }) => {
        // Navigate and wait for stable state
        await page.goto('/admin-dashboard', { waitUntil: 'domcontentloaded' });
        await page.waitForLoadState('networkidle');

        // Verify logout button is visible
        await expect(page.getByTestId('logout-button')).toBeVisible({ timeout: 10000 });

        // Verify dashboard title is visible
        await expect(page.getByTestId('admin-dashboard-title')).toBeVisible();

        console.log('✓ Admin interface elements visible');
    });

});
