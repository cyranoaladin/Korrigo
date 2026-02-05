/**
 * E2E Global Setup - Parallel Execution
 *
 * This setup handles parallel worker initialization for Playwright tests.
 * Each worker runs this setup independently to ensure proper isolation.
 *
 * IMPORTANT: Docker orchestration is handled by tools/e2e.sh (single entrypoint).
 * This setup validates that the E2E environment is ready and logs worker-specific info.
 *
 * When running tests directly (e.g., npx playwright test), ensure:
 * 1. Docker Compose is already running
 * 2. Backend is healthy
 * 3. E2E data is seeded
 */

export default async function globalSetup() {
  const workerIndex = process.env.PLAYWRIGHT_WORKER_INDEX;
  const workerId = workerIndex !== undefined ? `worker-${workerIndex}` : 'main';
  
  console.log(`\n==> E2E Global Setup [${workerId}]: Starting initialization...`);

  if (process.env.E2E_TEST_MODE !== 'true') {
    console.warn(`  [${workerId}] ⚠️  E2E_TEST_MODE is not set to "true"`);
    console.warn(`  [${workerId}] ⚠️  Run tests via: bash tools/e2e.sh`);
    console.warn(`  [${workerId}] ⚠️  Or ensure Docker Compose + seed are ready`);
  }

  await performHealthCheck(workerId);
  
  console.log(`  [${workerId}] ℹ️  Worker isolation: Each worker shares the same backend`);
  console.log(`  [${workerId}] ℹ️  Per-worker database isolation: Placeholder for future implementation`);
  console.log(`  [${workerId}] ✓ Environment validation complete\n`);
}

async function performHealthCheck(workerId: string): Promise<void> {
  const baseURL = process.env.E2E_BASE_URL || 'http://localhost:8088';
  const healthEndpoint = `${baseURL}/api/health/`;
  
  try {
    console.log(`  [${workerId}] Checking backend health at ${healthEndpoint}...`);
    const response = await fetch(healthEndpoint);
    
    if (response.ok) {
      console.log(`  [${workerId}] ✓ Backend health check passed (status: ${response.status})`);
    } else {
      console.warn(`  [${workerId}] ⚠️  Backend returned status ${response.status}`);
      console.warn(`  [${workerId}] ⚠️  Tests may fail - ensure backend is running`);
    }
  } catch (error) {
    console.warn(`  [${workerId}] ⚠️  Backend health check failed - ensure tools/e2e.sh was run`);
    console.warn(`  [${workerId}] Error: ${error instanceof Error ? error.message : 'Unknown'}`);
  }
}
