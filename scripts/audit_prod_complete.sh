#!/bin/bash
###############################################################################
#  KORRIGO — Audit Complet de Production (v2 — Fixed)
#  Date: 2026-02-10
#  Usage: bash scripts/audit_prod_complete.sh
#  Execute from /var/www/labomaths/korrigo on VPS
###############################################################################
set -uo pipefail

COMPOSE="docker compose --env-file .env -f infra/docker/docker-compose.prod.yml"
DOMAIN="korrigo.labomaths.tn"
LOCAL="http://127.0.0.1:8088"
PASS=0; FAIL=0; WARN=0

# Read IMAGE_SHA from .env (source of truth for running images)
if [ -f ".env" ]; then
  IMAGE_SHA=$(grep "^KORRIGO_SHA=" .env | cut -d= -f2)
else
  IMAGE_SHA="unknown"
fi

# ── Helpers (no name collision with system commands) ─────────────────────
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
[ "$OOM" -eq 0 ] && ok "Aucun OOM kill récent" || wn "$OOM messages OOM dans dmesg"

###############################################################################
section "2. DOCKER ENGINE"
###############################################################################
nfo "Docker:  $(docker --version 2>/dev/null || echo N/A)"
nfo "Compose: $(docker compose version 2>/dev/null || echo N/A)"

docker info >/dev/null 2>&1 && ok "Docker daemon actif" || ko "Docker daemon inactif"

nfo "Docker disk usage:"
docker system df 2>/dev/null | sed 's/^/     /'

DANGLING=$(docker images -f "dangling=true" -q 2>/dev/null | wc -l)
[ "$DANGLING" -eq 0 ] && ok "Aucune image dangling" || wn "$DANGLING image(s) dangling → docker image prune"

EXITED=$(docker ps -a --filter "status=exited" -q 2>/dev/null | wc -l)
[ "$EXITED" -eq 0 ] && ok "Aucun conteneur arrêté résiduel" || wn "$EXITED conteneur(s) arrêté(s) → docker container prune"
if [ "$EXITED" -gt 0 ]; then
  docker ps -a --filter "status=exited" --format "     {{.Names}}: {{.Status}} ({{.Image}})" 2>/dev/null
fi

ORPHAN_VOL=$(docker volume ls -f "dangling=true" -q 2>/dev/null | wc -l)
[ "$ORPHAN_VOL" -eq 0 ] && ok "Aucun volume orphelin" || wn "$ORPHAN_VOL volume(s) orphelin(s) → docker volume prune"

BUILD_CACHE=$(docker system df 2>/dev/null | awk '/Build Cache/{print $4}' || echo "N/A")
nfo "Build cache: $BUILD_CACHE"

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
for CID in $(docker ps -q 2>/dev/null); do
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
# Check running containers use correct image
for SVC in backend nginx; do
  RUNNING_IMG=$($COMPOSE ps --format '{{.Service}} {{.Image}}' 2>/dev/null | grep "^$SVC " | awk '{print $2}')
  if echo "$RUNNING_IMG" | grep -q "$IMAGE_SHA"; then
    ok "$SVC utilise l'image SHA $IMAGE_SHA"
  else
    ko "$SVC utilise une image incorrecte: $RUNNING_IMG"
  fi
done

# Count old images
OLD_COUNT=$(docker images --format '{{.Repository}}:{{.Tag}}' 2>/dev/null | grep -i "korrigo" | grep -v "$IMAGE_SHA" | grep -v "<none>" | wc -l)
if [ "$OLD_COUNT" -eq 0 ]; then
  ok "Aucune ancienne image Korrigo"
else
  wn "$OLD_COUNT ancienne(s) image(s) Korrigo à nettoyer"
  docker images --format '     {{.Repository}}:{{.Tag}} {{.Size}}' 2>/dev/null | grep -i "korrigo" | grep -v "$IMAGE_SHA" | grep -v "<none>"
fi

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
DB_OK=$($COMPOSE exec -T db psql -U korrigo_user -d korrigo_db -c "SELECT 1;" 2>/dev/null | grep -c "1" || echo "0")
[ "$DB_OK" -gt 0 ] && ok "PostgreSQL accessible" || ko "PostgreSQL inaccessible"

DB_VER=$($COMPOSE exec -T db psql -U korrigo_user -d korrigo_db -t -c "SELECT version();" 2>/dev/null | xargs || echo "N/A")
nfo "Version: $DB_VER"

TABLES=$($COMPOSE exec -T db psql -U korrigo_user -d korrigo_db -t -c "SELECT count(*) FROM information_schema.tables WHERE table_schema='public';" 2>/dev/null | xargs || echo "0")
nfo "Tables dans public: $TABLES"
[ "$TABLES" -gt 10 ] && ok "Schema complet ($TABLES tables)" || ko "Schema incomplet ($TABLES tables)"

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

PENDING=$($COMPOSE exec -T backend python manage.py showmigrations --plan 2>/dev/null | grep "\[ \]" | wc -l || echo "0")
PENDING=$(echo "$PENDING" | xargs)
[ "$PENDING" -eq 0 ] 2>/dev/null && ok "Aucune migration en attente" || ko "$PENDING migration(s) en attente"

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
nfo "Nginx config (default.conf):"
$COMPOSE exec -T nginx cat /etc/nginx/conf.d/default.conf 2>/dev/null | sed 's/^/     /'

SPA_FALLBACK=$($COMPOSE exec -T nginx cat /etc/nginx/conf.d/default.conf 2>/dev/null | grep -c "try_files.*index.html" || echo "0")
[ "$SPA_FALLBACK" -gt 0 ] && ok "SPA fallback configuré (try_files → index.html)" || wn "SPA fallback non détecté"

PROXY=$($COMPOSE exec -T nginx cat /etc/nginx/conf.d/default.conf 2>/dev/null | grep -c "proxy_pass" || echo "0")
[ "$PROXY" -gt 0 ] && ok "Proxy pass vers backend configuré" || ko "Aucun proxy_pass trouvé"

NGINX_5XX=$($COMPOSE logs --tail=50 nginx 2>/dev/null | grep -cE '" 5[0-9]{2} ' || echo "0")
[ "$NGINX_5XX" -eq 0 ] && ok "Nginx: 0 erreurs 5xx récentes" || wn "Nginx: $NGINX_5XX réponse(s) 5xx"

###############################################################################
section "9. API — ENDPOINTS CRITIQUES"
###############################################################################
# Health check
HTTP_CODE=$(curl -o /dev/null -w '%{http_code}' -sf --max-time 10 -H "X-Forwarded-Proto: https" -H "Host: $DOMAIN" "$LOCAL/api/health/" 2>/dev/null || echo "000")
HEALTH_BODY=$(curl -sf --max-time 10 -H "X-Forwarded-Proto: https" -H "Host: $DOMAIN" "$LOCAL/api/health/" 2>/dev/null || echo "{}")
[ "$HTTP_CODE" = "200" ] && ok "GET /api/health/ → $HTTP_CODE ($HEALTH_BODY)" || ko "GET /api/health/ → $HTTP_CODE"

for EP in "/api/health/live/" "/api/health/ready/"; do
  HTTP_CODE=$(curl -o /dev/null -w '%{http_code}' -sf --max-time 10 -H "X-Forwarded-Proto: https" -H "Host: $DOMAIN" "$LOCAL$EP" 2>/dev/null || echo "000")
  [ "$HTTP_CODE" = "200" ] && ok "GET $EP → $HTTP_CODE" || ko "GET $EP → $HTTP_CODE"
done

# Unauthenticated = 403
for EP in "/api/exams/" "/api/me/"; do
  HTTP_CODE=$(curl -o /dev/null -w '%{http_code}' -s --max-time 10 -H "X-Forwarded-Proto: https" -H "Host: $DOMAIN" "$LOCAL$EP" 2>/dev/null || echo "000")
  [ "$HTTP_CODE" = "403" ] && ok "GET $EP → $HTTP_CODE (protégé, normal)" || wn "GET $EP → $HTTP_CODE (attendu: 403)"
done

# Login
echo ""
nfo "Test de login admin:"
COOKIE_FILE="/tmp/korrigo_audit_cookies_$$.txt"
LOGIN_RESP=$(curl -s --max-time 10 -H "X-Forwarded-Proto: https" -H "Host: $DOMAIN" -H "Content-Type: application/json" -c "$COOKIE_FILE" -d '{"username":"admin","password":"8FvkX0wtMDj6ffsNLRBsRw"}' "$LOCAL/api/login/" 2>/dev/null)
echo "$LOGIN_RESP" | grep -q "Login successful" && ok "POST /api/login/ → Login successful" || ko "POST /api/login/ → $LOGIN_RESP"

CSRF=$(grep csrftoken "$COOKIE_FILE" 2>/dev/null | awk '{print $NF}' || echo "")
SESSION=$(grep sessionid "$COOKIE_FILE" 2>/dev/null | awk '{print $NF}' || echo "")
[ -n "$SESSION" ] && ok "Session cookie présent" || ko "Session cookie absent"
[ -n "$CSRF" ] && ok "CSRF token présent" || wn "CSRF token absent"

# Authenticated endpoints
echo ""
nfo "Endpoints authentifiés:"
for EP in "/api/me/" "/api/exams/" "/api/students/"; do
  HTTP_CODE=$(curl -o /dev/null -w '%{http_code}' -s --max-time 10 \
    -H "X-Forwarded-Proto: https" -H "Host: $DOMAIN" \
    -H "X-CSRFToken: $CSRF" -H "Referer: https://$DOMAIN/" \
    -b "$COOKIE_FILE" "$LOCAL$EP" 2>/dev/null || echo "000")
  if [ "$HTTP_CODE" = "200" ]; then
    ok "GET $EP → $HTTP_CODE ✓"
  else
    ko "GET $EP → $HTTP_CODE"
  fi
done

# Frontend SPA
HTTP_CODE=$(curl -o /dev/null -w '%{http_code}' -sf --max-time 10 "$LOCAL/" 2>/dev/null || echo "000")
[ "$HTTP_CODE" = "200" ] && ok "GET / (frontend SPA) → $HTTP_CODE" || ko "GET / (frontend SPA) → $HTTP_CODE"

# SPA deep links
for EP in "/login" "/dashboard"; do
  HTTP_CODE=$(curl -o /dev/null -w '%{http_code}' -sf --max-time 10 "$LOCAL$EP" 2>/dev/null || echo "000")
  [ "$HTTP_CODE" = "200" ] && ok "GET $EP (SPA deep link) → $HTTP_CODE" || ko "GET $EP (SPA deep link) → $HTTP_CODE"
done

# Django admin
HTTP_CODE=$(curl -o /dev/null -w '%{http_code}' -s --max-time 10 -H "X-Forwarded-Proto: https" -H "Host: $DOMAIN" "$LOCAL/admin/" 2>/dev/null || echo "000")
nfo "GET /admin/ → $HTTP_CODE"

# Static files DRF
HTTP_CODE=$(curl -o /dev/null -w '%{http_code}' -sf --max-time 10 -H "Host: $DOMAIN" "$LOCAL/static/rest_framework/css/default.css" 2>/dev/null || echo "000")
[ "$HTTP_CODE" = "200" ] && ok "Static files DRF → $HTTP_CODE" || wn "Static files DRF → $HTTP_CODE"

rm -f "$COOKIE_FILE"

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
if echo "$DJANGO_CHECK" | grep -q "System check identified no issues"; then
  ok "Django check --deploy: aucun problème"
else
  wn "Django check --deploy:"
  echo "$DJANGO_CHECK" | command tail -20 | sed 's/^/     /'
fi

GUNICORN_WORKERS=$($COMPOSE exec -T backend ps aux 2>/dev/null | grep -c "[g]unicorn" || echo "0")
nfo "Gunicorn workers: $GUNICORN_WORKERS"
[ "$GUNICORN_WORKERS" -ge 2 ] && ok "Gunicorn: $GUNICORN_WORKERS workers actifs" || wn "Gunicorn: seulement $GUNICORN_WORKERS worker(s)"

BACKEND_ERRORS=$($COMPOSE logs --tail=200 backend 2>/dev/null | grep -ciE "Traceback|Exception|ERROR" || echo "0")
[ "$BACKEND_ERRORS" -eq 0 ] && ok "Backend: 0 erreurs (200 dernières lignes)" || wn "Backend: $BACKEND_ERRORS erreur(s)"
if [ "$BACKEND_ERRORS" -gt 0 ]; then
  nfo "Dernières erreurs backend:"
  $COMPOSE logs --tail=200 backend 2>/dev/null | grep -B1 -A3 "Traceback\|Exception\|ERROR" | command tail -15 | sed 's/^/     /'
fi

###############################################################################
section "12. FICHIERS & VOLUMES"
###############################################################################
STATIC_COUNT=$($COMPOSE exec -T backend find /app/staticfiles -type f 2>/dev/null | wc -l || echo "0")
[ "$STATIC_COUNT" -gt 50 ] && ok "Static files: $STATIC_COUNT fichiers" || wn "Static files: $STATIC_COUNT (attendu > 50)"

MEDIA_COUNT=$($COMPOSE exec -T backend find /app/media -type f 2>/dev/null | wc -l || echo "0")
nfo "Media files: $MEDIA_COUNT fichiers"

echo ""
nfo "Docker volumes du projet:"
docker volume ls --format '{{.Name}}' 2>/dev/null | grep -iE "docker|korrigo" | while read -r VOL; do
  echo "     $VOL"
done

###############################################################################
section "13. SÉCURITÉ"
###############################################################################
SEC_HEADERS=$(curl -sI --max-time 10 -H "X-Forwarded-Proto: https" -H "Host: $DOMAIN" "$LOCAL/api/health/" 2>/dev/null)

echo ""
nfo "Headers de réponse:"
echo "$SEC_HEADERS" | sed 's/^/     /'

echo ""
echo "$SEC_HEADERS" | grep -qi "X-Frame-Options" && ok "X-Frame-Options présent" || wn "X-Frame-Options manquant"
echo "$SEC_HEADERS" | grep -qi "X-Content-Type-Options" && ok "X-Content-Type-Options présent" || wn "X-Content-Type-Options manquant"
echo "$SEC_HEADERS" | grep -qi "Strict-Transport-Security" && ok "HSTS présent" || wn "HSTS manquant"
echo "$SEC_HEADERS" | grep -qi "Content-Security-Policy" && ok "CSP présent" || wn "CSP manquant"
echo "$SEC_HEADERS" | grep -qi "Referrer-Policy" && ok "Referrer-Policy présent" || wn "Referrer-Policy manquant"

# Server header leak
echo "$SEC_HEADERS" | grep -qi "^Server:" && wn "Header 'Server' expose le serveur (server_tokens off recommandé)" || ok "Pas de fuite Server header"

echo ""
nfo "Ports exposés:"
docker ps --format '     {{.Names}}: {{.Ports}}' 2>/dev/null | grep -i "docker\|korrigo"
EXPOSED_COUNT=$(docker ps --format '{{.Ports}}' 2>/dev/null | grep -c "0.0.0.0" || true)
[ "$EXPOSED_COUNT" -le 2 ] && ok "Ports exposés raisonnables ($EXPOSED_COUNT)" || wn "$EXPOSED_COUNT ports exposés"

DB_EXPOSED=$(docker ps --format '{{.Names}} {{.Ports}}' 2>/dev/null | grep "docker-db" | grep -c "0.0.0.0" || true)
[ "$DB_EXPOSED" -eq 0 ] && ok "PostgreSQL NON exposé publiquement" || ko "PostgreSQL exposé ⚠ CRITIQUE"

REDIS_EXPOSED=$(docker ps --format '{{.Names}} {{.Ports}}' 2>/dev/null | grep "docker-redis" | grep -c "0.0.0.0" || true)
[ "$REDIS_EXPOSED" -eq 0 ] && ok "Redis NON exposé publiquement" || ko "Redis exposé ⚠ CRITIQUE"

###############################################################################
section "14. LOGS — ERREURS RÉCENTES (TOUS SERVICES)"
###############################################################################
for SVC in backend nginx celery celery-beat db redis; do
  ERR_COUNT=$($COMPOSE logs --tail=100 "$SVC" 2>/dev/null | grep -ciE "error|exception|fatal|critical|panic" || echo "0")
  if [ "$ERR_COUNT" -eq 0 ]; then
    ok "$SVC: 0 erreurs (dernières 100 lignes)"
  else
    wn "$SVC: $ERR_COUNT erreur(s)"
    $COMPOSE logs --tail=100 "$SVC" 2>/dev/null | grep -iE "error|exception|fatal|critical|panic" | command tail -3 | sed 's/^/     /'
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
  # Check if difference is only non-app files (audit scripts etc.)
  DIFF_FILES=$(git diff --name-only "$IMAGE_SHA" "$CURRENT_SHA" 2>/dev/null || echo "unknown")
  APP_CHANGES=$(echo "$DIFF_FILES" | grep -cE "^(backend|frontend|infra)/" || true)
  if [ "$APP_CHANGES" -eq 0 ] 2>/dev/null; then
    ok "Code ahead of images (non-app changes only: scripts, docs)"
    echo "     Changed files: $DIFF_FILES" | command head -5
  else
    wn "Code ($CURRENT_SHA) ≠ Images ($IMAGE_SHA) — $APP_CHANGES app file(s) changed"
  fi
fi

DIRTY=$(git status --porcelain 2>/dev/null | wc -l)
[ "$DIRTY" -eq 0 ] && ok "Working tree propre" || wn "$DIRTY fichier(s) modifié(s) localement"

###############################################################################
section "16. NETTOYAGE — FICHIERS PARASITES"
###############################################################################
BACKUPS=$(find . -maxdepth 3 \( -name "*.bak" -o -name "*.backup" -o -name "*.old" -o -name "*~" -o -name "*.orig" -o -name "*.swp" \) 2>/dev/null | wc -l)
[ "$BACKUPS" -eq 0 ] && ok "Aucun fichier .bak/.backup/.old/.orig/.swp" || wn "$BACKUPS fichier(s) de backup/temp"

CORES=$(find . -maxdepth 3 \( -name "core" -o -name "core.*" \) -not -path "*/core/*" 2>/dev/null | wc -l)
[ "$CORES" -eq 0 ] && ok "Aucun core dump" || ko "$CORES core dump(s)"

SQLITE=$(find . -maxdepth 3 \( -name "*.sqlite3" -o -name "*.sqlite" \) 2>/dev/null | wc -l)
[ "$SQLITE" -eq 0 ] && ok "Aucun fichier SQLite résiduel" || wn "$SQLITE fichier(s) SQLite (résidu dev)"

if [ -d "node_modules" ] || [ -d "frontend/node_modules" ]; then
  wn "node_modules sur le serveur (inutile en prod)"
else
  ok "Pas de node_modules sur le serveur"
fi

PYCACHE=$(find . -maxdepth 3 -name "__pycache__" -type d 2>/dev/null | wc -l)
nfo "__pycache__: $PYCACHE dossier(s)"

if [ -f "docker-compose.override.yml" ] || [ -f "infra/docker/docker-compose.override.yml" ]; then
  wn "docker-compose.override.yml présent (résidu dev?)"
else
  ok "Pas de docker-compose.override.yml"
fi

###############################################################################
section "17. PERFORMANCE — TEMPS DE RÉPONSE"
###############################################################################
for EP in "/api/health/" "/" "/api/login/"; do
  if [ "$EP" = "/api/login/" ]; then
    TIME=$(curl -o /dev/null -w '%{time_total}' -s --max-time 10 \
      -H "X-Forwarded-Proto: https" -H "Host: $DOMAIN" \
      -H "Content-Type: application/json" \
      -d '{"username":"admin","password":"8FvkX0wtMDj6ffsNLRBsRw"}' \
      "$LOCAL$EP" 2>/dev/null || echo "99")
  else
    TIME=$(curl -o /dev/null -w '%{time_total}' -s --max-time 10 \
      -H "X-Forwarded-Proto: https" -H "Host: $DOMAIN" \
      "$LOCAL$EP" 2>/dev/null || echo "99")
  fi
  MS=$(echo "$TIME" | awk '{printf "%.0f", $1*1000}')
  if [ "$MS" -lt 500 ] 2>/dev/null; then
    ok "$EP → ${MS}ms"
  elif [ "$MS" -lt 2000 ] 2>/dev/null; then
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
if [ "$FAIL" -eq 0 ] && [ "$WARN" -le 3 ]; then
  VERDICT="PRODUCTION READY — ETAT OPTIMAL"
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
  [ "${DANGLING:-0}" -gt 0 ] && echo "  - docker image prune -f"
  [ "${EXITED:-0}" -gt 0 ] && echo "  - docker container prune -f"
  [ "${ORPHAN_VOL:-0}" -gt 0 ] && echo "  - docker volume prune -f"
  [ "${OLD_COUNT:-0}" -gt 0 ] && echo "  - Supprimer les anciennes images: docker rmi \$(docker images | grep korrigo | grep -v $IMAGE_SHA | awk '{print \$3}')"
  echo ""
fi

echo "  Audit terminé."
echo ""
