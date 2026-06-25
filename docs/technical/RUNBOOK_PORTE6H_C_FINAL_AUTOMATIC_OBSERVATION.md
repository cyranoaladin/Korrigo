# Runbook - Porte 6H-C final automatic observation

Use this runbook only after `2026-06-24T18:50:00Z`.

Do not run manual backup. Do not run manual sync. Do not build, deploy, restart, prune, delete, migrate, or modify the database.

## 1. Verify UTC Time

```bash
date -u
```

Continue only if the time is after `2026-06-24T18:50:00Z`.

## 2. Local and Production Preflight

```bash
cd /home/alaeddine/.config/superpowers/worktrees/korrigo_v2_improved/release-reconcile
git status --short --branch
git rev-parse HEAD
git log --oneline --decorate -10
```

```bash
ssh nexus-prod 'set -eu
hostname
date -u
df -h /
cd /var/www/labomaths/korrigo_release
docker compose -p docker --env-file /var/www/labomaths/korrigo/.env \
  -f infra/docker/docker-compose.prod.yml \
  ps
curl -fsS https://korrigo.labomaths.tn/api/health/
'
```

Expected runtime:

- backend/celery/celery-beat: `korrigo-backend:korrigo-direct-c38a586`
- nginx: `korrigo-nginx:korrigo-direct-f793f0c`
- DB/Redis healthy

## 3. Create Server Audit Directory

```bash
ssh nexus-prod 'set -eu
TS="$(date -u +%Y%m%dT%H%M%SZ)"
AUDIT_DIR="/var/www/labomaths/korrigo_release/ops/porte6h_c_auto_observation_${TS}"
mkdir -p "$AUDIT_DIR"
chmod 755 "$AUDIT_DIR"
echo "$AUDIT_DIR" > /tmp/korrigo_porte6h_c_audit_dir.txt
echo "AUDIT_DIR=$AUDIT_DIR"
'
```

## 4. Verify Repair Persistence

```bash
ssh nexus-prod 'set -eu
AUDIT_DIR="$(cat /tmp/korrigo_porte6h_c_audit_dir.txt)"
cd /var/www/labomaths/korrigo_release
docker compose -p docker --env-file /var/www/labomaths/korrigo/.env \
  -f infra/docker/docker-compose.prod.yml \
  exec -T backend python manage.py shell <<'"'"'PY'"'"' > "$AUDIT_DIR/target_copy_current_state.txt"
from exams.models import Copy
copy = Copy.objects.get(pk="744cb7ed-bbfb-4109-b46d-f93d17002a03")
print(f"copy_pk={copy.pk}")
print(f"exam_pk={copy.exam_id}")
print(f"status={copy.status}")
print(f"has_final_pdf={bool(copy.final_pdf)}")
print(f"final_pdf_name_present={bool(getattr(copy.final_pdf, 'name', ''))}")
try:
    size = copy.final_pdf.size if copy.final_pdf else 0
except Exception:
    size = 0
print(f"final_pdf_size_positive={size > 0}")
PY
cat "$AUDIT_DIR/target_copy_current_state.txt"
'
```

Expected:

- `status=FINALIZED`
- `has_final_pdf=True`
- `final_pdf_name_present=True`
- `final_pdf_size_positive=True`

## 5. Run Global Integrity Audit

```bash
ssh nexus-prod 'set -eu
AUDIT_DIR="$(cat /tmp/korrigo_porte6h_c_audit_dir.txt)"
cd /var/www/labomaths/korrigo_release
set +e
docker compose -p docker --env-file /var/www/labomaths/korrigo/.env \
  -f infra/docker/docker-compose.prod.yml \
  exec -T backend python manage.py check_copy_integrity \
  --fail-on-issues \
  > "$AUDIT_DIR/check_copy_integrity_global_6hc.out" 2>&1
RC=$?
set -e
echo "GLOBAL_AUDIT_6HC_RC=$RC" | tee "$AUDIT_DIR/check_copy_integrity_global_6hc.rc"
python3 - <<'"'"'PY'"'"'
from pathlib import Path
import re
audit = Path(open("/tmp/korrigo_porte6h_c_audit_dir.txt").read().strip())
text = (audit / "check_copy_integrity_global_6hc.out").read_text(errors="ignore")
print(f"EMAIL_COUNT={len(re.findall(r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}', text))}")
print(f"STUDENT_EMAIL_KEY_COUNT={len(re.findall(r'student_email', text, re.I))}")
print(f"ANONYMOUS_ID_KEY_COUNT={len(re.findall(r'anonymous_id', text, re.I))}")
print(f"FINALIZED_WITHOUT_FINAL_PDF_COUNT={len(re.findall(r'FINALIZED_WITHOUT_FINAL_PDF', text))}")
print(f"ISSUES_ZERO_COUNT={len(re.findall(r'issues=0', text))}")
print(f"AT_SIGN_COUNT={text.count('@')}")
PY
'
```

Expected: RC 0, `issues=0`, no email, no `student_email`, no `anonymous_id`.

## 6. Verify Planned Celery Integrity Audit

```bash
ssh nexus-prod 'set -eu
AUDIT_DIR="$(cat /tmp/korrigo_porte6h_c_audit_dir.txt)"
SINCE="2026-06-24T12:31:30Z"
docker logs --since "$SINCE" docker-celery-1 > "$AUDIT_DIR/celery_logs_since_repair.raw" 2>&1 || true
python3 - <<'"'"'PY'"'"'
from pathlib import Path
import re
audit = Path(open("/tmp/korrigo_porte6h_c_audit_dir.txt").read().strip())
text = (audit / "celery_logs_since_repair.raw").read_text(errors="ignore")
print(f"CELERY_INTEGRITY_RUN_COUNT={len(re.findall(r'Integrity scan completed', text))}")
print(f"CELERY_INTEGRITY_ISSUES_ZERO_COUNT={len(re.findall(r'issues=0', text))}")
print(f"CELERY_INTEGRITY_ISSUE_POSITIVE_COUNT={len(re.findall(r'issues=[1-9]', text))}")
print(f"CELERY_COPY_AUDIT_ERROR_COUNT={len(re.findall(r'Copy integrity audit detected issues', text))}")
print(f"CELERY_EMAIL_COUNT={len(re.findall(r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}', text))}")
print(f"CELERY_STUDENT_EMAIL_KEY_COUNT={len(re.findall(r'student_email', text, re.I))}")
print(f"CELERY_ANONYMOUS_ID_KEY_COUNT={len(re.findall(r'anonymous_id', text, re.I))}")
print(f"CELERY_ERROR_LIKE_COUNT={len(re.findall(r'ERROR|CRITICAL|Traceback|Exception|500 ', text, re.I))}")
PY
'
```

Expected: at least one integrity run, at least one `issues=0`, no positive issue, no PII.

## 7. Verify Automatic Backup After 6G Manual Backup

```bash
ssh nexus-prod 'set -eu
AUDIT_DIR="$(cat /tmp/korrigo_porte6h_c_audit_dir.txt)"
LATEST="$(find /var/backups/korrigo/encrypted -mindepth 1 -maxdepth 1 -type d | sort | tail -n 1)"
B="$(basename "$LATEST")"
{
  echo "LATEST_ENCRYPTED_BACKUP=$B"
  echo "MANUAL_BACKUP_6G=20260624T124211Z"
  if [ "$B" \> "20260624T124211Z" ]; then
    echo "AUTOMATIC_BACKUP_AFTER_MANUAL_6G=YES"
  else
    echo "AUTOMATIC_BACKUP_AFTER_MANUAL_6G=NO"
  fi
} > "$AUDIT_DIR/automatic_backup_observation.txt"
cat "$AUDIT_DIR/automatic_backup_observation.txt"
(cd "$LATEST" && sha256sum -c SHA256SUMS.txt) > "$AUDIT_DIR/latest_backup_sha256_check.txt"
cat "$AUDIT_DIR/latest_backup_sha256_check.txt"
'
```

Expected:

- `AUTOMATIC_BACKUP_AFTER_MANUAL_6G=YES`
- all checksums OK

If the latest backup is not newer than `20260624T124211Z`, return `WAIT_NEXT_AUTOMATIC_CRON_OBSERVATION`.

## 8. Verify StorageBox Sync

```bash
ssh nexus-prod 'set -eu
AUDIT_DIR="$(cat /tmp/korrigo_porte6h_c_audit_dir.txt)"
/usr/local/bin/korrigo_sync_storagebox_v2.sh --dry-run \
  > /tmp/korrigo_sync_v2_porte6h_c_auto_observation_dryrun.txt
printf "WOULD_TRANSFER_COUNT=" | tee "$AUDIT_DIR/sync_auto_observation_counts.txt"
grep -E "^[<>ch.*]" /tmp/korrigo_sync_v2_porte6h_c_auto_observation_dryrun.txt | wc -l | tee -a "$AUDIT_DIR/sync_auto_observation_counts.txt"
printf "DELETE_COUNT=" | tee -a "$AUDIT_DIR/sync_auto_observation_counts.txt"
grep -E "^\*deleting" /tmp/korrigo_sync_v2_porte6h_c_auto_observation_dryrun.txt | wc -l | tee -a "$AUDIT_DIR/sync_auto_observation_counts.txt"
printf "ERROR_WORD_COUNT=" | tee -a "$AUDIT_DIR/sync_auto_observation_counts.txt"
grep -Eai "error|failed|denied|permission|No such|timeout" /tmp/korrigo_sync_v2_porte6h_c_auto_observation_dryrun.txt | wc -l | tee -a "$AUDIT_DIR/sync_auto_observation_counts.txt"
'
```

Expected: all three counts are zero.

## 9. Verify Logs

Count only. Do not print raw PII-bearing lines.

```bash
ssh nexus-prod 'bash -s' <<'"'"'REMOTE'"'"'
set -eu
AUDIT_DIR="$(cat /tmp/korrigo_porte6h_c_audit_dir.txt)"
SINCE_LINES=500
for log in /var/log/korrigo_backup_encrypted_v2.log /var/log/korrigo_sync_storagebox_v2.log; do
  echo "--- $log ---" | tee -a "$AUDIT_DIR/backup_sync_log_safety_counts.txt"
  tail -n "$SINCE_LINES" "$log" 2>/dev/null | python3 -c "
import sys, re
text=sys.stdin.read()
email=len(re.findall(r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}', text))
secret=len(re.findall(r'SECRET|PASSWORD|TOKEN|PRIVATE KEY|BEGIN RSA|PEPPER|POSTGRES_PASSWORD|REDIS_PASSWORD', text, re.I))
error=len(re.findall(r'ERROR|Traceback|Exception|failed|denied|timeout', text, re.I))
print(f'EMAIL_COUNT={email}')
print(f'SECRET_WORD_COUNT={secret}')
print(f'ERROR_LIKE_COUNT={error}')
" | tee -a "$AUDIT_DIR/backup_sync_log_safety_counts.txt"
done
REMOTE
```

Application logs:

```bash
ssh nexus-prod 'set -eu
AUDIT_DIR="$(cat /tmp/korrigo_porte6h_c_audit_dir.txt)"
SINCE="2026-06-24T12:42:11Z"
{
  echo "LOG_SINCE=$SINCE"
  for c in docker-backend-1 docker-celery-1 docker-celery-beat-1 docker-nginx-1; do
    TMP="$(mktemp /tmp/korrigo_porte6h_c_logs.XXXXXX)"
    docker logs --since "$SINCE" "$c" > "$TMP" 2>&1 || true
    python3 - "$TMP" "$c" <<'"'"'PY'"'"'
import re, sys
from pathlib import Path
path = Path(sys.argv[1])
service = sys.argv[2]
text = path.read_text(errors="ignore")
email = len(re.findall(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text))
student_email_key = len(re.findall(r"student_email", text, re.I))
anonymous_id_key = len(re.findall(r"anonymous_id", text, re.I))
error = len(re.findall(r"ERROR|CRITICAL|Traceback|Exception|500 |Copy integrity audit detected issues", text, re.I))
warning = len(re.findall(r"WARNING|WARN", text, re.I))
print(f"{service} EMAIL_COUNT={email} STUDENT_EMAIL_KEY_COUNT={student_email_key} ANONYMOUS_ID_KEY_COUNT={anonymous_id_key} ERROR_LIKE_COUNT={error} WARNING_LIKE_COUNT={warning}")
PY
    rm -f "$TMP"
  done
} > "$AUDIT_DIR/application_log_counts_since_6g.txt"
cat "$AUDIT_DIR/application_log_counts_since_6g.txt"
'
```

Expected: no email, no `student_email`, no `anonymous_id`, no error.

## 10. Health and Public Smoke

```bash
curl -fsS https://korrigo.labomaths.tn/api/health/
for url in \
  https://korrigo.labomaths.tn/ \
  https://korrigo.labomaths.tn/api/health/ \
  https://korrigo.labomaths.tn/api/csrf/ \
  https://korrigo.labomaths.tn/korrigo \
  https://korrigo.labomaths.tn/student/login \
  https://korrigo.labomaths.tn/admin/login
do
  code="$(curl -fsS -o /dev/null -w "%{http_code}" "$url")"
  echo "GET $url HTTP_STATUS=$code"
done
```

Expected: health OK and no 500.

## Verdict Rules

Return `POST_REPAIR_24H_OBSERVATION_DONE` only if all gates are green.

Return `WAIT_NEXT_AUTOMATIC_CRON_OBSERVATION` if the automatic backup or sync has not yet happened.

Return `NO-GO_OBSERVATION` if any gate fails or any sensitive value appears.
