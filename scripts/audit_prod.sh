#!/usr/bin/env bash
set -euo pipefail

# ============================================================
# Korrigo - PROD Audit Harness (Exhaustive)
# - Runs inventory, venv install, security scans, lint/type, tests,
#   DB/Django checks, and produces logs + summary.
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

  # shellcheck disable=SC2068
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

  # Run the command in a subshell so we can safely capture exit code
  # without risking exiting the parent script.
  set +e
  (
    set +e
    # shellcheck disable=SC2068
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

# Detect python
PY_BIN="${PY_BIN:-python3}"
command -v "$PY_BIN" >/dev/null 2>&1 || PY_BIN="python"
command -v "$PY_BIN" >/dev/null 2>&1 || { err "No python found in PATH"; exit 1; }

# ---------- pre-flight ----------
run_cmd "0.1" "Git sanity" "${OUT_DIR}/0.1_git_sanity.log" \
  bash -lc 'git rev-parse --is-inside-work-tree && git remote -v && git rev-parse HEAD'

run_cmd_allow_fail "0.2" "System python version" "${OUT_DIR}/0.2_system_python.log" \
  bash -lc 'python --version || true; python3 --version || true'

# ---------- 1) Inventory ----------
run_cmd "1.1" "Top-level files (maxdepth=2)" "${OUT_DIR}/1.1_inventory_files.log" \
  bash -lc "find . -maxdepth 2 -type f | sed 's|^\./||' | sort"

run_cmd_allow_fail "1.2" "Prod-relevant files quick check" "${OUT_DIR}/1.2_inventory_prod_files.log" \
  bash -lc "ls -la | egrep -i 'docker|compose|makefile|pyproject|requirements|manage\.py|wsgi|asgi|settings|nginx|gunicorn|celery|README|LICENSE' || true"

run_cmd_allow_fail "1.3" "Largest tracked files (top 30)" "${OUT_DIR}/1.3_largest_files.log" \
  bash -lc "git ls-files | xargs -I{} bash -lc 'test -f \"{}\" && echo \"\$(wc -c < \"{}\") {}\"' | sort -nr | head -n 30"

# ---------- 2) venv + deps ----------
run_cmd "2.1" "Create venv .venv" "${OUT_DIR}/2.1_venv_create.log" \
  bash -lc "$PY_BIN -m venv .venv"

# activate venv for subsequent steps via explicit .venv/bin/python & pip
VENV_PY="${ROOT_DIR}/.venv/bin/python"
VENV_PIP="${ROOT_DIR}/.venv/bin/pip"

run_cmd "2.2" "Upgrade pip tooling" "${OUT_DIR}/2.2_pip_upgrade.log" \
  bash -lc "\"$VENV_PY\" -m pip install -U pip wheel setuptools"

# Choose install strategy
INSTALL_MODE="none"
if [[ -f "requirements.txt" ]]; then
  INSTALL_MODE="requirements"
elif [[ -f "pyproject.toml" ]]; then
  INSTALL_MODE="pyproject"
fi

if [[ "$INSTALL_MODE" == "requirements" ]]; then
  run_cmd "2.3" "Install dependencies (requirements.txt)" "${OUT_DIR}/2.3_deps_install.log" \
    bash -lc "\"$VENV_PIP\" install -r requirements.txt"
elif [[ "$INSTALL_MODE" == "pyproject" ]]; then
  run_cmd_allow_fail "2.3" "Install dependencies (pyproject editable)" "${OUT_DIR}/2.3_deps_install.log" \
    bash -lc "\"$VENV_PIP\" install -e ."
else
  warn "No requirements.txt or pyproject.toml found at repo root. Dependency install step marked FAIL."
  printf "2.3\tFAIL\t%s\n" "N/A (no dependency file)" >> "$STATUS_FILE"
  echo "[FAIL] 2.3 — No requirements.txt or pyproject.toml found." >> "$SUMMARY_FILE"
fi

# ---------- 3) Security scanning ----------
run_cmd "3.1" "Install audit tools (pip-audit safety bandit)" "${OUT_DIR}/3.1_install_security_tools.log" \
  bash -lc "\"$VENV_PIP\" install pip-audit safety bandit"

run_cmd_allow_fail "3.2" "pip-audit" "${OUT_DIR}/3.2_pip_audit.log" \
  bash -lc "\"$VENV_PY\" -m pip_audit"

run_cmd_allow_fail "3.3" "safety check" "${OUT_DIR}/3.3_safety_check.log" \
  bash -lc "\"$VENV_PY\" -m safety check"

run_cmd_allow_fail "3.4" "bandit scan (exclude .venv)" "${OUT_DIR}/3.4_bandit.log" \
  bash -lc "\"$VENV_PY\" -m bandit -r . -x ./.venv -q"

# ---------- 4) Secrets scan (lightweight grep) ----------
run_cmd_allow_fail "4.1" "Secrets grep scan" "${OUT_DIR}/4.1_secrets_grep.log" \
  bash -lc "egrep -R --line-number -i \"secret|api[_-]?key|token|password|passwd|private[_-]?key|aws_|stripe|openai|mongodb\\+srv|BEGIN (RSA|OPENSSH) PRIVATE KEY\" . --exclude-dir=.git --exclude-dir=.venv || true"

run_cmd_allow_fail "4.2" ".env / env.example presence" "${OUT_DIR}/4.2_env_presence.log" \
  bash -lc "ls -la | egrep -i '\\.env|env\\.example|dotenv' || true"

# ---------- 5) Quality: ruff + mypy ----------
run_cmd "5.1" "Install quality tools (ruff mypy pytest pytest-cov)" "${OUT_DIR}/5.1_install_quality_tools.log" \
  bash -lc "\"$VENV_PIP\" install ruff mypy pytest pytest-cov"

run_cmd_allow_fail "5.2" "ruff check" "${OUT_DIR}/5.2_ruff_check.log" \
  bash -lc "\"$VENV_PY\" -m ruff check ."

run_cmd_allow_fail "5.3" "ruff format --check" "${OUT_DIR}/5.3_ruff_format_check.log" \
  bash -lc "\"$VENV_PY\" -m ruff format --check ."

run_cmd_allow_fail "5.4" "mypy" "${OUT_DIR}/5.4_mypy.log" \
  bash -lc "\"$VENV_PY\" -m mypy ."

# ---------- 6) Tests + coverage ----------
run_cmd_allow_fail "6.1" "pytest -q" "${OUT_DIR}/6.1_pytest_q.log" \
  bash -lc "\"$VENV_PY\" -m pytest -q"

run_cmd_allow_fail "6.2" "pytest -q --maxfail=1" "${OUT_DIR}/6.2_pytest_maxfail.log" \
  bash -lc "\"$VENV_PY\" -m pytest -q --maxfail=1"

run_cmd_allow_fail "6.3" "pytest coverage (term-missing)" "${OUT_DIR}/6.3_pytest_cov.log" \
  bash -lc "\"$VENV_PY\" -m pytest --cov=. --cov-report=term-missing -q"

# ---------- 7) Django checks (if manage.py exists) ----------
if [[ -f "manage.py" ]]; then
  run_cmd_allow_fail "7.1" "Django check" "${OUT_DIR}/7.1_django_check.log" \
    bash -lc "\"$VENV_PY\" manage.py check"

  run_cmd_allow_fail "7.2" "Django makemigrations --check --dry-run" "${OUT_DIR}/7.2_django_makemigrations_check.log" \
    bash -lc "\"$VENV_PY\" manage.py makemigrations --check --dry-run"

  run_cmd_allow_fail "7.3" "Django showmigrations" "${OUT_DIR}/7.3_django_showmigrations.log" \
    bash -lc "\"$VENV_PY\" manage.py showmigrations"
else
  warn "manage.py not found: skipping Django-specific checks."
  printf "7.1\tSKIP\tmanage.py not found\n" >> "$STATUS_FILE"
  printf "7.2\tSKIP\tmanage.py not found\n" >> "$STATUS_FILE"
  printf "7.3\tSKIP\tmanage.py not found\n" >> "$STATUS_FILE"
fi

# ---------- 8) Docker sanity (if docker files present) ----------
if ls Dockerfile docker-compose*.yml docker-compose*.yaml >/dev/null 2>&1; then
  run_cmd_allow_fail "8.1" "Docker version" "${OUT_DIR}/8.1_docker_version.log" \
    bash -lc "docker --version && docker compose version || true"

  run_cmd_allow_fail "8.2" "docker compose config (best effort)" "${OUT_DIR}/8.2_docker_compose_config.log" \
    bash -lc "for f in docker-compose*.yml docker-compose*.yaml; do echo \"--- $f\"; docker compose -f \"$f\" config >/dev/null && echo \"OK compose config $f\" || echo \"FAIL compose config $f\"; done"
else
  warn "No Dockerfile / docker-compose*.yml found: skipping Docker sanity."
  printf "8.1\tSKIP\tno docker files\n" >> "$STATUS_FILE"
  printf "8.2\tSKIP\tno docker files\n" >> "$STATUS_FILE"
fi

# ---------- 9) Final summary ----------
bold "==================== AUDIT SUMMARY ===================="
echo "Audit output directory: ${OUT_DIR}"
echo

# Print status table nicely
{
  echo "STEP    STATUS  LOG"
  echo "----    ------  ---"
  awk -F'\t' '{ printf "%-7s %-7s %s\n", $1, $2, $3 }' "$STATUS_FILE"
} | tee -a "$SUMMARY_FILE"

echo >> "$SUMMARY_FILE"
echo "Done. See logs in: ${OUT_DIR}" >> "$SUMMARY_FILE"
