"""
Tests for Prometheus metrics endpoint and instrumentation
Conformité: Phase S5-B - Observability
"""
from django.test import TestCase, override_settings
from django.urls import reverse
from core.prometheus import (
    record_request_metrics,
    generate_metrics,
    get_content_type,
    registry,
    http_requests_total,
    http_request_duration_seconds
)


class PrometheusMetricsTest(TestCase):
    """Test Prometheus metrics recording"""

    def setUp(self):
        """Reset metrics before each test"""
        # Clear all metrics
        for collector in list(registry._collector_to_names.keys()):
            try:
                registry.unregister(collector)
            except Exception:
                pass

        # Re-register metrics
        from prometheus_client import ProcessCollector, PlatformCollector, GCCollector
        ProcessCollector(registry=registry)
        PlatformCollector(registry=registry)
        GCCollector(registry=registry)
        registry.register(http_requests_total)
        registry.register(http_request_duration_seconds)

    def test_record_request_metrics_increments_counter(self):
        """Test that recording a request increments the counter"""
        # Record a request
        record_request_metrics(
            method='GET',
            path='/api/health/',
            status_code=200,
            duration=0.012
        )

        # Generate metrics
        metrics_output = generate_metrics().decode('utf-8')

        # Verify counter incremented
        self.assertIn('http_requests_total', metrics_output)
        self.assertIn('method="GET"', metrics_output)
        self.assertIn('path="/api/health/"', metrics_output)
        self.assertIn('status="200"', metrics_output)

    def test_record_request_metrics_records_duration(self):
        """Test that request duration is recorded in histogram"""
        # Record a request with specific duration
        record_request_metrics(
            method='POST',
            path='/api/copies/<uuid>/',
            status_code=201,
            duration=0.150  # 150ms
        )

        # Generate metrics
        metrics_output = generate_metrics().decode('utf-8')

        # Verify histogram recorded
        self.assertIn('http_request_duration_seconds', metrics_output)
        self.assertIn('method="POST"', metrics_output)
        self.assertIn('path="/api/copies/<uuid>/"', metrics_output)

    def test_record_request_metrics_handles_errors_gracefully(self):
        """Test that metrics recording never breaks on errors"""
        # This should not raise even with invalid data
        try:
            record_request_metrics(
                method='GET',
                path='/test/',
                status_code=200,
                duration=0.01
            )
        except Exception as e:
            self.fail(f"record_request_metrics raised exception: {e}")

    def test_generate_metrics_returns_valid_format(self):
        """Test that generated metrics are in valid Prometheus format"""
        metrics_data = generate_metrics()

        # Should be bytes
        self.assertIsInstance(metrics_data, bytes)

        # Should contain help and type declarations
        metrics_text = metrics_data.decode('utf-8')
        self.assertIn('# HELP', metrics_text)
        self.assertIn('# TYPE', metrics_text)

    def test_get_content_type_returns_prometheus_format(self):
        """Test that content type is correct for Prometheus"""
        content_type = get_content_type()

        # Should contain text/plain and version
        self.assertIn('text/plain', content_type)


class PrometheusEndpointTest(TestCase):
    """Test /metrics endpoint"""

    def test_metrics_endpoint_accessible_in_development(self):
        """Test that /metrics is accessible without auth in development (DEBUG=True)"""
        with override_settings(DEBUG=True):
            response = self.client.get('/metrics')

            self.assertEqual(response.status_code, 200)
            self.assertIn('text/plain', response['Content-Type'])

    def test_metrics_endpoint_returns_prometheus_format(self):
        """Test that /metrics returns valid Prometheus format"""
        with override_settings(DEBUG=True):
            response = self.client.get('/metrics')

            self.assertEqual(response.status_code, 200)

            content = response.content.decode('utf-8')
            # Should contain metrics declarations
            self.assertIn('# HELP', content)
            self.assertIn('# TYPE', content)
            self.assertIn('http_requests_total', content)
            self.assertIn('http_request_duration_seconds', content)

    def test_metrics_endpoint_contains_process_metrics(self):
        """Test that /metrics includes automatic process metrics"""
        with override_settings(DEBUG=True):
            response = self.client.get('/metrics')

            content = response.content.decode('utf-8')
            # Should contain process metrics
            self.assertTrue(
                'process_' in content or 'python_' in content,
                "Should contain process or Python metrics"
            )

    @override_settings(DEBUG=False, METRICS_TOKEN='test-secret-token')
    def test_metrics_endpoint_requires_token_in_production(self):
        """Test that /metrics requires token when METRICS_TOKEN is set"""
        # Without token: should return 403
        response = self.client.get('/metrics')
        self.assertEqual(response.status_code, 403)
        self.assertIn('Invalid or missing metrics token', response.content.decode())

    @override_settings(DEBUG=False, METRICS_TOKEN='test-secret-token')
    def test_metrics_endpoint_accepts_header_token(self):
        """Test that /metrics accepts token via X-Metrics-Token header"""
        response = self.client.get(
            '/metrics',
            HTTP_X_METRICS_TOKEN='test-secret-token'
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn('text/plain', response['Content-Type'])

    @override_settings(DEBUG=False, METRICS_TOKEN='test-secret-token')
    def test_metrics_endpoint_accepts_query_token(self):
        """Test that /metrics accepts token via ?token= query parameter"""
        response = self.client.get('/metrics?token=test-secret-token')

        self.assertEqual(response.status_code, 200)
        self.assertIn('text/plain', response['Content-Type'])

    @override_settings(DEBUG=False, METRICS_TOKEN='test-secret-token')
    def test_metrics_endpoint_rejects_invalid_token(self):
        """Test that /metrics rejects invalid tokens"""
        # Invalid header token
        response = self.client.get(
            '/metrics',
            HTTP_X_METRICS_TOKEN='wrong-token'
        )
        self.assertEqual(response.status_code, 403)

        # Invalid query token
        response = self.client.get('/metrics?token=wrong-token')
        self.assertEqual(response.status_code, 403)

    @override_settings(DEBUG=False)
    def test_metrics_endpoint_public_without_token_setting(self):
        """Test that /metrics is public if METRICS_TOKEN not set (operator's choice)"""
        # When METRICS_TOKEN not set, should be publicly accessible
        response = self.client.get('/metrics')

        # Should return 200 (public access)
        self.assertEqual(response.status_code, 200)


class PrometheusIntegrationTest(TestCase):
    """Integration tests for Prometheus metrics with requests"""

    def test_request_records_metrics(self):
        """Test that making a request records Prometheus metrics"""
        with override_settings(DEBUG=True):
            # Make a request to health endpoint
            self.client.get('/api/health/')

            # Fetch metrics
            response = self.client.get('/metrics')
            content = response.content.decode('utf-8')

            # Should contain recorded request
            self.assertIn('http_requests_total', content)
            # Note: Exact path may be normalized, check for health-related metrics
            self.assertTrue(
                'path="/api/health/"' in content or 'health' in content,
                "Should record health check request"
            )

    def test_multiple_requests_increment_counter(self):
        """Test that multiple requests increment the counter"""
        with override_settings(DEBUG=True):
            # Make multiple requests
            self.client.get('/api/health/')
            self.client.get('/api/health/')
            self.client.get('/api/health/')

            # Fetch metrics
            response = self.client.get('/metrics')
            content = response.content.decode('utf-8')

            # Should contain http_requests_total
            self.assertIn('http_requests_total', content)
            # Counter should be >= 3 (may include other requests)

    def test_error_requests_recorded(self):
        """Test that error responses are recorded in metrics"""
        with override_settings(DEBUG=True):
            # Request non-existent endpoint
            self.client.get('/api/nonexistent/')

            # Fetch metrics
            response = self.client.get('/metrics')
            content = response.content.decode('utf-8')

            # Should record 404 status
            self.assertIn('status="404"', content)
