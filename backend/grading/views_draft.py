from rest_framework import views, status, permissions
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from .models import DraftState, Copy, CopyLock
import uuid

class DraftReturnView(views.APIView):
    """
    GET /api/copies/<uuid:copy_id>/draft/
    PUT /api/copies/<uuid:copy_id>/draft/
    
    Gère le brouillon (Autosave).
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, copy_id):
        # Retrieve latest draft for this user and copy
        try:
            draft = DraftState.objects.get(copy_id=copy_id, owner=request.user)
            return Response({
                "id": str(draft.id),
                "payload": draft.payload,
                "version": draft.version,
                "updated_at": draft.updated_at,
                "client_id": str(draft.client_id) if draft.client_id else None
            })
        except DraftState.DoesNotExist:
             return Response(status=status.HTTP_204_NO_CONTENT)

    def put(self, request, copy_id):
        copy = get_object_or_404(Copy, id=copy_id)
        
        # Lock Enforcement
        token = request.headers.get('X-Lock-Token') or request.data.get('token')
        
        # Verify Lock is held by user (and matches token if provided)
        try:
            lock = CopyLock.objects.get(copy=copy)
            if lock.owner != request.user:
                 return Response({"error": "Lock not held by user"}, status=status.HTTP_409_CONFLICT)
            if token and str(lock.token) != str(token):
                 return Response({"error": "Lock token mismatch"}, status=status.HTTP_409_CONFLICT)
        except CopyLock.DoesNotExist:
             # Lock expired or released
             return Response({"error": "Lock lost (not found)"}, status=status.HTTP_409_CONFLICT)

        payload = request.data.get('payload', {})
        client_id = request.data.get('client_id')
        version_client = request.data.get('version')
        
        # Create or Update
        draft, created = DraftState.objects.get_or_create(
            copy=copy, 
            owner=request.user,
            defaults={
                "payload": payload,
                "lock_token": token,
                "client_id": client_id,
                "version": 1
            }
        )
        
        if not created:
            # Update
            draft.payload = payload
            draft.lock_token = token
            draft.client_id = client_id
            draft.version += 1
            draft.save()
            
        return Response({
            "status": "SAVED",
            "version": draft.version,
            "updated_at": draft.updated_at
        })

    def delete(self, request, copy_id):
        """
        Supprime le brouillon (ex: après une sauvegarde réussie).
        """
        DraftState.objects.filter(copy_id=copy_id, owner=request.user).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
