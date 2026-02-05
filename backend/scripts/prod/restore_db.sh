#!/bin/bash
set -e

RESTORE_FILE=$1

if [ -z "$RESTORE_FILE" ]; then
    echo "Usage: $0 <path_to_backup.sql.gz>"
    exit 1
fi

if [ ! -f "$RESTORE_FILE" ]; then
    echo "Error: File $RESTORE_FILE not found."
    exit 1
fi

# Configuration
COMPOSE_FILE="infra/docker/docker-compose.prod.yml"
DB_USER=${POSTGRES_USER:-viatique_user}
DB_NAME=${POSTGRES_DB:-viatique}

echo "⚠️  WARNING: This will OVERWRITE the database '$DB_NAME'."
read -p "Are you sure? (y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Aborted."
    exit 1
fi

if [ -f "$COMPOSE_FILE" ]; then
    CMD_PREFIX="docker compose -f $COMPOSE_FILE"
else
    CMD_PREFIX="docker compose"
fi

echo "Detailed Restore Process:"
echo "1. Stopping connection consumers (optional but recommended manually)"
echo "2. Dropping and Recreating Database..."

# Drop and Recreate to ensure clean state
$CMD_PREFIX exec -T db psql -U "$DB_USER" -d postgres -c "DROP DATABASE IF EXISTS $DB_NAME;"
$CMD_PREFIX exec -T db psql -U "$DB_USER" -d postgres -c "CREATE DATABASE $DB_NAME;"

echo "3. Restoring data from $RESTORE_FILE..."
zcat "$RESTORE_FILE" | $CMD_PREFIX exec -T db psql -U "$DB_USER" -d "$DB_NAME"

echo "✅ Database restore completed successfully."
