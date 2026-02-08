"""Tests for OCRPipelineService — cascade, cross-validation."""
import pytest
from unittest.mock import patch, MagicMock
from processing.services.ocr_pipeline import OCRPipelineService


@pytest.fixture
def csv_students():
    return [
        {'id': 1, 'last_name': 'DUPONT', 'first_name': 'MARIE',
         'date_of_birth': '15/03/2008', 'email': 'marie@e.fr'},
        {'id': 2, 'last_name': 'MARTIN', 'first_name': 'PAUL',
         'date_of_birth': '22/11/2007', 'email': 'paul@e.fr'},
    ]


class TestCascade:
    @patch('processing.services.ocr_pipeline.OCRPipelineService._run_tier1')
    def test_tier1_auto_skips_tier2(self, mock_tier1, csv_students):
        mock_tier1.return_value = {
            'last_name': 'DUPONT', 'first_name': 'MARIE',
            'date_of_birth': '15/03/2008', 'confidence': 0.90,
        }
        pipeline = OCRPipelineService(csv_students)
        result = pipeline.process_header(MagicMock(), 'test-uuid')
        assert result['tier'] == 'LOCAL'
        assert result['ocr_mode'] == 'AUTO'

    @patch('processing.services.ocr_pipeline.OCRPipelineService._run_tier2')
    @patch('processing.services.ocr_pipeline.OCRPipelineService._run_tier1')
    def test_tier1_fail_falls_to_tier2(self, mock_tier1, mock_tier2, csv_students):
        mock_tier1.return_value = None
        mock_tier2.return_value = {
            'last_name': 'DUPONT', 'first_name': 'MARIE',
            'date_of_birth': '15/03/2008', 'confidence': 0.80,
        }
        pipeline = OCRPipelineService(csv_students)
        result = pipeline.process_header(MagicMock(), 'test-uuid')
        assert result['tier'] == 'CLOUD'

    @patch('processing.services.ocr_pipeline.OCRPipelineService._run_tier2')
    @patch('processing.services.ocr_pipeline.OCRPipelineService._run_tier1')
    def test_both_fail_goes_manual(self, mock_tier1, mock_tier2, csv_students):
        mock_tier1.return_value = None
        mock_tier2.return_value = None
        pipeline = OCRPipelineService(csv_students)
        result = pipeline.process_header(MagicMock(), 'test-uuid')
        assert result['tier'] == 'MANUAL'
        assert result['ocr_mode'] == 'MANUAL'

    @patch('processing.services.ocr_pipeline.OCRPipelineService._run_tier1')
    def test_tier1_low_conf_not_local_auto(self, mock_tier1, csv_students):
        mock_tier1.return_value = {
            'last_name': 'DUP', 'first_name': 'M',
            'date_of_birth': '15/03/2008', 'confidence': 0.40,
        }
        pipeline = OCRPipelineService(csv_students)
        result = pipeline.process_header(MagicMock(), 'test-uuid')
        assert not (result['tier'] == 'LOCAL' and result['ocr_mode'] == 'AUTO')


class TestCrossValidation:
    def test_consistent_sheets(self, csv_students):
        pipeline = OCRPipelineService(csv_students)
        chunks = [
            {'extracted': {'last_name': 'DUPONT'}, 'ocr_mode': 'AUTO',
             'top_candidates': [{'student_id': 1}]},
            {'extracted': {'last_name': 'DUPONT'}, 'ocr_mode': 'AUTO',
             'top_candidates': [{'student_id': 1}]},
        ]
        result = pipeline.validate_cross_sheet(chunks)
        assert result[0]['cross_validation'] == 'CONSISTENT'

    def test_inconsistent_forced_manual(self, csv_students):
        pipeline = OCRPipelineService(csv_students)
        chunks = [
            {'extracted': {'last_name': 'DUPONT'}, 'ocr_mode': 'AUTO',
             'top_candidates': [{'student_id': 1}]},
            {'extracted': {'last_name': 'MARTIN'}, 'ocr_mode': 'AUTO',
             'top_candidates': [{'student_id': 1}]},
        ]
        result = pipeline.validate_cross_sheet(chunks)
        assert result[0]['cross_validation'] == 'INCONSISTENT'
        assert result[0]['ocr_mode'] == 'MANUAL'

    def test_single_sheet(self, csv_students):
        pipeline = OCRPipelineService(csv_students)
        chunks = [
            {'extracted': {'last_name': 'DUPONT'}, 'ocr_mode': 'AUTO',
             'top_candidates': [{'student_id': 1}]},
        ]
        result = pipeline.validate_cross_sheet(chunks)
        assert result[0]['cross_validation'] == 'SINGLE_SHEET'
