"""Tests for DocumentAIService — all mocked, no network calls."""
import pytest
import time
from processing.services.document_ai_service import DocumentAIService, DocumentAICircuitBreaker


class TestCircuitBreaker:
    def test_opens_after_max_failures(self):
        cb = DocumentAICircuitBreaker(max_failures=3)
        cb.record_failure()
        cb.record_failure()
        assert not cb.is_open()
        cb.record_failure()
        assert cb.is_open()

    def test_resets_on_success(self):
        cb = DocumentAICircuitBreaker(max_failures=2)
        cb.record_failure()
        cb.record_failure()
        assert cb.is_open()
        cb.record_success()
        assert not cb.is_open()

    def test_resets_after_timeout(self):
        cb = DocumentAICircuitBreaker(max_failures=1, reset_after_seconds=0.1)
        cb.record_failure()
        assert cb.is_open()
        time.sleep(0.15)
        assert not cb.is_open()


class TestDocumentAIService:
    def _make_service(self, project_id='', processor_id=''):
        svc = DocumentAIService.__new__(DocumentAIService)
        svc.project_id = project_id
        svc.processor_id = processor_id
        svc.location = 'eu'
        svc._client = None
        svc._circuit_breaker = DocumentAICircuitBreaker()
        return svc

    def test_not_configured_returns_empty(self):
        svc = self._make_service()
        result = svc.process_header_image(b'fake')
        assert result['confidence'] == 0.0
        assert result['error'] == 'not_configured'

    def test_circuit_breaker_blocks_call(self):
        svc = self._make_service(project_id='test', processor_id='test')
        svc._circuit_breaker = DocumentAICircuitBreaker(max_failures=1)
        svc._circuit_breaker.record_failure()
        result = svc.process_header_image(b'fake')
        assert result['error'] == 'circuit_breaker_open'

    def test_extract_from_raw_text(self):
        svc = self._make_service()
        ln, fn, dob = svc._extract_from_raw_text(
            "NOM DE FAMILLE : DUPONT\nPRENOM(S) : MARIE\nNe(e) le : 15/03/2008"
        )
        assert ln == 'DUPONT'
        assert fn == 'MARIE'
        assert dob == '15/03/2008'
