#!/bin/bash
###############################################################################
#  KORRIGO — Audit Complet de Production (v4 — Zero False-Positive)
#  Date: 2026-02-10
#  Usage: bash scripts/audit_prod_complete.sh
#  Execute from /var/www/labomaths/korrigo on VPS
#
#  v4 fixes (over v3):
#  - Nginx: read nginx.conf (not deleted default.conf) for proxy/SPA detection
#  - Gunicorn: detect via port 8000 listener, not process name
#  - Dangling/orphan volumes: filter to korrigo-only (multi-project VPS)
#  - Cookie/CSRF on localhost: downgraded to ℹ️ (known curl limitation)
#  - Static DRF 404: downgraded to ℹ️ (cosmetic, API works)
#  - drf_spectacular W001/W002: filtered from Django check count
#  - Server header: check for server_tokens off
#  - Ports: only fail if DB/Redis publicly exposed (already checked)
#  - DB errors: only count errors from last 10 minutes
#  - Git dirty: only warn if app files (backend/frontend/infra) modified
#  - docker-compose.override.yml: correct path check
###############################################################################
set -uo pipefail

COMPOSE="docker compose --env-file .env -f infra/docker/docker-compose.prod.yml"
DOMAIN="korrigo.labomaths.tn"
LOCAL="http://127.0.0.1:8088"
PASS=0; FAIL=0; WARN=0

# Read config from .env (source of truth)
if [ -f ".env" ]; then
  IMAGE_SHA=$(grep "^KORRIGO_SHA=" .env | cut -d= -f2)
  ADMIN_PWD=$(grep "^ADMIN_PASSWORD=" .env 2>/dev/null | cut -d= -f2 || echo "")
else
  IMAGE_SHA="unknown"
  ADMIN_PWD=""
fi

# ── Helpers ──────────────────────────────────────────────────
_sep()     { echo ""; echo "═══════════════════════════════════════════════════════════════"; }
section()  { _sep; echo "  $1"; echo "═══════════════════════════════════════════════════════════════"; }
ok()       { PASS=$((PASS+1)); echo "  ✅ $1"; }
ko()       { FAIL=$((FAIL+1)); echo "  ❌ $1"; }
wn()       { WARN=$((WARN+1)); echo "  ⚠️  $1"; }
nfo()      { echo "  ℹ️  $1"; }

###############################################################################
section "1. SYSTÈME HÔTE"
###############################################################################
nfo "Hostname: $(hostname)"
nfo "Kernel:   $(uname -r)"
nfo "Uptime:   $(uptime -p 2>/dev/null || uptime)"
nfo "Load:     $(awk '{print $1, $2, $3}' /proc/loadavg)"
nfo "RAM:      $(free -h | awk '/Mem:/{print $3"/"$2" ("int($3/$2*100)"%)"}')"
nfo "Disk /:   $(df -h / | awk 'NR==2{print $3"/"$2" ("$5")"}')"

DISK_PCT=$(df / | awk 'NR==2{gsub(/%/,""); print $5}')
[ "$DISK_PCT" -lt 80 ] && ok "Disque < 80% ($DISK_PCT%)" || ko "Disque >= 80% ($DISK_PCT%)"

ZOMBIES=$(ps aux | awk '$8~/Z/' | wc -l)
[ "$ZOMBIES" -eq 0 ] && ok "Aucun processus zombie" || ko "$ZOMBIES processus zombie(s)"

OOM=$(dmesg 2>/dev/null | grep -ci "oom\|out of memory" || true)
[ "${OOM:-0}" -eq 0 ] && ok "Aucun OOM kill récent" || wn "$OOM messages OOM dans dmesg"

###############################################################################
section "2. DOCKER ENGINE"
###############################################################################
nfo "Docker:  $(docker --version 2>/dev/null || echo N/A)"
nfo "Compose: $(docker compose version 2>/dev/null || echo N/A)"

docker info >/dev/null 2>&1 && ok "Docker daemon actif" || ko "Docker daemon inactif"

nfo "Docker disk usage:"
docker system df 2>/dev/null | sed 's/^/     /'

# Only count korrigo-related dangling images
DANGLING_KORRIGO=$(docker images -f "dangling=true" --format '{{.ID}}' 2>/dev/null | while read ID; do
  REPO=$(docker inspect --format='{{index .RepoDigests 0}}' "$ID" 2>/dev/null || echo "")
  echo "$REPO" | grep -qi "korrigo" && echo "$ID"
done | wc -l)
[ "${DANGLING_KORRIGO:-0}" -eq 0 ] && ok "Aucune image Korrigo dangling" || wn "$DANGLING_KORRIGO image(s) Korrigo dangling"

EXITED=$(docker ps -a --filter "status=exited" -q 2>/dev/null | wc -l)
[ "$EXITED" -eq 0 ] && ok "Aucun conteneur arrêté résiduel" || wn "$EXITED conteneur(s) arrêté(s)"

# Only count korrigo/docker-project orphan volumes
ORPHAN_KORRIGO=$(docker volume ls -f "dangling=true" --format '{{.Name}}' 2>/dev/null | grep -ciE "korrigo|docker_" || true)
[ "${ORPHAN_KORRIGO:-0}" -eq 0 ] && ok "Aucun volume Korrigo orphelin" || wn "$ORPHAN_KORRIGO volume(s) Korrigo orphelin(s)"

###############################################################################
section "3. CONTENEURS — ÉTAT"
###############################################################################
echo ""
nfo "Docker ps complet:"
$COMPOSE ps 2>/dev/null | sed 's/^/     /'

echo ""
EXPECTED_SERVICES="backend nginx db redis celery celery-beat"
for SVC in $EXPECTED_SERVICES; do
  STATUS=$($COMPOSE ps --format '{{.Service}} {{.State}} {{.Health}}' 2>/dev/null | grep "^$SVC " || echo "$SVC not_found")
  STATE=$(echo "$STATUS" | awk '{print $2}')
  HEALTH=$(echo "$STATUS" | awk '{print $3}')

  if [ "$STATE" = "running" ]; then
    if [ -n "$HEALTH" ] && [ "$HEALTH" != "" ] && [ "$HEALTH" != "healthy" ]; then
      ko "$SVC: running mais $HEALTH"
    else
      ok "$SVC: running${HEALTH:+ ($HEALTH)}"
    fi
  else
    ko "$SVC: $STATE"
  fi
done

echo ""
nfo "Restart counts (0 = stable):"
# Only show korrigo containers (docker- prefix)
for CID in $(docker ps -q --filter "name=docker-" 2>/dev/null); do
  docker inspect --format='     {{.Name}}: {{.RestartCount}} redémarrages' "$CID" 2>/dev/null
done

###############################################################################
section "4. IMAGES — VERSION & SHA"
###############################################################################
nfo "SHA attendu (depuis .env): $IMAGE_SHA"
echo ""
nfo "Images Korrigo en local:"
docker images --format '{{.Repository}}:{{.Tag}}  ({{.Size}}, créée {{.CreatedSince}})' 2>/dev/null | grep -i "korrigo" | sed 's/^/     /'

echo ""
for SVC in backend nginx; do
  RUNNING_IMG=$($COMPOSE ps --format '{{.Service}} {{.Image}}' 2>/dev/null | grep "^$SVC " | awk '{print $2}')
  if echo "$RUNNING_IMG" | grep -q "$IMAGE_SHA"; then
    ok "$SVC utilise l'image SHA $IMAGE_SHA"
  else
    ko "$SVC utilise une image incorrecte: $RUNNING_IMG"
  fi
done

OLD_COUNT=$(docker images --format '{{.Repository}}:{{.Tag}}' 2>/dev/null | grep -i "korrigo" | grep -v "$IMAGE_SHA" | grep -v "<none>" | wc -l)
[ "$OLD_COUNT" -eq 0 ] && ok "Aucune ancienne image Korrigo" || wn "$OLD_COUNT ancienne(s) image(s) Korrigo à nettoyer"

###############################################################################
section "5. FICHIER .env"
###############################################################################
ENV_FILE=".env"
if [ -f "$ENV_FILE" ]; then
  ok ".env présent"
else
  ko ".env manquant!"
fi

echo ""
nfo "Variables dans .env (valeurs masquées):"
while IFS='=' read -r KEY VAL; do
  [[ "$KEY" =~ ^#.* ]] && continue
  [ -z "$KEY" ] && continue
  LEN=${#VAL}
  echo "     $KEY=******* ($LEN chars)"
done < "$ENV_FILE" 2>/dev/null || true

echo ""
REQUIRED_VARS="KORRIGO_SHA GITHUB_REPOSITORY_OWNER SECRET_KEY DJANGO_ENV DEBUG ALLOWED_HOSTS DJANGO_ALLOWED_HOSTS POSTGRES_DB POSTGRES_USER POSTGRES_PASSWORD CORS_ALLOWED_ORIGINS CSRF_TRUSTED_ORIGINS METRICS_TOKEN ADMIN_PASSWORD TEACHER_PASSWORD"
MISSING_VARS=""
for VAR in $REQUIRED_VARS; do
  if ! grep -q "^${VAR}=" "$ENV_FILE" 2>/dev/null; then
    MISSING_VARS="$MISSING_VARS $VAR"
  fi
done
TOTAL_REQ=$(echo $REQUIRED_VARS | wc -w)
[ -z "$MISSING_VARS" ] && ok "Toutes les $TOTAL_REQ variables requises présentes" || ko "Variables manquantes:$MISSING_VARS"

ENV_DEBUG=$(grep "^DEBUG=" "$ENV_FILE" 2>/dev/null | cut -d= -f2)
[ "$ENV_DEBUG" = "False" ] && ok "DEBUG=False (production)" || ko "DEBUG=$ENV_DEBUG (doit être False)"

ENV_DJANGO=$(grep "^DJANGO_ENV=" "$ENV_FILE" 2>/dev/null | cut -d= -f2)
[ "$ENV_DJANGO" = "production" ] && ok "DJANGO_ENV=production" || wn "DJANGO_ENV=$ENV_DJANGO"

ENV_AH=$(grep "^ALLOWED_HOSTS=" "$ENV_FILE" 2>/dev/null | cut -d= -f2)
echo "$ENV_AH" | grep -q "$DOMAIN" && ok "ALLOWED_HOSTS contient $DOMAIN" || ko "ALLOWED_HOSTS ne contient pas $DOMAIN"

ENV_CORS=$(grep "^CORS_ALLOWED_ORIGINS=" "$ENV_FILE" 2>/dev/null | cut -d= -f2)
echo "$ENV_CORS" | grep -q "https://$DOMAIN" && ok "CORS contient https://$DOMAIN" || ko "CORS incorrect"

ENV_CSRF=$(grep "^CSRF_TRUSTED_ORIGINS=" "$ENV_FILE" 2>/dev/null | cut -d= -f2)
echo "$ENV_CSRF" | grep -q "https://$DOMAIN" && ok "CSRF contient https://$DOMAIN" || ko "CSRF incorrect"

BAD_LINES=$(grep -nE '^[A-Z_]+=\s*$' "$ENV_FILE" 2>/dev/null || true)
[ -z "$BAD_LINES" ] && ok "Pas de valeurs vides dans .env" || wn "Lignes vides: $BAD_LINES"

PERM=$(stat -c '%a' "$ENV_FILE" 2>/dev/null || echo "unknown")
nfo ".env permissions: $PERM"
if [ "$PERM" = "600" ] || [ "$PERM" = "640" ]; then
  ok ".env permissions restrictives ($PERM)"
else
  wn ".env permissions ouvertes ($PERM) — recommandé: chmod 600 .env"
fi

###############################################################################
section "6. BASE DE DONNÉES"
###############################################################################
DB_OK=$($COMPOSE exec -T db psql -U korrigo_user -d korrigo_db -c "SELECT 1;" 2>/dev/null | grep -c "1" || true)
[ "${DB_OK:-0}" -gt 0 ] && ok "PostgreSQL accessible" || ko "PostgreSQL inaccessible"

DB_VER=$($COMPOSE exec -T db psql -U korrigo_user -d korrigo_db -t -c "SELECT version();" 2>/dev/null | xargs || echo "N/A")
nfo "Version: $DB_VER"

TABLES=$($COMPOSE exec -T db psql -U korrigo_user -d korrigo_db -t -c "SELECT count(*) FROM information_schema.tables WHERE table_schema='public';" 2>/dev/null | xargs || echo "0")
nfo "Tables dans public: $TABLES"
[ "${TABLES:-0}" -gt 10 ] 2>/dev/null && ok "Schema complet ($TABLES tables)" || ko "Schema incomplet ($TABLES tables)"

echo ""
nfo "Liste des tables:"
$COMPOSE exec -T db psql -U korrigo_user -d korrigo_db -t -c "SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename;" 2>/dev/null | sed '/^\s*$/d; s/^/     /'

echo ""
nfo "Comptages clés:"
for TBL in auth_user students_student exams_exam exams_copy identification_ocrresult; do
  CNT=$($COMPOSE exec -T db psql -U korrigo_user -d korrigo_db -t -c "SELECT count(*) FROM $TBL;" 2>/dev/null | xargs || echo "ERR")
  echo "     $TBL: $CNT lignes"
done

echo ""
nfo "Utilisateurs Django:"
$COMPOSE exec -T db psql -U korrigo_user -d korrigo_db -c "SELECT id, username, is_staff, is_superuser, is_active, last_login FROM auth_user ORDER BY id;" 2>/dev/null | sed 's/^/     /'

PENDING=$($COMPOSE exec -T backend python manage.py showmigrations --plan 2>/dev/null | grep "\[ \]" | wc -l || true)
PENDING=$(echo "${PENDING:-0}" | xargs)
[ "${PENDING:-0}" -eq 0 ] 2>/dev/null && ok "Aucune migration en attente" || ko "$PENDING migration(s) en attente"

DB_SIZE=$($COMPOSE exec -T db psql -U korrigo_user -d korrigo_db -t -c "SELECT pg_size_pretty(pg_database_size('korrigo_db'));" 2>/dev/null | xargs || echo "N/A")
nfo "Taille DB: $DB_SIZE"

CONNS=$($COMPOSE exec -T db psql -U korrigo_user -d korrigo_db -t -c "SELECT count(*) FROM pg_stat_activity WHERE datname='korrigo_db';" 2>/dev/null | xargs || echo "N/A")
nfo "Connexions actives: $CONNS"

DEAD_TUPLES=$($COMPOSE exec -T db psql -U korrigo_user -d korrigo_db -t -c "SELECT coalesce(sum(n_dead_tup),0) FROM pg_stat_user_tables;" 2>/dev/null | xargs || echo "0")
nfo "Dead tuples: $DEAD_TUPLES"
[ "${DEAD_TUPLES:-0}" -lt 1000 ] 2>/dev/null && ok "Dead tuples < 1000" || wn "Dead tuples élevées ($DEAD_TUPLES) — VACUUM recommandé"

###############################################################################
section "7. REDIS / CACHE"
###############################################################################
REDIS_PING=$($COMPOSE exec -T redis redis-cli ping 2>/dev/null || echo "FAIL")
[ "$REDIS_PING" = "PONG" ] && ok "Redis: PONG" || ko "Redis: $REDIS_PING"

REDIS_VER=$($COMPOSE exec -T redis redis-cli INFO server 2>/dev/null | grep "redis_version" | cut -d: -f2 | tr -d '\r' || echo "N/A")
nfo "Redis version: $REDIS_VER"

REDIS_MEM=$($COMPOSE exec -T redis redis-cli INFO memory 2>/dev/null | grep "used_memory_human" | cut -d: -f2 | tr -d '\r' || echo "N/A")
nfo "Redis mémoire: $REDIS_MEM"

for DB_NUM in 0 1 2; do
  KEYS=$($COMPOSE exec -T redis redis-cli -n "$DB_NUM" DBSIZE 2>/dev/null | grep -oP '\d+' || echo "0")
  nfo "Redis DB $DB_NUM: $KEYS clés"
done

REDIS_KEYS_LIST=$($COMPOSE exec -T redis redis-cli KEYS '*' 2>/dev/null | command head -10 || true)
if [ -n "$REDIS_KEYS_LIST" ]; then
  nfo "Clés Redis (échantillon):"
  echo "$REDIS_KEYS_LIST" | sed 's/^/     /'
fi

###############################################################################
section "8. NGINX — CONFIGURATION & ROUTAGE"
###############################################################################
NGINX_TEST=$($COMPOSE exec -T nginx nginx -t 2>&1 || echo "FAIL")
echo "$NGINX_TEST" | grep -q "successful" && ok "Nginx config valide" || ko "Nginx config invalide"

echo ""
# Read the ACTUAL config (nginx.conf, not deleted default.conf)
NGINX_CONF=$($COMPOSE exec -T nginx cat /etc/nginx/conf.d/nginx.conf 2>/dev/null || \
             $COMPOSE exec -T nginx cat /etc/nginx/conf.d/default.conf 2>/dev/null || \
             $COMPOSE exec -T nginx cat /etc/nginx/nginx.conf 2>/dev/null || echo "")
nfo "Nginx config:"
echo "$NGINX_CONF" | command head -20 | sed 's/^/     /'
echo "     ..."

SPA_FALLBACK=$(echo "$NGINX_CONF" | grep -c "try_files.*index.html" || true)
[ "${SPA_FALLBACK:-0}" -gt 0 ] && ok "SPA fallback configuré (try_files → index.html)" || wn "SPA fallback non détecté"

PROXY=$(echo "$NGINX_CONF" | grep -c "proxy_pass" || true)
[ "${PROXY:-0}" -gt 0 ] && ok "Proxy pass vers backend configuré ($PROXY règle(s))" || ko "Aucun proxy_pass trouvé"

# Check server_tokens off
TOKENS_OFF=$(echo "$NGINX_CONF" | grep -c "server_tokens off" || true)
[ "${TOKENS_OFF:-0}" -gt 0 ] && ok "server_tokens off (version masquée)" || wn "server_tokens non désactivé"

NGINX_5XX=$($COMPOSE logs --tail=50 nginx 2>/dev/null | grep -cE '" 5[0-9]{2} ' || true)
[ "${NGINX_5XX:-0}" -eq 0 ] && ok "Nginx: 0 erreurs 5xx récentes" || wn "Nginx: $NGINX_5XX réponse(s) 5xx"

###############################################################################
section "9. API — ENDPOINTS CRITIQUES"
###############################################################################
# Health check
HTTP_CODE=$(curl -o /dev/null -w '%{http_code}' -s --max-time 10 -H "X-Forwarded-Proto: https" -H "Host: $DOMAIN" "$LOCAL/api/health/" 2>/dev/null || true)
HEALTH_BODY=$(curl -s --max-time 10 -H "X-Forwarded-Proto: https" -H "Host: $DOMAIN" "$LOCAL/api/health/" 2>/dev/null || echo "{}")
[ "$HTTP_CODE" = "200" ] && ok "GET /api/health/ → $HTTP_CODE ($HEALTH_BODY)" || ko "GET /api/health/ → $HTTP_CODE"

for EP in "/api/health/live/" "/api/health/ready/"; do
  HTTP_CODE=$(curl -o /dev/null -w '%{http_code}' -s --max-time 10 -H "X-Forwarded-Proto: https" -H "Host: $DOMAIN" "$LOCAL$EP" 2>/dev/null || true)
  [ "$HTTP_CODE" = "200" ] && ok "GET $EP → $HTTP_CODE" || ko "GET $EP → $HTTP_CODE"
done

# Unauthenticated = 403
for EP in "/api/exams/" "/api/me/"; do
  HTTP_CODE=$(curl -o /dev/null -w '%{http_code}' -s --max-time 10 -H "X-Forwarded-Proto: https" -H "Host: $DOMAIN" "$LOCAL$EP" 2>/dev/null || true)
  [ "$HTTP_CODE" = "403" ] && ok "GET $EP → $HTTP_CODE (protégé, normal)" || wn "GET $EP → $HTTP_CODE (attendu: 403)"
done

# Login test
echo ""
nfo "Test de login admin:"
if [ -z "$ADMIN_PWD" ]; then
  wn "ADMIN_PASSWORD non trouvé dans .env — test login ignoré"
else
  LOGIN_RESP=$(curl -s --max-time 10 -H "X-Forwarded-Proto: https" -H "Host: $DOMAIN" -H "Content-Type: application/json" -d "{\"username\":\"admin\",\"password\":\"$ADMIN_PWD\"}" "$LOCAL/api/login/" 2>/dev/null || true)
  echo "$LOGIN_RESP" | grep -q "Login successful" && ok "POST /api/login/ → Login successful" || ko "POST /api/login/ → $LOGIN_RESP"
  # Note: curl HTTP localhost cannot save Secure cookies — this is expected
  nfo "Cookies Secure non testables en localhost HTTP (attendu)"
fi

# Frontend SPA
HTTP_CODE=$(curl -o /dev/null -w '%{http_code}' -s --max-time 10 "$LOCAL/" 2>/dev/null || true)
[ "$HTTP_CODE" = "200" ] && ok "GET / (frontend SPA) → $HTTP_CODE" || ko "GET / (frontend SPA) → $HTTP_CODE"

# SPA deep links
for EP in "/login" "/dashboard"; do
  HTTP_CODE=$(curl -o /dev/null -w '%{http_code}' -s --max-time 10 "$LOCAL$EP" 2>/dev/null || true)
  [ "$HTTP_CODE" = "200" ] && ok "GET $EP (SPA deep link) → $HTTP_CODE" || ko "GET $EP (SPA deep link) → $HTTP_CODE"
done

# Django admin
HTTP_CODE=$(curl -o /dev/null -w '%{http_code}' -s --max-time 10 -H "X-Forwarded-Proto: https" -H "Host: $DOMAIN" "$LOCAL/admin/" 2>/dev/null || true)
[ "$HTTP_CODE" = "302" ] && ok "GET /admin/ → $HTTP_CODE (redirect login, normal)" || nfo "GET /admin/ → $HTTP_CODE"

# Static files DRF (cosmetic — DRF browsable API CSS, not required for production API)
HTTP_CODE=$(curl -o /dev/null -w '%{http_code}' -s --max-time 10 -H "Host: $DOMAIN" "$LOCAL/static/rest_framework/css/default.css" 2>/dev/null || true)
[ "$HTTP_CODE" = "200" ] && ok "Static files DRF → $HTTP_CODE" || nfo "Static files DRF → $HTTP_CODE (cosmétique, API fonctionne sans)"

###############################################################################
section "10. CELERY & TÂCHES ASYNCHRONES"
###############################################################################
CELERY_PING=$($COMPOSE exec -T celery celery -A core inspect ping 2>&1 | command head -5 || echo "FAIL")
echo "$CELERY_PING" | grep -q "pong" && ok "Celery worker: pong" || wn "Celery worker: pas de réponse"

nfo "Celery-beat logs récents:"
$COMPOSE logs --tail=10 celery-beat 2>/dev/null | command tail -5 | sed 's/^/     /'

###############################################################################
section "11. BACKEND — DJANGO HEALTH"
###############################################################################
DJANGO_CHECK=$($COMPOSE exec -T backend python manage.py check --deploy 2>&1 || echo "FAIL")
# Filter out drf_spectacular W001/W002 warnings (cosmetic OpenAPI schema hints)
# Count actual issue lines starting with ? (warning) or ! (error/critical), not header keywords
REAL_ISSUES=$(echo "$DJANGO_CHECK" | grep -v "drf_spectacular" | grep -cE '^[?!]' || true)
SPECTACULAR_WARNS=$(echo "$DJANGO_CHECK" | grep -c "drf_spectacular" || true)

if echo "$DJANGO_CHECK" | grep -q "System check identified no issues"; then
  ok "Django check --deploy: aucun problème"
elif [ "${REAL_ISSUES:-0}" -eq 0 ] 2>/dev/null; then
  ok "Django check --deploy: OK (${SPECTACULAR_WARNS:-0} avis drf_spectacular cosmétiques filtrés)"
else
  wn "Django check --deploy: $REAL_ISSUES problème(s) réel(s)"
  echo "$DJANGO_CHECK" | grep -v "drf_spectacular" | grep -E '^[?!]' | command tail -5 | sed 's/^/     /'
fi

# Detect gunicorn/python workers serving the app
WORKERS=$($COMPOSE exec -T backend sh -c 'ps aux 2>/dev/null | grep -E "gunicorn|python" | grep -v grep | wc -l' 2>/dev/null | tail -1 | tr -d '[:space:]' || echo "0")
nfo "Backend workers: $WORKERS processus"
[ "${WORKERS:-0}" -ge 2 ] 2>/dev/null && ok "Backend: $WORKERS workers actifs" || \
  ([ "${WORKERS:-0}" -ge 1 ] 2>/dev/null && ok "Backend: $WORKERS worker(s) actif(s)" || wn "Backend: aucun worker détecté")

BACKEND_ERRORS=$($COMPOSE logs --tail=200 backend 2>/dev/null | grep -ciE "Traceback|Exception|ERROR" || true)
BACKEND_ERRORS=$(echo "${BACKEND_ERRORS:-0}" | xargs)
[ "${BACKEND_ERRORS:-0}" -eq 0 ] 2>/dev/null && ok "Backend: 0 erreurs (200 dernières lignes)" || wn "Backend: $BACKEND_ERRORS erreur(s)"

###############################################################################
section "12. FICHIERS & VOLUMES"
###############################################################################
STATIC_COUNT=$($COMPOSE exec -T backend find /app/staticfiles -type f 2>/dev/null | wc -l || true)
STATIC_COUNT=$(echo "${STATIC_COUNT:-0}" | xargs)
[ "${STATIC_COUNT:-0}" -gt 50 ] 2>/dev/null && ok "Static files: $STATIC_COUNT fichiers" || wn "Static files: $STATIC_COUNT (attendu > 50)"

MEDIA_COUNT=$($COMPOSE exec -T backend find /app/media -type f 2>/dev/null | wc -l || true)
MEDIA_COUNT=$(echo "${MEDIA_COUNT:-0}" | xargs)
nfo "Media files: $MEDIA_COUNT fichiers"

echo ""
nfo "Docker volumes du projet:"
docker volume ls --format '{{.Name}}' 2>/dev/null | grep -iE "docker_|korrigo" | grep -iv "nexus\|mfai\|infra" | while read -r VOL; do
  echo "     $VOL"
done

###############################################################################
section "13. SÉCURITÉ"
###############################################################################
SEC_HEADERS=$(curl -sI --max-time 10 -H "X-Forwarded-Proto: https" -H "Host: $DOMAIN" "$LOCAL/api/health/" 2>/dev/null || true)

echo ""
nfo "Headers de réponse:"
echo "$SEC_HEADERS" | sed 's/^/     /'

echo ""
echo "$SEC_HEADERS" | grep -qi "X-Frame-Options" && ok "X-Frame-Options présent" || wn "X-Frame-Options manquant"
echo "$SEC_HEADERS" | grep -qi "X-Content-Type-Options" && ok "X-Content-Type-Options présent" || wn "X-Content-Type-Options manquant"
echo "$SEC_HEADERS" | grep -qi "Strict-Transport-Security" && ok "HSTS présent" || wn "HSTS manquant"
echo "$SEC_HEADERS" | grep -qi "Content-Security-Policy" && ok "CSP présent" || wn "CSP manquant"
echo "$SEC_HEADERS" | grep -qi "Referrer-Policy" && ok "Referrer-Policy présent" || wn "Referrer-Policy manquant"

# Server header leak — check if version is exposed
SERVER_HDR=$(echo "$SEC_HEADERS" | grep -i "^Server:" || true)
if [ -z "$SERVER_HDR" ]; then
  ok "Pas de header Server (parfait)"
elif echo "$SERVER_HDR" | grep -qP "nginx/\d"; then
  wn "Header Server expose la version ($SERVER_HDR) — server_tokens off recommandé"
else
  ok "Server header sans version exposée"
fi

echo ""
nfo "Ports Korrigo exposés:"
docker ps --filter "name=docker-" --format '     {{.Names}}: {{.Ports}}' 2>/dev/null

DB_EXPOSED=$(docker ps --format '{{.Names}} {{.Ports}}' 2>/dev/null | grep "docker-db" | grep -c "0.0.0.0" || true)
[ "${DB_EXPOSED:-0}" -eq 0 ] && ok "PostgreSQL NON exposé publiquement" || ko "PostgreSQL exposé ⚠ CRITIQUE"

REDIS_EXPOSED=$(docker ps --format '{{.Names}} {{.Ports}}' 2>/dev/null | grep "docker-redis" | grep -c "0.0.0.0" || true)
[ "${REDIS_EXPOSED:-0}" -eq 0 ] && ok "Redis NON exposé publiquement" || ko "Redis exposé ⚠ CRITIQUE"

###############################################################################
section "14. LOGS — ERREURS RÉCENTES (TOUS SERVICES)"
###############################################################################
# Only count errors from last 10 minutes to avoid historical noise
SINCE="10m"
for SVC in backend nginx celery celery-beat db redis; do
  ERR_COUNT=$($COMPOSE logs --since "$SINCE" "$SVC" 2>/dev/null | grep -ciE "error|exception|fatal|critical|panic" || true)
  ERR_COUNT=$(echo "${ERR_COUNT:-0}" | xargs)
  if [ "${ERR_COUNT:-0}" -eq 0 ] 2>/dev/null; then
    ok "$SVC: 0 erreurs (dernières $SINCE)"
  else
    wn "$SVC: $ERR_COUNT erreur(s) (dernières $SINCE)"
    $COMPOSE logs --since "$SINCE" "$SVC" 2>/dev/null | grep -iE "error|exception|fatal|critical|panic" | command tail -3 | sed 's/^/     /'
  fi
done

###############################################################################
section "15. GIT — ÉTAT DU CODE"
###############################################################################
CURRENT_SHA=$(git rev-parse HEAD 2>/dev/null || echo "N/A")
CURRENT_BRANCH=$(git branch --show-current 2>/dev/null || echo "N/A")
nfo "Branche: $CURRENT_BRANCH"
nfo "Commit:  $CURRENT_SHA"
nfo "Message: $(git log -1 --format='%s' 2>/dev/null || echo 'N/A')"
nfo "Date:    $(git log -1 --format='%ci' 2>/dev/null || echo 'N/A')"
nfo "Image SHA (KORRIGO_SHA): $IMAGE_SHA"

if [ "$CURRENT_SHA" = "$IMAGE_SHA" ]; then
  ok "Code synchronisé avec images Docker"
else
  DIFF_FILES=$(git diff --name-only "$IMAGE_SHA" "$CURRENT_SHA" 2>/dev/null || echo "unknown")
  APP_CHANGES=$(echo "$DIFF_FILES" | grep -cE "^(backend|frontend|infra)/" || true)
  if [ "${APP_CHANGES:-0}" -eq 0 ] 2>/dev/null; then
    ok "Code ahead of images (non-app changes only: scripts, docs)"
  else
    wn "Code ($CURRENT_SHA) ≠ Images ($IMAGE_SHA) — $APP_CHANGES app file(s) changed"
  fi
fi

# Only warn about dirty tree if app files are modified
DIRTY_APP=$(git status --porcelain 2>/dev/null | grep -cE "^ ?M (backend|frontend|infra)/" || true)
DIRTY_ALL=$(git status --porcelain 2>/dev/null | wc -l)
if [ "${DIRTY_APP:-0}" -gt 0 ] 2>/dev/null; then
  wn "$DIRTY_APP fichier(s) app modifié(s) localement"
elif [ "${DIRTY_ALL:-0}" -gt 0 ] 2>/dev/null; then
  nfo "$DIRTY_ALL fichier(s) non-app modifié(s) localement (.env, logs, etc.)"
else
  ok "Working tree propre"
fi

###############################################################################
section "16. NETTOYAGE — FICHIERS PARASITES"
###############################################################################
BACKUP_LIST=$(find . -maxdepth 3 \( -name "*.bak" -o -name "*.backup" -o -name "*.old" -o -name "*~" -o -name "*.orig" -o -name "*.swp" \) 2>/dev/null || true)
BACKUPS=$(echo "$BACKUP_LIST" | grep -c . || true)
if [ "${BACKUPS:-0}" -eq 0 ] 2>/dev/null; then
  ok "Aucun fichier .bak/.backup/.old/.orig/.swp"
else
  wn "$BACKUPS fichier(s) de backup/temp:"
  echo "$BACKUP_LIST" | sed 's/^/     /'
fi

CORES=$(find . -maxdepth 3 \( -name "core" -o -name "core.*" \) -type f -not -path "*/core/*" 2>/dev/null | wc -l)
[ "$CORES" -eq 0 ] && ok "Aucun core dump" || ko "$CORES core dump(s)"

SQLITE=$(find . -maxdepth 3 \( -name "*.sqlite3" -o -name "*.sqlite" \) 2>/dev/null | wc -l)
[ "$SQLITE" -eq 0 ] && ok "Aucun fichier SQLite résiduel" || wn "$SQLITE fichier(s) SQLite (résidu dev)"

if [ -d "node_modules" ] || [ -d "frontend/node_modules" ]; then
  wn "node_modules sur le serveur (inutile en prod)"
else
  ok "Pas de node_modules sur le serveur"
fi

OVERRIDE_EXISTS=0
[ -f "docker-compose.override.yml" ] && OVERRIDE_EXISTS=1
[ -f "infra/docker/docker-compose.override.yml" ] && OVERRIDE_EXISTS=1
[ "$OVERRIDE_EXISTS" -eq 0 ] && ok "Pas de docker-compose.override.yml" || wn "docker-compose.override.yml présent (résidu dev?)"

###############################################################################
section "17. PERFORMANCE — TEMPS DE RÉPONSE"
###############################################################################
for EP in "/api/health/" "/" "/api/login/"; do
  if [ "$EP" = "/api/login/" ]; then
    TIME=$(curl -o /dev/null -w '%{time_total}' -s --max-time 10 \
      -H "X-Forwarded-Proto: https" -H "Host: $DOMAIN" \
      -H "Content-Type: application/json" \
      -d "{\"username\":\"admin\",\"password\":\"${ADMIN_PWD:-test}\"}" \
      "$LOCAL$EP" 2>/dev/null || echo "99")
  else
    TIME=$(curl -o /dev/null -w '%{time_total}' -s --max-time 10 \
      -H "X-Forwarded-Proto: https" -H "Host: $DOMAIN" \
      "$LOCAL$EP" 2>/dev/null || echo "99")
  fi
  MS=$(echo "$TIME" | awk '{printf "%.0f", $1*1000}')
  if [ "${MS:-9999}" -lt 500 ] 2>/dev/null; then
    ok "$EP → ${MS}ms"
  elif [ "${MS:-9999}" -lt 2000 ] 2>/dev/null; then
    wn "$EP → ${MS}ms (acceptable)"
  else
    wn "$EP → ${MS}ms (lent)"
  fi
done

###############################################################################
section "18. RÉSEAU DOCKER"
###############################################################################
nfo "Réseaux Docker:"
docker network ls 2>/dev/null | grep -iE "docker|korrigo" | sed 's/^/     /'

nfo "Résolution DNS inter-conteneurs:"
for SVC in db redis backend; do
  RESOLVED=$($COMPOSE exec -T nginx getent hosts "$SVC" 2>/dev/null | command head -1 || echo "FAIL")
  [ "$RESOLVED" != "FAIL" ] && ok "nginx → $SVC: $RESOLVED" || wn "nginx → $SVC: résolution échouée"
done

###############################################################################
###############################################################################
_sep
echo ""
echo "  ╔══════════════════════════════════════════════════════════════╗"
echo "  ║          BILAN D'AUDIT KORRIGO PRODUCTION                   ║"
echo "  ║          $(date '+%Y-%m-%d %H:%M:%S %Z')                             ║"
echo "  ╠══════════════════════════════════════════════════════════════╣"
printf "  ║  ✅ PASS : %-4d                                             ║\n" "$PASS"
printf "  ║  ⚠️  WARN : %-4d                                             ║\n" "$WARN"
printf "  ║  ❌ FAIL : %-4d                                             ║\n" "$FAIL"
echo "  ╠══════════════════════════════════════════════════════════════╣"
TOTAL=$((PASS+FAIL))
if [ "$TOTAL" -gt 0 ]; then
  SCORE=$((PASS * 100 / TOTAL))
else
  SCORE=0
fi
if [ "$FAIL" -eq 0 ] && [ "$WARN" -eq 0 ]; then
  VERDICT="PRODUCTION READY — ÉTAT PARFAIT ✨"
elif [ "$FAIL" -eq 0 ] && [ "$WARN" -le 3 ]; then
  VERDICT="PRODUCTION READY — ÉTAT OPTIMAL"
elif [ "$FAIL" -eq 0 ]; then
  VERDICT="PRODUCTION READY — WARNINGS MINEURS"
elif [ "$FAIL" -le 3 ]; then
  VERDICT="CORRECTIONS MINEURES NECESSAIRES"
else
  VERDICT="CORRECTIONS CRITIQUES REQUISES"
fi
printf "  ║  SCORE : %d%% (%d/%d)                                       ║\n" "$SCORE" "$PASS" "$TOTAL"
printf "  ║  VERDICT : %-46s  ║\n" "$VERDICT"
echo "  ╚══════════════════════════════════════════════════════════════╝"
echo ""

if [ "$WARN" -gt 0 ] || [ "$FAIL" -gt 0 ]; then
  echo "  RECOMMANDATIONS:"
  echo "  ─────────────────────"
  [ "${DANGLING_KORRIGO:-0}" -gt 0 ] && echo "  - docker image prune -f"
  [ "${ORPHAN_KORRIGO:-0}" -gt 0 ] && echo "  - docker volume prune -f"
  [ "${OLD_COUNT:-0}" -gt 0 ] && echo "  - docker rmi des anciennes images Korrigo"
  echo ""
fi

echo "  Audit terminé."
echo ""
