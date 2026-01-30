/**
 * E2E Global Setup
 *
 * IMPORTANT: Docker orchestration is handled by tools/e2e.sh (single entrypoint).
 * This setup only validates that the E2E environment is ready.
 *
 * When running tests directly (e.g., npx playwright test), ensure:
 * 1. Docker Compose is already running
 * 2. Backend is healthy
 * 3. E2E data is seeded
 */

export default async function globalSetup() {
  console.log('==> E2E Global Setup: Validating environment...');

  // Verify E2E mode is enabled (guard against accidental runs)
  if (process.env.E2E_TEST_MODE !== 'true') {
    console.warn('⚠️  E2E_TEST_MODE is not set to "true"');
    console.warn('⚠️  Run tests via: bash tools/e2e.sh');
    console.warn('⚠️  Or ensure Docker Compose + seed are ready');
  }

  // Simple health check (non-blocking warning if fails)
  try {
    const response = await fetch('http://localhost:8088/api/health/');
    if (response.ok) {
      console.log('  ✓ Backend health check passed');
    } else {
      console.warn(`  ⚠️  Backend returned status ${response.status}`);
    }
  } catch (error) {
    console.warn('  ⚠️  Backend health check failed - ensure tools/e2e.sh was run');
    console.warn(`  Error: ${error instanceof Error ? error.message : 'Unknown'}`);
  }

  console.log('  ✓ Environment validation complete');
}
