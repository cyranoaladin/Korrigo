#!/bin/bash
set -euo pipefail

BACKUP_DIR="backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/db_backup_$TIMESTAMP.sql"

mkdir -p $BACKUP_DIR

echo "📦 Creating database backup: $BACKUP_FILE"
docker compose -f infra/docker/docker-compose.prod.yml exec -T db \
  pg_dump -U ${POSTGRES_USER:-korrigo_user} ${POSTGRES_DB:-korrigo} \
  > $BACKUP_FILE

gzip $BACKUP_FILE
echo "✅ Backup created: ${BACKUP_FILE}.gz ($(du -h ${BACKUP_FILE}.gz | cut -f1))"

# Rétention : supprimer backups > 30 jours
DELETED=$(find $BACKUP_DIR -name "db_backup_*.sql.gz" -mtime +30 -delete -print | wc -l)
if [ $DELETED -gt 0 ]; then
  echo "🧹 Cleaned $DELETED old backups (>30 days)"
fi

echo "📋 Available backups:"
ls -lh $BACKUP_DIR/db_backup_*.sql.gz 2>/dev/null | tail -5 || echo "  (no previous backups)"
