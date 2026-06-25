# Porte 6H - Automatic observation after repair

Date: 2026-06-24

## Context

Porte 6F repaired the single finalized copy without `final_pdf`.
Porte 6G locked the repair with a manual encrypted backup and manual StorageBox sync.

This Porte 6H observes the automatic cycles after repair before any Docker cleanup.

No build, deployment, restart, SQL, migration, prune, deletion, or Docker cleanup was performed.

## Audit Scope

Server audit directory:

`/var/www/labomaths/korrigo_release/ops/porte6h_auto_observation_20260624T124949Z`

Production preflight:

- Host: `korrigo`
- Runtime backend/celery/celery-beat: `korrigo-backend:korrigo-direct-c38a586`
- Runtime nginx: `korrigo-nginx:korrigo-direct-f793f0c`
- Public health: OK
- Six Korrigo services: healthy
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

Manual integrity audit:

- `GLOBAL_AUDIT_6H_RC=0`
- `EMAIL_COUNT=0`
- `STUDENT_EMAIL_KEY_COUNT=0`
- `ANONYMOUS_ID_KEY_COUNT=0`
- `FINALIZED_WITHOUT_FINAL_PDF_COUNT=0`
- `ISSUES_ZERO_COUNT=1`
- `AT_SIGN_COUNT=0`

The repair remains valid and the audit output is redacted.

## Planned Integrity Audit

Celery logs since `2026-06-24T12:31:30Z` show an automatic integrity run after repair:

- `CELERY_INTEGRITY_RUN_COUNT=1`
- `CELERY_INTEGRITY_ISSUES_ZERO_COUNT=1`
- `CELERY_INTEGRITY_ISSUE_POSITIVE_COUNT=0`
- `CELERY_COPY_AUDIT_ERROR_COUNT=0`
- `CELERY_EMAIL_COUNT=0`
- `CELERY_STUDENT_EMAIL_KEY_COUNT=0`
- `CELERY_ANONYMOUS_ID_KEY_COUNT=0`
- `CELERY_ERROR_LIKE_COUNT=0`

## Automatic Backup Observation

Manual Porte 6G backup:

- `MANUAL_BACKUP_6G=20260624T124211Z`

Latest encrypted backup during Porte 6H:

- `LATEST_ENCRYPTED_BACKUP=20260624T124211Z`
- `AUTOMATIC_BACKUP_AFTER_MANUAL_6G=NO`

Checksums for the latest backup are OK:

- `db.sql.gz.gpg: OK`
- `media_inventory.txt.gpg: OK`
- `manifest.json: OK`

The next automatic backup cycle had not yet passed at the time of observation, so the 24h automatic observation cannot be closed.

## StorageBox Sync

Dry-run after the latest backup:

- `WOULD_TRANSFER_COUNT=0`
- `DELETE_COUNT=0`
- `ERROR_WORD_COUNT=0`

Backup/sync log safety over recent tails:

- Backup log: `EMAIL_COUNT=0`, `SECRET_WORD_COUNT=0`, `ERROR_LIKE_COUNT=0`
- Sync log: `EMAIL_COUNT=0`, `SECRET_WORD_COUNT=0`, `ERROR_LIKE_COUNT=0`

## Application Logs

Application logs since `2026-06-24T12:42:11Z`:

- `docker-backend-1`: email 0, `student_email` 0, `anonymous_id` 0, errors 0, warnings 0
- `docker-celery-1`: email 0, `student_email` 0, `anonymous_id` 0, errors 0, warnings 0
- `docker-celery-beat-1`: email 0, `student_email` 0, `anonymous_id` 0, errors 0, warnings 0
- `docker-nginx-1`: email 0, `student_email` 0, `anonymous_id` 0, errors 0, warnings 0

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

All observed controls are clean, including the planned integrity audit and StorageBox dry-run. The remaining missing condition is an automatic encrypted backup after `20260624T124211Z`, followed by its automatic or observed sync verification.

Expected next automatic backup/sync window: backup at the next scheduled `HH:17 UTC` slot and sync at the corresponding `HH:47 UTC` slot.

## Confirmations

- No GitHub.
- No build.
- No deployment.
- No restart.
- No SQL.
- No migration.
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

Wait for the next automatic backup and StorageBox sync cycle, then re-run the automatic observation gate. Docker cleanup remains blocked until the automatic backup/sync observation is clean.
