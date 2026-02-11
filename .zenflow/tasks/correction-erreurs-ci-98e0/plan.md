# Full SDD workflow

## Configuration
- **Artifacts Path**: {@artifacts_path} → `.zenflow/tasks/{task_id}`

---

## Workflow Steps

### [x] Step: Requirements
<!-- chat-id: 68a05a9a-459e-470b-adbe-d66b23adb143 -->

Create a Product Requirements Document (PRD) based on the feature description.

1. Review existing codebase to understand current architecture and patterns
2. Analyze the feature definition and identify unclear aspects
3. Ask the user for clarifications on aspects that significantly impact scope or user experience
4. Make reasonable decisions for minor details based on context and conventions
5. If user can't clarify, make a decision, state the assumption, and continue

Save the PRD to `{@artifacts_path}/requirements.md`.

### [x] Step: Technical Specification
<!-- chat-id: 1db24751-582d-40b0-9d82-80ec1151b436 -->

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
<!-- chat-id: 2c0f6bf1-6630-4ca8-af03-03f2bb27011f -->

Create a detailed implementation plan based on `{@artifacts_path}/spec.md`.

1. Break down the work into concrete tasks
2. Each task should reference relevant contracts and include verification steps
3. Replace the Implementation step below with the planned tasks

Rule of thumb for step size: each step should represent a coherent unit of work (e.g., implement a component, add an API endpoint). Avoid steps that are too granular (single function) or too broad (entire feature).

Important: unit tests must be part of each implementation task, not separate tasks. Each task should implement the code and its tests together, if relevant.

If the feature is trivial and doesn't warrant full specification, update this workflow to remove unnecessary steps and explain the reasoning to the user.

Save to `{@artifacts_path}/plan.md`.

---

## Implementation Tasks

### [ ] Step: Fix CI Test Database Creation

Update GitHub Actions workflows to properly clean and recreate the test database on each CI run.

**Files to modify:**
- `.github/workflows/korrigo-ci.yml`
- `.github/workflows/release-gate.yml` (if uses PostgreSQL)
- `.github/workflows/tests-optimized.yml` (if uses PostgreSQL)

**Changes:**
- Replace `CREATE DATABASE ... || true` with explicit `DROP DATABASE IF EXISTS` + `CREATE DATABASE`
- Ensures clean database state on each CI run
- Prevents "database already exists" errors from failed runs

**Verification steps:**
- [ ] Check that all workflow files are updated consistently
- [ ] Verify database creation commands use correct credentials and database name
- [ ] Confirm proper error handling (no silent failures)

**Reference:** Spec section 2.2 (Test Database Cleanup Strategy)

### [ ] Step: Verify Migration State

Validate that the current migration state in main branch is correct and has no conflicts.

**Tasks:**
- [ ] Run `python manage.py makemigrations --check --dry-run` to verify no pending migrations
- [ ] Run `python manage.py migrate --check` to validate migration graph
- [ ] Inspect migration files to confirm single linear path
- [ ] Verify `students/models.py` matches the final migration state

**Expected outcomes:**
- No pending migrations detected
- Migration graph has single leaf node per app
- No conflicts or multiple heads

**Reference:** Spec section 7.1 (Pre-Deployment Validation)

### [ ] Step: Local Testing with PostgreSQL

Test the migration and database setup locally to ensure it works before pushing to CI.

**Setup:**
- [ ] Start PostgreSQL container with test configuration
- [ ] Create clean test database
- [ ] Run migrations against fresh database
- [ ] Execute test suite with PostgreSQL backend

**Commands to run:**
```bash
# Start PostgreSQL (if not running)
docker run --rm -d --name postgres-test \
  -e POSTGRES_DB=viatique_test \
  -e POSTGRES_USER=viatique_user \
  -e POSTGRES_PASSWORD=viatique_password \
  -p 5432:5432 postgres:15-alpine

# Run migrations
cd backend
python manage.py migrate

# Run PostgreSQL tests
pytest -q -m postgres grading/tests/test_concurrency_postgres.py

# Cleanup
docker stop postgres-test
```

**Verification:**
- [ ] Migrations apply successfully
- [ ] All PostgreSQL tests pass
- [ ] No database connection errors

**Reference:** Spec section 8.1 (Local Testing)

### [ ] Step: Run Full Test Suite and Linting

Execute all tests and linting checks locally before committing to ensure CI will pass.

**Tasks:**
- [ ] Run flake8 linting checks
- [ ] Run bandit security checks
- [ ] Run pip-audit dependency checks
- [ ] Run unit tests (non-database)
- [ ] Run integration tests
- [ ] Verify all tests pass

**Commands:**
```bash
cd backend

# Linting
flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
flake8 . --count --exit-zero --max-complexity=10 --max-line-length=127 --statistics

# Security
bandit -r . -c .bandit -ll
pip-audit -r requirements.txt \
  --ignore-vuln GHSA-w853-jp5j-5j7f \
  --ignore-vuln GHSA-qmgc-5h2g-mvrw

# Tests
pytest -q
```

**Acceptance criteria:**
- [ ] All linting checks pass (exit code 0)
- [ ] No security issues found
- [ ] All test suites pass

**Reference:** Spec section 7.1 (Pre-Deployment Validation)

### [ ] Step: Commit and Push to Main

Commit the CI workflow changes to main branch and push to trigger CI validation.

**Tasks:**
- [ ] Stage modified workflow files
- [ ] Create commit with descriptive message following project conventions
- [ ] Push to main branch
- [ ] Monitor GitHub Actions for triggered workflows

**Commit message:**
```
fix(ci): resolve test database conflicts in PostgreSQL tests

- Drop and recreate test_viatique_0 database on each CI run
- Prevents "database already exists" errors from failed runs
- Ensures migrations apply to clean schema every time

Fixes migration validation in:
- Korrigo CI (Deployable Gate)
- Release Gate One-Shot
- Tests (Optimized)

No application code changes - CI infrastructure only.
```

**Verification:**
- [ ] Commit created successfully
- [ ] Push to main succeeds
- [ ] GitHub Actions workflows trigger automatically

**Reference:** Spec section 6 (Delivery Phases - Phase 3)

### [ ] Step: Monitor and Verify CI Execution

Watch CI workflows execute and verify all jobs pass successfully.

**Workflows to monitor:**
- [ ] Korrigo CI (Deployable Gate) - all jobs green
- [ ] Release Gate One-Shot - all jobs green
- [ ] Tests (Optimized) - all jobs green

**What to check in logs:**
- [ ] Test database created successfully (no "already exists" errors)
- [ ] Migrations applied cleanly
- [ ] All test suites pass
- [ ] No warning messages about migration conflicts
- [ ] No manual intervention required

**Success criteria:**
- All CI workflows show green checkmarks
- No skipped or failed jobs
- Clean execution with no errors or warnings

**If CI fails:**
- Review logs to identify root cause
- Apply fixes and push again
- Consider rollback if issue is severe

**Reference:** Spec section 7.2 (Post-Deployment Validation)

---

## Notes

- **No migration merge needed:** Main branch already has correct final state via `0003_remove_ine_add_date_naissance.py`
- **Focus is CI infrastructure:** The issue is test database cleanup, not application code
- **All changes are in `.github/workflows/` directory:** No backend code modifications required
- **Verification commands are documented** in spec section 7 for reference
