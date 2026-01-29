#!/bin/bash
# Smoke test staging - Full workflow validation
# Usage: BASE_URL=https://staging.example.com SMOKE_USER=prof1 SMOKE_PASS=changeme ./scripts/smoke_staging.sh

set -euo pipefail

BASE_URL="${BASE_URL:-https://staging.example.com}"
USER="${SMOKE_USER:-prof1}"
PASS="${SMOKE_PASS:-changeme}"
TS="$(date -u +%Y%m%dT%H%M%SZ)"
LOGDIR="/tmp/staging_smoke_${TS}"
mkdir -p "$LOGDIR"

log(){ echo "[$(date -u +%H:%M:%S)] $*" | tee -a "$LOGDIR/smoke.log" ; }

log "=== STAGING SMOKE START ==="
log "BASE_URL=$BASE_URL"
log "USER=$USER"

# Cookies file for session-based authentication
COOKIES="$LOGDIR/cookies.txt"
touch "$COOKIES"

# 0) Login (session-based authentication, not token)
log "1) Login"
LOGIN_RESP=$(curl -fsS -c "$COOKIES" -X POST "$BASE_URL/api/login/" \
  -H "Content-Type: application/json" \
  -d "{\"username\":\"$USER\",\"password\":\"$PASS\"}" \
  | tee "$LOGDIR/login.json")

# Check login success (no token, just session cookie)
LOGIN_MSG=$(echo "$LOGIN_RESP" | jq -r '.message // empty')
if [ "$LOGIN_MSG" != "Login successful" ]; then
  log "❌ Login failed"
  cat "$LOGDIR/login.json"
  exit 1
fi
log "✅ Logged in (session cookie set)"

# Extract CSRF token from cookies
CSRF=$(grep csrftoken "$COOKIES" | awk '{print $NF}')
if [ -z "$CSRF" ]; then
  log "⚠️  No CSRF token found, trying without..."
  CSRF=""
fi

# 1) Get exam ID (need this to list copies)
log "2) Get exam ID"
EXAM_RESP=$(curl -fsS -b "$COOKIES" "$BASE_URL/api/exams/" | tee "$LOGDIR/exams.json")

EXAM_ID=$(echo "$EXAM_RESP" | jq -r '.results[0].id // .[0].id // empty')
if [ -z "$EXAM_ID" ] || [ "$EXAM_ID" = "null" ]; then
  log "❌ No exam found"
  cat "$LOGDIR/exams.json"
  exit 1
fi
log "✅ Exam ID: $EXAM_ID"

# 2) List READY copies
log "3) List READY copies"
COPIES_RESP=$(curl -fsS -b "$COOKIES" "$BASE_URL/api/exams/$EXAM_ID/copies/" \
  | tee "$LOGDIR/copies.json")

COPY_ID=$(echo "$COPIES_RESP" | jq -r '.results[] | select(.status=="READY") | .id' | head -1)
if [ -z "$COPY_ID" ] || [ "$COPY_ID" = "null" ]; then
  log "❌ No READY copy found"
  cat "$LOGDIR/copies.json"
  exit 1
fi
log "✅ Found READY copy: $COPY_ID"

# Verify copy has pages > 0
COPY_PAGES=$(echo "$COPIES_RESP" | jq -r ".results[] | select(.id==\"$COPY_ID\") | .booklets[0].pages_images | length")
if [ "$COPY_PAGES" -lt 1 ]; then
  log "❌ Copy has no pages (pages=$COPY_PAGES)"
  exit 1
fi
log "✅ Copy has $COPY_PAGES pages"

# 3) Lock copy
log "4) Lock copy"
LOCK_RESP=$(curl -fsS -b "$COOKIES" -X POST "$BASE_URL/api/grading/copies/$COPY_ID/lock/" \
  -H "X-CSRFToken: $CSRF" \
  -H "Content-Type: application/json" \
  -d '{}' \
  -w '\nHTTP_STATUS:%{http_code}' \
  | tee "$LOGDIR/lock.txt")

LOCK_CODE=$(echo "$LOCK_RESP" | grep 'HTTP_STATUS' | cut -d: -f2)
if [ "$LOCK_CODE" != "200" ] && [ "$LOCK_CODE" != "201" ]; then
  log "❌ Lock failed (HTTP $LOCK_CODE)"
  cat "$LOGDIR/lock.txt"
  exit 1
fi

LOCK_TOKEN=$(echo "$LOCK_RESP" | sed '$d' | jq -r '.token // empty')
if [ -z "$LOCK_TOKEN" ] || [ "$LOCK_TOKEN" = "null" ]; then
  log "❌ No lock token in response"
  cat "$LOGDIR/lock.txt"
  exit 1
fi
log "✅ Locked (HTTP $LOCK_CODE, token: ${LOCK_TOKEN:0:8}...)"

# 4) POST annotation (bounding box format: normalized [0,1])
log "5) POST annotation"
ANNOT_RESP=$(curl -fsS -b "$COOKIES" -X POST "$BASE_URL/api/grading/copies/$COPY_ID/annotations/" \
  -H "Content-Type: application/json" \
  -H "X-CSRFToken: $CSRF" \
  -H "X-Lock-Token: $LOCK_TOKEN" \
  -d '{
    "page_index": 0,
    "x": 0.10,
    "y": 0.10,
    "w": 0.20,
    "h": 0.10,
    "type": "COMMENT",
    "content": "staging-smoke-test"
  }' \
  -w '\nHTTP_STATUS:%{http_code}' \
  | tee "$LOGDIR/annotation_post.txt")

ANNOT_CODE=$(echo "$ANNOT_RESP" | grep 'HTTP_STATUS' | cut -d: -f2)
if [ "$ANNOT_CODE" != "200" ] && [ "$ANNOT_CODE" != "201" ]; then
  log "❌ Annotation POST failed (HTTP $ANNOT_CODE)"
  cat "$LOGDIR/annotation_post.txt"
  exit 1
fi
log "✅ Annotation created (HTTP $ANNOT_CODE)"

# 5) GET annotations (handle paginated/array)
log "6) GET annotations"
ANNOTS_GET_RESP=$(curl -fsS -b "$COOKIES" "$BASE_URL/api/grading/copies/$COPY_ID/annotations/" \
  | tee "$LOGDIR/annotations_get.json")

ANNOT_COUNT=$(echo "$ANNOTS_GET_RESP" | jq -r '
  if type=="object" and has("results") then (.results|length)
  elif type=="array" then length
  else 0 end
')

if [ "$ANNOT_COUNT" -lt 1 ]; then
  log "❌ Annotation GET returned count=$ANNOT_COUNT"
  cat "$LOGDIR/annotations_get.json"
  exit 1
fi
log "✅ Annotations found: $ANNOT_COUNT"

# 6) Finalize (optional - comment out if you want to keep copy for manual inspection)
log "7) Finalize copy"
FINALIZE_RESP=$(curl -fsS -b "$COOKIES" -X POST "$BASE_URL/api/grading/copies/$COPY_ID/finalize/" \
  -H "X-CSRFToken: $CSRF" \
  -H "X-Lock-Token: $LOCK_TOKEN" \
  -w '\nHTTP_STATUS:%{http_code}' \
  | tee "$LOGDIR/finalize.txt")

FINALIZE_CODE=$(echo "$FINALIZE_RESP" | grep 'HTTP_STATUS' | cut -d: -f2)
if [ "$FINALIZE_CODE" != "200" ]; then
  log "❌ Finalize failed (HTTP $FINALIZE_CODE)"
  cat "$LOGDIR/finalize.txt"
  exit 1
fi
log "✅ Finalize OK (HTTP $FINALIZE_CODE)"

# Check final status
FINAL_STATUS=$(echo "$FINALIZE_RESP" | sed '$d' | jq -r '.status // empty')
if [ "$FINAL_STATUS" != "GRADED" ]; then
  log "⚠️  Expected status GRADED, got: $FINAL_STATUS"
fi

# 7) Verify final PDF accessible
log "8) Verify final PDF"
PDF_URL="$BASE_URL/api/grading/copies/$COPY_ID/final-pdf/"

PDF_HEAD=$(curl -fsSI -b "$COOKIES" "$PDF_URL" | tee "$LOGDIR/pdf_head.txt")
if ! echo "$PDF_HEAD" | grep -q "200 OK"; then
  log "❌ PDF not accessible"
  cat "$LOGDIR/pdf_head.txt"
  exit 1
fi
log "✅ PDF accessible: $PDF_URL"

# 8) Unlock (best effort, may fail if finalize auto-unlocks)
log "9) Unlock (best effort)"
UNLOCK_RESP=$(curl -sS -b "$COOKIES" -X DELETE "$BASE_URL/api/grading/copies/$COPY_ID/lock/release/" \
  -H "X-CSRFToken: $CSRF" \
  -H "X-Lock-Token: $LOCK_TOKEN" \
  -w '\nHTTP_STATUS:%{http_code}' \
  | tee "$LOGDIR/unlock.txt" || true)

UNLOCK_CODE=$(echo "$UNLOCK_RESP" | grep 'HTTP_STATUS' | cut -d: -f2 || echo "N/A")
if [ "$UNLOCK_CODE" = "204" ] || [ "$UNLOCK_CODE" = "200" ]; then
  log "✅ Unlocked (HTTP $UNLOCK_CODE)"
elif [ "$UNLOCK_CODE" = "404" ] || [ "$UNLOCK_CODE" = "409" ]; then
  log "⚠️  Unlock not needed (HTTP $UNLOCK_CODE) - likely auto-unlocked by finalize"
else
  log "⚠️  Unlock response: HTTP $UNLOCK_CODE (ignored)"
fi

log "=== STAGING SMOKE SUCCESS ==="
log "Artifacts: $LOGDIR"
log ""
log "Summary:"
log "  ✅ Login successful"
log "  ✅ Exam found: $EXAM_ID"
log "  ✅ READY copy found with pages > 0"
log "  ✅ Lock acquired"
log "  ✅ Annotation created"
log "  ✅ Annotations retrieved ($ANNOT_COUNT)"
log "  ✅ Copy finalized (status: $FINAL_STATUS)"
log "  ✅ PDF accessible"
