#!/usr/bin/env bash
# run_task.sh - Individual task runner with proof generation
# Version: 3.0 - Final (file-based timeout flag, heredoc execution)
set -euo pipefail

ARG1="${1:-}"
RUN_ID="${RUN_ID:-$(date +%Y%m%d-%H%M%S)-$$}"
ZENFLOW_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"

if [[ -z "${ARG1}" ]]; then
  echo "Usage: $0 <task_id|path/to/task.yaml>" >&2
  echo "Example: RUN_ID=20260131-123456 $0 01-backend-lint-type" >&2
  echo "Example: RUN_ID=20260131-123456 $0 tasks/01-backend-lint-type/task.yaml" >&2
  exit 1
fi

# Backward compatibility: accept either task_id or yaml path
if [[ -f "${ARG1}" ]]; then
  # Argument is a file path (legacy mode)
  TASK_YAML="$(cd "$(dirname "${ARG1}")" && pwd)/$(basename "${ARG1}")"
  TASK_DIR="$(dirname "${TASK_YAML}")"
  TASK_ID="$(basename "${TASK_DIR}")"
elif [[ -f "${ZENFLOW_ROOT}/tasks/${ARG1}/task.yaml" ]]; then
  # Argument is a task_id (new mode)
  TASK_ID="${ARG1}"
  TASK_DIR="${ZENFLOW_ROOT}/tasks/${TASK_ID}"
  TASK_YAML="${TASK_DIR}/task.yaml"
else
  echo "ERROR: Task not found: ${ARG1}" >&2
  echo "  Tried: ${ZENFLOW_ROOT}/tasks/${ARG1}/task.yaml" >&2
  echo "  Tried: ${ARG1}" >&2
  exit 1
fi

if [[ ! -f "${TASK_YAML}" ]]; then
  echo "ERROR: Task YAML not found: ${TASK_YAML}" >&2
  exit 1
fi

# Setup proof directory
PROOF_DIR="${ZENFLOW_ROOT}/.zenflow/proofs/${RUN_ID}/${TASK_ID}"
mkdir -p "${PROOF_DIR}"/{00-meta,10-commands,20-logs,30-artifacts,40-checksums,99-summary}

echo "[$(date -Iseconds)] Starting task ${TASK_ID} (RUN_ID=${RUN_ID})"

# Capture metadata
cat > "${PROOF_DIR}/00-meta/task.json" <<EOF
{
  "task_id": "${TASK_ID}",
  "run_id": "${RUN_ID}",
  "started_at": "$(date -Iseconds)",
  "hostname": "$(hostname)",
  "user": "${USER}",
  "pwd": "$(pwd)"
}
EOF

# Parse task metadata
TIMEOUT_SEC=$(python3 -c "
import sys, yaml
try:
    with open('${TASK_YAML}', 'r') as f:
        doc = yaml.safe_load(f)
    print(doc.get('timeout_sec', 300))
except Exception:
    print(300)
" 2>/dev/null || echo 300)

TITLE=$(python3 -c "
import sys, yaml
try:
    with open('${TASK_YAML}', 'r') as f:
        doc = yaml.safe_load(f)
    print(doc.get('title', '${TASK_ID}'))
except Exception:
    print('${TASK_ID}')
" 2>/dev/null || echo "${TASK_ID}")

# Export environment variables (with shell-safe quoting)
ENV_FILE="${PROOF_DIR}/00-meta/env.sh"
python3 -c "
import sys, yaml, shlex, re
try:
    with open('${TASK_YAML}', 'r') as f:
        doc = yaml.safe_load(f)
    env_vars = doc.get('env', {})
    for k, v in env_vars.items():
        # Validate variable name (prevent injection)
        if not re.match(r'^[A-Za-z_][A-Za-z0-9_]*$', k):
            print(f'# Skipping invalid env var name: {k}', file=sys.stderr)
            continue
        vs = shlex.quote(str(v))
        print(f'export {k}={vs}')
except Exception as e:
    pass
" > "${ENV_FILE}" 2>/dev/null || echo "# No env vars"

# Source environment
source "${ENV_FILE}"

# Export additional context
export TASK_ID RUN_ID ZENFLOW_ROOT PROOF_DIR

# Generate unique COMPOSE_PROJECT_NAME for Docker isolation
export COMPOSE_PROJECT_NAME="zf-${RUN_ID}-${TASK_ID}"

# Helper function to run a command step with heredoc
run_step() {
  local step_name="$1"
  local step_num="${STEP_COUNTER:-0}"
  STEP_COUNTER=$((step_num + 1))

  echo "[$(date -Iseconds)] Step ${step_num}: ${step_name}"

  # Read entire step block from stdin
  local step_file="${PROOF_DIR}/10-commands/step-${step_num}.sh"
  cat > "${step_file}"

  # Save step metadata (JSON-safe)
  local name_json
  name_json=$(python3 -c 'import json,sys; print(json.dumps(sys.argv[1]))' "${step_name}")

  cat > "${PROOF_DIR}/10-commands/step-${step_num}.json" <<STEP_META
{
  "step": ${step_num},
  "name": ${name_json},
  "started_at": "$(date -Iseconds)"
}
STEP_META

  # Execute step with output capture
  local log_file="${PROOF_DIR}/20-logs/step-${step_num}.log"

  set +e
  (
    set -euo pipefail
    cd "${TASK_DIR}"
    bash "${step_file}"
  ) &> "${log_file}"
  local exit_code=$?
  set -e

  # Update step metadata with result
  python3 -c "
import json
meta_file = '${PROOF_DIR}/10-commands/step-${step_num}.json'
with open(meta_file, 'r') as f:
    meta = json.load(f)
meta['completed_at'] = '$(date -Iseconds)'
meta['exit_code'] = ${exit_code}
with open(meta_file, 'w') as f:
    json.dump(meta, f, indent=2)
" 2>/dev/null || true

  if [[ ${exit_code} -ne 0 ]]; then
    echo "[$(date -Iseconds)] Step ${step_num} failed (exit_code=${exit_code})" >&2
    tail -50 "${log_file}" >&2 || true
    return ${exit_code}
  fi

  echo "[$(date -Iseconds)] Step ${step_num} completed"
  return 0
}

export -f run_step
export STEP_COUNTER=0

# Parse and execute commands
COMMANDS_JSON="${PROOF_DIR}/10-commands/commands.json"
python3 -c "
import sys, yaml, json
try:
    with open('${TASK_YAML}', 'r') as f:
        doc = yaml.safe_load(f)
    commands = doc.get('commands', [])
    with open('${COMMANDS_JSON}', 'w') as f:
        json.dump(commands, f, indent=2)
except Exception as e:
    print('[]')
" 2>/dev/null || echo "[]" > "${COMMANDS_JSON}"

# Main execution block with timeout
STATUS="unknown"
EXIT_CODE=0

# Flag file for timeout (subshell-safe communication)
TIMEOUT_FLAG="${PROOF_DIR}/99-summary/.timeout_killed"
rm -f "${TIMEOUT_FLAG}"

# Create temporary script for execution (avoids complex bash -c quoting)
TEMP_SCRIPT="${PROOF_DIR}/99-summary/.exec_script.sh"
cat > "${TEMP_SCRIPT}" <<'EXEC_SCRIPT'
set -euo pipefail
STEP_COUNTER=0

# Re-source environment
source "${ENV_FILE}"

# Re-define run_step function
run_step() {
  local step_name="$1"
  local step_num="${STEP_COUNTER:-0}"
  STEP_COUNTER=$((step_num + 1))

  echo "[$(date -Iseconds)] Step ${step_num}: ${step_name}"

  local step_file="${PROOF_DIR}/10-commands/step-${step_num}.sh"
  cat > "${step_file}"

  # JSON-safe name
  local name_json
  name_json=$(python3 -c 'import json,sys; print(json.dumps(sys.argv[1]))' "${step_name}")

  cat > "${PROOF_DIR}/10-commands/step-${step_num}.json" <<STEP_META
{
  "step": ${step_num},
  "name": ${name_json},
  "started_at": "$(date -Iseconds)"
}
STEP_META

  local log_file="${PROOF_DIR}/20-logs/step-${step_num}.log"

  set +e
  (
    set -euo pipefail
    cd "${TASK_DIR}"
    bash "${step_file}"
  ) &> "${log_file}"
  local exit_code=$?
  set -e

  # Update step metadata
  python3 <<PYCODE 2>/dev/null || true
import json
meta_file = "${PROOF_DIR}/10-commands/step-${step_num}.json"
with open(meta_file, "r") as f:
    meta = json.load(f)
meta["completed_at"] = "$(date -Iseconds)"
meta["exit_code"] = ${exit_code}
with open(meta_file, "w") as f:
    json.dump(meta, f, indent=2)
PYCODE

  if [[ ${exit_code} -ne 0 ]]; then
    echo "[$(date -Iseconds)] Step ${step_num} failed (exit_code=${exit_code})" >&2
    tail -50 "${log_file}" >&2 || true
    return ${exit_code}
  fi

  echo "[$(date -Iseconds)] Step ${step_num} completed"
  return 0
}

# Execute each command from JSON
python3 <<PYCODE2 | bash
import json, sys
with open("${COMMANDS_JSON}", "r") as f:
    commands = json.load(f)

for i, cmd in enumerate(commands):
    name = cmd.get("name", f"Step {i}")
    run_block = cmd.get("run", "")

    # Escape for bash here-doc
    escaped_name = name.replace("'", "'\"'\"'")

    print(f"run_step '{escaped_name}' <<'STEP_BLOCK'")
    print(run_block)
    print("STEP_BLOCK")
    print()
PYCODE2

echo "[$(date -Iseconds)] All commands completed successfully"
EXEC_SCRIPT

# Export variables for the script
export ENV_FILE TASK_DIR PROOF_DIR COMMANDS_JSON TASK_ID RUN_ID ZENFLOW_ROOT COMPOSE_PROJECT_NAME

# Execute with process group isolation
(
  set -euo pipefail
  trap 'exit 130' INT TERM
  setsid bash "${TEMP_SCRIPT}"
) &

CMD_PID=$!
PGID=$(ps -o pgid= -p "${CMD_PID}" | tr -d ' ') || PGID="${CMD_PID}"

# Timeout watchdog (writes flag file if timeout occurs)
(
  sleep "${TIMEOUT_SEC}"
  if kill -0 "${CMD_PID}" 2>/dev/null; then
    echo "1" > "${TIMEOUT_FLAG}"
    echo "[$(date -Iseconds)] Timeout (${TIMEOUT_SEC}s) - killing process group ${PGID}" >&2
    kill -TERM -- "-${PGID}" 2>/dev/null || true
    sleep 5
    kill -KILL -- "-${PGID}" 2>/dev/null || true
  fi
) &

WATCHDOG_PID=$!

# Wait for command to complete
set +e
if wait "${CMD_PID}"; then
  EXIT_CODE=0
  STATUS="success"
else
  EXIT_CODE=$?

  # Check if timeout occurred (read flag file)
  if [[ -f "${TIMEOUT_FLAG}" ]]; then
    STATUS="timeout"
    EXIT_CODE=124
  else
    STATUS="failure"
  fi
fi
set -e

# Kill watchdog if still running
kill "${WATCHDOG_PID}" 2>/dev/null || true
wait "${WATCHDOG_PID}" 2>/dev/null || true

# Cleanup temporary files
rm -f "${TIMEOUT_FLAG}"
rm -f "${TEMP_SCRIPT}"

# Generate final status
cat > "${PROOF_DIR}/99-summary/status.json" <<EOF
{
  "task_id": "${TASK_ID}",
  "run_id": "${RUN_ID}",
  "status": "${STATUS}",
  "exit_code": ${EXIT_CODE},
  "completed_at": "$(date -Iseconds)",
  "timeout_sec": ${TIMEOUT_SEC}
}
EOF

# Compute checksums
if command -v sha256sum &>/dev/null; then
  find "${PROOF_DIR}/30-artifacts" -type f -exec sha256sum {} \; > "${PROOF_DIR}/40-checksums/artifacts.sha256" 2>/dev/null || true
fi

# Final log
if [[ "${STATUS}" == "success" ]]; then
  echo "[$(date -Iseconds)] Task ${TASK_ID} completed successfully"
  exit 0
elif [[ "${STATUS}" == "timeout" ]]; then
  echo "[$(date -Iseconds)] Task ${TASK_ID} timed out after ${TIMEOUT_SEC}s" >&2
  exit 124
else
  echo "[$(date -Iseconds)] Task ${TASK_ID} failed (exit_code=${EXIT_CODE})" >&2
  exit ${EXIT_CODE}
fi
