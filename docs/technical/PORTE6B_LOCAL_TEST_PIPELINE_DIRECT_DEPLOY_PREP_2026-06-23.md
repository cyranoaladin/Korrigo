# Porte 6B - Local test pipeline for direct deploy preparation

Date: 2026-06-23

## Strategic Decision

GitHub is no longer part of the Korrigo delivery path for this chantier.

The official delivery path is now local and direct:

1. serious local checks;
2. backend unit tests;
3. frontend tests;
4. local E2E or local HTTP smoke;
5. local commit;
6. local Docker build;
7. direct transfer to `nexus-prod`;
8. controlled direct deployment;
9. post-deployment verification.

No GitHub push, PR, workflow, GHCR operation, deployment, production restart, migration, prune, volume deletion, secret display, pepper display, PII display, or real email display is part of Porte 6B.

## Pipeline

New script:

```bash
scripts/release/local_release_check.sh <audit-dir>
```

The script writes logs and the release manifest into the provided audit directory. It stops at the first failing step and emits:

```text
LOCAL_RELEASE_CHECK_STATUS=PASS
```

or:

```text
LOCAL_RELEASE_CHECK_STATUS=FAIL
FAILED_STEP=<step>
```

The local pipeline runs:

- clean worktree check;
- `git diff --check`;
- HMAC PII gate on `frontend/src` with synthetic pepper;
- HMAC PII gate on existing `frontend/dist`, when present;
- fail-closed check with missing `PII_GATE_PEPPER`;
- redacted email classification;
- canonical Compose YAML validation;
- backend targeted tests;
- backend full test suite;
- frontend tests;
- Vite build;
- HMAC PII gate on rebuilt `frontend/dist`;
- E2E discovery;
- local smoke/E2E script.

## Local E2E / Smoke

New script:

```bash
scripts/release/local_smoke_e2e.sh <audit-dir>
```

The script does not touch production. It starts:

- a local Django backend on a temporary SQLite database under the audit directory;
- a local static frontend proxy serving `frontend/dist`;
- API proxying from the local frontend server to the local backend.

It checks these public routes locally:

- `/`;
- `/korrigo`;
- `/student/login`;
- `/admin/login`;
- `/api/health/`;
- `/api/csrf/`.

It also scans the locally served frontend assets with the HMAC PII gate and a generic email counter.

If an existing Playwright E2E script is available, the smoke script runs it against the local frontend URL. A release-ready E2E status requires:

- `PASS_EXISTING_PLAYWRIGHT_OR_CYPRESS`; or
- `PASS_LOCAL_HTTP_SMOKE`.

Public production smoke alone is not considered sufficient for a new direct release.

## Release Manifest

The pipeline creates:

```text
LOCAL_RELEASE_MANIFEST.md
```

inside the audit directory.

It records:

- HEAD;
- branch;
- baseline;
- backend targeted status;
- backend full status;
- frontend status;
- build status;
- HMAC gate status;
- email classification status;
- E2E status;
- final decision.

## Criteria For Direct Deploy Readiness

The pipeline may only produce `LOCAL_RELEASE_READY_FOR_DIRECT_DEPLOY` if:

- production preflight was healthy before running the pipeline;
- backup/sync guard passed before running the pipeline;
- local worktree is clean;
- backend targeted tests pass;
- backend full test suite passes;
- frontend tests pass;
- Vite build passes;
- HMAC PII gates pass on source and dist;
- missing pepper fails closed;
- email classification has no priority category;
- E2E/local smoke is acceptable;
- scripts and documentation are committed locally.

## Limitations

Real HMAC markers are still not active because the administrator input file and real pepper have not been provided. The gate mechanism is active and fail-closed, but real marker coverage still requires administrator regeneration outside the repository.

Existing Playwright tests may require seeded local data and browser availability. If they fail for environment reasons, the release must be blocked as `LOCAL_RELEASE_BLOCKED_E2E` until the local E2E path is made deterministic.

## Next Porte

If Porte 6B ends with `LOCAL_RELEASE_READY_FOR_DIRECT_DEPLOY`, the next porte is:

```text
Porte 6C - local Docker build, direct transfer, controlled direct deployment to nexus-prod
```

If it ends with `LOCAL_RELEASE_BLOCKED_E2E`, the next task is to make the local E2E path deterministic before any new deployment.
