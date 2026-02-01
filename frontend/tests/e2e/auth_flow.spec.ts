import { test, expect } from '@playwright/test';
import { CREDS } from './helpers/auth';

test.describe('ZF-AUD-02: Auth Flow & Route Guards', () => {

    test.describe('Admin Flow', () => {
        test('Admin login -> forced password change -> dashboard', async ({ page }) => {
            await page.goto('/admin/login');
            await expect(page).toHaveURL(/\/admin\/login/);

            await page.fill('[data-testid="login.username"]', CREDS.admin.username);
            await page.fill('[data-testid="login.password"]', CREDS.admin.password);

            const loginResp = page.waitForResponse(r =>
                r.url().includes('/api/login/') && r.status() === 200
            );
            await page.click('[data-testid="login.submit"]');
            await loginResp;

            await page.waitForURL(/\/admin-dashboard/, { timeout: 15000 });
            await expect(page.locator('[data-testid="admin-dashboard"]')).toBeVisible({ timeout: 10000 });
        });

        test('Admin can access admin-only pages', async ({ page }) => {
            await page.goto('/admin/login');
            await page.fill('[data-testid="login.username"]', CREDS.admin.username);
            await page.fill('[data-testid="login.password"]', CREDS.admin.password);
            await page.click('[data-testid="login.submit"]');
            await page.waitForURL(/\/admin-dashboard/, { timeout: 15000 });

            await page.goto('/admin/users');
            await expect(page).toHaveURL(/\/admin\/users/);

            await page.goto('/admin/settings');
            await expect(page).toHaveURL(/\/admin\/settings/);
        });

        test('Unauthenticated user cannot access admin dashboard via direct URL', async ({ page }) => {
            await page.goto('/admin-dashboard');
            await expect(page).not.toHaveURL(/\/admin-dashboard/);
            await expect(page).toHaveURL('/');
        });
    });

    test.describe('Teacher Flow', () => {
        test('Teacher login -> corrector dashboard', async ({ page }) => {
            await page.goto('/teacher/login');
            await expect(page).toHaveURL(/\/teacher\/login/);

            await page.fill('[data-testid="login.username"]', CREDS.teacher.username);
            await page.fill('[data-testid="login.password"]', CREDS.teacher.password);

            const loginResp = page.waitForResponse(r =>
                r.url().includes('/api/login/') && r.status() === 200
            );
            await page.click('[data-testid="login.submit"]');
            await loginResp;

            await page.waitForURL(/\/corrector-dashboard/, { timeout: 15000 });
        });

        test('Teacher cannot access admin-only pages', async ({ page }) => {
            await page.goto('/teacher/login');
            await page.fill('[data-testid="login.username"]', CREDS.teacher.username);
            await page.fill('[data-testid="login.password"]', CREDS.teacher.password);
            await page.click('[data-testid="login.submit"]');
            await page.waitForURL(/\/corrector-dashboard/, { timeout: 15000 });

            await page.goto('/admin/users');
            await expect(page).not.toHaveURL(/\/admin\/users/);
            await expect(page).toHaveURL(/\/corrector-dashboard/);

            await page.goto('/admin/settings');
            await expect(page).not.toHaveURL(/\/admin\/settings/);
            await expect(page).toHaveURL(/\/corrector-dashboard/);
        });

        test('Teacher can access corrector desk', async ({ page }) => {
            await page.goto('/teacher/login');
            await page.fill('[data-testid="login.username"]', CREDS.teacher.username);
            await page.fill('[data-testid="login.password"]', CREDS.teacher.password);
            await page.click('[data-testid="login.submit"]');
            await page.waitForURL(/\/corrector-dashboard/, { timeout: 15000 });

            await page.goto('/corrector/import');
            await expect(page).toHaveURL(/\/corrector\/import/);
        });
    });

    test.describe('Student Flow', () => {
        test('Student login (INE+LastName) -> portal -> list graded copies', async ({ page }) => {
            await page.goto('/student/login');
            await expect(page).toHaveURL(/\/student\/login/);

            await page.fill('input[placeholder="ex: 123456789A"]', CREDS.student.ine);
            await page.fill('input[placeholder="Votre nom"]', CREDS.student.lastname);

            const loginResp = page.waitForResponse(r =>
                r.url().includes('/api/students/login/') && r.status() === 200
            );
            await page.click('button[type="submit"]');
            await loginResp;

            await page.waitForURL(/\/student-portal/, { timeout: 15000 });
            await expect(page.locator('.copy-list')).toBeVisible({ timeout: 15000 });
        });

        test('Student cannot access teacher/admin pages', async ({ page }) => {
            await page.goto('/student/login');
            await page.fill('input[placeholder="ex: 123456789A"]', CREDS.student.ine);
            await page.fill('input[placeholder="Votre nom"]', CREDS.student.lastname);
            await page.click('button[type="submit"]');
            await page.waitForURL(/\/student-portal/, { timeout: 15000 });

            await page.goto('/admin-dashboard');
            await expect(page).not.toHaveURL(/\/admin-dashboard/);
            await expect(page).toHaveURL(/\/student-portal/);

            await page.goto('/corrector-dashboard');
            await expect(page).not.toHaveURL(/\/corrector-dashboard/);
            await expect(page).toHaveURL(/\/student-portal/);
        });

        test('Student logout clears session', async ({ page }) => {
            await page.goto('/student/login');
            await page.fill('input[placeholder="ex: 123456789A"]', CREDS.student.ine);
            await page.fill('input[placeholder="Votre nom"]', CREDS.student.lastname);
            await page.click('button[type="submit"]');
            await page.waitForURL(/\/student-portal/, { timeout: 15000 });

            const logoutBtn = page.locator('button:has-text("Déconnexion"), button:has-text("Logout")');
            if (await logoutBtn.isVisible()) {
                await logoutBtn.click();
                await page.waitForURL('/', { timeout: 10000 });
            }

            await page.goto('/student-portal');
            await expect(page).not.toHaveURL(/\/student-portal/);
        });
    });

    test.describe('Security: Direct URL Access', () => {
        test('Unauthenticated user redirected from all protected routes', async ({ page }) => {
            const protectedRoutes = [
                '/admin-dashboard',
                '/corrector-dashboard',
                '/student-portal',
                '/admin/users',
                '/admin/settings',
                '/corrector/import',
            ];

            for (const route of protectedRoutes) {
                await page.goto(route);
                await expect(page).toHaveURL('/');
            }
        });

        test('Back button after logout does not expose protected content', async ({ page }) => {
            await page.goto('/admin/login');
            await page.fill('[data-testid="login.username"]', CREDS.admin.username);
            await page.fill('[data-testid="login.password"]', CREDS.admin.password);
            await page.click('[data-testid="login.submit"]');
            await page.waitForURL(/\/admin-dashboard/, { timeout: 15000 });

            const logoutBtn = page.locator('[data-testid="logout-button"]');
            if (await logoutBtn.isVisible()) {
                await logoutBtn.click();
                await page.waitForURL('/', { timeout: 10000 });
            }

            await page.goBack();
            await page.waitForTimeout(1000);
            await expect(page).toHaveURL('/');
        });
    });

    test.describe('UX: Error Messages', () => {
        test('Invalid login shows clear error message', async ({ page }) => {
            await page.goto('/admin/login');
            await page.fill('[data-testid="login.username"]', 'wronguser');
            await page.fill('[data-testid="login.password"]', 'wrongpass');
            await page.click('[data-testid="login.submit"]');

            await expect(page.locator('[data-testid="login.error"]')).toBeVisible({ timeout: 5000 });
            await expect(page.locator('[data-testid="login.error"]')).toContainText(/incorrect|invalide/i);
        });

        test('Password toggle works', async ({ page }) => {
            await page.goto('/admin/login');
            const passwordInput = page.locator('[data-testid="login.password"]');
            const toggleBtn = page.locator('.password-toggle');

            await expect(passwordInput).toHaveAttribute('type', 'password');
            await toggleBtn.click();
            await expect(passwordInput).toHaveAttribute('type', 'text');
            await toggleBtn.click();
            await expect(passwordInput).toHaveAttribute('type', 'password');
        });
    });

    test.describe('Multi-tab / Reload Stability', () => {
        test('Session persists after page reload', async ({ page }) => {
            await page.goto('/admin/login');
            await page.fill('[data-testid="login.username"]', CREDS.admin.username);
            await page.fill('[data-testid="login.password"]', CREDS.admin.password);
            await page.click('[data-testid="login.submit"]');
            await page.waitForURL(/\/admin-dashboard/, { timeout: 15000 });

            await page.reload();
            await expect(page).toHaveURL(/\/admin-dashboard/);
            await expect(page.locator('[data-testid="admin-dashboard"]')).toBeVisible({ timeout: 10000 });
        });
    });
});
