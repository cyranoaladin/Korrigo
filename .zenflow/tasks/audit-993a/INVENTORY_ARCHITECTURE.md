# Architecture & Components Inventory - Korrigo PMF

**Date**: 2026-01-27  
**Audit Phase**: PHASE 1 - INVENTAIRE  
**Criticality**: Production-Ready Application (NOT MVP)

---

## Executive Summary

Korrigo PMF is a production-grade exam grading platform for educational institutions. This inventory catalogs all system components, their interactions, dependencies, and critical paths for the production readiness audit.

**Key Stats**:
- **Backend Apps**: 6 Django apps (core, exams, grading, processing, students, identification)
- **Database Models**: 8 business models + Django auth
- **API Endpoints**: ~30+ REST endpoints
- **Frontend Routes**: 12 routes with role-based guards
- **Docker Services**: 5+ services (db, redis, backend, celery, nginx/frontend)
- **Critical Workflows**: 4 main workflows (Import, Identification, Correction, Student Portal)

---

## 1. Technology Stack

### Backend Stack
| Component | Version | Role | Criticality |
|-----------|---------|------|-------------|
| Python | 3.9 | Language | HIGH |
| Django | 4.2 LTS | Framework, ORM, Admin | HIGH |
| Django REST Framework | 3.16+ | REST API | HIGH |
| PostgreSQL | 15+ | Database (ACID) | CRITICAL |
| Redis | 7+ | Cache, Celery broker | HIGH |
| Celery | 5+ | Async tasks (configured but minimal use) | MEDIUM |
| PyMuPDF (fitz) | 1.23.26 | PDF manipulation | HIGH |
| OpenCV | 4.8.0 | Image processing | MEDIUM |
| Pytesseract | - | OCR (optional) | LOW |
| Gunicorn | - | WSGI server (prod) | HIGH |

### Frontend Stack
| Component | Version | Role | Criticality |
|-----------|---------|------|-------------|
| Vue.js | 3.4+ | UI Framework (Composition API) | HIGH |
| Pinia | 2.1+ | State management | HIGH |
| Vue Router | 4.2+ | SPA routing | HIGH |
| Axios | 1.13+ | HTTP client | HIGH |
| PDF.js | 4.0+ | PDF rendering | HIGH |
| Vite | 5.1+ | Build tool, dev server | MEDIUM |
| TypeScript | 5.9+ | Type safety | MEDIUM |

### Infrastructure
| Component | Version | Role | Criticality |
|-----------|---------|------|-------------|
| Docker | 20+ | Containerization | HIGH |
| Docker Compose | 2+ | Orchestration | HIGH |
| Nginx | 1.25+ | Reverse proxy, static serving | HIGH |

---

## 2. System Architecture

### 2.1 High-Level Architecture

```
┌─────────────────┐
│  Browser Client │
└────────┬────────┘
         │ HTTP(S)
         ▼
┌─────────────────────────────────────────────────────────┐
│                    Docker Host                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │   Nginx      │  │   Frontend   │  │   Backend    │ │
│  │ (prod only)  │  │  Vue.js SPA  │  │ Django + DRF │ │
│  │  Port 80/443 │  │  Port 5173   │  │  Port 8000   │ │
│  └──────────────┘  └──────────────┘  └──────┬───────┘ │
│                                              │         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────▼───────┐ │
│  │  PostgreSQL  │  │    Redis     │  │    Celery    │ │
│  │  Port 5432   │  │  Port 6379   │  │   Worker     │ │
│  └──────────────┘  └──────────────┘  └──────────────┘ │
│                                                         │
│  Volumes: postgres_data, media_volume, static_volume   │
└─────────────────────────────────────────────────────────┘
```

### 2.2 Backend Architecture (Layered)

```
┌─────────────────────────────────────────────────────────┐
│                   API Layer (DRF)                       │
│  - Authentication (Session-based)                       │
│  - Permissions (RBAC: Admin/Teacher/Student)            │
│  - ViewSets (Exams, Copies, Grading, Students)          │
│  - Serializers (Data validation)                        │
└────────────────────────┬────────────────────────────────┘
                         ▼
┌─────────────────────────────────────────────────────────┐
│                 Service Layer (Business Logic)          │
│  - GradingService (workflow, state machine)             │
│  - AnnotationService (validation, audit)                │
│  - OCRService (identification)                          │
│  - PDF Processing (split, flatten, rasterize)           │
└────────────────────────┬────────────────────────────────┘
                         ▼
┌─────────────────────────────────────────────────────────┐
│                 Data Layer (ORM + DB)                   │
│  - Django ORM (Models: Exam, Copy, Annotation, etc.)    │
│  - PostgreSQL (ACID transactions)                       │
│  - File Storage (Media: PDF, images)                    │
└─────────────────────────────────────────────────────────┘
```

---

## 3. Database Schema

### 3.1 Core Models

#### exams.Exam
- **Purpose**: Represents an exam (e.g., "Bac Blanc Maths TG - Jan 2026")
- **Key Fields**:
  - `id` (UUID PK)
  - `name` (VARCHAR 255)
  - `date` (DATE)
  - `pdf_source` (FILE) - validated (PDF only, 50MB max)
  - `grading_structure` (JSON) - hierarchical grading scale
  - `is_processed` (BOOLEAN)
  - `correctors` (M2M → User) - assigned teachers
- **Validation**: PDF validators (extension, size, MIME, integrity)

#### exams.Booklet
- **Purpose**: Staging entity for split PDF chunks (before merge into Copy)
- **Key Fields**:
  - `id` (UUID PK)
  - `exam` (FK → Exam)
  - `start_page`, `end_page` (INT)
  - `header_image` (IMAGE) - OCR crop
  - `student_name_guess` (VARCHAR 255) - OCR result
  - `pages_images` (JSON) - list of page image paths
- **Workflow**: Upload PDF → Auto-split → Create Booklets → Admin validates/merges → Create Copy

#### exams.Copy
- **Purpose**: Final validated copy (core grading entity)
- **Key Fields**:
  - `id` (UUID PK)
  - `exam` (FK → Exam)
  - `student` (FK → Student, nullable)
  - `anonymous_id` (VARCHAR 50, unique)
  - `pdf_source` (FILE)
  - `final_pdf` (FILE) - with annotations
  - `status` (VARCHAR 20): STAGING, READY, LOCKED, GRADED
  - `booklets` (M2M → Booklet) - traceability
  - `locked_by` (FK → User, nullable)
  - `validated_at`, `locked_at`, `graded_at` (DATETIME)
- **State Machine**: STAGING → READY → LOCKED → GRADED
- **Critical**: All state transitions are audited via GradingEvent

#### students.Student
- **Purpose**: Student profile
- **Key Fields**:
  - `id` (INT PK)
  - `ine` (VARCHAR 50, unique) - National ID
  - `first_name`, `last_name` (VARCHAR 100)
  - `class_name` (VARCHAR 50)
  - `email` (EMAIL, nullable)
  - `user` (1-to-1 → User, nullable) - for auth

#### grading.Annotation
- **Purpose**: Vector annotation on copy (comment, score)
- **Key Fields**:
  - `id` (UUID PK)
  - `copy` (FK → Copy)
  - `page_index` (INT, 0-based)
  - `x`, `y`, `w`, `h` (FLOAT) - **normalized [0,1]**
  - `content` (TEXT)
  - `type` (VARCHAR 20): COMMENT, HIGHLIGHT, ERROR, BONUS
  - `score_delta` (INT, nullable)
  - `created_by` (FK → User, PROTECT)
  - `created_at`, `updated_at` (DATETIME)
- **Index**: (copy, page_index) for fast page queries

#### grading.GradingEvent
- **Purpose**: Audit trail for all grading actions (full traceability)
- **Key Fields**:
  - `id` (UUID PK)
  - `copy` (FK → Copy)
  - `action` (VARCHAR 20): IMPORT, VALIDATE, LOCK, UNLOCK, CREATE_ANN, UPDATE_ANN, DELETE_ANN, FINALIZE, EXPORT
  - `actor` (FK → User, PROTECT)
  - `timestamp` (DATETIME, auto)
  - `metadata` (JSON) - contextual data
- **Index**: (copy, timestamp) for chronological history
- **Critical**: Never deleted (audit compliance)

#### grading.CopyLock
- **Purpose**: Soft lock for concurrent editing (optimistic locking)
- **Key Fields**:
  - `id` (INT PK)
  - `copy` (1-to-1 → Copy)
  - `owner` (FK → User)
  - `token` (UUID) - session token
  - `locked_at` (DATETIME)
  - `expires_at` (DATETIME, indexed) - auto-expire after 30min
- **Logic**: One lock per copy, token required for all write ops
- **Cleanup**: Periodic task to remove expired locks (not yet implemented)

#### grading.DraftState
- **Purpose**: Autosave state (crash recovery)
- **Key Fields**:
  - `id` (UUID PK)
  - `copy` (FK → Copy)
  - `owner` (FK → User)
  - `payload` (JSON) - full editor state
  - `lock_token` (UUID, nullable)
  - `client_id` (UUID, nullable) - anti-overwrite
  - `version` (INT)
  - `updated_at` (DATETIME)
- **Constraint**: Unique (copy, owner) - one draft per user/copy

### 3.2 Relationships

```
User (Django Auth)
  ├─→ Copy.locked_by (1:N)
  ├─→ Annotation.created_by (1:N, PROTECT)
  ├─→ GradingEvent.actor (1:N, PROTECT)
  ├─→ CopyLock.owner (1:N)
  ├─→ DraftState.owner (1:N)
  └─→ Exam.correctors (M2M)

Exam
  ├─→ Booklet (1:N, CASCADE)
  └─→ Copy (1:N, CASCADE)

Copy
  ├─→ Booklet (M2M) - traceability
  ├─→ Annotation (1:N, CASCADE)
  ├─→ GradingEvent (1:N, CASCADE)
  ├─→ CopyLock (1:1)
  └─→ DraftState (1:N)

Student
  ├─→ Copy (1:N, SET_NULL)
  └─→ User (1:1, SET_NULL)
```

### 3.3 State Machine (Copy.status)

```
[*] → STAGING: Create copy from booklets
STAGING → READY: Admin validates (validated_at timestamp)
READY → LOCKED: Teacher acquires lock (locked_at, locked_by)
LOCKED → READY: Teacher releases lock (unlock)
LOCKED → GRADED: Teacher finalizes (graded_at, final_pdf generated)
GRADED → [*]: Terminal state
```

**Invariants**:
- LOCKED requires CopyLock exists with valid token
- All transitions audited via GradingEvent
- Timestamps set atomically with state change

---

## 4. Backend Components

### 4.1 Django Apps

#### core
- **Role**: Project settings, auth, middleware, URLs root
- **Key Files**:
  - `settings.py` - **CRITICAL**: Security settings, DEBUG, SECRET_KEY, ALLOWED_HOSTS, CORS, CSP, SSL
  - `auth.py` - RBAC: UserRole (Admin/Teacher/Student), permission classes
  - `urls.py` - URL routing
  - `celery.py` - Celery app config (autodiscover tasks)
  - `views.py` - Login/Logout, /me/, user management
  - `views_health.py` - /api/health/ endpoint
  - `views_dev.py` - E2E seed endpoint (only if E2E_SEED_TOKEN set)

#### exams
- **Role**: Exam, Booklet, Copy models and API
- **Key Files**:
  - `models.py` - Exam, Booklet, Copy models
  - `validators.py` - PDF validation (size, MIME, integrity)
  - `permissions.py` - IsTeacherOrAdmin, IsOwnerOrAdmin
  - `views.py` - Exam CRUD, upload, booklet management
  - `urls.py`, `urls_copies.py` - API routes

#### grading
- **Role**: Annotation, grading workflow, locks, drafts
- **Key Files**:
  - `models.py` - Annotation, GradingEvent, CopyLock, DraftState
  - `services.py` - **CRITICAL**: GradingService, AnnotationService (business logic, state machine)
  - `permissions.py` - IsLockedByOwnerOrReadOnly
  - `views.py` - Lock/unlock, annotate, finalize, draft CRUD
  - `urls.py` - Grading API routes

#### students
- **Role**: Student management, student auth, results portal
- **Key Files**:
  - `models.py` - Student model
  - `views.py` - Student login, /me/, results list
  - `urls.py` - Student API routes

#### identification
- **Role**: OCR, student matching (semi-automatic identification)
- **Key Files**:
  - `models.py` - OCRResult (if exists)
  - `services.py` - OCRService (Tesseract OCR, header extraction, student matching)
  - `views.py` - OCR endpoints
  - `urls.py` - Identification routes

#### processing
- **Role**: PDF processing services (split, flatten, rasterize)
- **Key Files**:
  - `services/pdf_splitter.py` - Split A3→A4, detect booklets
  - `services/pdf_flattener.py` - Flatten annotations into final PDF
  - `services/vision.py` - Header detection, image processing
  - `services/splitter.py` - Page splitting logic
- **Critical**: Heavy I/O operations, potential bottlenecks

### 4.2 Authentication & Authorization

#### Authentication (Session-based)
- **Method**: Django session auth (cookies, httpOnly, SameSite=Lax)
- **Endpoints**:
  - `POST /api/login/` - Admin/Teacher login (username/password)
  - `POST /api/students/login/` - Student login (INE + last_name)
  - `POST /api/logout/` - Logout (clear session)
  - `GET /api/me/` - Get current user (Admin/Teacher)
  - `GET /api/students/me/` - Get current student
- **CSRF**: Enabled (X-CSRFToken header required for POST/PUT/DELETE)
- **Security**: No JWT (prevents XSS token theft, allows instant revocation)

#### Authorization (RBAC)
- **Roles**: Admin, Teacher, Student (Django Groups)
- **Permission Classes**:
  - `IsAdmin` - Admin only
  - `IsTeacher` - Teacher only
  - `IsStudent` - Student only (or session-based fallback)
  - `IsAdminOrTeacher` - Admin or Teacher
  - `IsTeacherOrAdmin` - (duplicate, same as above)
  - `IsOwnerOrAdmin` - Object owner or Admin (for annotations)
  - `IsLockedByOwnerOrReadOnly` - Write requires lock ownership
  - `IsStudentForOwnData` - Student can only access own copies

#### Permission Matrix (Key Endpoints)

| Endpoint | Admin | Teacher | Student | Lock Required |
|----------|-------|---------|---------|---------------|
| POST /api/exams/upload/ | ✅ | ✅ | ❌ | - |
| POST /api/exams/{id}/merge/ | ✅ | ✅ | ❌ | - |
| POST /api/grading/copies/{id}/lock/ | ✅ | ✅ | ❌ | - |
| POST /api/grading/copies/{id}/annotations/ | ✅ | ✅ | ❌ | ✅ |
| POST /api/grading/copies/{id}/finalize/ | ✅ | ✅ | ❌ | ✅ |
| GET /api/students/results/ | ❌ | ❌ | ✅ (own only) | - |
| GET /api/students/copies/{id}/final-pdf/ | ❌ | ❌ | ✅ (own only) | - |

---

## 5. Frontend Components

### 5.1 Architecture

```
frontend/src/
├── components/           # Reusable UI components
│   ├── CanvasLayer.vue      # Annotation canvas
│   ├── GradingScaleBuilder.vue  # Hierarchical grading scale editor
│   ├── GradingSidebar.vue   # Grading sidebar with score
│   └── PDFViewer.vue        # PDF rendering
├── router/
│   └── index.js          # Vue Router config (12 routes, guards)
├── services/
│   ├── api.js            # Axios instance (CSRF, credentials, interceptors)
│   └── gradingApi.js     # Grading API calls (lock, annotate, finalize)
├── stores/
│   ├── auth.js           # Auth state (login, logout, user)
│   └── examStore.js      # Exam state (upload, booklets, merge)
├── utils/
│   └── storage.js        # Local storage helpers
├── views/
│   ├── admin/            # Admin views
│   │   ├── ImportCopies.vue
│   │   ├── IdentificationDesk.vue
│   │   ├── CorrectorDesk.vue  # **CRITICAL**: Grading interface
│   │   ├── UserManagement.vue
│   │   ├── StapleView.vue
│   │   └── MarkingSchemeView.vue
│   ├── student/          # Student views
│   │   ├── LoginStudent.vue
│   │   └── ResultView.vue  # Student portal
│   ├── AdminDashboard.vue
│   ├── CorrectorDashboard.vue
│   ├── Home.vue          # Landing page
│   ├── Login.vue         # Admin/Teacher login
│   └── Settings.vue
├── App.vue
└── main.js
```

### 5.2 Routing & Guards

**Router Guards** (in `router/index.js`):
1. **Authentication Check**: Fetches user if not loaded (`authStore.fetchUser()`)
2. **Protected Routes**: Require `meta.requiresAuth = true`
3. **Role-Based Access**: `meta.role` must match `user.role` (or Admin bypass)
4. **Redirect Logic**:
   - Unauthenticated → Home (/)
   - Wrong role → Correct dashboard
   - Already logged in on login page → Dashboard

**Routes**:
```
/ (Home) - Landing page with role selection
/admin/login - Admin login
/teacher/login - Teacher login
/student/login - Student login
/admin-dashboard - Admin dashboard (requiresAuth, role: Admin)
/corrector-dashboard - Teacher dashboard (requiresAuth, role: Teacher)
/corrector/desk/:copyId - Grading interface (requiresAuth, role: Teacher)
/exam/:examId/identification - Identification desk (requiresAuth, role: Admin)
/student-portal - Student results (requiresAuth, role: Student)
/admin/users - User management (requiresAuth, role: Admin)
/admin/settings - Settings (requiresAuth, role: Admin)
/exam/:examId/staple - Stapling view (requiresAuth, role: Admin)
/exam/:examId/grading-scale - Grading scale editor (requiresAuth, role: Admin)
```

### 5.3 State Management (Pinia)

#### authStore (auth.js)
- **State**:
  - `user` (ref) - Current user object { username, role, ... }
  - `isAuthenticated` (computed) - !!user
  - `isChecking` (ref) - Prevent infinite loop during auth check
- **Actions**:
  - `login(username, password)` - Admin/Teacher login
  - `loginStudent(ine, lastName)` - Student login
  - `logout()` - Clear session
  - `fetchUser(preferStudent=false)` - Fetch current user (tries /me/ then /students/me/)

#### examStore (examStore.js)
- **State**:
  - `currentExam` (ref)
  - `booklets` (ref)
  - `isLoading` (ref)
  - `error` (ref)
- **Actions**:
  - `uploadExam(file)` - Upload PDF, auto-fetch booklets
  - `fetchBooklets(examId)` - Get booklets for exam
  - `mergeBooklets(bookletIds)` - Merge booklets into copy

### 5.4 API Layer

#### api.js (Axios Instance)
- **Base URL**: `VITE_API_URL` (env) or `/api`
- **Credentials**: `withCredentials: true` (session cookies)
- **CSRF**: Interceptor reads `csrftoken` cookie, sets `X-CSRFToken` header
- **Timeout**: 10s
- **Headers**: `Content-Type: application/json`, `Accept: application/json`

#### gradingApi.js (Grading API)
- **Methods**:
  - `listCopies(params)` - GET /copies/
  - `getCopy(id)` - GET /copies/{id}/
  - `readyCopy(id)` - POST /grading/copies/{id}/ready/
  - `acquireLock(id, ttl)` - POST /grading/copies/{id}/lock/
  - `heartbeatLock(id, token)` - POST /grading/copies/{id}/lock/heartbeat/
  - `releaseLock(id, token)` - DELETE /grading/copies/{id}/lock/release/
  - `finalizeCopy(id, token)` - POST /grading/copies/{id}/finalize/
  - `createAnnotation(copyId, payload, token)` - POST /grading/copies/{copyId}/annotations/
  - `listAnnotations(copyId)` - GET /grading/copies/{copyId}/annotations/
  - `deleteAnnotation(copyId, annotationId, token)` - DELETE /grading/annotations/{annotationId}/
  - `getDraft(copyId)` - GET /grading/copies/{copyId}/draft/
  - `saveDraft(copyId, payload, token, clientId)` - PUT /grading/copies/{copyId}/draft/
  - `deleteDraft(copyId, token)` - DELETE /grading/copies/{copyId}/draft/
  - `listAuditLogs(copyId)` - GET /grading/copies/{copyId}/audit/
  - `getFinalPdfUrl(id)` - Helper for final PDF URL

---

## 6. Critical Workflows

### 6.1 Workflow 1: Admin Exam Upload & Identification

**Actors**: Admin  
**Goal**: Upload scanned PDF → Split into booklets → Merge/identify → Create copies

**Steps**:
1. **Upload PDF**
   - `POST /api/exams/upload/` (FormData: name, date, pdf_source)
   - Backend validates PDF (size, MIME, integrity)
   - Creates Exam record, saves PDF to media storage
   - Returns exam ID

2. **Process PDF** (Split)
   - Backend splits PDF into booklets (processing.services.pdf_splitter)
   - Creates Booklet records with page ranges
   - Generates header crops for each booklet
   - Optional: OCR on headers (identification.services.OCRService)
   - Frontend auto-fetches booklets after upload

3. **Admin Reviews Booklets** (Stapling View)
   - `GET /api/exams/{id}/booklets/` - List all booklets
   - Admin selects booklets belonging to same student
   - Admin clicks "Merge & Create Copy"

4. **Merge Booklets → Create Copy**
   - `POST /api/exams/{id}/merge/` (body: {booklet_ids: [...]})
   - Backend creates Copy in STAGING status
   - Links booklets via M2M
   - Generates anonymous_id
   - Creates audit event (GradingEvent.IMPORT)

5. **Identification** (Manual or Semi-Auto)
   - Admin navigates to Identification Desk
   - Reviews OCR suggestions or manually types student name
   - Links Copy to Student (Copy.student = student_id)
   - Sets Copy.is_identified = true

6. **Validate Copy → READY**
   - Admin clicks "Validate"
   - Backend transitions Copy: STAGING → READY
   - Sets Copy.validated_at timestamp
   - Creates audit event (GradingEvent.VALIDATE)
   - Copy now appears in teacher dashboards for grading

**Critical Points**:
- PDF validation must prevent malformed files (DoS, memory exhaustion)
- Booklet merge must be atomic (transaction)
- OCR is optional/fallible (must handle errors gracefully)
- State transitions must be audited

### 6.2 Workflow 2: Teacher Correction (Grading Desk)

**Actors**: Teacher  
**Goal**: Lock copy → Annotate → Autosave → Finalize → Generate final PDF

**Steps**:
1. **Teacher Selects Copy**
   - `GET /api/copies/` (filtered by status=READY, exam, etc.)
   - Teacher clicks "Start Grading"
   - Navigates to `/corrector/desk/:copyId`

2. **Acquire Lock**
   - `POST /api/grading/copies/{id}/lock/` (body: {ttl_seconds: 600})
   - Backend checks:
     - Copy status = READY (not STAGING or GRADED)
     - No existing lock OR lock expired
   - Creates CopyLock (copy, owner, token, expires_at)
   - Transitions Copy: READY → LOCKED
   - Sets Copy.locked_at, Copy.locked_by
   - Creates audit event (GradingEvent.LOCK)
   - Returns lock token to frontend

3. **Load Copy Data**
   - `GET /api/copies/{id}/` - Copy metadata
   - `GET /api/grading/copies/{id}/annotations/` - Existing annotations
   - `GET /api/grading/copies/{id}/draft/` - Autosaved draft (if exists)
   - Frontend renders PDF with existing annotations

4. **Teacher Annotates**
   - Teacher draws rectangles on PDF canvas
   - Each annotation: {page_index, x, y, w, h, content, type, score_delta}
   - Frontend sends: `POST /api/grading/copies/{id}/annotations/` (headers: {X-Lock-Token: token})
   - Backend validates:
     - Lock token matches CopyLock.token
     - Lock not expired
     - Coordinates in [0,1]
     - Page index valid
   - Creates Annotation record
   - Creates audit event (GradingEvent.CREATE_ANN)

5. **Autosave** (every 5s or on change)
   - Frontend sends: `PUT /api/grading/copies/{id}/draft/` (body: {payload, token, client_id})
   - Backend upserts DraftState (unique on copy+owner)
   - Payload includes: annotations, scroll position, active page, unsaved text

6. **Lock Heartbeat** (every 5min)
   - `POST /api/grading/copies/{id}/lock/heartbeat/` (body: {token})
   - Backend extends CopyLock.expires_at by 30min
   - Prevents timeout during long grading sessions

7. **Finalize Copy**
   - Teacher clicks "Finalize"
   - `POST /api/grading/copies/{id}/finalize/` (headers: {X-Lock-Token: token})
   - Backend:
     - Validates lock ownership
     - Flattens annotations into PDF (processing.services.pdf_flattener)
     - Saves final PDF to Copy.final_pdf
     - Transitions Copy: LOCKED → GRADED
     - Sets Copy.graded_at timestamp
     - Deletes CopyLock (release lock)
     - Deletes DraftState (cleanup)
     - Creates audit event (GradingEvent.FINALIZE)
   - Returns final PDF URL

8. **Release Lock** (Manual or Auto on Close)
   - `DELETE /api/grading/copies/{id}/lock/release/` (body: {token})
   - Backend deletes CopyLock
   - Transitions Copy: LOCKED → READY (if not finalized)
   - Creates audit event (GradingEvent.UNLOCK)

**Critical Points**:
- Lock token must be validated on every write operation
- Lock expiration must be enforced (prevent stale locks)
- Autosave must not overwrite from different client_id (concurrency)
- Final PDF generation is heavy I/O (potential bottleneck)
- State transitions must be atomic (transaction)
- All actions must be audited for compliance

### 6.3 Workflow 3: Student Portal (Gate 4)

**Actors**: Student  
**Goal**: Login → View graded copies → Download final PDF

**Steps**:
1. **Student Login**
   - Student navigates to `/student/login`
   - Enters INE + last_name
   - `POST /api/students/login/` (body: {ine, last_name})
   - Backend validates:
     - Student exists (INE match)
     - Last name matches (case-insensitive)
   - Creates session (or links Student.user if exists)
   - Frontend fetches: `GET /api/students/me/`
   - Sets authStore.user = {role: 'Student', ...}
   - Redirects to `/student-portal`

2. **List Graded Copies**
   - `GET /api/students/results/` (authenticated as student)
   - Backend filters:
     - Copy.student = current student
     - Copy.status = GRADED (only finalized copies)
   - Returns list of {exam_name, date, anonymous_id, final_pdf_url}

3. **View Final PDF**
   - Student clicks on copy
   - `GET /api/students/copies/{id}/final-pdf/` (authenticated)
   - Backend validates:
     - Copy belongs to current student (IsStudentForOwnData permission)
     - Copy status = GRADED
   - Serves final PDF (with annotations) via Django FileResponse or Nginx

**Critical Points**:
- Student login must validate INE + last_name (prevent IDOR)
- Results list must filter by student ownership (no data leakage)
- Final PDF access must enforce object-level permissions
- Must handle case where student has no graded copies (empty state)

### 6.4 Workflow 4: Export to Pronote (CSV)

**Actors**: Admin  
**Goal**: Export grades for all graded copies to CSV

**Steps**:
1. **Admin Navigates to Export**
   - Admin dashboard shows "Export Grades" button

2. **Generate CSV**
   - `GET /api/exams/{id}/export/` (or similar endpoint - **NOT YET VERIFIED**)
   - Backend queries:
     - All copies for exam with status=GRADED
     - Joins with Student data
   - Generates CSV: `INE, Last Name, First Name, Class, Anonymous ID, Score, Graded At`
   - Returns CSV file for download

**Critical Points**:
- CSV must include only GRADED copies (no partial data)
- Must handle unidentified copies (anonymous_id only, no student data)
- Must sanitize CSV output (prevent CSV injection)

---

## 7. Docker Infrastructure

### 7.1 Docker Compose Configurations

#### docker-compose.yml (Development)
**Location**: `infra/docker/docker-compose.yml`
**Services**:
- `db` (PostgreSQL 15): Port 5435 (exposed), volume: postgres_data
- `redis` (Redis 7): Port 6385 (exposed)
- `backend` (Django runserver): Port 8088 (exposed), DEBUG=true, hot reload (volume mount)
- `celery` (Celery worker): Shares backend code
- `frontend` (Vite dev): Port 5173, hot reload

**Env**:
- DEBUG=true
- SSL_ENABLED=false
- CORS permissive (localhost origins)

#### docker-compose.prod.yml (Production)
**Location**: `infra/docker/docker-compose.prod.yml`
**Services**:
- `db` (PostgreSQL 15-alpine): Internal only, health check
- `redis` (Redis 7-alpine): Internal only, health check
- `backend` (Gunicorn): Port 8000 (internal), workers=3, timeout=120, health check
- `celery`: Shares backend image
- `nginx`: Port 8088 (exposed), serves frontend + proxies backend, health check

**Env** (from .env):
- DJANGO_ENV=production
- DEBUG=False (enforced)
- SECRET_KEY (must be set)
- ALLOWED_HOSTS (explicit, no *)
- SSL_ENABLED (true for HTTPS)
- CORS_ALLOWED_ORIGINS (explicit)
- CSRF_TRUSTED_ORIGINS (explicit)

**Images**: Uses `ghcr.io/${GITHUB_REPOSITORY_OWNER}/korrigo-{backend|nginx}:${KORRIGO_SHA}`

#### docker-compose.e2e.yml (E2E Override)
**Location**: `infra/docker/docker-compose.e2e.yml`
**Purpose**: Override for E2E testing (Playwright)
**Changes**:
- DJANGO_ENV=e2e (not production)
- RATELIMIT_ENABLE=false (allow rapid API calls)
- Bind mount `backend/scripts` for seed script

#### docker-compose.prodlike.yml (Local Prod Test)
**Purpose**: Test production config locally (HTTP only, no SSL)
**Changes**:
- SSL_ENABLED=false (HTTP for E2E)
- Ports exposed for debugging
- Otherwise identical to prod

#### docker-compose.local-prod.yml
**Purpose**: Local production build (not fully documented in inventory)

### 7.2 Volumes

| Volume | Path | Purpose | Backup Criticality |
|--------|------|---------|-------------------|
| `postgres_data` | `/var/lib/postgresql/data` | PostgreSQL database | **CRITICAL** |
| `media_volume` | `/app/media` | Uploaded PDFs, images, final PDFs | **CRITICAL** |
| `static_volume` | `/app/staticfiles` | CSS, JS, Django admin static | Medium |

**DANGER**: `docker-compose down -v` destroys volumes (data loss)

### 7.3 Health Checks

- **PostgreSQL**: `pg_isready -U {user} -d {db}` (interval: 5s, retries: 5)
- **Redis**: `redis-cli ping` (interval: 5s, retries: 5)
- **Backend**: `curl -f http://localhost:8000/api/health/` (interval: 30s, start_period: 30s)
- **Nginx**: `curl -f http://localhost/` (interval: 30s)

---

## 8. Security Configuration

### 8.1 Django Settings (settings.py)

#### Production Guards
```python
DJANGO_ENV = os.environ.get("DJANGO_ENV", "development")

# SECRET_KEY: Required in production
if not SECRET_KEY and DJANGO_ENV == "production":
    raise ValueError("SECRET_KEY must be set in production")

# DEBUG: Must be False in production
if DJANGO_ENV == "production" and raw_debug:
    raise ValueError("DEBUG must be False in production")

# ALLOWED_HOSTS: No wildcards in production
if "*" in ALLOWED_HOSTS and DJANGO_ENV == "production":
    raise ValueError("ALLOWED_HOSTS cannot contain '*' in production")

# RATELIMIT_ENABLE: Cannot disable in production (unless E2E_TEST_MODE)
if DJANGO_ENV == "production" and not RATELIMIT_ENABLE and not E2E_TEST_MODE:
    raise ValueError("RATELIMIT_ENABLE cannot be false in production")
```

#### SSL/HTTPS Configuration
```python
SSL_ENABLED = os.environ.get("SSL_ENABLED", "False").lower() == "true"

if not DEBUG and SSL_ENABLED:
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
```

#### CORS Configuration
- **Development**: Permissive (localhost origins)
- **Production**: Explicit origins from `CORS_ALLOWED_ORIGINS` env var
- **Credentials**: `CORS_ALLOW_CREDENTIALS = True`

#### CSRF Configuration
- **Trusted Origins**: `CSRF_TRUSTED_ORIGINS` (explicit list)
- **Cookie**: `CSRF_COOKIE_HTTPONLY = False` (required for SPA to read token)
- **SameSite**: `Lax` (balance security vs usability)

#### Content Security Policy (CSP)
- **Production**:
  - `default-src: 'self'`
  - `script-src: 'self' 'unsafe-inline'` (Vue.js needs inline scripts)
  - `style-src: 'self' 'unsafe-inline'`
  - `img-src: 'self' data: blob:`
  - `frame-ancestors: 'none'`
  - `upgrade-insecure-requests: true`
- **Development**: Permissive (allow unsafe-eval for HMR)

#### Other Security Headers
- `SECURE_BROWSER_XSS_FILTER = True`
- `SECURE_CONTENT_TYPE_NOSNIFF = True`
- `X_FRAME_OPTIONS = 'DENY'`

### 8.2 File Upload Limits
```python
DATA_UPLOAD_MAX_MEMORY_SIZE = 104857600  # 100 MB
FILE_UPLOAD_MAX_MEMORY_SIZE = 104857600  # 100 MB
```

### 8.3 PDF Validators (exams/validators.py)
- **Extension**: `.pdf` only
- **Size**: Max 50 MB, 500 pages
- **MIME**: `application/pdf`
- **Integrity**: PyMuPDF can open without error

### 8.4 DRF Default Permissions
```python
REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',  # Deny by default
    ],
    ...
}
```

---

## 9. Testing Infrastructure

### 9.1 Backend Tests (pytest)

**Location**: `backend/tests/`, `backend/*/tests/`  
**Command**: `pytest` or `make test`  
**Config**: `pytest.ini`

**Test Types**:
- Unit tests (models, services, validators)
- Integration tests (API endpoints, workflows)
- Concurrency tests (lock contention, race conditions)

**Critical Areas** (expected coverage):
- State machine transitions (Copy status)
- Lock acquisition/release (concurrency)
- Annotation validation (coordinates, page index)
- PDF validation (malformed files)
- Permissions (RBAC, object-level)
- Audit trail (GradingEvent creation)

### 9.2 Frontend Tests (E2E - Playwright)

**Location**: `frontend/e2e/`  
**Command**: `npx playwright test`  
**Config**: `playwright.config.ts`

**E2E Scenarios** (expected):
- Admin login → Upload exam → Merge booklets → Validate copy
- Teacher login → Lock copy → Annotate → Finalize
- Student login → View results → Download PDF
- Concurrent editing (two teachers, lock conflict)
- Autosave recovery (refresh page, restore draft)

**Seed Data** (deterministic):
- `backend/scripts/seed_e2e.py` - Creates users, students, copies in different states
- Must create at least 2 students with copies (GRADED, LOCKED, READY)
- Seed invoked via `POST /api/dev/seed/` (only if E2E_SEED_TOKEN set)

### 9.3 Linting & Type Checking

**Frontend**:
- **Lint**: `npm run lint` (ESLint)
- **Typecheck**: `npm run typecheck` (vue-tsc)

**Backend**:
- **Lint**: (Not explicitly mentioned - likely ruff/flake8 if exists)
- **Typecheck**: (Python is dynamically typed - mypy if exists)

---

## 10. Deployment & Operations

### 10.1 Deployment Modes

| Mode | Compose File | Use Case | SSL | DEBUG |
|------|--------------|----------|-----|-------|
| Development | `docker-compose.yml` | Local dev, hot reload | No | True |
| Production | `docker-compose.prod.yml` | Real deployment | Yes | False |
| Prod-like | `docker-compose.prodlike.yml` | Local prod test | No | False |
| E2E | `docker-compose.local-prod.yml + e2e.yml` | E2E testing | No | False |

### 10.2 Makefile Commands

| Command | Action | Compose File |
|---------|--------|--------------|
| `make up` | Start production stack | `docker-compose.prod.yml` |
| `make down` | Stop stack (preserve volumes) | `docker-compose.prod.yml` |
| `make logs` | Tail logs | `docker-compose.prod.yml` |
| `make migrate` | Run Django migrations | `docker-compose.prod.yml` |
| `make superuser` | Create admin user | `docker-compose.prod.yml` |
| `make test` | Run backend tests | `docker-compose.prod.yml` |
| `make shell` | Django shell | `docker-compose.prod.yml` |
| `make init_pmf` | Init users/groups | `docker-compose.prod.yml` |

### 10.3 Environment Variables

**Required in Production**:
- `SECRET_KEY` - Django secret (never hardcode)
- `POSTGRES_PASSWORD` - Database password
- `ALLOWED_HOSTS` - Explicit hostnames (no *)
- `CORS_ALLOWED_ORIGINS` - Explicit origins
- `CSRF_TRUSTED_ORIGINS` - Explicit origins
- `SSL_ENABLED=True` - Enable HTTPS redirects

**Optional**:
- `DEBUG` (default: True in dev, must be False in prod)
- `E2E_SEED_TOKEN` (only for E2E testing, never in prod)
- `RATELIMIT_ENABLE` (default: true, never false in prod)
- `CELERY_BROKER_URL` (default: redis://redis:6379/0)
- `DATABASE_URL` (default: postgres://...)

### 10.4 Static & Media Files

**Static Files** (CSS, JS, admin):
- **Development**: Served by Django runserver (DEBUG=True)
- **Production**: Collected via `python manage.py collectstatic`, served by Nginx

**Media Files** (Uploaded PDFs, images):
- **Development**: Served by Django (DEBUG=True), stored in `backend/media/`
- **Production**: Served by Nginx (read-only volume mount), stored in `media_volume`

**Nginx Config** (assumed):
```nginx
location /media/ {
    alias /app/media/;
}
location /static/ {
    alias /app/staticfiles/;
}
location /api/ {
    proxy_pass http://backend:8000;
}
```

### 10.5 Database Migrations

**Commands**:
- `python manage.py makemigrations` - Generate migration files
- `python manage.py migrate` - Apply migrations
- `python manage.py makemigrations --check --dry-run` - Verify no unapplied migrations

**Safety**:
- Migrations must be backwards-compatible (additive changes)
- Never delete columns with data (use deprecation)
- Test migrations in staging before prod

---

## 11. Known Gaps & Assumptions

### Gaps (Not Yet Verified)
1. **Celery Tasks**: No task.py files found - async processing may not be fully implemented
2. **CSV Export Endpoint**: Mentioned in workflow but not verified in API inventory
3. **Rate Limiting**: Configured but implementation not verified (django-ratelimit decorators?)
4. **Nginx Config**: Not read (assumed standard reverse proxy setup)
5. **CI/CD Pipeline**: `.github/workflows/` not inventoried (likely exists but not verified)
6. **Backup/Restore Scripts**: Mentioned in docs but not verified in `ops/` or `scripts/`
7. **Monitoring/Logging**: Celery Flower, log aggregation not verified
8. **Lock Cleanup Task**: Periodic task to remove expired locks not found (may cause stale locks)

### Assumptions
1. **Nginx serves frontend in prod**: Assumed based on docker-compose.prod.yml (frontend built into nginx image)
2. **Celery autodiscovers tasks**: Configured in celery.py but no tasks found (may be in services.py as sync calls)
3. **CSRF token in cookie**: Frontend reads csrftoken cookie (CSRF_COOKIE_HTTPONLY=False)
4. **Session storage**: Default Django DB session backend (not Redis - may impact scalability)
5. **Media storage**: Local filesystem (not S3/cloud - OK for local deployment)

---

## 12. Critical Files for Audit

### P0 (Security/Data Integrity)
- `backend/core/settings.py` - Security settings, guards
- `backend/core/auth.py` - RBAC permissions
- `backend/exams/permissions.py` - Object-level permissions
- `backend/grading/permissions.py` - Lock-based permissions
- `backend/grading/services.py` - State machine, business logic
- `backend/exams/validators.py` - File upload validation
- `backend/grading/models.py` - CopyLock, DraftState (concurrency)
- `backend/exams/models.py` - Copy state machine
- `frontend/src/router/index.js` - Route guards
- `frontend/src/services/api.js` - CSRF handling

### P1 (Robustness/Operations)
- `backend/processing/services/*.py` - PDF processing (I/O bottlenecks)
- `backend/identification/services.py` - OCR (error handling)
- `backend/core/views.py` - Auth endpoints
- `backend/grading/views.py` - Lock/unlock, finalize
- `infra/docker/docker-compose.prod.yml` - Production config
- `.env.example` - Default env vars
- `backend/pytest.ini` - Test config
- `frontend/e2e/*.spec.ts` - E2E tests

### P2 (Quality/Documentation)
- `docs/ARCHITECTURE.md` - Architecture reference
- `docs/DATABASE_SCHEMA.md` - Schema reference
- `README.md` - Setup guide
- `Makefile` - Operational commands
- All `urls.py` - API surface area

---

## 13. Next Steps (Audit Phase 2)

With this inventory complete, proceed to:

1. **Risk Analysis (P0/P1/P2)**:
   - Security: AuthN bypass, AuthZ bypass, CSRF/XSS, injection, IDOR, sensitive data exposure
   - Data Integrity: State corruption, race conditions, data loss, orphaned records
   - Operations: Crash scenarios, silent failures, missing monitoring, performance bottlenecks

2. **Deep Code Review**:
   - State machine enforcement (Copy status transitions)
   - Lock mechanism (concurrency, expiration, token validation)
   - Permissions (all endpoints, object-level checks)
   - Error handling (services, views, frontend)
   - Transaction boundaries (atomic operations)

3. **Testing Validation**:
   - Run backend tests, verify coverage
   - Run E2E tests, verify determinism
   - Check lint/typecheck
   - Verify seed data creates valid test scenarios

4. **Production Readiness Checklist**:
   - Settings validation (DEBUG, SECRET_KEY, ALLOWED_HOSTS, etc.)
   - Migration safety
   - Docker health checks
   - Backup/restore procedures
   - Monitoring/alerting gaps

---

**Inventory Complete**: 2026-01-27  
**Next Phase**: AUDIT PAR RISQUE (P0/P1/P2)
