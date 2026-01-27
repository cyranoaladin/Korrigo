# P2 Audit: Quality & Technical Debt Issues

**Date**: 2026-01-27  
**Auditor**: Zenflow  
**Scope**: Code quality, test coverage, documentation, developer experience, maintainability

---

## Executive Summary

This document catalogs **P2 (nice-to-have improvement)** issues identified during the production readiness audit. These issues do not block production deployment but should be addressed in future sprints to improve code quality, maintainability, and developer experience.

**Total P2 Issues**: 24  
**Categories**: Code Quality (8), Test Coverage (5), Documentation (4), Developer Experience (3), Maintainability (4)

---

## P2-001: Console.log Statements in Production Code

**Category**: Code Quality  
**Severity**: Low  
**Impact**: Debug noise, potential information leakage in production

**Finding**:  
46 instances of `console.log` and `console.error` found in frontend code that should be removed or replaced with proper logging.

**Evidence**:
```bash
$ grep -r "console\.log\|console\.error" frontend/src --include="*.vue" --include="*.js" | wc -l
46
```

**Locations**:
- `frontend/src/views/Settings.vue` (2 instances)
- `frontend/src/views/admin/UserManagement.vue` (4 instances)
- `frontend/src/views/admin/CorrectorDesk.vue` (6 instances)
- `frontend/src/views/admin/IdentificationDesk.vue` (2 instances)
- And 14+ other files

**Recommendation**:
1. Replace `console.error` with proper error handling/user feedback
2. Remove or gate `console.log` with environment checks
3. Consider implementing a proper logging service (e.g., Sentry, LogRocket)

**Priority**: Medium (should address before next release)

---

## P2-002: Duplicate Logger Imports

**Category**: Code Quality  
**Severity**: Low  
**Impact**: Code duplication, inconsistency

**Finding**:  
In `backend/exams/views.py:38-39` and `exams/views.py:59-60`, the logger is imported twice in the same function.

**Evidence**:
```python
# exams/views.py:38-39
import logging
logger = logging.getLogger(__name__)

# Later in the same file (line 59-60)
import logging
logger = logging.getLogger(__name__)
```

**Recommendation**:
- Import logger once at module level
- Use consistent logging pattern across all modules

**Priority**: Low

---

## P2-003: Magic Numbers - DPI Hardcoded

**Category**: Maintainability  
**Severity**: Low  
**Impact**: Hard to change, inconsistency risk

**Finding**:  
DPI value `150` is hardcoded in multiple locations without configuration centralization.

**Evidence**:
```bash
backend/processing/services/pdf_splitter.py:    def __init__(self, pages_per_booklet=4, dpi=150):
backend/exams/views.py:                splitter = PDFSplitter(dpi=150)
backend/exams/views.py:            pix = page.get_pixmap(dpi=150)
```

**Recommendation**:
- Extract to settings: `PDF_RASTERIZATION_DPI = 150`
- Document why 150 DPI was chosen (balance between quality and performance)

**Priority**: Low

---

## P2-004: Magic Numbers - File Size Limits

**Category**: Maintainability  
**Severity**: Low  
**Impact**: Hard to configure

**Finding**:  
File size limit `104857600` (100 MB) is hardcoded in settings.

**Evidence**:
```python
# backend/core/settings.py
DATA_UPLOAD_MAX_MEMORY_SIZE = 104857600  # 100 MB
FILE_UPLOAD_MAX_MEMORY_SIZE = 104857600  # 100 MB
```

**Recommendation**:
- Already documented with comment (✅)
- Consider making configurable via environment variable for different deployments

**Priority**: Low

---

## P2-005: Missing Module Docstrings

**Category**: Code Quality / Documentation  
**Severity**: Low  
**Impact**: Reduced code understandability

**Finding**:  
20+ Python modules lack module-level docstrings.

**Evidence**:
```bash
backend/students/urls.py
backend/students/models.py
backend/students/admin.py
backend/exams/urls.py
backend/grading/views_lock.py
# ... and 15+ more
```

**Recommendation**:
- Add module docstrings explaining purpose and responsibilities
- Example format:
  ```python
  """
  Student management views.
  
  Provides endpoints for:
  - Student CRUD operations (admin only)
  - CSV import functionality
  - Student-copy association
  """
  ```

**Priority**: Low

---

## P2-006: Large Component - CorrectorDesk.vue (848 lines)

**Category**: Code Quality / Maintainability  
**Severity**: Medium  
**Impact**: Hard to maintain, test, and understand

**Finding**:  
`frontend/src/views/admin/CorrectorDesk.vue` is 848 lines long, making it the largest component by far.

**Evidence**:
```bash
$ find frontend/src -name "*.vue" | xargs wc -l | sort -rn | head -5
   848 frontend/src/views/admin/CorrectorDesk.vue
   476 frontend/src/views/AdminDashboard.vue
   413 frontend/src/views/admin/UserManagement.vue
   357 frontend/src/components/GradingScaleBuilder.vue
```

**Recommendation**:
1. Extract composables for lock management, autosave, annotation editing
2. Extract child components (AnnotationEditor, PageNavigator, HistoryPanel)
3. Target: < 400 lines per component

**Priority**: Medium (affects maintainability)

---

## P2-007: No Frontend Unit Tests

**Category**: Test Coverage  
**Severity**: High (already identified as P0 in inventory)  
**Impact**: Reduced confidence in frontend changes

**Finding**:  
Zero frontend unit tests. Only E2E tests exist.

**Evidence**:
```bash
$ find frontend/src -name "*.spec.js" -o -name "*.test.js"
# (no results)
```

**Recommendation**:
- Add Vitest for unit testing
- Test stores (auth, examStore) with ~80% coverage
- Test critical components (GradingScaleBuilder, CanvasLayer)
- Test utility functions

**Priority**: HIGH (should be addressed soon)

**Note**: This is already tracked as a P0 issue in `INVENTORY_TESTING_QA.md`

---

## P2-008: Test Marker Underutilization

**Category**: Test Coverage / Developer Experience  
**Severity**: Low  
**Impact**: Cannot filter tests reliably

**Finding**:  
pytest markers exist but are underutilized. Cannot easily run "only unit tests" or "only integration tests".

**Evidence**:
From `INVENTORY_TESTING_QA.md`:
- Only 2 uses of `@pytest.mark.slow`
- No consistent use of `@pytest.mark.unit` or `@pytest.mark.integration`

**Recommendation**:
1. Add markers to all tests:
   - `@pytest.mark.unit` - Pure logic, no DB
   - `@pytest.mark.integration` - Uses DB/services
   - `@pytest.mark.e2e` - Full workflow tests
2. Document in pytest.ini
3. Add to Makefile: `make test-unit`, `make test-integration`

**Priority**: Low (improves DX)

---

## P2-009: Missing Edge Case Tests

**Category**: Test Coverage  
**Severity**: Medium  
**Impact**: Potential bugs in edge cases

**Finding**:  
Several edge cases lack test coverage:

1. **PDF with > 500 pages**: No test for max page limit
2. **Concurrent lock attempts**: Concurrency tests exist but limited (SQLite)
3. **Student with > 100 copies**: Pagination edge case
4. **Annotation at exact boundary** (x+w=1.0): Epsilon handling
5. **Upload during server restart**: Crash recovery

**Recommendation**:
- Add explicit edge case test suite: `backend/tests/test_edge_cases.py`
- Test boundary conditions for all validators
- Test pagination with large datasets

**Priority**: Medium

---

## P2-010: No API Documentation Generated

**Category**: Documentation  
**Severity**: Low  
**Impact**: Harder for API consumers

**Finding**:  
While DRF Spectacular is configured (`docs/API_REFERENCE.md` references it), no instructions for generating interactive API docs.

**Recommendation**:
1. Add to README:
   ```bash
   # View API docs
   make api-docs
   # Opens http://localhost:8000/api/schema/swagger-ui/
   ```
2. Add to Makefile:
   ```makefile
   api-docs:
       @echo "API docs available at http://localhost:8000/api/schema/swagger-ui/"
       @open http://localhost:8000/api/schema/swagger-ui/ || xdg-open http://localhost:8000/api/schema/swagger-ui/
   ```

**Priority**: Low

---

## P2-011: Inconsistent Error Handling Patterns

**Category**: Code Quality  
**Severity**: Low  
**Impact**: Inconsistent user experience

**Finding**:  
Error handling is inconsistent between views:
- Some use generic `Exception` catch
- Some use specific `ValueError`, `ValidationError`
- Error messages sometimes technical, sometimes user-friendly

**Evidence**:
```python
# exams/views.py:58 - Generic error
except Exception as e:
    logger.error(f"Error processing PDF: {e}", exc_info=True)
    return Response({"error": f"PDF processing failed: {str(e)}"}, 
                   status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# grading/services.py - Specific ValueError with user message
if copy.status != Copy.Status.READY:
    raise ValueError(f"Cannot annotate copy in status {copy.status}")
```

**Recommendation**:
1. Define custom exception hierarchy:
   ```python
   class KorrigoException(Exception): pass
   class ValidationError(KorrigoException): pass
   class StateTransitionError(KorrigoException): pass
   ```
2. Centralize error handling in DRF exception handler
3. Document error response format

**Priority**: Low

---

## P2-012: Missing Type Hints in Backend

**Category**: Code Quality  
**Severity**: Low  
**Impact**: Reduced IDE support, harder to refactor

**Finding**:  
Type hints are inconsistent in backend code. Some functions have them, most don't.

**Evidence**:
```python
# Has type hints (good)
def validate_coordinates(x: float, y: float, w: float, h: float) -> None:
    ...

# Missing type hints (common pattern)
def add_annotation(copy, payload, user):
    ...
```

**Recommendation**:
1. Add type hints to all service layer functions
2. Add type hints to view methods
3. Consider mypy for type checking (optional)

**Priority**: Low

---

## P2-013: Hard-Coded Epsilon for Float Comparison

**Category**: Maintainability  
**Severity**: Low  
**Impact**: Magic number

**Finding**:  
Epsilon `1e-9` is hardcoded for float comparison in coordinate validation.

**Evidence**:
```python
# backend/grading/services.py:31-34
if x + w > 1.0 + 1e-9:  # Epsilon for float issues
     raise ValueError("x + w must not exceed 1")
if y + h > 1.0 + 1e-9:
     raise ValueError("y + h must not exceed 1")
```

**Recommendation**:
- Extract to constant: `COORDINATE_EPSILON = 1e-9`
- Add comment explaining why this epsilon value

**Priority**: Low

---

## P2-014: Canny Edge Detection Parameters Hardcoded

**Category**: Maintainability  
**Severity**: Low  
**Impact**: Hard to tune

**Finding**:  
Canny edge detection thresholds `50, 150` are hardcoded in vision service.

**Evidence**:
```python
# backend/processing/services/vision.py
edged = cv2.Canny(blurred, 50, 150)
```

**Recommendation**:
- Extract to settings or class constants
- Document why these values (standard Canny thresholds)

**Priority**: Low

---

## P2-015: No .env.example Documentation

**Category**: Documentation / Developer Experience  
**Severity**: Medium  
**Impact**: Harder for new developers

**Finding**:  
`.env.example` exists but has minimal documentation.

**Evidence**:
```bash
$ cat .env.example
DJANGO_ENV=development
DEBUG=True
SECRET_KEY=your-secret-key-here
DATABASE_URL=postgresql://user:pass@localhost:5432/dbname
ALLOWED_HOSTS=localhost,127.0.0.1
CORS_ALLOWED_ORIGINS=http://localhost:5173
```

No explanations of:
- When to use `DJANGO_ENV=production`
- What happens if `DEBUG=True` in production (fails)
- Required vs optional variables

**Recommendation**:
Add inline comments:
```bash
# Environment: 'development' or 'production'
# In production: DEBUG must be False and SECRET_KEY must be strong
DJANGO_ENV=development

# Debug mode: MUST be False in production (enforced by startup guard)
DEBUG=True

# Secret key: Generate with `python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'`
SECRET_KEY=your-secret-key-here
```

**Priority**: Medium (DX improvement)

---

## P2-016: No Changelog Maintenance Process

**Category**: Documentation / Process  
**Severity**: Low  
**Impact**: Documentation drift

**Finding**:  
`CHANGELOG.md` exists (created in Phase 3) but no documented process for maintaining it.

**Recommendation**:
1. Add to `CONTRIBUTING.md`:
   - Update CHANGELOG.md before each release
   - Use conventional commits for auto-generation
2. Consider automated changelog generation from git commits

**Priority**: Low

---

## P2-017: Makefile Uses Production Compose by Default

**Category**: Developer Experience  
**Severity**: Medium  
**Impact**: Confusing for new developers

**Finding**:  
Makefile targets use `docker-compose.prod.yml` by default, not `docker-compose.yml`.

**Evidence**:
```makefile
up:
	docker-compose -f infra/docker/docker-compose.prod.yml up --build -d
```

**Recommendation**:
1. Rename to `docker-compose.dev.yml` and `docker-compose.prod.yml`
2. Make Makefile targets use dev by default:
   ```makefile
   COMPOSE_FILE ?= infra/docker/docker-compose.dev.yml
   
   up:
       docker-compose -f $(COMPOSE_FILE) up --build -d
   
   up-prod:
       docker-compose -f infra/docker/docker-compose.prod.yml up --build -d
   ```

**Priority**: Medium (DX improvement)

---

## P2-018: No Database Backup/Restore Documentation

**Category**: Documentation  
**Severity**: Medium  
**Impact**: Operational risk

**Finding**:  
While `backup_restore.py` management command exists, no documentation on:
- How to perform manual backups
- Backup schedule recommendations
- Restore procedures

**Recommendation**:
Add to `docs/DEPLOYMENT_GUIDE.md`:
```markdown
## Backup & Restore

### Manual Backup
```bash
docker-compose exec backend python manage.py dumpdata > backup_$(date +%Y%m%d).json
```

### Restore
```bash
docker-compose exec backend python manage.py loaddata backup_20260127.json
```
```

**Priority**: Medium (operational documentation)

---

## P2-019: Tight Coupling - GradingService Knows About PDF Flattening

**Category**: Maintainability / Architecture  
**Severity**: Low  
**Impact**: Harder to test, change PDF library

**Finding**:  
`GradingService.finalize_copy()` directly calls PDF flattening logic. If PDF library changes, service must change.

**Evidence**:
```python
# backend/grading/services.py:316+
def finalize_copy(copy: Copy, user):
    # ... state transition ...
    # PDF flattening inline (P0: not in transaction)
    flattener = PDFFlattener()
    final_pdf_bytes = flattener.flatten(copy)
```

**Recommendation**:
- Consider injecting PDFFlattener as dependency (DI pattern)
- Or use message queue for heavy processing (Celery task)

**Priority**: Low (architecture improvement for future)

---

## P2-020: No Performance Benchmarks

**Category**: Testing  
**Severity**: Low  
**Impact**: Cannot detect performance regressions

**Finding**:  
No performance tests or benchmarks exist for:
- PDF processing (split, rasterize, flatten)
- Large exam handling (100+ copies)
- Concurrent grading (10+ teachers)

**Recommendation**:
1. Add pytest-benchmark tests for critical paths
2. Document baseline performance metrics
3. Add to CI: fail if performance degrades > 20%

**Priority**: Low (nice-to-have)

---

## P2-021: Frontend Router Guards Lack Tests

**Category**: Test Coverage  
**Severity**: Medium  
**Impact**: Security-critical code untested

**Finding**:  
Router guards (`frontend/src/router/index.js`) enforce role-based access but have no unit tests.

**Evidence**:
```javascript
// No tests for these guards
router.beforeEach((to, from, next) => {
  if (to.meta.requiresAuth && !authStore.isAuthenticated) {
    next('/login')
  }
  // ... role checks ...
})
```

**Recommendation**:
- Add unit tests for all route guard scenarios
- Test: unauthenticated, wrong role, correct role
- Mock authStore for testing

**Priority**: Medium (security-related)

---

## P2-022: No Code Coverage Reporting

**Category**: Test Coverage / Process  
**Severity**: Low  
**Impact**: Cannot track coverage trends

**Finding**:  
pytest-cov is used but no coverage reporting or tracking.

**Recommendation**:
1. Add to CI:
   ```bash
   pytest --cov=backend --cov-report=html --cov-report=term
   ```
2. Upload coverage to Codecov or similar
3. Add coverage badge to README

**Priority**: Low

---

## P2-023: Student Model Lacks Indexes

**Category**: Maintainability / Performance (P1 overlap)  
**Severity**: Medium  
**Impact**: Slow queries on large student datasets

**Finding**:  
`Student` model queries by email, student_id but no indexes defined.

**Recommendation**:
- Add indexes on frequently queried fields
- Already noted in P1 findings for Copy model
- Should be addressed together

**Priority**: Medium (P1 overlap)

---

## P2-024: No Linter for SQL Queries

**Category**: Code Quality  
**Severity**: Low  
**Impact**: Risk of inefficient queries

**Finding**:  
No automated detection of N+1 queries or missing select_related/prefetch_related.

**Recommendation**:
1. Add django-silk or django-debug-toolbar in dev
2. Add nplusone package to detect N+1 queries in tests
3. Document query optimization patterns

**Priority**: Low

---

## Summary Matrix

| ID | Category | Priority | Effort | Impact |
|----|----------|----------|--------|--------|
| P2-001 | Code Quality | Medium | Low | Low |
| P2-002 | Code Quality | Low | Low | Low |
| P2-003 | Maintainability | Low | Low | Low |
| P2-004 | Maintainability | Low | Low | Low |
| P2-005 | Documentation | Low | Medium | Low |
| P2-006 | Maintainability | Medium | High | Medium |
| P2-007 | Test Coverage | HIGH | High | High |
| P2-008 | Developer Experience | Low | Low | Low |
| P2-009 | Test Coverage | Medium | Medium | Medium |
| P2-010 | Documentation | Low | Low | Low |
| P2-011 | Code Quality | Low | Medium | Low |
| P2-012 | Code Quality | Low | High | Low |
| P2-013 | Maintainability | Low | Low | Low |
| P2-014 | Maintainability | Low | Low | Low |
| P2-015 | Documentation | Medium | Low | Medium |
| P2-016 | Documentation | Low | Low | Low |
| P2-017 | Developer Experience | Medium | Low | Medium |
| P2-018 | Documentation | Medium | Low | Medium |
| P2-019 | Maintainability | Low | High | Low |
| P2-020 | Testing | Low | Medium | Low |
| P2-021 | Test Coverage | Medium | Medium | Medium |
| P2-022 | Testing | Low | Low | Low |
| P2-023 | Performance | Medium | Low | Medium |
| P2-024 | Code Quality | Low | Medium | Low |

---

## Prioritized Backlog

### High Priority (Should Address Soon)
1. **P2-007**: Frontend unit tests (overlaps with P0 finding)
2. **P2-006**: Refactor large CorrectorDesk component
3. **P2-021**: Test router guards

### Medium Priority (Next Sprint)
4. **P2-009**: Edge case test coverage
5. **P2-015**: .env.example documentation
6. **P2-017**: Fix Makefile dev/prod confusion
7. **P2-018**: Backup/restore documentation
8. **P2-001**: Remove console.log statements

### Low Priority (Future Improvements)
9. **P2-003-P2-005, P2-008, P2-010-P2-024**: Code quality improvements

---

## Notes

- **P2-007** is already tracked as **P0** in `INVENTORY_TESTING_QA.md` (no frontend unit tests)
- **P2-023** is related to **P1** finding (missing indexes on Copy model)
- Several issues (P2-003, P2-004, P2-013, P2-014) are related to "magic numbers" - can be batched together

---

## Conclusion

While none of these P2 issues block production deployment, addressing them will:
1. **Improve maintainability**: Easier to modify and extend code
2. **Enhance developer experience**: Faster onboarding, clearer setup
3. **Increase confidence**: Better test coverage, clearer error messages
4. **Reduce technical debt**: Prevent accumulation of code quality issues

**Recommended approach**: Address high-priority items in next sprint, tackle medium-priority items over 2-3 sprints, and low-priority items as time permits.
