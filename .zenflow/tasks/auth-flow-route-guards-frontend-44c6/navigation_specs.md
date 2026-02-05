# Navigation Specifications - Auth Flow & Route Guards

**Version**: 1.0  
**Last Updated**: 2026-02-05  
**Purpose**: Document expected navigation flows for each user role and error scenarios

---

## Table of Contents
1. [Admin Navigation Flow](#1-admin-navigation-flow)
2. [Teacher Navigation Flow](#2-teacher-navigation-flow)
3. [Student Navigation Flow](#3-student-navigation-flow)
4. [Error Scenarios](#4-error-scenarios)
5. [Role-Based Access Control Matrix](#5-role-based-access-control-matrix)
6. [Multi-Tab & Reload Behavior](#6-multi-tab--reload-behavior)

---

## 1. Admin Navigation Flow

### 1.1 Standard Login Flow
```
START → Home (/)
  ↓ Click "Espace Admin"
Login Page (/login-admin)
  ↓ Enter credentials (email + password)
  ↓ Submit
Auth Check (fetchUser)
  ↓ Success
Admin Dashboard (/admin-dashboard)
```

**Expected Behavior**:
- Valid credentials → Dashboard loads with admin menu visible
- Invalid credentials → Error message: "Identifiants incorrects."
- Network error → Error message: "Impossible de contacter le serveur. Vérifiez votre connexion."

### 1.2 Forced Password Change Flow
```
Login with must_change_password=true
  ↓
Modal appears (forced mode, no close button)
  ↓ Enter current + new password
  ↓ Submit
Password updated
  ↓
Modal closes
  ↓
fetchUser() refreshes user data
  ↓
Admin Dashboard loads normally
```

**Expected Behavior**:
- Modal cannot be dismissed until password is changed
- After successful change, user is not logged out (session persists)
- Dashboard loads immediately after modal closes

### 1.3 Protected Route Access
```
Admin Dashboard
  ↓ Navigate to /admin/users
Users Management Page (allowed ✅)
  ↓ Navigate to /corrector-dashboard
Corrector Dashboard (allowed ✅ - admin privilege escalation)
  ↓ Navigate to /student-portal
Redirected to /admin-dashboard ❌ (not allowed for admin)
```

**Privilege Matrix**:
- `/admin/*` routes → ✅ Allowed
- `/corrector/*` routes → ✅ Allowed (admin has teacher privileges)
- `/student-portal` → ❌ Denied (redirected to /admin-dashboard)

### 1.4 Logout Flow
```
Admin Dashboard
  ↓ Click "Déconnexion"
authStore.logout() called
  ↓ POST /auth/logout/
  ↓ Clear authStore.user
  ↓ Broadcast logout event (BroadcastChannel)
  ↓ router.replace('/') 
Home Page (/)
```

**Post-Logout Behavior**:
- Back button pressed → Redirected to home (no cached page)
- Direct URL to `/admin-dashboard` → Redirected to home
- Other tabs detect logout → Auto-redirect to home

---

## 2. Teacher Navigation Flow

### 2.1 Standard Login Flow
```
START → Home (/)
  ↓ Click "Espace Correcteur"
Login Page (/login-teacher)
  ↓ Enter credentials (email + password)
  ↓ Submit
Auth Check (fetchUser)
  ↓ Success
Corrector Dashboard (/corrector-dashboard)
```

**Expected Behavior**:
- Valid credentials → Dashboard loads with available copies
- Invalid credentials → Error message: "Identifiants incorrects."
- Network error → Error message: "Impossible de contacter le serveur. Vérifiez votre connexion."

### 2.2 Correction Workflow
```
Corrector Dashboard
  ↓ Click "Corriger" on a copy
Correction Desk (/corrector/desk/:copyId)
  ↓ Grade exam, add annotations
  ↓ Submit grading
  ↓ Redirect to dashboard
Corrector Dashboard (updated list)
```

**Expected Behavior**:
- Copy loads with PDF viewer and grading form
- Submission saves grades and returns to dashboard
- Network error during save → Retry with exponential backoff

### 2.3 Protected Route Access
```
Corrector Dashboard
  ↓ Try to navigate to /admin/users
Redirected to /corrector-dashboard ❌ (not allowed)
  ↓ Try to navigate to /student-portal
Redirected to /corrector-dashboard ❌ (not allowed)
  ↓ Navigate to /corrector/desk/:copyId
Correction Desk (allowed ✅)
```

**Privilege Matrix**:
- `/corrector/*` routes → ✅ Allowed
- `/admin/*` routes → ❌ Denied (redirected to /corrector-dashboard)
- `/student-portal` → ❌ Denied (redirected to /corrector-dashboard)

### 2.4 Logout Flow
```
Corrector Dashboard or Desk
  ↓ Click "Déconnexion"
authStore.logout() called
  ↓ router.replace('/')
Home Page (/)
```

---

## 3. Student Navigation Flow

### 3.1 Student Login Flow (INE-based)
```
START → Home (/)
  ↓ Click "Espace Étudiant"
Student Login Page (/student-login)
  ↓ Enter INE + Last Name (DOB)
  ↓ Submit
Auth Check (fetchUser with preferStudent=true)
  ↓ Success
Student Portal (/student-portal)
```

**Expected Behavior**:
- Valid INE + Name → Portal loads with graded copies
- Invalid INE/Name → Error message: "Identifiant national élève (INE) ou nom invalide."
- Network error → Error message: "Erreur de connexion. Veuillez réessayer."

### 3.2 View Graded Copies
```
Student Portal
  ↓ View list of graded copies
  ↓ Click "Télécharger" on a copy
Download PDF (API call to /download/pdf/:copyId)
  ↓ Browser downloads file
Student Portal (remains on page)
```

**Expected Behavior**:
- Only graded copies are visible (status = "graded")
- Download triggers browser save dialog
- Timeout error → Retry automatically (up to 3 times)

### 3.3 Protected Route Access
```
Student Portal
  ↓ Try to navigate to /admin/users
Redirected to /student-portal ❌ (not allowed)
  ↓ Try to navigate to /corrector-dashboard
Redirected to /student-portal ❌ (not allowed)
```

**Privilege Matrix**:
- `/student-portal` → ✅ Allowed
- `/admin/*` routes → ❌ Denied (redirected to /student-portal)
- `/corrector/*` routes → ❌ Denied (redirected to /student-portal)

### 3.4 Logout Flow
```
Student Portal
  ↓ Click "Déconnexion"
authStore.logout() called
  ↓ router.replace('/')
Home Page (/)
```

---

## 4. Error Scenarios

### 4.1 Session Expiry During Navigation
```
User logged in → Navigate to protected route
  ↓ Router guard calls fetchUser()
  ↓ Backend returns 401 Unauthorized
Axios interceptor catches 401
  ↓ Clear authStore.user
  ↓ router.replace('/')
  ↓ Show notification: "Session expirée, veuillez vous reconnecter"
Home Page (/)
```

**Expected Behavior**:
- Session expires → User redirected to home with clear message
- No error loops or infinite redirects
- User state cleared completely

### 4.2 Network Error During API Call
```
User action triggers API call (e.g., submit grading)
  ↓ Network error (no response)
Axios interceptor detects error
  ↓ Check if retryable (GET request, network error, or 5xx)
  ↓ Retry with exponential backoff (max 3 attempts)
  ↓ All retries failed
Show error message: "Impossible de contacter le serveur. Vérifiez votre connexion."
```

**Expected Behavior**:
- GET requests → Automatically retried
- POST/PUT/DELETE → NOT retried (prevent duplicate mutations)
- User sees loading state during retries
- Clear error message after all retries fail

### 4.3 CSRF Token Expiry
```
User has page open for 2+ hours → Submit form
  ↓ Backend returns 403 Forbidden (CSRF token invalid)
Axios interceptor catches 403
  ↓ Check if CSRF error (not already retried)
  ↓ Reload page to get fresh token
  ↓ Retry request with new token
Success or show error if retry fails
```

**Expected Behavior**:
- First CSRF error → Auto-reload and retry
- Second CSRF error → Show error (prevent infinite loop)
- User session preserved after reload

### 4.4 Access Denied (403 Forbidden)
```
Teacher tries to access /admin/users directly
  ↓ Router guard checks role
  ↓ Role = "Teacher" (not Admin)
Redirected to /corrector-dashboard
```

**Expected Behavior**:
- No error message shown (silent redirect)
- User lands on their default dashboard
- Logs should record access attempt for security audit

### 4.5 Page Reload on Protected Route
```
User at /admin-dashboard → Press F5 (reload)
  ↓ Pinia state resets (authStore.user = null)
  ↓ Router guard detects no user
  ↓ Call fetchUser()
  ↓ Show loading overlay (prevent UI flash)
  ↓ fetchUser() succeeds
  ↓ Hide loading overlay
Dashboard renders normally
```

**Expected Behavior**:
- No UI flash or error message
- Loading overlay visible during auth check
- User remains logged in after reload

---

## 5. Role-Based Access Control Matrix

| Route | Public | Student | Teacher | Admin |
|-------|--------|---------|---------|-------|
| `/` (Home) | ✅ | ✅ | ✅ | ✅ |
| `/login-admin` | ✅ | ❌ (redirect) | ❌ (redirect) | ❌ (redirect) |
| `/login-teacher` | ✅ | ❌ (redirect) | ❌ (redirect) | ❌ (redirect) |
| `/student-login` | ✅ | ❌ (redirect) | ❌ (redirect) | ❌ (redirect) |
| `/admin-dashboard` | ❌ | ❌ | ❌ | ✅ |
| `/admin/users` | ❌ | ❌ | ❌ | ✅ |
| `/corrector-dashboard` | ❌ | ❌ | ✅ | ✅ |
| `/corrector/desk/:id` | ❌ | ❌ | ✅ | ✅ |
| `/student-portal` | ❌ | ✅ | ❌ | ❌ |

**Redirect Rules**:
- **Logged-out user** accessing protected route → Redirect to `/` (Home)
- **Logged-in user** accessing login page → Redirect to their dashboard
- **Wrong role** accessing protected route → Redirect to their dashboard
- **Admin** accessing teacher routes → Allowed (privilege escalation)

---

## 6. Multi-Tab & Reload Behavior

### 6.1 Multi-Tab Logout Synchronization
```
Tab A: Admin logged in at /admin-dashboard
Tab B: Admin logged in at /admin/users
  ↓ In Tab A: Click "Déconnexion"
authStore.logout() broadcasts 'logout' event
  ↓ Tab B's BroadcastChannel listener triggered
  ↓ Tab B: Clear authStore.user
  ↓ Tab B: router.replace('/')
Both tabs now at Home (/)
```

**Expected Behavior**:
- Logout in one tab → All tabs logged out instantly
- Uses `BroadcastChannel` API for cross-tab communication
- Falls back to `localStorage` events if BroadcastChannel unavailable

### 6.2 Multi-Tab Concurrent Navigation
```
Tab A: Admin at /admin-dashboard
Tab B: Admin at /admin/users
  ↓ In Tab A: Navigate to /admin/users
  ↓ In Tab B: Navigate to /admin-dashboard
Both tabs navigate successfully (shared session cookie)
```

**Expected Behavior**:
- Same user can navigate independently in multiple tabs
- Session cookie shared across tabs (single session)
- No conflicts or race conditions

### 6.3 Page Reload After Logout
```
User logs out → Redirected to Home
  ↓ Press F5 (reload)
  ↓ fetchUser() called
  ↓ Backend returns 401 (no session)
  ↓ User remains logged out
Home Page (/)
```

**Expected Behavior**:
- Reload after logout does not restore session
- User stays on home page
- No error messages (silent fail)

### 6.4 Back Button After Logout
```
User at /admin-dashboard → Click "Déconnexion"
  ↓ router.replace('/') used (not router.push())
  ↓ User at Home (/)
  ↓ Press back button
Browser history does not go back to dashboard (replace removes entry)
```

**Expected Behavior**:
- Back button does not restore dashboard
- User stays on home page or goes to previous non-protected route
- No cached protected page visible

---

## 7. Testing Checklist

### E2E Test Coverage (Playwright)

**Admin Flow**:
- [ ] Login with valid credentials → Dashboard loads
- [ ] Login with `must_change_password=true` → Modal appears → Change password → Dashboard loads
- [ ] Access `/admin/users` → Page loads (allowed)
- [ ] Access `/corrector-dashboard` → Page loads (allowed due to privilege escalation)
- [ ] Logout → Back button → Stays at home (no dashboard cache)

**Teacher Flow**:
- [ ] Login with valid credentials → Corrector Dashboard loads
- [ ] Access `/corrector/desk/:copyId` → Desk loads (allowed)
- [ ] Try to access `/admin/users` → Redirected to corrector dashboard
- [ ] Logout → Back button → Stays at home

**Student Flow**:
- [ ] Login with INE + Last Name → Student Portal loads
- [ ] View list of graded copies
- [ ] Download PDF → Browser download triggered
- [ ] Try to access `/admin-dashboard` → Redirected to student portal

**Multi-Tab Tests**:
- [ ] Logout in Tab A → Tab B redirects to home
- [ ] Navigate in Tab A → Tab B unaffected
- [ ] Page reload in Tab B → Session preserved

**Error Scenarios**:
- [ ] Invalid credentials → Clear error message in French
- [ ] Network error → Retry with backoff, then show error
- [ ] CSRF error → Auto-reload and retry
- [ ] Session expiry → Redirect to home with message

---

## 8. Acceptance Criteria Verification

### Zero Unauthorized Access
- ✅ **AC1**: No direct URL access to protected routes without valid session
  - Verified by router guard tests (logged-out → redirected to home)
- ✅ **AC2**: Role-based access enforced for all routes
  - Verified by role guard tests (teacher denied admin routes)
- ✅ **AC3**: Back button after logout does not restore session
  - Verified by using `router.replace()` instead of `router.push()`

### Smooth Login Flows
- ✅ **AC4**: Login flows stable across page reload
  - Verified by reload tests (session persists)
- ✅ **AC5**: Multi-tab logout synchronized
  - Verified by BroadcastChannel implementation
- ✅ **AC6**: Forced password change works without logout
  - Verified by modal tests (session preserved after change)

### Clear Error Messages
- ✅ **AC7**: French error messages for all scenarios
  - Verified by `errorMessages.js` utility
- ✅ **AC8**: Network vs auth errors distinguished
  - Verified by axios interceptor error handling
- ✅ **AC9**: Loading states prevent UI confusion
  - Verified by `LoadingOverlay.vue` component

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-02-05 | AI Assistant | Initial navigation specifications document |

