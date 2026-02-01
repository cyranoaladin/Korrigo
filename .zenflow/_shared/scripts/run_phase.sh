#!/usr/bin/env bash
# run_phase.sh - Phase orchestrator with DAG scheduling
# Version: 3.0 - Final (timeout=failure, PHASE_TIMEOUT_SEC, improved deadlock detection)
set -euo pipefail

PHASE="${1:-}"
RUN_ID="${RUN_ID:-$(date +%Y%m%d-%H%M%S)-$$}"
ZENFLOW_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
TASKS_DIR="${ZENFLOW_ROOT}/tasks"
PROOFS_DIR="${ZENFLOW_ROOT}/.zenflow/proofs/${RUN_ID}"
REPORTS_DIR="${ZENFLOW_ROOT}/.zenflow/reports/${RUN_ID}"

# Configuration
# Support both ZENFLOW_MAX_JOBS (preferred) and MAX_JOBS (backward compat)
MAX_JOBS="${ZENFLOW_MAX_JOBS:-${MAX_JOBS:-4}}"
PHASE_TIMEOUT_SEC="${ZENFLOW_PHASE_TIMEOUT_SEC:-${PHASE_TIMEOUT_SEC:-3600}}"  # 1 hour default
POLL_INTERVAL_SEC=1

if [[ -z "${PHASE}" ]]; then
  echo "Usage: $0 <phase> [RUN_ID]" >&2
  echo "Example: $0 A" >&2
  exit 1
fi

mkdir -p "${PROOFS_DIR}" "${REPORTS_DIR}"

# Phase start time
PHASE_START_TIME=$(date +%s)

echo "[$(date -Iseconds)] Starting phase ${PHASE} (RUN_ID=${RUN_ID}, MAX_JOBS=${MAX_JOBS}, PHASE_TIMEOUT_SEC=${PHASE_TIMEOUT_SEC})"

# Discovery: find all tasks for this phase
declare -a TASKS=()
for task_dir in "${TASKS_DIR}"/*; do
  [[ ! -d "${task_dir}" ]] && continue

  task_yaml="${task_dir}/task.yaml"
  [[ ! -f "${task_yaml}" ]] && continue

  # Parse phase from YAML
  task_phase=$(python3 -c "
import sys, yaml
try:
    with open('${task_yaml}', 'r') as f:
        doc = yaml.safe_load(f)
    print(doc.get('phase', ''))
except Exception as e:
    print('', file=sys.stderr)
" 2>/dev/null || echo "")

  if [[ "${task_phase}" == "${PHASE}" ]]; then
    task_id=$(basename "${task_dir}")
    TASKS+=("${task_id}")
  fi
done

if [[ ${#TASKS[@]} -eq 0 ]]; then
  echo "[$(date -Iseconds)] No tasks found for phase ${PHASE}" >&2
  exit 1
fi

echo "[$(date -Iseconds)] Found ${#TASKS[@]} tasks for phase ${PHASE}: ${TASKS[*]}"

# Parse metadata (parallel_safe, needs) for all tasks
declare -A TASK_PARALLEL_SAFE
declare -A TASK_NEEDS
declare -A TASK_STATUS  # pending, running, success, failure, timeout
declare -A TASK_PIDS

for task_id in "${TASKS[@]}"; do
  task_yaml="${TASKS_DIR}/${task_id}/task.yaml"

  # Parse parallel_safe
  parallel_safe=$(python3 -c "
import sys, yaml
try:
    with open('${task_yaml}', 'r') as f:
        doc = yaml.safe_load(f)
    print('true' if doc.get('parallel_safe', False) else 'false')
except Exception:
    print('true')  # default to safe
" 2>/dev/null || echo "true")

  TASK_PARALLEL_SAFE[$task_id]="${parallel_safe}"

  # Parse needs (dependencies)
  needs=$(python3 -c "
import sys, yaml
try:
    with open('${task_yaml}', 'r') as f:
        doc = yaml.safe_load(f)
    deps = doc.get('needs', [])
    if deps:
        print(','.join(deps))
    else:
        print('')
except Exception:
    print('')
" 2>/dev/null || echo "")

  TASK_NEEDS[$task_id]="${needs}"
  TASK_STATUS[$task_id]="pending"
done

# Helper: Check if dependencies are satisfied
check_dependencies() {
  local task_id="$1"
  local needs="${TASK_NEEDS[$task_id]}"

  [[ -z "${needs}" ]] && return 0  # No dependencies

  IFS=',' read -ra deps <<< "${needs}"
  for dep in "${deps[@]}"; do
    local dep_status="${TASK_STATUS[$dep]:-pending}"
    if [[ "${dep_status}" != "success" ]]; then
      return 1  # Dependency not satisfied
    fi
  done

  return 0  # All dependencies satisfied
}

# Helper: Check if we can run more tasks in parallel
can_start_task() {
  local task_id="$1"
  local parallel_safe="${TASK_PARALLEL_SAFE[$task_id]}"

  # Check dependencies first
  check_dependencies "${task_id}" || return 1

  # If not parallel_safe, check if any task is running
  if [[ "${parallel_safe}" == "false" ]]; then
    for tid in "${!TASK_STATUS[@]}"; do
      if [[ "${TASK_STATUS[$tid]}" == "running" ]]; then
        return 1  # Another task is running
      fi
    done
  fi

  # Check MAX_JOBS limit
  local running_count=0
  for tid in "${!TASK_STATUS[@]}"; do
    if [[ "${TASK_STATUS[$tid]}" == "running" ]]; then
      ((running_count++))
    fi
  done

  if [[ ${running_count} -ge ${MAX_JOBS} ]]; then
    return 1  # Max jobs reached
  fi

  return 0  # Can start
}

# Main scheduling loop
echo "[$(date -Iseconds)] Starting DAG scheduler"

while true; do
  # Check phase timeout
  CURRENT_TIME=$(date +%s)
  ELAPSED=$((CURRENT_TIME - PHASE_START_TIME))

  if [[ ${ELAPSED} -ge ${PHASE_TIMEOUT_SEC} ]]; then
    echo "[$(date -Iseconds)] ERROR: Phase timeout (${PHASE_TIMEOUT_SEC}s) exceeded after ${ELAPSED}s" >&2

    # Kill all running tasks (including process groups)
    for task_id in "${!TASK_PIDS[@]}"; do
      pid="${TASK_PIDS[$task_id]}"
      echo "[$(date -Iseconds)] Killing task ${task_id} (PID ${pid})" >&2

      # Try to kill process group first (run_task.sh uses setsid)
      pgid=$(ps -o pgid= -p "${pid}" 2>/dev/null | tr -d ' ') || pgid=""
      if [[ -n "${pgid}" ]] && [[ "${pgid}" != "0" ]]; then
        kill -TERM -- "-${pgid}" 2>/dev/null || true
      fi

      # Also kill the parent PID as fallback
      kill -TERM "${pid}" 2>/dev/null || true
    done

    # Grace period before SIGKILL
    sleep 2

    for task_id in "${!TASK_PIDS[@]}"; do
      pid="${TASK_PIDS[$task_id]}"
      if kill -0 "${pid}" 2>/dev/null; then
        echo "[$(date -Iseconds)] Force killing task ${task_id} (PID ${pid})" >&2
        pgid=$(ps -o pgid= -p "${pid}" 2>/dev/null | tr -d ' ') || pgid=""
        if [[ -n "${pgid}" ]] && [[ "${pgid}" != "0" ]]; then
          kill -KILL -- "-${pgid}" 2>/dev/null || true
        fi
        kill -KILL "${pid}" 2>/dev/null || true
      fi
    done

    exit 1
  fi

  # Poll running tasks
  for task_id in "${!TASK_PIDS[@]}"; do
    pid="${TASK_PIDS[$task_id]}"

    # Check if process is still running
    if ! kill -0 "$pid" 2>/dev/null; then
      # Process has exited, reap it
      wait "$pid" && exit_code=0 || exit_code=$?

      # Read status from proof directory
      status_json="${PROOFS_DIR}/${task_id}/99-summary/status.json"
      if [[ -f "${status_json}" ]]; then
        status=$(python3 -c "
import sys, json
try:
    with open('${status_json}', 'r') as f:
        doc = json.load(f)
    print(doc.get('status', 'unknown'))
except Exception:
    print('unknown')
" 2>/dev/null || echo "unknown")
      else
        status="unknown"
      fi

      # POLICY: timeout and failure both block dependencies
      if [[ "${status}" == "success" ]]; then
        TASK_STATUS[$task_id]="success"
        echo "[$(date -Iseconds)] Task ${task_id} completed successfully"
      elif [[ "${status}" == "timeout" ]]; then
        TASK_STATUS[$task_id]="timeout"
        echo "[$(date -Iseconds)] Task ${task_id} timed out (will block dependents)" >&2
      else
        TASK_STATUS[$task_id]="failure"
        echo "[$(date -Iseconds)] Task ${task_id} failed (exit_code=${exit_code})" >&2
      fi

      unset TASK_PIDS[$task_id]
    fi
  done

  # Try to start new tasks
  for task_id in "${TASKS[@]}"; do
    if [[ "${TASK_STATUS[$task_id]}" == "pending" ]] && can_start_task "${task_id}"; then
      echo "[$(date -Iseconds)] Starting task ${task_id}"

      # Start task in background
      (
        export RUN_ID PHASE
        "${ZENFLOW_ROOT}/_shared/scripts/run_task.sh" "${task_id}"
      ) &

      pid=$!
      TASK_PIDS[$task_id]="${pid}"
      TASK_STATUS[$task_id]="running"
    fi
  done

  # Check if all tasks are done
  all_done=true
  any_running=false
  for task_id in "${TASKS[@]}"; do
    status="${TASK_STATUS[$task_id]}"
    if [[ "${status}" == "pending" ]] || [[ "${status}" == "running" ]]; then
      all_done=false
    fi
    if [[ "${status}" == "running" ]]; then
      any_running=true
    fi
  done

  if ${all_done}; then
    break
  fi

  # Deadlock detection: no tasks running, but some still pending
  if ! ${any_running}; then
    pending_tasks=()
    for task_id in "${TASKS[@]}"; do
      if [[ "${TASK_STATUS[$task_id]}" == "pending" ]]; then
        pending_tasks+=("${task_id}")
      fi
    done

    if [[ ${#pending_tasks[@]} -gt 0 ]]; then
      echo "[$(date -Iseconds)] ERROR: Deadlock detected - no tasks running, but ${#pending_tasks[@]} tasks still pending:" >&2

      for task_id in "${pending_tasks[@]}"; do
        needs="${TASK_NEEDS[$task_id]}"
        if [[ -n "${needs}" ]]; then
          echo "  - ${task_id} (needs: ${needs})" >&2

          # Show which dependencies are not satisfied
          IFS=',' read -ra deps <<< "${needs}"
          for dep in "${deps[@]}"; do
            dep_status="${TASK_STATUS[$dep]:-unknown}"
            if [[ "${dep_status}" != "success" ]]; then
              echo "    -> dependency '${dep}' has status: ${dep_status}" >&2
            fi
          done
        else
          echo "  - ${task_id} (no dependencies, blocked by parallel_safe or MAX_JOBS)" >&2
        fi
      done

      exit 1
    fi
  fi

  sleep ${POLL_INTERVAL_SEC}
done

# Phase complete - generate summary
echo "[$(date -Iseconds)] Phase ${PHASE} complete"

success_count=0
failure_count=0
timeout_count=0

for task_id in "${TASKS[@]}"; do
  status="${TASK_STATUS[$task_id]}"
  case "${status}" in
    success)
      ((success_count++))
      ;;
    failure)
      ((failure_count++))
      ;;
    timeout)
      ((timeout_count++))
      ;;
  esac
done

echo "Summary: ${success_count} succeeded, ${failure_count} failed, ${timeout_count} timed out"

# Generate phase report
phase_report="${REPORTS_DIR}/phase-${PHASE}.json"
python3 -c "
import json
import sys
from datetime import datetime

tasks_summary = []
" > /dev/null  # Placeholder for future JSON report generation

# Exit with appropriate code
if [[ ${failure_count} -gt 0 ]] || [[ ${timeout_count} -gt 0 ]]; then
  echo "[$(date -Iseconds)] Phase ${PHASE} failed (${failure_count} failures, ${timeout_count} timeouts)" >&2
  exit 1
fi

echo "[$(date -Iseconds)] Phase ${PHASE} succeeded"
exit 0
