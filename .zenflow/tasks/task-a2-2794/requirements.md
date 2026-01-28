# Product Requirements Document: Fix Grading Tasks Test Failures

## Problem Statement

Tests in `backend/grading/tests/test_tasks.py` are failing with `AttributeError` when attempting to patch service dependencies:

- `AttributeError: module 'grading.tasks' has no attribute 'GradingService'`
- `AttributeError: module 'grading.tasks' has no attribute 'PDFProcessor'`

This breaks 5 out of 7 tests in the test suite, causing CI failures.

## Root Cause

The tests use `@patch('grading.tasks.GradingService')` and `@patch('grading.tasks.PDFProcessor')` decorators to mock dependencies, but these symbols are not accessible at module level in `backend/grading/tasks.py`:

1. **GradingService**: Currently imported locally inside functions (line 39), not at module level
2. **PDFProcessor**: Does not exist; tests expect it but code uses `GradingService.import_pdf` instead

Additionally, error handling does not match test expectations:
- Tests expect `Copy.DoesNotExist` to be caught and return `{'status': 'error', 'error': '...'}`
- Current implementation lets the exception propagate, triggering Celery retry logic

## Requirements

### R1: Make Dependencies Patchable

**User Story**: As a test developer, I need to mock service dependencies so tests can run in isolation without database or file system dependencies.

**Acceptance Criteria**:
- `GradingService` must be accessible as `grading.tasks.GradingService` for patching
- Either create `PDFProcessor` class or alias `GradingService` to match test expectations
- Service classes must be imported at module level in `tasks.py`, not inside functions

### R2: Handle Copy Not Found

**User Story**: As a Celery task, when processing a non-existent Copy ID, I should return an error result instead of crashing.

**Acceptance Criteria**:
- `async_finalize_copy` catches `Copy.DoesNotExist` 
- Returns `{'status': 'error', 'error': '<message containing "not found">'}` when Copy doesn't exist
- Test `test_async_finalize_copy_not_found` passes

### R3: Return Expected Status Values

**User Story**: As a caller of async tasks, I need consistent status values to determine success/failure.

**Acceptance Criteria**:
- `async_finalize_copy` success returns `{'status': 'success', 'copy_id': str, ...}` (currently returns `'graded'`)
- `async_import_pdf` success returns `{'status': 'success', ...}` (currently returns `'staging'`)
- Error cases return `{'status': 'error', 'error': '<error message>'}` instead of raising exceptions

### R4: Handle Service Exceptions

**User Story**: As a Celery task, when service methods throw exceptions, I should return error results for business logic errors and only retry for transient failures.

**Acceptance Criteria**:
- Service exceptions (ValueError, etc.) are caught and returned as `{'status': 'error', 'error': str(exc)}`
- Tests `test_async_finalize_handles_errors` and `test_async_import_handles_errors` pass
- Transient errors (network, DB connection) still trigger retry mechanism

## Success Metrics

- All 7 tests in `backend/grading/tests/test_tasks.py` pass
- No regressions in existing functionality
- CI pipeline succeeds for grading module

## Out of Scope

- Creating an actual `PDFProcessor` class with separate implementation (if not required)
- Modifying test expectations (tests define the contract)
- Changing Celery configuration or retry behavior beyond error handling

## Technical Constraints

- Must work in main directory `/home/alaeddine/viatique__PMF`, not worktrees
- Must use dedicated branch `zf/A2-grading-tasks-exports`
- Must verify locally before pushing (run pytest on grading tests)
- Atomic commits with explicit messages
