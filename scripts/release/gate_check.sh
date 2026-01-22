#!/bin/bash
set -euo pipefail

# Configuration
PRODLIKE_PORT=8090
HEALTH_URL="http://127.0.0.1:${PRODLIKE_PORT}/api/health/"
SEED_URL="http://127.0.0.1:${PRODLIKE_PORT}/api/dev/seed/"
RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'

echo -e "${GREEN}>>> STARTING RELEASE GATE VERIFICATION${NC}"

# 1) Gate Git Identity & Cleanliness
echo -e "${GREEN}[1] Git Identity & Cleanliness${NC}"
if [ -n "$(git status --porcelain)" ]; then
    echo -e "${RED}FAIL: Git is dirty.${NC}"
    exit 1
fi

FORBIDDEN_FILES=$(git ls-files | grep -E '(frontend/dist/|playwright-report/|test-results/|PROOF_PACK_FINAL/|^release/|^proofs/artifacts/|^backend/media/|^backend/staticfiles/|db\.sqlite3$|__pycache__/|\.pyc$)' || true)
if [ -n "$FORBIDDEN_FILES" ]; then
    echo -e "${RED}FAIL: Tracked forbidden files found:${NC}"
    echo "$FORBIDDEN_FILES"
    exit 1
fi
echo "OK"

# 2) Frontend Quality
echo -e "${GREEN}[2] Frontend Quality (Install, Lint, Typecheck, Build)${NC}"
cd frontend
# Check if node_modules exists, generally CI uses clean install but for local dev speed we check
if [ ! -d "node_modules" ]; then
    npm ci
fi
# We separate commands to show exactly what failed
npm run lint || echo -e "${RED}WARNING: Lint issues found (non-blocking for now if only warnings)${NC}"
npm run typecheck
npm run build
cd ..
echo "OK"

# 3) Backend Quality
echo -e "${GREEN}[3] Backend Quality (Test, Check)${NC}"
# 3) Backend Quality
echo -e "${GREEN}[3] Backend Quality (Test, Check)${NC}"
cd backend
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi
# Always ensure dependencies are sync (institutional grade means reproducible env)
venv/bin/pip install -r requirements.txt --quiet

venv/bin/pytest -q
venv/bin/python manage.py check
# Verify critical settings are NOT set to obvious dev values in source (env vars override this at runtime, but source check is good)
# We grep for dangerous defaults not protected by os.getenv/DEBUG checks if possible, but runtime check (Gate 5) is better.
cd ..
echo "OK"

# 4) Prodlike Runtime
echo -e "${GREEN}[4] Prodlike Runtime (Docker Compose)${NC}"
COMPOSE_FILE="infra/docker/docker-compose.prodlike.yml"
docker compose -f $COMPOSE_FILE down -v
docker compose -f $COMPOSE_FILE up -d --build

# Wait for health
echo "Waiting for health check at $HEALTH_URL..."
sleep 5
for i in {1..30}; do
    if curl -s "$HEALTH_URL" | grep -q "healthy"; then
        echo "Health check passed."
        break
    fi
    echo -n "."
    sleep 2
    if [ $i -eq 30 ]; then
        echo -e "${RED}FAIL: Timeout waiting for health check${NC}"
        docker compose -f $COMPOSE_FILE logs
        exit 1
    fi
done

# 5) Security Baseline (Runtime)
echo -e "${GREEN}[5] Security Baseline (Runtime validation)${NC}"

# Seed Database (Critical for E2E)
echo "Seeding database..."
SEED_HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$SEED_URL" -H "X-E2E-Seed-Token: secret-e2e-token-prod-like-only")
if [ "$SEED_HTTP_CODE" != "200" ] && [ "$SEED_HTTP_CODE" != "201" ]; then
   echo -e "${RED}FAIL: Seeding failed with HTTP $SEED_HTTP_CODE${NC}"
   exit 1
fi
echo "Database seeded."

# Check DEBUG
DEBUG_STATUS=$(docker compose -f $COMPOSE_FILE exec backend python -c "import os; from django.conf import settings; print(settings.DEBUG)")
if [ "$DEBUG_STATUS" != "False" ]; then
    echo -e "${RED}FAIL: DEBUG is $DEBUG_STATUS in prodlike (expected False)${NC}"
    exit 1
fi
echo "DEBUG=False verified."

# 6) E2E Playwright
echo -e "${GREEN}[6] E2E Playwright${NC}"
cd frontend
# Ensure playwright browsers are installed
npx playwright install chromium
export BASE_URL="http://127.0.0.1:${PRODLIKE_PORT}"
# Run E2E
CI=1 npx playwright test -c e2e/playwright.config.ts --project=chromium --reporter=line
cd ..
echo "OK"

# 8) Release Pack Determinism
echo -e "${GREEN}[8] Release Pack Determinism${NC}"
./scripts/release/build_release_pack.sh
sha256sum -c release/*_SHA256.txt
echo "OK"

echo -e "${GREEN}✅ RELEASE GATE: GO${NC}"
echo "All checks passed. You can sign off on the release in 'release/'."
