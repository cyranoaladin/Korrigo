#!/bin/bash
set -e

# Configuration
BACKUP_DIR="./backups"
COMPOSE_FILE="infra/docker/docker-compose.prod.yml"

# Ensure backup directory exists
mkdir -p "$BACKUP_DIR"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
FILENAME="$BACKUP_DIR/media_backup_$TIMESTAMP.tar.gz"

echo "Starting Media Files Backup..."
echo "Target: $FILENAME"

if [ -f "$COMPOSE_FILE" ]; then
    CMD_PREFIX="docker compose -f $COMPOSE_FILE"
else
    CMD_PREFIX="docker compose"
fi

# Archive media directory from backend container
$CMD_PREFIX exec -T backend tar -czf - -C /app media > "$FILENAME"

echo "✅ Media backup completed successfully."
echo "Path: $FILENAME"
