# Data Integrity & State Management Inventory

**Audit Phase**: Phase 1 - Inventory
**Component**: Data Integrity & State Management
**Date**: 2026-01-27
**Status**: COMPLETED

---

## 1. STATE MACHINES

### 1.1 Copy Status State Machine

**Model**: `exams.models.Copy`
**Location**: `backend/exams/models.py:99-103`

**States**:
```python
class Status(models.TextChoices):
    STAGING = 'STAGING'   # Initial state after import/split
    READY = 'READY'       # Validated, ready for correction
    LOCKED = 'LOCKED'     # Being corrected by a teacher
    GRADED = 'GRADED'     # Finalized with final PDF
```

**Valid Transitions**:
```
STAGING → READY       (via GradingService.validate_copy)
READY → LOCKED        (via GradingService.lock_copy)
LOCKED → READY        (via GradingService.unlock_copy)
LOCKED → GRADED       (via GradingService.finalize_copy)
READY → GRADED        (via GradingService.finalize_copy - allowed)
```

**State Enforcement**:
- Service layer: `backend/grading/services.py` (GradingService)
- State checks via `if copy.status != Copy.Status.XXX` before transitions
- **NO DATABASE CONSTRAINTS** on state transitions (only application-level)

**Audit Trail**:
- Each transition logged in `GradingEvent` model
- Timestamps tracked: `validated_at`, `locked_at`, `graded_at`
- Actor tracked: `locked_by` (ForeignKey to User)

**CRITICAL FINDINGS**:
- ❌ **P0**: No database-level state machine validation (constraints/triggers)
- ❌ **P0**: No `select_for_update()` on state transitions → race conditions possible
- ❌ **P1**: Annotation operations check `status == READY` but allow modifications on LOCKED copies in service logic inconsistency (services.py:61 vs services.py:94)

---

## 2. ATOMIC TRANSACTIONS

### 2.1 Transaction Boundaries

**Locations with `@transaction.atomic`**:

1. **AnnotationService** (`backend/grading/services.py`):
   - `add_annotation()` (line 59)
   - `update_annotation()` (line 92)
   - `delete_annotation()` (line 126)

2. **GradingService** (`backend/grading/services.py`):
   - `import_pdf()` (line 163)
   - `validate_copy()` (line 251)
   - `lock_copy()` (line 277)
   - `unlock_copy()` (line 295)
   - `finalize_copy()` (line 316)

3. **PDFSplitter** (`backend/processing/services/pdf_splitter.py`):
   - `split_exam()` (line 40)

### 2.2 Transaction Scope Analysis

**Good Practices**:
- ✅ Annotation create/update/delete are atomic with audit event creation
- ✅ State transitions are atomic with timestamp updates
- ✅ PDF import atomic with booklet creation and rasterization

**CRITICAL ISSUES**:
- ❌ **P0**: No pessimistic locking (`select_for_update()`) in concurrent operations
- ❌ **P0**: Race condition in `lock_copy()` - two users can check `status == READY` simultaneously
- ❌ **P0**: Race condition in `finalize_copy()` - double finalization possible
- ❌ **P1**: `import_pdf()` catches generic Exception but only raises ValueError (line 216)
- ❌ **P1**: No rollback handler or cleanup on transaction failure

### 2.3 Missing Transactions

**Areas without explicit transaction protection**:
- Copy identification (`exams/views.py:320`) - not atomic with audit logging
- Merge booklets (`exams/views.py:219`) - no transaction wrapper
- CSV export loops (`exams/views.py:246`) - no transaction for bulk operations

---

## 3. DATA VALIDATION

### 3.1 File Validation (PDF)

**Location**: `backend/exams/validators.py`

**Validators Applied**:
1. `validate_pdf_size()` - Max 50MB
2. `validate_pdf_not_empty()` - Not 0 bytes
3. `validate_pdf_mime_type()` - application/pdf or application/x-pdf via python-magic
4. `validate_pdf_integrity()` - PyMuPDF integrity check, 0-500 pages limit

**Applied to**:
- `Exam.pdf_source` (exams/models.py:17-29)
- `Copy.pdf_source` (exams/models.py:128-140)

**Findings**:
- ✅ Comprehensive PDF validation
- ✅ Graceful degradation on MIME library failure (logs warning, continues)
- ⚠️ **P2**: 500 page limit is arbitrary, not documented in business rules

### 3.2 Annotation Validation

**Serializer Validation** (`backend/grading/serializers.py:29-46`):
- Coordinates in [0,1] range
- x + w ≤ 1, y + h ≤ 1
- page_index ≥ 0

**Service Validation** (`backend/grading/services.py:26-56`):
- Same coordinate checks with epsilon tolerance (1e-9)
- Page index bounds check against total pages
- Status check (must be READY for annotation operations)

**Findings**:
- ✅ Dual validation (serializer + service)
- ✅ Epsilon tolerance for float precision
- ❌ **P1**: Inconsistency - service checks `status == READY` for add (line 61) but also for update (line 94), yet annotations can exist on LOCKED copies

### 3.3 Grading Structure Validation

**Location**: `backend/exams/serializers.py:33-64`

**Recursive Validation**:
- Must be JSON list
- Each node must be dict with 'label'
- 'points' must be positive float
- Recursive children validation

**Findings**:
- ✅ Comprehensive recursive validation
- ⚠️ **P2**: No maximum depth check (could cause stack overflow on malicious input)
- ⚠️ **P2**: No total points validation (sum of all points)

### 3.4 Model-Level Validation

**Field Validators**:
- `FileExtensionValidator(['pdf'])` on PDF fields
- `unique=True` on Copy.anonymous_id
- `unique=True` on Student.ine
- `unique_together = ['copy', 'owner']` on DraftState

**Missing Validations**:
- ❌ **P1**: No check that booklets belong to same exam when creating Copy
- ❌ **P1**: No validation that page_index is within booklet page count
- ❌ **P2**: No validation that exam.date is not in future (business rule)

---

## 4. CONCURRENCY CONTROLS

### 4.1 Soft Lock Mechanism

**Model**: `grading.models.CopyLock`
**Location**: `backend/grading/models.py:146-182`

**Fields**:
- `copy`: OneToOneField (only one lock per copy)
- `owner`: ForeignKey to User
- `token`: UUID (session token)
- `locked_at`: Timestamp
- `expires_at`: Timestamp with db_index

**Lock Enforcement**:
- Permission class: `IsLockedByOwnerOrReadOnly` (grading/permissions.py)
- Checked on annotation create/update/delete operations

**CRITICAL ISSUES**:
- ❌ **P0**: Lock acquisition not using `select_for_update()` → double-lock possible
- ❌ **P0**: No automatic lock cleanup on expiry (cron job or background task missing)
- ❌ **P1**: Lock expiry not checked in permission class (only owner check)
- ❌ **P1**: No mechanism to force-unlock as admin

### 4.2 Draft State (Autosave)

**Model**: `grading.models.DraftState`
**Location**: `backend/grading/models.py:185-231`

**Fields**:
- `copy`: ForeignKey (many drafts per copy)
- `owner`: ForeignKey to User
- `payload`: JSON (editor state)
- `lock_token`: UUID (link to CopyLock)
- `client_id`: UUID (anti-overwrite)
- `version`: PositiveIntegerField
- `unique_together`: ['copy', 'owner'] (one draft per user per copy)

**Version Control**:
- Optimistic concurrency via `version` field
- Client-side `client_id` for multi-tab detection

**CRITICAL ISSUES**:
- ❌ **P0**: No optimistic locking enforcement (no check on version before update)
- ❌ **P1**: No draft cleanup mechanism (old drafts accumulate)
- ❌ **P1**: Draft not deleted on finalize (stale data)

### 4.3 Race Condition Analysis

**Test Coverage**: `backend/grading/tests/test_concurrency.py`

**Test Cases**:
1. `test_concurrent_annotation_updates_sequential_lww` - Last Write Wins simulation
2. `test_double_finalize_race` - Incomplete (mocked, not testing real race)

**Findings**:
- ⚠️ Test comment (line 110): "For True Concurrency, we need `select_for_update`"
- ❌ **P0**: No actual concurrent test execution (SQLite limitation acknowledged)
- ❌ **P0**: No `select_for_update()` usage in any service method
- ❌ **P0**: Tests acknowledge the gap but don't enforce the fix

**Race Condition Scenarios**:

1. **Double Lock**:
   ```
   T1: Check status == READY ✓
   T2: Check status == READY ✓
   T1: Set status = LOCKED, save
   T2: Set status = LOCKED, save  (OVERWRITES T1)
   Result: Two users think they have lock
   ```

2. **Double Finalize**:
   ```
   T1: Check status in [LOCKED, READY] ✓
   T2: Check status in [LOCKED, READY] ✓
   T1: Generate PDF, set GRADED
   T2: Generate PDF, set GRADED  (WASTES RESOURCES)
   Result: PDF generated twice, potential file corruption
   ```

3. **Lost Update (Annotations)**:
   ```
   T1: Read annotation (score=5)
   T2: Read annotation (score=5)
   T1: Update score=10, save
   T2: Update score=15, save  (OVERWRITES T1)
   Result: T1's update lost
   ```

---

## 5. AUDIT TRAIL

### 5.1 Grading Events

**Model**: `grading.models.GradingEvent`
**Location**: `backend/grading/models.py:88-143`

**Tracked Actions**:
- IMPORT, VALIDATE, LOCK, UNLOCK
- CREATE_ANN, UPDATE_ANN, DELETE_ANN
- FINALIZE, EXPORT

**Audit Coverage**:
- ✅ All state transitions logged
- ✅ All annotation CRUD logged
- ✅ Actor and timestamp tracked
- ✅ Metadata field for context (JSON)

**CRITICAL ISSUES**:
- ❌ **P0**: GradingEvent.copy is `on_delete=CASCADE` → deleting copy deletes audit trail
- ❌ **P0**: Should be `on_delete=PROTECT` or separate audit table
- ⚠️ **P1**: No retention policy (audit log grows indefinitely)

### 5.2 Centralized Audit Log

**Model**: `core.models.AuditLog`
**Location**: `backend/core/models.py:28-92`

**Tracked Events**:
- Authentication (login.success, login.failed)
- Data access (copy.download, copy.view)
- Workflow actions (copy.lock, copy.unlock, copy.finalize)

**Audit Utilities**: `backend/core/utils/audit.py`
- `log_audit()` - Generic audit logging
- `log_authentication_attempt()` - Login/logout
- `log_data_access()` - Sensitive data access
- `log_workflow_action()` - Copy workflow

**Coverage Analysis**:
- ✅ CopyFinalPdfView logs downloads (views.py:244)
- ✅ StudentCopiesView logs list access (exams/views.py:377)
- ❌ **P1**: Missing audit on Copy creation, deletion
- ❌ **P1**: Missing audit on Exam upload, processing
- ❌ **P1**: Missing audit on identification actions

**Data Retention**:
- ⚠️ **P1**: No TTL or archival policy
- ⚠️ **P1**: Indexes on action+timestamp, resource, student_id but no partition strategy

---

## 6. CASCADE DELETIONS & REFERENTIAL INTEGRITY

### 6.1 Cascade Matrix

| Parent → Child | Relation | on_delete | Risk Assessment |
|---|---|---|---|
| Exam → Booklet | FK | CASCADE | ✅ OK (booklets part of exam) |
| Exam → Copy | FK | CASCADE | ✅ OK (copies part of exam) |
| Booklet → Copy (M2M) | M2M | - | ✅ Handled by Django |
| Copy → Annotation | FK | CASCADE | ✅ OK (annotations belong to copy) |
| Copy → GradingEvent | FK | CASCADE | ❌ **P0** (loses audit trail) |
| Copy → CopyLock | OneToOne | CASCADE | ✅ OK (lock lifecycle tied to copy) |
| Copy → DraftState | FK | CASCADE | ✅ OK (drafts belong to copy) |
| Copy → OCRResult | OneToOne | CASCADE | ✅ OK (OCR result tied to copy) |
| Copy ← Student | FK | SET_NULL | ✅ Good (student deletion safe) |
| Annotation ← User (created_by) | FK | PROTECT | ✅ Good (prevents user deletion) |
| GradingEvent ← User (actor) | FK | PROTECT | ✅ Good (protects audit integrity) |
| CopyLock ← User (owner) | FK | CASCADE | ⚠️ **P1** (deleting user deletes locks) |
| DraftState ← User (owner) | FK | CASCADE | ⚠️ **P1** (deleting user deletes drafts) |
| Student ← User | OneToOne | SET_NULL | ✅ Good (student profile preserved) |

### 6.2 Soft Delete Requirements

**Currently NO soft delete implemented**

**Should Have Soft Delete**:
- ❌ **P1**: Copy (historical data, audit requirements)
- ❌ **P1**: Exam (archival, year-over-year reports)
- ❌ **P2**: Annotation (correction history, disputes)

**Hard Delete Acceptable**:
- ✅ Booklet (intermediate processing artifact)
- ✅ CopyLock (ephemeral state)
- ✅ DraftState (temporary data)

---

## 7. CRITICAL DATA FLOWS

### 7.1 Import → Process → Ready Flow

```
1. ExamUploadView.post()
   - Create Exam
   - PDFSplitter.split_exam() [@transaction.atomic]
     - Create Booklets
     - Extract pages (PNG)
   - Create Copies (STAGING)
   
2. GradingService.validate_copy() [@transaction.atomic]
   - Check status == STAGING
   - Check pages exist
   - Set status = READY
   - Set validated_at
   - Create GradingEvent(VALIDATE)
```

**Integrity Checks**:
- ✅ Atomic booklet creation
- ✅ Pages extracted before READY
- ❌ **P1**: No rollback if PNG extraction fails mid-batch

### 7.2 Lock → Annotate → Finalize Flow

```
1. GradingService.lock_copy() [@transaction.atomic]
   - Check status == READY
   - Set status = LOCKED
   - Set locked_at, locked_by
   - Create GradingEvent(LOCK)

2. AnnotationService.add_annotation() [@transaction.atomic]
   - Check copy.status == READY (❌ BUG: should be LOCKED)
   - Validate coordinates
   - Create Annotation
   - Create GradingEvent(CREATE_ANN)

3. GradingService.finalize_copy() [@transaction.atomic]
   - Check status in [LOCKED, READY]
   - Compute score
   - PDFFlattener.flatten_copy() [NOT atomic]
   - Set status = GRADED
   - Set graded_at
   - Create GradingEvent(FINALIZE)
```

**Integrity Issues**:
- ❌ **P0**: Annotation service checks `status == READY` but should check `status == LOCKED` (services.py:61)
- ❌ **P0**: PDF flattening not in transaction boundary → partial state on failure
- ❌ **P1**: No cleanup of CopyLock on finalize

### 7.3 Student Portal Access Flow

```
1. Student login (session-based)
   - Set session['student_id']
   - Log authentication

2. StudentCopiesView.list()
   - Filter Copy.objects.filter(student_id, status=GRADED)
   - Compute score
   - Return data

3. CopyFinalPdfView.get()
   - Check status == GRADED
   - Check student ownership
   - Log download
   - Serve PDF
```

**Integrity Checks**:
- ✅ Only GRADED copies accessible
- ✅ Student ownership verified
- ✅ Download audited
- ❌ **P2**: No rate limiting on PDF downloads

---

## 8. INDEXES & PERFORMANCE

### 8.1 Existing Indexes

**Annotation** (grading/models.py:80-82):
```python
indexes = [
    models.Index(fields=['copy', 'page_index']),
]
```

**GradingEvent** (grading/models.py:138-140):
```python
indexes = [
    models.Index(fields=['copy', 'timestamp']),
]
```

**AuditLog** (core/models.py:83-87):
```python
indexes = [
    models.Index(fields=['action', '-timestamp']),
    models.Index(fields=['resource_type', 'resource_id']),
    models.Index(fields=['student_id', '-timestamp']),
]
```

**CopyLock** (grading/models.py:174):
```python
expires_at = models.DateTimeField(db_index=True)
```

### 8.2 Missing Indexes

**High Priority**:
- ❌ **P1**: Copy(status, exam) - frequent filter in list views
- ❌ **P1**: Copy(student_id, status) - student portal queries
- ❌ **P1**: Annotation(created_by) - permission checks
- ❌ **P2**: Booklet(exam, start_page) - ordering queries

---

## 9. IDENTIFIED RISKS SUMMARY

### P0 - Critical (Production Blockers)

1. **No pessimistic locking on state transitions**
   - File: `backend/grading/services.py`
   - Impact: Race conditions on lock/unlock/finalize
   - Fix: Add `.select_for_update()` on all state-changing queries

2. **GradingEvent cascade deletion**
   - File: `backend/grading/models.py:108`
   - Impact: Deleting copy deletes audit trail (compliance violation)
   - Fix: Change to `on_delete=PROTECT` or move to separate audit DB

3. **Annotation status check inconsistency**
   - File: `backend/grading/services.py:61,94`
   - Impact: Can annotate copies that are not in correct state
   - Fix: Enforce `status == LOCKED` for annotation operations

4. **No optimistic locking on DraftState**
   - File: `backend/grading/models.py:219`
   - Impact: Concurrent autosave overwrites without conflict detection
   - Fix: Check version before update, return conflict error

5. **PDF flattening not in transaction**
   - File: `backend/grading/services.py:327`
   - Impact: Status set to GRADED even if PDF generation fails
   - Fix: Move PDF generation into transaction or add rollback handler

### P1 - High Severity (Should Fix Before Production)

6. **No lock expiry enforcement**
   - Impact: Expired locks not automatically released
   - Fix: Background task to cleanup expired locks

7. **No draft cleanup**
   - Impact: Stale drafts accumulate in database
   - Fix: Delete drafts on finalize, add TTL

8. **Missing indexes on hot paths**
   - Impact: Slow queries on student portal, copy lists
   - Fix: Add composite indexes on (status, exam), (student_id, status)

9. **Missing audit on critical actions**
   - Impact: Incomplete audit trail for compliance
   - Fix: Add audit logging to exam upload, copy deletion, identification

10. **Cascade deletion of locks/drafts on user deletion**
    - Impact: User deletion orphans locked copies
    - Fix: Change to SET_NULL or PROTECT

### P2 - Medium Severity (Technical Debt)

11. **No soft delete on Copy/Exam**
    - Impact: Hard deletes prevent historical analysis
    - Fix: Add deleted_at field, filter by default

12. **No grading structure depth limit**
    - Impact: Stack overflow on malicious input
    - Fix: Add max depth validation (e.g., 10 levels)

13. **No rate limiting on PDF downloads**
    - Impact: Resource exhaustion via repeated downloads
    - Fix: Add rate limiting middleware

---

## 10. RECOMMENDATIONS

### Immediate Actions (P0)

1. **Add pessimistic locking**:
   ```python
   def lock_copy(copy: Copy, user):
       with transaction.atomic():
           copy = Copy.objects.select_for_update().get(pk=copy.pk)
           if copy.status != Copy.Status.READY:
               raise ValueError("...")
           # ... rest of logic
   ```

2. **Fix GradingEvent cascade**:
   ```python
   copy = models.ForeignKey(Copy, on_delete=models.PROTECT)
   ```

3. **Fix annotation status check**:
   ```python
   def add_annotation(copy: Copy, ...):
       if copy.status != Copy.Status.LOCKED:
           raise ValueError("Copy must be LOCKED to add annotations")
   ```

### Short-term (P1)

4. Implement lock expiry cleanup (Celery periodic task)
5. Add draft cleanup on finalize
6. Add missing database indexes
7. Complete audit logging coverage

### Long-term (P2)

8. Implement soft delete pattern
9. Add depth validation to grading structure
10. Implement rate limiting

---

## 11. VERIFICATION COMMANDS

```bash
# Check for select_for_update usage
cd backend
grep -r "select_for_update" --include="*.py"
# Expected: Only in test file (CURRENTLY)
# Should be: In services.py for lock/unlock/finalize

# Check cascade deletions
grep -r "on_delete=models.CASCADE" --include="*.py" | grep -E "(GradingEvent|AuditLog)"

# Check transaction usage
grep -r "@transaction.atomic" --include="*.py"

# Check indexes
grep -r "class Meta:" -A 5 --include="*.py" backend/*/models.py | grep -E "(indexes|index_together)"

# Run concurrency tests
pytest backend/grading/tests/test_concurrency.py -v
```

---

## CONCLUSION

The data integrity and state management implementation has **solid foundations** but contains **critical race condition vulnerabilities** that MUST be addressed before production deployment.

**Strengths**:
- ✅ Well-defined state machine with audit trail
- ✅ Comprehensive validation at multiple layers
- ✅ Atomic transaction boundaries on most operations
- ✅ Good cascade deletion strategy (mostly)

**Critical Gaps** (P0):
- ❌ No pessimistic locking → race conditions
- ❌ Audit trail cascade deletion → compliance risk
- ❌ Service logic inconsistencies (status checks)

**Verdict**: **NOT READY** for production without P0 fixes.

**Risk Score**: 7/10 (HIGH) - Data integrity at risk under concurrent load.
