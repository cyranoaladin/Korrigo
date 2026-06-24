# Porte 6B-FIX - E2E deterministic local release

Date UTC: 2026-06-24

## Context

Porte 6B created the local release pipeline used instead of GitHub CI. The pipeline was blocked by Playwright while the HTTP smoke, backend tests, frontend tests, Vite build, HMAC gates, and email classification were already passing.

The observed blocker was a local corrector login timeout waiting for `corrector-dashboard`. No deployment, Docker build, server transfer, GitHub action, push, or production restart was performed during this fix.

## Root Causes

Two independent E2E root causes were proven.

1. The local frontend proxy only implemented `GET` and `HEAD` for `/api/*`. Playwright login uses `POST /api/login/`, so the local proxy did not forward the login request and session cookies reliably.
2. After the proxy fix, Playwright advanced further and failed on the Direction flow because the local E2E seed did not create a Direction user matching the frontend E2E contract.
3. After Playwright passed in the full release pipeline, `local_release_check.sh` still failed because it parsed `LOCAL_SMOKE_E2E_STATUS=PASS` as if it were the final `E2E_STATUS`. The release gate now reads only lines starting with `E2E_STATUS=`.

Both failures were local pipeline defects, not production deployment issues.

## Corrections

- `scripts/release/local_smoke_e2e.sh`
  - Added `POST` proxying for `/api/*`.
  - Forwarded request body and relevant headers.
  - Forwarded response headers including repeated `Set-Cookie`.
  - Removed masking of `seed_e2e` failures.
  - Added deterministic E2E diagnostics in `E2E_DIAGNOSTIC.md`.
  - Added checks for teacher, admin, and Direction E2E users before Playwright.
  - Added a local login probe that verifies session cookie creation without printing credentials.

- `backend/core/management/commands/seed_e2e.py`
  - Added a synthetic Direction E2E account.
  - Added the expected Direction group assignment.
  - Kept seed data synthetic and idempotent.
  - Replaced the default student E2E email with a reserved-domain fixture.

- `frontend/tests/e2e/e2eEnv.ts`
  - Added Direction E2E username/password constants.
  - Kept defaults aligned with the local seed.

- `frontend/tests/e2e/authHelpers.ts`
  - Updated Direction login to use the central E2E contract.
  - Removed a hard-coded real-domain fallback.

- `frontend/tests/e2e/auth-flow.spec.ts`
  - Replaced the invalid-login email fixture with a reserved-domain address.

- `backend/core/tests/test_local_release_scripts_contract.py`
  - Added contract checks for deterministic release scripts.
  - Added checks forbidding destructive Docker/prod operations.
  - Added checks for Playwright as a hard gate.
  - Added checks for Direction seed/helper coverage.
  - Added a regression check for anchored `E2E_STATUS` parsing.

## Verification Probe

Probe audit directory:

`/tmp/korrigo_porte6b_fix_smoke_probe_20260624T052615Z`

Observed statuses:

- Local HTTP smoke: PASS
- Local public asset PII gate: PASS
- Local public asset email count: 0
- Teacher login probe: HTTP 200 with session cookie
- E2E users: teacher/admin/Direction present
- Playwright: PASS
- E2E status: `PASS_EXISTING_PLAYWRIGHT_OR_CYPRESS`

## Targeted Tests

Executed targeted checks before the full release pipeline:

- `bash -n scripts/release/local_release_check.sh scripts/release/local_smoke_e2e.sh`: PASS
- `git diff --check`: PASS
- `pytest -q -p no:cacheprovider backend/core/tests/test_local_release_scripts_contract.py backend/core/tests/test_prod_compose_contract.py backend/core/tests/test_lot0_rgpd_deploy_contract.py`: 35 passed
- Email classification:
  - `SECRET_LIKE=0`
  - `TO_REVIEW=0`
  - `PERSONAL_OR_UNKNOWN=0`

## Final Pipeline

A complete `scripts/release/local_release_check.sh` run was executed from a clean worktree after committing this fix.

Final statuses:

- `LOCAL_RELEASE_CHECK_STATUS=PASS`
- `E2E_STATUS=PASS_EXISTING_PLAYWRIGHT_OR_CYPRESS`
- Decision: `LOCAL_RELEASE_READY_FOR_DIRECT_DEPLOY`
- Audit artifact email scan: no non-reserved email remains after fixture sanitization.

Ready criteria satisfied:

- `LOCAL_RELEASE_CHECK_STATUS=PASS`
- `E2E_STATUS=PASS_EXISTING_PLAYWRIGHT_OR_CYPRESS`
- backend targeted tests PASS
- backend full tests PASS
- frontend tests PASS
- Vite build PASS
- HMAC source/dist gates PASS
- fail-closed HMAC gate PASS
- email classification has no priority categories
- local smoke PASS
- Playwright PASS

## Confirmations

- No GitHub push, PR, workflow, or GHCR action.
- No Docker build.
- No transfer to server.
- No deployment.
- No production restart.
- No production migration.
- No secret, pepper, real email, or PII intentionally displayed.
- No Playwright skip, fixme, only, artificial retry, or smoke-only bypass.

## Next Step

Only if the final local release check is fully green: Porte 6C, local Docker build, direct transfer to `nexus-prod`, and controlled direct deployment.
