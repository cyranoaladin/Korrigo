#!/bin/bash
# =============================================================================
# Korrigo Backup -> Hetzner StorageBox
# Cron : */30 * * * *
# =============================================================================

set -euo pipefail

STORAGEBOX_USER="u554481"
STORAGEBOX_HOST="u554481.your-storagebox.de"
STORAGEBOX_PORT="23"
STORAGEBOX_DIR="backups/korrigo_backups"
STORAGEBOX_KEY="/root/.ssh/storagebox_ed25519"
RETENTION_HOURS=24
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOCAL_TMP="/tmp/korrigo_backup_${TIMESTAMP}"
LOG_FILE="/var/log/korrigo_backup.log"
MEDIA_VOLUME="/var/lib/docker/volumes/docker_media_volume/_data"
SYNC_OK=false

SSH_OPTS=(-p "${STORAGEBOX_PORT}" -i "${STORAGEBOX_KEY}" -o IdentitiesOnly=yes -o StrictHostKeyChecking=no -o ConnectTimeout=10)
RSYNC_RSH="ssh -p ${STORAGEBOX_PORT} -i ${STORAGEBOX_KEY} -o IdentitiesOnly=yes -o StrictHostKeyChecking=no"

redact_log_message() {
    sed -E 's/[[:alnum:]_.%+-]+@[[:alnum:].-]+\.[[:alpha:]]{2,}/<redacted-email>/g'
}

redact_log_stream() {
    redact_log_message
}

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | redact_log_message | tee -a "${LOG_FILE}"
}

cleanup_local() {
    rm -rf "${LOCAL_TMP}"
}
trap cleanup_local EXIT

encrypt_artifact_if_configured() {
    local input_file="$1"
    local output_file="$2"
    local label="$3"

    if [ -z "${BACKUP_GPG_PASSPHRASE:-}" ]; then
        if [ "${REQUIRE_BACKUP_GPG:-true}" = "true" ]; then
            log "  ERREUR: BACKUP_GPG_PASSPHRASE must be set when REQUIRE_BACKUP_GPG=true"
            exit 1
        fi
        return 0
    fi

    if gpg --batch --yes --pinentry-mode loopback --passphrase-fd 3 \
        --symmetric --cipher-algo AES256 \
        -o "${output_file}" \
        "${input_file}" 3<<<"${BACKUP_GPG_PASSPHRASE}" 2> >(redact_log_stream >>"${LOG_FILE}"); then
        rm -f "${input_file}"
        log "  OK: ${label} chiffre GPG (AES256)"
    else
        rm -f "${output_file}"
        log "  ERREUR: chiffrement GPG ${label} echoue"
        exit 1
    fi
}

encrypt_json_exports_if_configured() {
    shopt -s nullglob
    for json_file in "${LOCAL_TMP}"/*.json; do
        encrypt_artifact_if_configured \
            "${json_file}" \
            "${json_file}.gpg" \
            "export JSON $(basename "${json_file}")"
    done
    shopt -u nullglob
}

log "=== Backup ${TIMESTAMP} START ==="
mkdir -p "${LOCAL_TMP}"

if [ "${REQUIRE_BACKUP_GPG:-true}" = "true" ] && [ -z "${BACKUP_GPG_PASSPHRASE:-}" ]; then
    log "ERREUR: BACKUP_GPG_PASSPHRASE must be set when REQUIRE_BACKUP_GPG=true"
    exit 1
fi

log "1/6 PostgreSQL dump..."
if docker exec docker-db-1 pg_dump -U korrigo_user -Fc korrigo_db > "${LOCAL_TMP}/db_${TIMESTAMP}.dump" 2> >(redact_log_stream >>"${LOG_FILE}"); then
    log "  OK: $(du -sh "${LOCAL_TMP}/db_${TIMESTAMP}.dump" | cut -f1)"
    # Encrypt the dump if a GPG passphrase is configured.
    # Passphrase is passed via fd 3 to avoid exposure in process listings (ps aux).
    encrypt_artifact_if_configured \
        "${LOCAL_TMP}/db_${TIMESTAMP}.dump" \
        "${LOCAL_TMP}/db_${TIMESTAMP}.dump.gpg" \
        "dump DB"
else
    log "  ERREUR: dump DB echoue"
fi

log "2/6 Export JSON corrections..."
if docker exec -i docker-backend-1 sh -lc 'cat > /app/extract_correction_data.py' < /var/www/labomaths/korrigo/scripts/extract_correction_data.py 2> >(redact_log_stream >>"${LOG_FILE}") && \
   docker exec docker-backend-1 python manage.py shell -c 'exec(open("/app/extract_correction_data.py").read())' > >(redact_log_stream >>"${LOG_FILE}") 2> >(redact_log_stream >>"${LOG_FILE}"); then
    for f in copies_data.json pages_manifest.json exams_bareme.json summary.json; do
        docker exec docker-backend-1 sh -lc "cat /tmp/korrigo_extract/${f}" > "${LOCAL_TMP}/${f}" 2> >(redact_log_stream >>"${LOG_FILE}") || true
    done
    if [ -f "${LOCAL_TMP}/copies_data.json" ]; then
        log "  OK: $(du -sh "${LOCAL_TMP}/copies_data.json" | cut -f1)"
    else
        log "  WARNING: copies_data.json absent apres export"
    fi
    encrypt_json_exports_if_configured
else
    log "  ERREUR: export JSON echoue"
fi

log "3/6 Archive media..."
if [ -d "${MEDIA_VOLUME}" ]; then
    if tar -czf "${LOCAL_TMP}/media_${TIMESTAMP}.tar.gz" -C "${MEDIA_VOLUME}" --exclude="./tmp" --exclude="./.cache" . 2> >(redact_log_stream >>"${LOG_FILE}"); then
        log "  OK: $(du -sh "${LOCAL_TMP}/media_${TIMESTAMP}.tar.gz" | cut -f1)"
        encrypt_artifact_if_configured \
            "${LOCAL_TMP}/media_${TIMESTAMP}.tar.gz" \
            "${LOCAL_TMP}/media_${TIMESTAMP}.tar.gz.gpg" \
            "archive media"
    else
        log "  ERREUR: archive media echouee"
    fi
else
    log "  SKIP: ${MEDIA_VOLUME} introuvable"
fi

log "4/6 Envoi StorageBox..."
REMOTE_DIR="${STORAGEBOX_DIR}/${TIMESTAMP}"
if ssh "${SSH_OPTS[@]}" "${STORAGEBOX_USER}@${STORAGEBOX_HOST}" "mkdir -p '${REMOTE_DIR}'" 2> >(redact_log_stream >>"${LOG_FILE}") && \
   rsync -az --timeout=120 -e "${RSYNC_RSH}" "${LOCAL_TMP}/" "${STORAGEBOX_USER}@${STORAGEBOX_HOST}:${REMOTE_DIR}/" 2> >(redact_log_stream >>"${LOG_FILE}"); then
    log "  OK: envoye vers ${STORAGEBOX_HOST}:${REMOTE_DIR}"
    SYNC_OK=true
else
    log "  ERREUR: rsync echoue - backup conserve localement en fallback"
fi

log "5/6 Nettoyage local..."
if [ "${SYNC_OK}" = true ]; then
    rm -rf "${LOCAL_TMP}"
    log "  OK: backup local supprime"
else
    FALLBACK_DIR="/var/www/labomaths/korrigo/backups/fallback_${TIMESTAMP}"
    mv "${LOCAL_TMP}" "${FALLBACK_DIR}"
    log "  FALLBACK: backup conserve dans ${FALLBACK_DIR}"
    FALLBACK_COUNT=$(find /var/www/labomaths/korrigo/backups -maxdepth 1 -type d -name 'fallback_*' | wc -l)
    if [ "${FALLBACK_COUNT}" -gt 2 ]; then
        find /var/www/labomaths/korrigo/backups -maxdepth 1 -type d -name 'fallback_*' | sort | head -n -2 | xargs rm -rf
        log "  Anciens fallbacks purges"
    fi
fi

log "6/6 Purge StorageBox (> ${RETENTION_HOURS}h)..."
CUTOFF=$(date -d "-${RETENTION_HOURS} hours" +%Y%m%d_%H%M%S)
REMOTE_LIST=$(ssh "${SSH_OPTS[@]}" "${STORAGEBOX_USER}@${STORAGEBOX_HOST}" "ls '${STORAGEBOX_DIR}'" 2> >(redact_log_stream >>"${LOG_FILE}") || true)
while IFS= read -r dir; do
    [ -n "${dir}" ] || continue
    case "${dir}" in
        20*)
            if [ "${dir}" \< "${CUTOFF}" ]; then
                if ssh "${SSH_OPTS[@]}" "${STORAGEBOX_USER}@${STORAGEBOX_HOST}" "rm -r '${STORAGEBOX_DIR}/${dir}'" 2> >(redact_log_stream >>"${LOG_FILE}"); then
                    log "  Purged: ${dir}"
                else
                    log "  WARNING: purge impossible pour ${dir}"
                fi
            fi
            ;;
    esac
done <<< "${REMOTE_LIST}"
log "  OK: purge terminee"

log "=== Backup ${TIMESTAMP} DONE (sync=${SYNC_OK}) ==="
log ""
