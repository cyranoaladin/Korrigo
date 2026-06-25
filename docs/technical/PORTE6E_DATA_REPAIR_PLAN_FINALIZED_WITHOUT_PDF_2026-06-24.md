# Porte 6E - Data Repair Plan For Finalized Copy Without Final PDF

Date: 2026-06-24

## Context

Porte 6D found a recurring copy integrity audit issue after the Porte 6C deployment.

The issue is not a frontend or deployment health failure. It is a data integrity anomaly reported by the scheduled backend audit:

`FINALIZED_WITHOUT_FINAL_PDF`

No student name, email, media path, or copy content is recorded here.

## Read-Only Findings

Production read-only diagnostic:

- `FINALIZED_TOTAL=731`
- `FINALIZED_WITHOUT_FINAL_PDF_COUNT=1`
- `RELEASED_FINALIZED_WITHOUT_STUDENT_COUNT=0`

Affected technical ids:

- `copy_pk=744cb7ed-bbfb-4109-b46d-f93d17002a03`
- `exam_pk=de96412e-8504-4929-abf1-89247df98775`
- `status=FINALIZED`
- `has_final_pdf=False`

Repair readiness, still read-only:

- `booklet_count=1`
- `page_image_count=2`
- `existing_page_image_count=2`
- `missing_page_image_count=0`
- `has_pdf_source=True`
- `pdf_regeneration_pending=False`

## Hypothesis

The copy is in `FINALIZED` state but the `final_pdf` field is blank rather than populated.

The source material required to regenerate the final PDF appears to exist, because the copy has one booklet, two page images, and no missing page image was detected.

## Repair Options

1. Regenerate the final PDF through the existing controlled integrity repair command.
2. If finalization is invalid, move the copy back to an appropriate non-finalized state through a dedicated repair command.
3. If a final PDF exists as an orphaned media file, link it back only after a protected inventory confirms the match without exposing media paths.

## Preferred Option

Preferred first option:

run a controlled regeneration using the existing integrity command for the single affected technical copy id.

Proposed command, not executed in Porte 6E:

```bash
cd /var/www/labomaths/korrigo_release
docker compose -p docker --env-file /var/www/labomaths/korrigo/.env \
  -f infra/docker/docker-compose.prod.yml \
  exec -T backend python manage.py check_copy_integrity \
  --copy-id 744cb7ed-bbfb-4109-b46d-f93d17002a03 \
  --repair-missing-final-pdf \
  --fail-on-issues
```

## Required Guards Before Execution

- fresh encrypted backup checksum OK;
- StorageBox dry-run caught up;
- rollback state available;
- command output redacted by the Porte 6E logging fix;
- no display of student data, emails, names, media paths, or copy content;
- post-repair read-only recount;
- post-repair public health check.

## Rollback Considerations

This repair would write a new final PDF file and update one `Copy.final_pdf` field.

Rollback must be prepared before execution:

- retain the pre-repair DB backup;
- capture the affected copy technical fields before repair without PII;
- if rollback is required, remove or unlink only the generated final PDF after explicit validation.

No rollback action was executed in Porte 6E.

## Status

`DATA_REPAIR_PLAN_REQUIRED`

The data issue is bounded to one technical copy id and appears repairable, but repair was not executed in Porte 6E.
