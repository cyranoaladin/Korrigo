"""
Auto-Identification Service for CMEN v2 Headers.

This service integrates:
1. Grid-based OCR extraction (grid_ocr.py)
2. Closed-world CSV matching with strict thresholds
3. Automatic chunking based on header detection
4. Copy creation/fusion with anti-duplicate protection

Key invariants:
- Each student block must have pages as multiple of 4
- One Copy per student per exam (unique constraint)
- No silent false matches (AMBIGUOUS_OCR for uncertain cases)
- Transactional safety with select_for_update

PRD-19: Grid-Based OCR Implementation
"""
import logging
import os
import cv2
import numpy as np
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
from django.db import transaction
from django.conf import settings

from .grid_ocr import (
    GridOCRService,
    GridOCRResult,
    MatchResult,
    MatchCandidate,
    THRESHOLD_STRICT,
    MARGIN_STRICT,
)
from .vision import HeaderDetector

logger = logging.getLogger(__name__)


# =============================================================================
# CONSTANTS
# =============================================================================

class ChunkStatus(Enum):
    """Status of a page chunk."""
    VALID = "VALID"              # Valid chunk, auto-identified
    AMBIGUOUS_OCR = "AMBIGUOUS"  # OCR uncertain, needs manual review
    INVALID_BLOCK = "INVALID"    # Page count not multiple of 4
    OCR_FAIL = "OCR_FAIL"        # OCR completely failed
    NO_MATCH = "NO_MATCH"        # No matching student in CSV


@dataclass
class PageChunk:
    """A chunk of pages belonging to one student."""
    pages: List[str]  # List of page image paths
    header_image_path: Optional[str] = None
    ocr_result: Optional[GridOCRResult] = None
    match_result: Optional[MatchResult] = None
    status: ChunkStatus = ChunkStatus.VALID
    error_message: Optional[str] = None
    
    @property
    def page_count(self) -> int:
        return len(self.pages)
    
    @property
    def is_valid_block(self) -> bool:
        """Check if page count is multiple of 4."""
        return self.page_count > 0 and self.page_count % 4 == 0


@dataclass
class AutoIdentificationResult:
    """Result of auto-identification process."""
    exam_id: str
    total_pages: int
    total_chunks: int
    auto_identified: int
    ambiguous: int
    invalid_blocks: int
    ocr_failures: int
    no_matches: int
    chunks: List[PageChunk]
    copies_created: List[str] = field(default_factory=list)
    copies_updated: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)


# =============================================================================
# AUTO-IDENTIFICATION SERVICE
# =============================================================================

class AutoIdentificationService:
    """
    Service for automatic student identification from CMEN v2 headers.
    
    Workflow:
    1. Detect header pages (first page of each student block)
    2. Extract OCR data using grid-based approach
    3. Match against CSV whitelist with strict thresholds
    4. Create/update Copy objects with anti-duplicate protection
    
    Usage:
        service = AutoIdentificationService(csv_students)
        result = service.process_exam(exam, page_images)
    """
    
    def __init__(self, 
                 students: List[Dict[str, Any]],
                 threshold: float = THRESHOLD_STRICT,
                 margin: float = MARGIN_STRICT,
                 debug: bool = False):
        """
        Args:
            students: List of student records from CSV
            threshold: Minimum score for auto-match
            margin: Minimum margin between best and second-best
            debug: Enable debug logging
        """
        self.students = students
        self.threshold = threshold
        self.margin = margin
        self.debug = debug
        
        self.ocr_service = GridOCRService(debug=debug)
        self.header_detector = HeaderDetector()
    
    def process_exam(self, 
                     exam,
                     page_images: List[str],
                     dry_run: bool = False) -> AutoIdentificationResult:
        """
        Process all pages of an exam and create/update copies.
        
        Args:
            exam: Exam model instance
            page_images: List of page image paths (A4, in order)
            dry_run: If True, don't create/update database objects
            
        Returns:
            AutoIdentificationResult with statistics and created copies
        """
        logger.info(f"Starting auto-identification for exam {exam.id}")
        logger.info(f"Total pages: {len(page_images)}, Students in whitelist: {len(self.students)}")
        
        result = AutoIdentificationResult(
            exam_id=str(exam.id),
            total_pages=len(page_images),
            total_chunks=0,
            auto_identified=0,
            ambiguous=0,
            invalid_blocks=0,
            ocr_failures=0,
            no_matches=0,
            chunks=[]
        )
        
        # Step 1: Chunk pages by header detection
        chunks = self._chunk_pages_by_header(page_images)
        result.total_chunks = len(chunks)
        
        logger.info(f"Detected {len(chunks)} student chunks")
        
        # Step 2: Process each chunk (OCR + matching)
        for i, chunk in enumerate(chunks):
            logger.info(f"Processing chunk {i+1}/{len(chunks)}: {chunk.page_count} pages")
            
            # Validate page count invariant
            if not chunk.is_valid_block:
                chunk.status = ChunkStatus.INVALID_BLOCK
                chunk.error_message = f"Page count {chunk.page_count} is not multiple of 4"
                result.invalid_blocks += 1
                logger.warning(f"Chunk {i+1}: INVALID_BLOCK - {chunk.error_message}")
                result.chunks.append(chunk)
                continue
            
            # Extract header and run OCR
            if chunk.header_image_path:
                try:
                    ocr_result = self._extract_and_ocr_header(chunk.header_image_path)
                    chunk.ocr_result = ocr_result
                    
                    if ocr_result.status == "FAILED":
                        chunk.status = ChunkStatus.OCR_FAIL
                        chunk.error_message = "OCR extraction failed"
                        result.ocr_failures += 1
                        logger.warning(f"Chunk {i+1}: OCR_FAIL")
                    else:
                        # Match against CSV
                        match_result = self.ocr_service.match_student(
                            ocr_result, 
                            self.students,
                            threshold=self.threshold,
                            margin=self.margin
                        )
                        chunk.match_result = match_result
                        
                        if match_result.status == "AUTO_MATCH":
                            chunk.status = ChunkStatus.VALID
                            result.auto_identified += 1
                            logger.info(f"Chunk {i+1}: AUTO_MATCH - {match_result.best_match.last_name} {match_result.best_match.first_name}")
                        elif match_result.status == "AMBIGUOUS_OCR":
                            chunk.status = ChunkStatus.AMBIGUOUS_OCR
                            result.ambiguous += 1
                            logger.warning(f"Chunk {i+1}: AMBIGUOUS_OCR - margin={match_result.margin:.3f}")
                        elif match_result.status == "NO_MATCH":
                            chunk.status = ChunkStatus.NO_MATCH
                            result.no_matches += 1
                            logger.warning(f"Chunk {i+1}: NO_MATCH")
                        else:
                            chunk.status = ChunkStatus.OCR_FAIL
                            result.ocr_failures += 1
                            
                except Exception as e:
                    chunk.status = ChunkStatus.OCR_FAIL
                    chunk.error_message = str(e)
                    result.ocr_failures += 1
                    logger.error(f"Chunk {i+1}: OCR error - {e}")
            else:
                chunk.status = ChunkStatus.OCR_FAIL
                chunk.error_message = "No header image available"
                result.ocr_failures += 1
            
            result.chunks.append(chunk)
        
        # Step 3: Create/update copies in database
        if not dry_run:
            self._create_or_update_copies(exam, result)
        
        # Log summary
        logger.info(f"=== AUTO-IDENTIFICATION SUMMARY ===")
        logger.info(f"Total chunks: {result.total_chunks}")
        logger.info(f"Auto-identified: {result.auto_identified}")
        logger.info(f"Ambiguous (needs review): {result.ambiguous}")
        logger.info(f"Invalid blocks: {result.invalid_blocks}")
        logger.info(f"OCR failures: {result.ocr_failures}")
        logger.info(f"No matches: {result.no_matches}")
        logger.info(f"Copies created: {len(result.copies_created)}")
        logger.info(f"Copies updated: {len(result.copies_updated)}")
        
        return result
    
    def _chunk_pages_by_header(self, page_images: List[str]) -> List[PageChunk]:
        """
        Chunk pages into student blocks based on header detection.
        
        A new chunk starts when a header is detected on a page.
        """
        chunks = []
        current_chunk_pages = []
        current_header_path = None
        
        for i, page_path in enumerate(page_images):
            # Check if this page has a header
            has_header = self._detect_header(page_path)
            
            if has_header:
                # Save previous chunk if exists
                if current_chunk_pages:
                    chunks.append(PageChunk(
                        pages=current_chunk_pages.copy(),
                        header_image_path=current_header_path
                    ))
                
                # Start new chunk
                current_chunk_pages = [page_path]
                current_header_path = page_path
                
                if self.debug:
                    logger.debug(f"Page {i+1}: Header detected, starting new chunk")
            else:
                # Add to current chunk
                current_chunk_pages.append(page_path)
        
        # Don't forget the last chunk
        if current_chunk_pages:
            chunks.append(PageChunk(
                pages=current_chunk_pages.copy(),
                header_image_path=current_header_path
            ))
        
        return chunks
    
    def _detect_header(self, page_path: str) -> bool:
        """Detect if a page has a CMEN header."""
        try:
            return self.header_detector.detect_header(page_path)
        except Exception as e:
            logger.warning(f"Header detection failed for {page_path}: {e}")
            return False
    
    def _extract_and_ocr_header(self, page_path: str) -> GridOCRResult:
        """Extract header region and run grid-based OCR."""
        # Load image
        image = cv2.imread(page_path)
        if image is None:
            raise ValueError(f"Cannot read image: {page_path}")
        
        # Extract header region (top 25%)
        height = image.shape[0]
        header_height = int(height * 0.25)
        header_image = image[:header_height, :]
        
        # Run OCR
        return self.ocr_service.extract_header(header_image)
    
    @transaction.atomic
    def _create_or_update_copies(self, exam, result: AutoIdentificationResult):
        """
        Create or update Copy objects with anti-duplicate protection.
        
        Uses select_for_update to prevent race conditions.
        """
        from exams.models import Copy, Booklet
        from students.models import Student
        import uuid
        
        for chunk in result.chunks:
            try:
                # Determine student
                student = None
                if chunk.status == ChunkStatus.VALID and chunk.match_result:
                    student = self._get_or_create_student(chunk.match_result.best_match)
                
                # Check for existing copy (anti-duplicate)
                existing_copy = None
                if student:
                    # Lock the row to prevent concurrent creation
                    existing_copy = Copy.objects.select_for_update().filter(
                        exam=exam,
                        student=student
                    ).first()
                
                if existing_copy:
                    # Update existing copy (multi-sheet fusion)
                    self._append_pages_to_copy(existing_copy, chunk)
                    result.copies_updated.append(str(existing_copy.id))
                    logger.info(f"Updated existing copy {existing_copy.id} for student {student}")
                else:
                    # Create new copy
                    copy = self._create_new_copy(exam, chunk, student)
                    result.copies_created.append(str(copy.id))
                    logger.info(f"Created new copy {copy.id}")
                    
            except Exception as e:
                error_msg = f"Failed to create/update copy: {e}"
                result.errors.append(error_msg)
                logger.error(error_msg)
    
    def _get_or_create_student(self, match: MatchCandidate) -> Optional['Student']:
        """Get student from database or return None."""
        from students.models import Student
        
        # Try by ID first
        if match.student_id:
            student = Student.objects.filter(id=match.student_id).first()
            if student:
                return student
        
        # Try by email
        if match.email:
            student = Student.objects.filter(email__iexact=match.email).first()
            if student:
                return student
        
        # Try by name
        student = Student.objects.filter(
            last_name__iexact=match.last_name,
            first_name__iexact=match.first_name
        ).first()
        
        return student
    
    def _create_new_copy(self, exam, chunk: PageChunk, student: Optional['Student']) -> 'Copy':
        """Create a new Copy with Booklet."""
        from exams.models import Copy, Booklet
        from identification.models import OCRResult
        import uuid
        
        # Determine status
        if chunk.status == ChunkStatus.VALID:
            status = Copy.Status.READY
        else:
            status = Copy.Status.STAGING
        
        # Create booklet
        booklet = Booklet.objects.create(
            exam=exam,
            start_page=1,
            end_page=len(chunk.pages),
            pages_images=chunk.pages,
            student_name_guess=f"{student.last_name} {student.first_name}" if student else "Unknown"
        )
        
        # Create copy
        copy = Copy.objects.create(
            exam=exam,
            anonymous_id=str(uuid.uuid4())[:8].upper(),
            status=status,
            is_identified=student is not None,
            student=student
        )
        copy.booklets.add(booklet)
        
        # Create OCR result if available
        if chunk.ocr_result and chunk.match_result:
            top_candidates = []
            for c in chunk.match_result.all_candidates[:5]:
                top_candidates.append({
                    'student_id': c.student_id,
                    'last_name': c.last_name,
                    'first_name': c.first_name,
                    'date_of_birth': c.date_of_birth,
                    'score': round(c.total_score, 3),
                    'dob_score': round(c.dob_score, 3),
                    'name_score': round(c.name_score, 3),
                    'firstname_score': round(c.firstname_score, 3)
                })
            
            OCRResult.objects.create(
                copy=copy,
                detected_text=f"{chunk.ocr_result.last_name} {chunk.ocr_result.first_name} ({chunk.ocr_result.date_of_birth})",
                confidence=chunk.ocr_result.overall_confidence,
                top_candidates=top_candidates,
                ocr_mode='AUTO' if chunk.status == ChunkStatus.VALID else 'SEMI_AUTO',
                selected_candidate_rank=1 if chunk.status == ChunkStatus.VALID else None,
                manual_override=False
            )
        
        return copy
    
    def _append_pages_to_copy(self, copy: 'Copy', chunk: PageChunk):
        """Append pages to an existing copy (multi-sheet fusion)."""
        from exams.models import Booklet
        
        # Get existing booklet
        existing_booklet = copy.booklets.first()
        
        if existing_booklet:
            # Append pages to existing booklet
            current_pages = existing_booklet.pages_images or []
            current_pages.extend(chunk.pages)
            existing_booklet.pages_images = current_pages
            existing_booklet.end_page = len(current_pages)
            existing_booklet.save()
        else:
            # Create new booklet
            booklet = Booklet.objects.create(
                exam=copy.exam,
                start_page=1,
                end_page=len(chunk.pages),
                pages_images=chunk.pages
            )
            copy.booklets.add(booklet)


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def load_students_from_csv(csv_path: str) -> List[Dict[str, Any]]:
    """
    Load student records from CSV file.
    
    Expected columns: NOM, PRENOM, DATE_NAISSANCE, EMAIL, CLASSE
    """
    import csv
    
    students = []
    
    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        # Try to detect delimiter
        sample = f.read(1024)
        f.seek(0)
        
        if ';' in sample:
            delimiter = ';'
        else:
            delimiter = ','
        
        reader = csv.DictReader(f, delimiter=delimiter)
        
        for i, row in enumerate(reader):
            # Normalize column names
            normalized = {}
            for key, value in row.items():
                if key:
                    normalized[key.strip().upper()] = value.strip() if value else ''
            
            # Extract fields with multiple possible column names
            student = {
                'id': i + 1,
                'last_name': normalized.get('NOM') or normalized.get('LAST_NAME') or '',
                'first_name': normalized.get('PRENOM') or normalized.get('FIRST_NAME') or '',
                'date_of_birth': normalized.get('DATE_NAISSANCE') or normalized.get('DATE_OF_BIRTH') or normalized.get('NE(E) LE') or '',
                'email': normalized.get('EMAIL') or normalized.get('MAIL') or '',
                'class_name': normalized.get('CLASSE') or normalized.get('CLASS') or normalized.get('GROUPE_EDS') or ''
            }
            
            # Skip empty rows
            if student['last_name'] or student['first_name']:
                students.append(student)
    
    logger.info(f"Loaded {len(students)} students from {csv_path}")
    return students


def auto_identify_exam(exam, csv_path: str, page_images: List[str], dry_run: bool = False) -> AutoIdentificationResult:
    """
    Convenience function for auto-identification.
    
    Args:
        exam: Exam model instance
        csv_path: Path to student CSV file
        page_images: List of page image paths
        dry_run: If True, don't modify database
        
    Returns:
        AutoIdentificationResult
    """
    students = load_students_from_csv(csv_path)
    service = AutoIdentificationService(students)
    return service.process_exam(exam, page_images, dry_run=dry_run)
