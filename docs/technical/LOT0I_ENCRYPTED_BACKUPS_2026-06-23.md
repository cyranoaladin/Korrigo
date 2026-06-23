# Lot 0-I - Encrypted Backups and Controlled Cron Reactivation

Date: 2026-06-23

## Context

Lot 0-G deployed the RGPD/deploy hotfix directly from local Docker images.
Lot 0-H stabilized the runtime with a persistent Compose override and runbook.

Production runtime:

```text
1fc58d15d9050ce82077624e1b2d3d0e291fe083
```

Expected application images:

```text
backend/celery/celery-beat: korrigo-backend:korrigo-lot0g-direct-1fc58d1
nginx: korrigo-nginx:korrigo-lot0g-direct-1fc58d1
```

The legacy Korrigo backup and StorageBox sync crons were suspended with:

```text
SUSPENDED_KORRIGO_BASCULE_20260621T075647Z
```

They were suspended because the prior backup chain contained cleartext backup artifacts and the StorageBox sync path was not proven for the encrypted workflow.

## Initial Audit

Read-only audit found:

- existing StorageBox helper scripts under `/usr/local/bin/korrigo*`;
- legacy Korrigo backup cron still commented in root crontab;
- legacy StorageBox sync cron still commented in `/etc/cron.d/korrigo_storagebox_sync`;
- existing `/var/backups/korrigo` tree containing legacy unencrypted backups and media artifacts.

No legacy artifact was deleted in this lot.

The required runtime variables were present through Docker Compose parsing:

```text
POSTGRES_DB_PRESENT=YES
POSTGRES_USER_PRESENT=YES
POSTGRES_PASSWORD_PRESENT=YES
BACKUP_GPG_PASSPHRASE_PRESENT=YES
REDIS_PASSWORD_PRESENT=YES
```

The `.env` file was never sourced as shell and was not displayed.

Docker Compose JSON support was verified:

```text
Docker Compose version v5.1.0
COMPOSE_JSON_OK=YES
SERVICES=backend,celery,celery-beat,db,nginx,redis
```

## Backup Script V2

Created on the server:

```text
/usr/local/bin/korrigo_backup_encrypted_v2.sh
```

Modes:

```bash
/usr/local/bin/korrigo_backup_encrypted_v2.sh --dry-run
/usr/local/bin/korrigo_backup_encrypted_v2.sh --run
```

Properties:

- `set -euo pipefail`;
- no `.env` sourcing;
- secrets read through `docker compose config --format json`;
- no secret value printed;
- uses Compose project `docker`;
- includes the persistent Lot 0-G override;
- refuses to run without the persistent override;
- refuses to run without `BACKUP_GPG_PASSPHRASE`;
- checks public health before backup;
- checks DB connectivity before backup;
- writes to `/var/backups/korrigo/encrypted/YYYYMMDDTHHMMSSZ/`;
- stores encrypted outputs only;
- writes SHA256 checksums;
- writes a non-sensitive manifest;
- keeps a local retention limit of 14 encrypted v2 backup directories.

Dry-run result:

```text
KORRIGO_BACKUP_V2 status=DRY_RUN_PASS backup_root=/var/backups/korrigo/encrypted
```

## Backup Produced

Encrypted backup directory:

```text
/var/backups/korrigo/encrypted/20260623T045552Z
```

Files:

```text
SHA256SUMS.txt 250 bytes
db.sql.gz.gpg 4822913 bytes
manifest.json 344 bytes
media_inventory.txt.gpg 92 bytes
```

Checksum verification:

```text
db.sql.gz.gpg: OK
media_inventory.txt.gpg: OK
manifest.json: OK
```

No plaintext DB dump or plaintext media inventory was retained.

## Restore Test

Restore test method:

- created a temporary `postgres:15-alpine` container;
- did not publish host ports;
- did not touch `docker-db-1`;
- decrypted `db.sql.gz.gpg` into a pipe;
- restored into the temporary database;
- executed non-nominative validation queries;
- removed the temporary container.

Restore result:

```text
RESTORE_PG_READY=YES
RESTORE_TABLE_COUNT=46
RESTORE_EXAMS_COPY_EXISTS=t
RESTORE_EXAMS_COPY_COUNT=733
RESTORE_AUTH_USER_COUNT=771
RESTORE_MIGRATION_COUNT=113
RESTORE_TEMP_RESIDUAL_COUNT=0
RESTORE_TEST_RESULT=PASS
```

No personal data was displayed.

## StorageBox Sync V2

Created on the server:

```text
/usr/local/bin/korrigo_sync_storagebox_v2.sh
```

Modes:

```bash
/usr/local/bin/korrigo_sync_storagebox_v2.sh --dry-run
/usr/local/bin/korrigo_sync_storagebox_v2.sh --run
```

Properties:

- syncs only `/var/backups/korrigo/encrypted`;
- includes only directories, `.gpg`, `manifest.json`, and `SHA256SUMS.txt`;
- excludes all other files;
- verifies local checksums before transfer;
- uses rsync checksum mode;
- does not use `--delete`;
- verifies the remote copy after `--run` with `rsync --checksum --dry-run --itemize-changes`;
- never displays secrets.

Dry-run result:

```text
KORRIGO_SYNC_STORAGEBOX_V2 status=START mode=--dry-run backup_root=/var/backups/korrigo/encrypted
KORRIGO_SYNC_STORAGEBOX_V2 status=PASS mode=--dry-run
```

Run result:

```text
KORRIGO_SYNC_STORAGEBOX_V2 status=START mode=--run backup_root=/var/backups/korrigo/encrypted
KORRIGO_SYNC_STORAGEBOX_V2 status=PASS mode=--run
```

Remote deletion was not enabled.

## Crons

Created and activated:

```text
/etc/cron.d/korrigo_backup_encrypted_v2
```

Active schedules:

```cron
17 */6 * * * root /usr/local/bin/korrigo_backup_encrypted_v2.sh --run >> /var/log/korrigo_backup_encrypted_v2.log 2>&1
47 */6 * * * root /usr/local/bin/korrigo_sync_storagebox_v2.sh --run >> /var/log/korrigo_sync_storagebox_v2.log 2>&1
```

The legacy crons remain suspended:

```text
root crontab legacy backup line: still commented with SUSPENDED_KORRIGO_BASCULE_20260621T075647Z
/etc/cron.d/korrigo_storagebox_sync: still commented with SUSPENDED_KORRIGO_BASCULE_20260621T075647Z
```

## Logs

Log paths:

```text
/var/log/korrigo_backup_encrypted_v2.log
/var/log/korrigo_sync_storagebox_v2.log
```

Verification:

```text
korrigo_backup_encrypted_v2.log_EMAIL_COUNT=0
korrigo_sync_storagebox_v2.log_EMAIL_COUNT=0
```

The observed log tails contained operational status only and no secret values.

## Production Health

After Lot 0-I:

```text
docker-backend-1 healthy
docker-celery-1 healthy
docker-celery-beat-1 healthy
docker-nginx-1 healthy
docker-db-1 healthy
docker-redis-1 healthy
```

Public health:

```json
{"status":"healthy","database":"connected"}
```

## Confirmations

- No GitHub push.
- No PR.
- No GitHub workflow.
- No GHCR push.
- No application deployment.
- No application restart.
- No migration.
- No `docker compose down`.
- No `down -v`.
- No Docker prune.
- No volume deletion.
- No secret displayed.
- No `.env` displayed.
- No passphrase displayed.
- No real PII displayed intentionally.
- No non-Korrigo project modified.

## Residual Risks

- Legacy unencrypted backups remain in `/var/backups/korrigo`; they need a separate retention/remediation plan after the encrypted chain has run long enough.
- StorageBox retention/deletion remains disabled in v2 until a safe retention policy is tested.
- Regular automated restore tests should be scheduled later.
- Monitoring/alerting for missed backups is not yet implemented.
- Asymmetric encryption may be preferable long-term.
- Docker cleanup remains blocked until backup chain stability is observed.
- HMAC/pepper for the anti-PII gate remains open.
- Emails outside the served frontend bundle still need classification.

## Next Step

Recommended next step: observe the first scheduled v2 backup and sync execution, then proceed to Porte 4 Docker cleanup only if the scheduled backup and sync logs remain clean.

If StorageBox retention is required before Porte 4, create Lot 0-J for retention policy and remote verification.
