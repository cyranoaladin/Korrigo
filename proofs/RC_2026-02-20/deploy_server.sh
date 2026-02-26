#!/bin/bash
# ============================================================
# SCRIPT DE DÉPLOIEMENT SERVEUR KORRIGO
# ============================================================
# Ce script configure un serveur Ubuntu 24.04 frais pour Korrigo :
# 1. Installe Docker + Docker Compose
# 2. Configure nginx externe
# 3. Déploie les overlay backend files
# 4. Crée le .env de production
# 5. Lance les containers Docker
# 6. Exécute les migrations Django
# 7. Lance le script de reconstitution DB
#
# Usage: Sur le serveur en tant que root
#   bash /root/deploy_server.sh
# ============================================================

set -euo pipefail

KORRIGO_DIR="/var/www/labomaths/korrigo"
INFRA_DIR="${KORRIGO_DIR}/infra/docker"
OVERLAY_DIR="${KORRIGO_DIR}/overlay"
DATA_DIR="${KORRIGO_DIR}/reconstitution_data"
SEED_DIR="${KORRIGO_DIR}/seed_data"

log() { echo "[$(date '+%H:%M:%S')] $1"; }

log "=========================================="
log "DÉPLOIEMENT KORRIGO - DÉBUT"
log "=========================================="

# ============================================================
# STEP 1: Install Docker
# ============================================================
log "--- STEP 1: Installation Docker ---"
if command -v docker &>/dev/null; then
    log "Docker déjà installé: $(docker --version)"
else
    apt-get update -qq
    apt-get install -y -qq ca-certificates curl gnupg
    install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
    chmod a+r /etc/apt/keyrings/docker.asc
    echo "deb [arch=amd64 signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu noble stable" > /etc/apt/sources.list.d/docker.list
    apt-get update -qq
    apt-get install -y -qq docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
    systemctl enable --now docker
    log "Docker installé: $(docker --version)"
fi

# ============================================================
# STEP 2: Install nginx
# ============================================================
log "--- STEP 2: Installation nginx ---"
if command -v nginx &>/dev/null; then
    log "nginx déjà installé"
else
    apt-get install -y -qq nginx
    systemctl enable --now nginx
    log "nginx installé"
fi

# ============================================================
# STEP 3: Create directory structure
# ============================================================
log "--- STEP 3: Structure des répertoires ---"
mkdir -p "${KORRIGO_DIR}"/{infra/docker,overlay,reconstitution_data,seed_data,backups}
log "Répertoires créés"

# ============================================================
# STEP 4: Configure nginx
# ============================================================
log "--- STEP 4: Configuration nginx ---"
cat > /etc/nginx/sites-available/korrigo <<'NGINX'
server {
    listen 80 default_server;
    listen [::]:80 default_server;
    server_name _;

    client_max_body_size 100M;

    location / {
        proxy_pass http://127.0.0.1:8088;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /api/ {
        proxy_pass http://127.0.0.1:8088;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 300;
    }
}
NGINX

ln -sf /etc/nginx/sites-available/korrigo /etc/nginx/sites-enabled/korrigo
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl reload nginx
log "nginx configuré"

# ============================================================
# STEP 5: Create .env file
# ============================================================
log "--- STEP 5: Fichier .env ---"
if [ ! -f "${INFRA_DIR}/.env" ]; then
    cat > "${INFRA_DIR}/.env" <<'ENV'
# Korrigo Production Environment
POSTGRES_DB=korrigo_db
POSTGRES_USER=korrigo_user
POSTGRES_PASSWORD=K0rr1g0_Pr0d_2026!
SECRET_KEY=django-insecure-reconstitution-change-me-in-production-k0rr1g0-2026
ALLOWED_HOSTS=88.99.254.59,korrigo.labomaths.tn,localhost
CORS_ALLOWED_ORIGINS=http://88.99.254.59,http://korrigo.labomaths.tn,http://localhost
CSRF_TRUSTED_ORIGINS=http://88.99.254.59,http://korrigo.labomaths.tn,http://localhost
METRICS_TOKEN=metrics-token-2026
GITHUB_REPOSITORY_OWNER=cyranoaladin
KORRIGO_SHA=latest
SEED_DATA_HOST_PATH=/var/www/labomaths/korrigo/seed_data
ADMIN_PASSWORD=admin2026!
TEACHER_PASSWORD=teacher2026!
DEFAULT_PASSWORD=passe123
SEED_ON_START=false
SSL_ENABLED=False
ENV
    log ".env créé"
else
    log ".env existe déjà"
fi

# ============================================================
# STEP 6: Create ollama network (required by compose)
# ============================================================
log "--- STEP 6: Réseau Docker ollama ---"
docker network create infra_rag_net 2>/dev/null || true
log "Réseau infra_rag_net créé/existant"

# ============================================================
# STEP 7: Pull and start containers
# ============================================================
log "--- STEP 7: Démarrage des containers ---"
cd "${INFRA_DIR}"

# Try to pull images - if GHCR fails, we'll need to build locally
log "Pull des images Docker..."
docker compose -f docker-compose.prod.yml pull 2>&1 || {
    log "WARN: Pull failed - may need GHCR auth or local build"
    log "Try: echo <GITHUB_TOKEN> | docker login ghcr.io -u cyranoaladin --password-stdin"
}

log "Démarrage des services..."
docker compose -f docker-compose.prod.yml up -d 2>&1 || {
    log "ERROR: Failed to start containers"
    docker compose -f docker-compose.prod.yml logs --tail=20 2>&1
    exit 1
}

log "Attente que la DB soit prête..."
sleep 10

# ============================================================
# STEP 8: Run migrations
# ============================================================
log "--- STEP 8: Migrations Django ---"
docker exec docker-backend-1 python manage.py migrate --run-syncdb 2>&1 || {
    log "WARN: Migration failed, retrying in 15s..."
    sleep 15
    docker exec docker-backend-1 python manage.py migrate --run-syncdb 2>&1
}
log "Migrations terminées"

# ============================================================
# STEP 9: Run reconstitution
# ============================================================
log "--- STEP 9: Reconstitution de la DB ---"
if [ -f "${DATA_DIR}/reconstitution_data.json" ]; then
    docker exec \
        -e RECONSTITUTION_DATA=/data/reconstitution_data.json \
        -e J1_PDF_DIR=/data/copies_J1/ \
        -e J2_PDF_DIR=/data/copies_J2/ \
        -e J1_CSV=/data/eleves_maths_J1.csv \
        -e J2_CSV=/data/eleves_maths_J2.csv \
        -e MEDIA_ROOT=/app/media \
        docker-backend-1 python /data/reconstitute_db.py 2>&1
    log "Reconstitution terminée"
else
    log "WARN: reconstitution_data.json non trouvé dans ${DATA_DIR}"
    log "       Uploadez les données puis lancez manuellement"
fi

# ============================================================
# STEP 10: Collect static files
# ============================================================
log "--- STEP 10: Collecte des fichiers statiques ---"
docker exec docker-backend-1 python manage.py collectstatic --noinput 2>&1 || true

# ============================================================
# STEP 11: Verification
# ============================================================
log "--- STEP 11: Vérification ---"
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" 2>&1
log ""
docker exec docker-backend-1 python -c "
import os, sys
sys.path.append('/app')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
import django; django.setup()
from django.contrib.auth.models import User
from exams.models import Copy, Exam
from grading.models import Score, Annotation, QuestionRemark
from students.models import Student
print(f'Users: {User.objects.count()}')
print(f'Students: {Student.objects.count()}')
print(f'Exams: {Exam.objects.count()}')
print(f'Copies: {Copy.objects.count()}')
print(f'Scores: {Score.objects.count()}')
print(f'Annotations: {Annotation.objects.count()}')
print(f'Remarks: {QuestionRemark.objects.count()}')
for e in Exam.objects.all():
    c = Copy.objects.filter(exam=e)
    s = Score.objects.filter(copy__exam=e)
    print(f'  {e.name}: {c.count()} copies, {c.filter(status=\"GRADED\").count()} graded, {s.count()} scores')
" 2>&1

log "=========================================="
log "DÉPLOIEMENT TERMINÉ"
log "=========================================="
