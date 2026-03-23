import { chromium, type FullConfig } from '@playwright/test'

async function globalSetup(config: FullConfig) {
  console.log('🚀 Starting E2E tests setup...')
  
  // Set up browser and context if needed
  const browser = await chromium.launch()
  const context = await browser.newContext()
  
  // You can add global setup logic here
  // For example: login, seed database, etc.
  
  await context.close()
  await browser.close()
  
  console.log('✅ E2E tests setup completed')
}

export default globalSetup
