#!/usr/bin/env bash
set -euo pipefail

# E2E Test Runner - Single Entrypoint (Docker-only prod-like)
# Usage: bash tools/e2e.sh

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_DIR="$ROOT_DIR/infra/docker"
COMPOSE_FILE="$COMPOSE_DIR/docker-compose.local-prod.yml"
ENV_FILE="$ROOT_DIR/.env"
HEALTH_TIMEOUT=120  # seconds
HEALTH_URL="http://localhost:8088/api/health/"

# Optional: Load E2E contract environment (if .env.e2e exists)
if [[ -f "$ROOT_DIR/.env.e2e" ]]; then
  echo "==> Loading .env.e2e contract"
  set -a
  source "$ROOT_DIR/.env.e2e"
  set +a
fi

# Export E2E mode for Playwright
export E2E_TEST_MODE=true

# Cleanup handler (optional: triggered on EXIT if E2E_CLEANUP=true or CI=true)
cleanup() {
  if [[ "${E2E_CLEANUP:-false}" == "true" ]] || [[ "${CI:-false}" == "true" ]]; then
    echo ""
    echo "==> Cleanup: Stopping Docker Compose"
    docker compose --project-directory "$COMPOSE_DIR" --env-file "$ENV_FILE" -f "$COMPOSE_FILE" down -v
  fi
}
trap cleanup EXIT

echo "==> Up docker env (prod-like)"
docker compose --project-directory "$COMPOSE_DIR" --env-file "$ENV_FILE" -f "$COMPOSE_FILE" down -v --remove-orphans
docker compose --project-directory "$COMPOSE_DIR" --env-file "$ENV_FILE" -f "$COMPOSE_FILE" up -d --build

echo "==> Wait health (timeout: ${HEALTH_TIMEOUT}s)"
SECONDS_WAITED=0
until curl -fsS "$HEALTH_URL" >/dev/null 2>&1; do
  if (( SECONDS_WAITED >= HEALTH_TIMEOUT )); then
    echo "  ✗ Health check timeout after ${HEALTH_TIMEOUT}s"
    echo ""
    echo "==> Backend logs (last 50 lines):"
    docker compose --project-directory "$COMPOSE_DIR" --env-file "$ENV_FILE" -f "$COMPOSE_FILE" logs backend --tail=50
    exit 1
  fi
  echo "  Waiting for backend... (${SECONDS_WAITED}s)"
  sleep 2
  SECONDS_WAITED=$((SECONDS_WAITED + 2))
done
echo "  ✓ Backend healthy"

echo "==> Run migrations"
docker compose --project-directory "$COMPOSE_DIR" --env-file "$ENV_FILE" -f "$COMPOSE_FILE" exec -T backend \
  bash -lc "export PYTHONPATH=/app && python manage.py migrate"

echo "==> Seed E2E (inside backend container)"
docker compose --project-directory "$COMPOSE_DIR" --env-file "$ENV_FILE" -f "$COMPOSE_FILE" exec -T backend \
  bash -lc "python manage.py seed_e2e"

echo "==> Run Playwright"
cd "$ROOT_DIR/frontend"
npx playwright test --workers=1

echo ""
echo "✅ E2E Tests Complete"
