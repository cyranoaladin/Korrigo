# Lot 0-M - Final Backup Sync Gate Before Porte 4

Date: 2026-06-23

## Context

Lot 0-K and Lot 0-L were waiting for the StorageBox sync cron to catch up with the encrypted backup `20260623T161702Z`.

Lot 0-L also corrected the strict log gate false positive caused by compact timestamp paths in backup logs.

This lot performs the final pre-Porte 4 backup/sync gate. It does not execute Porte 4.

## Production Runtime

Runtime:

```text
1fc58d15d9050ce82077624e1b2d3d0e291fe083
```

Health:

```json
{"status":"healthy","database":"connected"}
```

Services:

```text
docker-backend-1 healthy
docker-celery-1 healthy
docker-celery-beat-1 healthy
docker-nginx-1 healthy
docker-db-1 healthy
docker-redis-1 healthy
```

Disk:

```text
/dev/md2 929G used 730G available 153G use 83%
```

## Observation

Observation time:

```text
Tue Jun 23 16:52:16 UTC 2026
```

Encrypted backup timestamp directories:

```text
20260623T045552Z
20260623T101702Z
20260623T161702Z
```

Sync log after Lot 0-L marker contains:

```text
KORRIGO_SYNC_STORAGEBOX_V2 status=START mode=--run backup_root=/var/backups/korrigo/encrypted
KORRIGO_SYNC_STORAGEBOX_V2 status=PASS mode=--run
```

## Latest Backup

Latest encrypted backup:

```text
20260623T161702Z
```

Files:

```text
SHA256SUMS.txt 250 bytes
db.sql.gz.gpg 4822913 bytes
manifest.json 344 bytes
media_inventory.txt.gpg 92 bytes
```

Checksums:

```text
db.sql.gz.gpg: OK
media_inventory.txt.gpg: OK
manifest.json: OK
```

## StorageBox Dry-Run

Post-sync checksum dry-run:

```text
WOULD_TRANSFER_COUNT=0
DELETE_COUNT=0
ERROR_WORD_COUNT=0
```

This proves the encrypted backup tree is caught up remotely without requiring remote deletion.

## Logs After Lot 0-L Marker

Backup log:

```text
EMAIL_COUNT=0
POSSIBLE_DOB_FILENAME_COUNT=0
SECRET_WORD_COUNT=0
ERROR_COUNT=0
PASS_COUNT=0
SKIP_LOCKED_COUNT=0
```

Sync log:

```text
EMAIL_COUNT=0
POSSIBLE_DOB_FILENAME_COUNT=0
SECRET_WORD_COUNT=0
ERROR_COUNT=0
PASS_COUNT=1
SKIP_LOCKED_COUNT=0
```

## Scripts, Crons, Permissions

Cron file:

```text
/etc/cron.d/korrigo_backup_encrypted_v2
```

Schedules:

```cron
17 */6 * * * root /usr/local/bin/korrigo_backup_encrypted_v2.sh --run >> /var/log/korrigo_backup_encrypted_v2.log 2>&1
47 */6 * * * root /usr/local/bin/korrigo_sync_storagebox_v2.sh --run >> /var/log/korrigo_sync_storagebox_v2.log 2>&1
```

Locks:

```text
BACKUP_FLOCK_COUNT=1
SYNC_FLOCK_COUNT=1
```

Backup log redaction:

```text
BACKUP_DIR_LOG_COUNT=0
BACKUP_PATH_REDACTED_COUNT=2
```

Script permissions:

```text
-rwxr-x--- root:root /usr/local/bin/korrigo_backup_encrypted_v2.sh
-rwxr-x--- root:root /usr/local/bin/korrigo_sync_storagebox_v2.sh
```

Backup root permissions:

```text
/var/backups/korrigo: drwx------ root:root
GROUP_OR_WORLD_READABLE_FILES=0
ENCRYPTED_BACKUP_DIR_COUNT=3
```

## Decision

```text
GO_PREP_PORTE_4
```

Rationale:

- production is healthy;
- latest encrypted backup checksums are OK;
- StorageBox dry-run reports no remaining transfer;
- no remote deletion is involved;
- logs after marker are clean;
- scripts have locks;
- backup log path timestamps are redacted for future runs;
- backup permissions are strict;
- no legacy backup filename was printed.

Porte 4 was not executed in this lot.

## Confirmations

- No GitHub push.
- No PR.
- No workflow.
- No GHCR.
- No deployment.
- No application restart.
- No migration.
- No `docker compose down`.
- No `down -v`.
- No Docker prune.
- No volume deletion.
- No backup deletion.
- No legacy backup deletion.
- No `.env` displayed.
- No secret displayed.
- No passphrase displayed.
- No intentional PII display.
- No non-Korrigo project modified.

## Next Step

Proceed to a dedicated Porte 4 prompt for strict Korrigo-only Docker cleanup.

The next lot must preserve:

- current Lot 0-G runtime images;
- rollback images required by the runbook;
- DB/Redis containers and volumes;
- encrypted backup chain and scripts;
- non-Korrigo containers, volumes, networks, images, and vhosts.
