#!/bin/bash
#
# 🚀 SCRIPT DE DÉPLOIEMENT KORRIGO
# Déploie les mises à jour sur korrigo.labomaths.tn
#
# Usage: ./deploy_korrigo.sh
#

set -e  # Exit on error

# ============================================================================
# CONFIGURATION
# ============================================================================
PROJECT_DIR="/var/www/labomaths/korrigo"
DOCKER_COMPOSE_FILE="docker-compose.labomaths.yml"
BACKUP_DIR="/var/backups/korrigo"
LOG_FILE="/var/log/korrigo_deploy.log"

# Couleurs pour output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# ============================================================================
# FONCTIONS UTILITAIRES
# ============================================================================

log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1" | tee -a "$LOG_FILE"
}

success() {
    echo -e "${GREEN}✓${NC} $1" | tee -a "$LOG_FILE"
}

warning() {
    echo -e "${YELLOW}⚠${NC} $1" | tee -a "$LOG_FILE"
}

error() {
    echo -e "${RED}✗${NC} $1" | tee -a "$LOG_FILE"
    exit 1
}

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

# Vérifier que le script est exécuté en root
if [[ $EUID -ne 0 ]]; then
   error "Ce script doit être exécuté en tant que root (sudo)"
fi

# Vérifier que le répertoire existe
if [ ! -d "$PROJECT_DIR" ]; then
    error "Répertoire projet non trouvé: $PROJECT_DIR"
fi

cd "$PROJECT_DIR" || error "Impossible d'accéder au répertoire: $PROJECT_DIR"
success "Répertoire projet: $PROJECT_DIR"

# Vérifier Docker
if ! command -v docker &> /dev/null; then
    error "Docker n'est pas installé"
fi
success "Docker installé"

# Vérifier docker-compose
if ! command -v docker &> /dev/null; then
    error "Docker Compose n'est pas installé"
fi
success "Docker Compose installé"

# ============================================================================
# BACKUP BASE DE DONNÉES
# ============================================================================

section "💾 BACKUP BASE DE DONNÉES"

# Créer le répertoire de backup si nécessaire
mkdir -p "$BACKUP_DIR"

BACKUP_FILE="$BACKUP_DIR/korrigo_db_$(date +'%Y%m%d_%H%M%S').sql"

log "Création du backup: $BACKUP_FILE"
docker exec korrigo-db-1 pg_dump -U viatique_user viatique > "$BACKUP_FILE" 2>/dev/null || {
    warning "Impossible de créer le backup (conteneur peut-être arrêté)"
}

if [ -f "$BACKUP_FILE" ] && [ -s "$BACKUP_FILE" ]; then
    success "Backup créé: $BACKUP_FILE"
    # Garder seulement les 10 derniers backups
    ls -t "$BACKUP_DIR"/korrigo_db_*.sql | tail -n +11 | xargs -r rm
    success "Anciens backups nettoyés (gardé les 10 derniers)"
else
    warning "Backup vide ou non créé (première installation?)"
fi

# ============================================================================
# MISE À JOUR DU CODE SOURCE
# ============================================================================

section "📥 MISE À JOUR DU CODE SOURCE"

# Configurer Git safe directory
git config --global --add safe.directory "$PROJECT_DIR" 2>/dev/null || true

# Vérifier l'état Git
log "Vérification de l'état Git..."
git fetch origin || error "Impossible de récupérer les mises à jour depuis GitHub"

CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "main")
success "Branche actuelle: $CURRENT_BRANCH"

LOCAL_COMMIT=$(git rev-parse HEAD)
REMOTE_COMMIT=$(git rev-parse origin/$CURRENT_BRANCH)

if [ "$LOCAL_COMMIT" == "$REMOTE_COMMIT" ]; then
    warning "Aucune mise à jour disponible (déjà à jour)"
else
    log "Nouvelles modifications disponibles"
    log "Local:  $LOCAL_COMMIT"
    log "Remote: $REMOTE_COMMIT"
    
    # Sauvegarder les modifications locales si nécessaire
    if ! git diff-index --quiet HEAD --; then
        warning "Modifications locales détectées, création d'un stash..."
        git stash save "Auto-stash avant déploiement $(date +'%Y-%m-%d %H:%M:%S')"
    fi
    
    # Pull les modifications
    log "Récupération des modifications..."
    git pull origin "$CURRENT_BRANCH" || error "Échec du git pull"
    success "Code source mis à jour"
fi

# ============================================================================
# REBUILD DES CONTENEURS DOCKER
# ============================================================================

section "🐳 REBUILD DES CONTENEURS DOCKER"

log "Arrêt des conteneurs..."
docker compose -f "$DOCKER_COMPOSE_FILE" down || warning "Certains conteneurs n'étaient pas démarrés"

log "Rebuild des images Docker..."
docker compose -f "$DOCKER_COMPOSE_FILE" build --no-cache || error "Échec du build Docker"
success "Images Docker reconstruites"

# ============================================================================
# DÉMARRAGE DES SERVICES
# ============================================================================

section "🚀 DÉMARRAGE DES SERVICES"

log "Démarrage des conteneurs..."
docker compose -f "$DOCKER_COMPOSE_FILE" up -d || error "Échec du démarrage des conteneurs"

# Attendre que les services soient prêts
log "Attente du démarrage des services (30s)..."
sleep 30

# Vérifier l'état des conteneurs
log "Vérification de l'état des conteneurs..."
docker compose -f "$DOCKER_COMPOSE_FILE" ps

# ============================================================================
# MIGRATIONS BASE DE DONNÉES
# ============================================================================

section "🗄️  MIGRATIONS BASE DE DONNÉES"

log "Application des migrations..."
docker exec korrigo-backend-1 python manage.py migrate --noinput || error "Échec des migrations"
success "Migrations appliquées"

# ============================================================================
# COLLECTE DES FICHIERS STATIQUES
# ============================================================================

section "📦 COLLECTE DES FICHIERS STATIQUES"

log "Collecte des fichiers statiques..."
docker exec korrigo-backend-1 python manage.py collectstatic --noinput --clear || error "Échec de la collecte des fichiers statiques"
success "Fichiers statiques collectés"

# ============================================================================
# VÉRIFICATIONS POST-DÉPLOIEMENT
# ============================================================================

section "✅ VÉRIFICATIONS POST-DÉPLOIEMENT"

# Vérifier que tous les conteneurs sont en cours d'exécution
log "Vérification des conteneurs..."
RUNNING_CONTAINERS=$(docker compose -f "$DOCKER_COMPOSE_FILE" ps --services --filter "status=running" | wc -l)
TOTAL_CONTAINERS=$(docker compose -f "$DOCKER_COMPOSE_FILE" ps --services | wc -l)

if [ "$RUNNING_CONTAINERS" -eq "$TOTAL_CONTAINERS" ]; then
    success "Tous les conteneurs sont en cours d'exécution ($RUNNING_CONTAINERS/$TOTAL_CONTAINERS)"
else
    warning "Certains conteneurs ne sont pas démarrés ($RUNNING_CONTAINERS/$TOTAL_CONTAINERS)"
fi

# Vérifier le health check du backend
log "Vérification du health check backend..."
sleep 10
HEALTH_STATUS=$(docker inspect korrigo-backend-1 --format='{{.State.Health.Status}}' 2>/dev/null || echo "unknown")
if [ "$HEALTH_STATUS" == "healthy" ]; then
    success "Backend healthy"
else
    warning "Backend status: $HEALTH_STATUS (peut prendre quelques minutes)"
fi

# Tester l'endpoint API
log "Test de l'endpoint API..."
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:4000/api/health/ 2>/dev/null || echo "000")
if [ "$HTTP_CODE" == "200" ]; then
    success "API répond correctement (HTTP $HTTP_CODE)"
else
    warning "API status: HTTP $HTTP_CODE"
fi

# ============================================================================
# NETTOYAGE
# ============================================================================

section "🧹 NETTOYAGE"

log "Nettoyage des images Docker inutilisées..."
docker image prune -f || warning "Échec du nettoyage des images"
success "Images inutilisées supprimées"

# ============================================================================
# RÉSUMÉ
# ============================================================================

section "📊 RÉSUMÉ DU DÉPLOIEMENT"

echo ""
success "Déploiement terminé avec succès !"
echo ""
echo "📍 URL: https://korrigo.labomaths.tn"
echo "📂 Répertoire: $PROJECT_DIR"
echo "💾 Backup: $BACKUP_FILE"
echo "📝 Log: $LOG_FILE"
echo ""
echo "🔍 Commandes utiles:"
echo "  - Voir les logs backend:  docker logs -f korrigo-backend-1"
echo "  - Voir les logs frontend: docker logs -f korrigo-frontend_nginx-1"
echo "  - Voir les logs celery:   docker logs -f korrigo-celery-1"
echo "  - Redémarrer:             docker compose -f $DOCKER_COMPOSE_FILE restart"
echo "  - Arrêter:                docker compose -f $DOCKER_COMPOSE_FILE down"
echo ""

log "Déploiement terminé à $(date +'%Y-%m-%d %H:%M:%S')"
