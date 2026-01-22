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

    // Diagnostic logging for failures
    page.on('console', (msg) => console.log(`[browser:${msg.type()}]`, msg.text()));
    page.on('pageerror', (err) => console.log('[pageerror]', err));

    try {
        // Navigate to login page to establish session/cookies
        await page.goto(`${baseURL}/login`, { waitUntil: 'domcontentloaded', timeout: 15000 });
        console.log('  ✓ Login page loaded');

        // Perform login via direct API call (matches frontend auth.js behavior)
        const loginResult = await page.evaluate(async (url) => {
            try {
                const res = await fetch(`${url}/api/login/`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ username: 'admin', password: 'password' }),
                    credentials: 'include'  // Important: include cookies
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
        }, baseURL);

        if (!loginResult.ok) {
            throw new Error(`Login API failed: HTTP ${loginResult.status}\nBody:\n${loginResult.body}`);
        }
        console.log(`  ✓ Login API responded: HTTP ${loginResult.status}`);

        // Fetch user data to complete auth flow (matches frontend)
        const userResult = await page.evaluate(async (url) => {
            try {
                const res = await fetch(`${url}/api/me/`, {
                    credentials: 'include'
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
        }, baseURL);

        if (!userResult.ok) {
            throw new Error(`/api/me/ failed: HTTP ${userResult.status}\nBody:\n${userResult.body}`);
        }
        console.log(`  ✓ User data fetched: HTTP ${userResult.status}`);

        // Navigate to dashboard to verify auth works (protected route)
        // This triggers the real app hydration via router guard
        await page.goto(`${baseURL}/admin-dashboard`, { waitUntil: 'networkidle', timeout: 30000 });

        // Verify dashboard UI is visible, confirming real code hydration
        await expect(page.getByTestId('admin-dashboard')).toBeVisible({ timeout: 15000 });
        console.log('  ✓ Dashboard visible (Hydration confirmed via real app flow)');

        // Save authenticated state (cookies)
        const authDir = path.dirname(STORAGE_STATE);
        if (!fs.existsSync(authDir)) {
            fs.mkdirSync(authDir, { recursive: true });
        }
        await context.storageState({ path: STORAGE_STATE });
        console.log(`  ✓ Session saved to ${STORAGE_STATE}`);

    } catch (error) {
        console.error('  ✗ Global setup failed:', error);

        // Capture diagnostic artifacts
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
