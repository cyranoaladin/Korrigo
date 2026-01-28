"""
P0-OP-08: Basic metrics collection middleware
Collects HTTP request metrics for monitoring and alerting
Conformité: Phase S5-B - Prometheus metrics integration
"""
import time
import logging
from django.utils.deprecation import MiddlewareMixin
from collections import defaultdict
from threading import Lock
from core.prometheus import record_request_metrics

logger = logging.getLogger('metrics')

class MetricsCollector:
    """
    Thread-safe metrics collector for basic application monitoring
    P0-OP-08: Provides observability without external infrastructure
    """
    def __init__(self):
        self._lock = Lock()
        self._metrics = defaultdict(lambda: {
            'count': 0,
            'total_time': 0.0,
            'min_time': float('inf'),
            'max_time': 0.0,
            'errors': 0
        })
        
    def record_request(self, path, method, duration, status_code):
        """Record a request metric"""
        key = f"{method} {path}"
        with self._lock:
            m = self._metrics[key]
            m['count'] += 1
            m['total_time'] += duration
            m['min_time'] = min(m['min_time'], duration)
            m['max_time'] = max(m['max_time'], duration)
            if status_code >= 400:
                m['errors'] += 1
    
    def get_metrics(self):
        """Get current metrics snapshot"""
        with self._lock:
            return dict(self._metrics)
    
    def reset(self):
        """Reset all metrics"""
        with self._lock:
            self._metrics.clear()

# Global metrics collector instance
metrics_collector = MetricsCollector()


class MetricsMiddleware(MiddlewareMixin):
    """
    Middleware to collect HTTP request metrics
    P0-OP-08 FIX: Provides basic observability for production monitoring
    """
    
    def process_request(self, request):
        """Mark request start time"""
        request._metrics_start_time = time.time()
        return None
    
    def process_response(self, request, response):
        """Record request metrics"""
        if hasattr(request, '_metrics_start_time'):
            duration = time.time() - request._metrics_start_time
            duration_ms = duration * 1000

            # Normalize path to avoid explosion of unique paths
            path = self._normalize_path(request.path)

            metrics_collector.record_request(
                path=path,
                method=request.method,
                duration=duration,
                status_code=response.status_code
            )

            # S5-A: Structured logging with extra context for JSON logs
            logger.info(
                f"{request.method} {request.path} {response.status_code}",
                extra={
                    'status_code': response.status_code,
                    'duration_ms': duration_ms,
                }
            )

            # S5-B: Record Prometheus metrics
            record_request_metrics(
                method=request.method,
                path=path,
                status_code=response.status_code,
                duration=duration
            )

            # Log slow requests (> 5 seconds)
            if duration > 5.0:
                logger.warning(
                    f"Slow request detected: {request.method} {request.path} "
                    f"took {duration:.2f}s (status {response.status_code})",
                    extra={
                        'status_code': response.status_code,
                        'duration_ms': duration_ms,
                    }
                )

            # Add metrics header (useful for debugging)
            response['X-Response-Time-Ms'] = f"{duration_ms:.2f}"

        return response
    
    def process_exception(self, request, exception):
        """Record exception metrics"""
        if hasattr(request, '_metrics_start_time'):
            duration = time.time() - request._metrics_start_time
            duration_ms = duration * 1000
            path = self._normalize_path(request.path)

            metrics_collector.record_request(
                path=path,
                method=request.method,
                duration=duration,
                status_code=500  # Mark as error
            )

            # S5-B: Record Prometheus metrics for exceptions
            record_request_metrics(
                method=request.method,
                path=path,
                status_code=500,
                duration=duration
            )

            # S5-A: Structured logging with extra context for JSON logs
            logger.error(
                f"Request exception: {request.method} {request.path} "
                f"after {duration:.2f}s: {exception}",
                extra={
                    'status_code': 500,
                    'duration_ms': duration_ms,
                },
                exc_info=True
            )

        return None
    
    @staticmethod
    def _normalize_path(path):
        """Normalize path to reduce cardinality"""
        # Replace UUIDs with placeholder
        import re
        path = re.sub(
            r'/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}',
            '/<uuid>',
            path,
            flags=re.IGNORECASE
        )
        # Replace numeric IDs
        path = re.sub(r'/\d+', '/<id>', path)
        return path
