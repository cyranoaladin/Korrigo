import { expect, Page } from '@playwright/test';

/**
 * Login as admin user via direct API calls and hydrate the auth store
 * 
 * The auth store (Pinia) keeps user in memory (ref), not localStorage.
 * After API login, we must call fetchUser() to hydrate the store,
 * otherwise the router guard will see user=null and redirect to /login.
 */
export async function loginAsAdmin(page: Page) {
    // 1) Navigate to login page to establish origin and cookie jar
    await page.goto('/login', { waitUntil: 'domcontentloaded' });

    // 2) Perform login via API (same format as frontend auth.js)
    const username = process.env.E2E_ADMIN_USERNAME || 'admin';
    const password = process.env.E2E_ADMIN_PASSWORD || 'admin';

    const loginResult = await page.evaluate(async ({ username, password }) => {
        try {
            const res = await fetch('/api/login/', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify({ username, password }),
            });
            return {
                ok: res.ok,
                status: res.status,
                body: await res.text()
            };
        } catch (e) {
            return {
                ok: false,
                status: 0,
                body: (e as Error).toString()
            };
        }
    }, { username, password });

    expect(loginResult.ok, `Login API failed: HTTP ${loginResult.status}\nBody: ${loginResult.body}`).toBeTruthy();

    // 3) Navigate to a protected route to trigger the router guard's hydration
    // Since cookies are now set, the app's router guard will call fetchUser() 
    // when it sees a protected route is requested with user=null.
    await page.goto('/admin-dashboard', { waitUntil: 'networkidle' });

    // Verify hydration by waiting for a UI element that requires a logged-in user
    // e.g. the admin dashboard main element
    await expect(page.getByTestId('admin-dashboard')).toBeVisible({ timeout: 10000 });

    console.log('✓ Login successful and hydrated via real app flow');
}

/**
 * Login as teacher user via direct API calls and hydrate the auth store
 */
export async function loginAsTeacher(page: Page) {
    // 1) Navigate to login page to establish origin and cookie jar
    await page.goto('/login', { waitUntil: 'domcontentloaded' });

    // 2) Perform login via API
    const username = process.env.E2E_TEACHER_USERNAME || 'prof1';
    const password = process.env.E2E_TEACHER_PASSWORD || 'password';

    const loginResult = await page.evaluate(async ({ username, password }) => {
        try {
            const res = await fetch('/api/login/', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify({ username, password }),
            });
            return {
                ok: res.ok,
                status: res.status,
                body: await res.text()
            };
        } catch (e) {
            return {
                ok: false,
                status: 0,
                body: (e as Error).toString()
            };
        }
    }, { username, password });

    expect(loginResult.ok, `Login API failed: HTTP ${loginResult.status}\nBody: ${loginResult.body}`).toBeTruthy();

    // 3) Navigate to corrector dashboard to trigger hydration
    await page.goto('/corrector-dashboard', { waitUntil: 'networkidle' });

    // Verify hydration by waiting for a UI element that requires a logged-in user
    await expect(page.getByTestId('corrector-dashboard')).toBeVisible({ timeout: 10000 });

    console.log('✓ Teacher login successful and hydrated via real app flow');
}

/**
 * Login as student user via direct API calls and hydrate the auth store
 */
export async function loginAsStudent(page: Page, ine?: string, lastName?: string) {
    // 1) Navigate to student login page to establish origin and cookie jar
    await page.goto('/login-student', { waitUntil: 'domcontentloaded' });

    // 2) Perform login via API
    const studentIne = ine || process.env.E2E_STUDENT_INE || '123456789';
    const studentLastName = lastName || process.env.E2E_STUDENT_LASTNAME || 'E2E_STUDENT';

    const loginResult = await page.evaluate(async ({ ine, lastName }) => {
        try {
            const res = await fetch('/api/students/login/', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify({ ine, last_name: lastName }),
            });
            return {
                ok: res.ok,
                status: res.status,
                body: await res.text()
            };
        } catch (e) {
            return {
                ok: false,
                status: 0,
                body: (e as Error).toString()
            };
        }
    }, { ine: studentIne, lastName: studentLastName });

    expect(loginResult.ok, `Student login API failed: HTTP ${loginResult.status}\nBody: ${loginResult.body}`).toBeTruthy();

    // 3) Navigate to student portal to trigger hydration
    await page.goto('/student-portal', { waitUntil: 'networkidle' });

    // Verify hydration by waiting for a UI element that requires a logged-in student
    await expect(page.getByTestId('student-portal')).toBeVisible({ timeout: 10000 });

    console.log('✓ Student login successful and hydrated via real app flow');
}
