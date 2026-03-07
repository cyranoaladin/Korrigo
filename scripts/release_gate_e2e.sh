#!/usr/bin/env bash
# E2E workflow for Release Gate — lock-free architecture (post-LOT 8)
# Tests: authentication, exam listing, copy listing, annotation CRUD
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

  # POST annotation (lock-free: annotations work directly on READY copies)
  ann_resp=$(curl -s -b "$cookies" -X POST "$base/api/grading/copies/$copy_id/annotations/" \
    -H "Content-Type: application/json" \
    -H "X-CSRFToken: $csrf" \
    -H "Referer: $base/" \
    -d '{
      "page_index": 0,
      "x": 0.1,
      "y": 0.2,
      "w": 0.3,
      "h": 0.05,
      "type": "COMMENT",
      "content": "E2E release gate annotation (run '"$run"')"
    }' \
    -w '\nHTTP_STATUS:%{http_code}')

  ann_code=$(echo "$ann_resp" | grep 'HTTP_STATUS' | cut -d: -f2)
  [ "$ann_code" = "200" ] || [ "$ann_code" = "201" ] || { echo "❌ Annotation POST failed (HTTP $ann_code)"; echo "$ann_resp"; exit 1; }
  ann_id=$(echo "$ann_resp" | sed '$d' | jq -r '.id')
  echo "2️⃣  Annotation created (HTTP $ann_code), ID: ${ann_id:0:8}..."

  # GET annotations
  get_resp=$(curl -s -b "$cookies" "$base/api/grading/copies/$copy_id/annotations/" \
    -w '\nHTTP_STATUS:%{http_code}')

  get_code=$(echo "$get_resp" | grep 'HTTP_STATUS' | cut -d: -f2)
  [ "$get_code" = "200" ] || { echo "❌ Annotation GET failed (HTTP $get_code)"; exit 1; }

  ann_count=$(echo "$get_resp" | sed '$d' | jq -r 'if type=="array" then length elif .results then (.results | length) else 0 end')
  [ "$ann_count" != "0" ] || { echo '❌ Annotation count is 0'; exit 1; }
  echo "3️⃣  GET annotations (HTTP $get_code) — $ann_count annotation(s) found"

  # DELETE the annotation we just created (cleanup for idempotent re-runs)
  if [ -n "$ann_id" ] && [ "$ann_id" != "null" ]; then
    del_resp=$(curl -s -b "$cookies" -X DELETE "$base/api/grading/annotations/$ann_id/" \
      -H "X-CSRFToken: $csrf" \
      -H "Referer: $base/" \
      -w '\nHTTP_STATUS:%{http_code}')

    del_code=$(echo "$del_resp" | grep 'HTTP_STATUS' | cut -d: -f2)
    [ "$del_code" = "200" ] || [ "$del_code" = "204" ] || echo "⚠️  Annotation DELETE returned HTTP $del_code (non-fatal)"
    echo "4️⃣  Annotation deleted (HTTP $del_code) — cleanup OK"
  fi

  echo "✅ E2E RUN $run/3 COMPLETE"
done

echo ""
echo "========================================"
echo "✅ E2E: 3/3 RUNS PASSED"
echo "========================================"
