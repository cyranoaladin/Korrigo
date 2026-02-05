import { test, expect } from '@playwright/test';
import { loginAsAdmin, loginAsTeacher, loginAsStudent } from './helpers/auth';
import { logout } from './helpers/navigation';

test.describe('Back Button E2E Tests', () => {

    test('Admin: logout → back button → redirected to home (not cached dashboard)', async ({ page }) => {
        // Login as admin
        await loginAsAdmin(page);
        await page.goto('/admin-dashboard', { waitUntil: 'domcontentloaded' });
        await page.waitForLoadState('networkidle');

        await expect(page.getByTestId('admin-dashboard')).toBeVisible({ timeout: 10000 });

        // Navigate to another admin page to build history
        await page.goto('/admin/users', { waitUntil: 'domcontentloaded' });
        await page.waitForLoadState('networkidle');
        await page.waitForTimeout(500);

        // Logout
        await logout(page);

        // Wait for redirect after logout
        await page.waitForTimeout(1000);
        const urlAfterLogout = page.url();
        console.log('URL after logout:', urlAfterLogout);

        // Press back button
        await page.goBack();
        await page.waitForTimeout(1000);
        await page.waitForLoadState('networkidle');

        // Verify we're redirected to home/login, not back to protected page
        const currentUrl = page.url();
        const isProtected = !currentUrl.includes('/admin/users') &&
                           !currentUrl.includes('/admin-dashboard') &&
                           (currentUrl.includes('/login') || 
                            currentUrl === 'http://localhost:8088/' ||
                            currentUrl === 'http://127.0.0.1:8090/');
        
        expect(isProtected, `Expected redirect to home/login after back button, got: ${currentUrl}`).toBeTruthy();

        await page.screenshot({ path: 'frontend/e2e/screenshots/back-button-admin.png', fullPage: true });

        console.log('✓ Admin back button: Redirected to home, not cached protected page');
    });

    test('Teacher: logout → back button → redirected to home (not cached dashboard)', async ({ page }) => {
        // Login as teacher
        await loginAsTeacher(page);
        await page.goto('/corrector-dashboard', { waitUntil: 'domcontentloaded' });
        await page.waitForLoadState('networkidle');

        await expect(page.getByTestId('corrector-dashboard')).toBeVisible({ timeout: 10000 });

        // Stay on dashboard or navigate to build history
        await page.waitForTimeout(500);

        // Logout
        await logout(page);

        // Wait for redirect after logout
        await page.waitForTimeout(1000);
        const urlAfterLogout = page.url();
        console.log('URL after logout:', urlAfterLogout);

        // Press back button
        await page.goBack();
        await page.waitForTimeout(1000);
        await page.waitForLoadState('networkidle');

        // Verify we're redirected to home/login, not back to protected page
        const currentUrl = page.url();
        const isProtected = !currentUrl.includes('/corrector-dashboard') &&
                           (currentUrl.includes('/login') || 
                            currentUrl === 'http://localhost:8088/' ||
                            currentUrl === 'http://127.0.0.1:8090/');
        
        expect(isProtected, `Expected redirect to home/login after back button, got: ${currentUrl}`).toBeTruthy();

        await page.screenshot({ path: 'frontend/e2e/screenshots/back-button-teacher.png', fullPage: true });

        console.log('✓ Teacher back button: Redirected to home, not cached protected page');
    });

    test('Student: logout → back button → redirected to home (not cached portal)', async ({ page }) => {
        // Login as student
        await loginAsStudent(page);
        await page.goto('/student-portal', { waitUntil: 'domcontentloaded' });
        await page.waitForLoadState('networkidle');

        await expect(page.getByTestId('student-portal')).toBeVisible({ timeout: 10000 });

        // Stay on portal to build history
        await page.waitForTimeout(500);

        // Logout
        await logout(page);

        // Wait for redirect after logout
        await page.waitForTimeout(1000);
        const urlAfterLogout = page.url();
        console.log('URL after logout:', urlAfterLogout);

        // Press back button
        await page.goBack();
        await page.waitForTimeout(1000);
        await page.waitForLoadState('networkidle');

        // Verify we're redirected to home/login, not back to protected page
        const currentUrl = page.url();
        const isProtected = !currentUrl.includes('/student-portal') &&
                           (currentUrl.includes('/login') || 
                            currentUrl === 'http://localhost:8088/' ||
                            currentUrl === 'http://127.0.0.1:8090/');
        
        expect(isProtected, `Expected redirect to home/login after back button, got: ${currentUrl}`).toBeTruthy();

        await page.screenshot({ path: 'frontend/e2e/screenshots/back-button-student.png', fullPage: true });

        console.log('✓ Student back button: Redirected to home, not cached protected page');
    });

    test('Admin: back button from different admin pages after logout', async ({ page }) => {
        // Login as admin
        await loginAsAdmin(page);
        
        // Navigate through multiple admin pages
        await page.goto('/admin-dashboard', { waitUntil: 'domcontentloaded' });
        await page.waitForLoadState('networkidle');
        await page.waitForTimeout(500);

        await page.goto('/admin/users', { waitUntil: 'domcontentloaded' });
        await page.waitForLoadState('networkidle');
        await page.waitForTimeout(500);

        // Logout
        await logout(page);
        await page.waitForTimeout(1000);

        // Try to go back multiple times
        await page.goBack();
        await page.waitForTimeout(1000);
        await page.waitForLoadState('networkidle');

        let currentUrl = page.url();
        const firstBackIsProtected = !currentUrl.includes('/admin/users') &&
                                     !currentUrl.includes('/admin-dashboard');
        
        expect(firstBackIsProtected, `First back should not access protected page, got: ${currentUrl}`).toBeTruthy();

        // Try back button again
        await page.goBack();
        await page.waitForTimeout(1000);
        await page.waitForLoadState('networkidle');

        currentUrl = page.url();
        const secondBackIsProtected = !currentUrl.includes('/admin-dashboard') &&
                                      !currentUrl.includes('/admin/users');
        
        expect(secondBackIsProtected, `Second back should not access protected page, got: ${currentUrl}`).toBeTruthy();

        console.log('✓ Admin multiple back buttons: All protected pages blocked after logout');
    });
});
