import { test, expect, Page } from '@playwright/test';

// E2E credentials from seed script
const ADMIN_USERNAME = process.env.E2E_ADMIN_USERNAME || 'admin';
const ADMIN_PASSWORD = process.env.E2E_ADMIN_PASSWORD || 'admin';

/**
 * Helper function to login as admin via UI
 */
async function loginAsAdminUI(page: Page, username: string, password: string) {
    await page.goto('/admin/login');
    await expect(page.locator('.login-form')).toBeVisible();

    await page.fill('[data-testid="login.username"]', username);
    await page.fill('[data-testid="login.password"]', password);
    await page.click('[data-testid="login.submit"]');
}

/**
 * Helper function to logout
 */
async function logout(page: Page) {
    const logoutButton = page.getByTestId('logout-button');
    await expect(logoutButton).toBeVisible({ timeout: 10000 });
    await logoutButton.click();
    await page.waitForLoadState('networkidle');
}

test.describe('Admin Authentication Flow', () => {

    test('Admin login → dashboard (verify URL and page content)', async ({ page }) => {
        // Navigate to admin login page
        await loginAsAdminUI(page, ADMIN_USERNAME, ADMIN_PASSWORD);

        // Wait for redirect to dashboard
        await page.waitForURL(/\/admin-dashboard/, { timeout: 10000 });
        
        // Verify we're on the correct URL
        expect(page.url()).toContain('/admin-dashboard');

        // Wait for network to settle
        await page.waitForLoadState('networkidle');

        // Verify dashboard loaded correctly
        await expect(page.getByTestId('admin-dashboard')).toBeVisible({ timeout: 10000 });
        await expect(page.getByTestId('admin-dashboard-title')).toBeVisible();

        // Take screenshot for documentation
        await page.screenshot({ 
            path: 'e2e-screenshots/admin-login-dashboard.png',
            fullPage: true 
        });

        console.log('✓ Admin login successful, dashboard loaded');
    });

    test('Admin can access /admin/users (role-based access allowed)', async ({ page }) => {
        // Login first
        await loginAsAdminUI(page, ADMIN_USERNAME, ADMIN_PASSWORD);
        await page.waitForURL(/\/admin-dashboard/, { timeout: 10000 });
        await page.waitForLoadState('networkidle');

        // Navigate to user management page
        await page.goto('/admin/users');
        await page.waitForLoadState('networkidle');

        // Verify we're on the correct page (not redirected)
        expect(page.url()).toContain('/admin/users');

        // Wait for the page to load (check for common elements on user management page)
        // The page should have a heading or some content
        const pageContent = page.locator('body');
        await expect(pageContent).toBeVisible();

        // Take screenshot for documentation
        await page.screenshot({ 
            path: 'e2e-screenshots/admin-users-access.png',
            fullPage: true 
        });

        console.log('✓ Admin can access /admin/users page');
    });

    test('Admin logout → back button → redirected to home', async ({ page }) => {
        // Login first
        await loginAsAdminUI(page, ADMIN_USERNAME, ADMIN_PASSWORD);
        await page.waitForURL(/\/admin-dashboard/, { timeout: 10000 });
        await page.waitForLoadState('networkidle');

        // Verify we're on dashboard
        await expect(page.getByTestId('admin-dashboard')).toBeVisible();

        // Logout
        await logout(page);

        // Wait for redirect to home
        await page.waitForURL(/\/$/, { timeout: 10000 });
        expect(page.url()).toMatch(/\/$/);

        // Try to go back (browser back button)
        await page.goBack();
        await page.waitForLoadState('networkidle');

        // Should be redirected to home, not cached dashboard
        // The router guard should detect no session and redirect
        await page.waitForTimeout(1000); // Give time for guard to run
        
        // Check that we're still on home or login page (not dashboard)
        const currentUrl = page.url();
        expect(currentUrl).not.toContain('/admin-dashboard');
        expect(currentUrl).toMatch(/\/($|admin\/login|teacher\/login)/);

        // Take screenshot for documentation
        await page.screenshot({ 
            path: 'e2e-screenshots/admin-logout-back-button.png',
            fullPage: true 
        });

        console.log('✓ Back button after logout does not restore session');
    });

    // TODO: This test is pending - the ChangePasswordModal component is implemented but needs
    // additional investigation to ensure it shows when must_change_password is true
    test.skip('Admin with must_change_password → modal appears → change password → dashboard loads', async ({ page, context }) => {
        // Use pre-seeded test admin with must_change_password=True
        // This user is created in seed_e2e.py with the flag already set
        const testAdminUsername = 'test_admin_password_change';
        const testAdminPassword = 'initialpass123';
        const newPassword = 'newSecurePass123';

        // Step 1: Login as test admin with must_change_password flag
        await loginAsAdminUI(page, testAdminUsername, testAdminPassword);

        // Step 2: Wait for modal to appear
        await page.waitForLoadState('networkidle');
        
        // The modal should appear because must_change_password is true
        const modalOverlay = page.locator('.modal-overlay');
        await expect(modalOverlay).toBeVisible({ timeout: 10000 });
        
        const modalHeader = page.locator('.modal-header h2');
        await expect(modalHeader).toContainText('Changement de mot de passe requis');

        console.log('✓ Forced password change modal appeared');

        // Take screenshot of modal
        await page.screenshot({ 
            path: 'e2e-screenshots/admin-forced-password-modal.png',
            fullPage: true 
        });

        // Step 3: Fill in new password in the modal
        await page.fill('#new-password', newPassword);
        await page.fill('#confirm-password', newPassword);

        // Step 4: Submit password change
        const submitButton = page.locator('.modal-content button[type="submit"]');
        await expect(submitButton).toBeEnabled();
        await submitButton.click();

        // Step 5: Wait for modal to close and dashboard to load
        await expect(modalOverlay).not.toBeVisible({ timeout: 10000 });

        // Dashboard should now be visible
        await page.waitForURL(/\/admin-dashboard/, { timeout: 10000 });
        await expect(page.getByTestId('admin-dashboard')).toBeVisible({ timeout: 10000 });

        console.log('✓ Password changed successfully, dashboard loaded');

        // Take screenshot after password change
        await page.screenshot({ 
            path: 'e2e-screenshots/admin-after-password-change.png',
            fullPage: true 
        });

        console.log('✓ Password change flow completed successfully');
    });

});
