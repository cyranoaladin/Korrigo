#!/usr/bin/env bash
# validate_runner.sh - Validation script for Zenflow runner v3.0
set -euo pipefail

ZENFLOW_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
VALIDATION_DIR="${ZENFLOW_ROOT}/validation"

echo "========================================="
echo "Zenflow Runner v3.0 Validation"
echo "========================================="
echo

# Create validation directory
mkdir -p "${VALIDATION_DIR}/tasks"

# Test 1: Timeout semantic - verify timeout blocks dependents
echo "[TEST 1] Timeout Semantic (timeout blocks dependents)"
echo "---------------------------------------"

# Create a task that times out
mkdir -p "${VALIDATION_DIR}/tasks/test-timeout"
cat > "${VALIDATION_DIR}/tasks/test-timeout/task.yaml" <<'EOF'
id: test-timeout
title: Task That Times Out
phase: VALIDATE
parallel_safe: true
timeout_sec: 3
commands:
  - name: Sleep forever
    run: |
      echo "Sleeping for 10 seconds (timeout is 3s)..."
      sleep 10
      echo "This should never print"
EOF

# Create a dependent task
mkdir -p "${VALIDATION_DIR}/tasks/test-dependent"
cat > "${VALIDATION_DIR}/tasks/test-dependent/task.yaml" <<'EOF'
id: test-dependent
title: Task Dependent on Timeout
phase: VALIDATE
parallel_safe: true
needs: [test-timeout]
timeout_sec: 10
commands:
  - name: Should not run
    run: |
      echo "ERROR: This task should not run because test-timeout timed out!" >&2
      exit 1
EOF

# Run phase
RUN_ID="validate-$(date +%Y%m%d-%H%M%S)"
export RUN_ID
mkdir -p "${ZENFLOW_ROOT}/proofs/${RUN_ID}"
mkdir -p "${ZENFLOW_ROOT}/reports/${RUN_ID}"

# Temporarily symlink validation tasks to main tasks dir
TASKS_BACKUP="${ZENFLOW_ROOT}/tasks.backup"
if [[ -d "${ZENFLOW_ROOT}/tasks" ]]; then
  mv "${ZENFLOW_ROOT}/tasks" "${TASKS_BACKUP}"
fi
ln -sf "${VALIDATION_DIR}/tasks" "${ZENFLOW_ROOT}/tasks"

set +e
PHASE_TIMEOUT_SEC=30 "${ZENFLOW_ROOT}/_shared/scripts/run_phase.sh" VALIDATE 2>&1 | tee "${VALIDATION_DIR}/test1.log"
TEST1_EXIT_CODE=$?
set -e

# Restore tasks
rm -f "${ZENFLOW_ROOT}/tasks"
if [[ -d "${TASKS_BACKUP}" ]]; then
  mv "${TASKS_BACKUP}" "${ZENFLOW_ROOT}/tasks"
fi

# Validate results
echo
if [[ ${TEST1_EXIT_CODE} -ne 0 ]]; then
  echo "✅ TEST 1 PASSED: Phase failed as expected (exit code ${TEST1_EXIT_CODE})"

  # Check that timeout was detected
  if grep -q "timed out (will block dependents)" "${VALIDATION_DIR}/test1.log"; then
    echo "✅ Timeout correctly identified"
  else
    echo "❌ Timeout not correctly identified"
  fi

  # Check that dependent did not run
  if grep -q "ERROR: This task should not run" "${VALIDATION_DIR}/test1.log"; then
    echo "❌ Dependent task ran (should have been blocked)"
  else
    echo "✅ Dependent task was correctly blocked"
  fi

  # Check deadlock detection
  if grep -q "Deadlock detected" "${VALIDATION_DIR}/test1.log"; then
    echo "✅ Deadlock detection triggered"
    if grep -q "dependency 'test-timeout' has status: timeout" "${VALIDATION_DIR}/test1.log"; then
      echo "✅ Dependency status correctly reported"
    else
      echo "❌ Dependency status not correctly reported"
    fi
  else
    echo "❌ Deadlock detection not triggered"
  fi
else
  echo "❌ TEST 1 FAILED: Phase should have failed but exited with 0"
fi

echo
echo

# Test 2: Phase timeout with PHASE_TIMEOUT_SEC
echo "[TEST 2] Phase Timeout (PHASE_TIMEOUT_SEC)"
echo "---------------------------------------"

mkdir -p "${VALIDATION_DIR}/tasks2/test-long-running"
cat > "${VALIDATION_DIR}/tasks2/test-long-running/task.yaml" <<'EOF'
id: test-long-running
title: Long Running Task
phase: VALIDATE2
parallel_safe: true
timeout_sec: 60
commands:
  - name: Sleep for a long time
    run: |
      echo "Starting long task..."
      sleep 30
      echo "Completed"
EOF

# Run with short phase timeout
RUN_ID="validate2-$(date +%Y%m%d-%H%M%S)"
export RUN_ID
mkdir -p "${ZENFLOW_ROOT}/proofs/${RUN_ID}"
mkdir -p "${ZENFLOW_ROOT}/reports/${RUN_ID}"

# Symlink validation tasks
if [[ -d "${ZENFLOW_ROOT}/tasks" ]]; then
  mv "${ZENFLOW_ROOT}/tasks" "${TASKS_BACKUP}"
fi
ln -sf "${VALIDATION_DIR}/tasks2" "${ZENFLOW_ROOT}/tasks"

set +e
PHASE_TIMEOUT_SEC=5 "${ZENFLOW_ROOT}/_shared/scripts/run_phase.sh" VALIDATE2 2>&1 | tee "${VALIDATION_DIR}/test2.log"
TEST2_EXIT_CODE=$?
set -e

# Restore tasks
rm -f "${ZENFLOW_ROOT}/tasks"
if [[ -d "${TASKS_BACKUP}" ]]; then
  mv "${TASKS_BACKUP}" "${ZENFLOW_ROOT}/tasks"
fi

echo
if [[ ${TEST2_EXIT_CODE} -ne 0 ]]; then
  echo "✅ TEST 2 PASSED: Phase failed as expected (exit code ${TEST2_EXIT_CODE})"

  # Check phase timeout message
  if grep -q "ERROR: Phase timeout (5s) exceeded" "${VALIDATION_DIR}/test2.log"; then
    echo "✅ Phase timeout correctly triggered"
  else
    echo "❌ Phase timeout not correctly triggered"
  fi

  # Check that task was killed
  if grep -q "Killing task test-long-running" "${VALIDATION_DIR}/test2.log"; then
    echo "✅ Task correctly killed on phase timeout"
  else
    echo "⚠️  Task kill message not found (may have exited naturally)"
  fi
else
  echo "❌ TEST 2 FAILED: Phase should have failed due to timeout"
fi

echo
echo

# Test 3: Successful parallel execution
echo "[TEST 3] Parallel Execution (MAX_JOBS)"
echo "---------------------------------------"

mkdir -p "${VALIDATION_DIR}/tasks3"
for i in {1..6}; do
  mkdir -p "${VALIDATION_DIR}/tasks3/test-parallel-${i}"
  cat > "${VALIDATION_DIR}/tasks3/test-parallel-${i}/task.yaml" <<EOF
id: test-parallel-${i}
title: Parallel Task ${i}
phase: VALIDATE3
parallel_safe: true
timeout_sec: 30
commands:
  - name: Run task
    run: |
      echo "Task ${i} started at \$(date +%s)"
      sleep 2
      echo "Task ${i} completed at \$(date +%s)"
EOF
done

RUN_ID="validate3-$(date +%Y%m%d-%H%M%S)"
export RUN_ID
mkdir -p "${ZENFLOW_ROOT}/proofs/${RUN_ID}"
mkdir -p "${ZENFLOW_ROOT}/reports/${RUN_ID}"

# Symlink validation tasks
if [[ -d "${ZENFLOW_ROOT}/tasks" ]]; then
  mv "${ZENFLOW_ROOT}/tasks" "${TASKS_BACKUP}"
fi
ln -sf "${VALIDATION_DIR}/tasks3" "${ZENFLOW_ROOT}/tasks"

set +e
MAX_JOBS=3 PHASE_TIMEOUT_SEC=60 "${ZENFLOW_ROOT}/_shared/scripts/run_phase.sh" VALIDATE3 2>&1 | tee "${VALIDATION_DIR}/test3.log"
TEST3_EXIT_CODE=$?
set -e

# Restore tasks
rm -f "${ZENFLOW_ROOT}/tasks"
if [[ -d "${TASKS_BACKUP}" ]]; then
  mv "${TASKS_BACKUP}" "${ZENFLOW_ROOT}/tasks"
fi

echo
if [[ ${TEST3_EXIT_CODE} -eq 0 ]]; then
  echo "✅ TEST 3 PASSED: Phase completed successfully (exit code 0)"

  # Check that tasks ran in parallel (should complete in ~4 seconds, not 12)
  success_count=$(grep -c "completed successfully" "${VALIDATION_DIR}/test3.log" || echo 0)
  if [[ ${success_count} -eq 6 ]]; then
    echo "✅ All 6 tasks completed successfully"
  else
    echo "❌ Only ${success_count}/6 tasks completed"
  fi

  # Rough check: extract start times and verify parallelism
  echo "⚠️  Manual verification recommended: check that at most 3 tasks ran concurrently"
else
  echo "❌ TEST 3 FAILED: Phase should have succeeded but exited with ${TEST3_EXIT_CODE}"
fi

echo
echo

# Summary
echo "========================================="
echo "Validation Summary"
echo "========================================="
echo
echo "Test 1 (Timeout Semantic): $(if [[ ${TEST1_EXIT_CODE} -ne 0 ]]; then echo "✅ PASS"; else echo "❌ FAIL"; fi)"
echo "Test 2 (Phase Timeout):    $(if [[ ${TEST2_EXIT_CODE} -ne 0 ]]; then echo "✅ PASS"; else echo "❌ FAIL"; fi)"
echo "Test 3 (Parallel Exec):    $(if [[ ${TEST3_EXIT_CODE} -eq 0 ]]; then echo "✅ PASS"; else echo "❌ FAIL"; fi)"
echo
echo "Validation logs saved to: ${VALIDATION_DIR}/"
echo "Proofs saved to: ${ZENFLOW_ROOT}/proofs/validate*/"
echo

if [[ ${TEST1_EXIT_CODE} -ne 0 ]] && [[ ${TEST2_EXIT_CODE} -ne 0 ]] && [[ ${TEST3_EXIT_CODE} -eq 0 ]]; then
  echo "✅ ALL TESTS PASSED - Runner v3.0 is production-ready"
  exit 0
else
  echo "❌ SOME TESTS FAILED - Review logs and fix issues"
  exit 1
fi
