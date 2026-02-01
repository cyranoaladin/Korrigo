"""
Test structured JSON logging configuration
Conformité: Phase S5-A - Observability

Tests verify:
- JSON formatter produces valid JSON
- Request ID middleware generates and preserves IDs
- Request context added to logs (request_id, path, method, user_id)
- No secrets/PII in logs
- Backwards compatibility with existing tests
"""
import json
import logging
from io import StringIO
from django.test import TestCase, RequestFactory, override_settings
from django.contrib.auth.models import User
from core.logging import ViatiqueJSONFormatter
from core.middleware.request_id import RequestIDMiddleware, RequestContextLogFilter


class JSONFormatterTest(TestCase):
    """Test ViatiqueJSONFormatter produces valid JSON"""

    def setUp(self):
        """Set up test logger with JSON formatter"""
        self.stream = StringIO()
        self.handler = logging.StreamHandler(self.stream)

        # Use JSON formatter
        self.handler.setFormatter(ViatiqueJSONFormatter())

        self.logger = logging.getLogger('test_json_logger')
        self.logger.addHandler(self.handler)
        self.logger.setLevel(logging.INFO)

    def tearDown(self):
        """Clean up logger"""
        self.logger.removeHandler(self.handler)

    def test_json_formatter_produces_valid_json(self):
        """Verify JSON formatter outputs parseable JSON"""
        # Log a message
        self.logger.info("Test message")

        # Get output
        output = self.stream.getvalue().strip()

        # Verify JSON parseable
        log_entry = json.loads(output)

        # Assertions
        self.assertIn('message', log_entry)
        self.assertEqual(log_entry['message'], 'Test message')
        self.assertIn('timestamp', log_entry)
        self.assertIn('level', log_entry)
        self.assertIn('logger', log_entry)
        self.assertIn('module', log_entry)
        self.assertIn('function', log_entry)
        self.assertIn('line', log_entry)

    def test_json_formatter_includes_extra_fields(self):
        """Verify extra fields added to JSON logs"""
        # Log with extra context
        self.logger.info("Test with context", extra={
            'request_id': 'test-request-id',
            'path': '/api/test/',
            'method': 'GET',
            'status_code': 200,
            'user_id': 42
        })

        # Parse output
        output = self.stream.getvalue().strip()
        log_entry = json.loads(output)

        # Verify extra fields
        self.assertEqual(log_entry['request_id'], 'test-request-id')
        self.assertEqual(log_entry['path'], '/api/test/')
        self.assertEqual(log_entry['method'], 'GET')
        self.assertEqual(log_entry['status_code'], 200)
        self.assertEqual(log_entry['user_id'], 42)

    def test_json_formatter_handles_exceptions(self):
        """Verify exceptions serialized as string in JSON"""
        try:
            raise ValueError("Test exception")
        except ValueError:
            self.logger.error("Error occurred", exc_info=True)

        # Parse output
        output = self.stream.getvalue().strip()
        log_entry = json.loads(output)

        # Verify exception info present and serialized
        self.assertIn('exc_info', log_entry)
        self.assertIsInstance(log_entry['exc_info'], str)
        self.assertIn('ValueError: Test exception', log_entry['exc_info'])
        # Verify it's a single line (no newlines break JSON parsing)
        # Actually, exc_info may contain newlines, but it should be properly escaped in JSON


class RequestIDMiddlewareTest(TestCase):
    """Test Request ID middleware functionality"""

    def setUp(self):
        """Set up test request factory"""
        self.factory = RequestFactory()
        self.middleware = RequestIDMiddleware(get_response=lambda r: None)

    def test_request_id_generated(self):
        """Verify request ID generated automatically"""
        request = self.factory.get('/api/health/')

        # Process request
        self.middleware.process_request(request)

        # Verify request_id attribute set
        self.assertTrue(hasattr(request, 'request_id'))
        self.assertIsInstance(request.request_id, str)
        # UUID4 format: 36 characters including hyphens
        self.assertEqual(len(request.request_id), 36)

    def test_client_request_id_preserved(self):
        """Verify client-provided request ID preserved"""
        custom_id = 'custom-request-id-12345'
        request = self.factory.get('/api/health/', HTTP_X_REQUEST_ID=custom_id)

        # Process request
        self.middleware.process_request(request)

        # Verify custom ID preserved
        self.assertEqual(request.request_id, custom_id)

    def test_request_id_added_to_response_header(self):
        """Verify X-Request-ID header added to response"""
        from django.http import HttpResponse

        request = self.factory.get('/api/health/')
        response = HttpResponse()

        # Process request and response
        self.middleware.process_request(request)
        response = self.middleware.process_response(request, response)

        # Verify header present
        self.assertIn('X-Request-ID', response)
        self.assertEqual(response['X-Request-ID'], request.request_id)


class RequestContextLogFilterTest(TestCase):
    """Test RequestContextLogFilter adds context to log records"""

    def setUp(self):
        """Set up test logger with request context filter"""
        self.stream = StringIO()
        self.handler = logging.StreamHandler(self.stream)
        self.handler.setFormatter(ViatiqueJSONFormatter())

        # Add request context filter
        self.handler.addFilter(RequestContextLogFilter())

        self.logger = logging.getLogger('test_context_logger')
        self.logger.addHandler(self.handler)
        self.logger.setLevel(logging.INFO)

        self.factory = RequestFactory()
        self.middleware = RequestIDMiddleware(get_response=lambda r: None)

    def tearDown(self):
        """Clean up logger"""
        self.logger.removeHandler(self.handler)

    def test_request_context_added_to_logs(self):
        """Verify request context (request_id, path, method) added to logs"""
        request = self.factory.get('/api/health/')

        # Process request (adds request_id to thread-local)
        self.middleware.process_request(request)

        # Log a message
        self.logger.info("Test with request context")

        # Parse output
        output = self.stream.getvalue().strip()
        log_entry = json.loads(output)

        # Verify request context fields
        self.assertIn('request_id', log_entry)
        self.assertEqual(log_entry['request_id'], request.request_id)
        self.assertIn('path', log_entry)
        self.assertEqual(log_entry['path'], '/api/health/')
        self.assertIn('method', log_entry)
        self.assertEqual(log_entry['method'], 'GET')

        # Clean up thread-local
        self.middleware._cleanup_thread_locals()

    def test_authenticated_user_id_in_logs(self):
        """Verify authenticated user ID added to logs"""
        # Create user
        user = User.objects.create_user(username='testuser', password='testpass')

        request = self.factory.get('/api/health/')
        request.user = user

        # Process request
        self.middleware.process_request(request)

        # Log a message
        self.logger.info("Test with user context")

        # Parse output
        output = self.stream.getvalue().strip()
        log_entry = json.loads(output)

        # Verify user_id present (NOT email/username)
        self.assertIn('user_id', log_entry)
        self.assertEqual(log_entry['user_id'], user.id)
        # Ensure email/username NOT logged
        self.assertNotIn('testuser', str(log_entry))

        # Clean up thread-local
        self.middleware._cleanup_thread_locals()


class IntegrationTest(TestCase):
    """Integration test for request ID in API responses"""

    def test_api_health_returns_request_id(self):
        """Verify /api/health/ returns X-Request-ID header"""
        response = self.client.get('/api/health/')

        # Verify response
        self.assertEqual(response.status_code, 200)

        # Verify X-Request-ID header present
        self.assertIn('X-Request-ID', response)

        # Verify UUID format
        request_id = response['X-Request-ID']
        self.assertEqual(len(request_id), 36)

    def test_custom_request_id_preserved(self):
        """Verify custom request ID preserved in response"""
        custom_id = 'custom-trace-id-abcdef'

        response = self.client.get('/api/health/', HTTP_X_REQUEST_ID=custom_id)

        # Verify custom ID preserved
        self.assertEqual(response['X-Request-ID'], custom_id)
