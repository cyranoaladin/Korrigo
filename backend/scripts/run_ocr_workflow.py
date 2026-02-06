#!/usr/bin/env python
"""
PRD-19: Complete OCR Workflow Script

This script executes the full grid-based OCR workflow:
1. Load student CSV whitelist
2. Process PDF (detect A3, split to A4)
3. Extract headers and run grid-based OCR
4. Match against CSV with strict thresholds
5. Create/update copies in database
6. Generate detailed report

Usage:
    python scripts/run_ocr_workflow.py --pdf <path> --csv <path> [--dry-run]

Example:
    python scripts/run_ocr_workflow.py \
        --pdf /path/to/eval_loi_binom_log.pdf \
        --csv /path/to/G3_EDS_MATHS.csv
"""
import os
import sys
import argparse
import json
import logging
from pathlib import Path
from datetime import datetime

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
import django
django.setup()

from django.db import transaction
from processing.services.grid_ocr import GridOCRService, GridOCRResult
from processing.services.auto_identification import (
    AutoIdentificationService,
    load_students_from_csv,
    ChunkStatus,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def check_files(pdf_path: str, csv_path: str) -> bool:
    """Verify input files exist and are not empty."""
    errors = []
    
    if not os.path.exists(pdf_path):
        errors.append(f"PDF not found: {pdf_path}")
    elif os.path.getsize(pdf_path) == 0:
        errors.append(f"PDF is empty (0 bytes): {pdf_path}")
    
    if not os.path.exists(csv_path):
        errors.append(f"CSV not found: {csv_path}")
    elif os.path.getsize(csv_path) == 0:
        errors.append(f"CSV is empty (0 bytes): {csv_path}")
    
    if errors:
        for e in errors:
            logger.error(e)
        return False
    
    return True


def load_csv(csv_path: str) -> list:
    """Load and display CSV content."""
    logger.info(f"Loading CSV: {csv_path}")
    
    students = load_students_from_csv(csv_path)
    
    logger.info(f"Loaded {len(students)} students:")
    for i, s in enumerate(students[:10]):
        logger.info(f"  {i+1}. {s['last_name']} {s['first_name']} - {s['date_of_birth']}")
    
    if len(students) > 10:
        logger.info(f"  ... and {len(students) - 10} more")
    
    return students


def process_pdf(pdf_path: str, output_dir: str) -> list:
    """Process PDF and extract page images."""
    import fitz  # PyMuPDF
    import cv2
    import numpy as np
    
    logger.info(f"Processing PDF: {pdf_path}")
    
    doc = fitz.open(pdf_path)
    total_pages = doc.page_count
    logger.info(f"Total pages in PDF: {total_pages}")
    
    # Check if A3 format
    page = doc.load_page(0)
    width, height = page.rect.width, page.rect.height
    ratio = width / height if height > 0 else 0
    is_a3 = ratio > 1.2
    
    logger.info(f"Page dimensions: {width:.0f}x{height:.0f}, ratio={ratio:.2f}, A3={is_a3}")
    
    # Create output directory
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    page_images = []
    dpi = 200
    
    for page_idx in range(total_pages):
        page = doc.load_page(page_idx)
        mat = fitz.Matrix(dpi / 72, dpi / 72)
        pix = page.get_pixmap(matrix=mat)
        
        img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
        
        if pix.n == 3:
            img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
        elif pix.n == 4:
            img = cv2.cvtColor(img, cv2.COLOR_RGBA2BGR)
        
        if is_a3:
            # Split A3 into two A4 pages
            mid_x = img.shape[1] // 2
            left = img[:, :mid_x]
            right = img[:, mid_x:]
            
            # Save both halves
            left_path = os.path.join(output_dir, f"page_{page_idx*2+1:04d}.png")
            right_path = os.path.join(output_dir, f"page_{page_idx*2+2:04d}.png")
            
            cv2.imwrite(left_path, left)
            cv2.imwrite(right_path, right)
            
            page_images.extend([left_path, right_path])
            logger.info(f"  A3 page {page_idx+1} -> {left_path}, {right_path}")
        else:
            # Save A4 page directly
            page_path = os.path.join(output_dir, f"page_{page_idx+1:04d}.png")
            cv2.imwrite(page_path, img)
            page_images.append(page_path)
            logger.info(f"  A4 page {page_idx+1} -> {page_path}")
    
    doc.close()
    
    logger.info(f"Extracted {len(page_images)} A4 page images")
    return page_images


def run_ocr_workflow(pdf_path: str, csv_path: str, dry_run: bool = False) -> dict:
    """Execute the complete OCR workflow."""
    
    # Step 1: Check files
    logger.info("=" * 60)
    logger.info("STEP 1: Checking input files")
    logger.info("=" * 60)
    
    if not check_files(pdf_path, csv_path):
        return {"status": "ERROR", "message": "Input files validation failed"}
    
    # Step 2: Load CSV
    logger.info("=" * 60)
    logger.info("STEP 2: Loading student CSV")
    logger.info("=" * 60)
    
    students = load_csv(csv_path)
    if not students:
        return {"status": "ERROR", "message": "No students found in CSV"}
    
    # Step 3: Process PDF
    logger.info("=" * 60)
    logger.info("STEP 3: Processing PDF")
    logger.info("=" * 60)
    
    output_dir = f"/tmp/ocr_workflow_{datetime.now().strftime('%Y%m%d_%H%M%S')}"  # nosec B108 - temp dir for workflow processing
    page_images = process_pdf(pdf_path, output_dir)
    
    if not page_images:
        return {"status": "ERROR", "message": "No pages extracted from PDF"}
    
    # Step 4: Run auto-identification
    logger.info("=" * 60)
    logger.info("STEP 4: Running auto-identification")
    logger.info("=" * 60)
    
    # Create mock exam for dry run
    from exams.models import Exam
    
    if dry_run:
        class MockExam:
            id = "dry-run-exam"
        exam = MockExam()
    else:
        exam = Exam.objects.create(name=f"OCR Import {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        logger.info(f"Created exam: {exam.id}")
    
    service = AutoIdentificationService(students, debug=True)
    result = service.process_exam(exam, page_images, dry_run=dry_run)
    
    # Step 5: Generate report
    logger.info("=" * 60)
    logger.info("STEP 5: Generating report")
    logger.info("=" * 60)
    
    report = {
        "status": "SUCCESS",
        "timestamp": datetime.now().isoformat(),
        "dry_run": dry_run,
        "input": {
            "pdf_path": pdf_path,
            "csv_path": csv_path,
            "total_students_in_csv": len(students)
        },
        "processing": {
            "total_pages": result.total_pages,
            "total_chunks": result.total_chunks
        },
        "results": {
            "auto_identified": result.auto_identified,
            "ambiguous": result.ambiguous,
            "invalid_blocks": result.invalid_blocks,
            "ocr_failures": result.ocr_failures,
            "no_matches": result.no_matches
        },
        "copies": {
            "created": result.copies_created,
            "updated": result.copies_updated
        },
        "errors": result.errors,
        "chunks_detail": []
    }
    
    # Add chunk details
    for i, chunk in enumerate(result.chunks):
        chunk_info = {
            "chunk_id": i + 1,
            "page_count": chunk.page_count,
            "status": chunk.status.value,
            "is_valid_block": chunk.is_valid_block
        }
        
        if chunk.ocr_result:
            chunk_info["ocr"] = {
                "last_name": chunk.ocr_result.last_name,
                "first_name": chunk.ocr_result.first_name,
                "date_of_birth": chunk.ocr_result.date_of_birth,
                "confidence": round(chunk.ocr_result.overall_confidence, 3)
            }
        
        if chunk.match_result and chunk.match_result.best_match:
            chunk_info["match"] = {
                "student_id": chunk.match_result.best_match.student_id,
                "last_name": chunk.match_result.best_match.last_name,
                "first_name": chunk.match_result.best_match.first_name,
                "score": round(chunk.match_result.best_match.total_score, 3),
                "margin": round(chunk.match_result.margin, 3)
            }
        
        if chunk.error_message:
            chunk_info["error"] = chunk.error_message
        
        report["chunks_detail"].append(chunk_info)
    
    # Print summary
    logger.info("")
    logger.info("=" * 60)
    logger.info("WORKFLOW COMPLETE - SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Total pages processed: {result.total_pages}")
    logger.info(f"Total student chunks: {result.total_chunks}")
    logger.info(f"Auto-identified: {result.auto_identified}")
    logger.info(f"Ambiguous (needs review): {result.ambiguous}")
    logger.info(f"Invalid blocks: {result.invalid_blocks}")
    logger.info(f"OCR failures: {result.ocr_failures}")
    logger.info(f"No matches: {result.no_matches}")
    
    if not dry_run:
        logger.info(f"Copies created: {len(result.copies_created)}")
        logger.info(f"Copies updated: {len(result.copies_updated)}")
    
    # Save report to file
    report_path = os.path.join(output_dir, "ocr_workflow_report.json")
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    logger.info(f"Report saved to: {report_path}")
    
    return report


def main():
    parser = argparse.ArgumentParser(description="PRD-19 OCR Workflow")
    parser.add_argument("--pdf", required=True, help="Path to PDF file")
    parser.add_argument("--csv", required=True, help="Path to student CSV file")
    parser.add_argument("--dry-run", action="store_true", help="Don't create database objects")
    
    args = parser.parse_args()
    
    try:
        report = run_ocr_workflow(args.pdf, args.csv, dry_run=args.dry_run)
        
        if report["status"] == "SUCCESS":
            print("\n✅ Workflow completed successfully!")
            print(json.dumps(report, indent=2, ensure_ascii=False))
            sys.exit(0)
        else:
            print(f"\n❌ Workflow failed: {report.get('message', 'Unknown error')}")
            sys.exit(1)
            
    except Exception as e:
        logger.exception(f"Workflow failed with exception: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
