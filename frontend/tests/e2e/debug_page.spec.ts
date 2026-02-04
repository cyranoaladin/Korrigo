import { test, expect } from '@playwright/test'

test('Debug: Check what renders on /admin/login', async ({ page }) => {
    const consoleMessages: string[] = []
    const errors: string[] = []
    
    page.on('console', msg => {
        consoleMessages.push(`[${msg.type()}] ${msg.text()}`)
    })
    
    page.on('pageerror', error => {
        errors.push(`Page error: ${error.message}`)
    })
    
    await page.goto('/admin/login')
    await page.waitForLoadState('networkidle')
    await page.waitForTimeout(2000)
    
    const html = await page.content()
    console.log('=== PAGE HTML ===')
    console.log(html)
    console.log('\n=== CONSOLE MESSAGES ===')
    consoleMessages.forEach(msg => console.log(msg))
    console.log('\n=== ERRORS ===')
    errors.forEach(err => console.log(err))
    
    await page.screenshot({ 
        path: 'debug-admin-login.png',
        fullPage: true 
    })
    
    const appDiv = await page.locator('#app').innerHTML()
    console.log('\n=== APP DIV CONTENT ===')
    console.log(appDiv)
})
