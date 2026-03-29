import { test } from '@playwright/test';

test('Simulateur Tablette - Mode Manuel', async ({ page }) => {
    // Augmenter le timeout pour permettre une interaction manuelle prolongée
    test.setTimeout(0); 

    console.log('--- OUVERTURE DU SIMULATEUR TABLETTE ---');
    
    // Aller à la page de destination (utilise la baseURL de playwright.config.ts)
    await page.goto('/');

    // Message d'instruction dans la console
    console.log('Le simulateur est prêt. Vous pouvez interagir avec la fenêtre du navigateur.');
    console.log('La fenêtre restera ouverte tant que vous ne fermez pas ce processus (Ctrl+C).');

    // Attendre indéfiniment (ou jusqu'à fermeture manuelle)
    await page.waitForEvent('close', { timeout: 0 });
});
