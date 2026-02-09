import { defineConfig, devices } from '@playwright/test';
import path from 'path';

export default defineConfig({
  testDir: './tests',
  fullyParallel: false,  // Sequential for E2E stability
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 1,
  workers: 1,  // Single worker for deterministic execution
  reporter: 'html',
  timeout: 60000,

  // Global setup disabled — each test uses loginAsAdmin() in beforeEach
  // globalSetup: path.resolve(__dirname, 'global-setup.ts'),

  use: {
    baseURL: process.env.BASE_URL || 'http://127.0.0.1:8088',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',

    // Use direct API login in beforeEach instead of storageState for reliability
    // storageState: path.resolve(__dirname, '.auth/admin.json'),
  },

  // Configure projects - chromium only for speed
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
});
