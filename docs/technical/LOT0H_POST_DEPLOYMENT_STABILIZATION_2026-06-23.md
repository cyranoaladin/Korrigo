# Lot 0-H - Post-Deployment Stabilization

Date: 2026-06-23

## Context

Lot 0-G was deployed successfully by direct Docker image transfer, without GitHub, GHCR, CI, PR, or workflow execution.

Runtime currently deployed:

```text
1fc58d15d9050ce82077624e1b2d3d0e291fe083
```

Expected runtime images:

```text
backend/celery/celery-beat: korrigo-backend:korrigo-lot0g-direct-1fc58d1
nginx: korrigo-nginx:korrigo-lot0g-direct-1fc58d1
```

GitHub remains intentionally out of the deployment path for this lot.

## Stabilization Problem

Lot 0-G initially used a temporary Compose override:

```text
/tmp/korrigo-lot0g.override.yml
```

That was operationally fragile. A future Compose command without the override could recreate the application services from the canonical compose images, returning Korrigo to the previous GHCR images.

Lot 0-H therefore persists the runtime override and runbook under the deployed Korrigo release directory.

## Post-Deployment Verification

Server:

```text
hostname: korrigo
date: Mon Jun 22 23:34:20 UTC 2026
disk: /dev/md2 929G used 729G available 153G use 83%
```

Public health:

```json
{"status":"healthy","database":"connected"}
```

Services with the Lot 0-G runtime:

```text
docker-backend-1 healthy
docker-celery-1 healthy
docker-celery-beat-1 healthy
docker-nginx-1 healthy
docker-db-1 healthy
docker-redis-1 healthy
```

Application images and OCI labels:

```text
docker-backend-1: korrigo-backend:korrigo-lot0g-direct-1fc58d1
docker-celery-1: korrigo-backend:korrigo-lot0g-direct-1fc58d1
docker-celery-beat-1: korrigo-backend:korrigo-lot0g-direct-1fc58d1
docker-nginx-1: korrigo-nginx:korrigo-lot0g-direct-1fc58d1
org.opencontainers.image.revision=1fc58d15d9050ce82077624e1b2d3d0e291fe083
```

Data services:

```text
docker-db-1 ID prefix: 54202b9d02f8
docker-redis-1 ID prefix: 8a8bf2b8e8cc
```

DB and Redis were not recreated.

## Persistent Override

Created on the server:

```text
/var/www/labomaths/korrigo_release/ops/lot0g/docker-compose.lot0g.override.yml
```

Logical content:

```yaml
services:
  backend:
    image: korrigo-backend:korrigo-lot0g-direct-1fc58d1
  celery:
    image: korrigo-backend:korrigo-lot0g-direct-1fc58d1
  celery-beat:
    image: korrigo-backend:korrigo-lot0g-direct-1fc58d1
  nginx:
    image: korrigo-nginx:korrigo-lot0g-direct-1fc58d1
```

Validation:

```text
PERSISTENT_OVERRIDE_CONFIG=PASS
```

No `up`, restart, or redeployment was performed while creating this persistent override.

## Persistent Runbook

Created on the server:

```text
/var/www/labomaths/korrigo_release/ops/lot0g/README_LOT0G_RUNTIME.md
```

The runbook documents:

- the deployed runtime commit;
- expected images;
- the required Compose override;
- safe status command;
- safe application restart command, only if needed;
- explicit prohibition of `docker compose down`, `down -v`, DB/Redis recreation, and volume removal;
- rollback inputs;
- backup location;
- residual risks.

Safe status command:

```bash
docker compose -p docker --env-file /var/www/labomaths/korrigo/.env \
  -f infra/docker/docker-compose.prod.yml \
  -f ops/lot0g/docker-compose.lot0g.override.yml \
  ps
```

Safe app restart command, only if needed:

```bash
docker compose -p docker --env-file /var/www/labomaths/korrigo/.env \
  -f infra/docker/docker-compose.prod.yml \
  -f ops/lot0g/docker-compose.lot0g.override.yml \
  up -d --no-deps backend celery celery-beat nginx
```

## Rollback Evidence

Rollback file persisted:

```text
/var/www/labomaths/korrigo_release/ops/lot0g/rollback_20260622T232515Z.txt
```

Source file:

```text
/tmp/korrigo_lot0g_rollback_20260622T232515Z.txt
```

Current runtime state file created:

```text
/var/www/labomaths/korrigo_release/ops/lot0g/runtime_state_after_lot0g.txt
```

Preferred rollback remains:

- use the canonical compose without the Lot 0-G override;
- recreate only `backend`, `celery`, `celery-beat`, and `nginx`;
- do not restore DB unless a separate data incident occurred.

## Persistent Override Verification

Non-destructive verification with the persistent override:

```text
docker-backend-1 healthy
docker-celery-1 healthy
docker-celery-beat-1 healthy
docker-nginx-1 healthy
docker-db-1 healthy
docker-redis-1 healthy
```

Public health remained:

```json
{"status":"healthy","database":"connected"}
```

## Public Bundle Scan

Assets served publicly:

```text
PUBLIC_ASSET_COUNT=2
/assets/index-CmXNboRS.js
/assets/index-Ct6RsnJX.css
```

Gate results:

```text
PII_HASH_MATCH_COUNT=0
PUBLIC_ASSETS_EMAIL_FILE_COUNT=0
PUBLIC_ASSETS_EMAIL_TOTAL_COUNT=0
```

## Backup Crons

Read-only audit result:

```text
root crontab: backup line still suspended with SUSPENDED_KORRIGO_BASCULE_20260621T075647Z
/etc/cron.d/korrigo_storagebox_sync: sync line still suspended with SUSPENDED_KORRIGO_BASCULE_20260621T075647Z
```

No cron was reactivated in Lot 0-H.

Next backup chantier:

- implement encrypted-at-rest backup output;
- prove restore;
- then reactivate the scheduled backup and StorageBox sync under controlled conditions.

## Temporary Artifacts

Read-only inventory:

```text
/tmp/korrigo-lot0g-images: 315M
  SHA256SUMS.txt
  korrigo-backend-korrigo-lot0g-direct-1fc58d1.tar.gz: 294M
  korrigo-nginx-korrigo-lot0g-direct-1fc58d1.tar.gz: 21M

/var/backups/korrigo/manual_lot0g_20260622T224607Z: 4.7M
  SHA256SUMS.txt
  db.sql.gz: 4.6M
  media_inventory.txt
```

No temporary artifact was deleted in this lot.

## Confirmations

- No GitHub push.
- No GitHub PR.
- No GitHub tag.
- No GitHub Actions workflow.
- No GHCR push.
- No new application deployment.
- No migration.
- No `docker compose down`.
- No `down -v`.
- No volume deletion.
- No Docker prune.
- No scheduled backup reactivation.
- No secret displayed.
- No `.env` displayed.
- No real PII displayed.
- No non-Korrigo project touched.

## Residual Risks

- Canonical compose still references the previous GHCR images; the persistent override is required until a controlled follow-up reconciles it.
- Scheduled backups remain suspended until encryption-at-rest and restore verification are corrected.
- The anti-PII gate should move to HMAC with a non-committed pepper.
- Emails outside the served frontend bundle still need classification.
- `BilanBacBlanc.vue` remains structurally too static and needs backend-backed refactoring.
- `origin/main` remains misaligned with production.
- Existing Ruff, npm audit, and frontend lint warning debt remains.
- Docker image/build-cache cleanup remains for Porte 4, strictly within Korrigo scope.

## Recommended Next Step

Recommended order:

1. Lot 0-I: encrypted backups and controlled backup/sync reactivation.
2. Porte 4: strict Korrigo-only Docker cleanup.
3. Porte 5: HMAC/pepper for the anti-PII gate and classification of emails outside the bundle.
4. Portes 6/7: backend-backed bilan refactor, including `BilanBacBlanc.vue`.
