# Full SDD workflow

## Configuration
- **Artifacts Path**: {@artifacts_path} → `.zenflow/tasks/{task_id}`

---

## Workflow Steps

### [x] Step: Requirements
<!-- chat-id: f7bbf816-d9b1-4c73-a5e7-4aa01808d6fe -->

Create a Product Requirements Document (PRD) based on the feature description.

1. Review existing codebase to understand current architecture and patterns
2. Analyze the feature definition and identify unclear aspects
3. Ask the user for clarifications on aspects that significantly impact scope or user experience
4. Make reasonable decisions for minor details based on context and conventions
5. If user can't clarify, make a decision, state the assumption, and continue

Save the PRD to `{@artifacts_path}/requirements.md`.

### [x] Step: Technical Specification
<!-- chat-id: b5f5b12a-7bb9-4a8d-9860-1663dac18e09 -->

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
<!-- chat-id: e108408c-e0e9-4fd0-9fae-5143266476d5 -->

Create a detailed implementation plan based on `{@artifacts_path}/spec.md`.

1. Break down the work into concrete tasks
2. Each task should reference relevant contracts and include verification steps
3. Replace the Implementation step below with the planned tasks

Rule of thumb for step size: each step should represent a coherent unit of work (e.g., implement a component, add an API endpoint, write tests for a module). Avoid steps that are too granular (single function) or too broad (entire feature).

If the feature is trivial and doesn't warrant full specification, update this workflow to remove unnecessary steps and explain the reasoning to the user.

Save to `{@artifacts_path}/plan.md`.

---

## Implementation Steps

### [x] Step: Backend Parallel Foundation - pytest-xdist Setup
<!-- chat-id: 8749f227-1603-4766-a0c0-80edd1640d57 -->

**Objective**: Enable pytest-xdist for backend tests with proper isolation.

**Tasks**:
- [ ] Add `pytest-xdist~=3.5` to `backend/requirements.txt`
- [ ] Update `backend/pytest.ini` with xdist configuration (`--dist=loadscope`)
- [ ] Add `processing` marker to pytest.ini markers list
- [ ] Enhance `backend/conftest.py` mock_media fixture to include worker ID in temp directory prefix
- [ ] Add DB isolation logging to `backend/core/settings_test.py` for debugging

**Verification**:
```bash
cd backend
pip install -r requirements.txt
pytest -n 4 -v  # Should run with 4 workers
# Check logs for unique DB names: test_viatique_gw0, test_viatique_gw1, etc.
```

**Success Criteria**:
- pytest-xdist installed and workers spawn correctly
- Each worker uses unique database (verified in logs)
- Media directories isolated per worker
- No test failures due to isolation issues

**References**: 
- spec.md sections 3.1, 5.1
- requirements.md sections 3.1, 3.3

---

### [x] Step: Test Suite Categorization and Markers
<!-- chat-id: a14def61-6656-46ac-bdee-6dac49642616 -->

**Objective**: Organize tests into execution suites and add appropriate markers.

**Tasks**:
- [ ] Audit all test files and add `@pytest.mark.processing` to heavy I/O tests:
  - `grading/tests/test_fixtures_*.py`
  - `grading/tests/test_integration_real.py`
  - `processing/tests/test_splitter.py`
  - `exams/tests/test_pdf_validators.py`
  - `identification/test_ocr_assisted.py`
- [ ] Create test execution scripts:
  - `scripts/test_unit_fast.sh` → `pytest -n 8 -m unit`
  - `scripts/test_integration.sh` → `pytest -n 4 -m api`
  - `scripts/test_processing.sh` → `pytest -n 2 -m processing`
  - `scripts/test_all_parallel.sh` → Run all suites sequentially

**Verification**:
```bash
bash scripts/test_unit_fast.sh      # Should run only unit tests
bash scripts/test_integration.sh    # Should run only API integration tests
bash scripts/test_processing.sh     # Should run only processing tests
```

**Success Criteria**:
- All test files properly categorized
- Scripts execute correct test subsets
- No overlap between suites
- All scripts exit successfully

**References**:
- spec.md sections 2.2, 5.2
- requirements.md section 3.1

---

### [x] Step: Playwright Parallel Configuration
<!-- chat-id: 88504198-9b9c-4089-8b91-f9682c653102 -->

**Objective**: Enable parallel E2E tests with worker isolation.

**Tasks**:
- [ ] Update `frontend/playwright.config.ts`:
  - Set `fullyParallel: true`
  - Set `workers: process.env.CI ? 4 : 2`
  - Update `globalSetup` to `./tests/e2e/global-setup-parallel.ts`
- [ ] Create `frontend/tests/e2e/global-setup-parallel.ts`:
  - Detect `PLAYWRIGHT_WORKER_INDEX`
  - Implement health check for backend
  - Add per-worker database setup logic (placeholder for now)
  - Add logging for worker isolation
- [ ] Update `frontend/package.json` scripts:
  - Add `test:e2e:parallel` script
  - Add `test:e2e:debug` script with single worker

**Verification**:
```bash
cd frontend
npm ci
npx playwright install --with-deps chromium
npx playwright test --workers=2  # Should run with 2 workers
```

**Success Criteria**:
- Playwright runs with multiple workers
- Global setup executes per worker
- No worker conflicts during execution
- All E2E tests pass in parallel mode

**References**:
- spec.md sections 2.2.4, 3.2
- requirements.md section 3.1.4

---

### [x] Step: CI Pipeline Integration
<!-- chat-id: 056df66d-5003-45f7-920e-4411df10a097 -->

**Objective**: Update GitHub Actions to use parallel execution.

**Tasks**:
- [ ] Update `.github/workflows/korrigo-ci.yml`:
  - Modify `unit` job to run `pytest -n 4 --dist=loadscope -q`
  - Modify `integration` job to run parallel pytest for workflow tests
  - Remove explicit `pip install pytest` (already in requirements.txt)
- [ ] (Optional) Add E2E job with Playwright parallel execution
- [ ] Document expected CI time improvements

**Verification**:
```bash
# Trigger CI manually or push to branch
# Monitor CI logs for parallel execution
# Verify all jobs pass
```

**Success Criteria**:
- All CI jobs updated to use parallel execution
- Jobs complete successfully
- CI time reduced (measure baseline vs parallel)
- No new failures introduced

**References**:
- spec.md sections 3.3, 5.4
- requirements.md section 3.5

---

### [x] Step: Zenflow Multi-Task Isolation Setup
<!-- chat-id: 081de134-90fc-44d2-95f4-349047dca031 -->

**Objective**: Support multiple Zenflow tasks running in parallel without port conflicts.

**Tasks**:
- [ ] Create `.zenflow/tasks/template/.env.task` template with:
  - `ZENFLOW_TASK_ID` variable
  - `ZENFLOW_PORT_BASE` derived from task ID
  - Computed port variables (POSTGRES_PORT, REDIS_PORT, BACKEND_PORT, FRONTEND_PORT)
- [ ] Create `docker-compose.zenflow.yml` template with environment variable support
- [ ] Create `scripts/test_parallel_zenflow.sh` wrapper script:
  - Auto-detect Zenflow context
  - Source task-specific .env.task
  - Run pytest with appropriate workers
- [ ] Document port allocation algorithm

**Verification**:
```bash
# Simulate Zenflow task context
export ZENFLOW_TASK_ID="test-task-12345"
bash scripts/test_parallel_zenflow.sh
# Verify correct ports are loaded
```

**Success Criteria**:
- Template files created and documented
- Port allocation algorithm deterministic
- Script successfully detects and loads task environment
- Documentation explains setup

**References**:
- spec.md sections 2.3.3, 3.4, 5.5
- requirements.md sections 2.4, 3.2.3

---

### [ ] Step: Comprehensive Testing Guide Documentation
<!-- chat-id: c1eeb27c-c459-4149-b7c1-b100cfd43751 -->

**Objective**: Create developer guide for parallel testing best practices.

**Tasks**:
- [ ] Create `docs/development/PARALLEL_TESTING_GUIDE.md` with:
  - Overview of test suite organization
  - How to add a new test without breaking parallelism
  - Best practices (avoid singletons, use fixtures, DB isolation)
  - Debugging flaky tests guide
  - Suite selection guide (when to use which marker)
  - Examples of correct test patterns
  - Common pitfalls and solutions
- [ ] Create `ci_parallel_plan.md` summary with:
  - Implementation overview
  - Architecture decisions
  - Performance metrics
  - Validation results

**Verification**:
- Review documentation for completeness
- Ensure all sections from spec are covered
- Validate code examples are accurate

**Success Criteria**:
- Guide covers all required topics
- Code examples are tested and correct
- Documentation is clear and actionable
- New developers can follow guide successfully

**References**:
- spec.md sections 5.6, 6.4
- requirements.md sections 4.1, 5.1

---

### [ ] Step: Stability Validation - 5 Consecutive Runs
<!-- chat-id: f8f25700-cd27-4a9e-ad6d-d194f9873106 -->

**Objective**: Prove parallel execution is stable with 0 flakes over 5 runs.

**Tasks**:
- [ ] Run full backend test suite 5 times consecutively:
  ```bash
  for i in {1..5}; do
    pytest -n 4 --dist=loadscope -v 2>&1 | tee proof_backend_run$i.txt
  done
  ```
- [ ] Run Playwright tests 5 times consecutively:
  ```bash
  for i in {1..5}; do
    cd frontend && npx playwright test --workers=2 2>&1 | tee ../proof_e2e_run$i.txt
  done
  ```
- [ ] Analyze results for flakiness:
  - Check for any intermittent failures
  - Compare test counts across runs
  - Document any issues found
- [ ] Capture proof logs in task artifacts folder
- [ ] Document timing improvements (baseline vs parallel)

**Verification**:
```bash
# Check all runs passed
grep -E "PASSED|FAILED" proof_*_run*.txt
# Verify no failures
! grep -E "FAILED|ERROR" proof_*_run*.txt
```

**Success Criteria**:
- 5 backend runs complete with 0 failures
- 5 E2E runs complete with 0 failures
- No flaky tests detected
- Timing improvements documented
- Proof logs saved in artifacts folder

**References**:
- spec.md section 6.4
- requirements.md sections 1.3, 5.3

---

### [ ] Step: Final CI Validation and Metrics
<!-- chat-id: 20138590-56de-4185-8f0c-4644d0a215a7 -->

**Objective**: Validate parallel execution in actual CI environment.

**Tasks**:
- [ ] Trigger 5 consecutive CI runs (manual dispatch or commits)
- [ ] Monitor all CI jobs for:
  - Successful completion
  - Parallel worker execution
  - DB isolation (check logs)
  - No flaky failures
- [ ] Collect CI timing metrics:
  - Baseline (sequential) time
  - Parallel execution time
  - Calculate % improvement
- [ ] Document results in ci_parallel_plan.md
- [ ] Address any CI-specific issues found

**Verification**:
- Review GitHub Actions run history
- Confirm all 5 runs passed
- Validate timing improvements meet targets (>50% reduction)

**Success Criteria**:
- 5 consecutive CI runs pass without failures
- No flaky tests in CI environment
- Time improvement >50% documented
- All CI-specific issues resolved

**References**:
- spec.md sections 6.4, 8
- requirements.md sections 1.3, 3.5
