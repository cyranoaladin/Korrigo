#!/usr/bin/env bash
set -euo pipefail

# ==========================================
# Korrigo — Release Gate "one-shot" runner
# Build/Boot/Migrate/Seed/E2E/Tests + logs
# Adapted for Viatique/Korrigo project
# ==========================================

# ---- Config (adjust if needed)
# Use current directory if ROOT not set (for CI compatibility)
ROOT="${ROOT:-$(pwd)}"
COMPOSE_FILE="${COMPOSE_FILE:-infra/docker/docker-compose.local-prod.yml}"
NGINX_BASE_URL="${NGINX_BASE_URL:-http://localhost:8088}"
BACKEND_SVC="${BACKEND_SVC:-backend}"
LOG_DIR="${LOG_DIR:-/tmp/release_gate_$(date -u +%Y%m%dT%H%M%SZ)}"

# Optional env vars (recommended for "no warnings")
export DJANGO_ENV="${DJANGO_ENV:-production}"
export DEBUG="${DEBUG:-False}"
export METRICS_TOKEN="${METRICS_TOKEN:-}"  # empty => public metrics; set to strong secret in real prod
export ADMIN_PASSWORD="${ADMIN_PASSWORD:-}"     # if empty, seed should generate/randomize
export TEACHER_PASSWORD="${TEACHER_PASSWORD:-}" # if empty, seed should generate/randomize

# Test credentials (for E2E validation only; reset after seed)
TEST_PROF_PASSWORD="${TEST_PROF_PASSWORD:-prof}"

# ---- Helpers
ts() { date -u +"%Y-%m-%dT%H:%M:%SZ"; }
log() { echo "[$(ts)] $*"; }
run() { log "+ $*"; "$@"; }
run_logged() {
  local name="$1"; shift
  local out="${LOG_DIR}/${name}.log"
  log "+ $*  (logging -> $out)"
  # pipefail is already on; tee preserves exit code via PIPESTATUS[0]
  ( "$@" ) 2>&1 | tee "$out"
  test "${PIPESTATUS[0]}" -eq 0
}
fail() { echo "[$(ts)] ERROR: $*" >&2; exit 1; }

# ---- Preflight
mkdir -p "$LOG_DIR"
cd "$ROOT"

log "======================================"
log "Korrigo Release Gate — One-Shot Runner"
log "======================================"
log "Release Gate logs dir: $LOG_DIR"
log "ROOT=$ROOT"
log "COMPOSE_FILE=$COMPOSE_FILE"
log "BASE_URL=$NGINX_BASE_URL"

command -v docker >/dev/null || fail "docker not found"
docker compose version >/dev/null || fail "docker compose not available"
command -v jq >/dev/null || fail "jq not found (required for E2E tests)"

# ---- Ensure clean slate
log "Phase 0: Clean environment"
run_logged "00_compose_down" docker compose -f "$COMPOSE_FILE" down -v --remove-orphans

# ---- A) Build (no-cache) - strict
log "Phase A: Build (no-cache)"
run_logged "01_build_nocache" docker compose -f "$COMPOSE_FILE" build --no-cache

# ---- B) Boot stack
log "Phase B: Boot & Stability"
run_logged "02_up" docker compose -f "$COMPOSE_FILE" up -d
run_logged "03_ps_initial" docker compose -f "$COMPOSE_FILE" ps

# Wait for health endpoints (max 120s)
log "Waiting for /api/health/ (max 120s)…"
run_logged "04_wait_health" bash -c "
  set -euo pipefail
  for i in {1..120}; do
    code=\$(curl -s -o /dev/null -w '%{http_code}' '${NGINX_BASE_URL}/api/health/' || true)
    if [ \"\$code\" = \"200\" ]; then
      echo 'health: 200 OK'
      exit 0
    fi
    sleep 1
  done
  echo 'health: timeout'
  exit 1
"

log "Waiting for /metrics (max 120s)…"
run_logged "05_wait_metrics" bash -c "
  set -euo pipefail
  for i in {1..120}; do
    code=\$(curl -s -o /dev/null -w '%{http_code}' '${NGINX_BASE_URL}/metrics' || true)
    if [ \"\$code\" = \"200\" ]; then
      echo 'metrics: 200 OK'
      exit 0
    fi
    sleep 1
  done
  echo 'metrics: timeout'
  exit 1
"

# Stability: 3 minutes, no restarts
log "Stability check: 180s (no restarts expected)…"
run_logged "06_stability_180s" bash -c "
  set -euo pipefail
  before=\$(docker compose -f '$COMPOSE_FILE' ps --format json 2>/dev/null | jq -r '.[] | \"\(.Name) \(.Status)\"' | sort || docker compose -f '$COMPOSE_FILE' ps)
  echo '--- status(before) ---'
  echo \"\$before\"

  sleep 180

  after=\$(docker compose -f '$COMPOSE_FILE' ps --format json 2>/dev/null | jq -r '.[] | \"\(.Name) \(.Status)\"' | sort || docker compose -f '$COMPOSE_FILE' ps)
  echo '--- status(after) ---'
  echo \"\$after\"

  # Check for 'Restarting' or 'Exited' in status
  if echo \"\$after\" | grep -E '(Restarting|Exited)'; then
    echo 'ERROR: Some containers restarted or exited!'
    exit 1
  fi

  echo 'OK: no restarts detected, all containers stable.'
"

# ---- C) Migrations
log "Phase C: Migrations"
run_logged "07_migrate" docker compose -f "$COMPOSE_FILE" exec -T "$BACKEND_SVC" python manage.py migrate --noinput

# ---- D) Seed (idempotent x2)
log "Phase D: Seed (idempotent x2)"
run_logged "08_seed_run1" docker compose -f "$COMPOSE_FILE" exec -T "$BACKEND_SVC" python seed_prod.py
run_logged "09_seed_run2" docker compose -f "$COMPOSE_FILE" exec -T "$BACKEND_SVC" python seed_prod.py

# Reset prof1 password for E2E tests
log "Setting prof1 password for E2E tests..."
run_logged "10_reset_prof_password" docker compose -f "$COMPOSE_FILE" exec -T "$BACKEND_SVC" python manage.py shell -c "
from django.contrib.auth import get_user_model
User = get_user_model()
prof = User.objects.get(username='prof1')
prof.set_password('$TEST_PROF_PASSWORD')
prof.save()
print('✓ prof1 password set for E2E tests')
"

# DB sanity check with pages_images validation
log "DB sanity check..."
run_logged "11_db_sanity" docker compose -f "$COMPOSE_FILE" exec -T "$BACKEND_SVC" python manage.py shell -c "
from exams.models import Exam, Copy
from django.contrib.auth import get_user_model
U=get_user_model()
print('users:', U.objects.count())
print('exams:', Exam.objects.count())
print('copies total:', Copy.objects.count())
print('copies READY:', Copy.objects.filter(status='READY').count())
print('copies GRADED:', Copy.objects.filter(status='GRADED').count())
print()
print('=== READY Copies Validation (P0: pages > 0) ===')
for c in Copy.objects.filter(status='READY').order_by('id')[:5]:
    b=list(c.booklets.all())
    pages=sum((len(x.pages_images or []) for x in b))
    print(f'READY {c.id} {c.anonymous_id}: booklets={len(b)}, pages={pages}')
    if pages == 0:
        print('❌ CRITICAL: Copy has 0 pages!')
        exit(1)
print('✓ All READY copies have pages > 0')
"

# ---- E) E2E workflow (3 runs) — Django session auth with CSRF
log "Phase E: E2E Workflow (3 runs)"
run_logged "12_e2e_3runs" bash -c "
set -euo pipefail
base='$NGINX_BASE_URL'
cookies='/tmp/rg_cookies.txt'

# Helper: login and get CSRF token
login() {
  # Get initial CSRF token
  curl -s -c \"\$cookies\" \"\$base/api/exams/\" > /dev/null
  csrf=\$(grep csrftoken \"\$cookies\" | awk '{print \$7}')

  # Login
  local user=\"\$1\" pass=\"\$2\"
  curl -s -b \"\$cookies\" -c \"\$cookies\" -X POST \"\$base/api/login/\" \\
    -H 'Content-Type: application/json' \\
    -H \"X-CSRFToken: \$csrf\" \\
    -H \"Referer: \$base/\" \\
    -d \"{\\\"username\\\":\\\"\$user\\\",\\\"password\\\":\\\"\$pass\\\"}\" > /dev/null

  # Update CSRF token after login
  csrf=\$(grep csrftoken \"\$cookies\" | awk '{print \$7}')
  echo \"\$csrf\"
}

# Login once
csrf=\$(login prof1 '$TEST_PROF_PASSWORD')
[ -n \"\$csrf\" ] || { echo 'Login failed: no CSRF token'; exit 1; }
echo \"✓ Logged in, CSRF token obtained\"

# Get exam ID
exam_id=\$(curl -s -b \"\$cookies\" \"\$base/api/exams/\" | jq -r '.results[0].id')
[ \"\$exam_id\" != \"null\" ] && [ -n \"\$exam_id\" ] || { echo 'No exam found'; exit 1; }
echo \"✓ Exam ID: \$exam_id\"

for run in 1 2 3; do
  echo \"\"
  echo \"========================================\"
  echo \"E2E RUN \$run/3\"
  echo \"========================================\"

  # Get a READY copy
  copy_id=\$(curl -s -b \"\$cookies\" \"\$base/api/exams/\$exam_id/copies/\" | jq -r '.results[] | select(.status==\"READY\") | .id' | head -1)
  [ \"\$copy_id\" != \"null\" ] && [ -n \"\$copy_id\" ] || { echo 'No READY copy found'; exit 1; }
  echo \"1️⃣  Found READY copy: \$copy_id\"

  # Lock copy
  lock_resp=\$(curl -s -b \"\$cookies\" -X POST \"\$base/api/grading/copies/\$copy_id/lock/\" \\
    -H \"X-CSRFToken: \$csrf\" \\
    -H 'Content-Type: application/json' \\
    -d '{}' \\
    -w '\nHTTP_STATUS:%{http_code}')

  lock_code=\$(echo \"\$lock_resp\" | grep 'HTTP_STATUS' | cut -d: -f2)
  [ \"\$lock_code\" = \"200\" ] || [ \"\$lock_code\" = \"201\" ] || { echo \"❌ Lock failed (HTTP \$lock_code)\"; echo \"\$lock_resp\"; exit 1; }

  lock_token=\$(echo \"\$lock_resp\" | sed '\$d' | jq -r '.token')
  [ -n \"\$lock_token\" ] && [ \"\$lock_token\" != \"null\" ] || { echo '❌ No lock token'; exit 1; }
  echo \"2️⃣  Copy locked (HTTP \$lock_code), token: \${lock_token:0:8}...\"

  # POST annotation (bounding box format: x, y, w, h normalized [0,1])
  ann_resp=\$(curl -s -b \"\$cookies\" -X POST \"\$base/api/grading/copies/\$copy_id/annotations/\" \\
    -H 'Content-Type: application/json' \\
    -H \"X-CSRFToken: \$csrf\" \\
    -H \"X-Lock-Token: \$lock_token\" \\
    -d '{
      \"page_index\": 0,
      \"x\": 0.1,
      \"y\": 0.2,
      \"w\": 0.3,
      \"h\": 0.05,
      \"type\": \"COMMENT\",
      \"content\": \"Test annotation from E2E\"
    }' \\
    -w '\nHTTP_STATUS:%{http_code}')

  ann_code=\$(echo \"\$ann_resp\" | grep 'HTTP_STATUS' | cut -d: -f2)
  [ \"\$ann_code\" = \"200\" ] || [ \"\$ann_code\" = \"201\" ] || { echo \"❌ Annotation POST failed (HTTP \$ann_code)\"; echo \"\$ann_resp\"; exit 1; }
  echo \"3️⃣  Annotation created (HTTP \$ann_code) ← P0 FIX VERIFIED ✅\"

  # GET annotations
  get_resp=\$(curl -s -b \"\$cookies\" \"\$base/api/grading/copies/\$copy_id/annotations/\" \\
    -w '\nHTTP_STATUS:%{http_code}')

  get_code=\$(echo \"\$get_resp\" | grep 'HTTP_STATUS' | cut -d: -f2)
  [ \"\$get_code\" = \"200\" ] || { echo \"❌ Annotation GET failed (HTTP \$get_code)\"; exit 1; }

  ann_count=\$(echo \"\$get_resp\" | sed '\$d' | jq -r 'if type==\"array\" then length elif .results then (.results | length) else 0 end')
  [ \"\$ann_count\" != \"0\" ] || { echo '❌ Annotation count is 0'; exit 1; }
  echo \"4️⃣  GET annotations (HTTP \$get_code) - \$ann_count annotations found\"

  # Release lock
  unlock_resp=\$(curl -s -b \"\$cookies\" -X DELETE \"\$base/api/grading/copies/\$copy_id/lock/release/\" \\
    -H \"X-CSRFToken: \$csrf\" \\
    -H \"X-Lock-Token: \$lock_token\" \\
    -w '\nHTTP_STATUS:%{http_code}')

  unlock_code=\$(echo \"\$unlock_resp\" | grep 'HTTP_STATUS' | cut -d: -f2)
  [ \"\$unlock_code\" = \"200\" ] || [ \"\$unlock_code\" = \"204\" ] || { echo \"❌ Unlock failed (HTTP \$unlock_code)\"; exit 1; }
  echo \"5️⃣  Lock released (HTTP \$unlock_code)\"

  # Reset copy status for next run
  docker compose -f '$COMPOSE_FILE' exec -T '$BACKEND_SVC' python manage.py shell -c \"
from exams.models import Copy
from grading.models import CopyLock
CopyLock.objects.all().delete()
Copy.objects.filter(status='LOCKED').update(status='READY')
\" > /dev/null 2>&1

  echo \"✅ E2E RUN \$run/3 COMPLETE\"
done

echo \"\"
echo \"========================================\"
echo \"✅ E2E: 3/3 RUNS PASSED\"
echo \"========================================\"
"

# ---- F) Backend tests (0 fail, 0 error, 0 skipped)
log "Phase F: Backend Tests"
run_logged "13_pytest_full" docker compose -f "$COMPOSE_FILE" exec -T "$BACKEND_SVC" pytest -v --tb=short

# Extract failing test nodeids if any failures detected
PYTEST_LOG="$LOG_DIR/13_pytest_full.log"
if [ -f "$PYTEST_LOG" ]; then
  # Only match actual pytest failures (lines starting with FAILED/ERROR)
  if grep -qE '^FAILED |^ERROR ' "$PYTEST_LOG"; then
    log "❌ Pytest failures detected. Extracting failing nodeids..."
    grep -E '^(FAILED|ERROR) ' "$PYTEST_LOG" \
      | sed -E 's/^(FAILED|ERROR) +//' \
      | tee "$LOG_DIR/13_pytest_failing_tests.txt"

    log "❌ RELEASE GATE FAILED: Tests have failures"
    log "   Failing tests saved to: $LOG_DIR/13_pytest_failing_tests.txt"
    log "   Review logs: $LOG_DIR/13_pytest_full.log"
    exit 1
  fi

  # Check for skipped tests in pytest summary (zero-tolerance)
  if grep -qE '=.*\d+ skipped' "$PYTEST_LOG"; then
    log "❌ RELEASE GATE FAILED: Tests have skipped tests (zero-tolerance)"
    grep -E '=.*skipped' "$PYTEST_LOG" | tee "$LOG_DIR/13_pytest_skipped.txt"
    exit 1
  fi
fi

# ---- Logs capture (compose + service logs)
log "Phase G: Logs Capture"
run_logged "14_compose_logs" docker compose -f "$COMPOSE_FILE" logs --no-color
run_logged "15_backend_logs_tail" docker compose -f "$COMPOSE_FILE" logs --no-color --tail=500 "$BACKEND_SVC"
run_logged "16_ps_final" docker compose -f "$COMPOSE_FILE" ps

# ---- Validation summary from logs
log "Phase H: Validation Summary"
run_logged "17_validation_summary" bash -c "
set -euo pipefail

echo \"========================================\"
echo \"VALIDATION SUMMARY\"
echo \"========================================\"
echo \"\"

# Count test results
pytest_log='$LOG_DIR/13_pytest_full.log'
if [ -f \"\$pytest_log\" ]; then
  echo \"=== Test Results ===\"
  grep -E '===.*passed' \"\$pytest_log\" | tail -1 || echo 'Test summary not found'

  # Check for failures/errors/skipped (only match actual pytest output)
  if grep -qE '^FAILED |^ERROR ' \"\$pytest_log\"; then
    echo \"❌ FAILURES/ERRORS DETECTED IN TESTS\"
    grep -E '^(FAILED|ERROR) ' \"\$pytest_log\" | head -20 || true
  fi

  if grep -qE '=.*\d+ skipped' \"\$pytest_log\"; then
    echo \"⚠️  SKIPPED TESTS DETECTED\"
    grep -E '=.*skipped' \"\$pytest_log\" || true
  fi
  echo \"\"
fi

# Check seed logs for pages validation
seed_log='$LOG_DIR/08_seed_run1.log'
if [ -f \"\$seed_log\" ]; then
  echo \"=== Seed Validation (Pages > 0) ===\"
  grep -E 'Booklets.*Pages' \"\$seed_log\" || echo 'Pages info not found'
  echo \"\"
fi

# Check for warnings/errors in backend logs (permissive check)
backend_log='$LOG_DIR/15_backend_logs_tail.log'
if [ -f \"\$backend_log\" ]; then
  echo \"=== Backend Log Health Check ===\"
  # Count critical errors (exclude known acceptable warnings)
  error_count=\$(grep -iE 'error|critical|exception' \"\$backend_log\" | grep -viE 'METRICS_TOKEN|DEBUG.*False' | wc -l || echo 0)

  if [ \"\$error_count\" -gt 0 ]; then
    echo \"⚠️  Found \$error_count potential error lines (review logs)\"
  else
    echo \"✓ No critical errors detected\"
  fi
  echo \"\"
fi

echo \"========================================\"
echo \"ARTIFACTS LOCATION: $LOG_DIR\"
echo \"========================================\"
"

# ---- Final verdict
log ""
log "=========================================="
log "✅ RELEASE GATE ONE-SHOT COMPLETED"
log "=========================================="
log "Artifacts in: $LOG_DIR"
log ""
log "Next steps:"
log "1. Review logs in $LOG_DIR"
log "2. Verify pytest: 0 failed, 0 skipped"
log "3. Verify E2E: 3/3 runs passed"
log "4. Verify seed: all copies have pages > 0"
log "5. Attach $LOG_DIR as evidence in PR/report"
log ""
log "Tip: grep '✅\|❌' $LOG_DIR/*.log for quick validation status"
