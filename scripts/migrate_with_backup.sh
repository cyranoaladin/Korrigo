#!/bin/bash
set -euo pipefail

echo "🔄 Safe Migration Script (with automatic backup)"
echo "================================================"
echo ""

# 1. Backup DB
echo "📦 Step 1/3: Creating backup before migration..."
./scripts/backup_db.sh
if [ $? -ne 0 ]; then
  echo "❌ Backup failed! Aborting migration."
  exit 1
fi
echo ""

# 2. Show pending migrations
echo "📋 Step 2/3: Checking pending migrations..."
docker compose -f infra/docker/docker-compose.prod.yml exec backend \
  python manage.py showmigrations --plan | grep '\[ \]' || echo "  (no pending migrations)"
echo ""

# 3. Apply migrations
echo "🚀 Step 3/3: Applying migrations..."
docker compose -f infra/docker/docker-compose.prod.yml exec backend \
  python manage.py migrate

if [ $? -eq 0 ]; then
  echo ""
  echo "✅ Migrations applied successfully"
  echo "📦 Backup available in: backups/ (latest: $(ls -t backups/db_backup_*.sql.gz | head -1))"
else
  echo ""
  echo "❌ Migration failed!"
  echo "💾 Database backup is available for rollback: backups/"
  echo "To rollback: gunzip -c backups/<backup_file>.sql.gz | docker compose exec -T db psql ..."
  exit 1
fi
