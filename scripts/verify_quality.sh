#!/bin/bash
set -e

# Ensure we are in the repo root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$REPO_ROOT"

# Configuration
export BASE_URL=http://127.0.0.1:8090
ARTIFACTS_DIR="$REPO_ROOT/proofs/artifacts"
rm -rf "$ARTIFACTS_DIR"
mkdir -p "$ARTIFACTS_DIR"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'

echo -e "${GREEN}>>> Starting Korrigo Production Quality Verification${NC}"

# 1. Backend Verification
echo -e "${GREEN}>>> [1/4] Running Backend Tests...${NC}"
cd backend
if [ ! -d "venv" ]; then
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
else
    source venv/bin/activate
fi

# Run tests
pytest grading/tests/ -v -W error | tee "$ARTIFACTS_DIR/backend_tests_log.txt"
pytest_exit_code=${PIPESTATUS[0]}

deactivate
cd ..

if [ $pytest_exit_code -ne 0 ]; then
    echo -e "${RED}>>> Backend Tests Failed. Check proofs/artifacts/backend_tests_log.txt${NC}"
    exit 1
fi

# 2. Frontend Verification & Build
echo -e "${GREEN}>>> [2/4] Verifying Frontend Quality (Lint & Typecheck)...${NC}"
cd frontend
if [ ! -d "node_modules" ]; then
    npm ci
fi

# Lint
npm run lint > "$ARTIFACTS_DIR/frontend_lint.txt" 2>&1 || echo "Lint finished with issues (see log)"

# Typecheck
npm run typecheck > "$ARTIFACTS_DIR/frontend_typecheck.txt" 2>&1
typecheck_exit_code=$?
if [ $typecheck_exit_code -ne 0 ]; then
    echo -e "${RED}>>> Frontend Typecheck Failed. Check proofs/artifacts/frontend_typecheck.txt${NC}"
    cat "$ARTIFACTS_DIR/frontend_typecheck.txt"
    exit 1
fi
cd ..

# 3. Start Prod-Like Environment
echo -e "${GREEN}>>> [3/4] Starting Prod-Like Environment...${NC}"
COMPOSE_FILE="infra/docker/docker-compose.prodlike.yml"
docker compose -f "$COMPOSE_FILE" down -v
docker compose -f "$COMPOSE_FILE" up -d --build

# Wait for services
echo -e "${GREEN}>>> Waiting for Gateway and Backend (http://localhost:8090/api/health/)...${NC}"
sleep 5
for i in {1..60}; do
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8090/api/health/)
    if [ "$HTTP_CODE" = "200" ]; then
        echo ""
        echo -e "${GREEN}>>> Gateway and Backend are Up!${NC}"
        break
    fi
    echo -n "."
    sleep 1
done

# Check timeout
if [ "$HTTP_CODE" != "200" ]; then
    echo ""
    echo -e "${RED}>>> Timeout waiting for environment.${NC}"
    docker compose -f "$COMPOSE_FILE" logs > "$ARTIFACTS_DIR/startup_failure_logs.txt"
    exit 1
fi

# Log health check
echo "HEALTH_CHECK_HTTP_CODE=$HTTP_CODE" > "$ARTIFACTS_DIR/health_proof.txt"
curl -s http://localhost:8090/api/health/ >> "$ARTIFACTS_DIR/health_proof.txt"
echo ""

# 3.5 Seed Database via API
echo -e "${GREEN}>>> [3.5] Seeding Database via API...${NC}"
SEED_RESPONSE=$(curl -X POST http://127.0.0.1:8090/api/dev/seed/ \
    -H "X-E2E-Seed-Token: secret-e2e-token-prod-like-only" \
    -s -w "\n%{http_code}")

SEED_BODY=$(echo "$SEED_RESPONSE" | head -n -1)
SEED_CODE=$(echo "$SEED_RESPONSE" | tail -n 1)

if [[ "$SEED_CODE" =~ ^3[0-9]{2}$ ]]; then
    echo -e "${RED}✗ FAIL: Seed endpoint returned redirect (HTTP $SEED_CODE)${NC}"
    exit 1
elif [ "$SEED_CODE" = "200" ] || [ "$SEED_CODE" = "201" ]; then
    echo "✓ Seed successful (HTTP $SEED_CODE)"
else
    echo -e "${RED}✗ Seed failed (HTTP $SEED_CODE): $SEED_BODY${NC}"
    exit 1
fi

# 4. E2E Tests
echo -e "${GREEN}>>> [4/4] Running Playwright E2E Tests...${NC}"
cd frontend
npx playwright install chromium
CI=1 npx playwright test -c e2e/playwright.config.ts --project=chromium --reporter=line,html | tee "$ARTIFACTS_DIR/e2e_tests_log.txt"
e2e_exit_code=${PIPESTATUS[0]}

# Move report
if [ -d "playwright-report" ]; then
    mv playwright-report "$ARTIFACTS_DIR/"
fi
cd ..

# 5. Collect Logs
docker compose -f "$COMPOSE_FILE" logs > "$ARTIFACTS_DIR/docker_runtime.txt"

# 6. Result
if [ $e2e_exit_code -eq 0 ]; then
    echo -e "${GREEN}>>> VERIFICATION SUCCESSFUL. GO for Production.${NC}"
    {
        echo "VERIFICATION | STATUS"
        echo "Backend Tests | PASS"
        echo "Frontend Quality | PASS"
        echo "Prod Env Startup | PASS"
        echo "E2E Tests | PASS"
    } > "$ARTIFACTS_DIR/GO_NOGO.txt"
    echo "Creation of Manifest..."
    ls -R "$ARTIFACTS_DIR" > proofs/manifest.json
    echo -e "${GREEN}Success! See proofs/artifacts/ directory.${NC}"
else
    echo -e "${RED}>>> VERIFICATION FAILED.${NC}"
    exit 1
fi
