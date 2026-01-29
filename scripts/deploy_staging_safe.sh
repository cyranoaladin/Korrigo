#!/bin/bash
# Deploy staging with safety checks and automatic rollback on failure
# Usage: BASE_URL=https://staging.example.com ./scripts/deploy_staging_safe.sh

set -euo pipefail

TAG="${TAG:-v1.0.0-rc1}"
COMPOSE="${COMPOSE:-infra/docker/docker-compose.staging.yml}"
STACK="korrigo-staging"
TS="$(date -u +%Y%m%dT%H%M%SZ)"
LOGDIR="/tmp/staging_deploy_${TS}"
mkdir -p "$LOGDIR"

log(){ echo "[$(date -u +%H:%M:%S)] $*" | tee -a "$LOGDIR/deploy.log" ; }

log "=== STAGING DEPLOY START ($TAG) ==="
log "Logdir: $LOGDIR"

# 0) Baseline
git fetch --tags | tee -a "$LOGDIR/git_fetch.log"
git checkout "$TAG" 2>&1 | tee -a "$LOGDIR/git_checkout.log"
git rev-parse --short HEAD | tee -a "$LOGDIR/commit.txt"
log "Checked out $(cat "$LOGDIR/commit.txt")"

# 1) Env (no weak defaults)
export METRICS_TOKEN="${METRICS_TOKEN:-$(openssl rand -hex 32)}"
log "METRICS_TOKEN set (length=$(printf "%s" "$METRICS_TOKEN" | wc -c))"

# 2) Stop previous stack (keep volumes by default; adjust if you want clean slate)
log "Stopping existing stack (if any)"
docker compose -f "$COMPOSE" down 2>&1 | tee -a "$LOGDIR/compose_down.log" || true

# 3) Build + Up
log "Building images"
docker compose -f "$COMPOSE" build --no-cache 2>&1 | tee -a "$LOGDIR/build.log"

log "Starting stack"
docker compose -f "$COMPOSE" up -d 2>&1 | tee -a "$LOGDIR/up.log"

# 4) Wait healthy (max 90s)
log "Waiting services healthy (timeout 90s)"
END=$((SECONDS+90))
while [ $SECONDS -lt $END ]; do
  docker compose -f "$COMPOSE" ps 2>&1 | tee -a "$LOGDIR/ps.log" >/dev/null
  # If you have healthchecks on all, you can enforce: no (unhealthy)
  if ! docker compose -f "$COMPOSE" ps | grep -q "unhealthy"; then
    break
  fi
  sleep 3
done

if docker compose -f "$COMPOSE" ps | grep -q "unhealthy"; then
  log "❌ Unhealthy services detected"
  docker compose -f "$COMPOSE" ps | tee -a "$LOGDIR/ps_final.log"
  docker compose -f "$COMPOSE" logs --no-color | tee -a "$LOGDIR/logs_full.log" || true
  log "Rolling back (down)"
  docker compose -f "$COMPOSE" down 2>&1 | tee -a "$LOGDIR/rollback_down.log" || true
  exit 1
fi

log "✅ Stack up & stable"
docker compose -f "$COMPOSE" ps | tee -a "$LOGDIR/ps_final.log"

# 5) Quick health checks (edit base URL if needed)
BASE_URL="${BASE_URL:-https://staging.example.com}"
log "BASE_URL=$BASE_URL"

curl -fsS "$BASE_URL/api/health/" | tee -a "$LOGDIR/health_api.log" >/dev/null
log "✅ Health endpoint OK"

log "=== STAGING DEPLOY DONE ==="
log "Next: run smoke script (scripts/smoke_staging.sh) using same BASE_URL"
log "Artifacts: $LOGDIR"
