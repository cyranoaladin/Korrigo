# Product Requirements Document (PRD)
## Security Fix: Enforce Lock Token Validation (Task A3)

**Status**: Requirements  
**Branch**: `zf/A3-auth-token-403`  
**Priority**: Critical - Security Vulnerability  
**Created**: 2026-01-28

---

## 1. Problem Statement

### 1.1 Current Behavior
The grading API currently allows authenticated users to perform write operations (create/delete annotations, finalize copies) **without providing a valid lock token** in the `X-Lock-Token` HTTP header. This violates the security contract that requires all write operations on locked resources to validate lock ownership via the token.

### 1.2 Security Impact
- **Severity**: High
- **Type**: Authorization bypass
- **Risk**: Authenticated users can modify locked copies without proper lock token validation, potentially leading to:
  - Concurrent modification conflicts
  - Data integrity issues
  - Audit trail gaps

### 1.3 Failing Tests
Four tests document the expected security behavior:

1. **`test_annotation_create_missing_token_returns_403_detail`**
   - Endpoint: `POST /api/grading/copies/{id}/annotations/`
   - Expected: 403 Forbidden
   - Actual: 201 Created ❌

2. **`test_annotation_delete_missing_token_returns_403_detail`**
   - Endpoint: `DELETE /api/grading/annotations/{id}/`
   - Expected: 403 Forbidden
   - Actual: 204 No Content ❌

3. **`test_finalize_missing_token_returns_403_detail`**
   - Endpoint: `POST /api/grading/copies/{id}/finalize/`
   - Expected: 403 Forbidden
   - Actual: 200 OK ❌

4. **`test_permission_error_returns_403_detail`**
   - Endpoint: `DELETE /api/grading/annotations/{id}/` (when copy status doesn't allow)
   - Expected: 403 Forbidden with "Missing lock token" message
   - Actual: 204 No Content ❌

---

## 2. Root Cause Analysis

### 2.1 Technical Root Cause
Location: `backend/grading/services.py:65-84`

The `_require_active_lock()` method contains a bypass logic:

```python
def _require_active_lock(copy: Copy, user, lock_token: str):
    # ... lock existence and expiration checks ...
    
    if lock.owner != user:
        raise LockConflictError("Copy is locked by another user.")
    
    if not lock_token:
        return lock  # ❌ SECURITY ISSUE: Returns without validating token
    
    if str(lock.token) != str(lock_token):
        raise PermissionError("Invalid lock token.")
    
    return lock
```

**Issue**: Lines 79-80 allow operations to proceed when `lock_token` is `None` or empty, bypassing token validation.

### 2.2 Affected Components
- **Service Layer**: `backend/grading/services.py`
  - `AnnotationService.add_annotation()` (line 88)
  - `AnnotationService.delete_annotation()` (line 173)
  - `AnnotationService.update_annotation()` (line 150)
  - `GradingService.finalize_copy()` (line 501)

- **View Layer**: `backend/grading/views.py`
  - `AnnotationListCreateView.create()` (line 75)
  - `AnnotationDetailView.update()` (line 107)
  - `AnnotationDetailView.destroy()` (line 133)
  - `CopyFinalizeView.post()` (line 168)

---

## 3. Requirements

### 3.1 Security Contract
**REQ-SEC-001**: All write operations on locked copies MUST require a valid lock token.

**Validation Rules**:
1. Lock token MUST be present in the `X-Lock-Token` HTTP header
2. Lock token MUST match the active lock's token exactly
3. Lock MUST be owned by the authenticated user
4. Lock MUST NOT be expired

**Failure Responses**:
- Missing token → `403 Forbidden` with `{"detail": "Missing lock token"}`
- Invalid token → `403 Forbidden` with `{"detail": "Invalid lock token."}`
- Wrong owner → `409 Conflict` with `{"detail": "Copy is locked by another user."}`
- Expired lock → `409 Conflict` with `{"detail": "Lock expired."}`

### 3.2 API Response Format
**REQ-API-001**: All error responses MUST use the standardized format:

```json
{
  "detail": "<human-readable error message>"
}
```

**Forbidden**: Using `{"error": "..."}` or other custom formats.

### 3.3 Affected Endpoints
The following endpoints MUST enforce lock token validation:

| Endpoint | Method | Operation |
|----------|--------|-----------|
| `/api/grading/copies/{id}/annotations/` | POST | Create annotation |
| `/api/grading/annotations/{id}/` | PATCH | Update annotation |
| `/api/grading/annotations/{id}/` | DELETE | Delete annotation |
| `/api/grading/copies/{id}/finalize/` | POST | Finalize copy |

### 3.4 Backward Compatibility
**REQ-BC-001**: This is a **breaking change** for clients that do not send lock tokens.

**Migration Path**:
- Frontend clients MUST include `X-Lock-Token` header for all write operations
- Legacy integrations will receive 403 errors until updated

---

## 4. Success Criteria

### 4.1 Test Suite
All 13 tests in the error contract suite MUST pass:
- `backend/grading/tests/test_api_error_contract_runtime.py` (6 tests)
- `backend/grading/tests/test_error_handling.py` (7 tests)

### 4.2 Security Validation
- [ ] Manual testing: Attempt write operations without token → 403
- [ ] Manual testing: Attempt write operations with invalid token → 403
- [ ] Manual testing: Attempt write operations with valid token → Success
- [ ] Code review: No bypass logic remains in `_require_active_lock()`

### 4.3 Regression Testing
- [ ] Existing workflows with valid tokens continue to work
- [ ] Lock acquisition and release flow unchanged
- [ ] Audit trail logging unaffected

---

## 5. Non-Goals

### 5.1 Out of Scope
- **Authentication changes**: This fix does NOT change authentication requirements (users must still be authenticated)
- **Lock acquisition logic**: Lock creation and release mechanisms remain unchanged
- **Permission class refactoring**: The `IsTeacherOrAdmin` and `IsLockedByOwnerOrReadOnly` permission classes are not modified
- **Error message localization**: Error messages remain in English
- **Monitoring/alerting**: Security event logging is handled by existing audit mechanisms

### 5.2 Future Considerations
- **Rate limiting**: Consider adding rate limits for failed token validation attempts
- **Token rotation**: Future enhancement for periodic token refresh
- **Detailed error codes**: Structured error codes for programmatic handling

---

## 6. Acceptance Criteria

### 6.1 Functional Requirements
- ✅ All 4 failing tests pass
- ✅ No regression in existing tests (9 passing tests remain passing)
- ✅ Lock token is mandatory for write operations
- ✅ Error responses use `{"detail": "..."}` format

### 6.2 Code Quality
- ✅ No "guess & patch" fixes - all changes justified by test failures
- ✅ Atomic commits with clear messages
- ✅ Local test run before push
- ✅ CI pipeline passes

### 6.3 Documentation
- ✅ Code comments explain the security requirement
- ✅ Commit message references security fix
- ✅ No new documentation files created (per project rules)

---

## 7. Open Questions

### 7.1 Resolved
None - requirements are clear from test suite and existing security contract.

### 7.2 Assumptions
1. **Token format**: Lock tokens are UUIDs stored as strings
2. **Header name**: `X-Lock-Token` is the standard header name (confirmed in views.py:20)
3. **Error priority**: Missing token takes precedence over invalid token (both return 403)
4. **Idempotency**: Token validation does not affect idempotent operations (e.g., already-graded copies)

---

## 8. References

### 8.1 Code Locations
- Test contracts: `backend/grading/tests/test_api_error_contract_runtime.py`
- Service layer: `backend/grading/services.py:65` (`_require_active_lock`)
- View layer: `backend/grading/views.py`
- Lock model: `backend/grading/models.py` (`CopyLock`)

### 8.2 Related Tasks
- Original implementation: Lock-based concurrency control (C3)
- Security review: P1 Security Review - 2026-01-24

### 8.3 Compliance
- Project rules: `.antigravity/rules/01_security_rules.md § 2.2`
- Audit trail: All operations logged via `GradingEvent` model
