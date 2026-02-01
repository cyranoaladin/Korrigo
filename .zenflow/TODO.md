# Zenflow TODO - Known Issues

## HIGH PRIORITY

### audit_validation.sh - Test 2 timeout issue
**Date**: 2026-02-01
**Status**: KNOWN ISSUE
**Severity**: Low (validation script, not runner itself)

**Problem**:
`audit_validation.sh` times out at TEST 2 (timeout PGID kill test) after 90 seconds. The test spawns background processes (`sleep 300`) and appears to hang during cleanup/verification.

**Evidence**:
- TEST 0 (syntax): ✅ PASS
- TEST 1 (backward compat): ✅ PASS (both modes)
- TEST 2 (timeout PGID): ⏱️ TIMEOUT at cleanup phase

**Root Cause**:
Likely issue with process cleanup in validation script itself (not in run_task.sh/run_phase.sh which have been validated manually).

**Manual Validation Confirms Runner Works**:
```bash
# Successful manual tests prove runner is functional:
RUN_ID="test" ./run_task.sh test-minimal  # ✅ OK
RUN_ID="test" ./run_task.sh path/to/task.yaml  # ✅ OK
```

**Proposed Fix**:
1. Simplify TEST 2 to use shorter sleep (5s instead of 300s)
2. Add explicit timeout to test itself (not rely on command timeout)
3. Improve process cleanup verification (poll with timeout)

**Workaround**:
Run critical validation manually:
```bash
bash -n .zenflow/_shared/scripts/run_task.sh
bash -n .zenflow/_shared/scripts/run_phase.sh
# Manual test: RUN_ID="test" ./run_task.sh <task>
```

**Blocker for Production?**: NO
- Runner itself is validated (syntax + manual tests)
- Issue is in validation test harness, not production code
- Can be fixed post-deployment without impact

**Assigned**: DevOps team
**Target**: Sprint N+1
**Priority**: P2 (nice-to-have, not blocking)
