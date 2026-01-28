# Technical Specification: Fix Authentication Token Enforcement (A3)

## Context

**Language**: Python 3.9  
**Framework**: Django 4.2 + Django REST Framework  
**Affected Modules**: `backend/grading/`

## Problem Statement

Multiple test cases are failing because endpoints that require lock tokens are allowing requests through when the token is missing, returning 201/204/200 instead of the expected 403 status code.

### Failing Tests (from test_api_error_contract_runtime.py)
1. `test_annotation_create_missing_token_returns_403_detail` - expects 403, receives 201
2. `test_annotation_delete_missing_token_returns_403_detail` - expects 403, receives 204  
3. `test_finalize_missing_token_returns_403_detail` - expects 403, receives 200
4. `test_lock_heartbeat_missing_token_returns_403_detail` - expects 403
5. `test_permission_error_returns_403_detail` (from test_error_handling.py) - expects 403 when missing lock token

### Expected Contract
All responses must return:
```json
{
  "detail": "error message"
}
```
- **Status**: 403 Forbidden
- **No** `error` key in response payload

## Root Cause Analysis

### Primary Issue: `_require_active_lock()` in grading/services.py:65-84

```python
def _require_active_lock(copy: Copy, user, lock_token: str):
    # ... validation logic ...
    
    if not lock_token:
        return lock  # ← BUG: Returns early without validating token
    if str(lock.token) != str(lock_token):
        raise PermissionError("Invalid lock token.")
```

**Problem**: When `lock_token` is `None` or empty string, the function returns successfully instead of raising `PermissionError`.

**Impact**: 
- `AnnotationService.add_annotation()` (line 88)
- `AnnotationService.update_annotation()` (line 123)
- `AnnotationService.delete_annotation()` (line 173)
- `GradingService.finalize_copy()` (line 501)

All these methods call `_require_active_lock()` and will incorrectly allow operations without a valid token.

### Secondary Issue: Lock Views Missing Token Check

**Lock Heartbeat** (views_lock.py:51-74) and **Lock Release** (views_lock.py:77-97):
- Already check for missing token on lines 58-60 and 81-83
- Return 403 with correct payload format
- ✅ These are correctly implemented

## Solution Architecture

### Change 1: Fix `_require_active_lock()` logic

**File**: `backend/grading/services.py:65-84`

**Current Logic**:
```python
if not lock_token:
    return lock  # Wrong: allows missing token
if str(lock.token) != str(lock_token):
    raise PermissionError("Invalid lock token.")
```

**Corrected Logic**:
```python
if not lock_token:
    raise PermissionError("Missing lock token")
if str(lock.token) != str(lock_token):
    raise PermissionError("Invalid lock token.")
```

**Rationale**: 
- Missing token and invalid token are both security violations
- Both should raise `PermissionError` (mapped to 403 in views via `_handle_service_error()`)
- Maintains consistency with lock heartbeat/release views

### Error Handling Flow

Views already handle `PermissionError` correctly:
1. Service layer raises `PermissionError` 
2. View catches it in try/except block
3. `_handle_service_error()` maps `PermissionError` → 403 + `{"detail": str(e)}`
4. Response format matches contract: no `error` key, only `detail`

**Existing Infrastructure** (views.py:35-48):
```python
def _handle_service_error(e, context="API"):
    if isinstance(e, PermissionError):
        return Response({"detail": str(e)}, status=status.HTTP_403_FORBIDDEN)
    return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
```

✅ No changes needed in views layer - the infrastructure is correct.

## Implementation Approach

### Phase 1: Core Fix (Single Line Change)
- **File**: `backend/grading/services.py`
- **Line**: ~79
- **Change**: Replace `return lock` with `raise PermissionError("Missing lock token")`

### Phase 2: Verification
Run affected test suites:
```bash
cd backend
../backend/venv/bin/python -m pytest \
  grading/tests/test_api_error_contract_runtime.py \
  grading/tests/test_error_handling.py \
  -v
```

Expected outcomes:
- `test_annotation_create_missing_token_returns_403_detail` ✅ PASS
- `test_annotation_delete_missing_token_returns_403_detail` ✅ PASS  
- `test_finalize_missing_token_returns_403_detail` ✅ PASS
- `test_lock_heartbeat_missing_token_returns_403_detail` ✅ PASS
- `test_permission_error_returns_403_detail` ✅ PASS

### Phase 3: Regression Testing
Ensure the fix doesn't break existing functionality:
```bash
cd backend
../backend/venv/bin/python -m pytest grading/tests/ -v --tb=short
```

Focus on:
- Lock acquisition/release workflows
- Annotation CRUD operations
- Copy finalization workflows

## Data Model / API Changes

**None** - This is purely a security enforcement fix. No database schema, serializer, or API contract changes required.

## Delivery Phases

### Phase 1: Core Fix (Immediate)
- Single line change in `services.py`
- Atomic commit with clear message
- Push to branch `zf/A3-auth-token-403`

### Phase 2: Validation (Before Merge)
- Local test execution 
- CI pipeline verification
- Provide CI run ID and `--log-failed` output as proof

## Verification Approach

### Success Criteria
1. All 5 failing tests pass
2. No regression in existing tests
3. Error response format: `{"detail": "..."}` (no `error` key)
4. HTTP status: 403 for missing/invalid tokens

### Commands
```bash
# Full test suite
cd backend && ../backend/venv/bin/python -m pytest grading/tests/ -v

# Specific contract tests
cd backend && ../backend/venv/bin/python -m pytest \
  grading/tests/test_api_error_contract_runtime.py \
  grading/tests/test_error_handling.py \
  -v --tb=short
```

### CI Pipeline
After local validation:
```bash
git push -u origin zf/A3-auth-token-403
# Retrieve CI run ID and verify with --log-failed
```

## Risk Assessment

**Risk Level**: Low  
**Justification**: 
- Single line change in well-isolated function
- Existing error handling infrastructure already correct
- Comprehensive test coverage validates the fix
- No breaking changes to API contracts

**Rollback**: Simple git revert if issues arise

## References

- Test file: `backend/grading/tests/test_api_error_contract_runtime.py:49-153`
- Test file: `backend/grading/tests/test_error_handling.py:98-260`
- Service layer: `backend/grading/services.py:65-84`
- Views layer: `backend/grading/views.py:35-48`
- Lock views: `backend/grading/views_lock.py:51-97`
