import { chromium, expect } from '@playwright/test';
import path from 'path';
import fs from 'fs';

const STORAGE_STATE = path.resolve(__dirname, '.auth/admin.json');

export default async function globalSetup() {
    const baseURL = process.env.BASE_URL || 'http://127.0.0.1:8090';

    console.log('🔐 Global Setup: Creating authenticated session...');
    console.log(`  Base URL: ${baseURL}`);

    const browser = await chromium.launch();
    const context = await browser.newContext();
    const page = await context.newPage();

    page.on('console', (msg) => console.log(`[browser:${msg.type()}]`, msg.text()));
    page.on('pageerror', (err) => console.log('[pageerror]', err));

    try {
        // Step 1: Get CSRF token via context request (proper cookie handling)
        const csrfResponse = await context.request.get(`${baseURL}/api/csrf/`);
        const csrfData = await csrfResponse.json();
        const csrfToken = csrfData.csrfToken || '';
        console.log(`  ✓ CSRF token obtained`);

        // Step 2: Login via context request (cookies auto-managed by Playwright)
        const loginResponse = await context.request.post(`${baseURL}/api/login/`, {
            data: { username: 'admin', password: 'admin' },
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken,
            },
        });

        if (!loginResponse.ok()) {
            const body = await loginResponse.text();
            throw new Error(`Login API failed: HTTP ${loginResponse.status()}\nBody:\n${body}`);
        }
        console.log(`  ✓ Login API responded: HTTP ${loginResponse.status()}`);

        // Step 3: Verify session via /api/me/
        const meResponse = await context.request.get(`${baseURL}/api/me/`);
        if (!meResponse.ok()) {
            const body = await meResponse.text();
            throw new Error(`/api/me/ failed: HTTP ${meResponse.status()}\nBody:\n${body}`);
        }
        console.log(`  ✓ User data fetched: HTTP ${meResponse.status()}`);

        // Step 4: Navigate to dashboard (cookies already in context)
        await page.goto(`${baseURL}/admin-dashboard`, { waitUntil: 'networkidle', timeout: 30000 });

        // Verify dashboard is visible
        await expect(page.getByTestId('admin-dashboard')).toBeVisible({ timeout: 15000 });
        console.log('  ✓ Dashboard visible (Hydration confirmed via real app flow)');

        // Save authenticated state
        const authDir = path.dirname(STORAGE_STATE);
        if (!fs.existsSync(authDir)) {
            fs.mkdirSync(authDir, { recursive: true });
        }
        await context.storageState({ path: STORAGE_STATE });
        console.log(`  ✓ Session saved to ${STORAGE_STATE}`);

    } catch (error) {
        console.error('  ✗ Global setup failed:', error);

        const proofDir = path.resolve(process.cwd(), 'PROOF_PACK_FINAL');
        if (!fs.existsSync(proofDir)) {
            fs.mkdirSync(proofDir, { recursive: true });
        }

        await page.screenshot({
            path: path.join(proofDir, 'global_setup_failure.png'),
            fullPage: true
        }).catch(() => { });

        const html = await page.content().catch(() => '');
        fs.writeFileSync(path.join(proofDir, 'global_setup_failure.html'), html);

        throw error;
    } finally {
        await browser.close();
    }

    console.log('✅ Global setup completed\n');
}
