# Full SDD workflow

## Configuration
- **Artifacts Path**: {@artifacts_path} → `.zenflow/tasks/{task_id}`

---

## Workflow Steps

### [x] Step: Requirements
<!-- chat-id: ca781eb4-e1c9-4d82-94e6-769beff43b90 -->

Create a Product Requirements Document (PRD) based on the feature description.

1. Review existing codebase to understand current architecture and patterns
2. Analyze the feature definition and identify unclear aspects
3. Ask the user for clarifications on aspects that significantly impact scope or user experience
4. Make reasonable decisions for minor details based on context and conventions
5. If user can't clarify, make a decision, state the assumption, and continue

Save the PRD to `{@artifacts_path}/requirements.md`.

### [x] Step: Technical Specification
<!-- chat-id: d40889b6-a75c-46a0-a6ab-ba8542add1df -->

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
<!-- chat-id: 248e2318-d924-4582-b1ab-ed353dbf6342 -->

Create a detailed implementation plan based on `{@artifacts_path}/spec.md`.

1. Break down the work into concrete tasks
2. Each task should reference relevant contracts and include verification steps
3. Replace the Implementation step below with the planned tasks

Rule of thumb for step size: each step should represent a coherent unit of work (e.g., implement a component, add an API endpoint, write tests for a module). Avoid steps that are too granular (single function) or too broad (entire feature).

If the feature is trivial and doesn't warrant full specification, update this workflow to remove unnecessary steps and explain the reasoning to the user.

Save to `{@artifacts_path}/plan.md`.

---

## Implementation Steps

### [x] Step: Create Backend Unit Test Fixtures
<!-- chat-id: fcc62b0b-641e-417f-9d3b-bb0b12b2be8d -->

**Objective**: Set up test fixtures for DraftState endpoint testing

**Files to create**:
- `backend/grading/tests/test_draft_endpoints.py`

**Tasks**:
- [ ] Create pytest fixtures: `exam_factory` and `copy_factory`
- [ ] Import required models: Copy, DraftState, CopyLock, User
- [ ] Verify fixtures integrate with existing conftest.py fixtures

**Reference**: spec.md section 5.1 (lines 469-495)

**Verification**:
```bash
pytest backend/grading/tests/test_draft_endpoints.py --collect-only
# Should show test collection without errors
```

---

### [x] Step: Implement Backend Unit Tests for Draft Endpoints
<!-- chat-id: 67d1427b-7960-4a7c-81ec-1661313c8a11 -->

**Objective**: Create comprehensive test coverage for DraftState API

**Tests to implement** (10 test cases):
- [x] `test_save_draft_with_valid_lock` - AC-2.1: 200 OK, version incremented
- [x] `test_load_draft_as_owner` - AC-2.2: 200 OK, payload returned
- [x] `test_load_non_existent_draft` - AC-2.3: 204 No Content
- [x] `test_save_without_lock_token` - AC-2.4: 403 Forbidden
- [x] `test_save_with_wrong_lock_owner` - AC-2.5: 409 Conflict
- [x] `test_save_to_graded_copy_forbidden` - AC-2.6: 400 Bad Request (NEW)
- [x] `test_client_id_conflict` - AC-2.7: 409 Conflict
- [x] `test_unauthorized_access` - AC-2.8: 401/403
- [x] `test_delete_draft_as_owner` - 204 No Content
- [x] Test class structure with `@pytest.mark.django_db`

**Reference**: spec.md section 5.1 (lines 312-467)

**Verification**:
```bash
pytest backend/grading/tests/test_draft_endpoints.py -v --tb=short
# Expect: 9/10 tests pass (test_save_to_graded_copy_forbidden will fail until next step)
```

**Result**: ✅ All 10 tests implemented successfully
- Initial run: 9/10 tests passed (test_save_to_graded_copy_forbidden failed as expected, returning 200 instead of 400)
- GRADED protection already added to views_draft.py:64-65 by previous step
- All tests now pass with the GRADED protection in place

---

### [x] Step: Add GRADED Status Protection to Draft Endpoint
<!-- chat-id: 6454cde7-9135-4ba9-98bb-09d83a53f490 -->

**Objective**: Prevent draft saves to finalized copies

**File to modify**:
- `backend/grading/views_draft.py`

**Tasks**:
- [ ] Add GRADED status check in `DraftReturnView.put()` after line 62
- [ ] Use pattern from `backend/grading/views.py:170-171`
- [ ] Return 400 with message: "Cannot save draft to GRADED copy."
- [ ] Place check BEFORE lock validation

**Code location**: After copy retrieval, before token validation

**Reference**: spec.md section 3.3.2 (lines 194-210)

**Verification**:
```bash
pytest backend/grading/tests/test_draft_endpoints.py::TestDraftEndpoints::test_save_to_graded_copy_forbidden -v
# Should now PASS
```

---

### [ ] Step: Run Backend Tests and Verify Coverage

**Objective**: Ensure all backend tests pass with no regressions

**Tasks**:
- [ ] Run full backend test suite
- [ ] Verify all 10 draft endpoint tests pass
- [ ] Check for regressions in existing tests
- [ ] Generate coverage report for views_draft.py

**Verification**:
```bash
# All draft tests
pytest backend/grading/tests/test_draft_endpoints.py -v

# With coverage
pytest backend/grading/tests/test_draft_endpoints.py --cov=grading.views_draft --cov-report=term-missing

# Full backend suite (ensure no regressions)
pytest backend/grading/tests/
```

**Success Criteria**:
- 10/10 tests pass
- Coverage: 100% of DraftReturnView methods
- No new failures in existing tests

**Reference**: spec.md section 8.1 (lines 638-660)

---

### [x] Step: Enhance E2E Test with State Fidelity Checks
<!-- chat-id: fdbfa3b1-9a4f-4560-b41e-11e0a29c1252 -->

**Objective**: Verify 100% reproducible recovery with exact state restoration

**File to modify**:
- `frontend/tests/e2e/corrector_flow.spec.ts`

**Tasks**:
- [ ] Add assertion: Verify textarea content restored
- [ ] Add assertion: Verify score input value restored
- [ ] Add assertion: Verify annotation type selector restored
- [ ] Add assertion: Verify page indicator shows correct page
- [ ] Add assertion: Verify canvas annotation rect visible
- [ ] Add assertion: Verify rect coordinates (bounding box)
- [ ] Insert assertions after line 125 (after restore action)

**Reference**: spec.md section 5.2 (lines 499-544)

**Expected state to verify**:
- Content: 'Test E2E Annotation'
- Score: 2
- Type: 'ERREUR'
- Page: 1
- Rect: Visible with approximate coordinates

**Verification**:
```bash
cd frontend
npm run test:e2e -- corrector_flow.spec.ts
```

---

### [ ] Step: Run E2E Tests and Verify Recovery
<!-- chat-id: 79c7c81a-c90e-406f-a2e7-c1ea973c0bd9 -->

**Objective**: Prove 100% reproducible recovery works in real browser

**Tasks**:
- [ ] Start backend server: `python manage.py runserver 8088`
- [ ] Start frontend dev server: `npm run dev`
- [ ] Run E2E test 3 times to verify consistency
- [ ] Capture screenshot/video of successful restore
- [ ] Verify no console errors during restore
- [ ] Confirm draft cleared after final save

**Verification**:
```bash
# Run 3 times
npm run test:e2e -- corrector_flow.spec.ts --headed --repeat-each=3
```

**Success Criteria**:
- Test passes 3/3 times
- All 6 new state fidelity assertions pass
- Restore banner appears after refresh
- Draft cleared from localStorage and server

**Reference**: spec.md section 8.2 (lines 662-688)

---

### [ ] Step: Create Autosave Frequency Audit Document

**Objective**: Document actual autosave behavior and API rate limits

**File to create**:
- `.zenflow/tasks/autosave-recovery-draftstate-db-a6aa/audit.md`

**Content sections**:
- [ ] Trigger analysis (300ms local, 2000ms server)
- [ ] API rate calculation (0.5 req/s per user, peak load estimate)
- [ ] Anti-spam verification (debounce, read-only mode, lock requirement)
- [ ] Documentation mismatch findings (30s vs 2s)
- [ ] Recommendations (monitoring, rate limiting)

**Reference**: spec.md section 6.1 (lines 547-576)

**Verification**:
- Audit document contains all required sections
- API rate math is correct: 1 req / 2s = 0.5 req/s
- Documentation discrepancy clearly identified

---

### [x] Step: Update Business Workflows Documentation
<!-- chat-id: 311ee7a2-0da2-4307-93ed-3bd4fca49a42 -->

**Objective**: Fix outdated autosave frequency documentation

**File to modify**:
- `docs/technical/BUSINESS_WORKFLOWS.md`

**Tasks**:
- [x] Locate autosave documentation (around line 368)
- [x] Update "30s interval" to "2s server + 300ms localStorage (dual-layer)"
- [x] Verify change doesn't break document formatting

**Reference**: spec.md section 6.2 (lines 578-586)

**Verification**:
```bash
grep -n "autosave" docs/technical/BUSINESS_WORKFLOWS.md
# Verify updated line shows correct timing
```

---

### [ ] Step: Run Full Test Suite and Generate Proof Bundle

**Objective**: Final verification of all components and deliverables

**Tasks**:
- [ ] Run complete backend test suite: `pytest`
- [ ] Run complete E2E test suite: `npm run test:e2e`
- [ ] Run frontend lint: `npm run lint`
- [ ] Run frontend typecheck: `npm run typecheck`
- [ ] Collect test output logs
- [ ] Collect E2E screenshots/videos
- [ ] Verify all acceptance criteria met

**Verification Commands**:
```bash
# Backend
cd backend
pytest -v > test_results_backend.txt

# Frontend
cd frontend
npm run lint
npm run typecheck
npm run test:e2e > test_results_e2e.txt
```

**Final Acceptance Checklist**:
- [ ] Backend: 10/10 draft tests pass
- [ ] Backend: GRADED protection implemented
- [ ] E2E: State fidelity assertions added
- [ ] E2E: Test passes consistently (3/3)
- [ ] Audit: audit.md created with frequency analysis
- [ ] Docs: BUSINESS_WORKFLOWS.md updated
- [ ] Proof: Test outputs and screenshots collected

**Reference**: spec.md section 10 (lines 728-752)

**Deliverables**:
- ✅ `backend/grading/tests/test_draft_endpoints.py` (10 tests)
- ✅ Modified `backend/grading/views_draft.py` (GRADED check)
- ✅ Modified `frontend/tests/e2e/corrector_flow.spec.ts` (6 assertions)
- ✅ `.zenflow/tasks/autosave-recovery-draftstate-db-a6aa/audit.md`
- ✅ Updated `docs/technical/BUSINESS_WORKFLOWS.md`
- ✅ Test execution logs and E2E proof

---

**Implementation Plan Complete** ✓

**Estimated Effort**: 
- Phase 1 (Backend): 3-4 hours
- Phase 2 (E2E): 2-3 hours  
- Phase 3 (Audit): 1-2 hours
- **Total**: 6-9 hours

**Dependencies**:
- Backend: pytest, pytest-django (already installed)
- Frontend: Playwright (already installed)
- No new external dependencies required
