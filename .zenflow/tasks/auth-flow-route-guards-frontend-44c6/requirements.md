# Product Requirements Document: AUTH FLOW + ROUTE GUARDS (Frontend)

**Task ID**: ZF-AUD-02  
**Created**: 2026-01-31  
**Status**: Draft

---

## 1. Executive Summary

### Objective
Ensure zero-friction authentication according to user profile, and secure navigation where no sensitive page is accessible without a valid session. All three user roles (Admin, Teacher, Student) must have smooth, secure, and role-appropriate authentication flows with robust route guards.

### Success Criteria
- **Zero unauthorized access**: No sensitive page accessible via direct URL without proper authentication and role
- **Smooth login flows**: Each role has a frictionless login experience with clear error messages
- **Stable session management**: Works correctly across page reloads, multi-tab scenarios, and browser back button
- **Forced password change**: Admin users with `must_change_password` flag are required to change password before accessing dashboard
- **E2E test coverage**: All role-based workflows covered by Playwright tests with traces and screenshots

---

## 2. Current Architecture Analysis

### 2.1 Technology Stack
- **Frontend**: Vue 3.4.15 + Vite 5.1.0 + TypeScript
- **State Management**: Pinia 2.1.7
- **Router**: Vue Router 4.2.5
- **HTTP Client**: Axios 1.13.2
- **E2E Testing**: Playwright 1.57.0
- **Backend**: Django REST Framework with session-based authentication

### 2.2 Existing Auth Implementation

#### User Roles & Authentication Methods
1. **Admin**: Django User with superuser/staff flags
   - Login: `/admin/login` (username/email + password)
   - Dashboard: `/admin-dashboard`
   - Endpoints: `/api/login/`, `/api/me/`, `/api/logout/`

2. **Teacher (Corrector)**: Django User with Teacher group
   - Login: `/teacher/login` (username + password)
   - Dashboard: `/corrector-dashboard`
   - Endpoints: `/api/login/`, `/api/me/`, `/api/logout/`

3. **Student**: Custom session model (no Django User per ADR-001)
   - Login: `/student/login` (INE + Last Name)
   - Portal: `/student-portal`
   - Endpoints: `/api/students/login/`, `/api/students/me/`, `/api/students/logout/`

#### Current Components
- **Auth Store** (`stores/auth.js`): Manages user state, login/logout, fetchUser with dual-endpoint strategy
- **Router Guards** (`router/index.js`): Basic requiresAuth + role checks, prevents logged-in users from accessing login pages
- **Login UI** (`views/Login.vue`): Username/password with password toggle, role-aware styling
- **Student Login** (`views/student/LoginStudent.vue`): INE + Last Name form
- **Change Password Modal** (`components/ChangePasswordModal.vue`): Forced/optional password change with validation
- **Axios Config** (`services/api.js`): withCredentials, CSRF token handling, 10s timeout

#### Current E2E Tests
- `admin_flow.spec.ts`: Basic admin login and dashboard
- `tests/teacher_flow.spec.ts`: Admin dashboard access via API login helper
- `tests/helpers/auth.ts`: Helper for admin login via API + store hydration

---

## 3. Identified Gaps & Requirements

### 3.1 Router Guard Issues

#### Current State
- Basic `requiresAuth` and `role` checks exist
- `fetchUser()` is called in `beforeEach` guard
- Redirect logic for logged-in users on login pages

#### Gaps & Requirements
1. **Redirect Loop Prevention**: Ensure no infinite redirects between guards and login pages
2. **Back Button Handling**: Verify proper behavior when user clicks back after logout or role-denied access
3. **Role Enforcement**: Ensure strict role-based access (e.g., Teacher cannot access `/admin/users`)
4. **Session Expiry**: Handle expired sessions gracefully with redirect to appropriate login page
5. **Multi-Tab Sync**: Verify behavior when user logs out in one tab while another is active
6. **Loading States**: Prevent flashing of unauthorized content during `fetchUser()` checks

### 3.2 Axios Configuration Issues

#### Current State
- `withCredentials: true` configured
- CSRF token extracted from cookie and added to request headers
- 10-second timeout
- No retry logic

#### Gaps & Requirements
1. **Retry Logic**: Implement smart retry for transient network errors (not for 4xx)
2. **Timeout Strategy**: Review 10s timeout - may be too long for certain operations, too short for uploads
3. **401/403 Handling**: Implement global interceptor to catch auth errors and redirect appropriately
4. **CSRF Error Recovery**: Handle CSRF token mismatch scenarios
5. **Request Queueing**: Prevent race conditions when multiple requests fail due to expired session

### 3.3 E2E Test Coverage Gaps

#### Required Test Scenarios

##### Admin Flow
1. **Login → Dashboard**: Standard admin login flow
2. **Forced Password Change**: Admin with `must_change_password=true` → modal blocks → change → dashboard
3. **Role-Based Access**: Admin can access all admin pages (users, settings, identification)
4. **Denied Access**: Direct URL navigation to non-existent routes → redirect to dashboard
5. **Logout → Back Button**: After logout, back button should not restore session

##### Teacher Flow
1. **Login → Dashboard**: Teacher login → corrector dashboard
2. **Access Allowed Pages**: Teacher can access corrector desk, import copies
3. **Denied Access**: Teacher cannot access `/admin/users`, `/admin/settings` → redirect to corrector dashboard
4. **Copy Correction Workflow**: Login → lock copy → annotate → save → reload → restore draft
5. **Logout → Multi-Tab**: Logout in one tab → other tabs detect session loss

##### Student Flow
1. **Login (INE + DOB)**: Student login with INE and last name → student portal
2. **View Graded Copies**: List of graded copies displayed
3. **Download PDF**: Student can download their graded copy PDF
4. **Denied Access**: Student cannot access `/admin-dashboard`, `/corrector-dashboard` → redirect to home
5. **Session Timeout**: After 4h timeout, redirect to login with clear message

### 3.4 UX Error Handling

#### Current State
- Basic error messages in login forms
- Error messages not always user-friendly (technical jargon)

#### Requirements
1. **Clear Error Messages**: User-friendly, localized (French) error messages
2. **Consistent Error Display**: Unified error notification component
3. **No Inconsistent State**: Loading indicators during auth checks
4. **Network Error Feedback**: Distinguish between network errors vs auth errors vs server errors
5. **Form Validation**: Client-side validation before API call to reduce server load

---

## 4. Functional Requirements

### FR-1: Login UI & Password Management
**Priority**: P0 (Must Have)

#### FR-1.1: Password Visibility Toggle
- [x] Implemented in `Login.vue` and `ChangePasswordModal.vue`
- Eye icon to toggle password visibility
- Accessible (aria-label, keyboard navigation)

#### FR-1.2: Forced Password Change Flow
- [x] Modal appears when `must_change_password=true` (App.vue)
- Modal cannot be dismissed (forced mode)
- Password validation (min 8 chars, Django password validators)
- After successful change, modal clears flag and user proceeds to dashboard

**Verification**: E2E test simulates admin with must_change_password flag

#### FR-1.3: Optional Password Change
- Admin/Teacher can change password from settings or dashboard menu
- Uses same `ChangePasswordModal` in non-forced mode
- Can be cancelled

### FR-2: Auth Store & Session Management
**Priority**: P0 (Must Have)

#### FR-2.1: Dual-Endpoint Strategy
- [x] `fetchUser()` tries `/api/me/` first, then `/api/students/me/` if it fails
- Supports `preferStudent` parameter for optimization on student routes
- Sets user role correctly (Admin, Teacher, Student)

#### FR-2.2: Session State Tracking
- `isChecking` flag prevents race conditions during auth checks
- `isAuthenticated` computed property for reactive auth state
- `mustChangePassword` computed property triggers modal

#### FR-2.3: Logout Handling
- Role-aware logout endpoint (`/api/logout/` vs `/api/students/logout/`)
- Clears user state
- Redirects to home page

**Verification**: Unit tests for auth store logic, E2E tests for logout flows

### FR-3: Router Guards & Navigation
**Priority**: P0 (Must Have)

#### FR-3.1: Authentication Guard
- All routes with `meta.requiresAuth` must check for authenticated session
- If not authenticated, redirect to home (`/`) landing page
- No redirect loops (guard only redirects once)

#### FR-3.2: Role-Based Access Control
- Routes with `meta.role` must verify user has correct role
- Admin users can access any route (superuser bypass)
- Teacher can only access Teacher and public routes
- Student can only access Student and public routes
- Denied access redirects to user's appropriate dashboard

#### FR-3.3: Logged-In User Redirect
- If authenticated user visits login pages, redirect to their dashboard
- Admin → `/admin-dashboard`
- Teacher → `/corrector-dashboard`
- Student → `/student-portal`

#### FR-3.4: URL Protection
- Direct URL navigation must be protected (no client-side bypass)
- Back button after logout must not restore session
- Refresh on protected page must re-validate session

**Verification**: E2E tests for each scenario, manual testing of edge cases

### FR-4: Axios Configuration & Error Handling
**Priority**: P0 (Must Have)

#### FR-4.1: Request Configuration
- `withCredentials: true` for cookie-based auth
- CSRF token from cookie added to `X-CSRFToken` header
- `baseURL` from `VITE_API_URL` or `/api` default
- Timeout: 10s default (consider per-request override for uploads)

#### FR-4.2: Response Interceptor
- **401 Unauthorized**: Clear auth store, redirect to home (unless already on public page)
- **403 Forbidden**: Show "Access Denied" message, redirect to user's dashboard
- **Network Errors**: Show user-friendly "Connection lost" message
- **Timeout**: Show "Request timed out" message

#### FR-4.3: Retry Logic
- Retry transient errors (network, 5xx) up to 2 times with exponential backoff
- Do NOT retry 4xx errors (bad request, auth errors)
- Configurable retry count per request

**Verification**: E2E tests with network throttling, backend downtime simulation

### FR-5: E2E Test Coverage
**Priority**: P0 (Must Have)

#### FR-5.1: Admin Tests
- Test: Admin login → dashboard
- Test: Admin with forced password change → modal → change → dashboard
- Test: Admin can access `/admin/users`, `/admin/settings`
- Test: Admin logout → back button does not restore session

#### FR-5.2: Teacher Tests
- Test: Teacher login → corrector dashboard
- Test: Teacher can access corrector desk, import copies
- Test: Teacher CANNOT access `/admin/users` → redirected to corrector dashboard
- Test: Teacher workflow: lock copy → annotate → save → reload → verify

#### FR-5.3: Student Tests
- Test: Student login (INE + Last Name) → portal
- Test: Student can view list of graded copies
- Test: Student can download PDF
- Test: Student CANNOT access `/admin-dashboard` → redirected to home

#### FR-5.4: Multi-Tab & Reload Tests
- Test: Logout in tab A → tab B detects session loss
- Test: Reload protected page → session restored from cookie
- Test: Reload after logout → redirected to login

**Deliverables**: Playwright test files, screenshots on failure, trace files for debugging

---

## 5. Non-Functional Requirements

### NFR-1: Performance
- **Auth Check Latency**: `fetchUser()` must complete within 2s (p95)
- **Route Navigation**: Redirect decisions must not delay navigation > 100ms
- **No Redundant Requests**: Cache user info during single navigation flow (no double-fetch)

### NFR-2: Security
- **Session Security**: HttpOnly cookies, Secure flag in production, SameSite=Lax
- **CSRF Protection**: All mutating requests (POST, PUT, DELETE) include CSRF token
- **No Client-Side Auth Bypass**: All auth checks must be server-validated
- **Audit Trail**: Backend logs all login attempts (success/failure) per `.antigravity/rules/01_security_rules.md`

### NFR-3: Usability
- **Error Messages**: French, user-friendly, actionable
- **Loading States**: Visual feedback during auth checks (spinners, skeleton screens)
- **Accessibility**: WCAG 2.1 Level AA (keyboard navigation, screen reader support, ARIA labels)

### NFR-4: Testability
- **E2E Test Stability**: Tests must pass in Docker environment (per `docs/E2E_TESTING_CONTRACT.md`)
- **Test Data Seeding**: Use `backend/scripts/seed_e2e.py` for consistent test data
- **Trace Artifacts**: Playwright traces and screenshots on failure for debugging

---

## 6. User Workflows

### Workflow 1: Admin Login with Forced Password Change
1. Admin navigates to `/admin/login`
2. Enters username + password
3. Backend returns `must_change_password: true`
4. Auth store sets user with flag
5. Router redirects to `/admin-dashboard`
6. `ChangePasswordModal` appears (forced mode)
7. Admin enters new password (validated client + server)
8. Backend updates password, clears flag
9. Modal closes, admin sees dashboard

**Exit Criteria**: Admin can access all admin features without modal reappearing

### Workflow 2: Teacher Corrects Copy
1. Teacher navigates to `/teacher/login`
2. Enters credentials, logs in
3. Router redirects to `/corrector-dashboard`
4. Teacher clicks on a copy to correct
5. Router navigates to `/corrector/desk/:copyId`
6. Teacher locks copy, annotates, saves
7. Teacher reloads page
8. Router guard checks session (fetchUser)
9. Copy desk loads, draft restore modal appears
10. Teacher restores draft, continues work

**Exit Criteria**: Teacher can complete correction workflow without losing data or session

### Workflow 3: Student Views Results
1. Student navigates to `/student/login`
2. Enters INE + Last Name
3. Backend creates session with `student_id`
4. Router redirects to `/student-portal`
5. Student sees list of graded copies
6. Student clicks on a copy
7. Copy details displayed with score and annotations
8. Student clicks "Download PDF"
9. PDF downloads successfully
10. Student logs out

**Exit Criteria**: Student can view their data only, cannot access other students' data or admin pages

---

## 7. Edge Cases & Error Scenarios

### EC-1: Expired Session During Navigation
**Scenario**: User session expires while navigating between pages  
**Expected Behavior**: Router guard detects expired session (fetchUser fails), redirects to home with message "Session expired, please log in again"

### EC-2: Role Change Mid-Session
**Scenario**: Admin demotes user from Teacher to Student role while user is logged in  
**Expected Behavior**: Next navigation or API call returns updated role, router redirects to appropriate page. Consider: May require "Your role has changed, please log in again" message and forced logout.

### EC-3: Concurrent Logins (Same User, Multiple Tabs)
**Scenario**: User logs in as Admin in Tab A, then logs in as Teacher in Tab B  
**Expected Behavior**: Tab A session is replaced by Tab B session. On next navigation in Tab A, fetchUser returns Teacher role, user is redirected to Teacher dashboard.

### EC-4: Backend Downtime During Login
**Scenario**: User attempts login, backend is unreachable  
**Expected Behavior**: Show "Server unavailable, please try again later" message. Do not show "Invalid credentials" error.

### EC-5: CSRF Token Mismatch
**Scenario**: User session is valid but CSRF token is stale (e.g., after long idle)  
**Expected Behavior**: Axios intercepts 403 CSRF error, refreshes page to get new token, retries request once. If still fails, show error message.

### EC-6: Back Button After Logout
**Scenario**: User logs out, then clicks browser back button  
**Expected Behavior**: Router guard detects no session, redirects to home. User does not see cached protected page.

---

## 8. Deliverables

### 8.1 Audit Documentation
- **`audit.md`**: Detailed audit report of current router guards, axios config, and auth flow
  - Findings: Issues identified
  - Recommendations: Proposed fixes
  - Risk Assessment: Security and UX risks

### 8.2 E2E Test Suite
- **Playwright Tests**: Located in `frontend/e2e/`
  - `admin_auth_flow.spec.ts`: Admin login, forced password change, role access, logout
  - `teacher_auth_flow.spec.ts`: Teacher login, denied admin access, correction workflow
  - `student_auth_flow.spec.ts`: Student login, view copies, download PDF, denied admin access
  - `multi_tab_session.spec.ts`: Logout in one tab, session detection in other tab
  - `edge_cases.spec.ts`: Back button, reload, expired session, role change

- **Test Artifacts**:
  - Screenshots on failure (auto-captured by Playwright)
  - Trace files for debugging (`.zip` format)
  - Test execution logs

### 8.3 Navigation Specifications
- **`expected_navigation_specs.md`**: Document describing expected navigation for each role
  - Admin: All routes accessible
  - Teacher: Corrector routes + public routes
  - Student: Student routes + public routes
  - Denied access behavior for each role
  - Redirect logic flowcharts

### 8.4 Code Improvements (if audit identifies issues)
- Router guard enhancements
- Axios interceptor improvements
- Error message standardization
- Loading state components

---

## 9. Acceptance Criteria

### AC-1: Zero Unauthorized Access
- [ ] Admin pages (`/admin/*`) not accessible to Teacher or Student via direct URL
- [ ] Teacher pages (`/corrector/*`) not accessible to Student via direct URL
- [ ] Student pages (`/student-portal`) not accessible to unauthenticated users
- [ ] All E2E tests for unauthorized access attempts pass

### AC-2: Smooth Login Flows
- [ ] Admin can log in with username/email + password
- [ ] Teacher can log in with username + password
- [ ] Student can log in with INE + Last Name
- [ ] Forced password change works correctly for admin
- [ ] Error messages are clear and user-friendly (French)

### AC-3: Session Stability
- [ ] Page reload on protected route restores session correctly
- [ ] Multi-tab: Logout in one tab detected in other tab
- [ ] Back button after logout does not restore session
- [ ] No redirect loops in any navigation scenario

### AC-4: E2E Test Coverage
- [ ] Admin flow tests: 5+ scenarios (login, forced password, role access, logout, back button)
- [ ] Teacher flow tests: 5+ scenarios (login, denied access, correction workflow, multi-tab)
- [ ] Student flow tests: 4+ scenarios (login, view copies, download PDF, denied access)
- [ ] All tests pass in Docker environment (per E2E_TESTING_CONTRACT.md)
- [ ] Screenshots and traces captured on failure

### AC-5: Documentation
- [ ] `audit.md` completed with findings and recommendations
- [ ] `expected_navigation_specs.md` created with role-based navigation rules
- [ ] Playwright test suite documented (README in `frontend/e2e/`)

---

## 10. Out of Scope

The following items are explicitly **out of scope** for this task:

1. **Backend Changes**: This task focuses on frontend auth flow. Backend auth endpoints are assumed to be stable and correct.
2. **Password Reset Flow**: Forgot password / email-based reset is not part of this audit.
3. **Multi-Factor Authentication (MFA)**: Not required for this phase.
4. **Remember Me / Persistent Login**: All sessions are cookie-based with default expiry.
5. **Social Login (OAuth)**: Not supported.
6. **Admin User Creation UI**: Admins are created via Django management commands.
7. **Internationalization (i18n)**: Error messages in French only (no multi-language support).

---

## 11. Dependencies & Constraints

### Dependencies
- Backend API must be stable and return correct `must_change_password` flag in `/api/me/` response
- Docker environment must be available for E2E tests (per E2E_TESTING_CONTRACT.md)
- Seed data script (`backend/scripts/seed_e2e.py`) must be up-to-date

### Constraints
- Tests must run in Docker Compose environment (Playwright against `localhost:8088`)
- No changes to backend auth logic allowed
- Must maintain backward compatibility with existing frontend code
- All E2E tests must complete within 5 minutes total

---

## 12. Success Metrics

### Metrics
1. **Test Coverage**: 100% of critical auth flows covered by E2E tests
2. **Test Pass Rate**: 100% of E2E tests pass consistently
3. **Zero Critical Security Issues**: No unauthorized access possible via client-side bypass
4. **User Error Rate**: <1% of login attempts result in confusing error messages (from user feedback)
5. **Performance**: Auth check (fetchUser) latency p95 < 2s

### Validation Method
- Run E2E test suite in Docker environment
- Manual security audit of router guards
- Manual testing of edge cases (back button, multi-tab, reload)
- Code review of axios interceptor and error handling

---

## 13. Open Questions & Assumptions

### Questions for Stakeholder
1. **Session Timeout**: Current timeout is 4h for students, default Django session for admin/teacher. Is this acceptable?
2. **Concurrent Sessions**: Should we support multiple concurrent sessions per user, or enforce single session (logout on new login)?
3. **Role Change Handling**: If admin changes user role mid-session, should user be forced to log out immediately?

### Assumptions
1. Backend returns `must_change_password` correctly in `/api/me/` response
2. CSRF token handling is correct on backend (Django default)
3. All users have JavaScript enabled (no progressive enhancement)
4. All modern browsers supported (Chrome, Firefox, Safari, Edge - latest 2 versions)
5. E2E tests run in headless mode in CI/CD pipeline

---

## 14. Revision History

| Version | Date       | Author  | Changes                          |
|---------|------------|---------|----------------------------------|
| 1.0     | 2026-01-31 | AI Agent| Initial PRD based on task ZF-AUD-02 |

---

## 15. Approval

**Prepared by**: AI Agent (Requirements Phase)  
**Review Required**: Tech Lead, QA Lead  
**Approval Required**: Product Owner

---

**End of Document**
