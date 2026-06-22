# Lot 0-G - Direct Deployment Without GitHub

Date: 2026-06-22

## Context

The Lot 0 RGPD/deploy hotfix could not be delivered through GitHub at this stage because:

- the repository `cyranoaladin/Korrigo` was public during review;
- GitHub CI/deploy workflows were not trusted as a deployment path for this chantier;
- `origin/main` was not aligned with the production baseline `1958681b082402e06d0f463e685d8a9895c460c5`, so a PR to `main` would not be an isolated hotfix.

The deployment was therefore performed directly with locally built Docker images, transferred to the production server and loaded locally. No GitHub push, PR, tag, workflow dispatch, GHCR push, or CI action was used.

## Runtime Commit

Deployed runtime commit:

```text
1fc58d15d9050ce82077624e1b2d3d0e291fe083
```

Production baseline before Lot 0-G:

```text
1958681b082402e06d0f463e685d8a9895c460c5
```

The local commit `0d779f984995ff3577cc09b581429c6052ab76b2` was documentation-only and was not used as the runtime image source.

## Diff Against Production Baseline

The runtime worktree was created detached at `1fc58d15d9050ce82077624e1b2d3d0e291fe083`.

Diff against `1958681b082402e06d0f463e685d8a9895c460c5`: 19 files.

Files changed:

- `.github/workflows/ci.yml`
- `.github/workflows/deploy.yml`
- `backend/core/tests/test_lot0_rgpd_deploy_contract.py`
- `backend/core/views.py`
- `docs/technical/LOT0B_RGPD_DEPLOY_HOTFIX_REVIEW_2026-06-22.md`
- `docs/technical/LOT0E_CLEAN_HOTFIX_BRANCH_STRATEGY_2026-06-22.md`
- `frontend/public/images/Korrigo.png`
- `frontend/src/components/Footer.vue`
- `frontend/src/components/stats/StatsQcmTab.vue`
- `frontend/src/components/stats/StatsQualityTab.vue`
- `frontend/src/views/BilanBacBlanc.vue`
- `frontend/src/views/DirectionConformite.vue`
- `frontend/src/views/ForgotPassword.vue`
- `frontend/src/views/GuideEtudiant.vue`
- `frontend/src/views/HomeView.vue`
- `frontend/src/views/admin/QuestionnaireBilan.vue`
- `frontend/src/views/admin/UserManagement.vue`
- `frontend/src/views/student/LoginStudent.vue`
- `scripts/ci/check_frontend_pii_hashes.py`

No `.env`, dump, backup, media file, migration, or unrelated Step 3 file was included.

## Local Verification

Runtime worktree:

```text
/tmp/korrigo-lot0g-runtime-1fc58d1
```

Executed checks:

- `git diff --check`: passed.
- `python scripts/ci/check_frontend_pii_hashes.py frontend/src`: `PII_HASH_MATCH_COUNT=0`.
- Frontend tests: 27 files, 334 tests passed.
- Frontend build: passed.
- Frontend lint: 0 errors, existing warnings only.
- Targeted backend contract tests: 14 passed.
- Backend full suite: 1004 passed, 1 skipped, 3 deselected.
- `python scripts/ci/check_frontend_pii_hashes.py frontend/dist`: `PII_HASH_MATCH_COUNT=0`.
- Generic email scan:
  - `frontend/src`: `EMAIL_FILE_COUNT=0`, `EMAIL_TOTAL_COUNT=0`
  - `frontend/dist`: `EMAIL_FILE_COUNT=0`, `EMAIL_TOTAL_COUNT=0`
  - `frontend/public`: `EMAIL_FILE_COUNT=0`, `EMAIL_TOTAL_COUNT=0`

`npm ci` in the temporary runtime worktree reported existing npm audit debt. It was not changed in this hotfix.

## Docker Images Built Locally

Tag:

```text
korrigo-lot0g-direct-1fc58d1
```

Backend image:

```text
korrigo-backend:korrigo-lot0g-direct-1fc58d1
local image id: sha256:db07b4ad167eb9917eec5f8a9cea58293da70a3e739f7927347899ef93e28082
server image id: sha256:6f08c27d903fdbc3042e3d9450aeea2cbfa8179d7918f52b2ef074fe8fd5dadf
```

Nginx image:

```text
korrigo-nginx:korrigo-lot0g-direct-1fc58d1
local image id: sha256:775ce6436d47531fec89bee61732a9d6f54e09e1550cb0391190689914a7ff0b
server image id: sha256:528a98863479bcbcc10c1eb4183fe16211c9b91fc342adadfd86ec765fad50f6
```

The server image IDs differ from the local Docker content-address IDs after `docker load`, but both loaded images carry the expected OCI label:

```text
org.opencontainers.image.revision=1fc58d15d9050ce82077624e1b2d3d0e291fe083
org.opencontainers.image.source=direct-local-korrigo-lot0g
org.opencontainers.image.version=korrigo-lot0g-direct-1fc58d1
```

The extracted nginx image assets were scanned before deployment:

```text
PII_HASH_MATCH_COUNT=0
IMAGE_NGINX_EMAIL_FILE_COUNT=0
IMAGE_NGINX_EMAIL_TOTAL_COUNT=0
```

## Image Archives

Local artifact directory:

```text
/tmp/korrigo-lot0g-artifacts
```

Archive sizes:

- backend archive: 294M
- nginx archive: 21M

Checksums:

```text
75a166f55da62a26914dd0aaa8f2e5948a03351299de7466e63751402eca4dda  korrigo-backend-korrigo-lot0g-direct-1fc58d1.tar.gz
68f43debde421ce9318131eb72b243f92dad2094f36a942c8d0563e8ca257b39  korrigo-nginx-korrigo-lot0g-direct-1fc58d1.tar.gz
```

The first checksum file used absolute local paths and failed on the server. It was replaced with a basename-only checksum file, then verified successfully on the server:

```text
korrigo-backend-korrigo-lot0g-direct-1fc58d1.tar.gz: OK
korrigo-nginx-korrigo-lot0g-direct-1fc58d1.tar.gz: OK
```

## Production Preflight

Server:

```text
ssh nexus-prod
hostname: korrigo
```

Disk before deployment:

```text
/dev/md2 929G used 728G available 154G use 83%
```

Pre-deployment health:

```json
{"status":"healthy","database":"connected"}
```

Pre-deployment production images:

- backend/celery/celery-beat: `ghcr.io/cyranoaladin/korrigo-backend@sha256:aafe75e7e4bc475f066ed57cc4b16dc816ea3497c70f3e8e954c5ba496929e1e`
- nginx: `ghcr.io/cyranoaladin/korrigo-nginx@sha256:5c4dda163f3ce4a4ff7e4a2b321adafb398cc3cdaa4461d708de89dabae0f61a`
- DB container ID prefix: `54202b9d02f8`
- Redis container ID prefix: `8a8bf2b8e8cc`

## Point-In-Time Backup

Manual backup directory:

```text
/var/backups/korrigo/manual_lot0g_20260622T224607Z
```

DB dump:

```text
db.sql.gz size: 4.6M
sha256: fb9b94398f2412982220b6cf30f020edbb3961fd38b2389071c70b2c3b936005
```

Media inventory:

```text
file count: 8528
size: 13.6G
```

No full media archive was created because this hotfix does not modify media or schema. The media volume remained mounted and untouched.

## Compose Override

Temporary override file on the server:

```text
/tmp/korrigo-lot0g.override.yml
```

It overrides only:

- `backend`
- `celery`
- `celery-beat`
- `nginx`

It does not override `db` or `redis`.

Configuration validation:

```text
COMPOSE_OVERRIDE_CONFIG=PASS
```

Deployment command used `docker compose -p docker` with the canonical production compose file plus the temporary override.

## Bascule

Rollback state file:

```text
/tmp/korrigo_lot0g_rollback_20260622T232515Z.txt
```

Services recreated:

- `docker-backend-1`
- `docker-celery-1`
- `docker-celery-beat-1`
- `docker-nginx-1`

Services not recreated:

- `docker-db-1`
- `docker-redis-1`

Post-deployment DB/Redis IDs:

```text
docker-db-1: 54202b9d02f8
docker-redis-1: 8a8bf2b8e8cc
```

They match the pre-deployment IDs.

Post-deployment services:

```text
docker-backend-1 healthy
docker-celery-1 healthy
docker-celery-beat-1 healthy
docker-nginx-1 healthy
docker-db-1 healthy
docker-redis-1 healthy
```

Post-deployment public health:

```json
{"status":"healthy","database":"connected"}
```

## Public Bundle Scan

Public assets fetched from `https://korrigo.labomaths.tn/`:

- `/assets/index-CmXNboRS.js`
- `/assets/index-Ct6RsnJX.css`

Scan result:

```text
PII_HASH_MATCH_COUNT=0
PUBLIC_ASSETS_EMAIL_FILE_COUNT=0
PUBLIC_ASSETS_EMAIL_TOTAL_COUNT=0
```

## Smoke Tests

Observed statuses:

```text
GET https://korrigo.labomaths.tn/api/health/ -> healthy JSON
HEAD https://korrigo.labomaths.tn/ -> 200
HEAD https://korrigo.labomaths.tn/api/csrf/ -> 200
HEAD https://korrigo.labomaths.tn/korrigo -> 200
HEAD https://korrigo.labomaths.tn/student/login -> 200
HEAD https://korrigo.labomaths.tn/admin/login -> 200
```

`HEAD /api/health/` returned 405, while `GET /api/health/` returned the expected healthy JSON. This is acceptable for the health endpoint contract.

## Rollback

Rollback was not used.

Available rollback inputs:

- previous app images from `/tmp/korrigo_lot0g_rollback_20260622T232515Z.txt`;
- canonical compose without the Lot 0-G override;
- DB dump at `/var/backups/korrigo/manual_lot0g_20260622T224607Z/db.sql.gz`.

The preferred application rollback is to recreate only `backend`, `celery`, `celery-beat`, and `nginx` from the canonical compose without the Lot 0-G override. DB restore is not expected to be necessary because Lot 0-G made no schema or data migration.

## Confirmations

- No GitHub push.
- No GitHub PR.
- No GitHub tag.
- No GitHub Actions workflow dispatch.
- No GHCR push.
- No Docker prune.
- No `down -v`.
- No volume deletion.
- No production DB migration.
- No secret displayed.
- No `.env` displayed.
- No real PII displayed.
- No action outside Korrigo services.

## Residual Risks

- The anti-PII gate still uses committed digest markers and should be moved to HMAC with a non-committed pepper.
- Emails outside the served frontend bundle still need classification.
- Scheduled backups were previously suspended and need to be resumed only after encryption-at-rest is corrected.
- `BilanBacBlanc.vue` remains structurally too static and needs a proper backend-backed refactor.
- `origin/main` remains misaligned with production.
- Existing frontend lint warnings and backend Ruff debt remain.
- Docker/image/build-cache cleanup remains for Porte 4, strictly in Korrigo scope.
- The Lot 0-G compose override is temporary. Future compose operations must either include `/tmp/korrigo-lot0g.override.yml` or the canonical compose must be updated through a controlled follow-up.
