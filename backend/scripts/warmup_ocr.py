#!/usr/bin/env python3
"""
PRD-19: OCR Warm-up Script
Preloads OCR models to avoid cold-start delays in production
"""
import os
import sys
import logging
from pathlib import Path

# Add parent directory to path for Django imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
import django
django.setup()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)


def warmup_ocr():
    """
    Initialize OCR engines and preload models.
    This should be run after container startup to cache models.
    """
    logger.info("=== OCR Warm-up Started ===")

    try:
        # Import OCR engine
        from processing.services.ocr_engine import MultiLayerOCR
        import numpy as np

        logger.info("Initializing Multi-layer OCR engine...")
        ocr_engine = MultiLayerOCR()

        # Create dummy image for model preloading
        dummy_image = np.ones((100, 100), dtype=np.uint8) * 255

        # Warm up Tesseract
        logger.info("Warming up Tesseract...")
        try:
            ocr_engine._ocr_tesseract(dummy_image)
            logger.info("✓ Tesseract ready")
        except Exception as e:
            logger.warning(f"Tesseract warm-up failed: {e}")

        # Warm up EasyOCR (downloads models on first use)
        logger.info("Warming up EasyOCR (may download models, ~100MB)...")
        try:
            import easyocr
            reader = easyocr.Reader(['fr', 'en'], gpu=False, verbose=False)
            # Run dummy OCR to trigger model loading
            reader.readtext(dummy_image)
            logger.info("✓ EasyOCR models downloaded and ready")
        except ImportError:
            logger.warning("EasyOCR not installed, skipping")
        except Exception as e:
            logger.warning(f"EasyOCR warm-up failed: {e}")

        # Warm up PaddleOCR (downloads models on first use)
        logger.info("Warming up PaddleOCR (may download models, ~50MB)...")
        try:
            from paddleocr import PaddleOCR
            # Suppress PaddleOCR verbose logging
            import paddle
            paddle.set_device('cpu')

            ocr_paddle = PaddleOCR(
                use_angle_cls=True,
                lang='fr',
                show_log=False,
                use_gpu=False
            )
            # Run dummy OCR to trigger model loading
            ocr_paddle.ocr(dummy_image, cls=True)
            logger.info("✓ PaddleOCR models downloaded and ready")
        except ImportError:
            logger.warning("PaddleOCR not installed, skipping")
        except Exception as e:
            logger.warning(f"PaddleOCR warm-up failed: {e}")

        logger.info("=== OCR Warm-up Completed Successfully ===")
        return True

    except Exception as e:
        logger.error(f"OCR warm-up failed: {e}", exc_info=True)
        return False


if __name__ == '__main__':
    success = warmup_ocr()
    sys.exit(0 if success else 1)
