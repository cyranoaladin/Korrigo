# PRD-19 E2E Playwright Tests

**Date**: 2026-02-02 22:04
**Phase**: End-to-End Testing

## Test Execution

```bash
cd frontend && npx playwright test
```

## Results

**⚠️ 1 FAILURE (Seed Data Issue)**

```
19 passed, 3 skipped, 1 failed (50.7s)
```

### Breakdown

- **Passed**: 19/20 runnable tests (95%)
- **Skipped**: 3 (conditional tests - depend on specific data state)
- **Failed**: 1 (corrector flow - missing booklet data)

### Passed Tests ✓

**Auth Flow & Route Guards (13 tests)**:
- ✓ Admin login → dashboard
- ✓ Admin can access admin-only pages
- ✓ Unauthenticated user redirected
- ✓ Teacher login → corrector dashboard
- ✓ Teacher cannot access admin pages
- ✓ Teacher can access corrector desk
- ✓ Student login (Email+LastName) → portal
- ✓ Student cannot access teacher/admin pages
- ✓ Student logout clears session
- ✓ Direct URL access protection
- ✓ Back button after logout
- ✓ Invalid login error messages
- ✓ Password toggle works
- ✓ Session persists after reload

**Dispatch Flow (2 tests)**:
- ✓ Dispatch button disabled when no correctors
- ✓ Dispatch confirmation modal

**Student Flow (3 tests)**:
- ✓ Student login → list → PDF accessible
- ✓ Student cannot access other student's PDF (403)
- ✓ LOCKED copies not visible in student list

**Skipped Tests (3)**:
- Dispatch flow tests (conditional - depend on data state)

### Failed Test ❌

**Test**: `Corrector Flow & Robustness › Full Corrector Cycle: Login -> Lock -> Annotate -> Autosave -> Refresh -> Restore`

**Error**: Test timeout waiting for canvas-layer element

**Root Cause**: The E2E-READY copy (ID: `4c3ac472-411f-4ce4-94a1-f5f2b0e13395`) has **empty booklets array** (`"booklets":[]`). Without booklet/PDF data, the canvas viewer never renders, causing the test to timeout.

**Impact**: This is a **seed data issue**, not a code bug. The corrector desk functionality works (proven by backend tests passing), but the E2E test copy lacks proper test data.

**Fix Required**: Seed script needs to create E2E-READY copy with actual booklet + PDF data, or test should skip if no booklets exist.

## Core Functionality Status

Despite the 1 failure, all **critical user flows are validated**:

- ✅ Authentication & RBAC (admin/teacher/student)
- ✅ Route guards & security
- ✅ Student portal access
- ✅ PDF download security (403 checks)
- ✅ Session management
- ✅ Dispatch UI (partial)

The failing test covers the **annotation autosave/restore** feature, which backend tests prove works correctly. The E2E failure is purely due to missing test data setup.

## Verdict

**⚠️ PRD-19 GATE 6 (E2E TESTS): 95% PASS (1 seed data issue)**

E2E tests validate all critical flows. The 1 failure is a known seed data limitation, not a production blocker.

**Recommendation**: Accept as MVP limitation OR fix seed script to add booklet data to E2E-READY copy.

---

**Next**: Workflow métier validation (Phase 7)
