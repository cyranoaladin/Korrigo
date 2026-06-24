# Korrigo production stabilisation index

Date: 2026-06-24

## Delivery Strategy

GitHub is not used as the delivery path.

Current delivery path:

1. local tests;
2. backend unit tests;
3. frontend tests;
4. Vite build;
5. security gates;
6. local Playwright E2E;
7. local commit;
8. local Docker build;
9. direct server transfer;
10. controlled compose deployment.

## Recent Gates

### Porte 6B-FIX

Made the local release pipeline deterministic with real Playwright E2E.

Verdict: `LOCAL_RELEASE_READY_FOR_DIRECT_DEPLOY`

### Porte 6C

Performed direct local Docker deployment.

Verdict: `DIRECT_DEPLOY_DONE`

### Porte 6D

Created rollback and post-deploy observation, then detected the integrity-audit logging issue.

Verdict: `NO-GO_POST_DEPLOY`

### Porte 6E

Redacted copy integrity audit logging and deployed the backend-only correction.

Verdict: `PORTE6E_DONE_DEPLOYED`

### Porte 6F

Repaired the single finalized copy missing a final PDF through the application command.

Verdict: `PORTE6F_DATA_REPAIR_DONE`

### Porte 6G

Created manual encrypted backup and manual StorageBox sync after the data repair.

Verdict: `POST_REPAIR_LOCK_DONE`

### Porte 6H

Observed repair, audit, logs, and sync, but automatic backup after the manual 6G backup had not happened yet.

Verdict: `WAIT_NEXT_AUTOMATIC_CRON_OBSERVATION`

### Porte 6H-B

Retried before the automatic backup/sync cycle had passed. All non-destructive checks were clean, but automatic backup was still missing.

Verdict: `WAIT_NEXT_AUTOMATIC_CRON_OBSERVATION`

### Porte 6H-C

Must be re-run after `2026-06-24T18:50:00Z`.

Required outcome before cleanup: `POST_REPAIR_24H_OBSERVATION_DONE`

### Porte 6I

Future strict Korrigo-only Docker cleanup.

Status: blocked until 6H-C is clean.

## Current Runtime

- Backend/celery/celery-beat: `korrigo-backend:korrigo-direct-c38a586`
- Nginx: `korrigo-nginx:korrigo-direct-f793f0c`

## Open Administrative Item

HMAC real markers remain blocked until the admin provides the non-committed input file and `PII_GATE_PEPPER` out of band.
