# Full SDD workflow

## Configuration
- **Artifacts Path**: {@artifacts_path} → `.zenflow/tasks/{task_id}`

---

## Workflow Steps

### [x] Step: Requirements
<!-- chat-id: 11950bfb-1438-45b6-9421-ffa2dcc2efc3 -->

Create a Product Requirements Document (PRD) based on the feature description.

1. Review existing codebase to understand current architecture and patterns
2. Analyze the feature definition and identify unclear aspects
3. Ask the user for clarifications on aspects that significantly impact scope or user experience
4. Make reasonable decisions for minor details based on context and conventions
5. If user can't clarify, make a decision, state the assumption, and continue

Save the PRD to `{@artifacts_path}/requirements.md`.

### [x] Step: Technical Specification
<!-- chat-id: a7aa1bf8-5701-46e8-a690-95ea057f0747 -->

Create a technical specification based on the PRD in `{@artifacts_path}/requirements.md`.

1. Review existing codebase architecture and identify reusable components
2. Define the implementation approach

Save to `{@artifacts_path}/spec.md` with:
- Technical context (language, dependencies)
- Implementation approach referencing existing code patterns
- Source code structure changes
- Data model / API / interface changes
- Delivery phases (incremental, testable milestones)
- Verification approach using project lint/test commands

### [x] Step: Planning
<!-- chat-id: 5c519a09-68ea-4466-9614-f97b5ca2463a -->

**Root Cause Analysis:**
The issue is in `backend/grading/services.py` where the `_require_active_lock` method and `finalize_copy` method do not enforce the lock token requirement when it's missing. This allows authenticated users who own a lock to perform write operations without providing the `X-Lock-Token` header, violating the security contract.

**Affected Code Locations:**
1. `backend/grading/services.py:79-80` - `_require_active_lock` returns early when token is missing
2. `backend/grading/services.py:540-542` - `finalize_copy` only checks token if user is not owner

**Failing Tests:**
- `test_annotation_create_missing_token_returns_403_detail` (expects 403, gets 201)
- `test_annotation_delete_missing_token_returns_403_detail` (expects 403, gets 204)
- `test_finalize_missing_token_returns_403_detail` (expects 403, gets 200)
- `test_permission_error_returns_403_detail` (expects 403, gets 204)
- `test_lock_heartbeat_missing_token_returns_403_detail` (expects 403)

**Implementation Plan:**

### [x] Step: Pre-flight Branch Setup
<!-- chat-id: f5ff08c2-2235-4901-9953-9c06f995f86a -->

Switch to main project directory and create branch for the task.

**Actions:**
- Navigate to `/home/alaeddine/viatique__PMF`
- Run `git pull --ff-only` to sync with remote
- Run `git checkout -b zf/A3-auth-token-403`

**Verification:**
- Confirm on correct branch with `git branch --show-current`

---

### [x] Step: Fix Lock Token Validation in _require_active_lock
<!-- chat-id: 32d42318-408c-411c-900c-4962cd482907 -->

Fix the `_require_active_lock` method to always require a valid lock token.

**Current Behavior (lines 79-80):**
```python
if not lock_token:
    return lock
```

**Required Change:**
Replace the early return with an error raise to enforce token requirement:
```python
if not lock_token:
    raise PermissionError("Missing lock token.")
```

**Files to Modify:**
- `backend/grading/services.py:79-80`

**Affected Methods:**
- `add_annotation` (calls `_require_active_lock`)
- `update_annotation` (calls `_require_active_lock`)
- `delete_annotation` (calls `_require_active_lock`)

**Contract:**
All write operations on annotations require both lock ownership AND a valid lock token header.

---

### [x] Step: Fix Lock Token Validation in finalize_copy
<!-- chat-id: 183ef5c0-f1eb-4a18-b04a-60436c0a0968 -->

Fix the `finalize_copy` method to always require a valid lock token.

**Current Behavior (lines 540-542):**
```python
if not lock_token:
    if lock.owner != user:
        raise PermissionError("Missing lock token.")
```
This only raises an error if the user is NOT the owner, allowing owners to finalize without a token.

**Required Change:**
```python
if not lock_token:
    raise PermissionError("Missing lock token.")
```

**Files to Modify:**
- `backend/grading/services.py:540-542`

**Contract:**
Finalize operation requires both lock ownership AND a valid lock token header, regardless of who owns the lock.

---

### [ ] Step: Run Contract Runtime Tests
<!-- chat-id: test-runtime -->

Run the contract runtime tests to verify the fixes.

**Test Commands:**
```bash
cd /home/alaeddine/viatique__PMF/backend
../backend/venv/bin/python -m pytest -xvs \
  grading/tests/test_api_error_contract_runtime.py::test_annotation_create_missing_token_returns_403_detail \
  grading/tests/test_api_error_contract_runtime.py::test_annotation_delete_missing_token_returns_403_detail \
  grading/tests/test_api_error_contract_runtime.py::test_finalize_missing_token_returns_403_detail \
  grading/tests/test_api_error_contract_runtime.py::test_lock_heartbeat_missing_token_returns_403_detail
```

**Expected Result:**
- All 4 tests should pass (previously failing with 201/204/200, now returning 403)

**Verification:**
- Exit code 0
- No assertion errors
- All tests marked as PASSED

---

### [ ] Step: Run Error Handling Tests
<!-- chat-id: test-error-handling -->

Run the error handling tests to ensure the fixes work correctly.

**Test Commands:**
```bash
cd /home/alaeddine/viatique__PMF/backend
../backend/venv/bin/python -m pytest -xvs \
  grading/tests/test_error_handling.py::test_permission_error_returns_403_detail \
  grading/tests/test_error_handling.py -q
```

**Expected Result:**
- `test_permission_error_returns_403_detail` should pass
- All other error handling tests should still pass

**Verification:**
- Exit code 0
- No regressions in other tests

---

### [ ] Step: Run Full Test Suite
<!-- chat-id: test-full -->

Run the complete test suite for the grading module to ensure no regressions.

**Test Commands:**
```bash
cd /home/alaeddine/viatique__PMF/backend
../backend/venv/bin/python -m pytest grading/tests/ -q --tb=short
```

**Expected Result:**
- All tests pass
- No new failures introduced by the fixes

**Verification:**
- Exit code 0
- Check for any unexpected failures

---

### [ ] Step: Commit and Push Changes
<!-- chat-id: commit-push -->

Commit the changes and push to remote.

**Actions:**
```bash
cd /home/alaeddine/viatique__PMF
git add backend/grading/services.py
git commit -m "Fix(security): enforce 403 on missing lock token

- Modified _require_active_lock to always require lock token
- Modified finalize_copy to enforce token requirement regardless of ownership
- Fixes failing contract tests expecting 403 when X-Lock-Token header is missing
- Tests: test_annotation_create/delete/finalize_missing_token_returns_403_detail"

git push -u origin zf/A3-auth-token-403
```

**Verification:**
- Commit created successfully
- Push completed without errors
- Branch visible on remote

---

### [ ] Step: CI Verification
<!-- chat-id: ci-verify -->

Verify that CI passes with the changes.

**Actions:**
- Check CI status on the pushed branch
- If failures occur, review logs with `--log-failed` flag
- Document the run ID for audit purposes

**Expected Result:**
- All CI checks pass
- No security vulnerabilities introduced
- All contract tests pass
