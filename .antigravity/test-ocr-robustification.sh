#!/bin/bash
# Test script for OCR Robustification (PRD-19)

set -e

echo "=== OCR Robustification Test Suite ==="
echo ""

# Check if Docker is running
echo "1. Checking Docker containers..."
docker compose -f infra/docker/docker-compose.local-prod.yml ps

echo ""
echo "2. Running OCR Engine Unit Tests..."
docker compose -f infra/docker/docker-compose.local-prod.yml exec -T backend \
    pytest processing/tests/test_ocr_engine.py -v --tb=short

echo ""
echo "3. Running Batch Processor Tests..."
docker compose -f infra/docker/docker-compose.local-prod.yml exec -T backend \
    pytest processing/tests/test_batch_processor.py::TestMultiSheetFusion -v

echo ""
echo "4. Checking OCR libraries installation..."
docker compose -f infra/docker/docker-compose.local-prod.yml exec -T backend python << 'PYEOF'
print("Checking OCR library imports...")
try:
    import easyocr
    print("✓ EasyOCR imported successfully")
except ImportError as e:
    print(f"✗ EasyOCR import failed: {e}")

try:
    from paddleocr import PaddleOCR
    print("✓ PaddleOCR imported successfully")
except ImportError as e:
    print(f"✗ PaddleOCR import failed: {e}")

try:
    import pytesseract
    print("✓ Tesseract imported successfully")
except ImportError as e:
    print(f"✗ Tesseract import failed: {e}")

print("\nChecking multi-layer OCR engine...")
try:
    from processing.services.ocr_engine import MultiLayerOCR
    ocr = MultiLayerOCR()
    print("✓ Multi-layer OCR engine initialized")
except Exception as e:
    print(f"✗ Multi-layer OCR initialization failed: {e}")
PYEOF

echo ""
echo "5. Testing batch processor integration..."
docker compose -f infra/docker/docker-compose.local-prod.yml exec -T backend python << 'PYEOF'
from processing.services.batch_processor import BatchA3Processor
processor = BatchA3Processor()
print(f"✓ Batch processor initialized")
print(f"  - Multi-layer OCR available: {processor.ocr_engine is not None}")
PYEOF

echo ""
echo "=== Test Suite Complete ==="
