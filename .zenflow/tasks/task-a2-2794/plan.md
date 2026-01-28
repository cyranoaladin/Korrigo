# Full SDD workflow

## Configuration
- **Artifacts Path**: {@artifacts_path} → `.zenflow/tasks/{task_id}`

---

## Workflow Steps

### [-] Step: Requirements
<!-- chat-id: ff281dc4-ebc4-465d-9a59-eff718b95808 -->

**SKIPPED**: This is a bug fix task, not a feature. Requirements are clear from the task description:
- Fix `AttributeError: module 'grading.tasks' has no attribute 'GradingService'`
- Fix `AttributeError: module 'grading.tasks' has no attribute 'PDFProcessor'`
- Tests in `grading/tests/test_tasks.py` must pass

### [-] Step: Technical Specification
<!-- chat-id: e408fbc1-0202-4d16-aca8-baba57b0d9c8 -->

**SKIPPED**: Straightforward bug fix - no complex architecture changes needed. The fix is:
1. Move imports to module level in `grading/tasks.py`
2. Create `PDFProcessor` class to satisfy test expectations
3. Handle `Copy.DoesNotExist` properly

### [x] Step: Planning
<!-- chat-id: daecedc2-0f81-4129-91bf-1ddf2a81a347 -->

Created detailed implementation plan with 7 concrete steps. See Implementation steps below.

**Rationale for simplified workflow**: This is a bug fix to align code with test expectations, not a feature requiring full specification. The task description provides clear requirements and the fix is localized to 2 files.

---

# Task A2: Implementation Plan

## Problem Statement
Tests in `backend/grading/tests/test_tasks.py` fail with `AttributeError` because:
- `grading.tasks.GradingService` is not accessible (imported inside functions)
- `grading.tasks.PDFProcessor` doesn't exist
- Tests use `@patch('grading.tasks.GradingService.finalize_copy')` and `@patch('grading.tasks.PDFProcessor.import_pdf')`
- `async_finalize_copy` doesn't handle `Copy.DoesNotExist` as tests expect

---

### [ ] Step: Pre-flight checks

Verify environment and branch setup:
- Ensure in main directory `/home/alaeddine/viatique__PMF`
- Git pull --ff-only
- Create branch `zf/A2-grading-tasks-exports`
- Verify clean working tree

**Verification**: `git status --porcelain=v1` shows clean state, on correct branch

---

### [ ] Step: Audit test expectations

Analyze what tests expect from `grading.tasks`:
- Extract all patch targets from `backend/grading/tests/test_tasks.py` (lines 31, 48, 87, 102)
- Identify expected method signatures for `GradingService.finalize_copy` and `PDFProcessor.import_pdf`
- Document error handling contracts (test_async_finalize_copy_not_found expects specific error format)
- Verify which services actually exist in `backend/grading/services.py`

**Contracts to satisfy**:
- `grading.tasks.GradingService.finalize_copy` must be patchable
- `grading.tasks.PDFProcessor.import_pdf` must be patchable
- Copy not found → return `{'status': 'error', 'error': '...not found...'}`

---

### [ ] Step: Create PDFProcessor class

Since tests expect `grading.tasks.PDFProcessor.import_pdf` but it doesn't exist:
- Add `PDFProcessor` class to `backend/grading/services.py`
- Implement static method `import_pdf(exam, pdf_file, user, anonymous_id=None)`
- Wrap existing `GradingService.import_pdf()` to maintain backwards compatibility
- Handle `anonymous_id` parameter (GradingService.import_pdf doesn't accept it currently)

**Implementation**:
```python
class PDFProcessor:
    @staticmethod
    def import_pdf(exam, pdf_file, user, anonymous_id=None):
        return GradingService.import_pdf(exam, pdf_file, user)
```

---

### [ ] Step: Fix module-level exports in tasks.py

Make `GradingService` and `PDFProcessor` accessible at module level:
- Add imports at top of `backend/grading/tasks.py` (after logger, before first task):
  ```python
  from grading.services import GradingService, PDFProcessor
  ```
- Remove local import `from grading.services import GradingService` at line 39 (inside `async_finalize_copy`)
- Remove local import `from grading.services import GradingService` at line 99 (inside `async_import_pdf`)
- Update `async_import_pdf` line 113: use `PDFProcessor.import_pdf()` instead of `GradingService.import_pdf()`

**Verification**: `python -c "from grading.tasks import GradingService, PDFProcessor"` succeeds

---

### [ ] Step: Fix Copy.DoesNotExist error handling

Test `test_async_finalize_copy_not_found` (line 63-70) expects graceful error response:
- Wrap `Copy.objects.get(id=copy_id)` in `async_finalize_copy` (line 41)
- Catch `Copy.DoesNotExist` exception
- Return `{'status': 'error', 'error': 'Copy not found', 'copy_id': str(copy_id)}`
- Don't re-raise or retry when copy doesn't exist

**Pattern**:
```python
try:
    copy = Copy.objects.get(id=copy_id)
except Copy.DoesNotExist:
    return {
        'copy_id': str(copy_id),
        'status': 'error',
        'error': 'Copy not found'
    }
```

---

### [ ] Step: Run targeted tests locally

Execute tests before committing:
```bash
cd /home/alaeddine/viatique__PMF/backend
../backend/venv/bin/python -m pytest grading/tests/test_tasks.py -v > /tmp/zf_A2_tasks.txt 2>&1
echo "RC=$?" >> /tmp/zf_A2_tasks.txt
```

**Success criteria**:
- `test_async_finalize_success` PASSED
- `test_async_finalize_handles_errors` PASSED
- `test_async_finalize_copy_not_found` PASSED
- `test_async_import_success` PASSED
- `test_async_import_handles_errors` PASSED
- `test_cleanup_removes_old_files` PASSED
- `test_cleanup_handles_missing_directory` PASSED
- Exit code: 0

**If failures occur**: Analyze traceback, verify patch targets, check return value formats

---

### [ ] Step: Commit changes atomically

Commit only the fixed files:
```bash
cd /home/alaeddine/viatique__PMF
git add backend/grading/tasks.py backend/grading/services.py
git commit -m "fix(grading): expose GradingService/PDFProcessor at module level for test patching

- Add PDFProcessor class wrapping GradingService.import_pdf
- Move imports to module level in tasks.py (was inside functions)
- Handle Copy.DoesNotExist in async_finalize_copy
- Update async_import_pdf to use PDFProcessor.import_pdf

Fixes AttributeError in grading/tests/test_tasks.py"
```

**Verification**: `git show --stat` shows only 2 files changed

---

### [ ] Step: Push and verify CI

Push to remote and monitor CI:
```bash
cd /home/alaeddine/viatique__PMF
git push -u origin zf/A2-grading-tasks-exports
```

Get CI run ID and check results:
- Note the CI run ID from push output or GitHub Actions
- Wait for completion
- If red: use `--log-failed` to inspect failures
- Document final status

**Deliverables**:
- Diff of changes (git diff main...zf/A2-grading-tasks-exports)
- Local test RC=0
- CI run ID and status

---

## Success Criteria

✅ `grading.tasks.GradingService` is patchable by tests
✅ `grading.tasks.PDFProcessor` exists and is patchable  
✅ `async_finalize_copy` handles `Copy.DoesNotExist` gracefully
✅ All 7 tests in `test_tasks.py` pass locally (RC=0)
✅ CI workflow/e2e/import tests pass
✅ No regression in other grading tests
