# Porte 6G - Post Repair Backup Sync Observation

Date: 2026-06-24

## Context

Porte 6F repaired the unique technical copy that was `FINALIZED` without a `final_pdf`.

Porte 6G locks that repair by verifying:

- repair persistence;
- global integrity audit;
- logs strictly after repair;
- encrypted backup after repair;
- StorageBox synchronization;
- public health and smoke.

No GitHub, build, deployment, restart, SQL, migration, prune, deletion, or Docker cleanup was performed.

## Preflight

Local state:

- branch: `hotfix/lot0-rgpd-deploy-clean`
- HEAD before documentation: `57789a9dbb802105221a8039f0d205e7c51c6554`
- worktree clean before Porte 6G documentation

Production:

- host: `korrigo`
- disk `/`: 78% used
- health: `{"status":"healthy","database":"connected"}`
- backend/celery/celery-beat: `korrigo-backend:korrigo-direct-c38a586`
- nginx: `korrigo-nginx:korrigo-direct-f793f0c`
- DB/Redis: healthy

Server audit directory:

`/var/www/labomaths/korrigo_release/ops/porte6g_post_repair_lock_20260624T124002Z`

## Repair Persistence

Target technical state:

- `copy_pk=744cb7ed-bbfb-4109-b46d-f93d17002a03`
- `exam_pk=de96412e-8504-4929-abf1-89247df98775`
- `status=FINALIZED`
- `has_final_pdf=True`
- `final_pdf_name_present=True`
- `final_pdf_size_positive=True`

No student name, email, anonymous id, media path, or copy content was displayed.

## Integrity Audit

Global audit:

- `GLOBAL_AUDIT_6G_RC=0`
- `EMAIL_COUNT=0`
- `STUDENT_EMAIL_KEY_COUNT=0`
- `ANONYMOUS_ID_KEY_COUNT=0`
- `FINALIZED_WITHOUT_FINAL_PDF_COUNT=0`
- `ISSUES_ZERO_COUNT=1`
- `AT_SIGN_COUNT=0`

The integrity audit reports no remaining issue.

## Logs

Strict post-repair window:

`LOG_SINCE=2026-06-24T12:31:30Z`

| Service | Email count | `student_email` key count | `anonymous_id` key count | Error-like count | Warning-like count |
| --- | ---: | ---: | ---: | ---: | ---: |
| `docker-backend-1` | 0 | 0 | 0 | 0 | 0 |
| `docker-celery-1` | 0 | 0 | 0 | 0 | 2 |
| `docker-celery-beat-1` | 0 | 0 | 0 | 0 | 0 |
| `docker-nginx-1` | 0 | 0 | 0 | 0 | 0 |

The Celery warning lines were checked in redacted form. They correspond to the integrity scan summary with `issues=0`, not a new anomaly.

## Backup Post-Repair

Manual encrypted backup was executed after the repair.

- marker: `PORTE6G_MANUAL_BACKUP_START_20260624T124211Z`
- `MANUAL_BACKUP_RC=0`
- latest encrypted backup: `20260624T124211Z`
- `db.sql.gz.gpg: OK`
- `media_inventory.txt.gpg: OK`
- `manifest.json: OK`

Timestamp validation:

- repair threshold: `20260624T122834Z`
- latest backup: `20260624T124211Z`
- `BACKUP_IS_AFTER_REPAIR=YES`

The initial helper pattern only accepted `13:00Z+`, which was too strict for a repair completed after `12:28Z`. The corrected comparison uses the actual repair threshold.

## StorageBox Sync

Manual sync after the backup:

- `MANUAL_SYNC_RC=0`
- `WOULD_TRANSFER_COUNT=0`
- `DELETE_COUNT=0`
- `ERROR_WORD_COUNT=0`

The StorageBox dry-run after sync showed no pending transfer, deletion, or error.

## Backup/Sync Log Safety

Recent backup/sync log counts:

| Log | Email count | Secret word count | Error-like count |
| --- | ---: | ---: | ---: |
| `/var/log/korrigo_backup_encrypted_v2.log` | 0 | 0 | 0 |
| `/var/log/korrigo_sync_storagebox_v2.log` | 0 | 0 | 0 |

No secret, pepper, password, token, email, or traceback was found in the checked log tails.

## Public Smoke

Public health:

`{"status":"healthy","database":"connected"}`

Smoke endpoints returned HTTP 200:

- `/`
- `/api/health/`
- `/api/csrf/`
- `/korrigo`
- `/student/login`
- `/admin/login`

## Confirmations

- No GitHub, push, PR, workflow, GHCR, or registry.
- No build.
- No deployment or application restart.
- No `docker compose up`, `docker compose down`, or `down -v`.
- No prune.
- No image, volume, or backup deletion.
- No migration.
- No SQL direct.
- No DB modification during Porte 6G.
- No Docker cleanup.
- No `.env`, secret, pepper, real email, student name, anonymous id, media path, or copy content displayed.

## Verdict

`POST_REPAIR_LOCK_DONE`

The data repair is now locked by a post-repair encrypted backup, successful StorageBox sync, clean integrity audit, clean public health, and clean post-repair log safety checks.

## Next Step

Observe for 24 hours:

- next scheduled copy integrity audit;
- next scheduled encrypted backup;
- next scheduled StorageBox sync.

Only after those observations remain clean should strict Korrigo-only Docker cleanup be considered.
