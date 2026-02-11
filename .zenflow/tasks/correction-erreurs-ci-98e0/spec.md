# Technical Specification: Django Migration Conflict Resolution

## 1. Technical Context

### 1.1 Technology Stack
- **Framework**: Django 5.2.10 (per migration files) / Django 4.2.27 (mixed versions detected)
- **Language**: Python 3.9 (per CI configuration)
- **Database**: PostgreSQL 15 (per CI services configuration)
- **CI/CD**: GitHub Actions (Ubuntu latest runners)
- **Testing**: pytest with django test database

### 1.2 Current Architecture

#### Project Structure
```
backend/
├── students/
│   ├── models.py           # Student model definition (source of truth)
│   └── migrations/
│       ├── 0001_initial.py                          # ✓ Common base
│       ├── 0002_student_user.py                     # ✓ Common base
│       └── 0003_remove_ine_add_date_naissance.py    # ⚠️ Main branch
├── core/
│   ├── settings.py
│   └── settings_test.py    # Test database configuration
└── manage.py
```

#### Identified Migration Conflicts

**Common Base** (all branches share):
- `0001_initial.py`: Creates Student with `ine` field (unique)
- `0002_student_user.py`: Adds `user` OneToOneField relationship

**Conflicting Migrations** (multiple leaf nodes):
1. **Main branch**: `0003_remove_ine_add_date_naissance.py`
   - Removes `ine` field
   - Adds `date_naissance` (DateField, required)
   - Adds `groupe` (CharField, optional)
   - Creates unique constraint on `(last_name, first_name, date_naissance)`
   - Adds index on same fields

2. **Branch `ci-suite-tests-parallele-zenflow-9947`** (not in main, per PRD):
   - `0003_student_email_user_required.py`
   - `0004_remove_ine_add_fields.py`
   - `0005_refactor_student_model.py`
   - `0006_add_privacy_charter_fields.py`

3. **Branch `portail-eleve-auth-ine-dob-acces-6a41`** (not in main, per PRD):
   - `0003_student_birth_date.py`
   - `0004_alter_student_birth_date.py`

**Migration Graph Visualization**:
```
0001_initial
    ↓
0002_student_user
    ├─→ 0003_remove_ine_add_date_naissance (main)
    ├─→ 0003_student_email_user_required (branch: ci-suite-tests-parallele-zenflow-9947)
    └─→ 0003_student_birth_date (branch: portail-eleve-auth-ine-dob-acces-6a41)
```

**Result**: Three leaf nodes, causing Django migration validation to fail.

### 1.3 Target Model State

The final `Student` model (from [./backend/students/models.py](./backend/students/models.py:4-31)) should have:

```python
class Student(models.Model):
    first_name = models.CharField(max_length=100, verbose_name="Prénom")
    last_name = models.CharField(max_length=100, verbose_name="Nom")
    date_naissance = models.DateField(verbose_name="Date de naissance")
    email = models.EmailField(blank=True, null=True, verbose_name="Email")
    class_name = models.CharField(max_length=50, verbose_name="Classe")
    groupe = models.CharField(max_length=20, blank=True, null=True, verbose_name="Groupe")
    user = models.OneToOneField(User, on_delete=models.SET_NULL, null=True, blank=True, 
                                 related_name='student_profile', verbose_name="Utilisateur associé")
    
    class Meta:
        unique_together = [['last_name', 'first_name', 'date_naissance']]
        indexes = [models.Index(fields=['last_name', 'first_name', 'date_naissance'])]
```

**Key observation**: Current main branch migrations already achieve this target state via `0003_remove_ine_add_date_naissance.py`.

### 1.4 CI Configuration Analysis

#### Test Database Configuration ([./backend/core/settings_test.py](./backend/core/settings_test.py:33-46))
```python
DB_SUFFIX = "".join(ch for ch in str(raw_suffix) if ch.isalnum() or ch in "_").lower() or "0"
DATABASES['default']['TEST'] = {
    'NAME': f'test_viatique_{DB_SUFFIX}',  # Defaults to test_viatique_0
    'SERIALIZE': False,
}
```

#### CI Workflow Issue ([./.github/workflows/korrigo-ci.yml](./github/workflows/korrigo-ci.yml:169-171))
```yaml
- name: Create test database
  run: |
    PGPASSWORD=viatique_password psql -h 127.0.0.1 -U viatique_user -d postgres \
      -c "CREATE DATABASE test_viatique_0 OWNER viatique_user;" || true
```

**Problem**: 
- The `|| true` ignores errors if database exists from previous failed runs
- Django's migration check expects to create the test database itself
- Pre-existing `test_viatique_0` prevents Django from setting up fresh schema

## 2. Implementation Approach

### 2.1 Migration Conflict Resolution Strategy

Since **main branch already has the correct final state**, the approach is:

1. **No migration merge needed in main** - the current `0003_remove_ine_add_date_naissance.py` correctly represents the target model
2. **Feature branches will rebase** - other branches with conflicting migrations will need to rebase onto main and resolve their migrations
3. **Focus on CI fixes** - ensure CI can run migrations cleanly

**Rationale**:
- Main branch is the deployment target
- Main's `0003` migration matches the current `models.py` definition
- Other branches are feature branches that should align with main's schema
- This avoids creating artificial merge migrations for conflicts that don't exist in main

### 2.2 Test Database Cleanup Strategy

**Current Issue**: Pre-created database prevents Django from running migrations during test setup.

**Solution**: Drop and recreate database cleanly on each CI run.

**Implementation**:
```yaml
- name: Setup test database (clean)
  run: |
    PGPASSWORD=viatique_password psql -h 127.0.0.1 -U viatique_user -d postgres \
      -c "DROP DATABASE IF EXISTS test_viatique_0;"
    PGPASSWORD=viatique_password psql -h 127.0.0.1 -U viatique_user -d postgres \
      -c "CREATE DATABASE test_viatique_0 OWNER viatique_user;"
```

**Alternative** (let Django handle it entirely):
```yaml
# Remove the manual database creation step entirely
# Django's test runner will create and drop the database automatically
# This is cleaner but may fail if permissions are insufficient
```

**Recommended**: Use explicit DROP + CREATE for CI reliability and debugging clarity.

## 3. Source Code Structure Changes

### 3.1 Files to Modify

#### Required Changes
1. **[./.github/workflows/korrigo-ci.yml](./github/workflows/korrigo-ci.yml:169-171)** (High priority)
   - Update `tests-postgres` job to drop existing test database before creating
   - Ensures clean test environment on each run

2. **[./.github/workflows/release-gate.yml](./.github/workflows/release-gate.yml)** (if applicable)
   - Apply same test database cleanup pattern
   - Verify location via: `grep -r "test_viatique" .github/workflows/`

3. **[./.github/workflows/tests-optimized.yml](./.github/workflows/tests-optimized.yml)** (if applicable)
   - Apply same pattern if it uses PostgreSQL service

#### No Changes Required
- **Migration files** - No merge migration needed; main branch is correct
- **models.py** - Already matches target state
- **settings_test.py** - Current configuration is correct

### 3.2 Validation Commands

After changes, these commands must pass:

```bash
# Migration graph validation (no conflicting leaf nodes)
cd backend
python manage.py makemigrations --check --dry-run

# Migration consistency check
python manage.py migrate --check

# Full test suite (CI environment simulation)
pytest -q
pytest -q -m postgres grading/tests/test_concurrency_postgres.py
```

## 4. Data Model Changes

**No data model changes required** - the current `Student` model in [./backend/students/models.py](./backend/students/models.py:4-31) already represents the desired final state.

### 4.1 Database Constraints (Already Implemented)
- **Unique constraint**: `(last_name, first_name, date_naissance)` - prevents duplicate students
- **Index**: Composite index on same fields - optimizes student lookups
- **Foreign key**: `user` OneToOneField with `SET_NULL` - preserves student data if user deleted

## 5. API / Interface Changes

**No API changes** - this is purely a migration and CI infrastructure fix.

### 5.1 Backwards Compatibility
- Existing deployments: Not affected (no schema changes)
- API contracts: Unchanged
- Frontend integration: No impact

## 6. Delivery Phases

### Phase 1: CI Test Database Fix (Critical)
**Goal**: Restore CI to passing state

**Tasks**:
1. Update `.github/workflows/korrigo-ci.yml` test database setup
2. Test CI pipeline with clean database creation
3. Verify all test suites pass

**Verification**:
```bash
# Simulate CI environment locally
docker run --rm -d --name postgres-ci \
  -e POSTGRES_DB=viatique_test \
  -e POSTGRES_USER=viatique_user \
  -e POSTGRES_PASSWORD=viatique_password \
  -p 5432:5432 postgres:15-alpine

# Drop and create test database
PGPASSWORD=viatique_password psql -h 127.0.0.1 -U viatique_user -d postgres \
  -c "DROP DATABASE IF EXISTS test_viatique_0;"
PGPASSWORD=viatique_password psql -h 127.0.0.1 -U viatique_user -d postgres \
  -c "CREATE DATABASE test_viatique_0 OWNER viatique_user;"

# Run migrations and tests
cd backend
DATABASE_URL=postgres://viatique_user:viatique_password@127.0.0.1:5432/viatique_test \
  DJANGO_SETTINGS_MODULE=core.settings_test \
  pytest -q -m postgres grading/tests/test_concurrency_postgres.py

# Cleanup
docker stop postgres-ci
```

**Success Criteria**:
- ✅ `tests-postgres` job passes in CI
- ✅ No "database already exists" errors
- ✅ Migrations apply cleanly to empty test database

### Phase 2: Verify All CI Workflows (High)
**Goal**: Ensure complete CI pipeline passes

**Tasks**:
1. Run full CI suite (push to main triggers all workflows)
2. Verify each workflow job passes:
   - Lint
   - Unit tests
   - Security (pip-audit, bandit)
   - Integration tests
   - Postgres tests
   - Packaging (Docker build)
3. Check other workflows if they exist:
   - `release-gate.yml`
   - `tests-optimized.yml`

**Verification**:
- All GitHub Actions workflows show green checkmarks
- No skipped jobs
- No warning messages in logs

### Phase 3: Commit and Push (Critical)
**Goal**: Deploy fix to main branch

**Tasks**:
1. Commit changes with descriptive message
2. Push to main branch
3. Monitor CI execution
4. Verify deployment gate passes

**Commit Message Template**:
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

**Success Criteria**:
- ✅ Changes committed to main
- ✅ CI workflows triggered automatically
- ✅ All workflows pass on main branch

## 7. Verification Approach

### 7.1 Pre-Deployment Validation

#### Migration Consistency Check
```bash
cd backend
python manage.py makemigrations --check --dry-run
# Expected: "No changes detected"

python manage.py migrate --check
# Expected: Exit code 0 (no pending migrations)
```

#### Test Suite Execution
```bash
# Unit tests (no database)
DJANGO_SETTINGS_MODULE=core.settings_test pytest -q

# PostgreSQL tests (with database)
DATABASE_URL=postgres://viatique_user:viatique_password@127.0.0.1:5432/viatique_test \
  DJANGO_SETTINGS_MODULE=core.settings_test \
  pytest -q -m postgres

# Integration tests
DJANGO_SETTINGS_MODULE=core.settings_test \
  pytest -q grading/tests/test_workflow_complete.py \
           grading/tests/test_concurrency.py \
           exams/tests/test_pdf_validators.py \
           core/tests/test_full_audit.py
```

#### Lint and Security
```bash
cd backend

# Flake8 (per CI configuration)
flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
flake8 . --count --exit-zero --max-complexity=10 --max-line-length=127 --statistics

# Bandit (security)
bandit -r . -c .bandit -ll

# Dependency audit
pip-audit -r requirements.txt \
  --ignore-vuln GHSA-w853-jp5j-5j7f \
  --ignore-vuln GHSA-qmgc-5h2g-mvrw
```

### 7.2 Post-Deployment Validation

#### GitHub Actions Workflows
Monitor these workflows after push to main:
1. **Korrigo CI (Deployable Gate)** - Must pass all jobs
2. **Release Gate One-Shot** - Production validation
3. **Tests (Optimized)** - Quick test execution

#### Verification Checklist
- [ ] All CI jobs complete successfully (green checkmarks)
- [ ] No migration warnings in logs
- [ ] Test database created and dropped cleanly
- [ ] No manual intervention required
- [ ] Subsequent pushes continue to pass

### 7.3 Rollback Plan

If CI still fails after changes:

1. **Immediate**: Revert commit and push
   ```bash
   git revert HEAD
   git push origin main
   ```

2. **Investigate**: Check CI logs for:
   - Database connection errors
   - Permission issues
   - Migration dependency errors

3. **Alternative approach**: Remove manual database creation entirely and let Django handle it:
   ```yaml
   # Comment out or remove database creation step
   # Django's test runner will manage database lifecycle
   ```

## 8. Testing Strategy

### 8.1 Local Testing (Pre-commit)

**Setup**:
```bash
# Start PostgreSQL container
docker run --rm -d --name postgres-test \
  -e POSTGRES_DB=viatique_test \
  -e POSTGRES_USER=viatique_user \
  -e POSTGRES_PASSWORD=viatique_password \
  -p 5432:5432 postgres:15-alpine

# Wait for PostgreSQL to be ready
sleep 5
```

**Test Scenario 1: Clean Database Migration**
```bash
# Create test database
PGPASSWORD=viatique_password psql -h 127.0.0.1 -U viatique_user -d postgres \
  -c "DROP DATABASE IF EXISTS test_viatique_0;"
PGPASSWORD=viatique_password psql -h 127.0.0.1 -U viatique_user -d postgres \
  -c "CREATE DATABASE test_viatique_0 OWNER viatique_user;"

# Run migrations
cd backend
DATABASE_URL=postgres://viatique_user:viatique_password@127.0.0.1:5432/viatique_test \
  DJANGO_SETTINGS_MODULE=core.settings_test \
  python manage.py migrate

# Expected: All migrations apply successfully
```

**Test Scenario 2: Idempotent Database Recreation**
```bash
# Run database creation twice (simulates failed CI run + retry)
PGPASSWORD=viatique_password psql -h 127.0.0.1 -U viatique_user -d postgres \
  -c "DROP DATABASE IF EXISTS test_viatique_0;"
PGPASSWORD=viatique_password psql -h 127.0.0.1 -U viatique_user -d postgres \
  -c "CREATE DATABASE test_viatique_0 OWNER viatique_user;"

# Run again (should succeed)
PGPASSWORD=viatique_password psql -h 127.0.0.1 -U viatique_user -d postgres \
  -c "DROP DATABASE IF EXISTS test_viatique_0;"
PGPASSWORD=viatique_password psql -h 127.0.0.1 -U viatique_user -d postgres \
  -c "CREATE DATABASE test_viatique_0 OWNER viatique_user;"

# Expected: Both runs succeed without errors
```

**Test Scenario 3: Full Test Suite**
```bash
cd backend
DATABASE_URL=postgres://viatique_user:viatique_password@127.0.0.1:5432/viatique_test \
  DJANGO_SETTINGS_MODULE=core.settings_test \
  pytest -q -m postgres grading/tests/test_concurrency_postgres.py

# Expected: All tests pass, no skipped tests
```

**Cleanup**:
```bash
docker stop postgres-test
```

### 8.2 CI Testing (Post-commit)

**Trigger**: Push to main branch automatically triggers workflows

**Monitor**:
1. GitHub Actions UI: https://github.com/{org}/{repo}/actions
2. Check "Korrigo CI (Deployable Gate)" workflow
3. Verify all jobs pass:
   - ✅ lint
   - ✅ unit
   - ✅ security
   - ✅ integration
   - ✅ tests-postgres
   - ✅ packaging
   - ✅ deployable_gate

**Expected Results**:
- All jobs complete with exit code 0
- No "database already exists" errors in `tests-postgres` logs
- Migration output shows successful schema creation
- Test output shows all tests passed

### 8.3 Regression Testing

**After Fix Deployment**:
1. Make a trivial change (e.g., add comment to README.md)
2. Commit and push to main
3. Verify CI runs cleanly without manual intervention
4. Confirm test database is created and dropped properly

**Periodic Checks** (weekly):
- Review CI logs for any database-related warnings
- Ensure test execution time remains consistent
- Verify no stale test databases accumulate

## 9. Risk Mitigation

### 9.1 Identified Risks

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Database permission errors in CI | High | Low | Test database creation locally with same permissions |
| Migration conflicts re-emerge from feature branches | Medium | Medium | Document rebase requirements for feature branches |
| Test database cleanup fails | Medium | Low | Use `DROP DATABASE IF EXISTS` (idempotent) |
| CI workflow syntax errors | High | Low | Validate YAML syntax before commit |
| Other workflows also affected | Medium | Medium | Check all workflow files for similar patterns |

### 9.2 Contingency Plans

**If database drop fails**:
```yaml
# Fallback: Force drop with connection termination
- name: Force drop test database
  run: |
    PGPASSWORD=viatique_password psql -h 127.0.0.1 -U viatique_user -d postgres <<EOF
    SELECT pg_terminate_backend(pid) FROM pg_stat_activity 
    WHERE datname = 'test_viatique_0' AND pid <> pg_backend_pid();
    DROP DATABASE IF EXISTS test_viatique_0;
    CREATE DATABASE test_viatique_0 OWNER viatique_user;
    EOF
```

**If permissions insufficient**:
```yaml
# Use superuser (postgres) to create database
- name: Create test database as superuser
  run: |
    PGPASSWORD=postgres psql -h 127.0.0.1 -U postgres -d postgres <<EOF
    DROP DATABASE IF EXISTS test_viatique_0;
    CREATE DATABASE test_viatique_0 OWNER viatique_user;
    GRANT ALL PRIVILEGES ON DATABASE test_viatique_0 TO viatique_user;
    EOF
```

## 10. Dependencies and Constraints

### 10.1 Technical Dependencies
- Django ORM migration system (built-in)
- PostgreSQL 15 (GitHub Actions service)
- pytest (already in requirements.txt)
- psql CLI (available in ubuntu-latest runner)

### 10.2 Constraints
- **Python 3.9 compatibility**: Cannot use Python 3.10+ features
- **PostgreSQL 15**: Must use compatible SQL syntax
- **GitHub Actions runner**: Ubuntu latest (currently 22.04)
- **No breaking changes**: Must not affect existing APIs or data

### 10.3 External Dependencies
None - all changes are within the repository.

## 11. Open Questions and Assumptions

### 11.1 Assumptions
1. ✅ Main branch represents the canonical migration state
2. ✅ No production databases exist with conflicting migrations
3. ✅ Feature branches will rebase onto main after fix
4. ✅ Test database cleanup is acceptable (no persistent test data needed)
5. ✅ CI runners have sufficient permissions to drop/create databases

### 11.2 Decisions Made
1. **No migration merge in main** - Current migration is correct
2. **Explicit database cleanup** - Use `DROP DATABASE IF EXISTS` for reliability
3. **Target main branch only** - Feature branches handled separately
4. **CI-only changes** - No application code modifications needed

### 11.3 Future Considerations
- Document migration best practices to prevent future conflicts
- Consider squashing migrations after all branches align
- Add pre-merge checks to detect migration conflicts early
- Implement branch protection rules requiring CI pass before merge

## 12. Success Metrics

### 12.1 Immediate Success Criteria
- ✅ All CI workflows pass on main branch
- ✅ No migration conflict errors in logs
- ✅ Test database created cleanly on each run
- ✅ No manual intervention required

### 12.2 Long-Term Success Criteria
- ✅ CI remains stable for 1 week without failures
- ✅ Feature branches successfully rebase onto main
- ✅ New migrations do not create conflicts
- ✅ Development team follows updated migration guidelines

## 13. Documentation Updates Required

### 13.1 Code Comments
- Add comment in `.github/workflows/korrigo-ci.yml` explaining database cleanup
- Document why `DROP DATABASE IF EXISTS` is necessary

### 13.2 Team Documentation (if requested)
- Update developer onboarding guide with migration best practices
- Document branch rebasing procedure for feature branches
- Create troubleshooting guide for CI failures

### 13.3 Commit Messages
Use conventional commit format:
```
fix(ci): resolve test database conflicts in PostgreSQL tests

- Drop and recreate test_viatique_0 database on each CI run
- Prevents "database already exists" errors from failed runs
- Ensures migrations apply to clean schema every time

Fixes: students app migration graph conflicts
Affects: Korrigo CI, Release Gate, Tests (Optimized)

BREAKING CHANGE: None (CI infrastructure only)
```

---

## Appendix A: Migration File Reference

### Current Main Branch Migrations

**[./backend/students/migrations/0001_initial.py](./backend/students/migrations/0001_initial.py:1-30)**
- Creates `Student` model with `ine` field (unique)
- Fields: id, ine, first_name, last_name, class_name, email

**[./backend/students/migrations/0002_student_user.py](./backend/students/migrations/0002_student_user.py:1-22)**
- Adds `user` OneToOneField to User model
- Enables student authentication integration

**[./backend/students/migrations/0003_remove_ine_add_date_naissance.py](./backend/students/migrations/0003_remove_ine_add_date_naissance.py:1-55)**
- Removes `ine` field (privacy/GDPR compliance)
- Adds `date_naissance` field (required)
- Adds `groupe` field (optional)
- Creates unique constraint on `(last_name, first_name, date_naissance)`
- Adds composite index for performance

### Migration Dependency Graph (Main Branch Only)
```
0001_initial (Django 5.2.10, 2026-01-17)
    ↓
0002_student_user (Django 4.2.27, 2026-01-25)
    ↓
0003_remove_ine_add_date_naissance (custom, date unknown)
```

**Status**: Linear, no conflicts ✅

## Appendix B: CI Workflow Reference

**[./.github/workflows/korrigo-ci.yml](./github/workflows/korrigo-ci.yml)**: Main deployability gate
- Jobs: lint, unit, security, integration, tests-postgres, packaging
- Trigger: Push to main/develop, PRs to main/develop
- Concurrency: Cancels in-progress runs for same ref

**Test Database Setup** (lines 169-184):
```yaml
- name: Create test database
  run: |
    PGPASSWORD=viatique_password psql -h 127.0.0.1 -U viatique_user -d postgres \
      -c "CREATE DATABASE test_viatique_0 OWNER viatique_user;" || true
    # ^^^ PROBLEM: || true masks errors, leaves stale database
```

**Required Change**:
```yaml
- name: Setup test database (clean)
  run: |
    PGPASSWORD=viatique_password psql -h 127.0.0.1 -U viatique_user -d postgres <<EOF
    DROP DATABASE IF EXISTS test_viatique_0;
    CREATE DATABASE test_viatique_0 OWNER viatique_user;
    EOF
```

## Appendix C: References

### Related Files
- [./backend/students/models.py](./backend/students/models.py) - Student model definition
- [./backend/core/settings_test.py](./backend/core/settings_test.py) - Test configuration
- [./.github/workflows/korrigo-ci.yml](./.github/workflows/korrigo-ci.yml) - CI workflow
- [./backend/requirements.txt](./backend/requirements.txt) - Python dependencies

### Django Documentation
- [Django Migrations](https://docs.djangoproject.com/en/5.0/topics/migrations/)
- [Testing Django Applications](https://docs.djangoproject.com/en/5.0/topics/testing/)
- [Multiple Databases](https://docs.djangoproject.com/en/5.0/topics/db/multi-db/)

### GitHub Actions Documentation
- [PostgreSQL Service Container](https://docs.github.com/en/actions/using-containerized-services/creating-postgresql-service-containers)
- [Workflow Syntax](https://docs.github.com/en/actions/using-workflows/workflow-syntax-for-github-actions)

---

**Document Version**: 1.0  
**Created**: 2026-02-11  
**Author**: Zencoder AI (Technical Specification Step)  
**Status**: Ready for Planning Phase
