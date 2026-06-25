# Korrigo remaining blockers and debts

Date: 2026-06-24

## Blockers Before Docker Cleanup

- Porte 6H-C is not closed.
- Automatic encrypted backup newer than `20260624T124211Z` has not yet been observed.
- StorageBox sync after that automatic backup has not yet been validated.
- Docker cleanup is not authorized before those gates are green.

## Admin Debt Not Blocking Current Production

The HMAC PII gate mechanism exists, but real HMAC markers are not active because the admin inputs are missing:

- local non-committed input file with source values;
- `PII_GATE_PEPPER` provided outside the repository.

Do not invent a pepper. Do not commit source values. Do not store secrets in the repository.

## Debt Forbidden To Mask

- Do not treat the manual 6G backup as the required automatic backup observation.
- Do not treat a StorageBox dry-run at zero as proof of post-automatic-backup sync if no automatic backup exists yet.
- Do not authorize Docker cleanup before 6H-C.
- Do not remove old images before rollback and active runtime protection are verified.

## Current Stable Runtime

- Backend/celery/celery-beat: `korrigo-backend:korrigo-direct-c38a586`
- Nginx: `korrigo-nginx:korrigo-direct-f793f0c`

## Required Next Gate

Run Porte 6H-C after `2026-06-24T18:50:00Z`.
