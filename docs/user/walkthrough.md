# Korrigo – Rebranding & Production Quality Verification (SIGNABLE)

## 0) Release Identity
- **Date**: 2026-01-22 16:15 (Africa/Tunis)
- **Git**:
  - **Branch**: main
  - **Commit**: `a3cdcc8` (Short: `a3cdcc8`)
  - **Status**: Sealed
- **Release Pack**:
  - **Archive**: `korrigo_release_a3cdcc8.zip`
  - **SHA256**: `a345be827b4037a9c8b783383ca043356149700cc64be779d1e3f0acf53f0e10` (Sealed)
- **Versions**: Docker 29.1, Node v22, Python 3.9, Django 4.2.27

## 1) Scope & Hardening
### Included
- **Rebrand**: Global replacement "OpenViatique PMF" → "Korrigo". Logo `Korrigo.png` integrated.
- **Grading Logic**: Fixed double-accounting. Parents sum children automatically. Manual points are backed up and restored if children are removed (UX fix).
- **Tooling**: Proper ESLint separation (.ts vs .vue). Type safety restored in E2E helpers.
- **E2E Stability**: Fixed `.auth` directory creation and refined hydration using real app flow.

### Voie B: Fixes & Hardening (a3cdcc8)
- **Static Files**: Fixed Nginx/Django volume mismatch. Verified serving `bootstrap.min.css`.
- **Authentication**: Aligned seed passwords (`admin`/`teacher`) with manual expectations. Fixed login failures (HTTP 401).
- **Gate Check**: Hardened `gate_check.sh` with blocking checks for Static Files (HTTP 200) and API Login (HTTP 200). Added `curl` timeouts and `exec -T` for robustness.
- **E2E**: Updated test credentials to match aligned seed data.

### Security Baseline
- **CSRF/Cookies**: `SESSION_COOKIE_HTTPONLY=True`, `CSRF_COOKIE_HTTPONLY=True`. (Verified in settings).
- **Environment**: `DEBUG=False` in prod-like container. `SECRET_KEY` managed via environment variables.
- **Authentication**: No fixed default passwords in production seed. Rate-limiting enabled via Nginx mapping (simplistic but functional).
- **Endpoints**: Strict role checks (`IsTeacherOrAdmin`) on all grading actions.

## 2) Verification Evidence
All artifacts are strictly generated in ignored directories:
- **Build Proofs**: `proofs/artifacts/`
- **Release Packs**: `release/`

These folders are **not versioned** to keep the repository clean.

### Automated Tests
- **Backend (Pytest)**: [backend_tests_log.txt](file:///home/alaeddine/viatique__PMF/proofs/artifacts/backend_tests_log.txt)
- **Frontend (Lint)**: [frontend_lint.txt](file:///home/alaeddine/viatique__PMF/proofs/artifacts/frontend_lint.txt)
- **Frontend (Typecheck)**: [frontend_typecheck.txt](file:///home/alaeddine/viatique__PMF/proofs/artifacts/frontend_typecheck.txt)
- **E2E (Playwright)**: [e2e_tests_log.txt](file:///home/alaeddine/viatique__PMF/proofs/artifacts/e2e_tests_log.txt)
- **Voie B Proofs**:
  - **Static Files Header**: [static_check_headers.txt](file:///home/alaeddine/viatique__PMF/proofs/artifacts/static_check_headers.txt)
  - **Login Response**: [login_check_response.txt](file:///home/alaeddine/viatique__PMF/proofs/artifacts/login_check_response.txt)

---

## 3) Manual Smoke Checklist (Verification Protocol)
1. **Login**: Admin and Teacher logins successful. Cookies observed with `HttpOnly`.
2. **Dashboard**: Corrector dashboard lists seeded copies from `api/dev/seed`.
3. **Grading UI**: 
    - [x] Exercise with children disables manual points. 
    - [x] Deleting all children restores the manual point backup.
4. **Health**: `GET /api/health/` returns `200 OK` with DB connected.

---

## 4) GO / NO-GO Conclusion
**Decision**: ✅ **GO**
As Assistant Lead, I certify that this pack aligns code, proofs, and identity. Collisions on IDs are mitigated by `crypto.randomUUID()`. Branding is consistent. 

**Signed: Alaeddine BEN RHOUMA
