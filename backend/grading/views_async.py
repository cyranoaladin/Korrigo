"""
P0-OP-03: Async task status endpoints
Allows clients to poll for task completion
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status as http_status
from celery.result import AsyncResult
from django.conf import settings


@api_view(['GET'])
@permission_classes([IsAuthenticated])
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
            "error": "Failed to generate PDF: ...",
            "traceback": "..."
        }
    """
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
        response_data['result'] = result.result
        response_data['message'] = 'Task completed successfully'
        
    elif result.state == 'FAILURE':
        response_data['progress'] = 0
        response_data['error'] = str(result.info)
        response_data['message'] = 'Task failed'
        
        # Include traceback for debugging (admin only)
        if request.user.is_staff:
            response_data['traceback'] = result.traceback
            
    elif result.state == 'RETRY':
        response_data['progress'] = 25
        response_data['message'] = 'Task is retrying after failure'
        response_data['retry_count'] = result.info.get('retry', 0) if result.info else 0
        
    else:
        # Unknown state
        response_data['message'] = f'Unknown task state: {result.state}'
    
    return Response(response_data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def cancel_task(request, task_id):
    """
    POST /api/grading/tasks/<task_id>/cancel/
    
    Cancel a running async task (best effort)
    
    Note: Celery task cancellation is not guaranteed if task has already started.
    This sets a flag that the task should stop, but running code may continue.
    
    Returns:
        200: {"status": "cancelled", "task_id": "..."}
        400: {"error": "Task already completed"}
    """
    result = AsyncResult(task_id)
    
    if result.state in ['SUCCESS', 'FAILURE']:
        return Response(
            {'error': 'Task already completed, cannot cancel'},
            status=http_status.HTTP_400_BAD_REQUEST
        )
    
    # Revoke the task
    result.revoke(terminate=True, signal='SIGTERM')
    
    return Response({
        'status': 'cancelled',
        'task_id': task_id,
        'message': 'Task cancellation requested (may take a few seconds)'
    })
