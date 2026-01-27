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
        self.assertEqual(metrics['total_requests'], 0)
        self.assertEqual(metrics['total_errors'], 0)
        self.assertEqual(len(metrics['endpoints']), 0)

    def test_record_request_creates_endpoint_entry(self):
        """Recording a request creates endpoint entry"""
        self.collector.record_request('/api/test/', 200, 0.5)
        metrics = self.collector.get_metrics()
        
        self.assertEqual(metrics['total_requests'], 1)
        self.assertEqual(metrics['total_errors'], 0)
        self.assertEqual(len(metrics['endpoints']), 1)
        
        endpoint = metrics['endpoints'][0]
        self.assertEqual(endpoint['endpoint'], '/api/test/')
        self.assertEqual(endpoint['count'], 1)
        self.assertEqual(endpoint['errors'], 0)

    def test_record_error_increments_error_count(self):
        """Recording error responses increments error counters"""
        self.collector.record_request('/api/test/', 500, 0.3)
        metrics = self.collector.get_metrics()
        
        self.assertEqual(metrics['total_errors'], 1)
        endpoint = metrics['endpoints'][0]
        self.assertEqual(endpoint['errors'], 1)
        self.assertAlmostEqual(endpoint['error_rate'], 100.0)

    def test_path_normalization_uuid(self):
        """UUID patterns are normalized to prevent cardinality explosion"""
        uuid_path = '/api/copies/123e4567-e89b-12d3-a456-426614174000/finalize/'
        self.collector.record_request(uuid_path, 200, 0.1)
        
        metrics = self.collector.get_metrics()
        endpoint = metrics['endpoints'][0]
        self.assertEqual(endpoint['endpoint'], '/api/copies/<uuid>/finalize/')

    def test_path_normalization_integer(self):
        """Integer IDs are normalized"""
        self.collector.record_request('/api/exams/123/copies/', 200, 0.1)
        
        metrics = self.collector.get_metrics()
        endpoint = metrics['endpoints'][0]
        self.assertEqual(endpoint['endpoint'], '/api/exams/<id>/copies/')

    def test_aggregation_multiple_requests(self):
        """Multiple requests to same endpoint aggregate correctly"""
        for i in range(5):
            self.collector.record_request('/api/test/', 200, 0.1 * (i + 1))
        
        metrics = self.collector.get_metrics()
        endpoint = metrics['endpoints'][0]
        
        self.assertEqual(endpoint['count'], 5)
        self.assertAlmostEqual(endpoint['avg_time_ms'], 300.0)  # (100+200+300+400+500)/5
        self.assertAlmostEqual(endpoint['min_time_ms'], 100.0)
        self.assertAlmostEqual(endpoint['max_time_ms'], 500.0)

    def test_reset_clears_metrics(self):
        """Reset clears all metrics"""
        self.collector.record_request('/api/test/', 200, 0.1)
        self.collector.reset()
        
        metrics = self.collector.get_metrics()
        self.assertEqual(metrics['total_requests'], 0)
        self.assertEqual(len(metrics['endpoints']), 0)

    def test_thread_safety(self):
        """Collector is thread-safe"""
        import threading
        
        def record_requests():
            for _ in range(100):
                self.collector.record_request('/api/test/', 200, 0.1)
        
        threads = [threading.Thread(target=record_requests) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        metrics = self.collector.get_metrics()
        self.assertEqual(metrics['total_requests'], 500)  # 5 threads * 100 requests


class MetricsMiddlewareTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.middleware = MetricsMiddleware(get_response=lambda r: HttpResponse())

    def test_middleware_records_request(self):
        """Middleware records successful requests"""
        self.middleware.collector.reset()
        
        request = self.factory.get('/api/health/')
        response = self.middleware(request)
        
        metrics = self.middleware.collector.get_metrics()
        self.assertEqual(metrics['total_requests'], 1)
        self.assertEqual(metrics['total_errors'], 0)

    def test_middleware_adds_response_time_header(self):
        """Middleware adds X-Response-Time-Ms header"""
        request = self.factory.get('/api/test/')
        response = self.middleware(request)
        
        self.assertIn('X-Response-Time-Ms', response)
        response_time = float(response['X-Response-Time-Ms'])
        self.assertGreater(response_time, 0)

    def test_middleware_handles_exceptions(self):
        """Middleware records errors when view raises exception"""
        def error_view(request):
            raise ValueError("Test error")
        
        middleware = MetricsMiddleware(get_response=error_view)
        middleware.collector.reset()
        
        request = self.factory.get('/api/error/')
        
        with self.assertRaises(ValueError):
            middleware(request)
        
        metrics = middleware.collector.get_metrics()
        self.assertEqual(metrics['total_requests'], 1)
        self.assertEqual(metrics['total_errors'], 1)

    def test_slow_request_logging(self):
        """Middleware logs warning for slow requests"""
        def slow_view(request):
            time.sleep(0.01)  # Simulate slow operation
            return HttpResponse()
        
        middleware = MetricsMiddleware(get_response=slow_view)
        request = self.factory.get('/api/slow/')
        
        with self.assertLogs('core.middleware.metrics', level='INFO') as logs:
            response = middleware(request)
        
        # Verify response time header exists
        self.assertIn('X-Response-Time-Ms', response)
