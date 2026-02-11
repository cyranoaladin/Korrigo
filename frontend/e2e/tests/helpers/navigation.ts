import { expect, Page, BrowserContext } from '@playwright/test';

/**
 * Opens a new tab in the browser context and navigates to the specified URL
 */
export async function openNewTab(context: BrowserContext, url: string): Promise<Page> {
    const newPage = await context.newPage();
    await newPage.goto(url, { waitUntil: 'domcontentloaded' });
    await newPage.waitForLoadState('networkidle');
    return newPage;
}

/**
 * Verifies that the current page URL matches the expected URL or pattern
 */
export async function verifyRedirect(page: Page, expectedUrl: string | RegExp, timeout = 5000) {
    await page.waitForTimeout(500);
    await page.waitForLoadState('networkidle', { timeout });
    
    const currentUrl = page.url();
    
    if (typeof expectedUrl === 'string') {
        if (expectedUrl.startsWith('/')) {
            // Relative URL - check if current URL contains this path
            expect(currentUrl, `Expected URL to contain ${expectedUrl}, got ${currentUrl}`).toContain(expectedUrl);
        } else {
            // Absolute URL - exact match
            expect(currentUrl, `Expected ${expectedUrl}, got ${currentUrl}`).toBe(expectedUrl);
        }
    } else {
        // Regex pattern
        expect(currentUrl, `Expected URL to match ${expectedUrl}, got ${currentUrl}`).toMatch(expectedUrl);
    }
}

/**
 * Performs logout action by clicking the logout button
 * Uses multiple selectors to support different dashboards
 */
export async function logout(page: Page) {
    const logoutButton = page.locator('[data-testid="logout-button"], .logout-btn, .btn-logout').first();
    await logoutButton.click();
    await page.waitForTimeout(1500);
    await page.waitForLoadState('networkidle');
}
