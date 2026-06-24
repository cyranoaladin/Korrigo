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

Pending at this documentation checkpoint.

The logging correction changes backend code and therefore requires the full local pipeline before any direct deployment.

## Re-Observation

Pending at this documentation checkpoint.

The required post-correction log gate is:

- `EMAIL_COUNT=0`
- `STUDENT_EMAIL_KEY_COUNT=0`
- no sensitive fields in copy integrity audit output.

The integrity issue may still be reported until the bounded data repair is executed.

## Confirmations

- No GitHub, push, PR, workflow, GHCR, or registry was used.
- No production migration was run.
- No DB write was performed during triage.
- No `docker compose down`, `down -v`, or prune was run.
- No volume or backup was removed.
- No `.env`, secret, pepper, email value, student name, media path, or copy content was displayed.

## Verdict

Pending final pipeline and deployment decision.

Expected if the pipeline passes and deployment is completed:

`PORTE6E_DONE_DEPLOYED`

Expected if deployment is deferred:

`PORTE6E_READY_FOR_DIRECT_DEPLOY`

## Next Step

Run the full local pipeline. If it passes, deploy the backend image directly and re-observe logs. Then decide whether to execute the separate data repair plan.
