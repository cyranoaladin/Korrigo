#!/usr/bin/env bash
set -uo pipefail
G="\033[0;32m"; R="\033[0;31m"; Y="\033[1;33m"; N="\033[0m"
ok()   { echo -e "${G}✅ $*${N}"; }
fail() { echo -e "${R}❌ $*${N}"; E=$((E+1)); }
warn() { echo -e "${Y}⚠️  $*${N}"; }
E=0

echo "========================================"
echo "  Korrigo Production Health Check"
echo "  $(date)"
echo "========================================"
echo ""

# --- Find project dir ---
PROJ=""
for d in /root/korrigo /root/Korrigo /home/ubuntu/korrigo /opt/korrigo; do
  [ -d "$d/infra/docker" ] && PROJ="$d" && break
done
# Also check current dir
[ -z "$PROJ" ] && [ -d "./infra/docker" ] && PROJ="$(pwd)"

if [ -z "$PROJ" ]; then
  warn "Project dir not auto-detected. Searching..."
  PROJ=$(find / -maxdepth 4 -name "docker-compose.prod.yml" -path "*/infra/docker/*" 2>/dev/null | head -1 | sed 's|/infra/docker/docker-compose.prod.yml||')
fi

if [ -z "$PROJ" ]; then
  fail "Cannot find Korrigo project directory"
  echo "Please run: PROJ=/path/to/korrigo bash /tmp/verify_korrigo.sh"
  exit 1
fi

echo "Project dir: $PROJ"
CF="$PROJ/infra/docker/docker-compose.prod.yml"
echo "Compose file: $CF"
echo ""

# --- 1. Containers ---
echo "=== 1. Docker Containers ==="
docker compose -f "$CF" ps 2>/dev/null || docker-compose -f "$CF" ps 2>/dev/null || fail "Cannot list containers"
R=$(docker compose -f "$CF" ps --status running -q 2>/dev/null | wc -l || echo 0)
T=$(docker compose -f "$CF" ps -q 2>/dev/null | wc -l || echo 0)
if [ "$R" -gt 0 ] && [ "$R" -eq "$T" ]; then
  ok "$R/$T containers running"
else
  fail "Only $R/$T containers running"
fi
echo ""

# --- 2. Backend Health (internal) ---
echo "=== 2. Backend Health (internal) ==="
HC=$(curl -sf --max-time 5 -o /dev/null -w "%{http_code}" http://127.0.0.1:8088/api/health/live/ 2>/dev/null || echo "000")
[ "$HC" = "200" ] && ok "Backend: HTTP $HC" || fail "Backend: HTTP $HC"
echo ""

# --- 3. Frontend (internal) ---
echo "=== 3. Frontend (internal) ==="
FC=$(curl -sf --max-time 5 -o /dev/null -w "%{http_code}" http://127.0.0.1:8088/ 2>/dev/null || echo "000")
[ "$FC" = "200" ] && ok "Frontend: HTTP $FC" || fail "Frontend: HTTP $FC"
echo ""

# --- 4. HTTPS external ---
echo "=== 4. HTTPS External ==="
EC=$(curl -sf --max-time 10 -o /dev/null -w "%{http_code}" https://korrigo.labomaths.tn/api/health/live/ 2>/dev/null || echo "000")
[ "$EC" = "200" ] && ok "HTTPS API: HTTP $EC" || warn "HTTPS API: HTTP $EC"
EF=$(curl -sf --max-time 10 -o /dev/null -w "%{http_code}" https://korrigo.labomaths.tn/ 2>/dev/null || echo "000")
[ "$EF" = "200" ] && ok "HTTPS Frontend: HTTP $EF" || warn "HTTPS Frontend: HTTP $EF"
echo ""

# --- 5. Docker Images ---
echo "=== 5. Docker Images ==="
docker compose -f "$CF" images 2>/dev/null || true
echo ""

# --- 6. Recent Errors ---
echo "=== 6. Recent Backend Errors (last 100 lines) ==="
ERR=$(docker compose -f "$CF" logs --tail=100 backend 2>&1 | grep -iE "error|exception|traceback|critical" | grep -v "ERRORS FOUND" | tail -5 || true)
if [ -z "$ERR" ]; then
  ok "No recent errors"
else
  warn "Errors found:"
  echo "$ERR"
fi
echo ""

# --- 7. Database ---
echo "=== 7. Database ==="
DB=$(docker compose -f "$CF" exec -T backend python manage.py check --database default 2>&1 | tail -1 || echo "FAIL")
echo "$DB"
echo "$DB" | grep -q "no issues" && ok "Database OK" || fail "Database check failed"
echo ""

# --- 8. Migrations ---
echo "=== 8. Pending Migrations ==="
MIG=$(docker compose -f "$CF" exec -T backend python manage.py showmigrations --plan 2>&1 | grep "\[ \]" | head -5 || true)
if [ -z "$MIG" ]; then
  ok "All migrations applied"
else
  warn "Pending migrations:"
  echo "$MIG"
fi
echo ""

# --- 9. Disk Space ---
echo "=== 9. Disk Space ==="
df -h / | tail -1
DP=$(df / | tail -1 | awk '{print $5}' | tr -d '%')
if [ "$DP" -lt 80 ]; then
  ok "Disk: ${DP}%"
elif [ "$DP" -lt 90 ]; then
  warn "Disk: ${DP}% (getting full)"
else
  fail "Disk: ${DP}% CRITICAL"
fi
echo ""

# --- 10. Memory ---
echo "=== 10. Memory ==="
free -h | head -2
echo ""

# --- Summary ---
echo "========================================"
if [ "$E" -eq 0 ]; then
  echo -e "${G}✅ ALL CHECKS PASSED${N}"
else
  echo -e "${R}❌ $E CHECK(S) FAILED${N}"
fi
echo "========================================"
exit $E
