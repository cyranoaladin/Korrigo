"""
Prometheus /metrics endpoint
Conformité: Phase S5-B - Observability

Exposes Prometheus metrics in standard text exposition format.

Security:
- Development (DEBUG=True): No authentication required
- Production (DEBUG=False):
  - If METRICS_TOKEN environment variable is set:
    - Requires token via X-Metrics-Token header (preferred) OR ?token= query parameter
    - Invalid/missing token: 403 Forbidden
  - If METRICS_TOKEN not set:
    - Public access (operator's choice)
    - Warning logged on startup

URL: /metrics (standard Prometheus convention, at root level)
Format: Prometheus text exposition format (text/plain)
Method: GET only
CSRF: Exempt (Prometheus scraper doesn't send CSRF tokens)

Example usage:
    # Without token (development or public)
    curl http://localhost:8000/metrics

    # With token header (production, preferred)
    curl -H "X-Metrics-Token: secret" http://localhost:8000/metrics

    # With token query param (production, alternative)
    curl http://localhost:8000/metrics?token=secret
"""
import logging
from django.http import HttpResponse
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from core.prometheus import generate_metrics, get_content_type

logger = logging.getLogger('audit')


@csrf_exempt  # Prometheus scraper doesn't send CSRF token
@require_http_methods(["GET"])
def prometheus_metrics_view(request):
    """
    Prometheus /metrics endpoint.

    Returns Prometheus metrics in text exposition format.

    Security:
    - Development (DEBUG=True): No authentication required
    - Production (DEBUG=False):
      - If METRICS_TOKEN set: Token required via header or query param
      - If METRICS_TOKEN not set: Public access (operator chooses)

    Authentication (production):
    1. X-Metrics-Token header (preferred, more secure)
    2. token query parameter (fallback, convenient for Prometheus config)

    Returns:
        HttpResponse:
            - 200 OK with metrics (text/plain) if authorized
            - 403 Forbidden if token invalid or missing (production with METRICS_TOKEN set)

    Example Prometheus configuration:
        scrape_configs:
          - job_name: 'viatique-backend'
            static_configs:
              - targets: ['backend:8000']
            metrics_path: '/metrics'
            params:
              token: ['${METRICS_TOKEN}']  # From environment
    """
    # Development: No authentication required
    if settings.DEBUG:
        metrics_data = generate_metrics()
        return HttpResponse(
            metrics_data,
            content_type=get_content_type()
        )

    # Production: Check token if METRICS_TOKEN configured
    metrics_token = getattr(settings, 'METRICS_TOKEN', None)

    if metrics_token:
        # Method 1: X-Metrics-Token header (preferred, more secure)
        provided_token = request.META.get('HTTP_X_METRICS_TOKEN')

        # Method 2: token query parameter (fallback, convenient)
        if not provided_token:
            provided_token = request.GET.get('token')

        # Validate token
        if not provided_token or provided_token != metrics_token:
            # Log unauthorized access attempt
            logger.warning(
                f"Unauthorized /metrics access attempt",
                extra={
                    'path': '/metrics',
                    'method': 'GET',
                    'remote_addr': request.META.get('REMOTE_ADDR', 'unknown'),
                    'user_agent': request.META.get('HTTP_USER_AGENT', 'unknown'),
                }
            )
            return HttpResponse(
                "Forbidden: Invalid or missing metrics token\n"
                "Provide token via X-Metrics-Token header or ?token= query parameter",
                status=403,
                content_type='text/plain'
            )

    # Token valid or not required: Generate and return metrics
    metrics_data = generate_metrics()
    return HttpResponse(
        metrics_data,
        content_type=get_content_type()
    )
