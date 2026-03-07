import { test, expect, Page, BrowserContext } from '@playwright/test';
import { CREDS } from './helpers/auth';

/**
 * Helper: Login as student via the UI login form.
 * Returns the login API response.
 */
async function studentLogin(page: Page, email: string, password: string) {
    await page.goto('/student/login');
    await expect(page).toHaveURL(/student\/login/, { timeout: 15000 });

    await page.fill('input[type="email"]', email);
    await page.fill('input[type="password"]', password);

    const loginRespPromise = page.waitForResponse(resp =>
        resp.url().includes('/api/students/login/')
    );

    await page.click('button[type="submit"]');
    return await loginRespPromise;
}

/**
 * Helper: Extract CSRF token from browser cookies.
 */
async function getCsrfToken(page: Page): Promise<string> {
    const cookies = await page.context().cookies();
    const csrf = cookies.find(c => c.name === 'csrftoken');
    return csrf?.value || '';
}


// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// RATE LIMIT: Login endpoint has 5/15min limit per IP.
// This suite uses exactly 5 login POSTs across all tests.
//
// POST budget:
//   Test 1 (comprehensive):  error POSTs (2) + login (1) + student B login (1) = 4
//   Test 2 (wrong password): 1 POST via UI
//   Total: 5 POSTs ← exactly at the limit
//
// The destructive password-change test (Block 2) must be run SEPARATELY
// with a fresh rate-limit window. Run via:
//   npx playwright test --grep "Password Change"
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

test.describe('Student Auth E2E', () => {

    test('Comprehensive: errors + login + session + modal + copies + isolation + logout', async ({ browser, baseURL }) => {
        // ── Part A: Error cases via direct API (2 POSTs) ──
        const errCtx = await browser.newContext({ baseURL });
        const errPage = await errCtx.newPage();
        // Navigate once to establish cookie context
        await errPage.goto('/student/login');

        // A1: Missing password → 400
        const missingPwdResp = await errPage.request.post('/api/students/login/', {
            data: { email: CREDS.student.email },
            headers: { 'Content-Type': 'application/json' },
        });
        expect(missingPwdResp.status()).toBe(400);
        expect((await missingPwdResp.json()).error).toContain('requis');

        // A2: Unknown email → 401 (same message as wrong pwd = no enumeration)
        const unknownResp = await errPage.request.post('/api/students/login/', {
            data: { email: 'nonexistent@ert.tn', password: 'anypassword' },
            headers: { 'Content-Type': 'application/json' },
        });
        expect(unknownResp.status()).toBe(401);
        expect((await unknownResp.json()).error).toBe('Email ou mot de passe incorrect.');

        // A3: Unauthenticated GET → 403
        const meUnauth = await errPage.request.get('/api/students/me/');
        expect(meUnauth.status()).toBe(403);
        const copiesUnauth = await errPage.request.get('/api/students/copies/');
        expect(copiesUnauth.status()).toBe(403);

        await errCtx.close();

        // ── Part B: Student A — login + session + modal + copies + logout (1 POST) ──
        const ctxA = await browser.newContext();
        const pageA = await ctxA.newPage();

        const loginResp = await studentLogin(pageA, CREDS.student.email, CREDS.student.password);
        expect(loginResp.status()).toBe(200);

        const loginBody = await loginResp.json();
        expect(loginBody.message).toBe('Connexion réussie.');
        expect(loginBody.role).toBe('Student');
        expect(loginBody.must_change_password).toBe(true);
        expect(loginBody.student.email).toBe(CREDS.student.email);
        expect(loginBody.student.first_name).toBe(CREDS.student.first_name);

        // B1: Redirect to portal
        await pageA.waitForURL(/student-portal/, { timeout: 15000 });

        // B2: /students/me/ returns full student data
        const meResp = await pageA.request.get('/api/students/me/');
        expect(meResp.status()).toBe(200);
        const meBody = await meResp.json();
        expect(meBody.email).toBe(CREDS.student.email);
        expect(meBody.first_name).toBe(CREDS.student.first_name);
        expect(meBody.last_name).toBe(CREDS.student.last_name);
        expect(meBody).toHaveProperty('date_naissance');
        expect(meBody).toHaveProperty('class_name');
        expect(meBody.must_change_password).toBe(true);

        // B3: Forced password change modal visible
        const modal = pageA.locator('.modal-overlay');
        await expect(modal).toBeVisible({ timeout: 10000 });
        await expect(pageA.locator('text=date de naissance')).toBeVisible();
        await expect(pageA.locator('text=Changement de mot de passe requis')).toBeVisible();
        await expect(pageA.locator('.close-btn')).not.toBeVisible();

        // B4: Weak password → submit disabled
        await pageA.fill('#current-password', CREDS.student.password);
        await pageA.fill('#new-password', 'short');
        await pageA.fill('#confirm-password', 'short');
        await expect(pageA.locator('.modal-overlay button[type="submit"]')).toBeDisabled();

        // B5: Mismatched confirmation → error hint
        await pageA.fill('#new-password', 'MonNouveauMdpE2E2026!');
        await pageA.fill('#confirm-password', 'DifferentPassword2026!');
        await expect(pageA.locator('.error-hint')).toBeVisible();
        await expect(pageA.locator('.modal-overlay button[type="submit"]')).toBeDisabled();

        // B6: /students/copies/ returns array
        const copiesResp = await pageA.request.get('/api/students/copies/');
        expect(copiesResp.status()).toBe(200);
        const copies = await copiesResp.json();
        expect(Array.isArray(copies)).toBe(true);

        // ── Part C: Student B — cross-student isolation (1 POST) ──
        const ctxB = await browser.newContext();
        const pageB = await ctxB.newPage();
        const respB = await studentLogin(pageB, CREDS.other_student.email, CREDS.other_student.password);
        expect(respB.status()).toBe(200);
        await pageB.waitForURL(/student-portal/, { timeout: 15000 });

        const copiesBResp = await pageB.request.get('/api/students/copies/');
        const copiesB = await copiesBResp.json();

        if (copiesB.length > 0) {
            const copyBId = copiesB[0].id;
            // Student A tries to access B's PDF → 403
            const forbiddenResp = await pageA.request.get(
                `/api/grading/copies/${copyBId}/final-pdf/`,
                { headers: { 'Accept': 'application/pdf' } }
            );
            expect(forbiddenResp.status()).toBe(403);
        }

        await ctxB.close();

        // ── Part D: Logout clears session ──
        const csrfToken = await getCsrfToken(pageA);
        const logoutResp = await pageA.request.post('/api/students/logout/', {
            headers: {
                'X-CSRFToken': csrfToken,
                'Referer': `${baseURL}/`,
            },
        });
        expect(logoutResp.status()).toBe(200);

        const meAfter = await pageA.request.get('/api/students/me/');
        expect(meAfter.status()).toBe(403);

        await ctxA.close();
    });

    test('Wrong password returns 401, error shown in UI', async ({ page }) => {
        const resp = await studentLogin(page, CREDS.student.email, 'wrongpassword');

        expect(resp.status()).toBe(401);
        const body = await resp.json();
        expect(body.error).toBe('Email ou mot de passe incorrect.');

        await expect(page).toHaveURL(/student\/login/);
        await expect(page.locator('.error-msg')).toBeVisible({ timeout: 5000 });
    });
});

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// DESTRUCTIVE: Password change flow (3 login POSTs).
// Run SEPARATELY with fresh rate-limit window:
//   npx playwright test --grep "Password Change"
// After running, reset passwords:
//   docker exec docker-backend-1 python manage.py reset_student_passwords
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
test.describe('Student Auth — Password Change Flow', () => {

    test('Full cycle: DOB login → change password → re-login → old rejected', async ({ page }) => {
        const NEW_PASSWORD = 'MonNouveauMdpE2E2026!';

        // Step 1: Login with DOB (POST #1)
        const loginResp = await studentLogin(page, CREDS.student.email, CREDS.student.password);
        expect(loginResp.status()).toBe(200);
        await page.waitForURL(/student-portal/, { timeout: 15000 });

        // Step 2: Forced modal
        const modal = page.locator('.modal-overlay');
        await expect(modal).toBeVisible({ timeout: 10000 });

        // Step 3: Fill and submit
        await page.fill('#current-password', CREDS.student.password);
        await page.fill('#new-password', NEW_PASSWORD);
        await page.fill('#confirm-password', NEW_PASSWORD);

        const changePwdResp = page.waitForResponse(resp =>
            resp.url().includes('/api/students/change-password/')
        );
        await page.click('.modal-overlay button[type="submit"]');
        const pwdResp = await changePwdResp;
        expect(pwdResp.status()).toBe(200);

        // Step 4: Modal closes
        await expect(modal).not.toBeVisible({ timeout: 5000 });

        // Step 5: Logout
        const csrf1 = await getCsrfToken(page);
        await page.request.post('/api/students/logout/', {
            headers: {
                'X-CSRFToken': csrf1,
                'Referer': `${page.url()}/`,
            },
        });

        // Step 6: Re-login with NEW password (POST #2)
        const reloginResp = await studentLogin(page, CREDS.student.email, NEW_PASSWORD);
        expect(reloginResp.status()).toBe(200);
        const reloginBody = await reloginResp.json();
        expect(reloginBody.must_change_password).toBe(false);

        // Step 7: /me/ confirms must_change_password=false
        await page.waitForURL(/student-portal/, { timeout: 15000 });
        const meResp = await page.request.get('/api/students/me/');
        expect(meResp.status()).toBe(200);
        expect((await meResp.json()).must_change_password).toBe(false);

        // Step 8: Old DOB password rejected (POST #3)
        const csrf2 = await getCsrfToken(page);
        await page.request.post('/api/students/logout/', {
            headers: {
                'X-CSRFToken': csrf2,
                'Referer': `${page.url()}/`,
            },
        });
        const oldPwdResp = await studentLogin(page, CREDS.student.email, CREDS.student.password);
        expect(oldPwdResp.status()).toBe(401);
    });
});
