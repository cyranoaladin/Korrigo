#!/bin/bash
# Script to run full test suite with clean state
# Ensures 100% green tests for CI validation

set -e
set -o pipefail

COMPOSE_FILE="infra/docker/docker-compose.local-prod.yml"

echo "=============================================="
echo "  Full Test Suite - Clean Run"
echo "=============================================="
echo ""

# Step 1: Clean up test databases
echo "🧹 Cleaning up test databases..."
docker compose -f "${COMPOSE_FILE}" exec -T db psql -U viatique_user -d postgres -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname LIKE 'test_%';" || true
docker compose -f "${COMPOSE_FILE}" exec -T db psql -U viatique_user -d postgres -c "DROP DATABASE IF EXISTS test_viatique_0;" || true
docker compose -f "${COMPOSE_FILE}" exec -T db psql -U viatique_user -d postgres -c "DROP DATABASE IF EXISTS test_viatique_1;" || true
echo "✓ Test databases cleaned"
echo ""

# Step 2: Rebuild backend image with latest code
echo "🔨 Rebuilding backend image with latest code..."
docker compose -f "${COMPOSE_FILE}" build --no-cache backend
echo "✓ Backend image rebuilt"
echo ""

# Step 3: Restart services
echo "🔄 Restarting services..."
docker compose -f "${COMPOSE_FILE}" down
docker compose -f "${COMPOSE_FILE}" up -d
echo "✓ Services restarted"
echo ""

# Step 4: Wait for backend to be healthy
echo "⏳ Waiting for backend to be healthy..."
for i in {1..60}; do
    if docker compose -f "${COMPOSE_FILE}" exec -T backend curl -f http://localhost:8000/api/health/live/ &>/dev/null; then
        echo "✓ Backend is healthy"
        break
    fi
    if [ $i -eq 60 ]; then
        echo "❌ Backend did not become healthy"
        exit 1
    fi
    sleep 1
done
echo ""

# Step 5: Run migrations
echo "🗃️  Running migrations..."
docker compose -f "${COMPOSE_FILE}" exec -T backend python manage.py migrate
echo "✓ Migrations complete"
echo ""

# Step 6: Run full test suite
echo "🧪 Running full test suite..."
echo ""
docker compose -f "${COMPOSE_FILE}" exec -T backend pytest -v --tb=short --maxfail=5

TEST_EXIT=$?

echo ""
echo "=============================================="
if [ $TEST_EXIT -eq 0 ]; then
    echo "  ✅ ALL TESTS PASSED - 100% GREEN!"
else
    echo "  ❌ Some tests failed (exit code: $TEST_EXIT)"
fi
echo "=============================================="

exit $TEST_EXIT
