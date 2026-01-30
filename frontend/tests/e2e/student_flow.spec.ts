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

        // DEBUG: Route transition logger
        page.on('framenavigated', frame => {
            if (frame === page.mainFrame()) {
                console.log('[nav]', frame.url());
            }
        });

        // DEBUG: Script error logger (Chunk Load Error detection)
        page.on('pageerror', err => console.log('[pageerror]', err.message));
        page.on('requestfailed', r => {
            // Filter out insignificant errors (e.g. aborts)
            if (r.failure()?.errorText !== 'net::ERR_ABORTED') {
                console.log('[requestfailed]', r.url(), r.failure()?.errorText);
            }
        });

        // Ensure clean state
        await page.addInitScript(() => {
            localStorage.clear();
            sessionStorage.clear();
        });

        // 1) LOGIN with relative URL (uses baseURL from config)
        await page.goto('/student/login');
        await expect(page).toHaveURL(/student\/login/, { timeout: 15000 });

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
        expect(href || '').toContain('/api/grading/copies/');
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

    test('Security: Student cannot access another student\'s PDF (403)', async ({ browser }) => {
        // HELPER: Robust login function
        async function loginAs(contextPage: any, ine: string, name: string) {
            // Relative URL to bypass any relative routing ambiguity
            await contextPage.goto('/student/login', { waitUntil: 'domcontentloaded' });
            await expect(contextPage).toHaveURL(/\/student\/login/, { timeout: 15000 });

            await contextPage.fill('input[placeholder="ex: 123456789A"]', ine);
            await contextPage.fill('input[placeholder="Votre nom"]', name);

            const loginResp = contextPage.waitForResponse((r: any) =>
                r.url().includes('/api/students/login/') && r.status() === 200
            );

            await contextPage.click('button[type="submit"]');
            await loginResp;
            await contextPage.waitForURL(/\/student-portal/, { timeout: 15000 });
        }

        // CONTEXT A: Student 1 (E2E_STUDENT)
        const ctxA = await browser.newContext();
        const pageA = await ctxA.newPage();
        await loginAs(pageA, '123456789', 'E2E_STUDENT');

        // CONTEXT B: Student 2 (OTHER)
        const ctxB = await browser.newContext();
        const pageB = await ctxB.newPage();
        await loginAs(pageB, '987654321', 'OTHER');

        // Get OTHER copy id with user B
        const otherCopiesResp = await pageB.request.get('/api/students/copies/');
        expect(otherCopiesResp.status()).toBe(200);
        const otherCopies = await otherCopiesResp.json();
        expect(otherCopies.length).toBeGreaterThan(0);
        const otherCopyId = otherCopies[0].id;

        // Now attempt access from user A session using the ID from B
        // (User A should NOT be able to access User B's copy)
        const forbiddenResp = await pageA.request.get(`/api/grading/copies/${otherCopyId}/final-pdf/`, {
            headers: { 'Accept': 'application/pdf' }
        });
        expect(forbiddenResp.status()).toBe(403);

        await ctxA.close();
        await ctxB.close();
    });

    test('Security: LOCKED copies are not visible in student list', async ({ page }) => {
        // Login as the test student
        await page.goto('/student/login');
        await expect(page).toHaveURL(/\/student\/login/, { timeout: 15000 });
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
        expect(allItems).toBeGreaterThanOrEqual(1); // At least the GRADED copy should be visible

        // Double-check via API that LOCKED is filtered
        const copiesResp = await page.request.get('/api/students/copies/', {
            headers: { 'Accept': 'application/json' }
        });
        const copies = await copiesResp.json();
        const lockedCopy = copies.find((c: any) => c.anonymous_id === 'GATE4-LOCKED');
        expect(lockedCopy).toBeUndefined();
    });
});
