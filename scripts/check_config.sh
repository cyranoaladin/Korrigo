#!/usr/bin/env bash
# Script de vérification de configuration Korrigo
# Usage: bash scripts/check_config.sh

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

echo "=============================================="
echo "🔍 Vérification Configuration Korrigo"
echo "=============================================="
echo

# Fonction pour afficher un résultat
check_result() {
    local status=$1
    local message=$2
    if [ "$status" = "ok" ]; then
        echo -e "${GREEN}✅ $message${NC}"
    elif [ "$status" = "warn" ]; then
        echo -e "${YELLOW}⚠️  $message${NC}"
    else
        echo -e "${RED}❌ $message${NC}"
    fi
}

# Vérifier l'existence du fichier .env
echo "📄 Vérification fichier .env"
echo "--------------------------------------------"
if [ ! -f .env ]; then
    check_result "error" ".env n'existe pas"
    echo "   Créer le fichier .env en utilisant .env.labomaths comme template"
    exit 1
else
    check_result "ok" ".env existe"
fi
echo

# Vérifier les variables critiques dans .env
echo "🔐 Vérification variables d'environnement"
echo "--------------------------------------------"

check_env_var() {
    local var_name=$1
    local expected_value=$2
    local value=$(grep "^${var_name}=" .env 2>/dev/null | cut -d'=' -f2- || echo "")

    if [ -z "$value" ]; then
        check_result "error" "$var_name non défini dans .env"
        return 1
    elif [ -n "$expected_value" ] && [ "$value" != "$expected_value" ]; then
        check_result "warn" "$var_name = $value (attendu: $expected_value)"
        return 1
    else
        check_result "ok" "$var_name = $value"
        return 0
    fi
}

# Vérifier les variables critiques
check_env_var "SESSION_COOKIE_SAMESITE" "None"
check_env_var "CSRF_COOKIE_SAMESITE" "None"
check_env_var "SSL_ENABLED" "true"
check_env_var "DEBUG" "False"
check_env_var "DJANGO_ENV" "production"

echo
echo "🌐 Vérification CORS et CSRF"
echo "--------------------------------------------"
CORS_ORIGINS=$(grep "^CORS_ALLOWED_ORIGINS=" .env 2>/dev/null | cut -d'=' -f2- || echo "")
CSRF_ORIGINS=$(grep "^CSRF_TRUSTED_ORIGINS=" .env 2>/dev/null | cut -d'=' -f2- || echo "")

if [[ "$CORS_ORIGINS" == *"korrigo.labomaths.tn"* ]]; then
    check_result "ok" "CORS_ALLOWED_ORIGINS contient korrigo.labomaths.tn"
else
    check_result "error" "CORS_ALLOWED_ORIGINS ne contient pas korrigo.labomaths.tn"
fi

if [[ "$CSRF_ORIGINS" == *"korrigo.labomaths.tn"* ]]; then
    check_result "ok" "CSRF_TRUSTED_ORIGINS contient korrigo.labomaths.tn"
else
    check_result "error" "CSRF_TRUSTED_ORIGINS ne contient pas korrigo.labomaths.tn"
fi

echo
echo "📦 Vérification modifications backend/core/settings.py"
echo "--------------------------------------------"

# Vérifier que le fix SameSite est présent
if grep -q "# CRITICAL FIX: Re-apply SameSite settings from env in production" backend/core/settings.py; then
    check_result "ok" "Fix SameSite présent dans settings.py"
else
    check_result "error" "Fix SameSite MANQUANT dans settings.py (ligne ~119)"
    echo "   Appliquer la correction du fichier CORRECTIFS_403.md"
fi

# Vérifier FILE_UPLOAD_MAX_MEMORY_SIZE
if grep -q "DATA_UPLOAD_MAX_MEMORY_SIZE = 1073741824" backend/core/settings.py; then
    check_result "ok" "DATA_UPLOAD_MAX_MEMORY_SIZE = 1GB"
else
    check_result "warn" "DATA_UPLOAD_MAX_MEMORY_SIZE non défini à 1GB"
fi

echo
echo "🐳 Vérification containers Docker"
echo "--------------------------------------------"

# Vérifier si les containers sont en cours d'exécution
if docker ps | grep -q "korrigo.*backend"; then
    check_result "ok" "Container backend en cours d'exécution"

    # Tester la connexion au backend
    if docker exec $(docker ps | grep "korrigo.*backend" | awk '{print $1}') python -c "from django.conf import settings; print('ok')" 2>/dev/null | grep -q "ok"; then
        check_result "ok" "Backend Django accessible"

        # Vérifier la config Django
        echo
        echo "📋 Configuration Django actuelle:"
        echo "--------------------------------------------"
        docker exec $(docker ps | grep "korrigo.*backend" | awk '{print $1}') python -c "
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
    print(f'{k:30} = {v}')
" 2>/dev/null || echo "   Impossible de lire la configuration Django"
    else
        check_result "warn" "Impossible d'accéder au backend Django"
    fi
else
    check_result "warn" "Container backend non détecté (docker ps)"
    echo "   Démarrer les containers avec: docker-compose up -d"
fi

echo
echo "🌐 Vérification Nginx externe"
echo "--------------------------------------------"

# Vérifier si Nginx est installé
if command -v nginx &> /dev/null; then
    check_result "ok" "Nginx installé"

    # Vérifier la config Nginx
    if sudo nginx -t 2>&1 | grep -q "test is successful"; then
        check_result "ok" "Configuration Nginx valide"
    else
        check_result "error" "Configuration Nginx invalide"
        echo "   Exécuter: sudo nginx -t"
    fi

    # Vérifier client_max_body_size dans la config
    if sudo grep -r "client_max_body_size.*1[GgBb]" /etc/nginx/sites-enabled/ 2>/dev/null | grep -q .; then
        check_result "ok" "client_max_body_size configuré (>= 1GB)"
    else
        check_result "warn" "client_max_body_size non trouvé ou < 1GB"
        echo "   Vérifier /etc/nginx/sites-available/labomaths_ecosystem"
    fi
else
    check_result "warn" "Nginx non installé ou non accessible"
fi

echo
echo "=============================================="
echo "🎯 Résumé"
echo "=============================================="
echo
echo "Pour appliquer les corrections :"
echo "  1. Consulter CORRECTIFS_403.md"
echo "  2. Mettre à jour .env avec les valeurs de .env.labomaths"
echo "  3. Redéployer: docker-compose up -d --build"
echo "  4. Mettre à jour Nginx: scripts/nginx_korrigo_config.conf"
echo "  5. Tester: bash scripts/diag_403.sh"
echo
echo "✅ FIN DE VÉRIFICATION"
