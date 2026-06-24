# Porte 6H-PREP - Finalisation preparation before automatic observation

Date: 2026-06-24

## Context

Porte 6F repaired the single technical copy that was `FINALIZED` without a final PDF.
Porte 6G locked the repair with a manual encrypted backup and manual StorageBox sync.
Portes 6H and 6H-B remained in `WAIT_NEXT_AUTOMATIC_CRON_OBSERVATION` because the automatic backup after `20260624T124211Z` had not yet been observed.

This preparation step does not close 6H-C and does not authorize Docker cleanup.

## Already Validated

- Repair state persisted after Porte 6F.
- Global copy integrity audit returned `issues=0`.
- Planned Celery integrity audit was observed with `issues=0`.
- Manual post-repair encrypted backup exists: `20260624T124211Z`.
- Manual post-repair StorageBox sync completed and dry-run returned zero pending transfer.
- Application logs were clean after repair.
- Backup and sync logs were clean in the prior observations.
- Public health and smoke checks were OK in the prior observations.

## Remaining Blocker

The final automatic observation still requires:

- an encrypted automatic backup newer than `20260624T124211Z`;
- checksum verification for that automatic backup;
- StorageBox dry-run at zero after that automatic backup;
- clean backup/sync logs after the automatic cycle;
- final 6H-C health, smoke, and log checks.

## Forbidden Before 6H-C

The following remain blocked before a clean 6H-C:

- Docker cleanup;
- image deletion;
- volume deletion;
- backup deletion;
- build;
- deployment;
- application restart;
- `docker compose up`;
- `docker compose down`;
- `down -v`;
- prune operations;
- migration;
- SQL or DB modification.

## Authorized Preparation

Only the following preparation is allowed:

- documentation;
- runbooks;
- read-only inventory scripts;
- future cleanup checklist in dry-run form only;
- remaining debt registry.

## Verdict

`PREP_ONLY_DONE`

No production action was performed by this preparation step.
