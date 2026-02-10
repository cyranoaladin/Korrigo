#!/bin/bash
###############################################################################
#  KORRIGO — Audit Complet de Production (Premium)
#  Date: 2026-02-10
#  Auteur: Lead Senior DevOps
#  Usage: bash audit_prod_complete.sh
#  Exécuter depuis /var/www/labomaths/korrigo sur le VPS
###############################################################################
set -euo pipefail

COMPOSE="docker compose --env-file .env -f infra/docker/docker-compose.prod.yml"
DOMAIN="korrigo.labomaths.tn"
LOCAL="http://127.0.0.1:8088"
EXPECTED_SHA="202e1b9c2bc2e6e8af4fdadfe4676c693872924f"
PASS=0; FAIL=0; WARN=0

sep()  { echo ""; echo "═══════════════════════════════════════════════════════════════"; }
head() { sep; echo "  $1"; echo "═══════════════════════════════════════════════════════════════"; }
ok()   { PASS=$((PASS+1)); echo "  ✅ $1"; }
ko()   { FAIL=$((FAIL+1)); echo "  ❌ $1"; }
wn()   { WARN=$((WARN+1)); echo "  ⚠️  $1"; }
info() { echo "  ℹ️  $1"; }

###############################################################################
head "1. SYSTÈME HÔTE"
###############################################################################
info "Hostname: $(hostname)"
info "Kernel:   $(uname -r)"
info "Uptime:   $(uptime -p 2>/dev/null || uptime)"
info "Load:     $(cat /proc/loadavg | awk '{print $1, $2, $3}')"
info "RAM:      $(free -h | awk '/Mem:/{print $3"/"$2" ("int($3/$2*100)"%)"}')"
info "Disk /:   $(df -h / | awk 'NR==2{print $3"/"$2" ("$5")"}')"

DISK_PCT=$(df / | awk 'NR==2{gsub(/%/,""); print $5}')
[ "$DISK_PCT" -lt 80 ] && ok "Disque < 80% ($DISK_PCT%)" || ko "Disque >= 80% ($DISK_PCT%)"

# Zombies
ZOMBIES=$(ps aux | awk '$8~/Z/{print}' | wc -l)
[ "$ZOMBIES" -eq 0 ] && ok "Aucun processus zombie" || ko "$ZOMBIES processus zombie(s) détecté(s)"
if [ "$ZOMBIES" -gt 0 ]; then
  ps aux | awk '$8~/Z/' | head -5 | sed 's/^/     /'
fi

# OOM kills récents
OOM=$(dmesg 2>/dev/null | grep -ci "oom\|out of memory" || true)
[ "$OOM" -eq 0 ] && ok "Aucun OOM kill récent" || wn "$OOM messages OOM dans dmesg"

###############################################################################
head "2. DOCKER ENGINE"
###############################################################################
DOCKER_VER=$(docker --version 2>/dev/null || echo "N/A")
COMPOSE_VER=$(docker compose version 2>/dev/null || echo "N/A")
info "Docker:  $DOCKER_VER"
info "Compose: $COMPOSE_VER"

# Docker daemon running
docker info >/dev/null 2>&1 && ok "Docker daemon actif" || ko "Docker daemon inactif"

# Disk usage Docker
info "Docker disk usage:"
docker system df 2>/dev/null | sed 's/^/     /' || true

# Dangling images
DANGLING=$(docker images -f "dangling=true" -q 2>/dev/null | wc -l)
[ "$DANGLING" -eq 0 ] && ok "Aucune image dangling" || wn "$DANGLING image(s) dangling → docker image prune"

# Stopped/exited containers
EXITED=$(docker ps -a --filter "status=exited" -q 2>/dev/null | wc -l)
[ "$EXITED" -eq 0 ] && ok "Aucun conteneur arrêté résiduel" || wn "$EXITED conteneur(s) arrêté(s) → docker container prune"
if [ "$EXITED" -gt 0 ]; then
  docker ps -a --filter "status=exited" --format "     {{.Names}}: {{.Status}} ({{.Image}})" 2>/dev/null
fi

# Orphan volumes
ORPHAN_VOL=$(docker volume ls -f "dangling=true" -q 2>/dev/null | wc -l)
[ "$ORPHAN_VOL" -eq 0 ] && ok "Aucun volume orphelin" || wn "$ORPHAN_VOL volume(s) orphelin(s) → docker volume prune"

# Build cache
BUILD_CACHE=$(docker builder du 2>/dev/null | tail -1 | awk '{print $NF}' || echo "N/A")
info "Build cache: $BUILD_CACHE"

###############################################################################
head "3. CONTENEURS — ÉTAT"
###############################################################################
EXPECTED_SERVICES="backend nginx db redis celery celery-beat"
ALL_UP=true

echo ""
info "Docker ps complet:"
$COMPOSE ps 2>/dev/null | sed 's/^/     /'

echo ""
for SVC in $EXPECTED_SERVICES; do
  STATUS=$($COMPOSE ps --format '{{.Service}} {{.State}} {{.Health}}' 2>/dev/null | grep "^$SVC " || echo "$SVC not_found")
  STATE=$(echo "$STATUS" | awk '{print $2}')
  HEALTH=$(echo "$STATUS" | awk '{print $3}')
  
  if [ "$STATE" = "running" ]; then
    if [ -n "$HEALTH" ] && [ "$HEALTH" != "" ] && [ "$HEALTH" != "healthy" ]; then
      ko "$SVC: running mais $HEALTH"
      ALL_UP=false
    else
      ok "$SVC: running${HEALTH:+ ($HEALTH)}"
    fi
  else
    ko "$SVC: $STATE"
    ALL_UP=false
  fi
done

# Restart counts
echo ""
info "Restart counts (0 = stable):"
docker inspect --format='     {{.Name}}: {{.RestartCount}} redémarrages' $(docker ps -q 2>/dev/null) 2>/dev/null || true

# Uptime
echo ""
info "Uptime conteneurs:"
$COMPOSE ps --format '     {{.Service}}: {{.RunningFor}}' 2>/dev/null || true

###############################################################################
head "4. IMAGES — VERSION & SHA"
###############################################################################
info "Images Korrigo en local:"
docker images --format '     {{.Repository}}:{{.Tag}}  ({{.Size}}, créée {{.CreatedSince}})' 2>/dev/null | grep -i "korrigo" || echo "     (aucune)"

echo ""
for IMG_LABEL in "korrigo-backend" "korrigo-nginx"; do
  IMG_TAG=$(docker images --format '{{.Repository}}:{{.Tag}}' 2>/dev/null | grep "$IMG_LABEL" | head -1 || echo "NOT_FOUND")
  if echo "$IMG_TAG" | grep -q "$EXPECTED_SHA"; then
    ok "$IMG_LABEL: SHA correct"
  else
    ko "$IMG_LABEL: SHA incorrect — $IMG_TAG"
  fi
done

# Old images
OLD_IMGS=$(docker images --format '{{.Repository}}:{{.Tag}} {{.Size}}' 2>/dev/null | grep -i "korrigo" | grep -v "$EXPECTED_SHA" | grep -v "<none>" || true)
if [ -z "$OLD_IMGS" ]; then
  ok "Aucune ancienne image Korrigo"
else
  wn "Anciennes images Korrigo présentes:"
  echo "$OLD_IMGS" | sed 's/^/       /'
fi

###############################################################################
head "5. FICHIER .env"
###############################################################################
ENV_FILE=".env"
if [ -f "$ENV_FILE" ]; then
  ok ".env présent"
else
  ko ".env manquant!"
fi

# Show all vars (masked values)
echo ""
info "Variables dans .env (valeurs masquées):"
while IFS='=' read -r KEY VAL; do
  [[ "$KEY" =~ ^#.* ]] && continue
  [ -z "$KEY" ] && continue
  MASKED=$(echo "$VAL" | sed 's/./*/g' | head -c 20)
  echo "     $KEY=$MASKED"
done < "$ENV_FILE" 2>/dev/null || true

# Required vars
echo ""
REQUIRED_VARS="KORRIGO_SHA GITHUB_REPOSITORY_OWNER SECRET_KEY DJANGO_ENV DEBUG ALLOWED_HOSTS DJANGO_ALLOWED_HOSTS POSTGRES_DB POSTGRES_USER POSTGRES_PASSWORD CORS_ALLOWED_ORIGINS CSRF_TRUSTED_ORIGINS METRICS_TOKEN ADMIN_PASSWORD TEACHER_PASSWORD"
MISSING_VARS=""
for VAR in $REQUIRED_VARS; do
  if ! grep -q "^${VAR}=" "$ENV_FILE" 2>/dev/null; then
    MISSING_VARS="$MISSING_VARS $VAR"
  fi
done
[ -z "$MISSING_VARS" ] && ok "Toutes les variables requises présentes ($(echo $REQUIRED_VARS | wc -w) vars)" || ko "Variables manquantes:$MISSING_VARS"

# SHA match
ENV_SHA=$(grep "^KORRIGO_SHA=" "$ENV_FILE" 2>/dev/null | cut -d= -f2)
[ "$ENV_SHA" = "$EXPECTED_SHA" ] && ok ".env SHA = commit attendu" || ko ".env SHA mismatch: '$ENV_SHA' vs '$EXPECTED_SHA'"

# DEBUG
ENV_DEBUG=$(grep "^DEBUG=" "$ENV_FILE" 2>/dev/null | cut -d= -f2)
[ "$ENV_DEBUG" = "False" ] && ok "DEBUG=False (production)" || ko "DEBUG=$ENV_DEBUG ⚠ doit être False"

# DJANGO_ENV
ENV_DJANGO=$(grep "^DJANGO_ENV=" "$ENV_FILE" 2>/dev/null | cut -d= -f2)
[ "$ENV_DJANGO" = "production" ] && ok "DJANGO_ENV=production" || wn "DJANGO_ENV=$ENV_DJANGO"

# ALLOWED_HOSTS must include domain
ENV_AH=$(grep "^ALLOWED_HOSTS=" "$ENV_FILE" 2>/dev/null | cut -d= -f2)
echo "$ENV_AH" | grep -q "$DOMAIN" && ok "ALLOWED_HOSTS contient $DOMAIN" || ko "ALLOWED_HOSTS ne contient pas $DOMAIN"

# CORS
ENV_CORS=$(grep "^CORS_ALLOWED_ORIGINS=" "$ENV_FILE" 2>/dev/null | cut -d= -f2)
echo "$ENV_CORS" | grep -q "https://$DOMAIN" && ok "CORS_ALLOWED_ORIGINS contient https://$DOMAIN" || ko "CORS_ALLOWED_ORIGINS incorrect"

# CSRF
ENV_CSRF=$(grep "^CSRF_TRUSTED_ORIGINS=" "$ENV_FILE" 2>/dev/null | cut -d= -f2)
echo "$ENV_CSRF" | grep -q "https://$DOMAIN" && ok "CSRF_TRUSTED_ORIGINS contient https://$DOMAIN" || ko "CSRF_TRUSTED_ORIGINS incorrect"

# Trailing whitespace or empty values
BAD_LINES=$(grep -nE '=\s*$' "$ENV_FILE" 2>/dev/null | head -5 || true)
[ -z "$BAD_LINES" ] && ok "Pas de valeurs vides dans .env" || wn "Lignes avec valeurs vides dans .env: $BAD_LINES"

# File permissions
PERM=$(stat -c '%a' "$ENV_FILE" 2>/dev/null || echo "unknown")
info ".env permissions: $PERM"

###############################################################################
head "6. BASE DE DONNÉES"
###############################################################################
# Connection
DB_OK=$($COMPOSE exec -T db psql -U korrigo_user -d korrigo_db -c "SELECT 1;" 2>/dev/null | grep -c "1" || echo "0")
[ "$DB_OK" -gt 0 ] && ok "PostgreSQL accessible" || ko "PostgreSQL inaccessible"

# Version
DB_VER=$($COMPOSE exec -T db psql -U korrigo_user -d korrigo_db -t -c "SELECT version();" 2>/dev/null | head -1 | xargs || echo "N/A")
info "Version: $DB_VER"

# Tables count
TABLES=$($COMPOSE exec -T db psql -U korrigo_user -d korrigo_db -t -c "SELECT count(*) FROM information_schema.tables WHERE table_schema='public';" 2>/dev/null | tr -d ' ' || echo "0")
info "Tables dans public: $TABLES"
[ "$TABLES" -gt 10 ] && ok "Schema complet ($TABLES tables)" || ko "Schema incomplet ($TABLES tables)"

# List tables
echo ""
info "Liste des tables:"
$COMPOSE exec -T db psql -U korrigo_user -d korrigo_db -t -c "SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename;" 2>/dev/null | sed '/^\s*$/d; s/^/     /'

# Key row counts
echo ""
info "Comptages clés:"
for TBL in auth_user students_student exams_exam grading_copy identification_studentidentification; do
  CNT=$($COMPOSE exec -T db psql -U korrigo_user -d korrigo_db -t -c "SELECT count(*) FROM $TBL;" 2>/dev/null | tr -d ' ' || echo "ERR")
  echo "     $TBL: $CNT lignes"
done

# Users details
echo ""
info "Utilisateurs Django:"
$COMPOSE exec -T db psql -U korrigo_user -d korrigo_db -c "SELECT id, username, is_staff, is_superuser, is_active, last_login FROM auth_user ORDER BY id;" 2>/dev/null | sed 's/^/     /'

# Pending migrations
PENDING=$($COMPOSE run --rm -T backend python manage.py showmigrations --plan 2>/dev/null < /dev/null | grep "\[ \]" | wc -l || echo "0")
[ "$PENDING" -eq 0 ] && ok "Aucune migration en attente" || ko "$PENDING migration(s) en attente"

# DB size
DB_SIZE=$($COMPOSE exec -T db psql -U korrigo_user -d korrigo_db -t -c "SELECT pg_size_pretty(pg_database_size('korrigo_db'));" 2>/dev/null | tr -d ' ' || echo "N/A")
info "Taille DB: $DB_SIZE"

# Connections actives
CONNS=$($COMPOSE exec -T db psql -U korrigo_user -d korrigo_db -t -c "SELECT count(*) FROM pg_stat_activity WHERE datname='korrigo_db';" 2>/dev/null | tr -d ' ' || echo "N/A")
info "Connexions actives: $CONNS"

# Dead tuples (needs vacuum?)
DEAD_TUPLES=$($COMPOSE exec -T db psql -U korrigo_user -d korrigo_db -t -c "SELECT sum(n_dead_tup) FROM pg_stat_user_tables;" 2>/dev/null | tr -d ' ' || echo "0")
info "Dead tuples: $DEAD_TUPLES"
[ "${DEAD_TUPLES:-0}" -lt 1000 ] 2>/dev/null && ok "Dead tuples < 1000 (pas besoin de VACUUM)" || wn "Dead tuples élevées ($DEAD_TUPLES) — VACUUM recommandé"

###############################################################################
head "7. REDIS / CACHE"
###############################################################################
REDIS_PING=$($COMPOSE exec -T redis redis-cli ping 2>/dev/null || echo "FAIL")
[ "$REDIS_PING" = "PONG" ] && ok "Redis: PONG" || ko "Redis: $REDIS_PING"

REDIS_INFO=$($COMPOSE exec -T redis redis-cli INFO server 2>/dev/null | grep "redis_version" | cut -d: -f2 | tr -d '\r' || echo "N/A")
info "Redis version: $REDIS_INFO"

REDIS_MEM=$($COMPOSE exec -T redis redis-cli INFO memory 2>/dev/null | grep "used_memory_human" | cut -d: -f2 | tr -d '\r' || echo "N/A")
info "Redis mémoire: $REDIS_MEM"

for DB_NUM in 0 1 2; do
  KEYS=$($COMPOSE exec -T redis redis-cli -n $DB_NUM DBSIZE 2>/dev/null | grep -oP '\d+' || echo "0")
  info "Redis DB $DB_NUM: $KEYS clés"
done

# Check stale keys
REDIS_KEYS_DETAIL=$($COMPOSE exec -T redis redis-cli KEYS '*' 2>/dev/null | head -20 || true)
KEY_COUNT=$(echo "$REDIS_KEYS_DETAIL" | grep -c . || echo "0")
info "Échantillon de clés Redis (max 20): $KEY_COUNT"
[ "$KEY_COUNT" -gt 0 ] && echo "$REDIS_KEYS_DETAIL" | head -10 | sed 's/^/     /'

###############################################################################
head "8. NGINX — CONFIGURATION & ROUTAGE"
###############################################################################
# Config test
NGINX_TEST=$($COMPOSE exec -T nginx nginx -t 2>&1 || echo "FAIL")
echo "$NGINX_TEST" | grep -q "successful" && ok "Nginx config syntaxiquement valide" || ko "Nginx config invalide"

# Show full config
echo ""
info "Nginx config (default.conf):"
$COMPOSE exec -T nginx cat /etc/nginx/conf.d/default.conf 2>/dev/null | sed 's/^/     /'

# Check SPA fallback (try_files with index.html)
SPA_FALLBACK=$($COMPOSE exec -T nginx cat /etc/nginx/conf.d/default.conf 2>/dev/null | grep -c "try_files.*index.html" || echo "0")
[ "$SPA_FALLBACK" -gt 0 ] && ok "SPA fallback configuré (try_files → index.html)" || wn "SPA fallback non détecté"

# Check proxy_pass to backend
PROXY=$($COMPOSE exec -T nginx cat /etc/nginx/conf.d/default.conf 2>/dev/null | grep -c "proxy_pass" || echo "0")
[ "$PROXY" -gt 0 ] && ok "Proxy pass vers backend configuré" || ko "Aucun proxy_pass trouvé"

# Access/error logs récents
echo ""
NGINX_ERR_COUNT=$($COMPOSE logs --tail=50 nginx 2>/dev/null | grep -ciE " 5[0-9][0-9] " || echo "0")
[ "$NGINX_ERR_COUNT" -eq 0 ] && ok "Nginx: aucune erreur 5xx récente" || wn "Nginx: $NGINX_ERR_COUNT réponse(s) 5xx récente(s)"

NGINX_404_COUNT=$($COMPOSE logs --tail=50 nginx 2>/dev/null | grep -ciE " 404 " || echo "0")
info "Nginx 404 récents: $NGINX_404_COUNT"

###############################################################################
head "9. API — ENDPOINTS CRITIQUES"
###############################################################################

# Health check
HTTP_CODE=$(curl -o /dev/null -w '%{http_code}' -sf --max-time 10 -H "X-Forwarded-Proto: https" -H "Host: $DOMAIN" "$LOCAL/api/health/" 2>/dev/null || echo "000")
HEALTH_BODY=$(curl -sf --max-time 10 -H "X-Forwarded-Proto: https" -H "Host: $DOMAIN" "$LOCAL/api/health/" 2>/dev/null || echo "{}")
[ "$HTTP_CODE" = "200" ] && ok "GET /api/health/ → $HTTP_CODE ($HEALTH_BODY)" || ko "GET /api/health/ → $HTTP_CODE"

# Health live
HTTP_CODE=$(curl -o /dev/null -w '%{http_code}' -sf --max-time 10 -H "X-Forwarded-Proto: https" -H "Host: $DOMAIN" "$LOCAL/api/health/live/" 2>/dev/null || echo "000")
[ "$HTTP_CODE" = "200" ] && ok "GET /api/health/live/ → $HTTP_CODE" || ko "GET /api/health/live/ → $HTTP_CODE"

# Health ready
HTTP_CODE=$(curl -o /dev/null -w '%{http_code}' -sf --max-time 10 -H "X-Forwarded-Proto: https" -H "Host: $DOMAIN" "$LOCAL/api/health/ready/" 2>/dev/null || echo "000")
[ "$HTTP_CODE" = "200" ] && ok "GET /api/health/ready/ → $HTTP_CODE" || ko "GET /api/health/ready/ → $HTTP_CODE"

# Unauthenticated endpoints (should return 403)
for EP in "/api/exams/" "/api/me/"; do
  HTTP_CODE=$(curl -o /dev/null -w '%{http_code}' -s --max-time 10 -H "X-Forwarded-Proto: https" -H "Host: $DOMAIN" "$LOCAL$EP" 2>/dev/null || echo "000")
  [ "$HTTP_CODE" = "403" ] && ok "GET $EP → $HTTP_CODE (protégé, normal sans auth)" || wn "GET $EP → $HTTP_CODE (attendu: 403)"
done

# Login
echo ""
info "Test de login admin:"
LOGIN_RESP=$(curl -s --max-time 10 -H "X-Forwarded-Proto: https" -H "Host: $DOMAIN" -H "Content-Type: application/json" -c /tmp/korrigo_audit_cookies.txt -d '{"username":"admin","password":"8FvkX0wtMDj6ffsNLRBsRw"}' "$LOCAL/api/login/" 2>/dev/null)
echo "$LOGIN_RESP" | grep -q "Login successful" && ok "POST /api/login/ → Login successful" || ko "POST /api/login/ → $LOGIN_RESP"

# Display cookies
info "Cookies reçus:"
cat /tmp/korrigo_audit_cookies.txt 2>/dev/null | grep -v "^#" | awk 'NF>0{print "     " $6 "=" substr($7,1,20) "..."}' || echo "     (aucun)"

# Extract CSRF
CSRF=$(grep csrftoken /tmp/korrigo_audit_cookies.txt 2>/dev/null | awk '{print $NF}' || echo "")
SESSION=$(grep sessionid /tmp/korrigo_audit_cookies.txt 2>/dev/null | awk '{print $NF}' || echo "")
[ -n "$SESSION" ] && ok "Session cookie présent" || ko "Session cookie absent"
[ -n "$CSRF" ] && ok "CSRF token présent" || wn "CSRF token absent"

# Authenticated endpoints
echo ""
info "Endpoints authentifiés:"
for EP in "/api/me/" "/api/exams/" "/api/students/"; do
  RESP=$(curl -s --max-time 10 -H "X-Forwarded-Proto: https" -H "Host: $DOMAIN" -H "X-CSRFToken: $CSRF" -H "Referer: https://$DOMAIN/" -b /tmp/korrigo_audit_cookies.txt "$LOCAL$EP" 2>/dev/null)
  HTTP_CODE=$(curl -o /dev/null -w '%{http_code}' -s --max-time 10 -H "X-Forwarded-Proto: https" -H "Host: $DOMAIN" -H "X-CSRFToken: $CSRF" -H "Referer: https://$DOMAIN/" -b /tmp/korrigo_audit_cookies.txt "$LOCAL$EP" 2>/dev/null || echo "000")
  if [ "$HTTP_CODE" = "200" ]; then
    ok "GET $EP → $HTTP_CODE ✓"
    # Show truncated response
    echo "     $(echo "$RESP" | head -c 200)..."
  else
    ko "GET $EP → $HTTP_CODE"
    echo "     $(echo "$RESP" | head -c 200)"
  fi
done

# Frontend SPA
HTTP_CODE=$(curl -o /dev/null -w '%{http_code}' -sf --max-time 10 "$LOCAL/" 2>/dev/null || echo "000")
[ "$HTTP_CODE" = "200" ] && ok "GET / (frontend SPA) → $HTTP_CODE" || ko "GET / (frontend SPA) → $HTTP_CODE"

# SPA routing (deep link should return index.html)
HTTP_CODE=$(curl -o /dev/null -w '%{http_code}' -sf --max-time 10 "$LOCAL/login" 2>/dev/null || echo "000")
[ "$HTTP_CODE" = "200" ] && ok "GET /login (SPA deep link) → $HTTP_CODE" || ko "GET /login (SPA deep link) → $HTTP_CODE"

HTTP_CODE=$(curl -o /dev/null -w '%{http_code}' -sf --max-time 10 "$LOCAL/dashboard" 2>/dev/null || echo "000")
[ "$HTTP_CODE" = "200" ] && ok "GET /dashboard (SPA deep link) → $HTTP_CODE" || ko "GET /dashboard (SPA deep link) → $HTTP_CODE"

# Admin Django (si exposé)
HTTP_CODE=$(curl -o /dev/null -w '%{http_code}' -s --max-time 10 -H "X-Forwarded-Proto: https" -H "Host: $DOMAIN" "$LOCAL/admin/" 2>/dev/null || echo "000")
info "GET /admin/ → $HTTP_CODE (${HTTP_CODE:+OK si 200 ou 302})"

# Static files
HTTP_CODE=$(curl -o /dev/null -w '%{http_code}' -sf --max-time 10 -H "Host: $DOMAIN" "$LOCAL/static/rest_framework/css/default.css" 2>/dev/null || echo "000")
[ "$HTTP_CODE" = "200" ] && ok "Static files DRF servis → $HTTP_CODE" || wn "Static files DRF → $HTTP_CODE"

# Cleanup
rm -f /tmp/korrigo_audit_cookies.txt

###############################################################################
head "10. CELERY & TÂCHES ASYNCHRONES"
###############################################################################
CELERY_PING=$($COMPOSE exec -T celery celery -A core inspect ping 2>&1 | head -5 || echo "FAIL")
echo "$CELERY_PING" | grep -q "pong" && ok "Celery worker: pong" || wn "Celery worker: pas de réponse (vérifier logs)"

# Active tasks
ACTIVE_TASKS=$($COMPOSE exec -T celery celery -A core inspect active 2>/dev/null | head -10 || echo "N/A")
info "Tâches actives:"
echo "$ACTIVE_TASKS" | head -5 | sed 's/^/     /'

# Scheduled tasks
SCHEDULED=$($COMPOSE exec -T celery celery -A core inspect scheduled 2>/dev/null | head -10 || echo "N/A")
info "Tâches planifiées:"
echo "$SCHEDULED" | head -5 | sed 's/^/     /'

# Celery-beat logs
echo ""
info "Celery-beat logs récents:"
$COMPOSE logs --tail=10 celery-beat 2>/dev/null | tail -5 | sed 's/^/     /'

###############################################################################
head "11. BACKEND — DJANGO HEALTH"
###############################################################################
# Django settings check (via manage.py)
DJANGO_CHECK=$($COMPOSE run --rm -T backend python manage.py check --deploy 2>&1 < /dev/null || echo "FAIL")
CHECK_ISSUES=$(echo "$DJANGO_CHECK" | grep -c "WARNINGS\|ERROR" || echo "0")
if echo "$DJANGO_CHECK" | grep -q "System check identified no issues"; then
  ok "Django check --deploy: aucun problème"
else
  wn "Django check --deploy a trouvé des issues:"
  echo "$DJANGO_CHECK" | tail -20 | sed 's/^/     /'
fi

# Gunicorn workers
GUNICORN_WORKERS=$($COMPOSE exec -T backend ps aux 2>/dev/null | grep -c "[g]unicorn" || echo "0")
info "Gunicorn workers: $GUNICORN_WORKERS"
[ "$GUNICORN_WORKERS" -ge 2 ] && ok "Gunicorn: $GUNICORN_WORKERS workers actifs" || wn "Gunicorn: seulement $GUNICORN_WORKERS worker(s)"

# Backend logs errors
BACKEND_ERRORS=$($COMPOSE logs --tail=200 backend 2>/dev/null | grep -ciE "ERROR|Traceback|Exception" || echo "0")
[ "$BACKEND_ERRORS" -eq 0 ] && ok "Backend: 0 erreurs dans les 200 dernières lignes" || wn "Backend: $BACKEND_ERRORS erreur(s)/exception(s)"

if [ "$BACKEND_ERRORS" -gt 0 ]; then
  echo ""
  info "Dernières erreurs backend:"
  $COMPOSE logs --tail=200 backend 2>/dev/null | grep -B2 -A3 "ERROR\|Traceback\|Exception" | tail -20 | sed 's/^/     /'
fi

###############################################################################
head "12. FICHIERS & VOLUMES"
###############################################################################
# Static files
STATIC_COUNT=$($COMPOSE exec -T backend find /app/staticfiles -type f 2>/dev/null | wc -l || echo "0")
[ "$STATIC_COUNT" -gt 50 ] && ok "Static files: $STATIC_COUNT fichiers collectés" || wn "Static files: $STATIC_COUNT (attendu > 50)"

# Media volume
MEDIA_COUNT=$($COMPOSE exec -T backend find /app/media -type f 2>/dev/null | wc -l || echo "0")
info "Media files: $MEDIA_COUNT fichiers"

# Volume details
echo ""
info "Docker volumes du projet:"
docker volume ls --format '{{.Name}}' 2>/dev/null | grep -i "docker\|korrigo" | while read VOL; do
  SIZE=$(docker run --rm -v "$VOL:/data" alpine du -sh /data 2>/dev/null | awk '{print $1}' || echo "N/A")
  echo "     $VOL: $SIZE"
done

# Backups sur le host
echo ""
BACKUP_FILES=$(find /var/www/labomaths/korrigo -maxdepth 2 -name "*.bak" -o -name "*.backup" -o -name "*.sql.gz" -o -name "*.tar.gz" 2>/dev/null | wc -l)
info "Fichiers de backup sur le host: $BACKUP_FILES"
if [ "$BACKUP_FILES" -gt 0 ]; then
  find /var/www/labomaths/korrigo -maxdepth 2 \( -name "*.bak" -o -name "*.backup" -o -name "*.sql.gz" -o -name "*.tar.gz" \) 2>/dev/null | head -10 | sed 's/^/     /'
fi

###############################################################################
head "13. SÉCURITÉ"
###############################################################################
# Security headers
SEC_HEADERS=$(curl -sI --max-time 10 -H "X-Forwarded-Proto: https" -H "Host: $DOMAIN" "$LOCAL/api/health/" 2>/dev/null)

echo ""
info "Headers de réponse complets:"
echo "$SEC_HEADERS" | sed 's/^/     /'

echo ""
echo "$SEC_HEADERS" | grep -qi "X-Frame-Options" && ok "X-Frame-Options présent" || wn "X-Frame-Options manquant"
echo "$SEC_HEADERS" | grep -qi "X-Content-Type-Options" && ok "X-Content-Type-Options présent" || wn "X-Content-Type-Options manquant"
echo "$SEC_HEADERS" | grep -qi "Strict-Transport-Security" && ok "HSTS présent" || wn "HSTS manquant (à configurer au niveau reverse proxy)"
echo "$SEC_HEADERS" | grep -qi "Content-Security-Policy" && ok "CSP présent" || wn "CSP manquant"
echo "$SEC_HEADERS" | grep -qi "Referrer-Policy" && ok "Referrer-Policy présent" || wn "Referrer-Policy manquant"
echo "$SEC_HEADERS" | grep -qi "X-XSS-Protection" && ok "X-XSS-Protection présent" || info "X-XSS-Protection absent (obsolète, CSP suffit)"

# Server header leak
echo "$SEC_HEADERS" | grep -qi "^Server: nginx" && wn "Header 'Server' expose nginx (recommandé: server_tokens off)" || ok "Pas de fuite Server header"

# Exposed ports
echo ""
info "Ports exposés sur l'hôte:"
docker ps --format '{{.Names}}: {{.Ports}}' 2>/dev/null | sed 's/^/     /'
EXPOSED_COUNT=$(docker ps --format '{{.Ports}}' 2>/dev/null | grep -c "0.0.0.0" || true)
[ "$EXPOSED_COUNT" -le 1 ] && ok "Seul nginx exposé publiquement" || wn "$EXPOSED_COUNT ports exposés (idéal: nginx uniquement)"

# Check no DB port exposed
DB_EXPOSED=$(docker ps --format '{{.Names}} {{.Ports}}' 2>/dev/null | grep "db" | grep -c "0.0.0.0" || true)
[ "$DB_EXPOSED" -eq 0 ] && ok "PostgreSQL NON exposé publiquement" || ko "PostgreSQL exposé publiquement ⚠ CRITIQUE"

# Check no Redis port exposed
REDIS_EXPOSED=$(docker ps --format '{{.Names}} {{.Ports}}' 2>/dev/null | grep "redis" | grep -c "0.0.0.0" || true)
[ "$REDIS_EXPOSED" -eq 0 ] && ok "Redis NON exposé publiquement" || ko "Redis exposé publiquement ⚠ CRITIQUE"

###############################################################################
head "14. LOGS — ERREURS RÉCENTES (TOUS SERVICES)"
###############################################################################
for SVC in backend nginx celery celery-beat db redis; do
  ERR_COUNT=$($COMPOSE logs --tail=100 "$SVC" 2>/dev/null | grep -ciE "error|exception|fatal|critical|panic" || echo "0")
  if [ "$ERR_COUNT" -eq 0 ]; then
    ok "$SVC: 0 erreurs (100 dernières lignes)"
  else
    wn "$SVC: $ERR_COUNT erreur(s)"
    $COMPOSE logs --tail=100 "$SVC" 2>/dev/null | grep -iE "error|exception|fatal|critical|panic" | tail -3 | sed 's/^/     /'
  fi
done

###############################################################################
head "15. GIT — ÉTAT DU CODE"
###############################################################################
CURRENT_SHA=$(git rev-parse HEAD 2>/dev/null || echo "N/A")
CURRENT_BRANCH=$(git branch --show-current 2>/dev/null || echo "N/A")
info "Branche: $CURRENT_BRANCH"
info "Commit:  $CURRENT_SHA"
info "Message: $(git log -1 --format='%s' 2>/dev/null || echo 'N/A')"
info "Date:    $(git log -1 --format='%ci' 2>/dev/null || echo 'N/A')"

[ "$CURRENT_SHA" = "$EXPECTED_SHA" ] && ok "Code synchronisé avec images Docker" || ko "Code ($CURRENT_SHA) ≠ Images ($EXPECTED_SHA)"

DIRTY=$(git status --porcelain 2>/dev/null | wc -l)
[ "$DIRTY" -eq 0 ] && ok "Working tree propre" || wn "$DIRTY fichier(s) modifié(s) localement"
if [ "$DIRTY" -gt 0 ]; then
  git status --porcelain 2>/dev/null | head -10 | sed 's/^/     /'
fi

###############################################################################
head "16. NETTOYAGE — FICHIERS PARASITES"
###############################################################################
# Backup files
BACKUPS=$(find . -maxdepth 3 -name "*.bak" -o -name "*.backup" -o -name "*.old" -o -name "*~" -o -name "*.orig" -o -name "*.swp" 2>/dev/null | wc -l)
[ "$BACKUPS" -eq 0 ] && ok "Aucun fichier .bak/.backup/.old/.orig/.swp" || wn "$BACKUPS fichier(s) de backup/temp"
if [ "$BACKUPS" -gt 0 ]; then
  find . -maxdepth 3 \( -name "*.bak" -o -name "*.backup" -o -name "*.old" -o -name "*~" -o -name "*.orig" -o -name "*.swp" \) 2>/dev/null | head -10 | sed 's/^/     /'
fi

# Core dumps
CORES=$(find . -maxdepth 3 -name "core" -o -name "core.*" 2>/dev/null | wc -l)
[ "$CORES" -eq 0 ] && ok "Aucun core dump" || ko "$CORES core dump(s)"

# SQLite (dev database leftover)
SQLITE=$(find . -maxdepth 3 -name "*.sqlite3" -o -name "*.sqlite" 2>/dev/null | wc -l)
[ "$SQLITE" -eq 0 ] && ok "Aucun fichier SQLite résiduel" || wn "$SQLITE fichier(s) SQLite (résidu dev?)"
if [ "$SQLITE" -gt 0 ]; then
  find . -maxdepth 3 \( -name "*.sqlite3" -o -name "*.sqlite" \) 2>/dev/null | sed 's/^/     /'
fi

# node_modules (shouldn't be on server)
if [ -d "node_modules" ] || [ -d "frontend/node_modules" ]; then
  wn "node_modules présent sur le serveur (inutile en prod)"
else
  ok "Pas de node_modules sur le serveur"
fi

# __pycache__ on host
PYCACHE=$(find . -maxdepth 3 -name "__pycache__" -type d 2>/dev/null | wc -l)
info "__pycache__ sur le host: $PYCACHE dossier(s)"

# .pyc files
PYC=$(find . -maxdepth 3 -name "*.pyc" 2>/dev/null | wc -l)
info ".pyc sur le host: $PYC fichier(s)"

# Temp/log files
TEMP_LOGS=$(find . -maxdepth 2 -name "*.log" 2>/dev/null | wc -l)
info "Fichiers .log: $TEMP_LOGS"

# Docker compose override (dev leftover?)
if [ -f "docker-compose.override.yml" ] || [ -f "infra/docker/docker-compose.override.yml" ]; then
  wn "docker-compose.override.yml présent (résidu dev?)"
else
  ok "Pas de docker-compose.override.yml"
fi

###############################################################################
head "17. PERFORMANCE — TEMPS DE RÉPONSE"
###############################################################################
for EP in "/api/health/" "/api/login/" "/" "/api/exams/"; do
  if [ "$EP" = "/api/login/" ]; then
    TIME=$(curl -o /dev/null -w '%{time_total}' -s --max-time 10 -H "X-Forwarded-Proto: https" -H "Host: $DOMAIN" -H "Content-Type: application/json" -d '{"username":"admin","password":"8FvkX0wtMDj6ffsNLRBsRw"}' "$LOCAL$EP" 2>/dev/null || echo "timeout")
  elif [ "$EP" = "/api/exams/" ]; then
    TIME=$(curl -o /dev/null -w '%{time_total}' -s --max-time 10 -H "X-Forwarded-Proto: https" -H "Host: $DOMAIN" -b /tmp/korrigo_audit_cookies.txt "$LOCAL$EP" 2>/dev/null || echo "timeout")
  else
    TIME=$(curl -o /dev/null -w '%{time_total}' -s --max-time 10 -H "X-Forwarded-Proto: https" -H "Host: $DOMAIN" "$LOCAL$EP" 2>/dev/null || echo "timeout")
  fi
  MS=$(echo "$TIME" | awk '{printf "%.0f", $1*1000}' 2>/dev/null || echo "?")
  if [ "$MS" != "?" ] && [ "$MS" -lt 500 ] 2>/dev/null; then
    ok "$EP → ${MS}ms"
  elif [ "$MS" != "?" ] && [ "$MS" -lt 2000 ] 2>/dev/null; then
    wn "$EP → ${MS}ms (acceptable)"
  else
    wn "$EP → ${MS}ms (lent)"
  fi
done

###############################################################################
head "18. RÉSEAU DOCKER"
###############################################################################
info "Réseaux Docker du projet:"
docker network ls 2>/dev/null | grep -i "docker\|korrigo" | sed 's/^/     /'

info "Résolution DNS inter-conteneurs:"
for SVC in db redis backend; do
  RESOLVED=$($COMPOSE exec -T nginx getent hosts $SVC 2>/dev/null | head -1 || echo "FAIL")
  [ "$RESOLVED" != "FAIL" ] && ok "nginx → $SVC: $RESOLVED" || wn "nginx → $SVC: résolution échouée"
done

###############################################################################
###############################################################################
sep
echo ""
echo "  ╔══════════════════════════════════════════════════════════════╗"
echo "  ║          BILAN D'AUDIT KORRIGO PRODUCTION                   ║"
echo "  ║          $(date '+%Y-%m-%d %H:%M:%S %Z')                             ║"
echo "  ╠══════════════════════════════════════════════════════════════╣"
printf "  ║  ✅ PASS : %-4d                                             ║\n" $PASS
printf "  ║  ⚠️  WARN : %-4d                                             ║\n" $WARN
printf "  ║  ❌ FAIL : %-4d                                             ║\n" $FAIL
echo "  ╠══════════════════════════════════════════════════════════════╣"
TOTAL=$((PASS+FAIL))
if [ "$TOTAL" -gt 0 ]; then
  SCORE=$((PASS * 100 / TOTAL))
else
  SCORE=0
fi
if [ "$FAIL" -eq 0 ] && [ "$WARN" -le 3 ]; then
  VERDICT="🟢 PRODUCTION READY — ÉTAT OPTIMAL"
elif [ "$FAIL" -eq 0 ]; then
  VERDICT="🟢 PRODUCTION READY — WARNINGS MINEURS"
elif [ "$FAIL" -le 3 ]; then
  VERDICT="🟡 CORRECTIONS MINEURES NÉCESSAIRES"
else
  VERDICT="🔴 CORRECTIONS CRITIQUES REQUISES"
fi
printf "  ║  📊 SCORE : %d%% (%d/%d)                                    ║\n" $SCORE $PASS $TOTAL
printf "  ║  🏷️  %s  ║\n" "$VERDICT"
echo "  ╚══════════════════════════════════════════════════════════════╝"
echo ""

# Recommendations
if [ "$WARN" -gt 0 ] || [ "$FAIL" -gt 0 ]; then
  echo "  📋 RECOMMANDATIONS:"
  echo "  ─────────────────────"
  [ "$DANGLING" -gt 0 ] && echo "  • docker image prune -f  (supprimer images dangling)"
  [ "$EXITED" -gt 0 ] && echo "  • docker container prune -f  (supprimer conteneurs arrêtés)"
  [ "$ORPHAN_VOL" -gt 0 ] && echo "  • docker volume prune -f  (supprimer volumes orphelins)"
  [ "${DEAD_TUPLES:-0}" -ge 1000 ] 2>/dev/null && echo "  • VACUUM ANALYZE sur PostgreSQL"
  echo ""
fi

echo "  Audit terminé."
echo ""
