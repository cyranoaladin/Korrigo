#!/bin/bash
set -e

RESTORE_FILE=$1

if [ -z "$RESTORE_FILE" ]; then
    echo "Usage: $0 <path_to_media.tar.gz>"
    exit 1
fi

if [ ! -f "$RESTORE_FILE" ]; then
    echo "Error: File $RESTORE_FILE not found."
    exit 1
fi

# Configuration
COMPOSE_FILE="infra/docker/docker-compose.prod.yml"

echo "⚠️  WARNING: This will OVERWRITE files in the media volume."
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

echo "Restoring media from $RESTORE_FILE..."

# Extract directly into /app (archive contains 'media' folder)
cat "$RESTORE_FILE" | $CMD_PREFIX exec -T -i backend tar -xzf - -C /app

echo "✅ Media restore completed successfully."
