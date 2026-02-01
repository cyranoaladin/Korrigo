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

    await page.fill('input[type="email"]', username);
    await page.fill('input[type="password"]', password);
    await page.click('button[type="submit"]');
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
            path: 'e2e/screenshots/admin-login-dashboard.png',
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
            path: 'e2e/screenshots/admin-users-access.png',
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
            path: 'e2e/screenshots/admin-logout-back-button.png',
            fullPage: true 
        });

        console.log('✓ Back button after logout does not restore session');
    });

    test('Admin with must_change_password → modal appears → change password → dashboard loads', async ({ page, context }) => {
        // Step 1: Login as admin normally first to set up must_change_password
        await loginAsAdminUI(page, ADMIN_USERNAME, ADMIN_PASSWORD);
        await page.waitForURL(/\/admin-dashboard/, { timeout: 10000 });
        await page.waitForLoadState('networkidle');

        // Step 2: Create a test admin user with must_change_password via API
        // This simulates an admin that was created or had password reset
        const testAdminUsername = 'test_admin_password_change';
        const testAdminPassword = 'initialpass123';
        const newPassword = 'newSecurePass123';

        // Create test admin user via API
        const createResponse = await page.evaluate(async ({ username, password }) => {
            const res = await fetch('/api/users/', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify({
                    username,
                    password,
                    email: `${username}@example.com`,
                    role: 'Admin'
                }),
            });
            return {
                ok: res.ok,
                status: res.status,
                body: await res.json()
            };
        }, { username: testAdminUsername, password: testAdminPassword });

        expect(createResponse.ok, `Failed to create test admin: ${JSON.stringify(createResponse)}`).toBeTruthy();
        const userId = createResponse.body.id;

        // Step 3: Reset the test admin's password to trigger must_change_password
        const resetResponse = await page.evaluate(async (userId) => {
            const res = await fetch(`/api/users/${userId}/reset-password/`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
            });
            return {
                ok: res.ok,
                status: res.status,
                body: await res.json()
            };
        }, userId);

        expect(resetResponse.ok, `Failed to reset password: ${JSON.stringify(resetResponse)}`).toBeTruthy();
        const temporaryPassword = resetResponse.body.temporary_password;

        console.log(`✓ Test admin created and password reset. Using temporary password.`);

        // Step 4: Logout current admin
        await logout(page);
        await page.waitForURL(/\/$/, { timeout: 10000 });

        // Step 5: Login as test admin with temporary password
        await loginAsAdminUI(page, testAdminUsername, temporaryPassword);

        // Step 6: Wait for dashboard or modal to appear
        await page.waitForLoadState('networkidle');
        
        // The modal should appear because must_change_password is true
        // The modal has class "modal-overlay" and contains "Changement de mot de passe requis"
        const modalOverlay = page.locator('.modal-overlay');
        await expect(modalOverlay).toBeVisible({ timeout: 10000 });
        
        const modalHeader = page.locator('.modal-header h2');
        await expect(modalHeader).toContainText('Changement de mot de passe requis');

        console.log('✓ Forced password change modal appeared');

        // Take screenshot of modal
        await page.screenshot({ 
            path: 'e2e/screenshots/admin-forced-password-modal.png',
            fullPage: true 
        });

        // Step 7: Fill in new password in the modal
        await page.fill('#new-password', newPassword);
        await page.fill('#confirm-password', newPassword);

        // Step 8: Submit password change
        const submitButton = page.locator('.modal-content button[type="submit"]');
        await expect(submitButton).toBeEnabled();
        await submitButton.click();

        // Step 9: Wait for modal to close and dashboard to load
        await expect(modalOverlay).not.toBeVisible({ timeout: 10000 });

        // Dashboard should now be visible
        await page.waitForURL(/\/admin-dashboard/, { timeout: 10000 });
        await expect(page.getByTestId('admin-dashboard')).toBeVisible({ timeout: 10000 });

        console.log('✓ Password changed successfully, dashboard loaded');

        // Take screenshot after password change
        await page.screenshot({ 
            path: 'e2e/screenshots/admin-after-password-change.png',
            fullPage: true 
        });

        // Cleanup: Delete test admin user
        await page.evaluate(async (userId) => {
            await fetch(`/api/users/${userId}/`, {
                method: 'DELETE',
                credentials: 'include',
            });
        }, userId);

        console.log('✓ Test admin user cleaned up');
    });

});
