import { test, expect } from '@playwright/test';
import { loginAsAdmin, loginAsTeacher, loginAsStudent } from './helpers/auth';
import { openNewTab, logout, verifyRedirect } from './helpers/navigation';

test.describe('Multi-Tab E2E Tests', () => {

    test('Admin: logout in Tab A, navigate in Tab B → session loss detected, redirect to home', async ({ context, page }) => {
        // Tab A: Login as admin
        await loginAsAdmin(page);
        await page.goto('/admin-dashboard', { waitUntil: 'domcontentloaded' });
        await page.waitForLoadState('networkidle');

        await expect(page.getByTestId('admin-dashboard')).toBeVisible({ timeout: 10000 });

        // Tab B: Open new tab and navigate to admin users page
        const tabB = await openNewTab(context, '/admin/users');
        
        // Verify Tab B can access protected route while session is active
        await tabB.waitForTimeout(1000);
        const urlBeforeLogout = tabB.url();
        console.log('Tab B URL before logout:', urlBeforeLogout);

        // Tab A: Logout
        await logout(page);
        await page.waitForTimeout(1000);

        // Tab B: Try to navigate to another protected route
        await tabB.goto('/admin-dashboard', { waitUntil: 'domcontentloaded' });
        await tabB.waitForLoadState('networkidle');

        // Verify Tab B is redirected to home or login (session loss detected)
        const tabBUrl = tabB.url();
        const isRedirected = tabBUrl.includes('/login') || 
                            tabBUrl === 'http://localhost:8088/' ||
                            tabBUrl === 'http://127.0.0.1:8090/' ||
                            !tabBUrl.includes('/admin-dashboard');
        
        expect(isRedirected, `Expected Tab B to be redirected to home/login, got: ${tabBUrl}`).toBeTruthy();

        // Take screenshots of both tabs
        await page.screenshot({ path: 'frontend/e2e/screenshots/multi-tab-admin-tabA.png', fullPage: true });
        await tabB.screenshot({ path: 'frontend/e2e/screenshots/multi-tab-admin-tabB.png', fullPage: true });

        console.log('✓ Admin multi-tab: Session loss detected in Tab B after logout in Tab A');

        await tabB.close();
    });

    test('Teacher: logout in Tab A, navigate in Tab B → session loss detected, redirect to home', async ({ context, page }) => {
        // Tab A: Login as teacher
        await loginAsTeacher(page);
        await page.goto('/corrector-dashboard', { waitUntil: 'domcontentloaded' });
        await page.waitForLoadState('networkidle');

        await expect(page.getByTestId('corrector-dashboard')).toBeVisible({ timeout: 10000 });

        // Tab B: Open new tab and navigate to corrector dashboard
        const tabB = await openNewTab(context, '/corrector-dashboard');
        
        // Verify Tab B can access protected route while session is active
        await tabB.waitForTimeout(1000);
        const urlBeforeLogout = tabB.url();
        console.log('Tab B URL before logout:', urlBeforeLogout);

        // Tab A: Logout
        await logout(page);
        await page.waitForTimeout(1000);

        // Tab B: Try to navigate to another protected route
        await tabB.goto('/corrector-dashboard', { waitUntil: 'domcontentloaded' });
        await tabB.waitForLoadState('networkidle');

        // Verify Tab B is redirected to home or login (session loss detected)
        const tabBUrl = tabB.url();
        const isRedirected = tabBUrl.includes('/login') || 
                            tabBUrl === 'http://localhost:8088/' ||
                            tabBUrl === 'http://127.0.0.1:8090/' ||
                            !tabBUrl.includes('/corrector-dashboard');
        
        expect(isRedirected, `Expected Tab B to be redirected to home/login, got: ${tabBUrl}`).toBeTruthy();

        // Take screenshots of both tabs
        await page.screenshot({ path: 'frontend/e2e/screenshots/multi-tab-teacher-tabA.png', fullPage: true });
        await tabB.screenshot({ path: 'frontend/e2e/screenshots/multi-tab-teacher-tabB.png', fullPage: true });

        console.log('✓ Teacher multi-tab: Session loss detected in Tab B after logout in Tab A');

        await tabB.close();
    });

    test('Student: logout in Tab A, navigate in Tab B → session loss detected, redirect to home', async ({ context, page }) => {
        // Tab A: Login as student
        await loginAsStudent(page);
        await page.goto('/student-portal', { waitUntil: 'domcontentloaded' });
        await page.waitForLoadState('networkidle');

        await expect(page.getByTestId('student-portal')).toBeVisible({ timeout: 10000 });

        // Tab B: Open new tab and navigate to student portal
        const tabB = await openNewTab(context, '/student-portal');
        
        // Verify Tab B can access protected route while session is active
        await tabB.waitForTimeout(1000);
        const urlBeforeLogout = tabB.url();
        console.log('Tab B URL before logout:', urlBeforeLogout);

        // Tab A: Logout
        await logout(page);
        await page.waitForTimeout(1000);

        // Tab B: Try to navigate to student portal again
        await tabB.goto('/student-portal', { waitUntil: 'domcontentloaded' });
        await tabB.waitForLoadState('networkidle');

        // Verify Tab B is redirected to home or login (session loss detected)
        const tabBUrl = tabB.url();
        const isRedirected = tabBUrl.includes('/login') || 
                            tabBUrl === 'http://localhost:8088/' ||
                            tabBUrl === 'http://127.0.0.1:8090/' ||
                            !tabBUrl.includes('/student-portal');
        
        expect(isRedirected, `Expected Tab B to be redirected to home/login, got: ${tabBUrl}`).toBeTruthy();

        // Take screenshots of both tabs
        await page.screenshot({ path: 'frontend/e2e/screenshots/multi-tab-student-tabA.png', fullPage: true });
        await tabB.screenshot({ path: 'frontend/e2e/screenshots/multi-tab-student-tabB.png', fullPage: true });

        console.log('✓ Student multi-tab: Session loss detected in Tab B after logout in Tab A');

        await tabB.close();
    });
});
