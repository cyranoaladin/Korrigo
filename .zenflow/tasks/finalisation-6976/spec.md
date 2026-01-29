# Technical Specification: Finalisation Features

## Difficulty Assessment
**HARD** - This is a complex multi-feature implementation involving:
- Database schema changes (migrations)
- Authentication enhancements with security implications
- Complex business logic (fair dispatch algorithm)
- Multiple UI components across admin and corrector interfaces
- Integration across backend and frontend
- Seed data and migration scripts

## Technical Context

### Stack
- **Backend**: Django 4.2 + Django REST Framework + PostgreSQL
- **Frontend**: Vue 3 (Composition API) + Pinia + Vite + TypeScript
- **Auth**: Django's default User model + Django Groups (roles: ADMIN, TEACHER, STUDENT)
- **Session**: Session-based authentication (SessionAuthentication + BasicAuthentication)

### Repository Structure
- Backend: `/backend` (Django project root: `backend/core`)
- Frontend: `/frontend` (Vue app)
- Branch: `main` (direct push, no PR)

### Current State
1. **User Model**: Django's default `auth.User` model, roles via Groups
2. **Auth Endpoints**: `/api/login/`, `/api/logout/`, `/api/me/`, `/api/change-password/`
3. **User Management**: Admin can create/edit users via `/api/users/`
4. **Exam Model**: Has `correctors` M2M field (assigned correctors to exam)
5. **Copy Model**: Has `status`, `locked_by`, but **NO** `assigned_corrector` field
6. **Grading Structure**: JSON field on Exam (`grading_structure`) - hierarchical structure
7. **Frontend Login**: Separate routes `/admin/login`, `/teacher/login`, `/student/login`
8. **Home Page**: Already shows 3 cards (Student, Teacher, Admin)

---

## Implementation Approach

### Phase 1: Authentication & Login UI Enhancements

#### A) Admin Default Credentials + Forced Password Change
**Backend Changes:**
1. **Create management command** `backend/core/management/commands/ensure_admin.py`:
   - Creates default admin user (username: `admin`, password: `admin`) if not exists
   - Sets flag `must_change_password` on User model (extend via profile or custom field)
   - Run on startup or via migration signal

2. **Add must_change_password field**:
   - Option 1: Extend User with OneToOne UserProfile model
   - Option 2: Use JSONField in GlobalSettings or direct field extension
   - **Decision**: Create `UserProfile` model with `must_change_password` BooleanField

3. **Model**: `backend/core/models.py`
   ```python
   class UserProfile(models.Model):
       user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
       must_change_password = models.BooleanField(default=False)
   ```

4. **Middleware/View Check**: In `LoginView` after successful login:
   - Check `user.profile.must_change_password`
   - Return special response with `must_change_password: true`

5. **Update `/api/me/` endpoint**: Include `must_change_password` in response

**Frontend Changes:**
1. **Modify stores/auth.js**:
   - After login, check `must_change_password` in user data
   - Store in user object

2. **Add ChangePasswordModal.vue** component:
   - Forced modal (no dismiss) if `must_change_password`
   - Call `/api/change-password/` endpoint
   - Clear flag after successful change

3. **App.vue or router guard**: Detect `must_change_password` and show modal

#### B) Email-based Login for Teachers/Students
**Backend Changes:**
1. **Update LoginView** (`backend/core/views.py`):
   - Accept both `username` OR `email` in login payload
   - Try authenticate by username first, then by email
   - Django `authenticate()` accepts `username` only, so use:
     ```python
     user = User.objects.filter(email=username).first()
     if user:
         user = authenticate(request, username=user.username, password=password)
     ```

2. **Ensure email uniqueness**: Add validation in `UserListView.post()` to enforce unique emails

**Frontend Changes:**
- Update Login.vue placeholder text to show "Identifiant / Email" (already done!)
- No major changes needed

#### C) Password Show/Hide Toggle in Login Form
**Frontend Changes:**
1. **Login.vue**:
   - Add `passwordVisible` ref (boolean)
   - Change input `type` from `"password"` to `passwordVisible ? "text" : "password"`
   - Add eye icon button next to password field
   - Toggle `passwordVisible` on click
   - Add ARIA label for accessibility

#### D) Admin Reset Password for Users
**Backend Changes:**
1. **New endpoint**: `POST /api/users/<id>/reset-password/`
   - Admin only
   - Generates temporary password (12-char random string)
   - Sets `user.profile.must_change_password = True`
   - Returns temporary password in response (one-time display)

2. **View**: `UserResetPasswordView` in `backend/core/views.py`

**Frontend Changes:**
1. **UserManagement.vue**:
   - Add "Reset Password" button per user
   - Show modal with generated temporary password
   - Display warning "Show this to user once, it won't be shown again"

---

### Phase 2: Copy Dispatch (Fair & Random Assignment)

#### A) Database Changes
**Backend Migration:**
1. **Add field to Copy model** (`backend/exams/models.py`):
   ```python
   assigned_corrector = models.ForeignKey(
       settings.AUTH_USER_MODEL,
       on_delete=models.SET_NULL,
       null=True,
       blank=True,
       related_name='assigned_copies',
       verbose_name="Correcteur assigné"
   )
   dispatch_run_id = models.UUIDField(null=True, blank=True, verbose_name="ID du dispatch")
   assigned_at = models.DateTimeField(null=True, blank=True, verbose_name="Date d'assignation")
   ```

2. **Migration**: `python manage.py makemigrations && python manage.py migrate`

#### B) Dispatch Algorithm
**Backend Endpoint:**
1. **New endpoint**: `POST /api/exams/<exam_id>/dispatch/`
   - Admin only (IsAdmin permission)
   - Transaction-wrapped logic:
     ```python
     from django.db import transaction
     from random import shuffle
     from uuid import uuid4
     
     @transaction.atomic()
     def dispatch_copies(exam_id):
         exam = Exam.objects.get(id=exam_id)
         correctors = list(exam.correctors.all())
         
         if not correctors:
             raise ValidationError("No correctors assigned to exam")
         
         # Get unassigned copies (assigned_corrector is NULL)
         copies = list(Copy.objects.filter(
             exam=exam,
             assigned_corrector__isnull=True,
             status__in=['READY', 'STAGING']
         ))
         
         if not copies:
             raise ValidationError("No copies to assign")
         
         # Shuffle for randomness
         shuffle(copies)
         
         # Round-robin assignment
         dispatch_id = uuid4()
         for idx, copy in enumerate(copies):
             corrector = correctors[idx % len(correctors)]
             copy.assigned_corrector = corrector
             copy.dispatch_run_id = dispatch_id
             copy.assigned_at = timezone.now()
         
         Copy.objects.bulk_update(copies, ['assigned_corrector', 'dispatch_run_id', 'assigned_at'])
         
         # Return distribution stats
         distribution = {}
         for copy in copies:
             distribution[copy.assigned_corrector.username] = distribution.get(copy.assigned_corrector.username, 0) + 1
         
         return {
             'dispatch_id': str(dispatch_id),
             'total_copies': len(copies),
             'correctors_count': len(correctors),
             'distribution': distribution
         }
     ```

2. **View**: `ExamDispatchView` in `backend/exams/views.py`
3. **URL**: Add to `backend/exams/urls.py`

#### C) Frontend UI
**AdminDashboard.vue or Exam Detail Page:**
1. Add "Dispatch Copies" button for each exam
2. Show modal confirming action with stats preview
3. After dispatch, show distribution results:
   - Total copies assigned
   - Distribution per corrector (min/max)
   - Dispatch ID for traceability

---

### Phase 3: Grading Remarks & Global Appreciation

#### A) Database Models
**Backend Models:**
1. **QuestionRemark model** (`backend/grading/models.py`):
   ```python
   class QuestionRemark(models.Model):
       id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
       copy = models.ForeignKey(Copy, on_delete=models.CASCADE, related_name='question_remarks')
       question_id = models.CharField(max_length=100, verbose_name="Question/Item ID")
       remark = models.TextField(blank=True, verbose_name="Remarque")
       created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
       created_at = models.DateTimeField(auto_now_add=True)
       updated_at = models.DateTimeField(auto_now=True)
   ```

2. **Global Appreciation**: Add field to Copy model:
   ```python
   global_appreciation = models.TextField(blank=True, null=True, verbose_name="Appréciation globale")
   ```

3. **Migration**: Create and run migration

#### B) API Endpoints
**Backend:**
1. **Question Remarks**:
   - `GET /api/grading/copies/<copy_id>/remarks/` - List all remarks for a copy
   - `POST /api/grading/copies/<copy_id>/remarks/` - Create/update remark
     - Payload: `{ question_id, remark }`
     - Use get_or_create pattern
   - `PUT /api/grading/copies/<copy_id>/remarks/<question_id>/` - Update specific remark
   - `DELETE /api/grading/copies/<copy_id>/remarks/<question_id>/` - Delete remark

2. **Global Appreciation**:
   - Include in existing Copy serializer/detail endpoint
   - Update via PATCH on copy endpoint or dedicated endpoint

#### C) Frontend UI - CorrectorDesk.vue
**Changes to Correction Interface:**
1. **Sidebar - Grading Section**:
   - Under each question/item in barème:
     - Add textarea "Remarque (facultatif)"
     - Auto-save on blur/debounce
     - Store in local state + persist to backend

2. **Bottom of Sidebar**:
   - Add "Appréciation Globale" textarea
   - Large text area (4-6 rows)
   - Auto-save on blur

3. **State Management**:
   - Add `questionRemarks` ref: `Map<question_id, remark_text>`
   - Add `globalAppreciation` ref
   - Fetch on load, save on change

4. **API Integration**:
   - Load remarks with copy data
   - Save individual remarks via debounced API calls
   - Save global appreciation via debounced PATCH to copy

---

## Source Code Structure

### Files to Create
**Backend:**
1. `backend/core/models.py` - Add `UserProfile` model
2. `backend/core/migrations/000X_add_user_profile.py` - Migration
3. `backend/core/management/commands/ensure_admin.py` - Admin seed command
4. `backend/core/views.py` - Add `UserResetPasswordView`
5. `backend/exams/models.py` - Modify `Copy` model (add fields)
6. `backend/exams/migrations/000X_add_dispatch_fields.py` - Migration
7. `backend/exams/views.py` - Add `ExamDispatchView`
8. `backend/exams/urls.py` - Add dispatch endpoint
9. `backend/grading/models.py` - Add `QuestionRemark` model, modify `Copy`
10. `backend/grading/migrations/000X_add_remarks.py` - Migration
11. `backend/grading/views.py` - Add remarks endpoints
12. `backend/grading/serializers.py` - Add `QuestionRemarkSerializer`
13. `backend/grading/urls.py` - Add remarks routes

**Frontend:**
1. `frontend/src/views/Login.vue` - Add password toggle
2. `frontend/src/components/ChangePasswordModal.vue` - New component
3. `frontend/src/stores/auth.js` - Handle `must_change_password`
4. `frontend/src/views/admin/UserManagement.vue` - Add reset password UI
5. `frontend/src/views/AdminDashboard.vue` - Add dispatch button
6. `frontend/src/views/admin/CorrectorDesk.vue` - Add remarks & appreciation UI
7. `frontend/src/services/api.js` - Add dispatch & remarks API calls

### Files to Modify
**Backend:**
1. `backend/core/views.py` - Update `LoginView` for email login
2. `backend/core/settings.py` - Ensure admin command runs on startup (optional)
3. `backend/exams/models.py` - Add Copy fields
4. `backend/grading/models.py` - Add QuestionRemark, modify Copy

**Frontend:**
1. `frontend/src/views/Login.vue` - Password toggle
2. `frontend/src/views/admin/CorrectorDesk.vue` - Remarks UI
3. `frontend/src/stores/auth.js` - Must change password handling

---

## Data Model Changes

### UserProfile (new)
```python
user: OneToOneField -> User
must_change_password: BooleanField (default=False)
```

### Copy (modifications)
```python
# New fields:
assigned_corrector: ForeignKey -> User (nullable)
dispatch_run_id: UUIDField (nullable)
assigned_at: DateTimeField (nullable)
global_appreciation: TextField (blank=True, null=True)
```

### QuestionRemark (new)
```python
id: UUIDField (PK)
copy: ForeignKey -> Copy
question_id: CharField (max_length=100)
remark: TextField (blank=True)
created_by: ForeignKey -> User
created_at: DateTimeField (auto)
updated_at: DateTimeField (auto)

# Unique constraint: (copy, question_id)
```

---

## API Contracts

### Authentication
```
POST /api/login/
Request: { username: string (or email), password: string }
Response: { message: string, must_change_password?: boolean }

POST /api/change-password/
Request: { password: string }
Response: { message: string }

GET /api/me/
Response: { id, username, email, role, must_change_password: boolean }
```

### User Management (Admin)
```
POST /api/users/<id>/reset-password/
Request: {}
Response: { temporary_password: string, message: string }
```

### Copy Dispatch
```
POST /api/exams/<exam_id>/dispatch/
Request: {}
Response: {
  dispatch_id: string,
  total_copies: number,
  correctors_count: number,
  distribution: { [username]: count }
}
```

### Question Remarks
```
GET /api/grading/copies/<copy_id>/remarks/
Response: [{ question_id, remark, created_at, updated_at }]

POST /api/grading/copies/<copy_id>/remarks/
Request: { question_id: string, remark: string }
Response: { id, question_id, remark, ... }

PUT /api/grading/remarks/<id>/
Request: { remark: string }
Response: { id, question_id, remark, ... }

DELETE /api/grading/remarks/<id>/
Response: 204
```

---

## Verification Approach

### Unit Tests
1. **Backend Tests** (`backend/core/tests/`, `backend/exams/tests/`, `backend/grading/tests/`):
   - Test admin seed command creates default user
   - Test email-based login
   - Test dispatch algorithm (0 correctors, 10 copies/3 correctors, already assigned)
   - Test dispatch transaction atomicity
   - Test remarks CRUD
   - Test global appreciation save/load

2. **Frontend Tests** (optional, time permitting):
   - E2E test login flow with password toggle
   - E2E test forced password change

### Manual Testing Checklist
1. **Auth**:
   - [ ] Login as admin/admin succeeds
   - [ ] Forced password change modal appears
   - [ ] After change, modal doesn't reappear
   - [ ] Login with email (teacher/student)
   - [ ] Password toggle works (eye icon)
   - [ ] Admin can reset user password

2. **Dispatch**:
   - [ ] Dispatch button visible for exam with correctors
   - [ ] Dispatch assigns all unassigned copies
   - [ ] Distribution is fair (max diff ≤ 1)
   - [ ] Re-dispatch doesn't reassign existing copies
   - [ ] Distribution stats displayed correctly

3. **Remarks & Appreciation**:
   - [ ] Remark field appears under each barème question
   - [ ] Remarks are saved and reloaded
   - [ ] Global appreciation field at bottom
   - [ ] Global appreciation saves and reloads
   - [ ] Read-only mode preserves remarks

### Integration Tests
- Run full backend test suite: `cd backend && pytest`
- Run linting: `cd backend && ruff check .` (if configured)
- Run frontend build: `cd frontend && npm run build`
- Run frontend lint: `cd frontend && npm run lint`
- Run frontend typecheck: `cd frontend && npm run typecheck`

### CI/CD
- Push to `origin/main`
- Verify GitHub Actions CI passes (all tests, linting, build)
- Capture CI run URL and status

---

## Security Considerations

1. **Admin Default Password**: 
   - Only created if admin doesn't exist
   - Force password change on first login
   - Warning logged if password not changed

2. **Email Login**:
   - Case-insensitive email lookup
   - Rate limiting already in place (5/15min)

3. **Password Reset**:
   - Admin-only action
   - Temporary password displayed once
   - Force change on next login

4. **Dispatch**:
   - Admin-only action
   - Transaction-wrapped (atomicity)
   - No PII in logs

5. **Remarks**:
   - Teacher/corrector only
   - Tied to authenticated user
   - No XSS (Django escapes by default)

---

## Traceability

1. **Admin Creation**: Logged via Django logging
2. **Password Changes**: Audit via existing audit trail
3. **Password Resets**: Audit log entry (admin action)
4. **Dispatch**: `dispatch_run_id` + `assigned_at` timestamp
5. **Remarks**: `created_by`, `created_at`, `updated_at` fields

---

## Migration Strategy

1. **Order of migrations**:
   - UserProfile model
   - Copy dispatch fields
   - QuestionRemark model + Copy.global_appreciation
   
2. **Data migration**: None needed (all new fields are nullable/default)

3. **Seed admin**: Run `python manage.py ensure_admin` after deployment

4. **Backwards compatibility**: All new fields are optional, existing functionality unaffected

---

## Rollback Plan

1. If dispatch fails: Copies remain unassigned, no data loss
2. If migration fails: Revert migration, no schema change persisted
3. If frontend breaks: Revert frontend commit, backend changes are backwards compatible
4. If admin seed fails: Manually create admin via Django admin or `createsuperuser`

---

## Performance Considerations

1. **Dispatch algorithm**: O(n) where n = number of copies, uses bulk_update
2. **Remarks**: Indexed by (copy, question_id), fast lookups
3. **Auto-save**: Debounced (500ms-1s) to avoid excessive API calls
4. **Transaction isolation**: Uses Django default (READ COMMITTED), lock_timeout configured

---

## Acceptance Criteria

All criteria from task description must be met:
- [x] Home page shows 3 connection types (already exists)
- [ ] Login form has password show/hide toggle
- [ ] Admin login: admin/admin works
- [ ] Admin forced to change password on first login
- [ ] Admin can change password from profile
- [ ] Teachers/Students login with email
- [ ] Teachers/Students can change password
- [ ] Admin can reset user passwords
- [ ] Dispatch button assigns copies fairly & randomly
- [ ] Dispatch is atomic & doesn't reassign existing
- [ ] Dispatch shows distribution stats
- [ ] Correction UI has remark field per question
- [ ] Correction UI has global appreciation field
- [ ] Remarks & appreciation are saved & reloaded
- [ ] All tests pass locally
- [ ] CI GitHub Actions is green
- [ ] Code pushed to origin/main

---

## Estimated Effort

- **Phase 1 (Auth)**: 4-6 hours (backend + frontend + testing)
- **Phase 2 (Dispatch)**: 3-4 hours (algorithm + UI + testing)
- **Phase 3 (Remarks)**: 3-4 hours (models + UI + testing)
- **Integration & Testing**: 2-3 hours
- **CI/CD & Documentation**: 1-2 hours

**Total**: 13-19 hours of focused development

---

## Next Steps

1. Create detailed implementation plan with substeps
2. Implement Phase 1 (Auth enhancements)
3. Implement Phase 2 (Dispatch)
4. Implement Phase 3 (Remarks & Appreciation)
5. Run full test suite
6. Commit & push to origin/main
7. Verify CI passes
8. Generate final report with proofs
