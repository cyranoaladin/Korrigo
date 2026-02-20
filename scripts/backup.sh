#!/bin/bash
# =============================================================================
# Korrigo/Korrigo Backup Script
# Production backup for DB and media files
# =============================================================================

set -euo pipefail

# Configuration
BACKUP_DIR="${BACKUP_DIR:-/var/backups/korrigo}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
RETENTION_DAYS="${RETENTION_DAYS:-30}"

# Database configuration (from environment or defaults)
DB_NAME="${DB_NAME:-korrigo}"
DB_USER="${DB_USER:-korrigo_user}"
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"

# Media directory
MEDIA_DIR="${MEDIA_DIR:-/var/www/korrigo/media}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1" >&2
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1" >&2
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1" >&2
}

# Create backup directory if not exists
mkdir -p "${BACKUP_DIR}"

# =============================================================================
# Database Backup
# =============================================================================
backup_database() {
    log_info "Starting database backup..."
    
    DB_BACKUP_FILE="${BACKUP_DIR}/db_${DB_NAME}_${TIMESTAMP}.sql.gz"
    
    # Check if PostgreSQL is available
    if command -v pg_dump &> /dev/null; then
        log_info "Dumping PostgreSQL database: ${DB_NAME}"
        
        PGPASSWORD="${DB_PASSWORD:-}" pg_dump \
            -h "${DB_HOST}" \
            -p "${DB_PORT}" \
            -U "${DB_USER}" \
            -d "${DB_NAME}" \
            --no-owner \
            --no-acl \
            --clean \
            --if-exists \
            | gzip > "${DB_BACKUP_FILE}"
        
        log_info "Database backup created: ${DB_BACKUP_FILE}"
        log_info "Size: $(du -h "${DB_BACKUP_FILE}" | cut -f1)"
    else
        # Fallback to SQLite if pg_dump not available
        SQLITE_DB="${SQLITE_DB:-/var/www/korrigo/backend/db.sqlite3}"
        if [ -f "${SQLITE_DB}" ]; then
            log_info "Backing up SQLite database: ${SQLITE_DB}"
            DB_BACKUP_FILE="${BACKUP_DIR}/db_sqlite_${TIMESTAMP}.sql.gz"
            sqlite3 "${SQLITE_DB}" .dump | gzip > "${DB_BACKUP_FILE}"
            log_info "SQLite backup created: ${DB_BACKUP_FILE}"
        else
            log_error "No database found to backup"
            return 1
        fi
    fi
    
    echo "${DB_BACKUP_FILE}"
}

# =============================================================================
# Media Files Backup
# =============================================================================
backup_media() {
    log_info "Starting media backup..."
    
    if [ ! -d "${MEDIA_DIR}" ]; then
        log_warn "Media directory not found: ${MEDIA_DIR}"
        return 0
    fi
    
    MEDIA_BACKUP_FILE="${BACKUP_DIR}/media_${TIMESTAMP}.tar.gz"
    
    log_info "Archiving media files from: ${MEDIA_DIR}"
    
    tar -czf "${MEDIA_BACKUP_FILE}" \
        -C "$(dirname "${MEDIA_DIR}")" \
        "$(basename "${MEDIA_DIR}")" \
        2>/dev/null || true
    
    log_info "Media backup created: ${MEDIA_BACKUP_FILE}"
    log_info "Size: $(du -h "${MEDIA_BACKUP_FILE}" | cut -f1)"
    
    echo "${MEDIA_BACKUP_FILE}"
}

# =============================================================================
# Cleanup Old Backups
# =============================================================================
cleanup_old_backups() {
    log_info "Cleaning up backups older than ${RETENTION_DAYS} days..."
    
    find "${BACKUP_DIR}" -name "db_*.sql.gz" -mtime +${RETENTION_DAYS} -delete 2>/dev/null || true
    find "${BACKUP_DIR}" -name "media_*.tar.gz" -mtime +${RETENTION_DAYS} -delete 2>/dev/null || true
    
    log_info "Cleanup completed"
}

# =============================================================================
# Verify Backup
# =============================================================================
verify_backup() {
    local backup_file="$1"
    
    if [ ! -f "${backup_file}" ]; then
        log_error "Backup file not found: ${backup_file}"
        return 1
    fi
    
    # Check file is not empty
    if [ ! -s "${backup_file}" ]; then
        log_error "Backup file is empty: ${backup_file}"
        return 1
    fi
    
    # Verify gzip integrity
    if [[ "${backup_file}" == *.gz ]]; then
        if gzip -t "${backup_file}" 2>/dev/null; then
            log_info "Backup verified: ${backup_file}"
            return 0
        else
            log_error "Backup corrupted: ${backup_file}"
            return 1
        fi
    fi
    
    return 0
}

# =============================================================================
# Main
# =============================================================================
main() {
    log_info "=========================================="
    log_info "Korrigo Backup Started"
    log_info "=========================================="
    log_info "Backup directory: ${BACKUP_DIR}"
    log_info "Timestamp: ${TIMESTAMP}"
    
    # Backup database
    DB_FILE=$(backup_database)
    verify_backup "${DB_FILE}"
    
    # Backup media
    MEDIA_FILE=$(backup_media)
    if [ -n "${MEDIA_FILE}" ]; then
        verify_backup "${MEDIA_FILE}"
    fi
    
    # Cleanup old backups
    cleanup_old_backups
    
    log_info "=========================================="
    log_info "Backup Completed Successfully"
    log_info "=========================================="
    log_info "Database: ${DB_FILE}"
    log_info "Media: ${MEDIA_FILE:-N/A}"
    
    # Create manifest
    MANIFEST="${BACKUP_DIR}/manifest_${TIMESTAMP}.txt"
    cat > "${MANIFEST}" << EOF
Korrigo Backup Manifest
=======================
Timestamp: ${TIMESTAMP}
Date: $(date)
Host: $(hostname)

Files:
- Database: ${DB_FILE}
- Media: ${MEDIA_FILE:-N/A}

Sizes:
- Database: $(du -h "${DB_FILE}" | cut -f1)
- Media: $([ -f "${MEDIA_FILE}" ] && du -h "${MEDIA_FILE}" | cut -f1 || echo "N/A")

Checksums:
- Database: $(sha256sum "${DB_FILE}" | cut -d' ' -f1)
- Media: $([ -f "${MEDIA_FILE}" ] && sha256sum "${MEDIA_FILE}" | cut -d' ' -f1 || echo "N/A")
EOF
    
    log_info "Manifest: ${MANIFEST}"
}

# Run main function
main "$@"
