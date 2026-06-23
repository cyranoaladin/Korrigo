# Lot 0-K - Post-Cron Backup Observation

Date: 2026-06-23

## Context

Lot 0-I created encrypted local backups, restore testing, StorageBox sync v2, and cron activation.
Lot 0-J added anti-overlap locks, logrotate, stricter backup permissions, and a redacted legacy backup inventory.

This lot observes the first scheduled cron activity after those changes and decides whether Porte 4 Docker cleanup can begin.

Production runtime remains:

```text
1fc58d15d9050ce82077624e1b2d3d0e291fe083
```

## Observation Time

```text
Tue Jun 23 16:22:07 UTC 2026
```

At this time, the 16:17 UTC backup slot had already run, but the 16:47 UTC sync slot had not yet run.

## Cron Schedule

```cron
17 */6 * * * root /usr/local/bin/korrigo_backup_encrypted_v2.sh --run >> /var/log/korrigo_backup_encrypted_v2.log 2>&1
47 */6 * * * root /usr/local/bin/korrigo_sync_storagebox_v2.sh --run >> /var/log/korrigo_sync_storagebox_v2.log 2>&1
```

## Encrypted Backup Directories

Timestamp-only directory names:

```text
20260623T045552Z
20260623T101702Z
20260623T161702Z
```

The scheduled backup cron produced post-manual backups at 10:17 UTC and 16:17 UTC.

Latest backup:

```text
20260623T161702Z
```

Files in latest encrypted backup:

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

## Log Counts

Backup log:

```text
EMAIL_COUNT=0
POSSIBLE_DOB_FILENAME_COUNT=4
SECRET_WORD_COUNT=0
ERROR_COUNT=0
PASS_COUNT=3
SKIP_LOCKED_COUNT=0
```

The DOB-like matches are caused by timestamp strings in backup directory paths logged by the v2 script. No legacy filename listing was printed in this lot. The counter is nevertheless not zero, so this remains a conservative blocker for Porte 4 until the logs are made timestamp-neutral or the check is refined.

Sync log:

```text
EMAIL_COUNT=0
POSSIBLE_DOB_FILENAME_COUNT=0
SECRET_WORD_COUNT=0
ERROR_COUNT=0
PASS_COUNT=2
SKIP_LOCKED_COUNT=0
```

## StorageBox Dry-Run

Post-cron sync dry-run:

```text
WOULD_TRANSFER_COUNT=6
DELETE_COUNT=0
ERROR_WORD_COUNT=0
```

The dry-run still shows the 16:17 UTC encrypted backup waiting to transfer. This is expected because the observation occurred before the 16:47 UTC sync slot, but it means the remote state is not yet fully caught up at observation time.

No deletion was proposed.

## Scripts And Crons

Cron file:

```text
/etc/cron.d/korrigo_backup_encrypted_v2
```

Script locks:

```text
BACKUP_FLOCK_COUNT=1
SYNC_FLOCK_COUNT=1
```

Script permissions:

```text
-rwxr-x--- root:root /usr/local/bin/korrigo_backup_encrypted_v2.sh
-rwxr-x--- root:root /usr/local/bin/korrigo_sync_storagebox_v2.sh
```

## Backup Permissions

```text
/var/backups/korrigo: drwx------ root:root
GROUP_OR_WORLD_READABLE_FILES=0
LEGACY_INVENTORY_FILES_COUNT=2
ENCRYPTED_BACKUP_DIR_COUNT=3
aggregate size: 14G
```

No legacy backup file names were displayed.

## Production Health

Production health remained:

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

## Decision

```text
WAIT_NEXT_CRON_CYCLE
```

Reasons:

- a new backup was produced by cron and its checksums are valid;
- the latest backup had not yet reached the scheduled sync slot at observation time;
- StorageBox dry-run showed remaining transfers;
- DOB-like log count was non-zero due timestamp strings, so the current strict gate is not green.

Porte 4 Docker cleanup should not start until:

- the next sync slot has run;
- StorageBox dry-run reports no remaining transfer;
- log scans are clean or timestamp false positives are explicitly eliminated.

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

Observe again after the 16:47 UTC sync slot, or after the next complete backup-plus-sync pair. The next observation should verify:

- latest encrypted backup checksums;
- `WOULD_TRANSFER_COUNT=0`;
- `DELETE_COUNT=0`;
- `ERROR_WORD_COUNT=0`;
- no secret or PII indicators in logs;
- production health still OK.

If all pass, produce `GO_PREP_PORTE_4` for strict Korrigo Docker cleanup.
