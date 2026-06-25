# Porte 6H-C - Automatic backup and sync observation

Date: 2026-06-24

## Context

Porte 6H-B ended with `WAIT_NEXT_AUTOMATIC_CRON_OBSERVATION` because it was executed before the expected automatic backup and sync cycle.

Expected cycle:

- Automatic encrypted backup: around `2026-06-24T18:17:00Z`
- Automatic StorageBox sync: around `2026-06-24T18:47:00Z`
- Observation close threshold: after `2026-06-24T18:50:00Z`

Manual Porte 6G backup:

- `MANUAL_BACKUP_6G=20260624T124211Z`

## Execution Time

This Porte 6H-C attempt was started at:

- Local UTC: `Wed Jun 24 13:07:15 UTC 2026`
- Server UTC: `Wed Jun 24 13:07:29 UTC 2026`

This is before `2026-06-24T18:50:00Z`, so the automatic backup and sync cycle could not be conclusively observed.

## Preflight

Read-only production preflight was healthy:

- Host: `korrigo`
- Backend/celery/celery-beat image: `korrigo-backend:korrigo-direct-c38a586`
- Nginx image: `korrigo-nginx:korrigo-direct-f793f0c`
- DB/Redis: healthy
- Public health: OK

## Checks Not Run

The following closing checks were intentionally not run because the required automatic cycle had not had time to pass:

- New server audit directory for completed 6H-C evidence
- Repair-state recheck
- Global integrity audit replay
- Planned integrity log recount
- Automatic backup comparison after `20260624T124211Z`
- StorageBox dry-run for the post-automatic-backup state
- Backup/sync log safety recount
- Application log recount
- Public smoke recount

The previous 6H-B evidence remains the latest full observation before this time-gated attempt.

## Verdict

`WAIT_NEXT_AUTOMATIC_CRON_OBSERVATION`

The gate is blocked only by time. No anomaly was observed in the read-only preflight, but `POST_REPAIR_24H_OBSERVATION_DONE` cannot be declared until after the automatic backup and sync window has passed and the corresponding evidence is collected.

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

Re-run Porte 6H-C after `2026-06-24T18:50:00Z` and verify:

- latest encrypted backup is greater than `20260624T124211Z`;
- backup checksums are OK;
- StorageBox dry-run is zero;
- backup/sync logs are clean;
- application logs are clean;
- production health and public smoke are OK.
