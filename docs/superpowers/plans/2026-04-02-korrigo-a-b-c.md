# Korrigo A-B-C Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Corriger les écarts de sécurité/cohérence restants puis ajouter les capacités backend et frontend demandées sans régression sur la production active.

**Architecture:** Le travail est séquencé en trois lots. Le lot A sécurise et stabilise les permissions et le login. Le lot B ajoute les nouvelles API backend et la tâche asynchrone d'email. Le lot C branche le frontend sur ces nouvelles capacités avec le minimum de surface modifiée.

**Tech Stack:** Django 4.2, DRF, Celery, PostgreSQL, Vue 3 Composition API, Pinia, Vue Router, TailwindCSS

---

## Chunk 1: Lot A Backend Safety

### Task 1: Permissions grading admin-only

**Files:**
- Modify: `backend/grading/views.py`
- Test: `backend/grading/tests/test_audit_remediation.py`

- [ ] Step 1: Add failing tests for teacher/admin access to force unlock and reopen.
- [ ] Step 2: Run the targeted tests and verify the current failures or weak coverage.
- [ ] Step 3: Remove redundant inline admin checks from `AdminForceUnlockView` and `CopyReopenView`, keeping `permission_classes = [IsKorrigoAdmin]`.
- [ ] Step 4: Run `pytest backend/grading/tests/test_audit_remediation.py -q`.
- [ ] Step 5: Commit the chunk.

### Task 2: Student login robustness

**Files:**
- Modify: `backend/students/views.py`
- Test: `backend/core/tests/test_student_rbac.py`

- [ ] Step 1: Add failing test for duplicate or ambiguous student email login not crashing.
- [ ] Step 2: Run the targeted test to verify the current failure mode or missing behavior.
- [ ] Step 3: Replace `User.objects.get(email=email)` with a case-insensitive `.filter(...).first()` flow and keep the password-change session cache behavior.
- [ ] Step 4: Run `pytest backend/core/tests/test_student_rbac.py -q`.
- [ ] Step 5: Commit the chunk.

### Task 3: Group name consistency

**Files:**
- Modify: `backend/core/migrations/0004_questionnaire_coordinator_group.py`
- Test: existing auth/role tests if impacted

- [ ] Step 1: Update the migration to create `questionnaire_coordinator` in lowercase and delete with `name__iexact`.
- [ ] Step 2: Run targeted auth tests plus `python manage.py makemigrations --check --dry-run`.
- [ ] Step 3: Commit the chunk.

## Chunk 2: Lot B Backend Features

### Task 4: Result release notifications

**Files:**
- Modify: `backend/grading/views.py`
- Modify/Create: `backend/grading/tasks.py`
- Test: `backend/grading/tests/` new targeted test file

- [ ] Step 1: Add failing tests for queuing notifications on results release.
- [ ] Step 2: Implement the Celery task and queue it from `ExamReleaseResultsView`.
- [ ] Step 3: Audit the action and keep idempotent release behavior.
- [ ] Step 4: Run targeted grading tests.
- [ ] Step 5: Commit the chunk.

### Task 5: Admin global stats endpoint

**Files:**
- Modify: `backend/exams/views.py`
- Modify: `backend/exams/urls.py`
- Test: `backend/exams/tests/` new targeted test file

- [ ] Step 1: Add failing tests for admin-only access and response aggregates.
- [ ] Step 2: Implement `/api/exams/global-stats/` with SQL aggregations.
- [ ] Step 3: Run the targeted tests.
- [ ] Step 4: Commit the chunk.

### Task 6: Password reset JSON API

**Files:**
- Modify: `backend/core/urls.py`
- Modify/Create: `backend/core/views.py` or dedicated password reset views module
- Create: `backend/templates/email/password_reset.html`
- Test: `backend/core/tests/` new targeted test file

- [ ] Step 1: Add failing tests for request and confirm endpoints.
- [ ] Step 2: Implement public ratelimited JSON endpoints with generic responses and password validation.
- [ ] Step 3: Add audit logging for the sensitive operations.
- [ ] Step 4: Run targeted core tests.
- [ ] Step 5: Commit the chunk.

### Task 7: Annotation export endpoints

**Files:**
- Modify: `backend/grading/views.py`
- Modify: `backend/grading/urls.py`
- Test: `backend/grading/tests/` new targeted test file

- [ ] Step 1: Add failing tests for copy export and exam export permissions/shape.
- [ ] Step 2: Implement JSON exports for copy and exam.
- [ ] Step 3: Run targeted grading tests.
- [ ] Step 4: Commit the chunk.

## Chunk 3: Lot C Frontend Integration

### Task 8: Admin overview global stats

**Files:**
- Modify: `frontend/src/views/admin/AdminOverview.vue`
- Test: relevant frontend test file or add one

- [ ] Step 1: Add or update tests for parallel stats loading.
- [ ] Step 2: Fetch `/api/exams/global-stats/` alongside `/api/exams/`.
- [ ] Step 3: Use global stats for KPI cards while keeping the exams table logic.
- [ ] Step 4: Run targeted frontend tests.
- [ ] Step 5: Commit the chunk.

### Task 9: Forgot/reset password frontend

**Files:**
- Create: `frontend/src/views/ForgotPassword.vue`
- Create: `frontend/src/views/ResetPasswordConfirm.vue`
- Modify: `frontend/src/router/index.js`
- Modify: `frontend/src/views/Login.vue`
- Test: frontend tests as needed

- [ ] Step 1: Add or update tests for the public password reset flow.
- [ ] Step 2: Implement the two views and routes.
- [ ] Step 3: Add the login link.
- [ ] Step 4: Run targeted frontend tests.
- [ ] Step 5: Commit the chunk.

### Task 10: Annotation export UI and corrector progress

**Files:**
- Modify: `frontend/src/views/admin/ExamCopies.vue`
- Modify: `frontend/src/views/admin/CorrectorDesk.vue`
- Test: relevant frontend tests

- [ ] Step 1: Add or update tests for the export trigger and progress indicator.
- [ ] Step 2: Implement the export download action.
- [ ] Step 3: Implement the grading completion indicator and incomplete-finalization warning.
- [ ] Step 4: Run targeted frontend tests.
- [ ] Step 5: Commit the chunk.

## Chunk 4: Final Verification

### Task 11: Full verification

**Files:**
- No code changes unless verification reveals a defect

- [ ] Step 1: Run backend targeted tests for all modified areas.
- [ ] Step 2: Run backend full suite.
- [ ] Step 3: Run frontend lint, typecheck, unit and integration tests.
- [ ] Step 4: Review migrations and git diff for unintended changes.
- [ ] Step 5: Prepare final summary with residual risks, if any.
