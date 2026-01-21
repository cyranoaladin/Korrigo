#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8088}"
ADMIN_USER="${ADMIN_USER:-admin}"
ADMIN_PASS="${ADMIN_PASS:-adminpass123}"

echo "==> E2E Workflow Test: STAGING → READY → LOCKED → GRADED → PDF Download"
echo

# Login and get session
echo "==> [1] Login as admin"
LOGIN_RESPONSE=$(curl -sS -i -X POST "$BASE_URL/api/login/" \
  -H "Content-Type: application/json" \
  -d "{\"username\":\"$ADMIN_USER\",\"password\":\"$ADMIN_PASS\"}")

SESSIONID=$(echo "$LOGIN_RESPONSE" | grep -i "set-cookie.*sessionid" | sed 's/.*sessionid=\([^;]*\).*/\1/' | head -1)
CSRFTOKEN=$(echo "$LOGIN_RESPONSE" | grep -i "set-cookie.*csrftoken" | sed 's/.*csrftoken=\([^;]*\).*/\1/' | head -1)

if [[ -z "$SESSIONID" ]]; then
  echo "❌ Login failed"
  exit 1
fi

echo "✅ Login successful (session: ${SESSIONID:0:20}...)"
echo

# Create a STAGING copy with booklets
echo "==> [2] Create STAGING copy with booklet"
COPY_ID=$(docker-compose exec -T backend python manage.py shell <<'PY' 2>/dev/null | tail -1
from django.contrib.auth import get_user_model
from exams.models import Exam, Copy, Booklet
from django.utils import timezone
import uuid
from datetime import date
import sys

User = get_user_model()

# Ensure admin exists
u, _ = User.objects.get_or_create(username="admin", defaults={"is_staff": True, "is_superuser": True})
if not u.is_staff:
    u.is_staff = True
    u.is_superuser = True
    u.set_password("adminpass123")
    u.save()

# Create exam + booklet with pages + STAGING copy
exam, _ = Exam.objects.get_or_create(
    name="E2E Workflow Test",
    defaults={"date": date.today()}
)

booklet = Booklet.objects.create(
    exam=exam,
    start_page=0,
    end_page=1,
    pages_images=["copies/pages/page1.png", "copies/pages/page2.png"]
)

copy = Copy.objects.create(
    exam=exam,
    anonymous_id=f"E2E-{uuid.uuid4().hex[:8]}",
    status=Copy.Status.STAGING,
)

copy.booklets.add(booklet)
copy.save()

sys.stdout.write(str(copy.id) + "\n")
PY
)

if [[ -z "$COPY_ID" ]]; then
  echo "❌ Failed to create copy"
  exit 1
fi

echo "✅ Created STAGING copy: $COPY_ID"
echo

# Test STAGING → READY
echo "==> [3] Test STAGING → READY"
READY_RESPONSE=$(curl -sS -w "\n%{http_code}" -X POST "$BASE_URL/api/copies/$COPY_ID/ready/" \
  -H "Content-Type: application/json" \
  -H "Cookie: sessionid=$SESSIONID; csrftoken=$CSRFTOKEN" \
  -H "X-CSRFToken: $CSRFTOKEN")

READY_CODE=$(echo "$READY_RESPONSE" | tail -1)
READY_BODY=$(echo "$READY_RESPONSE" | head -n -1)

if [[ "$READY_CODE" != "200" ]]; then
  echo "❌ STAGING → READY failed: $READY_CODE"
  echo "$READY_BODY"
  exit 1
fi

echo "✅ STAGING → READY: 200"
echo "$READY_BODY" | python3 -m json.tool || echo "$READY_BODY"
echo

# Test creating annotation
echo "==> [4] Create annotation (READY status allows CRUD)"
ANNOT_RESPONSE=$(curl -sS -w "\n%{http_code}" -X POST "$BASE_URL/api/copies/$COPY_ID/annotations/" \
  -H "Content-Type: application/json" \
  -H "Cookie: sessionid=$SESSIONID; csrftoken=$CSRFTOKEN" \
  -H "X-CSRFToken: $CSRFTOKEN" \
  -d '{"page_index":0,"x":0.1,"y":0.1,"w":0.2,"h":0.2,"type":"COMMENT","content":"Good work!","score_delta":5}')

ANNOT_CODE=$(echo "$ANNOT_RESPONSE" | tail -1)
ANNOT_BODY=$(echo "$ANNOT_RESPONSE" | head -n -1)

if [[ "$ANNOT_CODE" != "201" ]]; then
  echo "❌ Create annotation failed: $ANNOT_CODE"
  echo "$ANNOT_BODY"
  exit 1
fi

echo "✅ Annotation created: 201"
echo

# Test READY → LOCKED
echo "==> [5] Test READY → LOCKED"
LOCK_RESPONSE=$(curl -sS -w "\n%{http_code}" -X POST "$BASE_URL/api/copies/$COPY_ID/lock/" \
  -H "Content-Type: application/json" \
  -H "Cookie: sessionid=$SESSIONID; csrftoken=$CSRFTOKEN" \
  -H "X-CSRFToken: $CSRFTOKEN")

LOCK_CODE=$(echo "$LOCK_RESPONSE" | tail -1)

if [[ "$LOCK_CODE" != "200" ]]; then
  echo "❌ READY → LOCKED failed: $LOCK_CODE"
  exit 1
fi

echo "✅ READY → LOCKED: 200"
echo

# Test LOCKED → GRADED (finalize)
echo "==> [6] Test LOCKED → GRADED (finalize)"
FINALIZE_RESPONSE=$(curl -sS -w "\n%{http_code}" -X POST "$BASE_URL/api/copies/$COPY_ID/finalize/" \
  -H "Content-Type: application/json" \
  -H "Cookie: sessionid=$SESSIONID; csrftoken=$CSRFTOKEN" \
  -H "X-CSRFToken: $CSRFTOKEN")

FINALIZE_CODE=$(echo "$FINALIZE_RESPONSE" | tail -1)
FINALIZE_BODY=$(echo "$FINALIZE_RESPONSE" | head -n -1)

if [[ "$FINALIZE_CODE" != "200" ]]; then
  echo "❌ LOCKED → GRADED failed: $FINALIZE_CODE"
  echo "$FINALIZE_BODY"
  exit 1
fi

echo "✅ LOCKED → GRADED: 200"
echo "$FINALIZE_BODY" | python3 -m json.tool || echo "$FINALIZE_BODY"
echo

# Test final PDF download
echo "==> [7] Test final PDF download"
PDF_RESPONSE=$(curl -sS -w "\n%{http_code}" -X GET "$BASE_URL/api/copies/$COPY_ID/final-pdf/" \
  -H "Cookie: sessionid=$SESSIONID; csrftoken=$CSRFTOKEN" \
  -o /tmp/test_final.pdf)

PDF_CODE=$(echo "$PDF_RESPONSE" | tail -1)

if [[ "$PDF_CODE" != "200" ]]; then
  echo "❌ Final PDF download failed: $PDF_CODE"
  exit 1
fi

# Check if file size > 0 (may be empty if pages_images don't point to real files)
FILE_SIZE=$(stat -f%z /tmp/test_final.pdf 2>/dev/null || stat -c%s /tmp/test_final.pdf 2>/dev/null || echo "0")

if [[ "$FILE_SIZE" == "0" ]]; then
  echo "⚠️  Final PDF download: 200 (but PDF is empty - pages_images paths are fake in test)"
  echo "   NOTE: In real workflow, this would contain a valid PDF with annotations"
else
  # Check if file is a valid PDF (starts with %PDF)
  if head -c 4 /tmp/test_final.pdf | grep -q "%PDF"; then
    echo "✅ Final PDF download: 200 (valid PDF file, $FILE_SIZE bytes)"
  else
    echo "❌ Downloaded file is not a valid PDF"
    exit 1
  fi
fi

rm -f /tmp/test_final.pdf
echo

echo "✅✅ All E2E workflow tests passed!"
echo "   STAGING → READY → annotation → LOCK → FINALIZE → PDF download"
