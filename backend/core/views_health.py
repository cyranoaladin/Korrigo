from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.db import connection
from django.core.cache import cache
from django.conf import settings
from pathlib import Path

@api_view(['GET'])
@permission_classes([AllowAny])
def health_check(request):
    """
    Basic health check endpoint (legacy compatibility)
    Returns 200 if backend is healthy (DB accessible)
    """
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        
        return Response({
            'status': 'healthy',
            'database': 'connected'
        })
    except Exception as e:
        return Response({
            'status': 'unhealthy',
            'error': str(e)
        }, status=503)


@api_view(['GET'])
@permission_classes([AllowAny])
def liveness_check(request):
    """
    P0-OP-07: Liveness probe for orchestrators (K8s, Docker)
    Minimal check - is the application process running?
    Returns 200 if app is alive, 503 if dead
    """
    return Response({'status': 'alive'}, status=200)


@api_view(['GET'])
@permission_classes([AllowAny])
def readiness_check(request):
    """
    P0-OP-07: Readiness probe for orchestrators (K8s, Docker)
    Comprehensive check - can the app serve traffic?
    Checks: database, cache, media directory
    Returns 200 if ready, 503 if not ready
    """
    checks = {}
    overall_healthy = True
    
    # Check 1: Database connection
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        checks['database'] = 'ok'
    except Exception as e:
        checks['database'] = f'error: {str(e)[:100]}'
        overall_healthy = False
    
    # Check 2: Cache/Redis connection
    try:
        cache.set('health_check_probe', 'ok', 10)
        if cache.get('health_check_probe') == 'ok':
            checks['cache'] = 'ok'
        else:
            checks['cache'] = 'error: cache read failed'
            overall_healthy = False
    except Exception as e:
        checks['cache'] = f'error: {str(e)[:100]}'
        overall_healthy = False
    
    # Check 3: Media directory writable
    try:
        media_root = Path(settings.MEDIA_ROOT)
        test_file = media_root / '.health_check_probe'
        test_file.write_text('ok')
        test_file.unlink()
        checks['media'] = 'ok'
    except Exception as e:
        checks['media'] = f'error: {str(e)[:100]}'
        overall_healthy = False
    
    status_code = 200 if overall_healthy else 503
    return Response({
        'status': 'ready' if overall_healthy else 'not_ready',
        'checks': checks
    }, status=status_code)
