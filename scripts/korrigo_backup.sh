#!/bin/bash
# =============================================================================
# Korrigo Automated Backup Script
# Runs every 30 minutes via cron
# 
# Backs up:
#   1. Full PostgreSQL dump
#   2. JSON export of all corrections data (scores, annotations, remarks, appreciations)
#   3. Media files (PDFs source, PDFs finaux, pages PNG)
#
# Retention: keeps last 48 backups (24 hours at 30min intervals)
# Location: /var/www/labomaths/korrigo/backups/automated/
# =============================================================================

set -euo pipefail

BACKUP_BASE="/var/www/labomaths/korrigo/backups/automated"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="${BACKUP_BASE}/${TIMESTAMP}"
RETENTION_COUNT=48
LOG_FILE="${BACKUP_BASE}/backup.log"

# Create directories
mkdir -p "${BACKUP_DIR}"
mkdir -p "${BACKUP_BASE}"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "${LOG_FILE}"
}

log "=== Starting backup ${TIMESTAMP} ==="

# -------------------------------------------------------
# 1. PostgreSQL full dump
# -------------------------------------------------------
log "Step 1: PostgreSQL dump..."
if docker exec docker-db-1 pg_dump -U korrigo_user -Fc korrigo_db > "${BACKUP_DIR}/db_${TIMESTAMP}.dump" 2>>"${LOG_FILE}"; then
    DB_SIZE=$(du -sh "${BACKUP_DIR}/db_${TIMESTAMP}.dump" | cut -f1)
    log "  -> DB dump OK: ${DB_SIZE}"
else
    log "  -> ERROR: DB dump failed!"
fi

# -------------------------------------------------------
# 2. JSON export of all correction data
# -------------------------------------------------------
log "Step 2: JSON data extraction..."
docker cp /var/www/labomaths/korrigo/scripts/extract_correction_data.py docker-backend-1:/app/extract_correction_data.py 2>>"${LOG_FILE}"

if docker exec docker-backend-1 python manage.py shell -c 'exec(open("/app/extract_correction_data.py").read())' >>"${LOG_FILE}" 2>&1; then
    # Copy JSON files from container
    docker cp docker-backend-1:/tmp/korrigo_extract/copies_data.json "${BACKUP_DIR}/copies_data.json" 2>>"${LOG_FILE}"
    docker cp docker-backend-1:/tmp/korrigo_extract/pages_manifest.json "${BACKUP_DIR}/pages_manifest.json" 2>>"${LOG_FILE}"
    docker cp docker-backend-1:/tmp/korrigo_extract/exams_bareme.json "${BACKUP_DIR}/exams_bareme.json" 2>>"${LOG_FILE}"
    docker cp docker-backend-1:/tmp/korrigo_extract/summary.json "${BACKUP_DIR}/summary.json" 2>>"${LOG_FILE}"
    
    JSON_SIZE=$(du -sh "${BACKUP_DIR}/copies_data.json" | cut -f1)
    log "  -> JSON export OK: copies_data=${JSON_SIZE}"
else
    log "  -> ERROR: JSON extraction failed!"
fi

# -------------------------------------------------------
# 3. Media backup (PDFs source, PDFs finaux, pages PNG)
# -------------------------------------------------------
log "Step 3: Media backup..."
MEDIA_VOLUME="/var/lib/docker/volumes/docker_media_volume/_data"
MEDIA_ARCHIVE="${BACKUP_DIR}/media_${TIMESTAMP}.tar.gz"

# Only back up the sub-directories that contain real data (skip uploads in progress)
if tar -czf "${MEDIA_ARCHIVE}" \
    -C "${MEDIA_VOLUME}" \
    --exclude="./tmp" \
    --exclude="./.cache" \
    . 2>>"${LOG_FILE}"; then
    MEDIA_SIZE=$(du -sh "${MEDIA_ARCHIVE}" | cut -f1)
    log "  -> Media backup OK: ${MEDIA_SIZE}"
else
    log "  -> WARNING: Media backup failed (non-fatal)"
fi

# -------------------------------------------------------
# 4. Cleanup old backups (keep last RETENTION_COUNT)
# -------------------------------------------------------
log "Step 4: Cleanup (keeping last ${RETENTION_COUNT} backups)..."
BACKUP_COUNT=$(ls -1d "${BACKUP_BASE}"/2* 2>/dev/null | wc -l)
if [ "${BACKUP_COUNT}" -gt "${RETENTION_COUNT}" ]; then
    REMOVE_COUNT=$((BACKUP_COUNT - RETENTION_COUNT))
    ls -1d "${BACKUP_BASE}"/2* | head -n "${REMOVE_COUNT}" | while read -r old_dir; do
        log "  Removing old backup: $(basename "${old_dir}")"
        rm -rf "${old_dir}"
    done
    log "  -> Removed ${REMOVE_COUNT} old backups"
else
    log "  -> No cleanup needed (${BACKUP_COUNT}/${RETENTION_COUNT})"
fi

# -------------------------------------------------------
# 5. Final summary
# -------------------------------------------------------
TOTAL_SIZE=$(du -sh "${BACKUP_DIR}" | cut -f1)
log "=== Backup ${TIMESTAMP} complete: ${TOTAL_SIZE} ==="
log ""
