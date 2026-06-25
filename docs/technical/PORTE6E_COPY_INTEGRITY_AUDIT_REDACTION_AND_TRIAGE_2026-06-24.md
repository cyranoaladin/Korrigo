# Porte 6E - Copy Integrity Audit Redaction And Triage

Date: 2026-06-24

## Context

Porte 6D ended with `NO-GO_POST_DEPLOY` although production was healthy.

Blocking signal:

- Celery repeatedly logged copy integrity audit issues;
- the audit detected a `FINALIZED` copy without a final PDF;
- the command output included `student_email` in the issue payload.

No cleanup, functional evolution, or Docker image removal is allowed until this signal is corrected or triaged.

## Root Cause

Code path:

- Celery task: `grading.tasks.run_copy_integrity_audit`
- Management command: `grading.management.commands.check_copy_integrity`

The management command built issue dictionaries containing non-essential sensitive fields, then wrote `str(issue)` to stdout. Celery captured that output.

Sensitive or unnecessary fields removed from command output:

- `student_email`
- student id;
- exam name;
- anonymous id;
- raw repair details that could include media paths or exception text.

## Logging Correction

The command now emits only non-sensitive technical fields:

- `issue_type`
- `copy_pk`
- `exam_pk`
- `status`
- `has_final_pdf`
- `repair_status` and `repair_reason` when relevant.

The summary now includes:

- `scanned`
- `issues`
- `repaired`
- `issue_type_counts`

The issue type for the observed anomaly is:

`FINALIZED_WITHOUT_FINAL_PDF`

## Tests

Added:

`backend/core/tests/test_copy_integrity_audit_logging.py`

The test verifies that a finalized copy without `final_pdf`:

- reports `scanned=1`;
- reports `issues=1`;
- reports `repaired=0`;
- reports `FINALIZED_WITHOUT_FINAL_PDF`;
- reports only technical ids and status;
- does not output `student_email`;
- does not output email values;
- does not output student first/last name;
- does not output anonymous id.

Red/green evidence:

- before the correction, the test failed because the output contained the old issue payload;
- after the correction, the test passed.

Targeted test run:

- `backend/core/tests/test_copy_integrity_audit_logging.py`: PASS
- `backend/core/tests/test_copy_integrity_command.py`: PASS
- `backend/core/tests/test_local_release_scripts_contract.py`: PASS
- `backend/core/tests/test_lot0_rgpd_deploy_contract.py`: PASS

## Data Triage

Production read-only diagnostics found:

- `FINALIZED_TOTAL=731`
- `FINALIZED_WITHOUT_FINAL_PDF_COUNT=1`
- `RELEASED_FINALIZED_WITHOUT_STUDENT_COUNT=0`

Affected technical ids:

- `copy_pk=744cb7ed-bbfb-4109-b46d-f93d17002a03`
- `exam_pk=de96412e-8504-4929-abf1-89247df98775`

Repair readiness:

- `booklet_count=1`
- `page_image_count=2`
- `existing_page_image_count=2`
- `missing_page_image_count=0`
- `has_pdf_source=True`
- `pdf_regeneration_pending=False`

No data repair was executed in Porte 6E.

Separate plan:

`docs/technical/PORTE6E_DATA_REPAIR_PLAN_FINALIZED_WITHOUT_PDF_2026-06-24.md`

## Deployment

The logging correction was deployed directly after the full local pipeline passed.

Release commit:

`c38a5861ddd64b2419521cde62e9290644aa2be3`

Backend image:

`korrigo-backend:korrigo-direct-c38a586`

Nginx was not rebuilt or recreated because no frontend/nginx asset changed.

Server audit directory:

`/var/www/labomaths/korrigo_release/ops/porte6e_direct_deploy_20260624T120550Z`

Local Docker audit directory:

`/tmp/korrigo_porte6e_direct_deploy_20260624T120549Z`

Services recreated:

- `backend`
- `celery`
- `celery-beat`

Services not recreated:

- `nginx`
- `db`
- `redis`

No migration was run.

The server canonical Compose file was reconciled after successful health checks:

- `backend`: `korrigo-backend:korrigo-direct-c38a586`
- `celery`: `korrigo-backend:korrigo-direct-c38a586`
- `celery-beat`: `korrigo-backend:korrigo-direct-c38a586`
- `nginx`: unchanged at `korrigo-nginx:korrigo-direct-f793f0c`

## Re-Observation

The integrity command was executed after deployment in read-only fail-on-issues mode.

Expected return code:

- `CHECK_COPY_INTEGRITY_RC=1`, because the bounded data issue still exists.

Redaction counts on the captured command output:

- `EMAIL_COUNT=0`
- `STUDENT_EMAIL_KEY_COUNT=0`
- `FINALIZED_WITHOUT_FINAL_PDF_COUNT=2`
- `RAW_PROBLEM_TEXT_COUNT=0`
- `ANONYMOUS_ID_KEY_COUNT=0`
- `AT_SIGN_COUNT=0`

The integrity issue is still correctly reported, but the output is non-sensitive.

Recent container log counts after the Porte 6E deployment:

| Service | Email count | `student_email` key count | Error-like count | Warning-like count |
| --- | ---: | ---: | ---: | ---: |
| `docker-backend-1` | 0 | 0 | 0 | 0 |
| `docker-celery-1` | 0 | 0 | 0 | 0 |
| `docker-celery-beat-1` | 0 | 0 | 0 | 0 |
| `docker-nginx-1` | 0 | 0 | 0 | 0 |

Public health after deployment:

`{"status":"healthy","database":"connected"}`

Public smoke returned HTTP 200 for:

- `/`
- `/api/health/`
- `/api/csrf/`
- `/korrigo`
- `/student/login`
- `/admin/login`

Backup/sync post-deployment:

- latest encrypted backup: `20260624T101701Z`
- backup checksums: OK
- `WOULD_TRANSFER_COUNT=0`
- `DELETE_COUNT=0`
- `ERROR_WORD_COUNT=0`

## Pipeline Local

Full local release check before build:

Audit directory:

`/tmp/korrigo_porte6e_local_release_check_20260624T120151Z`

Status:

- `LOCAL_RELEASE_CHECK_STATUS=PASS`
- `E2E_STATUS=PASS_EXISTING_PLAYWRIGHT_OR_CYPRESS`

## Confirmations

- No GitHub, push, PR, workflow, GHCR, or registry was used.
- No production migration was run.
- No DB write was performed during triage.
- No `docker compose down`, `down -v`, or prune was run.
- No volume or backup was removed.
- No `.env`, secret, pepper, email value, student name, media path, or copy content was displayed.

## Verdict

`PORTE6E_DONE_DEPLOYED`

The log redaction code is deployed and verified. The data anomaly remains bounded to one technical copy id and requires a separate controlled repair decision.

## Next Step

Decide whether to execute the separate controlled data repair plan for the single finalized copy without final PDF.

Do not start Docker cleanup until logs remain clean through the next scheduled integrity audit window.
