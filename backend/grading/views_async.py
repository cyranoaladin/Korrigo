"""
P0-OP-03: Async task status endpoints
Allows clients to poll for task completion
"""
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.authentication import BasicAuthentication
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status as http_status
from celery.result import AsyncResult
from django.conf import settings


@api_view(['GET'])
@authentication_classes([BasicAuthentication])
@permission_classes([AllowAny])
def task_status(request, task_id):
    """
    GET /api/grading/tasks/<task_id>/
    
    Check status of async Celery task
    
    P0-OP-03 FIX: Enables async PDF processing workflow
    
    Response states:
    - PENDING: Task waiting to be executed
    - STARTED: Task has begun execution
    - SUCCESS: Task completed successfully
    - FAILURE: Task failed (includes error info)
    - RETRY: Task is being retried
    
    Returns:
        200: {
            "task_id": "abc-123",
            "status": "SUCCESS",
            "result": {"copy_id": "...", "status": "graded", "final_score": 75},
            "progress": 100
        }
        
        or on failure:
        200: {
            "task_id": "abc-123",
            "status": "FAILURE",
            "detail": "Failed to generate PDF: ...",
            "traceback": "..."
        }
    """
    if not request.user or not request.user.is_authenticated:
        payload = {'detail': 'Authentication credentials were not provided.'}
        payload['error'] = payload['detail']
        return Response(payload, status=http_status.HTTP_401_UNAUTHORIZED)

    result = AsyncResult(task_id)
    
    response_data = {
        'task_id': task_id,
        'status': result.state,
    }
    
    if result.state == 'PENDING':
        response_data['progress'] = 0
        response_data['message'] = 'Task is waiting in queue'
        
    elif result.state == 'STARTED':
        response_data['progress'] = 50
        response_data['message'] = 'Task is processing'
        
    elif result.state == 'SUCCESS':
        response_data['progress'] = 100
        if isinstance(result.info, dict):
            response_data['result'] = result.info
        elif isinstance(result.result, (dict, list, str, int, float, bool)) or result.result is None:
            response_data['result'] = result.result
        elif isinstance(result.info, (dict, list, str, int, float, bool)) or result.info is None:
            response_data['result'] = result.info
        else:
            response_data['result'] = str(result.result or result.info)
        response_data['message'] = 'Task completed successfully'
        
    elif result.state == 'FAILURE':
        response_data['progress'] = 0
        response_data['detail'] = str(result.info)
        response_data['error'] = response_data['detail']
        response_data['message'] = 'Task failed'
        
        # Include traceback for debugging (admin only)
        if request.user.is_staff:
            response_data['traceback'] = result.traceback
            
    elif result.state == 'RETRY':
        response_data['progress'] = 25
        response_data['message'] = 'Task is retrying after failure'
        if isinstance(result.info, dict):
            response_data['retry_count'] = result.info.get('retry', 0)
        else:
            response_data['retry_count'] = 0
        
    else:
        # Unknown state
        response_data['message'] = f'Unknown task state: {result.state}'
    
    return Response(response_data)


@api_view(['POST'])
@authentication_classes([BasicAuthentication])
@permission_classes([AllowAny])
def cancel_task(request, task_id):
    """
    POST /api/grading/tasks/<task_id>/cancel/
    
    Cancel a running async task (best effort)
    
    Note: Celery task cancellation is not guaranteed if task has already started.
    This sets a flag that the task should stop, but running code may continue.
    
    Returns:
        200: {"status": "cancelled", "task_id": "..."}
        400: {"detail": "Task already completed"}
    """
    result = AsyncResult(task_id)
    
    if result.state in ['SUCCESS', 'FAILURE']:
        payload = {'detail': 'Task already completed, cannot cancel'}
        payload['error'] = payload['detail']
        return Response(payload, status=http_status.HTTP_400_BAD_REQUEST)
    
    # Revoke the task
    result.revoke(terminate=True, signal='SIGTERM')
    
    return Response({
        'status': 'cancelled',
        'task_id': task_id,
        'message': 'Task cancellation requested (may take a few seconds)'
    })
