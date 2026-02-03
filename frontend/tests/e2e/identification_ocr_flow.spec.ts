import { test, expect } from '@playwright/test';
import { CREDS } from './helpers/auth';

test.describe('PRD-19: Multi-layer OCR Identification Flow', () => {

    test.beforeEach(async ({ page }) => {
        // Login as teacher/admin
        await page.goto('/admin/login');
        await page.fill('input[name="username"]', CREDS.admin.username);
        await page.fill('input[name="password"]', CREDS.admin.password);
        await page.click('input[type="submit"]');
        await page.waitForURL(/\/admin\/$/, { timeout: 15000 });
    });

    test('Teacher can access identification desk', async ({ page }) => {
        await page.goto('/identification-desk');
        await expect(page).toHaveURL(/\/identification-desk/);
        await expect(page.locator('h1:has-text("Identification")')).toBeVisible();
    });

    test('Semi-automatic mode: Display OCR candidates with confidence scores', async ({ page }) => {
        // Navigate to identification desk
        await page.goto('/identification-desk');
        await page.waitForLoadState('networkidle');

        // Check if there are copies to identify
        const noCopiesMessage = page.locator('text=Toutes les copies sont identifiées');
        const hasCopies = !(await noCopiesMessage.isVisible());

        if (!hasCopies) {
            test.skip();
            return;
        }

        // Wait for OCR candidates to load (if available)
        const ocrCandidatesSection = page.locator('text=Candidats OCR Multi-Moteur');

        if (await ocrCandidatesSection.isVisible({ timeout: 5000 })) {
            // Verify OCR candidates are displayed
            await expect(ocrCandidatesSection).toBeVisible();

            // Check for candidate cards
            const candidateCards = page.locator('[class*="border-2"][class*="rounded-lg"]').filter({
                has: page.locator('button:has-text("Sélectionner cet étudiant")')
            });

            const count = await candidateCards.count();
            expect(count).toBeGreaterThan(0);
            expect(count).toBeLessThanOrEqual(5); // Max 5 candidates

            // Verify first candidate has all required elements
            const firstCandidate = candidateCards.first();
            await expect(firstCandidate.locator('.font-bold.text-gray-900')).toBeVisible(); // Student name
            await expect(firstCandidate.locator('text=Confiance')).toBeVisible(); // Confidence label
            await expect(firstCandidate.locator('text=moteurs en accord')).toBeVisible(); // Vote info
            await expect(firstCandidate.locator('details summary:has-text("Voir détails OCR")')).toBeVisible(); // Expandable details
        }
    });

    test('Semi-automatic mode: Expand OCR source details', async ({ page }) => {
        await page.goto('/identification-desk');
        await page.waitForLoadState('networkidle');

        const ocrCandidatesSection = page.locator('text=Candidats OCR Multi-Moteur');

        if (await ocrCandidatesSection.isVisible({ timeout: 5000 })) {
            // Find first candidate card
            const firstCandidate = page.locator('[class*="border-2"][class*="rounded-lg"]')
                .filter({ has: page.locator('button:has-text("Sélectionner cet étudiant")') })
                .first();

            // Expand OCR details
            const detailsSummary = firstCandidate.locator('details summary:has-text("Voir détails OCR")');
            await detailsSummary.click();

            // Verify OCR sources are displayed
            const ocrSources = firstCandidate.locator('details ul li');
            const sourceCount = await ocrSources.count();
            expect(sourceCount).toBeGreaterThan(0);

            // Verify source format contains engine name and text
            const firstSource = ocrSources.first();
            const sourceText = await firstSource.textContent();
            expect(sourceText).toMatch(/(tesseract|easyocr|paddleocr)/i);
        }
    });

    test('Semi-automatic mode: Select OCR candidate', async ({ page }) => {
        await page.goto('/identification-desk');
        await page.waitForLoadState('networkidle');

        const ocrCandidatesSection = page.locator('text=Candidats OCR Multi-Moteur');

        if (await ocrCandidatesSection.isVisible({ timeout: 5000 })) {
            // Count initial unidentified copies
            const initialCopyId = await page.locator('.absolute.top-4.left-4').textContent();

            // Select first candidate
            const firstCandidateButton = page.locator('button:has-text("Sélectionner cet étudiant")').first();

            // Mock API response for candidate selection
            await page.route('**/api/identification/copies/*/select-candidate/', async (route) => {
                await route.fulfill({
                    status: 200,
                    contentType: 'application/json',
                    body: JSON.stringify({
                        success: true,
                        student: {
                            id: 1,
                            first_name: 'Jean',
                            last_name: 'Dupont',
                            email: 'jean.dupont@example.com'
                        },
                        status: 'READY'
                    })
                });
            });

            await firstCandidateButton.click();

            // Wait for next copy to load or completion message
            await page.waitForTimeout(1000);

            // Verify we moved to next copy or see completion message
            const newCopyId = await page.locator('.absolute.top-4.left-4').textContent();
            const completionMessage = page.locator('text=Toutes les copies sont identifiées');

            const didProgress = newCopyId !== initialCopyId || await completionMessage.isVisible();
            expect(didProgress).toBeTruthy();
        }
    });

    test('Semi-automatic mode: Fallback to manual search', async ({ page }) => {
        await page.goto('/identification-desk');
        await page.waitForLoadState('networkidle');

        const ocrCandidatesSection = page.locator('text=Candidats OCR Multi-Moteur');

        if (await ocrCandidatesSection.isVisible({ timeout: 5000 })) {
            // Click "Manual Search" button
            const manualSearchButton = page.locator('button:has-text("Aucun de ces candidats ? Recherche manuelle")');
            await expect(manualSearchButton).toBeVisible();
            await manualSearchButton.click();

            // Verify manual search interface is shown
            await expect(page.locator('label:has-text("Rechercher (Nom, Prénom, INE)")')).toBeVisible();
            await expect(page.locator('input[placeholder*="Tapez pour chercher"]')).toBeVisible();

            // Verify OCR candidates are hidden
            await expect(ocrCandidatesSection).not.toBeVisible();
        }
    });

    test('Manual mode: Search and select student', async ({ page }) => {
        await page.goto('/identification-desk');
        await page.waitForLoadState('networkidle');

        // Check if manual search is available (no OCR candidates or after clicking manual override)
        const searchInput = page.locator('input[placeholder*="Tapez pour chercher"]');

        // If OCR candidates are shown, click manual override first
        const manualSearchButton = page.locator('button:has-text("Aucun de ces candidats ? Recherche manuelle")');
        if (await manualSearchButton.isVisible({ timeout: 2000 })) {
            await manualSearchButton.click();
        }

        // Wait for search input to be visible
        await expect(searchInput).toBeVisible();

        // Mock student search API
        await page.route('**/api/students/?search=*', async (route) => {
            await route.fulfill({
                status: 200,
                contentType: 'application/json',
                body: JSON.stringify([
                    {
                        id: 1,
                        first_name: 'Jean',
                        last_name: 'Dupont',
                        class_name: '3A',
                        ine: '1234567890A'
                    },
                    {
                        id: 2,
                        first_name: 'Marie',
                        last_name: 'Durand',
                        class_name: '3B',
                        ine: '1234567890B'
                    }
                ])
            });
        });

        // Type in search box
        await searchInput.fill('Dupont');
        await page.waitForTimeout(500);

        // Verify search results appear
        const searchResults = page.locator('.p-3.border-b.cursor-pointer');
        await expect(searchResults.first()).toBeVisible();

        // Click first result
        await searchResults.first().click();

        // Verify student is selected
        await expect(page.locator('text=Sélectionné :')).toBeVisible();
        await expect(page.locator('text=Dupont Jean')).toBeVisible();

        // Verify validate button is enabled
        const validateButton = page.locator('button:has-text("VALIDER & SUIVANT")');
        await expect(validateButton).toBeEnabled();
    });

    test('Confidence score visual indicators', async ({ page }) => {
        await page.goto('/identification-desk');
        await page.waitForLoadState('networkidle');

        const ocrCandidatesSection = page.locator('text=Candidats OCR Multi-Moteur');

        if (await ocrCandidatesSection.isVisible({ timeout: 5000 })) {
            // Check first candidate card styling based on confidence
            const firstCandidate = page.locator('[class*="border-2"][class*="rounded-lg"]')
                .filter({ has: page.locator('button:has-text("Sélectionner cet étudiant")') })
                .first();

            // High confidence cards should have green styling
            const hasGreenBorder = await firstCandidate.evaluate((el) => {
                return el.className.includes('border-green');
            });

            const hasGrayBorder = await firstCandidate.evaluate((el) => {
                return el.className.includes('border-gray');
            });

            // Should have either green (high confidence) or gray (lower confidence) border
            expect(hasGreenBorder || hasGrayBorder).toBeTruthy();

            // Verify confidence bar exists
            const confidenceBar = firstCandidate.locator('.h-2.bg-gray-200.rounded-full');
            await expect(confidenceBar).toBeVisible();
        }
    });

    test('Rank badges display correctly', async ({ page }) => {
        await page.goto('/identification-desk');
        await page.waitForLoadState('networkidle');

        const ocrCandidatesSection = page.locator('text=Candidats OCR Multi-Moteur');

        if (await ocrCandidatesSection.isVisible({ timeout: 5000 })) {
            const candidateCards = page.locator('[class*="border-2"][class*="rounded-lg"]')
                .filter({ has: page.locator('button:has-text("Sélectionner cet étudiant")') });

            const count = await candidateCards.count();

            // Verify rank badges (1-5)
            for (let i = 0; i < Math.min(count, 5); i++) {
                const rankBadge = candidateCards.nth(i).locator('.w-8.h-8.rounded-full').first();
                await expect(rankBadge).toBeVisible();

                const rankText = await rankBadge.textContent();
                expect(rankText).toBe((i + 1).toString());
            }

            // First place should have gold gradient
            const firstBadge = candidateCards.first().locator('.w-8.h-8.rounded-full').first();
            const hasGoldGradient = await firstBadge.evaluate((el) => {
                return el.className.includes('from-yellow-400');
            });
            expect(hasGoldGradient).toBeTruthy();
        }
    });
});
