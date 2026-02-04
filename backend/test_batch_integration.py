#!/usr/bin/env python
"""
Test d'intégration batch A3 avec données réelles.
Teste la segmentation multi-feuilles par élève.
"""
import os
import sys
import django
import pytest

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from processing.services.batch_processor import BatchA3Processor
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


@pytest.mark.skip(reason="Legacy test - PDF files no longer available")
def test_batch_a3_real_data():
    """Test avec les données réelles : eval_loi_binom_log.pdf + G3_EDS_MATHS.csv"""

    # Chemins des fichiers
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)
    
    # Try current dir first (Docker /app) then project root (Local)
    pdf_path = os.path.join(current_dir, 'eval_loi_binom_log.pdf')
    if not os.path.exists(pdf_path):
        pdf_path = os.path.join(project_root, 'eval_loi_binom_log.pdf')

    csv_path = os.path.join(current_dir, 'G3_EDS_MATHS.csv')
    if not os.path.exists(csv_path):
        csv_path = os.path.join(project_root, 'G3_EDS_MATHS.csv')

    if not os.path.exists(pdf_path):
        pytest.skip(f"PDF not found: {pdf_path}. Skipping integration test.")

    if not os.path.exists(csv_path):
        pytest.skip(f"CSV not found: {csv_path}. Skipping integration test.")

    logger.info("=" * 80)
    logger.info("BATCH A3 INTEGRATION TEST - REAL DATA")
    logger.info("=" * 80)
    logger.info(f"PDF: {pdf_path}")
    logger.info(f"CSV: {csv_path}")
    logger.info("")

    # Créer le processeur
    processor = BatchA3Processor(dpi=200, csv_path=csv_path)

    logger.info(f"Loaded {len(processor.students_whitelist)} students from CSV")
    logger.info("")

    # Vérifier le format
    is_a3 = processor.is_a3_format(pdf_path)
    logger.info(f"Is A3 format: {is_a3}")

    if not is_a3:
        pytest.fail("PDF is not A3 format!")

    # Traiter le batch
    logger.info("")
    logger.info("Processing batch PDF...")
    logger.info("")

    try:
        student_copies = processor.process_batch_pdf(pdf_path, "test_batch_001")

        logger.info("")
        logger.info("=" * 80)
        logger.info("SEGMENTATION RESULTS")
        logger.info("=" * 80)
        logger.info(f"Total copies created: {len(student_copies)}")
        logger.info("")

        # Analyse détaillée
        total_pages = 0
        identified_count = 0
        needs_review_count = 0

        for idx, copy in enumerate(student_copies, 1):
            student_name = "UNKNOWN"
            if copy.student_match:
                student_name = f"{copy.student_match.last_name} {copy.student_match.first_name}"
                identified_count += 1

            sheets_count = len(copy.pages) // 4
            total_pages += len(copy.pages)

            if copy.needs_review:
                needs_review_count += 1

            logger.info(f"Copy #{idx}:")
            logger.info(f"  Student: {student_name}")
            logger.info(f"  Pages: {len(copy.pages)} ({sheets_count} sheets)")
            logger.info(f"  Identified: {copy.student_match is not None}")
            logger.info(f"  Needs review: {copy.needs_review}")
            if copy.needs_review:
                logger.info(f"  Review reason: {copy.review_reason}")
            if copy.student_match:
                logger.info(f"  Confidence: {copy.student_match.confidence:.2f}")
            logger.info(f"  Header crops: {len(copy.header_crops)}")
            logger.info("")

        # Stats globales
        logger.info("=" * 80)
        logger.info("GLOBAL STATISTICS")
        logger.info("=" * 80)
        logger.info(f"Total copies: {len(student_copies)}")
        logger.info(f"Identified: {identified_count}")
        logger.info(f"Needs review: {needs_review_count}")
        logger.info(f"Total pages A4: {total_pages}")
        if len(student_copies) > 0:
            logger.info(f"Average pages per copy: {total_pages / len(student_copies):.1f}")
        else:
            logger.info("Average pages per copy: N/A (no copies)")
        logger.info("")

        # Validation des invariants
        logger.info("=" * 80)
        logger.info("INVARIANT VALIDATION")
        logger.info("=" * 80)

        validation_ok = True

        # Vérifier que chaque copie a un nombre de pages multiple de 4
        for idx, copy in enumerate(student_copies, 1):
            if len(copy.pages) % 4 != 0:
                logger.error(f"❌ Copy #{idx}: {len(copy.pages)} pages (NOT multiple of 4)")
                validation_ok = False
            else:
                logger.info(f"✓ Copy #{idx}: {len(copy.pages)} pages (OK)")

        logger.info("")

        if validation_ok:
            logger.info("✓ All copies have page count as multiple of 4")
        else:
            logger.error("❌ Some copies have invalid page count")

        logger.info("")
        logger.info("=" * 80)

        assert validation_ok, "Validation failed: some copies have invalid page counts"

    except Exception as e:
        logger.error(f"Error processing batch: {e}")
        import traceback
        traceback.print_exc()
        pytest.fail(f"Batch processing failed: {e}")


if __name__ == '__main__':
    # Run test via pytest when executed directly
    import pytest
    sys.exit(pytest.main([__file__, '-v']))
