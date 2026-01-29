# Spec and build

## Configuration
- **Artifacts Path**: {@artifacts_path} → `.zenflow/tasks/{task_id}`

---

## Agent Instructions

Ask the user questions when anything is unclear or needs their input. This includes:
- Ambiguous or incomplete requirements
- Technical decisions that affect architecture or user experience
- Trade-offs that require business context

Do not make assumptions on important decisions — get clarification first.

---

## Workflow Steps

### [x] Step: Technical Specification
<!-- chat-id: 79b3070e-e748-4982-a8e0-851fe0a32793 -->

Assess the task's difficulty, as underestimating it leads to poor outcomes.
- easy: Straightforward implementation, trivial bug fix or feature
- medium: Moderate complexity, some edge cases or caveats to consider
- hard: Complex logic, many caveats, architectural considerations, or high-risk changes

Create a technical specification for the task that is appropriate for the complexity level:
- Review the existing codebase architecture and identify reusable components.
- Define the implementation approach based on established patterns in the project.
- Identify all source code files that will be created or modified.
- Define any necessary data model, API, or interface changes.
- Describe verification steps using the project's test and lint commands.

Save the output to `{@artifacts_path}/spec.md` with:
- Technical context (language, dependencies)
- Implementation approach
- Source code structure changes
- Data model / API / interface changes
- Verification approach

If the task is complex enough, create a detailed implementation plan based on `{@artifacts_path}/spec.md`:
- Break down the work into concrete tasks (incrementable, testable milestones)
- Each task should reference relevant contracts and include verification steps
- Replace the Implementation step below with the planned tasks

Rule of thumb for step size: each step should represent a coherent unit of work (e.g., implement a component, add an API endpoint, write tests for a module). Avoid steps that are too granular (single function).

Save to `{@artifacts_path}/plan.md`. If the feature is trivial and doesn't warrant this breakdown, keep the Implementation step below as is.

---

### [x] Step: Backend - UserProfile Model & Admin Seed
<!-- chat-id: 026e222f-7def-4ee7-b059-1b8aee62328e -->

Create UserProfile model for tracking must_change_password flag and admin seed command.

**Backend Tasks:**
1. Create `UserProfile` model in `backend/core/models.py`
   - OneToOne relationship with User
   - `must_change_password` BooleanField (default=False)
2. Create migration: `python manage.py makemigrations core`
3. Create management command `backend/core/management/commands/ensure_admin.py`
   - Create admin user (username: admin, password: admin) if doesn't exist
   - Set `must_change_password=True` on created admin
4. Update `LoginView` in `backend/core/views.py`
   - After successful login, check `user.profile.must_change_password`
   - Include flag in response
5. Update `/api/me/` endpoint to include `must_change_password` in response

**Verification:**
- Run migration: `python manage.py migrate`
- Run command: `python manage.py ensure_admin`
- Test login returns `must_change_password` field
- Run backend tests: `cd backend && pytest`

---

### [x] Step: Backend - Email Login & Password Reset
<!-- chat-id: d9ba556d-1041-4ddc-9874-254a40e4fda9 -->

Enable email-based login and admin password reset functionality.

**Backend Tasks:**
1. Update `LoginView` in `backend/core/views.py`
   - Accept email as username alternative
   - Try User.objects.filter(email=username) if username auth fails
2. Add email uniqueness validation in `UserListView.post()`
3. Create `UserResetPasswordView` in `backend/core/views.py`
   - POST `/api/users/<id>/reset-password/`
   - Generate 12-char random password
   - Set `must_change_password=True`
   - Return temporary password (one-time display)
4. Add route in `backend/core/urls.py`
5. Add audit logging for password reset action

**Verification:**
- Test login with email address
- Test admin can reset user password
- Verify temporary password works
- Verify must_change_password flag set
- Run backend tests

---

### [x] Step: Frontend - Password Toggle & Forced Password Change
<!-- chat-id: 993c8faa-1d11-41ce-ad07-c44b6499344d -->

Add password visibility toggle and handle forced password changes.

**Frontend Tasks:**
1. Update `Login.vue`:
   - Add `passwordVisible` ref
   - Add eye icon button
   - Toggle input type between "password" and "text"
   - Add ARIA labels for accessibility
2. Create `ChangePasswordModal.vue` component:
   - Modal with password input fields (new password, confirm)
   - Call `/api/change-password/` endpoint
   - Cannot be dismissed if forced
   - Show success/error messages
3. Update `stores/auth.js`:
   - Store `must_change_password` flag in user object
   - Add method to clear flag after password change
4. Add router guard or App.vue logic to show modal when `must_change_password=true`

**Verification:**
- Test password toggle works
- Test forced password change modal appears for admin/admin
- Test modal cannot be dismissed
- Test successful password change clears flag
- Run: `npm run lint && npm run typecheck`

---

### [x] Step: Frontend - Admin User Management UI
<!-- chat-id: aade4ca9-2c77-4e78-8f8c-47afc350defa -->

Add password reset UI in admin user management.

**Frontend Tasks:**
1. Update `UserManagement.vue`:
   - Add "Reset Password" button for each user
   - Create modal to display temporary password
   - Add warning "Show this to user once"
   - Call `/api/users/<id>/reset-password/` endpoint
2. Add API method in `services/api.js` for password reset

**Verification:**
- Test admin can click "Reset Password"
- Test temporary password is displayed
- Test user can login with temporary password
- Test forced password change after reset

---

### [x] Step: Backend - Copy Dispatch Model & Algorithm
<!-- chat-id: 9574b400-4786-435b-a332-285b5e31aed3 -->

Add dispatch fields to Copy model and implement fair distribution algorithm.

**Backend Tasks:**
1. Update `Copy` model in `backend/exams/models.py`:
   - Add `assigned_corrector` ForeignKey to User (nullable)
   - Add `dispatch_run_id` UUIDField (nullable)
   - Add `assigned_at` DateTimeField (nullable)
2. Create migration: `python manage.py makemigrations exams`
3. Run migration: `python manage.py migrate`
4. Create `ExamDispatchView` in `backend/exams/views.py`:
   - POST `/api/exams/<exam_id>/dispatch/`
   - Admin-only permission
   - Transaction-wrapped logic:
     - Get exam correctors
     - Get unassigned copies (assigned_corrector is NULL)
     - Shuffle copies for randomness
     - Round-robin assignment
     - Bulk update with dispatch_run_id
   - Return distribution stats
5. Add route in `backend/exams/urls.py`
6. Create serializer if needed

**Verification:**
- Test dispatch with 0 correctors (error)
- Test dispatch with 10 copies, 3 correctors (distribution: 4/3/3)
- Test dispatch doesn't reassign existing copies
- Test transaction atomicity
- Run backend tests: `cd backend && pytest`

---

### [x] Step: Frontend - Dispatch UI in Admin Dashboard
<!-- chat-id: 97673899-c5c2-48fe-86f7-0443c125b2fc -->

Add dispatch button and results display in admin interface.

**Frontend Tasks:**
1. Update `AdminDashboard.vue`:
   - Add "Dispatch Copies" button for each exam
   - Disable if exam has no correctors
   - Show confirmation modal before dispatch
2. Create dispatch modal component or inline:
   - Show exam details
   - Confirm action
   - Display results after dispatch:
     - Total copies assigned
     - Number of correctors
     - Distribution (username: count)
     - Dispatch ID for traceability
3. Add API method in `services/api.js` for dispatch

**Verification:**
- Test dispatch button appears for exam with correctors
- Test dispatch button disabled if no correctors
- Test distribution stats displayed correctly
- Test re-dispatch doesn't affect already assigned copies

---

### [x] Step: Backend - Question Remarks & Global Appreciation
<!-- chat-id: c1d4a659-6172-49d9-96ff-447955ad9a72 -->

Add models and endpoints for per-question remarks and global appreciation.

**Backend Tasks:**
1. Create `QuestionRemark` model in `backend/grading/models.py`:
   - UUIDField primary key
   - ForeignKey to Copy
   - `question_id` CharField
   - `remark` TextField
   - `created_by` ForeignKey to User
   - Timestamps
   - Unique constraint on (copy, question_id)
2. Update `Copy` model in `backend/exams/models.py`:
   - Add `global_appreciation` TextField (blank=True, null=True)
3. Create migrations: `python manage.py makemigrations grading exams`
4. Run migrations: `python manage.py migrate`
5. Create `QuestionRemarkSerializer` in `backend/grading/serializers.py`
6. Create views in `backend/grading/views.py`:
   - GET `/api/grading/copies/<copy_id>/remarks/` - List remarks
   - POST `/api/grading/copies/<copy_id>/remarks/` - Create/update remark
   - PUT `/api/grading/remarks/<id>/` - Update remark
   - DELETE `/api/grading/remarks/<id>/` - Delete remark
7. Update Copy serializer to include `global_appreciation`
8. Add routes in `backend/grading/urls.py`

**Verification:**
- Test create remark
- Test update remark
- Test delete remark
- Test list remarks for copy
- Test global appreciation save/load
- Run backend tests

---

### [x] Step: Frontend - Correction UI Remarks & Appreciation
<!-- chat-id: d996727f-2ba0-462e-8ff2-2982d61e72a2 -->

Add remarks and global appreciation fields to correction interface.

**Frontend Tasks:**
1. Update `CorrectorDesk.vue`:
   - Add `questionRemarks` ref (Map of question_id -> remark)
   - Add `globalAppreciation` ref
   - Fetch remarks on copy load
   - In sidebar grading section:
     - Add textarea under each barème question
     - Label: "Remarque (facultatif)"
     - Bind to questionRemarks map
     - Debounced auto-save (500ms-1s)
   - At bottom of sidebar:
     - Add "Appréciation Globale" textarea (4-6 rows)
     - Bind to globalAppreciation
     - Debounced auto-save
2. Add API methods in `services/gradingApi.js`:
   - fetchRemarks(copyId)
   - saveRemark(copyId, questionId, remark)
   - saveGlobalAppreciation(copyId, appreciation)
3. Handle loading/saving states
4. Show save indicators (e.g., "Saving...", "Saved")

**Verification:**
- Test remark field appears under each question
- Test remarks are saved on blur/debounce
- Test remarks are loaded on page reload
- Test global appreciation field at bottom
- Test global appreciation saves and reloads
- Test read-only mode preserves remarks
- Run: `npm run lint && npm run typecheck`

---

### [x] Step: Testing & Quality Assurance
<!-- chat-id: ed4e2784-c5eb-4f36-92b0-cd4da8c75370 -->

Run comprehensive tests and verify all functionality.

**Backend Testing:**
1. Run full test suite: `cd backend && pytest -v`
2. Check code coverage if configured
3. Run linting (if configured): `ruff check .` or `flake8`
4. Verify no warnings in test output

**Frontend Testing:**
1. Run lint: `cd frontend && npm run lint`
2. Run typecheck: `cd frontend && npm run typecheck`
3. Run build: `npm run build`
4. Verify no errors or warnings

**Manual Testing Checklist:**
- [ ] Login as admin/admin → forced password change
- [ ] After password change, can access admin dashboard
- [ ] Login with teacher email works
- [ ] Password toggle works (eye icon)
- [ ] Admin can reset teacher password
- [ ] Teacher forced to change password after reset
- [ ] Dispatch button assigns copies fairly
- [ ] Dispatch shows distribution stats
- [ ] Re-dispatch doesn't affect existing assignments
- [ ] Remark field appears under each barème question
- [ ] Remarks save and reload correctly
- [ ] Global appreciation saves and reloads
- [ ] All UI elements responsive and accessible

---

### [ ] Step: Commit, Push & CI Verification
<!-- chat-id: 6f09f577-decc-4229-bebb-623917406eb9 -->

Create clean commits and verify CI passes.

**Git Operations:**
1. Review all changes: `git status` and `git diff`
2. Create logical commits (2-5 commits max):
   - Commit 1: "feat: add UserProfile model and admin seed command"
   - Commit 2: "feat: add email login and admin password reset"
   - Commit 3: "feat: implement copy dispatch algorithm and UI"
   - Commit 4: "feat: add question remarks and global appreciation"
   - Commit 5: "test: add tests and fix linting issues" (if needed)
3. Write clear commit messages (conventional commits format)
4. Push to origin/main: `git push origin main`
5. Monitor GitHub Actions CI run
6. Capture CI run URL and status

**CI Verification:**
- Wait for all jobs to complete
- Verify all tests pass
- Verify build succeeds
- Verify no linting errors
- If CI fails, fix issues and push again

**Deliverables:**
- List of commit SHAs and messages
- GitHub Actions run URL
- CI status: GREEN ✓

---

### [ ] Step: Final Report & Proofs

Document implementation and gather proofs of completion.

**Report Creation:**
Write to `.zenflow/tasks/finalisation-6976/report.md`:

1. **Summary of Implementation**:
   - List all features implemented
   - Key technical decisions made
   - Files created/modified

2. **Testing Results**:
   - Backend test results (pytest output)
   - Frontend lint/typecheck results
   - Manual testing checklist results

3. **Functional Proofs**:
   - Screenshots or logs of:
     - Admin login with forced password change
     - Email-based login
     - Password toggle in action
     - Dispatch operation with distribution stats
     - Remarks and appreciation UI
   - Commands executed and outputs

4. **CI/CD Proofs**:
   - GitHub Actions run URL
   - CI status (green)
   - Commit SHAs

5. **Known Issues & Future Work** (if any):
   - Any edge cases not covered
   - Potential improvements

**Verification:**
- All acceptance criteria met
- All manual tests passed
- CI is green
- Documentation complete
