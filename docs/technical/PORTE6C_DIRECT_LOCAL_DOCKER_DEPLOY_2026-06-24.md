# Porte 6C - Direct local Docker deployment

Date UTC: 2026-06-24

## Context

GitHub is no longer used as a delivery path for Korrigo. Porte 6C deployed the locally validated release directly to `nexus-prod`.

Runtime commit deployed:

`f793f0c8248ae860be44c9972b6201e9f86babe4`

Release tag:

`korrigo-direct-f793f0c`

## Preflight

Local worktree was clean and on the expected HEAD before Docker build.

Pre-build local release audit:

`/tmp/korrigo_porte6c_prebuild_release_20260624T060252Z`

Results:

- `LOCAL_RELEASE_CHECK_STATUS=PASS`
- `E2E_STATUS=PASS_EXISTING_PLAYWRIGHT_OR_CYPRESS`
- backend targeted tests: PASS
- backend full tests: PASS
- frontend tests: PASS
- Vite build: PASS
- HMAC source/dist gates: PASS
- HMAC fail-closed: PASS
- email classification: PASS
- Playwright E2E: PASS

Production preflight before deployment:

- host: `korrigo`
- compose canonical only: OK
- public health: `{"status":"healthy","database":"connected"}`
- services healthy before bascule.

Backup/sync guard before deployment:

- latest encrypted backup: `20260624T041702Z`
- backup checksums: OK
- StorageBox sync dry-run: `WOULD_TRANSFER_COUNT=0`, `DELETE_COUNT=0`, `ERROR_WORD_COUNT=0`

## Audit Directories

Local audit directory:

`/tmp/korrigo_porte6c_direct_deploy_20260624T060700Z`

Server audit directory:

`/var/www/labomaths/korrigo_release/ops/porte6c_direct_deploy_20260624T060701Z`

## Images

Local image tags:

- `korrigo-backend:korrigo-direct-f793f0c`
- `korrigo-nginx:korrigo-direct-f793f0c`

Local image IDs:

- backend: `sha256:25b920ba7760d13ad68944abf877535da72b355cdaae47005ac053260fcd1f87`
- nginx: `sha256:92f2ba5f8d448bc7ce4ee5f95c442471ffed534a368573a4fc977d638c6da880`

OCI labels:

- `org.opencontainers.image.revision=f793f0c8248ae860be44c9972b6201e9f86babe4`
- `org.opencontainers.image.source=direct-local-korrigo-porte6c`
- `org.opencontainers.image.version=korrigo-direct-f793f0c`

The first backend Docker build attempt hit a transient PyPI/DNS resolution failure during `pip install`. Docker and host PyPI reachability were checked, the package version was confirmed available, and the backend build was retried successfully. The deployment did not proceed until both images were built and scanned.

## Image Scans

Nginx image extracted locally before transfer:

- HMAC PII gate: PASS
- `PII_HASH_MATCH_COUNT=0`
- `IMAGE_NGINX_EMAIL_FILE_COUNT=0`
- `IMAGE_NGINX_EMAIL_TOTAL_COUNT=0`

## Archives

Archive directory:

`/tmp/korrigo_porte6c_direct_deploy_20260624T060700Z/docker_images`

Checksums:

- backend archive: `69b6359d58ce7923ff515c8219e45b8f2a7989a5cb451afe3a8c973b85124afa`
- nginx archive: `31fb372ed785baade4c1fa86e24e7ecb20fc9445aa01b8b4bb012aec012b8223`

Server-side `sha256sum -c SHA256SUMS.txt`: OK.

## Transfer And Load

Archives were transferred directly to:

`/var/www/labomaths/korrigo_release/ops/porte6c_direct_deploy_20260624T060701Z/images`

No registry, GHCR, GitHub workflow, or remote Docker push was used.

Server images loaded:

- `korrigo-backend:korrigo-direct-f793f0c`
- `korrigo-nginx:korrigo-direct-f793f0c`

Server image labels match the expected Porte 6C revision/source/version.

## Bascule

Deployment override:

`/var/www/labomaths/korrigo_release/ops/porte6c_direct_deploy_20260624T060701Z/docker-compose.porte6c.override.yml`

Command used:

`docker compose ... up -d --no-deps backend celery celery-beat nginx`

Services recreated:

- `backend`
- `celery`
- `celery-beat`
- `nginx`

Not touched:

- `db`
- `redis`
- volumes
- networks

Production has `DJANGO_AUTO_MIGRATE=false` for backend/celery/celery-beat, so no automatic migration was run during service startup.

## Post-Deployment

Post-deployment services:

- `docker-backend-1`: `korrigo-backend:korrigo-direct-f793f0c`, healthy
- `docker-celery-1`: `korrigo-backend:korrigo-direct-f793f0c`, healthy
- `docker-celery-beat-1`: `korrigo-backend:korrigo-direct-f793f0c`, healthy
- `docker-nginx-1`: `korrigo-nginx:korrigo-direct-f793f0c`, healthy
- `docker-db-1`: unchanged, healthy
- `docker-redis-1`: unchanged, healthy

Health:

`{"status":"healthy","database":"connected"}`

Protected volumes verified present:

- `docker_postgres_data`
- `docker_media_volume`
- `docker_backup_volume`

## Public Bundle Scan

Served public assets downloaded from production:

- asset count: 2
- HMAC PII gate: PASS
- `PII_HASH_MATCH_COUNT=0`
- `PROD_ASSETS_EMAIL_FILE_COUNT=0`
- `PROD_ASSETS_EMAIL_TOTAL_COUNT=0`

## Public Smoke

Public routes checked:

- `/`: 200
- `/api/health/`: 200
- `/api/csrf/`: 200
- `/korrigo`: 200
- `/student/login`: 200
- `/admin/login`: 200

## Canonical Compose

After production was healthy on the Porte 6C images, server canonical compose was updated to point directly to:

- `korrigo-backend:korrigo-direct-f793f0c`
- `korrigo-nginx:korrigo-direct-f793f0c`

The server diff was verified as image-only. Local `infra/docker/docker-compose.prod.yml` was aligned with the same runtime tags and the local compose contract tests were updated.

## Rollback

Rollback state captured before bascule:

`/var/www/labomaths/korrigo_release/ops/porte6c_direct_deploy_20260624T060701Z/rollback_state_before.txt`

Rollback was not used.

## Post-Deployment Backup Guard

Post-deployment backup/sync check:

- latest encrypted backup: `20260624T101701Z`
- backup checksums: OK
- StorageBox sync dry-run: `WOULD_TRANSFER_COUNT=0`, `DELETE_COUNT=0`, `ERROR_WORD_COUNT=0`

## Confirmations

- No GitHub.
- No PR.
- No workflow.
- No GHCR.
- No registry push.
- No `docker compose down`.
- No `down -v`.
- No prune.
- No volume removal.
- No DB restart.
- No Redis restart.
- No production migration.
- No secret, pepper, `.env`, real email, or PII intentionally displayed.

## Verdict

`DIRECT_DEPLOY_DONE`

## Next Steps

Recommended:

1. Observe production for 24h.
2. Verify the next scheduled encrypted backup and StorageBox sync.
3. Later, clean obsolete Korrigo images only, with the same strict no-volume/no-prune-global policy.
4. Activate real HMAC markers when the admin input file and pepper are provided out of band.
