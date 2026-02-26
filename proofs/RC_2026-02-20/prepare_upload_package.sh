#!/bin/bash
# ============================================================
# Prépare le package de données à uploader sur le serveur
# Crée un répertoire structuré prêt à scp
# ============================================================
set -euo pipefail

PACKAGE_DIR="/home/alaeddine/viatique__PMF/proofs/RC_2026-02-20/server_package"
J1_SRC="/home/alaeddine/Téléchargements/scan_J1_BB_maths/copies_finales_J1_korrigo"
J2_SRC="/home/alaeddine/Bureau/scan_J2_BB_maths/Copies_completes"

echo "=== Préparation du package de déploiement ==="

# Clean and create
rm -rf "${PACKAGE_DIR}"
mkdir -p "${PACKAGE_DIR}"/{copies_J1,copies_J2,overlay,seed_data}

# 1. Reconstitution data + script
echo "1. Données de reconstitution..."
cp /home/alaeddine/viatique__PMF/proofs/RC_2026-02-20/reconstitution_data.json "${PACKAGE_DIR}/"
cp /home/alaeddine/viatique__PMF/proofs/RC_2026-02-20/reconstitute_db.py "${PACKAGE_DIR}/"
cp /home/alaeddine/viatique__PMF/proofs/RC_2026-02-20/deploy_server.sh "${PACKAGE_DIR}/"

# 2. CSV élèves
echo "2. CSV élèves..."
cp /home/alaeddine/viatique__PMF/eleves_maths_J1.csv "${PACKAGE_DIR}/"
cp /home/alaeddine/viatique__PMF/eleves_maths_J2.csv "${PACKAGE_DIR}/"

# 3. PDFs BB_J1 (source de vérité)
echo "3. PDFs BB_J1 (106 copies)..."
cp "${J1_SRC}"/*.pdf "${PACKAGE_DIR}/copies_J1/"
echo "   Copiés: $(ls "${PACKAGE_DIR}/copies_J1/" | wc -l) fichiers"

# 4. PDFs BB_J2 (source de vérité)
echo "4. PDFs BB_J2 (103 copies)..."
cp "${J2_SRC}"/*.pdf "${PACKAGE_DIR}/copies_J2/"
echo "   Copiés: $(ls "${PACKAGE_DIR}/copies_J2/" | wc -l) fichiers"

# 5. Overlay backend files
echo "5. Overlay backend..."
cd /home/alaeddine/viatique__PMF/backend
for f in \
    core/auth.py core/celery.py core/logging.py core/models.py core/prometheus.py \
    core/settings.py core/settings_prod.py core/settings_test.py core/urls.py \
    core/views.py core/views_dev.py core/views_health.py core/views_metrics.py core/views_prometheus.py \
    core/utils/audit.py core/utils/errors.py core/utils/ratelimit.py \
    core/management/commands/backup.py core/management/commands/backup_restore.py \
    core/management/commands/cleanup_orphaned_files.py core/management/commands/ensure_admin.py \
    core/management/commands/init_pmf.py core/management/commands/restore.py \
    exams/models.py exams/permissions.py exams/serializers.py exams/tasks.py \
    exams/urls.py exams/urls_copies.py exams/validators.py exams/validators_antivirus.py \
    exams/views.py exams/views_analytics.py exams/views_documents.py \
    exams/management/commands/export_pronote.py exams/management/commands/generate_test_copies.py \
    exams/management/commands/seed_initial_exams.py \
    exams/migrations/0021_copy_llm_summary.py \
    grading/models.py grading/permissions.py grading/serializers.py grading/services.py \
    grading/urls.py grading/views.py grading/views_annotation_bank.py grading/views_async.py \
    grading/views_draft.py grading/views_lock.py \
    grading/management/commands/recover_stuck_copies.py \
    identification/models.py identification/services.py identification/views.py \
    processing/services/llm_summary.py processing/services/pdf_flattener.py \
    students/models.py students/serializers.py students/urls.py students/views.py \
    students/management/commands/provision_student_users.py \
; do
    if [ -f "$f" ]; then
        mkdir -p "${PACKAGE_DIR}/overlay/$(dirname "$f")"
        cp "$f" "${PACKAGE_DIR}/overlay/$f"
    else
        echo "   WARN: $f not found"
    fi
done
echo "   Overlay: $(find "${PACKAGE_DIR}/overlay" -type f | wc -l) fichiers"

# 6. docker-compose.prod.yml
echo "6. Docker compose..."
cp /home/alaeddine/viatique__PMF/infra/docker/docker-compose.prod.yml "${PACKAGE_DIR}/"

# 7. Seed data (copies finales pour le réimport)
echo "7. Seed data..."
if [ -d /home/alaeddine/viatique__PMF/backend/seed_data/copies_finales_J1 ]; then
    cp -r /home/alaeddine/viatique__PMF/backend/seed_data/copies_finales_J1 "${PACKAGE_DIR}/seed_data/"
fi
if [ -d /home/alaeddine/viatique__PMF/backend/seed_data/copies_finales_J2 ]; then
    cp -r /home/alaeddine/viatique__PMF/backend/seed_data/copies_finales_J2 "${PACKAGE_DIR}/seed_data/"
fi

# Summary
echo ""
echo "=== PACKAGE PRÊT ==="
echo "Répertoire: ${PACKAGE_DIR}"
du -sh "${PACKAGE_DIR}"
echo ""
echo "Structure:"
find "${PACKAGE_DIR}" -maxdepth 2 -type d | sort
echo ""
echo "Fichiers principaux:"
ls -lh "${PACKAGE_DIR}"/*.{json,py,sh,csv,yml} 2>/dev/null
echo ""
echo "Pour uploader sur le serveur:"
echo "  scp -r ${PACKAGE_DIR}/ root@88.99.254.59:/var/www/labomaths/korrigo/reconstitution_data/"
echo "  ssh root@88.99.254.59 'bash /var/www/labomaths/korrigo/reconstitution_data/deploy_server.sh'"
