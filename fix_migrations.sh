#!/bin/bash
# Script pour corriger les migrations et déployer le système d'authentification

set -e

echo "🔧 Correction des migrations et déploiement..."

cd /var/www/labomaths/korrigo

# 1. Créer les migrations avec --noinput pour éviter les prompts
echo "📊 Création des migrations..."
docker exec korrigo-backend-1 python manage.py makemigrations --noinput

# 2. Appliquer les migrations
echo "🗄️  Application des migrations..."
docker exec korrigo-backend-1 python manage.py migrate

# 3. Redémarrer le backend
echo "🔄 Redémarrage du backend..."
docker compose -f docker-compose.labomaths.yml restart backend

echo "✅ Migrations appliquées avec succès!"
