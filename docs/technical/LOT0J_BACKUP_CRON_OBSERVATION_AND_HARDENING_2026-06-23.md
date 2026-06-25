# Lot 0-J - Backup Cron Observation and Hardening

Date: 2026-06-23

## Context

Lot 0-I created the encrypted backup chain:

- local encrypted backup script: `/usr/local/bin/korrigo_backup_encrypted_v2.sh`;
- encrypted StorageBox sync script: `/usr/local/bin/korrigo_sync_storagebox_v2.sh`;
- active cron file: `/etc/cron.d/korrigo_backup_encrypted_v2`;
- legacy Korrigo backup and sync crons still suspended with `SUSPENDED_KORRIGO_BASCULE_20260621T075647Z`.

Production runtime remains:

```text
1fc58d15d9050ce82077624e1b2d3d0e291fe083
```

## Cron Cycle Observation

Observation time:

```text
Tue Jun 23 05:39:21 UTC 2026
```

Active v2 schedules:

```cron
17 */6 * * * root /usr/local/bin/korrigo_backup_encrypted_v2.sh --run >> /var/log/korrigo_backup_encrypted_v2.log 2>&1
47 */6 * * * root /usr/local/bin/korrigo_sync_storagebox_v2.sh --run >> /var/log/korrigo_sync_storagebox_v2.log 2>&1
```

The first scheduled cycle had not yet occurred at observation time. The next expected scheduled backup was 06:17 UTC and the next expected scheduled sync was 06:47 UTC.

Decision:

```text
PENDING_FIRST_CRON_CYCLE
```

No manual backup run was triggered for this observation step.

## Log Scan

Log scan was performed by counts only, without printing sensitive lines.

```text
/var/log/korrigo_backup_encrypted_v2.log:
  EMAIL_COUNT=0
  POSSIBLE_DOB_FILENAME_COUNT=0
  SECRET_WORD_COUNT=0
  ERROR_COUNT=0

/var/log/korrigo_sync_storagebox_v2.log:
  EMAIL_COUNT=0
  POSSIBLE_DOB_FILENAME_COUNT=0
  SECRET_WORD_COUNT=0
  ERROR_COUNT=0
```

Observed tails contained operational status only.

## Methodology Incident Corrected

A previous legacy backup audit printed at least one path containing personal information embedded in a historical filename. Lot 0-J changes the rule for backup inventory:

- no recursive path listing under `/var/backups/korrigo`;
- no file names from legacy backups printed in reports;
- only aggregate counts, sizes, permissions, and extension summaries are allowed.

## Hardening Applied

### Anti-overlap Locks

Both v2 scripts now use `flock`.

Backup lock:

```text
/run/lock/korrigo_backup_encrypted_v2.lock
```

Sync lock:

```text
/run/lock/korrigo_sync_storagebox_v2.lock
```

If a lock is already held, the script exits cleanly:

```text
status=SKIP_LOCKED
```

Verification:

```text
BACKUP_FLOCK_COUNT=1
SYNC_FLOCK_COUNT=1
```

Dry-runs after lock insertion:

```text
KORRIGO_BACKUP_V2 status=DRY_RUN_PASS backup_root=/var/backups/korrigo/encrypted
KORRIGO_SYNC_STORAGEBOX_V2 status=START mode=--dry-run backup_root=/var/backups/korrigo/encrypted
KORRIGO_SYNC_STORAGEBOX_V2 status=PASS mode=--dry-run
```

### Logrotate

Created:

```text
/etc/logrotate.d/korrigo_backup_v2
```

Policy:

```text
weekly
rotate 8
compress
missingok
notifempty
create 0640 root adm
```

Validation was done with `logrotate -d`, which performs no real rotation.

### Backup Permissions

Before hardening:

```text
/var/backups/korrigo: drwxr-xr-x root:root
GROUP_OR_WORLD_READABLE_FILES=82
```

After hardening:

```text
/var/backups/korrigo: drwx------ root:root
GROUP_OR_WORLD_READABLE_FILES=0
```

No legacy backup was deleted.

## Redacted Legacy Inventory

Created:

```text
/var/backups/korrigo/legacy_plaintext_inventory_20260623T054229Z_redacted.txt
```

The inventory contains:

- top-level directory count;
- aggregate size;
- file count by extension;
- encrypted v2 directory count.

It does not contain legacy file names or full legacy paths.

Summary:

```text
Top-level directories count: 5
Aggregate size: 14G
Encrypted v2 directories count: 1
```

## Current Backup Evidence

Latest encrypted backup:

```text
/var/backups/korrigo/encrypted/20260623T045552Z
```

Checksum status:

```text
db.sql.gz.gpg: OK
media_inventory.txt.gpg: OK
manifest.json: OK
```

Restore test from Lot 0-I remains the latest restore proof:

```text
RESTORE_TEST_RESULT=PASS
```

## Production Health

Production remained healthy:

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

Porte 4 Docker cleanup should wait until the first scheduled cron cycle is observed.

Decision:

```text
WAIT_FIRST_CRON_CYCLE
```

Reasons:

- backup and sync scripts are proven manually;
- crons are active;
- but the first scheduled backup and scheduled sync had not yet run at observation time.

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
- No backup deletion.
- No legacy backup deletion.
- No `.env` displayed.
- No secret displayed.
- No passphrase displayed.
- No intentional PII display.
- No non-Korrigo project modified.

## Residual Risks

- First scheduled cron cycle still needs observation.
- Legacy cleartext backups remain stored, but are now permission-restricted.
- StorageBox remote retention/deletion remains disabled.
- Automated restore tests are not scheduled yet.
- Backup monitoring and alerting are not implemented yet.
- Docker cleanup Porte 4 remains pending.
- HMAC/pepper for the anti-PII gate remains pending.
- Emails outside the served frontend bundle still need classification.

## Next Step

Re-run Lot 0-J observation after 06:47 UTC, once both the scheduled backup and scheduled sync should have executed. If logs and checksums remain clean, proceed to Porte 4 Docker cleanup in strict Korrigo scope.
