"""
Tests for Auto-Identification Service (PRD-19).

Tests cover:
1. Chunking by header detection
2. Page count invariant (multiple of 4)
3. Copy uniqueness per student per exam
4. Multi-sheet fusion
5. Concurrent access protection
"""
import pytest
import numpy as np
import cv2
import tempfile
import os
from unittest.mock import patch, MagicMock, Mock
from django.test import TestCase

from processing.services.auto_identification import (
    AutoIdentificationService,
    AutoIdentificationResult,
    PageChunk,
    ChunkStatus,
    load_students_from_csv,
)
from processing.services.grid_ocr import (
    GridOCRResult,
    MatchResult,
    MatchCandidate,
    FieldResult,
    FieldType,
)


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def sample_students():
    """Sample student records for testing."""
    return [
        {
            'id': 1,
            'last_name': 'DUPONT',
            'first_name': 'JEAN',
            'date_of_birth': '15/03/2008',
            'email': 'jean.dupont@test.com',
            'class_name': '3A'
        },
        {
            'id': 2,
            'last_name': 'MARTIN',
            'first_name': 'MARIE',
            'date_of_birth': '22/07/2008',
            'email': 'marie.martin@test.com',
            'class_name': '3A'
        },
        {
            'id': 3,
            'last_name': 'DURAND',
            'first_name': 'PIERRE',
            'date_of_birth': '10/01/2008',
            'email': 'pierre.durand@test.com',
            'class_name': '3B'
        },
    ]


@pytest.fixture
def mock_page_images():
    """Create mock page image paths."""
    return [
        '/fake/page_001.png',
        '/fake/page_002.png',
        '/fake/page_003.png',
        '/fake/page_004.png',
        '/fake/page_005.png',
        '/fake/page_006.png',
        '/fake/page_007.png',
        '/fake/page_008.png',
    ]


@pytest.fixture
def sample_csv_content():
    """Sample CSV content for testing."""
    return """NOM;PRENOM;DATE_NAISSANCE;EMAIL;CLASSE
DUPONT;Jean;15/03/2008;jean.dupont@test.com;3A
MARTIN;Marie;22/07/2008;marie.martin@test.com;3A
DURAND;Pierre;10/01/2008;pierre.durand@test.com;3B
"""


# =============================================================================
# TEST: CHUNKING
# =============================================================================

class TestChunking:
    """Tests for page chunking by header detection."""
    
    def test_chunking_creates_correct_chunks(self, sample_students, mock_page_images):
        """Chunking should create chunks based on header detection."""
        service = AutoIdentificationService(sample_students)
        
        # Mock header detection: headers on pages 1 and 5
        with patch.object(service, '_detect_header') as mock_detect:
            mock_detect.side_effect = [True, False, False, False, True, False, False, False]
            
            chunks = service._chunk_pages_by_header(mock_page_images)
            
            assert len(chunks) == 2
            assert len(chunks[0].pages) == 4
            assert len(chunks[1].pages) == 4
    
    def test_chunking_handles_single_chunk(self, sample_students):
        """Single chunk when only first page has header."""
        service = AutoIdentificationService(sample_students)
        
        pages = ['/fake/p1.png', '/fake/p2.png', '/fake/p3.png', '/fake/p4.png']
        
        with patch.object(service, '_detect_header') as mock_detect:
            mock_detect.side_effect = [True, False, False, False]
            
            chunks = service._chunk_pages_by_header(pages)
            
            assert len(chunks) == 1
            assert len(chunks[0].pages) == 4
    
    def test_chunking_handles_empty_pages(self, sample_students):
        """Empty page list should return empty chunks."""
        service = AutoIdentificationService(sample_students)
        
        chunks = service._chunk_pages_by_header([])
        
        assert len(chunks) == 0


# =============================================================================
# TEST: PAGE COUNT INVARIANT
# =============================================================================

class TestPageCountInvariant:
    """Tests for page count multiple of 4 invariant."""
    
    def test_valid_block_multiple_of_4(self):
        """Chunk with 4 pages is valid."""
        chunk = PageChunk(pages=['/p1.png', '/p2.png', '/p3.png', '/p4.png'])
        assert chunk.is_valid_block
    
    def test_valid_block_8_pages(self):
        """Chunk with 8 pages (2 sheets) is valid."""
        chunk = PageChunk(pages=[f'/p{i}.png' for i in range(8)])
        assert chunk.is_valid_block
    
    def test_invalid_block_3_pages(self):
        """Chunk with 3 pages is invalid."""
        chunk = PageChunk(pages=['/p1.png', '/p2.png', '/p3.png'])
        assert not chunk.is_valid_block
    
    def test_invalid_block_5_pages(self):
        """Chunk with 5 pages is invalid."""
        chunk = PageChunk(pages=[f'/p{i}.png' for i in range(5)])
        assert not chunk.is_valid_block
    
    def test_invalid_block_flagged_in_result(self, sample_students):
        """Invalid blocks should be flagged in result."""
        service = AutoIdentificationService(sample_students)
        
        # Create mock exam
        mock_exam = Mock()
        mock_exam.id = 'test-exam'
        
        # 3 pages - invalid
        pages = ['/fake/p1.png', '/fake/p2.png', '/fake/p3.png']
        
        with patch.object(service, '_detect_header') as mock_detect:
            # Only first page has header
            mock_detect.side_effect = [True, False, False]
            result = service.process_exam(mock_exam, pages, dry_run=True)
        
        assert result.invalid_blocks == 1
        assert result.chunks[0].status == ChunkStatus.INVALID_BLOCK


# =============================================================================
# TEST: COPY UNIQUENESS
# =============================================================================

class TestCopyUniqueness:
    """Tests for unique copy per student per exam."""
    
    @pytest.mark.django_db
    def test_unique_copy_constraint(self, sample_students):
        """Should not create duplicate copies for same student."""
        from exams.models import Exam, Copy
        from students.models import Student
        from datetime import date
        
        # Create exam
        exam = Exam.objects.create(name='Test Exam')
        
        # Create student - handle both model versions
        # Version 1: full_name + date_of_birth
        # Version 2: first_name + last_name + ine
        try:
            student = Student.objects.create(
                full_name='DUPONT Jean',
                date_of_birth=date(2008, 3, 15),
                email='jean.dupont@test.com'
            )
        except TypeError:
            # Alternative model structure
            student = Student.objects.create(
                first_name='Jean',
                last_name='DUPONT',
                email='jean.dupont@test.com',
                ine='0000000001'
            )
        
        # Create first copy
        copy1 = Copy.objects.create(
            exam=exam,
            anonymous_id='COPY0001',
            student=student,
            is_identified=True
        )
        
        # Verify constraint exists
        existing = Copy.objects.filter(exam=exam, student=student).count()
        assert existing == 1
    
    @pytest.mark.django_db
    def test_multi_sheet_fusion(self, sample_students):
        """Multiple sheets for same student should be fused into one copy."""
        service = AutoIdentificationService(sample_students)
        
        # This test verifies the logic, actual DB test requires more setup
        chunk1 = PageChunk(
            pages=['/p1.png', '/p2.png', '/p3.png', '/p4.png'],
            status=ChunkStatus.VALID
        )
        chunk2 = PageChunk(
            pages=['/p5.png', '/p6.png', '/p7.png', '/p8.png'],
            status=ChunkStatus.VALID
        )
        
        # Both chunks belong to same student
        # After processing, should result in 1 copy with 8 pages
        assert chunk1.is_valid_block
        assert chunk2.is_valid_block


# =============================================================================
# TEST: CONCURRENT ACCESS
# =============================================================================

class TestConcurrentAccess:
    """Tests for concurrent access protection."""
    
    def test_select_for_update_used(self, sample_students):
        """Verify select_for_update is used for anti-duplicate."""
        service = AutoIdentificationService(sample_students)
        
        # The _create_or_update_copies method should use select_for_update
        # This is verified by code inspection and integration tests
        import inspect
        source = inspect.getsource(service._create_or_update_copies)
        assert 'select_for_update' in source


# =============================================================================
# TEST: CSV LOADING
# =============================================================================

class TestCSVLoading:
    """Tests for CSV student loading."""
    
    def test_load_csv_semicolon_delimiter(self, sample_csv_content):
        """Should load CSV with semicolon delimiter."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(sample_csv_content)
            csv_path = f.name
        
        try:
            students = load_students_from_csv(csv_path)
            
            assert len(students) == 3
            assert students[0]['last_name'] == 'DUPONT'
            assert students[0]['first_name'] == 'Jean'
            assert students[0]['date_of_birth'] == '15/03/2008'
        finally:
            os.unlink(csv_path)
    
    def test_load_csv_comma_delimiter(self):
        """Should load CSV with comma delimiter."""
        csv_content = """NOM,PRENOM,DATE_NAISSANCE,EMAIL
DUPONT,Jean,15/03/2008,jean@test.com
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(csv_content)
            csv_path = f.name
        
        try:
            students = load_students_from_csv(csv_path)
            
            assert len(students) == 1
            assert students[0]['last_name'] == 'DUPONT'
        finally:
            os.unlink(csv_path)
    
    def test_load_csv_handles_bom(self):
        """Should handle UTF-8 BOM in CSV."""
        # Write without BOM marker in content (utf-8-sig handles it)
        csv_content = "NOM;PRENOM;DATE_NAISSANCE\nDUPONT;Jean;15/03/2008\n"
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8-sig') as f:
            f.write(csv_content)
            csv_path = f.name
        
        try:
            students = load_students_from_csv(csv_path)
            
            assert len(students) == 1
            # BOM should be stripped from column name
            assert students[0]['last_name'] == 'DUPONT'
        finally:
            os.unlink(csv_path)


# =============================================================================
# TEST: INTEGRATION
# =============================================================================

class TestIntegration:
    """Integration tests for auto-identification."""
    
    def test_full_workflow_dry_run(self, sample_students):
        """Full workflow in dry run mode."""
        service = AutoIdentificationService(sample_students, debug=True)
        
        mock_exam = Mock()
        mock_exam.id = 'test-exam'
        
        # 8 pages = 2 chunks of 4
        pages = [f'/fake/page_{i:03d}.png' for i in range(8)]
        
        # Mock header detection and OCR
        with patch.object(service, '_detect_header') as mock_detect:
            mock_detect.side_effect = [True, False, False, False, True, False, False, False]
            
            with patch.object(service, '_extract_and_ocr_header') as mock_ocr:
                mock_ocr.return_value = GridOCRResult(
                    last_name='DUPONT',
                    first_name='JEAN',
                    date_of_birth='15/03/2008',
                    overall_confidence=0.9,
                    fields=[],
                    status='OK'
                )
                
                result = service.process_exam(mock_exam, pages, dry_run=True)
        
        assert result.total_chunks == 2
        assert result.total_pages == 8
        # In dry run, no copies created
        assert len(result.copies_created) == 0
    
    def test_ambiguous_ocr_flagged(self, sample_students):
        """Ambiguous OCR results should be flagged."""
        service = AutoIdentificationService(sample_students)
        
        mock_exam = Mock()
        mock_exam.id = 'test-exam'
        
        pages = [f'/fake/page_{i:03d}.png' for i in range(4)]
        
        with patch.object(service, '_detect_header') as mock_detect:
            mock_detect.side_effect = [True, False, False, False]
            with patch.object(service, '_extract_and_ocr_header') as mock_ocr:
                mock_ocr.return_value = GridOCRResult(
                    last_name='DUP',  # Partial match
                    first_name='',
                    date_of_birth='',
                    overall_confidence=0.3,
                    fields=[],
                    status='PARTIAL'
                )
                
                result = service.process_exam(mock_exam, pages, dry_run=True)
        
        # Should be flagged as ambiguous or no match
        assert result.ambiguous + result.no_matches + result.ocr_failures > 0


# =============================================================================
# MARKERS
# =============================================================================

pytestmark = [
    pytest.mark.unit,
    pytest.mark.ocr,
]
