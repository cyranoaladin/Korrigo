#!/usr/bin/env bash
set -euo pipefail

# ============================================================
# Korrigo - PROD Audit Harness (P1)
# - Uses existing project venv as SOURCE OF TRUTH:
#     1) backend/venv/bin/python
#     2) venv/bin/python
# - Runs proof harness: proof_imports + proof_all (LOT1/LOT2/postgres marker)
# - Produces logs + STATUS.tsv + SUMMARY.txt under audit_out/<timestamp>/
# ============================================================

# ---------- helpers ----------
ts() { date +"%Y-%m-%d_%H-%M-%S"; }
bold() { printf "\033[1m%s\033[0m\n" "$*"; }
warn() { printf "\033[33mWARN:\033[0m %s\n" "$*" >&2; }
err()  { printf "\033[31mERROR:\033[0m %s\n" "$*" >&2; }

# Prefer repo root if available
ROOT_DIR="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$ROOT_DIR"

OUT_DIR="${ROOT_DIR}/audit_out/$(ts)"
mkdir -p "$OUT_DIR"

SUMMARY_FILE="${OUT_DIR}/SUMMARY.txt"
STATUS_FILE="${OUT_DIR}/STATUS.tsv"   # machine-readable: step\tstatus\tlog
touch "$SUMMARY_FILE" "$STATUS_FILE"

# run_cmd <step_id> <title> <logfile> <command...>
run_cmd() {
  local step="$1"; shift
  local title="$1"; shift
  local logfile="$1"; shift

  bold "==> ${step} — ${title}"
  echo "==> ${step} — ${title}" >> "$SUMMARY_FILE"

  {
    echo "COMMAND: $*"
    echo "PWD: $(pwd)"
    echo "DATE: $(date -Is)"
    echo "------------------------------------------------------------"
    "$@"
    echo
    echo "EXIT_CODE: 0"
  } > "${logfile}" 2>&1

  printf "%s\tOK\t%s\n" "$step" "$logfile" >> "$STATUS_FILE"
  echo "[OK] ${step} — log: ${logfile}" >> "$SUMMARY_FILE"
  echo
}

# run_cmd_allow_fail <step_id> <title> <logfile> <command...>
# MUST NEVER terminate the script, regardless of exit code.
run_cmd_allow_fail() {
  local step="$1"; shift
  local title="$1"; shift
  local logfile="$1"; shift

  bold "==> ${step} — ${title} (allow-fail)"
  echo "==> ${step} — ${title} (allow-fail)" >> "$SUMMARY_FILE"

  set +e
  (
    set +e
    {
      echo "COMMAND: $*"
      echo "PWD: $(pwd)"
      echo "DATE: $(date -Is)"
      echo "------------------------------------------------------------"
      "$@"
      code=$?
      echo
      echo "EXIT_CODE: ${code}"
      exit "${code}"
    }
  ) > "${logfile}" 2>&1
  code=$?
  set -e

  if [[ $code -eq 0 ]]; then
    printf "%s\tOK\t%s\n" "$step" "$logfile" >> "$STATUS_FILE"
    echo "[OK] ${step} — log: ${logfile}" >> "$SUMMARY_FILE"
  else
    printf "%s\tFAIL\t%s\n" "$step" "$logfile" >> "$STATUS_FILE"
    echo "[FAIL] ${step} — exit=$code — log: ${logfile}" >> "$SUMMARY_FILE"
  fi
  echo
  return 0
}

# ---------- pre-flight ----------
run_cmd "0.1" "Git sanity" "${OUT_DIR}/0.1_git_sanity.log" \
  bash -lc 'git rev-parse --is-inside-work-tree && git remote -v && git rev-parse HEAD'

run_cmd_allow_fail "0.2" "System python version" "${OUT_DIR}/0.2_system_python.log" \
  bash -lc 'python --version || true; python3 --version || true'

# ---------- 1) Inventory (light) ----------
run_cmd "1.1" "Top-level files (maxdepth=2)" "${OUT_DIR}/1.1_inventory_files.log" \
  bash -lc "find . -maxdepth 2 -type f | sed 's|^\./||' | sort"

run_cmd_allow_fail "1.2" "Prod-relevant files quick check" "${OUT_DIR}/1.2_inventory_prod_files.log" \
  bash -lc "ls -la | egrep -i 'docker|compose|makefile|pyproject|requirements|manage\.py|wsgi|asgi|settings|nginx|gunicorn|celery|README|LICENSE' || true"

# ---------- 2) Source-of-truth venv selection ----------
run_cmd "2.0" "Detect source-of-truth venv (backend/venv preferred)" "${OUT_DIR}/2.0_detect_venv.log" \
  bash -lc "cd \"${ROOT_DIR}\" && \
    if [[ -x \"${ROOT_DIR}/backend/venv/bin/python\" ]]; then \
      echo 'VENV_SELECTED=backend/venv'; \
      echo 'PY=${ROOT_DIR}/backend/venv/bin/python'; \
    elif [[ -x \"${ROOT_DIR}/venv/bin/python\" ]]; then \
      echo 'VENV_SELECTED=venv'; \
      echo 'PY=${ROOT_DIR}/venv/bin/python'; \
    else \
      echo 'ERROR: no venv python found. Expected ./backend/venv/bin/python or ./venv/bin/python' >&2; \
      exit 1; \
    fi"

# Parse selection from log for subsequent steps (no fragile env coupling)
VENV_SELECTED="$(grep -E '^VENV_SELECTED=' "${OUT_DIR}/2.0_detect_venv.log" | tail -n 1 | cut -d= -f2 || true)"
PY_PATH="$(grep -E '^PY=' "${OUT_DIR}/2.0_detect_venv.log" | tail -n 1 | cut -d= -f2 || true)"

if [[ -z "${VENV_SELECTED}" || -z "${PY_PATH}" || ! -x "${PY_PATH}" ]]; then
  err "Venv detection failed. See ${OUT_DIR}/2.0_detect_venv.log"
  printf "2.0\tFAIL\t%s\n" "${OUT_DIR}/2.0_detect_venv.log" >> "$STATUS_FILE"
  exit 1
fi

# Log selection in SUMMARY for proof readability
{
  echo "VENV_SELECTED=${VENV_SELECTED}"
  echo "PY=${PY_PATH}"
} >> "$SUMMARY_FILE"

# Extra environment fingerprint (allow-fail)
run_cmd_allow_fail "2.0b" "Venv python + pip freeze (fingerprint)" "${OUT_DIR}/2.0b_venv_fingerprint.log" \
  bash -lc "\"${PY_PATH}\" --version && \"${PY_PATH}\" -m pip --version && \"${PY_PATH}\" -m pip freeze | sed -n '1,120p'"

# ---------- 3) Proof harness (SOURCE OF TRUTH) ----------
if [[ ! -f "${ROOT_DIR}/scripts/proof_imports.sh" ]]; then
  err "Missing scripts/proof_imports.sh (required)"
  printf "2.1\tFAIL\tmissing scripts/proof_imports.sh\n" >> "$STATUS_FILE"
  exit 1
fi

if [[ ! -f "${ROOT_DIR}/scripts/proof_all.sh" ]]; then
  err "Missing scripts/proof_all.sh (required)"
  printf "2.2\tFAIL\tmissing scripts/proof_all.sh\n" >> "$STATUS_FILE"
  exit 1
fi

# Ensure proof scripts use same venv by exporting PY_BIN if they support it (non-breaking)
export PYTHONDONTWRITEBYTECODE=1
export PY_BIN="${PY_PATH}"

run_cmd "2.1" "Proof imports (Django setup + DRF imports)" "${OUT_DIR}/2.1_proof_imports.log" \
  bash -lc "PYTHONDONTWRITEBYTECODE=1 PY_BIN='${PY_PATH}' bash ./scripts/proof_imports.sh"

run_cmd_allow_fail "2.2" "Proof all (imports -> LOT1 -> LOT2 -> postgres marker)" "${OUT_DIR}/2.2_proof_all.log" \
  bash -lc "PYTHONDONTWRITEBYTECODE=1 PY_BIN='${PY_PATH}' bash ./scripts/proof_all.sh"

# ---------- 4) Optional tools (SKIP if not installed) ----------
# Do NOT install anything. Only run if available.
run_cmd_allow_fail "3.1" "pip-audit (skip if unavailable)" "${OUT_DIR}/3.1_pip_audit.log" \
  bash -lc "\"${PY_PATH}\" -m pip_audit >/dev/null 2>&1 && \"${PY_PATH}\" -m pip_audit || echo 'SKIP: pip_audit not installed'"

run_cmd_allow_fail "3.2" "ruff check (skip if unavailable)" "${OUT_DIR}/3.2_ruff_check.log" \
  bash -lc "\"${PY_PATH}\" -m ruff --version >/dev/null 2>&1 && \"${PY_PATH}\" -m ruff check . || echo 'SKIP: ruff not installed'"

run_cmd_allow_fail "3.3" "mypy (skip if unavailable)" "${OUT_DIR}/3.3_mypy.log" \
  bash -lc "\"${PY_PATH}\" -m mypy --version >/dev/null 2>&1 && \"${PY_PATH}\" -m mypy . || echo 'SKIP: mypy not installed'"

# ---------- 9) Final summary ----------
bold "==================== AUDIT SUMMARY (P1) ===================="
echo "Audit output directory: ${OUT_DIR}"
echo

{
  echo "STEP    STATUS  LOG"
  echo "----    ------  ---"
  awk -F'\t' '{ printf "%-7s %-7s %s\n", $1, $2, $3 }' "$STATUS_FILE"
} | tee -a "$SUMMARY_FILE"

echo >> "$SUMMARY_FILE"
echo "Done. See logs in: ${OUT_DIR}" >> "$SUMMARY_FILE"
