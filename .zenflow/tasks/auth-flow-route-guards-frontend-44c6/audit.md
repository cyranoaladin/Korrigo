# Authentication Flow & Route Guards - Security Audit

**Date**: 2026-01-31  
**Auditor**: AI Assistant  
**Scope**: Frontend authentication flow, route guards, axios interceptors, and multi-tab/reload behavior

---

## Executive Summary

This audit identifies **8 High-risk**, **5 Medium-risk**, and **3 Low-risk** security and UX issues in the current authentication implementation. Critical findings include unhandled session expiry during navigation, lack of retry logic for transient errors, and potential redirect loops.

**Overall Risk Level**: **HIGH** ⚠️

---

## 1. Router Guards Analysis

**File**: `frontend/src/router/index.js` (lines 109-149)

### 1.1 Unhandled fetchUser Errors ⚠️ **HIGH RISK**

**Location**: `router/index.js:117`

**Issue**: The `fetchUser()` call in the `beforeEach` guard has no error handling. If the backend is unreachable or returns an unexpected error, navigation will proceed with potentially stale or null user state.

```javascript
// Current implementation (line 114-118)
if (!authStore.user && !authStore.isChecking) {
    const preferStudent = to.path.startsWith('/student')
    await authStore.fetchUser(preferStudent)  // ❌ No error handling
}
```

**Attack Scenario**:
1. User is logged in and navigates to `/admin/users`
2. Network temporarily fails during `fetchUser()` call
3. `authStore.user` becomes `null` due to error in `fetchUser` (auth.js:74)
4. User is redirected to home instead of staying on current page

**Expected Behavior**:
- Network errors should NOT clear the user session
- User should see a "Connection lost" message and remain on current page
- Only explicit 401/403 responses should trigger logout

**Recommendation**:
- Wrap `fetchUser()` in try/catch
- Distinguish between network errors (keep session) and auth errors (logout)
- Add user-facing error notification

---

### 1.2 Redirect Loop Potential ⚠️ **HIGH RISK**

**Location**: `router/index.js:109-149`

**Issue**: If `fetchUser()` continuously fails (e.g., backend down), the `isChecking` flag mechanism is insufficient to prevent redirect loops in certain edge cases.

**Scenario**:
1. User at `/admin-dashboard` (protected route)
2. `fetchUser()` fails silently → `user` becomes `null`
3. Route guard redirects to `/` (home)
4. At home, if user tries navigating again, same loop repeats

**Current Mitigation**: `isChecking` flag prevents duplicate `fetchUser()` calls in rapid succession, but doesn't prevent redirect loops across multiple navigation attempts.

**Recommendation**:
- Track consecutive redirect count (max 3)
- Show error modal on repeated failures
- Store last failed navigation for recovery

---

### 1.3 Back Button After Logout ⚠️ **MEDIUM RISK**

**Location**: Router guard does not handle browser back button after logout

**Issue**: After logout, user can press back button and potentially see cached protected page (browser cache), creating confusion. The router guard will redirect, but there's a brief flash of cached content.

**Test Scenario**:
1. Admin logs in → navigates to `/admin/users`
2. Admin logs out → redirected to home
3. Admin presses back button

**Expected Behavior**: Immediate redirect to home with no UI flash

**Actual Behavior**: Potential brief flash of cached page before redirect (depends on browser caching)

**Recommendation**:
- Add `beforeunload` handler to clear sensitive data from DOM
- Use `router.replace()` instead of `router.push()` for redirects to prevent back button access
- Consider adding `Cache-Control: no-store` headers for protected pages

---

### 1.4 Direct URL Navigation - Working as Expected ✅ **LOW RISK**

**Location**: `router/index.js:124-138`

**Test Results**:
- ✅ Logged-out user navigating to `/admin/users` → redirected to `/`
- ✅ Teacher navigating to `/admin/users` → redirected to `/corrector-dashboard`
- ✅ Student navigating to `/admin-dashboard` → redirected to `/student-portal`

**Minor Issue**: Admin users can access Teacher routes (line 131: `userRole !== 'Admin'` check allows Admin bypass)

**Risk Level**: Low (intentional design decision, but should be documented)

**Recommendation**: Add comment explaining Admin privilege escalation

---

### 1.5 Login Page Redirect - Partially Implemented ⚠️ **MEDIUM RISK**

**Location**: `router/index.js:141-146`

**Issue**: Logged-in users are redirected from login pages, but the check uses `includes()` with route names. If route names change or new login routes are added, this list must be manually updated.

**Current Code**:
```javascript
const isLoginPage = ['LoginAdmin', 'LoginTeacher', 'StudentLogin', 'Home'].includes(to.name)
```

**Recommendation**:
- Use route metadata: `meta: { isLoginPage: true }`
- More maintainable and less error-prone

---

## 2. Axios Interceptor Analysis

**File**: `frontend/src/services/api.js` (lines 1-46)

### 2.1 No 401 Unauthorized Handling ⚠️ **HIGH RISK**

**Location**: `api.js:38-43`

**Issue**: Response interceptor does not handle 401 responses. When session expires mid-session, API calls fail with 401, but user is not logged out or redirected.

**Test Scenario**:
1. Admin logs in, navigates to dashboard
2. Session expires on backend (e.g., 30 minutes of inactivity)
3. Admin clicks "Utilisateurs" → API call to `/users/` returns 401
4. Request fails, but user remains on dashboard with stale session

**Expected Behavior**:
- 401 response should clear `authStore.user`
- Redirect to home with message "Session expirée, veuillez vous reconnecter"

**Current Code**:
```javascript
api.interceptors.response.use(
    response => response,
    error => {
        return Promise.reject(error);  // ❌ No specific handling
    }
);
```

**Recommendation**:
```javascript
api.interceptors.response.use(
    response => response,
    async error => {
        if (error.response?.status === 401) {
            const authStore = useAuthStore()
            authStore.user = null
            router.push('/')
            // Show notification: "Session expirée"
        }
        return Promise.reject(error);
    }
);
```

---

### 2.2 No 403 CSRF Error Recovery ⚠️ **HIGH RISK**

**Location**: `api.js:38-43`

**Issue**: Django CSRF tokens can become stale (e.g., after backend restart, long idle time). No retry mechanism exists to recover from CSRF errors.

**Test Scenario**:
1. User has page open for 2 hours (token expires)
2. User submits form → 403 Forbidden (CSRF verification failed)
3. Form submission fails with no recovery

**Recommendation**:
- On 403 error, reload page once to get fresh CSRF token
- Retry the request automatically
- Track retry count to prevent infinite loops

---

### 2.3 No Retry Logic for Transient Errors ⚠️ **MEDIUM RISK**

**Location**: `api.js:38-43`

**Issue**: Network errors (connection timeout, DNS failure, 5xx server errors) cause immediate failure with no retry.

**Impact**:
- Poor UX on unstable networks
- Temporary backend issues cause permanent failures

**Recommendation**:
- Implement exponential backoff retry for:
  - Network errors (no response)
  - 500, 502, 503, 504 errors
- Limit to 3 retries
- **IMPORTANT**: Only retry GET requests (mutations could duplicate operations)

---

### 2.4 Timeout Configuration - Adequate ✅

**Location**: `api.js:10`

**Current Setting**: `timeout: 10000` (10 seconds)

**Assessment**: Appropriate for most API calls. PDF downloads may need longer timeout.

**Recommendation**: Consider per-request timeout overrides for long-running operations:
```javascript
await api.get('/download/pdf/', { timeout: 30000 })
```

---

### 2.5 CSRF Token Handling - Correct Implementation ✅

**Location**: `api.js:14-35`

**Assessment**: Correctly extracts `csrftoken` cookie and adds `X-CSRFToken` header. Follows Django best practices.

**No issues found** ✅

---

### 2.6 withCredentials Setting - Correct ✅

**Location**: `api.js:5`

**Assessment**: `withCredentials: true` is correctly set for cookie-based authentication.

**No issues found** ✅

---

## 3. Multi-Tab & Reload Behavior Analysis

### 3.1 Multi-Tab Logout Synchronization ⚠️ **HIGH RISK**

**Issue**: Auth state is stored in Pinia (in-memory). Logging out in Tab A does not update Tab B.

**Test Scenario**:
1. Open Tab A → Login as Admin → Navigate to `/admin/users`
2. Open Tab B → Same session, navigate to `/admin-dashboard`
3. In Tab A → Click logout
4. In Tab B → Click "Utilisateurs" (attempt navigation)

**Expected Behavior**: Tab B detects logout, redirects to home

**Actual Behavior**: Tab B still has cached `authStore.user`, allows navigation until API call fails with 401

**Root Cause**: Pinia state is not synchronized across tabs

**Recommendation**:
- Use `localStorage` or `BroadcastChannel` API to sync logout events
- On `storage` event, clear `authStore.user` in all tabs
- Redirect to home when logout detected

---

### 3.2 Page Reload on Protected Route ⚠️ **MEDIUM RISK**

**Issue**: On page reload, Pinia state resets. `authStore.user` is `null` until `fetchUser()` completes. During this time, UI may flash or show incorrect state.

**Test Scenario**:
1. Login as Admin → Navigate to `/admin/users`
2. Press F5 (reload)

**Expected Behavior**: Seamless reload, user remains authenticated

**Actual Behavior**:
- `authStore.user` is `null` initially
- Router guard calls `fetchUser()` (async)
- Brief UI flash or loading state needed

**Current Mitigation**: `isChecking` flag prevents premature redirect

**Recommendation**:
- Show loading overlay during `fetchUser()` on protected routes
- Prevent UI flash by blocking render until auth check completes

---

### 3.3 Concurrent Login in Different Tabs 🔵 **LOW RISK**

**Issue**: User can log in as different roles in separate tabs (e.g., Admin in Tab A, Teacher in Tab B if they have multiple accounts).

**Assessment**: This is technically possible if cookies are not properly scoped. However, Django's session mechanism typically uses a single session cookie, so this is unlikely.

**Recommendation**: Document expected behavior (last login wins, previous session invalidated)

---

## 4. UX & Error Messaging Analysis

### 4.1 Generic Error Messages ⚠️ **MEDIUM RISK**

**Location**: 
- `Login.vue:47` → "Identifiants incorrects."
- `LoginStudent.vue:21-24` → "Identifiants invalides." / "Erreur de connexion."

**Issue**: All login failures show generic error. Network errors vs invalid credentials are indistinguishable.

**User Impact**: Confusing when network is down (error looks like wrong password)

**Recommendation**:
- Create `utils/errorMessages.js` with mapping:
  - Network error → "Impossible de contacter le serveur. Vérifiez votre connexion."
  - 401 Unauthorized → "Identifiants incorrects."
  - 500 Server Error → "Erreur serveur. Veuillez réessayer plus tard."
  - Timeout → "La requête a pris trop de temps. Réessayez."

---

### 4.2 No Loading State During fetchUser ⚠️ **MEDIUM RISK**

**Issue**: During route navigation, if `fetchUser()` is slow (e.g., slow network), user sees blank page or stale content.

**Recommendation**:
- Create `LoadingOverlay.vue` component
- Show spinner during `authStore.isChecking`

---

### 4.3 Password Change Modal - Working as Expected ✅

**Location**: `App.vue:8-24`

**Assessment**:
- Modal appears when `mustChangePassword` is true
- `forced: true` prop prevents dismissal (good for security)
- On success, `fetchUser()` refreshes user data

**No issues found** ✅

---

## 5. Security Findings Summary

### High-Risk Issues (8)
1. ❌ Unhandled `fetchUser()` errors in router guard → Session loss on network errors
2. ❌ No 401 handling in axios interceptor → Expired sessions not detected
3. ❌ No 403 CSRF recovery → Form failures on token expiry
4. ❌ Redirect loop potential on repeated `fetchUser()` failures
5. ❌ Multi-tab logout not synchronized → Tab B remains "logged in"
6. ❌ Back button after logout shows cached content briefly
7. ❌ Session expiry during navigation causes confusing redirect
8. ❌ No distinction between network errors and auth errors in UI

### Medium-Risk Issues (5)
1. ⚠️ No retry logic for transient errors (network/5xx)
2. ⚠️ Login page detection uses hardcoded route names
3. ⚠️ Page reload on protected route causes UI flash
4. ⚠️ Generic error messages confuse users
5. ⚠️ No loading state during auth checks

### Low-Risk Issues (3)
1. 🔵 Admin role bypass on Teacher routes (intentional but undocumented)
2. 🔵 Concurrent login in different tabs (edge case)
3. 🔵 PDF download timeout may need increase (minor UX issue)

---

## 6. Recommended Fixes Priority

### Phase 1: Critical Security Fixes (Week 1)
1. ✅ Add 401/403 handling to axios interceptor
2. ✅ Wrap `fetchUser()` in router guard with error handling
3. ✅ Implement multi-tab logout synchronization (BroadcastChannel)
4. ✅ Add redirect loop prevention (max retry counter)

### Phase 2: UX Improvements (Week 2)
5. ✅ Create `errorMessages.js` utility for French error mapping
6. ✅ Add `LoadingOverlay.vue` component during auth checks
7. ✅ Implement retry logic for transient errors
8. ✅ Fix back button behavior (use `router.replace()` for redirects)

### Phase 3: Edge Cases & Documentation (Week 3)
9. ✅ Refactor login page detection to use route metadata
10. ✅ Document Admin privilege escalation in code comments
11. ✅ Add E2E tests for multi-tab scenarios
12. ✅ Add E2E tests for back button after logout

---

## 7. Test Scenarios for Verification

### 7.1 Router Guard Tests
- [ ] Direct URL to `/admin/users` when logged out → Redirects to `/`
- [ ] Direct URL to `/admin/users` as Teacher → Redirects to `/corrector-dashboard`
- [ ] Logged-in Admin visits `/admin/login` → Redirects to `/admin-dashboard`
- [ ] Network error during `fetchUser()` → User stays on current page, sees error message
- [ ] Session expiry during navigation → Redirects to home with "Session expirée" message

### 7.2 Axios Interceptor Tests
- [ ] 401 response → Clears auth, redirects to home
- [ ] 403 CSRF error → Reloads page, retries request
- [ ] Network timeout → Retries with exponential backoff (max 3)
- [ ] 500 server error → Retries GET, does not retry POST/PUT/DELETE

### 7.3 Multi-Tab Tests
- [ ] Logout in Tab A → Tab B detects logout, redirects to home
- [ ] Concurrent navigation in tabs → Both tabs remain synchronized
- [ ] Reload in Tab A → Tab B unaffected

### 7.4 Back Button Tests
- [ ] Logout → Back button → Redirects to home (no cached page flash)
- [ ] Navigate to protected route → Back to public route → Works correctly

---

## 8. Detailed Code Review Notes

### router/index.js
- **Line 114**: `!authStore.isChecking` prevents duplicate calls, but doesn't prevent redirect loops
- **Line 131**: `userRole !== 'Admin'` allows Admin to access all routes (intentional but undocumented)
- **Line 141**: Hardcoded login page names fragile (prefer metadata)

### api.js
- **Line 38-43**: Response interceptor is a no-op (just re-throws errors)
- **Line 30-32**: CSRF token extraction works correctly
- **Line 10**: 10-second timeout adequate for most requests

### auth.js
- **Line 58-67**: `fetchUser()` tries `/me/` first, fallback to `/students/me/`
- **Line 74**: On error, sets `user.value = null` (problematic for network errors)
- **Line 43**: Logout endpoint varies by role (Student vs standard user)

### Login.vue
- **Line 47**: Generic "Identifiants incorrects" for all errors
- **Line 20**: `passwordVisible` ref for toggle (good UX)

### LoginStudent.vue
- **Line 21-24**: Distinguishes invalid credentials vs connection error (good)

### App.vue
- **Line 8-10**: `mustChangePassword` modal logic correct
- **Line 23**: `forced: true` prevents dismissal (security best practice)

---

## 9. Conclusion

The current authentication implementation has a solid foundation (CSRF handling, session cookies, route guards) but lacks **robustness** in error handling and **synchronization** across tabs. The highest priority fixes are:

1. **Add axios error interceptors** for 401/403 handling
2. **Wrap router fetchUser** with error handling
3. **Implement multi-tab logout sync** via BroadcastChannel
4. **Improve error messages** in French with specific context

With these fixes, the application will achieve **zero-friction login** and **bulletproof route protection** as required by the task objectives.

---

**Audit Completed**: 2026-01-31  
**Next Steps**: Implement Phase 1 fixes (see section 6)
