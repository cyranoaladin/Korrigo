#!/bin/bash
set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${GREEN}Generating Strict Workflow Test Fixtures...${NC}"

# Removed hardcoded mkdir - django management command handles it.

CMD="python3 manage.py generate_test_copies --copies 3 --pages 4"

# Check if backend container is running
if docker compose ps | grep -q "backend"; then
    OUTPUT=$(docker compose exec -T backend $CMD)
else
    echo "Running locally..."
    OUTPUT=$($CMD)
fi

echo "$OUTPUT"

echo -e "${BLUE}---------------------------------------------------${NC}"
echo -e "${GREEN}Data Generation Complete.${NC}"
echo -e "${BLUE}Credentials:${NC}"
echo "  Teacher: teacher_test / password123"
echo "  Admin:   admin_test   / password123"
echo -e "${BLUE}Access UIs:${NC}"
echo "  Use the UUIDs printed above (READY / LOCKED / STAGING)."
echo "  Dashboard: http://localhost:5173/corrector-dashboard"
echo "  Example:   http://localhost:5173/corrector/desk/<UUID>"
echo -e "${BLUE}---------------------------------------------------${NC}"
