import { expect, Page } from '@playwright/test';

/**
 * Login as admin user via the real SPA login form.
 * 
 * Uses /admin/login which renders the Login.vue component with roleContext=Admin.
 * Fills username + password, clicks submit, and waits for redirect to /admin-dashboard.
 * This ensures cookies (sessionid, csrftoken) are properly set via the real app flow.
 */
export async function loginAsAdmin(page: Page) {
    const username = process.env.E2E_ADMIN_USERNAME || 'admin';
    const password = process.env.E2E_ADMIN_PASSWORD || 'admin';

    // 1) Navigate to the admin login page (NOT /login which redirects to /)
    await page.goto('/admin/login', { waitUntil: 'networkidle' });

    // 2) Fill the login form using data-testid attributes
    await page.getByTestId('login.username').fill(username);
    await page.getByTestId('login.password').fill(password);

    // 3) Click submit and wait for navigation to admin-dashboard
    await page.getByTestId('login.submit').click();

    // 4) Wait for the admin dashboard to appear (login → fetchUser → redirect)
    await expect(page.getByTestId('admin-dashboard')).toBeVisible({ timeout: 15000 });

    console.log('✓ Login successful via real form flow');
}
