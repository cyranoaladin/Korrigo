#!/bin/bash
# =============================================================================
# Korrigo/Korrigo Restore Script
# Production restore for DB and media files
# =============================================================================

set -euo pipefail

# Configuration
BACKUP_DIR="${BACKUP_DIR:-/var/backups/korrigo}"

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
    echo -e "${GREEN}[INFO]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

# =============================================================================
# Safety Confirmation
# =============================================================================
confirm_restore() {
    echo ""
    echo -e "${RED}╔════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${RED}║                    ⚠️  WARNING ⚠️                               ║${NC}"
    echo -e "${RED}║  This will OVERWRITE the current database and media files!    ║${NC}"
    echo -e "${RED}║  All existing data will be PERMANENTLY LOST!                  ║${NC}"
    echo -e "${RED}╚════════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    
    read -p "Type 'RESTORE' to confirm: " confirmation
    
    if [ "${confirmation}" != "RESTORE" ]; then
        log_error "Restore cancelled by user"
        exit 1
    fi
    
    log_info "Restore confirmed by user"
}

# =============================================================================
# List Available Backups
# =============================================================================
list_backups() {
    log_info "Available backups in ${BACKUP_DIR}:"
    echo ""
    
    echo "Database backups:"
    ls -lh "${BACKUP_DIR}"/db_*.sql.gz 2>/dev/null || echo "  No database backups found"
    echo ""
    
    echo "Media backups:"
    ls -lh "${BACKUP_DIR}"/media_*.tar.gz 2>/dev/null || echo "  No media backups found"
    echo ""
    
    echo "Manifests:"
    ls -lh "${BACKUP_DIR}"/manifest_*.txt 2>/dev/null || echo "  No manifests found"
}

# =============================================================================
# Restore Database
# =============================================================================
restore_database() {
    local backup_file="$1"
    
    if [ ! -f "${backup_file}" ]; then
        log_error "Database backup file not found: ${backup_file}"
        return 1
    fi
    
    log_info "Restoring database from: ${backup_file}"
    
    # Verify backup integrity
    if ! gzip -t "${backup_file}" 2>/dev/null; then
        log_error "Backup file is corrupted: ${backup_file}"
        return 1
    fi
    
    # Check if PostgreSQL
    if command -v psql &> /dev/null && [[ "${backup_file}" != *"sqlite"* ]]; then
        log_info "Restoring PostgreSQL database: ${DB_NAME}"
        
        # Drop and recreate database
        log_warn "Dropping existing database..."
        PGPASSWORD="${DB_PASSWORD:-}" psql \
            -h "${DB_HOST}" \
            -p "${DB_PORT}" \
            -U "${DB_USER}" \
            -d postgres \
            -c "DROP DATABASE IF EXISTS ${DB_NAME};" 2>/dev/null || true
        
        PGPASSWORD="${DB_PASSWORD:-}" psql \
            -h "${DB_HOST}" \
            -p "${DB_PORT}" \
            -U "${DB_USER}" \
            -d postgres \
            -c "CREATE DATABASE ${DB_NAME};"
        
        # Restore
        log_info "Restoring data..."
        gunzip -c "${backup_file}" | PGPASSWORD="${DB_PASSWORD:-}" psql \
            -h "${DB_HOST}" \
            -p "${DB_PORT}" \
            -U "${DB_USER}" \
            -d "${DB_NAME}" \
            --quiet
        
        log_info "PostgreSQL database restored successfully"
    else
        # SQLite restore
        SQLITE_DB="${SQLITE_DB:-/var/www/korrigo/backend/db.sqlite3}"
        log_info "Restoring SQLite database: ${SQLITE_DB}"
        
        # Backup current DB
        if [ -f "${SQLITE_DB}" ]; then
            mv "${SQLITE_DB}" "${SQLITE_DB}.pre-restore.$(date +%s)"
        fi
        
        # Restore
        gunzip -c "${backup_file}" | sqlite3 "${SQLITE_DB}"
        
        log_info "SQLite database restored successfully"
    fi
}

# =============================================================================
# Restore Media Files
# =============================================================================
restore_media() {
    local backup_file="$1"
    
    if [ ! -f "${backup_file}" ]; then
        log_error "Media backup file not found: ${backup_file}"
        return 1
    fi
    
    log_info "Restoring media from: ${backup_file}"
    
    # Verify backup integrity
    if ! gzip -t "${backup_file}" 2>/dev/null; then
        log_error "Backup file is corrupted: ${backup_file}"
        return 1
    fi
    
    # Backup current media
    if [ -d "${MEDIA_DIR}" ]; then
        MEDIA_BACKUP="${MEDIA_DIR}.pre-restore.$(date +%s)"
        log_warn "Moving current media to: ${MEDIA_BACKUP}"
        mv "${MEDIA_DIR}" "${MEDIA_BACKUP}"
    fi
    
    # Create media directory
    mkdir -p "$(dirname "${MEDIA_DIR}")"
    
    # Restore
    log_info "Extracting media files..."
    tar -xzf "${backup_file}" -C "$(dirname "${MEDIA_DIR}")"
    
    # Fix permissions
    chown -R www-data:www-data "${MEDIA_DIR}" 2>/dev/null || true
    chmod -R 755 "${MEDIA_DIR}" 2>/dev/null || true
    
    log_info "Media files restored successfully"
}

# =============================================================================
# Usage
# =============================================================================
usage() {
    echo "Usage: $0 [command] [options]"
    echo ""
    echo "Commands:"
    echo "  list                    List available backups"
    echo "  db <backup_file>        Restore database from backup"
    echo "  media <backup_file>     Restore media from backup"
    echo "  full <timestamp>        Restore both DB and media from timestamp"
    echo ""
    echo "Examples:"
    echo "  $0 list"
    echo "  $0 db /var/backups/korrigo/db_korrigo_20260131_120000.sql.gz"
    echo "  $0 media /var/backups/korrigo/media_20260131_120000.tar.gz"
    echo "  $0 full 20260131_120000"
    echo ""
    echo "Environment variables:"
    echo "  BACKUP_DIR    Backup directory (default: /var/backups/korrigo)"
    echo "  DB_NAME       Database name (default: korrigo)"
    echo "  DB_USER       Database user (default: korrigo_user)"
    echo "  DB_HOST       Database host (default: localhost)"
    echo "  DB_PORT       Database port (default: 5432)"
    echo "  DB_PASSWORD   Database password"
    echo "  MEDIA_DIR     Media directory (default: /var/www/korrigo/media)"
}

# =============================================================================
# Main
# =============================================================================
main() {
    if [ $# -lt 1 ]; then
        usage
        exit 1
    fi
    
    local command="$1"
    shift
    
    case "${command}" in
        list)
            list_backups
            ;;
        db)
            if [ $# -lt 1 ]; then
                log_error "Database backup file required"
                usage
                exit 1
            fi
            confirm_restore
            restore_database "$1"
            ;;
        media)
            if [ $# -lt 1 ]; then
                log_error "Media backup file required"
                usage
                exit 1
            fi
            confirm_restore
            restore_media "$1"
            ;;
        full)
            if [ $# -lt 1 ]; then
                log_error "Timestamp required"
                usage
                exit 1
            fi
            local timestamp="$1"
            local db_file="${BACKUP_DIR}/db_${DB_NAME}_${timestamp}.sql.gz"
            local media_file="${BACKUP_DIR}/media_${timestamp}.tar.gz"
            
            if [ ! -f "${db_file}" ]; then
                log_error "Database backup not found: ${db_file}"
                exit 1
            fi
            
            confirm_restore
            
            log_info "=========================================="
            log_info "Full Restore Started"
            log_info "=========================================="
            
            restore_database "${db_file}"
            
            if [ -f "${media_file}" ]; then
                restore_media "${media_file}"
            else
                log_warn "Media backup not found, skipping: ${media_file}"
            fi
            
            log_info "=========================================="
            log_info "Full Restore Completed"
            log_info "=========================================="
            ;;
        *)
            log_error "Unknown command: ${command}"
            usage
            exit 1
            ;;
    esac
}

# Run main function
main "$@"
