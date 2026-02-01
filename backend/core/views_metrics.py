"""
P0-OP-08: Metrics endpoint for monitoring
Exposes collected metrics via HTTP endpoint
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser
from django.utils.decorators import method_decorator
from core.middleware.metrics import metrics_collector
from core.utils.ratelimit import maybe_ratelimit
import logging

logger = logging.getLogger('audit')


class MetricsView(APIView):
    """
    GET /api/metrics/ - Returns collected application metrics
    Permission: Admin only
    
    P0-OP-08 FIX: Provides observability endpoint for monitoring systems
    Security: Rate limited to prevent reconnaissance, audit logged
    """
    permission_classes = [IsAdminUser]
    
    @method_decorator(maybe_ratelimit(key='user', rate='60/h', method='GET', block=True))
    def get(self, request):
        """Return current metrics"""
        logger.info(f"Metrics accessed by user {request.user.id}")
        
        metrics = metrics_collector.get_metrics()
        
        # Calculate aggregates
        summary = {
            'total_requests': sum(m['count'] for m in metrics.values()),
            'total_errors': sum(m['errors'] for m in metrics.values()),
            'avg_response_time': 0.0,
            'endpoints': []
        }
        
        total_time = sum(m['total_time'] for m in metrics.values())
        if summary['total_requests'] > 0:
            summary['avg_response_time'] = total_time / summary['total_requests']
        
        # Format endpoint metrics
        for endpoint, m in sorted(metrics.items(), key=lambda x: x[1]['count'], reverse=True):
            avg_time = m['total_time'] / m['count'] if m['count'] > 0 else 0
            summary['endpoints'].append({
                'endpoint': endpoint,
                'count': m['count'],
                'errors': m['errors'],
                'avg_time_ms': round(avg_time * 1000, 2),
                'min_time_ms': round(m['min_time'] * 1000, 2),
                'max_time_ms': round(m['max_time'] * 1000, 2),
                'error_rate': round(m['errors'] / m['count'] * 100, 2) if m['count'] > 0 else 0.0
            })
        
        return Response(summary)
    
    @method_decorator(maybe_ratelimit(key='user', rate='10/h', method='DELETE', block=True))
    def delete(self, request):
        """Reset metrics (admin only)"""
        logger.warning(f"Metrics reset by user {request.user.id}")
        metrics_collector.reset()
        return Response({'status': 'metrics_reset'})
