#!/bin/bash
# Staging Validation Wrapper - Audit-proof execution
# Usage: bash scripts/run_staging_validation.sh
# Description: Orchestrates deploy + smoke with full logging and pre-flight checks

set -euo pipefail  # Fail-fast + pipefail
set +x             # Disable tracing (secrets protection)

# ====================================
# LOCK (éviter runs concurrents)
# ====================================

LOCK=/tmp/staging_checklist.lock
exec 8>"$LOCK"
if ! flock -n 8; then
  echo "❌ Un autre run staging est déjà en cours (lock: $LOCK)"
  echo "➡️  Diagnostics: ls -l $LOCK ; ps aux | grep [r]un_staging_validation"
  exit 1
fi

# ====================================
# PRE-RUN VALIDATION
# ====================================

cd "$(dirname "$0")/.." || exit 1  # Repo root

echo "=== Git status check ==="
if [ -n "$(git status --porcelain)" ]; then
  echo "❌ Working tree not clean. Commit/stash changes before running."
  git status --porcelain
  exit 1
fi
echo "✅ Working tree clean"
git rev-parse --short HEAD
git log --oneline -1
echo ""

# Pre-flight tools
echo "=== Tools check ==="
command -v docker >/dev/null && docker --version
docker compose version  # Fail-fast if not available
command -v flock  >/dev/null && echo "flock: OK"
command -v jq     >/dev/null && jq --version
command -v curl   >/dev/null && curl --version
command -v openssl >/dev/null && openssl version
echo ""

# ====================================
# CREATE LOGS DIRECTORY
# ====================================

ts="$(date -u +%Y%m%dT%H%M%SZ)"
runlog="/tmp/staging_run_$ts"

# Strict permissions (audit & secrets protection)
umask 077
mkdir -p "$runlog"
chmod 700 "$runlog"

echo "Logs directory created: $runlog (mode 700)"
echo ""

# Context dump (audit-ready)
{
  echo "=== Run Context ==="
  date -u
  echo "Git commit: $(git rev-parse HEAD)"
  echo "Git status:"
  git status --porcelain
  echo ""
  echo "=== Tools versions ==="
  docker --version
  docker compose version
  flock --version 2>&1 | head -1 || echo "flock: available"
  jq --version
  curl --version | head -1
  openssl version
} > "$runlog/context.txt" 2>&1

# ====================================
# SECRETS (zéro inline, zéro trace)
# ====================================

set +x  # Redundant but explicit (no tracing)

export BASE_URL="${BASE_URL:-https://staging.korrigo.example.com}"
export TAG="${TAG:-v1.0.0-rc1}"
export SMOKE_USER="${SMOKE_USER:-prof1}"

if [ -z "${SMOKE_PASS:-}" ]; then
  read -sp "SMOKE_PASS: " SMOKE_PASS; echo
  export SMOKE_PASS
fi

if [ -z "${METRICS_TOKEN:-}" ]; then
  export METRICS_TOKEN="$(openssl rand -hex 32)"
fi

echo "✅ Secrets configured (masked)"
echo "   BASE_URL: $BASE_URL"
echo "   TAG: $TAG"
echo "   SMOKE_USER: $SMOKE_USER"
echo "   SMOKE_PASS: ********"
echo "   METRICS_TOKEN: <generated>"
echo ""

# ====================================
# PHASE 1: DEPLOY
# ====================================

echo "========================================="
echo "PHASE 1: DEPLOY STAGING"
echo "========================================="
echo ""

if ! bash scripts/deploy_staging_safe.sh 2>&1 | tee "$runlog/deploy.log"; then
  rc=${PIPESTATUS[0]:-1}
  echo ""
  echo "❌ Deploy failed (RC=$rc)"
  echo "Logs: $runlog/deploy.log"
  echo ""
  echo "Rollback command:"
  echo "  docker compose -f infra/docker/docker-compose.staging.yml down"
  echo "  docker compose -f infra/docker/docker-compose.staging.yml up -d --build"
  exit 1
fi

echo ""
echo "✅ Deploy phase completed"
echo ""

# ====================================
# PHASE 2: SMOKE TEST
# ====================================

echo "========================================="
echo "PHASE 2: SMOKE TEST"
echo "========================================="
echo ""

if ! bash scripts/smoke_staging.sh 2>&1 | tee "$runlog/smoke.log"; then
  rc=${PIPESTATUS[0]:-1}
  echo ""
  echo "❌ Smoke test failed (RC=$rc)"
  echo "Logs: $runlog/smoke.log"
  echo ""
  echo "Rollback command:"
  echo "  docker compose -f infra/docker/docker-compose.staging.yml down"
  exit 1
fi

echo ""
echo "✅ Smoke test completed"
echo ""

# ====================================
# SUCCESS SUMMARY
# ====================================

echo "========================================="
echo "✅ STAGING VALIDATION SUCCESS"
echo "========================================="
echo ""
echo "Logs directory: $runlog"
echo ""
echo "📋 Next steps for SRE verdict:"
echo ""
echo "# Copy-paste these commands to share logs:"
echo "tail -50 '$runlog/deploy.log'"
echo "tail -50 '$runlog/smoke.log'"
echo ""
echo "📝 If verdict PASS:"
echo "  1) Fill RELEASE_NOTES_v1.0.0.md"
echo "  2) git tag -a v1.0.0 -m 'Production Release'"
echo "  3) git push origin v1.0.0"
echo ""
echo "🎯 Validation complete at $(date -u +%Y-%m-%dT%H:%M:%SZ)"
