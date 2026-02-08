"""
OCR Pipeline Orchestrator — cascading Tier1 (local) -> Tier2 (cloud) -> Manual.
Feature-flagged via USE_NEW_OCR_PIPELINE setting.
"""
import logging
import time
from typing import Optional
from django.conf import settings

logger = logging.getLogger(__name__)

TIER1_AUTO_THRESHOLD = 0.75
TIER2_AUTO_THRESHOLD = 0.65


class OCRPipelineService:
    def __init__(self, csv_students: list):
        from .student_matcher import StudentMatcherService
        self.matcher = StudentMatcherService(csv_students)
        self._doc_ai = None

    @property
    def doc_ai(self):
        if self._doc_ai is None:
            project_id = getattr(settings, 'DOCUMENT_AI_PROJECT_ID', '')
            if project_id:
                from .document_ai_service import DocumentAIService
                self._doc_ai = DocumentAIService()
        return self._doc_ai

    def process_header(self, header_image, copy_uuid: str = '') -> dict:
        start = time.monotonic()

        tier1_result = self._run_tier1(header_image)
        if tier1_result and tier1_result['confidence'] >= TIER1_AUTO_THRESHOLD:
            match = self.matcher.match(
                tier1_result['last_name'], tier1_result['first_name'],
                tier1_result['date_of_birth'],
            )
            if match.decision == 'AUTO':
                elapsed = int((time.monotonic() - start) * 1000)
                return self._build_result('LOCAL', 'AUTO', tier1_result, match, elapsed)

        tier2_result = self._run_tier2(header_image)
        if tier2_result and tier2_result['confidence'] >= TIER2_AUTO_THRESHOLD:
            match = self.matcher.match(
                tier2_result['last_name'], tier2_result['first_name'],
                tier2_result['date_of_birth'],
            )
            elapsed = int((time.monotonic() - start) * 1000)
            if match.decision in ('AUTO', 'SEMI_AUTO'):
                return self._build_result('CLOUD', match.decision, tier2_result, match, elapsed)

        best_ocr = tier2_result or tier1_result or {
            'last_name': '', 'first_name': '', 'date_of_birth': '', 'confidence': 0.0,
        }
        match = self.matcher.match(
            best_ocr.get('last_name', ''), best_ocr.get('first_name', ''),
            best_ocr.get('date_of_birth', ''),
        )
        elapsed = int((time.monotonic() - start) * 1000)
        mode = match.decision if match.decision != 'AUTO' else 'SEMI_AUTO'
        return self._build_result('MANUAL', mode, best_ocr, match, elapsed)

    def _run_tier1(self, image) -> Optional[dict]:
        try:
            from .grid_ocr import GridOCRService
            service = GridOCRService()
            result = service.extract(image)
            if result.status == 'FAILED':
                return None
            return {
                'last_name': result.last_name, 'first_name': result.first_name,
                'date_of_birth': result.date_of_birth, 'confidence': result.overall_confidence,
            }
        except Exception as e:
            logger.warning(f"Tier 1 OCR failed: {e}")
            return None

    def _run_tier2(self, image) -> Optional[dict]:
        if not self.doc_ai or not self.doc_ai.is_configured:
            return None
        try:
            import cv2
            _, buffer = cv2.imencode('.png', image)
            result = self.doc_ai.process_header_image(buffer.tobytes())
            return None if result.get('error') else result
        except Exception as e:
            logger.warning(f"Tier 2 OCR failed: {e}")
            return None

    def _build_result(self, tier, mode, ocr_data, match, elapsed_ms):
        return {
            'tier': tier, 'ocr_mode': mode,
            'extracted': {
                'last_name': ocr_data.get('last_name', ''),
                'first_name': ocr_data.get('first_name', ''),
                'date_of_birth': ocr_data.get('date_of_birth', ''),
            },
            'top_candidates': [
                {'student_id': c.student_id, 'last_name': c.last_name,
                 'first_name': c.first_name, 'date_of_birth': c.date_of_birth,
                 'score': round(c.total_score, 4)}
                for c in match.candidates[:5]
            ],
            'confidence': round(match.best_score, 4),
            'processing_time_ms': elapsed_ms,
        }

    def validate_cross_sheet(self, chunks: list) -> list:
        from collections import defaultdict
        from .student_matcher import normalize_text

        by_student = defaultdict(list)
        for chunk in chunks:
            top = chunk.get('top_candidates', [])
            if top and chunk.get('ocr_mode') != 'MANUAL':
                by_student[top[0]['student_id']].append(chunk)

        for student_id, student_chunks in by_student.items():
            if len(student_chunks) < 2:
                for c in student_chunks:
                    c['cross_validation'] = 'SINGLE_SHEET'
                continue
            names = [normalize_text(c['extracted']['last_name']) for c in student_chunks]
            if len(set(names)) == 1:
                for c in student_chunks:
                    c['cross_validation'] = 'CONSISTENT'
            else:
                for c in student_chunks:
                    c['cross_validation'] = 'INCONSISTENT'
                    c['ocr_mode'] = 'MANUAL'
        return chunks
