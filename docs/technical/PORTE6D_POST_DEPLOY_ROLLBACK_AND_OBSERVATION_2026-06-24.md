# Porte 6D - Post Deploy Rollback And Observation

Date: 2026-06-24

## Context

Porte 6C completed with `DIRECT_DEPLOY_DONE`.

Active runtime:

- Git commit: `f793f0c8248ae860be44c9972b6201e9f86babe4`
- Backend image: `korrigo-backend:korrigo-direct-f793f0c`
- Nginx image: `korrigo-nginx:korrigo-direct-f793f0c`
- Delivery path: local checks, local Docker build, direct transfer, controlled Compose deployment
- GitHub/GHCR: not used

Porte 6D did not redeploy, restart, migrate, prune, delete images, delete backups, or touch DB/Redis.

## Current Production State

Server audit directory:

`/var/www/labomaths/korrigo_release/ops/porte6d_post_deploy_lock_20260624T113708Z`

Production health during Porte 6D:

`{"status":"healthy","database":"connected"}`

Canonical Compose alone was used for status checks. The active application services were on:

- `korrigo-backend:korrigo-direct-f793f0c`
- `korrigo-nginx:korrigo-direct-f793f0c`

OCI labels were verified on the active images:

- `org.opencontainers.image.revision=f793f0c8248ae860be44c9972b6201e9f86babe4`
- `org.opencontainers.image.source=direct-local-korrigo-porte6c`
- `org.opencontainers.image.version=korrigo-direct-f793f0c`

DB and Redis remained on their existing containers:

- `docker-db-1`: present and healthy
- `docker-redis-1`: present and healthy

Protected volumes were present:

- `docker_postgres_data`
- `docker_media_volume`
- `docker_backup_volume`

## Rollback

Rollback state from Porte 6C is present:

`/var/www/labomaths/korrigo_release/ops/porte6c_direct_deploy_20260624T060701Z/rollback_state_before.txt`

Rollback images were verified as present:

- `korrigo-backend:korrigo-lot0g-direct-1fc58d1`
- `korrigo-nginx:korrigo-lot0g-direct-1fc58d1`

A ready-to-use rollback override was created and validated with `docker compose config --quiet`:

`/var/www/labomaths/korrigo_release/ops/porte6d_post_deploy_lock_20260624T113708Z/docker-compose.rollback-pre-porte6c.override.yml`

Rollback was not executed.

## Active Release Manifest

The active release manifest was written on the server:

`/var/www/labomaths/korrigo_release/ops/ACTIVE_RELEASE.md`

It records the active runtime, canonical Compose path, rollback state, rollback override, and rollback command. It contains no secrets.

## Logs Since Deployment

Logs were observed since `2026-06-24T06:00:00Z`.

Counts:

| Service | Email count | Error-like count | Warning-like count |
| --- | ---: | ---: | ---: |
| `docker-backend-1` | 0 | 0 | 0 |
| `docker-celery-1` | 2 | 4 | 4 |
| `docker-celery-beat-1` | 0 | 0 | 0 |
| `docker-nginx-1` | 0 | 0 | 0 |

The Celery signal is blocking for a clean post-deploy lock:

- the scheduled copy integrity audit repeatedly reported a finalized copy without a final PDF;
- the task logged redacted `student_email` occurrences;
- no real email or PII was recorded in this document.

This requires a follow-up before cleanup or further evolution:

- redact or remove email fields from copy integrity audit logs;
- triage the finalized-copy-without-final-PDF data issue without exposing student data;
- re-observe logs after the correction.

## Public Bundle

Local audit directory:

`/tmp/korrigo_porte6d_post_deploy_20260624T113926Z`

Public assets:

- `PROD_PUBLIC_ASSET_COUNT=2`
- `PII_GATE_STATUS=PASS`
- `PII_HASH_MATCH_COUNT=0`
- `PROD_ASSETS_EMAIL_FILE_COUNT=0`
- `PROD_ASSETS_EMAIL_TOTAL_COUNT=0`

## Public Smoke

The public smoke endpoints returned HTTP 200:

- `/`
- `/api/health/`
- `/api/csrf/`
- `/korrigo`
- `/student/login`
- `/admin/login`

No HTTP 500 was observed in the smoke checks.

## Backup And Sync

Latest encrypted backup observed:

`20260624T101701Z`

Checksum verification:

- `db.sql.gz.gpg: OK`
- `media_inventory.txt.gpg: OK`
- `manifest.json: OK`

StorageBox dry-run after deployment:

- `WOULD_TRANSFER_COUNT=0`
- `DELETE_COUNT=0`
- `ERROR_WORD_COUNT=0`

## Local Pipeline After Deployment

The first post-deploy local release check exposed a stale local contract: `scripts/release/local_release_check.sh` still expected the pre-Porte 6C Lot 0-G image tags.

That local pipeline contract was corrected to expect:

- `korrigo-backend:korrigo-direct-f793f0c`
- `korrigo-nginx:korrigo-direct-f793f0c`

Targeted verification after the correction:

- `backend/core/tests/test_local_release_scripts_contract.py`: PASS
- `backend/core/tests/test_prod_compose_contract.py`: PASS
- `backend/core/tests/test_lot0_rgpd_deploy_contract.py`: PASS

Full local release check after committing the correction:

Audit directory:

`/tmp/korrigo_porte6d_local_release_check_20260624T114340Z`

Status:

- `LOCAL_RELEASE_CHECK_STATUS=PASS`
- `E2E_STATUS=PASS_EXISTING_PLAYWRIGHT_OR_CYPRESS`
- backend targeted tests: PASS
- backend full tests: PASS
- frontend tests: PASS
- Vite build: PASS
- HMAC source/dist gates: PASS
- fail-closed HMAC: PASS
- email classification: PASS
- Playwright E2E: PASS

## Confirmations

- No GitHub action was used.
- No push, PR, workflow, GHCR, or registry was used.
- No redeployment was performed in Porte 6D.
- No application restart was performed in Porte 6D.
- No `docker compose up` was run in Porte 6D.
- No `docker compose down` or `down -v` was run.
- No prune was run.
- No image, volume, backup, DB, or Redis deletion was performed.
- No migration was run.
- No `.env`, secret, pepper, real email, or PII was displayed.

## Verdict

`NO-GO_POST_DEPLOY`

Production is healthy and rollback is ready, but Porte 6D found a blocking Celery log signal after deployment:

- one repeated integrity audit issue;
- redacted email occurrences in Celery logs.

No cleanup, no Docker image removal, and no further functional evolution should start before that is corrected or explicitly triaged.

## Next Step

Recommended next porte:

`Porte 6E - copy integrity audit redaction and data issue triage`

Scope:

- remove or redact email output from integrity audit logs;
- investigate the finalized-copy-without-final-PDF issue without exposing student data;
- run the local pipeline;
- deploy directly only if an application code correction is required and the pipeline is fully green;
- observe logs again after correction.
