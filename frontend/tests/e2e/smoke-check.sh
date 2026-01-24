#!/bin/bash
# E2E Smoke Check - Vérifie les préconditions avant Playwright
# Échoue immédiatement si l'environnement est cassé (volume, nginx, seed)
#
# Usage: ./smoke-check.sh [BASE_URL] [COMPOSE_FILE]
# Default BASE_URL: http://localhost:8088
# Default COMPOSE_FILE: ../infra/docker/docker-compose.local-prod.yml

set -euo pipefail

BASE_URL="${1:-http://localhost:8088}"
ANON_ID="E2E-READY"

# Change to project root for docker compose
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
cd "$PROJECT_ROOT"

COMPOSE_BASE="infra/docker/docker-compose.local-prod.yml"
COMPOSE_E2E="infra/docker/docker-compose.e2e.yml"

echo "🔍 E2E Smoke Check - Base URL: $BASE_URL"
echo "================================================"

# 1. Media servi (image PNG E2E)
echo -n "1. Media served (e2e_page_1.png)... "
if curl -fsI "${BASE_URL}/media/e2e/pages/e2e_page_1.png" >/dev/null 2>&1; then
    echo "✅"
else
    echo "❌ FAILED"
    echo "   → Check: nginx volume mount, seed execution, file permissions"
    exit 1
fi

# 2. Database contains E2E-READY copy (direct check via backend)
echo -n "2. Database contains ${ANON_ID} copy... "
DB_CHECK=$(docker compose -f "$COMPOSE_BASE" -f "$COMPOSE_E2E" exec -T backend \
    python -c "
import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()
from exams.models import Copy
print(Copy.objects.filter(anonymous_id='${ANON_ID}').exists())
" 2>/dev/null || echo "False")

if [ "$DB_CHECK" = "True" ]; then
    echo "✅"
else
    echo "❌ FAILED"
    echo "   → Check: seed_e2e.py execution, database state"
    exit 1
fi

# 3. La copie E2E-READY a bien une page image
echo -n "3. ${ANON_ID} copy has booklet with pages_images... "
BOOKLET_CHECK=$(docker compose -f "$COMPOSE_BASE" -f "$COMPOSE_E2E" exec -T backend \
    python -c "
import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()
from exams.models import Copy
c = Copy.objects.filter(anonymous_id='${ANON_ID}').first()
if c and c.booklets.exists():
    b = c.booklets.first()
    print(bool(b.pages_images and len(b.pages_images) > 0))
else:
    print(False)
" 2>/dev/null || echo "False")

if [ "$BOOKLET_CHECK" = "True" ]; then
    echo "✅"
else
    echo "❌ FAILED"
    echo "   → Check: seed creates booklet with pages_images"
    exit 1
fi

echo "================================================"
echo "✅ All smoke checks passed - ready for Playwright"
