from rest_framework import views, status, permissions
from rest_framework.response import Response
from django.utils import timezone
from django.shortcuts import get_object_or_404
from .models import Copy, CopyLock
import uuid
import datetime

class LockAcquireView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, copy_id):
        copy = get_object_or_404(Copy, id=copy_id)
        user = request.user
        now = timezone.now()
        
        # Default TTL=10min (600s), configurable via body (but enforced max)
        ttl = min(int(request.data.get('ttl_seconds', 600)), 3600)
        expires_at = now + datetime.timedelta(seconds=ttl)

        # Clean expired lock if exists
        try:
            current_lock = copy.lock
            if current_lock.expires_at < now:
                current_lock.delete()
                current_lock = None
        except CopyLock.DoesNotExist:
            current_lock = None

        if current_lock:
            # Idempotency: if owned by requester, return existing token
            if current_lock.owner == user:
                # Refresh expiration on re-acquire
                current_lock.expires_at = expires_at
                current_lock.save()
                return Response({
                    "copy_id": str(copy.id),
                    "status": "LOCKED",
                    "token": str(current_lock.token),
                    "owner": {"id": user.id, "username": user.username},
                    "expires_at": current_lock.expires_at,
                    "server_time": now
                }, status=status.HTTP_200_OK)
            else:
                # Conflict
                return Response({
                    "copy_id": str(copy.id),
                    "status": "LOCKED_BY_OTHER",
                    "owner": {"id": current_lock.owner.id, "username": current_lock.owner.username},
                    "expires_at": current_lock.expires_at,
                    "server_time": now
                }, status=status.HTTP_409_CONFLICT)
        
        # Create new lock
        lock = CopyLock.objects.create(
            copy=copy,
            owner=user,
            expires_at=expires_at
        )
        
        return Response({
            "copy_id": str(copy.id),
            "status": "LOCKED",
            "token": str(lock.token),
            "owner": {"id": user.id, "username": user.username},
            "expires_at": lock.expires_at,
            "server_time": now
        }, status=status.HTTP_201_CREATED)


class LockHeartbeatView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, copy_id):
        # We don't check Copy existence first to avoid double DB hit usually, 
        # but for robustness let's follow standard flow.
        # Actually, faster to query Lock directly.
        try:
            lock = CopyLock.objects.select_related('owner').get(copy_id=copy_id)
        except CopyLock.DoesNotExist:
             return Response({"error": "Lock not found or expired"}, status=status.HTTP_404_NOT_FOUND)

        token = request.data.get('token')
        if not token or str(lock.token) != token:
             return Response({"error": "Invalid lock token"}, status=status.HTTP_403_FORBIDDEN)
        
        if lock.owner != request.user:
             return Response({"error": "Lock owner mismatch"}, status=status.HTTP_403_FORBIDDEN)
             
        # Refresh logic
        now = timezone.now()
        if lock.expires_at < now:
             # Too late, expired
             lock.delete()
             return Response({"error": "Lock expired"}, status=status.HTTP_404_NOT_FOUND)
             
        ttl = 600 # standard refresh
        lock.expires_at = now + datetime.timedelta(seconds=ttl)
        lock.save()
        
        return Response({
            "status": "HEARTBEAT_OK",
            "expires_at": lock.expires_at,
            "server_time": now
        })


class LockReleaseView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request, copy_id):
        try:
            lock = CopyLock.objects.get(copy_id=copy_id)
        except CopyLock.DoesNotExist:
            return Response(status=status.HTTP_204_NO_CONTENT)

        token = request.data.get('token')
        # Check token if provided
        if token and str(lock.token) != token:
             return Response({"error": "Invalid token"}, status=status.HTTP_403_FORBIDDEN)
             
        if lock.owner != request.user:
             return Response({"error": "Not owner"}, status=status.HTTP_403_FORBIDDEN)
             
        lock.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class LockStatusView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, copy_id):
        now = timezone.now()
        try:
            lock = CopyLock.objects.select_related('owner').get(copy_id=copy_id)
            
            # Lazy expire check
            if lock.expires_at < now:
                lock.delete()
                raise CopyLock.DoesNotExist
                
            return Response({
                "status": "LOCKED",
                "owner": {"id": lock.owner.id, "username": lock.owner.username},
                "expires_at": lock.expires_at,
                "server_time": now,
                # Helper for UI to know if it's me
                "is_active_user": (lock.owner == request.user)
            })
            
        except CopyLock.DoesNotExist:
            return Response({
                "status": "UNLOCKED",
                "server_time": now
            })
