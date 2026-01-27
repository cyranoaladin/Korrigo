"""
Tests for MetricsMiddleware
P1-OP-08: Monitoring infrastructure tests
"""
import time
from django.test import TestCase, RequestFactory
from django.http import HttpResponse
from django.contrib.auth import get_user_model
from core.middleware.metrics import MetricsMiddleware, MetricsCollector

User = get_user_model()


class MetricsCollectorTests(TestCase):
    def setUp(self):
        self.collector = MetricsCollector()

    def test_initial_state(self):
        """Collector starts with empty metrics"""
        metrics = self.collector.get_metrics()
        self.assertEqual(len(metrics), 0)

    def test_record_request_creates_endpoint_entry(self):
        """Recording a request creates endpoint entry"""
        self.collector.record_request('/api/test/', 'GET', 0.5, 200)
        metrics = self.collector.get_metrics()
        
        self.assertEqual(len(metrics), 1)
        self.assertIn('GET /api/test/', metrics)
        
        endpoint = metrics['GET /api/test/']
        self.assertEqual(endpoint['count'], 1)
        self.assertEqual(endpoint['errors'], 0)

    def test_record_error_increments_error_count(self):
        """Recording error responses increments error counters"""
        self.collector.record_request('/api/test/', 'POST', 0.3, 500)
        metrics = self.collector.get_metrics()
        
        endpoint = metrics['POST /api/test/']
        self.assertEqual(endpoint['errors'], 1)

    def test_path_normalization_uuid(self):
        """UUID patterns are normalized to prevent cardinality explosion"""
        uuid_path = '/api/copies/123e4567-e89b-12d3-a456-426614174000/finalize/'
        normalized_path = MetricsMiddleware._normalize_path(uuid_path)
        self.assertEqual(normalized_path, '/api/copies/<uuid>/finalize/')

    def test_path_normalization_integer(self):
        """Integer IDs are normalized"""
        normalized_path = MetricsMiddleware._normalize_path('/api/exams/123/copies/')
        self.assertEqual(normalized_path, '/api/exams/<id>/copies/')

    def test_aggregation_multiple_requests(self):
        """Multiple requests to same endpoint aggregate correctly"""
        for i in range(5):
            self.collector.record_request('/api/test/', 'GET', 0.1 * (i + 1), 200)
        
        metrics = self.collector.get_metrics()
        endpoint = metrics['GET /api/test/']
        
        self.assertEqual(endpoint['count'], 5)
        self.assertAlmostEqual(endpoint['total_time'], 1.5)  # 0.1+0.2+0.3+0.4+0.5
        self.assertAlmostEqual(endpoint['min_time'], 0.1)
        self.assertAlmostEqual(endpoint['max_time'], 0.5)

    def test_reset_clears_metrics(self):
        """Reset clears all metrics"""
        self.collector.record_request('/api/test/', 'GET', 0.1, 200)
        self.collector.reset()
        
        metrics = self.collector.get_metrics()
        self.assertEqual(len(metrics), 0)

    def test_thread_safety(self):
        """Collector is thread-safe"""
        import threading
        
        def record_requests():
            for _ in range(100):
                self.collector.record_request('/api/test/', 'GET', 0.1, 200)
        
        threads = [threading.Thread(target=record_requests) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        metrics = self.collector.get_metrics()
        endpoint = metrics['GET /api/test/']
        self.assertEqual(endpoint['count'], 500)


class MetricsMiddlewareTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.middleware = MetricsMiddleware(get_response=lambda r: HttpResponse())
        self.collector = MetricsCollector()
        
        # Replace global collector with test instance
        import core.middleware.metrics
        self.original_collector = core.middleware.metrics.metrics_collector
        core.middleware.metrics.metrics_collector = self.collector

    def tearDown(self):
        # Restore original collector
        import core.middleware.metrics
        core.middleware.metrics.metrics_collector = self.original_collector

    def test_middleware_records_request(self):
        """Middleware records request metrics"""
        request = self.factory.get('/api/test/')
        self.middleware.process_request(request)
        
        response = HttpResponse(status=200)
        self.middleware.process_response(request, response)
        
        metrics = self.collector.get_metrics()
        self.assertIn('GET /api/test/', metrics)

    def test_middleware_records_errors(self):
        """Middleware records error responses"""
        request = self.factory.post('/api/fail/')
        self.middleware.process_request(request)
        
        response = HttpResponse(status=500)
        self.middleware.process_response(request, response)
        
        metrics = self.collector.get_metrics()
        endpoint = metrics['POST /api/fail/']
        self.assertEqual(endpoint['errors'], 1)

    def test_middleware_normalizes_paths(self):
        """Middleware normalizes paths with UUIDs and IDs"""
        request = self.factory.get('/api/copies/123e4567-e89b-12d3-a456-426614174000/')
        self.middleware.process_request(request)
        
        response = HttpResponse(status=200)
        self.middleware.process_response(request, response)
        
        metrics = self.collector.get_metrics()
        self.assertIn('GET /api/copies/<uuid>/', metrics)

    def test_slow_request_logging(self):
        """Middleware logs slow requests"""
        import logging
        with self.assertLogs('metrics', level='WARNING') as cm:
            request = self.factory.get('/api/slow/')
            request._metrics_start_time = time.time() - 6.0  # Simulate slow request
            
            response = HttpResponse(status=200)
            self.middleware.process_response(request, response)
        
        self.assertTrue(any('Slow request detected' in msg for msg in cm.output))

    def test_response_time_header(self):
        """Middleware adds response time header"""
        request = self.factory.get('/api/test/')
        self.middleware.process_request(request)
        
        response = HttpResponse(status=200)
        response = self.middleware.process_response(request, response)
        
        self.assertIn('X-Response-Time-Ms', response)
