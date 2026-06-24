#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -ne 1 ]; then
  echo "Usage: scripts/release/local_release_check.sh <audit-dir>" >&2
  exit 2
fi

ROOT_DIR="$(git rev-parse --show-toplevel)"
AUDIT_DIR="$1"
LOG_DIR="$AUDIT_DIR/logs"
SUMMARY="$AUDIT_DIR/local_release_summary.env"
MANIFEST="$AUDIT_DIR/LOCAL_RELEASE_MANIFEST.md"
VENV_DIR="$ROOT_DIR/.venv-release-check"
BASELINE="1958681b082402e06d0f463e685d8a9895c460c5"

mkdir -p "$LOG_DIR"
chmod 700 "$AUDIT_DIR"
: > "$SUMMARY"

CURRENT_STEP="initialization"
FAILED_STEP=""

write_manifest() {
  local decision="$1"
  local e2e_status="${2:-UNKNOWN}"
  {
    echo "# Korrigo local release manifest"
    echo
    echo "- Date UTC: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
    echo "- Branch: $(git branch --show-current)"
    echo "- HEAD: $(git rev-parse HEAD)"
    echo "- Baseline: $BASELINE"
    echo "- Production preflight: NOT_RUN_BY_SCRIPT"
    echo "- Backup/sync guard: NOT_RUN_BY_SCRIPT"
    echo "- Backend targeted tests: ${BACKEND_TARGETED_STATUS:-UNKNOWN}"
    echo "- Backend full tests: ${BACKEND_FULL_STATUS:-UNKNOWN}"
    echo "- Frontend tests: ${FRONTEND_TEST_STATUS:-UNKNOWN}"
    echo "- Frontend build: ${FRONTEND_BUILD_STATUS:-UNKNOWN}"
    echo "- HMAC source gate: ${HMAC_SOURCE_STATUS:-UNKNOWN}"
    echo "- HMAC dist gate: ${HMAC_DIST_STATUS:-UNKNOWN}"
    echo "- HMAC fail-closed: ${HMAC_FAIL_CLOSED_STATUS:-UNKNOWN}"
    echo "- Email classification: ${EMAIL_CLASSIFICATION_STATUS:-UNKNOWN}"
    echo "- E2E: $e2e_status"
    echo "- Decision: $decision"
  } > "$MANIFEST"
}

fail_step() {
  local step="$1"
  local log_file="$2"
  FAILED_STEP="$step"
  {
    echo "LOCAL_RELEASE_CHECK_STATUS=FAIL"
    echo "FAILED_STEP=$step"
    echo "FAILED_LOG=$log_file"
  } | tee "$SUMMARY"
  write_manifest "LOCAL_RELEASE_BLOCKED_TESTS" "${E2E_STATUS:-UNKNOWN}"
  exit 1
}

read_e2e_status() {
  local status_file="$AUDIT_DIR/local_smoke_e2e/status.txt"
  if [ -f "$status_file" ]; then
    grep "^E2E_STATUS=" "$status_file" | tail -n 1 | cut -d= -f2-
  else
    echo "NO-GO_E2E_NOT_AVAILABLE"
  fi
}

run_step() {
  local name="$1"
  shift
  local log_file="$LOG_DIR/${name}.log"
  CURRENT_STEP="$name"
  echo "STEP_START=$name"
  if "$@" >"$log_file" 2>&1; then
    echo "STEP_PASS=$name"
  else
    echo "STEP_FAIL=$name"
    fail_step "$name" "$log_file"
  fi
}

cleanup() {
  rm -rf "$VENV_DIR"
}
trap cleanup EXIT

cd "$ROOT_DIR"

run_step git_status bash -c 'git status --short --branch && test -z "$(git status --porcelain)"'
run_step git_diff_check git diff --check

run_step hmac_source_gate bash -c 'PII_GATE_PEPPER="test-pepper-not-secret" python scripts/ci/check_frontend_pii_hashes.py frontend/src'
HMAC_SOURCE_STATUS=PASS

if [ -d frontend/dist ]; then
  run_step hmac_dist_prebuild_gate bash -c 'PII_GATE_PEPPER="test-pepper-not-secret" python scripts/ci/check_frontend_pii_hashes.py frontend/dist'
else
  echo "STEP_SKIP=hmac_dist_prebuild_gate reason=frontend_dist_missing"
fi

CURRENT_STEP="hmac_fail_closed"
echo "STEP_START=hmac_fail_closed"
if env -u PII_GATE_PEPPER python scripts/ci/check_frontend_pii_hashes.py frontend/src >"$LOG_DIR/hmac_fail_closed.log" 2>&1; then
  echo "STEP_FAIL=hmac_fail_closed"
  fail_step "hmac_fail_closed" "$LOG_DIR/hmac_fail_closed.log"
fi
if grep -q "PII_GATE_STATUS=FAIL_MISSING_PEPPER" "$LOG_DIR/hmac_fail_closed.log"; then
  echo "STEP_PASS=hmac_fail_closed"
  HMAC_FAIL_CLOSED_STATUS=PASS
else
  echo "STEP_FAIL=hmac_fail_closed"
  fail_step "hmac_fail_closed" "$LOG_DIR/hmac_fail_closed.log"
fi

CURRENT_STEP="email_classification"
echo "STEP_START=email_classification"
python scripts/audit/classify_plain_emails_redacted.py > "$LOG_DIR/email_classification.log" 2>&1 || fail_step "email_classification" "$LOG_DIR/email_classification.log"
if grep -E 'EMAIL_CATEGORY_(SECRET_LIKE|TO_REVIEW|PERSONAL_OR_UNKNOWN)=[1-9]' "$LOG_DIR/email_classification.log" >/dev/null; then
  echo "STEP_FAIL=email_classification"
  fail_step "email_classification" "$LOG_DIR/email_classification.log"
fi
echo "STEP_PASS=email_classification"
EMAIL_CLASSIFICATION_STATUS=PASS

run_step compose_yaml_validation python - <<'PY'
from pathlib import Path
import yaml

data = yaml.safe_load(Path("infra/docker/docker-compose.prod.yml").read_text())
required = {
    "backend": "korrigo-backend:korrigo-direct-f793f0c",
    "celery": "korrigo-backend:korrigo-direct-f793f0c",
    "celery-beat": "korrigo-backend:korrigo-direct-f793f0c",
    "nginx": "korrigo-nginx:korrigo-direct-f793f0c",
    "db": "postgres:15-alpine",
    "redis": "redis:7-alpine",
}
for service, image in required.items():
    actual = data["services"][service].get("image")
    print(f"{service}_IMAGE={actual}")
    if actual != image:
        raise SystemExit(f"unexpected image for {service}")
PY

run_step python_venv_install bash -c 'python3 -m venv .venv-release-check && . .venv-release-check/bin/activate && pip install --upgrade pip && pip install -r backend/requirements-dev.txt'

run_step backend_targeted_lot0 bash -c '. .venv-release-check/bin/activate && pytest -q -p no:cacheprovider backend/core/tests/test_lot0_rgpd_deploy_contract.py'
run_step backend_targeted_seed bash -c '. .venv-release-check/bin/activate && pytest -q -p no:cacheprovider backend/exams/tests/test_seed_initial_exams.py'
BACKEND_TARGETED_STATUS=PASS

run_step backend_full bash -c '. .venv-release-check/bin/activate && cd backend && pytest -q -p no:cacheprovider'
BACKEND_FULL_STATUS=PASS

run_step frontend_install_if_needed bash -c 'cd frontend && if [ ! -d node_modules ]; then npm ci; fi'
run_step frontend_tests bash -c 'cd frontend && npm test -- --run'
FRONTEND_TEST_STATUS=PASS

run_step frontend_build bash -c 'cd frontend && npm run build'
FRONTEND_BUILD_STATUS=PASS

run_step hmac_dist_postbuild_gate bash -c 'PII_GATE_PEPPER="test-pepper-not-secret" python scripts/ci/check_frontend_pii_hashes.py frontend/dist'
HMAC_DIST_STATUS=PASS

run_step e2e_discovery bash -c 'find . -maxdepth 3 -type f \( -name "playwright.config.*" -o -name "cypress.config.*" -o -name "vitest.config.*" \) -print && python - <<PY
import json
from pathlib import Path
for p in [Path("package.json"), Path("frontend/package.json")]:
    if p.exists():
        data = json.loads(p.read_text())
        print(f"PACKAGE={p}")
        for name, cmd in sorted(data.get("scripts", {}).items()):
            if any(k in name.lower() for k in ["e2e", "playwright", "cypress", "test"]):
                print(f"{name}: {cmd}")
PY'

CURRENT_STEP="local_smoke_e2e"
echo "STEP_START=local_smoke_e2e"
if scripts/release/local_smoke_e2e.sh "$AUDIT_DIR" > "$LOG_DIR/local_smoke_e2e.log" 2>&1; then
  echo "STEP_PASS=local_smoke_e2e"
else
  echo "STEP_FAIL=local_smoke_e2e"
  E2E_STATUS="$(read_e2e_status)"
  {
    echo "LOCAL_RELEASE_CHECK_STATUS=FAIL"
    echo "FAILED_STEP=local_smoke_e2e"
    echo "FAILED_LOG=$LOG_DIR/local_smoke_e2e.log"
    echo "E2E_STATUS=$E2E_STATUS"
  } | tee "$SUMMARY"
  write_manifest "LOCAL_RELEASE_BLOCKED_E2E" "$E2E_STATUS"
  exit 1
fi

E2E_STATUS="$(read_e2e_status)"
if [ "$E2E_STATUS" != "PASS_EXISTING_PLAYWRIGHT_OR_CYPRESS" ]; then
  {
    echo "LOCAL_RELEASE_CHECK_STATUS=FAIL"
    echo "FAILED_STEP=local_smoke_e2e"
    echo "E2E_STATUS=$E2E_STATUS"
  } | tee "$SUMMARY"
  write_manifest "LOCAL_RELEASE_BLOCKED_E2E" "$E2E_STATUS"
  exit 1
fi

{
  echo "LOCAL_RELEASE_CHECK_STATUS=PASS"
  echo "E2E_STATUS=$E2E_STATUS"
} | tee "$SUMMARY"
write_manifest "LOCAL_RELEASE_READY_FOR_DIRECT_DEPLOY" "$E2E_STATUS"
echo "LOCAL_RELEASE_CHECK_STATUS=PASS"
