"""
Google Cloud Document AI integration — Tier 2 OCR.
Strictly MOCK in CI/tests (no network calls).
"""
import logging
import re
import time
import unicodedata
from django.conf import settings

logger = logging.getLogger(__name__)


class DocumentAICircuitBreaker:
    def __init__(self, max_failures=5, reset_after_seconds=300):
        self._failures = 0
        self._max = max_failures
        self._reset_after = reset_after_seconds
        self._last_failure = None
        self._open = False

    def record_failure(self):
        self._failures += 1
        self._last_failure = time.monotonic()
        if self._failures >= self._max:
            self._open = True
            logger.error(f"Document AI circuit breaker OPEN after {self._failures} failures")

    def record_success(self):
        self._failures = 0
        self._open = False

    def is_open(self) -> bool:
        if self._open and self._last_failure:
            if time.monotonic() - self._last_failure > self._reset_after:
                self._open = False
                self._failures = 0
        return self._open


class DocumentAIService:
    def __init__(self):
        self.project_id = getattr(settings, 'DOCUMENT_AI_PROJECT_ID', '')
        self.location = getattr(settings, 'DOCUMENT_AI_LOCATION', 'us')
        self.processor_id = getattr(settings, 'DOCUMENT_AI_PROCESSOR_ID', '')
        self._client = None
        self._circuit_breaker = DocumentAICircuitBreaker()

    @property
    def is_configured(self) -> bool:
        return bool(self.project_id and self.processor_id)

    def process_header_image(self, image_bytes: bytes, mime_type: str = "image/png") -> dict:
        if self._circuit_breaker.is_open():
            return self._empty_result('circuit_breaker_open')
        if not self.is_configured:
            return self._empty_result('not_configured')
        try:
            from google.cloud import documentai_v1 as documentai
            from google.api_core.client_options import ClientOptions
            if self._client is None:
                endpoint = f"{self.location}-documentai.googleapis.com"
                self._client = documentai.DocumentProcessorServiceClient(
                    client_options=ClientOptions(api_endpoint=endpoint)
                )
            proc_name = self._client.processor_path(self.project_id, self.location, self.processor_id)
            raw_document = documentai.RawDocument(content=image_bytes, mime_type=mime_type)
            result = self._client.process_document(
                request=documentai.ProcessRequest(name=proc_name, raw_document=raw_document)
            )
            self._circuit_breaker.record_success()
            return self._parse_response(result.document)
        except Exception as e:
            self._circuit_breaker.record_failure()
            logger.error(f"Document AI call failed: {e}", exc_info=True)
            return self._empty_result(str(e))

    def _parse_response(self, document) -> dict:
        raw_text = document.text or ''
        last_name = first_name = date_of_birth = ''
        entities = []
        overall_confidence = 0.0
        for page in document.pages:
            for ff in page.form_fields:
                key = self._get_text(ff.field_name, raw_text).strip().upper()
                value = self._get_text(ff.field_value, raw_text).strip()
                conf = ff.field_value.confidence if ff.field_value else 0.0
                entities.append({'key': key, 'value': value, 'confidence': conf})
                if any(k in key for k in ['NOM', 'FAMILLE', 'NAME']):
                    if not last_name or conf > overall_confidence:
                        last_name = value.upper()
                elif any(k in key for k in ['PRENOM', 'FIRST']):
                    first_name = value.upper()
                elif any(k in key for k in ['NE', 'NAISSANCE', 'DATE', 'BIRTH']):
                    date_of_birth = value
        if not last_name and raw_text:
            last_name, first_name, date_of_birth = self._extract_from_raw_text(raw_text)
        if entities:
            overall_confidence = sum(e['confidence'] for e in entities) / len(entities)
        return {'last_name': last_name, 'first_name': first_name,
                'date_of_birth': date_of_birth, 'confidence': overall_confidence,
                'raw_text': raw_text, 'entities': entities}

    def _get_text(self, layout, full_text: str) -> str:
        if not layout or not layout.text_anchor or not layout.text_anchor.text_segments:
            return ''
        return ''.join(
            full_text[int(seg.start_index):int(seg.end_index)]
            for seg in layout.text_anchor.text_segments
        )

    def _extract_from_raw_text(self, text: str) -> tuple:
        text_clean = unicodedata.normalize('NFD', text.upper())
        text_clean = ''.join(c for c in text_clean if unicodedata.category(c) != 'Mn')
        last_name = first_name = dob = ''
        m = re.search(r'NOM\s*(?:DE\s+FAMILLE)?\s*[:;]?\s*([A-Z \-]{2,})', text_clean)
        if m:
            last_name = m.group(1).strip()
        m = re.search(r'PRENOM\s*(?:\(S\))?\s*[:;]?\s*([A-Z \-]{2,})', text_clean)
        if m:
            first_name = m.group(1).strip()
        m = re.search(r'(\d{1,2})\s*[/\-\.]\s*(\d{1,2})\s*[/\-\.]\s*(\d{2,4})', text)
        if m:
            dob = f"{m.group(1).zfill(2)}/{m.group(2).zfill(2)}/{m.group(3)}"
        return last_name, first_name, dob

    def _empty_result(self, error: str = '') -> dict:
        return {'last_name': '', 'first_name': '', 'date_of_birth': '',
                'confidence': 0.0, 'raw_text': '', 'entities': [], 'error': error}
