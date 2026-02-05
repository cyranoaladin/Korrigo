#!/usr/bin/env bash
# Script de déploiement des correctifs Korrigo
# Usage: bash scripts/deploy_fixes.sh [--dry-run]

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

DRY_RUN=false
if [[ "${1:-}" == "--dry-run" ]]; then
    DRY_RUN=true
    echo -e "${YELLOW}⚠️  Mode DRY-RUN activé (aucune modification ne sera effectuée)${NC}"
    echo
fi

echo "=============================================="
echo "🚀 Déploiement Correctifs Korrigo"
echo "=============================================="
echo "Date: $(date)"
echo "Utilisateur: $(whoami)"
echo "Répertoire: $PROJECT_ROOT"
echo

# Fonction pour afficher un message
info() {
    echo -e "${BLUE}ℹ️  $*${NC}"
}

success() {
    echo -e "${GREEN}✅ $*${NC}"
}

warning() {
    echo -e "${YELLOW}⚠️  $*${NC}"
}

error() {
    echo -e "${RED}❌ $*${NC}"
}

# Fonction pour exécuter une commande (avec support dry-run)
run_cmd() {
    local cmd="$*"
    if [ "$DRY_RUN" = true ]; then
        echo -e "${YELLOW}[DRY-RUN]${NC} $cmd"
    else
        info "Exécution: $cmd"
        eval "$cmd"
    fi
}

# Étape 0 : Vérification préalable
echo "--------------------------------------------"
echo "📋 Étape 0 : Vérification préalable"
echo "--------------------------------------------"

if [ ! -f "backend/core/settings.py" ]; then
    error "Fichier backend/core/settings.py introuvable"
    exit 1
fi

if [ ! -f ".env.labomaths" ]; then
    error "Fichier .env.labomaths introuvable"
    error "Ce fichier devrait avoir été créé par l'audit"
    exit 1
fi

success "Fichiers requis présents"
echo

# Étape 1 : Backup
echo "--------------------------------------------"
echo "💾 Étape 1 : Backup"
echo "--------------------------------------------"

BACKUP_DIR="backups/$(date +%Y%m%d_%H%M%S)"
run_cmd "mkdir -p $BACKUP_DIR"

if [ -f ".env" ]; then
    run_cmd "cp .env $BACKUP_DIR/.env.backup"
    success "Backup .env → $BACKUP_DIR/.env.backup"
else
    warning ".env n'existe pas encore (première installation)"
fi

run_cmd "cp backend/core/settings.py $BACKUP_DIR/settings.py.backup"
success "Backup settings.py → $BACKUP_DIR/settings.py.backup"

if [ -d "media" ]; then
    info "Backup media/ (peut prendre du temps)..."
    run_cmd "tar -czf $BACKUP_DIR/media_backup.tar.gz media/ || true"
fi

echo

# Étape 2 : Configuration .env
echo "--------------------------------------------"
echo "🔧 Étape 2 : Configuration .env"
echo "--------------------------------------------"

if [ -f ".env" ]; then
    warning ".env existe déjà"
    read -p "Écraser avec .env.labomaths ? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        run_cmd "cp .env.labomaths .env"
        success ".env mis à jour depuis .env.labomaths"
        warning "⚠️  IMPORTANT: Éditer .env et remplacer SECRET_KEY, DB_PASSWORD, etc."
    else
        info "Conservation du .env existant"
    fi
else
    run_cmd "cp .env.labomaths .env"
    success ".env créé depuis .env.labomaths"
    warning "⚠️  IMPORTANT: Éditer .env et remplacer SECRET_KEY, DB_PASSWORD, etc."
fi

echo

# Étape 3 : Vérification des modifications settings.py
echo "--------------------------------------------"
echo "🔍 Étape 3 : Vérification settings.py"
echo "--------------------------------------------"

if grep -q "# CRITICAL FIX: Re-apply SameSite settings from env in production" backend/core/settings.py; then
    success "Correctif SameSite déjà appliqué dans settings.py"
else
    error "Correctif SameSite MANQUANT dans settings.py"
    error "Les modifications ont été perdues. Réappliquer depuis le commit Git ou AUDIT_FINAL.md"
    exit 1
fi

if grep -q "DATA_UPLOAD_MAX_MEMORY_SIZE = 1073741824" backend/core/settings.py; then
    success "Limite upload 1GB déjà appliquée dans settings.py"
else
    warning "Limite upload non définie à 1GB (vérifier settings.py ligne 74)"
fi

echo

# Étape 4 : Redéploiement Docker
echo "--------------------------------------------"
echo "🐳 Étape 4 : Redéploiement Docker"
echo "--------------------------------------------"

COMPOSE_FILE="infra/docker/docker-compose.prod.yml"

if [ ! -f "$COMPOSE_FILE" ]; then
    warning "Fichier $COMPOSE_FILE introuvable"
    info "Recherche d'un autre fichier docker-compose..."

    if [ -f "docker-compose.yml" ]; then
        COMPOSE_FILE="docker-compose.yml"
        info "Utilisation de docker-compose.yml"
    else
        error "Aucun fichier docker-compose trouvé"
        exit 1
    fi
fi

info "Utilisation de $COMPOSE_FILE"

# Arrêt des containers
run_cmd "docker-compose -f $COMPOSE_FILE down || true"
success "Containers arrêtés"

# Rebuild backend
info "Rebuild du backend..."
run_cmd "docker-compose -f $COMPOSE_FILE build backend"
success "Backend rebuild terminé"

# Démarrage
info "Démarrage des containers..."
run_cmd "docker-compose -f $COMPOSE_FILE up -d"
success "Containers démarrés"

# Attendre que le backend soit prêt
info "Attente du backend (30s)..."
if [ "$DRY_RUN" = false ]; then
    sleep 30
fi

echo

# Étape 5 : Vérification Django
echo "--------------------------------------------"
echo "🔍 Étape 5 : Vérification configuration Django"
echo "--------------------------------------------"

if [ "$DRY_RUN" = false ]; then
    BACKEND_CONTAINER=$(docker ps | grep backend | awk '{print $1}' | head -1)

    if [ -z "$BACKEND_CONTAINER" ]; then
        error "Container backend non trouvé"
    else
        info "Container backend: $BACKEND_CONTAINER"

        echo "Configuration Django actuelle:"
        docker exec "$BACKEND_CONTAINER" python -c "
from django.conf import settings
config = {
    'DEBUG': settings.DEBUG,
    'SESSION_COOKIE_SAMESITE': settings.SESSION_COOKIE_SAMESITE,
    'CSRF_COOKIE_SAMESITE': settings.CSRF_COOKIE_SAMESITE,
    'SESSION_COOKIE_SECURE': settings.SESSION_COOKIE_SECURE,
    'CSRF_COOKIE_SECURE': settings.CSRF_COOKIE_SECURE,
    'CORS_ALLOW_CREDENTIALS': settings.CORS_ALLOW_CREDENTIALS,
}
for k, v in config.items():
    status = '✅' if (k.endswith('SAMESITE') and v == 'None') or (k.endswith('SECURE') and v == True) or (k == 'DEBUG' and v == False) or (k == 'CORS_ALLOW_CREDENTIALS' and v == True) else '⚠️'
    print(f'{status} {k:30} = {v}')
" || error "Impossible de vérifier la configuration Django"
    fi
else
    info "[DRY-RUN] Vérification Django skipped"
fi

echo

# Étape 6 : Instructions Nginx
echo "--------------------------------------------"
echo "🌐 Étape 6 : Configuration Nginx externe"
echo "--------------------------------------------"

warning "⚠️  Configuration Nginx externe requise (action manuelle)"
echo
echo "1. Éditer la configuration Nginx:"
echo "   sudo nano /etc/nginx/sites-available/labomaths_ecosystem"
echo
echo "2. Ajouter les directives suivantes (voir scripts/nginx_korrigo_config.conf):"
echo "   client_max_body_size 1G;"
echo "   proxy_connect_timeout 3600s;"
echo "   proxy_send_timeout 3600s;"
echo "   proxy_read_timeout 3600s;"
echo "   proxy_set_header X-Forwarded-Proto https;"
echo
echo "3. Tester et recharger:"
echo "   sudo nginx -t"
echo "   sudo systemctl reload nginx"
echo

read -p "Configuration Nginx externe effectuée ? (y/N) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    success "Configuration Nginx confirmée"
else
    warning "Configuration Nginx à effectuer manuellement"
fi

echo

# Étape 7 : Tests
echo "--------------------------------------------"
echo "🧪 Étape 7 : Tests"
echo "--------------------------------------------"

if [ "$DRY_RUN" = false ]; then
    if [ -f "scripts/diag_403.sh" ]; then
        info "Exécution du diagnostic..."
        bash scripts/diag_403.sh || warning "Diagnostic échoué (vérifier manuellement)"
    else
        warning "Script scripts/diag_403.sh introuvable"
    fi
else
    info "[DRY-RUN] Tests skipped"
fi

echo

# Résumé final
echo "=============================================="
echo "✅ Déploiement Terminé"
echo "=============================================="
echo
success "Correctifs déployés avec succès"
echo
echo "📋 Actions manuelles restantes:"
echo "  1. Éditer .env et remplacer SECRET_KEY, DB_PASSWORD"
echo "  2. Configurer Nginx externe (voir étape 6)"
echo "  3. Tester dans le navigateur:"
echo "     - Login sur https://korrigo.labomaths.tn"
echo "     - Vérifier cookies (DevTools > Application)"
echo "     - Recharger (F5)"
echo "     - Vérifier /api/me/ → 200 OK"
echo
echo "📂 Backup sauvegardé dans: $BACKUP_DIR"
echo
echo "📖 Documentation complète: AUDIT_FINAL.md"
echo

if [ "$DRY_RUN" = true ]; then
    echo -e "${YELLOW}⚠️  Mode DRY-RUN: Aucune modification effectuée${NC}"
    echo -e "${YELLOW}   Relancer sans --dry-run pour appliquer les changements${NC}"
fi
