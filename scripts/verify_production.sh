#!/usr/bin/env bash
# ============================================================
# Korrigo Production Verification Script
# Run directly on the production server (korrigo.labomaths.tn)
# ============================================================
set -euo pipefail

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

ok()   { echo -e "${GREEN}✅ $*${NC}"; }
fail() { echo -e "${RED}❌ $*${NC}"; ERRORS=$((ERRORS+1)); }
warn() { echo -e "${YELLOW}⚠️  $*${NC}"; }
ERRORS=0

echo "========================================"
echo "  Korrigo Production Health Check"
echo "  $(date)"
echo "========================================"
echo ""

# --- 1. Docker containers ---
echo "=== 1. Docker Containers ==="
COMPOSE_FILE=""
for f in docker-compose.prod.yml infra/docker/docker-compose.prod.yml; do
  [ -f "$f" ] && COMPOSE_FILE="$f" && break
done

if [ -z "$COMPOSE_FILE" ]; then
  fail "docker-compose.prod.yml not found"
else
  echo "Compose file: $COMPOSE_FILE"
  echo ""
  docker compose -f "$COMPOSE_FILE" ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}" 2>/dev/null || docker compose -f "$COMPOSE_FILE" ps

  # Check all services are running
  RUNNING=$(docker compose -f "$COMPOSE_FILE" ps --status running -q 2>/dev/null | wc -l)
  TOTAL=$(docker compose -f "$COMPOSE_FILE" ps -q 2>/dev/null | wc -l)
  if [ "$RUNNING" -eq "$TOTAL" ] && [ "$TOTAL" -gt 0 ]; then
    ok "$RUNNING/$TOTAL containers running"
  else
    fail "Only $RUNNING/$TOTAL containers running"
  fi
fi
echo ""

# --- 2. Backend health ---
echo "=== 2. Backend Health ==="
HEALTH_CODE=$(curl -sf --max-time 5 -o /dev/null -w "%{http_code}" http://127.0.0.1:8088/api/health/live/ 2>/dev/null || echo "000")
if [ "$HEALTH_CODE" = "200" ]; then
  ok "Backend health: HTTP $HEALTH_CODE"
else
  fail "Backend health: HTTP $HEALTH_CODE"
fi
echo ""

# --- 3. Frontend ---
echo "=== 3. Frontend ==="
FRONT_CODE=$(curl -sf --max-time 5 -o /dev/null -w "%{http_code}" http://127.0.0.1:8088/ 2>/dev/null || echo "000")
if [ "$FRONT_CODE" = "200" ]; then
  ok "Frontend: HTTP $FRONT_CODE"
else
  fail "Frontend: HTTP $FRONT_CODE"
fi
echo ""

# --- 4. HTTPS external access ---
echo "=== 4. HTTPS External Access ==="
EXT_CODE=$(curl -sf --max-time 10 -o /dev/null -w "%{http_code}" https://korrigo.labomaths.tn/ 2>/dev/null || echo "000")
if [ "$EXT_CODE" = "200" ]; then
  ok "HTTPS frontend: HTTP $EXT_CODE"
else
  warn "HTTPS frontend: HTTP $EXT_CODE (may need external DNS)"
fi

API_CODE=$(curl -sf --max-time 10 -o /dev/null -w "%{http_code}" https://korrigo.labomaths.tn/api/health/live/ 2>/dev/null || echo "000")
if [ "$API_CODE" = "200" ]; then
  ok "HTTPS API health: HTTP $API_CODE"
else
  warn "HTTPS API health: HTTP $API_CODE"
fi
echo ""

# --- 5. Docker image versions ---
echo "=== 5. Docker Image Versions ==="
if [ -n "$COMPOSE_FILE" ]; then
  docker compose -f "$COMPOSE_FILE" images --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}" 2>/dev/null || docker compose -f "$COMPOSE_FILE" images
fi
echo ""

# --- 6. Current Git SHA (if available) ---
echo "=== 6. Deployed Version ==="
if [ -n "$COMPOSE_FILE" ]; then
  BACKEND_IMAGE=$(docker compose -f "$COMPOSE_FILE" images backend --format "{{.Tag}}" 2>/dev/null | head -1 || echo "unknown")
  echo "Backend image tag: $BACKEND_IMAGE"
  
  NGINX_IMAGE=$(docker compose -f "$COMPOSE_FILE" images nginx --format "{{.Tag}}" 2>/dev/null | head -1 || echo "unknown")
  echo "Nginx image tag: $NGINX_IMAGE"
fi

# Check expected SHA from latest commit
EXPECTED_SHA="11baac1599176f7abd87b13f407a49c837edd27e"
echo "Expected SHA: ${EXPECTED_SHA:0:8}"
echo ""

# --- 7. Recent backend logs (errors only) ---
echo "=== 7. Recent Backend Errors (last 50 lines) ==="
if [ -n "$COMPOSE_FILE" ]; then
  RECENT_ERRORS=$(docker compose -f "$COMPOSE_FILE" logs --tail=50 backend 2>&1 | grep -iE "(error|exception|traceback|critical)" | tail -5 || true)
  if [ -z "$RECENT_ERRORS" ]; then
    ok "No recent errors in backend logs"
  else
    warn "Recent errors found:"
    echo "$RECENT_ERRORS"
  fi
fi
echo ""

# --- 8. Database connectivity ---
echo "=== 8. Database ==="
if [ -n "$COMPOSE_FILE" ]; then
  DB_CHECK=$(docker compose -f "$COMPOSE_FILE" exec -T backend python -c "
import django, os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()
from django.db import connection
cursor = connection.cursor()
cursor.execute('SELECT 1')
print('OK')
" 2>/dev/null || echo "FAIL")
  if [ "$DB_CHECK" = "OK" ]; then
    ok "Database connection OK"
  else
    fail "Database connection failed"
  fi
fi
echo ""

# --- 9. Disk space ---
echo "=== 9. Disk Space ==="
df -h / | tail -1 | awk '{printf "Used: %s / %s (%s)\n", $3, $2, $5}'
DISK_PCT=$(df / | tail -1 | awk '{print $5}' | tr -d '%')
if [ "$DISK_PCT" -lt 80 ]; then
  ok "Disk usage: ${DISK_PCT}%"
elif [ "$DISK_PCT" -lt 90 ]; then
  warn "Disk usage: ${DISK_PCT}% (getting full)"
else
  fail "Disk usage: ${DISK_PCT}% (CRITICAL)"
fi
echo ""

# --- Summary ---
echo "========================================"
if [ "$ERRORS" -eq 0 ]; then
  echo -e "${GREEN}✅ ALL CHECKS PASSED${NC}"
else
  echo -e "${RED}❌ $ERRORS CHECK(S) FAILED${NC}"
fi
echo "========================================"
exit $ERRORS
