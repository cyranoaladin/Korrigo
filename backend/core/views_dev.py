from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.conf import settings
import subprocess
import sys

@api_view(['POST'])
@permission_classes([AllowAny])
def seed_e2e_endpoint(request):
    """
    E2E Seeding endpoint - protected by token
    Only available when E2E_SEED_TOKEN is set (prod-like environment)
    """
    # Security: check token
    token = request.headers.get('X-E2E-Seed-Token')
    expected_token = getattr(settings, 'E2E_SEED_TOKEN', None)
    
    if not expected_token:
        return Response({
            'error': 'E2E seeding not enabled (E2E_SEED_TOKEN not set)'
        }, status=503)
    
    if token != expected_token:
        return Response({
            'error': 'Unauthorized - invalid seed token'
        }, status=403)
    
    # Run seed script
    try:
        result = subprocess.run(
            [sys.executable, 'seed_e2e.py'],
            cwd=settings.BASE_DIR,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            return Response({
                'status': 'success',
                'message': 'E2E data seeded successfully',
                'output': result.stdout
            })
        else:
            return Response({
                'status': 'error',
                'message': 'Seed script failed',
                'error': result.stderr
            }, status=500)
            
    except subprocess.TimeoutExpired:
        return Response({
            'status': 'error',
            'message': 'Seed script timeout'
        }, status=500)
    except Exception as e:
        return Response({
            'status': 'error',
            'message': str(e)
        }, status=500)
