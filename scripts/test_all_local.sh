#!/bin/bash
set -euo pipefail

# Script pour tester localement en conditions de production
# Usage: ./scripts/test_all_local.sh

COMPOSE_FILE="infra/docker/docker-compose.local-prod.yml"
BACKEND_SVC="backend"

echo "==========================================="
echo "Test complet en environnement local-prod"
echo "==========================================="

# 1. Démarrer les services
echo "1. Démarrage des services..."
docker compose -f "$COMPOSE_FILE" up -d

# 2. Attendre que les services soient prêts
echo "2. Attente des services..."
sleep 30

# Vérifier que backend répond
for i in {1..30}; do
  if curl -f http://localhost:8088/api/health/live/ > /dev/null 2>&1; then
    echo "✅ Backend est prêt!"
    break
  fi
  echo "Attente du backend... ($i/30)"
  sleep 2
done

# 3. Migrations
echo "3. Exécution des migrations..."
docker compose -f "$COMPOSE_FILE" exec -T "$BACKEND_SVC" python manage.py migrate --noinput

# 4. Seed data
echo "4. Initialisation des données..."
docker compose -f "$COMPOSE_FILE" exec -T "$BACKEND_SVC" python seed_prod.py

# 5. Tests unitaires + intégration
echo "5. Exécution des tests pytest..."
docker compose -f "$COMPOSE_FILE" exec -T "$BACKEND_SVC" pytest -v --tb=short --maxfail=5

TEST_EXIT_CODE=$?

# 6. Résumé
echo ""
echo "==========================================="
echo "RÉSUMÉ DES TESTS"
echo "==========================================="

if [ $TEST_EXIT_CODE -eq 0 ]; then
  echo "✅ TOUS LES TESTS SONT PASSÉS!"
else
  echo "❌ CERTAINS TESTS ONT ÉCHOUÉ (exit code: $TEST_EXIT_CODE)"
fi

echo ""
echo "Pour voir les logs:"
echo "  docker compose -f $COMPOSE_FILE logs backend"
echo ""
echo "Pour arrêter les services:"
echo "  docker compose -f $COMPOSE_FILE down"
echo ""

exit $TEST_EXIT_CODE
