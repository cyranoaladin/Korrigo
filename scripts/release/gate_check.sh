#!/bin/bash
set -euo pipefail

# Configuration
SHORT_SHA=$(git rev-parse --short HEAD)
PRODLIKE_PORT=8090
PROJECT_NAME="korrigo_gate_${SHORT_SHA}"
COMPOSE_FILE="infra/docker/docker-compose.prodlike.yml"

HEALTH_URL="http://127.0.0.1:${PRODLIKE_PORT}/api/health/"
SEED_URL="http://127.0.0.1:${PRODLIKE_PORT}/api/dev/seed/"

RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'

# Cleanup Trap
cleanup() {
    echo -e "\n${RED}>>> CLEANING UP RESOURCES...${NC}"
    docker compose -p "$PROJECT_NAME" -f "$COMPOSE_FILE" down -v >/dev/null 2>&1 || true
    # Note: .env is preserved for manual usage if present
}
trap cleanup EXIT

echo -e "${GREEN}>>> STARTING RELEASE GATE VERIFICATION (Commit: $SHORT_SHA)${NC}"

# 1) Gate Git Identity & Cleanliness
echo -e "${GREEN}[1] Git Identity & Cleanliness${NC}"
if [ -n "$(git status --porcelain)" ]; then
    echo -e "${RED}FAIL: Git is dirty. Commit changes first.${NC}"
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
if [ ! -d "node_modules" ]; then
    npm ci
fi
# Blocking Lint
npm run lint
npm run typecheck
npm run build
cd ..
echo "OK"

# 3) Backend Quality
echo -e "${GREEN}[3] Backend Quality (Test, Check)${NC}"
cd backend
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi
# Ensure robust environment
venv/bin/pip install -r requirements.txt --quiet

venv/bin/pytest -q
venv/bin/python manage.py check
cd ..
echo "OK"

# Configure Env File option if present
ENV_FILE_OPT=""
if [ -f .env ]; then
    ENV_FILE_OPT="--env-file .env"
fi

# 4) Prodlike Runtime
echo -e "${GREEN}[4] Prodlike Runtime (Docker Compose)${NC}"
# Use unique project name to avoid collision
docker compose -p "$PROJECT_NAME" $ENV_FILE_OPT -f "$COMPOSE_FILE" down -v >/dev/null 2>&1 || true
docker compose -p "$PROJECT_NAME" $ENV_FILE_OPT -f "$COMPOSE_FILE" up -d --build

# Wait for health
echo "Waiting for health check at $HEALTH_URL..."
sleep 5
for i in {1..30}; do
    if curl -sf --max-time 5 "$HEALTH_URL" >/dev/null; then
        echo "Health check passed."
        break
    fi
    echo -n "."
    sleep 2
    if [ $i -eq 30 ]; then
        echo -e "${RED}FAIL: Timeout waiting for health check${NC}"
        docker compose -p "$PROJECT_NAME" $ENV_FILE_OPT -f "$COMPOSE_FILE" logs
        exit 1
    fi
done

# 5) Security Baseline (Runtime)
echo -e "${GREEN}[5] Security Baseline (Runtime validation)${NC}"

# ... (Parsing E2E token) ...

# ...

# Check DEBUG=False
DEBUG_STATUS=$(docker compose -p "$PROJECT_NAME" $ENV_FILE_OPT -f "$COMPOSE_FILE" exec -T backend python -c "import os; from django.conf import settings; print(settings.DEBUG)" | tr -d '\r')
if [ "$DEBUG_STATUS" != "False" ]; then
    echo -e "${RED}FAIL: DEBUG is $DEBUG_STATUS in prodlike (expected False)${NC}"
    exit 1
fi
echo "DEBUG=False verified."

# Check Static Files
echo "Verifying Static Files..."
mkdir -p proofs/artifacts
curl -I --max-time 10 "http://127.0.0.1:${PRODLIKE_PORT}/static/rest_framework/css/bootstrap.min.css" > proofs/artifacts/static_check_headers.txt 2>&1
# Extract code (handle HTTP/1.1 200 OK or HTTP/2 200)
STATIC_HTTP_CODE=$(grep -m 1 "HTTP/" proofs/artifacts/static_check_headers.txt | awk '{print $2}')
if [ "$STATIC_HTTP_CODE" != "200" ]; then
    echo -e "${RED}FAIL: Static file check failed at /static/rest_framework/css/bootstrap.min.css (HTTP $STATIC_HTTP_CODE)${NC}"
    cat proofs/artifacts/static_check_headers.txt
    exit 1
fi
echo "Static files serving verified."

# Check Authentication (Admin)
echo "Verifying Authentication..."
curl -is -X POST --max-time 10 "http://127.0.0.1:${PRODLIKE_PORT}/api/login/" -H "Content-Type: application/json" -d '{"username":"admin","password":"admin"}' > proofs/artifacts/login_check_response.txt 2>&1
LOGIN_HTTP_CODE=$(grep -m 1 "HTTP/" proofs/artifacts/login_check_response.txt | awk '{print $2}')
if [ "$LOGIN_HTTP_CODE" != "200" ] && [ "$LOGIN_HTTP_CODE" != "302" ]; then
    echo -e "${RED}FAIL: Admin Login failed (HTTP $LOGIN_HTTP_CODE)${NC}"
    cat proofs/artifacts/login_check_response.txt
    exit 1
fi
echo "Authentication verified."

echo "Authentication verified."

# 5.5) Gate Concurrency (Soft Lock)
echo -e "${GREEN}[5.5] Concurrency Gate (Lock API)${NC}"

if [ -z "$COPY_ID" ]; then
    echo -e "${RED}SKIP: No Copy ID available for Concurrency Gate${NC}"
else
    # 1. Login Teacher 1
    rm -f proofs/artifacts/cookies_t1.txt
    curl -s -c proofs/artifacts/cookies_t1.txt -X POST "http://127.0.0.1:${PRODLIKE_PORT}/api/login/" -H "Content-Type: application/json" -d '{"username":"teacher","password":"teacher"}' > /dev/null

    # 2. Login Teacher 2
    rm -f proofs/artifacts/cookies_t2.txt
    curl -s -c proofs/artifacts/cookies_t2.txt -X POST "http://127.0.0.1:${PRODLIKE_PORT}/api/login/" -H "Content-Type: application/json" -d '{"username":"teacher2","password":"teacher"}' > /dev/null

    # 3. Teacher 1 acquires lock
    echo "  > Teacher 1 acquiring lock..."
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -b proofs/artifacts/cookies_t1.txt -X POST "http://127.0.0.1:${PRODLIKE_PORT}/api/copies/$COPY_ID/lock/" -H "Content-Type: application/json" -d '{"ttl_seconds": 60}')
    if [ "$HTTP_CODE" != "201" ] && [ "$HTTP_CODE" != "200" ]; then
        echo -e "${RED}FAIL: Teacher 1 failed to lock (HTTP $HTTP_CODE)${NC}"
        exit 1
    fi

    # 4. Teacher 2 tries to lock (Should Fail 409)
    echo "  > Teacher 2 trying to lock (Expect 409)..."
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -b proofs/artifacts/cookies_t2.txt -X POST "http://127.0.0.1:${PRODLIKE_PORT}/api/copies/$COPY_ID/lock/" -H "Content-Type: application/json" -d '{"ttl_seconds": 60}')
    if [ "$HTTP_CODE" != "409" ]; then
        echo -e "${RED}FAIL: Teacher 2 should have been blocked (Got HTTP $HTTP_CODE, Expected 409)${NC}"
        exit 1
    fi
    echo "  ✓ Concurrency Lock verified (409 Conflict received)"
fi

# 6) E2E Playwright
echo -e "${GREEN}[6] E2E Playwright${NC}"
cd frontend
npx playwright install chromium
export BASE_URL="http://127.0.0.1:${PRODLIKE_PORT}"
CI=1 npx playwright test -c e2e/playwright.config.ts --project=chromium --reporter=line
cd ..
echo "OK"

# 7) Release Pack Determinism
echo -e "${GREEN}[7] Release Pack Determinism${NC}"
./scripts/release/build_release_pack.sh
sha256sum -c release/*_SHA256.txt
echo "OK"

echo -e "${GREEN}✅ RELEASE GATE: GO${NC}"
echo "Identity: $SHORT_SHA"
echo "Artifacts in release/"
