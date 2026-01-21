#!/usr/bin/env bash
set -euo pipefail

BASE_URL="http://localhost:8088"
COPY_ID="ee909bf6-a0da-474c-b5b1-344e8cf48144"

echo "==> Testing P0 Validation with COPY_ID=$COPY_ID"
echo

# Get session and CSRF token
echo "==> [1] Login and get session"
LOGIN_RESPONSE=$(curl -sS -i -X POST "$BASE_URL/api/login/" \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"adminpass123"}')

# Extract sessionid from Set-Cookie header
SESSIONID=$(echo "$LOGIN_RESPONSE" | grep -i "set-cookie.*sessionid" | sed 's/.*sessionid=\([^;]*\).*/\1/' | head -1)
CSRFTOKEN=$(echo "$LOGIN_RESPONSE" | grep -i "set-cookie.*csrftoken" | sed 's/.*csrftoken=\([^;]*\).*/\1/' | head -1)

echo "Session ID: ${SESSIONID:0:20}..."
echo "CSRF Token: ${CSRFTOKEN:0:20}..."
echo

test_request() {
  local method="$1"
  local endpoint="$2"
  local data="$3"
  local expected_code="$4"
  local label="$5"

  response=$(curl -sS -w "\n%{http_code}" -X "$method" "$BASE_URL$endpoint" \
    -H "Content-Type: application/json" \
    -H "Cookie: sessionid=$SESSIONID; csrftoken=$CSRFTOKEN" \
    -H "X-CSRFToken: $CSRFTOKEN" \
    -d "$data")

  http_code=$(echo "$response" | tail -1)
  body=$(echo "$response" | head -n -1)

  if [[ "$http_code" == "$expected_code" ]]; then
    echo "✅ $label -> $http_code"
    return 0
  else
    echo "❌ $label -> expected $expected_code, got $http_code"
    echo "Response: $body"
    return 1
  fi
}

echo "==> [2] Test #1: w = 0 => 400"
test_request POST "/api/copies/$COPY_ID/annotations/" \
  '{"page_index":0,"x":0.1,"y":0.1,"w":0,"h":0.2,"type":"COMMENT","content":"w=0"}' \
  "400" "w=0 rejected"

echo

echo "==> [3] Test #2: x+w > 1 => 400"
test_request POST "/api/copies/$COPY_ID/annotations/" \
  '{"page_index":0,"x":0.9,"y":0.1,"w":0.2,"h":0.2,"type":"COMMENT","content":"overflow"}' \
  "400" "x+w overflow rejected"

echo

echo "==> [4] Test #3: page_index out of bounds => 400"
test_request POST "/api/copies/$COPY_ID/annotations/" \
  '{"page_index":2,"x":0.1,"y":0.1,"w":0.2,"h":0.2,"type":"COMMENT","content":"bad page"}' \
  "400" "page_index out of bounds rejected"

echo

echo "==> [5] Test #4a: Create annotation near edge => 201"
response=$(curl -sS -w "\n%{http_code}" -X POST "$BASE_URL/api/copies/$COPY_ID/annotations/" \
  -H "Content-Type: application/json" \
  -H "Cookie: sessionid=$SESSIONID; csrftoken=$CSRFTOKEN" \
  -H "X-CSRFToken: $CSRFTOKEN" \
  -d '{"page_index":0,"x":0.9,"y":0.1,"w":0.1,"h":0.2,"type":"COMMENT","content":"near edge"}')

http_code=$(echo "$response" | tail -1)
body=$(echo "$response" | head -n -1)

if [[ "$http_code" == "201" ]]; then
  echo "✅ create near-edge annotation -> 201"
  ANNOT_ID=$(echo "$body" | python3 -c "import sys, json; print(json.load(sys.stdin)['id'])")
  echo "Created annotation: $ANNOT_ID"
else
  echo "❌ Failed to create annotation: $http_code"
  echo "$body"
  exit 1
fi

echo

echo "==> [6] Test #4b: PATCH w=0.2 causing overflow => 400"
test_request PATCH "/api/annotations/$ANNOT_ID/" \
  '{"w":0.2}' \
  "400" "PATCH partial overflow rejected"

echo
echo "✅✅ All 4 P0 validation tests passed!"
