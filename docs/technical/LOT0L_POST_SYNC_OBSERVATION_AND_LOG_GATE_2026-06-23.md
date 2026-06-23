# Lot 0-L - Post-Sync Observation and Log Gate

Date: 2026-06-23

## Context

Lot 0-K ended with `WAIT_NEXT_CRON_CYCLE` because the backup cron had produced `20260623T161702Z`, but the observation happened before the following sync slot.

Lot 0-L verifies the post-sync state, fixes the timestamp false positive in backup logs, and decides whether Porte 4 Docker cleanup can start.

Production runtime remains:

```text
1fc58d15d9050ce82077624e1b2d3d0e291fe083
```

## Observation

Observation time:

```text
Tue Jun 23 16:38:00 UTC 2026
```

This was still before the 16:47 UTC sync slot for the 16:17 UTC backup.

Encrypted backup timestamp directories:

```text
20260623T045552Z
20260623T101702Z
20260623T161702Z
```

Latest encrypted backup:

```text
20260623T161702Z
```

Latest encrypted backup files:

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

## StorageBox Dry-Run

Post-observation dry-run:

```text
WOULD_TRANSFER_COUNT=6
DELETE_COUNT=0
ERROR_WORD_COUNT=0
```

The dry-run still had items to transfer for `20260623T161702Z`. This is expected because the 16:47 UTC sync slot had not yet occurred, but it blocks a Porte 4 GO in this lot.

## Log False Positive Correction

Cause:

- backup logs contained `backup_dir=/var/backups/.../YYYYMMDDTHHMMSSZ`;
- the compact timestamp triggered the strict DOB-like regex;
- this was not PII, but it prevented a clean log gate.

Action:

- added `LOT0L_LOG_GATE_START` markers to both v2 logs;
- modified `/usr/local/bin/korrigo_backup_encrypted_v2.sh` so future run logs no longer include `backup_dir=...`;
- new backup status lines use `backup_path_redacted=YES`.

Verification:

```text
LOCAL_BACKUP_DIR_LOG_COUNT=0
LOCAL_REDACTED_LOG_COUNT=2
```

Script verification:

```text
backup_dir= absent
backup_path_redacted present
```

Dry-run verification:

```text
KORRIGO_BACKUP_V2 status=DRY_RUN_PASS backup_root=/var/backups/korrigo/encrypted
```

## Logs After Marker

After fresh `LOT0L_LOG_GATE_START` marker:

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
PASS_COUNT=0
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

## Production Health

Production remained healthy:

```json
{"status":"healthy","database":"connected"}
```

Services remained healthy:

```text
docker-backend-1 healthy
docker-celery-1 healthy
docker-celery-beat-1 healthy
docker-nginx-1 healthy
docker-db-1 healthy
docker-redis-1 healthy
```

## Decision

```text
WAIT_NEXT_CRON_CYCLE
```

Reasons:

- production is healthy;
- latest encrypted backup checksum is OK;
- log false positives are corrected for future log entries;
- logs after marker are clean;
- but StorageBox dry-run still shows pending transfers because the observation happened before the sync slot.

Porte 4 Docker cleanup must wait until the next sync slot has run and dry-run shows:

```text
WOULD_TRANSFER_COUNT=0
DELETE_COUNT=0
ERROR_WORD_COUNT=0
```

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

Observe after the next sync slot. If the StorageBox dry-run reports no remaining transfer and production remains healthy, issue `GO_PREP_PORTE_4`.
