# Product Requirements Document: Django Migration Conflict Resolution

## Executive Summary

The CI pipeline is failing due to Django migration conflicts in the `students` app. Multiple branches have independently created migrations with the same sequence numbers, resulting in conflicting migration histories that prevent the application from deploying successfully.

## Problem Statement

### Current Issues

1. **Migration Graph Conflicts**: Multiple leaf nodes exist in the Django migration graph for the `students` app, preventing migrations from running successfully
2. **Test Database Creation Failures**: The PostgreSQL test database `test_viatique_0` already exists from previous failed CI runs, causing subsequent test runs to fail
3. **CI/CD Pipeline Blockage**: The main branch cannot be deployed due to migration validation failures

### Root Cause Analysis

Through codebase examination, I identified the following migration conflicts across branches:

**Main Branch (current state)**:
- `0001_initial.py`
- `0002_student_user.py`
- `0003_remove_ine_add_date_naissance.py`

**Branch: `ci-suite-tests-parallele-zenflow-9947`**:
- `0001_initial.py`
- `0002_student_user.py`
- `0003_student_email_user_required.py`
- `0004_remove_ine_add_fields.py`
- `0005_refactor_student_model.py`
- `0006_add_privacy_charter_fields.py`

**Branch: `portail-eleve-auth-ine-dob-acces-6a41`**:
- `0001_initial.py`
- `0002_student_user.py`
- `0003_student_birth_date.py`
- `0004_alter_student_birth_date.py`

**Conflict**: Multiple branches created different `0003` migrations after branching from the same `0002` base, creating multiple leaf nodes in the migration dependency graph.

## Requirements

### Functional Requirements

#### FR1: Resolve Migration Conflicts
- **Priority**: Critical
- **Description**: Merge all conflicting migration branches into a single, linear migration history
- **Acceptance Criteria**:
  - Django's migration graph has exactly one leaf node per app
  - `python manage.py migrate --check` passes without errors
  - All model changes from conflicting migrations are preserved in the final state
  - The final `Student` model matches the current model definition in `students/models.py`

#### FR2: Clean Test Environment
- **Priority**: High
- **Description**: Ensure CI test database can be created cleanly on each run
- **Acceptance Criteria**:
  - Test database creation succeeds in CI
  - No manual database cleanup required between test runs
  - Database teardown is properly configured in test settings

#### FR3: CI Pipeline Restoration
- **Priority**: Critical
- **Description**: Restore all CI workflows to passing state
- **Acceptance Criteria**:
  - `Korrigo CI (Deployable Gate)` workflow passes completely
  - `Release Gate One-Shot` workflow passes completely
  - `Tests (Optimized)` workflow passes completely
  - All test suites execute successfully

### Non-Functional Requirements

#### NFR1: Data Integrity
- **Priority**: Critical
- **Description**: Migration resolution must not corrupt existing data
- **Acceptance Criteria**:
  - All database constraints are preserved
  - Unique constraints on `(last_name, first_name, date_naissance)` are maintained
  - Foreign key relationships remain intact
  - Indexes are properly created

#### NFR2: Deployment Safety
- **Priority**: High
- **Description**: Changes must be deployable to production without risk
- **Acceptance Criteria**:
  - Migration merge is reversible if issues arise
  - Production database can be migrated forward without data loss
  - Migrations are idempotent (can be run multiple times safely)

#### NFR3: Version Control Hygiene
- **Priority**: High
- **Description**: Maintain clean git history
- **Acceptance Criteria**:
  - Changes are committed to main branch
  - Commit messages clearly describe migration resolution
  - No large binary files or temporary files are committed

## Current System State

### Student Model (Target State)
The final `Student` model in `backend/students/models.py` should have:
- `first_name`: CharField(max_length=100)
- `last_name`: CharField(max_length=100)
- `date_naissance`: DateField (required)
- `email`: EmailField (optional)
- `class_name`: CharField(max_length=50)
- `groupe`: CharField(max_length=20, optional)
- `user`: OneToOneField to Django User (optional)
- Unique constraint: `(last_name, first_name, date_naissance)`
- Index on: `(last_name, first_name, date_naissance)`

### CI Workflows Affected
1. **Korrigo CI (Deployable Gate)** (`.github/workflows/korrigo-ci.yml`)
   - Lint job
   - Unit tests (pytest)
   - Security checks (pip-audit, bandit)
   - Integration tests
   - Postgres tests
   - Packaging (Docker build)

2. **Release Gate One-Shot** (`.github/workflows/release-gate.yml`)
   - Production-like environment validation
   - Full test suite
   - E2E tests
   - Zero-tolerance validation

3. **Tests (Optimized)** (`.github/workflows/tests-optimized.yml`)
   - Quick test execution

## Success Criteria

1. ✅ All CI workflows pass on main branch
2. ✅ Migration graph has single linear path with no conflicts
3. ✅ Student model schema matches the current model definition
4. ✅ All tests pass (unit, integration, E2E)
5. ✅ Changes are committed and pushed to main branch
6. ✅ No manual intervention required for future CI runs

## Out of Scope

- Refactoring the Student model structure
- Adding new fields or features to the Student model
- Modifying CI workflow configurations (unless required for test database cleanup)
- Migrating existing production data (this fix applies to fresh deployments)

## Constraints

1. Must maintain Python 3.9 compatibility (per CI configuration)
2. Must use PostgreSQL 15 (per CI configuration)
3. Must follow existing Django migration best practices
4. Must not introduce breaking changes to existing APIs
5. Solution must work in CI environment (GitHub Actions Ubuntu runner)

## Assumptions

1. The current `Student` model definition in `models.py` represents the desired final state
2. No production data exists that would prevent migration merge
3. The test database issue is due to improper cleanup, not infrastructure problems
4. All branches will eventually align with the merged migration history

## Dependencies

- Django ORM migration system
- PostgreSQL 15 database
- GitHub Actions CI environment
- pytest test framework
- Docker (for containerized testing in release gate)

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Migration merge creates data loss | Low | Critical | Test migrations on fresh database before committing |
| Merge migration is not compatible with all branches | Medium | High | Coordinate with branch owners to rebase |
| Test database cleanup fails in CI | Low | Medium | Add explicit teardown in CI workflow |
| Production deployment fails after merge | Low | Critical | Test in production-like environment (release gate) |

## Clarification Questions

**Q1**: Are there any production databases currently running with the conflicting migrations?
- **Decision**: Assume no production data exists; this is a pre-production fix

**Q2**: Should we rebase feature branches or have them create new migrations?
- **Decision**: Feature branches should rebase on main after the fix to inherit the merged migration history

**Q3**: Should we preserve all migration history or squash into fewer migrations?
- **Decision**: Preserve individual migrations but merge conflicts to maintain audit trail

## Next Steps

Upon approval of this PRD:
1. Create technical specification for migration merge approach
2. Plan detailed implementation steps
3. Execute migration merge in development environment
4. Test in CI environment
5. Commit and push to main
6. Verify all CI workflows pass
