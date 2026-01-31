# Technical Specification: AUTH FLOW + ROUTE GUARDS (Frontend)

**Task ID**: ZF-AUD-02  
**Created**: 2026-01-31  
**Status**: Draft

---

## 1. Technical Context

### 1.1 Technology Stack

**Frontend**:
- **Framework**: Vue 3.4.15 (Composition API)
- **Build Tool**: Vite 5.1.0
- **Language**: TypeScript (with .js files for gradual migration)
- **State Management**: Pinia 2.1.7
- **Router**: Vue Router 4.2.5
- **HTTP Client**: Axios 1.13.2
- **Testing**: Playwright 1.57.0 (E2E)

**Backend**:
- **Framework**: Django REST Framework
- **Authentication**: Session-based (HttpOnly cookies)
- **CSRF Protection**: Django CSRF middleware
- **Database**: PostgreSQL (via Docker)

**Infrastructure**:
- **Development**: Docker Compose (local-prod environment)
- **Test Environment**: Docker Compose (per `E2E_TESTING_CONTRACT.md`)
- **Base URL**: `http://localhost:8088` (reverse proxy)

### 1.2 Current Architecture

#### Authentication Flow
1. **Admin/Teacher**: 
   - POST `/api/login/` → Django session cookie → GET `/api/me/` → role determined by `is_staff`/`is_superuser`
2. **Student**: 
   - POST `/api/students/login/` → Django session → GET `/api/students/me/` → role = 'Student'

#### Existing Components
- **Auth Store** (`stores/auth.js`): Manages user state, dual-endpoint fetching
- **Router Guards** (`router/index.js`): Basic `requiresAuth` + role checks
- **Axios Config** (`services/api.js`): CSRF token injection, withCredentials
- **Password Modal** (`components/ChangePasswordModal.vue`): Forced/optional password change
- **Login Views**: `Login.vue` (Admin/Teacher), `LoginStudent.vue` (Student)

---

## 2. Implementation Approach

### 2.1 Audit & Documentation Phase

**Objective**: Identify gaps, security issues, and UX problems in current implementation

**Approach**:
1. **Router Audit**:
   - Analyze `router/index.js` for redirect loops, race conditions, and edge cases
   - Test back button behavior after logout
   - Verify role enforcement with direct URL navigation
   - Document findings in `audit.md`

2. **Axios Audit**:
   - Review interceptor implementation for 401/403 handling
   - Assess timeout strategy (10s may be inappropriate for all operations)
   - Evaluate retry logic (currently none)
   - Test CSRF error recovery scenarios
   - Document findings in `audit.md`

3. **Auth Flow Audit**:
   - Test multi-tab scenarios (logout in one tab)
   - Verify session expiry handling
   - Test concurrent login scenarios
   - Document findings in `audit.md`

**Deliverables**:
- `audit.md` with findings, recommendations, and risk assessment

### 2.2 Router Guards Enhancement

**Objective**: Fix identified issues and ensure bulletproof route protection

**Implementation Strategy** (based on existing patterns in `router/index.js:109-149`):

```javascript
// Enhanced guard structure
router.beforeEach(async (to, from, next) => {
    const authStore = useAuthStore()
    
    // 1. Prevent infinite loops - only fetch if needed
    if (!authStore.user && !authStore.isChecking && to.meta.requiresAuth) {
        const preferStudent = to.path.startsWith('/student')
        try {
            await authStore.fetchUser(preferStudent)
        } catch (error) {
            // Session expired or network error
            if (to.meta.requiresAuth) {
                return next('/') // Redirect to home
            }
        }
    }
    
    // 2. Auth check
    const isAuthenticated = authStore.isAuthenticated
    const userRole = authStore.user?.role
    
    // 3. Protected routes
    if (to.meta.requiresAuth && !isAuthenticated) {
        return next('/')
    }
    
    // 4. Role-based access (Admin can access all)
    if (to.meta.role && userRole !== to.meta.role && userRole !== 'Admin') {
        return next(getDashboardForRole(userRole))
    }
    
    // 5. Logged-in redirect from login pages
    if (isLoginPage(to.name) && isAuthenticated) {
        return next(getDashboardForRole(userRole))
    }
    
    // 6. No issues - proceed
    next()
})
```

**Key Changes**:
- Add try/catch around `fetchUser()` to handle session expiry gracefully
- Extract helper functions: `getDashboardForRole()`, `isLoginPage()`
- Add explicit handling for network errors vs auth errors
- Ensure no redirect loops by checking `from` route

**Files to modify**:
- `frontend/src/router/index.js`

### 2.3 Axios Interceptor Enhancement

**Objective**: Robust error handling, retry logic, and auth error recovery

**Implementation Strategy** (based on existing `services/api.js:38-43`):

```javascript
// Response interceptor with retry logic
api.interceptors.response.use(
    response => response,
    async error => {
        const { config, response } = error
        
        // 1. Handle 401 Unauthorized (session expired)
        if (response?.status === 401) {
            const authStore = useAuthStore()
            authStore.user = null // Clear stale session
            
            // Redirect to home if on protected route
            if (router.currentRoute.value.meta.requiresAuth) {
                router.push('/')
            }
            return Promise.reject(error)
        }
        
        // 2. Handle 403 Forbidden (CSRF or permission denied)
        if (response?.status === 403) {
            // Check if CSRF error
            if (response.data?.detail?.includes('CSRF')) {
                // Refresh page to get new token (once)
                if (!config._csrfRetry) {
                    window.location.reload()
                    return
                }
            }
            
            // Permission denied - redirect to dashboard
            const authStore = useAuthStore()
            const userRole = authStore.user?.role
            if (userRole) {
                router.push(getDashboardForRole(userRole))
            }
            return Promise.reject(error)
        }
        
        // 3. Retry transient errors (5xx, network)
        if (shouldRetry(error, config)) {
            config._retryCount = config._retryCount || 0
            if (config._retryCount < 2) {
                config._retryCount++
                const delay = Math.pow(2, config._retryCount) * 1000
                await new Promise(resolve => setTimeout(resolve, delay))
                return api.request(config)
            }
        }
        
        return Promise.reject(error)
    }
)
```

**Helper Functions**:
```javascript
function shouldRetry(error, config) {
    // Don't retry for mutations with side effects (already processed)
    if (config.method !== 'get' && error.response) return false
    
    // Retry network errors
    if (!error.response) return true
    
    // Retry 5xx errors
    if (error.response.status >= 500) return true
    
    return false
}
```

**Files to modify**:
- `frontend/src/services/api.js`

### 2.4 E2E Test Suite Implementation

**Objective**: Comprehensive test coverage for all role-based workflows

**Testing Strategy** (based on `E2E_TESTING_CONTRACT.md` and existing `admin_flow.spec.ts`):

#### Test Files Structure:
```
frontend/e2e/tests/
├── admin_auth_flow.spec.ts      # Admin login, forced pwd change, role access
├── teacher_auth_flow.spec.ts    # Teacher login, denied admin access
├── student_auth_flow.spec.ts    # Student login, view/download copies
├── multi_tab.spec.ts            # Multi-tab logout detection
├── back_button.spec.ts          # Back button after logout
└── helpers/
    ├── auth.ts                  # Login helpers (already exists)
    └── navigation.ts            # Navigation helpers
```

#### Test Pattern (based on `admin_flow.spec.ts:1-40`):
```typescript
test('Admin with forced password change', async ({ page }) => {
    // 1. Setup: Create admin with must_change_password=true
    // (via seed or API)
    
    // 2. Login
    await page.goto('http://localhost:8088/admin/login')
    await page.fill('input[type="email"]', 'admin@test.com')
    await page.fill('input[type="password"]', 'password')
    await page.click('button[type="submit"]')
    
    // 3. Verify modal appears (forced mode)
    await expect(page.locator('.password-modal')).toBeVisible()
    await expect(page.locator('.password-modal .close-btn')).not.toBeVisible()
    
    // 4. Change password
    await page.fill('input[name="new_password"]', 'NewP@ssw0rd')
    await page.fill('input[name="confirm_password"]', 'NewP@ssw0rd')
    await page.click('button:has-text("Changer")')
    
    // 5. Verify modal closes and dashboard loads
    await expect(page.locator('.password-modal')).not.toBeVisible()
    await expect(page).toHaveURL('http://localhost:8088/admin-dashboard')
    
    // 6. Take screenshot
    await page.screenshot({ path: 'screenshots/admin-forced-pwd.png' })
})
```

**Key E2E Scenarios** (per requirements.md):

**Admin Tests**:
1. ✅ Login → Dashboard (already exists in `admin_flow.spec.ts`)
2. 🆕 Login with `must_change_password` → Modal → Change → Dashboard
3. 🆕 Access `/admin/users` (allowed)
4. 🆕 Logout → Back button → Redirected to home

**Teacher Tests**:
1. 🆕 Login → Corrector Dashboard
2. 🆕 Access `/corrector/desk/:copyId` (allowed)
3. 🆕 Access `/admin/users` (denied → redirect to corrector dashboard)
4. 🆕 Lock copy → Annotate → Save → Reload → Restore draft

**Student Tests**:
1. 🆕 Login (INE + Last Name) → Student Portal
2. 🆕 View graded copies list
3. 🆕 Download PDF
4. 🆕 Access `/admin-dashboard` (denied → redirect to home)

**Multi-Tab Tests**:
1. 🆕 Logout in Tab A → Switch to Tab B → Next navigation detects no session

**Files to create**:
- `frontend/e2e/tests/admin_auth_flow.spec.ts`
- `frontend/e2e/tests/teacher_auth_flow.spec.ts`
- `frontend/e2e/tests/student_auth_flow.spec.ts`
- `frontend/e2e/tests/multi_tab.spec.ts`
- `frontend/e2e/tests/back_button.spec.ts`
- `frontend/e2e/tests/helpers/navigation.ts`

**Files to modify**:
- `frontend/e2e/tests/helpers/auth.ts` (add student login helper)

### 2.5 UX Error Handling Improvements

**Objective**: User-friendly, consistent error messages in French

**Implementation Strategy**:

1. **Error Message Mapping** (new file):
```javascript
// frontend/src/utils/errorMessages.js
export const ERROR_MESSAGES = {
    'INVALID_CREDENTIALS': 'Identifiants invalides. Veuillez vérifier votre nom d'utilisateur et mot de passe.',
    'SESSION_EXPIRED': 'Votre session a expiré. Veuillez vous reconnecter.',
    'NETWORK_ERROR': 'Erreur de connexion. Veuillez vérifier votre connexion Internet.',
    'SERVER_ERROR': 'Erreur du serveur. Veuillez réessayer plus tard.',
    'ACCESS_DENIED': 'Accès refusé. Vous n'avez pas les permissions nécessaires.',
    'CSRF_ERROR': 'Erreur de sécurité. La page va se recharger.',
    'TIMEOUT': 'La requête a expiré. Veuillez réessayer.',
}

export function getErrorMessage(error) {
    if (!error.response) return ERROR_MESSAGES.NETWORK_ERROR
    if (error.response.status === 401) return ERROR_MESSAGES.SESSION_EXPIRED
    if (error.response.status === 403) return ERROR_MESSAGES.ACCESS_DENIED
    if (error.response.status >= 500) return ERROR_MESSAGES.SERVER_ERROR
    if (error.code === 'ECONNABORTED') return ERROR_MESSAGES.TIMEOUT
    return ERROR_MESSAGES.SERVER_ERROR
}
```

2. **Loading Indicator Component** (new file):
```vue
<!-- frontend/src/components/LoadingOverlay.vue -->
<template>
    <div v-if="isLoading" class="loading-overlay">
        <div class="spinner"></div>
        <p>{{ message || 'Chargement...' }}</p>
    </div>
</template>

<script setup>
defineProps({
    isLoading: Boolean,
    message: String
})
</script>
```

3. **Update Login Views** to use error messages:
```vue
<!-- Update Login.vue -->
<script setup>
import { getErrorMessage } from '@/utils/errorMessages'

const errorMessage = ref(null)

async function handleLogin() {
    try {
        const success = await authStore.login(username.value, password.value)
        if (!success) {
            errorMessage.value = ERROR_MESSAGES.INVALID_CREDENTIALS
        }
    } catch (error) {
        errorMessage.value = getErrorMessage(error)
    }
}
</script>
```

**Files to create**:
- `frontend/src/utils/errorMessages.js`
- `frontend/src/components/LoadingOverlay.vue`

**Files to modify**:
- `frontend/src/views/Login.vue`
- `frontend/src/views/student/LoginStudent.vue`
- `frontend/src/stores/auth.js` (add error handling)

---

## 3. Source Code Structure Changes

### 3.1 New Files

```
frontend/src/
├── utils/
│   └── errorMessages.js              # Error message mapping
├── components/
│   └── LoadingOverlay.vue            # Loading indicator
└── e2e/
    └── tests/
        ├── admin_auth_flow.spec.ts   # Admin E2E tests
        ├── teacher_auth_flow.spec.ts # Teacher E2E tests
        ├── student_auth_flow.spec.ts # Student E2E tests
        ├── multi_tab.spec.ts         # Multi-tab tests
        ├── back_button.spec.ts       # Back button tests
        └── helpers/
            └── navigation.ts          # Navigation helpers

.zenflow/tasks/auth-flow-route-guards-frontend-44c6/
└── audit.md                          # Audit report
```

### 3.2 Modified Files

```
frontend/src/
├── router/
│   └── index.js                      # Enhanced guards + helpers
├── services/
│   └── api.js                        # Enhanced interceptors + retry
├── stores/
│   └── auth.js                       # Error handling improvements
├── views/
│   ├── Login.vue                     # Error message integration
│   └── student/
│       └── LoginStudent.vue          # Error message integration
└── e2e/
    └── tests/
        └── helpers/
            └── auth.ts               # Add student login helper
```

### 3.3 Configuration Files (No changes required)

- `frontend/vite.config.js` - Already configured
- `frontend/playwright.config.ts` - Already configured per contract
- `frontend/package.json` - Already has lint/typecheck scripts

---

## 4. Data Model / API / Interface Changes

### 4.1 Backend API (No changes required)

All required endpoints already exist:
- ✅ `/api/login/` (Admin/Teacher login)
- ✅ `/api/logout/` (Admin/Teacher logout)
- ✅ `/api/me/` (User info)
- ✅ `/api/students/login/` (Student login)
- ✅ `/api/students/logout/` (Student logout)
- ✅ `/api/students/me/` (Student info)
- ✅ `/api/change-password/` (Password change)

### 4.2 Frontend State Management (Minor enhancements)

**Auth Store** (`stores/auth.js`):
- Add `lastError` ref for storing error messages
- Add `clearError()` method
- Enhance error handling in `login()`, `loginStudent()`, `fetchUser()`

```javascript
// stores/auth.js enhancements
const lastError = ref(null)

function clearError() {
    lastError.value = null
}

// Update in return statement
return { 
    user, 
    isAuthenticated, 
    mustChangePassword, 
    isChecking,
    lastError,  // NEW
    login, 
    loginStudent, 
    logout, 
    fetchUser,
    clearMustChangePassword,
    clearError  // NEW
}
```

### 4.3 Router Metadata (No changes)

Existing route metadata is sufficient:
- `meta.requiresAuth` - Already used
- `meta.role` - Already used

---

## 5. Delivery Phases

### Phase 1: Audit & Documentation (2-3 hours)

**Goal**: Identify and document all issues

**Tasks**:
1. Create `audit.md` document structure
2. Audit router guards:
   - Test all redirect scenarios
   - Test back button after logout
   - Test direct URL navigation
   - Document findings
3. Audit axios configuration:
   - Test timeout scenarios
   - Test CSRF handling
   - Test 401/403 responses
   - Document findings
4. Audit multi-tab behavior:
   - Test logout in one tab
   - Test concurrent logins
   - Document findings
5. Compile recommendations and risk assessment

**Verification**:
- `audit.md` exists and contains structured findings
- All identified issues have risk level (High/Medium/Low)

### Phase 2: Router & Axios Enhancements (3-4 hours)

**Goal**: Fix critical security and UX issues

**Tasks**:
1. Enhance router guards:
   - Add try/catch around `fetchUser()`
   - Add helper functions
   - Fix redirect loops
   - Handle session expiry
2. Enhance axios interceptors:
   - Add 401 handling
   - Add 403 handling with CSRF retry
   - Add retry logic for transient errors
   - Add error differentiation
3. Run lint and typecheck:
   ```bash
   cd frontend
   npm run lint
   npm run typecheck
   ```

**Verification**:
- `npm run lint` passes
- `npm run typecheck` passes
- Manual testing: Logout → back button does not restore session
- Manual testing: Direct URL to `/admin/users` when not logged in → redirects to home

### Phase 3: UX Error Handling (2 hours)

**Goal**: User-friendly error messages

**Tasks**:
1. Create `errorMessages.js` utility
2. Create `LoadingOverlay.vue` component
3. Update `Login.vue` to use error messages
4. Update `LoginStudent.vue` to use error messages
5. Update `auth.js` store with error handling
6. Run lint and typecheck

**Verification**:
- `npm run lint` passes
- `npm run typecheck` passes
- Manual testing: Invalid credentials → French error message
- Manual testing: Network error → French error message

### Phase 4: E2E Test Suite - Admin (2-3 hours)

**Goal**: Complete Admin workflow tests

**Tasks**:
1. Create `admin_auth_flow.spec.ts`:
   - Test: Login → Dashboard
   - Test: Forced password change → Dashboard
   - Test: Access `/admin/users` (allowed)
   - Test: Logout → Back button
2. Run tests in Docker:
   ```bash
   cd infra/docker
   docker-compose -f docker-compose.local-prod.yml up -d
   docker-compose -f docker-compose.local-prod.yml exec backend sh -c "export PYTHONPATH=/app && python scripts/seed_e2e.py"
   cd ../../frontend
   npx playwright test admin_auth_flow
   ```

**Verification**:
- All admin tests pass in Docker environment
- Screenshots saved on failure
- Traces available for debugging

### Phase 5: E2E Test Suite - Teacher & Student (3-4 hours)

**Goal**: Complete Teacher and Student workflow tests

**Tasks**:
1. Create `teacher_auth_flow.spec.ts`:
   - Test: Login → Corrector Dashboard
   - Test: Access corrector desk (allowed)
   - Test: Access `/admin/users` (denied)
2. Create `student_auth_flow.spec.ts`:
   - Test: Login (INE + Last Name) → Portal
   - Test: View graded copies
   - Test: Download PDF
   - Test: Access `/admin-dashboard` (denied)
3. Update `helpers/auth.ts` with student login helper
4. Run tests in Docker

**Verification**:
- All teacher tests pass
- All student tests pass
- Role-based access control working correctly

### Phase 6: E2E Test Suite - Edge Cases (2 hours)

**Goal**: Test multi-tab and edge case scenarios

**Tasks**:
1. Create `multi_tab.spec.ts`:
   - Test: Logout in Tab A → Tab B detects session loss
2. Create `back_button.spec.ts`:
   - Test: Back button after logout for each role
3. Create `helpers/navigation.ts` with reusable helpers
4. Run all E2E tests:
   ```bash
   npx playwright test
   ```

**Verification**:
- All E2E tests pass (Admin + Teacher + Student + Edge cases)
- Test suite stable in CI environment
- All traces and screenshots captured

### Phase 7: Documentation & Handoff (1 hour)

**Goal**: Document expected navigation for each role

**Tasks**:
1. Create navigation specification document:
   - Admin navigation flow
   - Teacher navigation flow
   - Student navigation flow
   - Error scenarios
2. Update `audit.md` with verification results
3. Final verification:
   ```bash
   # Lint and typecheck
   cd frontend
   npm run lint
   npm run typecheck
   
   # E2E tests
   npx playwright test
   ```

**Verification**:
- All lint checks pass
- All typecheck passes
- All E2E tests pass
- Navigation specs documented

---

## 6. Verification Approach

### 6.1 Code Quality

**Commands**:
```bash
cd frontend
npm run lint         # ESLint validation
npm run typecheck    # TypeScript type checking
```

**Criteria**:
- ✅ Zero lint errors
- ✅ Zero type errors
- ✅ No console.error in production code

### 6.2 E2E Testing

**Environment**: Docker Compose (per `E2E_TESTING_CONTRACT.md`)

**Commands**:
```bash
# 1. Start environment
cd infra/docker
docker-compose -f docker-compose.local-prod.yml up -d

# 2. Seed data
docker-compose -f docker-compose.local-prod.yml exec backend \
  sh -c "export PYTHONPATH=/app && python scripts/seed_e2e.py"

# 3. Run tests
cd ../../frontend
npx playwright test

# 4. View report (if failures)
npx playwright show-report
```

**Criteria**:
- ✅ All tests pass in Docker environment
- ✅ Screenshots captured on failure
- ✅ Traces available for debugging
- ✅ Tests stable (no flakiness)

### 6.3 Manual Testing Checklist

**Admin Flow**:
- [ ] Login with forced password change works
- [ ] Can access all admin pages
- [ ] Cannot be bypassed via direct URL
- [ ] Logout → back button redirects to home

**Teacher Flow**:
- [ ] Login redirects to corrector dashboard
- [ ] Can access corrector desk
- [ ] Cannot access `/admin/users` (redirects to dashboard)
- [ ] Copy correction workflow stable

**Student Flow**:
- [ ] Login with INE + Last Name works
- [ ] Can view graded copies
- [ ] Can download PDF
- [ ] Cannot access admin/teacher pages (redirects to home)

**Edge Cases**:
- [ ] Logout in one tab → other tab detects on next navigation
- [ ] Session expiry shows clear message
- [ ] Network error shows clear message
- [ ] Page reload preserves session

### 6.4 Security Verification

**Checklist**:
- [ ] No client-side auth bypass possible
- [ ] CSRF token properly handled
- [ ] Session cookies are HttpOnly (backend responsibility)
- [ ] No sensitive data logged in console
- [ ] Error messages don't leak implementation details

### 6.5 Performance Metrics

**Targets** (per requirements NFR-1):
- `fetchUser()` latency < 2s (p95)
- Route navigation decision < 100ms
- No redundant API calls during single navigation

**Verification**:
- Use browser DevTools Network tab
- Verify single `/api/me/` or `/api/students/me/` call per navigation
- Verify guard decisions are synchronous after `fetchUser()` completes

---

## 7. Risk Assessment & Mitigation

### 7.1 Technical Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| Redirect loops in guards | High | Add loop detection, test all redirect scenarios |
| Race condition in `fetchUser()` | Medium | Use `isChecking` flag, test multi-tab scenarios |
| CSRF token refresh breaks flow | Medium | Test CSRF error recovery, implement single retry |
| E2E tests flaky in Docker | Medium | Follow `E2E_TESTING_CONTRACT.md`, use stable selectors |
| Session expiry during workflow | Medium | Test long-running sessions, show clear expiry message |

### 7.2 UX Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| Confusing error messages | High | Use French, user-friendly messages per `errorMessages.js` |
| Loading state not visible | Medium | Add `LoadingOverlay` component during auth checks |
| Back button restores protected page | High | Clear browser history on logout, test thoroughly |
| Multi-tab inconsistency | Medium | Test logout detection, document expected behavior |

### 7.3 Security Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| Client-side auth bypass | Critical | All auth checks server-validated, test direct URL access |
| CSRF token leakage | High | Use Django's HttpOnly cookie, never log token |
| Session fixation | High | Backend responsibility (Django session framework) |
| Role privilege escalation | High | Test role checks, Admin bypass only for Admin users |

---

## 8. Dependencies & Prerequisites

### 8.1 Backend Requirements (Already Met)

- ✅ `/api/me/` returns `must_change_password` flag
- ✅ `/api/change-password/` endpoint works
- ✅ Session-based auth with HttpOnly cookies
- ✅ CSRF protection enabled
- ✅ Role information in user response

### 8.2 Frontend Requirements (Already Met)

- ✅ Vue Router 4.x installed
- ✅ Pinia store configured
- ✅ Axios configured with interceptors
- ✅ Playwright installed and configured
- ✅ TypeScript types available

### 8.3 Infrastructure Requirements (Already Met)

- ✅ Docker Compose environment available
- ✅ Seed script `scripts/seed_e2e.py` exists
- ✅ E2E testing contract documented

---

## 9. Success Criteria

### 9.1 Functional Requirements

- ✅ All three role workflows (Admin, Teacher, Student) work flawlessly
- ✅ Forced password change blocks admin until changed
- ✅ No unauthorized access via direct URL navigation
- ✅ Back button after logout does not restore session
- ✅ Multi-tab logout detected on next navigation
- ✅ Session expiry handled gracefully with clear message

### 9.2 Technical Requirements

- ✅ All lint checks pass (`npm run lint`)
- ✅ All type checks pass (`npm run typecheck`)
- ✅ All E2E tests pass in Docker environment
- ✅ No console errors in browser
- ✅ `fetchUser()` latency < 2s (p95)
- ✅ No redundant API calls

### 9.3 Documentation Requirements

- ✅ `audit.md` with structured findings
- ✅ Navigation specs for each role documented
- ✅ E2E test suite covers all critical paths
- ✅ Screenshots and traces captured on test failure

---

## 10. Out of Scope

The following items are explicitly **out of scope** for this task:

1. **Backend Changes**:
   - Password validation rules (already implemented in Django)
   - Session timeout configuration (4h default is acceptable)
   - Audit logging (already required per security rules)

2. **Advanced Features**:
   - Remember me functionality
   - OAuth/SSO integration
   - 2FA/MFA
   - Password reset via email

3. **Mobile Responsiveness**:
   - Mobile UI optimizations (focus is on auth flow, not styling)

4. **Internationalization**:
   - Multi-language support (French only per requirements)

5. **Performance Optimizations**:
   - Code splitting for auth module
   - Lazy loading optimizations
   - (Current performance is acceptable)

---

## 11. References

### 11.1 Project Documentation

- `docs/E2E_TESTING_CONTRACT.md` - E2E testing environment and standards
- `docs/decisions/ADR-001.md` - Architecture decisions (if exists)
- `.antigravity/rules/01_security_rules.md` - Security requirements

### 11.2 External Documentation

- [Vue Router 4 - Navigation Guards](https://router.vuejs.org/guide/advanced/navigation-guards.html)
- [Axios - Interceptors](https://axios-http.com/docs/interceptors)
- [Playwright - Best Practices](https://playwright.dev/docs/best-practices)
- [Django CSRF Protection](https://docs.djangoproject.com/en/stable/ref/csrf/)

### 11.3 Code Patterns

**Router Guards**: Follow existing pattern in `router/index.js:109-149`  
**Axios Config**: Follow existing pattern in `services/api.js:1-46`  
**Pinia Store**: Follow existing pattern in `stores/auth.js:1-101`  
**E2E Tests**: Follow existing pattern in `e2e/admin_flow.spec.ts:1-40`

---

**Document Status**: ✅ Ready for Implementation  
**Estimated Effort**: 15-20 hours (across 7 phases)  
**Next Step**: Proceed to Planning phase (breakdown into tasks)
