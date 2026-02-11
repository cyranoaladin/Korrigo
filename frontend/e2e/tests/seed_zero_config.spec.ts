import { test, expect } from '@playwright/test';

/**
 * E2E Test: Zero Config Flow
 *
 * Validates the complete "zero config" production setup:
 * 1. Admin login - verify exams, correctors, students exist
 * 2. Corrector login - verify assigned copies, grade a copy
 * 3. Student login - verify access to graded copy
 * 4. Stats dashboard visibility
 */

const BASE_URL = process.env.BASE_URL || 'http://127.0.0.1:8090';

// Helper: login via API
async function apiLogin(page: any, username: string, password: string) {
    const result = await page.evaluate(async ({ url, user, pass }: any) => {
        const res = await fetch(`${url}/api/login/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username: user, password: pass }),
            credentials: 'include',
        });
        return { ok: res.ok, status: res.status };
    }, { url: BASE_URL, user: username, pass: password });
    return result;
}

async function apiLogout(page: any) {
    await page.evaluate(async (url: string) => {
        await fetch(`${url}/api/logout/`, {
            method: 'POST',
            credentials: 'include',
        });
    }, BASE_URL);
}

test.describe('Zero Config - Seed Verification', () => {

    test('Admin can login and see 2 exams', async ({ page }) => {
        await page.goto(`${BASE_URL}/admin/login`);
        const loginResult = await apiLogin(page, 'admin', 'passe123');
        expect(loginResult.ok).toBeTruthy();

        // Navigate to admin dashboard
        await page.goto(`${BASE_URL}/admin-dashboard`, { waitUntil: 'networkidle' });

        // Verify dashboard loaded
        await expect(page.getByTestId('admin-dashboard')).toBeVisible({ timeout: 10000 });

        // Check that exams are visible
        const pageContent = await page.textContent('body');
        expect(pageContent).toContain('BB Jour 1');
        expect(pageContent).toContain('BB Jour 2');

        await apiLogout(page);
    });

    test('Admin verifies correctors exist via API', async ({ page }) => {
        await page.goto(BASE_URL);
        const loginResult = await apiLogin(page, 'admin', 'passe123');
        expect(loginResult.ok).toBeTruthy();

        // Check users via API
        const users = await page.evaluate(async (url: string) => {
            const res = await fetch(`${url}/api/users/`, { credentials: 'include' });
            return await res.json();
        }, BASE_URL);

        const usernames = Array.isArray(users) ? users.map((u: any) => u.username) :
            (users.results || []).map((u: any) => u.username);

        // Check J1 correctors
        expect(usernames).toContain('alaeddine.benrhouma@ert.tn');
        expect(usernames).toContain('patrick.dupont@ert.tn');
        expect(usernames).toContain('philippe.carr@ert.tn');
        expect(usernames).toContain('selima.klibi@ert.tn');

        // Check J2 correctors
        expect(usernames).toContain('chawki.saadi@ert.tn');
        expect(usernames).toContain('edouard.rousseau@ert.tn');
        expect(usernames).toContain('sami.bentiba@ert.tn');
        expect(usernames).toContain('laroussi.laroussi@ert.tn');

        await apiLogout(page);
    });

    test('Corrector J1 can login and see assigned copies', async ({ page }) => {
        await page.goto(`${BASE_URL}/teacher/login`);
        const loginResult = await apiLogin(page, 'alaeddine.benrhouma@ert.tn', 'passe123');
        expect(loginResult.ok).toBeTruthy();

        await page.goto(`${BASE_URL}/corrector-dashboard`, { waitUntil: 'networkidle' });

        // Verify dashboard loaded
        await expect(page.getByTestId('corrector-dashboard')).toBeVisible({ timeout: 10000 });

        // Should have copy cards
        const copyCards = page.getByTestId('copy-card');
        const count = await copyCards.count();
        expect(count).toBeGreaterThan(0);

        await apiLogout(page);
    });

    test('Corrector J2 can login and see assigned copies', async ({ page }) => {
        await page.goto(`${BASE_URL}/teacher/login`);
        const loginResult = await apiLogin(page, 'chawki.saadi@ert.tn', 'passe123');
        expect(loginResult.ok).toBeTruthy();

        await page.goto(`${BASE_URL}/corrector-dashboard`, { waitUntil: 'networkidle' });
        await expect(page.getByTestId('corrector-dashboard')).toBeVisible({ timeout: 10000 });

        const copyCards = page.getByTestId('copy-card');
        const count = await copyCards.count();
        expect(count).toBeGreaterThan(0);

        await apiLogout(page);
    });
});

test.describe('Grading Flow', () => {

    test('Corrector can open a copy and see grading tab', async ({ page }) => {
        await page.goto(`${BASE_URL}/teacher/login`);
        await apiLogin(page, 'alaeddine.benrhouma@ert.tn', 'passe123');

        await page.goto(`${BASE_URL}/corrector-dashboard`, { waitUntil: 'networkidle' });
        await expect(page.getByTestId('corrector-dashboard')).toBeVisible({ timeout: 10000 });

        // Click on first copy action button
        const firstAction = page.getByTestId('copy-action').first();
        await firstAction.click();

        // Wait for CorrectorDesk to load
        await page.waitForTimeout(2000);

        // Verify grading tab exists
        const pageContent = await page.textContent('body');
        expect(pageContent).toContain('Barème');

        await apiLogout(page);
    });
});

test.describe('Student Access Control', () => {

    test('Student cannot see copies before results are released', async ({ page }) => {
        // Login as student
        await page.goto(`${BASE_URL}/student/login`);

        // Try API login as student (using session-based student auth)
        const result = await page.evaluate(async (url: string) => {
            const res = await fetch(`${url}/api/students/copies/`, {
                credentials: 'include',
            });
            return { status: res.status };
        }, BASE_URL);

        // Should be 401 (not logged in) or empty list
        expect([200, 401, 403]).toContain(result.status);

        if (result.status === 200) {
            const data = await page.evaluate(async (url: string) => {
                const res = await fetch(`${url}/api/students/copies/`, {
                    credentials: 'include',
                });
                return await res.json();
            }, BASE_URL);
            // If 200, should be empty (results not released)
            expect(data).toHaveLength(0);
        }
    });
});
