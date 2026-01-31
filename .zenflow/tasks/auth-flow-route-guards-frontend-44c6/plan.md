# Full SDD workflow

## Configuration
- **Artifacts Path**: {@artifacts_path} → `.zenflow/tasks/{task_id}`

---

## Workflow Steps

### [x] Step: Requirements
<!-- chat-id: 2e8c8fa5-213f-429f-bd59-523dfabd41bb -->

Create a Product Requirements Document (PRD) based on the feature description.

1. Review existing codebase to understand current architecture and patterns
2. Analyze the feature definition and identify unclear aspects
3. Ask the user for clarifications on aspects that significantly impact scope or user experience
4. Make reasonable decisions for minor details based on context and conventions
5. If user can't clarify, make a decision, state the assumption, and continue

Save the PRD to `{@artifacts_path}/requirements.md`.

### [x] Step: Technical Specification
<!-- chat-id: 316fb142-830d-4549-b086-0cf2edf03e0e -->

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

Create a detailed implementation plan based on `{@artifacts_path}/spec.md`.

1. Break down the work into concrete tasks
2. Each task should reference relevant contracts and include verification steps
3. Replace the Implementation step below with the planned tasks

Rule of thumb for step size: each step should represent a coherent unit of work (e.g., implement a component, add an API endpoint, write tests for a module). Avoid steps that are too granular (single function) or too broad (entire feature).

If the feature is trivial and doesn't warrant full specification, update this workflow to remove unnecessary steps and explain the reasoning to the user.

Save to `{@artifacts_path}/plan.md`.

---

## Implementation Steps

### [x] Step: Audit & Documentation Phase
<!-- chat-id: 70317ac7-8507-4012-9f67-701f7811504a -->

**Objective**: Identify and document all security/UX issues in current auth implementation

**Tasks**:
1. Create `audit.md` document structure in task artifacts folder
2. Audit router guards (`frontend/src/router/index.js`):
   - Test all redirect scenarios (logged-in to login page, logged-out to protected page)
   - Test back button behavior after logout for each role
   - Test direct URL navigation to protected routes
   - Check for redirect loops or race conditions
   - Document all findings with risk levels (High/Medium/Low)
3. Audit axios configuration (`frontend/src/services/api.js`):
   - Review current interceptor implementation
   - Test timeout scenarios (slow network)
   - Test CSRF error handling (simulate stale token)
   - Test 401/403 response handling
   - Assess retry logic (currently none exists)
   - Document all findings with recommendations
4. Audit multi-tab/reload behavior:
   - Test logout in one tab, switch to another tab
   - Test concurrent logins (different roles)
   - Test page reload on protected routes
   - Document findings and edge cases
5. Compile recommendations and risk assessment in `audit.md`

**Verification**:
- [ ] `audit.md` exists with structured findings (Router, Axios, Multi-tab sections)
- [ ] All issues have risk assessment and recommended fixes
- [ ] Test scenarios documented with expected vs actual behavior

**Files to create**:
- `.zenflow/tasks/auth-flow-route-guards-frontend-44c6/audit.md`

### [x] Step: Router Guards Enhancement
<!-- chat-id: 51997ca9-28b8-45d2-a728-10adfac5d60d -->

**Objective**: Fix identified router guard issues for bulletproof route protection

**Contract Reference**: Follows existing pattern in `router/index.js:109-149`

**Tasks**:
1. Review findings from `audit.md` Router section
2. Enhance `beforeEach` guard in `frontend/src/router/index.js`:
   - Add try/catch around `fetchUser()` to handle session expiry gracefully
   - Prevent infinite redirect loops (track redirect count or check `from` route)
   - Add explicit handling for network errors vs auth errors
   - Ensure `isChecking` flag prevents race conditions
3. Create helper functions in `router/index.js`:
   - `getDashboardForRole(role)` - returns dashboard path for given role
   - `isLoginPage(routeName)` - checks if route is a login page
4. Test router guard fixes:
   - Direct URL to `/admin/users` when logged out → redirects to home
   - Back button after logout → redirects to home (no cached page)
   - Session expiry during navigation → redirects with clear message
   - Logged-in user visits login page → redirects to dashboard
5. Run lint and typecheck:
   ```bash
   cd frontend
   npm run lint
   npm run typecheck
   ```

**Verification**:
- [ ] `npm run lint` passes with zero errors
- [ ] `npm run typecheck` passes with zero errors
- [ ] Manual test: Logout → back button does not restore session
- [ ] Manual test: Direct URL navigation protected correctly

**Files to modify**:
- `frontend/src/router/index.js`

### [x] Step: Axios Interceptor Enhancement
<!-- chat-id: 57f36352-e4cb-4f97-9433-5d421dfd7213 -->

**Objective**: Robust error handling, retry logic, and auth error recovery

**Contract Reference**: Follows existing pattern in `services/api.js:38-43`

**Tasks**:
1. Review findings from `audit.md` Axios section
2. Enhance response interceptor in `frontend/src/services/api.js`:
   - Add 401 Unauthorized handler (clear auth store, redirect to home)
   - Add 403 Forbidden handler with CSRF retry logic (reload once if CSRF error)
   - Add retry logic for transient errors (network errors, 5xx) with exponential backoff
   - Ensure mutations (POST/PUT/DELETE) are not retried (prevent duplicate operations)
3. Create helper function `shouldRetry(error, config)`:
   - Return true for network errors (no response)
   - Return true for 5xx errors
   - Return false for 4xx errors and non-GET requests with responses
4. Test interceptor enhancements:
   - Simulate 401 → verify redirect to home
   - Simulate 403 CSRF error → verify page reload
   - Simulate network error → verify retry with backoff
   - Simulate 500 error → verify retry
5. Run lint and typecheck

**Verification**:
- [ ] `npm run lint` passes
- [ ] `npm run typecheck` passes
- [ ] Manual test: Expired session → clear redirect to home
- [ ] Manual test: Network error → retry with backoff (check DevTools Network tab)

**Files to modify**:
- `frontend/src/services/api.js`

### [ ] Step: UX Error Handling

**Objective**: User-friendly, consistent error messages in French

**Tasks**:
1. Create `frontend/src/utils/errorMessages.js`:
   - Define `ERROR_MESSAGES` object with French messages
   - Implement `getErrorMessage(error)` function to map axios errors to user messages
2. Create `frontend/src/components/LoadingOverlay.vue`:
   - Loading spinner component with optional message prop
   - Used during auth checks to prevent UI flashing
3. Update `frontend/src/stores/auth.js`:
   - Add `lastError` ref for storing error messages
   - Add `clearError()` method
   - Enhance `login()`, `loginStudent()`, `fetchUser()` with error handling
4. Update `frontend/src/views/Login.vue`:
   - Import and use `getErrorMessage()`
   - Display error message on login failure
   - Add loading state during login
5. Update `frontend/src/views/student/LoginStudent.vue`:
   - Import and use `getErrorMessage()`
   - Display error message on login failure
   - Add loading state during login
6. Run lint and typecheck

**Verification**:
- [ ] `npm run lint` passes
- [ ] `npm run typecheck` passes
- [ ] Manual test: Invalid credentials → French error message displayed
- [ ] Manual test: Network error → French error message displayed
- [ ] Manual test: Loading state visible during login

**Files to create**:
- `frontend/src/utils/errorMessages.js`
- `frontend/src/components/LoadingOverlay.vue`

**Files to modify**:
- `frontend/src/stores/auth.js`
- `frontend/src/views/Login.vue`
- `frontend/src/views/student/LoginStudent.vue`

### [ ] Step: E2E Tests - Admin Flow

**Objective**: Complete E2E test coverage for Admin workflows

**Contract Reference**: Follow `docs/E2E_TESTING_CONTRACT.md` and existing `e2e/admin_flow.spec.ts`

**Tasks**:
1. Create `frontend/e2e/tests/admin_auth_flow.spec.ts`:
   - Test: Admin login → dashboard (verify URL, page content)
   - Test: Admin with `must_change_password=true` → modal appears (forced mode) → change password → modal closes → dashboard loads
   - Test: Admin can access `/admin/users` (allowed, verify page loads)
   - Test: Admin logout → back button → redirected to home (not dashboard)
   - Take screenshots for each test scenario
2. Setup E2E environment:
   ```bash
   cd infra/docker
   docker-compose -f docker-compose.local-prod.yml up -d
   docker-compose -f docker-compose.local-prod.yml exec backend sh -c "export PYTHONPATH=/app && python scripts/seed_e2e.py"
   ```
3. Run admin tests:
   ```bash
   cd ../../frontend
   npx playwright test admin_auth_flow
   ```
4. Verify traces and screenshots generated on failure

**Verification**:
- [ ] All admin tests pass in Docker environment
- [ ] Screenshots saved on failure in `frontend/e2e/screenshots/`
- [ ] Traces available for debugging
- [ ] Tests stable (run 3 times, all pass)

**Files to create**:
- `frontend/e2e/tests/admin_auth_flow.spec.ts`

### [ ] Step: E2E Tests - Teacher & Student Flow

**Objective**: Complete E2E test coverage for Teacher and Student workflows

**Contract Reference**: Follow `docs/E2E_TESTING_CONTRACT.md`

**Tasks**:
1. Update `frontend/e2e/tests/helpers/auth.ts`:
   - Add `loginAsStudent(page, ine, lastName)` helper function
   - Reuse existing patterns from admin login helper
2. Create `frontend/e2e/tests/teacher_auth_flow.spec.ts`:
   - Test: Teacher login → corrector dashboard
   - Test: Teacher can access `/corrector/desk/:copyId` (allowed)
   - Test: Teacher CANNOT access `/admin/users` → redirected to corrector dashboard
   - Test: Teacher logout → back button → redirected to home
   - Take screenshots for each scenario
3. Create `frontend/e2e/tests/student_auth_flow.spec.ts`:
   - Test: Student login (INE + Last Name) → student portal
   - Test: Student can view list of graded copies
   - Test: Student can download PDF (verify download triggered)
   - Test: Student CANNOT access `/admin-dashboard` → redirected to home
   - Take screenshots for each scenario
4. Run teacher and student tests:
   ```bash
   npx playwright test teacher_auth_flow
   npx playwright test student_auth_flow
   ```

**Verification**:
- [ ] All teacher tests pass
- [ ] All student tests pass
- [ ] Role-based access control verified (denied routes redirect correctly)
- [ ] Screenshots captured for all scenarios

**Files to create**:
- `frontend/e2e/tests/teacher_auth_flow.spec.ts`
- `frontend/e2e/tests/student_auth_flow.spec.ts`

**Files to modify**:
- `frontend/e2e/tests/helpers/auth.ts`

### [ ] Step: E2E Tests - Multi-Tab & Edge Cases

**Objective**: Test multi-tab scenarios and edge cases

**Tasks**:
1. Create `frontend/e2e/tests/helpers/navigation.ts`:
   - Add helper `openNewTab(context, url)` for multi-tab testing
   - Add helper `verifyRedirect(page, expectedUrl)` for assertions
2. Create `frontend/e2e/tests/multi_tab.spec.ts`:
   - Test: Open Tab A (logged in) → Open Tab B → Logout in Tab A → Navigate in Tab B → Session loss detected, redirect to home
   - Take screenshots of both tabs
3. Create `frontend/e2e/tests/back_button.spec.ts`:
   - Test: Admin logout → back button for each role
   - Test: Teacher logout → back button
   - Test: Student logout → back button
   - Verify all redirect to home/login, not cached protected pages
4. Run all E2E tests together:
   ```bash
   npx playwright test
   ```
5. Review test report for any failures or flaky tests

**Verification**:
- [ ] All multi-tab tests pass
- [ ] All back button tests pass
- [ ] Full E2E suite passes (Admin + Teacher + Student + Edge cases)
- [ ] No flaky tests (run full suite 3 times, all pass)

**Files to create**:
- `frontend/e2e/tests/helpers/navigation.ts`
- `frontend/e2e/tests/multi_tab.spec.ts`
- `frontend/e2e/tests/back_button.spec.ts`

### [ ] Step: Navigation Specs & Final Verification

**Objective**: Document expected navigation flows and verify all acceptance criteria

**Tasks**:
1. Create navigation specification document `.zenflow/tasks/auth-flow-route-guards-frontend-44c6/navigation_specs.md`:
   - Admin navigation flow (login → dashboard → pages → logout)
   - Teacher navigation flow (login → corrector dashboard → desk → logout)
   - Student navigation flow (login → portal → view copies → download → logout)
   - Error scenarios (session expiry, access denied, network errors)
   - Expected redirects for each role on denied access
2. Update `audit.md` with verification results:
   - Add "Resolution" section showing how each issue was fixed
   - Add "Verification Results" with test outcomes
3. Run final verification:
   ```bash
   # Lint and typecheck
   cd frontend
   npm run lint
   npm run typecheck
   
   # Full E2E suite
   npx playwright test
   ```
4. Verify all acceptance criteria from task description:
   - [ ] Zero unauthorized access via direct URL
   - [ ] Login flows smooth and stable (reload, multi-tab)
   - [ ] Forced password change works for admins
   - [ ] Clear error messages in French
   - [ ] All E2E tests pass with traces/screenshots

**Verification**:
- [ ] `npm run lint` passes with zero errors
- [ ] `npm run typecheck` passes with zero errors
- [ ] `npx playwright test` passes (all tests green)
- [ ] Navigation specs documented in `navigation_specs.md`
- [ ] `audit.md` updated with resolution and verification results
- [ ] All acceptance criteria met

**Files to create**:
- `.zenflow/tasks/auth-flow-route-guards-frontend-44c6/navigation_specs.md`

**Files to update**:
- `.zenflow/tasks/auth-flow-route-guards-frontend-44c6/audit.md`

---

## Notes

**Estimated Effort**: 15-20 hours total
- Phase 1 (Audit): 2-3 hours
- Phase 2 (Router): 1.5-2 hours  
- Phase 3 (Axios): 1.5-2 hours
- Phase 4 (UX): 2 hours
- Phase 5 (Admin E2E): 2-3 hours
- Phase 6 (Teacher/Student E2E): 3-4 hours
- Phase 7 (Edge Cases E2E): 2 hours
- Phase 8 (Docs): 1 hour

**Testing Environment**: 
- Use Docker Compose per `docs/E2E_TESTING_CONTRACT.md`
- Seed data with `backend/scripts/seed_e2e.py`
- Base URL: `http://localhost:8088`

**Key Files**:
- Router: `frontend/src/router/index.js`
- Axios: `frontend/src/services/api.js`
- Auth Store: `frontend/src/stores/auth.js`
- E2E Tests: `frontend/e2e/tests/`
