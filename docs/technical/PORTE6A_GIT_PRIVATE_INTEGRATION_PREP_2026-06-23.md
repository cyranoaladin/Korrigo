# Porte 6A - Git private integration preparation

Date: 2026-06-23

## Context

Korrigo production is stabilized on runtime commit `1fc58d15d9050ce82077624e1b2d3d0e291fe083`.

Porte 5A reconciled the production server canonical Compose file with the Lot 0-G runtime images. Porte 5B migrated the anti-PII gate to HMAC with a non-committed pepper. Portes 5C and 5D reduced priority email exposure and sanitized historical migration fixtures.

No GitHub push, PR, workflow, GHCR operation, deployment, restart, migration, or Docker action was performed during Porte 6A.

## Local State

- Branch: `hotfix/lot0-rgpd-deploy-clean`
- Pre-Porte 6A HEAD: `10658860076f0cc4d11cf8f0f9cfc21a5ff659a2`
- Production baseline: `1958681b082402e06d0f463e685d8a9895c460c5`
- Baseline ancestry: `BASE_PROD_IS_ANCESTOR=YES`
- Commits since baseline before the Porte 6A commit: 17
- Files changed since baseline before the Porte 6A commit: 48

## Server State

- Production health: `{"status":"healthy","database":"connected"}`
- Compose mode observed: canonical Compose file only, no Lot 0-G override required
- Server audit directory: `/var/www/labomaths/korrigo_release/ops/porte6a_git_reconcile_20260623T201157Z`

Captured server artifacts:

- `docker-compose.prod.server.yml`
- `compose.canonical.server.yml`
- `docker_ps_server.txt`
- `health_server.json`
- Lot 0-G runbook and override snapshots when present

No `.env` file or secret-bearing file was copied.

## Compose Reconciliation

The local canonical Compose file was not yet aligned with the server canonical Compose file. It still referenced the previous GHCR images for the application services.

The local file `infra/docker/docker-compose.prod.yml` was updated to match the production server file. The diff is limited to the `image:` field for these services:

- `backend`
- `celery`
- `celery-beat`
- `nginx`

Unchanged:

- `db`
- `redis`
- volumes
- networks
- environment configuration
- ports
- commands
- healthchecks
- dependencies

Effective images after reconciliation:

- `backend`: `korrigo-backend:korrigo-lot0g-direct-1fc58d1`
- `celery`: `korrigo-backend:korrigo-lot0g-direct-1fc58d1`
- `celery-beat`: `korrigo-backend:korrigo-lot0g-direct-1fc58d1`
- `nginx`: `korrigo-nginx:korrigo-lot0g-direct-1fc58d1`
- `db`: `postgres:15-alpine`
- `redis`: `redis:7-alpine`

After the local edit, the local Compose file matched the server Compose file exactly.

## Security Audit

Diff audit from production baseline:

- `SECRET_WORD_COUNT=123`
- `EMAIL_TOTAL_IN_DIFF=138`
- `EMAIL_NON_RESERVED_COUNT=84`
- `EMAIL_NON_RESERVED_DOMAIN_COUNT=10`

These counts were not printed with values. The email classifier was run separately and reported no priority categories:

- `EMAIL_CLASSIFICATION_FILE_COUNT=100`
- `EMAIL_CLASSIFICATION_TOTAL_OCCURRENCES=453`
- `EMAIL_CATEGORY_DOC_EXAMPLE=9`
- `EMAIL_CATEGORY_PUBLIC_INSTITUTIONAL=69`
- `EMAIL_CATEGORY_SANITIZED_MIGRATION_FIXTURE=19`
- `EMAIL_CATEGORY_TEST_FIXTURE=356`
- Priority categories: 0

HMAC gate state:

- `DENY_HASHES_PRESENT=False`
- `DENY_HMAC_HEX_COUNT=0`
- `NEEDS_ADMIN_REGENERATION_PRESENT=True`

The HMAC mechanism is present, but real markers still require administrator-provided input values and a non-committed pepper.

## Verification

Executed locally:

- `git diff --check`: passed
- HMAC gate on `frontend/src` with synthetic pepper: `PII_GATE_STATUS=PASS`, `PII_HASH_MATCH_COUNT=0`
- HMAC gate on `frontend/dist` with synthetic pepper: `PII_GATE_STATUS=PASS`, `PII_HASH_MATCH_COUNT=0`
- HMAC gate without pepper: `PII_GATE_STATUS=FAIL_MISSING_PEPPER`
- redacted email classification: no `SECRET_LIKE`, `TO_REVIEW`, or `PERSONAL_OR_UNKNOWN`
- YAML parse of `infra/docker/docker-compose.prod.yml`: passed

## Artifacts

The final bundle and patches are generated after the Porte 6A local commit so that they represent the final local HEAD.

Expected artifact contents:

- `commits_since_prod.txt`
- `diffstat_since_prod.txt`
- `name_status_since_prod.txt`
- `patches/`
- `korrigo_hotfix_since_prod.bundle`
- `SHA256SUMS.txt`

The artifact directory is under `/tmp` and is not published.

## Decision

Decision: `GIT_INTEGRATION_READY_PRIVATE_ONLY`

The local branch is suitable for private, human-reviewed integration preparation only. It must not be pushed to the current public GitHub repository.

## Conditions Before Any Future Push

- The target repository must be private, or a new private remote must be used.
- CI must be controlled or explicitly disabled until it is safe.
- If CI is enabled, `PII_GATE_PEPPER` must be configured as a secret in the private CI environment.
- Human review must validate the generated patches and bundle before push.
- No push to a public repository.

## Residual Risks

- Real HMAC markers are still blocked pending administrator-provided source values and pepper.
- GitHub/main remains historically misaligned and public.
- CI cannot be trusted for this chantier until reconfigured in a private context.
- `BilanBacBlanc.vue` remains a structural refactor debt.

## Next Step

Recommended next step: make GitHub private or create a new private remote, then integrate the generated bundle or patches after human review. Real HMAC marker activation should be completed before relying on the CI anti-PII gate for production-grade coverage.
