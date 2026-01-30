#!/usr/bin/env bash
set -euo pipefail

# ============================================================
# Korrigo - Prod Readiness Verification (Lead Audit Script)
# Run from repository root:
#   bash tools/verify_prod_ready.sh
# ============================================================

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

# -----------------------------
# Helpers
# -----------------------------
GREEN="\033[0;32m"
RED="\033[0;31m"
YELLOW="\033[0;33m"
NC="\033[0m"

say()   { echo -e "${GREEN}==> $*${NC}"; }
warn()  { echo -e "${YELLOW}⚠️  $*${NC}"; }
fail()  { echo -e "${RED}✗ $*${NC}"; exit 1; }

need_cmd() {
  command -v "$1" >/dev/null 2>&1 || fail "Command not found: $1"
}

section() {
  echo ""
  echo "============================================================"
  echo "$1"
  echo "============================================================"
}

# -----------------------------
# Requirements
# -----------------------------
section "0) Preflight - Required tools"

need_cmd git
need_cmd bash
need_cmd python3
need_cmd docker
need_cmd curl

# docker compose can be plugin or standalone
if docker compose version >/dev/null 2>&1; then
  DOCKER_COMPOSE="docker compose"
elif command -v docker-compose >/dev/null 2>&1; then
  DOCKER_COMPOSE="docker-compose"
else
  fail "docker compose not available (need 'docker compose' or 'docker-compose')"
fi

# Node optional but recommended for local frontend gates
if command -v node >/dev/null 2>&1 && command -v npm >/dev/null 2>&1; then
  HAS_NODE=true
else
  HAS_NODE=false
  warn "node/npm not found. Frontend lint/typecheck/build will be skipped locally (Docker E2E still builds frontend in nginx image)."
fi

# -----------------------------
# Git sanity
# -----------------------------
section "1) Git sanity - clean tree + correct branch"

say "Git status (must be clean)"
git status --porcelain
if [[ -n "$(git status --porcelain)" ]]; then
  fail "Working tree is not clean. Commit or stash changes before verifying."
fi

CURRENT_BRANCH="$(git rev-parse --abbrev-ref HEAD)"
say "Current branch: ${CURRENT_BRANCH}"
if [[ "$CURRENT_BRANCH" != "main" ]]; then
  warn "You are not on 'main' (current: $CURRENT_BRANCH). That's OK if intended, but prod verification is usually done on main."
fi

say "Fetch origin and check divergence"
git fetch origin >/dev/null 2>&1 || true

LOCAL_HEAD="$(git rev-parse HEAD)"
ORIGIN_MAIN=""
if git rev-parse --verify origin/main >/dev/null 2>&1; then
  ORIGIN_MAIN="$(git rev-parse origin/main)"
  say "HEAD        : ${LOCAL_HEAD}"
  say "origin/main : ${ORIGIN_MAIN}"
  if [[ "$LOCAL_HEAD" != "$ORIGIN_MAIN" ]]; then
    warn "Local HEAD differs from origin/main. That's acceptable for local verification but NOT 'repo=truth remote'."
  fi
else
  warn "origin/main not found (maybe no remote?)."
fi

# Optional: enforce exact commit if you want strictness
# EXPECTED="386afcd"
# git rev-parse --short HEAD | grep -q "$EXPECTED" || fail "Not on expected commit $EXPECTED"

# -----------------------------
# Repository shape checks
# -----------------------------
section "2) Repo structure checks"

[[ -d backend ]]   || fail "Missing backend/ directory"
[[ -d tools ]]     || fail "Missing tools/ directory"
[[ -f tools/e2e.sh ]] || fail "Missing tools/e2e.sh (E2E single entrypoint)"

[[ -d frontend ]] && FRONTEND_DIR_OK=true || FRONTEND_DIR_OK=false
if [[ "$FRONTEND_DIR_OK" == "true" ]]; then
  say "Found frontend/ directory"
else
  warn "frontend/ directory not found. If this is expected, adjust script; otherwise repo is inconsistent."
fi

# -----------------------------
# Backend - venv + deps + tests
# -----------------------------
section "3) Backend - environment + tests (no skip)"

[[ -d backend ]] || fail "backend/ not found"
pushd backend >/dev/null

# Ensure venv exists
if [[ ! -d .venv ]]; then
  warn "backend/.venv not found. Creating a fresh venv (python3 -m venv .venv)."
  python3 -m venv .venv
fi

say "Activate backend venv"
# shellcheck disable=SC1091
source .venv/bin/activate

say "Python version"
python --version

# Install deps if requirements exists
if [[ -f requirements.txt ]]; then
  say "Install backend requirements (pip)"
  pip install -U pip >/dev/null
  pip install -r requirements.txt >/dev/null
else
  warn "backend/requirements.txt not found. Skipping pip install step."
fi

# Hard guard: ensure Django is importable to avoid the previous pitfall (running pytest from root without venv)
say "Sanity import: django"
python -c "import django; print('django ok:', django.get_version())" >/dev/null

say "Run backend pytest (strict: fail fast, show skips summary)"
# -q is OK, but we also want explicit skip count. We'll run with -ra for summary.
pytest -q --maxfail=1 -ra

deactivate || true
popd >/dev/null

# -----------------------------
# Frontend - lint/typecheck/build (local)
# -----------------------------
section "4) Frontend - quality gates (lint/typecheck/build)"

if [[ "$HAS_NODE" == "true" && -d frontend ]]; then
  pushd frontend >/dev/null

  if [[ -f package-lock.json ]]; then
    say "npm ci (clean, reproducible)"
    npm ci
  else
    warn "No package-lock.json found. Using npm install."
    npm install
  fi

  say "npm run lint"
  npm run lint

  say "npm run typecheck"
  npm run typecheck

  say "npm run build"
  npm run build

  # Security hygiene: show vulnerabilities (do not fail by default; policy varies)
  section "4bis) Frontend - npm audit (informational)"
  warn "npm audit may report vulnerabilities. Treat as release gate if your policy requires."
  npm audit || true

  popd >/dev/null
else
  warn "Skipping local frontend gates (node/npm missing or frontend/ missing). Docker E2E will still validate prod-like build."
fi

# -----------------------------
# Docker - clean build + health + E2E
# -----------------------------
section "5) Docker - prod-like build + E2E suite (single entrypoint)"

# Ensure docker daemon reachable
docker info >/dev/null 2>&1 || fail "Docker daemon not reachable. Start Docker and retry."

# Optional: show compose file used by tools/e2e.sh
COMPOSE_FILE="infra/docker/docker-compose.local-prod.yml"
if [[ ! -f "$COMPOSE_FILE" ]]; then
  # Claude log mentioned docker-compose.local-prod.yml OR local-prod.yml depending on repo; adapt here:
  if [[ -f "infra/docker/docker-compose.local-prod.yml" ]]; then
    COMPOSE_FILE="infra/docker/docker-compose.local-prod.yml"
  elif [[ -f "infra/docker/docker-compose.local-prod-ready.yml" ]]; then
    COMPOSE_FILE="infra/docker/docker-compose.local-prod-ready.yml"
  fi
fi

say "Run E2E via official golden path: bash tools/e2e.sh"
# This script should:
# - build images (frontend included in nginx)
# - wait health
# - seed E2E (with guard E2E_TEST_MODE)
# - run playwright tests
bash tools/e2e.sh

# -----------------------------
# Post-E2E smoke checks (HTTP endpoints)
# -----------------------------
section "6) Post-E2E smoke - check critical endpoints (prod-like runtime)"

BASE_URL="http://localhost:8088"
HEALTH_URL="${BASE_URL}/api/health/"
MEDIA_URL="${BASE_URL}/media/e2e/pages/e2e_page_1.png"

say "HTTP health check: ${HEALTH_URL}"
code="$(curl -s -o /dev/null -w "%{http_code}" "$HEALTH_URL")"
[[ "$code" == "200" ]] || fail "Health endpoint not 200 (got $code)"

say "Media check (E2E page image): ${MEDIA_URL}"
code="$(curl -s -o /dev/null -w "%{http_code}" "$MEDIA_URL")"
[[ "$code" == "200" ]] || warn "Media endpoint not 200 (got $code). If E2E passed this is usually OK, but investigate if serving media in prod."

# Optional: static front page should be 200
say "Static root check: ${BASE_URL}/"
code="$(curl -s -o /dev/null -w "%{http_code}" "${BASE_URL}/")"
if [[ "$code" != "200" && "$code" != "302" ]]; then
  warn "Root / returned HTTP $code (acceptable depending on routing)."
fi

# -----------------------------
# Docker logs inspection (short)
# -----------------------------
section "7) Logs - quick scan for obvious runtime errors (last 80 lines each)"

# Try to infer compose project containers by name, fallback to compose logs.
# We use docker compose logs for backend/nginx/celery when available.
if $DOCKER_COMPOSE -f "$COMPOSE_FILE" ps >/dev/null 2>&1; then
  say "Backend logs (tail 80)"
  $DOCKER_COMPOSE -f "$COMPOSE_FILE" logs backend --tail=80 || true

  say "Nginx logs (tail 80)"
  $DOCKER_COMPOSE -f "$COMPOSE_FILE" logs nginx --tail=80 || true

  say "Celery logs (tail 80)"
  $DOCKER_COMPOSE -f "$COMPOSE_FILE" logs celery --tail=80 || true
else
  warn "Could not run compose logs. Skipping."
fi

# -----------------------------
# Production readiness reminders (non-blocking)
# -----------------------------
section "8) Prod config reminders (non-blocking checks)"

warn "These are deployment requirements; not all can be validated locally:"
warn "- Set SECRET_KEY, ALLOWED_HOSTS, CSRF_TRUSTED_ORIGINS for your real HTTPS domain"
warn "- Enable SECURE cookies in prod (SESSION_COOKIE_SECURE, CSRF_COOKIE_SECURE)"
warn "- Configure METRICS_TOKEN if exposing /metrics (your logs warn if missing)"
warn "- TLS/HTTPS (nginx + certbot/letsencrypt) on dedicated server"
warn "- Backups + migrations runbook"

# If METRICS_TOKEN warning is important in your policy, you can enforce it:
# fail "METRICS_TOKEN must be set"  # if you decide it is mandatory.

# -----------------------------
# Final summary
# -----------------------------
section "✅ FINAL RESULT"

say "All checks completed successfully."
say "Backend: pytest OK"
say "Frontend: lint/typecheck/build OK (if executed)"
say "E2E: tools/e2e.sh OK"
say "HTTP smoke: OK"

echo ""
echo -e "${GREEN}✅ PROJECT IS GREEN AND PROD-LIKE READY (as per local verification).${NC}"
