# Porte 6H-B - Automatic backup and sync observation

Date: 2026-06-24

## Context

Porte 6H ended with `WAIT_NEXT_AUTOMATIC_CRON_OBSERVATION` because the repair was clean but no automatic encrypted backup after the manual Porte 6G backup had yet been observed.

Manual Porte 6G backup:

- `MANUAL_BACKUP_6G=20260624T124211Z`

The expected automatic cycle is the `18:17 UTC` backup followed by the `18:47 UTC` StorageBox sync. This observation was executed before `2026-06-24T18:50:00Z`, so the automatic backup cycle was not expected to have completed yet.

No build, deployment, restart, SQL, migration, backup manual, sync manual, prune, deletion, or Docker cleanup was performed.

## Audit Scope

Server audit directory:

`/var/www/labomaths/korrigo_release/ops/porte6h_b_auto_observation_20260624T125852Z`

Production preflight:

- Host: `korrigo`
- Backend/celery/celery-beat image: `korrigo-backend:korrigo-direct-c38a586`
- Nginx image: `korrigo-nginx:korrigo-direct-f793f0c`
- Six Korrigo services: healthy
- Public health: OK
- Root filesystem: stable

## Repair Persistence

Target technical copy state remains repaired:

- `copy_pk=744cb7ed-bbfb-4109-b46d-f93d17002a03`
- `exam_pk=de96412e-8504-4929-abf1-89247df98775`
- `status=FINALIZED`
- `has_final_pdf=True`
- `final_pdf_name_present=True`
- `final_pdf_size_positive=True`

No student, email, anonymous id, media path, or copy content was displayed.

## Global Integrity Audit

Manual global audit:

- `GLOBAL_AUDIT_6HB_RC=0`
- `EMAIL_COUNT=0`
- `STUDENT_EMAIL_KEY_COUNT=0`
- `ANONYMOUS_ID_KEY_COUNT=0`
- `FINALIZED_WITHOUT_FINAL_PDF_COUNT=0`
- `ISSUES_ZERO_COUNT=1`
- `AT_SIGN_COUNT=0`

The audit is clean and the output contains no sensitive value.

## Planned Integrity Audit

Celery logs since `2026-06-24T12:31:30Z`:

- `CELERY_INTEGRITY_RUN_COUNT=2`
- `CELERY_INTEGRITY_ISSUES_ZERO_COUNT=2`
- `CELERY_INTEGRITY_ISSUE_POSITIVE_COUNT=0`
- `CELERY_COPY_AUDIT_ERROR_COUNT=0`
- `CELERY_EMAIL_COUNT=0`
- `CELERY_STUDENT_EMAIL_KEY_COUNT=0`
- `CELERY_ANONYMOUS_ID_KEY_COUNT=0`
- `CELERY_ERROR_LIKE_COUNT=0`

A redacted warning line was inspected and corresponds to:

- `Integrity scan completed: scanned=733 issues=0 repaired=0 issue_type_counts={}`

## Automatic Backup Observation

Latest encrypted backup during this observation:

- `LATEST_ENCRYPTED_BACKUP=20260624T124211Z`
- `MANUAL_BACKUP_6G=20260624T124211Z`
- `AUTOMATIC_BACKUP_AFTER_MANUAL_6G=NO`

Checksums for the latest backup are OK:

- `db.sql.gz.gpg: OK`
- `media_inventory.txt.gpg: OK`
- `manifest.json: OK`

The automatic backup after `20260624T124211Z` had not yet occurred at the time of observation.

## StorageBox Sync

StorageBox dry-run:

- `WOULD_TRANSFER_COUNT=0`
- `DELETE_COUNT=0`
- `ERROR_WORD_COUNT=0`

Because there is no automatic backup after the manual 6G backup yet, this proves the current latest backup is synchronized, but does not close the automatic post-repair observation.

## Backup and Sync Logs

Recent backup/sync log safety:

- Backup log: `EMAIL_COUNT=0`, `SECRET_WORD_COUNT=0`, `ERROR_LIKE_COUNT=0`
- Sync log: `EMAIL_COUNT=0`, `SECRET_WORD_COUNT=0`, `ERROR_LIKE_COUNT=0`

## Application Logs

Application logs since `2026-06-24T12:42:11Z`:

- `docker-backend-1`: email 0, `student_email` 0, `anonymous_id` 0, errors 0, warnings 0
- `docker-celery-1`: email 0, `student_email` 0, `anonymous_id` 0, errors 0, warnings 1
- `docker-celery-beat-1`: email 0, `student_email` 0, `anonymous_id` 0, errors 0, warnings 0
- `docker-nginx-1`: email 0, `student_email` 0, `anonymous_id` 0, errors 0, warnings 0

The single Celery warning is the expected integrity summary with `issues=0`, without PII.

## Public Smoke

Public endpoints checked:

- `/`: 200
- `/api/health/`: 200
- `/api/csrf/`: 200
- `/korrigo`: 200
- `/student/login`: 200
- `/admin/login`: 200

## Verdict

`WAIT_NEXT_AUTOMATIC_CRON_OBSERVATION`

All non-destructive checks are clean. The only missing condition is a new automatic encrypted backup after `20260624T124211Z`, followed by a StorageBox dry-run showing zero pending transfer.

## Confirmations

- No GitHub.
- No build.
- No deployment.
- No restart.
- No SQL.
- No migration.
- No manual backup.
- No manual sync.
- No `docker compose up`.
- No `docker compose down`.
- No prune.
- No Docker cleanup.
- No volume deletion.
- No backup deletion.
- No secret displayed.
- No PII displayed.
- No email displayed.
- No student name displayed.
- No anonymous id displayed.
- No media path displayed.

## Next Step

Wait until after the `2026-06-24T18:17:00Z` automatic backup and the `2026-06-24T18:47:00Z` automatic sync window, then re-run this observation. Docker cleanup remains blocked until that automatic cycle is clean.
