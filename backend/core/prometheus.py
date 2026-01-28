"""
Prometheus metrics instrumentation for Viatique
Conformité: Phase S5-B - Observability

Exposes Prometheus-compatible metrics with:
- HTTP request counter (method, path, status)
- HTTP request duration histogram (method, path)
- Process metrics (automatic: CPU, memory, GC, file descriptors)

Security:
- Metrics collection never blocks requests (exceptions caught)
- No sensitive data exposed (paths normalized, no PII)

Multi-process considerations:
- Basic mode: Per-process metrics (acceptable for v1)
- Future enhancement: Use prometheus_client.multiprocess mode
  for multi-worker Gunicorn deployments

Usage:
    from core.prometheus import record_request_metrics

    record_request_metrics(
        method='GET',
        path='/api/health/',
        status_code=200,
        duration=0.012  # seconds
    )
"""
import logging
from prometheus_client import (
    Counter,
    Histogram,
    generate_latest,
    CONTENT_TYPE_LATEST,
    CollectorRegistry,
    ProcessCollector,
    PlatformCollector,
    GCCollector,
)

logger = logging.getLogger(__name__)

# Registry for metrics (allows isolation in tests)
registry = CollectorRegistry()

# Automatic process metrics (CPU, memory, GC, file descriptors)
ProcessCollector(registry=registry)
PlatformCollector(registry=registry)
GCCollector(registry=registry)

# HTTP Request Counter
http_requests_total = Counter(
    'http_requests_total',
    'Total HTTP requests processed',
    ['method', 'path', 'status'],
    registry=registry
)

# HTTP Request Duration Histogram
# Buckets: 5ms, 10ms, 25ms, 50ms, 100ms, 250ms, 500ms, 1s, 2.5s, 5s, 10s
http_request_duration_seconds = Histogram(
    'http_request_duration_seconds',
    'HTTP request latency distribution in seconds',
    ['method', 'path'],
    buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
    registry=registry
)


def record_request_metrics(method, path, status_code, duration):
    """
    Record HTTP request metrics for Prometheus.

    Args:
        method (str): HTTP method (GET, POST, PUT, DELETE, etc.)
        path (str): Normalized request path (e.g., /api/copies/<uuid>/)
                    IMPORTANT: Path should be normalized to avoid cardinality explosion
                    Use MetricsMiddleware._normalize_path() before calling
        status_code (int): HTTP status code (200, 404, 500, etc.)
        duration (float): Request duration in seconds

    Note:
        This function catches all exceptions to ensure metrics recording
        never breaks request processing.

    Example:
        record_request_metrics(
            method='GET',
            path='/api/health/',
            status_code=200,
            duration=0.012
        )
    """
    try:
        # Increment request counter
        http_requests_total.labels(
            method=method,
            path=path,
            status=str(status_code)
        ).inc()

        # Record request duration
        http_request_duration_seconds.labels(
            method=method,
            path=path
        ).observe(duration)

    except Exception as e:
        # Metrics recording should never break requests
        # Log warning and continue
        logger.warning(f"Failed to record Prometheus metrics: {e}", exc_info=True)


def generate_metrics():
    """
    Generate Prometheus metrics in text exposition format.

    Returns:
        bytes: Prometheus metrics in text format

    Example output:
        # HELP http_requests_total Total HTTP requests processed
        # TYPE http_requests_total counter
        http_requests_total{method="GET",path="/api/health/",status="200"} 42.0
        # HELP http_request_duration_seconds HTTP request latency distribution in seconds
        # TYPE http_request_duration_seconds histogram
        http_request_duration_seconds_bucket{le="0.005",method="GET",path="/api/health/"} 10.0
        ...
    """
    return generate_latest(registry)


def get_content_type():
    """
    Get Prometheus content type header value.

    Returns:
        str: Content-Type header value for Prometheus metrics
              Usually 'text/plain; version=0.0.4; charset=utf-8'
    """
    return CONTENT_TYPE_LATEST
