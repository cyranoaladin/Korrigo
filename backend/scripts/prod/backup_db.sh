#!/bin/bash
set -e

# Configuration
BACKUP_DIR="./backups"
COMPOSE_FILE="infra/docker/docker-compose.prod.yml"
DB_USER=${POSTGRES_USER:-viatique_user}
DB_NAME=${POSTGRES_DB:-viatique}

# Ensure backup directory exists
mkdir -p "$BACKUP_DIR"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
FILENAME="$BACKUP_DIR/db_backup_$TIMESTAMP.sql.gz"

echo "Starting Database Backup..."
echo "Target: $FILENAME"

# Execute Dump
if [ -f "$COMPOSE_FILE" ]; then
    CMD_PREFIX="docker compose -f $COMPOSE_FILE"
else
    # Fallback/Try to find compose
    CMD_PREFIX="docker compose"
    echo "Warning: $COMPOSE_FILE not found, trying default 'docker compose'"
fi

$CMD_PREFIX exec -T db pg_dump -U "$DB_USER" "$DB_NAME" | gzip > "$FILENAME"

echo "✅ Database backup completed successfully."
echo "Path: $FILENAME"
