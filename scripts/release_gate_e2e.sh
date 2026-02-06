#!/usr/bin/env bash
# E2E workflow for Release Gate — extracted to avoid quoting issues in bash -c
# Usage: ./release_gate_e2e.sh <base_url> <prof_password> <compose_file> <backend_svc>
set -euo pipefail

base="${1:?Usage: $0 <base_url> <prof_password> <compose_file> <backend_svc>}"
prof_password="${2:?}"
compose_file="${3:?}"
backend_svc="${4:?}"
cookies="/tmp/rg_cookies.txt"

# Helper: login and get CSRF token
login() {
  local user="$1" pass="$2"

  # Get initial CSRF token
  curl -s -c "$cookies" "$base/api/exams/" > /dev/null
  local csrf
  csrf=$(grep csrftoken "$cookies" | awk '{print $7}')

  # Login
  curl -s -b "$cookies" -c "$cookies" -X POST "$base/api/login/" \
    -H "Content-Type: application/json" \
    -H "X-CSRFToken: $csrf" \
    -H "Referer: $base/" \
    -d "{\"username\":\"$user\",\"password\":\"$pass\"}" > /dev/null

  # Update CSRF token after login
  csrf=$(grep csrftoken "$cookies" | awk '{print $7}')
  echo "$csrf"
}

# Login once
csrf=$(login prof1 "$prof_password")
[ -n "$csrf" ] || { echo 'Login failed: no CSRF token'; exit 1; }
echo "✓ Logged in, CSRF token obtained"

# Get exam ID
exam_id=$(curl -s -b "$cookies" "$base/api/exams/" | jq -r '.results[0].id')
[ "$exam_id" != "null" ] && [ -n "$exam_id" ] || { echo 'No exam found'; exit 1; }
echo "✓ Exam ID: $exam_id"

for run in 1 2 3; do
  echo ""
  echo "========================================"
  echo "E2E RUN $run/3"
  echo "========================================"

  # Get a READY copy
  copy_id=$(curl -s -b "$cookies" "$base/api/exams/$exam_id/copies/" | jq -r '.results[] | select(.status=="READY") | .id' | head -1)
  [ "$copy_id" != "null" ] && [ -n "$copy_id" ] || { echo 'No READY copy found'; exit 1; }
  echo "1️⃣  Found READY copy: $copy_id"

  # Lock copy
  lock_resp=$(curl -s -b "$cookies" -X POST "$base/api/grading/copies/$copy_id/lock/" \
    -H "X-CSRFToken: $csrf" \
    -H "Referer: $base/" \
    -H "Content-Type: application/json" \
    -d '{}' \
    -w '\nHTTP_STATUS:%{http_code}')

  lock_code=$(echo "$lock_resp" | grep 'HTTP_STATUS' | cut -d: -f2)
  [ "$lock_code" = "200" ] || [ "$lock_code" = "201" ] || { echo "❌ Lock failed (HTTP $lock_code)"; echo "$lock_resp"; exit 1; }

  lock_token=$(echo "$lock_resp" | sed '$d' | jq -r '.token')
  [ -n "$lock_token" ] && [ "$lock_token" != "null" ] || { echo '❌ No lock token'; echo "DEBUG lock_resp:"; echo "$lock_resp" | sed '$d'; exit 1; }
  echo "2️⃣  Copy locked (HTTP $lock_code), token: ${lock_token:0:8}..."

  # POST annotation (bounding box format: x, y, w, h normalized [0,1])
  ann_resp=$(curl -s -b "$cookies" -X POST "$base/api/grading/copies/$copy_id/annotations/" \
    -H "Content-Type: application/json" \
    -H "X-CSRFToken: $csrf" \
    -H "X-Lock-Token: $lock_token" \
    -H "Referer: $base/" \
    -d '{
      "page_index": 0,
      "x": 0.1,
      "y": 0.2,
      "w": 0.3,
      "h": 0.05,
      "type": "COMMENT",
      "content": "Test annotation from E2E"
    }' \
    -w '\nHTTP_STATUS:%{http_code}')

  ann_code=$(echo "$ann_resp" | grep 'HTTP_STATUS' | cut -d: -f2)
  [ "$ann_code" = "200" ] || [ "$ann_code" = "201" ] || { echo "❌ Annotation POST failed (HTTP $ann_code)"; echo "$ann_resp"; exit 1; }
  echo "3️⃣  Annotation created (HTTP $ann_code) ← P0 FIX VERIFIED ✅"

  # GET annotations
  get_resp=$(curl -s -b "$cookies" "$base/api/grading/copies/$copy_id/annotations/" \
    -w '\nHTTP_STATUS:%{http_code}')

  get_code=$(echo "$get_resp" | grep 'HTTP_STATUS' | cut -d: -f2)
  [ "$get_code" = "200" ] || { echo "❌ Annotation GET failed (HTTP $get_code)"; exit 1; }

  ann_count=$(echo "$get_resp" | sed '$d' | jq -r 'if type=="array" then length elif .results then (.results | length) else 0 end')
  [ "$ann_count" != "0" ] || { echo '❌ Annotation count is 0'; exit 1; }
  echo "4️⃣  GET annotations (HTTP $get_code) - $ann_count annotations found"

  # Release lock
  unlock_resp=$(curl -s -b "$cookies" -X DELETE "$base/api/grading/copies/$copy_id/lock/release/" \
    -H "X-CSRFToken: $csrf" \
    -H "X-Lock-Token: $lock_token" \
    -H "Referer: $base/" \
    -w '\nHTTP_STATUS:%{http_code}')

  unlock_code=$(echo "$unlock_resp" | grep 'HTTP_STATUS' | cut -d: -f2)
  [ "$unlock_code" = "200" ] || [ "$unlock_code" = "204" ] || { echo "❌ Unlock failed (HTTP $unlock_code)"; exit 1; }
  echo "5️⃣  Lock released (HTTP $unlock_code)"

  # Reset copy status for next run
  docker compose -f "$compose_file" exec -T "$backend_svc" python manage.py shell -c "
from exams.models import Copy
from grading.models import CopyLock
CopyLock.objects.all().delete()
Copy.objects.filter(status='LOCKED').update(status='READY')
" > /dev/null 2>&1

  echo "✅ E2E RUN $run/3 COMPLETE"
done

echo ""
echo "========================================"
echo "✅ E2E: 3/3 RUNS PASSED"
echo "========================================"
