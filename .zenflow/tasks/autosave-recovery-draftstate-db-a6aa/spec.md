# Technical Specification
## AUTOSAVE + RECOVERY (DraftState DB + localStorage)

**Task ID**: ZF-AUD-06  
**Created**: 2026-01-31  
**Status**: Technical Specification  
**PRD Reference**: requirements.md

---

## 1. Technical Context

### 1.1 Technology Stack

**Backend**:
- **Framework**: Django 4.2 LTS
- **Database**: PostgreSQL 15+
- **Testing**: pytest 8.0, pytest-django 4.8
- **API**: Django REST Framework
- **ORM**: Django ORM with F() expressions for atomic operations

**Frontend**:
- **Framework**: Vue 3.4.15 (Composition API)
- **Build Tool**: Vite 5.1.0
- **HTTP Client**: Axios 1.13.2
- **Testing**: Playwright 1.57.0
- **Type Checking**: TypeScript 5.9.3, vue-tsc 3.2.2
- **Linting**: ESLint 9.39.2, eslint-plugin-vue 10.7.0

**Existing Components**:
- `backend/grading/models.py:214-260` - DraftState model
- `backend/grading/views_draft.py` - Draft API endpoints (GET, PUT, DELETE)
- `backend/grading/views.py:170` - GRADED status protection pattern
- `frontend/src/views/admin/CorrectorDesk.vue:364-395` - Autosave implementation
- `frontend/src/utils/storage.js` - localStorage utilities with TTL and quota management

### 1.2 Dependencies

**Backend**:
- `django>=4.2,<5.0`
- `djangorestframework`
- `pytest~=8.0`
- `pytest-django~=4.8`

**Frontend**:
- `@playwright/test: ^1.57.0`
- `vue: ^3.4.15`
- `axios: ^1.13.2`

---

## 2. Implementation Approach

### 2.1 Architecture Overview

The autosave system uses a **dual-layer persistence strategy**:

```
┌─────────────────────────────────────────────────────────┐
│                    CorrectorDesk.vue                     │
│                                                          │
│  ┌──────────────────────────────────────────────────┐  │
│  │  draftAnnotation (reactive state)                │  │
│  └────────┬─────────────────────────────────┬───────┘  │
│           │                                  │          │
│           ▼                                  ▼          │
│  ┌─────────────────┐              ┌─────────────────┐  │
│  │  localStorage   │              │   Server API    │  │
│  │  (300ms)        │              │   (2000ms)      │  │
│  └─────────────────┘              └─────────────────┘  │
│           │                                  │          │
│           ▼                                  ▼          │
│  ┌─────────────────┐              ┌─────────────────┐  │
│  │  Browser Local  │              │  DraftState DB  │  │
│  │  draft_{id}     │              │  (PostgreSQL)   │  │
│  └─────────────────┘              └─────────────────┘  │
│                                                          │
│  Recovery: Compare timestamps → Prefer local if newer   │
└─────────────────────────────────────────────────────────┘
```

### 2.2 Existing Implementation Analysis

**Current State** (from requirements.md):
- ✅ DraftState model with unique constraint (copy, owner)
- ✅ Draft endpoints (GET, PUT, DELETE)
- ✅ Dual autosave (300ms local, 2s server)
- ✅ Lock token validation in PUT
- ✅ client_id conflict detection
- ✅ Recovery logic with timestamp comparison
- ✅ localStorage quota management

**Missing Components**:
- ❌ Backend unit tests for DraftState endpoints
- ❌ GRADED status protection in views_draft.py
- ❌ E2E test for 100% state fidelity verification
- ❌ Autosave frequency audit documentation

### 2.3 Reusable Patterns from Codebase

#### 2.3.1 Status Protection Pattern
**Reference**: `backend/grading/views.py:170-171`

```python
if copy.status == Copy.Status.GRADED:
    return Response({"detail": "Copy already graded."}, status=status.HTTP_400_BAD_REQUEST)
```

**Application**: Add identical check to `DraftReturnView.put()` before lock validation.

#### 2.3.2 Permission Testing Pattern
**Reference**: `backend/conftest.py:39-54`

```python
@pytest.fixture
def teacher_user(db):
    User = get_user_model()
    user = User.objects.create_user(
        username="teacher_test",
        password="testpass123",
        is_staff=True,
        is_superuser=False
    )
    g, _ = Group.objects.get_or_create(name=UserRole.TEACHER)
    user.groups.add(g)
    return user
```

**Application**: Use existing fixtures (`teacher_user`, `api_client`) for draft endpoint tests.

#### 2.3.3 E2E Autosave Pattern
**Reference**: `frontend/tests/e2e/corrector_flow.spec.ts:99-117`

```typescript
const restoreTitle = page.getByText(/Restaurer le brouillon non sauvegardé/i);
const shouldRestore = await restoreTitle.isVisible({ timeout: 4000 }).catch(() => false);
if (shouldRestore) {
    await page.getByRole('button', { name: /Oui, restaurer/i }).click();
}
```

**Application**: Extend existing E2E test to verify exact state restoration (rect coordinates, content, score).

---

## 3. Source Code Structure Changes

### 3.1 New Files

```
backend/grading/tests/
├── test_draft_endpoints.py       # Backend unit tests (NEW)

.zenflow/tasks/autosave-recovery-draftstate-db-a6aa/
├── audit.md                       # Autosave frequency audit (NEW)
```

### 3.2 Modified Files

```
backend/grading/
├── views_draft.py                 # Add GRADED status check

frontend/tests/e2e/
├── corrector_flow.spec.ts         # Extend with state fidelity checks

docs/technical/
├── BUSINESS_WORKFLOWS.md          # Update autosave frequency (line 368)
```

### 3.3 File Responsibilities

#### 3.3.1 `backend/grading/tests/test_draft_endpoints.py`
**Purpose**: Comprehensive unit tests for DraftState API endpoints  
**Dependencies**: pytest, pytest-django, DRF test client  
**Test Coverage**:
- Draft save/load/delete operations
- Lock token validation
- client_id conflict detection
- Owner-only access (permissions)
- GRADED status protection (NEW requirement)

**Test Structure**:
```python
@pytest.mark.django_db
class TestDraftEndpoints:
    def test_save_draft_with_valid_lock(self, ...)
    def test_load_draft_as_owner(self, ...)
    def test_save_to_graded_copy_forbidden(self, ...)  # NEW
    def test_client_id_conflict(self, ...)
    # ... (full list in section 4.2)
```

#### 3.3.2 `backend/grading/views_draft.py`
**Modification**: Add GRADED status gate in `DraftReturnView.put()`  
**Location**: After line 62 (copy retrieval), before lock validation  
**Code Pattern**:
```python
copy = get_object_or_404(Copy, id=copy_id)

# NEW: GRADED status protection
if copy.status == Copy.Status.GRADED:
    return _handle_value_error(
        "Cannot save draft to GRADED copy.",
        context=context
    )

token = request.headers.get('X-Lock-Token') or request.data.get('token')
# ... existing lock validation
```

#### 3.3.3 `frontend/tests/e2e/corrector_flow.spec.ts`
**Modification**: Add precise state verification after restore  
**Approach**:
1. Record exact draft state before refresh (rect, content, score, page)
2. After restore, verify editor contains identical values
3. Use Playwright's `expect().toHaveValue()` for text inputs
4. Compare numeric values for rect coordinates and score

**New Assertions** (extend existing test at line 125):
```typescript
// Verify exact state fidelity
await expect(page.locator('textarea')).toHaveValue('Test E2E Annotation');
await expect(page.locator('input[type="number"]')).toHaveValue('2');

// Verify rect was restored (check canvas annotation position)
const canvas = page.getByTestId('canvas-layer');
const annotation = canvas.locator('.annotation-rect').first();
await expect(annotation).toBeVisible();

// Verify page navigation
const pageIndicator = page.getByTestId('page-indicator');
await expect(pageIndicator).toContainText('Page 1'); // Restored to correct page
```

---

## 4. API & Data Model Changes

### 4.1 Data Model

**No Changes Required** - DraftState model is complete:
- ✅ Unique constraint (copy, owner)
- ✅ Atomic version increment via F() expression
- ✅ client_id field for session tracking
- ✅ JSONField for flexible payload

**Schema Reference** (`backend/grading/models.py:214-260`):
```python
class DraftState(models.Model):
    id = UUIDField(primary_key=True)
    copy = ForeignKey(Copy, CASCADE)
    owner = ForeignKey(User, CASCADE)
    payload = JSONField(default=dict)
    lock_token = UUIDField(null=True)
    client_id = UUIDField(null=True)
    version = PositiveIntegerField(default=1)
    updated_at = DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['copy', 'owner']
```

### 4.2 API Contract Changes

#### Endpoint: `PUT /api/grading/copies/<uuid:copy_id>/draft/`

**New Validation Rule**:
```json
{
  "rule": "GRADED status protection",
  "condition": "copy.status == 'GRADED'",
  "response": {
    "status": 400,
    "body": {
      "detail": "Cannot save draft to GRADED copy."
    }
  }
}
```

**Updated Error Contract**:
| Condition | Status | Response Body |
|-----------|--------|---------------|
| Missing lock token | 403 | `{"detail": "Missing lock token."}` |
| Invalid lock token | 403 | `{"detail": "Invalid lock token."}` |
| Lock owner mismatch | 409 | `{"detail": "Lock owner mismatch."}` |
| client_id conflict | 409 | `{"detail": "Draft conflict: Modified by another session."}` |
| **GRADED status** | **400** | **`{"detail": "Cannot save draft to GRADED copy."}`** *(NEW)* |

**Behavioral Change**:
- **Before**: GRADED copies could receive draft saves (no protection)
- **After**: GRADED copies reject draft saves with 400 Bad Request
- **Impact**: Frontend autosave will fail silently if copy becomes GRADED during editing

---

## 5. Test Scenarios

### 5.1 Backend Unit Tests

#### Test Suite: `backend/grading/tests/test_draft_endpoints.py`

**Fixtures Required**:
- `api_client` (from conftest.py)
- `teacher_user` (from conftest.py)
- `exam_factory` (create via pytest fixture)
- `copy_factory` (create via pytest fixture)

**Test Cases**:

```python
@pytest.mark.django_db
class TestDraftEndpoints:
    
    # === HAPPY PATH ===
    
    def test_save_draft_with_valid_lock(self, api_client, teacher_user, copy_factory):
        """AC-2.1: Save draft with valid lock → 200 OK, version incremented"""
        copy = copy_factory(status='READY')
        lock = CopyLock.objects.create(copy=copy, owner=teacher_user, token=uuid.uuid4())
        
        api_client.force_authenticate(teacher_user)
        response = api_client.put(f'/api/grading/copies/{copy.id}/draft/', {
            'payload': {'rect': [10, 20, 100, 50], 'content': 'Test'},
            'token': str(lock.token),
            'client_id': str(uuid.uuid4())
        }, headers={'X-Lock-Token': str(lock.token)})
        
        assert response.status_code == 200
        assert response.data['status'] == 'SAVED'
        assert response.data['version'] == 1
        
        draft = DraftState.objects.get(copy=copy, owner=teacher_user)
        assert draft.payload['content'] == 'Test'
    
    def test_load_draft_as_owner(self, api_client, teacher_user, copy_factory):
        """AC-2.2: Load draft as owner → 200 OK, payload returned"""
        copy = copy_factory()
        client_id = uuid.uuid4()
        DraftState.objects.create(
            copy=copy, 
            owner=teacher_user, 
            payload={'content': 'Draft content'},
            client_id=client_id,
            version=3
        )
        
        api_client.force_authenticate(teacher_user)
        response = api_client.get(f'/api/grading/copies/{copy.id}/draft/')
        
        assert response.status_code == 200
        assert response.data['payload']['content'] == 'Draft content'
        assert response.data['version'] == 3
        assert response.data['client_id'] == str(client_id)
    
    def test_load_non_existent_draft(self, api_client, teacher_user, copy_factory):
        """AC-2.3: Load non-existent draft → 204 No Content"""
        copy = copy_factory()
        
        api_client.force_authenticate(teacher_user)
        response = api_client.get(f'/api/grading/copies/{copy.id}/draft/')
        
        assert response.status_code == 204
    
    # === PERMISSIONS ===
    
    def test_save_without_lock_token(self, api_client, teacher_user, copy_factory):
        """AC-2.4: Save without lock token → 403 Forbidden"""
        copy = copy_factory()
        
        api_client.force_authenticate(teacher_user)
        response = api_client.put(f'/api/grading/copies/{copy.id}/draft/', {
            'payload': {'content': 'Test'},
            'client_id': str(uuid.uuid4())
        })
        
        assert response.status_code == 403
        assert 'lock token' in response.data['detail'].lower()
    
    def test_save_with_wrong_lock_owner(self, api_client, teacher_user, copy_factory):
        """AC-2.5: Save with wrong lock owner → 409 Conflict"""
        copy = copy_factory()
        other_user = User.objects.create_user(username='other', password='test')
        lock = CopyLock.objects.create(copy=copy, owner=other_user, token=uuid.uuid4())
        
        api_client.force_authenticate(teacher_user)
        response = api_client.put(f'/api/grading/copies/{copy.id}/draft/', {
            'payload': {'content': 'Test'},
            'token': str(lock.token),
            'client_id': str(uuid.uuid4())
        }, headers={'X-Lock-Token': str(lock.token)})
        
        assert response.status_code == 409
        assert 'owner mismatch' in response.data['detail'].lower()
    
    # === GRADED PROTECTION (NEW) ===
    
    def test_save_to_graded_copy_forbidden(self, api_client, teacher_user, copy_factory):
        """AC-2.6: Save to GRADED copy → 400 Bad Request"""
        copy = copy_factory(status='GRADED')
        lock = CopyLock.objects.create(copy=copy, owner=teacher_user, token=uuid.uuid4())
        
        api_client.force_authenticate(teacher_user)
        response = api_client.put(f'/api/grading/copies/{copy.id}/draft/', {
            'payload': {'content': 'Test'},
            'token': str(lock.token),
            'client_id': str(uuid.uuid4())
        }, headers={'X-Lock-Token': str(lock.token)})
        
        assert response.status_code == 400
        assert 'GRADED' in response.data['detail']
        
        # Verify no draft was created
        assert not DraftState.objects.filter(copy=copy, owner=teacher_user).exists()
    
    # === CONFLICT DETECTION ===
    
    def test_client_id_conflict(self, api_client, teacher_user, copy_factory):
        """AC-2.7: client_id conflict → 409 Conflict"""
        copy = copy_factory()
        lock = CopyLock.objects.create(copy=copy, owner=teacher_user, token=uuid.uuid4())
        
        # Create existing draft with different client_id
        existing_client_id = uuid.uuid4()
        DraftState.objects.create(
            copy=copy,
            owner=teacher_user,
            payload={'content': 'Old'},
            client_id=existing_client_id,
            version=1
        )
        
        # Try to save with different client_id
        new_client_id = uuid.uuid4()
        api_client.force_authenticate(teacher_user)
        response = api_client.put(f'/api/grading/copies/{copy.id}/draft/', {
            'payload': {'content': 'New'},
            'token': str(lock.token),
            'client_id': str(new_client_id)
        }, headers={'X-Lock-Token': str(lock.token)})
        
        assert response.status_code == 409
        assert 'another session' in response.data['detail'].lower()
    
    def test_unauthorized_access(self, api_client, copy_factory):
        """AC-2.8: Unauthorized access → 403 Forbidden"""
        copy = copy_factory()
        
        # No authentication
        response = api_client.get(f'/api/grading/copies/{copy.id}/draft/')
        
        assert response.status_code in [401, 403]
    
    # === DELETION ===
    
    def test_delete_draft_as_owner(self, api_client, teacher_user, copy_factory):
        """Delete draft as owner → 204 No Content"""
        copy = copy_factory()
        DraftState.objects.create(copy=copy, owner=teacher_user, payload={'content': 'Test'})
        
        api_client.force_authenticate(teacher_user)
        response = api_client.delete(f'/api/grading/copies/{copy.id}/draft/')
        
        assert response.status_code == 204
        assert not DraftState.objects.filter(copy=copy, owner=teacher_user).exists()
```

**Fixtures to Create** (in test file):
```python
@pytest.fixture
def exam_factory(db):
    def create_exam(**kwargs):
        defaults = {
            'name': 'Test Exam',
            'date': timezone.now().date(),
            'grading_structure': {}
        }
        defaults.update(kwargs)
        return Exam.objects.create(**defaults)
    return create_exam

@pytest.fixture
def copy_factory(db, exam_factory):
    def create_copy(**kwargs):
        exam = kwargs.pop('exam', None) or exam_factory()
        defaults = {
            'exam': exam,
            'anonymous_id': f'TEST-{uuid.uuid4().hex[:8]}',
            'status': 'READY'
        }
        defaults.update(kwargs)
        return Copy.objects.create(**defaults)
    return create_copy
```

### 5.2 E2E Test Enhancement

#### Test: `frontend/tests/e2e/corrector_flow.spec.ts`

**Enhancement**: Add state fidelity verification

**Current Test** (line 7-147):
- ✅ Login → Lock → Annotate → Save → Refresh → Restore
- ❌ Does not verify exact state restoration

**New Assertions** (insert after line 125):
```typescript
// === NEW: 100% State Fidelity Verification ===

// 1. Verify textarea content
await expect(page.locator('textarea')).toHaveValue('Test E2E Annotation');

// 2. Verify score input
await expect(page.locator('input[type="number"]')).toHaveValue('2');

// 3. Verify annotation type selector
await expect(page.getByTestId('annotation-type-select')).toHaveValue('ERREUR');

// 4. Verify page was restored
const pageIndicator = page.getByTestId('page-indicator');
await expect(pageIndicator).toContainText('Page 1');

// 5. Verify canvas annotation rect exists
const canvas = page.getByTestId('canvas-layer');
const annotation = canvas.locator('.annotation-rect').first();
await expect(annotation).toBeVisible();

// 6. Verify rect coordinates (approximate - canvas rendering may vary)
const bbox = await annotation.boundingBox();
expect(bbox).toBeTruthy();
expect(bbox!.x).toBeGreaterThan(90);  // ~100px from drag
expect(bbox!.y).toBeGreaterThan(90);
```

**Expected Behavior**:
- Draft restoration must preserve ALL fields:
  - `rect`: Annotation coordinates
  - `content`: Textarea text
  - `score_delta`: Numeric input
  - `type`: Dropdown selection
  - `page_index`: Current page number

---

## 6. Autosave Frequency Audit

### 6.1 Audit Deliverable: `audit.md`

**Structure**:
```markdown
# Autosave Frequency Audit

## Trigger Analysis
- **localStorage**: 300ms debounce (CorrectorDesk.vue:383)
- **Server API**: 2000ms debounce (CorrectorDesk.vue:393)

## API Rate Calculation
- Max frequency: 1 request / 2s = 0.5 req/s per active user
- Concurrent users (peak): 50 correctors
- Peak load: 50 × 0.5 = 25 req/s to /draft/ endpoint

## Anti-Spam Verification
- ✅ Debounce prevents rapid-fire requests
- ✅ No autosave during read-only mode (line 366)
- ✅ No autosave without lock (line 388)

## Documentation Mismatch
- **Docs claim**: 30s autosave
- **Implementation**: 2s autosave
- **Action**: Update BUSINESS_WORKFLOWS.md line 368

## Recommendations
- Monitor /draft/ endpoint latency (P95 < 200ms)
- Add rate limiting: 10 req/min per user (failsafe)
```

### 6.2 Documentation Update

**File**: `docs/technical/BUSINESS_WORKFLOWS.md`  
**Line**: 368 (search for "autosave" or "30s")  
**Change**:
```diff
- Autosave: 30s interval to server
+ Autosave: 2s server + 300ms localStorage (dual-layer)
```

---

## 7. Delivery Phases

### Phase 1: Backend Validation (Day 1)
**Goal**: Ensure DraftState API is bulletproof

**Tasks**:
1. ✅ Create `test_draft_endpoints.py` with 10 test cases
2. ✅ Add GRADED status check to `views_draft.py:63-66`
3. ✅ Run backend tests: `pytest backend/grading/tests/test_draft_endpoints.py -v`
4. ✅ Verify all 10 tests pass

**Success Criteria**:
- 10/10 tests pass
- Coverage: 100% of DraftReturnView methods
- No regression in existing tests

### Phase 2: E2E Recovery Proof (Day 1)
**Goal**: Prove 100% reproducible recovery

**Tasks**:
1. ✅ Extend `corrector_flow.spec.ts` with state fidelity checks
2. ✅ Run E2E test: `npm run test:e2e -- corrector_flow.spec.ts`
3. ✅ Verify all assertions pass (including new 6 assertions)
4. ✅ Record screenshot/video of successful recovery

**Success Criteria**:
- E2E test passes consistently (3/3 runs)
- Restored state matches original (content, score, page, rect)
- No console errors during restore

### Phase 3: Audit & Documentation (Day 2)
**Goal**: Document findings and update stale docs

**Tasks**:
1. ✅ Create `audit.md` with frequency analysis
2. ✅ Update `BUSINESS_WORKFLOWS.md:368` with correct timing
3. ✅ Run full test suite: `pytest` + `npm run test:e2e`
4. ✅ Generate proof bundle (test output + screenshots)

**Success Criteria**:
- audit.md contains API rate calculation
- Documentation reflects implementation (2s, not 30s)
- All tests pass (backend + E2E)

---

## 8. Verification Approach

### 8.1 Backend Testing

**Commands**:
```bash
# Run draft endpoint tests only
pytest backend/grading/tests/test_draft_endpoints.py -v

# Run with coverage
pytest backend/grading/tests/test_draft_endpoints.py --cov=grading.views_draft --cov-report=term-missing

# Expected output:
# test_draft_endpoints.py::TestDraftEndpoints::test_save_draft_with_valid_lock PASSED
# test_draft_endpoints.py::TestDraftEndpoints::test_load_draft_as_owner PASSED
# test_draft_endpoints.py::TestDraftEndpoints::test_save_to_graded_copy_forbidden PASSED
# ... (10 tests total)
# 
# Coverage: 100% (views_draft.py lines 36-143)
```

**Failure Handling**:
- If `test_save_to_graded_copy_forbidden` fails → GRADED check not added
- If `test_client_id_conflict` fails → Regression in conflict detection
- Fix issues before proceeding to Phase 2

### 8.2 E2E Testing

**Commands**:
```bash
# Setup (ensure backend + frontend running)
cd backend && python manage.py runserver 8088 &
cd frontend && npm run dev &

# Run E2E test
cd frontend/e2e
npm run test:e2e -- corrector_flow.spec.ts --headed

# Expected output:
# ✓ Full Corrector Cycle: Login -> Lock -> Annotate -> Autosave -> Refresh -> Restore (35s)
```

**Verification Points**:
1. **Autosave Trigger**: Wait 3s after typing (2s debounce + buffer)
2. **Network Capture**: Verify PUT /draft/ request in console logs
3. **Restore Banner**: Must appear after refresh
4. **State Fidelity**: All 6 new assertions pass

**Failure Scenarios**:
- Banner doesn't appear → Check localStorage key format
- Restore fails → Check server draft client_id adoption (line 331)
- Wrong page → Check page_index restoration (line 338)

### 8.3 Lint & Type Check

**Commands**:
```bash
# Frontend
cd frontend
npm run lint        # ESLint check
npm run typecheck   # TypeScript validation

# Backend
cd backend
ruff check grading/  # If ruff is configured (not in requirements.txt, skip if absent)
```

**Expected**: No new warnings or errors introduced.

---

## 9. Risks & Mitigations

### 9.1 Technical Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| **GRADED check breaks existing flow** | High | Add defensive check early in PUT method; verify with existing E2E tests |
| **localStorage quota exceeded mid-session** | Medium | Already mitigated by `storage.js:26-43` (auto-cleanup) |
| **E2E test flakiness** | Low | Use explicit waits; retry on network failures |
| **Multi-tab conflict not covered** | Low | Out of scope; existing 409 handling sufficient |

### 9.2 Integration Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| **Backend tests require PostgreSQL** | Low | Use pytest-django with `@pytest.mark.django_db` |
| **E2E requires seeded data** | Medium | Ensure E2E-READY copy exists (see `corrector_flow.spec.ts:44`) |
| **Draft cleanup race condition** | Low | Use atomic DELETE in views_draft.py:141 |

---

## 10. Acceptance Checklist

### Backend (AC-2)
- [ ] ✅ 10 unit tests in `test_draft_endpoints.py`
- [ ] ✅ All tests pass (`pytest -v`)
- [ ] ✅ GRADED status check in `views_draft.py`
- [ ] ✅ No regression (run full backend test suite)

### E2E (AC-3)
- [ ] ✅ State fidelity assertions added to `corrector_flow.spec.ts`
- [ ] ✅ Test passes 3/3 times
- [ ] ✅ Screenshot/video proof of successful restore
- [ ] ✅ Draft cleared after final save (localStorage + server)

### Audit (AC-1 + AC-5)
- [ ] ✅ `audit.md` created with frequency analysis
- [ ] ✅ API rate calculation documented
- [ ] ✅ Anti-spam verification included
- [ ] ✅ `BUSINESS_WORKFLOWS.md` updated (line 368)

### GRADED Protection (AC-4)
- [ ] ✅ Backend returns 400 on GRADED copy draft save
- [ ] ✅ Frontend read-only mode prevents autosave (already implemented)
- [ ] ✅ E2E test: restore on GRADED copy discarded (optional enhancement)

---

## 11. Non-Functional Requirements

### Performance
- **localStorage write**: < 10ms (synchronous)
- **Server autosave**: < 200ms (P95 latency)
- **E2E test duration**: < 60s (full cycle)

### Reliability
- **Recovery success rate**: 100% (verified by E2E test)
- **Zero data loss**: Verified by state fidelity assertions
- **Zero GRADED overwrites**: Verified by backend test

### Security
- **Lock token validation**: Already implemented (line 64-77)
- **Owner-only access**: Already implemented (line 48, 86)
- **GRADED immutability**: NEW requirement (Phase 1)

---

## 12. Out of Scope

1. **Multi-device sync UI**: DraftState allows it, but no UI for conflict resolution
2. **Draft history/versioning**: Only latest draft stored
3. **Offline mode**: No ServiceWorker implementation
4. **Auto-recovery without user action**: User must click "Restore"
5. **Draft expiration**: No TTL on DraftState records (localStorage has 7-day TTL)

---

## 13. References

### Codebase Files
- `backend/grading/models.py:214-260` - DraftState model
- `backend/grading/views_draft.py` - Draft API endpoints
- `backend/grading/views.py:170` - GRADED status pattern
- `frontend/src/views/admin/CorrectorDesk.vue:364-395` - Autosave logic
- `frontend/src/utils/storage.js` - localStorage utilities
- `frontend/tests/e2e/corrector_flow.spec.ts` - Existing E2E test
- `backend/conftest.py` - Test fixtures

### Documentation
- `requirements.md` - Product requirements
- `docs/technical/BUSINESS_WORKFLOWS.md:368` - Autosave documentation (outdated)
- `docs/technical/DATABASE_SCHEMA.md` - DraftState schema

### External Dependencies
- pytest documentation: https://docs.pytest.org/
- Playwright documentation: https://playwright.dev/
- Django REST Framework testing: https://www.django-rest-framework.org/api-guide/testing/

---

**End of Technical Specification**
