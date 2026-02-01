#!/usr/bin/env bash
set -euo pipefail

# ============================================================
# Korrigo - PROD Audit Harness (P1)
# Source of truth:
# - Use backend/venv if present (or fallback venv)
# - Run proof_imports.sh and proof_all.sh via bash
# - Record logs + STATUS.tsv + SUMMARY.txt
# - allow-fail steps must never terminate the script
# ============================================================

# ---------- helpers ----------
ts() { date +"%Y-%m-%d_%H-%M-%S"; }
bold() { printf "\033[1m%s\033[0m\n" "$*"; }
warn() { printf "\033[33mWARN:\033[0m %s\n" "$*" >&2; }
err()  { printf "\033[31mERROR:\033[0m %s\n" "$*" >&2; }

ROOT_DIR="$(pwd)"
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

# allow-fail runner: must NEVER exit the whole script
run_cmd_allow_fail() {
  local step="$1"; shift
  local title="$1"; shift
  local logfile="$1"; shift

  bold "==> ${step} — ${title} (allow-fail)"
  echo "==> ${step} — ${title} (allow-fail)" >> "$SUMMARY_FILE"

  set +e
  (
    set +e
    echo "COMMAND: $*"
    echo "PWD: $(pwd)"
    echo "DATE: $(date -Is)"
    echo "------------------------------------------------------------"
    "$@"
    code=$?
    echo
    echo "EXIT_CODE: ${code}"
    exit "${code}"
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

# ---------- 0) Git sanity ----------
run_cmd "0.1" "Git sanity" "${OUT_DIR}/0.1_git_sanity.log" \
  bash -lc 'git rev-parse --is-inside-work-tree && git remote -v && git rev-parse HEAD'

# ---------- 1) Inventory (minimal) ----------
run_cmd "1.1" "Top-level files (maxdepth=2)" "${OUT_DIR}/1.1_inventory_files.log" \
  bash -lc "find . -maxdepth 2 -type f | sed 's|^\./||' | sort"

# ---------- 2) Detect backend venv ----------
VENV_SELECTED="none"
PY_PATH=""

if [[ -x "${ROOT_DIR}/backend/venv/bin/python" ]]; then
  VENV_SELECTED="backend/venv"
  PY_PATH="${ROOT_DIR}/backend/venv/bin/python"
elif [[ -x "${ROOT_DIR}/venv/bin/python" ]]; then
  VENV_SELECTED="venv"
  PY_PATH="${ROOT_DIR}/venv/bin/python"
else
  warn "No python venv found at backend/venv or venv. Marking steps as FAIL but continuing."
fi

{
  echo "VENV_SELECTED=${VENV_SELECTED}"
  echo "PY=${PY_PATH}"
} | tee "${OUT_DIR}/2.0_detect_venv.log" >> "$SUMMARY_FILE"

if [[ -n "${PY_PATH}" ]]; then
  printf "2.0\tOK\t%s\n" "${OUT_DIR}/2.0_detect_venv.log" >> "$STATUS_FILE"
else
  printf "2.0\tFAIL\t%s\n" "${OUT_DIR}/2.0_detect_venv.log" >> "$STATUS_FILE"
fi

# ---------- 2.0b) Venv fingerprint (minimal) ----------
set +e
{
  echo "VENV_SELECTED=${VENV_SELECTED}"
  echo "PY=${PY_PATH}"
  if [[ -n "${PY_PATH}" ]]; then
    echo "PY_VERSION=$("${PY_PATH}" -V 2>&1)"
    if command -v readlink >/dev/null 2>&1; then
      py_realpath="$(readlink -f "${PY_PATH}" 2>/dev/null || true)"
      echo "PY_REALPATH=${py_realpath}"
    fi
    site_packages="$("${PY_PATH}" -c 'import site; print(site.getsitepackages())' 2>/dev/null || true)"
    echo "SITE_PACKAGES=${site_packages}"
  fi
} > "${OUT_DIR}/2.0b_venv_fingerprint.log" 2>&1
fp_code=$?
set -e

if [[ -n "${PY_PATH}" && $fp_code -eq 0 ]]; then
  printf "2.0b\tOK\t%s\n" "${OUT_DIR}/2.0b_venv_fingerprint.log" >> "$STATUS_FILE"
  echo "[OK] 2.0b — log: ${OUT_DIR}/2.0b_venv_fingerprint.log" >> "$SUMMARY_FILE"
else
  printf "2.0b\tFAIL\t%s\n" "${OUT_DIR}/2.0b_venv_fingerprint.log" >> "$STATUS_FILE"
  echo "[FAIL] 2.0b — log: ${OUT_DIR}/2.0b_venv_fingerprint.log" >> "$SUMMARY_FILE"
fi

# ---------- 2.0c) Proof scripts fingerprint ----------
set +e
{
  if command -v sha256sum >/dev/null 2>&1; then
    if [[ -f "${ROOT_DIR}/scripts/proof_imports.sh" ]]; then
      proof_imports_sha="$(sha256sum "${ROOT_DIR}/scripts/proof_imports.sh" | awk '{print $1}')"
      echo "PROOF_IMPORTS_SHA256=${proof_imports_sha}"
    else
      echo "PROOF_IMPORTS_SHA256=missing"
    fi
    if [[ -f "${ROOT_DIR}/scripts/proof_all.sh" ]]; then
      proof_all_sha="$(sha256sum "${ROOT_DIR}/scripts/proof_all.sh" | awk '{print $1}')"
      echo "PROOF_ALL_SHA256=${proof_all_sha}"
    else
      echo "PROOF_ALL_SHA256=missing"
    fi
  else
    echo "PROOF_IMPORTS_SHA256=sha256sum missing"
    echo "PROOF_ALL_SHA256=sha256sum missing"
  fi
} > "${OUT_DIR}/2.0c_proof_fingerprint.log" 2>&1
fp_code=$?
set -e

if [[ $fp_code -eq 0 ]]; then
  printf "2.0c\tOK\t%s\n" "${OUT_DIR}/2.0c_proof_fingerprint.log" >> "$STATUS_FILE"
  echo "[OK] 2.0c — log: ${OUT_DIR}/2.0c_proof_fingerprint.log" >> "$SUMMARY_FILE"
else
  printf "2.0c\tFAIL\t%s\n" "${OUT_DIR}/2.0c_proof_fingerprint.log" >> "$STATUS_FILE"
  echo "[FAIL] 2.0c — log: ${OUT_DIR}/2.0c_proof_fingerprint.log" >> "$SUMMARY_FILE"
fi

# ---------- 3) Proof scripts (source of truth) ----------
# Always run via bash; do NOT require exec bit.
if [[ -z "${PY_PATH}" ]]; then
  warn "PY_PATH empty. Skipping proof scripts."
  printf "3.1\tFAIL\t%s\n" "PY_PATH empty" >> "$STATUS_FILE"
  echo "[FAIL] 3.1 — PY_PATH empty (skipped)" >> "$SUMMARY_FILE"
  printf "3.2\tFAIL\t%s\n" "PY_PATH empty" >> "$STATUS_FILE"
  echo "[FAIL] 3.2 — PY_PATH empty (skipped)" >> "$SUMMARY_FILE"
else
  if [[ -f "${ROOT_DIR}/scripts/proof_imports.sh" ]]; then
    run_cmd_allow_fail "3.1" "Proof imports (source of truth)" "${OUT_DIR}/3.1_proof_imports.log" \
      bash -lc "PYTHONDONTWRITEBYTECODE=1 PY_BIN='${PY_PATH}' bash ./scripts/proof_imports.sh"
  else
    warn "scripts/proof_imports.sh not found."
    printf "3.1\tFAIL\t%s\n" "scripts/proof_imports.sh missing" >> "$STATUS_FILE"
  fi

  if [[ -f "${ROOT_DIR}/scripts/proof_all.sh" ]]; then
    run_cmd_allow_fail "3.2" "Proof all (LOT1 + LOT2 + postgres marker — source of truth)" "${OUT_DIR}/3.2_proof_all.log" \
      bash -lc "PYTHONDONTWRITEBYTECODE=1 PY_BIN='${PY_PATH}' bash ./scripts/proof_all.sh"
  else
    warn "scripts/proof_all.sh not found."
    printf "3.2\tFAIL\t%s\n" "scripts/proof_all.sh missing" >> "$STATUS_FILE"
  fi
fi

# ---------- 9) Final summary ----------
bold "==================== AUDIT SUMMARY ===================="
echo "Audit output directory: ${OUT_DIR}"
echo
echo "STEP    STATUS  LOG"
echo "----    ------  ---"
cat "$STATUS_FILE" | awk -F'\t' '{printf "%-6s  %-6s  %s\n", $1, $2, $3}' || true
echo
echo "Summary file: ${SUMMARY_FILE}"
echo "Status file:  ${STATUS_FILE}"
