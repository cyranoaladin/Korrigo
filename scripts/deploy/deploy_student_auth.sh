#!/bin/bash
# Script de déploiement du nouveau système d'authentification des étudiants
# À exécuter sur le serveur de production

set -e

echo "═══════════════════════════════════════════════════════════"
echo "  🔐 DÉPLOIEMENT SYSTÈME D'AUTHENTIFICATION ÉTUDIANTS"
echo "═══════════════════════════════════════════════════════════"
echo ""

# 1. Pull les modifications
echo "📥 Pull des modifications depuis GitHub..."
cd /var/www/labomaths/korrigo
git pull origin main

# 2. Créer les migrations
echo ""
echo "📊 Création des migrations de base de données..."
docker exec korrigo-backend-1 python manage.py makemigrations students

# 3. Appliquer les migrations
echo ""
echo "🗄️  Application des migrations..."
docker exec korrigo-backend-1 python manage.py migrate

# 4. Redémarrer le backend pour charger les nouvelles vues
echo ""
echo "🔄 Redémarrage du backend..."
docker compose -f docker-compose.labomaths.yml restart backend

# 5. Vérifier que tout fonctionne
echo ""
echo "✅ Vérification du système..."
docker compose -f docker-compose.labomaths.yml ps

echo ""
echo "═══════════════════════════════════════════════════════════"
echo "  ✅ DÉPLOIEMENT TERMINÉ"
echo "═══════════════════════════════════════════════════════════"
echo ""
echo "📝 PROCHAINES ÉTAPES :"
echo ""
echo "1. Importez votre fichier CSV des étudiants via l'interface admin"
echo "2. Le système générera automatiquement des mots de passe sécurisés"
echo "3. Les mots de passe seront affichés dans la réponse de l'import"
echo "4. IMPORTANT : Sauvegardez ces mots de passe et communiquez-les aux étudiants"
echo ""
echo "📧 Format de communication aux étudiants :"
echo "   - Email : [leur adresse email du CSV]"
echo "   - Mot de passe : [mot de passe généré automatiquement]"
echo "   - Les étudiants pourront changer leur mot de passe après première connexion"
echo ""
echo "🔗 Endpoints disponibles :"
echo "   - POST /api/students/login/ (email + password)"
echo "   - POST /api/students/change-password/ (current_password + new_password)"
echo ""
