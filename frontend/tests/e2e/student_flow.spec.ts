import { test, expect } from '@playwright/test';

test.describe('Student Flow (Mission 17)', () => {
    test('Full Student Cycle: Login -> List -> PDF accessible', async ({ page }) => {
        page.on('console', msg => console.log('[browser]', msg.type(), msg.text()));
        page.on('pageerror', err => console.log('[pageerror]', err.message));

        page.on('response', async (resp) => {
            const url = resp.url();
            if (url.includes('/api/copies/')) {
                console.log(`[pdf-req] ${resp.status()} ${url}`);
            }

            if (url.includes('/api/students/login/') && resp.status() !== 200) {
                console.log(`[login-api] ${resp.status()} ${resp.statusText()} ${url}`);
                try {
                    const txt = await resp.text();
                    console.log('[login-api-body]', txt.slice(0, 800));
                } catch { }
            }
        });

        // 1) LOGIN
        await page.goto('/student/login');
        await expect(page).toHaveURL(/\/student\/login/);

        await page.fill('input[placeholder="ex: 123456789A"]', '123456789');
        await page.fill('input[placeholder="Votre nom"]', 'E2E_STUDENT');

        // Wait for login API 200 (more robust than URL-only)
        const loginRespPromise = page.waitForResponse(resp =>
            resp.url().includes('/api/students/login/') && resp.status() === 200
        );

        await page.click('button[type="submit"]');
        await loginRespPromise;

        // 2) REDIRECT TO PORTAL
        await page.waitForURL(/\/student-portal/, { timeout: 15000 });

        // 3) LIST
        await expect(page.locator('.copy-list')).toBeVisible({ timeout: 15000 });

        const examItem = page.locator('.copy-list li', { hasText: 'Gate 4 Exam' });
        await expect(examItem.locator('.exam-name')).toBeVisible();

        await examItem.click();

        // 4) PDF LINK
        const pdfLink = page.locator('a.btn-download');
        await expect(pdfLink).toBeVisible();

        const href = await pdfLink.getAttribute('href');
        expect(href).toBeTruthy();
        expect(href || '').toContain('/api/copies/');
        expect(href || '').toContain('/final-pdf/');

        // 5) Verify PDF is accessible (robust: avoid race with iframe auto-load)
        // Use page.request to reuse the browser session cookies (student session).
        const pdfResp = await page.request.get(href!, {
            headers: { 'Accept': 'application/pdf' }
        });
        expect(pdfResp.status()).toBe(200);
        const ct = (pdfResp.headers()['content-type'] || '').toLowerCase();
        expect(ct).toContain('application/pdf');
    });

    test('Security: Student cannot access another student\'s PDF (403)', async ({ page }) => {
        // STEP 1: Login as the test student and get their copy ID
        await page.goto('/student/login');
        await page.fill('input[placeholder="ex: 123456789A"]', '123456789');
        await page.fill('input[placeholder="Votre nom"]', 'E2E_STUDENT');

        let loginRespPromise = page.waitForResponse(resp =>
            resp.url().includes('/api/students/login/') && resp.status() === 200
        );
        await page.click('button[type="submit"]');
        await loginRespPromise;
        await page.waitForURL(/\/student-portal/, { timeout: 15000 });

        const copiesResp = await page.request.get('/api/students/copies/');
        expect(copiesResp.status()).toBe(200);
        const copies = await copiesResp.json();
        expect(copies.length).toBe(1);

        // STEP 2: Logout and login as the OTHER student to get their copy UUID
        await page.goto('/student/login');
        await page.fill('input[placeholder="ex: 123456789A"]', '987654321');
        await page.fill('input[placeholder="Votre nom"]', 'OTHER');

        loginRespPromise = page.waitForResponse(resp =>
            resp.url().includes('/api/students/login/') && resp.status() === 200
        );
        await page.click('button[type="submit"]');
        await loginRespPromise;
        await page.waitForURL(/\/student-portal/, { timeout: 15000 });

        const otherCopiesResp = await page.request.get('/api/students/copies/');
        expect(otherCopiesResp.status()).toBe(200);
        const otherCopies = await otherCopiesResp.json();
        expect(otherCopies.length).toBeGreaterThan(0);
        const otherCopyId = otherCopies[0].id;

        // STEP 3: Logout and login back as the first student
        await page.goto('/student/login');
        await page.fill('input[placeholder="ex: 123456789A"]', '123456789');
        await page.fill('input[placeholder="Votre nom"]', 'E2E_STUDENT');

        loginRespPromise = page.waitForResponse(resp =>
            resp.url().includes('/api/students/login/') && resp.status() === 200
        );
        await page.click('button[type="submit"]');
        await loginRespPromise;
        await page.waitForURL(/\/student-portal/, { timeout: 15000 });

        // STEP 4: Attempt to access the OTHER student's PDF using actual UUID
        const forbiddenResp = await page.request.get(`/api/copies/${otherCopyId}/final-pdf/`, {
            headers: { 'Accept': 'application/pdf' }
        });

        // MUST return 403 (resource exists but access denied)
        expect(forbiddenResp.status()).toBe(403);
    });

    test('Security: LOCKED copies are not visible in student list', async ({ page }) => {
        // Login as the test student
        await page.goto('/student/login');
        await page.fill('input[placeholder="ex: 123456789A"]', '123456789');
        await page.fill('input[placeholder="Votre nom"]', 'E2E_STUDENT');

        const loginRespPromise = page.waitForResponse(resp =>
            resp.url().includes('/api/students/login/') && resp.status() === 200
        );
        await page.click('button[type="submit"]');
        await loginRespPromise;

        await page.waitForURL(/\/student-portal/, { timeout: 15000 });

        // Verify the copy list is visible
        await expect(page.locator('.copy-list')).toBeVisible({ timeout: 15000 });

        // Verify only GRADED copies appear (GATE4-GRADED should be visible)
        const gradedItem = page.locator('.copy-list li', { hasText: 'Gate 4 Exam' });
        await expect(gradedItem).toBeVisible();

        // Verify LOCKED copy is NOT visible in the UI
        // The GATE4-LOCKED copy should not appear in the list
        const allItems = await page.locator('.copy-list li').count();
        expect(allItems).toBe(1); // Only the GRADED copy should be visible

        // Double-check via API that LOCKED is filtered
        const copiesResp = await page.request.get('/api/students/copies/', {
            headers: { 'Accept': 'application/json' }
        });
        const copies = await copiesResp.json();
        const lockedCopy = copies.find((c: any) => c.anonymous_id === 'GATE4-LOCKED');
        expect(lockedCopy).toBeUndefined();
    });
});
