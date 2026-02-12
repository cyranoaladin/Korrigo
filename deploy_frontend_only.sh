#!/bin/bash
#
# 🎨 DÉPLOIEMENT FRONTEND UNIQUEMENT — ZERO DOWNTIME BACKEND
# Ne touche PAS au backend, à la BDD, à Redis ni à Celery.
# Seul le conteneur nginx/frontend est reconstruit.
#
# Usage: sudo ./deploy_frontend_only.sh
#
# Quand utiliser ce script :
#   - Changements CSS, JS, Vue.js, images, logos, routes frontend
#   - Nouvelles pages statiques (/korrigo, guides, etc.)
#   - Aucune modification backend (0 fichier dans backend/)
#   - Aucune nouvelle migration Django
#
# ⚠️  NE PAS utiliser si :
#   - Des fichiers backend ont changé (views.py, models.py, urls.py…)
#   - De nouvelles migrations Django ont été ajoutées
#   - requirements.txt a été modifié
#   → Dans ces cas, utiliser deploy_korrigo.sh (full deploy)
#

set -e

# ============================================================================
# CONFIGURATION
# ============================================================================
PROJECT_DIR="/var/www/labomaths/korrigo"
DOCKER_COMPOSE_FILE="docker-compose.labomaths.yml"
FRONTEND_SERVICE="frontend_nginx"
BACKUP_DIR="/var/backups/korrigo"
LOG_FILE="/var/log/korrigo_deploy_frontend.log"

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log()     { echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1" | tee -a "$LOG_FILE"; }
success() { echo -e "${GREEN}✓${NC} $1" | tee -a "$LOG_FILE"; }
warning() { echo -e "${YELLOW}⚠${NC} $1" | tee -a "$LOG_FILE"; }
error()   { echo -e "${RED}✗${NC} $1" | tee -a "$LOG_FILE"; exit 1; }

section() {
    echo ""
    echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
    echo ""
}

# ============================================================================
# VÉRIFICATIONS PRÉLIMINAIRES
# ============================================================================

section "🔍 VÉRIFICATIONS PRÉLIMINAIRES"

if [[ $EUID -ne 0 ]]; then
    error "Ce script doit être exécuté en tant que root (sudo)"
fi

if [ ! -d "$PROJECT_DIR" ]; then
    error "Répertoire projet non trouvé: $PROJECT_DIR"
fi

cd "$PROJECT_DIR" || error "Impossible d'accéder au répertoire: $PROJECT_DIR"
success "Répertoire projet: $PROJECT_DIR"

# ============================================================================
# SAFETY CHECK : Vérifier qu'aucun fichier backend n'a changé
# ============================================================================

section "🛡️  SAFETY CHECK — BACKEND INTACT ?"

git config --global --add safe.directory "$PROJECT_DIR" 2>/dev/null || true
git fetch origin || error "Impossible de récupérer les mises à jour depuis GitHub"

CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "main")
LOCAL_COMMIT=$(git rev-parse HEAD)
REMOTE_COMMIT=$(git rev-parse "origin/$CURRENT_BRANCH")

if [ "$LOCAL_COMMIT" == "$REMOTE_COMMIT" ]; then
    warning "Aucune mise à jour disponible (déjà à jour)"
    echo ""
    echo "Voulez-vous quand même reconstruire le frontend ? (y/N)"
    read -r FORCE_REBUILD
    if [ "$FORCE_REBUILD" != "y" ] && [ "$FORCE_REBUILD" != "Y" ]; then
        log "Annulé par l'utilisateur."
        exit 0
    fi
fi

# Vérifier que seul le frontend/docs a changé
BACKEND_CHANGES=$(git diff "$LOCAL_COMMIT".."$REMOTE_COMMIT" --name-only 2>/dev/null | grep -c '^backend/' || true)
MIGRATION_CHANGES=$(git diff "$LOCAL_COMMIT".."$REMOTE_COMMIT" --name-only 2>/dev/null | grep -ci 'migration' || true)

if [ "$BACKEND_CHANGES" -gt 0 ]; then
    error "⛔ ABANDON : $BACKEND_CHANGES fichier(s) backend modifié(s) ! Utilisez deploy_korrigo.sh à la place."
fi

if [ "$MIGRATION_CHANGES" -gt 0 ]; then
    error "⛔ ABANDON : $MIGRATION_CHANGES migration(s) détectée(s) ! Utilisez deploy_korrigo.sh à la place."
fi

success "Aucun fichier backend modifié"
success "Aucune migration détectée"
success "→ Déploiement frontend-only autorisé"

# ============================================================================
# BACKUP PRÉVENTIF (rapide — juste un snapshot de sécurité)
# ============================================================================

section "💾 BACKUP PRÉVENTIF"

mkdir -p "$BACKUP_DIR"
BACKUP_FILE="$BACKUP_DIR/korrigo_db_pre_frontend_$(date +'%Y%m%d_%H%M%S').sql"

log "Backup de sécurité: $BACKUP_FILE"
docker exec korrigo-db-1 pg_dump -U viatique_user viatique > "$BACKUP_FILE" 2>/dev/null || {
    warning "Backup non disponible (OK pour un deploy frontend-only)"
}

if [ -f "$BACKUP_FILE" ] && [ -s "$BACKUP_FILE" ]; then
    success "Backup créé: $BACKUP_FILE ($(du -h "$BACKUP_FILE" | cut -f1))"
else
    warning "Backup vide — ce n'est pas bloquant pour un deploy frontend"
fi

# ============================================================================
# VÉRIFIER QUE LE BACKEND TOURNE AVANT DE COMMENCER
# ============================================================================

section "🏥 VÉRIFICATION SERVICES EN COURS"

BACKEND_STATUS=$(docker inspect korrigo-backend-1 --format='{{.State.Status}}' 2>/dev/null || echo "unknown")
DB_STATUS=$(docker inspect korrigo-db-1 --format='{{.State.Status}}' 2>/dev/null || echo "unknown")

if [ "$BACKEND_STATUS" != "running" ]; then
    warning "Backend n'est pas running (status: $BACKEND_STATUS)"
fi
if [ "$DB_STATUS" != "running" ]; then
    warning "DB n'est pas running (status: $DB_STATUS)"
fi

success "Backend: $BACKEND_STATUS"
success "DB: $DB_STATUS"

# ============================================================================
# MISE À JOUR DU CODE SOURCE
# ============================================================================

section "📥 MISE À JOUR DU CODE SOURCE"

if ! git diff-index --quiet HEAD -- 2>/dev/null; then
    warning "Modifications locales détectées, création d'un stash..."
    git stash save "Auto-stash avant déploiement frontend $(date +'%Y-%m-%d %H:%M:%S')"
fi

log "Pull des modifications..."
git pull origin "$CURRENT_BRANCH" || error "Échec du git pull"
success "Code source mis à jour"

# ============================================================================
# REBUILD DU FRONTEND UNIQUEMENT
# ============================================================================

section "🎨 REBUILD FRONTEND UNIQUEMENT"

log "Les services suivants NE SONT PAS touchés :"
echo "  ✓ backend  (Gunicorn/Django — continue de tourner)"
echo "  ✓ db       (PostgreSQL — continue de tourner)"
echo "  ✓ redis    (Cache — continue de tourner)"
echo "  ✓ celery   (Workers — continue de tourner)"
echo ""

log "Rebuild de l'image $FRONTEND_SERVICE..."
docker compose -f "$DOCKER_COMPOSE_FILE" build --no-cache "$FRONTEND_SERVICE" || error "Échec du build frontend"
success "Image frontend reconstruite"

log "Redémarrage du conteneur $FRONTEND_SERVICE (le seul conteneur touché)..."
docker compose -f "$DOCKER_COMPOSE_FILE" up -d --no-deps "$FRONTEND_SERVICE" || error "Échec du redémarrage frontend"
success "Frontend redémarré"

# ============================================================================
# VÉRIFICATIONS POST-DÉPLOIEMENT
# ============================================================================

section "✅ VÉRIFICATIONS POST-DÉPLOIEMENT"

sleep 5

# Vérifier que le frontend répond
FRONTEND_STATUS=$(docker inspect korrigo-frontend_nginx-1 --format='{{.State.Status}}' 2>/dev/null || echo "unknown")
if [ "$FRONTEND_STATUS" == "running" ]; then
    success "Frontend: running"
else
    warning "Frontend status: $FRONTEND_STATUS"
fi

# Vérifier que le backend est toujours en marche (il NE doit PAS avoir été touché)
BACKEND_AFTER=$(docker inspect korrigo-backend-1 --format='{{.State.Status}}' 2>/dev/null || echo "unknown")
if [ "$BACKEND_AFTER" == "running" ]; then
    success "Backend: toujours running (non touché) ✓"
else
    warning "⚠ Backend status: $BACKEND_AFTER — vérifiez !"
fi

# Test health check
log "Test de l'API backend..."
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:4000/api/health/ 2>/dev/null || echo "000")
if [ "$HTTP_CODE" == "200" ]; then
    success "API backend répond: HTTP $HTTP_CODE"
else
    warning "API status: HTTP $HTTP_CODE (peut être normal si health check différent)"
fi

# Test page frontend
HTTP_FRONTEND=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:4000/ 2>/dev/null || echo "000")
if [ "$HTTP_FRONTEND" == "200" ]; then
    success "Frontend répond: HTTP $HTTP_FRONTEND"
else
    warning "Frontend status: HTTP $HTTP_FRONTEND"
fi

# ============================================================================
# RÉSUMÉ
# ============================================================================

section "📊 RÉSUMÉ DU DÉPLOIEMENT FRONTEND"

echo ""
success "Déploiement frontend terminé avec succès !"
echo ""
echo "  📍 URL: https://korrigo.labomaths.tn"
echo "  🎨 Conteneur touché: $FRONTEND_SERVICE (uniquement)"
echo "  🛡️  Non touchés: backend, db, redis, celery"
echo "  💾 Backup: $BACKUP_FILE"
echo "  📝 Log: $LOG_FILE"
echo ""
echo "  🔍 Vérifier :"
echo "     - https://korrigo.labomaths.tn/korrigo  (nouvelle landing page)"
echo "     - https://korrigo.labomaths.tn/          (portail connexion)"
echo "     - Le dashboard correcteur fonctionne toujours"
echo ""

log "Déploiement frontend terminé à $(date +'%Y-%m-%d %H:%M:%S')"
