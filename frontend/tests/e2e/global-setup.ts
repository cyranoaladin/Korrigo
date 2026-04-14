import { execFileSync } from 'node:child_process'
import type { FullConfig } from '@playwright/test'

const HEALTH_TIMEOUT_MS = 30000
const POLL_INTERVAL_MS = 1000

async function waitForHealthy(baseUrl: string) {
  const startedAt = Date.now()
  while (Date.now() - startedAt < HEALTH_TIMEOUT_MS) {
    try {
      execFileSync('curl', ['-sf', `${baseUrl}/api/health/`], { stdio: 'pipe' })
      return
    } catch {
      // Backend still booting.
    }
    await new Promise((resolve) => setTimeout(resolve, POLL_INTERVAL_MS))
  }
  throw new Error(`Backend health check timed out after ${HEALTH_TIMEOUT_MS}ms (${baseUrl})`)
}

async function globalSetup(config: FullConfig) {
  console.log('🚀 Starting E2E tests setup...')

  const baseUrl = String(
    process.env.E2E_BASE_URL ||
    config.projects[0]?.use?.baseURL ||
    'http://localhost:8088'
  ).replace(/\/$/, '')
  const backendUrl = String(
    process.env.E2E_BACKEND_URL ||
    process.env.VITE_API_TARGET ||
    'http://127.0.0.1:8000'
  ).replace(/\/$/, '')
  const seedToken = process.env.E2E_SEED_TOKEN

  if (!seedToken) {
    throw new Error('E2E_SEED_TOKEN is required for deterministic Playwright seeding.')
  }

  await waitForHealthy(backendUrl)

  let payload: Record<string, unknown>
  try {
    const raw = execFileSync(
      'curl',
      [
        '-sf',
        '-X',
        'POST',
        '-H',
        `X-E2E-Seed-Token: ${seedToken}`,
        `${backendUrl}/api/dev/seed/`,
      ],
      { encoding: 'utf-8' }
    )
    payload = JSON.parse(raw)
  } catch (error) {
    throw new Error(`E2E seed failed against ${backendUrl}: ${String(error)}`)
  }

  console.log(`🌱 Seed OK for ${baseUrl}: ${payload.message || 'done'}`)
  console.log('✅ E2E tests setup completed')
}

export default globalSetup
