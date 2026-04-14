import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { defineConfig, devices } from '@playwright/test'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const repoRoot = path.resolve(__dirname, '..')

function loadEnvFile(filePath: string) {
    if (!fs.existsSync(filePath)) return

    const content = fs.readFileSync(filePath, 'utf-8')
    for (const rawLine of content.split(/\r?\n/)) {
        const line = rawLine.trim()
        if (!line || line.startsWith('#')) continue
        const idx = line.indexOf('=')
        if (idx <= 0) continue

        const key = line.slice(0, idx).trim()
        if (process.env[key]) continue

        let value = line.slice(idx + 1).trim()
        if (
            (value.startsWith('"') && value.endsWith('"')) ||
            (value.startsWith("'") && value.endsWith("'"))
        ) {
            value = value.slice(1, -1)
        }
        process.env[key] = value
    }
}

loadEnvFile(path.join(repoRoot, '.env.e2e'))
loadEnvFile(path.join(repoRoot, '.env'))

export default defineConfig({
    testDir: './tests/e2e',
    globalSetup: './tests/e2e/global-setup.ts',
    fullyParallel: false,
    forbidOnly: !!process.env.CI,
    retries: process.env.CI ? 2 : 0,
    workers: 1,
    reporter: process.env.CI ? 'html' : 'list',
    use: {
        baseURL: process.env.E2E_BASE_URL || 'http://localhost:8088',
        trace: 'on-first-retry',
    },
    projects: [
        {
            name: 'tablet',
            use: { 
                ...devices['iPad Air'],
                viewport: { width: 820, height: 1180 },
                deviceScaleFactor: 2,
                isMobile: true,
                hasTouch: true,
            },
        },
    ],
});
